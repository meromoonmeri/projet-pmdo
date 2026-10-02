# Allègement du dépôt — 2 octobre 2026

**Demande** : « Ok allège-le alors ! » (2 octobre 2026), après l'échec du clonage du dépôt dans la session Arena. Le dernier état pesait 6,67 Go pour 41 868 fichiers, soit environ 11,5 Go avec `.git` et l'arbre de travail, sur un disque de 21 Go. Le message d'erreur ne donnait aucun détail : la taille est la piste la plus probable, sans preuve.
**Niveau choisi par l'utilisateur** : « Tout archiver, y compris la world map et final_duos ».

## Résultat

| Dernier état (fichiers suivis) | Avant | Après |
| --- | ---: | ---: |
| Poids | 6,67 Go | 2,42 Go |
| Fichiers | 41 868 | 16 343 |
| Dossiers de lots dans `renders/` | 166 | 46 |

Retirés du dernier état : **120 lots** de `renders/`, leurs ZIP voisins (`renders/<lot>_pack.zip`) et **74 aperçus** `apercu_*.html` de la racine, soit 25 525 fichiers et 4,25 Go.

## Rien n'est perdu, rien n'est réécrit

Les fichiers sont seulement absents du dernier état. L'historique n'a pas été touché : tout est au commit **`6cca4a09380211e510ab1bea454a1b1926ef4b5a`** (dernier commit de `main` avant l'allègement).

- **Parcourir ou télécharger à la main** : <https://github.com/meromoonmeri/projet-pmdo/tree/6cca4a09380211e510ab1bea454a1b1926ef4b5a/renders>
- **Restaurer** (mêmes chemins, mêmes octets, récupération partielle, quelques secondes) :
  ```
  python3 source/restaurer_lot.py --liste                      # lots archivés, dates, tailles
  python3 source/restaurer_lot.py cendres_palette_raccord_v4   # un lot : dossier, ZIP voisin, aperçu
  python3 source/restaurer_lot.py --avec-dependances tours_layers_v3   # + les lots que ses scripts lisent
  python3 source/restaurer_lot.py --prefixe world_map          # une famille
  ```
  Le manifeste est `source/allegement_2026-10-02.json` (chemins, tailles, dates, dépendances de build). Les fichiers restaurés restent **non suivis** et sont ajoutés à `.git/info/exclude` : un `git add -A` ne les recommit pas par erreur.
- **Sans l'outil** : `git fetch --depth=1 --filter=blob:none origin 6cca4a09380211e510ab1bea454a1b1926ef4b5a` puis `git checkout 6cca4a09380211e510ab1bea454a1b1926ef4b5a -- renders/<lot>`.

## Critère

Lots de renders/ dont la dernière modification précède le 25 septembre 2026, que ni les lots récents, ni les outils partagés, ni un aperçu conservé ne lisent ; leurs ZIP voisins (renders/<lot>_pack.zip) et leurs aperçus apercu_*.html de la racine partent avec eux.

- **Gardé tel quel** : les 43 lots modifiés depuis le 25 septembre (entrées, fins de donjon, Zone Zéro fleurie…), plus `dungeon_biomes_v1` (lu par `source/entree_sables_mouvants_sud_nord_v1/build.py`), tout `source/` (code, tests, bruts générés), `exports/`, `sprites/`, `salles/`, `calques/`, `tiled/`, les références de la racine (captures PMD, envois de l'utilisateur), les packs livrés de la racine (mods Métano, etc.) et 92 aperçus de la racine.
- **Exemptés malgré leur date** : `mega_evolution_v1` et `mega_evolution_v2` (38 Mo). Des aperçus conservés (`apercu_mega_et_carapagos.html`, `apercu_carapagos_v4_animations.html`, `apercu_mega_generee_v2.html`) chargent leurs images ; les archiver aurait cassé ces pages.
- Dépendances relevées par lecture des scripts : aucun script modifié depuis le 25 septembre, aucun outil partagé et aucune page conservée ne lit un lot archivé (seule mention : une docstring de `source/entree_sud_nord_generee_v1/build.py` et une chaîne de provenance du manifeste d'`entree_vapeur_sud_nord_v1`, sans lecture de fichier). Les scripts des anciens lots restent dans `source/` et lisent parfois d'autres lots archivés (indiqués par `--liste`).

## Ce qui change pour le travail courant

- Les chemins `renders/<lot>/…` et `apercu_<lot>.html` des lots archivés, cités dans les anciennes sections de `README.md`, `AGENTS.md` et `REPRISE_MAPS.md`, sont **absents tant que le lot n'est pas restauré**. Ces textes n'ont pas été réécrits.
- Le serveur d'aperçus (`source/serveur_apercus/serve.py`) liste moins de pages : seulement les aperçus conservés.
- Relancer le `build.py`, `verify.py` ou les tests d'un lot archivé (ou d'un lot qui en lit un) demande de le restaurer d'abord, avec `--avec-dependances`. Les lots récents ne sont pas concernés.
- Cinq dossiers d'anciennes livraisons, restés dans `source/`, lisent aussi des lots archivés (liste dans le manifeste, clé `scripts_conserves_lisant_des_lots_archives`). Restaurer leurs lots avant de relancer leurs scripts :

| Dossier conservé | Dernière modification | Lots archivés qu'il lit |
| --- | --- | --- |
| `source/corrections_northern_v1` | 2026-09-13 | `crooked_statique_v2`, `crooked_verdure_v1`, `northern_calques_v1`, `references_calques_v1`, `soleil_spring_v1`, `spring_escalier_v1`, `spring_pulsation_v2` |
| `source/livraison_jungle_dtef_v3` | 2026-09-15 | `donjons_dtef_v2`, `donjons_generes_dtef_v3`, `jungle_geysers_v2` |
| `source/retouches_v6` | 2026-09-13 | `entrees_calques_v6`, `entrees_pmd_collection`, `metano_expeditions_actuel`, `retouches_zones_v6` |
| `source/suite_foret_cafe_v1` | 2026-09-21 | `cafe_spinda_revisite_v7`, `lisiere_pmd_v1`, `spinda_decor_v1` |
| `source/tours_saisons_v1` | 2026-09-15 | `designs_dtef_v4`, `foret_saisons_v1`, `tours_hooh_v1` |

## Contrôles

### Tests, avant et après l'allègement

`python -m unittest -v` lancé fichier par fichier sur les 85 fichiers de tests du dépôt (Python 3.11, Pillow 12.3, NumPy 2.4, SciPy 1.17), statut de **chaque** test comparé entre l'arbre complet (commit `6cca4a09`) et l'arbre allégé :

| Groupe | Fichiers | Tests | Résultat |
| --- | ---: | ---: | --- |
| Lots récents conservés | 49 | 527 | identique test par test (461 ok) |
| Autres outils conservés (guilde, pipeline personnages…) | 20 | 128 | identique test par test (123 ok) |
| Anciens lots archivés | 16 | 135 | 134 ok avant, 1 ok sans restauration (leurs rendus sont absents), **134 ok après restauration** de leurs 18 lots : identique à l'avant pour 16 fichiers sur 16 |

Les 71 tests non-ok des fichiers conservés l'étaient déjà avant l'allègement : ils demandent le cache `.cache/<lot>/` que seul `build.py` produit et qu'un clone neuf n'a pas (voir plus bas, ils passent après reconstruction).

### Reconstruction des lots conservés, sans aucun lot archivé

Pour les 51 fichiers de tests conservés qui avaient des tests non-ok à la référence, le build a été relancé sur l'arbre allégé (sans aucun lot archivé), puis leurs tests : le `build.py` voisin dans 44 cas, le `build.py` + `package.py` du dossier parent pour les quatre zones de `zone_zero_v2`, et `build_mod.py` pour le mod des entrées.

- **48 builds sur 49 terminés sans erreur.** Les plus longs : `zone_reveil_prairie_horizon_v1` (197 s) et `_v2` (487 s, repris après un premier arrêt à mon plafond de 400 s). Le seul échec est `tera_v2`, dont le script importe `cv2`, absent de l'environnement de contrôle ;
- **0 régression** : aucun test ok à la référence ne casse ;
- **60 tests auparavant en erreur (cache absent) passent** maintenant. Par exemple, `zone_reveil_prairie_horizon_v2` passe ses 18 tests, chaque lot `zone_zero_v2` ses 13 et le mod des entrées ses 6 ;
- 10 tests restent non-ok, tous déjà non-ok à la référence et sans lien avec les lots archivés : `etude_animations_canoniques_sky_v1` (8 : module `skytemple_files` absent), `pmd_character_pipeline` (1 : import du module `validate`, à lancer depuis son dossier) et `tera_v2` (1 : module `cv2` absent) ;
- 64 fichiers suivis (ZIP et ORA) ont été régénérés par ces builds, puis remis à l'état committé. Ils ont tous le même contenu (membres, tailles, CRC) sauf 8 paquets de `zone_zero_v2` : les quatre `*_calques_png_8px.zip` ne diffèrent que par l'horodatage d'un `.ora` embarqué, et les quatre `*_projet_pmdo_0812.zip` que par leur `README.md`, plus ancien dans la version committée que le script actuel (pour `EAF1` et `RAF3`, il ne décrit pas encore les calques `cristaux` et `reflets`). Aucun calque PNG ne diffère. Ce décalage de README existait déjà avant l'allègement et n'a pas été corrigé.

### Aperçus HTML et références

Les 175 pages HTML conservées (92 aperçus de la racine, plus celles des lots et de `source/`) ont été relues : parmi 3 984 références de fichiers (`src`, `href`, `url()`, chemins entre guillemets), **aucune n'est devenue introuvable** par rapport à l'arbre complet. Ce contrôle ne voit pas les chemins construits dynamiquement par du JavaScript, et les pages n'ont pas été ouvertes dans un navigateur.

### Restauration

`source/restaurer_lot.py` a été testé : `--liste` (avec filtre), `--a-sec`, lot inconnu (suggestions), un petit lot avec aperçu racine (16 fichiers, empreintes git identiques au commit d'archive), `--prefixe antre_` (2 518 fichiers), répétition d'une restauration (aucun doublon dans `.git/info/exclude`) et `--avec-dependances` sur 16 lots (18 lots, 1 911 fichiers, 820 Mo en 6 s). Les fichiers restaurés restent non suivis par git, et le nettoyage complet a été vérifié.

Clone neuf, simulé en local (`git clone --depth 1`, protocole pack) : 43 s, `.git` 1,9 Go et arbre 2,3 Go, contre environ 5,1 et 6,4 Go avant l'allègement. Ce dernier état ne contient pas le commit d'archive : l'outil l'a récupéré lui-même (métadonnées seules, 60 Mo de base annexe après la restauration), puis a restauré `arene_halcyon_v16` avec sa dépendance `arene_guide_couches_v14` (58 fichiers, 65 Mo, 21 s). Les fichiers sont identiques au commit d'archive (empreintes git) et les 16 tests des deux lots passent. Cette simulation n'a pas interrogé GitHub ; la récupération réelle du commit d'archive depuis GitHub (métadonnées, 1,2 Mo, 4 s) avait été mesurée plus tôt dans la session.

### Ce qui n'est pas vérifié

Ces contrôles portent sur le code, les fichiers et les tests existants. Le moteur PMDO n'a pas été lancé, la qualité artistique n'a pas été revue, et rien ici ne valide l'import dans l'éditeur. Le poids d'un clone n'a été mesuré qu'en simulation locale, pas depuis GitHub.

## Pour la suite

- Le dernier état a été ramené à 2,42 Go. Les 44 lots récents conservés pèsent à eux seuls 0,87 Go (observé du 25 au 29 septembre) ; à ce rythme, le dépôt retrouve 6 Go en moins d'un mois.
- Repère indicatif, pas une règle : mesurer le dernier état avant de pousser un nouveau lot (`git ls-files -z | xargs -0 du -cb | tail -1`) et proposer un nouvel archivage, avec la même méthode, vers 3 Go. Le contenu des lots n'est pas limité pour autant.
- Les copies dépaquetées de ce que contient déjà un ZIP représentent environ 42 % du poids des lots récents (365 Mo sur 872 Mo). Ne plus les committer demanderait un changement de convention (aujourd'hui : « PNG visibles avec leurs chemins GitHub »), **à décider avec l'utilisateur**, comme un archivage périodique des plus anciens lots avec la même méthode.
- L'historique GitHub pèse toujours environ 6,4 Go. Seuls les clones complets le paient ; les clones superficiels d'Arena ne récupèrent que le dernier état. Le réduire demanderait de réécrire l'historique (nouveaux SHA, branches à refaire) : **non fait**.

## Lots archivés (120)

Triés par poids. « Aussi retiré » : ZIP voisin et aperçus de la racine qui partent avec le lot.

| Lot | Dernière modification | Taille | Fichiers | Aussi retiré |
| --- | --- | ---: | ---: | --- |
| `world_map_texture_strict_v6` | 2026-09-23 | 166,0 Mo | 68 | — |
| `world_map_texture_strict_v5` | 2026-09-23 | 164,8 Mo | 68 | — |
| `world_map_texture_strict_v9` | 2026-09-23 | 159,9 Mo | 68 | — |
| `world_map_texture_strict_v8` | 2026-09-23 | 158,6 Mo | 68 | — |
| `final_duos_v1` | 2026-09-22 | 123,5 Mo | 34 | — |
| `references_calques_v2` | 2026-09-13 | 114,9 Mo | 379 | `apercu_references_calques_v2.html` |
| `tours_layers_v3` | 2026-09-15 | 112,2 Mo | 1 789 | `apercu_tours_layers_v3.html` |
| `cendres_grotte_eruptions_v3` | 2026-09-14 | 104,9 Mo | 605 | `apercu_cendres_grotte_eruptions_v3.html` |
| `layouts_magenta_v1` | 2026-09-14 | 104,5 Mo | 354 | `apercu_variantes_magenta_v1.html` |
| `cendres_fissures_matiere_v5` | 2026-09-14 | 98,7 Mo | 677 | `apercu_cendres_fissures_matiere_v5.html` |
| `boreales_frames_generees_v5` | 2026-09-17 | 95,8 Mo | 123 | `boreales_frames_generees_v5_pack.zip`, `apercu_boreales_generees_palette_v5.html` |
| `cendres_palette_raccord_v4` | 2026-09-14 | 94,6 Mo | 606 | `apercu_cendres_palette_raccord_v4.html` |
| `donjons_10_biomes_v1` | 2026-09-15 | 89,3 Mo | 477 | `apercu_cascades_biomes_steam_v1.html` |
| `eau_siphons_rapides_v2` | 2026-09-14 | 86,0 Mo | 303 | `apercu_eau_siphons_rapides_v2.html` |
| `tours_hooh_v1` | 2026-09-15 | 78,3 Mo | 153 | — |
| `world_map_7_continents_v2` | 2026-09-23 | 77,0 Mo | 20 | — |
| `arene_boreales_v4` | 2026-09-17 | 74,7 Mo | 110 | `arene_boreales_v4_pack.zip`, `apercu_boreales_animees_v4.html` |
| `boreales_ondulation_glace_v8` | 2026-09-18 | 74,1 Mo | 65 | `boreales_ondulation_glace_v8_pack.zip`, `apercu_arene_ondulation_glace_v8.html` |
| `arene_glace_large_v3` | 2026-09-17 | 73,2 Mo | 232 | `arene_glace_large_v3_pack.zip`, `apercu_arene_glace_large_v3.html` |
| `mont_horn_panorama_v1` | 2026-09-15 | 68,5 Mo | 680 | `apercu_mont_horn_panorama_v1.html` |
| `siphons_ecoulement_v3` | 2026-09-14 | 64,6 Mo | 527 | `apercu_siphons_ecoulement_v3.html` |
| `cote_cendres_passage_v2` | 2026-09-14 | 62,0 Mo | 723 | `apercu_cote_cendres_passage_v2.html` |
| `crooked_verdure_v1` | 2026-09-13 | 60,4 Mo | 63 | `apercu_crooked_verdure_v1.html` |
| `antre_cascades_v2` | 2026-09-15 | 59,6 Mo | 868 | `apercu_antre_cascades_v2.html` |
| `panoramas_tours_v2` | 2026-09-15 | 56,3 Mo | 215 | `apercu_panoramas_tours_v2.html` |
| `entrees_six_donjons_v1` | 2026-09-14 | 54,2 Mo | 45 | `apercu_sakura_entree_calques_v1.html` |
| `caps_terrasses_v4` | 2026-09-13 | 53,3 Mo | 65 | `apercu_caps_terrasses_v4.html` |
| `soleil_spring_v1` | 2026-09-13 | 53,2 Mo | 214 | `apercu_soleil_spring_v1.html` |
| `amp_plains_fleurie_v1` | 2026-09-14 | 52,7 Mo | 122 | `apercu_amp_plains_fleurie_v1.html` |
| `references_54d3731` | 2026-09-13 | 52,4 Mo | 164 | `apercu_references_54d3731.html` |
| `donjons_generes_dtef_v3` | 2026-09-15 | 52,2 Mo | 859 | — |
| `mont_horn_altitude_v2` | 2026-09-15 | 52,1 Mo | 680 | `apercu_mont_horn_altitude_v2.html` |
| `caps_terrasses_v3` | 2026-09-13 | 51,4 Mo | 174 | `apercu_caps_terrasses_v3.html` |
| `beach_network_v1` | 2026-09-20 | 50,7 Mo | 193 | `apercu_reseau_plage_v1.html` |
| `beach_layers_v1` | 2026-09-23 | 50,4 Mo | 290 | `apercu_beach_calques_v1.html` |
| `entrees_pmd_collection` | 2026-09-12 | 47,3 Mo | 28 | — |
| `donjons_dtef_v2` | 2026-09-15 | 46,4 Mo | 1 354 | `apercu_donjons_dtef_v2.html` |
| `corrections_spring_tours_v2` | 2026-09-15 | 43,6 Mo | 647 | `apercu_spring_applewoods_v2.html` |
| `applewoods_skygrass_v1` | 2026-09-14 | 41,5 Mo | 104 | `apercu_applewoods_skygrass_v1.html`, `apercu_pommier_et_siphons.html`, `apercu_siphons_ecoulement_v3.html` |
| `jungle_geysers_v2` | 2026-09-15 | 39,7 Mo | 671 | — |
| `retouches_zones_v6` | 2026-09-13 | 38,5 Mo | 23 | — |
| `arene_halcyon_v15` | 2026-09-18 | 37,0 Mo | 25 | `arene_halcyon_v15_pack.zip`, `apercu_arene_halcyon_v15.html` |
| `spring_arc_en_ciel_v1` | 2026-09-13 | 37,0 Mo | 152 | `apercu_spring_arc_en_ciel_v1.html` |
| `arene_halcyon_v16` | 2026-09-19 | 36,7 Mo | 27 | `arene_halcyon_v16_pack.zip`, `apercu_arene_halcyon_v16.html` |
| `boreales_suite_generee_v11` | 2026-09-18 | 35,0 Mo | 42 | `boreales_suite_generee_v11_pack.zip`, `apercu_boreale_suite_generee_v11.html` |
| `zones_pmd_20_v1` | 2026-09-14 | 33,4 Mo | 13 | `apercu_references_fideles_v1.html` |
| `cafe_multietage_v3` | 2026-09-22 | 32,0 Mo | 43 | `apercu_cafe_calques_v3.html` |
| `arene_aquatique_bois_v1` | 2026-09-15 | 31,6 Mo | 855 | `apercu_arene_aquatique_bois_v1.html` |
| `sky_peak_v1` | 2026-09-13 | 31,4 Mo | 6 | `apercu_sky_peak_ambiances_v2.html`, `apercu_sky_peak_canonique_v1.html` |
| `arene_guide_couches_v13` | 2026-09-18 | 30,5 Mo | 25 | `arene_guide_couches_v13_pack.zip`, `apercu_arene_guide_couches_v13.html` |
| `onde_boreale_v9` | 2026-09-18 | 30,2 Mo | 29 | `onde_boreale_v9_pack.zip`, `apercu_onde_boreale_v9.html` |
| `references_calques_v1` | 2026-09-13 | 30,0 Mo | 165 | `apercu_references_calques_v1.html` |
| `corrections_eau_canopy_v1` | 2026-09-14 | 29,9 Mo | 75 | `apercu_corrections_eau_canopy_v1.html` |
| `ledian_dojo_v1` | 2026-09-14 | 28,4 Mo | 80 | `apercu_ledian_dojo_v1.html` |
| `arene_guide_couches_v14` | 2026-09-18 | 28,1 Mo | 31 | `arene_guide_couches_v14_pack.zip`, `apercu_arene_guide_couches_v14.html` |
| `entrees_calques_v6` | 2026-09-13 | 27,9 Mo | 33 | — |
| `waterfall_lake_raccords_v3` | 2026-09-15 | 27,2 Mo | 771 | `apercu_waterfall_lake_raccords_v3.html` |
| `arene_glace_generee_v2` | 2026-09-17 | 26,5 Mo | 159 | `arene_glace_generee_v2_pack.zip`, `apercu_arene_glace_generee_v2.html` |
| `world_map_layers_v1` | 2026-09-23 | 26,1 Mo | 21 | — |
| `sky_peak_ambiances_v2` | 2026-09-13 | 26,1 Mo | 220 | — |
| `references_fideles_v1` | 2026-09-14 | 23,3 Mo | 161 | — |
| `waterfall_lake_demi_cercle_v4` | 2026-09-15 | 22,8 Mo | 787 | `apercu_waterfall_lake_demi_cercle_v4.html` |
| `antre_bassin_v4` | 2026-09-15 | 21,7 Mo | 465 | `apercu_antre_bassin_v4.html` |
| `foret_saisons_v1` | 2026-09-15 | 20,3 Mo | 66 | — |
| `antre_ecumes_v6` | 2026-09-15 | 18,5 Mo | 503 | `apercu_antre_ecumes_v6.html` |
| `spring_escalier_v1` | 2026-09-13 | 17,9 Mo | 16 | `apercu_spring_colonne_irisee_v1.html`, `apercu_spring_escalier_v1.html` |
| `boreales_pmdsky_v7` | 2026-09-18 | 17,6 Mo | 70 | `boreales_pmdsky_v7_pack.zip`, `apercu_ciel_boreal_pmdsky_v7.html` |
| `waterfall_lake_encastrees_v5` | 2026-09-15 | 17,3 Mo | 776 | `apercu_waterfall_lake_encastrees_v5.html` |
| `beach_extension_v2` | 2026-09-20 | 16,7 Mo | 123 | `apercu_extension_plage_v2.html` |
| `dungeon_autotiles_v1` | 2026-09-14 | 15,7 Mo | 317 | `apercu_dungeon_autotiles_v1.html` |
| `waterfall_lake_trois_v2` | 2026-09-15 | 15,5 Mo | 764 | `apercu_waterfall_lake_trois_v2.html` |
| `antre_harmonie_v3` | 2026-09-15 | 14,2 Mo | 192 | `apercu_antre_harmonie_v3.html` |
| `boreales_palette_cycling_v12` | 2026-09-18 | 14,2 Mo | 28 | `boreales_palette_cycling_v12_pack.zip`, `apercu_palette_cycling_v12.html` |
| `antre_raccords_v5` | 2026-09-15 | 13,7 Mo | 490 | `apercu_antre_raccords_v5.html` |
| `waterfall_lake_generateur_v6` | 2026-09-15 | 13,3 Mo | 767 | `apercu_waterfall_lake_generateur_v6.html` |
| `entrees_halcyon_generees` | 2026-09-12 | 12,7 Mo | 6 | — |
| `steam_cave_geysers_v1` | 2026-09-15 | 12,4 Mo | 286 | — |
| `effet_boreale_canonique_v10` | 2026-09-18 | 12,2 Mo | 28 | `effet_boreale_canonique_v10_pack.zip`, `apercu_effet_boreale_canonique_v10.html` |
| `metano_expeditions_actuel` | 2026-09-12 | 11,4 Mo | 81 | — |
| `viewport_pmdo_v1` | 2026-09-21 | 10,8 Mo | 11 | — |
| `sky_peak_canonique_v1` | 2026-09-13 | 10,2 Mo | 98 | — |
| `waterfall_lake_fidele_v1` | 2026-09-15 | 9,7 Mo | 529 | `apercu_waterfall_lake_fidele_v1.html` |
| `network_zones_multicalques_v3` | 2026-09-23 | 9,4 Mo | 93 | — |
| `spring_colonne_irisee_v1` | 2026-09-13 | 7,7 Mo | 86 | — |
| `designs_dtef_v4` | 2026-09-15 | 7,6 Mo | 113 | — |
| `casino_network_v1` | 2026-09-21 | 7,6 Mo | 47 | `apercu_casino_reseau_v1.html` |
| `falaise_metano_temoin` | 2026-09-13 | 6,4 Mo | 4 | — |
| `cafe_multietage_v1` | 2026-09-13 | 6,4 Mo | 113 | `apercu_cafe_multietage_v1.html` |
| `sky_peak_plaine_v1` | 2026-09-13 | 5,6 Mo | 5 | — |
| `spring_pulsation_v2` | 2026-09-13 | 5,1 Mo | 84 | — |
| `network_zones_multicalques_v2` | 2026-09-23 | 5,0 Mo | 91 | — |
| `network_zones_multicalques_v1` | 2026-09-23 | 4,8 Mo | 50 | — |
| `world_map_9_continents_orange_v1` | 2026-09-23 | 4,3 Mo | 5 | — |
| `map_zones_debloquees_v1` | 2026-09-22 | 4,2 Mo | 18 | — |
| `northern_calques_v1` | 2026-09-13 | 4,1 Mo | 27 | — |
| `cafe_spinda_revisite_v8` | 2026-09-21 | 3,7 Mo | 33 | `apercu_cafe_spinda_revisite_v8.html` |
| `cafe_spinda_reseau_v4` | 2026-09-21 | 3,4 Mo | 58 | `apercu_cafe_spinda_reseau_v4.html` |
| `world_map_8_continents_v1` | 2026-09-23 | 3,0 Mo | 5 | — |
| `cafe_spinda_revisite_v7` | 2026-09-20 | 2,8 Mo | 59 | `apercu_cafe_spinda_revisite_v7.html` |
| `spinda_decor_v1` | 2026-09-21 | 2,4 Mo | 45 | — |
| `waterfall_lake_etendu_v1` | 2026-09-15 | 2,3 Mo | 2 | — |
| `world_map_layers_v2_reverie` | 2026-09-23 | 2,2 Mo | 5 | — |
| `cafe_multietage_v2` | 2026-09-13 | 2,2 Mo | 121 | `apercu_cafe_multietage_v2.html` |
| `world_map_7_continents_v1` | 2026-09-23 | 2,2 Mo | 21 | — |
| `world_map_layers_v2` | 2026-09-23 | 2,2 Mo | 5 | — |
| `cafe_spinda_revisite_v6` | 2026-09-20 | 2,1 Mo | 10 | `apercu_cafe_spinda_revisite_v6.html` |
| `world_map_zones_v1` | 2026-09-22 | 1,7 Mo | 23 | — |
| `world_map_userfond_v1` | 2026-09-23 | 1,3 Mo | 5 | — |
| `world_map_9_continents_v1` | 2026-09-23 | 1,3 Mo | 5 | — |
| `spinda_torches_v1` | 2026-09-21 | 1,2 Mo | 45 | `apercu_spinda_torches.html` |
| `world_map_8_continents_reference_da_v4` | 2026-09-23 | 1,2 Mo | 5 | — |
| `world_map_8_continents_reverie_v1` | 2026-09-23 | 1,1 Mo | 5 | — |
| `world_map_8_continents_reverie_generator_v3` | 2026-09-23 | 1,1 Mo | 5 | — |
| `world_map_latest_references_v1` | 2026-09-23 | 1,1 Mo | 5 | — |
| `crooked_statique_v2` | 2026-09-13 | 0,6 Mo | 17 | — |
| `cafe_halcyon_agrandi_v1` | 2026-09-20 | 0,5 Mo | 34 | `apercu_cafe_halcyon_agrandi_v1.html` |
| `beach_sky_gradient_v3` | 2026-09-20 | 0,4 Mo | 16 | `apercu_plages_ciels_v3.html` |
| `lisiere_pmd_v1` | 2026-09-21 | 0,3 Mo | 7 | — |
| `cafe_spinda_revisite_v5` | 2026-09-20 | 0,2 Mo | 8 | — |
| `casino_bois_v1` | 2026-09-21 | 0,0 Mo | 1 | — |
