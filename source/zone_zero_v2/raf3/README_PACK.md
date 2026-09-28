# Route Zone Zéro 3 fleurie — fond du cratère et tunnel (RAF3), PMDO 0.8.12

Nouvelle version de **RAZ3** (fond cristallin), qui reste disponible telle quelle. Elle termine le passage des routes Area Zero au style fleuri (RAF1 → RAF2 → RAF3 → EAZ1). La demande est la même que pour RAF1/RAF2 :
- la texture de Sky Peak ;
- des fleurs de différentes couleurs ;
- des arbres PMD ;
- les cascades gardées ;
- chaque élément sur son propre calque ;
- des trous qui donnent vraiment un effet de profondeur.

EAZ1 est l'intérieur d'une grotte : de l'herbe et des arbres Sky Peak n'y ont pas de sens, elle n'est donc pas retouchée.

Format 4:3 : 768 × 576 px, soit 96 × 72 cases de 8 px.

- **Références** :
  - **Sky Peak** (`2cwdrrs469f61.gif`, image 0) ;
  - **Apple Woods** pour les arbres ;
  - le **décor RAF2**, comme modèle du style de la série ;
  - `P03P01A` pour la loi et la palette des cascades.
- **Décor** : un rendu généré. Le générateur a reçu le brut de RAZ3 (pour le layout), le décor RAF2 et une découpe Sky Peak ×2.
  - Le lac magenta de RAZ3 devient deux gouffres en magenta pur.
  - La chaussée de cristal devient une prairie fleurie, avec un chemin clair.
  - **Ce ne sont pas des tuiles natives.**
  - Un petit point de magenta pur, hors des gouffres, est repeint avec le pixel voisin (`retouche_magenta`).
- **Gouffres** : une édition du décor. Seuls les pixels situés dans le masque magenta sont gardés.
- **Arbres** : les 8 sprites découpés dans les bruts RAF1/RAF2 (voir RAF1), plus les arbres peints dans le décor.
- **Fidélité** (seuil 35) :

  | Matière | Distance | Statut |
  |---|---|---|
  | Herbe | 10,7 (aplat HQ au ton dominant du GIF) | seuillée |
  | Arbres | 8,5 | seuillée |
  | Falaises | 44,8 | signalée, non seuillée |

  Les falaises dépassent le seuil : la couronne rocheuse générée est sarcelle, et non gris-bleu comme à Sky Peak. C'est une matière secondaire, laissée telle quelle et signalée dans le manifeste.
- **Layout** :
  - arrivée au sud (`entrance`) ;
  - une longue prairie fleurie entre deux gouffres ;
  - un pavage de dalles entre les piliers de cristal ;
  - une terrasse haute avec les deux cascades et leurs bassins ;
  - le **tunnel nord** (`sortie`, vers EAZ1) ;
  - `belvedere` au bord du gouffre de gauche ;
  - un îlot boisé, inaccessible, dans le gouffre de droite.
  - Aucune sortie latérale, aucun warp.

## Passe haute qualité (septembre 2026)

Demande : « faut que les zone route area zero soit magnifique avec la verdure sky peak hight qualité less fleur avec plein de couleur des cascade de la brume etc ». La réduction ×0,64 rendait l'herbe floue et les fleurs baveuses. La passe est calculée (`source/zone_zero_v2/haute_qualite.py`), pas des tuiles natives ; seuls les tons viennent du GIF Sky Peak.

- **Herbe** : l'herbe claire du sol devient un aplat franc au ton dominant du GIF Sky Peak (134 202 px). Seuls les pixels à moins de 40 du ton dominant du lot sont concernés, donc le chemin clair reste.
- **Nettoyage** : 1 101 px de restes flous et 3 155 px de tiges maigres redeviennent de l'herbe.
- **Massifs repris** : 2 389 px de massifs flous restés dans le sol et 4 956 px de massifs classés falaises (boîtes `massifs_falaise` de la config) sont redessinés nets et deviennent praticables.
- **Touffes** : 55 étoiles de 6 brins qui se balancent en A B A C, comme toute la prairie du GIF.
- **Fleurs** : 270 fleurs nettes en huit couleurs. Les massifs d'origine gardent leur couleur et d'autres massifs s'ajoutent sur l'herbe franche.
- **Embruns** au pied des cascades, et **papillons**.
- **Sol et buissons** : le sol est quantifié seul sur 128 couleurs, sinon les buissons ronds du sol tombaient en olive plat. Les falaises et les buissons passent à 96 couleurs.

Contrôles : 12 tests, dont `test_haute_qualite`, et 23 mutations toutes détectées (`source/zone_zero_v2/mutations.py raf3`).

## Calques (du bas vers le haut)

Les calques et leurs lois sont les mêmes que dans RAF1 et RAF2 :

| # | Calque | Animation |
|---|---|---|
| 00 | sol_complet | fixe |
| 01 | abime | fixe : le gouffre généré, avec un dégradé de profondeur vers le bleu nuit |
| 02 | brume_profonde | 24 × 20 ticks : +4 px par phase, trame de Bayer, plus dense vers le fond |
| 03 | brume_haute | 24 × 10 ticks : −8 px par phase, effet de parallaxe |
| 04 | lueurs | 24 × 10 ticks : 34 éclats lointains |
| 05 | eau | 3 × 10 ticks : rides dans les deux bassins |
| 06 | sol | fixe : herbe Sky Peak en **aplat franc** (135,247,119, ton dominant du GIF) et chemin |
| 07 | falaises | fixe, cristaux compris |
| 08 | herbes | 4 × 12 ticks, A B A C : 55 **touffes en étoile** nettes (tons relevés sur Sky Peak) ; en B et C les brins du haut penchent de ±1 px |
| 09 | fleurs | 4 × 12 ticks, loi du GIF Sky Peak (A B A C) : en B et C chaque fleur descend de 1 px et penche de ±1 px. 270 **fleurs nettes de 7 px** (4 pétales, reflet, cœur, ombre verte) en **huit couleurs** : corail, rouge, rose, orange, jaune, blanc, bleu, violet |
| 10 | buissons | fixe |
| 11 | arbres | fixe : 23 arbres plantés, plus ceux du décor |
| 12 | cascades | 3 × 10 ticks : loi de P03P01A |
| 13 | ecume | 3 × 10 ticks |
| 14 | embruns | 24 × 10 ticks : 81 gouttelettes partent du haut de l'écume de chaque cascade, montent de 34 px en ondulant et s'effacent (trame de Bayer) |
| 15 | papillons | 48 × 10 ticks : 8 papillons de couleurs différentes sur des boucles fermées (Lissajous) au-dessus de la prairie ; ailes ouvertes et fermées une phase sur deux |
| 16 | Top (vide) | à vous |

La scène boucle en 480 ticks (8 s).

**Collisions** : le sol, le chemin, les fleurs et le pavage entre les cristaux (rectangle mesuré sur le brut, écrit dans la config) sont praticables. On compte 5 184 cases bloquées sur 6 912.

**Réglages propres à ce décor**, notés dans `build.py` :
- les cristaux clairs passaient la règle des cascades. Seules les chutes peintes sont gardées : elles partent du bord haut, en x 300–395 et 820–915 en pleine résolution ;
- les falaises bleu sombre passaient la règle de l'eau. L'eau est limitée aux bassins, sous l'écume de chaque chute ;
- les éclats de cristal menthe ne sont pas comptés comme des fleurs.

## Installation

Lancez `python INSTALLER.py <dossier PMDO>`.

**Non testé dans PMDO** : `runtime_tested: false`, `art_approved: false`. Les raccords (RAF2 → RAF3 → EAZ1) restent à scripter.

## Fichiers

Même organisation que RAF1, avec le préfixe `RAF3_`.

Source : `source/zone_zero_v2/`. On lance `build.py raf3`, puis `package.py raf3`.
