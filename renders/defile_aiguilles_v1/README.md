# Défilé des Aiguilles — CPL1 (code interne provisoire)

Carte carrée **456×456 px**, 57×57 cellules de 8 px, guidée par le fond D13P11A. Aperçu : [`apercu_defile_aiguilles_v1.html`](../../apercu_defile_aiguilles_v1.html). Source et méthode : [`source/defile_aiguilles_v1/README.md`](../../source/defile_aiguilles_v1/README.md).

- Référence originale : `D13P11A_ROM.png` (rendu ROM 456×456 px, une frame, 30 couleurs RGB distinctes, pas d'animation palette selon `index_rom.json`).
- Composition : guide généré référencé sur D13P11A, réduit à la taille carrée de la référence; couleurs quantifiées sans tramage dans les 30 couleurs du rip.
- Les couleurs de sable, de grès et le patch de base viennent du rip; les formes générées restent des rendus référencés, **pas des tuiles originales**.
- Ground PMDO 0.8.12, calques séparés (base canonique, sable/chemin générés référencés, falaises, piliers), collisions et marqueurs de transit provisoires. Un col de sable de 22 px, texturé avec un patch du rip, relie les deux tronçons sous la mesa.
- Écart RGB moyen des matières au rip : sable 10.92, grès 8.63.

Packs produits après tests : `CPL1_projet_pmdo_0812.zip` et `CPL1_calques_png_8px.zip`; empreintes : `SHA256SUMS.json`. Aucun runtime PMDO, rendu GPU ou gameplay n'est revendiqué.
