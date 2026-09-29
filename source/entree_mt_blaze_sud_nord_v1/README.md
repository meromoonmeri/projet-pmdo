# EMB1 — Entrée Mt. Blaze : génération, calques et animations

**Lot** : `entree_mt_blaze_sud_nord_v1` · **Préfixe** : `EMB1` · **Branche** : `arena/01a0ef03-projet-pmdo`.

## Reprise

Travail poursuivi sur la branche de session déjà présente, sans cloner ni rebaser `main` et sans récupérer le contenu des branches sœurs. Les captures `Rescue_Team_-_Mt._Blaze_Entrance.png` et `221081.png` fournies dans la demande ont guidé la composition. Les pièces jointes n'étant pas montées dans le checkout, elles ne sont pas recopiées dans les bruts et il n'y a pas de mesure de fidélité pixel/RGB.

Le README de `source/outil_maps_pmdsky/` a été lu. Cet outil récupère les maps/BG d'Explorers of Sky ; Mt. Blaze ici est la référence de Red Rescue Team (GBA), absente de `index_rom.json`. Il n'a donc pas été utilisé comme faux rip canonique.

## Bruts générés

`bruts/` contient les trois images pleine résolution **1200 × 896** :

1. `decor.png` — entrée top-down 4:3, sentier au sud, bouche de grotte au nord, piliers et falaises latérales, deux poches de lave réservées en magenta.
2. `sol_complet.png` — texture intégrale de terre volcanique, destinée au fond opaque du Ground.
3. `lave_texture.png` — édition du premier décor : magma rouge sombre, veines orange et points chauds. Seules les couleurs dans les deux masques des bassins sont extraites.

Le générateur a approché le magenta par des tons tels que (253, 0, 248), plutôt que #FF00FF. Le masque utilise une tolérance couleur, conserve les deux grandes composantes et repeint le petit point parasite sur une roche. Aucun pixel magenta n'entre dans les exports finaux.

## Fabrication

La normalisation réutilise les fonctions 4:3 de `source/entree_jungle_sud_nord_v1/build.py` : facteur uniforme 576/896 = 0,642857, mise à 771 × 576, recadrage centré de 1 px à gauche et 2 px à droite, réduction BOX pondérée **par classe** sans mélange des matières. Les masques fixes sont exclusifs ; le sentier constitue le praticable et les autres zones les obstacles.

| Calque | Source | Traitement |
|---|---|---|
| sol_complet | `sol_complet.png` | Réduction entière + palette terre séparée |
| ombres | silhouettes rocheuses | Décalage de 3 × 5 px, visible au bord du sentier |
| lave | `lave_texture.png` × masque `decor.png` | 24 phases, onde de chaleur chromatique |
| sentier | composante terre cuite principale | Matériau praticable |
| eboulis | composantes rocheuses isolées | Petites pierres et détails du sol |
| parois | résidu rocheux connecté au bord | Palette roche (112 couleurs) |
| piliers | pixels pierre claire dans les deux boîtes du portail | Calque indépendant |
| grotte | composante sombre autour de (600, 96) | Ouverture non praticable |
| lueurs | fissures orange de la texture de lave | 24 phases scintillantes |
| braises | sprites générés par code | 28 émetteurs répartis sur les deux bassins |

Trois boucles de 24 × 10 ticks partagent la période de scène de 240 ticks (4 secondes). Les sprites de braise et toutes les phases sont déterministes. Dans le Ground natif, les phases de lave et de lueur sont réparties par groupes de quatre TileBanks : la plus grande feuille reste à 1 096 px de haut, plutôt que de dépasser 4 000 px en banque unique.

## Reproduire et tester

Dépendances : Python 3.11+, Pillow, NumPy et SciPy.

```bash
.venv/bin/python source/entree_mt_blaze_sud_nord_v1/build.py
.venv/bin/python -m unittest source.entree_mt_blaze_sud_nord_v1.test_build -v
.venv/bin/python source/entree_mt_blaze_sud_nord_v1/package.py
```

Le build produit les PNG transparents de 768 × 576, les 72 frames animées, les masques de contrôle, l'ORA, le Ground natif PMDO 0.8.12, l'aperçu WebP, le ZIP des calques, le ZIP du projet et la page autonome racine. `art_approved` et `runtime_tested` restent à `false` jusqu'à validation visuelle et test dans PMDO.
