# EMB2 — Mt. Blaze avec un layout proche de la référence

**Lot** : `entree_mt_blaze_sud_nord_v2` · **Préfixe** : `EMB2` · **Branche** : `arena/01a0ef03-projet-pmdo`.

Cette V2 répond à la correction de layout : elle ne reprend pas la composition d’EMB1. Le cadrage et la disposition sont reconstruits à partir de la vignette « Rescue Team - Mt. Blaze Entrance » : large sol sableux au premier plan, bassins irréguliers à gauche et à droite, ruisseaux latéraux, deux structures de pierre autour d’une bouche sombre au centre-haut, falaises et blocs. EMB1 reste intact.

## Référence et limites

- Copie locale consultable : `reference/mt_blaze_reference_300x260.png` (300 × 260 px), retrouvée sur [Mystery Dungeon Wiki — Mt. Blaze](https://mysterydungeonwiki.com/wiki/Rescue_Team:Mt._Blaze). L’URL de l’image originale et les empreintes sont enregistrées dans `renders/entree_mt_blaze_sud_nord_v2/manifest.json`.
- `bruts/decor_ref_layout.png` est une reconstruction illustrée 4:3 générée depuis cette vignette, avec sa disposition comme blueprint. Ce n’est ni un rip pixel-par-pixel de la ROM ni une carte originale certifiée.
- Les textures visent les matériaux visibles dans cette référence : basalte lavande-gris, lave vin-rouge et sol sableux. Les masques de matière sont indépendants et restent éditables.
- Contrôle indicatif des couleurs modales (RGB euclidien sur des zones échantillonnées, pas une comparaison pixel-à-pixel) : roche **9,38**, lave **4,90**, sentier **7,55** unités par rapport à la vignette. Les valeurs et masques d’échantillonnage sont dans le manifeste.
- Le README de `source/outil_maps_pmdsky/` a été consulté. Il concerne les maps/BG d’Explorers of Sky et ne fournit pas Mt. Blaze GBA ; il n’est pas utilisé comme source graphique de la composition.

## Correction EMB2 — layout magenta et textures séparées

- `bruts/layout_magenta.png` est le layout source de placement : les pixels de lave sont codés en **magenta pur `#FF00FF`**. Le masque est défini par égalité RGB exacte (aucune tolérance) et son nombre de pixels est vérifié.
- `bruts/lave_texture_rgba.png` extrait uniquement la texture des zones marquées par ce key. `bruts/veines_roche_rgba.png` isole séparément les fissures chaudes dans la roche. Les deux sources sont en 1200 × 896, alpha binaire, RGB transparent noir ; leurs calques EMB2 restent disjoints.
- Dans le Ground et l’ORA, `lave` et `veines_roche` sont des calques animés indépendants, chacun avec 13 frames × 10 ticks. La vignette autonome permet désormais d’inspecter le layout magenta et ces deux textures source sous « Inspecter les sources de matière ».
- Les trois fichiers sont inclus dans `EMB2_calques_png_8px.zip` sous `sources/` et leurs empreintes, modes et dimensions figurent dans `manifest.json`.

## Animation canonique utilisée

L’étude locale `renders/etude_animations_canoniques_sky_v1/` établit pour la carte **D41P41A** une rotation exacte des palettes magma **10 et 11** : **13 crans, 10 ticks par cran, boucle de 130 ticks**. EMB2 garde fixes les positions des pixels et applique ces deux pistes aux accents de lave et aux veines rocheuses.

Point de provenance important : les tables et la cadence sont celles de **PMD Explorers of Sky**. Elles sont adaptées ici à l’illustration de **Red Rescue Team** ; elles ne sont pas présentées comme une capture vérifiée de l’animation GBA originale. L’animation RRT n’est pas revendiquée.

## Calques (bas → haut)

| Calque | Contenu |
|---|---|
| `sol_complet` | fond de terre sableuse de référence |
| `ombres` | ombres courtes portées des pierres |
| `lave` | bassins/chenaux latéraux, textures maroon ; accents palette 10, 13 × 10 ticks |
| `sentier` | grand sol praticable du premier plan vers la bouche |
| `eboulis` | groupes de pierres et rochers des rives |
| `parois` | murs et falaises latérales / arrière-plan |
| `piliers` | structures de pierre encadrant la porte |
| `grotte` | ouverture sombre au centre-haut |
| `veines_roche` | fissures chaudes dessinées dans la roche ; palette 11, 13 × 10 ticks |
| `Top` | calque avant-plan vide, réservé à l’édition |

Résolution finale : **768 × 576 px**, soit **96 × 72 cases de 8 px**. Boucle animation : **130 ticks ≈ 2,17 secondes** à 60 ticks/s. Aucun déplacement de pixel, aucune braise ajoutée : seules les couleurs cyclent, selon la méthode documentée de D41P41A.

## Construire, tester et empaqueter

Dépendances : Python 3.11+, Pillow, NumPy et SciPy.

```bash
.venv/bin/python source/entree_mt_blaze_sud_nord_v2/build.py
.venv/bin/python -m unittest source.entree_mt_blaze_sud_nord_v2.test_build -v
.venv/bin/python source/entree_mt_blaze_sud_nord_v2/package.py
```

Le build génère les calques PNG transparents, les 26 phases, les masques, l’ORA, le Ground natif PMDO 0.8.12, le WebP de revue, les ZIP et `apercu_entree_mt_blaze_sud_nord_v2.html`. Les contrôles valident la partition des matières, les deux bassins, le chemin, les marqueurs et les couleurs exactes des deux pistes de palette.

`art_approved` et `runtime_tested` restent à `false` : l’aperçu et la compilation du mod ne remplacent pas une validation visuelle par l’utilisateur ni un essai en jeu.
