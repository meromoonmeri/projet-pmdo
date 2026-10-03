# Entrée Forêt Brumeuse sud → nord (4:3) — projet PMDO 0.8.12

Projet d'édition autonome `entree_foret_brumeuse_sud_nord`. Il contient un Ground `efb1_entree_foret_brumeuse` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

Biome choisi par l'utilisateur : **Forêt Brumeuse (Foggy Forest, `D08P11A` / `P21P02A`)**, décliné en 3 layouts (ici l'entrée sud → nord `EFB1`).

## Installer

- **Projet séparé** : copier `entree_foret_brumeuse_sud_nord` dans `PMDO/MODS/`, l'activer, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Eau du ruisseau forestier, façon Métano (couleurs Métano exactes, sans liseré clair) | 4 × 10 ticks |
| 01 | Scintillements Métano natifs | 4 × 10 ticks |
| 02 | Sol complet (herbe) | fixe |
| 03 | Herbe de la clairière (praticable) | fixe |
| 04 | Chemin de terre ocre (praticable) | fixe |
| 05 | Fleurs de clairière (praticables) | fixe |
| 06 | Rochers ocre | fixe |
| 07 | Buissons | fixe |
| 08 | Herbes hautes et sous-bois | fixe |
| 09 | Parois : arche rocheuse moussue au nord | fixe |
| 10 | Arbres : houppiers vert sauge/lime, troncs, racines | fixe |
| 11 | Profondeur : ouverture sombre sous l'arche au nord | fixe |
| 12 | Feuilles qui tombent (générées) | 48 × 5 ticks |
| 13 | Lucioles / spores brumeuses (générées) | 48 × 5 ticks |
| 14 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 240 ticks (4 s).

## Marqueurs et collisions

- `entrance` est au sud, sur le chemin. `donjon_seuil` est au bout nord du chemin, au pied de l'arche rocheuse moussue et de son ouverture sombre. **Aucun warp.**
- Sont praticables l'herbe de la clairière, le chemin et les petites fleurs. Un chemin libre de 16 × 16 px a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain, feuilles et lucioles** : dessins générés à partir de la capture `Foggy_Forest_Base_Camp_TDS.png` (`D08P11A`). Les trajectoires, les boucles et la chronologie sont créées par nous ; ce ne sont pas des animations officielles.
- **Eau** : façon Métano, pixels recalculés avec les couleurs Métano exactes (sans liseré clair contre la rive).
- **Scintillements** : seuls pixels Métano natifs du pack.
- **Tests** : aucun test fait dans PMDO.
