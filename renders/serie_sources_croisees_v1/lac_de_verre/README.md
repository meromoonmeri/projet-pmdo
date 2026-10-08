# Lac de Verre — carte pilote, série PMD Red × Sky (4:3)

Ground d’édition pour PMDO 0.8.12, format **4:3 vaste : 768 × 576 px**, grille de **96 × 72 cases de 8 px** (`TexSize=1`). Le layout — lac intérieur, anneau de marche et arche nord — est nouveau.

## Installer

Copier le dossier `lac_de_verre_sud_nord` dans `PMDO/MODS/`, activer le mod et ouvrir le Ground. Pour intégrer le Ground à un mod existant : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, vérifier le résumé, puis relancer sans `--dry-run`. L’installateur fusionne l’index des `.tile` au lieu de remplacer celui du mod cible.

Le projet est une base d’édition : **aucun warp n’est raccordé**, aucun personnage ni spawn n’est inclus. `donjon_seuil` doit être relié au donjon voulu.

## Calques (bas → haut)

| # | Calque | Animation | Origine |
|---:|---|---|---|
| 00 | Eau du lac | 4 phases × 10 ticks (≈0,67 s) | Texture procédurale en couleurs échantillonnées sur le rendu Red T01P02A |
| 01 | Sol givré | fixe | `sol_complet.png`, rendu généré |
| 02 | Chemin givré | fixe | segmentation du brut de sol |
| 03 | Parois givrées | fixe | segmentation du brut décor par luminance/chroma et voisinage des rives |
| 04 | Cristaux | fixe | segmentation des accents cyan |
| 05 | Arche nord | fixe | segmentation de la zone d’entrée |
| 06 | Avant-plan / Top | — | calque vide (`Layer=4`) |

## Méthode et provenance

- **Échantillonnage-génération**, pas de collage ni de réutilisation de pixels natifs comme rendu final. Les références PMDO ont été fournies au générateur pour produire une nouvelle composition :
  - [PMD-RED-PMDO-PORT — T01P02A, Whiscash Pond](https://github.com/meromoonmeri/PMD-RED-PMDO-PORT/blob/680fb85efacbde40473ef3f09dde2c0152e96f6c/PMDRed_PMDO_Framework/output/Visual_Renders/T01P02A_Frame_0.png)
  - [PMD-SKY-PMDO-PORT — D52P11A preview](https://github.com/meromoonmeri/PMD-SKY-PMDO-PORT/blob/d62110a00269bdc861b8fe41b077607a80f50978/output/Previews/d52p11a.png). Le code de preview est conservé, sans lui attribuer de nom canonique non vérifié.
- Les bruts `decor_magenta.png` et `sol_complet.png` font **1200 × 896**. Le masque magenta, les matériaux et les eaux sont segmentés à cette résolution, réduits séparément par classe avec le facteur uniforme `576/896`, puis centrés en **768 × 576** : 771 × 576 intermédiaires, 1 px rogné à gauche et 2 px à droite.
- Une palette partagée de **96 couleurs** est échantillonnée sur les deux références et utilisée sans tramage pour les matières générales. Une palette distincte de **28 couleurs** sert aux cristaux, prélevée dans les RGB bleus/cyans des frames Red. L’eau utilise une rampe dédiée de couleurs bleues/cyan réellement échantillonnées dans les frames 0–5 de T01P02A; elle n’est pas rabattue dans la palette générale.
- **Les pixels du rendu sont générés et retravaillés. Ce ne sont pas des tuiles natives PMDO certifiées.** Les frames, le déplacement des reflets, les partitions de calques et les collisions sont des créations de ce lot.

Les sources, bruts, hashes et mesures figurent dans `manifest.json` et `palette_reference.json`; les PNG de calque indépendants et le document OpenRaster sont également livrés dans le ZIP de calques.

## Accès et limites

- `entrance` au sud et `donjon_seuil` au nord; un passage de personnage **16 × 16 px** est testé sur la grille, pas dans PMDO.
- Les collisions sont estimatives, déduites des masques; les faces cachées ne sont pas reconstruites.
- `art_approved`, `native_texture_certified` et `runtime_tested` restent faux. Aucun test d’exécution dans PMDO n’a été réalisé.

## Reproduction

Depuis la racine du dépôt :

```bash
.venv/bin/python source/serie_sources_croisees_v1/lac_de_verre/build.py
.venv/bin/python -m unittest source.serie_sources_croisees_v1.lac_de_verre.test_build -v
.venv/bin/python source/serie_sources_croisees_v1/lac_de_verre/package.py
```

Dépendances : Pillow, NumPy et SciPy (voir `source/requirements.txt`).
