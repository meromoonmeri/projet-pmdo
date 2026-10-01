# Fin Clairière tropicale — arène de jungle et lagon (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_clairiere_tropicale`. Il contient le Ground `ftc1_fin_clairiere_tropicale` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

C'est la zone de fin de donjon qui prolonge l'entrée Clairière tropicale (ETC1) : piste de dalles au sud, grande arène d'herbe ceinte de jungle, lagon et estrade de pierre au nord. Biome et portée choisis par l'agent pour la suite de la série. Ils restent à confirmer.

## Installer

- **Projet séparé** : copier `fin_clairiere_tropicale` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Sol complet (herbe claire, aussi sous tout le reste) | fixe |
| 01 | Herbe de l'arène | fixe |
| 02 | Dalles de sable (piste et anneau central) | fixe |
| 03 | Touffes et cailloux | fixe |
| 04 | Fleurs (hibiscus) | fixe |
| 05 | Jungle dense | fixe |
| 06 | Palmiers | fixe |
| 07 | Estrade de pierre à marches, au nord | fixe |
| 08 | Rive : falaise de terre au bord du lagon | fixe |
| 09 | Mer : vagues de la capture qui avancent vers la rive (sud) ; seule une bande sombre touche la terre | 24 × 5 ticks |
| 10 | Papillons (planche d'ETC1), vol en huit | 24 × 5 ticks |
| 11 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 120 ticks (2 s). Tous les calques sont opaques ou transparents, sans alpha intermédiaire.

## Marqueurs et collisions

- **Marqueurs** : `entrance` est au sud, sur la piste de dalles. `boss` est au centre de l'arène. `objectif` est sur l'estrade, au nord. **Aucun warp, aucune sortie.**
- **Collisions** : l'herbe, les dalles, l'estrade et les touffes reliées à l'arène sont praticables. La jungle, les palmiers, les fleurs, la rive et la mer sont bloqués. Les papillons sont purement visuels. Un chemin libre de 16 × 16 px de l'arrivée au boss et à l'objectif a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain** : dessin généré à partir de la capture et du décor d'ETC1. Les papillons reprennent la planche d'ETC1, sans nouvelle génération.
- **Mer** : pixels posés par programme, avec uniquement le profil, la crête et les couleurs relevés sur la capture. Le défilement est créé par nous. Le filet clair de la capture contre la rive n'est **pas** repris.
- **Animations** : ce ne sont pas des animations officielles.
- **Tests** : aucun test fait dans PMDO.
