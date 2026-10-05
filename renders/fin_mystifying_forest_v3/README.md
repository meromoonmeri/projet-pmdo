# Fin Mystifying Forest V3 — sanctuaire de la forêt mystique (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_mystifying_forest`. Il contient le Ground `fmf3_fin_mystifying_forest` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

C'est la zone de fin de donjon qui prolonge l'entrée de Mystifying Forest (EMF1) : arrivée au sud sur le chemin de terre rose-brun, grande clairière dégagée en arène circulaire d'herbe et de terre au centre (avec la mare à l'ouest), et au nord, au bout du chemin entre les grands arbres et leurs racines, un **autel-sanctuaire de pierre moussue** fermé (sans ouverture sombre). Biome et portée choisis par l'agent (`« alors ........... »`). Ils restent à confirmer.

## Installer

- **Projet séparé** : copier `fin_mystifying_forest` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Mare (façon rivière Métano, couleurs Métano exactes, sans liseré de rive) | 4 × 10 ticks |
| 01 | Scintillements (`Metano_Town_River_Sparkles.tile` natifs) | 4 × 10 ticks |
| 02 | Sol complet (herbe hors mare, réutilisé d'EMF1) | fixe |
| 03 | Herbe claire praticable | fixe |
| 04 | Chemin de terre rose-brun (et anneau d'arène central) | fixe |
| 05 | Herbes hautes | fixe |
| 06 | Rochers moussus | fixe |
| 07 | Arbres (houppiers, troncs et racines) | fixe |
| 08 | Sanctuaire (autel de pierre moussue au bout nord du chemin) | fixe |
| 09 | Feuilles qui tombent (poses d'EMF1 réutilisées) | 48 × 5 ticks |
| 10 | Lucioles (poses d'EMF1 réutilisées) | 48 × 5 ticks |
| 11 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 240 ticks (4 s). Tous les calques sont opaques ou transparents, sans alpha intermédiaire.

## Marqueurs et collisions

- **Marqueurs** : `entrance` est au sud, sur le chemin. `boss` est au centre de la clairière. `objectif` est au pied de l'autel-sanctuaire, au nord. **Aucun warp, aucune sortie.**
- **Collisions** : l'herbe claire et le chemin sont praticables. La mare, les herbes hautes, les rochers, les arbres et le sanctuaire sont bloqués. Un chemin libre de 16 × 16 px de l'arrivée au boss et à l'objectif a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain** : dessin généré à partir du décor d'EMF1 et de `Mystifying_Forest_entrance_TDS.png`. Le sol complet et la planche de feuilles/lucioles reprennent ceux d'EMF1, sans nouvelle génération.
- **Animations** : les couleurs de la mare et les scintillements viennent des fichiers `.tile` de Métano. L'onde de la mare, les feuilles et les lucioles sont créées par nous. Ce ne sont pas des animations officielles.
- **Tests** : aucun test fait dans PMDO.
