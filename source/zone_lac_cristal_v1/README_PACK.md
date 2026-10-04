# Zone Lac Cristallin — Carrefour & Belvédères (4:3) — projet PMDO 0.8.12

Projet d'édition autonome `zone_lac_cristal`. Il contient un Ground `zlc1_zone_lac_cristal` au **format 4:3 vaste** : 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`), environ 2,4 × 2,4 écrans PMDO.

Biome choisi par l'utilisateur : **Lac Cristallin / Crystal Crossing (`lakecrystalpmdsky.png`, `D17P34A`)**, décliné en trilogie complète de 3 layouts (`ELC1` entrée, `FLC1` fin/sanctuaire, `ZLC1` zone ouverte).

## Installer

- **Projet séparé** : copier `zone_lac_cristal` dans `PMDO/MODS/`, l'activer, puis ouvrir le Ground.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis relancer sans `--dry-run`.

## Calques (bas → haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Eau du lac souterrain, façon Métano (couleurs exactes du rip `lakecrystalpmdsky.png`, sans liseré clair) | 4 × 10 ticks |
| 01 | Lueur cristalline sous-marine (9 couleurs cyan/bleu exactes du rip) | 12 × 10 ticks |
| 02 | Scintillements Métano natifs | 4 × 10 ticks |
| 03 | Gouttes cristallines et ronds dans l'eau (générés) | 24 × 5 ticks |
| 04 | Sol complet (dalles cristallines cyan) | fixe |
| 05 | Dalles cristallines de l'esplanade traversante (praticables) | fixe |
| 06 | Reflets aqua en croix sur les dalles (praticables) | fixe |
| 07 | Rebords biseautés de la plateforme | fixe |
| 08 | Cristaux sombres bleu-sarcelle en bordure | fixe |
| 09 | Îlots et piliers hexagonaux isolés dans le lac | fixe |
| 10 | Piliers d'épaule au nord et piédestaux hexagonaux des alcôves | fixe |
| 11 | Éclats prismatiques flottants (générés) | 48 × 5 ticks |
| 12 | Vide, `Layer=4` (Top) | — |

La scène complète boucle en 240 ticks (4 s).

## Marqueurs et collisions

- `entrance_sud` est au sud, `sortie_nord` est au bord nord de la chaussée cristalline ouverte. **Aucun warp.**
- Sont praticables les dalles et reflets cristallins de l'esplanade et des alcôves latérales. Un chemin libre de 16 × 16 px a été vérifié du sud au nord. **À contrôler en jeu.**
