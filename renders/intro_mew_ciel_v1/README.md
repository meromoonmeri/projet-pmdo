# Ciel de Mew (IMW2) — fond animé en boucle, PMDO 0.8.12

Le fond de ciel de l'intro de Mew (voir IMW1, la cinématique vidéo), au format **projet PMDO** : 768 × 576 px, soit 96 × 72 cases de 8 px, boucle de **2400 ticks (40 s)**.

> **Fond de cinématique, pas une zone de jeu** : toute la grille est bloquante et les marqueurs (`entrance`, `mew`, `soleil`) ne sont que des repères. Aucun warp. `art_approved: false`, non testé dans PMDO.

## Ce qu'on voit

Mew vole **sur place** (il flotte de 3 px et sa queue ondule) : c'est le décor qui défile derrière lui vers la gauche, donc il voyage vers la droite. Un soleil à 14 rayons tourne très lentement. Trois plans de nuages défilent à 12, 24 et 36 px/s, devant et derrière le soleil, et une mer de nuages occupe le bas de l'image. Des éclats de lumière suivent Mew.

## Calques (du bas vers le haut)

| # | Calque | Animation |
|---|---|---|
| 00 | ciel | fixe, dégradé tramé en 14 bandes |
| 01 | soleil | 12 phases × 200 ticks, rotation de 1/6 de rayon par phase, boucle exacte |
| 02 | nuages loin | 240 phases × 10 ticks, 2 px par phase (12 px/s), période 480 px |
| 03 | nuages moyens | 240 phases × 10 ticks, 4 px par phase (24 px/s), période 960 px |
| 04 | mew | 8 phases × 6 ticks (0,8 s), onde de queue et bosse |
| 05 | mer | 240 phases × 10 ticks, 6 px par phase (36 px/s), période 1440 px, devant Mew |
| 06 | eclats | 8 phases × 6 ticks, 8 émissions par cycle, vie de 1,1 s |
| 07 | Top (vide) | à vous |

Chaque cycle divise exactement la boucle de 2400 ticks.

## Origine

- **Mew** : un sprite généré (`source/intro_mew_v1/bruts/mew_a.png`), ré-échantillonné à sa grille native (66 × 58 px, 13 couleurs) puis posé en pixels × 2. Pas validé comme sprite SpriteCollab.
- Nuages, soleil, éclats et dégradé : **procéduraux**, sans référence ROM, sans liseré.
- **Limite** : les nuages lointains répètent leur motif tous les 480 px (un peu plus d'une fois et demie par écran).

## Installation

`python INSTALLER.py <dossier PMDO>`. Le script fusionne l'index des tuiles au lieu de l'écraser.

## Fichiers

`calques/`, `animation/` (une série de PNG par calque animé), `review/` (scène à t = 0, scène animée en WebP de 240 images, quatre instants), `IMW2_ciel_de_mew_calques.ora`, `manifest.json`, `IMW2_projet_pmdo_0812.zip`, `IMW2_calques_png_8px.zip`.

Source : `source/intro_mew_ciel_v1/`. On lance `build.py` (quelques minutes), puis `package.py`, qui joue d'abord les tests.
