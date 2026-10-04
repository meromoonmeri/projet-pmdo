# ZGT2 — Village arboricole de guilde, version révisée

**ZGT1 reste la composition de référence validée** et n'est pas écrasée. ZGT2 conserve ce layout et applique les corrections demandées : chemin continu jusqu'à la maison droite, retrait des quatre panneaux, bâtiment droit en calque isolé, PNG transparent jour/nuit, atlas 8px et projet PMDO multicalque.

## Livrables

- `renders/zone_guilde_treehouse_v2/ZGT2_scene_t000.png` : aperçu révisé.
- `renders/zone_guilde_treehouse_v2/ZGT2_layers.ora` et `layers/` : calques séparés (sol généré résiduel, sol canonique, eau, détails, bâtiments, maison droite, canopée, raccords/panneaux).
- `renders/zone_guilde_treehouse_v2/ZGT2_PMDO_0812.zip` et `PMDO_project/` : projet de terrain d'édition PMDO 0.8.12, non testé dans le moteur.
- `sprites/` : QG treehouse transparent, petite maison de jour et variante de nuit.
- `tilesheets/ZGT2_structures_sans_fond_8px.png` + `.tsx` : atlas transparent 8px pour Tiled/pose manuelle; aperçu annoté distinct.
- `tilesheets/ZGT2_T00P01_textures_8px.png` + `.json` : planche des textures 8×8 et coordonnées source; `ZGT2_terrain_source_tiles.npz` trace l'échantillonnage par case.
- `ZGT2_collision_walkability.png`, manifeste et aperçu interactif.

## Provenance texture et animation

Les pixels des surfaces de sol retouchées, le raccord vers la maison et les corrections de panneaux sont des échantillons 8×8 exacts du rendu canonique `T00P01_canonique.png`; l'eau utilise l'atlas canonique T00P01. Ce sont des pixels issus du rendu de référence, pas des indices BPC prétendument extraits. Le reste du décor, les bâtiments et la canopée restent des pixels générés et quantifiés sur la palette T00P01.

`town_map.gif` n'est pas accessible dans le workspace et doit encore être réattaché. Son extraction d'images d'herbe/eau ne fait donc pas partie de ce livrable; aucune animation n'est attribuée à ce GIF. L'eau de ZGT2 a son cycle T00P01 (36 frames de 2 ticks); la végétation est statique jusqu'à réception du fichier.

## Sprites

Le QG treehouse transparent réutilise l'objet isolé du lot `exports/guild_structures_v1`. Le grand QG central de ZGT1 est fusionné visuellement avec sa canopée; le sprite fourni est un asset treehouse autonome réutilisable, **pas** un détourage exact de cette masse fusionnée. La petite maison de droite est détourée manuellement du rendu ZGT1; son porche reste sur la carte, tandis que son PNG transparent ne garde que le bâtiment. La variante nuit emploie provisoirement le filtre `source/cote_v4_abyss/night.py`, sans changer l'alpha; c'est un prototype, pas un choix de style validé par l'utilisateur.

## État

ZGT1 conserve `art_approved: true` pour la composition présentée. ZGT2 est une révision de travail, `art_approved: false`, `runtime_tested: false`. Les collisions restent approximatives; vérifier la composition ZGT2, le détourage et les collisions dans PMDO avant publication.

Reconstruction : `.venv/bin/python source/zone_guilde_treehouse_v2/build.py`
Tests : `.venv/bin/python -m unittest source.zone_guilde_treehouse_v2.test_build -v`
