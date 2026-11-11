# SPEC : spécification technique

## Architecture
- Application **Next.js** (pages serveur + routes API), TypeScript.
- **PostgreSQL (Neon)** : toutes les données. Fichiers (logos) dans un stockage objet à choisir en V1 (Neon storage ou équivalent).
- **PDF** générés côté serveur à partir des données (voir `SKILL.md`). Option de départ : reprendre la logique du programme Python existant comme petit service, ou la porter en JavaScript.
- **Excel** généré côté serveur (bibliothèque `exceljs`).
- **Emails** de connexion et de rappel via un service d'envoi (à choisir, ex. Resend).
- **PayDunya** : création de facture de paiement côté serveur, redirection du client, confirmation par rappel serveur (IPN) puis vérification auprès de l'API avant activation.

## Données
Schéma complet dans `db/001_schema.sql`. Tables : `entreprises`, `membres`, `abonnements`, `paiements`, `clients`, `dossiers`, `lignes`, `versements`, vue `dossier_totaux`.

Points clés :
- `dossiers (entreprise_id, numero)` est unique.
- `lignes.qte` vide = main d'œuvre ou forfait (le total de la ligne vaut le prix unitaire).
- `dossiers.marge_pct` vide = aucune marge.
- `membres` relie un utilisateur à une entreprise (`proprietaire` ou `employe`).
- Un abonnement `essai` de 14 jours est créé par un déclencheur à la création d'une entreprise.

## Sécurité
- Connexion : code à usage unique envoyé par email, durée courte, limite de tentatives. Session par cookie `httpOnly`, `secure`, `sameSite=lax`.
- À chaque requête authentifiée, ouvrir une transaction et exécuter `select set_config('app.user_id', '<uuid>', true)`. Les règles RLS font le reste.
- Le rôle de connexion de l'application ne doit ni être propriétaire des tables ni avoir `BYPASSRLS`. Un second rôle, réservé au serveur de paiement, appelle `activer_abonnement`.
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
- Limites : 23 lignes pour facture et pro forma, 22 pour le bon de réception (pagination ou refus clair).
- Isolation : un utilisateur B ne lit ni n'écrit rien chez A ; écriture refusée si abonnement expiré, lecture permise.
- Paiement : double confirmation du même paiement = un seul abonnement ; prolongation à partir de la fin en cours.
