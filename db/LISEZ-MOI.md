# Base de données

PostgreSQL sur Neon, projet `seyegarage`. Les fichiers s'appliquent dans l'ordre, avec le rôle propriétaire, et ne se modifient plus une fois appliqués : toute évolution passe par un nouveau fichier `00N_nom.sql`. La table `migrations` dit ce qui est en place.

| Fichier | Contenu |
|---|---|
| `001_schema.sql` | Tables, règles RLS, essai de 14 jours, activation d'abonnement |
| `002_durcissement.sql` | Rôles `app` et `service`, `utilisateurs`, quantités décimales, corbeille et journal, numérotation, `tarifs`, `rappels` |

## Les trois rôles
| Rôle | Qui s'en sert | Ce qu'il peut faire |
|---|---|---|
| propriétaire (`neondb_owner`) | Migrations et tests seulement | Tout, y compris contourner la RLS. **Jamais dans l'application.** |
| `app` | Le site (`DATABASE_URL`) | Lire et écrire les données de l'utilisateur connecté, dans les limites de la RLS. Ne peut ni effacer un dossier pour de bon, ni toucher aux abonnements, aux tarifs ou au journal. |
| `service` | Confirmation PayDunya et rappels (`DATABASE_URL_SERVICE`) | Appeler `activer_abonnement`, noter les rappels envoyés. Aucun accès aux clients ni aux dossiers. |

`app` et `service` sont créés **sans mot de passe** : ils ne peuvent pas se connecter tant qu'on ne leur en a pas donné un. À faire une fois, dans l'éditeur SQL de Neon, avec un mot de passe long tiré au hasard, qui ne va ensuite que dans les variables secrètes de l'hébergeur :

```sql
alter role app password '…';
alter role service password '…';
```

Ne pas créer ces rôles depuis la console Neon : un rôle créé là reçoit le droit de contourner la RLS.

## Ce que l'application doit faire
- Ouvrir une transaction par requête et y exécuter `select set_config('app.user_id', '<uuid>', true)`.
- Après vérification du code de connexion : `select utilisateur_par_email('<email>')` donne l'identifiant du compte (créé s'il n'existe pas).
- Dossier créé sans `numero` : la base attribue `AAAA-NNN` (2026-001). Un numéro saisi est gardé tel quel.
- Supprimer un dossier = `update dossiers set supprime_le = now()`. Le rétablir = remettre `supprime_le` à `null`. Les listes filtrent sur `supprime_le is null`.
- Lire le prix d'un abonnement avec `tarif_en_vigueur('mensuel')`, jamais en dur dans le code.
- Limiter la saisie des quantités à deux décimales : la base arrondit le reste sans prévenir (1,005 devient 1,01).
- `dossier_totaux` donne les totaux **avant marge**. Le reste à payer et le titre « Facture acquittée » d'un dossier avec marge se calculent côté serveur à partir du total avec marge (tâche 6), pas avec cette vue.

## Limites connues, à traiter plus tard
- **Paiement et rappels (V2, migration suivante)** : aujourd'hui ni `app` ni `service` ne peuvent créer une ligne dans `paiements`, et `service` ne lit pas les abonnements qui arrivent à échéance. Il faudra une fonction `creer_paiement(entreprise, plan)` ouverte à `app` (montant pris dans `tarifs`) et une lecture des échéances pour `service`. Ne jamais contourner ce manque avec le rôle propriétaire.
- **Compteur de numéros** : un numéro saisi par erreur (`2026-5000`) fait repartir la suite de 5001 jusqu'à la fin de l'année. Le remettre en ordre demande pour l'instant le rôle propriétaire (table `compteurs_dossiers`).
- **Journal** : il couvre clients, dossiers, lignes et versements, pas les paramètres de l'entreprise (compte bancaire, NINEA).
- **Essai gratuit** : chaque nouvelle entreprise reçoit 14 jours, sans limite par compte (décision en attente, voir `PILOTE.md`).
- **Suppression d'un compte** : impossible tant que le compte a créé une entreprise.

## Tests
```bash
psql "$URL_PROPRIETAIRE" -v ON_ERROR_STOP=1 -f db/tests/002_isolation.sql
```
80 cas joués sous les rôles `app` et `service` (cloisonnement, lecture seule après expiration, numérotation, corbeille, journal, paiement confirmé une seule fois). Les tests n'écrivent rien de durable : tout est annulé à la fin.
