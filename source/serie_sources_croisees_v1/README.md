# Série de cartes PMD Red × Sky — v1

Série en cours, avec un **premier pilote** : `lac_de_verre/` (préfixe `LGV1`). La portée finale (nombre de cartes et thèmes suivants) reste ouverte; les références déjà choisies pour ce pilote ne sont pas à reprendre comme paire au prochain lot.

## Méthode retenue

- Références visuelles prises dans les deux dépôts PMDO Red et PMDO Sky.
- **Échantillonnage-génération par générateur d’image**, sur plusieurs plates magenta (`decor_magenta.png`, `sol_complet.png`), puis segmentation et exports traités en Python.
- Gabarit **4:3 vaste** : bruts 1200 × 896, segmentation pleine résolution, réduction uniforme par matière avec le facteur `576/896`, recadrage centré vers **768 × 576** (96 × 72 cases de 8 px).
- Palette partagée de 96 couleurs échantillonnées, palette séparée pour les matières qui le demandent; les exports précisent l’origine générée.
- Aucun rendu n’est présenté comme un jeu de tuiles PMDO natif certifié. Chaque lot garde `art_approved: false` et `runtime_tested: false` tant que ces validations n’ont pas eu lieu.

## Pilote 01 — Lac de Verre

- Sources : Red `T01P02A` (Whiscash Pond) et Sky `D52P11A` (code de preview; aucun nom canonique affirmé).
- Sky `D04P12A` / Waterfall Cave est écartée car déjà reprise antérieurement.
- Dossier de build, bruts, références et tests : `lac_de_verre/`.
- Livrables : `renders/serie_sources_croisees_v1/lac_de_verre/` et `apercu_serie_sources_croisees_v1.html`.
- Tests du pilote : `10 PASS`; aucune validation dans le moteur PMDO.
