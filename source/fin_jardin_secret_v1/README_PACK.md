# FGS1 — Fin Jardin secret (PMDO 0.8.12, 4:3)

Suite après FTH1. Ce lot a ses dossiers propres (`source/fin_jardin_secret_v1/`, `renders/fin_jardin_secret_v1/`) ; il ne copie pas le dossier d'entrée EJS1/EJS2 ni les rendus de `main` ou des branches sœurs. Préfixes voisins à ne pas réutiliser : FJS1 (Fin Jungle) et FJS3 (branche sœur); **FGS1** est réservé à ce lot.

## Référence / composition

Référence unique : `secretgarden.png` (Explorers of Sky). Grande arène de prairie au centre, entrée au sud par une allée, souche dorée à marches au nord sous le rayon vert, haies, arbres ronds, pierres beiges et petits massifs blancs/jaunes/roses. Le centre reste dégagé. Pas de temple/Celebi, pas d'objet spécial ajouté, pas d'eau ni papillons. Le temple de la variante EJS2 n'est pas repris : FGS1 suit directement la scène canonique de `secretgarden.png`.

## Calques

Sol complet (sous-couche), prairie, herbe, ombres, fleurs, rochers, arbres, haies, souche, marches, profondeur, fond, rayon, lucioles, Top vide. Le rayon respire sur les **22 verts exacts** du rip; les 10 lucioles reprennent cette palette. Trajectoires et cadence de 24 phases × 5 ticks fabriquées pour FGS1, non officielles.

- 768 × 576 px, 96 × 72 cases de 8 px (`TexSize=1`).
- Marqueurs entrée sud, boss au centre de la prairie, objectif sur les marches au nord; dégagement 16 × 16 vérifié par BFS.
- `runtime_tested: false`, `art_approved: false` : aucun test dans PMDO et aucune approbation artistique revendiqués.

## Méthode et reconstruction

« Textures canoniques » = **rendu généré référencé**, pas tuiles natives. `temoin_sans_objets.png` sert à isoler les arbres, rochers et fleurs; le témoin et le décor sont recalés (0,0). Le guide de fond magenta n'est pas exporté (ce lot n'en a pas besoin). `sol_complet.png` est une sous-couche générée depuis une zone d'herbe propre du décor et masquée par les matières séparées.

```bash
.venv/bin/python source/fin_jardin_secret_v1/build.py
.venv/bin/python -m unittest source.fin_jardin_secret_v1.test_build -v
.venv/bin/python source/fin_jardin_secret_v1/package.py
```

Paquets : `FGS1_projet_pmdo_0812.zip` et `FGS1_calques_png_8px.zip`.
