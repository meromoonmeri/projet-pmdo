# Fin Underground Lake (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_underground_lake`. Il contient le Ground `ful1_fin_underground_lake` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

C'est la zone de fin du lac souterrain, dans la suite de l'entrée Underground Lake (EUL1). Biome et portée choisis par l'agent, à confirmer.

## Installer

- **Projet séparé** : copier `fin_underground_lake` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Eau du lac (3 couleurs exactes du rip ; bande, accent, aplat, onde) | 4 × 10 ticks |
| 01 | Lueur du lac (9 anneaux aux couleurs exactes du rip qui respirent) | 12 × 10 ticks |
| 02 | Scintillements Métano natifs | 4 × 10 ticks |
| 03 | Gouttes et ronds dans l'eau (générés) | 24 × 5 ticks |
| 04 | Sol complet (sable) | fixe |
| 05 | Sable praticable | fixe |
| 06 | Ombres au pied des parois | fixe |
| 07 | Berge du lac | fixe |
| 08 | Parois rocheuses | fixe |
| 09 | Piliers et stalagmites | fixe |
| 10 | Profondeur (bouche sombre) | fixe |
| 11 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 120 ticks (2 s). Aucun ciel, arène fermée.

## Marqueurs et collisions

- **Marqueurs** : `entrance` au sud, sur le sable ; `boss` sur la chaussée au sud du lac ; `objectif` devant la grotte au nord, sur sable sec. **Aucune sortie, aucun warp, pas de `donjon_seuil`.**
- **Collisions** : seul le sable (ombres comprises) est praticable. Le lac, la berge, les parois, les piliers et la bouche sont bloqués ; la bande nord est une paroi. Des chemins libres de 16 × 16 px de l'arrivée au boss et à l'objectif ont été vérifiés sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain, eau et lueur** : dessins générés à partir de la capture `Underground_Lake_shore_TDS.png`. Ce ne sont pas des tuiles natives.
- **Animations** : lac façon rivière Métano, lueur qui respire et gouttes sont créés par nous, aux couleurs exactes du rip. Ce ne sont pas des animations officielles.
- **Boss** : aucun boss n'est nommé ni placé ; `boss` est seulement un marqueur d'emplacement.
- **Tests** : aucun test fait dans PMDO.
