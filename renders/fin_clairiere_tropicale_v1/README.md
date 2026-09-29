# FCT1 — Fin Clairière tropicale (PMDO 0.8.12, 4:3)

Suite proposée à l'entrée ETC1 : arrivée par le sentier de dalles depuis le sud, grande arène d'herbe centrale, végétation tropicale et bord de mer au sud; objectif posé au bout nord du sentier, sans objet ou créature inventés. Préfixe FCT1 (FTC1 est déjà pris dans une branche sœur; aucun fichier de celle-ci n'a été repris).

## Correction de direction artistique et provenance

- Le premier brut a été écarté après retour utilisateur : il inventait une pomme/sanctuaire et une rivière-cascade derrière l'arène, absents de la référence PMD.
- Le décor retenu a été régénéré directement avec `large.S01P03A.png.84e22fb77c4061e77b0f546545fed2c7.png` en référence. Il reprend la clairière, les palmiers, fleurs, dalles et formes générales du rip. **La seule eau est au bord sud; aucune cascade, rivière, eau derrière l'arène, pomme, fruit, autel ou bâtiment n'est retenu.**
- **« Textures canoniques » signifie ici rendu généré référencé**, pas extraction de tuiles natives. `bruts/objets_magenta.png` remplace seulement l'herbe ouverte par du magenta et sert de témoin de segmentation; son RGB n'est pas exporté. Le décor retenu fournit les pixels visibles.
- La fidélité matière est mesurée sur la capture ETC1 avec le même classifieur que cette entrée : herbe 5,6; jungle 2,0; dalles 4,3 en distance RGB moyenne, seuil 35. C'est un contrôle de palette, pas une preuve pixel-perfect.

## Calques et animations

Dimensions : **768 × 576 px**, grille 96 × 72 cases de 8 px (`TexSize=1`). Calques bas→haut : sol complet, mer de base, herbe, dalles/sentier, ombres, végétation, cailloux, fleurs, canopée de premier plan, mer animée, papillons, Top vide.

- La mer de FCT1 **n'utilise pas la texture d'eau générée** : ses pixels de vagues et sa palette sont réutilisés sans resampling depuis le calque ETC1, lui-même relevé sur le rip canonique. Le lit est la couleur bleu foncé exacte `(15,95,199)` du module ETC1. La coupe est masquée à la seule rive sud de FCT1.
- La mer compte 24 phases × 5 ticks (cadence/animation d'atelier, non officielle); les papillons réemploient sans modification les poses générées et découpées pour ETC1, avec de nouvelles boucles de vol.
- Boucle : 120 ticks (2 s). Les PNG de phases, l'ORA et une scène animée de contrôle sont fournis.

## Accès et limites

Marqueurs `entrance` au sud, `boss` au centre de la clairière et `objectif` au bout nord du sentier. Le passage 16 × 16 px jusqu'aux deux marqueurs est contrôlé par BFS sur les collisions exportées. Aucun warp, aucune sortie ni comportement de boss n'est ajouté. Végétation, rochers, fleurs et mer sont bloquants; herbe, dalles et ombres sont praticables.

**Pas de test de rendu PMDO, pas de test en jeu, pas d'approbation artistique** (`runtime_tested: false`, `art_approved: false`). Les tests de fichiers ne valident ni la qualité artistique ni le comportement des collisions dans le moteur. Le raccord ETC1 → FCT1 reste à scripter.

## Rebuild

```bash
.venv/bin/python source/fin_clairiere_tropicale_v1/build.py
.venv/bin/python -m unittest source.fin_clairiere_tropicale_v1.test_build -v
.venv/bin/python source/fin_clairiere_tropicale_v1/package.py
```

Pack PMDO autonome : `FCT1_projet_pmdo_0812.zip`. PNG/calques : `FCT1_calques_png_8px.zip`.
