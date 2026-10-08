# Mod des fins de donjon — workflow de production

## Périmètre de cette version

`mod_fins_donjons_v1` assemble les Grounds PMDO existants de la série : neuf maps dans l'ordre (FVS1 → FST1), l'ancienne variante de Givre FGG1 et la map spéciale FOC1 hors-série. Les quatre prochaines fins annoncées (Clairière tropicale, Couloir violet, Mt. Thunder, Jardin secret) ne sont pas encore créées : ne pas ajouter de placeholders.

Ce lot est un **assembleur, pas un nouveau générateur de cartes**. Il ne redessine aucun pixel et ne rebâtit pas les lots individuels. Il reprend depuis chaque ZIP versionné les banques `.tile`, le Ground `.rsground` et le script Lua. Les deux variantes de Givre restent accessibles ; FGG2 est le choix de la séquence principale.

## Commandes

```sh
# Reconstituer le cache de staging et produire le projet mod, le ZIP et la galerie
.venv/bin/python source/mod_fins_donjons_v1/build_mod.py

# Vérifier le mod assemblé, après le build
.venv/bin/python -m unittest source.mod_fins_donjons_v1.test_mod -v
```

Dépendances images : Pillow, NumPy et SciPy sont nécessaires aux builders de cartes amont ; cet assembleur n'utilise directement que Pillow. `.venv/` et `.cache/` sont ignorés par Git et peuvent être absents après une réinitialisation. Les ZIP projets sources, eux, sont versionnés et constituent l'entrée reproductible du mod.

## Contrat de l'assembleur

1. Garder la liste `MAPS` explicite, dans l'ordre de la série ; différencier `serie`, `variante` et `hors_serie`.
2. Pour chaque source, vérifier le hash SHA-256 du ZIP, le manifeste, un seul Ground et un seul script, le préfixe des banques, l'index local et le nœud lu dans chaque `.tile`.
3. Copier `.tile`, `.rsground` et le contenu des scripts sans transformation. Déplacer seulement leur chemin sous le namespace commun `guilde_fins_donjons`.
4. Fusionner les nœuds de tous les index dans un `Content/Tile/index.idx` unique. Refuser toute collision de nom de banque, d'asset ou de préfixe.
5. Vérifier dimensions 768 × 576, grille 8 px, `TexSize=1`, couches alignées, Top (`Layer=4`) en dernier, collisions alignées, marqueur `entrance` et coordonnées des tuiles référencées.
6. Produire un ZIP à ordre et horodatage fixes, un manifeste de provenance, un README qui liste les calques/animations/marqueurs, une planche et une galerie reliée aux aperçus individuels.
7. Exécuter les tests d'assemblage et d'installateur. Un chargement ou un rendu PMDO réel reste un niveau de validation distinct.

## Ajouter une map plus tard

- Construire et documenter d'abord son lot individuel (`renders/fin_.../` + ZIP projet PMDO), sans toucher aux autres maps.
- Ajouter une entrée dans `MAPS` avec un préfixe unique, son ordre/catégorie et ses chemins d'aperçu ; mettre à jour les fins planifiées dans `PLANNED`.
- Ne sélectionner que le Ground explicitement prévu pour la série. Si un lot V2 remplace un choix principal, conserver le V1 comme variante au lieu de l'écraser.
- Refaire le build et les tests, comparer le manifeste et la galerie, puis mettre à jour `README.md`, `AGENTS.md`, `REPRISE_MAPS.md` et les notes de workflow.
- Ne pas marquer `art_approved` ni `runtime_tested` sans validation correspondante. Un test JSON, un test de ZIP et une galerie ne sont pas un test moteur.

## Limites

- La composition et la matière de chaque map restent celles de son lot source ; l'assemblage ne rend pas rétroactivement une image générée « pixel-perfect native ».
- Le mod fournit les Grounds, calques graphiques, banques, collisions et marqueurs déjà présents. Aucun warp ni raccord vers le donjon suivant n'est ajouté.
- La version 1 est une livraison de travail : 9 cartes de la séquence plus FGG1 et FOC1 en compléments. Les quatre fins suivantes sont encore à produire.
