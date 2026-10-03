# Fin Clairière tropicale V2 — arène du sanctuaire du lagon (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_clairiere_tropicale`. Il contient le Ground `fct2_fin_clairiere_tropicale` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

C'est la zone de fin de donjon qui prolonge l'entrée Clairière tropicale (ETC1) : couloir d'herbe et de dalles au sud, grande clairière d'arène bordée de deux vasques de lagon tropical, tertre rocheux et autel-sanctuaire de pierre sculptée au nord. Biome et portée choisis par l'agent pour la suite de la série (`« passons a la suite »`). Ils restent à confirmer.

## Installer

- **Projet séparé** : copier `fin_clairiere_tropicale` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Sol complet (herbe claire de la clairière sur toute la surface) | fixe |
| 01 | Herbe praticable | fixe |
| 02 | Ombres : l'herbe s'assombrit au pied du tertre et de l'autel | fixe |
| 03 | Dalles de sable praticables | fixe |
| 04 | Touffes d'herbe et petits cailloux gris | fixe |
| 05 | Massifs de fleurs d'hibiscus (rouge, jaune, cyan, rose) | fixe |
| 06 | Jungle dense (bordures feuillues) | fixe |
| 07 | Palmiers (6 cocotiers) | fixe |
| 08 | Tertre de terre et de roche au nord | fixe |
| 09 | Autel-sanctuaire de pierre sculptée au centre du tertre nord | fixe |
| 10 | Rive de terre brune au-dessus des deux vasques de lagon | fixe |
| 11 | Mer / lagons : vagues du rip (profil de 48 px et crête exacts, bande sombre contre la rive) | 24 × 5 ticks |
| 12 | Papillons : poses générées d'ETC1 (battement 8 phases, vol en huit sur 24 phases) | 24 × 5 ticks |
| 13 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 120 ticks (2 s). Tous les calques sont opaques ou transparents, sans alpha intermédiaire.

## Marqueurs et collisions

- **Marqueurs** : `entrance` est au sud, au bout du couloir d'herbe et de dalles. `boss` est au centre de l'arène. `objectif` est au pied de l'autel-sanctuaire de pierre, au nord. **Aucun warp, aucune sortie.**
- **Collisions** : l'herbe, les ombres, les dalles et les touffes reliées à la clairière sont praticables. La jungle, les palmiers, les fleurs, le tertre, l'autel, la rive et les lagons sont bloqués. Les papillons sont purement visuels. Un chemin libre de 16 × 16 px de l'arrivée au boss et à l'objectif a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain** : dessin généré à partir de la capture `large.S01P03A.png.84e22fb77c4061e77b0f546545fed2c7.png`. Les papillons reprennent la planche générée d'ETC1, sans nouvelle génération.
- **Animations** : le profil et les couleurs des vagues proviennent du rip, mais le défilement dans les deux vasques, le traitement de la rive et le vol des papillons sont créés par nous. Ce ne sont pas des animations officielles.
- **Tests** : aucun test fait dans PMDO.
