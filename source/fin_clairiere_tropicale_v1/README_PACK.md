# Fin Clairiere tropicale — clairiere jungle (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_clairiere_tropicale`. Il contient le Ground `fct1_fin_clairiere_tropicale` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

C'est la zone de fin de donjon qui prolonge l'entrée Clairiere tropicale (ETC1) : arrivée au sud par un couloir étroit entre les jungles, grande clairière ronde enclose de jungle et de palmiers, chemin de dalles jusqu'au tertre de terre au nord. Biome et portée choisis par l'agent pour la suite de la série. Ils restent à confirmer.

## Installer

- **Projet séparé** : copier `fin_clairiere_tropicale` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Sol complet (herbe claire, aussi sous les jungles) | fixe |
| 01 | Herbe praticable | fixe |
| 02 | Ombres : l'herbe s'assombrit au pied du tertre et des palmiers | fixe |
| 03 | Dalles (pierres plates beige en chemin) | fixe |
| 04 | Touffes basses vertes | fixe |
| 05 | Fleurs hibiscus (rouge, jaune, cyan, pink) | fixe |
| 06 | Jungle dense (massifs vert sombre) | fixe |
| 07 | Palmiers (troncs et palmes) | fixe |
| 08 | Tertre de terre au nord (surmonté d'une pierre) | fixe |
| 09 | Rochers / pierres (grosse pierre du tertre et cailloux) | fixe |
| 10 | Papillons (orange et jaune, vol en 8) | 24 × 5 ticks |
| 11 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 120 ticks (2 s). Tous les calques sont opaques ou transparents, sans alpha intermédiaire.

## Marqueurs et collisions

- **Marqueurs** : `entrance` est au sud, au bout du couloir. `boss` est au centre de la clairière. `objectif` est au pied du tertre, au nord. **Aucun warp, aucune sortie.**
- **Collisions** : seuls l'herbe, les ombres et les dalles sont praticables. La jungle, les palmiers, le tertre et les rochers sont bloqués. Un chemin libre de 16 × 16 px de l'arrivée au boss et à l'objectif a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain** : dessin généré à partir de la capture `large.S01P03A.png.84e22fb77c4061e77b0f546545fed2c7.png`. Le témoin sans objets est édité depuis le décor, la planche de papillons est réutilisée de l'entrée ETC1.
- **Animations** : le vol des papillons est créé par nous : battement et vol en 8 fermé. Ce n'est pas une animation officielle.
- **Tests** : aucun test fait dans PMDO.
