# Mémoire de reprise — Passage du Canyon des Piliers / CPL1

Mise à jour : 7 octobre 2026. Projet sous `source/defile_aiguilles_v1/`, rendus dans ce dossier, aperçu `apercu_defile_aiguilles_v1.html` à la racine. La branche de session fixe est `arena/f4987da6-projet-pmdo`.

## Carte livrée

- Nom de travail : **Passage du Canyon des Piliers**; titre Ground **Défilé des Aiguilles**; préfixe local **CPL1** (pas un ID MAP_BG officiel).
- Référence ROM **D13P11A**, ressources BMA/BPC/BPL extraites du dépôt `pret/pmd-sky` au commit `c8073235b39746a7ee74e6cea16c730bd91a1e67` avec `skytemple-files`, commande ciblée `recuperer_maps.py rom --only D13P11A`.
- Le rendu réel du rip est fourni sous `source/defile_aiguilles_v1/bruts/D13P11A_ROM.png`. Il fait 456×456 px, une frame, deux couches, 30 couleurs, sans collision ni animation de palette; le GIF canonique versionné à la racine a été comparé et lui est pixel-identique.
- Carte carrée 456×456 px = 57×57 cellules de 8 px. Guide généré référencé sur D13P11A, quantifié sans tramage aux 30 couleurs du rip. Sable de base et raccord de 22 px sous la mesa copiés du rip; le reste de la composition reste généré/référencé, **pas des tuiles natives**.
- Calques : base canonique, sable/chemin référencés, falaises, piliers/blocs, Top vide. Masque d'obstacles; marqueurs `entrance`/`sortie` provisoires; chemin libre 16×16 validé algorithmiquement.

## Livrables et vérification

- `CPL1_projet_pmdo_0812.zip` — SHA-256 `cd6b4277467c8fb681128a717cb48362a30231e7db41e58daf1d7dec43b5f81b` (285 089 octets).
- `CPL1_calques_png_8px.zip` — SHA-256 `6ffef09cb4ca8342422e6d988d02abe274a40a54f74b50e83a88bce41412a92a` (3 267 645 octets); inclut calques, masques, revue, rip et guide généré.
- `SHA256SUMS.json` : empreintes des deux packs et sources; `manifest.json` : provenance, palette, connecteur, compteurs et limites.
- Résultat combiné des suites CPL1 et outil ROM : **11 PASS, 1 ignoré** (le test des rendus complets, car le cache complet de ROM n'est pas conservé). Le rendu ciblé D13P11A a été extrait, vérifié, copié dans les sources puis le cache ROM partiel supprimé pour préserver l'ignorance attendue du test complet.
- Aucun lancement PMDO, GPU, gameplay ni approbation artistique; il faut valider en éditeur les collisions, l'occlusion, les marqueurs et le raccord. Les warps ne sont pas reliés.

## Continuité Colonnes Ocre

Les anciens ZIP `OCO1_projet_pmdo_0812.zip` et `OCO1_calques_png_8px.zip` ne sont pas dans le checkout restauré jusqu'à `0b52defd`. La recherche Drive initiale n'avait trouvé aucun fichier OCO. Les sommes historiques connues sont respectivement `14c65d67899a0ea8d29673b66938623362a5d7eaef23ef69f6c8a4f8b46932f4` et `658f93c5a10f053dcc32080bf3e7f347d4e8ca25212889ee176414ab09c0d0e8`; elles ne prouvent pas que les archives soient récupérables. Ne pas prétendre qu'Ocre a été restauré; demander une copie si l'utilisateur veut récupérer ces anciens livrables.

Les dossiers `source/defile_aiguilles_v1/` et `renders/defile_aiguilles_v1/` du dépôt sont la source de vérité. Google Drive est un miroir de continuité, pas un remplacement du dépôt.
