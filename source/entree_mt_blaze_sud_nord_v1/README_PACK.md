# EMB1 — Entrée Mt. Blaze sud → nord (4:3, PMDO 0.8.12)

Projet d'édition autonome de la zone d'entrée de Mt. Blaze, inspirée de **Pokémon Mystery Dungeon: Red Rescue Team** (GBA). Format 768 × 576 px, soit 96 × 72 cases de 8 px (`TexSize=1`). Le personnage arrive au sud par le sentier de terre et avance vers la bouche de grotte au nord.

## Installer

- **Projet séparé** : décompresser `EMB1_projet_pmdo_0812.zip` dans `PMDO/MODS/`, activer le mod puis ouvrir le Ground `emb1_entree_mt_blaze`.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, vérifier le rapport, puis relancer sans `--dry-run`.

C'est une base graphique d'édition, pas une aventure jouable : aucun warp, aucun Pokémon, aucun événement.

## Calques (bas → haut)

| # | Calque | Contenu / animation |
|---:|---|---|
| 00 | Sol complet | Terre volcanique intégrale sous le décor |
| 01 | Ombres | Ombre portée courte sous les bords rocheux |
| 02 | Lave | Deux bassins et chenaux, 24 × 10 ticks |
| 03 | Sentier | Chemin central praticable du bord sud au seuil |
| 04 | Éboulis | Pierres isolées et détails rocheux |
| 05 | Parois | Falaises sombres et blocs latéraux |
| 06 | Piliers | Deux piliers de pierre encadrant l'entrée |
| 07 | Grotte | Bouche sombre au nord |
| 08 | Lueurs | Fissures chaudes qui scintillent, 24 × 10 ticks |
| 09 | Braises | Particules ascendantes, 24 × 10 ticks |
| 10 | Top | Calque vide réservé à l'avant-plan |

La boucle complète dure 240 ticks (4 s). Les animations sont créées pour ce projet, pas des animations officielles du jeu. Chaque pixel des calques est opaque ou transparent (pas d'alpha intermédiaire).

## Collisions et marqueurs

- `entrance` est au sud, sur le sentier.
- `donjon_seuil` est placé sur la case 16 × 16 libre la plus au nord, au pied de la grotte.
- La règle de collision bloque une case de 8 px si plus de 25 % de sa surface est hors du masque de sentier praticable. Les berges de lave, les piliers, les parois et la grotte sont bloqués.
- Un chemin de collision 16 × 16 entre les deux marqueurs est testé par BFS.

## Sources, méthode et limites

- Les captures GBA de Mt. Blaze jointes à la demande servent de référence de composition et d'ambiance ; elles ne sont pas recopiées ni incluses dans le pack.
- Le dossier `source/outil_maps_pmdsky/` a été consulté. Son outil couvre Explorers of Sky, pas Red Rescue Team ; il ne fournit pas de carte Mt. Blaze exploitable ici.
- La matière est une génération pixel-art 4:3 segmentée par masques (sol, lave, sentier, éboulis, piliers, parois, grotte), puis intégrée dans un Ground PMDO 0.8.12.
- Les images intermédiaires, prompts, empreintes SHA-256, masques et tests sont conservés dans `source/entree_mt_blaze_sud_nord_v1/` et `renders/entree_mt_blaze_sud_nord_v1/`.
- Aucun test n'a été effectué dans le moteur PMDO ; les collisions restent à valider en jeu.
