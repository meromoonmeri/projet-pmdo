# Zone de réveil V2 — prairie de Sky Peak face à l'océan (jour, aube, nuit) — projet PMDO 0.8.12

Projet d'édition autonome, namespace `zone_reveil_prairie_horizon_v2`. C'est **la première scène** : le Pokémon se réveille dans une grande prairie fleurie de Sky Peak, au bord d'un promontoire plat, face à l'océan.

La V2 garde **la disposition de la V1** : même prairie, mêmes collisions, mêmes marqueurs. Seuls la mer et l'arrière-plan sont refaits, et chacun a son propre calque :

- **Mer** : générée avec la carte V24P04A de PMD Ciel en référence, et animée selon les lois relevées dans la ROM. Les crêtes naissent en houle sombre sous l'horizon, grandissent en descendant et roulent vers la prairie (12 crans de 10 ticks). L'horizon scintille (16 crans de 4 ticks).
- **Montagne** : celle de la V1. Ses flancs descendent jusqu'à l'horizon.
- **Nuages** : un banc posé sur l'horizon, qui défile lentement **derrière** la montagne. La profondeur va de l'avant vers l'arrière : mer, montagne, nuages.
- **Lune (nuit) et soleil levant (aube)** : chacun a un reflet animé sur la mer, dont les bandes ondulent au rythme de la houle.
- **Fleurs** : les têtes se balancent comme dans le GIF de Sky Peak (cycle A B A C).

Trois Grounds, même disposition, mêmes collisions :

| Ground | Ambiance |
|---|---|
| `zrv2_zone_reveil_jour` | plein jour, ciel bleu |
| `zrv2_zone_reveil_aube` | aube, ciel du violet au rose, soleil levant et son reflet doré |
| `zrv2_zone_reveil_nuit` | nuit, pleine lune derrière le sommet, reflet, étoiles qui scintillent |

**Aucun warp** : c'est une base d'édition, pas une aventure jouable. **Non testé dans PMDO.**

## Installer

- **Mod séparé** : copier `zone_reveil_prairie_horizon_v2` dans `PMDO/MODS/`, activer le mod, puis ouvrir les Grounds dans l'éditeur (mode développeur).
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis la même commande sans `--dry-run`. L'installeur ne remplace jamais un fichier existant différent. Il sauvegarde l'index des tuiles avant de le fusionner.

## Calques (du bas vers le haut)

| # | Calque | Animation |
|---|---|---|
| 00 | Sol complet (herbe unie) | fixe |
| 01 | Ciel | fixe |
| 02 | Étoiles (nuit seulement) | 24 × 5 ticks |
| 03 | Lune ou soleil (nuit, aube) | fixe |
| 04 | Nuages : le banc défile de 1 px par cran, sur une boucle de 256 px | 256 × 8 ticks |
| 05 | Montagne | fixe |
| 06 | Mer (fond) | fixe |
| 07 | Scintillement de l'horizon | 16 × 4 ticks |
| 08 | Houle et crêtes | 12 × 10 ticks |
| 09 | Reflet de la lune ou du soleil (nuit, aube) | 12 × 10 ticks |
| 10 | Écume au pied de la prairie | 12 × 10 ticks |
| 11 | Herbe | fixe |
| 12 | Chemin | fixe |
| 13 | Fleurs | 4 × 12 ticks |
| 14 | Rochers | fixe |
| 15 | Buissons | fixe |
| 16 | Vide, `Layer=4` (Top) | — |

Les banques sont préfixées `ZRV2J_`, `ZRV2A_` et `ZRV2N_` (jour, aube, nuit). Toutes les boucles se referment ; la plus longue fait 2048 ticks (les nuages).

## Marqueurs et collisions

Ils sont repris tels quels de la V1 :

- `reveil` : au bord nord de la prairie, au centre, tourné vers l'océan. C'est là que le héros se réveille.
- `entrance` : au bord sud, sur le chemin. C'est la sortie de la zone.
- La mer, l'arrière-plan, les rochers et les buissons sont bloqués. L'herbe, les fleurs et le chemin sont praticables.

## Origine des pixels

- **Prairie** (herbe, chemin, fleurs, rochers, buissons) : ce sont les calques de la V1, eux-mêmes générés avec le GIF de Sky Peak en référence.
- **Ciel et mer, crêtes, banc de nuages, lune et soleil** : générés avec les captures de V24P04A et V24P02A en référence.
- **Montagne** : la montagne de la V1, redessinée seule à partir de son recadrage.

Ce sont des pixels générés, pas des tuiles natives.

- **Cadences** (houle 12 × 10, scintillement 16 × 4, motif de 96 px) : relevées dans la ROM (pret/pmd-sky, carte v24p04a).
- **Aube et nuit** : les couleurs sont transposées depuis les bruts de la V1 pour ces ambiances.
- **Balancement des fleurs** : mesuré sur le GIF de Sky Peak.
- **Trajet des nuages, reflets, étoiles** : créés par nous.
- **Les petits pics sombres** de la mer de nuages de la V1 ne sont pas repris.
