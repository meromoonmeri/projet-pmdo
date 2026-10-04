# BMF1 — Bosquet Mycélien : Clairière des Lanternes

Carte fongique 4:3 entièrement distincte de la série des ruines. La capture canonique de **Mushroom Forest** (*Pokémon Mystery Dungeon: Red Rescue Team*, rip Toastypk) guide les couleurs menthe, cyan, corail, crème, violet et indigo ainsi que l'échelle des champignons. La composition, les pixels et les effets sont générés ou calculés : ils ne sont **pas** présentés comme des tuiles ni comme des animations natives certifiées.

## Composition

- Canevas final : **768×576 px**, soit 96×72 cellules de 8×8.
- Entrée unique au sud, clairière à deux branches autour d'un îlot de champignons et de bois, corridor de petits champignons-lanternes, grande arche fongique fermée au nord.
- Repères : entrée `[384,552]`, clairière `[384,470]`, objectif des lanternes `[384,112]`.
- La grille compte **858 cellules marchables**, toutes accessibles depuis l'entrée ; les branches gauche et droite sont contrôlées séparément.
- Les bords nord, est et ouest sont bloqués. Aucun warp ni raccord de scénario n'est configuré.

Les trois bruts retenus sont dans `bruts/` : décor avec route magenta, sol complet sans clé et fond sans objets. `bruts/ecartes/` conserve la première édition du sol, rejetée parce qu'elle ajoutait des champignons sur la route, ainsi que la sortie de fond 1194×880 avant sa normalisation nearest vers 1200×896.

## Calques et animations

Les PNG transparents séparent le sol, la sous-couche mycélienne, les ombres, le sous-bois, les bois/racines, les champignons géants, l'arche nord, l'îlot central et le premier plan.

Deux animations calculées restent indépendantes :

- `lueurs_lanternes` — pulsation alternée des petits champignons cyan, roses et crème ;
- `spores` — particules en trajectoires fermées autour des deux branches.

Chacune compte **24 phases × 8 ticks**, soit une boucle de 192 ticks. Elles ne proviennent pas d'un cycle d'animation de la ROM.

## Exports et limites

Le builder produit les calques PNG, 24 scènes, APNG/WebP, overlay des collisions, ORA éditable, manifeste JSON, aperçu HTML et projet Ground/Tile PMDO 0.8.12. Le projet contient **13 447 tuiles** dans onze banques.

Distances RGB moyennes des bruts vers les 93 couleurs de la référence, avant quantification : sol `24,68`, sous-bois `13,85`, bois `19,08`, champignons `15,07`, scène complète `18,30`. Toutes restent sous le seuil strict de 35. Cette quantification ne transforme pas les pixels générés en pixels natifs récupérés.

`art_approved` et `runtime_tested` restent `false` : aucune approbation artistique, ouverture dans l'éditeur, désérialisation moteur, vérification GPU, collision en jeu ou validation de gameplay n'est revendiquée.

## Reconstruction

Depuis la racine du dépôt :

```sh
.venv/bin/python -m py_compile \
  source/bosquet_mycelien_v1/build.py \
  source/bosquet_mycelien_v1/test_build.py
.venv/bin/python source/bosquet_mycelien_v1/build.py
.venv/bin/python -m unittest source.bosquet_mycelien_v1.test_build -v
```

Le build repart uniquement des PNG bruts versionnés, de la référence locale et des modules d'export existants du dépôt.
