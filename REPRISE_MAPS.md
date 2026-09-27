# Reprise des maps — 20 septembre 2026

## Demande actuelle

Reprendre la création de maps avec textures canoniques. **Mise à jour du 25 septembre** : l'utilisateur a choisi une entrée de donjon sud → nord, la méthode rendu généré et les deux livrables (PNG 8 px + Ground). Premier lot : `renders/entree_vapeur_sud_nord_v1/`, biome Steam Cave choisi par l'agent et à confirmer. Les anciens travaux sont conservés. **V2** (`renders/entree_vapeur_sud_nord_v2/`) : eau façon rivière Métano, scintillements Métano, bulles de marais générées ; V1 intacte. Map suivante réalisée : **Entrée Cratère** (`renders/entree_cratere_sud_nord_v1/`, réf. Dark Crater, biome choisi par l'agent et à confirmer). Puis **Entrée Ruine** (`renders/entree_ruine_sud_nord_v1/`, réf. Sealed Ruin) et **Entrée Givre** (`renders/entree_givre_sud_nord_v1/`, réf. Frosty Forest, neige). Puis **Entrée Bristle** (`renders/entree_bristle_sud_nord_v1/`, réf. Mt. Bristle, canyon de sable et torrent). **Nouveau standard demandé (26 septembre) : maps plus vastes au format 4:3** — premier lot `renders/entree_jungle_sud_nord_v1/` en 768 × 576 (96 × 72 cases). L'utilisateur a demandé de continuer la série de maps.

Reprise du 25 septembre : `.venv` absente du checkout puis recréée (Pillow 12.3, NumPy 2.4, SciPy 1.17). Les tests V16 + sud–nord V3 donnent de nouveau 18/19, avec la même erreur liée à l'objet historique `438b9288`.

Reprise du 26 septembre, 09 h 20 UTC (session `arena/01a0dd03`, branchée sur `0eaa002c` = Entrée Jungle V1) : lecture de `README.md`, `AGENTS.md`, `MANUEL_METHODE_PMDO.md`, de ce fichier, des `WORKFLOW.md`, des README de méthode (zones guidées, audit d'import, Sky Peak canonique, sud–nord V3, runtime PMDO), du gabarit Jungle et de ses utilitaires. `.venv` recréée (Pillow 12.3, NumPy 2.4, SciPy 1.17). Le `build.py` Jungle, relancé en 17 s, redonne des sorties byte-identiques aux fichiers versionnés, sauf les horodatages ZIP internes de l'ORA (16 membres identiques, fichier restauré) ; **9 tests PASS**. **Distant vérifié : trois branches sœurs issues de la même base contiennent du travail absent d'ici**, dont la dernière correction de méthode de l'utilisateur (sections suivantes). Rien n'a été fusionné sans son accord, et aucune nouvelle map n'a été produite dans cette reprise.

**Décision de l'utilisateur, même session** : « tu dois utiliser la méthode et reprendre seulement de ta branche parente. Et refaire waterfall avec la génération fond majenta multicalque ». On ne fusionne pas les branches sœurs et on n'en reprend rien. Lot réalisé : **Entrée Waterfall Cave** (`renders/entree_waterfall_cave_sud_nord_v1/`, préfixe `EWC1`, réf. `entrancecascade.png`, aperçu `apercu_entree_waterfall_cave_sud_nord_v1.html`) : rendu généré référencé, décor sur magenta, 16 calques, cascade, écume et embruns animés, 13 tests PASS. **Retours sur EWC1, puis EWC2** (`renders/entree_waterfall_cave_sud_nord_v2/`, aperçu `apercu_entree_waterfall_cave_sud_nord_v2.html`, mêmes bruts) : liseré clair de rive retiré, couloir de sable jusqu'à la grotte (plus d'eau devant), cascade en deux temps (fermée → fente qui s'ouvre → ouverte, calques d'état), 15 tests PASS. **EWC3** (`renders/entree_waterfall_cave_sud_nord_v3/`, aperçu `apercu_entree_waterfall_cave_sud_nord_v3.html`) : autre lecture de « la cascade se fend ». Le rideau se fend en deux sur toute sa hauteur et ses moitiés s'écartent devant une paroi générée (4e brut : décor EWC1 édité sans la cascade). Le reste est identique à EWC2, 17 tests PASS. Carte suivante, biome choisi par l'agent à la demande de l'utilisateur (« go carte suivante choisis ! ») : **Entrée Underground Lake** (`renders/entree_underground_lake_sud_nord_v1/`, préfixe `EUL1`, aperçu `apercu_entree_underground_lake_sud_nord_v1.html`). Rendu généré référencé, lac aux couleurs exactes du rip sans liseré clair, lueur qui respire, gouttes et ronds générés, 11 calques, 15 tests PASS. L'utilisateur a demandé ensuite de passer à la map suivante : **Entrée Mystifying Forest** (`renders/entree_mystifying_forest_sud_nord_v1/`, préfixe `EMF1`, réf. `Mystifying_Forest_entrance_TDS.png`, aperçu `apercu_entree_mystifying_forest_sud_nord_v1.html`, biome choisi par l'agent, à confirmer). Elle a été faite par rendu généré référencé : mare en magenta, 11 calques, eau sans liseré, feuilles et lucioles générées, 13 tests PASS.

Reprise du 27 septembre (session `arena/01a0e2f1`, branchée sur `95160e32` = EUL1) : sur « poursuis le projet », lot **Entrée Sables mouvants** (`renders/entree_sables_mouvants_sud_nord_v1/`, préfixe `EQS1`, réf. `witheringdesert.png` = Furnace Desert, aperçu `apercu_entree_sables_mouvants_sud_nord_v1.html`). Biome choisi par l'agent, **à confirmer**. Fosse de sable mouvant, chutes de sable, poussière et rayons animés ; 14 tests PASS.

Même jour, sur « poursuis les prochaines maps ! faut tourner le serveur dans la session arena » : lot **Entrée Star Cave** (`renders/entree_star_cave_sud_nord_v1/`, préfixe `ESC1`, réf. `starcavepmdsky.png`, aperçu `apercu_entree_star_cave_sud_nord_v1.html`). Biome choisi par l'agent, **à confirmer**. Étoiles aux formes exactes du rip, reflets des cristaux et poussière d'étoile animés ; 13 tests PASS.

Même jour, sur « continue ! » : lot **Entrée Clairière tropicale** (`renders/entree_clairiere_tropicale_sud_nord_v1/`, préfixe `ETC1`, réf. `large.S01P03A.png.84e22fb77c4061e77b0f546545fed2c7.png`, aperçu `apercu_entree_clairiere_tropicale_sud_nord_v1.html`). Biome choisi par l'agent, **à confirmer**. Arrivée par un ponton sur la mer, clairière de palmiers et d'hibiscus, entrée dans un tertre au nord ; mer aux profil, crête et couleurs exacts du rip, sans liseré ; papillons générés ; 15 calques, 13 tests PASS.

Même jour, sur « Push et passe a la prochaine ! » : lot **Entrée Couloir violet** (`renders/entree_couloir_violet_sud_nord_v1/`, préfixe `ECV1`, réf. `large.S05P03A.png.301f7a1eadda348357be0801e81faa2a.png`, aperçu `apercu_entree_couloir_violet_sud_nord_v1.html`). Biome choisi par l'agent, **à confirmer**. Arrivée par un couloir étroit au sud, grande salle semée de blocs, tunnel sous une arche de rochers au nord ; éboulis animés avec des gravillons exacts de la capture, poussière générée ; 11 calques, 12 tests PASS.

Même jour, sur « Continue ! Très bon travail » : lot **Entrée Mt. Thunder** (`renders/entree_mt_thunder_sud_nord_v1/`, préfixe `EMT1`, réf. `Game Boy Advance - Pokemon Mystery Dungeon_ Red Rescue Team - Dungeon Boss Rooms - Mt. Thunder.png`, aperçu `apercu_entree_mt_thunder_sud_nord_v1.html`). Biome choisi par l'agent, **à confirmer**. Crête de sable qui sort des nuages au sud, plateau du sommet à gradins, grotte dans un piton au nord ; éclairs et arc « Flash » copiés de la planche, couleurs Normal / Fading exactes ; 12 calques, 10 tests PASS.

Même jour, sur « Lance la suite ! » : lot **Entrée Jardin secret** (`renders/entree_jardin_secret_sud_nord_v1/`, préfixe `EJS1`, réf. `secretgarden.png`, aperçu `apercu_entree_jardin_secret_sud_nord_v1.html`). Biome choisi par l'agent, **à confirmer**. Allée entre deux haies au sud, grande prairie fleurie, souche dorée à marches au nord sous un rayon de lumière ; rayon qui respire sur la rampe exacte du rip, lucioles aux couleurs exactes ; 14 calques, 11 tests PASS. **Après ce lot, plus aucune capture de la racine n'est libre pour une entrée, sauf `oldcastlepmd` (un intérieur) : demander la direction à l'utilisateur.**

Même jour, sur « j'aimerais que tu regardes les animations canoniques des map magma / de l'eau par exemple sur la map S01P02A » : **étude** `renders/etude_animations_canoniques_sky_v1/` (source `source/etude_animations_canoniques_sky_v1/`, aperçu `apercu_etude_animations_canoniques_sky_v1.html`). Fichiers de la ROM lus depuis `pret/pmd-sky` : l'eau et la lave sont des rotations de palette, avec leurs vraies durées. Le Ground du port `PMD-SKY-PMDO-PORT` dédoublonne les frames et fixe `FrameLength` à 10 : lave fausse 72 à 89 % du temps. Pistes exactes calculées et vérifiées tick par tick ; 9 tests PASS. **Suite proposée, à faire confirmer** : appliquer le vrai cycle de palette à nos cartes (ETC2 avec la mer de s01p03a, carte de magma avec le cycle de d41p41a), ou porter fidèlement des cartes du port.

Même jour, sur la demande de la **zone de départ** (« zone où le Pokémon se réveille », grande prairie à la Sky Peak, « falaise sans relief », mer en contrebas « comme la mer animée dans PMD Sky » avec bulles, nuages qui passent, jour et nuit) : lot **ZRV1**. C'est la zone de réveil (`renders/zone_reveil_prairie_horizon_v1/`, aperçu `apercu_zone_reveil_prairie_horizon_v1.html`, 12 tests PASS).

- Trois Grounds : jour, aube (ajoutée) et nuit.
- La mer suit la rotation de palette exacte de s01p02a ; son motif de bandes est le nôtre.
- L'écume et les bulles sont l'exception explicite à la règle « pas de liseré blanc ».
- ZRV1 n'est **pas dans le mod unique**. C'est une zone, pas une entrée de la série : l'y ajouter seulement si l'utilisateur le demande.

Même jour, sur « regarde l'animation de la mer V24P04A et des nuages, c'est ce que je te demandais pour la zone réveil », puis « je veux garder le layout de la v1 juste corrige la mer et le background laisse la montagne mais faut que les nuages soient derrière la montagne : la mer ⇒ montagne ⇒ nuage » : lot **ZRV2** (`renders/zone_reveil_prairie_horizon_v2/`, aperçu `apercu_zone_reveil_prairie_horizon_v2.html`, 16 tests PASS).

- Layout de ZRV1 inchangé.
- Mer générée avec V24P04A en référence et animée par ses lois : houle 12 × 10, scintillement 16 × 4.
- Ciel, nuages, montagne et mer sur des calques séparés. Les nuages défilent derrière la montagne de ZRV1, dont les flancs sont prolongés jusqu'à l'horizon.
- Reflet animé de la lune et du soleil ; fleurs A B A C.
- ZRV1 est gardée. ZRV2 n'est **pas dans le mod unique**.
- Ensuite, « je valide l'ensemble », avec des ajustements : reflets générés, nuages sans rognure (dôme), vagues sans interstices, **crépuscule ajouté** (4 Grounds), écume et bulles de ZRV1, et la cadence de houle décodée de V24P04A (`references/v24p04a_12_crans_bpa.png`).

Même jour, sur « Je veux un petit temple miniature qui tiens sur la buche celebi gardien secret » puis « lance la suite ! » : lot **EJS2**, Jardin secret V2 avec le temple de Celebi (`renders/entree_jardin_secret_sud_nord_v2/`, aperçu `apercu_entree_jardin_secret_sud_nord_v2.html`, 13 tests PASS). Un seul brut nouveau, collé sur la souche ; le reste est le décor d'EJS1 au pixel près. La porte du temple est l'entrée, et Celebi est un emblème qui luit. Ce sont des choix de l'agent, **à confirmer**. EJS2 est ajoutée au mod unique (19 cartes, version 1.1.0.0).

Même jour, sur « BEAU TRAVAIL JE VALIDE PREPARELE MOD AVEC TOUTE CES CARTE ET LANCE LA SUITE ! » : **série validée par l'utilisateur**, et **mod unique** des 18 entrées (`renders/mod_guilde_entrees_v1/guilde_entrees_sud_nord_pmdo_0812.zip`, namespace `guilde_entrees_sud_nord`, galerie `apercu_mod_guilde_entrees_v1.html`, source `source/mod_guilde_entrees_v1/`, 6 tests PASS). Chaque nouvelle carte de la série doit être ajoutée à `MAPS` dans `build_mod.py`.

**Serveur d'aperçus, à relancer au début de chaque session** : `python3 source/serveur_apercus/serve.py --port 8000`, via l'outil de processus de fond. Il écoute sur 0.0.0.0 et sa page d'accueil liste tous les aperçus, les entrées sud → nord en tête.

## Branches sœurs de la série (relevé du 27 septembre)

Cinq sessions sont reparties de la même base que `arena/01a0dd03` (`95160e32`) ; `01a0e017` travaille sur un autre historique. Aucune n'a été fusionnée et rien n'en a été repris. Leurs têtes étaient identiques au démarrage et avant le commit d'EQS1.

| Branche | Tête | Préfixes ajoutés |
|---|---|---|
| `arena/01a0de11` | `6d72314e` | EFF1, EFF2, EDP1, ECF1, ECC1, ECC2, ESJ1, ESR1, EWL1, TMA1-3, ZGE1, ZGA1 |
| `arena/01a0dfad` | `ab2d40e6` | EJT1 |
| `arena/01a0dfe2` | `f0918bd1` | aucun (reprise documentaire de `REPRISE_MAPS.md`) |
| `arena/01a0e001` | `fc94f5a6` | EFF1 (autre lot Foggy Forest, **même préfixe** que sur `01a0de11`) |
| `arena/01a0e017` | `46a1f159` | aucun préfixe `E__1` ; autre historique (pas de base commune), cartes glace et cristal |
| `arena/01a0e2db` | `66afe893` | ESP1, ESP2 |

Préfixes de ces six branches : EFF1, EFF2, EDP1, ECF1, ECC1, ECC2, ESJ1, TMA1-3, EWL1, ESR1, ZGE1, ZGA1, EJT1, ESP1, ESP2. **Préfixes pris, toutes branches confondues** : ceux de la liste ci-dessous, plus ceux-ci, plus EQS1, ESC1, ETC1, ECV1, EMT1, EJS1, EJS2, ZRV1 et ZRV2.

`git fetch` ne récupère que `main` dans ce checkout. Pour inspecter les branches, passer les refspecs `+refs/heads/arena/…:refs/remotes/origin/arena/…`. Les quelque 60 autres branches `arena/*` sont d'anciennes sessions (5 au 25 septembre), sur d'autres historiques. Il faut quand même y chercher le nom de la référence visée (`git grep -l <ref> origin/<branche>`) : c'est ainsi qu'on a trouvé l'usage de `witheringdesert.png` par `01a0d498`.

## Branches sœurs non intégrées, premier relevé (relevé du 26 septembre, 09 h 30 UTC)

La branche parente `arena/01a0da3c` est toujours à `0eaa002c`, mais cela ne prouve pas l'absence de travail parallèle : plusieurs sessions peuvent repartir de cette même base. Au démarrage, lister `git ls-remote --heads origin` et inspecter les branches `arena/*` récentes, pas seulement la parente.

| Branche | Commits après `0eaa002c` | Lots | Référence principale |
|---|---|---|---|
| `arena/01a0db11` | `76e42a0e` | EGC1 Entrée Grotte des Cascades (terrain et eau générés, eau 12 × 10 ticks) | `Waterfall_Cave_ledge_TDS.png` |
| `arena/01a0dc8e` | `ccdbde18`, `91aa92d2`, `284303c2` | EAN1 Amp, EHN1 Horn, EWN1 Waterfall (grotte aux gemmes) ; bruts guidés par le rip, fidélité mesurée par test | Amp Plains, Mt Horn, `Waterfall_Cave_gem_TDS.png` |
| `arena/01a0dc9b` | `c1549ba3`, `25cac19d`, `f6647b7c` | reprise ; ECN1 Cascade V1 en pixels natifs (pas la méthode demandée) ; **ECN2 Cascade V2, rendu généré référencé = livrable corrigé** | Waterfall Cave ledge + gem |

Points d'attention :

- **Trois entrées Waterfall Cave en doublon** (EGC1, EWN1, ECN2, plus ECN1 native). L'utilisateur a tranché : reprendre seulement de la branche parente, et refaire Waterfall ici (EWC1). Les branches sœurs restent telles quelles, non fusionnées.
- **Le préfixe `ECN1` est pris deux fois** : par l'Entrée Cratère (ici) et par la Cascade V1 (`01a0dc9b`). Les banques `.tile` sont distinctes, mais des PNG `ECN1_*` de deux lots différents sont ambigus pour « PNG to Tileset », qui nomme par basename. Préfixes déjà pris, toutes branches confondues : ESN1, ESN2, ECN1, ERN1, EGN1, EBN1, EJN1, EGC1, EAN1, EHN1, EWN1, ECN2, EWC1, EWC2, EMF1, EWC3, EUL1.
- Une fusion toucherait `README.md` (insertions en tête), `AGENTS.md` (ajouts en fin) et ce fichier. Ce sont des conflits purement documentaires, à résoudre par union ; les lots sont des dossiers nouveaux, sans chevauchement.

## Règle « textures canoniques » — état consolidé

Dernière consigne de l'utilisateur (session `01a0dc9b`, après la Cascade V1) : « tu dois utiliser ton générateur d'image tu as mal audité l'ancienne méthode ». Pour la série des entrées sud → nord :

1. **« Textures canoniques » = rendu généré RÉFÉRENCÉ.** Le rip canonique du biome est passé au générateur en image de référence (`images=[rip]`). Le décor reproduit ses textures, sa palette et son style de pixel sur un layout nouveau (« même endroit, autre lieu », consigne donnée pour Amp). Exemple type : le brut Bristle est presque identique au rip Mt. Bristle.
2. Ce n'est **pas** un relayout de pixels natifs (`zones_south_north_v3`, Cascade V1). Cette méthode ne s'emploie que si l'utilisateur la nomme explicitement. Les règles de copie native Métano restent réservées aux extensions de Métano.
3. Mesurer la fidélité de la matière principale contre le rip : moyenne RGB sur masque, distance sous un seuil documenté (Amp 9,6 < 35 ; Waterfall 17,0 < 40 ; Horn 34,8 < 40). Écarter un brut non conforme plutôt que de le corriger en silence.
4. Ne jamais présenter les pixels générés comme des tuiles natives certifiées. Seuls les scintillements, et la cascade de ECN2, sont des pixels Métano natifs.
5. La méthode vaut pour les **nouvelles** maps, sans reprendre les livraisons existantes. Si le sens de « canonique », la référence ou la portée d'un lot est ambigu, demander avant le build (consigne `01a0db11`).

## Méthode courante des entrées sud → nord (résumé opératoire)

Gabarit 4:3 à copier : `source/entree_jungle_sud_nord_v1/` (`build.py`, `test_build.py`, `package.py`, `viewer_template.html`, `README_PACK.md`). Outils partagés, chargés par `loadmod`. Les builders de la série n'écrivent qu'à l'appel de `build()`, mais certains anciens builders écrivent dès l'import : lire le code avant.

| Outil | Fichier |
|---|---|
| `keep_large`, `quantize_layers` (96 couleurs), `place`, `cell_grid`, `write_ora`, `sparkle_families` | `source/entree_bristle_sud_nord_v1/build.py` (régler `BM.W, BM.H`) |
| `down_class` (réduction BOX par classe), `water_phases` façon Métano, `ground_project` 4:3 | `source/entree_jungle_sud_nord_v1/build.py` |
| `reachable` (BFS, personnage 16 × 16) | `source/entree_sud_nord_generee_v1/build.py` |
| `decode_tile` ; `extract_poses` (planches de poses) | `source/entree_vapeur_sud_nord_v2/build.py` ; `source/entree_ruine_sud_nord_v1/build.py` |
| `TileBank`, `layer`, `save`, `write_dir` (codec Ground et `.tile`) | `source/pmdo_cote/build.py` |
| `read_node`, `encode_index`, `read_index`, installateur avec fusion d'index | `source/pmdo_cote/INSTALLER.py` |
| Lecteur natif `.tile` des tests (`tiles`, `straight`) | `source/cote_v5_expeditions/audit_references.py` |
| Gabarit `.rsground` 0.8.12 | `mod_metano_expeditions_pmdo_0812.zip` → `v50812_01_crete_sillage_jour.rsground` |

Étapes :

1. **Générer** dans `bruts/`, avec le rip du biome en `images=` : `decor_magenta.png` (décor complet, eau ou lave en magenta, « WIDE LANDSCAPE 4:3, zoomed out » → 1200 × 896), `sol_complet.png` (même cadrage, sol seul ; à défaut, quilting depuis le sol du décor comme ECN2) et une planche de poses pour l'animation propre au biome. Si rien ne revient, relancer avec un prompt plus court. Choisir les cases de planche à la main : le générateur respecte rarement la grille demandée.
2. **Segmenter en pleine résolution** (`classify`, seuils mesurés et commentés), puis **réduire par classe** (`down_class`, ×576/896, recadrage centré à 768 × 576 ; jamais l'image entière avant la segmentation). Palette commune de 96 couleurs, palettes séparées pour les matières qui virent (arbres, cristaux).
3. **Animer chaque effet sur son calque** : eau façon rivière Métano 4 × 10 ticks (couleurs Métano exactes si le biome le permet, sinon rôles Métano ou couleurs du rip), scintillements Métano natifs, poses générées réduites uniformément. Boucle fermée testée, dernière → première comprise ; scène au PPCM des cadences.
4. **Collisions et accès** : `cell_grid` (case bloquée si plus de 25 % non praticable), `entrance` au sud, `donjon_seuil` sous la bouche, chemin 16 × 16 prouvé par `reachable`, aucun warp.
5. **Exports** : `PFX_NN_nom.png`, `animation/<effet>/`, masques, ORA, `review/` (scène t000, WebP, collisions), `manifest.json` (hashes des bruts, normalisation, origine de chaque matière, `art_approved: false`, `runtime_tested: false`).
6. **Ground PMDO 0.8.12** : une banque `.tile` par calque, un calque Top vide (`Layer=4`), `index.idx`, `Mod.xml`, `INSTALLER.py`, staging dans `.cache/<lot>/`.
7. **Tests puis paquet** (`test_build.py`, `package.py`). Documenter le lot, `README.md`, `AGENTS.md` et ce fichier, puis **commit + push sur la branche de session après vérification des branches sœurs**.

`.venv` et `.cache` ne sont pas persistés : recréer la première, puis relancer le `build.py` d'un lot avant ses tests, qui relisent le Ground dans `.cache`. Un rebuild réécrit l'ORA avec de nouveaux horodatages ZIP : restaurer le fichier s'il n'a pas d'autre changement.

`entrancecascade.png` (vraie entrée de Waterfall Cave) sert désormais à EWC1. `Mystifying_Forest_entrance_TDS.png` sert désormais à EMF1. `Underground_Lake_shore_TDS.png` sert désormais à EUL1 (lac souterrain, chaussée jusqu'à la grotte). `witheringdesert.png` (Furnace Desert, *Rescue Team*) sert désormais à EQS1. Il servait déjà hors de la série : duo désert DB1 dans `dungeon_biomes_v1`, biome swap en eau dans `01a0d498`. **Les références que ce paragraphe donnait comme libres (Foggy Forest Base Camp, Sealed Ruin pit, Southern Jungle exit 2, etc.) ont toutes été prises sur les branches sœurs** (relevé du 27 septembre). `starcavepmdsky.png` sert désormais à ESC1. `secretgarden.png` sert désormais à EJS1. Rips de la racine encore jamais pris comme référence d'une entrée de la série : rockgeyserlike, Steam_Cave_Peak_TDS, secretgarden, energeticforest, finalisland, roadundergound, junglewaterfallzonepmdsky, oldcastlepmd, volcanicpit (1). Certains servent déjà hors série : energeticforest, finalisland et volcanicpit dans DB1 ; secretgarden sur les anciennes branches `01a0d315` et `01a0d4b6`. **Correction (27 septembre, relevé `git grep` sur les 72 têtes et main)** : le relevé d'ESC1 donnait à tort roadundergound et rockgeyserlike comme « libres partout ». Tous deux ont servi de relayouts natifs sur d'anciennes branches non fusionnées : rockgeyserlike dans `source/zones_rock_layouts_v1/build.py` de `01a0b211` ; roadundergound dans ce même lot et dans `zones_south_north_v4` de `01a0d42e` et `01a0d546` (plus les inventaires `banque_canonique` de `01a0ca50`, `01a0d315`, `01a0d546`). Les geysers sont en outre déjà un motif de notre base (`jungle_geysers_v2`, `steam_cave_geysers_v1`). junglewaterfallzonepmdsky est pris aussi (`maps_v17_spec` de `01a0be56`, `jungle_cascades_v1` de `01a0cf23`). Seul oldcastlepmd (salle au trésor, un intérieur) n'est utilisé nulle part. `large.S01P03A…png` (clairière tropicale) sert désormais à ETC1 ; il n'était cité que par l'inventaire `zones_bg_audit_v1`. Autres relevés du même jour : `lakecrystalpmdsky` et `bassinchauffantpmdsky` sont pris sur `01a0e017` (sanctuaire de cristal, bassin chauffant) ; `large.P04P01C` est dans `references_fideles_v1` de dizaines de branches ; `large.P27P01A` est cité par `maps_v17_spec` (`01a0be56`) ; **`large.S05P03A` (couloir rocheux violet) n'est utilisé nulle part**. Il sert désormais à ECV1. Il ne reste alors, parmi les rips de la racine relevés ce jour, que `oldcastlepmd` (un intérieur) de libre partout ; les autres candidats ont été relevés au lot suivant (EMT1). **Relevé complet (lot EMT1, 97 images de la racine, clés courtes)** : `git grep -o -h -I -F -f clés.txt` sur les 72 têtes, un appel par tête ; clés = code des `large.*`, nom du lieu pour les noms GBA/DS, radical pour les autres (les noms complets sous-comptent : `Murky Forest` 0 au lieu de 56). Plus aucune image n'est libre partout, sauf `oldcastlepmd` (un intérieur) ; `large.P21P02A` est un doublon de `forêtglomypmdsky` (48 branches). Jamais utilisées pour une entrée de la série mais déjà utilisées hors série : `Mt. Thunder` (`mt_thunder_orage_v1` sur `01a0d8a8`, `01a0d9b3`, `01a0d9f7` ; désormais EMT1) et `secretgarden` (`01a0d315`, `01a0d4b6`). Dark_Crater, Foggy_Forest_Base_Camp, Sealed_Ruin, Southern_Jungle, energeticforest, finalisland et volcanicpit sont pris (entrées sœurs ou DB1). **Méthode de relevé** : `git grep -l -I -F <nom> origin/<branche> -- '*.py' '*.md'` sur **chaque** tête (refspecs explicites) et main, en écartant les inventaires (zones_relayout, zones_bg_audit, banque_canonique, README/AGENTS/REPRISE). Un relevé par nom de dossier de lot, ou sur quelques branches seulement, ne suffit pas : c'est ce qui a produit l'erreur ci-dessus.

## Repérage effectué

- 141 fichiers README recensés ; parcours de leurs présentations et statuts, lecture approfondie des méthodes et lots pertinents pour les maps.
- Instructions dans `AGENTS.md`, historique de `README.md`, manuel `MANUEL_METHODE_PMDO.md`, audit `audits/metano_import/RAPPORT.md` et méthode `source/layouts_magenta_v1/WORKFLOW.md` consultés.
- 353 scripts Python recensés et analysés syntaxiquement : aucune erreur de syntaxe. Ce n’est pas une exécution de tous les scripts.
- 74 fichiers `.tile` présents sous `source/` ; ce nombre inclut des références de différents lots, pas nécessairement 74 textures distinctes.
- Inspection visuelle du témoin canonique Métano, de la forêt sud–nord V3 et de la composition d’arène V16.

## Contrat à préserver

Deux méthodes historiques coexistent :

1. **Rendu généré référencé PMD** : composition complète avec références canoniques, terrain sur magenta, détourage, plans de profondeur, fonds et effets séparés. La correction explicite de l’arène rejette une mosaïque de bouts de maps. Ne pas revenir silencieusement à cette méthode rejetée.
2. **Pixels natifs exacts** : prélèvements documentés, modules complets cohérents, pas de rotation/miroir/redimensionnement/recoloration des textures de jour. C’est notamment la route d’import native Métano. Un dessin généré même remis dans la palette source n’est pas une extraction canonique.

La demande actuelle insiste sur les textures canoniques : annoncer clairement l’origine de chaque matériau et ne pas certifier une génération comme pixel-exacte. Choisir la méthode en fonction de la map demandée, sans réimposer les contraintes spécifiques de Métano à tous les biomes.

Dans les deux cas : conserver la DA, l’échelle, les raccords, les volumes et les accès lisibles ; éviter les falaises fragmentées en cellules indépendantes. Préserver les compositions approuvées. Pour les entrées concernées par la correction historique : arrivée sud, progression vers l’entrée au nord.

## Points d’entrée utiles

| Besoin | Sources / outils |
|---|---|
| Composition générée, magenta, calques | `source/layouts_magenta_v1/WORKFLOW.md`, `palette.py`, `build.py` |
| Modules natifs Métano | `source/cote_v4_abyss/natifs/`, `prepare.py`, `sample.py` |
| Nuit Abyss exacte | `source/cote_v4_abyss/night.py` ; ne pas cumuler les filtres |
| Eau native Métano | `source/eau_metano/natifs/`, `source/build_water_metano.py`, `source/verify_water_metano.py` |
| Entrées sud–nord, provenance par pixel | `source/zones_south_north_v3/`, `exports/zones_south_north_v3/manifest.json` |
| Sky Peak, terrain original | `renders/sky_peak_canonique_v1/README.md`, `source/sky_peak_v1/build_canonique.py` |
| Donjons/autotiles natifs | `renders/donjons_dtef_v2/README.md`, `source/donjons_dtef_v2/` |
| Dernière arène générée | `source/arene_halcyon_v16/`, `renders/arene_halcyon_v16/` |
| Export Ground, ressources, index | `source/pmdo_cote/`, `source/cote_v5_expeditions/`, manuel PMDO |
| Procédure de restauration du runtime | `source/pmdo_runtime/README.md` |

Attention : certains anciens builders écrivent leurs exports dès l’import Python. Lire le code avant de les importer ou de les relancer.

## Livraison et contrôle attendus

- PNG transparents alignés, noms uniques, manifeste des positions et ordre des couches ; ORA éditable lorsque le pipeline le prévoit.
- Sol, chemin, parois/relief, entrée, végétation, premier plan, ciel et effets séparés selon les besoins. Des plans visibles découpés ne constituent pas automatiquement des objets complets avec faces cachées.
- Animations sur leurs propres calques : taille constante, cadence documentée, vérification de toutes les transitions, y compris dernière → première. Ne pas appeler une animation créée un cycle officiel récupéré.
- Prévisualisation à 1× et zoom entier, contrôle de recomposition et de provenance ; test moteur séparé.
- **Ground/PNG to Tileset : généralement 8 px pour nos packs. DTEF : sources à 24 px, feuilles 432×192, 47 configurations utiles par bloc. Ne pas confondre les routes d’import.**
- Collisions, occlusion, warps et gameplay ne sont jamais déduits des seuls contrôles d’images.

## État technique vérifié dans cette session

Environnement `.venv` recréé avec Pillow, NumPy et SciPy ; ignoré par Git. OpenCV et Playwright non installés lors de ce repérage. Node et GitHub CLI disponibles ; Aseprite/Tiled/PMDC non trouvés dans PATH. Le cache runtime décrit par les anciens README est absent ici.

Commande réellement exécutée :

```sh
.venv/bin/python -m unittest source.arene_halcyon_v16.test_build source.zones_south_north_v3.test_build -v
```

**19 tests : 18 réussis, 1 en erreur.** L’erreur est `test_original_sources_unchanged`, qui appelle `git show 438b9288:...` : cet objet historique est absent du checkout. Vérification séparée des SHA-256 des cinq sources contre le manifeste : **5/5 conformes**. Cela ne remplace pas la comparaison historique manquante. Aucun test n’a été affaibli ou modifié.

Réserves relevées dans V16 :

- La dénomination « boucle parfaite » repose sur un seuil de différence des masques, pas sur une preuve de continuité du mouvement. Une revue animée reste nécessaire.
- Des commentaires/champs générés du builder parlent encore de 8 frames/planche 2×4, alors que le code et les exports testés en utilisent 10/2×5. À corriger dans une intervention dédiée, sans reconstruire aveuglément les anciens exports.
- L’alignement sur 8 px et le nommage Halcyon ne prouvent pas un import moteur.

Les succès de chargement PMDO cités dans les anciens rapports restent historiques ; aucun lancement PMDO, rendu GPU ou test de gameplay n’a été effectué dans cette reprise.
