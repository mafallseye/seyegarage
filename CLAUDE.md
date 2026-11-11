# CLAUDE.md : consignes pour travailler sur SeyeGarage

Plateforme web de facturation par abonnement pour garages, menuiseries et autres métiers au Sénégal. Domaine : seyegarage.com.
Lire d'abord : `PRD.md` (quoi et pourquoi), `SPEC.md` (comment), `PILOTE.md` (où on en est), `SKILL.md` (règles métier des documents).

## Équipe
- Développement : Maguette
- Design : Safia
- Relecture : Karim (toute modification passe par une branche et une pull request relue par lui)

## Langue
- Interface, messages d'erreur, documentation et commentaires : **français**.
- Montants en **F CFA**, sans décimales à l'affichage, séparateur de milliers = espace (`1 250 000`).
- Dates au format `JJ/MM/AAAA`.

## Stack
- Next.js (App Router) + TypeScript, interface pensée d'abord pour le **téléphone**.
- Base : **PostgreSQL sur Neon** (projet `seyegarage`, Frankfurt). Schéma dans `db/`.
- Paiement : **PayDunya** (Wave, Orange Money, carte).
- Déploiement : Hostinger Cloud si Node.js y est disponible, sinon Vercel avec le domaine chez Hostinger.

## Règles à ne jamais enfreindre
1. **Aucun secret dans le dépôt** (clés PayDunya, URL de connexion Neon, clés d'envoi d'emails). Ils vivent dans les variables d'environnement de l'hébergeur. Garder `.env.example` à jour sans valeurs.
2. **Cloisonnement par entreprise** : chaque requête fixe `app.user_id` dans sa transaction (`select set_config('app.user_id', $1, true)`), et la base applique les règles RLS. L'application se connecte avec un rôle **sans** droit de contourner la RLS.
3. **Abonnement expiré = lecture seule**, jamais de blocage des données : l'export Excel reste possible.
4. **Un paiement ne s'active que par confirmation serveur** auprès de PayDunya (jamais sur la foi du navigateur). Activation idempotente via `activer_abonnement(token)`.
5. **Les calculs d'argent se font côté serveur**, en entiers ou `numeric`, jamais en flottants JavaScript pour les totaux stockés.
6. Ne pas modifier un fichier de `db/` déjà appliqué : ajouter une nouvelle migration `db/00N_nom.sql`.

## Commandes (à compléter quand l'application existe)
- `npm run dev`, `npm run build`, `npm run lint`, `npm test`
- Migrations : appliquer les fichiers de `db/` dans l'ordre sur la branche Neon voulue.

## Conventions
- Branches : `feat/…`, `fix/…`. Commits courts en français à l'impératif.
- Tester les règles métier (marges, totaux, acquittée, limites de lignes) avec des tests automatiques avant de les brancher à l'interface.
