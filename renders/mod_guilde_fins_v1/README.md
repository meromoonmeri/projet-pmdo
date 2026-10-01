# Guilde Treehouse — fins de donjon (16 cartes) — mod PMDO 0.8.12

Ce dossier est un mod d'édition autonome, namespace `guilde_fins_donjon`. Il regroupe les **16 fins de donjon** de la série, au nord de chaque entrée sud → nord (mod `guilde_entrees_sud_nord`). Chaque carte est un Ground animé 768 × 576, avec ses collisions et ses marqueurs : `entrance` (arrivée, au sud) et un ou deux repères au nord (`boss` et `objectif`, ou le repère propre à la fin). **Aucun warp** : c'est une base d'édition, pas une aventure jouable. Les versions successives d'une même fin sont conservées (FGG1 et FGG2, FCO1 et FCO2).

**Aucune validation de l'utilisateur n'est enregistrée pour les fins** : elles sont toutes à confirmer. **Aucune carte n'a encore été testée dans PMDO.**

## Installer

- **Mod séparé** : copier le dossier `guilde_fins_donjon` dans `PMDO/MODS/`, activer le mod, puis ouvrir les Grounds dans l'éditeur (mode développeur).
- **Dans un mod existant** : `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis la même commande sans `--dry-run`. L'installeur ne remplace jamais un fichier existant différent, et fusionne l'index des tuiles après en avoir fait une sauvegarde.

## Cartes

| # | Ground | Fin | Calques | Animations (frames × ticks) | Marqueurs |
|---|---|---|---|---|---|
| 1 | `fvs1_fin_vapeur_sommet` | Vapeur (sommet) | 9 | 4 × 10, 24 × 5 | `entrance` (384, 560), `boss` (376, 344), `source` (376, 224) |
| 2 | `fcf1_fin_cratere_fosse` | Cratère (fosse) | 10 | 4 × 10, 6 × 10, 24 × 5 | `entrance` (384, 560), `boss` (376, 288), `embleme` (376, 96) |
| 3 | `frp1_fin_ruine_puits` | Ruine (puits scellé) | 9 | 6 × 10, 8 × 5, 24 × 5 | `entrance` (384, 560), `boss` (384, 288), `cle_de_voute` (376, 176) |
| 4 | `fgg1_fin_givre_grotte` | Givre, grotte de cristal | 9 | 4 × 10, 6 × 10, 48 × 5 | `entrance` (384, 560), `boss` (376, 312), `cristal` (376, 232) |
| 5 | `fgg2_fin_givre_aurore` | Givre V2 (aurore) | 10 | 4 × 10, 12 × 10, 48 × 5 | `entrance` (384, 560), `boss` (376, 304), `belvedere` (376, 184) |
| 6 | `fbs1_fin_bristle_sommet` | Bristle (sommet) | 7 | 12 × 10, 24 × 5 | `entrance` (384, 560), `boss` (384, 288), `azurill` (376, 160) |
| 7 | `fjs1_fin_jungle_sud` | Jungle sud | 9 | 48 × 5 | `entrance` (376, 560), `boss` (384, 296), `objectif` (376, 176) |
| 8 | `fwc1_fin_waterfall_cave` | Waterfall Cave | 9 | 12 × 5, 24 × 10 | `entrance` (376, 560), `arene` (384, 312), `joyau` (376, 224) |
| 9 | `foc1_fin_ocean_kyogre` | Océan de Kyogre | 11 | 12 × 5, 12 × 20, 16 × 15, 24 × 10, 48 × 5 | `entrance` (384, 560), `sceau` (376, 296), `kyogre` (368, 200) |
| 10 | `fsm1_fin_sables_mouvants` | Sables mouvants | 10 | 12 × 10, 24 × 5 | `entrance` (376, 560), `boss` (384, 440), `objectif` (352, 160) |
| 11 | `fst1_fin_star_cave` | Star Cave | 9 | 24 × 5 | `entrance` (384, 560), `boss` (384, 320), `objectif` (384, 152) |
| 12 | `ftc1_fin_clairiere_tropicale` | Clairière tropicale | 12 | 24 × 5 | `entrance` (352, 560), `boss` (384, 240), `objectif` (384, 64) |
| 13 | `fco1_fin_couloir_violet` | Couloir violet | 11 | 24 × 5 | `entrance` (392, 560), `boss` (384, 272), `objectif` (384, 144) |
| 14 | `fco2_fin_couloir_violet` | Couloir violet V2 | 13 | 24 × 5 | `entrance` (392, 560), `boss` (384, 272), `objectif` (384, 144) |
| 15 | `fth1_fin_mt_thunder` | Mt. Thunder | 10 | 48 × 5 | `entrance` (376, 560), `boss` (376, 232), `objectif` (384, 112) |
| 16 | `fja1_fin_jardin_secret` | Jardin secret (végétation animée) | 18 | 4 × 14, 8 × 7, 24 × 7, 24 × 14 | `entrance` (376, 560), `boss` (376, 272), `objectif` (376, 160) |

Toutes les cartes font 768 × 576 (96 × 72 cases de 8 px). Chaque carte a un calque Top vide (`Layer=4`) en dernier.

## Scripts

Chaque carte a son script `Data/Script/guilde_fins_donjon/ground/<carte>/init.lua`, copié tel quel depuis son lot.

## Limites

- Terrains générés à partir de captures des jeux (rendu généré référencé) ; les rendus générés ne sont pas des tuiles natives, sauf les fleurs Halcyon de FJA1 (Palikadude/Halcyon, attribution à ses auteurs).
- Les animations sont créées pour ces cartes : ce ne sont pas les animations officielles.
- Collisions et marqueurs vérifiés sur la grille, pas en jeu. Aucun marqueur n'est raccordé à un donjon ou à un boss réel.
