# Route Zone Zéro 2 fleurie — terrasses aux cascades (RAF2), PMDO 0.8.12

Nouvelle version de **RAZ2**, qui reste disponible telle quelle. La demande était la suivante :
- la texture de Sky Peak ;
- des fleurs de différentes couleurs ;
- des arbres PMD ;
- les cascades gardées ;
- chaque élément sur son propre calque ;
- des trous qui donnent vraiment un effet de profondeur.

Format 4:3 : 768 × 576 px, soit 96 × 72 cases de 8 px.

- **Références** :
  - **Sky Peak** (`2cwdrrs469f61.gif`, image 0) pour l'herbe, les falaises gris-bleu et les fleurs ;
  - **Apple Woods** (`Apple_Woods_entrance_TDS.png`) pour les arbres ;
  - la loi et la palette des cascades viennent de `P03P01A`.
- **Décor** : un rendu généré. Le générateur a reçu le brut de RAZ2, une découpe Sky Peak ×2 et une découpe d'arbres Apple Woods ×2, avec le gouffre en magenta. **Ce ne sont pas des tuiles natives.**
- **Gouffre** : une édition du décor. Seuls les pixels situés dans le masque magenta sont gardés.
- **Arbres** : les mêmes 8 sprites que RAF1, soit des feuillages découpés dans les bruts de décor. Les deux planches générées à part ont été rejetées (voir RAF1).
- **Fidélité** (seuil 35) :

  | Matière | Distance | Statut |
  |---|---|---|
  | Herbe | 5,2 | seuillée |
  | Arbres | 8,5 | seuillée |
  | Falaises | 20,5 | signalée |

- **Layout** :
  - arrivée au sud (`entrance`), sur un chemin beige ;
  - on monte l'**escalier de pierre**, entre deux cascades, vers la terrasse haute ;
  - le chemin de corniche longe le gouffre jusqu'aux marches du nord-est (`sortie`) ;
  - trois cascades sur la terrasse haute, deux sur la basse, chacune avec son bassin ;
  - `belvedere` près du bord du gouffre, qui occupe tout l'est ;
  - aucune sortie latérale, aucun warp.

## Calques (du bas vers le haut)

| # | Calque | Animation |
|---|---|---|
| 00 | sol_complet | fixe |
| 01 | abime | fixe : le gouffre généré avec un **dégradé de profondeur** vers le bleu nuit |
| 02 | brume_profonde | 24 × 20 ticks : +4 px par phase, trame de Bayer, plus dense vers le fond |
| 03 | brume_haute | 24 × 10 ticks : −8 px par phase, effet de **parallaxe** |
| 04 | lueurs | 24 × 10 ticks : 34 éclats lointains |
| 05 | eau | 3 × 10 ticks : rides |
| 06 | sol | fixe : herbe Sky Peak, chemins, escaliers |
| 07 | falaises | fixe |
| 08 | fleurs | 4 × 12 ticks, loi Sky Peak (A B A C). 281 têtes en cinq couleurs : rouge et rose, jaune, bleu, violet et blanc |
| 09 | buissons | fixe |
| 10 | arbres | fixe : 51 arbres PMD |
| 11 | cascades | 3 × 10 ticks : loi de P03P01A |
| 12 | ecume | 3 × 10 ticks |
| 13 | Top (vide) | à vous |

La scène boucle en 480 ticks (8 s).

**Collisions** : le sol, les chemins, l'escalier, les fleurs et les massifs sont praticables. On compte 5 206 cases bloquées sur 6 912.

Les reflets clairs des marches passaient la règle de l'eau, et les massifs de fleurs bleues aussi. Les deux sont maintenant exclus, et un test le vérifie.

## Installation

Lancez `python INSTALLER.py <dossier PMDO>`.

**Non testé dans PMDO** : `runtime_tested: false`, `art_approved: false`. Les raccords restent à scripter.

## Fichiers

Même organisation que RAF1, avec le préfixe `RAF2_`.

Source : `source/zone_zero_v2/`. On lance `build.py raf2`, puis `package.py raf2`.
