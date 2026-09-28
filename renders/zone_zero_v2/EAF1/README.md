# Entrée Zone Zéro fleurie — la géode du donjon (EAF1), PMDO 0.8.12

Suite du réseau fleuri de la Zone Zéro, demandée par « la suite ! » après la passe haute qualité des routes. **EAF1** remplace, dans le réseau fleuri, l'entrée **EAZ1**, qui reste disponible telle quelle : une grotte de cristal sombre, dans le style de l'ancienne série. Le réseau devient : RAF1 → RAF2 → RAF3 → **EAF1** → ATP1.

Format 4:3 : 768 × 576 px, soit 96 × 72 cases de 8 px.

- **Références** :
  - le décor d'**EAZ1** pour le layout de départ (géode de cristal, plateau de cristaux, pas japonais) ;
  - le brut **RAF3** pour le style de la série ;
  - **Sky Peak** (découpe ×2 de `2cwdrrs469f61.gif`) pour l'herbe et les fleurs ;
  - la loi et la palette des cascades viennent de `P03P01A`, comme pour les RAF ;
  - les arbres sont les feuillages PMD découpés dans les bruts de RAF1 et RAF2.
- **Bruts générés** (générateur d'images, référencés). **Ce ne sont pas des tuiles natives.** Ils ont été produits dans cet ordre :
  1. `decor_magenta.png` : le décor EAZ1 repeint au style RAF3 et Sky Peak. Il a une prairie, deux cascades, des fleurs et la géode, mais le vide n'y est qu'un liseré magenta.
  2. `decor_magenta_b.png` : une édition qui élargit le magenta sur les bords.
  3. `decor_gouffre.png` : l'édition « gouffre ». Le générateur a **refait le layout** : deux grands gouffres au sud-ouest et au sud-est encadrent une chaussée fleurie qui monte vers la géode. Ce layout, plus beau, a été gardé.
  4. `decor_magenta_c.png` : `decor_gouffre.png` avec le fond des gouffres en magenta pur. C'est le **décor** utilisé. Le gouffre n'est pris dans `decor_gouffre.png` que sous ce masque. Hors magenta, l'écart moyen avec le gouffre est de 15.
- **Pas japonais** : ce sont des dalles vert sauge (178,197,152), déclarées dans la config (`dalles`) et traitées comme le chemin de RAF2.
- **Fidélité** (seuil 35) :

  | Matière | Distance | Statut |
  |---|---|---|
  | Herbe, contre Sky Peak | 3,4 | seuillée |
  | Arbres, contre les cœurs de feuillage d'Apple Woods | 8,5 | seuillée |
  | Falaises | 32,3 | signalée, non seuillée |

- **Layout** :
  - arrivée au sud (`entrance`), au pied de la chaussée fleurie ;
  - on monte entre les deux gouffres, puis on traverse la prairie haute jusqu'à la **géode de cristal**, l'entrée du donjon (`sortie`, devant la bouche du tunnel) ;
  - `belvedere` au bord du gouffre de droite ;
  - deux cascades tombent de la falaise nord dans des bassins ;
  - le plateau de cristaux à l'ouest est un décor ;
  - aucune sortie latérale, aucun warp.

## Passe haute qualité

Même passe que RAF1-3 (`source/zone_zero_v2/haute_qualite.py`), avec un seuil d'aplat de 52 (`aplat_max`) : l'herbe du brut est plus tramée que celle des RAF.

- **Herbe** : aplat franc au ton dominant du GIF Sky Peak (95 565 px) ; restes flous et tiges maigres effacés.
- **Massifs flous repris** : 9 025 px restés dans le sol, plus 2 383 px de massifs classés falaises (deux boîtes `massifs_falaise`), redessinés nets et praticables.
- **Fleurs** : 234 fleurs nettes de 7 px en **sept couleurs** (blanc, bleu, corail, jaune, rose, rouge, violet).
- **Touffes** : 51 touffes en étoile qui se balancent.
- **Embruns** : 70 gouttelettes au pied des deux cascades.
- **Papillons** : 5, sur des boucles fermées.

## Calques (du bas vers le haut)

| # | Calque | Animation |
|---|---|---|
| 00 | sol_complet | fixe |
| 01 | abime | fixe : le gouffre généré, avec un dégradé de profondeur vers le bleu nuit |
| 02 | brume_profonde | 24 × 20 ticks : +4 px par phase, trame de Bayer, plus dense vers le fond |
| 03 | brume_haute | 24 × 10 ticks : −8 px par phase, effet de parallaxe |
| 04 | lueurs | 24 × 10 ticks : 34 éclats lointains |
| 05 | eau | 3 × 10 ticks : rides dans les deux bassins |
| 06 | sol | fixe : herbe Sky Peak en aplat franc, dalles |
| 07 | falaises | fixe : parois des gouffres, cristaux, géode |
| 08 | herbes | 4 × 12 ticks, A B A C : touffes en étoile |
| 09 | fleurs | 4 × 12 ticks, loi du GIF Sky Peak (A B A C) : en B et C, chaque fleur descend de 1 px et penche de ±1 px |
| 10 | buissons | fixe |
| 11 | arbres | fixe : 13 arbres plantés, plus ceux du décor |
| 12 | cascades | 3 × 10 ticks : loi de P03P01A |
| 13 | ecume | 3 × 10 ticks |
| 14 | embruns | 24 × 10 ticks : les gouttelettes partent du haut de l'écume, montent de 34 px et s'effacent |
| 15 | papillons | 48 × 10 ticks : boucles de Lissajous fermées ; les ailes s'ouvrent et se ferment une phase sur deux |
| 16 | Top (vide) | à vous |

La scène boucle en 480 ticks (8 s).

**Collisions** : le sol, les dalles, les fleurs et les massifs sont praticables. On compte 5 465 cases bloquées sur 6 912.

Contrôles : 12 tests (`source/zone_zero_v2/eaf1/test_build.py`) et mutations (`source/zone_zero_v2/mutations.py eaf1`).

## Installation

Lancez `python INSTALLER.py <dossier PMDO>`. Le script fusionne l'index des tuiles.

**Non testé dans PMDO.** Le manifeste indique `runtime_tested: false` et `art_approved: false`. Les raccords (RAF3 → EAF1 → donjon) restent à scripter.
