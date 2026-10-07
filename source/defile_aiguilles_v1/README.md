# CPL1 — Défilé des Aiguilles

Prochaine carte de la série PMDO, à la suite du chantier Colonnes Ocre. **CPL1 est un code de travail local, pas un code MAP_BG du jeu.** Direction choisie sans reprendre la carte à l'identique : passage sableux qui serpente autour d'une mesa centrale, falaises latérales et aiguilles de grès.

## Référence et méthode

- Référence canonique **D13P11A** fournie avec la source : `bruts/D13P11A_ROM.png`, rendu direct des ressources `BMA/BPC/BPL` extraites de `pret/pmd-sky` (`c8073235b39746a7ee74e6cea16c730bd91a1e67`) par `recuperer_maps.py rom --only D13P11A` / skytemple-files. Le GIF versionné à la racine est pixel-identique à ce rendu. `index_rom.json` confirme 456×456, une frame, deux couches, sans collision ni animation de palette.
- L'image de composition `bruts/CPL1_layout_reference.png` a été générée en prenant ce rip comme référence stricte de couleur, matière et échelle. Elle sert de **guide de composition généré**; ses dessins ne sont pas des tuiles originales.
- Le guide carré est ramené à 456×456 par filtrage BOX, puis quantifié sans tramage aux **30 couleurs exactes du rip D13P11A**. Le patch de sable du calque de base est prélevé directement dans le GIF de référence. Cela conserve une palette et quelques pixels de matière canoniques, mais ne transforme pas les contours générés en art natif.
- Taille maintenue à 456×456 (57×57 cellules de 8 px, `TexSize=1`), sans agrandir le rip. Une seule frame statique; aucune animation de palette inventée.
- Calques éditables : base de sable canonique, sable/chemin générés référencés, falaises, piliers/blocs. La première segmentation montrait deux tronçons non reliés : un court col de 22 px, au sud-est de la mesa, est raccordé avec un patch de sable extrait du rip D13P11A. Cette correction est déclarée dans le manifeste; sa position et les séparations roche/sable restent à vérifier artistiquement.

## Livrables

- `renders/defile_aiguilles_v1/maps/passage/CPL1_calques.ora` : calques modifiables.
- `renders/defile_aiguilles_v1/maps/passage/calques/` : PNG RGBA alignés sur la grille PMD 8 px.
- `renders/defile_aiguilles_v1/maps/passage/masques/` : grès et praticabilité provisoire.
- `renders/defile_aiguilles_v1/maps/passage/review/` : rendu et superposition collisions/marqueurs.
- `renders/defile_aiguilles_v1/CPL1_projet_pmdo_0812.zip` : projet d'édition Ground/Tile PMDO 0.8.12.
- `renders/defile_aiguilles_v1/CPL1_calques_png_8px.zip` : calques, masques, revue, rip D13P11A et guide de composition.
- `apercu_defile_aiguilles_v1.html` : aperçu local à calques activables et collisions.

Le Ground comporte des marqueurs `entrance` et `sortie` provisoires. La route 16×16 nord-sud est vérifiée par le test hors jeu; les destinations/warps doivent être reliées à la carte voulue. Les collisions sont déduites du grès sombre et des bords; leur forme exacte requiert une vérification en éditeur.

## Build / validation

```bash
.venv/bin/python source/defile_aiguilles_v1/build.py
.venv/bin/python -m unittest source/defile_aiguilles_v1/test_build.py -v
.venv/bin/python source/defile_aiguilles_v1/package.py
```

Le pipeline construit un vrai conteneur `.rsground`, ses `.tile` et `Content/Tile/index.idx` à partir du codec Ground PMDO déjà présent dans `source/pmdo_cote/`. Aucun binaire du jeu n'est exécuté. **Aucun test runtime, rendu GPU, test gameplay ni approbation artistique n'est revendiqué.** Installer le pack dans une copie/sauvegarde de PMDO seulement, puis vérifier visuellement les bords, couches, collisions, marqueurs, occlusions et rendu.
