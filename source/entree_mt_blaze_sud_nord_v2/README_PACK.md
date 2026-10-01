# Entrée Mt. Blaze (EMB2) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `entree_mt_blaze_sud_nord_v2`. Il contient le Ground `emb2_entree_mt_blaze_sud_nord_v2` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`).

C'est l'entrée de donjon du volcan, inspirée de `Rescue_Team_-_Mt._Blaze_Entrance.png` (GBA). Rendu généré référencé avec les textures canoniques : lave = magenta plat pour segmentation, base = sable/roche.

## Méthode

- **Décor** : rendu généré référencé avec le rip en `images=` (lave en magenta #FF00FF)
- **Sol complet** : édité depuis le décor (sable seul, 0,0)
- **Base** (sable, ombres, berge, roche, piliers, profondeur) : segmentation pleine résolution → down_class 8px (moyenne pondérée par classe), palette commune quantifiée
- **Lave** : **texture canonique GBA** relevée sur les planches Spriters Resource `65097.png` (Mt Blaze Dungeon Tiles, rip ToastyPK) et `221081.png` (Mt. Blaze Entrance, re-rip à palette unique). 12 tons, chacun présent tel quel dans la planche : liseré (40,32,24), croûtes (96,40,56) et (136,96,88), braise 5 tons de (152,0,0) à (216,72,16), **surface de mare à plat (216,120,40)**, rehaut (240,128,88), cœurs (240,160,0) et (240,232,0). Le calque est un rendu généré dédié (`bruts/lave_source.png`, layout strict + planche canonique en `images=`) clippé sur la silhouette de lave du layout — **aucune greffe manuelle**.
Lecture de la planche (`lave_canon.clean_look`, appliquée **à chaque phase**) : les plaques de croûte franches gardent le marron `96,40,56` (le clair `136,96,88` n'y subsiste qu'en givre sur les plaques épaisses), un liseré braise fait le tour des plaques, un halo orangé clair le suit, et **tout le reste de la mare est à plat** `216,120,40` — soit 58 % de la surface de lave, contre 23 % sur la planche elle-même (le reste y étant les rives et le canal)
- **Veines** : **calque généré dédié** (`bruts/veines_source.png`, layout strict + planche 221081 en `images=`) — le générateur a dessiné les filaments ramifiés le long des parois, des piliers et des rochers, comme dans le layout. Filtrage canonique : on ne garde que le **cœur sombre** `152,0,0` et les **filaments chauds** qui le bordent (le rendu avait recopié la croûte de lave, écartée), paquets ≥ 10 px, épaisseur médiane 2 px / 90ᵉ centile 4,5 px (planche : 2 à 5 px). Animation : **palette cycling le long de la fissure** — le rang de température monte et descend, onde verticale (2 périodes sur la hauteur) + onde du cœur vers le halo, aucun pixel ne bouge, 32 phases × 24 ticks

### Animation « super visqueuse » (2 composantes)

| Composante | Détail |
|---|---|
| Palette cycling | Deux familles tournent **sur place** par permutation cyclique : braise 5 entrées, cœurs chauds 2 entrées. La surface de mare reste **à plat** (elle ne change jamais de ton, comme sur la planche). Pas ralenti : **24 ticks par phase**, soit 12,8 s la boucle |
| Dérive visqueuse | La matière dérive lentement (pliage 0,8 px, une oscillation par boucle, amplitude **annulée au bord**) et **les plaques glissent moins vite que la mare** (second échantillonnage contracté, cisaillement collant), croûtes qui se soulèvent puis retombent, liseré chaud qui s'allume le long des plaques |
| **Frames natifs de la planche** | La planche 65097 contient sa propre animation de lave, collée **telle quelle** (aucun redessin, aucune mise à l'échelle) : **12 bulles** qui gonflent puis s'éteignent (les 8 premières frames de la bande y 551–604, en aller-retour) et **10 gouttes** accrochées à la croûte qui pendent, s'allongent puis se détachent en gouttelettes (16 frames de la bande y 635–711). Le cœur blanc incandescent (240,240,240) et la chair chaude (240,128,88) viennent de ces frames |

Les frames natifs parcourent leur séquence entière une fois par boucle (12,8 s), donc l'animation reste **super visqueuse** : une bulle met ~3,5 s à gonfler et autant à s'éteindre.

La silhouette de la couche de lave est **exactement** celle du layout à chaque phase : le pliage est annulé au bord, donc la découpe ne bouge jamais et la boucle se referme (phase 32 ≡ phase 0).

Boucle : **768 ticks = 12,8 s** (32×24). Aucun warp.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Lave canonique (palette Spriters Resource 65097 + 221081) | 32 × 20 ticks |
| 01 | Sol complet (sable) | fixe |
| 02 | Sable praticable | fixe |
| 03 | Ombres au pied des parois | fixe |
| 04 | Berge de lave | fixe |
| 05 | Parois rocheuses grises | fixe |
| 06 | Rochers et piliers | fixe |
| 07 | Profondeur (bouche sombre) | fixe |
| 08 | Veines de lave dans la roche (filaments de la planche, cycling) | 32 × 24 ticks |
| 09 | Vide, `Layer=4` (Top) | — |

## Marqueurs et collisions

- **Marqueurs** : `entrance` au sud, `boss` au centre de la clairière, `objectif` devant la grotte au nord. Aucun warp.
- **Collisions** : seul le sable (ombres comprises) est praticable ; lave, berge, parois, piliers et bouche sont bloqués. Chemins 16×16 vérifiés entrance→boss et entrance→objectif.

## Limites

- Terrain, roche, piliers et sable restent des dessins générés à partir du rip ; ce ne sont pas des tuiles natives.
- Lave : palette **canonique** (relevée sur les planches), texture issue du rendu généré référencé sur ces planches, animation `source/magma_visqueux/lave_canon.py` (palette cycling fermé + dérive visqueuse). Aucune tuile native de la planche n'est collée : la proximité vient de la palette et de la référence en `images=`.
- Veines : calque généré puis filtré sur les tons de fissure de la planche ; animation par cycling le long de la fissure. Ce sont des filaments dessinés, pas les tuiles natives de la planche.
