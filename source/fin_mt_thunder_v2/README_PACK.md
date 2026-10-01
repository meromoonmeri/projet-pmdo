# Fin Mt. Thunder — arène du sommet (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_mt_thunder`. Il contient le Ground `ftn1_fin_mt_thunder` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

C'est la zone de fin de donjon qui prolonge l'entrée Mt. Thunder (EMT1) : crête de sable au sud, grande arène ronde fermée par une couronne de falaises, nid de pierre plein au nord, mer de nuages d'orage autour. Biome et portée choisis avec l'utilisateur parmi les fins restantes ; ils restent à confirmer.

## Installer

- **Projet séparé** : copier `fin_mt_thunder` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Sol complet (sable, aussi sous tout le reste) | fixe |
| 01 | Sable de l'arène et de la crête (avec les dessus jaunes des blocs de la couronne) | fixe |
| 02 | Cailloux (petits, praticables) | fixe |
| 03 | Pics de roche | fixe |
| 04 | Falaise : couronne de l'arène et corniche du nid | fixe |
| 05 | Nid : pilier de pierre plein, au nord | fixe |
| 06 | Ciel d'orage | fixe |
| 07 | Nuages | fixe |
| 08 | Lueurs : arc « Flash » de la planche, au pied de chaque éclair | 48 × 5 ticks |
| 09 | Éclairs : les 4 éclairs de la planche, « Normal » puis « Fading » | 48 × 5 ticks |
| 10 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 240 ticks (4 s). Huit éclairs par boucle, un toutes les 6 phases. Tous les calques sont opaques ou transparents, sans alpha intermédiaire. Pas de calque de profondeur ni de seuil : la fin n'a pas de bouche.

## Marqueurs et collisions

- **Marqueurs** : `entrance` est au sud, sur la crête. `boss` est au centre de l'arène. `objectif` est au pied du nid, au nord. **Aucun warp, aucune sortie, pas de `donjon_seuil`.**
- **Collisions** : seul le sol de sable et de cailloux relié à la crête est praticable. Le dessus des blocs de la couronne, jaune comme le sable, est exclu par un noyau (ouverture de 9 px, réagrandi de 7 px) et reste bloqué. Pics, couronne, nid, ciel et nuages sont bloqués. Les éclairs et lueurs sont purement visuels. Un chemin libre de 16 × 16 px de l'arrivée au boss et à l'objectif a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain** : dessin généré à partir de la capture `Game Boy Advance - … - Dungeon Boss Rooms - Mt. Thunder.png`. Pas de tuiles natives.
- **Nid** : plus sombre que les falaises de la capture (distance 52,7 pour un seuil de 35). Limite signalée, brut gardé. La roche de l'ensemble est à 26,0.
- **Éclairs et arc** : pixels et couleurs exacts de la planche ; le placement, la cadence et l'arc au pied de l'éclair sont créés par nous.
- **Animations** : ce ne sont pas des animations officielles.
- **Tests** : aucun test fait dans PMDO.
