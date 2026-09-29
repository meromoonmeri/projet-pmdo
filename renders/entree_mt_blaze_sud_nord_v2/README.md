# EMB2 — Mt. Blaze (PMDO 0.8.12)

Projet d’édition 4:3 (768 × 576 px, 96 × 72 cases). Le layout est reconstruit depuis la référence GBA : grand sol sableux en avant-plan, bassins de lave irréguliers sur les côtés, rochers, deux structures de pierre, puis une petite bouche sombre au centre-haut.

## Ouvrir le Ground

- **Projet séparé** : extraire `EMB2_projet_pmdo_0812.zip` dans `PMDO/MODS/`, activer le mod puis ouvrir le Ground `emb2_entree_mt_blaze`.
- **Dans un mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, contrôler le rapport, puis relancer sans `--dry-run`.

C’est une base graphique d’édition, pas une aventure jouable : aucun warp, Pokémon ou événement n’est ajouté.

## Sources de matière

Dans `EMB2_calques_png_8px.zip/sources/` :

- `layout_magenta.png` : le placement de lave est encodé par le magenta pur `#FF00FF`; la clé est testée par égalité exacte RGB, sans seuil ni tolérance.
- `lave_texture_rgba.png` : texture lave isolée par l’alpha exact du key magenta.
- `veines_roche_rgba.png` : fissures rocheuses extraites sur un alpha séparé.

Les images sources font 1200 × 896 px ; l’alpha est binaire et le RGB des pixels transparents vaut zéro. La vignette HTML permet d’inspecter ces trois sources.

## Calques (bas → haut)

`sol_complet` · `ombres` · `lave` · `sentier` · `eboulis` · `parois` · `piliers` · `grotte` · `veines_roche` · `Top`.

La lave et les fissures de roche utilisent les cycles de palettes 10 et 11 de D41P41A : 13 phases × 10 ticks, soit 130 ticks par boucle. Le mécanisme, l’ordre des crans et les couleurs viennent de l’étude locale d’Explorers of Sky ; ils sont adaptés au décor GBA Mt. Blaze et ne sont pas revendiqués comme animation originale de Red Rescue Team. Les positions restent fixes.

## Collisions

`entrance` est au sud dans le sol praticable ; `donjon_seuil` est devant la bouche de grotte. Une case est bloquée si plus de 25 % de ses pixels sont hors du masque du sentier. Le trajet pour un footprint 16 × 16 entre les marqueurs est vérifié par BFS. Les collisions, l’occlusion et le Ground restent à valider dans PMDO.

La vignette Mt. Blaze utilisée pour le layout est incluse dans le ZIP des calques sous `reference/` et documentée dans `manifest.json`. L’image finale est une reconstruction illustrée ; ce n’est pas un rip officiel.
