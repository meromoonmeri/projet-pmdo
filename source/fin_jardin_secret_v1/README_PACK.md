# Fin Jardin secret — arène (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_jardin_secret`. Il contient le Ground `fja1_fin_jardin_secret` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

Le biome (jardin secret : prairie fleurie entre des haies, souche dorée à marches sous un rayon de lumière verte, d'après la capture `secretgarden.png`) a été choisi par l'agent pour la dernière fin de la série (zone de fin : arène de prairie bordée de haies, souche à marches au nord). Il reste à confirmer.

## Installer

- **Projet séparé** : copier `fin_jardin_secret` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Sol complet (herbe, aussi sous tout le reste) | fixe |
| 01 | Prairie : herbe claire et jaune du centre | fixe |
| 02 | Herbe moyenne | fixe |
| 03 | Ombres : herbe assombrie au pied des haies, des arbres et des rochers | fixe |
| 04 | Fleurs blanches, jaunes et roses (praticables) | fixe |
| 05 | Rochers beiges | fixe |
| 06 | Arbres ronds | fixe |
| 07 | Haies de bordure | fixe |
| 08 | Souche dorée | fixe |
| 09 | Marches de la souche (praticables) | fixe |
| 10 | Profondeur : trou sombre de la souche | fixe |
| 11 | Fond vert sombre | fixe |
| 12 | Fleurs Halcyon : 14 touffes natives (Vast_Steppe_Flower_Animations), séquence 0 / 1 / 0 / 2 | 4 × 14 ticks |
| 13 | Pétales : 38 pétales aux couleurs exactes des fleurs du rip, qui tombent et dérivent | 24 × 14 ticks |
| 14 | Feuilles : amas de feuilles des arbres et des haies, houle d'ouest en est (phase 0 = décor d'origine) | 8 × 7 ticks |
| 15 | Rayon de lumière : le faisceau « respire » sur la rampe exacte de la capture | 24 × 7 ticks |
| 16 | Lucioles : 10 points lumineux qui montent, couleurs exactes du rayon | 24 × 7 ticks |
| 17 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 336 ticks (5,6 s). Tous les calques sont opaques ou transparents, sans alpha intermédiaire.

## Marqueurs et collisions

- **Marqueurs** : `entrance` est au sud, au bout de l'allée entre les haies. `boss` est au centre de l'arène. `objectif` est au pied des marches de la souche, au nord. **Aucun warp, aucune sortie.**
- **Collisions** : la prairie, l'herbe, les ombres, les fleurs et les marches reliées à l'allée sud sont praticables. Les rochers, les arbres, les haies, la souche, le trou, le fond et le rayon sont bloqués. Les lucioles, les feuilles, les fleurs Halcyon et les pétales sont purement visuels : ils ne bloquent rien. Quelques poches d'herbe murées entre les haies et les rochers restent bloquées. Un chemin libre de 16 × 16 px a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain** : dessin généré à partir de la capture et du décor d'EJS1 ; le fond d'herbe est copié d'EJS1.
- **Fleurs Halcyon** : dessins et séquence natifs de Palikadude/Halcyon (attribution à Palikadude et à leurs artistes ; aucune autorisation générale de redistribution déduite). Le placement est créé par nous.
- **Feuilles et pétales** : pixels du décor généré (feuilles) et couleurs exactes des fleurs du rip (pétales) ; la houle, les trajets et la cadence sont créés par nous.
- **Rayon et lucioles** : couleurs exactes de la capture ; la forme du rayon est générée, le souffle, les trajets et la cadence sont créés par nous.
- **Animations** : ce ne sont pas des animations officielles.
- **Tests** : aucun test fait dans PMDO.
