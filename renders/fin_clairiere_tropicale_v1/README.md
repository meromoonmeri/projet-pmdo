# FTC1 — Fin Clairière tropicale : arène de jungle et lagon (4:3, PMDO 0.8.12)

Dixième zone de fin de donjon de la série, après Fin Vapeur, Cratère, Ruine, Givre, Bristle, Jungle, Waterfall Cave, Sables mouvants et Star Cave. Elle prolonge l'entrée **ETC1** (Clairière tropicale). Biome et portée choisis par l'agent, **à confirmer**.

- **Référence** : `large.S01P03A.png.84e22fb77c4061e77b0f546545fed2c7.png` (456 × 456), passée au générateur avec le décor d'ETC1 en images de référence. C'est un **rendu généré référencé**, pas des tuiles natives.
- **Layout** : arrivée au sud par une piste de dalles (`entrance`) à travers la jungle, grande arène d'herbe ceinte de jungle, de palmiers et d'hibiscus, anneau de dalles au centre ; lagon au nord avec une falaise de terre et une estrade de pierre à marches. `boss` au centre de l'arène, `objectif` sur l'estrade. Ni sortie ni warp.
- **Bruts** (`source/fin_clairiere_tropicale_v1/bruts/`) : `decor_magenta.png` (1200 × 896, mer en magenta pur), `temoin_sans_objets.png` et `sol_complet.png` (édités depuis le décor), `papillons_poses.png` (planche d'ETC1 réutilisée sans nouvelle génération). Le premier décor est gardé dans `ecartes/` pour la traçabilité, jamais lu par le build.
- **Décor écarté** : jungle trop sombre. Elle était à 33,6 du rip sur le brut, mais le calque final montait à 35,1–35,4 après réduction, au-dessus du seuil 35. Le décor a été édité (jungle plus claire, même disposition) : 24,1 sur le brut, **28,9** sur le calque final. Un premier `sol_complet` (motif de buissons répétés, non recalé, écart 20,6) a aussi été refait.
- **Calques** (12 dans le Ground, dont un Top vide) : sol complet, herbe, dalles, touffes, fleurs, jungle, palmiers, estrade, rive, mer, papillons. Boucle de scène : 120 ticks. Aucun calque translucide. Pas de calque d'ombres (relief plat) ni de profondeur (pas de bouche sombre dans une fin).
- **Animations** : la mer reprend le profil de 48 px, la crête et les couleurs EXACTES du rip d'ETC1 ; les vagues avancent de **2 px par phase vers la rive (sud)**, la mer étant au nord. Contre la terre : uniquement la bande sombre, pas de liseré. Papillons : poses d'ETC1, vol en huit. Le mouvement est créé par nous.
- **Fidélité au rip** (distance RVB moyenne par matière, seuil 35) : herbe 22,2 (calque 21,7), jungle 24,1 (calque 28,9), dalles 15,4 (calque 15,1).
- **Segmentation** : les reflets olive de la jungle passaient pour des dalles (110 695 px en pleine résolution au lieu de 21 636 une fois le critère resserré) ; le critère des dalles a été resserré (rouge > vert + 12, lum > 165) et un test vérifie qu'aucune dalle n'est dans la jungle.
- **Accès** : 2 490 cases praticables sur 6 912 ; chemins 16 × 16 de l'arrivée au boss et à l'objectif vérifiés.
- **Recalage** du sol complet sur le décor : (0, 0), écart moyen 6,87 (décalé de 1 px : 6,93). Témoin : (0, 0), 8,65 (10,76).
- **Tests** : `.venv/bin/python -m unittest source.fin_clairiere_tropicale_v1.test_build -v` (12 PASS). 5 mutations vérifiées : sens des vagues inversé, critère des dalles relâché, boss déplacé au sud, mer rendue praticable, papillon envoyé dans la jungle.
- **Paquets** : `FTC1_projet_pmdo_0812.zip`, `FTC1_calques_png_8px.zip`, aperçu `apercu_fin_clairiere_tropicale_v1.html` à la racine.

Limites : `runtime_tested: false`, `art_approved: false`. La jungle est la matière la plus éloignée du rip (28,9 sur 35) : olive plus jaune que la capture. Les papillons sont petits (échelle d'ETC1). Collisions, occlusion et gameplay ne sont pas déduits des contrôles d'images. Pas de boss nommé.
