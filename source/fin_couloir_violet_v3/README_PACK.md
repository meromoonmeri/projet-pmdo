# Fin Couloir violet V3 — arène du monolithe (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_couloir_violet`. Il contient le Ground `fcv3_fin_couloir_violet` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

C'est la zone de fin de donjon qui prolonge l'entrée Couloir violet (ECV1) : couloir au sud, grande salle rocheuse semée de blocs, cul-de-sac rocheux dominé par un monolithe de pierre bleu-violet au nord (comme le haut du rip `S05P03A`). Biome et portée choisis par l'agent pour la suite de la série (`« bon avance »`). Ils restent à confirmer.

## Installer

- **Projet séparé** : copier `fin_couloir_violet` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Sol complet (sol mauve marbré sur toute la surface, réutilisé d'ECV1) | fixe |
| 01 | Sol praticable | fixe |
| 02 | Ombres : le sol s'assombrit au pied des parois et des blocs | fixe |
| 03 | Gravillons posés au sol (praticables) | fixe |
| 04 | Blocs : amas de rochers posés dans l'arène | fixe |
| 05 | Rochers : parois empilées et monolithe nord | fixe |
| 06 | Falaise striée sombre | fixe |
| 07 | Vide noir hors carte | fixe |
| 08 | Éboulis : 3 gravillons exacts du rip qui tombent, rebondissent et roulent | 24 × 5 ticks |
| 09 | Poussière : 4 poses générées d'ECV1 à chaque impact | 24 × 5 ticks |
| 10 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 120 ticks (2 s). Tous les calques sont opaques ou transparents, sans alpha intermédiaire.

## Marqueurs et collisions

- **Marqueurs** : `entrance` est au sud, au bout du couloir. `boss` est au centre de la salle. `objectif` est au pied du monolithe rocheux, au nord. **Aucun warp, aucune sortie.**
- **Collisions** : le sol, les ombres et les gravillons sont praticables. Les blocs, les rochers, la falaise et le vide sont bloqués. Un chemin libre de 16 × 16 px de l'arrivée au boss et à l'objectif a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain** : dessin généré à partir de la capture `large.S05P03A.png.301f7a1eadda348357be0801e81faa2a.png`. Le sol complet et la planche de poussière reprennent ceux d'ECV1, sans nouvelle génération.
- **Animations** : les gravillons d'éboulis proviennent pixel par pixel du rip, mais leur chute, leur rebond et les nuages de poussière sont créés par nous. Ce ne sont pas des animations officielles.
- **Tests** : aucun test fait dans PMDO.
