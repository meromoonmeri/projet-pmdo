# ZGT2 — Village arboricole de guilde (V2)

ZGT1 reste inchangée et sa composition validée est conservée. Cette V2 ajoute un chemin canonique vers la maison droite, retire les quatre panneaux, isole cette maison en calque, et livre un atlas transparent jour/nuit.

Les surfaces retouchées du sol et le raccord utilisent des échantillons 8x8 exacts du rendu canonique T00P01; l'eau reste animée à partir de son atlas canonique. Le reste de la scène est généré, puis quantifié sur la palette T00P01 : il n'est pas présenté comme extrait de la ROM.

Le GIF animé `town_map.gif` n'est pas accessible dans le workspace. La végétation animée de cette pièce jointe est en attente de réattache; le sol de cette version reste statique.

Sprites: `tilesheets/ZGT2_structures_sans_fond_8px.png` + TSX Tiled; PNG séparés dans `sprites/`. Le QG treehouse vient du lot Structures Guilde déjà isolé; la petite maison est détourée depuis ZGT1. La nuit Abyss V4 est une proposition provisoire, non validée comme style final.

Pas de runtime PMDO, art V2 à réexaminer. Reconstruction: `.venv/bin/python source/zone_guilde_treehouse_v2/build.py`; tests: `.venv/bin/python -m unittest source.zone_guilde_treehouse_v2.test_build -v`.
