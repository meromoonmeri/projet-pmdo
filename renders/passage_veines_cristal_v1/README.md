# Passage des Veines Cristallines — PVC1 (code local)

Carte 4:3 **768×576 px**, 96×72 cellules de 8 px (`TexSize=1`). Aperçu : [`apercu_passage_veines_cristal_v1.html`](../../apercu_passage_veines_cristal_v1.html). Build : [`source/passage_veines_cristal_v1/`](../../source/passage_veines_cristal_v1/).

- Rip canonique D17P33A : 456×504 px, 12 rendus, 2 couches, 96 couleurs RGB distinctes; PNG et animation WebP extraits par skytemple-files. Les 12 frames du rendu ROM et du GIF galerie sont pixel-identiques.
- Animations du rip : BPA1 = 6 frames × 10 ticks; BPA5 = 4 × 10 ticks. Le cycle combiné dure 12 phases / 120 ticks. Les durées d'affichage GIF/WebP ne définissent pas le timing du jeu.
- Le décor et le sol ont été générés séparément avec le rip comme référence, segmentés, normalisés uniformément à 768×576 puis quantifiés sans tramage dans la palette exacte du rip. **Aucun pixel de texture natif n'est copié** : formes et textures demeurent générées.
- Calques éditables : sol complet, bordure minérale, alcôve géode, cristaux, veine lumineuse, reflets (6 phases), ondes de la veine (4 phases), plus Top vide dans le Ground.
- Ground PMDO 0.8.12; collisions calculées et marqueurs `entrance` / `sortie` provisoires. Destinations/warps à relier.
- Tests unitaires, exports, ZIP et provenance : `test_build.py`, `package.py`, `manifest.json`, `SHA256SUMS.json`.

**Limites** : les animations visuelles sont générées; seules leurs cadences 6/4 × 10 ticks s'inspirent des BPA. Aucun lancement PMDO, test GPU/gameplay ni approbation artistique n'est revendiqué.
