# Cliff Nord (`cliffnordouesttest1` & `cliffdaytest`) — Ciel Nuit Étoilé (Scène du Réveil), Lune, Étoiles Scintillantes, Wrap Nuages & Mer PMD Sky Port

Ce lot applique sur `cliffnordouesttest1.rsground` et `cliffdaytest.rsground` :

1. **Aucun calque de falaise, d'objet ou d'animation existante n'est touché, renommé ou déplacé** :
   - Dans `cliffnordouesttest1.rsground` : `Layers[2]` (`New Layer`) et `Layers[3]` (`Layer 3`) sont **100 % identiques octet pour octet** à l'original (ainsi que la case `Altere_Pond_Cliffs` sur `Layers[1]`).
   - Dans `cliffdaytest.rsground` : `Layers[2]` (`Layer 2`), `Layers[3]` (`Layer 4`), `Layers[4]` (`Layer 3`), les 5 cases `Altere_Pond_Cliffs` / `CanyonCamp` sur `Layers[0]` et les **325 cases d'objets** (`Altere_Pond_Objects`, `Altere_Pond_Objects_Under`, `Metano_Town_Objects`, `Metano_Town_Trimmed`, `Metano_Inn_Objects`) sur `Layers[5]` (`Cloud/nuage`) sont **100 % identiques octet pour octet** à l'original.
   - Aucune banque `.tile` factice/proxy n'est générée pour les falaises ou les objets : seule `Content/Tile/v2_promontoire_jour_03.tile` est livrée.

2. **Ciel nuit étoilé de la Scène du Réveil (`ZRV1`/`ZRV2`), pleine lune, étoiles scintillantes & wrap nuages (`LayeredBG` / `MapBG`)** :
   - `Object["Background"]` est configuré en `RogueEssence.Dungeon.LayeredBG, RogueEssence` avec 3 calques `MapBG` :
     - **Calque BG 0 (`CLIFF_NORD_OUEST_CIEL` / `CLIFF_DAY_CIEL`)** : dégradé nocturne de la scène du réveil (`ZRV2N_01_ciel.png`), halo bleu concentrique (`ZRV1N_06_panorama.png`) et pleine lune cratérisée `64×64` px (`ZRV2N_03_astre.png`).
     - **Calque BG 1 (`CLIFF_NORD_OUEST_ETOILES` / `CLIFF_DAY_ETOILES`)** : `DirSheet` animé sur **24 phases** (`FrameTime = 5` ticks, cycle de 120 ticks = 2,0 s) reprenant la loi de scintillement (`eteint -> coeur -> plein -> coeur -> eteint`) et les motifs d'étoiles de `ZRV1`/`ZRV2` et `bgnightbackgroundpmdskyda.png`.
     - **Calque BG 2 (`CLIFF_NORD_OUEST_NUAGES` / `CLIFF_DAY_NUAGES`)** : nuages en wrap horizontal (`RepeatX = true`, `RepeatY = false`, `BGMovement = (-4, 0)`, `Parallax = "1, 1"`), passant devant la lune et les étoiles scintillantes.
   - Les tuiles statiques `00_ciel` sur `Layers[0]` et `01_long_cap_jour_02` sur `Layers[5]` sont vidées pour que le `LayeredBG` soit visible derrière les calques de tuiles sans doublon statique.

3. **Mer (`Layers[1]`) : animation canonique PMD Sky Port (`reference_ciel_mer.png`, Pelipper Post Office)** :
   - Extrait les **5 bandes `far_sea`** (`(544+56*f, 224, 592+56*f, 352)`, `48×128` px) et les **10 bandes `near_sea`** (`(824+56*f, 224, 872+56*f, 392)`, `48×168` px) de `source/falaises_cotieres_nues/reference_ciel_mer.png`.
   - Construit les 10 phases canoniques `1312×1024` px dans le repère exact de `v2_promontoire_jour_03` (`0` pixel d'écart sur la phase 0 face à `sprites/cote_dix_zones/fonds/jour_mer_00.png`).
   - Encode `Content/Tile/v2_promontoire_jour_03.tile` au format binaire natif `TileSheet` de RogueEssence (Phase 0 conservée aux coordonnées `(tx, ty)` exactes dans `ty = 0..127`, phases `1..9` dédupliquées dans `ty >= 128`) et anime les `6209` cases de mer de `cliffnordouesttest1.rsground` et les `7503` cases de mer de `cliffdaytest.rsground` sur 10 phases (`FrameLength = 10` ticks à 60 Hz).

## Limites honnêtes
- `art_approved: false`
- `runtime_tested: false` (aucun test d'ouverture dans l'exécutable PMDO n'a été effectué dans cet environnement).
