# PILOTE : suivi du projet

Mis à jour à chaque étape. Équipe : Maguette (développement), Safia (design), Karim (relecture).

## Où on en est
| Brique | État |
|---|---|
| Outil actuel Excel + Python (GIE SEYE & FRERES, Seye Motor) | En service chez le client |
| Dépôt GitHub `mafallseye/seyegarage` (privé) | Créé |
| Base Neon `seyegarage` (Frankfurt, offre gratuite) | Créée, schéma 001 appliqué |
| Documents projet (CLAUDE, PRD, SPEC, SKILL, PILOTE) | Rédigés, à relire par Karim |
| Application Next.js | À construire |
| Maquettes (Safia) | À faire |
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

## Questions ouvertes
- Hostinger Cloud propose-t-il les applications Node.js ? (vérifier dans hPanel)
- Service d'envoi d'emails : Resend, ou Neon Auth ?
- Stockage des logos.
- Domaine seyegarage.com : que garde-t-on du site actuel ?
- Mentions légales, conditions d'utilisation, politique de confidentialité à rédiger.

## Prochaines étapes
1. Autoriser l'installation de paquets dans l'environnement de développement (npm).
2. Créer l'application Next.js, la connexion par email et la création d'entreprise.
3. Écrans paramètres, clients, dossiers.
4. PDF (reprise de la logique existante) et export Excel.
5. Tests d'isolation et de calcul (voir `SPEC.md`).
6. Essai avec le frère de l'utilisateur, puis 2 à 3 garages.
7. V2 : PayDunya, rappels, expiration.

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
