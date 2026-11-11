# -*- coding: utf-8 -*-
"""
Générateur de documents sur les deux modèles : Facture (pro forma / facture acquittée) et Bon de réception. Lit les fichiers Excel du dossier "demandes"
et crée les PDF dans le dossier "sortie".
"""
import os, sys, glob, math, unicodedata, datetime
from openpyxl import load_workbook
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth

EXE = getattr(sys, "frozen", False)   # True quand le programme est un .exe (PyInstaller)
BASE = os.path.dirname(sys.executable) if EXE else os.path.dirname(os.path.abspath(__file__))
DOSSIER_DEMANDES = os.path.join(BASE, "demandes")
DOSSIER_SORTIE = os.path.join(BASE, "sortie")
W, H = A4
X0, X1 = 36, W - 36
MOIS_ABR = ["Janv.","Févr.","Mars","Avr.","Mai","Juin","Juil.","Août","Sept.","Oct.","Nov.","Déc."]

# ---------- Utilitaires ----------
def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return "".join(ch for ch in s.lower() if ch.isalnum())

def txt(v):
    return "" if v is None else str(v).strip()

def num(v, default=None):
    if v is None or str(v).strip() == "": return default
    if isinstance(v, (int, float)): return float(v)
    s = str(v).replace("\u00a0", "").replace(" ", "").replace("%", "").replace(",", ".")
    return float(s)

def pct(v, default):
    x = num(v, None)
    if x is None: return default
    return x / 100.0 if x > 1 else x

TIRETS = {"", "-", "--", "---", "—", "–", "_", "/", "n/a", "na", "néant", "neant", "aucune", "aucun"}

def qte_tolerante(v, alertes, ligne):
    """Quantité : vide, espace, tiret (-, --, —) = pas de quantité. Texte non numérique = ignoré avec avertissement."""
    if v is None: return None
    if isinstance(v, (int, float)): return int(round(v)) if v else None
    t = str(v).replace("\u00a0", " ").strip().lower()
    if t in TIRETS: return None
    try:
        x = float(t.replace(" ", "").replace(",", "."))
        return int(round(x)) if x else None
    except ValueError:
        alertes.append(f"Onglet Lignes, ligne {ligne} : quantité « {v} » non reconnue → traitée comme vide (ligne sans quantité)")
        return None

def prix_tolerant(v, alertes, ligne):
    """Prix : vide ou tiret = 0. Texte non numérique = 0 avec avertissement."""
    if v is None: return 0.0
    if isinstance(v, (int, float)): return float(v)
    t = str(v).replace("\u00a0", " ").strip().lower()
    if t in TIRETS: return 0.0
    try: return float(t.replace(" ", "").replace(",", "."))
    except ValueError:
        alertes.append(f"Onglet Lignes, ligne {ligne} : prix « {v} » non reconnu → traité comme 0")
        return 0.0

def marge_pct(v, default=0.0):
    """Marge facultative : vide = défaut. 5 ou 5% ou 0,05 = 5 % ; 1 = 1 %."""
    x = num(v, None)
    if x is None: return default
    return x / 100.0 if x >= 1 else x

def arrondi(x, pas):
    pas = max(1, int(pas or 1))
    return int(math.floor(x / pas + 0.5) * pas)

def fmt2(n):
    return f"{n:,.2f}".replace(",", " ").replace(".", ",")

def date_num(d):
    if isinstance(d, (datetime.datetime, datetime.date)): return d.strftime("%d/%m/%Y")
    return txt(d)

def date_abr(d):
    if isinstance(d, (datetime.datetime, datetime.date)): return f"{d.day:02d} {MOIS_ABR[d.month-1]} {d.year}"
    return txt(d)

def fr_words(n):
    UN = ["","un","deux","trois","quatre","cinq","six","sept","huit","neuf","dix","onze","douze",
          "treize","quatorze","quinze","seize","dix-sept","dix-huit","dix-neuf"]
    DIZ = {2:"vingt",3:"trente",4:"quarante",5:"cinquante",6:"soixante"}
    def b100(n, term):
        if n < 20: return UN[n]
        if n < 70:
            t, u = divmod(n, 10)
            return DIZ[t] + ("" if u == 0 else (" et un" if u == 1 else "-" + UN[u]))
        if n < 80: return "soixante" + (" et onze" if n == 71 else "-" + UN[n-60])
        if n == 80: return "quatre-vingts" if term else "quatre-vingt"
        return "quatre-vingt-" + UN[n-80]
    def b1000(n, term):
        h, r = divmod(n, 100); p = []
        if h: p.append("cent" if h == 1 else UN[h] + " cent" + ("s" if r == 0 and term else ""))
        if r: p.append(b100(r, term))
        return " ".join(p)
    n = int(round(n))
    if n == 0: return "zéro"
    if n >= 10**9: raise ValueError("Montant trop grand")
    m, rest = divmod(n, 10**6); t, u = divmod(rest, 1000); p = []
    if m: p.append("un million" if m == 1 else b1000(m, True) + " millions")
    if t: p.append("mille" if t == 1 else b1000(t, False) + " mille")
    if u: p.append(b1000(u, True))
    return " ".join(p)

def montant_lettres(n):
    return fr_words(n).upper() + " francs CFA"

# ---------- Lecture Excel ----------
CLES_PARAM = {
    "nomdelentreprise": "nom", "activite": "activite", "adresse": "adresse", "ninea": "ninea", "rc": "rc",
    "email": "email", "telephones": "tel", "ndecompte": "compte", "banque": "banque",
    "titredusignataire": "signataire", "tva": "tva", "margepardefaut": "marge_def",
    "arrondiprixproforma": "arrondi", "fichiercachetoptionnel": "cachet", "siteweb": "web",
    "fichierlogooptionnel": "logo", "montantenlettresouinon": "lettres", "margeaussisurlafactureouinon": "marge_facture",
    "libelleduregistrercrccm": "rc_label", "conditionsdereglementpardefaut": "cond_def",
    "modedereglementpardefaut": "mode_def", "mentionsbasdefacture": "mentions",
    "themedesdocumentsclassiquecharte": "theme", "themedesdocumentsecocharteclassique": "theme", "slogansecondaire": "slogan2", "fichierlogoeconomiquethemeeco": "logo_eco", "fichierlogothemecharte": "logo_charte",
}

def lire_fichier(chemin):
    wb = load_workbook(chemin, data_only=True)
    noms = {norm(n): n for n in wb.sheetnames}
    for requis in ("parametres", "documents", "lignes"):
        if requis not in noms:
            raise ValueError(f"Onglet « {requis.capitalize()} » introuvable dans {os.path.basename(chemin)}")
    P = {}
    for row in wb[noms["parametres"]].iter_rows(min_row=1, values_only=True):
        if row and row[0] and norm(row[0]) in CLES_PARAM:
            P[CLES_PARAM[norm(row[0])]] = row[1]
    P["tva"] = pct(P.get("tva"), 0.18)
    P["marge_def"] = marge_pct(P.get("marge_def"), 0.0)
    P["arrondi"] = int(num(P.get("arrondi"), 1) or 1)
    def g(row, i): return row[i] if len(row) > i else None
    docs = []
    for row in wb[noms["documents"]].iter_rows(min_row=2, values_only=True):
        if row and row[0] is not None and txt(row[0]):
            docs.append(dict(num=txt(row[0]), date=row[1], client=txt(row[2]), marque=txt(row[3]), type=txt(row[4]),
                             immat=txt(row[5]), marge=row[6], acquittee=txt(row[7]), code=txt(g(row, 8)),
                             adresse=txt(g(row, 9)), echeance=g(row, 10), conditions=txt(g(row, 11)),
                             mode=txt(g(row, 12)), num_bl=txt(g(row, 13)), ref=txt(g(row, 14)),
                             incoterm=txt(g(row, 15)), lieu=txt(g(row, 16)), bc=txt(g(row, 17)), km=txt(g(row, 18))))
    lignes = {}; alertes = []; dernier = ""
    for i, row in enumerate(wb[noms["lignes"]].iter_rows(min_row=2, values_only=True), start=2):
        if not row: continue
        ndoc = txt(row[0]); des = txt(g(row, 2))
        if not des:
            if ndoc: dernier = ndoc
            if txt(g(row, 3)) not in TIRETS or (ndoc and txt(g(row, 1)) not in TIRETS):
                alertes.append(f"Onglet Lignes, ligne {i} : un montant ou une quantité est saisi SANS désignation → ligne ignorée")
            continue
        if not ndoc:
            if dernier:
                ndoc = dernier
                alertes.append(f"Onglet Lignes, ligne {i} : « {des} » n'avait pas de N° document → rattachée au dossier {dernier}")
            else:
                alertes.append(f"Onglet Lignes, ligne {i} : « {des} » n'a pas de N° document → ligne ignorée")
                continue
        else:
            dernier = ndoc
        lignes.setdefault(ndoc, []).append(
            dict(qte=qte_tolerante(row[1], alertes, i), des=des, prix=prix_tolerant(g(row, 3), alertes, i),
                 tva=(pct(g(row, 4), None) if txt(g(row, 4)).lower() not in TIRETS else None), comm=txt(g(row, 5))))
    connus = {d["num"] for d in docs}
    for n_, lst in lignes.items():
        if n_ not in connus:
            alertes.append(f"Onglet Lignes : le N° « {n_} » n'existe pas dans l'onglet Documents → {len(lst)} ligne(s) ignorée(s)")
    versements = {}
    if "versements" in noms:
        for row in wb[noms["versements"]].iter_rows(min_row=2, values_only=True):
            if row and row[0] is not None and txt(row[0]) and num(row[2], None) is not None:
                versements.setdefault(txt(row[0]), []).append(
                    dict(date=row[1], montant=num(row[2], 0.0), type=txt(g(row, 3)), num=txt(g(row, 4))))
    for n_ in versements:
        if n_ not in connus:
            alertes.append(f"Onglet Versements : le N° « {n_} » n'existe pas dans l'onglet Documents → versement(s) ignoré(s)")
    return P, docs, lignes, versements, alertes

# ---------- Éléments de dessin ----------
def fit_font(c, text, font, size, maxw, mini=6):
    while size > mini and stringWidth(text, font, size) > maxw: size -= 0.5
    return size

def centered(c, x, y, text, font, size, maxw=None):
    if maxw: size = fit_font(c, text, font, size, maxw)
    c.setFont(font, size); c.drawCentredString(x, y, text)

def underlined(c, x, y, text, font, size, align="left"):
    c.setFont(font, size); w = stringWidth(text, font, size)
    x0 = x if align == "left" else (x - w if align == "right" else x - w/2)
    c.drawString(x0, y, text); c.setLineWidth(0.7); c.line(x0, y-1.8, x0+w, y-1.8)

def chemin_image(nom):
    nom = txt(nom)
    if not nom: return None
    p = nom if os.path.isabs(nom) else os.path.join(BASE, nom)
    return p if os.path.exists(p) else None

def logo_ou_nom(c, P, x, ytop, maxw=190, maxh=62):
    p = chemin_image(P.get("logo"))
    if p:
        try:
            c.drawImage(p, x, ytop-maxh, width=maxw, height=maxh, preserveAspectRatio=True, mask="auto", anchor="nw")
            return
        except Exception:
            pass
    nom = txt(P.get("nom")); sz = fit_font(c, nom, "Helvetica-Bold", 17, 250)
    c.setFillColorRGB(.2, .2, .3); c.setFont("Helvetica-Bold", sz); c.drawString(x, ytop-26, nom)
    c.setFillColorRGB(0, 0, 0)

def bloc_entreprise(c, P, x, y, size=9, width=230):
    c.setFont("Helvetica-Bold", size+1.5); c.drawString(x, y, txt(P.get("nom"))); y -= 12
    if txt(P.get("activite")):
        c.setFont("Helvetica-Oblique", size-1); c.drawString(x, y, " ".join(txt(P.get("activite")).split())); y -= 11
    c.setFont("Helvetica", size)
    for l in simpleSplit(txt(P.get("adresse")), "Helvetica", size, width):
        c.drawString(x, y, l); y -= 11
    y -= 5
    for lab, key in (("Tél.: ", "tel"), ("Email: ", "email"), ("Web: ", "web")):
        if txt(P.get(key)):
            c.drawString(x, y, lab + txt(P.get(key))); y -= 11
    return y

def bloc_client(c, D, x, y, width=240, size=9):
    c.setFont("Helvetica-Bold", size+1.5); c.drawString(x, y, D["client"]); y -= 12
    c.setFont("Helvetica", size)
    for raw in D["adresse"].replace("\r", "").split("\n"):
        for l in simpleSplit(raw, "Helvetica", size, width):
            c.drawString(x, y, l); y -= 11
    return y

def pied(c, P):
    c.setFont("Helvetica", 7)
    c.drawCentredString(W/2, 29, f"{txt(P.get('rc_label')) or 'RC'}: {txt(P.get('rc'))} - NINEA: {txt(P.get('ninea'))}")
    ligne = " ".join(x for x in (f"N° Cpte : {txt(P.get('compte'))}" if txt(P.get("compte")) else "", txt(P.get("banque"))) if x)
    if ligne: c.drawCentredString(W/2, 20, ligne)
    c.drawRightString(X1, 29, "1/1")

def cachet_img(c, P, x, y, w, h):
    p = chemin_image(P.get("cachet"))
    if p:
        try: c.drawImage(p, x, y, width=w, height=h, preserveAspectRatio=True, mask="auto", anchor="c")
        except Exception: pass

def bloc_vehicule(c, D, x, y, size=9):
    c.setFont("Helvetica", size)
    if D["immat"]: c.drawString(x, y, f"Véhicule : {D['immat']}"); y -= 11
    mt = " ".join(t for t in (D["marque"], D["type"]) if t)
    if mt: c.drawString(x, y, mt); y -= 11
    if D["km"]:
        km = D["km"]
        if km.replace(" ", "").isdigit(): km = f"{int(km.replace(' ', '')):,}".replace(",", " ")
        if "km" not in km.lower(): km += " km"
        c.drawString(x, y, f"Kilométrage : {km}"); y -= 11
    return y

def en_tete(c, P, D, titre, kind):
    logo_ou_nom(c, P, X0, H-30)
    c.setFont("Helvetica-Bold", 15)
    if kind == "br":
        c.drawRightString(X1, H-48, f"{titre} N° {D['num_bl'] or D['num']}")
        c.setFont("Helvetica", 12); c.drawRightString(X1, H-64, f"Date : {date_abr(D['date'])}"); yy = H - 80
        if D["code"]: c.drawRightString(X1, yy, f"Code client : {D['code']}"); yy -= 12
        if D["ref"]:
            c.setFont("Helvetica", 7.5); c.drawRightString(X1, yy, f"Réf. commande / Réf. expédition : {D['ref']}")
    else:
        c.drawRightString(X1, H-48, f"{titre} N° {D['num']}")
        c.setFont("Helvetica", 7.5); yy = H - 62
        lab_date = "Date" if kind == "proforma" else "Date facturation"
        for lab, val in ((lab_date, date_num(D["date"])), ("Date échéance", date_num(D["echeance"])), ("Code client", D["code"])):
            if val: c.drawRightString(X1, yy, f"{lab}   {val}"); yy -= 10

# ---------- Modèle 1 : Facture (pro forma / facture / facture acquittée) ----------
def marge_sur_facture(P):
    return norm(P.get("marge_facture")) != "non"   # OUI par défaut

def dessiner_facture(c, P, D, L, V, kind):
    avec = kind == "proforma" or (kind == "facture" and marge_sur_facture(P))
    ht, tva, ttc = totaux(P, D, L, avec)
    paye = (sum(v["montant"] for v in V) if V else ttc) if kind == "facture" else 0
    reste = ttc - paye
    titre = "Facture pro forma" if kind == "proforma" else ("Facture acquittée" if abs(reste) < 0.5 else "Facture")
    en_tete(c, P, D, titre, kind)
    bloc_entreprise(c, P, X0, H-135)
    y = bloc_client(c, D, 300, H-135); bloc_vehicule(c, D, 300, y-3)
    c.setFont("Helvetica", 8); c.drawRightString(X1, H-258, "Montants exprimés en Francs CFA BCEAO")
    top = H - 262; HDR, RH, bottom = 18, 14, 238
    nmax = int((top - HDR - bottom) / RH)
    if len(L) > nmax: raise ValueError(f"Trop de lignes ({len(L)}) pour {D['num']} (maximum {nmax})")
    E = [X0, 300, 350, 440, 482, X1]
    c.setFillColorRGB(.95, .95, .95); c.rect(X0, top-HDR, X1-X0, HDR, fill=1, stroke=0); c.setFillColorRGB(0, 0, 0)
    c.setLineWidth(0.6); c.rect(X0, bottom, X1-X0, top-bottom); c.line(X0, top-HDR, X1, top-HDR)
    for x in E[1:-1]: c.line(x, top, x, bottom)
    c.setFont("Helvetica", 9); c.drawString(E[0]+4, top-HDR+5.5, "Désignation")
    for i, h in ((1, "TVA"), (2, "P.U. HT"), (3, "Qté"), (4, "Total HT")):
        centered(c, (E[i]+E[i+1])/2, top-HDR+5.5, h, "Helvetica", 9)
    for i, l in enumerate(L):
        q = l["qte"] or 1
        pu = arrondi(l["prix"] * (1 + D["marge_eff"]), P["arrondi"]) if avec else l["prix"]
        rate = P["tva"] if l["tva"] is None else l["tva"]
        yb = top - HDR - i*RH - 10
        c.setFont("Helvetica", fit_font(c, l["des"], "Helvetica", 8.5, E[1]-E[0]-10)); c.drawString(E[0]+4, yb, l["des"])
        c.setFont("Helvetica", 8.5)
        c.drawRightString(E[2]-6, yb, f"{rate*100:g}%")
        if l["qte"]: c.drawRightString(E[3]-6, yb, fmt2(pu))
        c.drawRightString(E[4]-6, yb, str(l["qte"]) if l["qte"] else "")
        c.drawRightString(E[5]-6, yb, fmt2(q * pu))
    # gauche : conditions, (montant en lettres + signataire)
    yl = bottom - 16
    cond = D["conditions"] or txt(P.get("cond_def")); mode = D["mode"] or txt(P.get("mode_def"))
    for lab, val in (("Conditions de règlement:", cond), ("Mode de règlement:", mode)):
        c.setFont("Helvetica-Bold", 8.5); c.drawString(X0, yl, lab)
        c.setFont("Helvetica", 8.5)
        for k, ligne in enumerate(simpleSplit(val, "Helvetica", 8.5, 172) or [""]):
            c.drawString(X0+118, yl, ligne); yl -= 11
        yl -= 4
    ment = txt(P.get("mentions"))
    if ment:
        c.setFont("Helvetica-Bold", 8.5); c.drawString(X0, yl, "Mentions"); yl -= 10
        c.setFont("Helvetica", 7)
        for ligne in simpleSplit(ment, "Helvetica", 7, 285):
            c.drawString(X0, yl, ligne); yl -= 8.5
        yl -= 4
    if norm(P.get("lettres")) != "non":
        mot = "FACTURE PRO FORMA" if kind == "proforma" else "FACTURE"
        c.setFont("Helvetica", 7.5); c.drawString(X0, yl-4, f"ARRÊTÉE LA PRÉSENTE {mot} A LA SOMME DE :"); yl -= 17
        c.setFont("Helvetica-Bold", 8.5)
        for ligne in simpleSplit(montant_lettres(ttc), "Helvetica-Bold", 8.5, 270):
            c.drawString(X0, yl, ligne); yl -= 11
        sig = txt(P.get("signataire")) or "LE PRÉSIDENT"
        underlined(c, X0, yl-12, sig.upper(), "Helvetica-Bold", 9.5)
    # droite : totaux
    rows = [("Total HT", ht, False)]
    if tva > 0: rows.append(("TVA", tva, False))
    rows.append(("Total TTC", ttc, True))
    if kind == "facture": rows += [("Payé", paye, False), ("Reste à payer", reste, True)]
    y = bottom - 14; LX = 330
    for lab, val, shade in rows:
        if shade:
            c.setFillColorRGB(.82, .82, .82); c.rect(LX, y-4, X1-LX, 14, fill=1, stroke=0); c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 9.5); c.drawString(LX+2, y, lab); c.drawRightString(X1-2, y, fmt2(val)); y -= 15
    if kind == "facture" and V:
        y -= 8
        c.setFont("Helvetica-Bold", 7); c.drawString(LX+2, y, "Versements déjà effectués"); y -= 9
        cols = [LX+2, LX+62, LX+132, LX+172]
        c.setLineWidth(0.4); c.line(LX, y+7, X1, y+7)
        for xx, h in zip(cols, ("Règlement", "Montant", "Type", "Num")):
            c.setFont("Helvetica-Bold", 6.5); c.drawString(xx, y, h)
        c.line(LX, y-3, X1, y-3); y -= 11
        for v in V[:5]:
            c.setFont("Helvetica", 6.8)
            c.drawString(cols[0], y, date_num(v["date"])); c.drawString(cols[1], y, fmt2(v["montant"]))
            c.drawString(cols[2], y, v["type"]); c.drawString(cols[3], y, v["num"]); y -= 9
        c.line(LX, y+6, X1, y+6)
    cachet_img(c, P, X1-150, 38, 140, 62)
    pied(c, P)

# ---------- Modèle 2 : Bon de réception ----------
def dessiner_bon_reception(c, P, D, L):
    en_tete(c, P, D, "Bon de réception", "br")
    c.setFont("Helvetica", 7.5); c.drawString(X0, H-142, "Émetteur"); c.drawString(250, H-134, "Adresse de livraison")
    c.setFillColorRGB(.96, .96, .96); c.rect(X0, H-262, 200, 114, fill=1, stroke=0); c.setFillColorRGB(0, 0, 0)
    bloc_entreprise(c, P, X0+8, H-164, width=185)
    c.setLineWidth(0.6); c.rect(250, H-262, X1-250, 124)
    y = bloc_client(c, D, 258, H-154, 290); bloc_vehicule(c, D, 258, y-3)
    c.setFillColorRGB(.96, .96, .96); c.rect(X0, H-282, X1-X0, 14, fill=1, stroke=0); c.setFillColorRGB(0, 0, 0)
    c.rect(X0, H-282, X1-X0, 14)
    c.setFont("Helvetica", 8.5); c.drawString(X0+4, H-278, f"Incoterm : {D['incoterm']}".rstrip())
    c.rect(X0, H-322, X1-X0, 34)
    lab1, lab2 = "Lieu de livraison : ", "Numéro bon de commande : "
    c.setFont("Helvetica-Bold", 8.5); c.drawString(X0+4, H-302, lab1); c.drawString(X0+4, H-314, lab2)
    c.setFont("Helvetica", 8.5)
    c.drawString(X0+4+stringWidth(lab1, "Helvetica-Bold", 8.5), H-302, D["lieu"])
    c.drawString(X0+4+stringWidth(lab2, "Helvetica-Bold", 8.5), H-314, D["bc"])
    top = H - 336; HDR, RH, bottom = 20, 15, 150
    nmax = int((top - HDR - bottom) / RH)
    if len(L) > nmax: raise ValueError(f"Trop de lignes ({len(L)}) pour le bon de réception {D['num']} (maximum {nmax})")
    E = [X0, 300, 430, 495, X1]
    c.rect(X0, bottom, X1-X0, top-bottom); c.line(X0, top-HDR, X1, top-HDR)
    for x in E[1:-1]: c.line(x, top, x, bottom)
    c.setFont("Helvetica", 9); c.drawString(E[0]+4, top-HDR+6, "Désignation")
    for i, h in ((1, "Commentaires"), (2, "Qté exp."), (3, "Reste")):
        centered(c, (E[i]+E[i+1])/2, top-HDR+6, h, "Helvetica", 9)
    for i, l in enumerate(L):
        yb = top - HDR - i*RH - 11
        c.setFont("Helvetica", fit_font(c, l["des"], "Helvetica", 9, E[1]-E[0]-10)); c.drawString(E[0]+4, yb, l["des"])
        if l["comm"]:
            c.setFont("Helvetica", fit_font(c, l["comm"], "Helvetica", 8.5, E[2]-E[1]-8)); c.drawString(E[1]+4, yb, l["comm"])
        c.setFont("Helvetica", 9)
        if l["qte"]: c.drawRightString(E[3]-8, yb, str(l["qte"]))
    nom = txt(P.get("nom"))
    signature_boite(c, X0+8, 46, 226, 92, f"Pour {nom}:", cachet=True, P=P)
    signature_boite(c, 330, 46, X1-330, 92, "Pour le client:")
    pied(c, P)

def signature_boite(c, x, y, w, h, titre, cachet=None, P=None):
    c.setLineWidth(0.6); c.rect(x, y, w, h)
    c.setFont("Helvetica", 9.5); c.drawString(x+8, y+h-14, titre)
    if cachet: cachet_img(c, P, x+10, y+4, w-20, h-24)

# ---------- Thème « CHARTE » (noir / rouge / argent) ----------
RED = (0.890, 0.071, 0.122); NEON = (1.0, 0.165, 0.165); LIGHT = (0.949, 0.953, 0.961)
SILV = (0.788, 0.808, 0.839); STEEL = (0.553, 0.580, 0.620); ANTH = (0.063, 0.063, 0.071)

ECO = False
def theme_charte(P):
    return norm(P.get("theme")).startswith(("charte", "eco"))

def theme_eco(P):
    return norm(P.get("theme")).startswith("eco")

def bandeau_eco(c, P):
    p = chemin_image(P.get("logo_eco"))
    if p:
        try: c.drawImage(p, X0, H-84, width=215, height=68, preserveAspectRatio=True, anchor="w")
        except Exception: pass
    else:
        c.setFont("Helvetica-Bold", 18); c.drawString(X0, H-50, txt(P.get("nom")).upper())
    infos = [txt(P.get("adresse")), (f"Tél : {txt(P.get('tel'))}" if txt(P.get("tel")) else ""), txt(P.get("email")), txt(P.get("web"))]
    y = H - 38
    c.setFillColorRGB(0.25, 0.25, 0.28)
    for t in infos:
        if not t: continue
        for ligne in simpleSplit(t, "Helvetica", 7.5, 230):
            c.setFont("Helvetica", 7.5); c.drawRightString(X1, y, ligne); y -= 9.5
    c.setFillColorRGB(0, 0, 0)
    c.setStrokeColorRGB(*RED); c.setLineWidth(1.4); c.line(X0, H-92, X1, H-92); c.setStrokeColorRGB(0, 0, 0)

def bandeau(c, P):
    if ECO: return bandeau_eco(c, P)
    c.setFillColorRGB(0, 0, 0); c.rect(0, H-84, W, 84, fill=1, stroke=0)
    c.setFillColorRGB(*RED); c.rect(0, H-87, W, 3, fill=1, stroke=0)
    p = chemin_image(P.get("logo_charte")) or chemin_image(P.get("logo"))
    if p:
        try: c.drawImage(p, X0-8, H-83, width=112, height=82, preserveAspectRatio=True, anchor="c")
        except Exception: pass
    x = X0 + 112
    c.setFillColorRGB(1, 1, 1); c.setFont("Helvetica-Bold", 21); c.drawString(x, H-36, txt(P.get("nom")).upper())
    sl = txt(P.get("activite")); xx = x; f = "Helvetica"
    c.setFont(f, 9.5)
    parts = [(sl, (0.95, 0.95, 0.96))]
    if "sécurité" in sl:
        pre, post = sl.split("sécurité", 1)
        parts = [(pre, (0.95, 0.95, 0.96)), ("sécurité", NEON), (post, (0.95, 0.95, 0.96))]
    for part, col in parts:
        c.setFillColorRGB(*col); c.drawString(xx, H-51, part); xx += stringWidth(part, f, 9.5)
    infos = [txt(P.get("adresse")), (f"Tél : {txt(P.get('tel'))}" if txt(P.get("tel")) else ""), txt(P.get("email")), txt(P.get("web"))]
    ligne = " · ".join(t for t in infos if t)
    c.setFillColorRGB(*STEEL); c.setFont("Helvetica", fit_font(c, ligne, "Helvetica", 7.2, W-x-X0))
    c.drawString(x, H-66, ligne); c.setFillColorRGB(0, 0, 0)

def entete_charte(c, P, titre, infos):
    bandeau(c, P)
    c.setFillColorRGB(*RED); c.setFont("Helvetica-Bold", 20); c.drawString(X0, H-118, titre.upper()); c.setFillColorRGB(0, 0, 0)
    y = H - 103
    for lab, val in infos:
        c.setFont("Helvetica", 8.5); w = stringWidth(val, "Helvetica", 8.5); c.drawRightString(X1, y, val)
        c.setFont("Helvetica-Bold", 8.5); c.drawRightString(X1-w-3, y, lab); y -= 11

def boite(c, x, y, w, h, titre):
    if ECO:
        c.setStrokeColorRGB(*SILV); c.setLineWidth(0.6); c.rect(x, y-h, w, h); c.setStrokeColorRGB(0, 0, 0)
    else:
        c.setFillColorRGB(*LIGHT); c.rect(x, y-h, w, h, fill=1, stroke=0)
    c.setFillColorRGB(*RED); c.rect(x, y-1.3, w, 1.3, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 8); c.drawString(x+8, y-14, titre); c.setFillColorRGB(0, 0, 0)
    return y - 28

def champ(c, x, y, w, lab, val):
    if not val: return y
    c.setFont("Helvetica-Bold", 8.5); c.drawString(x, y, lab); lw = stringWidth(lab+" ", "Helvetica-Bold", 8.5)
    lignes = []
    for raw in val.replace("\r", "").split("\n"): lignes += simpleSplit(raw, "Helvetica", 8.5, w-lw) or [""]
    c.setFont("Helvetica", 8.5)
    for k, l in enumerate(lignes):
        c.drawString(x+lw if k == 0 else x, y, l); y -= 10.5
    return y

def boites_client_vehicule(c, D, top, h, titre_client):
    y = boite(c, X0, top, 255, h, titre_client)
    y = champ(c, X0+8, y, 240, "Client :", D["client"]); champ(c, X0+8, y, 240, "Adresse :", D["adresse"])
    y = boite(c, X0+268, top, X1-X0-268, h, "VÉHICULE")
    y = champ(c, X0+276, y, 235, "Marque / modèle :", " ".join(t for t in (D["marque"], D["type"]) if t))
    y = champ(c, X0+276, y, 235, "Immatriculation :", D["immat"])
    km = D["km"]
    if km:
        if km.replace(" ", "").isdigit(): km = f"{int(km.replace(' ', '')):,}".replace(",", " ")
        if "km" not in km.lower(): km += " km"
    champ(c, X0+276, y, 235, "Kilométrage :", km)

def pied_charte(c, P):
    c.setStrokeColorRGB(*SILV); c.setLineWidth(0.6); c.line(X0, 46, X1, 46); c.setStrokeColorRGB(0, 0, 0)
    l1 = " · ".join(t for t in (txt(P.get("nom")).upper(), txt(P.get("activite")), txt(P.get("slogan2"))) if t)
    c.setFont("Helvetica-Bold", 7.5); c.drawCentredString(W/2, 35, l1)
    l2 = f"NINEA : {txt(P.get('ninea'))} · {txt(P.get('rc_label')) or 'RC'} : {txt(P.get('rc'))}"
    cpt = " ".join(t for t in (f"N° Cpte : {txt(P.get('compte'))}" if txt(P.get("compte")) else "", txt(P.get("banque"))) if t)
    if cpt: l2 += " · " + cpt
    c.setFillColorRGB(*STEEL); c.setFont("Helvetica", 7); c.drawCentredString(W/2, 25, l2)
    c.drawRightString(X1, 25, "Page 1"); c.setFillColorRGB(0, 0, 0)

def entete_tableau(c, E, top, HDR, heads):
    if ECO:
        c.setFillColorRGB(0, 0, 0); c.setLineWidth(1.2); c.line(E[0], top-HDR, E[-1], top-HDR); c.setLineWidth(0.6)
    else:
        c.setFillColorRGB(0, 0, 0); c.rect(E[0], top-HDR, E[-1]-E[0], HDR, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
    for i, h in enumerate(heads):
        if i == 0: c.setFont("Helvetica-Bold", 8.5); c.drawString(E[0]+6, top-HDR+6, h)
        else: centered(c, (E[i]+E[i+1])/2, top-HDR+6, h, "Helvetica-Bold", 8.5)
    c.setFillColorRGB(0, 0, 0)

def cadre_tableau(c, E, top, bottom, HDR, RH, nlignes):
    c.setStrokeColorRGB(*SILV); c.setLineWidth(0.6)
    c.rect(E[0], bottom, E[-1]-E[0], top-bottom)
    for x in E[1:-1]: c.line(x, top-HDR, x, bottom)
    for i in range(1, nlignes+1): c.line(E[0], top-HDR-i*RH, E[-1], top-HDR-i*RH)
    c.setStrokeColorRGB(0, 0, 0)

def dessiner_facture_charte(c, P, D, L, V, kind):
    avec = kind == "proforma" or (kind == "facture" and marge_sur_facture(P))
    ht, tva, ttc = totaux(P, D, L, avec)
    paye = (sum(v["montant"] for v in V) if V else ttc) if kind == "facture" else 0
    reste = ttc - paye
    titre = "Facture pro forma" if kind == "proforma" else ("Facture acquittée" if abs(reste) < 0.5 else "Facture")
    infos = [("N° :", D["num"]), ("Date :", date_num(D["date"]))]
    if D["echeance"]: infos.append(("Échéance :", date_num(D["echeance"])))
    if D["code"]: infos.append(("Code client :", D["code"]))
    entete_charte(c, P, titre, infos)
    boites_client_vehicule(c, D, H-148, 66, "FACTURÉ À")
    c.setFont("Helvetica", 7.5); c.drawRightString(X1, H-223, "Montants exprimés en Francs CFA BCEAO")
    top = H - 228; HDR, RH, bottom = 20, 14, 238
    nmax = int((top - HDR - bottom) / RH)
    if len(L) > nmax: raise ValueError(f"Trop de lignes ({len(L)}) pour {D['num']} (maximum {nmax})")
    E = [X0, 300, 350, 440, 482, X1]
    cadre_tableau(c, E, top, bottom, HDR, RH, len(L))
    entete_tableau(c, E, top, HDR, ["Désignation", "TVA", "P.U. HT", "Qté", "Total HT"])
    for i, l in enumerate(L):
        q = l["qte"] or 1
        pu = arrondi(l["prix"] * (1 + D["marge_eff"]), P["arrondi"]) if avec else l["prix"]
        rate = P["tva"] if l["tva"] is None else l["tva"]
        yb = top - HDR - i*RH - 10
        c.setFont("Helvetica", fit_font(c, l["des"], "Helvetica", 8.5, E[1]-E[0]-12)); c.drawString(E[0]+6, yb, l["des"])
        c.setFont("Helvetica", 8.5)
        c.drawRightString(E[2]-6, yb, f"{rate*100:g}%")
        if l["qte"]: c.drawRightString(E[3]-6, yb, fmt2(pu))
        c.drawRightString(E[4]-6, yb, str(l["qte"]) if l["qte"] else "")
        c.drawRightString(E[5]-6, yb, fmt2(q * pu))
    # gauche
    yl = bottom - 16
    cond = D["conditions"] or txt(P.get("cond_def")); mode = D["mode"] or txt(P.get("mode_def"))
    for lab, val in (("Modalités de paiement", None),):
        pass
    for lab, val in (("Conditions :", cond), ("Paiement :", mode)):
        if not val: continue
        c.setFillColorRGB(*RED); c.setFont("Helvetica-Bold", 8.5); c.drawString(X0, yl, lab); c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 8.5)
        for ligne in simpleSplit(val, "Helvetica", 8.5, 220):
            c.drawString(X0+62, yl, ligne); yl -= 11
        yl -= 3
    ment = txt(P.get("mentions"))
    if ment:
        c.setFillColorRGB(*RED); c.setFont("Helvetica-Bold", 8.5); c.drawString(X0, yl, "Mentions"); c.setFillColorRGB(0, 0, 0); yl -= 10
        c.setFillColorRGB(*STEEL); c.setFont("Helvetica", 7)
        for ligne in simpleSplit(ment, "Helvetica", 7, 285): c.drawString(X0, yl, ligne); yl -= 8.5
        c.setFillColorRGB(0, 0, 0); yl -= 4
    if norm(P.get("lettres")) != "non":
        mot = "FACTURE PRO FORMA" if kind == "proforma" else "FACTURE"
        c.setFont("Helvetica", 7.5); c.drawString(X0, yl-4, f"ARRÊTÉE LA PRÉSENTE {mot} A LA SOMME DE :"); yl -= 17
        c.setFont("Helvetica-Bold", 8.5)
        for ligne in simpleSplit(montant_lettres(ttc), "Helvetica-Bold", 8.5, 270): c.drawString(X0, yl, ligne); yl -= 11
        sig = txt(P.get("signataire")) or "LE PRÉSIDENT"
        c.setFont("Helvetica-Bold", 8.5); c.drawString(X0, yl-12, sig)
    # totaux
    rows = [("Total HT", ht, "light")]
    if tva > 0: rows.append(("TVA", tva, "light"))
    rows.append(("TOTAL TTC", ttc, "red"))
    if kind == "facture": rows += [("Payé", paye, "light"), ("Reste à payer", reste, "black")]
    y = bottom - 14; LX = 330
    for lab, val, style in rows:
        if ECO:
            col = RED if style == "red" else (0, 0, 0)
            if style != "light":
                c.setStrokeColorRGB(*col); c.setLineWidth(1.1); c.line(LX, y+11, X1, y+11); c.line(LX, y-5, X1, y-5); c.setStrokeColorRGB(0, 0, 0)
            c.setFillColorRGB(*col); c.setFont("Helvetica" if style == "light" else "Helvetica-Bold", 9.5)
            c.drawString(LX+6, y, lab); c.drawRightString(X1-6, y, fmt2(val)); c.setFillColorRGB(0, 0, 0); y -= 18
            continue
        fillc = {"light": LIGHT, "red": RED, "black": (0, 0, 0)}[style]
        c.setFillColorRGB(*fillc); c.rect(LX, y-5, X1-LX, 16, fill=1, stroke=0)
        white = style != "light"; c.setFillColorRGB(*((1, 1, 1) if white else (0, 0, 0)))
        c.setFont("Helvetica-Bold" if white else "Helvetica", 9.5); c.drawString(LX+6, y, lab); c.drawRightString(X1-6, y, fmt2(val))
        c.setFillColorRGB(0, 0, 0); y -= 18
    if kind == "facture" and V:
        y -= 6
        c.setFillColorRGB(*RED); c.setFont("Helvetica-Bold", 7); c.drawString(LX+2, y, "Versements déjà effectués"); c.setFillColorRGB(0, 0, 0); y -= 9
        cols = [LX+2, LX+62, LX+132, LX+172]
        c.setStrokeColorRGB(*SILV); c.setLineWidth(0.4); c.line(LX, y+7, X1, y+7)
        for xx, h in zip(cols, ("Règlement", "Montant", "Type", "Num")):
            c.setFont("Helvetica-Bold", 6.5); c.drawString(xx, y, h)
        c.line(LX, y-3, X1, y-3); y -= 11
        for v in V[:5]:
            c.setFont("Helvetica", 6.8)
            c.drawString(cols[0], y, date_num(v["date"])); c.drawString(cols[1], y, fmt2(v["montant"]))
            c.drawString(cols[2], y, v["type"]); c.drawString(cols[3], y, v["num"]); y -= 9
        c.line(LX, y+6, X1, y+6); c.setStrokeColorRGB(0, 0, 0)
    cachet_img(c, P, X1-150, 52, 140, 56)
    pied_charte(c, P)

def dessiner_bon_reception_charte(c, P, D, L):
    infos = [("N° :", D["num_bl"] or D["num"]), ("Date :", date_abr(D["date"]))]
    if D["code"]: infos.append(("Code client :", D["code"]))
    if D["ref"]: infos.append(("Réf. :", D["ref"]))
    entete_charte(c, P, "Bon de réception", infos)
    boites_client_vehicule(c, D, H-148, 66, "ADRESSE DE LIVRAISON")
    y = H - 228
    lst = [t for t in ((f"Incoterm : {D['incoterm']}" if D["incoterm"] else ""), (f"Lieu de livraison : {D['lieu']}" if D["lieu"] else ""),
                       (f"Numéro bon de commande : {D['bc']}" if D["bc"] else "")) if t]
    if lst:
        hh = 8 + 11*len(lst)
        if ECO: c.setStrokeColorRGB(*SILV); c.setLineWidth(0.6); c.rect(X0, y-hh, X1-X0, hh); c.setStrokeColorRGB(0, 0, 0)
        else: c.setFillColorRGB(*LIGHT); c.rect(X0, y-hh, X1-X0, hh, fill=1, stroke=0); c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 8.5); yy = y - 13
        for t in lst: c.drawString(X0+8, yy, t); yy -= 11
        y -= hh + 8
    top = y - 4; HDR, RH, bottom = 20, 15, 150
    nmax = int((top - HDR - bottom) / RH)
    if len(L) > nmax: raise ValueError(f"Trop de lignes ({len(L)}) pour le bon de réception {D['num']} (maximum {nmax})")
    E = [X0, 300, 430, 495, X1]
    cadre_tableau(c, E, top, bottom, HDR, RH, len(L))
    entete_tableau(c, E, top, HDR, ["Désignation", "Commentaires", "Qté exp.", "Reste"])
    for i, l in enumerate(L):
        yb = top - HDR - i*RH - 11
        c.setFont("Helvetica", fit_font(c, l["des"], "Helvetica", 9, E[1]-E[0]-12)); c.drawString(E[0]+6, yb, l["des"])
        if l["comm"]:
            c.setFont("Helvetica", fit_font(c, l["comm"], "Helvetica", 8.5, E[2]-E[1]-8)); c.drawString(E[1]+4, yb, l["comm"])
        c.setFont("Helvetica", 9)
        if l["qte"]: c.drawRightString(E[3]-8, yb, str(l["qte"]))
    nom = txt(P.get("nom"))
    for x, w, titre, st in ((X0, 240, f"Pour {nom}", True), (330, X1-330, "Bon pour accord du client", False)):
        if ECO: c.setStrokeColorRGB(*SILV); c.setLineWidth(0.6); c.rect(x, 58, w, 80); c.setStrokeColorRGB(0, 0, 0)
        else: c.setFillColorRGB(*LIGHT); c.rect(x, 58, w, 80, fill=1, stroke=0)
        c.setFillColorRGB(*RED); c.rect(x, 136.7, w, 1.3, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8); c.drawString(x+8, 124, titre); c.setFillColorRGB(0, 0, 0)
        if st: cachet_img(c, P, x+10, 62, w-20, 56)
    pied_charte(c, P)

def rendre(cv, kind, P, D, L, V):
    global ECO
    ECO = theme_eco(P)
    if theme_charte(P):
        if kind == "br": dessiner_bon_reception_charte(cv, P, D, L)
        else: dessiner_facture_charte(cv, P, D, L, V, kind)
    elif kind == "br": dessiner_bon_reception(cv, P, D, L)
    else: dessiner_facture(cv, P, D, L, V, kind)

def totaux(P, D, L, avec_marge):
    ht = tva = 0.0
    for l in L:
        q = l["qte"] or 1
        pu = arrondi(l["prix"] * (1 + D["marge_eff"]), P["arrondi"]) if avec_marge else l["prix"]
        ht += q * pu; tva += q * pu * (P["tva"] if l["tva"] is None else l["tva"])
    tva = round(tva)
    return ht, tva, ht + tva

def ecrire_recap(sortie, lignes_recap):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook(); ws = wb.active; ws.title = "Recapitulatif"
    heads = ["N° document", "Client", "Marge %", "Total HT réel", "Total TTC réel (sans marge)",
             "Total HT pro forma", "Total TTC pro forma", "Marge gagnée HT (FCFA)", "Marge gagnée TTC (FCFA)"]
    ws.append(heads)
    for c in ws[1]:
        c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="D9D9D9")
        c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 44
    for r in lignes_recap: ws.append(r)
    for row in ws.iter_rows(min_row=2):
        row[2].number_format = "0.0%"
        for c in row[3:]: c.number_format = "#,##0"
    for col, w in zip("ABCDEFGHI", (14, 34, 10, 16, 20, 16, 18, 18, 18)): ws.column_dimensions[col].width = w
    wb.save(os.path.join(sortie, "Recapitulatif_marges.xlsx"))

def nom_sur(s):
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in s)

def traiter(chemin):
    nom_f = os.path.splitext(os.path.basename(chemin))[0]
    P, docs, lignes, versements, alertes = lire_fichier(chemin)
    for a_ in alertes: print(f"   ATTENTION  {a_}")
    sortie = os.path.join(DOSSIER_SORTIE, nom_sur(nom_f)); os.makedirs(sortie, exist_ok=True)
    ok, erreurs, recap = 0, [], []
    for D in docs:
        try:
            L = lignes.get(D["num"], [])
            if not L: raise ValueError("aucune ligne trouvée dans l'onglet Lignes")
            V = versements.get(D["num"], [])
            marge = marge_pct(D["marge"], P["marge_def"])
            if marge < 0: raise ValueError("la marge ne peut pas être négative")
            if marge > 0.30: print(f"   ATTENTION  {D['num']} : marge de {marge*100:g}% (vérifiez la saisie)")
            D["marge_eff"] = marge
            id_ = nom_sur(D["num"])
            genres = [("proforma", f"ProForma_{id_}.pdf"), ("br", f"BonReception_{id_}.pdf")]
            if D["acquittee"].upper() != "NON": genres.append(("facture", f"Facture_{id_}.pdf"))
            lot = canvas.Canvas(os.path.join(sortie, f"{id_}_Dossier_complet.pdf"), pagesize=A4)
            for kind, fichier in genres:
                for cv, fin in ((canvas.Canvas(os.path.join(sortie, fichier), pagesize=A4), True), (lot, False)):
                    rendre(cv, kind, P, D, L, V); cv.showPage()
                    if fin: cv.save()
            lot.save(); ok += 1
            hr, _, tr = totaux(P, D, L, False); hp, _, tp = totaux(P, D, L, True)
            recap.append([D["num"], D["client"], D["marge_eff"], hr, tr, hp, tp, hp - hr, tp - tr])
            print(f"   OK  {D['num']}  ({D['client']})")
        except PermissionError:
            erreurs.append((D["num"], "fichier PDF déjà ouvert : fermez-le puis relancez"))
        except Exception as e:
            erreurs.append((D["num"], str(e)))
    for num_, msg in erreurs: print(f"   ERREUR  {num_} : {msg}")
    if recap:
        try: ecrire_recap(sortie, recap)
        except PermissionError: print("   (Recapitulatif_marges.xlsx déjà ouvert : fermez-le puis relancez)")
    return ok, erreurs, sortie

def main():
    os.makedirs(DOSSIER_DEMANDES, exist_ok=True); os.makedirs(DOSSIER_SORTIE, exist_ok=True)
    fichiers = [f for f in sorted(glob.glob(os.path.join(DOSSIER_DEMANDES, "*.xlsx")))
                if not os.path.basename(f).startswith("~$")]
    if not fichiers:
        print("Aucun fichier Excel trouvé dans le dossier « demandes »."); return 1
    total, nerr = 0, 0
    for f in fichiers:
        print(f"\nFichier : {os.path.basename(f)}")
        try:
            ok, err, out = traiter(f); total += ok; nerr += len(err)
        except Exception as e:
            nerr += 1; print(f"   ERREUR fichier : {e}")
    print(f"\nTerminé : {total} dossier(s) créé(s), {nerr} erreur(s). PDF dans : {DOSSIER_SORTIE}")
    return 0

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    code = 1
    try:
        code = main()
    except Exception:
        import traceback; traceback.print_exc()
    if EXE:
        try: os.startfile(DOSSIER_SORTIE)
        except Exception: pass
        input("\nAppuyez sur Entrée pour fermer cette fenêtre...")
    sys.exit(code)
