# Entrée Lac Cristallin sud → nord (4:3) — projet PMDO 0.8.12

Projet d'édition autonome `entree_lac_cristal_sud_nord`. Il contient un Ground `elc1_entree_lac_cristal` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

Biome choisi par l'utilisateur : **Lac Cristallin / Crystal Crossing (`lakecrystalpmdsky.png`, `D17P34A`)**, décliné en trilogie complète de 3 layouts (`ELC1` entrée, `FLC1` fin/sanctuaire, `ZLC1` zone ouverte).

## Installer

- **Projet séparé** : copier `entree_lac_cristal_sud_nord` dans `PMDO/MODS/`, l'activer, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Eau du lac souterrain, façon Métano (couleurs exactes du rip `lakecrystalpmdsky.png`, sans liseré clair) | 4 × 10 ticks |
| 01 | Lueur cristalline sous-marine (9 couleurs cyan/bleu exactes du rip) | 12 × 10 ticks |
| 02 | Scintillements Métano natifs | 4 × 10 ticks |
| 03 | Gouttes cristallines et ronds dans l'eau (générés) | 24 × 5 ticks |
| 04 | Sol complet (dalles cristallines cyan) | fixe |
| 05 | Dalles cristallines de la plateforme centrale (praticables) | fixe |
| 06 | Reflets aqua en croix sur les dalles (praticables) | fixe |
| 07 | Rebords biseautés de la plateforme | fixe |
| 08 | Cristaux sombres bleu-sarcelle en bordure | fixe |
| 09 | Îlots et piliers hexagonaux isolés dans le lac | fixe |
| 10 | Piliers hexagonaux et arche cristalline au nord | fixe |
| 11 | Profondeur : ouverture sombre sous l'arche au nord | fixe |
| 12 | Éclats prismatiques flottants (générés) | 48 × 5 ticks |
| 13 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 240 ticks (4 s).

## Marqueurs et collisions

- `entrance` est au sud, sur la chaussée cristalline. `donjon_seuil` est au bout nord de la plateforme, au pied sec de l'ouverture sombre sous l'arche de cristal. **Aucun warp.**
- Sont praticables les dalles et reflets cristallins de la plateforme centrale. Un chemin libre de 16 × 16 px a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain, gouttes et éclats** : dessins générés à partir de la capture `lakecrystalpmdsky.png` (`D17P34A`). Les trajectoires, les boucles et la chronologie sont créées par nous ; ce ne sont pas des animations officielles.
- **Eau et lueur** : façon Métano et anneaux respirants recalculés avec les couleurs exactes du rip (sans liseré clair contre la rive).
- **Scintillements** : seuls pixels Métano natifs du pack.
- **Tests** : aucun test fait dans PMDO.
