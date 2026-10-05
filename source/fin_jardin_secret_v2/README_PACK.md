# Fin Jardin secret V2 — stèle sanctuaire de Celebi (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_jardin_secret`. Il contient le Ground `fjs4_fin_jardin_secret` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

C'est la zone de fin de donjon qui prolonge les entrées du Jardin secret (EJS1 / EJS2) : allée d'herbe au sud entre les haies, grande prairie fleurie, et au nord, sur la souche dorée baignée par le rayon de lumière verte, une **stèle sanctuaire de pierre fermée** (sans trou ni porte) ornée d'un emblème de Celebi en relief. Biome et portée choisis par l'agent (`« bon avance »`). Ils restent à confirmer.

## Installer

- **Projet séparé** : copier `fin_jardin_secret` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Sol complet (herbe moyenne sur toute la surface, réutilisé d'EJS1) | fixe |
| 01 | Prairie (herbe claire centrale) | fixe |
| 02 | Herbe moyenne | fixe |
| 03 | Ombres au sol (herbe assombrie au pied des haies, arbres et rochers) | fixe |
| 04 | Fleurs (blanches, jaunes, roses) | fixe |
| 05 | Rochers | fixe |
| 06 | Arbres | fixe |
| 07 | Haies | fixe |
| 08 | Souche dorée | fixe |
| 09 | Sanctuaire (socle et stèle de pierre fermée sur la souche) | fixe |
| 10 | Marches (escalier de bois au devant de la souche) | fixe |
| 11 | Fond vert sombre | fixe |
| 12 | Emblème de Celebi (luit de 3 crans sur la rampe exacte du rayon du rip) | 24 × 5 ticks |
| 13 | Rayon de lumière verte (rampe exacte de 22 couleurs du rip, souffle doux) | 24 × 5 ticks |
| 14 | Lucioles (10 grains lumineux qui montent vers le rayon) | 24 × 5 ticks |
| 15 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 120 ticks (2 s). Tous les calques sont opaques ou transparents, sans alpha intermédiaire.

## Marqueurs et collisions

- **Marqueurs** : `entrance` est au sud, dans l'allée d'herbe. `boss` est au centre de la prairie. `objectif` est au pied des marches du sanctuaire de Celebi, au nord. **Aucun warp, aucune sortie.**
- **Collisions** : la prairie, l'herbe, les ombres, les fleurs et les marches sont praticables. Les rochers, les arbres, les haies, la souche, la stèle sanctuaire et le fond sont bloqués. Un chemin libre de 16 × 16 px de l'arrivée au boss et à l'objectif a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain** : dessin généré à partir du décor d'EJS1 et de `secretgarden.png` (seule la zone de la stèle sanctuaire est collée sur le décor d'EJS1 ; témoin et sol complet d'EJS1 réutilisés).
- **Animations** : l'emblème, le rayon et les lucioles utilisent les couleurs exactes du rayon du rip, mais leurs mouvements sont créés par nous. Ce ne sont pas des animations officielles.
- **Tests** : aucun test fait dans PMDO.
