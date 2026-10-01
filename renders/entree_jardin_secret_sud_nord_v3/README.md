# EJS3 — Entrée Jardin secret V3 : temple de Celebi et végétation animée, sud → nord, 4:3

- **Demande** : « rajoute un calque de mouvement de feuille et des animation de fleur palika halcyon et des petale de fleur », puis « lance toi » (1er octobre, après FJA1). Les questions de cadrage n'ont pas reçu de réponse : choix de l'agent, **à confirmer** : appliquer les mêmes trois calques à l'entrée du jardin secret, pour qu'entrée et fin soient assorties.
- **Nouvelle version** : EJS2 et EJS1 restent intactes. EJS3 relit les bruts d'EJS2 par chemin (`source/entree_jardin_secret_sud_nord_v2/bruts/`, jamais copiés) et reprend toute sa segmentation : mêmes 16 calques, même temple, mêmes marqueurs (`entrance`, `donjon_seuil`), aucun warp.
- **Taille** : 768 × 576 px = 96 × 72 cases de 8 px.

## Trois calques ajoutés (code et règles identiques à FJA1)

| Calque | Contenu | Animation |
|---|---|---|
| fleurs_halcyon | 14 touffes **natives de Palikadude/Halcyon** (`Vast_Steppe_Flower_Animations`, 3 dessins 24 × 24, commit 1522c7a8), pixels sans retouche, séquence 0 / 1 / 0 / 2, décalée de `i % 4` par touffe ; posées sur le sol praticable, hors prairie centrale, à 8 px au moins du temple, de la souche et des marches | 4 × 14 ticks |
| petales | 38 pétales (2 par touffe, 10 partis de fleurs du décor) aux couleurs exactes des fleurs du rip (247,255,231 ; 239,207,103 ; 223,127,119) ; ils tombent de 22 px et dérivent vers l'est ; jamais sur le fond, le rayon, le temple, la souche ni l'emblème | 24 × 14 ticks |
| feuilles | 513 amas de 2 à 12 px de feuilles claires des arbres et des haies, retirés des calques fixes et redessinés décalés de 1 à 2 px (houle d'ouest en est, 220 px d'onde) ; la phase 0 redonne **exactement** les calques arbres et haies d'origine (sha256 testé) | 8 × 7 ticks |

Les pétales violets des touffes Halcyon sont ceux de l'atlas natif (le test anti-magenta est exempté pour ce seul calque). Attribution à Palikadude et aux artistes d'origine ; aucune autorisation générale de redistribution n'est déduite.

## Ce qui change ailleurs

- L'**emblème**, le **rayon** et les **lucioles** passent de 24 × 5 à **24 × 7 ticks**, pour que la boucle commune de **336 ticks (5,6 s)** soit un multiple de toutes les cadences (EJS2 : 120 ticks).
- Calques : 19 + Top vide dans le Ground (EJS2 : 16 + Top).
- Fidélité au rip : inchangée (prairie 31,5, herbe 7,3, ombres 2,2, rochers 20,6, fond 11,7 ; seuil 35). Les nouveaux calques ne sont pas mesurés contre le rip, qui ne contient ni touffes Halcyon, ni pétales isolés.
- Accès : inchangé (2141 cases praticables, chemin 16 × 16 prouvé jusqu'au seuil). Les trois calques sont visuels et ne bloquent rien.

## Contrôles

- `.venv/bin/python -m unittest source.entree_jardin_secret_sud_nord_v3.test_build -v` : **17 PASS** (les 13 d'EJS2 adaptés, plus feuilles, fleurs Halcyon, pétales, boucle commune).
- 5 mutations détectées par les tests : houle non nulle à la phase 0, couleur de pétale hors rip, séquence de fleurs changée, touffes posées hors du sol praticable, pétales qui remontent. Une 6e (marge de 8 px autour du temple réduite à 1 px) ne change rien au résultat : l'échantillonnage du point le plus éloigné tient déjà les touffes à distance ; la marge reste, mais elle n'est pas démontrée par un test.
- Paquets : `EJS3_projet_pmdo_0812.zip`, `EJS3_calques_png_8px.zip`, aperçu `apercu_entree_jardin_secret_sud_nord_v3.html` à la racine.

Limites : `runtime_tested: false`, `art_approved: false`. Le calque de feuilles est une houle de pixels, pas un feuillage dessiné (≈ 4 000 tuiles sur 8 phases). Pas de test dans PMDO.
