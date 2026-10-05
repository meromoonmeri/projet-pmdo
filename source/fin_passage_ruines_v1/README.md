# FPR1 — Fin du Passage des Ruines : Sanctuaire du Cadran

Carte terminale 4:3 conçue comme le complément fermé d'**EPR1 — Entrée du Sentier des Ruines**. Le rendu canonique PMD Sky `P22P01A` (408×408, 109 couleurs) sert de référence de matière, de palette et d'échelle. La composition et les effets sont générés ou calculés : leurs pixels ne sont **pas** présentés comme des tuiles ni comme des animations natives certifiées.

## Composition et collisions

- Canevas final : **768×576 px**, soit **96×72 cellules de 8×8**.
- Layout : entrée unique au sud, arène ovale au cadran brisé, terrasses ruinées asymétriques, escalier monumental et sanctuaire fermé au nord.
- Repères en pixels : entrée `[384,548]`, boss `[384,340]`, objectif du cadran `[384,152]`.
- La grille réserve **1 528 cellules marchables**, toutes accessibles depuis l'entrée par quatre-voisins. Les bords nord, est et ouest sont bloqués ; il n'existe ni sortie ni warp configuré.
- Ce contrôle valide le masque calculé pour un collider 16×16, pas un déplacement réel dans PMDO.

Les trois bruts retenus sont dans `bruts/` (`1200×896`) : décor détouré sur magenta, fond sans objets et sol complet texturé. `bruts/ecartes/` conserve deux essais rejetés : un premier layout trop proche d'EPR1 et une première texture de sol dont l'herbe était trop vive (`46,76`, au-dessus du seuil RGB de 35).

## Calques et animations

Les PNG alignés dans `renders/fin_passage_ruines_v1/layers/` séparent :

1. sol complet de référence ;
2. sol praticable ;
3. sous-couche des murs ;
4. ombres de contact ;
5. relief et falaises ;
6. ruines, escalier et cadran central ;
7. végétation ;
8. stèle et pierres du sanctuaire ;
9. débris isolés.

Deux effets restent indépendants : `lueur_cadran` et `pollen_dore`, chacun en **24 phases × 8 ticks**, soit une boucle de **192 ticks**. Ils sont créés pour FPR1 et ne proviennent pas d'un cycle d'animation de la ROM.

Le builder produit également 24 scènes composées, APNG/WebP, overlay des collisions, ORA éditable, manifeste JSON, aperçu HTML, banques `.tile` et Ground PMDO 0.8.12.

## Fidélité mesurée et limites

Distance RGB moyenne des bruts retenus vers les 109 couleurs du rendu `P22P01A`, avant quantification :

| Matière | Distance moyenne |
|---|---:|
| Sol | 13,10 |
| Relief | 20,70 |
| Ruines et sanctuaire | 11,32 |
| Végétation | 10,92 |
| Scène complète | 14,61 |

Toutes les mesures sont strictement inférieures au seuil de 35. Les RGB statiques exportés sont ensuite quantifiés vers la palette de la référence. Cette normalisation ne transforme pas le dessin généré en pixels natifs récupérés.

Le projet PMDO compte **14 098 tuiles** dans dix banques. `art_approved` et `runtime_tested` restent `false` : aucune approbation artistique, ouverture dans l'éditeur, désérialisation par le moteur, vérification GPU, collision en jeu ou validation de gameplay n'est revendiquée.

## Livrables

- `apercu_fin_passage_ruines_v1.html` — visualiseur avec calques, animations et collisions ;
- `livrable_fin_passage_ruines_v1.zip` — PNG, scènes, animations, ORA, manifeste et notice ;
- `mod_fin_passage_ruines_pmdo_0812.zip` — projet autonome Ground/Tile pour PMDO 0.8.12.

## Reconstruction et tests

Depuis la racine du dépôt :

```sh
.venv/bin/python -m py_compile \
  source/fin_passage_ruines_v1/build.py \
  source/fin_passage_ruines_v1/test_build.py
.venv/bin/python source/fin_passage_ruines_v1/build.py
.venv/bin/python -m unittest source.fin_passage_ruines_v1.test_build -v
```

Le build ne sollicite aucun service distant : il repart des trois PNG bruts, de la référence locale épinglée et des modules d'export déjà présents dans le dépôt.
