# PILOTE : suivi du projet

Mis à jour à chaque étape. Documents liés : `DESIGN.md` (design), `REVUE.md` (relecture). Équipe : trois agents IA, Maguette (développement), Safia (design), Karim (relecture). Organisation et backlog dans `DOSSIER_AGENTS.md`.

## Où on en est
| Brique | État |
|---|---|
| Outil actuel Excel + Python (GIE SEYE & FRERES, Seye Motor) | En service chez le client |
| Dépôt GitHub `mafallseye/seyegarage` (privé) | Créé |
| Base Neon `seyegarage` (Frankfurt, offre gratuite) | Schémas 001 et 002 appliqués ; 83 tests passés sous les rôles `app` et `service` (`db/tests/002_isolation.sql`) |
| Rôles `app` et `service` | Créés sans mot de passe : **à fixer par l'utilisateur** avant la tâche 4 (voir `db/LISEZ-MOI.md`) |
| Documents projet (CLAUDE, PRD, SPEC, SKILL, PILOTE) | Rédigés, à relire par Karim |
| Application Next.js | À construire |
| Design « Terre & Soleil » (Safia) | Brief rédigé (`DESIGN.md`), maquettes à faire |
| Dossier des agents (`DOSSIER_AGENTS.md`, `.claude/agents/`) | Rédigé : consignes, backlog de 14 tâches, messages de lancement |
| Relecture (Karim) | Les 8 remarques de la première relecture sont traitées (migration 002, relue deux fois) |
| Connexion par email | À construire, service d'envoi à choisir |
| PDF et export Excel | À construire |
| PayDunya | Compte marchand en cours d'ouverture, intégration en V2 |
| Hébergement | À trancher : Hostinger Cloud (Node.js ?) ou Vercel |

## Décisions prises
- Base PostgreSQL sur **Neon** (pas Supabase, pas MongoDB, pas MySQL).
- Frontend **Next.js**, mobile d'abord.
- Paiement **PayDunya**, abonnement par entreprise, tarif : 10 000 F par mois ou 100 000 F par an.
- Connexion par email sans mot de passe.
- Essai gratuit de 14 jours (confirmé) ; abonnement expiré = lecture seule + export Excel.
- Thème PDF par défaut : classique.
- Design du site : **Terre & Soleil** (terracotta, soleil, sable, brun café), préparé par Safia.
- Karim relit tout et propose de meilleures versions (`REVUE.md`).

## Questions ouvertes
- Hostinger Cloud propose-t-il les applications Node.js ? (vérifier dans hPanel)
- Service d'envoi d'emails : Resend, ou Neon Auth ?
- Stockage des logos.
- Domaine seyegarage.com : que garde-t-on du site actuel ?
- Mentions légales, conditions d'utilisation, politique de confidentialité à rédiger.
- **Essai gratuit : un seul par compte, ou un par entreprise ?** Aujourd'hui chaque nouvelle entreprise reçoit 14 jours : un compte peut recréer son garage toutes les deux semaines et ne jamais payer. À trancher par l'utilisateur avant l'ouverture aux garages test.
- Numéro automatique des dossiers : la forme `2026-001` convient-elle ? (utilisateur)
- Le numéro d'un dossier mis à la corbeille redevient disponible : d'accord ? (utilisateur)
- Total d'une ligne à quantité décimale arrondi au franc (1,5 × 333 = 500 F) : d'accord ? (utilisateur)

## Prochaines étapes
1. Donner un mot de passe aux rôles `app` et `service` dans l'éditeur SQL de Neon (utilisateur).
2. Safia livre la planche de style et les maquettes mobiles.
3. Autoriser l'installation de paquets dans l'environnement de développement (npm).
4. Créer l'application Next.js, la connexion par email et la création d'entreprise.
5. Écrans paramètres, clients, dossiers.
6. PDF (reprise de la logique existante) et export Excel.
7. Tests d'isolation et de calcul (voir `SPEC.md`).
8. Essai avec le frère de l'utilisateur, puis 2 à 3 garages.
9. V2 : PayDunya, rappels, expiration.

## Jalons
| Jalon | Contenu | Date cible |
|---|---|---|
| J1 | Connexion + entreprises + dossiers | à fixer |
| J2 | PDF + Excel | à fixer |
| J3 | Essai avec garages test | à fixer |
| J4 | Paiement PayDunya | à fixer |
| J5 | Mise en ligne sur seyegarage.com | à fixer |

## Journal
- 2026-11-11 : choix de la stack, création du dépôt et de la base Neon, schéma appliqué et testé (isolation entre entreprises, lecture seule après expiration, activation d'abonnement idempotente).
- 2026-11-16 : tâche 1 (Maguette, relue deux fois par Karim). Migration `002_durcissement` appliquée sur Neon : rôles `app` et `service` sans contournement de la RLS, table `utilisateurs`, quantités décimales, corbeille et journal, numérotation automatique, `tarifs`, `rappels`, droits de modification par colonne. 83 tests passés sur Neon sous les rôles `app` et `service`. La première relecture avait trouvé un défaut bloquant (numérotation bloquée au 1000ᵉ dossier), corrigé avant application. Une branche Neon `test-migration-002`, créée pour un essai et non utilisée, peut être supprimée.
