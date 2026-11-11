# PRD : SeyeGarage

## Problème
Les garages et artisans du Sénégal font leurs devis, bons de réception et factures à la main ou sur Word/Excel : erreurs de calcul, documents peu soignés, historique éparpillé. Deux entreprises du cercle familial (GIE SEYE & FRERES, Seye Motor, à Rufisque) utilisent déjà un outil Excel + Python qui fonctionne ; il faut le transformer en service accessible à d'autres.

## Vision
Un site simple, utilisable depuis un téléphone, où un artisan crée un dossier (pro forma → bon de réception → facture), télécharge des PDF propres à son nom, et exporte tout son historique en Excel.

## Utilisateurs
- **Gérant de garage** (cible principale) : peu à l'aise avec l'informatique, travaille surtout sur téléphone, connexion internet variable.
- **Autres métiers** (menuiserie, etc.) : mêmes documents, quelques champs différents.
- **Comptable ou employé** (plus tard) : accès à une entreprise sans la gérer.

## Version 1 : périmètre
1. Connexion par **email, sans mot de passe** (code ou lien).
2. Un compte → **plusieurs entreprises**, chacune avec ses paramètres (nom, adresse, tél, email, NINEA, RCCM, compte et banque, logo, thème de PDF).
3. **Clients** : fiche réutilisable.
4. **Dossiers** : numéro, date, client, véhicule (marque, type, immatriculation, **kilométrage**), lignes (désignation, quantité facultative, prix), marge facultative, acomptes (versements), conditions et mode de règlement.
5. **PDF** : pro forma, bon de réception (sans prix), facture ; « Facture acquittée » quand le reste à payer est nul ; dossier complet en un seul PDF.
6. **Export Excel** de l'historique (clients, dossiers, lignes, versements) pour sauvegarde.
7. **Essai gratuit de 14 jours** à la création d'une entreprise.

## Hors périmètre V1
Paiement en ligne (V2), autres métiers et modèles PDF libres (V3), statistiques, application mobile native, comptabilité, stock.

## Version 2 : abonnement
- Tarif de départ : **10 000 F par mois**, ou **annuel** avec réduction (à fixer, ex. 100 000 F).
- Paiement via **PayDunya**. Pas de prélèvement automatique (mobile money) : l'abonnement a une **date de fin**, avec rappels par email ou WhatsApp quelques jours avant.
- Abonnement **par entreprise** : un compte avec deux entreprises paie deux abonnements.
- À l'expiration : lecture seule + export Excel.

## Version 3
Types d'activité (garage, menuiserie, autre) qui activent ou masquent des champs, modèles PDF supplémentaires, statistiques (chiffre d'affaires, marges), accès employé.

## Critères de réussite
- Un gérant crée une facture complète depuis son téléphone en moins de 5 minutes, sans aide.
- Les PDF sont identiques à ceux de l'outil actuel (références : modèles Mecatrozone).
- Aucune donnée visible entre entreprises différentes (vérifié par tests).
- 3 garages test utilisent la V1 pendant un mois avant d'ouvrir le paiement.

## Risques
- Réseau mobile instable → pages légères, enregistrement fiable, mode brouillon plus tard.
- Hébergement Hostinger : support Node.js à vérifier ; repli sur Vercel.
- Paiements : dépendance à PayDunya (frais, disponibilité) ; garder les paiements journalisés pour rapprochement manuel.
- Protection des données : mentions légales, conditions d'utilisation et politique de confidentialité avant l'ouverture au public.
