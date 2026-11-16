# SPEC : spécification technique

## Architecture
- Application **Next.js** (pages serveur + routes API), TypeScript.
- **PostgreSQL (Neon)** : toutes les données. Fichiers (logos) dans un stockage objet à choisir en V1 (Neon storage ou équivalent).
- **PDF** générés côté serveur à partir des données (voir `SKILL.md`). Option de départ : reprendre la logique du programme Python existant comme petit service, ou la porter en JavaScript.
- **Excel** généré côté serveur (bibliothèque `exceljs`).
- **Emails** de connexion et de rappel via un service d'envoi (à choisir, ex. Resend).
- **PayDunya** : création de facture de paiement côté serveur, redirection du client, confirmation par rappel serveur (IPN) puis vérification auprès de l'API avant activation.

## Données
Schéma dans `db/` (`001_schema.sql` puis `002_durcissement.sql`, mode d'emploi dans `db/LISEZ-MOI.md`). Tables : `utilisateurs`, `entreprises`, `membres`, `abonnements`, `paiements`, `tarifs`, `rappels`, `clients`, `dossiers`, `lignes`, `versements`, `journal`, `compteurs_dossiers`, vue `dossier_totaux`.

Points clés :
- `dossiers (entreprise_id, numero)` est unique parmi les dossiers non supprimés. Numéro laissé vide : la base attribue `AAAA-NNN` par entreprise et par année ; un numéro saisi est gardé tel quel.
- Un dossier ne s'efface pas : `supprime_le` le met à la corbeille, d'où il peut être rétabli. Le `journal` garde l'état d'avant chaque modification ou suppression (clients, dossiers, lignes, versements).
- `lignes.qte` vide = main d'œuvre ou forfait (le total de la ligne vaut le prix unitaire). Quantités à deux décimales ; total de ligne arrondi au franc.
- Une ligne, un versement ou le client d'un dossier appartiennent forcément à la même entreprise que le dossier (clés étrangères composées).
- `tarifs` (plan, montant, depuis) porte le prix des abonnements ; `rappels` note chaque rappel d'expiration envoyé.
- `dossiers.marge_pct` vide = aucune marge.
- `utilisateurs` : un compte par email. `membres` relie un utilisateur à une entreprise (`proprietaire` ou `employe`).
- Un abonnement `essai` de 14 jours est créé par un déclencheur à la création d'une entreprise.

## Sécurité
- Connexion : code à usage unique envoyé par email, durée courte, limite de tentatives. Session par cookie `httpOnly`, `secure`, `sameSite=lax`.
- À chaque requête authentifiée, ouvrir une transaction et exécuter `select set_config('app.user_id', '<uuid>', true)`. Les règles RLS font le reste.
- L'application se connecte avec le rôle `app`, qui ne possède aucune table et n'a pas `BYPASSRLS`. Un second rôle, `service`, réservé au serveur (paiement, rappels), appelle `activer_abonnement` et n'a aucun accès aux données de travail. Le rôle propriétaire ne sert qu'aux migrations et aux tests.
- Webhook PayDunya : ne jamais se fier au contenu reçu ; relire l'état du paiement chez PayDunya avant d'activer.
- Limiter le débit (connexion, génération de PDF, export).
- Sauvegardes : points de restauration Neon + export Excel par l'utilisateur.

## Écrans V1
1. Connexion (email → code).
2. Choix ou création d'entreprise.
3. Paramètres de l'entreprise (identité, logo, thème, conditions par défaut, marge par défaut).
4. Liste des dossiers (recherche par numéro ou client, filtre par date).
5. Fiche dossier : en-tête, véhicule, lignes, marge, versements, boutons PDF (pro forma, bon de réception, facture, dossier complet).
6. Clients.
7. Export Excel.
8. Abonnement (état, date de fin ; paiement en V2).

## Routes API (indicatif)
- `POST /api/auth/demander-code`, `POST /api/auth/verifier-code`, `POST /api/auth/deconnexion`
- `GET/POST /api/entreprises`, `PATCH /api/entreprises/:id`
- `GET/POST /api/entreprises/:id/clients`
- `GET/POST /api/entreprises/:id/dossiers`, `GET/PATCH/DELETE /api/dossiers/:id`
- `GET /api/dossiers/:id/pdf?type=proforma|reception|facture|complet`
- `GET /api/entreprises/:id/export.xlsx`
- V2 : `POST /api/paiement/creer`, `POST /api/paiement/ipn`

## Performance et mobile
- Pages légères, formulaires utilisables au pouce, pas de dépendance lourde côté navigateur.
- PDF et Excel générés à la demande, jamais précalculés.

## Tests obligatoires avant mise en ligne
- Calculs : marges (5, 5 %, 0,05 → 5 % ; vide → aucune), totaux, reste à payer, « acquittée ».
- Limites : 23 lignes pour facture et pro forma, 22 pour le bon de réception (pagination ou refus clair), vérifiées pour chacun des trois thèmes (classique, eco, charte).
- Isolation : un utilisateur B ne lit ni n'écrit rien chez A ; écriture refusée si abonnement expiré, lecture permise. Tests joués sous le rôle `app` : `db/tests/002_isolation.sql`.
- Paiement : double confirmation du même paiement = un seul abonnement ; prolongation à partir de la fin en cours.
