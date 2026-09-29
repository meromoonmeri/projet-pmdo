# FTH1 — références et génération

Les deux références sont déjà versionnées dans ce checkout; aucune donnée d'une branche sœur ou de `main` n'est copiée :

- `source/references_54d3731/thunder.png` : image de scène 432×320 ; le plateau, falaises et nuages du sommet servent de guide visuel.
- `Game Boy Advance - Pokemon Mystery Dungeon_ Red Rescue Team - Dungeon Boss Rooms - Mt. Thunder.png` : scène plus panneau de sprites en bas. Le builder n'utilise que les boîtes documentées de ce panneau pour extraire les éclairs et l'arc Flash.

## Décor

Prompt envoyé au générateur, capture `thunder.png` en référence :

> New variation of a PMD Mt. Thunder summit boss room, using the provided summit screenshot as the exact reference for material, palette, shape language and composition. 4:3 landscape, 1200x896. Make the isolated sandy summit plateau occupy only about 72% of the image width and 72% of image height, centered, leaving broad visible bands of layered scalloped storm clouds on BOTH left and right and across the foreground and upper background. The platform is a broad oval/rounded irregular summit, not a corridor: open pale butter-yellow sand arena with sparse tiny grey pebbles and only three or four small pointed tan rock spurs near the outer edge. Its rugged tan/brown cracked cliff wall is visible around the whole rim. Around the mountain is the same storm-cloud sea from the reference: muted dark purple-grey clouds high in frame, medium slate-lavender clouds at the sides, bright white-grey clouds in the lower foreground; dark storm sky beyond. Match the screenshot's exact warm sand, brown stone, subdued gray-purple clouds, and crisp pixel-art cluster shapes. Top-down three-quarter PMD battle-map pixel art, compact low-resolution clusters, no smooth painting, no gradients, no 3D, no antialiasing. Leave the centre of the platform empty for a boss marker and a clear open strip from the bottom of the platform to its centre. This is a summit boss room, no trail, no cave entrance, no arch, no building, no shrine, no altar, no crystal, no flowers, no tree, no water, no waterfall, no lava, no snow, no lightning in the generated art, no electric symbols, no characters, no Pokémon, no text, no UI, no border or grid.

## Segmentation guide

`objets_magenta.png` is an edit of the chosen decor; pure #FF00FF marks the summit's yellow sand top surface. The generated guide is inspected against the original, then used only for masks. Magenta pixels never reach the final layers or Ground. Stone spurs and gravel remain separate foreground objects; collision treats small surface stones as passable.

## Lighting sprites

The lightning sprites and Flash arc are cropped directly from the lower sprite panel of the already-versioned GBA reference using the box coordinates and RGB swatches in `build.py`. Their pixels and colors are retained without resize or recolor. The new map-specific placement and 48-phase flash timing are authored here; they are not presented as official animation timing.

## Storage

The output is confined to `renders/fin_mt_thunder_v1/`. The new bundle is only this map's exports; existing main/sibling render folders and packages are not copied into it. Shared builder utilities are imported from this branch's source code instead of duplicated.
