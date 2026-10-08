#!/usr/bin/env python3
"""LGV1 — Lac de Verre, variante légère d’un Ground PMD canonique.

Le décor de base est reconstruit pixel pour pixel depuis le Ground Sky D52P11A
et son tileset natif. Une petite zone centrale reçoit les pixels d’eau animés
prélevés dans les six frames Red T01P02A. Aucun décor n’est généré et aucun
pixel extrait n’est présenté comme une tuile native certifiée.

Le Ground source (63×51 cases, 504×408 px) est prolongé par réflexion de 5 cases
pour former un canvas 4:3 (68×51 cases), sans étirement. Le brut adapté est en
1200×896; les calques sont ensuite réduits uniformément vers 768×576 (96×72
cases de 8 px), avec recadrage centré. Le lac et son masque sont distincts; il
n’y a aucun fond magenta.

Lancer depuis la racine : .venv/bin/python source/serie_sources_croisees_v1/lac_de_verre/build.py
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import shutil
import uuid
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageChops, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / 'bruts'
REFS = HERE / 'references'
NATIVE_DIR = REFS / 'native_D52P11A'
NATIVE_GROUND = NATIVE_DIR / 'd52p11a.rsground'
NATIVE_TILE = NATIVE_DIR / 'D52p11a_Base.tile'
SKY_FILE = REFS / 'sky_D52P11A.png'
RED_FILES = [REFS / f'red_T01P02A_frame{i}.png' for i in range(6)]
OUT = ROOT / 'renders/serie_sources_croisees_v1/lac_de_verre'
STAGE = ROOT / '.cache/serie_sources_croisees_v1/lac_de_verre/lac_de_verre_sud_nord'
NAMESPACE = 'serie_sources_croisees_lac_de_verre'
ASSET = 'lgv1_lac_de_verre'
PFX = 'LGV1'

W, H = 768, 576
SRC_W, SRC_H = 1200, 896
SCALE = H / SRC_H
SCALED_W = round(SRC_W * SCALE)
CROP_X = (SCALED_W - W) // 2
CROP_RIGHT = SCALED_W - W - CROP_X
TILE = 8
PALETTE_COLORS = 96
WATER_FRAMES, WATER_TICKS = 6, 10
NATIVE_W, NATIVE_H = 504, 408
PAD_LEFT, PAD_RIGHT = 16, 24
ADAPTED_W, ADAPTED_H = NATIVE_W + PAD_LEFT + PAD_RIGHT, NATIVE_H
WATER_CROP = (270, 226, 334, 258)  # 64×32 px, eau ouverte de T01P02A
LAKE_X, LAKE_Y, LAKE_W, LAKE_H = 224, 216, 96, 48

RAW_FILES = [
    RAW / 'D52P11A_zone_1200x896.png',
    RAW / 'LGV1_lac_de_verre_frame0_1200x896.png',
    RAW / 'LGV1_masque_lac_1200x896.png',
]


def loadmod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Chargement impossible : {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert('RGB'), dtype=np.uint8)


def render_native_d52() -> tuple[Image.Image, np.ndarray, dict]:
    """Decode D52P11A from its Ground and .tile bank; assert preview equality."""
    reader = loadmod('audit_native_lgv1', ROOT / 'source/cote_v5_expeditions/audit_references.py')
    doc = json.loads(NATIVE_GROUND.read_text(encoding='utf-8-sig'))
    obj = doc['Object']
    if int(obj.get('TexSize', 0)) != 1 or len(obj.get('Layers', [])) != 1:
        raise AssertionError('Le Ground canonique D52P11A a changé de format')
    grid = obj['Layers'][0]['Tiles']
    grid_w, grid_h = len(grid), len(grid[0])
    if (grid_w, grid_h) != (63, 51):
        raise AssertionError(f'Grille D52P11A inattendue : {grid_w}×{grid_h}')
    tile_size, bank, _ = reader.tiles(NATIVE_TILE)
    if tile_size != TILE:
        raise AssertionError(f'Taille de tuile native inattendue : {tile_size}')
    rendered = Image.new('RGBA', (grid_w * TILE, grid_h * TILE), (0, 0, 0, 0))
    for x, column in enumerate(grid):
        for y, cell in enumerate(column):
            for track in cell.get('Layers', []):
                frame = track['Frames'][0]
                loc = frame['TexLoc']
                tile = reader.straight(bank[(loc['X'], loc['Y'])])
                rendered.alpha_composite(tile, (x * TILE, y * TILE))
    reference = Image.open(SKY_FILE).convert('RGBA')
    if rendered.size != (NATIVE_W, NATIVE_H) or reference.size != rendered.size:
        raise AssertionError('Dimensions du rendu Sky D52P11A inattendues')
    if ImageChops.difference(rendered, reference).getbbox() is not None:
        raise AssertionError('Le rendu .rsground/.tile ne correspond plus à la preview Sky locale')
    native_blocked = np.asarray([
        [int(obj['obstacles'][x][y].get('Tags', 0)) != 0 for x in range(grid_w)]
        for y in range(grid_h)
    ], dtype=bool)
    return rendered, native_blocked, {
        'ground_grid': [grid_w, grid_h],
        'native_render_px': [NATIVE_W, NATIVE_H],
        'tile_px': TILE,
        'ground_version': doc.get('Version'),
        'ground_sha256': sha(NATIVE_GROUND),
        'tile_sha256': sha(NATIVE_TILE),
        'render_matches_reference_png': True,
        'native_blocked_cells': int(native_blocked.sum()),
    }


def adapt_native_canvas(native: Image.Image) -> np.ndarray:
    """Reflect-pad only the sides: 63×51 → 68×51 cells, exactly 4:3."""
    pixels = np.asarray(native.convert('RGB'), dtype=np.uint8)
    adapted = np.pad(pixels, ((0, 0), (PAD_LEFT, PAD_RIGHT), (0, 0)), mode='reflect')
    if adapted.shape != (ADAPTED_H, ADAPTED_W, 3):
        raise AssertionError(f'Canvas adapté inattendu : {adapted.shape}')
    return adapted


def to_raw(array: np.ndarray, resample=Image.Resampling.NEAREST) -> np.ndarray:
    """Uniformly scale the 4:3 source to 1200×900 and crop 2 px top/bottom."""
    image = Image.fromarray(np.asarray(array))
    scaled = image.resize((SRC_W, 900), resample=resample)
    raw = scaled.crop((0, 2, SRC_W, 900 - 2))
    return np.asarray(raw)


def lake_mask_native() -> np.ndarray:
    mask = Image.new('L', (ADAPTED_W, ADAPTED_H), 0)
    x1, y1 = LAKE_X + LAKE_W - 1, LAKE_Y + LAKE_H - 1
    ImageDraw.Draw(mask).ellipse((LAKE_X, LAKE_Y, x1, y1), fill=255)
    return np.asarray(mask, dtype=np.uint8)


def water_crop_from_red(path: Path, water_geometry: np.ndarray,
                        nearest_water: tuple[np.ndarray, np.ndarray]) -> tuple[np.ndarray, dict]:
    """Extract a source frame using frame 0's water geometry, preserving animated colors."""
    source = Image.open(path).convert('RGB').crop(WATER_CROP)
    patch = np.asarray(source, dtype=np.uint8)
    if patch.shape[:2] != (32, 64) or water_geometry.shape != (32, 64):
        raise AssertionError(f'Recadrage Red inattendu : {patch.shape}, mask={water_geometry.shape}')
    p = patch.astype(np.int16)
    r, g, b = p.transpose(2, 0, 1)
    blue_coverage = float(((b > r + 10) & (b > g + 5) & (g > 35) & (b > 70)).mean())
    geometry_coverage = float(water_geometry.mean())
    if geometry_coverage < 0.88:
        raise AssertionError(f'Trop de rive/sol dans le masque du recadrage Red : {geometry_coverage:.3f}')
    # The same spatial mask is used for all frames: some official animated
    # water pixels turn green/teal temporarily and must not be mistaken for shore.
    filled = patch[nearest_water[0], nearest_water[1]]
    return filled, {
        'file': str(path.relative_to(ROOT)),
        'water_geometry_coverage': round(geometry_coverage, 6),
        'blue_pixel_ratio_this_frame': round(blue_coverage, 6),
        'mask_source': 'frame 0 water geometry reused for frames 0–5 to retain teal animation pixels',
        'crop_xyxy': list(WATER_CROP),
        'crop_px': [64, 32],
        'unique_rgb_after_fill': int(len(np.unique(filled.reshape(-1, 3), axis=0))),
    }


def palette_image(palette: np.ndarray) -> Image.Image:
    image = Image.new('P', (1, 1))
    values = np.zeros((256, 3), dtype=np.uint8)
    values[:len(palette)] = palette
    image.putpalette(values.reshape(-1).tolist())
    return image


def shared_native_palette(native_pixels: np.ndarray, water_patches: list[np.ndarray]) -> tuple[Image.Image, np.ndarray, dict]:
    """Keep every RGB used by the two source regions, then fill to 96 source RGBs."""
    required_chunks = [native_pixels.reshape(-1, 3)] + [p.reshape(-1, 3) for p in water_patches]
    required = np.unique(np.concatenate(required_chunks, axis=0), axis=0).astype(np.uint8)
    if len(required) > PALETTE_COLORS:
        raise AssertionError(f'{len(required)} couleurs source dépassent la palette partagée de 96')
    source_chunks = [rgb(path).reshape(-1, 3) for path in RED_FILES + [SKY_FILE]]
    candidates = np.unique(np.concatenate(source_chunks, axis=0), axis=0).astype(np.int32)
    chosen = required.astype(np.int32)
    while len(chosen) < PALETTE_COLORS:
        delta = candidates[:, None, :] - chosen[None, :, :]
        nearest = np.min(np.sum(delta * delta, axis=2), axis=1)
        candidate_index = int(np.argmax(nearest))
        candidate = candidates[candidate_index]
        if np.any(np.all(chosen == candidate, axis=1)):
            remaining = ~np.any(np.all(candidates[:, None, :] == chosen[None, :, :], axis=2), axis=1)
            if not remaining.any():
                raise AssertionError('Les références ne contiennent pas assez de RGB uniques pour 96 couleurs')
            candidate = candidates[np.flatnonzero(remaining)[int(np.argmax(nearest[remaining]))]]
        chosen = np.vstack((chosen, candidate))
    palette = chosen.astype(np.uint8)
    luminance = palette.astype(np.float32) @ np.array([.299, .587, .114], dtype=np.float32)
    palette = palette[np.argsort(luminance)]
    metadata = {
        'label': 'PMD natif D52P11A + eau extraite de T01P02A',
        'target_colors': PALETTE_COLORS,
        'actual_colors': int(len(palette)),
        'required_source_unique_rgb': int(len(required)),
        'all_source_colors_retained': True,
        'filler_colors_are_exact_reference_rgb': True,
        'source_files': [str(path.relative_to(ROOT)) for path in RED_FILES + [SKY_FILE]],
        'method': 'RGB sources exacts conservés; palette complétée par échantillonnage farthest-point, sans nouvelle couleur; sans tramage',
    }
    return palette_image(palette), palette, metadata


def quantize_layer(layer: np.ndarray, pal_img: Image.Image, palette: np.ndarray) -> np.ndarray:
    out = np.asarray(layer, dtype=np.uint8).copy()
    visible = out[..., 3] > 0
    if visible.any():
        q = Image.fromarray(out[..., :3], 'RGB').quantize(
            palette=pal_img, dither=Image.Dither.NONE)
        indices = np.asarray(q, dtype=np.uint8)
        out[..., :3][visible] = palette[indices[visible]]
    out[~visible] = 0
    return out


def resize_plane(plane: np.ndarray) -> np.ndarray:
    image = Image.fromarray(np.asarray(plane, dtype=np.float32), mode='F')
    return np.asarray(image.resize((SCALED_W, H), Image.Resampling.BOX))[:, CROP_X:CROP_X + W]


def rgba(colors: np.ndarray, mask: np.ndarray) -> np.ndarray:
    layer = np.zeros((H, W, 4), dtype=np.uint8)
    layer[..., :3] = np.asarray(colors, dtype=np.uint8)
    layer[..., 3] = np.where(mask, 255, 0).astype(np.uint8)
    layer[~mask] = 0
    return layer


def downsample_rgb(raw: np.ndarray) -> np.ndarray:
    channels = [resize_plane(raw[..., c].astype(np.float32)) for c in range(3)]
    return np.clip(np.rint(np.stack(channels, axis=-1)), 0, 255).astype(np.uint8)


def downsample_mask(mask: np.ndarray, threshold: float = 0.18) -> np.ndarray:
    return resize_plane(mask.astype(np.float32)) > threshold


def downsample_masked_color(raw_rgb: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    weight = resize_plane(mask.astype(np.float32))
    channels = [resize_plane(raw_rgb[..., c].astype(np.float32) * mask) for c in range(3)]
    colors = np.stack(channels, axis=-1) / np.maximum(weight, 1e-6)[..., None]
    colors = np.clip(np.rint(colors), 0, 255).astype(np.uint8)
    return colors, weight > 0.18


def nearest_palette_distance(colors: np.ndarray, palette: np.ndarray, limit: int = 24_000) -> dict:
    pixels = np.asarray(colors, dtype=np.uint8).reshape(-1, 3)
    if len(pixels) > limit:
        pixels = pixels[np.linspace(0, len(pixels) - 1, limit, dtype=np.int64)]
    values = []
    pal = palette.astype(np.int32)
    for start in range(0, len(pixels), 2048):
        block = pixels[start:start + 2048].astype(np.int32)
        delta = block[:, None, :] - pal[None, :, :]
        values.extend(np.sqrt(np.min(np.sum(delta * delta, axis=2), axis=1)).tolist())
    distances = np.asarray(values, dtype=np.float32)
    return {'sample_pixels': int(len(distances)),
            'mean_rgb_euclidean': round(float(distances.mean()), 3),
            'p95_rgb_euclidean': round(float(np.percentile(distances, 95)), 3),
            'max_rgb_euclidean': round(float(distances.max()), 3)}


def cell_grid(blocked_pixels: np.ndarray) -> np.ndarray:
    return blocked_pixels.reshape(H // TILE, TILE, W // TILE, TILE).mean((1, 3)) > 0.25


def walkable2x2(blocked: np.ndarray) -> np.ndarray:
    h, w = blocked.shape
    open_footprints = np.zeros_like(blocked, dtype=bool)
    for y in range(h - 1):
        for x in range(w - 1):
            open_footprints[y, x] = not blocked[y:y + 2, x:x + 2].any()
    return open_footprints


def choose_horizontal_markers(blocked: np.ndarray) -> tuple[tuple[int, int], tuple[int, int], int]:
    """Choose connected 16×16 entry/seuil cells on the native map's east-west corridor."""
    open_footprints = walkable2x2(blocked)
    h, w = blocked.shape
    starts = [(y, x) for y in range(h - 1) for x in range(3, 16) if open_footprints[y, x]]
    if not starts:
        raise AssertionError('Aucune case 16×16 libre à gauche du bassin')
    start = min(starts, key=lambda p: (abs(p[0] - 44) + 2 * abs(p[1] - 7), p[0], p[1]))
    seen = np.zeros_like(open_footprints, dtype=bool)
    seen[start] = True
    queue = deque([start])
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if (0 <= ny < h - 1 and 0 <= nx < w - 1 and
                    open_footprints[ny, nx] and not seen[ny, nx]):
                seen[ny, nx] = True
                queue.append((ny, nx))
    goals = [(y, x) for y in range(h - 1) for x in range(68, min(w - 1, 84)) if seen[y, x]]
    if not goals:
        raise AssertionError('Aucune case 16×16 reliée à droite du bassin')
    goal = min(goals, key=lambda p: (abs(p[0] - 44) + 2 * abs(p[1] - 73), p[0], p[1]))
    return start, goal, int(seen.sum())


def write_ora(path: Path, layers: list[tuple[str, np.ndarray]], name: str) -> None:
    root = ET.Element('image', w=str(W), h=str(H), name=name)
    stack = ET.SubElement(root, 'stack')
    merged = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('mimetype', 'image/openraster', compress_type=zipfile.ZIP_STORED)
        for i, (title, layer) in reversed(list(enumerate(layers))):
            filename = f'data/layer{i:02d}.png'
            ET.SubElement(stack, 'layer', name=title, src=filename, x='0', y='0', opacity='1.0',
                          visibility='visible', **{'composite-op': 'svg:src-over'})
            stream = io.BytesIO()
            Image.fromarray(layer).save(stream, format='PNG')
            archive.writestr(filename, stream.getvalue())
        for _, layer in layers:
            merged.alpha_composite(Image.fromarray(layer))
        stream = io.BytesIO()
        merged.save(stream, format='PNG')
        archive.writestr('mergedimage.png', stream.getvalue())
        thumbnail = merged.copy()
        thumbnail.thumbnail((256, 256))
        stream = io.BytesIO()
        thumbnail.save(stream, format='PNG')
        archive.writestr('Thumbnails/thumbnail.png', stream.getvalue())
        archive.writestr('stack.xml', ET.tostring(root, encoding='utf-8', xml_declaration=True))


def ground_project(stack: list[tuple[str, list[np.ndarray], int]], blocked: np.ndarray,
                   entry_px: list[int], threshold_px: list[int], manifest: dict) -> dict:
    gfx = loadmod('pmdo_codec_lgv1', ROOT / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools_lgv1', ROOT / 'source/pmdo_cote/INSTALLER.py')
    if STAGE.exists():
        shutil.rmtree(STAGE)
    with zipfile.ZipFile(ROOT / 'mod_metano_expeditions_pmdo_0812.zip') as archive:
        template = json.loads(archive.read(
            'metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground'))
    obj = template['Object']
    grid_w, grid_h = W // TILE, H // TILE
    layers, banks = [], []
    for i, (title, frames, ticks) in enumerate(stack):
        bank = gfx.TileBank(f'{PFX}_{i:02d}_{title.split()[0].upper()}')
        bank.ids[bytes(256)] = (0, 0)
        bank.data[(0, 0)] = bytes(256)

        def cell(x, y, frames=frames, bank=bank):
            refs = []
            for frame in frames:
                tile = Image.fromarray(frame[y*TILE:y*TILE+TILE, x*TILE:x*TILE+TILE])
                ref = bank.add(tile, x, y)
                refs.append(ref if ref else {'Sheet': bank.name, 'TexLoc': {'X': 0, 'Y': 0}})
            if all(ref['TexLoc'] == {'X': 0, 'Y': 0} for ref in refs):
                return []
            return [refs[0]] if all(ref == refs[0] for ref in refs) else refs

        layers.append(gfx.layer(f'{i:02d} {title}', grid_w, grid_h, cell, ticks))
        banks.append(bank)
    layers.append(gfx.layer(f'{len(layers):02d} Vos éléments avant-plan (Top)',
                            grid_w, grid_h, draw=4))
    for bank in banks:
        bank.write(STAGE / f'Content/Tile/{bank.name}.tile')
    obj.update(
        Name={'DefaultText': 'Lac de Verre - variante D52P11A', 'LocalTexts': {}},
        AssetName=ASSET, Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None,
        ViewOffset={'X': 0, 'Y': 0}, ActiveChar=None, Status={}, Layers=layers,
        Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
        Comment=('Variante légère du Ground natif PMD-SKY D52P11A. Base reconstruite depuis son '
                 '.rsground et son tileset; eau du bassin prélevée dans le rendu Red T01P02A. '
                 'Canvas adapté au 4:3 sans étirement; texture recompilée en banques LGV1. '
                 'Collisions issues du Ground source, ajustées par le masque du lac. '
                 'Aucun warp; entrée et seuil à raccorder.'))
    obj['obstacles'] = [[{'Bounds': {'X': x*TILE, 'Y': y*TILE, 'Width': TILE, 'Height': TILE},
                          'Tags': int(blocked[y, x])} for y in range(grid_h)] for x in range(grid_w)]
    marker = lambda name, pos: {'EntName': name, 'Direction': 4, 'EntEnabled': True, 'triggerType': 0,
                                'Collider': {'X': pos[0], 'Y': pos[1], 'Width': 16, 'Height': 16}}
    obj['Entities'] = [{'Name': 'Entrée et seuil à raccorder', 'Visible': True, 'MapChars': [],
                        'GroundObjects': [], 'Spawners': [],
                        'Markers': [marker('entrance', entry_px), marker('donjon_seuil', threshold_px)]}]
    obj['Decorations'] = [{'Name': 'Décorations à créer', 'Layer': 2, 'Visible': True, 'Anims': []}]
    template['Version'] = '0.8.12.0'
    gfx.save(STAGE / f'Data/Ground/{ASSET}.rsground',
             json.dumps(template, ensure_ascii=False, separators=(',', ':')).encode())
    gfx.save(STAGE / f'Data/Script/{NAMESPACE}/ground/{ASSET}/init.lua',
             f'-- {ASSET} : variante de D52P11A; aucun warp.\nlocal {ASSET} = {{}}\nreturn {ASSET}\n'.encode())
    nodes = {}
    for path in sorted((STAGE / 'Content/Tile').glob('*.tile')):
        with path.open('rb') as stream:
            nodes[path.stem] = tools.read_node(stream)
    (STAGE / 'Content/Tile/index.idx').write_bytes(tools.encode_index(nodes))
    ident = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/meromoonmeri/projet-pmdo/' + NAMESPACE)
    (STAGE / 'Mod.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Lac de Verre — variante PMD-SKY D52P11A (4:3)</Name>
  <Author>meromoonmeri</Author>
  <Description>Ground PMDO éditable : base Sky D52P11A conservée, petite zone de lac depuis Red T01P02A. Aucun décor généré; pixels non certifiés comme tuiles natives.</Description>
  <Namespace>{NAMESPACE}</Namespace>
  <UUID>{ident}</UUID>
  <Version>1.0.0.0</Version>
  <GameVersion>0.8.12.0</GameVersion>
  <ModType>Quest</ModType>
  <Relationships />
</Header>
''', encoding='utf-8')
    installer = (ROOT / 'source/pmdo_cote/INSTALLER.py').read_text(encoding='utf-8')
    needle = '            relative = src.relative_to(source)\n'
    if needle not in installer:
        raise RuntimeError('Point d’insertion index.idx introuvable dans INSTALLER.py')
    installer = installer.replace(needle, needle +
        "            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n")
    (STAGE / 'INSTALLER.py').write_text(installer, encoding='utf-8')
    (STAGE / 'README.md').write_text((HERE / 'README_PACK.md').read_text(encoding='utf-8'), encoding='utf-8')
    (STAGE / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'banks': [bank.name for bank in banks],
            'tiles_per_bank': {bank.name: len(bank.data) for bank in banks}}


def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    for directory in ['calques', 'animation/eau', 'masques', 'review']:
        path = OUT / directory
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    native_image, native_blocked, native_meta = render_native_d52()
    native_pixels = np.asarray(native_image.convert('RGB'), dtype=np.uint8)
    adapted = adapt_native_canvas(native_image)
    adapted_raw = to_raw(adapted, Image.Resampling.NEAREST).astype(np.uint8)
    if adapted_raw.shape != (SRC_H, SRC_W, 3):
        raise AssertionError(f'Brut D52 adapté inattendu : {adapted_raw.shape}')

    native_lake_mask = lake_mask_native()
    raw_lake_mask = to_raw(native_lake_mask, Image.Resampling.NEAREST).astype(np.uint8)
    if set(np.unique(raw_lake_mask)) - {0, 255}:
        raise AssertionError('Le masque haute résolution doit rester binaire')

    first_crop = np.asarray(Image.open(RED_FILES[0]).convert('RGB').crop(WATER_CROP), dtype=np.uint8)
    first = first_crop.astype(np.int16)
    r0, g0, b0 = first.transpose(2, 0, 1)
    water_geometry = (b0 > r0 + 10) & (b0 > g0 + 5) & (g0 > 35) & (b0 > 70)
    _, nearest_water = nd.distance_transform_edt(~water_geometry, return_indices=True)
    source_water, water_crop_meta = [], []
    for path in RED_FILES:
        patch, meta = water_crop_from_red(path, water_geometry, nearest_water)
        source_water.append(patch)
        water_crop_meta.append(meta)
    # The 64×32 source crop is enlarged uniformly by 1.5× to the 96×48 lake.
    lake_region_mask = Image.fromarray(native_lake_mask[LAKE_Y:LAKE_Y+LAKE_H,
                                                       LAKE_X:LAKE_X+LAKE_W])
    raw_water_frames = []
    for patch in source_water:
        water_patch = Image.fromarray(patch).resize((LAKE_W, LAKE_H), Image.Resampling.NEAREST)
        water_canvas = np.zeros((ADAPTED_H, ADAPTED_W, 4), dtype=np.uint8)
        water_canvas[LAKE_Y:LAKE_Y+LAKE_H, LAKE_X:LAKE_X+LAKE_W, :3] = np.asarray(water_patch)
        water_canvas[LAKE_Y:LAKE_Y+LAKE_H, LAKE_X:LAKE_X+LAKE_W, 3] = np.asarray(lake_region_mask)
        raw_water_frames.append(to_raw(water_canvas, Image.Resampling.NEAREST).astype(np.uint8))

    # Durable, full-resolution source plates; the first raw contains no key color.
    base_raw_path, composite_raw_path, mask_raw_path = RAW_FILES
    Image.fromarray(adapted_raw, 'RGB').save(base_raw_path)
    base_rgba_raw = Image.fromarray(adapted_raw, 'RGB').convert('RGBA')
    composite_raw = Image.alpha_composite(base_rgba_raw, Image.fromarray(raw_water_frames[0], 'RGBA'))
    composite_raw.convert('RGB').save(composite_raw_path)
    Image.fromarray(raw_lake_mask, 'L').save(mask_raw_path)

    palette_img, palette, palette_meta = shared_native_palette(native_pixels, source_water)
    base_down = downsample_rgb(adapted_raw)
    base_layer = quantize_layer(rgba(base_down, np.ones((H, W), dtype=bool)), palette_img, palette)
    water_layers, water_down_masks = [], []
    for raw_water in raw_water_frames:
        raw_mask = raw_water[..., 3] > 0
        colors, visible = downsample_masked_color(raw_water[..., :3], raw_mask)
        water_down_masks.append(visible)
        water_layers.append(quantize_layer(rgba(colors, visible), palette_img, palette))
    if any(not np.array_equal(water_down_masks[0], mask) for mask in water_down_masks[1:]):
        raise AssertionError('Le masque du lac varie entre les frames Red')
    water_mask_down = water_down_masks[0]

    # Preserve the native collision grid and add water as blocked terrain.
    adapted_blocked = np.pad(native_blocked, ((0, 0), (2, 3)), mode='reflect')
    native_blocked_down = np.asarray(Image.fromarray(adapted_blocked.astype(np.uint8) * 255)
                                     .resize((W // TILE, H // TILE), Image.Resampling.NEAREST)) > 0
    water_cells = cell_grid(water_mask_down)
    blocked = native_blocked_down | water_cells
    entry, threshold, explored = choose_horizontal_markers(blocked)
    entry_px = [entry[1] * TILE, entry[0] * TILE]
    threshold_px = [threshold[1] * TILE, threshold[0] * TILE]

    # Full-resolution source masks and output-resolution collision review.
    Image.fromarray(raw_lake_mask, 'L').save(OUT / 'masques/LGV1_masque_lac_1200x896.png')
    Image.fromarray(water_mask_down.astype(np.uint8) * 255, 'L').save(OUT / 'masques/LGV1_masque_lac_768x576.png')
    Image.fromarray(native_blocked_down.astype(np.uint8) * 255, 'L').save(OUT / 'masques/LGV1_masque_collisions_D52_768x576.png')
    Image.fromarray(blocked.astype(np.uint8) * 255, 'L').resize((W, H), Image.Resampling.NEAREST).save(
        OUT / 'masques/LGV1_masque_collisions_768x576.png')

    # One shared 96-color palette contains all original pixels used by base and lake.
    swatch = Image.new('RGB', (12 * 24, ((len(palette) + 11) // 12) * 28), (24, 32, 42))
    draw = ImageDraw.Draw(swatch)
    for i, color in enumerate(palette):
        x, y = (i % 12) * 24, (i // 12) * 28
        draw.rectangle((x, y, x + 22, y + 22), fill=tuple(map(int, color)))
        draw.text((x + 2, y + 22), str(i), fill=(255, 255, 255))
    swatch.save(OUT / 'review/LGV1_palette_96_sources.png')
    water_source_colors = np.unique(np.concatenate(source_water, axis=0).reshape(-1, 3), axis=0)
    palette_json = {
        'shared_palette_rgb': palette.tolist(),
        'shared_palette_meta': palette_meta,
        'water_source_rgb': water_source_colors.tolist(),
        'water_source': {
            'repo': 'meromoonmeri/PMD-RED-PMDO-PORT',
            'commit': '680fb85efacbde40473ef3f09dde2c0152e96f6c',
            'map': 'T01P02A (Whiscash Pond)',
            'crop_xyxy': list(WATER_CROP),
            'crop_px': [64, 32],
            'note': 'pixels prélevés des rendus publiés; ce n’est pas la banque .tile Red et le rendu n’est pas certifié natif',
        },
    }
    (OUT / 'palette_reference.json').write_text(
        json.dumps(palette_json, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    base_file = 'calques/LGV1_00_zone_D52P11A.png'
    Image.fromarray(base_layer).save(OUT / base_file)
    water_files = []
    for i, frame in enumerate(water_layers):
        filename = f'LGV1_01_eau_T01P02A_f{i:02d}.png'
        Image.fromarray(frame).save(OUT / 'animation/eau' / filename)
        water_files.append(f'animation/eau/{filename}')
    layer_manifest = [
        {'index': 0, 'name': 'zone_glace_D52P11A', 'file': base_file,
         'frames': 1, 'frame_length_ticks': 60,
         'origin': 'Ground natif D52P11A décodé puis adapté au 4:3 sans étirement'},
        {'index': 1, 'name': 'eau_lac_T01P02A', 'file': 'animation/eau/LGV1_01_eau_T01P02A_fXX.png',
         'frames': WATER_FRAMES, 'frame_length_ticks': WATER_TICKS,
         'origin': 'recadrage des six frames du rendu Red T01P02A; aucune animation procédurale'},
    ]
    base_fidelity = nearest_palette_distance(base_down.reshape(-1, 3), palette)
    water_fidelity = nearest_palette_distance(
        np.concatenate([f[f[..., 3] > 0, :3] for f in water_layers], axis=0), palette)
    water_distinct_frames = len({hashlib.sha256(frame.tobytes()).hexdigest() for frame in water_layers})

    scene_frames = []
    base_rgba = Image.fromarray(base_layer, 'RGBA')
    for frame in water_layers:
        scene = base_rgba.copy()
        scene.alpha_composite(Image.fromarray(frame, 'RGBA'))
        scene_frames.append(scene)
    scene_frames[0].save(OUT / 'review/LGV1_scene_t000.png')
    scene_frames[0].resize((W * 2, H * 2), Image.Resampling.NEAREST).save(
        OUT / 'review/LGV1_scene_x2.png')
    scene_frames[0].save(OUT / 'review/LGV1_scene_eau_source.webp', save_all=True,
                          append_images=scene_frames[1:],
                          duration=round(WATER_TICKS * 1000 / 60), loop=0, lossless=True)

    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(overlay)
    for y, x in zip(*np.nonzero(blocked)):
        dd.rectangle((x*TILE, y*TILE, x*TILE+TILE-1, y*TILE+TILE-1), fill=(236, 53, 61, 100))
    dd.rectangle((entry_px[0], entry_px[1], entry_px[0]+15, entry_px[1]+15),
                 outline=(60, 152, 255, 255), width=2)
    dd.rectangle((threshold_px[0], threshold_px[1], threshold_px[0]+15, threshold_px[1]+15),
                 outline=(255, 220, 60, 255), width=2)
    collision_review = scene_frames[0].copy()
    collision_review.alpha_composite(overlay)
    review_draw = ImageDraw.Draw(collision_review)
    review_draw.text((entry_px[0]+18, entry_px[1]), 'entrée', fill=(60, 152, 255, 255))
    review_draw.text((threshold_px[0]+18, threshold_px[1]), 'seuil', fill=(255, 220, 60, 255))
    collision_review.save(OUT / 'review/LGV1_collisions_marqueurs.png')
    write_ora(OUT / 'LGV1_lac_de_verre_calques.ora',
              [('zone_glace_D52P11A', base_layer), ('eau_lac_T01P02A', water_layers[0])],
              'Lac de Verre — base D52P11A + eau T01P02A')

    refs_meta = []
    for path in RED_FILES + [SKY_FILE]:
        refs_meta.append({'file': str(path.relative_to(ROOT)), 'sha256': sha(path),
                          'size_px': list(Image.open(path).size)})
    native_files = [NATIVE_GROUND, NATIVE_TILE]
    native_meta_files = [{'file': str(path.relative_to(ROOT)), 'sha256': sha(path),
                          'size_bytes': path.stat().st_size} for path in native_files]
    source_refs = [
        {'repo': 'meromoonmeri/PMD-RED-PMDO-PORT', 'branch': 'main',
         'commit': '680fb85efacbde40473ef3f09dde2c0152e96f6c',
         'map': 'T01P02A (Whiscash Pond)',
         'path': 'PMDRed_PMDO_Framework/output/Visual_Renders/T01P02A_Frame_0.png',
         'url': 'https://github.com/meromoonmeri/PMD-RED-PMDO-PORT/blob/680fb85efacbde40473ef3f09dde2c0152e96f6c/PMDRed_PMDO_Framework/output/Visual_Renders/T01P02A_Frame_0.png',
         'use': 'source de pixels pour le petit bassin; recadrage identique dans les frames 0–5; non présenté comme banque .tile'},
        {'repo': 'meromoonmeri/PMD-SKY-PMDO-PORT', 'branch': 'master',
         'commit': 'd62110a00269bdc861b8fe41b077607a80f50978',
         'map': 'D52P11A (Ground natif; code de preview, nom canonique non affirmé)',
         'path': 'output/Grounds/d52p11a.rsground',
         'tiles_path': 'output/Tiles/D52p11a_Base.tile',
         'preview_path': 'output/Previews/d52p11a.png',
         'ground_blob': 'b938d1668244302f02cac52989627b66e15b243a',
         'tiles_blob': '68a914a3281fa3cfef46b0347a5b9c3d9136e4da',
         'url': 'https://github.com/meromoonmeri/PMD-SKY-PMDO-PORT/tree/d62110a00269bdc861b8fe41b077607a80f50978/output',
         'use': 'base D52 décodée depuis le Ground et le tileset natifs; le rendu brut décode pixel-pour-pixel la preview locale'},
    ]
    raw_meta = [{'file': str(path.relative_to(ROOT)), 'sha256': sha(path),
                 'size_px': list(Image.open(path).size)} for path in RAW_FILES]
    manifest = {
        'lot': 'serie_sources_croisees_v1/lac_de_verre',
        'title': 'Lac de Verre', 'prefix': PFX,
        'format': '4:3 vaste', 'size_px': [W, H], 'grid_8px': [W // TILE, H // TILE],
        'method': ('recomposition légère de sources PMD canoniques; base du Ground Sky D52P11A '
                   'rendue depuis son .rsground et son .tile; pixels d’eau Red T01P02A recadrés '
                   'dans le bassin central; traitement et export Python; aucune image de décor générée'),
        'references': source_refs, 'reference_files': refs_meta,
        'native_source_files': native_meta_files,
        'native_decode': native_meta,
        'raw_inputs': raw_meta,
        'adaptation_4_3': {
            'native_ground_grid': native_meta['ground_grid'],
            'native_ground_px': [NATIVE_W, NATIVE_H],
            'horizontal_reflect_pad_cells_left_right': [PAD_LEFT // TILE, PAD_RIGHT // TILE],
            'adapted_grid': [ADAPTED_W // TILE, ADAPTED_H // TILE],
            'adapted_canvas_px': [ADAPTED_W, ADAPTED_H],
            'raw_scale_uniforme': SRC_W / ADAPTED_W,
            'raw_intermediate_px': [SRC_W, 900],
            'raw_crop_top_bottom_px': [2, 2],
            'raw_px': [SRC_W, SRC_H],
            'method': 'extension par réflexion aux bords horizontaux, sans étirement; agrandissement NEAREST pour composer à 1200×900 puis retrait de 2 px en haut et en bas',
        },
        'normalization': {
            'source_px': [SRC_W, SRC_H], 'scale_uniforme': SCALE,
            'scaled_px': [SCALED_W, H], 'crop_x_left_right': [CROP_X, CROP_RIGHT],
            'output_px': [W, H],
            'method': 'BOX, facteur uniforme 576/896, recadrage centré vers 768×576; calque d’eau et masque traités séparément',
        },
        'segmentation': {
            'decor_sol': 'Ground D52P11A conservé comme calque plein cadre; aucun key magenta',
            'water': 'ellipse centrale dessinée comme masque binaire Python; eau hors masque transparente',
            'water_crop': {'xyxy': list(WATER_CROP), 'source_px': [64, 32],
                           'lake_box_native_px': [LAKE_X, LAKE_Y, LAKE_W, LAKE_H]},
            'exterior': 'aucun extérieur transparent: le Ground source couvre tout le canvas',
        },
        'palette': {
            'shared_colors': int(len(palette)), 'target_colors': PALETTE_COLORS,
            'sampling': palette_meta,
            'source_rgb_distance': {'base_D52P11A': base_fidelity, 'eau_T01P02A': water_fidelity},
            'water_source_unique_rgb': water_source_colors.tolist(),
            'dither': False,
        },
        'water': {
            'frames': WATER_FRAMES, 'distinct_frames_after_export': water_distinct_frames,
            'frame_length_ticks': WATER_TICKS,
            'frame_ms': round(WATER_TICKS * 1000 / 60, 2),
            'loop_seconds': WATER_FRAMES * WATER_TICKS / 60,
            'animation': 'recadrage des frames Red T01P02A 0–5; cycle source conservé, aucune onde procédurale',
            'source_frames': water_crop_meta,
        },
        'layers_bottom_to_top': layer_manifest,
        'layer_limits': ('Base visuelle décodée d’un Ground Sky réel et frames Red issues de rendus publiés; '
                         'mise à l’échelle et extraction du bassin modifient les pixels. Les nouvelles banques '
                         'LGV1 ne sont pas les banques Sky/Red originales et la texture n’est pas certifiée native.'),
        'access': {
            'entry_px': entry_px, 'threshold_px': threshold_px,
            'entry_grid_yx': list(entry), 'threshold_grid_yx': list(threshold),
            'path_found_16x16': True, 'reachable_16x16_cells': explored,
            'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size),
            'rule': 'collisions natives D52P11A rééchantillonnées; eau du lac bloquante (>25 % d’une case); empreinte personnage 16×16 px; corridor est-ouest',
        },
        'pmdo': {'target': '0.8.12', 'serialization': '0.8.12.0', 'asset': ASSET,
                 'namespace': NAMESPACE, 'tex_size': 1, 'tile_px': TILE, 'banks': [],
                 'runtime_tested': False, 'warp': 'aucun; markers entrance/donjon_seuil à raccorder'},
        'art_approved': False, 'native_texture_certified': False, 'runtime_tested': False,
    }
    pmdo_meta = ground_project([
        ('zone_D52P11A', [base_layer], 60),
        ('eau_T01P02A', water_layers, WATER_TICKS),
    ], blocked, entry_px, threshold_px, manifest)
    manifest['pmdo']['banks'] = pmdo_meta['banks']
    manifest['pmdo']['tiles_per_bank'] = pmdo_meta['tiles_per_bank']
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    shutil.copyfile(OUT / 'palette_reference.json', STAGE / 'palette_reference.json')
    print(json.dumps({
        'scene': str((OUT / 'review/LGV1_scene_t000.png').relative_to(ROOT)),
        'entry_px': entry_px, 'threshold_px': threshold_px,
        'route_found': manifest['access']['path_found_16x16'],
        'blocked_cells': int(blocked.sum()), 'palette_colors': len(palette),
        'water_frames': WATER_FRAMES, 'water_crop': WATER_CROP,
        'banks': pmdo_meta['banks'], 'tiles': pmdo_meta['tiles_per_bank'],
    }, ensure_ascii=False, indent=2))
    return manifest


if __name__ == '__main__':
    build()
