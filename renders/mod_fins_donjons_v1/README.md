# Guilde Treehouse — fins de donjon (11 Grounds) — mod PMDO 0.8.12

Mod d’édition autonome, namespace `guilde_fins_donjons`. Il rassemble **9 cartes de la série principale**, dans l’ordre du mod, et **2 cartes conservées en complément** (ancienne variante de Givre et map Océan hors-série). Les onze Grounds sont au format 768 × 576 px, grille 8 px (96 × 72 cases), et gardent leurs calques PMDO, animations, collisions et marqueurs propres.

**Assemblage sans retouche des maps :** banques `.tile`, Grounds `.rsground` et scripts Lua sont copiés octet pour octet depuis les ZIP projets individuels. Seuls l’index des banques est fusionné et les scripts sont rangés sous le namespace commun. Les README et manifestes de chaque lot restent la référence pour sa méthode artistique et la provenance de ses pixels.

## Installer

- **Mod séparé** : extraire `guilde_fins_donjons` dans `PMDO/MODS/`, activer le mod puis ouvrir un Ground dans l’éditeur PMDO.
- **Mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, vérifier le plan, puis relancer sans `--dry-run`. L’installateur fusionne `index.idx`, fait une sauvegarde et refuse d’écraser un fichier différent.

## Série principale et compléments

| Ordre | Préfixe | Carte | Ground | Calques (bas → haut) | Animations (calque : frames × ticks) | Marqueurs |
|---:|---|---|---|---|---|---|
| 1 | **FVS1** | Fin Vapeur — sommet de Steam Cave<br>Série — 01 | `fvs1_fin_vapeur_sommet` | 00 eau source 4 phases → 01 bulles 24 phases → 02 sol complet → 03 sol arene → 04 margelle → 05 events → 06 stalagmites → 07 vapeur 24 phases → 08 Vos elements avant-plan (Top) | 00 eau source 4 phases : 4 × 10 ticks; 01 bulles 24 phases : 24 × 5 ticks; 07 vapeur 24 phases : 24 × 5 ticks | `entrance` (384, 560), `boss` (376, 344), `source` (376, 224) |
| 2 | **FCF1** | Fin Cratère — fosse de Dark Crater<br>Série — 02 | `fcf1_fin_cratere_fosse` | 00 lave 4 phases → 01 eclats 4 phases → 02 bulles 24 phases → 03 sol complet → 04 sol plateau → 05 rebord → 06 pitons → 07 embleme → 08 lueur 6 phases → 09 Vos elements avant-plan (Top) | 00 lave 4 phases : 4 × 10 ticks; 01 eclats 4 phases : 4 × 10 ticks; 02 bulles 24 phases : 24 × 5 ticks; 08 lueur 6 phases : 6 × 10 ticks | `entrance` (384, 560), `boss` (376, 288), `embleme` (376, 96) |
| 3 | **FRP1** | Fin Ruine — puits de Sealed Ruin<br>Série — 03 | `frp1_fin_ruine_puits` | 00 sol complet → 01 ombre parois → 02 aura 6 phases → 03 tourbillons 8 phases → 04 parois → 05 cle de voute → 06 fissure 6 phases → 07 feux follets 24 phases → 08 Vos elements avant-plan (Top) | 02 aura 6 phases : 6 × 10 ticks; 03 tourbillons 8 phases : 8 × 5 ticks; 06 fissure 6 phases : 6 × 10 ticks; 07 feux follets 24 phases : 24 × 5 ticks | `entrance` (384, 560), `boss` (384, 288), `cle_de_voute` (376, 176) |
| 4 | **FGG2** | Fin Givre V2 — Frosty Grotto sous les aurores<br>Série — 04 | `fgg2_fin_givre_aurore` | 00 eau glacee 4 phases → 01 reflets 4 phases → 02 sol complet → 03 ciel → 04 etoiles 12 phases → 05 aurore 12 phases → 06 sol glace → 07 parois → 08 flocons 48 phases → 09 Vos elements avant-plan (Top) | 00 eau glacee 4 phases : 4 × 10 ticks; 01 reflets 4 phases : 4 × 10 ticks; 04 etoiles 12 phases : 12 × 10 ticks; 05 aurore 12 phases : 12 × 10 ticks; 08 flocons 48 phases : 48 × 5 ticks | `entrance` (384, 560), `boss` (376, 304), `belvedere` (376, 184) |
| 5 | **FBS1** | Fin Bristle — sommet de Mt. Bristle<br>Série — 05 | `fbs1_fin_bristle_sommet` | 00 sol complet → 01 sable → 02 rafales 24 phases → 03 rochers → 04 touffes 12 phases → 05 falaises → 06 Vos elements avant-plan (Top) | 02 rafales 24 phases : 24 × 5 ticks; 04 touffes 12 phases : 12 × 10 ticks | `entrance` (384, 560), `boss` (384, 288), `azurill` (376, 160) |
| 6 | **FJS1** | Fin Jungle — Southern Jungle<br>Série — 06 | `fjs1_fin_jungle_sud` | 00 sol complet → 01 sable → 02 pelouse → 03 feuilles 48 phases → 04 rocher → 05 jungle → 06 papillons 48 phases → 07 canopee → 08 Vos elements avant-plan (Top) | 03 feuilles 48 phases : 48 × 5 ticks; 06 papillons 48 phases : 48 × 5 ticks | `entrance` (376, 560), `boss` (384, 296), `objectif` (376, 176) |
| 7 | **FWC1** | Fin Waterfall Cave — salle du joyau<br>Série — 07 | `fwc1_fin_waterfall_cave` | 00 sol complet → 01 eau 24 phases → 02 sol → 03 parois → 04 cristaux → 05 joyau → 06 lueur joyau 24 phases → 07 scintillements 12 phases → 08 Vos elements avant-plan (Top) | 01 eau 24 phases : 24 × 10 ticks; 06 lueur joyau 24 phases : 24 × 10 ticks; 07 scintillements 12 phases : 12 × 5 ticks | `entrance` (376, 560), `arene` (384, 312), `joyau` (376, 224) |
| 8 | **FSM1** | Fin Sables mouvants — arène du désert<br>Série — 08 | `fsm1_fin_sables_mouvants` | 00 fosse 12 phases → 01 sol complet → 02 sable → 03 ombres → 04 bord fosse → 05 roche → 06 pierres → 07 chutes 24 phases → 08 poussiere 24 phases → 09 Vos elements avant-plan (Top) | 00 fosse 12 phases : 12 × 10 ticks; 07 chutes 24 phases : 24 × 5 ticks; 08 poussiere 24 phases : 24 × 5 ticks | `entrance` (376, 560), `boss` (384, 440), `objectif` (352, 160) |
| 9 | **FST1** | Fin Star Cave — arène de cristal<br>Série — 09 | `fst1_fin_star_cave` | 00 sol complet → 01 sol → 02 ombres → 03 parois → 04 blocs → 05 reflets 24 phases → 06 etoiles 24 phases → 07 poussiere etoile 24 phases → 08 Vos elements avant-plan (Top) | 05 reflets 24 phases : 24 × 5 ticks; 06 etoiles 24 phases : 24 × 5 ticks; 07 poussiere etoile 24 phases : 24 × 5 ticks | `entrance` (384, 560), `boss` (384, 320), `objectif` (384, 152) |
| — | **FGG1** | Fin Givre V1 — Frosty Grotto (variante conservée)<br>Variante conservée | `fgg1_fin_givre_grotte` | 00 eau glacee 4 phases → 01 reflets 4 phases → 02 sol complet → 03 sol glace → 04 parois → 05 cristal → 06 lueur cristal 6 phases → 07 flocons 48 phases → 08 Vos elements avant-plan (Top) | 00 eau glacee 4 phases : 4 × 10 ticks; 01 reflets 4 phases : 4 × 10 ticks; 06 lueur cristal 6 phases : 6 × 10 ticks; 07 flocons 48 phases : 48 × 5 ticks | `entrance` (384, 560), `boss` (376, 312), `cristal` (376, 232) |
| — | **FOC1** | Fin Océan — arène de Kyogre (hors-série)<br>Hors-série | `foc1_fin_ocean_kyogre` | 00 sol complet → 01 abysse 24 phases → 02 sol → 03 nuances eau 16 phases → 04 motifs lumineux 24 phases → 05 parois → 06 coraux → 07 algues 12 phases → 08 bulles 48 phases → 09 scintillements 12 phases → 10 Vos elements avant-plan (Top) | 01 abysse 24 phases : 24 × 10 ticks; 03 nuances eau 16 phases : 16 × 15 ticks; 04 motifs lumineux 24 phases : 24 × 10 ticks; 07 algues 12 phases : 12 × 20 ticks; 08 bulles 48 phases : 48 × 5 ticks; 09 scintillements 12 phases : 12 × 5 ticks | `entrance` (384, 560), `kyogre` (368, 200), `sceau` (376, 296) |

**État de la série :** cette première édition contient les neuf fins actuellement dans l’ordre principal, de FVS1 à FST1. Fin Clairière tropicale, Fin Couloir violet, Fin Mt. Thunder et Fin Jardin secret restent à créer ; elles ne sont pas simulées ni incluses. FGG1 et FGG2 sont toutes deux gardées : FGG2 occupe le quatrième emplacement de la série, FGG1 est une variante antérieure. FOC1 est proposée comme map bonus, hors de cet ordre.

## Commandes de reproduction

```sh
.venv/bin/python source/mod_fins_donjons_v1/build_mod.py
.venv/bin/python -m unittest source.mod_fins_donjons_v1.test_mod -v
```

Le build ne lance aucun générateur d’images et ne change pas les ZIP des cartes sources. L’archive mod est reproductible (ordre trié, horodatage ZIP fixe). La galerie `apercu_mod_fins_donjons_v1.html` ouvre les aperçus animés individuels ; chaque aperçu conserve ses contrôles de calques.

## Limites de validation

- Les tests vérifient les fichiers, les index, les références des tuiles, les calques, marqueurs, collisions, l’installation simulée et la conservation octet pour octet des contenus sources.
- **Aucun Ground n’a été ouvert dans PMDO pendant ce build.** Le chargement moteur, l’affichage, les collisions en mouvement, le gameplay et les raccords de donjon ne sont pas validés. Aucun warp n’est ajouté.
- Les indicateurs `art_approved` des lots sources ne sont pas changés ; l’assemblage du mod ne vaut pas validation artistique des cartes.
