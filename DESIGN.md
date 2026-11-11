# DESIGN : brief pour Safia

Direction : **Terre & Soleil**. Un site chaleureux, sophistiqué, qui inspire confiance à un gérant de garage comme à un menuisier, et qui reste lisible sur un téléphone d'entrée de gamme, en plein soleil.

## Ce qu'on veut ressentir
Solide comme un atelier bien tenu, chaud comme la terre de Rufisque, net comme une facture bien faite. Pas de jargon, pas de décor inutile : de la matière (grain, ombres douces), de l'espace, une couleur forte à la fois.

## Palette (jetons à reprendre tels quels, contrastes vérifiés)
| Rôle | Nom | Couleur | Usage |
|---|---|---|---|
| Texte principal | Brun café | `#3B2418` | Titres, texte, icônes |
| Texte secondaire | Terre séchée | `#7A5C48` | Légendes, aides, champs désactivés |
| Primaire | Terracotta | `#A63F22` | Boutons principaux, liens, état actif |
| Accent | Soleil | `#F2A93B` | Mise en avant, badges, soulignements, graphiques ; **texte brun dessus, jamais blanc** |
| Fond | Sable | `#FBF4E8` | Fond des pages |
| Surface | Blanc chaud | `#FFFFFF` | Cartes, formulaires |
| Surface soutenue | Sable foncé | `#F6E3C5` | Bandeaux, lignes de tableau alternées |
| Bordure | Argile claire | `#E8D9C0` | Séparateurs, contours de champs |
| Succès | Baobab | `#4F7B4A` | Facture acquittée, paiement reçu |
| Erreur | Brique | `#B3261E` | Erreurs, suppressions |

Contrastes mesurés (WCAG, minimum visé 4,5 pour le texte) : brun sur sable 13,2 ; brun sur blanc 14,5 ; blanc sur terracotta 6,3 ; brun sur soleil 7,2 ; terre séchée sur sable 5,6 ; blanc sur baobab 4,9 ; blanc sur brique 6,5.

Règle d'or : **une seule couleur forte par écran** (terracotta pour l'action, soleil pour l'attention), le reste en sable, brun et blanc. Le soleil ne sert pas pour du texte long.

## Typographie
- Titres : une serif chaleureuse et affirmée (propositions : Fraunces, Playfair Display).
- Texte et chiffres : une sans-serif très lisible (propositions : Inter, DM Sans), **chiffres tabulaires** pour tous les montants.
- Tailles : texte courant 16 px minimum sur mobile ; zones tactiles 44 px minimum.

## Formes et ambiance
- Coins arrondis modérés (12 px cartes, 10 px champs), ombres douces teintées de brun, jamais de noir pur.
- Motif discret inspiré du textile ou de la terre (bogolan, wax) en filigrane ou en bandeau, très léger, jamais derrière du texte.
- Icônes à trait épais et arrondi ; illustration sobre d'atelier (clé, rabot, engrenage) plutôt que photos génériques.
- Mode sombre : fond brun très foncé `#1E120B`, texte sable, mêmes accents (à valider avec Safia).

## Écrans à dessiner (ordre de priorité, mobile d'abord)
1. **Accueil public** (seyegarage.com) : promesse en une phrase, aperçu d'une facture, tarifs (10 000 F par mois, 100 000 F par an, 14 jours d'essai gratuit), bouton « Essayer gratuitement ».
2. **Connexion** : email, puis code à 6 chiffres.
3. **Tableau de bord entreprise** : choix de l'entreprise, dossiers récents, état de l'abonnement et date de fin.
4. **Fiche dossier** : en-tête, véhicule et kilométrage, lignes, marge, versements, boutons PDF.
5. **Liste des dossiers** et **clients**.
6. **Paramètres de l'entreprise** : identité, logo, thème de PDF.
7. **Abonnement et paiement** (Wave, Orange Money, carte via PayDunya).
8. **États vides, erreurs, chargement, hors connexion.**

## Distinction importante
Le **site** adopte Terre & Soleil. Les **PDF** gardent leurs thèmes propres à chaque entreprise (classique marine et orange par défaut, eco, charte) : ne pas les confondre. Un thème PDF « Terre & Soleil » pourra être proposé plus tard.

## Livrables attendus de Safia
1. Planche de style : palette, typographie, boutons, champs, cartes, badges d'état.
2. Maquettes mobile des écrans 1 à 4, puis desktop.
3. Variante mode sombre de l'écran 3.
4. Logo SeyeGarage (déclinaisons claire et sombre, favicon).
5. Export des jetons (couleurs, rayons, ombres) pour que le développement les reprenne dans le code.

Karim relit les maquettes avec la grille de `REVUE.md` avant tout développement d'écran.
