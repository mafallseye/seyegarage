# DOSSIER AGENTS : comment faire travailler Maguette, Safia et Karim

Trois agents IA, trois rôles. Leurs consignes détaillées sont dans `.claude/agents/` (`maguette.md`, `safia.md`, `karim.md`). Ce dossier dit **qui fait quoi, dans quel ordre, et quand c'est terminé**.

## Documents que tous lisent d'abord
`CLAUDE.md` (règles) · `reference/outil-actuel/` (le programme Python existant, référence du moteur PDF) · `PRD.md` (le produit) · `SPEC.md` (la technique) · `SKILL.md` (règles métier) · `DESIGN.md` (le design) · `REVUE.md` (la relecture) · `PILOTE.md` (l'avancement).

## Accès nécessaires
| Ressource | Pour qui | État |
|---|---|---|
| Dépôt GitHub `mafallseye/seyegarage` (privé) | Les trois | Créé |
| Base Neon `seyegarage` (Frankfurt) | Maguette, Karim (lecture) | Créée, schéma 001 appliqué |
| Installation de paquets (npm) dans l'environnement | Maguette | **À autoriser** (réglage du compte Claude) |
| Compte marchand PayDunya, clés de test | Maguette (V2) | En cours d'ouverture ; clés dans les paramètres secrets de l'hébergeur, jamais dans le dépôt |
| Service d'envoi d'emails | Maguette | À choisir (Resend ou Neon Auth) |
| Hébergement | Maguette | À trancher : Hostinger Cloud (Node.js ?) ou Vercel |

## Règles de collaboration
1. **Une tâche = une branche = une pull request.** Jamais de commit direct sur `main`.
2. **Karim relit avant toute fusion.** Pas d'approbation, pas de fusion.
3. **Safia livre avant que Maguette construise un écran.** Sans maquette, Maguette construit la logique (données, API, calculs) et laisse l'écran minimal.
4. Chaque agent met à jour `PILOTE.md` (état et journal) en fin de tâche.
5. Toute décision de produit (prix, règles métier, palette) revient à l'utilisateur ; l'agent pose la question au lieu de décider.
6. **Jamais de secret** dans le dépôt, les messages ou les journaux.

## Backlog dans l'ordre
| # | Tâche | Responsable | Dépend de | Terminé quand |
|---|---|---|---|---|
| 1 | Traiter les 8 remarques de `REVUE.md` : rôle `app` sans contournement de la RLS, table `utilisateurs`, quantités décimales, suppression douce, numérotation automatique, tarifs, rappels (migration `db/002`) | Maguette, relu par Karim | | Migration appliquée sur Neon, test d'isolation passé avec le rôle `app` |
| 2 | Planche de style + jetons (`design/tokens.json`, `tokens.css`) | Safia | | Palette de `DESIGN.md` appliquée, contrastes vérifiés, relu par Karim |
| 3 | Maquettes mobile : accueil, connexion, tableau de bord, fiche dossier | Safia | 2 | Écrans 1 à 4 avec états vide, erreur, chargement |
| 4 | Squelette Next.js, connexion par email (code à 6 chiffres), sessions | Maguette | 1 | On se connecte et on se déconnecte ; limite de tentatives testée |
| 5 | Création et paramètres d'entreprise, multi-entreprises par compte, essai de 14 jours | Maguette | 4, 3 | Un compte crée 2 entreprises, chacune avec son essai |
| 6 | Clients et dossiers : lignes, marge, versements, totaux | Maguette | 5 | Tests de calcul de `SKILL.md` tous verts |
| 7 | Moteur PDF : pro forma, bon de réception, facture et acquittée, dossier complet, 3 thèmes, kilométrage | Maguette | 6 | PDF comparés aux modèles de référence ; 23 et 22 lignes testés |
| 8 | Export Excel de l'historique | Maguette | 6 | Fichier ouvert et vérifié (colonnes, totaux) |
| 9 | Maquettes : liste, clients, paramètres, abonnement ; version desktop ; mode sombre ; logo | Safia | 3 | Livrables de `DESIGN.md` complets |
| 10 | Intégration du design Terre & Soleil dans l'application | Maguette | 9 | Relu par Safia et Karim ; sur petit téléphone |
| 11 | Mentions légales, conditions d'utilisation, politique de confidentialité | Karim propose, utilisateur valide | | Textes validés |
| 12 | Déploiement (Hostinger ou Vercel) sur seyegarage.com, variables secrètes | Maguette | 10 | Site en ligne, essai complet fait par l'utilisateur |
| 13 | **V2** : PayDunya (création, IPN, vérification serveur, activation idempotente), expiration en lecture seule, rappels | Maguette | 12 | Paiement test complet ; double confirmation = un seul abonnement |
| 14 | Test avec 3 garages pendant un mois | Utilisateur | 12 | Retours notés dans `PILOTE.md` |

## Définition de « terminé » pour tout le monde
- Fonctionne sur petit téléphone et réseau lent.
- Tests écrits et verts (calculs, isolation).
- Messages d'erreur en français, sans jargon.
- Relu et approuvé par Karim.
- `PILOTE.md` mis à jour.

## Messages prêts à copier pour lancer chaque agent

**Maguette**
> Tu es Maguette (voir `.claude/agents/maguette.md`). Lis `CLAUDE.md`, `SPEC.md`, `SKILL.md` et `DOSSIER_AGENTS.md`. Commence par la tâche 1 du backlog sur une branche `feat/migration-002`, puis ouvre une pull request pour Karim. Pose-moi une question si une règle métier n'est pas claire.

**Safia**
> Tu es Safia (voir `.claude/agents/safia.md`). Lis `DESIGN.md` et `PRD.md`. Commence par la tâche 2 (planche de style et jetons) puis la tâche 3 (maquettes mobiles). Livre dans `design/` sur une branche `design/planche-de-style` et ouvre une pull request pour Karim.

**Karim**
> Tu es Karim (voir `.claude/agents/karim.md`). Lis `REVUE.md`. Relis la pull request indiquée avec la grille, lance les tests, et rends un avis avec des propositions concrètes.

## Si un seul agent doit tout faire
Possible : Claude peut enchaîner les rôles (Maguette, puis Safia, puis Karim) dans l'ordre du backlog. Les limites actuelles : sans installation de paquets autorisée, l'application ne peut pas être lancée ni testée dans cet environnement.
