# Outil actuel (Excel + Python) : référence pour le moteur PDF

Ces deux programmes produisent déjà les PDF validés par le client (pro forma, bon de réception, facture, facture acquittée). **Le site doit donner les mêmes résultats.** À lire pour reprendre la mise en page et les règles.

- `generer_factures_seye_motor.py` : version la plus complète (thèmes classique, eco, charte ; conditions et mode de règlement par défaut ; kilométrage).
- `generer_factures_gie.py` : version GIE SEYE & FRERES (thème classique, kilométrage).

Points à connaître (reportlab, A4) :
- `lire_fichier` lit l'Excel ; `totaux`, `marge_pct`, `qte_tolerante`, `prix_tolerant` portent les règles de calcul ; `rendre(cv, kind, P, D, L, V)` dessine `proforma`, `br` (bon de réception) ou `facture`.
- Limites : 23 lignes (facture, pro forma), 22 (bon de réception).
- Les modèles de référence du client (Mecatrozone) ne sont pas dans le dépôt ; les règles métier sont résumées dans `SKILL.md`.

Ces fichiers ne sont pas du code du site : ne pas les modifier, ne les consulter que pour porter la logique.
