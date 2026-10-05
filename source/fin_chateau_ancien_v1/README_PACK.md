# FAC1 — Fin Château Ancien, Salle du Trésor

Carte finale 4:3 inspirée du rip canonique `oldcastlepmd.png` (408×408). La composition oppose un grand médaillon au centre de l'arène, un accès sud, des alcôves aux coffres et un dais au nord. Le parcours contrôlé relie l'entrée au sud, le repère de boss et l'objectif devant le trésor nord.

## Construction

```bash
.venv/bin/python source/fin_chateau_ancien_v1/build.py
.venv/bin/python -m unittest source.fin_chateau_ancien_v1.test_build -v
```

- Taille : 768×576 px, 96×72 cases de 8×8 px.
- Préfixe : `FAC1` ; marqueurs : entrée sud `[384,520]`, boss `[384,280]`, objectif nord `[384,165]` ; 2 934 cases accessibles reliées par BFS.
- Calques PNG RGBA : scène complète de référence, sol, murs, ombres, ornements, coffres, statues/rails, appliques, et reflets d'or (24 images × 10 ticks).
- Rendus bruts générés à partir de `oldcastlepmd.png`, réduits de 1200×896 à 768×576. Distances RGB moyennes mesurées : sol 4,79 ; murs 4,78 ; décors 9,48 ; scène complète 5,62 (seuil <35).
- Le projet PMDO encode 10 324 tuiles sur neuf calques.
- Les reflets d'or sont calculés à partir de la palette de référence, pas extraits d'une animation native.
- Exports : PNG 8 px, ORA éditable, manifeste, aperçu, projet Ground/Tile PMDO 0.8.12 et ZIP de livraison.

## Limites de validation

Les pixels générés ne sont pas certifiés comme tuiles natives. `art_approved: false` et `runtime_tested: false` restent dans le manifeste. Les tests vérifient les dimensions, la fidélité couleur, les calques, la connectivité entrée→boss→objectif, les images animées et l'intégrité des archives ; aucun lancement dans PMDO n'a été effectué.
