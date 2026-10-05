# EPR1 — rendu et exports

**Entrée du Sentier des Ruines**, 4:3 (768×576 px), référence stylistique `P22P01A`. L'entrée sud, la clairière de boss et la sortie sous l'arche nord restent reliées par un passage ouvert. Le manifeste adjacent contient les mesures, la provenance et les marqueurs.

- Aperçu : `apercu_entree_passage_ruines_v1.html` à la racine ; l'index servi sur le port 8000 liste aussi cette page.
- PNG transparents alignés 8 px : `layers/` ; poussière lumineuse calculée en 24 phases : `anim/`.
- Compositions de phase : `EPR1_scene_t000.png` à `EPR1_scene_t184.png`, pas de 8 ticks.
- Animation consolidée : `EPR1_anim.png` (APNG) et `EPR1_anim.webp`.
- Fichier de calques : `EPR1_entree_passage_ruines.ora` (calque complet de référence masqué par défaut).
- Grille de marche : `EPR1_walkability.png` ; superposition verte = cellules marchables, les trois repères sont colorés.
- Projet PMDO 0.8.12 : `mod_entree_passage_ruines_pmdo_0812.zip` à la racine.
- Pack complet : `livrable_entree_passage_ruines_v1.zip` à la racine.
- Build et six tests : `source/entree_passage_ruines_v1/`.

Distance RGB moyenne vers la palette P22P01A : sol 6,89, murs 5,63, décors 10,34, scène 8,26 (seuil <35). Le build rapporte 2 136 cellules marchables et 6 869 tuiles PMDO. Pollen et composition sont générés ; les pixels ne sont pas certifiés natifs. `art_approved: false`, `runtime_tested: false`.
