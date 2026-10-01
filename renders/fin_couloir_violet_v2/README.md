# FCO2 — Fin Couloir violet V2 : arène de rochers et feux follets (4:3, PMDO 0.8.12)

Version 2 de la fin du Couloir violet, demandée le 1er octobre : « rajoute de feu folet dans cette salle améliore la ». **FCO1 est conservée** (`renders/fin_couloir_violet_v1/`). Biome et portée restent choisis par l'agent, **à confirmer**.

- **Préfixe** : FCO2 (FCO1 = version sans feux follets). Namespace du lot : `fin_couloir_violet_v2`, Ground `fco2_fin_couloir_violet`.
- **Même base que FCO1** : décor, segmentation, collisions, éboulis et poussière sont repris de FCO1 (le décor est copié octet pour octet, sans nouvelle génération). Référence : `large.S05P03A.png.301f7a1eadda348357be0801e81faa2a.png`. C'est un **rendu généré référencé**, pas des tuiles natives.
- **Ajouts** :
  - **Feux follets** (calque animé, 24 × 5 ticks) : cinq flammes, trois bleu glace et deux violettes, qui dérivent dans l'arène en un huit fermé sur 24 phases et vacillent (12 poses par couleur, deux vacillements par boucle). Dessin généré (planche `source/fin_couloir_violet_v2/bruts/feux_follets_poses.png`, une seule génération ; la grille n'a pas été respectée, les fenêtres ont été mesurées ; 12 couleurs ; réduction au tiers). Les vols restent au-dessus du sol de l'arène, jamais dans le vide ni sur la falaise.
  - **Lueur** (calque animé, 24 × 5 ticks) : le sol et les rochers proches de chaque feu s'éclaircissent. Comme les calques n'ont pas d'alpha intermédiaire, chaque pixel éclairé prend la couleur **exacte du rip**, 1 cran (halo), 2 (milieu) ou 3 (cœur) plus claire dans la rampe du sol ou des rochers, et toujours plus claire que le pixel d'origine. Le rayon pulse de ± 3 px.
- **Calques** (13 dans le Ground, dont un Top vide) : sol complet, sol, ombres, gravillons, blocs, rochers, falaise, vide, éboulis, poussière, **lueur**, **feux follets**. Boucle de scène : 120 ticks. Aucun calque translucide.
- **Fidélité au rip** (distance RVB moyenne, seuil 35) : identique à FCO1 pour le terrain, sol 14,1, rochers 13,6, blocs 20,8. Les couleurs de la lueur sont exactement celles du rip. Les feux follets sont du dessin généré et ne sont pas comparés au rip.
- **Accès** : marqueurs `entrance` (sud), `boss` (centre de l'arène) et `objectif` (pied de la pile du nord) dans `manifest.json`. Aucun warp. Chemins 16 × 16 vérifiés. Les feux follets n'ont pas de collision.
- **Tests** : `.venv/bin/python -m unittest source.fin_couloir_violet_v2.test_build -v` (14 PASS : les 12 de FCO1 adaptés, plus `test_feux_follets` et `test_lueur`). Mutations vérifiées : un feu placé dans la paroi, une lueur qui assombrit, un vacillement qui ne boucle pas, une lueur démesurée qui déborde dans le vide.
- **Paquets** : `FCO2_projet_pmdo_0812.zip`, `FCO2_calques_png_8px.zip`, aperçu `apercu_fin_couloir_violet_v2.html` à la racine.

Limites : `runtime_tested: false`, `art_approved: false`. Les feux follets sont décoratifs : ni PNJ, ni danger, ni lumière dynamique du moteur. La trajectoire, le vacillement et la lueur sont créés par nous, pas des animations officielles. Collisions et gameplay ne sont pas déduits des contrôles d'images.
