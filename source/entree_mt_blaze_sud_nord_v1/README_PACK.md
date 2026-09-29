# Entrée Mt. Blaze (4:3) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `entree_mt_blaze_sud_nord`. Il contient le Ground `emb1_entree_mt_blaze_sud_nord` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

C'est la entrée de donjon du volcan, inspirée de Rescue_Team_-_Mt._Blaze_Entrance.png (GBA, Red Rescue Team). Rendu généré référencé avec les textures canoniques, lave en magenta.

## Installer

- **Projet séparé** : copier `entree_mt_blaze_sud_nord` dans `PMDO/MODS/`, activer le mod, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer la même commande sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Lave (3 teintes lave exactes du rip : 208/64/8, 240/120/0, 240/176/0 ; onde Métano) | 4 × 10 ticks |
| 01 | Lueur de lave (9 anneaux orange→jaune qui respirent) | 12 × 10 ticks |
| 02 | Scintillements de braises sur lave | 4 × 10 ticks |
| 03 | Flammes et impacts (poses générées sur lave) | 24 × 5 ticks |
| 04 | Sol complet (sable) | fixe |
| 05 | Sable praticable | fixe |
| 06 | Ombres au pied des parois | fixe |
| 07 | Berge de lave | fixe |
| 08 | Parois rocheuses grises | fixe |
| 09 | Rochers et piliers | fixe |
| 10 | Profondeur (bouche sombre) | fixe |
| 11 | Vide, `Layer=4` (Top) | — |

La scène boucle en 120 ticks (2 s). Entrée ouverte au sud, grotte au nord.

## Marqueurs et collisions

- **Marqueurs** : `entrance` au sud, sur le sable ; `boss` au centre de la clairière ; `objectif` devant la grotte au nord, sur sable sec. **Aucune sortie, aucun warp, pas de `donjon_seuil`.**
- **Collisions** : seul le sable (ombres comprises) est praticable. Le lave, la berge, les parois, les piliers et la bouche sont bloqués ; la bande nord est une paroi. Des chemins libres de 16 × 16 px de l'arrivée au boss et à l'objectif ont été vérifiés sur la grille. **À contrôler en jeu.**

## Limites

- **Terrain, eau et lueur** : dessins générés à partir de la capture `Rescue_Team_-_Mt._Blaze_Entrance.png`. Ce ne sont pas des tuiles natives.
- **Animations** : lave façon rivière Métano, lueur de lave et flammes sont créés par nous, aux couleurs exactes du rip. Ce ne sont pas des animations officielles.
- **Boss** : aucun boss n'est nommé ni placé ; `boss` est seulement un marqueur d'emplacement.
- **Tests** : aucun test fait dans PMDO.
