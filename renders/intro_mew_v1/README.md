# IMW1 — Intro animée : Mew voyage à travers le ciel et le monde Pokémon

Cinématique 4:3 de **63,5 s** (768 × 576, 30 i/s, H.264). Mew traverse l'aube, survole **11 biomes** déjà livrés par le projet, puis s'éloigne dans le soleil doré.

> **Ce n'est pas une map PMDO ni un Ground.** C'est une vidéo générée à partir des maps existantes. `art_approved: false`, `runtime_tested: false`.

## Déroulé

| t (s) | Acte |
|---|---|
| 0 – 8 | Ouverture : aube, soleil qui se lève derrière une mer de nuages, 3 plans de nuages en parallaxe ; Mew entre par la gauche |
| 8 – 12,5 | Aube sur la prairie et la mer (ZRV2) |
| 12,5 – 17 | Clairière tropicale et rivière (ETC1) |
| 17 – 21,5 | Jungle du sud (EJN1) |
| 21,5 – 26 | Jardin secret (EJS3) |
| 26 – 30,5 | Sables mouvants (EQS1) |
| 30,5 – 35 | Grotte de la cascade (EWC3) |
| 35 – 39,5 | Mont Foudre au-dessus des nuages (EMT1) |
| 39,5 – 44 | Cratère de magma (ECM1) |
| 44 – 48,5 | Forêt de givre et aurores (FGG2) |
| 48,5 – 53 | Fonds de l'océan (FOC1) |
| 53 – 57,5 | Colonnes Lances, le sommet (CLR2) |
| 57,5 – 63,5 | Finale : soleil doré, Mew s'éloigne et rapetisse dans la lumière, fondu au noir |

Les noms de lieux sont des légendes du projet pour ses propres cartes ; rien n'affirme qu'ils correspondent à des lieux officiels.

## Comment c'est fait

- **Mew** : un seul sprite généré (`bruts/mew_a.png`). Sa grille de gros pixels (11,75 px) est retrouvée par autocorrélation, puis le sprite est ré-échantillonné à sa taille native, **66 × 58 px, 13 couleurs** (profil du projet : au plus 15). Les 8 poses viennent d'une onde calculée le long de la queue (colonnes décalées de 3 px au plus ; le reste du corps ne bouge pas) : boucle exacte de 0,8 s. Une seconde génération a été écartée (queue enroulée sur le corps, `bruts/ecartes/`).
- **Biomes** : la caméra survole la scène animée de chaque carte (fenêtre 384 × 288, rendu × 2 en pixels entiers) en avançant vers la droite. Mew porte une ombre au sol, les nuages de passage aussi.
- **Ciel** : soleil à 3 tons avec 14 rayons qui tournent par tiers, dégradé tramé en 14 bandes, nuages en dôme à 4 tons, sans liseré. Tout est procédural, **sans rip**.
- **Transitions** : un mur de nuages de 960 px traverse l'écran en 1,6 s ; la carte change à l'instant où il couvre tout.
- **Lumière du jour** : une teinte multiplicative et une lueur du soleil (mélange « écran », étagée, tramée) suivent le cycle aube, jour, couchant, nuit, aube dorée.
- Tout est **déterministe** : le même instant donne toujours le même cadre.

## Fichiers

- `IMW1_intro_mew.mp4` : la cinématique (11,5 Mo). Compression H.264 : les calques PNG font foi pour les pixels.
- `calques/` : Mew (8 poses en bande 528 × 66), nuages (`far`, `mid`, `near`), mer de nuages, mur de transition, ciels d'ouverture et de finale.
- `review/` : 15 arrêts sur image à 768 × 576.
- `manifest.json` : chronologie, cartes sources, cycle de lumière, réserves.
- Source : `source/intro_mew_v1/`. On lance `build.py` (environ une minute), puis `package.py`, qui joue d'abord les 10 tests.

## Réserves

- Mew est un sprite généré, jamais validé comme sprite SpriteCollab ni revu à la main pixel par pixel.
- Le choix des biomes et leur ordre sont à confirmer.
- Les cartes survolées gardent leurs réserves propres (rendus générés, `art_approved: false`).
