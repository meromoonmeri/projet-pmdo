# Fin Mt. Thunder V3 — sommet d'orage (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_mt_thunder`. Il contient le Ground `fmt3_fin_mt_thunder` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

C'est la zone de fin de donjon qui prolonge l'entrée Mt. Thunder (EMT1) : crête de sable qui sort des nuages au sud, plateau du sommet à deux gradins, aiguille rocheuse sommitale au nord au-dessus de la mer d'orage (sans grotte, fidèle à la vraie salle de boss de Mt. Thunder Peak). Biome et portée choisis par l'agent (`« bon avance »`). Ils restent à confirmer.

## Installer

- **Projet séparé** : copier `fin_mt_thunder` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Sol complet (sable jaune pâle sur toute la surface, réutilisé d'EMT1) | fixe |
| 01 | Sable praticable | fixe |
| 02 | Cailloux au sol (praticables) | fixe |
| 03 | Pics de roche et pierres moussues | fixe |
| 04 | Falaise (bords et gradins du plateau) | fixe |
| 05 | Piton (aiguille rocheuse sommitale au nord) | fixe |
| 06 | Ciel d'orage sombre | fixe |
| 07 | Mer de nuages d'orage | fixe |
| 08 | Lueurs : arc « Flash » exact de la planche sur les nuages au pied des éclairs | 48 × 5 ticks |
| 09 | Éclairs : les 4 éclairs exacts de la planche (couleurs Normal / Fading exactes) | 48 × 5 ticks |
| 10 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 240 ticks (4 s). Tous les calques sont opaques ou transparents, sans alpha intermédiaire.

## Marqueurs et collisions

- **Marqueurs** : `entrance` est au sud, sur la crête de sable. `boss` est au centre du plateau. `objectif` est au pied de l'aiguille rocheuse sommitale, au nord. **Aucun warp, aucune sortie.**
- **Collisions** : le sable et les cailloux sont praticables. Les pics, la falaise, le piton, le ciel et les nuages sont bloqués. Un chemin libre de 16 × 16 px de l'arrivée au boss et à l'objectif a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain** : dessin généré à partir de la planche `Game Boy Advance - Pokemon Mystery Dungeon_ Red Rescue Team - Dungeon Boss Rooms - Mt. Thunder.png`. Le sol complet reprend celui d'EMT1, sans nouvelle génération.
- **Animations** : les 4 éclairs, l'arc Flash et les couleurs Normal / Fading sont copiés pixel par pixel de la planche, mais leur chronologie et leur placement sont créés par nous. Ce ne sont pas des animations officielles.
- **Tests** : aucun test fait dans PMDO.
