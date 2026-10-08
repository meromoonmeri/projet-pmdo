# Workflow — assembler une série de fins PMDO

## A. Déterminer la source

Ce dépôt contient plusieurs familles de maps. Le mod présent assemble uniquement les livraisons `renders/fin_*/*_projet_pmdo_0812.zip`. Avant d'ajouter un dossier, vérifier qu'il s'agit bien d'une fin de donjon de cette série, qu'un ZIP PMDO individuel est déjà livré, et qu'un Ground multicalque ainsi qu'un aperçu existent. Les cartes d'entrée, zones de réveil et cartes Métano suivent d'autres workflows.

La sélection courante est explicite dans `build_mod.py` : neuf étapes principales (FVS1, FCF1, FRP1, FGG2, FBS1, FJS1, FWC1, FSM1, FST1), FGG1 comme variante conservée et FOC1 comme carte hors-série. Les fins encore annoncées mais absentes ne sont pas représentées par des fichiers factices.

## B. Contrôler les sources avant copie

Pour chaque ZIP source :

- relever le SHA-256 et le comparer à celui écrit dans le manifeste du mod ;
- lire `Content/Tile/index.idx` et vérifier chaque nœud avec la banque `.tile` correspondante ;
- confirmer le préfixe unique, un seul Ground, un script Lua, le nom d'asset et la liste des banques déclarée par le lot ;
- parcourir le Ground sans le sérialiser à nouveau : version, taille, `TexSize`, calques, collision, marqueurs, banques et coordonnées de tuiles ;
- vérifier que les aperçus et vignettes liés par la galerie existent.

La source de vérité est le ZIP individuel livré avec la carte. Ne pas reconstruire un lot uniquement pour produire le mod : un rebuild peut réécrire les ORA ou les archives de ce lot.

## C. Assembler

- Copier les `.tile` et `.rsground` octet pour octet.
- Copier le script Lua octet pour octet vers `Data/Script/guilde_fins_donjons/ground/<asset>/`; ne pas éditer les événements ni ajouter des destinations.
- Fusionner les nœuds d'index; ne jamais remplacer un index complet par celui d'une seule carte.
- Garder un projet autonome, un namespace et un UUID stables. L'installateur doit fusionner l'index et protéger les fichiers déjà modifiés.
- Produire le ZIP avec membres triés et horodatage fixe afin que deux builds identiques soient reproductibles.

## D. Tester et documenter

```sh
.venv/bin/python source/mod_fins_donjons_v1/build_mod.py
.venv/bin/python -m unittest source.mod_fins_donjons_v1.test_mod -v
```

Les tests couvrent la liste des sources, l'intégrité octet pour octet, l'index fusionné, les références des tuiles et les marqueurs, le Ground 4:3, les métadonnées, la galerie, la reproductibilité de l'archive et l'installateur en simulation/réinstallation/conflit.

Pour une map ajoutée : mettre à jour en même temps `MAPS`, `PLANNED`, le README généré, le manifeste et les docs racines; indiquer explicitement si elle est dans la séquence, une variante ou hors-série. Les statuts d'approbation restent ceux des lots individuels.

## E. Ne pas sur-vendre la validation

- Les tests de fichier ne valident pas l'affichage, les animations en jeu, les collisions en mouvement ni les warps.
- Tous les marqueurs peuvent avoir des noms spécifiques au lot (`boss`, `source`, `belvedere`, `joyau`, `kyogre`, etc.). L'assembleur les conserve; il ne les interprète pas comme un scénario commun.
- Aucune destination de donjon n'est connue ou raccordée dans cette livraison. Pas d'aventure jouable annoncée.
- Chaque map garde sa provenance et sa méthode d'origine. Un assemblage commun ne transforme pas les cartes générées référencées en tuiles natives canoniques.
