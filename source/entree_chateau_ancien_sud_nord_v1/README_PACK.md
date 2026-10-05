# EAC1 — Entrée Château Ancien, Galerie des trésors

Carte intérieure PMD au format 4:3, créée à partir du rip canonique `oldcastlepmd.png` (408×408). Le rip montre un dallage doré, un médaillon central, des coffres et des ornements ; la nouvelle composition organise une galerie traversable entre le seuil sud et la porte nord.

## Construction

```bash
.venv/bin/python source/entree_chateau_ancien_sud_nord_v1/build.py
.venv/bin/python -m unittest source.entree_chateau_ancien_sud_nord_v1.test_build -v
```

- Taille : 768×576 px, 96×72 cases de 8×8 px.
- Préfixe : `EAC1`. Parcours contrôlé par BFS du marqueur `entrance_sud` au `sortie_nord`.
- Calques PNG RGBA séparés : `sol_complet` (référence générée), `sol`, `murs`, `ombres`, `ornements/porte`, `coffres`, `statues/rails`, `appliques`, `reflets_or` (24×10 ticks).
- Les couleurs du décor généré sont quantifiées sur la palette RGB échantillonnée dans le rip. Les distances moyennes non quantifiées sont enregistrées par catégorie dans `renders/entree_chateau_ancien_sud_nord_v1/manifest.json` ; seuil visé : <35.
- Le scintillement doré est calculé à partir de deux couleurs du rip ; il ne s'agit pas d'une animation native extraite.
- Exports : PNG 8 px, ORA, scènes animées, aperçu HTML, Ground/Tile PMDO 0.8.12 et deux ZIP.

## Limites de validation

Les éléments générés et recolorisés sont des propositions graphiques, pas des tuiles PMD certifiées. `art_approved` et `runtime_tested` restent `false` dans le manifeste. Les tests unitaires vérifient le format, la fidélité couleur moyenne, les calques, la boucle, le parcours et les archives ; aucun lancement du mod dans PMDO n'a été effectué.
