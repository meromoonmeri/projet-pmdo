# Série de cartes PMD Red × Sky — v1

Série en cours, avec un premier pilote : `lac_de_verre/` (préfixe `LGV1`). La portée finale (nombre de cartes et thèmes suivants) reste ouverte; les références choisies pour ce pilote ne sont pas à reprendre comme paire au prochain lot.

## Méthode retenue

- **Correction de direction :** partir d’une vraie zone PMD, conserver son layout et ne le modifier que légèrement. Réutiliser les assets canoniques; aucun décor généré.
- Le Ground Sky `D52P11A` est décodé depuis son `.rsground` et son `.tile`; le rendu Python est comparé pixel pour pixel à la preview Sky locale.
- Une petite zone centrale d’eau réutilise des pixels issus des six rendus visuels Red `T01P02A`. Ce n’est pas la banque `.tile` Red; les pixels extraits ne sont donc pas présentés comme des tuiles natives.
- Gabarit **4:3 vaste** : Ground 504 × 408 px (63 × 51 cases), étendu par réflexion horizontale à 544 × 408 (68 × 51 cases) sans étirement. Bruts 1200 × 896, masque plein format, réduction BOX uniforme par `576/896`, crop centré vers **768 × 576** (96 × 72 cases de 8 px).
- Palette partagée de 96 couleurs, fond transparent ou masques séparés selon le calque; **pas de fond magenta**. Chaque lot garde `art_approved: false`, `native_texture_certified: false` et `runtime_tested: false` tant que les validations correspondantes n’ont pas eu lieu.

## Pilote 01 — Lac de Verre

- Sources : Red `T01P02A` (*Whiscash Pond*) et Sky `D52P11A` (code de preview; aucun nom canonique supplémentaire n’est affirmé).
- Sky `D04P12A` / *Waterfall Cave* est écartée car déjà reprise antérieurement.
- Dossier de build, bruts, copies canoniques, références et tests : `lac_de_verre/`.
- Livrables : `renders/serie_sources_croisees_v1/lac_de_verre/` et `apercu_serie_sources_croisees_v1.html`.
- Tests du pilote : **11 PASS**; aucun test de chargement/rendu dans le moteur PMDO.
