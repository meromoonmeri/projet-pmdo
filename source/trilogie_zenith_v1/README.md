# Trilogie du Zénith — entrée, chemin et fin

Série cohérente de trois cartes autonomes 4:3 guidées par **Final Island** de *Pokémon Mystery Dungeon: Red Rescue Team* :

| Rôle | Lot | Carte | Parcours |
|---|---|---|---|
| Entrée | EIZ1 | Portail des Alizés | arrivée sud, deux branches, belvédères, seuil nord |
| Chemin | IFZ1 | Couronne des Vents | ouverture sud, couronne bifurquée, deux îlots, sortie nord |
| Fin | FIZ1 | Sanctuaire des Alizés | arrivée sud, arène, observatoires, objectif nord fermé |

Chaque carte mesure 768×576 px, utilise une grille de 96×72 cases de 8 px, possède des calques PNG et OpenRaster, deux animations calculées séparées, une collision vérifiée et un projet Ground/Tile PMDO 0.8.12.

Les pixels sont issus de compositions générées référencées puis quantifiées vers la palette de la capture. Ils ne sont pas présentés comme des tuiles natives certifiées. Aucun test runtime PMDO, rendu GPU, gameplay ou approbation artistique n’est revendiqué.

## Aperçus et paquets

- `apercu_entree_ile_zenith_v1.html` — `livrable_entree_ile_zenith_v1.zip` — `mod_entree_ile_zenith_pmdo_0812.zip`
- `apercu_ile_flottante_zenith_v1.html` — `livrable_ile_flottante_zenith_v1.zip` — `mod_ile_flottante_zenith_pmdo_0812.zip`
- `apercu_fin_ile_zenith_v1.html` — `livrable_fin_ile_zenith_v1.zip` — `mod_fin_ile_zenith_pmdo_0812.zip`
- `apercu_trilogie_zenith_v1.html` — galerie des trois cartes.

## Validation

```bash
.venv/bin/python source/trilogie_zenith_v1/build.py
.venv/bin/python -m unittest -v \
  source.entree_ile_zenith_v1.test_build \
  source.ile_flottante_zenith_v1.test_build \
  source.fin_ile_zenith_v1.test_build \
  source.trilogie_zenith_v1.test_trilogie
```
