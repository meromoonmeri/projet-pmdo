# Fin Forêt Brumeuse — arène de boss et stèle ancienne (4:3) — projet PMDO 0.8.12

Projet d'édition autonome `fin_foret_brumeuse`. Il contient un Ground `ffb1_fin_foret_brumeuse` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

Biome choisi par l'utilisateur : **Forêt Brumeuse (Foggy Forest, `D08P11A` / `P21P02A`)**, décliné en 3 layouts (ici la fin de donjon / arène de boss `FFB1`).

## Installer

- **Projet séparé** : copier `fin_foret_brumeuse` dans `PMDO/MODS/`, l'activer, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Eau des bassins latéraux, façon Métano (couleurs Métano exactes, sans liseré clair) | 4 × 10 ticks |
| 01 | Scintillements Métano natifs | 4 × 10 ticks |
| 02 | Sol complet (herbe) | fixe |
| 03 | Herbe de la clairière sacrée (praticable) | fixe |
| 04 | Chemin et anneau de pierre de l'arène (praticables) | fixe |
| 05 | Fleurs de clairière (praticables) | fixe |
| 06 | Rochers ocre | fixe |
| 07 | Buissons | fixe |
| 08 | Herbes hautes et sous-bois | fixe |
| 09 | Stèle ancienne moussue au nord | fixe |
| 10 | Arbres : houppiers vert sauge/lime, troncs, racines | fixe |
| 11 | Feuilles qui tombent (générées) | 48 × 5 ticks |
| 12 | Lucioles / spores brumeuses (générées) | 48 × 5 ticks |
| 13 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 240 ticks (4 s).

## Marqueurs et collisions

- `entrance` est au sud, sur le chemin. `boss` est au centre de l'arène circulaire. `objectif` est au nord de l'arène, au pied de la stèle ancienne moussue. **Aucune sortie au nord ni warp** (le bord nord et les flancs ouest/est sont fermés par la forêt).
- Sont praticables l'herbe de la clairière, le chemin/anneau de l'arène et les petites fleurs. Un chemin libre de 16 × 16 px a été vérifié de `entrance` vers `boss` et vers `objectif`. **À contrôler en jeu.**

## Limites

- **Terrain, feuilles et lucioles** : dessins générés à partir de la capture `Foggy_Forest_Base_Camp_TDS.png` (`D08P11A`). Les trajectoires, les boucles et la chronologie sont créées par nous ; ce ne sont pas des animations officielles.
- **Eau** : façon Métano, pixels recalculés avec les couleurs Métano exactes (sans liseré clair contre la rive).
- **Scintillements** : seuls pixels Métano natifs du pack.
- **Tests** : aucun test fait dans PMDO.
