# Fin Couloir violet V2 — arène de rochers et feux follets (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_couloir_violet_v2`. Il contient le Ground `fco2_fin_couloir_violet` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

C'est la zone de fin de donjon qui prolonge l'entrée Couloir violet (ECV1) : couloir au sud, grande arène ronde de rochers bleu-violet, énorme pile de rochers dans l'alcôve du nord. Biome et portée choisis par l'agent pour la suite de la série. Ils restent à confirmer.

## Installer

- **Projet séparé** : copier `fin_couloir_violet_v2` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Sol complet (sol mauve, aussi sous tout le reste) | fixe |
| 01 | Sol mauve de l'arène et du couloir | fixe |
| 02 | Ombres : le sol s'assombrit au pied des parois et des blocs | fixe |
| 03 | Gravillons (petits cailloux au sol, praticables) | fixe |
| 04 | Blocs : amas de rochers posés dans l'arène | fixe |
| 05 | Rochers : parois empilées, pile géante du nord | fixe |
| 06 | Falaise striée du fond | fixe |
| 07 | Vide : noir hors carte | fixe |
| 08 | Éboulis : gravillons de la capture qui tombent du pied des parois, rebondissent et roulent | 24 × 5 ticks |
| 09 | Poussière (planche d'ECV1) : un nuage à chaque impact | 24 × 5 ticks |
| 10 | Lueur : le sol et les rochers s'éclaircissent autour de chaque feu follet (couleurs exactes du rip, rayon qui pulse) | 24 × 5 ticks |
| 11 | Feux follets : 5 flammes (3 bleu glace, 2 violettes) qui dérivent en huit et vacillent | 24 × 5 ticks |
| 12 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 120 ticks (2 s). Tous les calques sont opaques ou transparents, sans alpha intermédiaire.

## Marqueurs et collisions

- **Marqueurs** : `entrance` est au sud, dans le couloir. `boss` est au centre de l'arène. `objectif` est au pied de la pile de rochers, au nord. **Aucun warp, aucune sortie.**
- **Collisions** : le sol, les ombres et les gravillons reliés au couloir sud sont praticables. Les blocs, les rochers, la falaise et le vide sont bloqués. Les éboulis, la poussière, la lueur et les feux follets sont purement visuels (aucun feu follet n'est un PNJ ni un danger). Un chemin libre de 16 × 16 px de l'arrivée au boss et à l'objectif a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain** : dessin généré à partir de la capture et du décor d'ECV1. Le décor est celui de FCO1, le fond de sol et la planche de poussière sont copiés d'ECV1, sans nouvelle génération. La planche des feux follets est générée.
- **Gravillons des éboulis** : pixels et couleurs exacts de la capture ; la chute, le rebond et le roulement sont créés par nous.
- **Feux follets** : dessin généré (12 couleurs), réduit au quart de la planche ; leur trajectoire, leur vacillement et la lueur au sol sont créés par nous, comme les autres animations. Ce ne sont pas des animations officielles.
- **Animations** : ce ne sont pas des animations officielles.
- **Tests** : aucun test fait dans PMDO.
