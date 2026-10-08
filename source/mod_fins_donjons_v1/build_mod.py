"""Assemble un mod PMDO 0.8.12 à partir des livraisons fin_* existantes.

Aucun décor ni Ground n'est recalculé : les banques .tile, les Grounds .rsground
et les scripts Lua sont repris octet pour octet des ZIP projets individuels.
Seuls le namespace Lua, l'index consolidé, le Mod.xml et la documentation sont
propres à ce mod.

Lancer : .venv/bin/python source/mod_fins_donjons_v1/build_mod.py
Puis :   .venv/bin/python -m unittest source.mod_fins_donjons_v1.test_mod -v
"""
from pathlib import Path, PurePosixPath
import hashlib
import html
import importlib.util
import io
import json
import shutil
import struct
import uuid
import zipfile

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
LOT = 'mod_fins_donjons_v1'
NAMESPACE = 'guilde_fins_donjons'
TARGET = '0.8.12'
VERSION = '1.0.0.0'
OUT = R / 'renders' / LOT
STAGE = R / '.cache' / LOT / NAMESPACE
ZIP = OUT / f'{NAMESPACE}_pmdo_0812.zip'
PREVIEW = R / f'apercu_{LOT}.html'
FIXED_DATE = (2026, 10, 8, 12, 0, 0)

# Les neuf emplacements de la série suivent l'ordre consigné dans README.md.
# FGG1 est gardée comme ancienne variante, FOC1 comme map spéciale hors série.
MAPS = [
    {'folder': 'fin_vapeur_sommet_v1', 'prefix': 'FVS1',
     'title': 'Fin Vapeur — sommet de Steam Cave', 'scene': 'FVS1_scene_t000.png',
     'group': 'serie', 'order': 1},
    {'folder': 'fin_cratere_fosse_v1', 'prefix': 'FCF1',
     'title': 'Fin Cratère — fosse de Dark Crater', 'scene': 'FCF1_scene_t000.png',
     'group': 'serie', 'order': 2},
    {'folder': 'fin_ruine_puits_v1', 'prefix': 'FRP1',
     'title': 'Fin Ruine — puits de Sealed Ruin', 'scene': 'FRP1_scene_t000.png',
     'group': 'serie', 'order': 3},
    {'folder': 'fin_givre_aurore_v2', 'prefix': 'FGG2',
     'title': 'Fin Givre V2 — Frosty Grotto sous les aurores', 'scene': 'FGG2_scene_t000.png',
     'group': 'serie', 'order': 4},
    {'folder': 'fin_bristle_sommet_v1', 'prefix': 'FBS1',
     'title': 'Fin Bristle — sommet de Mt. Bristle', 'scene': 'FBS1_scene_t000.png',
     'group': 'serie', 'order': 5},
    {'folder': 'fin_jungle_sud_v1', 'prefix': 'FJS1',
     'title': 'Fin Jungle — Southern Jungle', 'scene': 'FJS1_scene_t000.png',
     'group': 'serie', 'order': 6},
    {'folder': 'fin_waterfall_cave_v1', 'prefix': 'FWC1',
     'title': 'Fin Waterfall Cave — salle du joyau', 'scene': 'FWC1_scene_t000.png',
     'group': 'serie', 'order': 7},
    {'folder': 'fin_sables_mouvants_v1', 'prefix': 'FSM1',
     'title': 'Fin Sables mouvants — arène du désert', 'scene': 'FSM1_scene_t000.png',
     'group': 'serie', 'order': 8},
    {'folder': 'fin_star_cave_v1', 'prefix': 'FST1',
     'title': 'Fin Star Cave — arène de cristal', 'scene': 'FST1_scene_t000.png',
     'group': 'serie', 'order': 9},
    {'folder': 'fin_givre_grotte_v1', 'prefix': 'FGG1',
     'title': 'Fin Givre V1 — Frosty Grotto (variante conservée)', 'scene': 'FGG1_scene_t000.png',
     'group': 'variante', 'order': None},
    {'folder': 'fin_ocean_kyogre_v1', 'prefix': 'FOC1',
     'title': 'Fin Océan — arène de Kyogre (hors-série)', 'scene': 'FOC1_scene_t000.png',
     'group': 'hors_serie', 'order': None},
]
PLANNED = [
    'Fin Clairière tropicale',
    'Fin Couloir violet',
    'Fin Mt. Thunder',
    'Fin Jardin secret',
]


def loadmod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INST = loadmod('pmdo_installer_for_fins', R / 'source/pmdo_cote/INSTALLER.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha(Path(path).read_bytes())


def source_zip(map_def):
    return R / 'renders' / map_def['folder'] / f"{map_def['prefix']}_projet_pmdo_0812.zip"


def temporary_index(raw):
    path = R / '.cache' / LOT / 'source_index.idx'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def make_installer_bytes():
    """Réutilise l'installateur commun, avec fusion d'index non destructive."""
    script = (R / 'source/pmdo_cote/INSTALLER.py').read_text(encoding='utf-8')
    needle = '            relative = src.relative_to(source)\n'
    if script.count(needle) != 1:
        raise RuntimeError('Le point d’insertion de l’installateur a changé : revoir le patch index.idx.')
    script = script.replace(
        needle,
        needle + "            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n",
    )
    return script.encode('utf-8')


def tile_locations(raw):
    """Lit l'index spatial d'une banque .tile sans décoder ses images."""
    if len(raw) < 8:
        raise ValueError('Banque .tile trop courte.')
    _, count = struct.unpack_from('<ii', raw, 0)
    if count < 0 or 8 + count * 16 > len(raw):
        raise ValueError(f'Index spatial .tile invalide (count={count}, bytes={len(raw)}).')
    return {struct.unpack_from('<ii', raw, 8 + i * 16) for i in range(count)}


def read_source(map_def):
    """Lit et audite un ZIP projet, sans extraire ni modifier sa source."""
    path = source_zip(map_def)
    if not path.is_file():
        raise FileNotFoundError(f'ZIP projet manquant : {path.relative_to(R)}')
    with zipfile.ZipFile(path) as zf:
        files = [name for name in zf.namelist() if not name.endswith('/')]
        roots = {name.split('/', 1)[0] for name in files}
        if len(roots) != 1:
            raise ValueError(f'{path.name}: racines ZIP inattendues {sorted(roots)}')
        root = next(iter(roots))
        tile_paths = [name for name in files if name.startswith(root + '/Content/Tile/') and name.endswith('.tile')]
        ground_paths = [name for name in files if name.startswith(root + '/Data/Ground/') and name.endswith('.rsground')]
        script_paths = [name for name in files if name.startswith(root + '/Data/Script/') and name.endswith('.lua')]
        index_path = f'{root}/Content/Tile/index.idx'
        if index_path not in files:
            raise ValueError(f'{path.name}: Content/Tile/index.idx absent.')
        if len(ground_paths) != 1 or len(script_paths) != 1 or not tile_paths:
            raise ValueError(
                f'{path.name}: attend un Ground, un script Lua et des banques; '
                f'got grounds={len(ground_paths)}, scripts={len(script_paths)}, tiles={len(tile_paths)}.'
            )
        tiles = {PurePosixPath(name).stem: zf.read(name) for name in sorted(tile_paths)}
        ground_path = ground_paths[0]
        script_path = script_paths[0]
        ground_raw = zf.read(ground_path)
        script_raw = zf.read(script_path)
        source_index = INST.read_index(temporary_index(zf.read(index_path)))
        if set(source_index) != set(tiles):
            raise ValueError(f'{path.name}: l’index source et les banques ne correspondent pas.')
        for bank, raw in tiles.items():
            if not bank.startswith(map_def['prefix'] + '_'):
                raise ValueError(f'{path.name}: nom de banque hors préfixe {map_def["prefix"]}: {bank}')
            if source_index[bank] != INST.read_node(io.BytesIO(raw)):
                raise ValueError(f'{path.name}: nœud index incorrect pour {bank}.')
        for name in files:
            rel = name[len(root) + 1:]
            if rel.startswith('Content/BG/') or rel.startswith('Data/BG/'):
                raise ValueError(f'{path.name}: fond non prévu dans ce lot de cartes : {rel}')
        ground_asset = PurePosixPath(ground_path).stem
        manifest_path = R / 'renders' / map_def['folder'] / 'manifest.json'
        source_manifest_raw = manifest_path.read_bytes()
        source_manifest = json.loads(source_manifest_raw)
        pmdo = source_manifest.get('pmdo', {})
        if pmdo.get('asset') != ground_asset:
            raise ValueError(f'{path.name}: asset du Ground différent du manifeste source.')
        if set(pmdo.get('banks', [])) != set(tiles):
            raise ValueError(f'{path.name}: banques différentes de celles du manifeste source.')
        return {
            'folder': map_def['folder'],
            'prefix': map_def['prefix'],
            'title': map_def['title'],
            'group': map_def['group'],
            'order': map_def['order'],
            'scene': map_def['scene'],
            'preview': f"apercu_{map_def['folder']}.html",
            'source_zip': path.relative_to(R).as_posix(),
            'source_zip_sha256': sha_file(path),
            'source_manifest_sha256': sha(source_manifest_raw),
            'source_project_root': root,
            'source_namespace': pmdo.get('namespace'),
            'source_script_path': script_path[len(root) + 1:],
            'script_filename': PurePosixPath(script_path).name,
            'ground_asset': ground_asset,
            'ground_source_path': ground_path[len(root) + 1:],
            'ground_sha256': sha(ground_raw),
            'script_sha256': sha(script_raw),
            'tiles': tiles,
            'ground_raw': ground_raw,
            'script_raw': script_raw,
            'source_manifest': source_manifest,
            'source_archive_files': {name[len(root) + 1:] for name in files},
        }


def ground_info(raw, tile_bytes, prefix):
    """Contrôle un Ground et extrait calques, pistes animées et marqueurs."""
    doc = json.loads(raw)
    if doc.get('Version') != '0.8.12.0':
        raise ValueError(f'{prefix}: version Ground inattendue {doc.get("Version")!r}.')
    obj = doc['Object']
    layers = obj['Layers']
    if not layers:
        raise ValueError(f'{prefix}: aucun calque.')
    cells_w = len(layers[0]['Tiles'])
    cells_h = len(layers[0]['Tiles'][0])
    size_px = [cells_w * 8, cells_h * 8]
    if size_px != [768, 576]:
        raise ValueError(f'{prefix}: format attendu 768 × 576, obtenu {size_px}.')
    if obj.get('TexSize') != 1:
        raise ValueError(f'{prefix}: TexSize doit être 1, reçu {obj.get("TexSize")!r}.')
    if layers[-1].get('Layer') != 4:
        raise ValueError(f'{prefix}: le dernier calque n’est pas le calque Top (Layer=4).')
    if len(obj.get('obstacles', [])) != cells_w or any(len(col) != cells_h for col in obj.get('obstacles', [])):
        raise ValueError(f'{prefix}: dimensions de collision différentes du Ground.')
    locations = {name: tile_locations(raw_tile) for name, raw_tile in tile_bytes.items()}
    used_banks = set()
    layer_details = []
    all_animations = set()
    for layer in layers:
        if len(layer['Tiles']) != cells_w or any(len(col) != cells_h for col in layer['Tiles']):
            raise ValueError(f'{prefix}: dimensions irrégulières dans le calque {layer.get("Name")!r}.')
        animated = set()
        for x, col in enumerate(layer['Tiles']):
            for y, cell in enumerate(col):
                for tile in cell.get('Layers', []):
                    frames = tile.get('Frames', [])
                    if not frames:
                        continue
                    if len(frames) > 1:
                        pattern = (len(frames), int(tile['FrameLength']))
                        animated.add(pattern)
                        all_animations.add(pattern)
                    for frame in frames:
                        bank = frame['Sheet']
                        if bank not in locations:
                            raise ValueError(f'{prefix}: banque absente {bank} à {x},{y}.')
                        point = (int(frame['TexLoc']['X']), int(frame['TexLoc']['Y']))
                        if point not in locations[bank]:
                            raise ValueError(f'{prefix}: tuile absente de {bank} à {point}, cellule {x},{y}.')
                        used_banks.add(bank)
        layer_details.append({
            'name': str(layer.get('Name', '')),
            'layer_id': layer.get('Layer'),
            'visible': bool(layer.get('Visible', True)),
            'animations': [{'frames': n, 'frame_length_ticks': ticks} for n, ticks in sorted(animated)],
        })
    marker_map = {}
    for entity_group in obj.get('Entities', []):
        for marker in entity_group.get('Markers', []):
            name = marker['EntName']
            collider = marker['Collider']
            box = [int(collider['X']), int(collider['Y']), int(collider['Width']), int(collider['Height'])]
            if name in marker_map:
                raise ValueError(f'{prefix}: marqueur dupliqué {name}.')
            if box[0] < 0 or box[1] < 0 or box[0] + box[2] > size_px[0] or box[1] + box[3] > size_px[1]:
                raise ValueError(f'{prefix}: marqueur hors carte {name}={box}.')
            marker_map[name] = {'xy_px': box[:2], 'size_px': box[2:]}
    if 'entrance' not in marker_map:
        raise ValueError(f'{prefix}: marqueur entrance absent.')
    if used_banks != set(tile_bytes):
        unused = sorted(set(tile_bytes) - used_banks)
        raise ValueError(f'{prefix}: banques jamais référencées dans le Ground: {unused}.')
    return {
        'name': obj.get('Name', {}).get('DefaultText', obj.get('Name', '')) if isinstance(obj.get('Name'), dict) else obj.get('Name', ''),
        'size_px': size_px,
        'grid_8px': [cells_w, cells_h],
        'tex_size': obj.get('TexSize'),
        'layer_count': len(layers),
        'layers': layer_details,
        'animations': [{'frames': n, 'frame_length_ticks': ticks} for n, ticks in sorted(all_animations)],
        'used_banks': sorted(used_banks),
        'markers': marker_map,
        'obstacle_cells': [len(obj['obstacles']), len(obj['obstacles'][0])],
        'version': doc['Version'],
        'asset': obj.get('AssetName'),
    }


def zipdir(path, root):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for item in sorted(root.rglob('*')):
            if item.is_file():
                info = zipfile.ZipInfo(f'{root.name}/' + item.relative_to(root).as_posix(), FIXED_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                zf.writestr(info, item.read_bytes(), compresslevel=9)


def mod_xml(count):
    uid = uuid.uuid5(uuid.NAMESPACE_URL, f'meromoonmeri/projet-pmdo/{NAMESPACE}')
    return f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Guilde Treehouse - Fins de donjon ({count} cartes) - 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Neuf Ground multicalques dans l'ordre de la serie des fins, plus une variante de Givre et Fin Ocean. Mod d'edition : marqueurs et collisions sont fournis, aucun warp ni destination de donjon n'est raccorde.</Description>
  <Namespace>{NAMESPACE}</Namespace>
  <UUID>{uid}</UUID>
  <Version>{VERSION}</Version>
  <GameVersion>{TARGET}.0</GameVersion>
  <ModType>Quest</ModType>
  <Relationships />
</Header>
'''


def group_label(row):
    if row['group'] == 'serie':
        return f"Série — {row['order']:02d}"
    if row['group'] == 'variante':
        return 'Variante conservée'
    return 'Hors-série'


def animation_text(ground):
    items = []
    for layer in ground['layers']:
        for anim in layer['animations']:
            items.append(f"{layer['name']} : {anim['frames']} × {anim['frame_length_ticks']} ticks")
    return '; '.join(items) if items else 'Aucune animation détectée'


def readme(rows):
    core = [row for row in rows if row['group'] == 'serie']
    variants = [row for row in rows if row['group'] != 'serie']
    lines = [
        f'# Guilde Treehouse — fins de donjon ({len(rows)} Grounds) — mod PMDO {TARGET}', '',
        f"Mod d’édition autonome, namespace `{NAMESPACE}`. Il rassemble **{len(core)} cartes de la série principale**, dans l’ordre du mod, "
        f"et **{len(variants)} cartes conservées en complément** (ancienne variante de Givre et map Océan hors-série). Les onze Grounds sont "
        'au format 768 × 576 px, grille 8 px (96 × 72 cases), et gardent leurs calques PMDO, animations, collisions et marqueurs propres.', '',
        '**Assemblage sans retouche des maps :** banques `.tile`, Grounds `.rsground` et scripts Lua sont copiés octet pour octet depuis les ZIP '
        'projets individuels. Seuls l’index des banques est fusionné et les scripts sont rangés sous le namespace commun. Les README et manifestes '
        'de chaque lot restent la référence pour sa méthode artistique et la provenance de ses pixels.', '',
        '## Installer', '',
        f'- **Mod séparé** : extraire `{NAMESPACE}` dans `PMDO/MODS/`, activer le mod puis ouvrir un Ground dans l’éditeur PMDO.',
        '- **Mod existant** : lancer `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, vérifier le plan, puis relancer sans `--dry-run`. '
        'L’installateur fusionne `index.idx`, fait une sauvegarde et refuse d’écraser un fichier différent.', '',
        '## Série principale et compléments', '',
        '| Ordre | Préfixe | Carte | Ground | Calques (bas → haut) | Animations (calque : frames × ticks) | Marqueurs |',
        '|---:|---|---|---|---|---|---|',
    ]
    for row in rows:
        ground = row['ground']
        order = str(row['order']) if row['group'] == 'serie' else '—'
        layers = ' → '.join(layer['name'] for layer in ground['layers'])
        markers = ', '.join(f"`{name}` {tuple(info['xy_px'])}" for name, info in ground['markers'].items())
        lines.append(
            f"| {order} | **{row['prefix']}** | {row['title']}<br>{group_label(row)} | "
            f"`{row['ground_asset']}` | {layers} | {animation_text(ground)} | {markers} |"
        )
    lines += [
        '',
        '**État de la série :** cette première édition contient les neuf fins actuellement dans l’ordre principal, de FVS1 à FST1. '
        'Fin Clairière tropicale, Fin Couloir violet, Fin Mt. Thunder et Fin Jardin secret restent à créer ; elles ne sont pas simulées ni incluses. '
        'FGG1 et FGG2 sont toutes deux gardées : FGG2 occupe le quatrième emplacement de la série, FGG1 est une variante antérieure. FOC1 est '
        'proposée comme map bonus, hors de cet ordre.', '',
        '## Commandes de reproduction', '',
        '```sh',
        '.venv/bin/python source/mod_fins_donjons_v1/build_mod.py',
        '.venv/bin/python -m unittest source.mod_fins_donjons_v1.test_mod -v',
        '```', '',
        'Le build ne lance aucun générateur d’images et ne change pas les ZIP des cartes sources. L’archive mod est reproductible (ordre trié, '
        'horodatage ZIP fixe). La galerie `apercu_mod_fins_donjons_v1.html` ouvre les aperçus animés individuels ; chaque aperçu conserve ses contrôles '
        'de calques.', '',
        '## Limites de validation', '',
        '- Les tests vérifient les fichiers, les index, les références des tuiles, les calques, marqueurs, collisions, l’installation simulée et la '
        'conservation octet pour octet des contenus sources.',
        '- **Aucun Ground n’a été ouvert dans PMDO pendant ce build.** Le chargement moteur, l’affichage, les collisions en mouvement, le gameplay et '
        'les raccords de donjon ne sont pas validés. Aucun warp n’est ajouté.',
        '- Les indicateurs `art_approved` des lots sources ne sont pas changés ; l’assemblage du mod ne vaut pas validation artistique des cartes.',
        '',
    ]
    return '\n'.join(lines)


def make_planche(rows):
    cols, thumb_w, thumb_h, pad, label_h = 4, 256, 192, 12, 38
    row_count = (len(rows) + cols - 1) // cols
    image = Image.new('RGB', (pad + cols * (thumb_w + pad), pad + row_count * (thumb_h + label_h + pad)), (19, 28, 38))
    draw = ImageDraw.Draw(image)
    font_path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    font = ImageFont.truetype(str(font_path), 12) if font_path.is_file() else ImageFont.load_default()
    for index, row in enumerate(rows):
        scene_path = R / 'renders' / row['folder'] / 'review' / row['scene']
        with Image.open(scene_path) as src:
            thumb = src.convert('RGB').resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = pad + (index % cols) * (thumb_w + pad)
        y = pad + (index // cols) * (thumb_h + label_h + pad)
        image.paste(thumb, (x, y))
        label = f"{row['prefix']} — {row['title']}"
        draw.text((x + 2, y + thumb_h + 5), label[:42], fill=(229, 235, 243), font=font)
        draw.text((x + 2, y + thumb_h + 20), group_label(row), fill=(157, 190, 203), font=font)
    return image


def gallery(rows, zip_relative):
    cards = []
    for row in rows:
        scene = f"renders/{row['folder']}/review/{row['scene']}"
        ground = row['ground']
        badges = html.escape(group_label(row))
        layers = html.escape(' · '.join(layer['name'] for layer in ground['layers']))
        cards.append(
            f'<a class="card" href="{html.escape(row["preview"])}">'
            f'<img src="{html.escape(scene)}" loading="lazy" alt="{html.escape(row["prefix"] + " — " + row["title"])}">'
            f'<span class="tag">{badges}</span><strong>{html.escape(row["prefix"])} — {html.escape(row["title"])}</strong>'
            f'<span>{ground["size_px"][0]} × {ground["size_px"][1]} · {ground["layer_count"]} calques · '
            f'{len(ground["animations"])} cadence(s)</span><small>{layers}</small></a>'
        )
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Guilde Treehouse — fins de donjon</title>
<style>
:root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;padding:24px;background:#111a22;color:#e8edf4;font:15px/1.55 system-ui,sans-serif}}
main{{max-width:1440px;margin:auto}}h1{{font-size:clamp(25px,4vw,40px);margin:0 0 8px}}p{{max-width:100ch;color:#b6c7d2}}
.actions{{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0 26px}}.button{{border:1px solid #66808e;border-radius:8px;padding:9px 13px;color:#e8edf4;text-decoration:none}}
.button.primary{{background:#d9bb78;color:#17212a;border-color:#d9bb78;font-weight:700}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:16px}}
.card{{display:flex;flex-direction:column;gap:7px;background:#17242d;border:1px solid #2c414c;border-radius:10px;padding:11px;color:inherit;text-decoration:none;min-width:0}}
.card:hover{{border-color:#d9bb78;transform:translateY(-1px)}}.card img{{display:block;width:100%;aspect-ratio:4/3;object-fit:contain;background:#081116;image-rendering:pixelated;border-radius:5px}}
.card strong{{font-size:16px}}.card span,.card small{{color:#b1c4ce}}.card small{{font-size:11px;line-height:1.4}}.tag{{align-self:flex-start;border:1px solid #45616f;border-radius:20px;padding:1px 8px;font-size:11px}}
footer{{margin-top:30px;color:#9fb2bd;font-size:13px}}code{{color:#e9d396}}
</style></head><body><main>
<h1>Guilde Treehouse — fins de donjon</h1>
<p>Mod d’édition PMDO 0.8.12 : neuf cartes dans la séquence principale, une variante de Givre et une map Océan hors-série. Chaque vignette ouvre
l’aperçu individuel avec ses calques, animations et contrôles. Les Grounds sources ne sont pas modifiés par l’assemblage.</p>
<div class="actions"><a class="button primary" href="{html.escape(zip_relative)}">Télécharger le mod PMDO</a>
<a class="button" href="renders/{LOT}/README.md">README et limites</a>
<a class="button" href="renders/{LOT}/planche_cartes.png">Planche complète</a></div>
<section class="grid">{''.join(cards)}</section>
<footer>Pas de test moteur PMDO ni de warp de donjon. Les quatre prochaines fins annoncées ne sont pas encore intégrées.</footer>
</main></body></html>
'''


def zip_project(path, stage):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for item in sorted(stage.rglob('*')):
            if item.is_file():
                info = zipfile.ZipInfo(f'{stage.name}/' + item.relative_to(stage).as_posix(), FIXED_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                zf.writestr(info, item.read_bytes(), compresslevel=9)


def build():
    prefixes = [item['prefix'] for item in MAPS]
    if len(set(prefixes)) != len(prefixes):
        raise ValueError('Préfixes de map en doublon.')
    core = [item for item in MAPS if item['group'] == 'serie']
    if [item['order'] for item in core] != list(range(1, len(core) + 1)):
        raise ValueError('Ordre de la série principale incomplet ou désordonné.')
    expected_archives = {p.parent.name for p in (R / 'renders').glob('fin_*/*_projet_pmdo_0812.zip')}
    configured_archives = {item['folder'] for item in MAPS}
    if configured_archives != expected_archives:
        raise ValueError(f'Lots fin_* oubliés ou inattendus: manquants={sorted(expected_archives-configured_archives)}, '
                         f'en trop={sorted(configured_archives-expected_archives)}')
    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE / 'Content/Tile').mkdir(parents=True)
    (STAGE / 'Data/Ground').mkdir(parents=True)
    OUT.mkdir(parents=True, exist_ok=True)

    index_nodes = {}
    rows = []
    for map_def in MAPS:
        source = read_source(map_def)
        for bank, raw in source['tiles'].items():
            if bank in index_nodes:
                raise ValueError(f'Banque partagée ou doublonnée entre cartes : {bank}')
            index_nodes[bank] = INST.read_node(io.BytesIO(raw))
            (STAGE / 'Content/Tile' / f'{bank}.tile').write_bytes(raw)
        asset = source['ground_asset']
        if (STAGE / 'Data/Ground' / f'{asset}.rsground').exists():
            raise ValueError(f'Ground en doublon : {asset}')
        (STAGE / 'Data/Ground' / f'{asset}.rsground').write_bytes(source['ground_raw'])
        script_dest = STAGE / 'Data/Script' / NAMESPACE / 'ground' / asset / source['script_filename']
        script_dest.parent.mkdir(parents=True, exist_ok=True)
        script_dest.write_bytes(source['script_raw'])
        info = ground_info(source['ground_raw'], source['tiles'], source['prefix'])
        if info['asset'] != asset or set(info['used_banks']) != set(source['tiles']):
            raise ValueError(f"{source['prefix']}: AssetName ou banques utilisées incohérents.")
        scene_path = R / 'renders' / source['folder'] / 'review' / source['scene']
        preview_path = R / source['preview']
        if not scene_path.is_file() or not preview_path.is_file():
            raise FileNotFoundError(f"{source['prefix']}: vignette ou aperçu manquant.")
        source_manifest = source['source_manifest']
        pmdo = source_manifest.get('pmdo', {})
        rows.append({
            'folder': source['folder'], 'prefix': source['prefix'], 'title': source['title'],
            'group': source['group'], 'order': source['order'], 'scene': source['scene'], 'preview': source['preview'],
            'source_zip': source['source_zip'], 'source_zip_sha256': source['source_zip_sha256'],
            'source_manifest_sha256': source['source_manifest_sha256'],
            'source_project_root': source['source_project_root'], 'source_namespace': source['source_namespace'],
            'source_script_path': source['source_script_path'], 'script_path_in_mod': script_dest.relative_to(STAGE).as_posix(),
            'script_sha256': source['script_sha256'], 'ground_source_path': source['ground_source_path'],
            'ground_asset': asset, 'ground_sha256': source['ground_sha256'],
            'tile_banks': sorted(source['tiles']),
            'tile_sha256': {name: sha(raw) for name, raw in sorted(source['tiles'].items())},
            'reference_method': source_manifest.get('method', source_manifest.get('methodology', 'Voir le manifeste du lot source.')),
            'reference': source_manifest.get('reference_da'),
            'source_art_approved': bool(source_manifest.get('art_approved', False)),
            'source_runtime_tested': bool(pmdo.get('runtime_tested', False)),
            'ground': info,
        })

    index_raw = INST.encode_index(index_nodes)
    (STAGE / 'Content/Tile/index.idx').write_bytes(index_raw)
    (STAGE / 'Mod.xml').write_text(mod_xml(len(rows)), encoding='utf-8')
    (STAGE / 'INSTALLER.py').write_bytes(make_installer_bytes())
    readme_text = readme(rows)
    (STAGE / 'README.md').write_text(readme_text, encoding='utf-8')
    manifest = {
        'lot': LOT, 'namespace': NAMESPACE, 'target': TARGET, 'mod_version': VERSION,
        'map_count': len(rows), 'main_series_count': len(core), 'tile_bank_count': len(index_nodes),
        'main_series_order': [row['prefix'] for row in rows if row['group'] == 'serie'],
        'preserved_complements': [row['prefix'] for row in rows if row['group'] != 'serie'],
        'planned_not_included': PLANNED,
        'assembly_method': 'ZIP projets existants; .tile, .rsground et scripts Lua conserves octet pour octet; index fusionne; '
                           'namespace commun pour les scripts; aucune generation de map ni retouche des pixels.',
        'runtime_tested': False,
        'art_approved': False,
        'maps': rows,
    }
    manifest_raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    (STAGE / 'manifest.json').write_bytes(manifest_raw)
    (OUT / 'manifest.json').write_bytes(manifest_raw)
    (OUT / 'README.md').write_text(readme_text, encoding='utf-8')
    (STAGE / 'Content/Tile/index.idx').write_bytes(index_raw)

    zip_project(ZIP, STAGE)
    planche_path = OUT / 'planche_cartes.png'
    make_planche(rows).save(planche_path)
    (R / f'apercu_{LOT}.html').write_text(
        gallery(rows, ZIP.relative_to(R).as_posix()), encoding='utf-8'
    )
    report = {
        'lot': LOT,
        'build_checks': 'PASS',
        'maps': len(rows),
        'main_series_maps': len(core),
        'tile_banks': len(index_nodes),
        'zip': ZIP.relative_to(R).as_posix(),
        'zip_sha256': sha_file(ZIP),
        'zip_bytes': ZIP.stat().st_size,
        'index_sha256': sha(index_raw),
        'runtime_tested': False,
        'art_approved': False,
    }
    (OUT / 'build_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({
        'maps': len(rows), 'series_principale': len(core), 'complements': len(rows) - len(core),
        'banques': len(index_nodes), 'Grounds': [row['ground_asset'] for row in rows],
        'zip': report['zip'], 'Mo': round(report['zip_bytes'] / 1e6, 2), 'sha256': report['zip_sha256'],
        'preview': PREVIEW.relative_to(R).as_posix(),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    build()
