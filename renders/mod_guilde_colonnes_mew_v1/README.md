# Guilde Treehouse — Colonnes Lances et Mew (4 cartes) — mod PMDO 0.8.12

Ce dossier est un mod d'édition autonome, namespace `guilde_colonnes_mew`. Il regroupe **4 cartes** : les deux sommets de Colonnes Lances (CLR1 : ruines flottantes, CLR2 : sommet de la montagne), le sentier d'entrée qui monte vers CLR2 (ECL1, marqueurs `entrance` et `donjon_seuil`) et le fond de ciel animé de l'intro de Mew (IMW2, boucle de 40 s). Chaque carte est un Ground animé 768 × 576, avec ses collisions et ses marqueurs. **Aucun warp** : base d'édition, pas une aventure jouable. IMW2 est un fond de cinématique : toute sa grille est bloquante, ses marqueurs ne sont que des repères.

**Aucune validation de l'utilisateur n'est enregistrée pour ces cartes** : toutes sont à confirmer. **Aucune carte n'a encore été testée dans PMDO.**

## Installer

- **Mod séparé** : copier le dossier `guilde_colonnes_mew` dans `PMDO/MODS/`, activer le mod, puis ouvrir les Grounds dans l'éditeur (mode développeur).
- **Dans un mod existant** : `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis la même commande sans `--dry-run`. L'installeur ne remplace jamais un fichier existant différent, et fusionne l'index des tuiles après en avoir fait une sauvegarde.

## Cartes

| # | Ground | Carte | Calques | Animations (frames × ticks) | Marqueurs |
|---|---|---|---|---|---|
| 1 | `clr1_colonnes_lances` | Colonnes Lances, ruines flottantes | 8 | 12 × 10, 30 × 20, 60 × 10, 120 × 10 | `entrance` (376, 560), `centre` (376, 296), `autel` (376, 160) |
| 2 | `clr2_colonnes_lances_sommet` | Colonnes Lances, sommet de la montagne | 8 | 12 × 10, 30 × 20, 60 × 10, 120 × 10 | `entrance` (376, 560), `centre` (376, 264), `autel` (376, 184) |
| 3 | `ecl1_entree_colonnes_lances` | Entrée Colonnes Lances, sentier de la montagne | 8 | 12 × 10, 30 × 20, 60 × 10, 120 × 10 | `entrance` (376, 560), `donjon_seuil` (376, 104) |
| 4 | `imw2_ciel_de_mew` | Ciel de Mew, fond animé en boucle | 8 | 8 × 6, 12 × 200, 240 × 10 | `entrance` (376, 560), `mew` (272, 292), `soleil` (532, 228) |

Toutes les cartes font 768 × 576 (96 × 72 cases de 8 px). Chaque carte a un calque Top vide (`Layer=4`) en dernier.

## Scripts

Chaque carte a son script `Data/Script/guilde_colonnes_mew/ground/<carte>/init.lua`, copié tel quel depuis son lot.

## Limites

- Décors et Mew générés (rendu généré référencé pour CLR1, CLR2 et ECL1 ; nuages, soleil et éclats procéduraux pour IMW2) : ce ne sont pas des tuiles natives. Aucune référence de la ROM pour la roche et la neige de CLR2 et d'ECL1.
- Les animations sont créées pour ces cartes : ce ne sont pas les animations officielles.
- Collisions et marqueurs vérifiés sur la grille, pas en jeu. Aucun marqueur n'est raccordé à un donjon ou à un boss réel.
