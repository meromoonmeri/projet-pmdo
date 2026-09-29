# FTH1 — Fin Mt. Thunder (PMDO 0.8.12, 4:3)

Suite après FVC1 dans la série des fins. Nouvelle carte indépendante dans `renders/fin_mt_thunder_v1/` (préfixe FTH1, distinct de FMT1 déjà pris dans une branche sœur). Référence de composition/matière : `source/references_54d3731/thunder.png`, plateau sommital Mt. Thunder (Red Rescue Team/GBA). Aucun artefact de branche sœur n'est repris.

## Carte

Plateau de sable jaune pâle au-dessus de la mer de nuages, falaise brun-beige, quelques cailloux et aiguilles de roche repris de la capture. Centre ouvert, arrivée au sud, boss au centre, objectif au nord sans objet ajouté. Calques transparents : fond de ciel, nuages arrière, falaise, sol, ombres, pierres, lueurs, éclairs, nuages avant-plan, Top vide.

Éclairs (4 formes), arc Flash, couleurs Normal/Fading : pixels et palette extraits à l'échelle native du panneau de référence Mt. Thunder. Les chutes/flashs sont animés par une loi créée pour FTH1 (48 phases × 5 ticks), non officielle. Aucun personnage, Pokémon, caverne, sanctuaire, arbre, fleur, eau, cascade, cristal ni papillon.

## Méthode / limites

« Textures canoniques » signifie **rendu généré référencé**, pas tuiles natives. Le décor est généré en prenant la capture comme référence de composition, palette et matière; le témoin magenta isole uniquement la surface sableuse et n'est jamais exporté. Le sous-sol uniforme du ciel est masqué par les calques segmentés.

- Taille : 768 × 576 px, 96 × 72 cases de 8 px (`TexSize=1`).
- Collisions issues du masque de surface; chemin libre de 16 × 16 px testé par BFS.
- `runtime_tested: false`, `art_approved: false`; aucun test dans le moteur PMDO ni validation artistique revendiqués.
- Validation de chemins d'installation seulement : `INSTALLER.py --dry-run` a proposé 11 fichiers et 9 tilesets, sans écrire de fichier dans la cible.

## Rebuild

```bash
.venv/bin/python source/fin_mt_thunder_v1/build.py
.venv/bin/python -m unittest source.fin_mt_thunder_v1.test_build -v
.venv/bin/python source/fin_mt_thunder_v1/package.py
```

Archives : `FTH1_projet_pmdo_0812.zip` et `FTH1_calques_png_8px.zip`.
