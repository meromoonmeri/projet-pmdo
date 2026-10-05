# Zone Lac Cristallin — Carrefour Zone Zéro 4:3 (ZLC1, PMDO 0.8.12)

Zone d'exploration / Carrefour & Belvédères sud <-> nord au format **4:3 vaste** (`768 x 576 px`, `96 x 72` cases de 8 px), construite à partir du rip canonique `lakecrystalpmdsky.png` (`D17P34A`, *Crystal Lake / Crystal Crossing*, PMD Explorers of Sky) avec :
- **Cristaux Zone Zéro (*Area Zero*, Pokémon Écarlate et Violet)** : base en cristal blanc nacré / opale / quartz-améthyste (`CRISTAL_TONS`) et reflets irisés arc-en-ciel Téra animés (`reflets_tera`, `24 x 10 ticks = 240 ticks`) ;
- **Eau abyssale et effet reflet de profondeur (`reflet_profondeur`)** : dégradé de profondeur en 5 paliers sans aucun liseré clair aux rives et reflet vertical immergé des cristaux plongeant dans l'eau (`24 x 10 ticks = 240 ticks`).

## Calques (13 calques : 7 fixes + 6 animés, boucle de 240 ticks = 4 s)
1. `00 eau` — 4 phases x 10 ticks (dégradé abyssal en 5 paliers + onde de rive sans liseré clair)
2. `01 reflet_profondeur` — 24 phases x 10 ticks (reflet vertical immergé des cristaux dans la profondeur de l'eau)
3. `02 scintillements` — 4 phases x 10 ticks (`Metano_Town_River_Sparkles` natifs)
4. `03 gouttes` — 24 phases x 5 ticks (gouttes cristallines et ronds d'eau)
5. `04 sol_complet` — fixe (fond de dalles nacrées sous toute la plateforme)
6. `05 dalles` — fixe (chaussée et esplanade centrale praticables)
7. `06 reflets` — fixe (motifs géométriques nacrés sur les dalles)
8. `07 rebords` — fixe (margelles biseautées du plateau)
9. `08 cristaux` — fixe (amas de pointes de quartz-améthyste)
10. `09 ilots` — fixe (îlots et piliers émergeant du lac)
11. `10 piliers` — fixe (colonnes et piédestaux des belvédères latéraux)
12. `11 reflets_tera` — 24 phases x 10 ticks (reflets irisés arc-en-ciel Téra sur les cristaux)
13. `12 eclats` — 48 phases x 5 ticks (éclats prismatiques flottants)

## Installation
```bash
python3 INSTALLER.py /chemin/vers/PMDO
```
Nom de la carte dans l'éditeur PMDO : **`zlc1_zone_lac_cristal`**.
