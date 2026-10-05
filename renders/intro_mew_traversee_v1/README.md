# IMW3 — Traversée (nouvelle intro dans l'esprit de Treasure Town)

Cinématique **vidéo 28 s**, 768 × 576, 30 i/s, H.264 (crf 19), dans l'esprit de l'ouverture d'*Explorers of Sky* (Treasure Town, intro) : un grand décor vertical peint parcouru de haut en bas, Mew surgit du soleil en grossissant, traverse ciel et nuages, survole le monde (mers, montagnes enneigées, désert, volcan, plateaux, forêt avec village) puis s'envole en éclat blanc.

> **Pas une carte PMDO jouable** : c'est une vidéo MP4, livrée avec ses calques sources (PNG), ses jalons PNG et son manifeste JSON. Les intros existantes **IMW1** (cinématique 63 s, 11 cartes) et **IMW2** (fond Ground animé en boucle) sont conservées telles quelles. `art_approved: false`, non testé dans PMDO.

## Déroulé (3 actes)

| Acte | t (s) | Ce qu'on voit |
|---|---|---|
| 1 — Le soleil | 0 → 9 | fondu depuis un bleu profond, étoile à 8 branches et halo qui pulsent (3,2 s), un anneau part du soleil toutes les 2 s ; Mew apparaît minuscule dans la lumière, grossit en descendant, un dernier anneau rose l'entoure à t = 7,4 s |
| 2 — La descente | 9 → 22 | la caméra parcourt le décor vertical (800 px vers le bas, courbe douce) : ciel et nuages, mer, montagnes, désert, volcan, plateaux, forêt ; Mew vole en planant vers la droite-droite et s'éloigne progressivement ; les pétales sakura tournent en deux plans |
| 3 — Le village puis l'envol | 22 → 28 | le village apparaît (maisons, place, fontaine) ; Mew accélère vers le haut à droite ; éclat blanc à t = 25,6 s, fondu de sortie au noir |

## Calques sources (dans `calques/`)

- `IMW3_fond_vertical.png` (768 × 1376) : le décor peint complet, du ciel en haut au village en bas.
- `IMW3_mew_pose_A.png`, `IMW3_mew_pose_B.png` : Mew peint, détouré du magenta (seule la queue diffère entre A et B).
- `IMW3_mew_pose_AB.png` : fondu à 50 % entre A et B (montre le mouvement de la queue).
- `IMW3_petales_8poses_4tailles.png` : planche des pétales sakura (8 poses de retournement × 4 tailles : 12, 18, 28, 42 px).

## Effets procéduraux

- **Soleil** : halo gaussien pulsant + étoile à 8 branches qui tourne lentement.
- **Anneaux** : 5 anneaux qui s'éloignent du soleil toutes les 2 s (vie 3 s), plus un anneau rose au moment où Mew arrive au premier plan (t = 7,4 s).
- **Nuages** : voiles flous générés procéduralement, périodiques (1100 px), à parallaxe ×1,25 (ils défilent plus vite que le décor).
- **Pétales sakura** : 60 pétales en deux plans (30 petits en arrière, 30 gros devant Mew), 8 poses de retournement, vent vers la gauche avec oscillation sinusoïdale et rotation individuelle.
- **Mew** : interpolation de taille/position/rotation en courbes lisses, halo doux derrière lui, fondu de pose A↔B pour le battement de queue (période 0,9 s).
- **Vignette** légère aux bords, fondu d'entrée depuis un bleu profond, éclat blanc final.

## Origine et réserves

- La demande : « pour l'introduction faut quelque chose de ce genre » (capture de la ressource Spriters Resource « Treasure Town (Intro) », Explorers of Sky). Le fichier joint n'était plus disponible dans le bac à sable au moment du build : j'ai travaillé **d'après l'image vue dans la conversation**, sans rien mesurer ni recopier pixel par pixel. Le style est imité, pas reproduit.
- Le décor vertical et Mew ont été **générés comme peintures** puis détourés ; ce ne sont pas des rips ROM. Mew n'est pas conforme au contrat SpriteCollab (pas ≤ 15 couleurs, pas de grille native) : c'est un asset de cinématique, pas un sprite de jeu.
- La vidéo MP4 est compressée (H.264, ~5,5 Mo) ; les PNG de calques et de jalons font foi pour la fidélité.
- Déterministe : deux exécutions de `build.py` produisent la même suite d'images.

## Utilisation

`build.py` (environ 2 min 20) génère :
- `IMW3_traversee.mp4` (la vidéo) ;
- `calques/*.png` ;
- `review/IMW3_t*.png` (15 jalons : 0,5 → 27,6 s) ;
- `manifest.json`.

`package.py` lance les tests (10), écrit `README.md`, génère la page d'aperçu HTML et assemble `IMW3_traversee_pack.zip` (mp4 + calques + jalons + manifeste).

Source : `source/intro_mew_traversee_v1/`. Tests : `.venv/bin/python -m unittest source.intro_mew_traversee_v1.test_build -v`.
