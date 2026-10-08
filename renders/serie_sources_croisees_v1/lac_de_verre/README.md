# Lac de Verre — variante légère du Ground Sky D52P11A

Ground PMDO 0.8.12, **4:3 : 768 × 576 px**, grille **96 × 72 cases de 8 px** (`TexSize=1`). Le décor part du Ground réel Sky `D52P11A` (code de preview; aucun nom canonique supplémentaire n’est affirmé). Le layout d’origine est conservé; seule une petite zone centrale d’eau est ajoutée depuis le rendu Red `T01P02A`. **Aucun fond magenta et aucun décor généré.**

## Installer

Copier `lac_de_verre_sud_nord` dans `PMDO/MODS/`, activer le mod et ouvrir le Ground. Pour intégrer le Ground à un mod existant :

```bash
python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run
```

Vérifier le résumé, puis relancer sans `--dry-run`. L’installateur fusionne l’index des `.tile` au lieu de remplacer celui du mod cible.

Le projet reste une base d’édition : **aucun warp n’est raccordé**, aucun personnage ni spawn n’est inclus. `entrance` et `donjon_seuil` doivent être reliés au parcours voulu.

## Calques (bas → haut)

| # | Calque | Animation | Origine |
|---:|---|---|---|
| 00 | Zone glacée D52P11A | fixe | Ground natif et tileset Sky décodés, puis adaptés au gabarit 4:3 sans étirement |
| 01 | Eau du lac T01P02A | 6 frames × 10 ticks (1 s; 3 états distincts après export) | Recadrages des six rendus Red, dans un masque ovale distinct |
| 02 | Avant-plan / Top | — | Calque PMDO vide (`Layer=4`) |

## Provenance et adaptations

- Base native : [PMD-SKY-PMDO-PORT — D52P11A](https://github.com/meromoonmeri/PMD-SKY-PMDO-PORT/tree/d62110a00269bdc861b8fe41b077607a80f50978/output), Ground `.rsground` et `.tile`. Le rendu décodé par Python correspond pixel pour pixel au PNG Sky de référence.
- Eau : [PMD-RED-PMDO-PORT — T01P02A / Whiscash Pond](https://github.com/meromoonmeri/PMD-RED-PMDO-PORT/tree/680fb85efacbde40473ef3f09dde2c0152e96f6c/PMDRed_PMDO_Framework/output/Visual_Renders). Le patch 64 × 32 px est prélevé dans les frames 0–5 et agrandi uniformément. Il provient des **rendus visuels Red**, pas de sa banque `.tile`.
- La zone Sky native mesure **504 × 408 px** (63 × 51 cases). Pour obtenir un canvas 4:3 sans étirer, 2 cases sont réfléchies à gauche et 3 à droite, soit 544 × 408 px. Le brut est préparé en **1200 × 896 px**; le masque et l’eau restent séparés.
- Réduction de chaque calque à facteur uniforme `576/896`, BOX, largeur intermédiaire 771 px puis crop centré de 1 px à gauche et 2 px à droite : **768 × 576 px**.
- Palette partagée de **96 couleurs** : RGB des textures effectivement utilisées conservés; compléments exacts échantillonnés dans les mêmes références, sans tramage.
- Les collisions Sky sont reprises puis complétées par le masque d’eau. Le passage d’une empreinte 16 × 16 px est vérifié sur grille de gauche à droite, mais pas dans le moteur PMDO.

**Limite de provenance :** la base vient d’un Ground PMD réel et le bassin reprend des pixels du rendu Red. La mise à l’échelle, le masque et la recompilation créent toutefois de nouvelles banques LGV1. Les nouvelles banques ne sont pas les `.tile` originaux; aucune certification native n’est revendiquée. `art_approved`, `native_texture_certified` et `runtime_tested` restent faux.

## Livrables et reproduction

Les sources, hashes et adaptations sont dans `manifest.json` et `palette_reference.json`. Les PNG de calque indépendants et le document OpenRaster sont inclus dans l’archive de calques.

Depuis la racine du dépôt :

```bash
.venv/bin/python source/serie_sources_croisees_v1/lac_de_verre/build.py
.venv/bin/python -m unittest source.serie_sources_croisees_v1.lac_de_verre.test_build -v
.venv/bin/python source/serie_sources_croisees_v1/lac_de_verre/package.py
```

Dépendances : Pillow, NumPy et SciPy (voir `source/requirements.txt`).
