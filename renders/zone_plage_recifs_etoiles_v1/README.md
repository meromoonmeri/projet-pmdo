# Plage aux récifs étoilés — ZPR1 (jour, aube, crépuscule, nuit) — projet PMDO 0.8.12

Projet d'édition autonome, namespace `zone_plage_recifs_etoiles_v1`. Demande : *« une zone magnifique en bord de plage avec ciel étoilé dans les différents temps, avec des récifs, etc., multicalque »*.

C'est une **baie de plage** de 768 × 576 px (4:3, grille de 8 px) : deux promontoires de roches rouges ferment une baie turquoise ; devant le rivage s'étagent une **barrière de récifs** (sept récifs rocheux émergés) et un **lagon de corail** (treize patates de corail vues à travers l'eau) ; la plage de sable porte six palmiers qui se balancent, deux mares, des coquillages, des étoiles de mer et un tronc échoué. Le **ciel est étoilé à chaque moment de la journée**, de façon de plus en plus dense du jour à la nuit.

| Ground | Ambiance |
|---|---|
| `zpr1_plage_recifs_jour` | plein jour : ciel bleu, soleil haut, banc de nuages, quelques étoiles très pâles |
| `zpr1_plage_recifs_aube` | aube : ciel lavande et rose, soleil levant à demi caché par les nuages, reflet doré, étoiles rares |
| `zpr1_plage_recifs_crepuscule` | crépuscule : ciel rouge et orange, soleil couchant, reflet rouge, premières étoiles, étoile filante |
| `zpr1_plage_recifs_nuit` | nuit : pleine lune et son halo, Voie lactée, 536 étoiles dont 96 qui scintillent, étoile filante, coraux luminescents, plancton |

**Aucun warp** : c'est une base d'édition, pas une aventure jouable. **Non testé dans PMDO.**

## Installer

- **Mod séparé** : copier `zone_plage_recifs_etoiles_v1` dans `PMDO/MODS/`, activer le mod, puis ouvrir les Grounds dans l'éditeur (mode développeur).
- **Dans un mod existant** : `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis la même commande sans `--dry-run`. L'installeur ne remplace jamais un fichier existant différent et sauvegarde l'index des tuiles avant de le fusionner.

## Calques (du bas vers le haut)

Chaque élément a son propre calque ; un calque absent d'une ambiance garde son numéro (les numéros sont les mêmes partout).

| # | Calque | Ambiances | Animation |
|---|---|---|---|
| 00 | Ciel (bandes) | toutes | fixe |
| 01 | Voie lactée (poussière d'étoiles en diagonale) | aube, crépuscule, nuit | fixe |
| 02 | Étoiles fixes | aube, crépuscule, nuit | fixe |
| 03 | Étoiles qui scintillent (états plein / cœur / éteint) | toutes | 24 × 5 ticks |
| 04 | Étoile filante (une par cycle de 6 s) | crépuscule, nuit | 72 × 5 ticks |
| 05 | Soleil ou lune, avec son halo | toutes | fixe |
| 06 | Nuages (un banc sur l'horizon, boucle de 768 px, 2 px par cran) | toutes | 384 × 16 ticks |
| 07 | Mer | toutes | fixe |
| 08 | Coraux vus à travers l'eau (patates d'eau sombre + coraux) | toutes | fixe |
| 09 | Reflets de lumière sur le fond du lagon (caustiques) | toutes | 12 × 10 ticks |
| 10 | Houle : crêtes en arcs qui épousent la baie | toutes | 12 × 10 ticks |
| 11 | Scintillement de l'horizon | toutes | 16 × 4 ticks |
| 12 | Reflet de l'astre sur l'eau | aube, crépuscule, nuit | 12 × 10 ticks |
| 13 | Lueur des coraux et plancton | nuit | 12 × 10 ticks |
| 14 | Récifs rocheux émergés | toutes | fixe |
| 15 | Écume qui bat contre les récifs | toutes | 12 × 10 ticks |
| 16 | Sable | toutes | fixe |
| 17 | Marée : écume mouchetée, sable mouillé, eau claire qui avance sur la plage | toutes | 18 × 8 ticks |
| 18 | Mares | toutes | fixe |
| 19 | Éclats d'eau dans les mares | toutes | 8 × 10 ticks |
| 20 | Rochers (promontoires et petits rochers) | toutes | fixe |
| 21 | Coquillages et étoiles de mer | toutes | fixe |
| 22 | Bois flotté | toutes | fixe |
| 23 | Troncs de palmiers | toutes | fixe |
| 24 | Couronnes de palmiers (se balancent de 2 px au sommet) | toutes | 12 × 10 ticks |
| 25 | Herbes (se balancent de 1 à 2 px) | toutes | 8 × 12 ticks |
| 26 | Vide, `Layer=4` (Top) | — | — |

Les banques sont préfixées `ZPR1J_`, `ZPR1A_`, `ZPR1C_` et `ZPR1N_`. Toutes les boucles se referment ; la plus longue fait 6144 ticks (les nuages, 102 s).

## Marqueurs et collisions

- `plage` : au bord de l'eau, au centre de la baie. C'est là qu'on arrive.
- `entrance` : au bord sud, sur le chemin clair. C'est la sortie de la zone.
- Sont bloqués : la mer et le ciel, les promontoires et petits rochers, le pied des troncs de palmiers, le bois flotté. Le sable, les mares, les herbes, les coquillages et le dessous des couronnes de palmiers sont praticables. Les récifs et les coraux sont dans l'eau.
- Un chemin de 16 × 16 px existe entre la sortie sud et la plage (vérifié par le même parcours que les autres zones).

## Origine des pixels

Ce sont des pixels générés, pas des tuiles natives, et rien n'a été validé dans le moteur.

- **Générés** (`source/zone_plage_recifs_etoiles_v1/bruts/`, journal `generation.json`) : la terre du jour sur fond magenta, le ciel et la mer, une planche de sept récifs rocheux, une planche de douze coraux, et trois retouches d'ambiance (aube, crépuscule, nuit) du décor de jour.
- **Réutilisés de ZRV2**, tels quels (sha256 dans `manifest.json`) : planche des astres, planche des reflets, trois bancs de nuages.
- **Calculés** (`build.py`) : le découpage en calques, les récifs et leur placement, les couleurs de l'aube, du crépuscule et de la nuit (échantillons des retouches par quantile de luminance), les étoiles, la Voie lactée, l'étoile filante, la houle, les caustiques, l'écume, la marée, le balancement des palmes et des herbes, la lueur de nuit, les collisions.
- **Lois reprises de ZRV2** (qui les tient de V24P04A) : houle 12 × 10 ticks, scintillement 16 × 4, étoiles 24 × 5, nuages 768 px en 384 × 16.
- **Choix de l'agent, à confirmer** : le biome et la composition, les quatre ambiances, la présence d'étoiles à tous les temps et leurs effectifs (constantes `ETOILES`), les positions des récifs et des coraux.
