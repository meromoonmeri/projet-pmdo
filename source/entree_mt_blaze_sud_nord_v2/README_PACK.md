# Entrée Mt. Blaze (EMB2) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `entree_mt_blaze_sud_nord_v2`. Il contient le Ground `emb2_entree_mt_blaze_sud_nord_v2` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`).

C'est l'entrée de donjon du volcan, inspirée de `Rescue_Team_-_Mt._Blaze_Entrance.png` (GBA). Rendu généré référencé avec les textures canoniques : lave = magenta plat pour segmentation, base = sable/roche.

## Méthode

- **Décor** : rendu généré référencé avec le rip en `images=` (lave en magenta #FF00FF)
- **Sol complet** : édité depuis le décor (sable seul, 0,0)
- **Base** (sable, ombres, berge, roche, piliers, profondeur) : segmentation pleine résolution → down_class 8px (moyenne pondérée par classe), palette commune quantifiée
- **Lave** : magma visqueux procédural — bruit de Worley périodique (cellules 24px, période 192×96), dérive lente plein sud (1 période par boucle), pliage, gonflement et croûte sombre ; rampe de 13 tons Mt Blaze (croûte 3 + lave 10, du rouge sombre au jaune vif), pixels calculés, 32 phases × 15 ticks — **animation palette cycling frame par frame, cohérente à la texture du rip**
- **Veines** : fissures orange dans la roche extraites du décor + fissures Worley fines (cell 18) pour garantir la densité ; même rampe, 32 phases × 15 ticks, palette cycling (distance au bord + Worley + heave sinus)

Boucle : **480 ticks = 8 s** (32×15). Aucun warp.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Lave visqueuse (Worley, palette Mt Blaze) | 32 × 15 ticks |
| 01 | Sol complet (sable) | fixe |
| 02 | Sable praticable | fixe |
| 03 | Ombres au pied des parois | fixe |
| 04 | Berge de lave | fixe |
| 05 | Parois rocheuses grises | fixe |
| 06 | Rochers et piliers | fixe |
| 07 | Profondeur (bouche sombre) | fixe |
| 08 | Veines de lave dans la roche (palette cycling) | 32 × 15 ticks |
| 09 | Vide, `Layer=4` (Top) | — |

## Marqueurs et collisions

- **Marqueurs** : `entrance` au sud, `boss` au centre de la clairière, `objectif` devant la grotte au nord. Aucun warp.
- **Collisions** : seul le sable (ombres comprises) est praticable ; lave, berge, parois, piliers et bouche sont bloqués. Chemins 16×16 vérifiés entrance→boss et entrance→objectif.

## Limites

- Terrain et lave : dessins générés à partir du rip ; ce ne sont pas des tuiles natives.
- Lave et veines : modules `source/magma_visqueux/magma.py` adapté palette Mt Blaze ; textures procédurales cohérentes au rip, animées par palette cycling + dérive visqueuse.
