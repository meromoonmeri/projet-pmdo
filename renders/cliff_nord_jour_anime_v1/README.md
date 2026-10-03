# Cliff Nord-Ouest & Cliff Day — Nuages et Mer Animés (PMDO 0.8.12)

## Ce qui a été animé
1. **`cliffnordouesttest1.rsground` (`138 × 98` cases = `1104 × 784` px)** :
   - **Calque `01 Cloud/nuage (16 phases)`** (`01_long_cap_jour_02.tile`) : 16 phases de dérive éolienne multi-altitude sans saut de boucle (`FrameLength = 10` ticks = `2,67 s`), placé au-dessus du ciel `00_ciel` et derrière la mer/falaise. Le haut du ciel (`y = 0..25`) a également été complété avec `00_ciel`.
   - **Calque `02 Mer animee (8 phases)`** (`v2_promontoire_jour_03.tile`) : les `6 209` cases de mer passent de 1 frame fixe aux **8 phases canoniques** (`jour_mer_00..07.png`, `FrameLength = 10` ticks = `1,33 s`).
   - **Calque `04 Chemins et cascade animee`** (`Metano_Town_Animation_Tileset.tile`) : les `80` cases d'eau/cascade Métano en bas à droite (`x = 90..97, y = 88..97`) passent de 1 frame fixe à leurs **4 phases natives** (`FrameLength = 10`).
   - **`Background` (`LayeredBG`)** : configuré avec `CLIFF_JOUR_CIEL`, `CLIFF_JOUR_ASTRES` et `CLIFF_JOUR_NUAGES` (`RepeatX = true`, `-4 px/s`).

2. **`cliffdaytest.rsground` (`123 × 99` cases = `984 × 792` px)** :
   - **Calque `01 Mer animee (8 phases)`** (`v2_promontoire_jour_03.tile`) : les `7 503` cases de mer passent de 1 frame fixe aux **8 phases canoniques** (`FrameLength = 10` ticks = `1,33 s`).
   - **Calque `Cloud/nuage (16 phases)`** (`01_long_cap_jour_02.tile`) : la phase 0 conserve à 100 % les `600` tuiles de nuages posées sur la carte (`y = 5..38`), animées sur **16 phases** fluides multi-altitudes (`FrameLength = 10` ticks = `2,67 s`).
   - **Calque `06 Objets Decor (ex-Cloud/nuage)`** : les `325` tuiles d'objets/décors (`Altere_Pond_Objects`, `Metano_Town_Objects`, `Metano_Town_Trimmed`, `Metano_Inn_Objects`) qui étaient mélangées dans `Cloud/nuage` sont isolées proprement sur leur propre calque au-dessus afin qu'aucun décor ne bouge avec les nuages ni ne soit perdu.
   - **Calque `04 Cascades et eau animee`** (`Metano_Town_Animation_Tileset.tile`) : les `520` tuiles d'eau/cascades Métano ont été nettoyées (suppression des frames vides `""` qui faisaient clignoter l'eau, restauration des phases intermédiaires `dx = 6 / 8 / 9`, cadence ramenée de `60` à `10` ticks).

## Installation dans votre projet PMDO 0.8.12 existant
Fermez PMDO, puis lancez :
```bash
python INSTALLER.py "CHEMIN/VERS/PMDO/MODS/VOTRE_MOD"
```
Le script met à jour `cliffnordouesttest1.rsground`, `cliffdaytest.rsground`, `00_ciel.tile`, `01_long_cap_jour_02.tile`, `v2_promontoire_jour_03.tile` et reconstruit `Content/Tile/index.idx` sans toucher à vos autres feuilles `.tile` (`INVERSEPATHWAY.tile`, `terrain.tile`, etc.), avec sauvegarde automatique `.avant_anim.bak`.
