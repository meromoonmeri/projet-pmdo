# Fin Lac Cristallin — Sanctuaire Zone Zéro & Rune Pulsante 4:3 (FLC1, PMDO 0.8.12)

Fin de donjon / Sanctuaire & Arène de boss au format **4:3 vaste** (`768 x 576 px`, `96 x 72` cases de 8 px), construite à partir du rip canonique `lakecrystalpmdsky.png` (`D17P34A`, *Crystal Lake / Crystal Crossing*, PMD Explorers of Sky) avec :
- **Signes gravés sur la rune du monolithe animés (`runes_pulse`)** : les glyphes gravés sur le monolithe central du sanctuaire nord s'animent et pulsent d'une lumière magnifique et subtile (saphir-améthyste -> cyan astral -> rose-aurore nacré -> or céleste et cœur diamant + halo doux tramé, `24 x 10 ticks = 240 ticks`) ;
- **Cristaux Zone Zéro (*Area Zero*, Pokémon Écarlate et Violet)** : base en cristal blanc nacré / opale / quartz-améthyste (`CRISTAL_TONS`) et reflets irisés arc-en-ciel Téra animés (`reflets_tera`, `24 x 10 ticks = 240 ticks`) ;
- **Eau abyssale et effet reflet de profondeur (`reflet_profondeur`)** : dégradé de profondeur en 5 paliers sans aucun liseré clair aux rives et reflet vertical immergé des cristaux plongeant dans l'eau (`24 x 10 ticks = 240 ticks`).

## Calques (15 calques : 8 fixes + 7 animés, boucle de 240 ticks = 4 s)
1. `00 eau` — 4 phases x 10 ticks (dégradé abyssal en 5 paliers + onde de rive sans liseré clair)
2. `01 reflet_profondeur` — 24 phases x 10 ticks (reflet vertical immergé des cristaux dans la profondeur de l'eau)
3. `02 scintillements` — 4 phases x 10 ticks (`Metano_Town_River_Sparkles` natifs)
4. `03 gouttes` — 24 phases x 5 ticks (gouttes cristallines et ronds d'eau)
5. `04 sol_complet` — fixe (fond de dalles nacrées sous toute la plateforme)
6. `05 dalles` — fixe (arène et parvis praticables)
7. `06 reflets` — fixe (motifs géométriques nacrés sur les dalles)
8. `07 rebords` — fixe (margelles biseautées du plateau)
9. `08 cristaux` — fixe (amas de pointes de quartz-améthyste)
10. `09 ilots` — fixe (îlots et piliers émergeant du lac)
11. `10 piliers` — fixe (couronne nord fermée de grands piliers hexagonaux blancs nacrés)
12. `11 sanctuaire` — fixe (monolithe-rune central et estrade sacrée au nord — aucun trou noir)
13. `12 reflets_tera` — 24 phases x 10 ticks (reflets irisés arc-en-ciel Téra sur les cristaux)
14. `13 runes_pulse` — 24 phases x 10 ticks (pulsation lumineuse subtile des signes gravés sur le monolithe-rune)
15. `14 eclats` — 48 phases x 5 ticks (éclats prismatiques flottants)

## Installation
```bash
python3 INSTALLER.py /chemin/vers/PMDO
```
Nom de la carte dans l'éditeur PMDO : **`flc1_fin_lac_cristal`**.
