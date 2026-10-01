# FTH1 — Fin Mt. Thunder : sommet d'orage (4:3, PMDO 0.8.12)

Douzième zone de fin de donjon de la série, après Fin Vapeur, Cratère, Ruine, Givre, Bristle, Jungle, Waterfall Cave, Sables mouvants, Star Cave, Clairière tropicale et Couloir violet (FCO1 et FCO2). Elle prolonge l'entrée **EMT1** (Mt. Thunder). Demandée le 1er octobre avec « passe a la prochaine map » après FCO2. Biome et portée choisis par l'agent, **à confirmer**.

- **Préfixe** : FTH1. FMT1 est cité comme repère par des branches sœurs (notes du 29 septembre, non accessibles ici) : évité.
- **Référence** : `Game Boy Advance - Pokemon Mystery Dungeon_ Red Rescue Team - Dungeon Boss Rooms - Mt. Thunder.png` (432 × 498), passée au générateur. C'est un **rendu généré référencé**, pas des tuiles natives.
- **Layout** : arrivée au sud par une crête de sable étroite qui sort des nuages, très grand plateau rond de sable bordé de falaises, quelques pics et cailloux près des bords, estrade de roche au nord (sans grotte, sans bouche sombre). `entrance` au sud, `boss` au centre du plateau, `objectif` au pied de l'estrade. Ni sortie, ni warp. Le dessus de l'estrade est séparé du plateau par la roche : il reste bloqué.
- **Bruts** (`source/fin_mt_thunder_v1/bruts/`) : `decor.png` (1200 × 896, premier essai, conforme) ; `sol_complet.png` copié d'EMT1 (mêmes octets, testé).
- **Calques** (10 dans le Ground, dont un Top vide) : sol complet, sable, cailloux, pics, falaise, ciel, nuages, lueurs, éclairs. Boucle de scène : 240 ticks (4 s). Aucun alpha intermédiaire.
- **Animations** (48 × 5 ticks, comme EMT1) : les 4 éclairs et l'arc « Flash » de la planche, pixels et couleurs EXACTS ; 6 frappes par boucle, une toutes les 8 phases, « Normal » 2 phases puis « Fading » 2 phases, éclair 1 à gauche seulement, les autres à gauche ou en miroir (note de la planche). Les frappes sont replacées pour ce décor, le long des flancs du plateau, jamais sur le relief (test). Placement et cadence créés par nous.
- **Fidélité au rip** (distance RVB, seuil 35) : sable 2,4 (calque 3,9), roche 8,0 (falaise 10,2), ciel 5,5 (6,9), nuages sombres 2,5 (2,9) et clairs 4,9 (6,8) ; sol complet 3,7.
- **Accès** : boss (376, 232), objectif (384, 112), entrée (376, 560) ; chemins 16 × 16 vérifiés ; 2188 cases praticables sur 6912.
- **Tests** : `.venv/bin/python -m unittest source.fin_mt_thunder_v1.test_build -v` (10 PASS, EMT1 adaptés : grotte, seuil et piton remplacés par un test de l'estrade, du boss et de l'objectif). 5 mutations vérifiées : boss collé au haut du plateau, éclair posé sur le plateau, objectif décalé, falaise rendue praticable, pics rendus praticables. Une première mutation (boss dans le coin) était arrêtée par l'assertion du build, pas par un test : elle a été remplacée.
- **Paquets** : `FTH1_projet_pmdo_0812.zip`, `FTH1_calques_png_8px.zip`, aperçu `apercu_fin_mt_thunder_v1.html` à la racine.

Limites : `runtime_tested: false`, `art_approved: false`. L'estrade du nord est une plate-forme de roche du même style que les falaises, pas un objet du jeu. Collisions, occlusion et gameplay ne sont pas déduits des contrôles d'images. Pas de boss nommé.
