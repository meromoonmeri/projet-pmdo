# EIZ1 — Entrée de l’Île du Zénith : Portail des Alizés

Premier volet de la **Trilogie du Zénith** :

1. **EIZ1** — entrée et portail des Alizés ;
2. **IFZ1** — chemin de la Couronne des Vents ;
3. **FIZ1** — fin au Sanctuaire des Alizés.

## Carte

- 768×576 px, soit 96×72 cases de 8 px ;
- arrivée ouverte au sud ;
- palier inférieur puis deux branches autour d’un grand puits de ciel ;
- deux belvédères latéraux accessibles par des ponts plats ;
- seuil du portail au nord, sans warp configuré ;
- calques éditables, ORA et Ground/Tile PMDO 0.8.12 ;
- runes du portail et voiles de nuages séparés, 24 phases × 8 ticks.

La capture `references/Final_Island_RRT.png` guide les matières et la palette. Le décor est une composition générée référencée puis quantifiée : ses pixels ne sont pas présentés comme des tuiles natives certifiées.

## Bruts

- `bruts/decor_magenta.png` : route, branches et belvédères sur clé magenta ;
- `bruts/sol_complet.png` : scène complète avec herbe chartreuse ;
- `bruts/fond_sans_objets.png` : ciel et bancs de nuages propres, communs à la trilogie.

## Construction et validation

```bash
.venv/bin/python source/entree_ile_zenith_v1/build.py
.venv/bin/python -m unittest -v source.entree_ile_zenith_v1.test_build
```

Sorties : `renders/entree_ile_zenith_v1/`, `apercu_entree_ile_zenith_v1.html`, `livrable_entree_ile_zenith_v1.zip` et `mod_entree_ile_zenith_pmdo_0812.zip`.

Aucune approbation artistique, ouverture dans l’éditeur PMDO, exécution moteur, rendu GPU ou validation de gameplay n’est revendiquée.
