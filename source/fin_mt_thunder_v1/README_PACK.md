# Fin Mt. Thunder — sommet (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_mt_thunder`. Il contient le Ground `fth1_fin_mt_thunder` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

Le biome (sommet d'orage au-dessus des nuages, d'après la planche de la salle du sommet de Mt. Thunder, *Red Rescue Team*) et la portée ont été choisis par l'agent pour la suite des fins de donjon. Ils restent à confirmer. Cette zone prolonge l'entrée Mt. Thunder (EMT1).

## Installer

- **Projet séparé** : copier `fin_mt_thunder` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Sol complet (sable, aussi sous tout le reste) | fixe |
| 01 | Sable du plateau, de la crête et du dessus de l'estrade | fixe |
| 02 | Cailloux (petits, praticables) | fixe |
| 03 | Pics de roche et pierres moussues | fixe |
| 04 | Falaise : parois du plateau, face de l'estrade du nord | fixe |
| 05 | Ciel d'orage | fixe |
| 06 | Nuages | fixe |
| 07 | Lueurs : arc « Flash » de la planche, au pied de chaque éclair | 48 × 5 ticks |
| 08 | Éclairs : les 4 éclairs de la planche, « Normal » puis « Fading » | 48 × 5 ticks |
| 09 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 240 ticks (4 s). Tous les calques sont opaques ou transparents, sans alpha intermédiaire.

## Marqueurs et collisions

- **Marqueurs** : `entrance` est au sud, sur la crête d'arrivée. `boss` est au centre du plateau. `objectif` est au pied de l'estrade, au nord. **Aucun warp, aucune sortie.**
- **Collisions** : le sable et les cailloux reliés à la crête sud sont praticables. Les pics, la falaise, le ciel et les nuages sont bloqués. Les éclairs et les lueurs sont purement visuels. Le dessus de l'estrade est séparé du plateau par la roche et reste bloqué. Un chemin libre de 16 × 16 px de l'arrivée au boss et à l'objectif a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain** : dessin généré à partir de la capture ; le sable de fond est celui d'EMT1 (mêmes octets).
- **Éclairs et arc** : pixels et couleurs exacts de la planche ; le placement, la cadence et l'arc au pied de l'éclair sont créés par nous.
- **Animations** : ce ne sont pas des animations officielles.
- **Tests** : aucun test fait dans PMDO.
