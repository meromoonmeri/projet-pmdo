# FIZ1 — Fin de l’Île du Zénith : Sanctuaire des Alizés

Troisième volet de la **Trilogie du Zénith**, après EIZ1 et le chemin IFZ1.

## Carte

- 768×576 px, soit 96×72 cases de 8 px ;
- arrivée ouverte au sud et finale fermée au nord ;
- grande arène ovale, deux routes en croissant et deux observatoires latéraux ;
- autel de vent central décoratif et entièrement bloqué ;
- objectif sur la terrasse haute devant trois monolithes ;
- calques éditables, ORA et Ground/Tile PMDO 0.8.12 ;
- halo du sanctuaire et voiles de nuages séparés, 24 phases × 8 ticks.

La capture `references/Final_Island_RRT.png` guide les matières et la palette. Le décor est une composition générée référencée puis quantifiée : ses pixels ne sont pas présentés comme des tuiles natives certifiées.

## Bruts

- `bruts/decor_magenta.png` : terrasses et arène praticables sur clé magenta ;
- `bruts/sol_complet.png` : scène complète avec herbe chartreuse ;
- `bruts/fond_sans_objets.png` : ciel et bancs de nuages propres, communs à la trilogie.

## Construction et validation

```bash
.venv/bin/python source/fin_ile_zenith_v1/build.py
.venv/bin/python -m unittest -v source.fin_ile_zenith_v1.test_build
```

Sorties : `renders/fin_ile_zenith_v1/`, `apercu_fin_ile_zenith_v1.html`, `livrable_fin_ile_zenith_v1.zip` et `mod_fin_ile_zenith_pmdo_0812.zip`.

Aucune approbation artistique, ouverture dans l’éditeur PMDO, exécution moteur, rendu GPU ou validation de gameplay n’est revendiquée.
