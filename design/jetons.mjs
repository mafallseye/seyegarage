// Safia : fabrique tokens.css à partir de tokens.json et vérifie les contrastes (WCAG 2).
// Lancer :  node design/jetons.mjs      (aucune dépendance)
import { readFileSync, writeFileSync } from 'node:fs';

const ici = new URL('.', import.meta.url);
const j = JSON.parse(readFileSync(new URL('tokens.json', ici), 'utf8'));

const luminance = (hex) => {
  const [r, v, b] = [1, 3, 5]
    .map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * v + 0.0722 * b;
};
const contraste = (a, b) => {
  const [x, y] = [luminance(a), luminance(b)];
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
};

// ---- contrastes
let echecs = 0;
for (const [mode, couleurs] of Object.entries(j.couleur)) {
  console.log(`\nMode ${mode}`);
  for (const [devant, derriere, minimum] of j.contrastes) {
    const c = contraste(couleurs[devant], couleurs[derriere]);
    const ok = c >= minimum;
    if (!ok) echecs += 1;
    console.log(`  ${ok ? 'ok   ' : 'ÉCHEC'} ${c.toFixed(1).replace('.', ',').padStart(4)} (min ${minimum})  ${devant} sur ${derriere}`);
  }
}

// ---- tokens.css
const vars = (objet, prefixe) => Object.entries(objet).map(([nom, valeur]) => `  --${prefixe}-${nom}: ${valeur};`);
const autres = [
  ...vars(j.police, 'police'), ...vars(j.taille, 'taille'), ...vars(j.interligne, 'interligne'),
  ...vars(j.graisse, 'graisse'), ...vars(j.espace, 'espace'), ...vars(j.rayon, 'rayon'),
  ...vars(j.ombre, 'ombre'), `  --tactile: ${j.tactile};`, `  --hauteur-controle: ${j['hauteur-controle']};`, ...vars(j.largeur, 'largeur'),
];
const sombre = vars(j.couleur.sombre, 'couleur');
const css = `/* ${j.nom} : jetons de design. Fichier fabriqué par jetons.mjs à partir de tokens.json : ne pas le modifier à la main. */
:root {
  color-scheme: light;
${[...vars(j.couleur.clair, 'couleur'), ...autres].join('\n')}
}

/* Mode sombre : suit le réglage du téléphone, ou forcé avec data-theme="sombre" (data-theme="clair" force le clair). */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="clair"]) {
    color-scheme: dark;
${sombre.map((l) => '  ' + l).join('\n')}
  }
}
:root[data-theme="sombre"] {
  color-scheme: dark;
${sombre.join('\n')}
}
`;
writeFileSync(new URL('tokens.css', ici), css);
console.log(`\ntokens.css écrit. ${echecs === 0 ? 'Tous les contrastes passent.' : echecs + ' contraste(s) insuffisant(s).'}`);
process.exit(echecs === 0 ? 0 : 1);
