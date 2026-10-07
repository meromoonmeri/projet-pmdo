# PVC1 — Passage des Veines Cristallines

Projet Ground éditable pour **PMDO 0.8.12**. Identifiant local `PVC1` (ce n'est pas un identifiant `MAP_BG` officiel). Asset : `pvc1_passage_veines_cristallines`, namespace : `passage_veines_cristal`.

## Contenu et installation

Le paquet contient un Ground `.rsground`, ses banques `.tile`, `Content/Tile/index.idx`, `Mod.xml`, les scripts minimaux d'initialisation, ce README, un manifeste et `INSTALLER.py`. Installer seulement dans une copie/sauvegarde de PMDO 0.8.12. L'installateur fusionne l'entrée `index.idx`; il n'ajoute aucune destination de warp.

## Origine graphique

Référence : rip D17P33A extrait des ressources `BMA/BPC/BPL/BPA` de `pret/pmd-sky`, puis vérifié contre le GIF de galerie. Le décor et le sol ont été générés séparément, segmentés et quantifiés sur la palette RGB exacte de 96 couleurs du rip. **La palette et le timing des deux pistes sont référencés; les formes, textures et effets visuels ne sont pas des pixels/tuiles natifs extraits.** Les animations du Ground sont des reflets générés à 6 et 4 phases de 10 ticks; elles n'utilisent pas les images d'animation natives.

## Dimensions, couches, contrôles

- 768×576 px, grille 96×72, cellules 8×8 (`TexSize=1`), cinq calques de décor statiques et deux pistes animées, plus Top vide.
- Obstacles et marqueurs `entrance` / `sortie` provisoires, route libre 16×16 contrôlée hors moteur.
- Aucun runtime PMDO, GPU, gameplay, warp ou approbation artistique n'est revendiqué. Vérifier le rendu, les collisions, les occlusions, les marqueurs et les connexions dans l'éditeur avant usage.

Le paquet est un projet d'édition, pas une aventure PMDO complète.
