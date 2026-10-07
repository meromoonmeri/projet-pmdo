# Note de reprise — PVC1, Passage des Veines Cristallines

Date : 7 octobre 2026 · branche de session : `arena/f4987da6-projet-pmdo` · base héritée `50995264` (CPL1).

## Décision et référence

L'utilisateur a demandé de poursuivre la série et a délégué le choix du thème. Le candidat D14P11A (« Bassins du Vent ») a été écarté pour ce lot; choix final : D17P33A, passage cristallin, afin de varier après CPL1. `PVC1` est un identifiant local, pas un code MAP_BG du jeu.

Rip extrait de `pret/pmd-sky` (`c8073235b39746a7ee74e6cea16c730bd91a1e67`) via `source/outil_maps_pmdsky/recuperer_maps.py rom --only D17P33A` et skytemple-files. Référence : 456×504 px, 96 couleurs, 12 frames, 2 couches, pas de collision intégrée ni d'animation de palette. Le PNG/WebP rendu ROM et le GIF galerie correspondent pixel à pixel sur les 12 frames.

Cadence ROM lue dans les BPA : slot 1, 6 frames × 10 ticks; slot 5, 4 frames × 10 ticks; PPCM 12 phases × 10 ticks = 120 ticks (≈2 s à 60 ticks/s). Les métadonnées d'affichage du GIF (160 ms) et du WebP (167 ms) ne sont pas utilisées comme cadence de jeu.

## Composition et ressources

Deux guides générés avec le rip fourni en référence : `source/passage_veines_cristal_v1/bruts/decor_magenta.png` et `sol_complet.png`, tous deux 1200×896. Segmentation pleine résolution, réduction uniforme ×576/896 (771×576) puis recadrage 1 px à gauche / 2 px à droite pour 768×576. Calques de sol, bordure, alcôve, cristaux et veine; animations visuelles générées à 6×10 et 4×10 ticks. Les couleurs opaques sont quantifiées sur la palette exacte de 96 couleurs du rip. **Aucun pixel de texture natif n'est copié**; formes, textures et effets restent générés.

Sources/build/tests : `source/passage_veines_cristal_v1/`. Sorties : `renders/passage_veines_cristal_v1/`. Aperçu : `apercu_passage_veines_cristal_v1.html`. Ground PMDO 0.8.12, 768×576, grille 96×72, cinq calques visuels statiques, deux animés et Top vide. Collision calculée avec 4 227 cases bloquées et 2 685 libres; chemin 16×16 nord-sud connecté. Marqueurs `entrance`/`sortie` provisoires, destinations/warps non reliés.

## Contrôles et sommes

Commande de test :

```sh
.venv/bin/python -m unittest source.passage_veines_cristal_v1.test_build -v
```

**7 tests PASS** : extraction/rip, frames GIF/WebP, palette, dimensions, ORA et calques, animations Ground 6/4×10 ticks, route/collisions, `.rsground`, banques `.tile`, index et limites.

- `PVC1_projet_pmdo_0812.zip` — 790 257 octets — SHA-256 `ee7e0fe24128b3bbf3906e053ba372150c6fffcf5ace581823c8fb6e79904631`
- `PVC1_calques_png_8px.zip` — 6 250 510 octets — SHA-256 `a462576b2de92a3b24c3ec3121d0a5f038f37192954a47c9f7863951c326b24b`
- Sommes complètes : `SHA256SUMS.json`.

Drive privé vérifié avant dépôt : le dossier `PMDO — Cartes et mémoire Arena` contenait les 7 artefacts CPL1, sans fichier PVC1/D17 correspondant. Après dépôt, il contient 16 fichiers (7 CPL1 + 9 PVC1 : deux packs, rip PNG/WebP, aperçu HTML, scène t000, manifeste, sommes et note); aucun doublon ni partage public ajouté.

## Limites

Aucun test runtime PMDO, rendu GPU, test gameplay ou approbation artistique. Les collisions, l'occlusion et les marqueurs doivent être revus dans l'éditeur; les destinations de warp ne sont pas définies. `runtime_tested`, `gpu_tested` et `art_approved` restent `false`.
