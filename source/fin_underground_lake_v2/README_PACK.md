# Fin Underground Lake V2 — sanctuaire du lac souterrain (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_underground_lake`. Il contient le Ground `ful2_fin_underground_lake` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

C'est la zone de fin de donjon qui prolonge l'entrée d'Underground Lake (EUL1) : arrivée au sud sur le sable entre les parois de roche kaki, grande plateforme d'arène de sable au centre entre les deux bassins du lac souterrain, et au nord, au bout de la chaussée sèche, un **monolithe-sanctuaire de pierre sculptée** adossé à la paroi fermée (sans bouche sombre). Biome et portée choisis par l'agent (`« alors ........... »`). Ils restent à confirmer.

## Installer

- **Projet séparé** : copier `fin_underground_lake` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Eau du lac (structure rivière Métano, couleurs exactes du rip, sans liseré clair) | 4 × 10 ticks |
| 01 | Lueur du lac (cœur + 8 anneaux aux 9 couleurs exactes du rip qui respirent) | 12 × 10 ticks |
| 02 | Scintillements (`Metano_Town_River_Sparkles.tile` natifs sur le cœur de la lueur) | 4 × 10 ticks |
| 03 | Gouttes et ronds dans l'eau (poses générées d'EUL1 réutilisées) | 24 × 5 ticks |
| 04 | Sol complet (sable et parois hors lac, réutilisé d'EUL1) | fixe |
| 05 | Sable praticable | fixe |
| 06 | Ombres au sol (sable assombri au pied des parois et de la berge) | fixe |
| 07 | Berge du lac | fixe |
| 08 | Roche (parois de la grotte) | fixe |
| 09 | Piliers et stalagmites dans le lac | fixe |
| 10 | Sanctuaire (monolithe de pierre sculptée au bout nord de la chaussée) | fixe |
| 11 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 120 ticks (2 s). Tous les calques sont opaques ou transparents, sans alpha intermédiaire.

## Marqueurs et collisions

- **Marqueurs** : `entrance` est au sud, dans le goulet de sable. `boss` est au centre de la plateforme de sable. `objectif` est au pied du monolithe-sanctuaire, au nord. **Aucun warp, aucune sortie.**
- **Collisions** : le sable et les ombres sont praticables. Le lac, la berge, les parois, les piliers et le sanctuaire sont bloqués. Un chemin libre de 16 × 16 px de l'arrivée au boss et à l'objectif a été vérifié sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain** : dessin généré à partir du décor d'EUL1 et de `Underground_Lake_shore_TDS.png`. Le sol complet et la planche de gouttes reprennent ceux d'EUL1, sans nouvelle génération.
- **Animations** : seuls les scintillements viennent des fichiers `.tile` de Métano. L'eau, la lueur et les gouttes sont créées par nous. Ce ne sont pas des animations officielles.
- **Tests** : aucun test fait dans PMDO.
