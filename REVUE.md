# REVUE : grille de relecture (Karim)

Rôle de Karim : relire chaque modification et **proposer une meilleure version**, pas seulement signaler les erreurs. Chaque remarque contient : le problème, pourquoi il compte, et une proposition concrète.

## Comment relire
1. Lire `PRD.md` (le but), puis la modification.
2. Passer la grille ci-dessous. Cocher ou commenter.
3. Proposer l'alternative qu'il juge la plus simple et la plus sûre, avec ses raisons.
4. Valider ou demander des changements dans la pull request. Rien n'est fusionné sans son accord.

## Grille : code
- [ ] Les règles de `CLAUDE.md` sont respectées (secrets, cloisonnement, lecture seule, paiement confirmé par le serveur).
- [ ] Les calculs d'argent sont testés (marge vide / 5 / 5 % / 0,05, totaux, reste à payer, acquittée, lignes sans quantité).
- [ ] Aucune donnée d'une entreprise n'est lisible par une autre (test d'isolation).
- [ ] Les erreurs sont en français, claires, sans jargon technique.
- [ ] Les écrans fonctionnent sur petit téléphone et connexion lente.
- [ ] Pas de dépendance lourde ou inutile ajoutée.

## Grille : design (maquettes de Safia)
- [ ] Palette Terre & Soleil de `DESIGN.md` respectée, une seule couleur forte par écran.
- [ ] Contraste du texte d'au moins 4,5 ; zones tactiles de 44 px.
- [ ] Montants lisibles (chiffres tabulaires, séparateur d'espace, F CFA).
- [ ] Parcours « créer une facture » en moins de 5 minutes sans aide.
- [ ] États vides, erreurs et chargement prévus.

## Grille : documents (PRD, SPEC, SKILL, PILOTE)
- [ ] Rien n'est annoncé comme fait s'il ne l'est pas.
- [ ] Les décisions confirmées par l'utilisateur sont à jour (tarif, essai, stack).
- [ ] Les questions ouvertes sont listées avec une personne responsable.

## Première relecture : points relevés sur l'existant
Suite donnée le 16/11/2026 : points 1 à 7 traités par la migration `db/002_durcissement.sql` ; point 8 inscrit dans `SPEC.md` et à vérifier à la tâche 7 (moteur PDF).

| # | Point | Pourquoi | Proposition |
|---|---|---|---|
| 1 | La base est créée avec le rôle propriétaire de Neon, qui **contourne la RLS** | Le cloisonnement ne protégerait rien si l'application se connecte avec ce rôle | Créer un rôle `app` sans droit de contournement, donner les droits strictement nécessaires, et n'utiliser que lui dans l'application (migration `002`) |
| 2 | `user_id` des membres n'est pas relié à une table d'utilisateurs | On peut rattacher un identifiant qui n'existe pas | Ajouter une table `utilisateurs` (email unique) et la clé étrangère |
| 3 | Pas de journal des actions | Impossible de rétablir un document supprimé par erreur ou de comprendre un litige | Ajouter une suppression douce (`supprime_le`) sur les dossiers et un journal minimal |
| 4 | Numéros de dossier saisis à la main | Risque de doublons ou de trous dans la numérotation d'une facture | Proposer une numérotation automatique par entreprise et par année, modifiable |
| 5 | Quantités arrondies à l'entier | Un garagiste peut vendre 1,5 m ou 0,5 L | Passer `qte` en `numeric(10,2)` dès la migration `002`, avant que des données existent |
| 6 | Abonnements : plan annuel sans montant de référence en base | Le prix peut changer sans trace | Table `tarifs` (plan, montant, depuis), ou constantes versionnées dans le code |
| 7 | Aucun rappel d'expiration prévu côté données | Les rappels (email ou WhatsApp) ont besoin d'un suivi d'envoi | Table `rappels` (abonnement, canal, envoyé le) pour ne pas relancer deux fois |
| 8 | Modèle PDF unique « classique » dans les spécifications | Le thème est choisi par entreprise | Garder les trois thèmes en V1, tester le rendu sur 23 lignes pour chacun |
