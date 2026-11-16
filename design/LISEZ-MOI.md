# Design « Terre & Soleil » : livraisons de Safia

Brief : `DESIGN.md`. Tout est original ; noms et montants des exemples sont fictifs.

| Fichier | Rôle |
|---|---|
| `tokens.json` | **Source** des jetons : couleurs (clair et sombre), polices, tailles, espaces, rayons, ombres, et la liste des contrastes à tenir |
| `tokens.css` | Les mêmes jetons en variables CSS. Fabriqué par `jetons.mjs`, ne pas le modifier à la main |
| `jetons.mjs` | `node design/jetons.mjs` : refabrique `tokens.css` et vérifie chaque contraste (échoue si l'un est insuffisant) |
| `composants.css` | Boutons, champs, cartes, pastilles, messages, lignes de liste, motif, chargement, état vide |
| `planche-de-style.html` | La planche, avec bascule clair / sombre : s'ouvre directement dans un navigateur |

## Pour le développement (Maguette)
- Reprendre `tokens.css` et `composants.css` tels quels ; n'écrire aucune couleur en dur, toujours `var(--couleur-…)`.
- Le mode sombre suit le réglage du téléphone ; `data-theme="clair"` ou `"sombre"` sur `<html>` le force.
- Tout montant porte la classe `montant` (chiffres tabulaires, jamais coupé) : `1 250 000 F CFA`, toujours « F CFA » en entier.
- **Séparateur des milliers : l'espace insécable ordinaire (U+00A0)**, pas l'espace fine que produit `Intl.NumberFormat('fr-FR')` (U+202F) : avec elle les chiffres se collent et 1 250 000 se lit comme 12 500 000. En pratique : `new Intl.NumberFormat('fr-FR').format(n).replace(/\u202f/g, '\u00a0')`.
- Boutons et champs font 48 px de haut (`--hauteur-controle` ; minimum demandé : 44 px).
- **Un seul bouton plein par écran.** « Supprimer » est en contour (`bouton--danger`) ; le plein brique (`bouton--danger-plein`) ne sert qu'à confirmer la suppression, dans sa fenêtre.
- Un bouton en attente porte `aria-busy="true"` et `aria-disabled="true"`, et le code ignore un second appui : sur réseau lent, on tape deux fois.
- Un chargement montre toujours un texte (`role="status"`, « Chargement de vos dossiers… ») en plus des silhouettes.
- Liste de dossiers : chaque fragment du détail (numéro, date, plaque) dans son `<span>`, pour qu'une plaque ne soit jamais coupée en deux.
- Pastille : libellé court (une vingtaine de caractères) ; au-delà, utiliser un message.
- Champs à 16 px : en dessous, l'iPhone zoome à la saisie.
- Une erreur de champ se dit avec du texte sous le champ, pas seulement avec la couleur.

## Contrastes vérifiés
Les sept mesures de `DESIGN.md` sont confirmées par le calcul (13,2 ; 14,5 ; 6,3 ; 7,2 ; 5,6 ; 4,9 ; 6,5). `jetons.mjs` en vérifie 27 par mode, dont le texte secondaire sur sable foncé (4,8) et les liens sur sable (5,7).

## Choix de Safia
- **Polices** : Fraunces (titres, graisse 600) et Inter (texte et chiffres). En production, les héberger avec le site (deux ou trois fichiers `woff2`, sous-ensemble latin) plutôt que de les appeler chez Google : plus rapide sur réseau lent. Sans elles, la page reste lisible (Georgia et la police du téléphone).
- **Motif** : frise géométrique dessinée pour le projet (chevrons, points, traits), en bandeau de 14 px, jamais derrière du texte.
- **Baobab en texte** : sur sable il n'atteint que 4,5. Pour du texte vert ou rouge sur fond teinté, utiliser `succes-texte` et `erreur-texte`.

## À valider par l'utilisateur (la palette de `DESIGN.md` n'est pas modifiée)
Teintes **ajoutées**, dérivées de la palette, parce que le brief ne les prévoyait pas :

| Jeton | Couleur | Pourquoi |
|---|---|---|
| `bordure-champ` | `#9A7B60` | L'argile claire `#E8D9C0` ne fait que 1,4 de contraste sur blanc : le contour d'un champ serait invisible en plein soleil. Celle-ci fait 3,9. L'argile claire reste pour les séparateurs et les cartes. |
| `primaire-appui`, `erreur-appui` | `#8C331A`, `#9C1F18` | Terracotta et brique plus sombres quand on appuie sur un bouton plein |
| `accent-fond`, `succes-fond`, `erreur-fond` | `#FDEFD3`, `#E6EFE2`, `#FBE6E3` | Fonds pâles des messages et des pastilles |
| `succes-texte`, `erreur-texte` | `#345C31`, `#9C1F18` | Texte lisible sur ces fonds pâles |
| Mode sombre | fond `#1E120B` (brief), surface `#2B1A10`, liens en soleil | Le terracotta en texte sur fond brun foncé est illisible (2,6) : en sombre, les liens passent en soleil ; les boutons restent terracotta |
