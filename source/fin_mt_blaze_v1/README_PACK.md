# Fin Mt. Blaze (FMB1) — projet PMDO 0.8.12

Ce dossier est un projet d'édition autonome, `fin_mt_blaze`. Il contient le Ground `fmb1_fin_mt_blaze` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px.

C'est l'arène du cratère du volcan, prolonge l'entrée EMB1. Rendu généré référencé avec `images.jpg` + `Rescue_Team_-_Mt._Blaze_Entrance.png` (cratère central en magenta, plateforme centrale, chaussée).

## Méthode

- **Décor** : rendu généré référencé (lave en magenta, 1200×896)
- **Sol complet** : édité depuis le décor (sable seul)
- **Base** : segmentation + down_class 8px, palette commune
- **Lave** : magma visqueux procédural (Worley 24px, période 192×96, dérive sud, pliage/gonflement/croûte), rampe Mt Blaze 13 tons, 32×15 — palette cycling, cohérent au rip
- **Veines** : fissures dans la roche, 32×15 palette cycling

Boucle 480 ticks = 8 s. Aucun warp.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Lave visqueuse (cratère) | 32 × 15 |
| 01 | Sol complet | fixe |
| 02 | Sable | fixe |
| 03 | Ombres | fixe |
| 04 | Berge | fixe |
| 05 | Parois | fixe |
| 06 | Rochers/piliers | fixe |
| 07 | Profondeur | fixe |
| 08 | Veines | 32 × 15 |
| 09 | Vide Top | — |

## Marqueurs et collisions

- **Marqueurs** : `entrance` au sud, `boss` sur la plateforme centrale du cratère (384,232), `objectif` à côté (376,224). Chemins 16×16 vérifiés.
- **Collisions** : seul le sable praticable ; cratère, berge, parois bloqués. Causeway de 80px relie le sud au centre, plateforme 120×80 walkable.

## Limites

- Générés à partir des rips, pas de tuiles natives ; lave/veines procédurales palette cycling cohérentes à la texture du rip.
