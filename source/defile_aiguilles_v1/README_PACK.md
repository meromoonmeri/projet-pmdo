# Défilé des Aiguilles — pack PMDO 0.8.12

Ground d'édition CPL1 (code local provisoire), 456×456 px / 57×57 tuiles de 8 px. Les pixels de composition sont générés et référencés sur D13P11A, puis quantifiés sur ses couleurs exactes; ils **ne sont pas** les tuiles originales du jeu. Voir `manifest.json` et le README source pour la provenance et les limites.

## Installer dans une copie de sauvegarde

1. Fermer PMDO.
2. Extraire l'archive dans un dossier temporaire.
3. Copier `INSTALLER.py` dans le dossier du mod qui contient `Mod.xml`.
4. Depuis ce dossier, lancer `python INSTALLER.py .`.
5. Dans PMDO, activer le mod, ouvrir les Ground maps, puis contrôler visuellement toutes les couches et collisions.

L'installateur standard-library-only préserve les fichiers en conflit et fusionne l'index des tuiles. Un col de sable de 22 px, texturé avec un patch du rip, raccorde les deux tronçons générés sous la mesa; vérifier son placement en jeu. Les marqueurs `entrance` et `sortie` n'ont pas de destination/warp relié. Pack d'édition, pas une aventure jouable. Le runtime PMDO, le GPU et le gameplay n'ont pas été testés.
