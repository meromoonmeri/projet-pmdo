# IFZ1 — Île Flottante du Zénith : Couronne des Vents

Nouvelle carte autonome au format **4:3**, guidée par l’aire d’amis **Final Island** de *Pokémon Mystery Dungeon: Red Rescue Team*. Elle est distincte de BMF1 et de la série du Passage des Ruines.

## Statut et portée

- format final : **768×576 px**, soit **96×72 cases de 8 px** ;
- entrée au sud, sortie au nord ;
- couronne praticable par deux branches autour d’un monolithe suspendu ;
- deux belvédères latéraux reliés à la route principale ;
- sceau de vent central décoratif et bloqué ;
- deux animations indépendantes : courants ascendants et voiles de nuages ;
- calques PNG, fichier OpenRaster et projets Ground/Tile PMDO **0.8.12** ;
- aucun test runtime PMDO ni validation artistique externe n’est revendiqué.

## Référence canonique

`references/Final_Island_RRT.png` est une capture 480×312 de Final Island déjà archivée dans le dépôt. Elle sert à guider les matières et les couleurs, puis à construire la palette de quantification.

Les images produites sont une **composition générée référencée et quantifiée**. Elles ne sont pas présentées comme des tuiles natives certifiées ni comme une reconstruction exacte des pixels du jeu.

## Bruts conservés

Entrées actives, toutes en 1200×896 avant réduction :

- `bruts/decor_magenta.png` : décor complet avec les surfaces praticables remplacées par une clé magenta ;
- `bruts/sol_complet.png` : même scène avec herbe, ponts/marches plats et sceau central ;
- `bruts/fond_sans_objets.png` : plaque propre de ciel cyan et de bancs de nuages.

Les cinq versions refusées sont préservées dans `bruts/ecartes/` : une première passe trop vive, puis une seconde dont la roche restait trop bleu marine, et enfin une scène à roche corrigée dont le sol était devenu trop beige. Elles sont documentées et hachées dans le manifeste ; le builder ne les emploie pas.

## Construction

Le script `build.py` :

1. réduit les trois bruts à 768×576 ;
2. détecte la clé magenta par composantes connexes ;
3. exclut le disque central de la collision et raccorde les bandes de marches ;
4. segmente le décor en ciel, nuages, falaises, végétation, pierres, monolithe, îlots et premier plan ;
5. quantifie les RGB statiques vers la palette de Final Island ;
6. produit les deux cycles calculés de 24 images, à 8 ticks par image ;
7. construit une grille 96×72 et vérifie l’accès aux cinq marqueurs ;
8. exporte les PNG, l’ORA, le visualiseur, les banques Tile PMDO et le Ground PMDO.

```bash
.venv/bin/python source/ile_flottante_zenith_v1/build.py
.venv/bin/python -m unittest -v source.ile_flottante_zenith_v1.test_build
```

## Sorties

- `renders/ile_flottante_zenith_v1/` : calques, animations, scènes, masque de marche, ORA et manifeste ;
- `apercu_ile_flottante_zenith_v1.html` : visualiseur à calques et animation ;
- `livrable_ile_flottante_zenith_v1.zip` : lot graphique ;
- `mod_ile_flottante_zenith_pmdo_0812.zip` : projet PMDO 0.8.12 éditable.

Les ouvertures nord et sud n’ont volontairement aucun warp de destination. Il faut les raccorder dans un mod hôte avant un test de gameplay réel.
