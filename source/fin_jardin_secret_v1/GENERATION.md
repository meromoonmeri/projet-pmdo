# FGS1 — carnet de génération et recalage

## Provenance

- Référence visuelle : `secretgarden.png` à la racine du dépôt (Explorers of Sky).
- Brut FGS1 retenu : `bruts/decor.png`, 1200 × 896. La composition a été générée directement depuis cette référence, sans réemploi de gros artefacts d'une branche sœur ni d'un rendu historique.
- Itération 2 : correction locale de collision sur l'ouverture sud. La première version avait un rideau de haies/rochers qui coupait visuellement et mécaniquement l'accès à la prairie. La retouche n'a ouvert que le passage au sud; la souche, les autres haies et les objets n'ont pas bougé. Le résultat (largeur d'ouverture visible > 32 px) est conservé comme unique `decor.png` final.
- Témoin final `bruts/temoin_sans_objets.png` généré depuis le même brut final : enlève seulement arbres, rochers et fleurs; souche/rayon/haies/ouverture sud/fond restent. `classify()` trouve 61 massifs de fleurs, 15 rochers et 12 arbres; recalage estimé 0,0 px (écart brut moyen 4,13; décalage de 1 px 4,43).
- `bruts/sol_complet.png` est une sous-couche cachée produite par le build : un carré de prairie sans objets est échantillonné dans le rendu, les pixels étrangers éventuels du patch sont remplis au plus proche voisin et le patch est répété. Ce n'est pas une texture canonique distincte ni un visuel exposé.

## Prompts (résumés fidèles)

1. **Décor** : composition pixel art 4:3 inspirée de `secretgarden.png`, arène de prairie au centre, entrée sud, souche creuse à marches au nord sous un rayon vert, fleurs/rochers/arbres ronds/haies; centre dégagé; exclure temple, emblème/sprite Celebi, eau, cascade, papillons et accessoires non présents dans la référence.
2. **Correction d'accès** : conserver dimensions, cadrage, palette et objets; ouvrir un passage d'au moins 32 px à l'entrée sud dans la bordure de haies/rochers, retirer seulement les pixels bloquants et les remplacer par la prairie.
3. **Témoin** : garder le décor final strictement en place, retirer seulement arbres/ombres, rochers et petites fleurs, remplir par la prairie voisine; préserver souche, rayon, haies et ouverture sud.

Les prompts complets ne sont pas reproduits mot à mot; les images réelles constituent la source de vérité. Les couches sont un rendu généré référencé, pas des tuiles natives.

## Découpe et fidélité mesurée

Le script importe les fonctions de méthode EJS1 (classification du témoin, décomposition des masques, recalage, réduction et animation de rampe) sans importer ni copier aucun calque/rendu EJS1. La rampe RVB de 22 verts est celle lue par EJS1 sur le rip `secretgarden.png`; les lucioles gardent ses couleurs. Placement, pulsation et cadence FGS1 sont composés pour ce lot et ne sont pas officiels.

La distance indicative RVB d'herbe claire au rip est 41,9 (l'herbe médiane 24,0, le fond 8,3, les rochers 12,9). Elle dépasse le seuil atelier historique de 35 pour la seule classe d'herbe claire : conserver ce résultat visible dans l'audit, **ne pas le présenter comme une réussite du seuil**. La mesure n'est ni une validation artistique, ni pixel-perfect.
