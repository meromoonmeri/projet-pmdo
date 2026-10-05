# ZGT1 — Village arboricole de guilde

Carte PMDO 0.8.12, 768×576 px (96×72 cases de 8×8). Composition V1 approuvée par l'utilisateur le 4 octobre 2026; les corrections demandées sont conservées pour V2.

- Aperçu : `../../apercu_zone_guilde_treehouse_v1.html`
- Projet Ground/Tile directement inspectable : `PMDO_project/`
- Mod PMDO : `ZGT1_PMDO_0812.zip`
- Calques PNG et animation d'eau : `layers/` et `anim/`
- Projet éditable : `ZGT1_layers.ora`

Les pixels de `bruts/decor_magenta.png` et `bruts/sol_complet.png` sont des rendus générés. Ils ne sont pas présentés comme des extractions de tuiles de la ROM. La scène non aquatique est quantifiée sur les 134 couleurs de la référence T00P01. Le canal magenta sert de masque; les 11 motifs de tuiles d'eau 8×8 sont des échantillons directs du canal canonique T00P01, réassemblés dans une forme nouvelle. Les 36 phases à FrameLength=2 reproduisent la boucle BPL/BPA de 72 ticks.

Les calques séparent le résiduel de sol généré, les détails, les zones bâties, la canopée et l'eau. Les surfaces de sol générées ne sont pas des sprites natifs découpés. Collisions et repères sont des propositions d'édition; il n'y a ni warp, ni personnage, ni test d'exécution PMDO.

Reconstruction : `.venv/bin/python source/zone_guilde_treehouse_v1/build.py`; tests : `.venv/bin/python -m unittest source.zone_guilde_treehouse_v1.test_build -v`.
