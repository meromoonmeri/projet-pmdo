# Guilde Treehouse — zones de fin de donjon (17 cartes) — mod PMDO 0.8.12

Ce dossier est un mod d'édition autonome, namespace `guilde_fins_donjons`. Il regroupe les **17 zones de fin de donjon** au format **4:3 vaste (768 × 576 px)** qui prolongent la série des entrées (`guilde_entrees_sud_nord` + `EFB1`). Chaque carte est un Ground animé avec ses collisions et trois marqueurs : `entrance` (arrivée, au sud), un marqueur d'arène centrale (`boss` ou `arene`) et un marqueur d'objectif au nord (`objectif`, `source`, `embleme`, `cle_de_voute`, `cristal`, `belvedere`, `azurill` ou `joyau`). **Aucun warp, aucune sortie** : c'est une base d'édition, pas une aventure jouable.

**Aucune carte n'a encore été testée dans PMDO.**

## Installer

- **Mod séparé** : copier le dossier `guilde_fins_donjons` dans `PMDO/MODS/`, activer le mod, puis ouvrir les Grounds dans l'éditeur (mode développeur).
- **Dans un mod existant** : `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis la même commande sans `--dry-run`. L'installeur ne remplace jamais un fichier existant différent, et fusionne l'index des tuiles après en avoir fait une sauvegarde.

## Cartes

| # | Ground | Carte | Entrée associée | Taille | Calques | Animations (frames × ticks) | `entrance` | Arène / Objectif |
|---|---|---|---|---|---|---|---|---|
| 1 | `fvs1_fin_vapeur_sommet` | Fin Vapeur (Steam Cave Peak) | `ESN1 / ESN2` | 768 × 576 | 9 | 4 × 10, 24 × 5 | (384, 560) | boss=(376, 344), source=(376, 224) |
| 2 | `fcf1_fin_cratere_fosse` | Fin Cratère (Dark Crater Pit) | `ECN1` | 768 × 576 | 10 | 4 × 10, 6 × 10, 24 × 5 | (384, 560) | boss=(376, 288), embleme=(376, 96) |
| 3 | `frp1_fin_ruine_puits` | Fin Ruine (Sealed Ruin Pit) | `ERN1` | 768 × 576 | 9 | 6 × 10, 8 × 5, 24 × 5 | (384, 560) | boss=(384, 288), cle_de_voute=(376, 176) |
| 4 | `fgg1_fin_givre_grotte` | Fin Givre V1 (grotte de glace) | `EGN1` | 768 × 576 | 9 | 4 × 10, 6 × 10, 48 × 5 | (384, 560) | boss=(376, 312), cristal=(376, 232) |
| 5 | `fgg2_fin_givre_aurore` | Fin Givre V2 (aurore boréale) | `EGN1` | 768 × 576 | 10 | 4 × 10, 12 × 10, 48 × 5 | (384, 560) | boss=(376, 304), belvedere=(376, 184) |
| 6 | `fbs1_fin_bristle_sommet` | Fin Bristle (Mt. Bristle Peak) | `EBN1` | 768 × 576 | 7 | 12 × 10, 24 × 5 | (384, 560) | boss=(384, 288), azurill=(376, 160) |
| 7 | `fjs1_fin_jungle_sud` | Fin Jungle (Southern Jungle) | `EJN1` | 768 × 576 | 9 | 48 × 5 | (376, 560) | boss=(384, 296), objectif=(376, 176) |
| 8 | `fwc1_fin_waterfall_cave` | Fin Waterfall Cave (chambre du joyau) | `EWC1..3` | 768 × 576 | 9 | 12 × 5, 24 × 10 | (376, 560) | arene=(384, 312), joyau=(376, 224) |
| 9 | `ful2_fin_underground_lake` | Fin Underground Lake (sanctuaire du lac) | `EUL1` | 768 × 576 | 12 | 4 × 10, 12 × 10, 24 × 5 | (384, 560) | boss=(376, 336), objectif=(376, 128) |
| 10 | `fmf3_fin_mystifying_forest` | Fin Mystifying Forest (sanctuaire sylvestre) | `EMF1` | 768 × 576 | 12 | 4 × 10, 48 × 5 | (384, 560) | boss=(376, 280), objectif=(376, 136) |
| 11 | `fsm1_fin_sables_mouvants` | Fin Sables mouvants (fosse du désert) | `EQS1` | 768 × 576 | 10 | 12 × 10, 24 × 5 | (376, 560) | boss=(384, 440), objectif=(352, 160) |
| 12 | `fst1_fin_star_cave` | Fin Star Cave (alcôve de cristal) | `ESC1` | 768 × 576 | 9 | 24 × 5 | (384, 560) | boss=(384, 320), objectif=(384, 152) |
| 13 | `fct2_fin_clairiere_tropicale` | Fin Clairière tropicale (autel du lagon) | `ETC1` | 768 × 576 | 14 | 24 × 5 | (384, 560) | boss=(376, 288), objectif=(376, 168) |
| 14 | `fcv3_fin_couloir_violet` | Fin Couloir violet (monolithe rocheux) | `ECV1` | 768 × 576 | 11 | 24 × 5 | (392, 560) | boss=(384, 312), objectif=(376, 120) |
| 15 | `fmt3_fin_mt_thunder` | Fin Mt. Thunder (sommet d'orage) | `EMT1` | 768 × 576 | 11 | 48 × 5 | (384, 560) | boss=(376, 192), objectif=(376, 128) |
| 16 | `fjs4_fin_jardin_secret` | Fin Jardin secret V2 (stèle de Celebi) | `EJS1 / EJS2` | 768 × 576 | 16 | 24 × 5 | (384, 560) | boss=(376, 280), objectif=(376, 128) |
| 17 | `ffb1_fin_foret_brumeuse` | Fin Forêt brumeuse (stèle moussue) | `EFB1` | 768 × 576 | 14 | 4 × 10, 48 × 5 | (384, 560) | boss=(376, 312), objectif=(376, 200) |

Les 17 cartes sont toutes au format 4:3 vaste 768 × 576 px (96 × 72 cases de 8 px) et possèdent un calque Top vide (`Layer=4`) en dernier.

## Limites

- Terrains générés à partir des captures des jeux (rendu généré référencé) ; seuls les scintillements Métano sont des tuiles natives.
- Les animations sont créées pour ces cartes : ce ne sont pas les animations officielles.
- Collisions et marqueurs vérifiés sur la grille, pas en jeu (`art_approved: false`, `runtime_tested: false`).
