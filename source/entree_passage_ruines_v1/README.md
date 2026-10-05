# EPR1 — Entrée du Sentier des Ruines

Nouvelle carte 4:3 conçue depuis le rendu canonique PMD Sky `P22P01A` (408×408 RGBA, 109 couleurs). La référence guide le style et la palette ; le layout généré, les décors segmentés et les particules ne sont **pas** des tuiles ou animations natives certifiées.

## Composition et collisions

- Canevas final : **768×576 px**, soit 96×72 tuiles de 8×8.
- Composition : entrée par le sentier au sud, clairière centrale ouverte pour le boss, arche et sortie au nord. Repères (pixels) : entrée `[384,540]`, boss `[384,330]`, objectif nord `[384,140]`.
- La grille 8 px réserve le passage de l'arche et relie les trois repères par quatre-voisins : **2 136 cases marchables**. Ce contrôle prouve la connectivité du masque calculé, pas un déplacement en jeu.
- Les trois bruts de génération se trouvent dans `bruts/` : `sol_complet.png`, `fond_sans_objets.png` et `decor_magenta.png` (1200×896). `references/P22P01A.png` est la référence épinglée.

## Calques et animation

PNG alignés 768×576 dans `renders/entree_passage_ruines_v1/layers/` ; décor segmenté avec transparence, ombres semi-transparentes, sous-couches sol/murs et image complète générée. Les groupes sont : sol complet, sol, murs, ombres, ruines, végétation/rochers, stèles et débris. Une couche séparée `pollen_dore` contient **24 phases × 8 ticks**, calculées depuis des couleurs de la palette (boucle de 192 ticks, soit 3,2 s à 60 Hz), et non extraites d'une animation ROM.

`build.py` produit aussi les scènes de phase, l'animation APNG/WebP, l'aperçu de marche, un ORA éditable, le manifeste, l'aperçu HTML et deux archives à la racine :

- `mod_entree_passage_ruines_pmdo_0812.zip` : Ground et banques Tile pour PMDO 0.8.12 ;
- `livrable_entree_passage_ruines_v1.zip` : PNG, animations, ORA, manifeste et aperçu.

## Mesures et limites

La distance RGB moyenne vers la palette du rendu `P22P01A` est de **6,89** pour le sol, **5,63** pour les murs, **10,34** pour les décors et **8,26** pour la scène complète (seuil fixé à 35). Le projet PMDO contient **6 869 tuiles** réparties dans huit banques. `art_approved` et `runtime_tested` restent `false` : aucune validation artistique ni exécution dans PMDO n'est revendiquée.

## Reproduction

Depuis la racine du dépôt, avec l'environnement `.venv` du projet :

```sh
.venv/bin/python -m py_compile source/entree_passage_ruines_v1/build.py source/entree_passage_ruines_v1/test_build.py
.venv/bin/python source/entree_passage_ruines_v1/build.py
.venv/bin/python -m unittest source.entree_passage_ruines_v1.test_build -v
```

Le build n'appelle pas de générateur distant : il repart des PNG bruts versionnés et de la référence locale. Les six tests vérifient le manifeste, la fidélité, les calques, la connectivité, les 24 phases, l'ORA et les archives PMDO.
