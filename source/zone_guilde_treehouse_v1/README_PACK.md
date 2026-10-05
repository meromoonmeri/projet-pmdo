# ZGT1 — Village arboricole de guilde

Carte PMDO de travail inspirée visuellement de `T00P01`. L'utilisateur a validé la composition V1 le 4 octobre 2026; cette validation porte sur le layout présenté, pas sur un test moteur. La maison droite déconnectée et les panneaux sont des corrections demandées pour V2. Les pixels de la scène ne sont pas présentés comme des textures extraites du jeu.

## Référence et provenance

- `reference/T00P01_canonique.png` : rendu canonique T00P01, 960×720, SHA-256 `e1f0330b23ceb1767bcd82beab557b1c7f06ebd00ffc11f9ef129f50ad577496`.
- `bruts/decor_magenta.png` et `bruts/sol_complet.png` : images générées pour ce prototype, chacune en 1200×896. Le canal magenta du premier sert de masque d'eau. Les deux bruts ne sont pas parfaitement alignés; `sol_complet` reste un support de référence masqué.
- `reference/T00P01_eau_atlas.npz` : petit atlas dérivé directement des pixels du canal T00P01, échantillonnés en tuiles 8×8. Source ROM de la décompilation `pret/pmd-sky`, commit `c8073235b39746a7ee74e6cea16c730bd91a1e67`; les empreintes des fichiers BMA/BPC/BPL/BPA sont dans le JSON adjacent.
- La scène générée est réduite à 768×576 puis quantifiée sur les 134 couleurs de T00P01. La distance RGB moyenne avant quantification est un indicateur de palette, pas une mesure d'identité de layout.

## Construction et exports

```bash
.venv/bin/python source/zone_guilde_treehouse_v1/build.py
.venv/bin/python -m unittest source.zone_guilde_treehouse_v1.test_build -v
```

Pour régénérer l'atlas depuis la décompilation locale, préparer `T00P01` avec `source/outil_maps_pmdsky/recuperer_maps.py rom --only T00P01`, puis lancer `extract_water_atlas.py`. La construction standard utilise l'atlas versionné et n'a pas besoin de relire ces fichiers ROM.

- Carte finale : 768×576 px, 96×72 cellules de 8×8, format 4:3.
- Calques PNG RGBA séparés : sol résiduel généré, eau T00P01, détails/végétation basse, zones d'habitations/pont, canopée; le masque d'eau est remplacé par de vrais échantillons de tuiles source.
- L'eau est portée sur une boucle de 72 ticks : 36 états à `FrameLength=2`, combinant les phases BPL (6×4 ticks) et BPA (6×6 ticks) de T00P01. La cadence et les couleurs source sont reprises; la composition géométrique du canal est nouvelle.
- Sorties : scène PNG, aperçu HTML avec contrôle des calques/collisions, WebP d'eau, ORA éditable, manifeste, collisions approximatives, marqueurs d'édition et projet/ZIP Ground+Tile PMDO 0.8.12.
- Marqueurs provisoires : entrée sud, place centrale, maison de guilde, pont est. Aucun warp, personnage, événement ou gameplay n'est configuré.

## Limites

`art_approved: true` concerne uniquement la composition V1 montrée; `runtime_tested: false` reste inchangé. Les plans décoratifs sont une segmentation de travail de l'image générée, pas un détourage certifié d'objets natifs; les collisions sont des blocs approximatifs. Aucun test d'exécution dans PMDO n'a été effectué. La V2 doit relier la maison droite au chemin, retirer les panneaux et livrer les sprites séparés avant nouvelle revue.
