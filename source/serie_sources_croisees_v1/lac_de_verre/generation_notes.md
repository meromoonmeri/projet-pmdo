# Journal de reprise — LGV1 / Lac de Verre

## Décision de méthode

La première approche (décor original généré sur magenta, ensuite segmenté) a été **rejetée** après correction de l’utilisateur : prendre une vraie zone PMD, modifier légèrement le layout et réutiliser les assets canoniques. Les anciens bruts `decor_magenta.png`, `sol_complet.png` et `decor_canonique_sans_magenta.png` ont été retirés; ils ne font plus partie du pipeline ni du livrable.

## Base Sky D52P11A

- Ground : `references/native_D52P11A/d52p11a.rsground`, source Sky commit `d62110a00269bdc861b8fe41b077607a80f50978`, blob `b938d1668244302f02cac52989627b66e15b243a`.
- Tileset : `references/native_D52P11A/D52p11a_Base.tile`, même commit, blob `68a914a3281fa3cfef46b0347a5b9c3d9136e4da`.
- Dimensions source : **63 × 51 cases**, 8 px par case, soit **504 × 408 px**. Le builder décode ce Ground et son tileset avec le lecteur du dépôt; le résultat est testé pixel pour pixel contre `references/sky_D52P11A.png`.
- Pour le gabarit 4:3, deux cases sont réfléchies à gauche et trois à droite : 68 × 51 cases, **544 × 408 px**. Il n’y a pas d’étirement. Le rendu est agrandi par NEAREST à 1200 × 900 puis recadré de 2 px en haut et en bas vers le brut **1200 × 896**.

## Bassin Red T01P02A

- Source : frames de rendu 0 à 5 de `T01P02A` (commit Red `680fb85efacbde40473ef3f09dde2c0152e96f6c`).
- Patch d’eau commun : coordonnées `(270, 226)` dans chaque rendu, taille **64 × 32 px**. Les quelques pixels de rive/sol dans le patch sont remplacés par le pixel aquatique valide le plus proche; les couleurs sont toujours prélevées dans l’image Red. Le patch est agrandi uniformément 1,5× vers **96 × 48 px**.
- Une ellipse centrale forme le bassin. Son masque binaire reste un calque séparé. L’animation réutilise les six frames source avec 10 ticks par frame; aucune onde ni cycle d’eau procédural n’est ajouté. Après réduction/palette, trois états distincts subsistent; les frames répétées du cycle source sont gardées, pas remplacées par une animation inventée.
- Ces pixels viennent des **rendus visuels Red**. Ils ne sont pas extraits du tileset Red et ne sont pas présentés comme des tuiles natives.

## Pipeline et contrôle

- Les trois bruts persistants sont dans `bruts/` : base D52P11A, composite frame 0 et masque d’eau. Ils font chacun **1200 × 896 px**; aucun n’a de fond magenta.
- La base et l’eau sont réduites séparément par BOX, facteur uniforme `576/896`, largeur intermédiaire 771 px, puis recadrage centré de 1 px à gauche et 2 px à droite vers **768 × 576** (96 × 72 cases de 8 px).
- Palette partagée de **96 couleurs**. Tous les RGB de la base native et du patch Red sont conservés; les cases restantes sont complétées par des RGB exacts des mêmes références. Aucun tramage.
- La collision Sky est reprise depuis le Ground source; les cases couvertes par l’eau sont ajoutées comme obstacles. Un passage est vérifié pour une empreinte 16 × 16 px, de gauche à droite. Cela ne remplace pas un essai dans PMDO.
- `native_texture_certified`, `art_approved` et `runtime_tested` restent faux. La composition est une variante éditable et une démonstration de provenance, pas une certification officielle des nouvelles banques `.tile`.

## Reproduction

Depuis la racine :

```bash
.venv/bin/python source/serie_sources_croisees_v1/lac_de_verre/build.py
.venv/bin/python -m unittest source.serie_sources_croisees_v1.lac_de_verre.test_build -v
.venv/bin/python source/serie_sources_croisees_v1/lac_de_verre/package.py
```

Les hashes, fichiers sources, dimensions et mesures sont consignés dans `references.json`, `manifest.json` et `palette_reference.json`.
