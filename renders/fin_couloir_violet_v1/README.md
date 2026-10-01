# FCO1 — Fin Couloir violet : arène de rochers (4:3, PMDO 0.8.12)

Onzième zone de fin de donjon de la série, après Fin Vapeur, Cratère, Ruine, Givre, Bristle, Jungle, Waterfall Cave, Sables mouvants, Star Cave et Clairière tropicale. Elle prolonge l'entrée **ECV1** (Couloir violet). Biome et portée choisis par l'agent, **à confirmer**.

- **Préfixe** : FCO1. FCV1 est cité comme pris par un repère d'une branche sœur dans les notes du 29 septembre (non accessible dans ce checkout : seules `main` et la branche de session existent), donc évité.
- **Référence** : `large.S05P03A.png.301f7a1eadda348357be0801e81faa2a.png` (312 × 720), passée au générateur avec le décor d'ECV1. C'est un **rendu généré référencé**, pas des tuiles natives.
- **Layout** : arrivée au sud par un couloir étroit entre deux parois de rochers (`entrance`), grande arène ronde, des amas de rochers posés près des parois, énorme pile de rochers dans l'alcôve du nord ; `boss` au centre de l'arène, `objectif` au pied de la pile. Ni sortie, ni warp, ni bouche sombre.
- **Bruts** (`source/fin_couloir_violet_v1/bruts/`) : `decor.png` (1200 × 896, premier essai, conforme), `sol_complet.png` et `poussiere_poses.png` (copiés d'ECV1, mêmes octets, sans nouvelle génération).
- **Calques** (11 dans le Ground, dont un Top vide) : sol complet, sol, ombres, gravillons, blocs, rochers, falaise, vide, éboulis, poussière. Boucle de scène : 120 ticks. Aucun calque translucide. Pas de calque de profondeur.
- **Animations** : mêmes fonctions qu'ECV1. Trois gravillons aux pixels et couleurs EXACTS du rip tombent du pied des parois de l'arène (quatre chutes décalées de 6 phases), un nuage de poussière à chaque impact. Le mouvement est créé par nous.
- **Fidélité au rip** (distance RVB moyenne par matière, seuil 35) : sol 10,3 (calque 14,1), roche 10,5 (rochers 13,6, blocs 20,8).
- **Accès** : cases praticables et bloquées dans `manifest.json` ; chemins 16 × 16 de l'arrivée au boss et à l'objectif vérifiés.
- **Tests** : `.venv/bin/python -m unittest source.fin_couloir_violet_v1.test_build -v` (12 PASS). 5 mutations vérifiées : boss collé à la paroi, objectif décalé, rochers rendus praticables, chute linéaire, vide rendu praticable.
- **Paquets** : `FCO1_projet_pmdo_0812.zip`, `FCO1_calques_png_8px.zip`, aperçu `apercu_fin_couloir_violet_v1.html` à la racine.

Limites : `runtime_tested: false`, `art_approved: false`. La pile du nord est une grosse pile de rochers du même style que les parois, pas un objet du jeu. Collisions, occlusion et gameplay ne sont pas déduits des contrôles d'images. Pas de boss nommé.
