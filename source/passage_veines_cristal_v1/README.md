# PVC1 — Passage des Veines Cristallines

Carte suivante choisie par l'agent après CPL1 pour apporter un biome cristallin. `PVC1` est un code local de lot, pas un identifiant `MAP_BG` officiel. La composition est nouvelle : large galerie bleue, bassin/veine lumineuse décalé, route en S du sud au nord, bordure minérale et alcôve au nord-est.

## Rip et provenance

- `bruts/D17P33A_ROM.png` : frame de référence rendue des ressources ROM `D17P33A` avec skytemple-files.
- `bruts/D17P33A_animations.webp` : 12 frames rendues; chaque frame est pixel-identique aux frames correspondantes du GIF de galerie `large.D17P33A.gif.188f8399cf4c18292d9ecdd2454bcd10.gif` à la racine.
- Ressources sources du clone `pret/pmd-sky`, commit `c8073235b39746a7ee74e6cea16c730bd91a1e67` : `d17p33a.bma`, `.bpc`, `.bpl`, `d17p33a1.bpa` et `d17p33a5.bpa`.
- Index ROM : 456×504 px, 12 rendus, 2 couches, aucune collision intégrée, pas d'animation de palette. BPA1 : 6 images × 10 ticks; BPA5 : 4 images × 10 ticks. PPCM : 12 états × 10 ticks = 120 ticks. Les durées du GIF (160 ms) et du WebP extrait (167 ms) ne servent pas à définir la cadence canonique.

## Méthode

1. Génération d'un décor 1200×896 sur magenta et d'un sol complet séparé, avec le rip D17P33A fourni comme référence.
2. Détourage magenta et segmentation pleine résolution (bordure, alcôve, cristaux, veine); réduction uniforme `576/896` à 771×576 puis recadrage centré à 768×576. Réduction BOX pondérée par classe, puis quantification sans tramage dans les 96 couleurs RGB exactes du rip.
3. Calques éditables alignés sur la grille de 8 px. Les deux effets animés sont générés : reflets de cristaux (6×10 ticks) et ondes de la veine (4×10 ticks); la scène combinée boucle sur 120 ticks.
4. Construction d'un Ground PMDO 0.8.12, masque d'obstacles, marqueurs provisoires et contrôle de continuité d'un personnage 16×16.

**Limite de provenance :** aucun pixel de texture n'est prélevé du rip. La palette exacte et la structure temporelle BPA guident le build, mais la composition, les matériaux et les effets visuels restent générés; ce ne sont pas des textures/tuiles natives.

## Build et contrôles

```sh
.venv/bin/python source/passage_veines_cristal_v1/build.py
.venv/bin/python -m unittest source/passage_veines_cristal_v1/test_build.py -v
.venv/bin/python source/passage_veines_cristal_v1/package.py
```

Livrables : `renders/passage_veines_cristal_v1/`, l'aperçu `apercu_passage_veines_cristal_v1.html`, un ZIP Ground/Tile PMDO et un ZIP de calques/animations/masques/références. Aucun lancement PMDO, rendu GPU ou gameplay n'est annoncé; `art_approved` et `runtime_tested` restent `false`.
