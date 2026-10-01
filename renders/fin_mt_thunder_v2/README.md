# FTN1 — Fin Mt. Thunder : arène du sommet (4:3, PMDO 0.8.12)

Zone de fin de donjon qui prolonge l'entrée **EMT1** (Mt. Thunder). Portée et biome choisis avec l'utilisateur (« Poursuis le projet », 1er octobre 2026), **à confirmer**.

- **Référence** : `Game Boy Advance - Pokemon Mystery Dungeon_ Red Rescue Team - Dungeon Boss Rooms - Mt. Thunder.png` (432 × 498 ; scène y < 352, planche d'éclairs dessous), passée au générateur en image de référence. C'est un **rendu généré référencé**, pas des tuiles natives.
- **Layout** : arrivée au sud par une crête de sable (`entrance`), grande arène ronde fermée par une couronne de falaises, anneau de pics, nid de pierre plein au nord sur une corniche ; `boss` au centre, `objectif` au pied du nid. Ni sortie, ni warp, ni `donjon_seuil`.
- **Bruts** (`source/fin_mt_thunder_v2/bruts/`) : `decor.png` (1200 × 896, premier essai, conforme au format) et `sol_complet.png` (sable seul, premier essai). Le prompt évite « boss » et « cave » (leçon de FST1).
- **Calques** (11 dans le Ground, dont un Top vide) : sol complet, sable, cailloux, pics, falaise, nid, ciel, nuages, lueurs, éclairs. Boucle de scène : 240 ticks. Aucun calque translucide. Pas de calque de profondeur ni de seuil.
- **Animations** : mêmes sprites et mêmes couleurs EXACTES de la planche qu'EMT1 (éclairs 1 à 4, arc « Flash », Normal 2 phases puis Fading 2 phases). **8 frappes par boucle**, une toutes les 6 phases (6 toutes les 8 dans l'entrée) : la fin est plus orageuse. Placement, cadence et arc au pied de l'éclair créés par nous.
- **Fidélité au rip** (distance RVB moyenne par matière, seuil 35, même classifieur des deux côtés) :

| Matière | Brut | Calque final |
|---|---|---|
| sable | 2,2 | 3,2 |
| roche | 26,0 | falaise 23,5 ; **nid 52,7 (limite signalée)** |
| ciel | 5,8 | 7,7 |
| nuages sombres | 9,7 | 7,8 |
| nuages clairs | 23,7 | 24,4 |

  Le **nid** (pilier de pierre) est nettement plus sombre que les falaises du rip (135,109,87 contre 166,141,116). Layout gardé, brut non régénéré : une génération ciblée du nid est la première amélioration. Le test impose que cet écart reste entre 35 et 60 et qu'il soit déclaré dans le manifeste (`fidelite_rip.limites`).
- **Collisions** : les dessus des blocs de la couronne sont jaunes comme le sable (calque sable) mais ne se marchent pas. Le sol praticable est un **noyau** : sable + cailloux ouverts de 9 px (diamant), le plus grand morceau, réagrandi de 7 px, relié au bord sud. 1 326 cases praticables sur 6 912 ; chemins 16 × 16 de l'arrivée au boss et à l'objectif vérifiés ; la bande nord, le haut et les flancs sont des parois.
- **Segmentation** : voir `classify` dans `build.py` (seuils pleine résolution commentés). Pics : 22 ; cailloux : 54.
- **Tests** : `.venv/bin/python -m unittest source.fin_mt_thunder_v2.test_build -v` (11 PASS). 5 mutations vérifiées : pixel rouge dans le sable, boss déplacé sur une paroi, marqueur `donjon_seuil` ajouté au Ground, éclair décalé d'un pixel, masque du nid modifié.
- **Paquets** : `FTN1_projet_pmdo_0812.zip`, `FTN1_calques_png_8px.zip`, aperçu `apercu_fin_mt_thunder_v2.html` à la racine.

Limites : `runtime_tested: false`, `art_approved: false`. Collisions, occlusion et gameplay ne sont pas déduits des contrôles d'images. Pas de boss nommé. Une branche sœur a sa propre fin Mt. Thunder (FTH1) ; rien n'en est repris.
