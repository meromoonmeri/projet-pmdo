# FVC1 — Fin Couloir violet (PMDO 0.8.12, 4:3)

Suite proposée à l'entrée ECV1 (capture `large.S05P03A…png`) : couloir étroit au sud, grande arène de pierre au nord, murs de rochers violets et gravillons. Le point `objectif` est un marqueur au nord du sol dégagé, sans relique/personnage ajouté. Préfixe FVC1 : FCV1 est déjà pris dans une branche sœur.

## Méthode et limites

**Textures canoniques = rendu généré référencé** : le décor 4:3 a reçu la capture ECV1 comme référence de style, palette et matière. Ce ne sont pas des tuiles natives ni une copie pixel-par-pixel. Le guide magenta sert uniquement à isoler le sol ouvert; ses pixels ne sont jamais exportés. L'underpainting est construit à partir de pixels échantillonnés sur le sol du décor et est caché par les calques visibles.

Le terrain, les murs, les gravillons et le vide sont sur des PNG transparents distincts. Les petites poses de gravillon proviennent de l'entrée ECV1 (détourage déjà mesuré, sans redimensionnement); leurs trajectoires de chute sont nouvelles et non officielles.

## Carte et exports

- 768 × 576 px, 96 × 72 cases de 8 px (`TexSize=1`), format 4:3.
- Calques bas→haut : sol complet, sol praticable, ombres de bord, gravillons, murs rocheux, vide extérieur, gravillons qui tombent, Top vide.
- Entrée sud, `boss` au centre, `objectif` au nord. Chemin 16 × 16 vérifié par BFS. Pas de warp, pas de sortie ni de Pokémon nommé.
- Boucle de gravillons : 24 phases × 5 ticks (création de mouvement par le pipeline; pas une animation ROM).

Aucun test de rendu ou de collision dans PMDO : `runtime_tested: false`; art à confirmer (`art_approved: false`). Le script `INSTALLER.py --dry-run` a seulement vérifié les chemins de 9 fichiers et 7 tilesets; cette simulation n'est pas un essai dans le jeu.

Sources, consignes de génération et limites détaillées : `GENERATION.md`.

## Rebuild

```bash
.venv/bin/python source/fin_couloir_violet_v1/build.py
.venv/bin/python -m unittest source.fin_couloir_violet_v1.test_build -v
.venv/bin/python source/fin_couloir_violet_v1/package.py
```

Pack PMDO : `FVC1_projet_pmdo_0812.zip`; calques : `FVC1_calques_png_8px.zip`.
