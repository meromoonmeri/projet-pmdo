#!/usr/bin/env python3
"""LGV1 — Lac de Verre, carte pilote de la série PMD Red × Sky.

Méthode 4:3 « échantillonnage-génération » : deux références PMDO distinctes
(T01P02A Red + D52P11A Sky) guident le générateur; les bruts décor/sol sont
sur magenta; Python segmente à 1200×896, réduit chaque classe séparément avec
le facteur uniforme 576/896, puis recadre au centre en 768×576 (96×72 cases).
Les couleurs sont quantifiées dans une palette échantillonnée des références.
Les pixels rendus sont générés, pas des tuiles natives certifiées.

Lancer : .venv/bin/python source/serie_sources_croisees_v1/lac_de_verre/build.py
"""
from __future__ import annotations

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
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / 'bruts'
REFS = HERE / 'references'
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
WATER_FRAMES, WATER_TICKS = 4, 10
PALETTE_COLORS = 96
RED_FILES = [REFS / f'red_T01P02A_frame{i}.png' for i in range(6)]
SKY_FILE = REFS / 'sky_D52P11A.png'
RAW_FILES = [RAW / 'decor_magenta.png', RAW / 'sol_complet.png']


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


def magenta_mask(a: np.ndarray) -> np.ndarray:
    """Repère le key #FF00FF et ses franges antialiasées générées.

    Les deux bruts ont un magenta légèrement bruité (médiane ≈253,0,253),
    d'où le seuil chromatique mesuré plutôt qu'une égalité RGB stricte.
    """
    p = a.astype(np.int16)
    r, g, b = p.transpose(2, 0, 1)
    return ((r >= 150) & (b >= 150) & (g <= 130) &
            (np.abs(r - b) <= 100) & (r - g >= 55) & (b - g >= 55))


def key_regions(a: np.ndarray, min_water_area: int = 120) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (key, exterior-connected key, interior water-key components)."""
    key = magenta_mask(a)
    labels, n = nd.label(key)
    edge_ids = np.unique(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
    edge_ids = edge_ids[edge_ids != 0]
    exterior = np.isin(labels, edge_ids) & (labels != 0)
    water = np.zeros_like(key)
    for i in range(1, n + 1):
        if i not in edge_ids and int(np.count_nonzero(labels == i)) >= min_water_area:
            water |= labels == i
    water = nd.binary_fill_holes(water)
    return key, exterior, water


def resize_plane(p: np.ndarray) -> np.ndarray:
    """Uniform 4:3 reduction, then the standard centered 3 px crop to 768."""
    im = Image.fromarray(np.asarray(p, dtype=np.float32), mode='F')
    return np.asarray(im.resize((SCALED_W, H), Image.Resampling.BOX))[:, CROP_X:CROP_X + W]


def down_class(a: np.ndarray, masks: dict[str, np.ndarray], order: list[str]) -> tuple[dict, dict]:
    """Resample class coverage and class colors separately; never blend key pixels."""
    weights = {k: resize_plane(masks[k].astype(np.float32)) for k in order}
    stack = np.stack([weights[k] for k in order])
    win = stack.argmax(0)
    has = stack.max(0) > 0.05
    exclusive = {k: (win == i) & has for i, k in enumerate(order)}
    colors = {}
    af = a.astype(np.float32)
    for k in order:
        w = weights[k]
        m = masks[k].astype(np.float32)
        channels = [resize_plane(af[..., c] * m) for c in range(3)]
        c = np.stack(channels, -1) / np.maximum(w, 1e-6)[..., None]
        colors[k] = np.clip(np.round(c), 0, 255).astype(np.uint8)
    return exclusive, colors


def down_mask(mask: np.ndarray, threshold: float = 0.05) -> np.ndarray:
    return resize_plane(mask.astype(np.float32)) > threshold


def rgba(colors: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros((H, W, 4), dtype=np.uint8)
    out[..., :3] = colors
    out[..., 3] = np.where(mask, 255, 0).astype(np.uint8)
    out[~mask] = 0
    return out


def palette_image(palette: np.ndarray) -> Image.Image:
    pal_img = Image.new('P', (1, 1))
    padded = np.zeros((256, 3), dtype=np.uint8)
    padded[:len(palette)] = palette
    pal_img.putpalette(padded.reshape(-1).tolist())
    return pal_img


def sample_pixels(path: Path, limit: int = 100_000) -> np.ndarray:
    pixels = rgb(path).reshape(-1, 3)
    count = min(limit, len(pixels))
    return pixels[np.linspace(0, len(pixels) - 1, count, dtype=np.int64)]


def palette_from_samples(samples: np.ndarray, requested: int, label: str) -> tuple[Image.Image, np.ndarray, dict]:
    """Median-cut sampled colors, snapped to real pixels in the reference sample."""
    samples = np.asarray(samples, dtype=np.uint8).reshape(-1, 3)
    width = 1024
    height = (len(samples) + width - 1) // width
    padded = np.zeros((height * width, 3), dtype=np.uint8)
    padded[:len(samples)] = samples
    source = Image.fromarray(padded.reshape(height, width, 3), 'RGB')
    q = source.quantize(colors=requested, method=Image.Quantize.MEDIANCUT,
                        dither=Image.Dither.NONE)
    centers = np.asarray(q.getpalette()[:requested * 3], dtype=np.uint8).reshape(-1, 3)
    used = np.unique(np.asarray(q).ravel())
    centers = centers[used].astype(np.int32)
    candidates = np.unique(samples, axis=0).astype(np.int32)
    chosen = []
    for center in centers:
        d = ((candidates - center) ** 2).sum(1)
        chosen.append(candidates[int(np.argmin(d))])
    colors = np.unique(np.asarray(chosen, dtype=np.uint8), axis=0)
    # Median-cut can leave duplicate/unused slots; fill to the requested size with
    # the most palette-distant real source colors, still never inventing RGB values.
    while len(colors) < min(requested, len(candidates)):
        delta = candidates[:, None, :] - colors[None, :, :].astype(np.int32)
        nearest = np.min(np.sum(delta * delta, axis=2), axis=1)
        candidate = candidates[int(np.argmax(nearest))]
        colors = np.unique(np.vstack((colors, candidate.astype(np.uint8))), axis=0)
    lum = colors.astype(np.float32) @ np.array([.299, .587, .114], dtype=np.float32)
    colors = colors[np.argsort(lum)]
    meta = {'label': label, 'requested_colors': requested, 'actual_colors': int(len(colors)),
            'source_pixels': int(len(samples)), 'source_unique_rgb': int(len(candidates)),
            'source_sha256': hashlib.sha256(samples.tobytes()).hexdigest(),
            'method': 'Pillow median-cut; centers snapped to actual sampled reference RGB; no dither'}
    return palette_image(colors), colors, meta


def make_palette() -> tuple[Image.Image, np.ndarray, dict]:
    """Build the shared 96-color Red+Sky palette with equal source weight."""
    red = sample_pixels(RED_FILES[0])
    sky = sample_pixels(SKY_FILE)
    samples = np.concatenate((red, sky), axis=0)
    pal_img, palette, meta = palette_from_samples(samples, PALETTE_COLORS, 'shared_red_sky')
    meta['sample_counts'] = {'red_T01P02A': int(len(red)), 'sky_D52P11A': int(len(sky))}
    return pal_img, palette, meta


def make_crystal_palette() -> tuple[Image.Image, np.ndarray, dict]:
    """Material-specific crystal palette: exact blue/cyan RGBs from the Red pond."""
    frames = []
    for path in RED_FILES:
        red = rgb(path).astype(np.int16)
        r, g, b = red.transpose(2, 0, 1)
        cyan_mask = (b > r + 10) & (b > g + 5) & (g > 35) & (b > 70)
        frames.append(red[cyan_mask].astype(np.uint8))
    samples = np.concatenate(frames, axis=0)
    colors = np.unique(samples, axis=0)
    lum = colors.astype(np.float32) @ np.array([.299, .587, .114], dtype=np.float32)
    colors = colors[np.argsort(lum)]
    meta = {'label': 'cristaux_red_cyan', 'requested_colors': int(len(colors)),
            'actual_colors': int(len(colors)), 'source_pixels': int(len(samples)),
            'source_unique_rgb': int(len(colors)), 'source_sha256': hashlib.sha256(samples.tobytes()).hexdigest(),
            'method': 'RGB exacts uniques bleus/cyans des six frames Red T01P02A, triés par luminance',
            'sample_counts': {'red_T01P02A_frames_0_to_5': int(len(samples))}}
    return palette_image(colors), colors, meta


def quantize_layer(layer: np.ndarray, palette_img: Image.Image, palette: np.ndarray) -> np.ndarray:
    out = layer.copy()
    mask = out[..., 3] > 0
    if mask.any():
        q = Image.fromarray(out[..., :3], 'RGB').quantize(palette=palette_img,
                                                          dither=Image.Dither.NONE)
        indices = np.asarray(q, dtype=np.uint8)
        out[..., :3][mask] = palette[indices[mask]]
    out[~mask] = 0
    return out


def quantize_rgb_to_colors(source_colors: np.ndarray, count: int = 10) -> np.ndarray:
    """Build a compact ramp from exact source colors, sorted dark to light."""
    source_colors = np.asarray(source_colors, dtype=np.uint8).reshape(-1, 3)
    candidates = np.unique(source_colors, axis=0).astype(np.int32)
    width = 1024
    height = (len(source_colors) + width - 1) // width
    padded = np.zeros((height * width, 3), dtype=np.uint8)
    padded[:len(source_colors)] = source_colors
    image = Image.fromarray(padded.reshape(height, width, 3), 'RGB')
    q = image.quantize(colors=count, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    centers = np.asarray(q.getpalette()[:count * 3], dtype=np.uint8).reshape(-1, 3)
    centers = centers[np.unique(np.asarray(q).ravel())].astype(np.int32)
    snapped = []
    for center in centers:
        d = ((candidates - center) ** 2).sum(1)
        snapped.append(candidates[int(np.argmin(d))])
    ramp = np.unique(np.asarray(snapped, dtype=np.uint8), axis=0)
    while len(ramp) < min(count, len(candidates)):
        delta = candidates[:, None, :] - ramp[None, :, :].astype(np.int32)
        nearest = np.min(np.sum(delta * delta, axis=2), axis=1)
        ramp = np.unique(np.vstack((ramp, candidates[int(np.argmax(nearest))].astype(np.uint8))), axis=0)
    lum = ramp.astype(np.float32) @ np.array([.299, .587, .114], dtype=np.float32)
    return ramp[np.argsort(lum)]


def sampled_water_palette() -> np.ndarray:
    """Sample blue/cyan RGB values directly from the six Red pond render frames."""
    chunks = []
    for path in RED_FILES:
        a = rgb(path).astype(np.int16)
        r, g, b = a.transpose(2, 0, 1)
        blue = (b > r + 10) & (b > g + 5) & (g > 35) & (b > 70)
        chunks.append(a[blue].astype(np.uint8))
    source = np.concatenate(chunks, axis=0)
    if len(source) < 100:
        raise AssertionError('Échantillon d’eau insuffisant dans T01P02A')
    return quantize_rgb_to_colors(source, count=10)


def nearest_palette_distance(colors: np.ndarray, palette: np.ndarray, limit: int = 24_000) -> dict:
    pix = np.asarray(colors, dtype=np.uint8).reshape(-1, 3)
    if len(pix) > limit:
        pix = pix[np.linspace(0, len(pix) - 1, limit, dtype=np.int64)]
    dists = []
    pal = palette.astype(np.int32)
    for start in range(0, len(pix), 2048):
        block = pix[start:start + 2048].astype(np.int32)
        delta = block[:, None, :] - pal[None, :, :]
        dists.extend(np.sqrt(np.min(np.sum(delta * delta, axis=2), axis=1)).tolist())
    vals = np.asarray(dists, dtype=np.float32)
    return {'sample_pixels': int(len(vals)), 'mean_rgb_euclidean': round(float(vals.mean()), 3),
            'p95_rgb_euclidean': round(float(np.percentile(vals, 95)), 3),
            'max_rgb_euclidean': round(float(vals.max()), 3)}


def water_frames(mask: np.ndarray, palette: np.ndarray) -> tuple[list[np.ndarray], np.ndarray]:
    if len(palette) < 2:
        raise ValueError('Palette d’eau trop courte')
    distance = nd.distance_transform_edt(mask)
    yy, xx = np.mgrid[:H, :W]
    rng = np.random.default_rng(52011)
    noise = nd.gaussian_filter(rng.random((H, W)), sigma=13)
    noise = (noise - noise.min()) / max(float(np.ptp(noise)), 1e-6) - .5
    phase_index = np.zeros((H, W), dtype=np.uint8)
    frames = []
    ramp = palette.astype(np.uint8)
    for t in range(WATER_FRAMES):
        phase = 2 * np.pi * t / WATER_FRAMES
        # Long, slightly warped surface ripples; the phase shift is periodic and
        # does not create concentric topographic bands around the basin.
        flow_x = xx + 10 * np.sin(yy * .035) + 4 * np.sin(xx * .021 + yy * .019)
        wave = (np.sin(flow_x * .075 - phase) +
                .52 * np.sin(xx * .027 - yy * .038 + phase * .75) +
                .28 * noise)
        level = np.clip(np.rint((wave + 1.8) / 3.6 * (len(ramp) - 1)), 0, len(ramp) - 1).astype(np.int16)
        # A restrained darker rim sampled from the same source ramp.
        level[distance <= 2.0] = np.minimum(level[distance <= 2.0], 1)
        level[distance <= 1.0] = 0
        frame = np.zeros((H, W, 4), dtype=np.uint8)
        frame[..., :3] = ramp[level]
        frame[..., 3] = np.where(mask, 255, 0).astype(np.uint8)
        frame[~mask] = 0
        if t == 0:
            phase_index = level.astype(np.uint8)
        frames.append(frame)
    return frames, phase_index


def cell_grid(blocked_pixels: np.ndarray) -> np.ndarray:
    return blocked_pixels.reshape(H // TILE, TILE, W // TILE, TILE).mean((1, 3)) > .25


def walkable2x2(blocked: np.ndarray) -> np.ndarray:
    gh, gw = blocked.shape
    ok = np.zeros_like(blocked)
    for y in range(gh - 1):
        for x in range(gw - 1):
            ok[y, x] = not blocked[y:y + 2, x:x + 2].any()
    return ok


def reachable(blocked: np.ndarray, start: tuple[int, int], goal: tuple[int, int]) -> tuple[bool, int, np.ndarray]:
    from collections import deque
    ok = walkable2x2(blocked)
    seen = np.zeros_like(ok)
    q = deque([start])
    seen[start] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if (ny, nx) == goal:
                seen[ny, nx] = True
                return True, int(seen.sum()), seen
            if 0 <= ny < ok.shape[0] and 0 <= nx < ok.shape[1] and ok[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    return start == goal, int(seen.sum()), seen


def choose_markers(blocked: np.ndarray) -> tuple[tuple[int, int], tuple[int, int], int]:
    """Choose a 16×16 arrival at the south and a reachable goal near the north arch."""
    ok = walkable2x2(blocked)
    gh, gw = blocked.shape
    cy = gw // 2
    starts = [(y, x) for y in range(max(0, gh - 8), gh - 1) for x in range(max(0, cy - 10), min(gw - 1, cy + 11)) if ok[y, x]]
    if not starts:
        raise AssertionError('aucune case 16×16 libre à l’arrivée sud')
    start = min(starts, key=lambda p: (abs(p[0] - (gh - 3)) + 2 * abs(p[1] - (cy - 1)), -p[0]))
    # One BFS; choose the nearest reachable free cell in the north-center target zone.
    from collections import deque
    seen = np.zeros_like(ok)
    q = deque([start]); seen[start] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < gh - 1 and 0 <= nx < gw - 1 and ok[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    goals = [(y, x) for y in range(0, min(gh - 1, 20)) for x in range(max(0, cy - 12), min(gw - 1, cy + 13)) if seen[y, x]]
    if not goals:
        # Allow an upper approach up to one third map height, still prefer the arch center.
        goals = [(y, x) for y in range(0, gh // 3) for x in range(gw - 1) if seen[y, x]]
    if not goals:
        raise AssertionError('aucune case 16×16 reliée dans le tiers nord')
    goal = min(goals, key=lambda p: (abs(p[0] - 7) + 2 * abs(p[1] - (cy - 1)), p[0]))
    return start, goal, int(seen.sum())


def write_ora(path: Path, layers: list[tuple[str, np.ndarray]], name: str) -> None:
    root = ET.Element('image', w=str(W), h=str(H), name=name)
    stack = ET.SubElement(root, 'stack')
    comp = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype', 'image/openraster', compress_type=zipfile.ZIP_STORED)
        for i, (title, layer) in reversed(list(enumerate(layers))):
            filename = f'data/layer{i:02d}.png'
            ET.SubElement(stack, 'layer', name=title, src=filename, x='0', y='0', opacity='1.0',
                          visibility='visible', **{'composite-op': 'svg:src-over'})
            buff = io.BytesIO(); Image.fromarray(layer).save(buff, format='PNG')
            z.writestr(filename, buff.getvalue())
        for _, layer in layers:
            comp.alpha_composite(Image.fromarray(layer))
        buff = io.BytesIO(); comp.save(buff, format='PNG'); z.writestr('mergedimage.png', buff.getvalue())
        thumb = comp.copy(); thumb.thumbnail((256, 256))
        buff = io.BytesIO(); thumb.save(buff, format='PNG'); z.writestr('Thumbnails/thumbnail.png', buff.getvalue())
        z.writestr('stack.xml', ET.tostring(root, encoding='utf-8', xml_declaration=True))


def ground_project(stack: list[tuple[str, list[np.ndarray], int]], blocked: np.ndarray,
                   entry_px: list[int], threshold_px: list[int], manifest: dict) -> dict:
    gfx = loadmod('pmdo_codec_lgv1', ROOT / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools_lgv1', ROOT / 'source/pmdo_cote/INSTALLER.py')
    if STAGE.exists():
        shutil.rmtree(STAGE)
    with zipfile.ZipFile(ROOT / 'mod_metano_expeditions_pmdo_0812.zip') as z:
        template = json.loads(z.read('metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground'))
    obj = template['Object']
    gw, gh = W // TILE, H // TILE
    layers, banks = [], []
    for i, (title, frames, ticks) in enumerate(stack):
        bank = gfx.TileBank(f'{PFX}_{i:02d}_{title.split()[0].upper()}')
        bank.ids[bytes(256)] = (0, 0)
        bank.data[(0, 0)] = bytes(256)

        def cell(x, y, frames=frames, bank=bank):
            refs = []
            for fr in frames:
                tile = Image.fromarray(fr[y*TILE:y*TILE+TILE, x*TILE:x*TILE+TILE])
                ref = bank.add(tile, x, y)
                refs.append(ref if ref else {'Sheet': bank.name, 'TexLoc': {'X': 0, 'Y': 0}})
            if all(r['TexLoc'] == {'X': 0, 'Y': 0} for r in refs):
                return []
            return [refs[0]] if all(r == refs[0] for r in refs) else refs

        layers.append(gfx.layer(f'{i:02d} {title}', gw, gh, cell, ticks))
        banks.append(bank)
    layers.append(gfx.layer(f'{len(layers):02d} Vos éléments avant-plan (Top)', gw, gh, draw=4))
    for bank in banks:
        bank.write(STAGE / f'Content/Tile/{bank.name}.tile')
    obj.update(Name={'DefaultText': 'Lac de Verre - entrée sud / arche nord', 'LocalTexts': {}},
               AssetName=ASSET, Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None,
               ViewOffset={'X': 0, 'Y': 0}, ActiveChar=None, Status={}, Layers=layers,
               Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
               Comment=('PMDO 0.8.12. Composition générée et référencée sur T01P02A (Red PMDO) + D52P11A (Sky PMDO). '
                        'Terrain non natif certifié. Eau 4×10 ticks à palette échantillonnée. Collisions estimatives; '
                        'aucun warp; passage sud-nord à vérifier en jeu.'))
    obj['obstacles'] = [[{'Bounds': {'X': x*TILE, 'Y': y*TILE, 'Width': TILE, 'Height': TILE},
                          'Tags': int(blocked[y, x])} for y in range(gh)] for x in range(gw)]
    marker = lambda name, pos: {'EntName': name, 'Direction': 4, 'EntEnabled': True, 'triggerType': 0,
                                'Collider': {'X': pos[0], 'Y': pos[1], 'Width': 16, 'Height': 16}}
    obj['Entities'] = [{'Name': 'Entrées et acteurs à placer', 'Visible': True, 'MapChars': [],
                        'GroundObjects': [], 'Spawners': [],
                        'Markers': [marker('entrance', entry_px), marker('donjon_seuil', threshold_px)]}]
    obj['Decorations'] = [{'Name': 'Décorations à créer', 'Layer': 2, 'Visible': True, 'Anims': []}]
    template['Version'] = '0.8.12.0'
    gfx.save(STAGE / f'Data/Ground/{ASSET}.rsground',
             json.dumps(template, ensure_ascii=False, separators=(',', ':')).encode())
    gfx.save(STAGE / f'Data/Script/{NAMESPACE}/ground/{ASSET}/init.lua',
             f'-- {ASSET} : base d’édition; aucun warp.\nlocal {ASSET} = {{}}\nreturn {ASSET}\n'.encode())
    nodes = {}
    for path in sorted((STAGE / 'Content/Tile').glob('*.tile')):
        with path.open('rb') as f:
            nodes[path.stem] = tools.read_node(f)
    (STAGE / 'Content/Tile/index.idx').write_bytes(tools.encode_index(nodes))
    ident = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/meromoonmeri/projet-pmdo/' + NAMESPACE)
    (STAGE / 'Mod.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Lac de Verre — série PMD Red × Sky (4:3)</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d’édition PMDO : carte générée et référencée, calques magenta, lac animé. Pas une aventure jouable.</Description>
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
    return {'banks': [b.name for b in banks], 'tiles_per_bank': {b.name: len(b.data) for b in banks}}


def build() -> dict:
    for directory in ['calques', 'animation/eau', 'masques', 'review']:
        path = OUT / directory
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
    decor = rgb(RAW_FILES[0]).astype(np.int16)
    floor_raw = rgb(RAW_FILES[1]).astype(np.int16)
    if decor.shape != (SRC_H, SRC_W, 3) or floor_raw.shape != decor.shape:
        raise AssertionError(f'Bruts attendus en 4:3 {SRC_W}×{SRC_H}; décor={decor.shape}, sol={floor_raw.shape}')

    # The decor plate owns map bounds and water silhouettes. Exterior key regions
    # touch the image border; internal magenta components are water pools/lake.
    _, exterior, water_full = key_regions(decor)
    map_footprint = ~exterior
    floor_full_mask = map_footprint & ~water_full

    # The separately generated floor plate is not pixel-identical. Use it as the
    # material source, then fill any alignment/key holes from the nearest valid
    # floor pixel while keeping the decor plate's exact 4:3 map silhouette.
    _, floor_exterior, floor_water = key_regions(floor_raw)
    floor_source_valid = ~magenta_mask(floor_raw) & ~floor_exterior & ~floor_water
    if not floor_source_valid.any():
        raise AssertionError('sol_complet sans zone de sol échantillonnable')
    _, nearest = nd.distance_transform_edt(~floor_source_valid, return_indices=True)
    floor_filled = floor_raw[nearest[0], nearest[1]]
    floor_filled = np.clip(floor_filled, 0, 255).astype(np.uint8)

    y, x = np.mgrid[:SRC_H, :SRC_W]
    fr, fg, fb = floor_filled.transpose(2, 0, 1).astype(np.int16)
    floor_luma = .299 * fr + .587 * fg + .114 * fb
    # The bright, pebble-marked band is separated from the more even frozen base.
    path_full = floor_full_mask & (floor_luma > 205)
    base_full = floor_full_mask & ~path_full

    # Segment generated decor by measured luminance/chroma and the lake/outer
    # cliff boundaries. Thresholds are intentionally explicit and editable.
    dr, dg, db = decor.transpose(2, 0, 1).astype(np.int16)
    luma = .299 * dr + .587 * dg + .114 * db
    saturation = decor.max(2).astype(np.int16) - decor.min(2).astype(np.int16)
    decor_key, decor_exterior, decor_water = key_regions(decor)
    decor_solid = ~decor_key & ~decor_exterior
    distance_to_water = nd.distance_transform_edt(~decor_water)
    distance_to_exterior = nd.distance_transform_edt(~decor_exterior)
    edge_band = (distance_to_water < 28) | (distance_to_exterior < 28)

    # The arch occupies the centered north approach; keep the dark doorway with it.
    arch_roi = (x >= 505) & (x <= 690) & (y <= 142)
    arch = decor_solid & arch_roi & ((luma < 203) | (saturation > 68))
    cyan_bright = (db > dr + 28) & (dg > dr + 13) & (luma >= 182) & (saturation >= 58)
    crystals = decor_solid & cyan_bright & ~arch
    wall_dark = (luma < 148) & (saturation > 24)
    wall_cold_edge = edge_band & (saturation > 64) & (luma < 205)
    walls = decor_solid & (wall_dark | wall_cold_edge) & ~crystals & ~arch
    # Avoid classifying isolated antialias dust as an obstacle/decor layer.
    walls = nd.binary_closing(walls, iterations=1) & decor_solid
    crystals = nd.binary_closing(crystals, iterations=1) & decor_solid & ~arch & ~walls
    arch = nd.binary_closing(arch, iterations=1) & decor_solid
    crystals &= ~arch
    walls &= ~arch & ~crystals

    classes = {
        'base_sol': base_full,
        'chemin_givre': path_full,
        'parois_givrees': walls,
        'cristaux': crystals,
        'arche_nord': arch,
    }
    class_order = list(classes)
    # Separate source material buffers for the floor and decor classes.
    floor_classes = {'base_sol': base_full, 'chemin_givre': path_full}
    floor_ex, floor_colors = down_class(floor_filled, floor_classes, list(floor_classes))
    decor_classes = {'parois_givrees': walls, 'cristaux': crystals, 'arche_nord': arch}
    decor_ex, decor_colors = down_class(decor.astype(np.uint8), decor_classes, list(decor_classes))
    ex = {**floor_ex, **decor_ex}
    color_by_class = {**floor_colors, **decor_colors}

    # Shared Red+Sky palette for most materials; ice crystals get the documented
    # material-specific palette (Sky cold pixels + Red pond cyan samples).
    palette_image, palette, palette_meta = make_palette()
    crystal_palette_image, crystal_palette, crystal_palette_meta = make_crystal_palette()
    raw_layers = {k: rgba(color_by_class[k], ex[k]) for k in class_order}
    static_layers = {}
    for key, layer in raw_layers.items():
        if key == 'cristaux':
            static_layers[key] = quantize_layer(layer, crystal_palette_image, crystal_palette)
        else:
            static_layers[key] = quantize_layer(layer, palette_image, palette)
    water_palette = sampled_water_palette()

    water_full_mask = water_full
    water_down = down_mask(water_full_mask, threshold=0.18)
    water, water_index = water_frames(water_down, water_palette)

    # Measure palette fit before quantization, primarily on generated ground.
    fidelity = {}
    for key in class_order:
        m = classes[key]
        source_img = floor_filled if key in floor_classes else decor.astype(np.uint8)
        raw_material = source_img[m]
        material_palette = crystal_palette if key == 'cristaux' else palette
        fidelity[key] = nearest_palette_distance(raw_material, material_palette)

    # Collision mask: no water/exterior, low ice cliffs, bright crystal blocks,
    # or cave arch; ordinary path/base floor remains walkable.
    object_blocked = walls | crystals | arch
    walk_full = floor_full_mask & ~water_full & ~object_blocked
    blocked = cell_grid(~down_mask(walk_full, threshold=0.25))
    entry, threshold, explored = choose_markers(blocked)
    path_ok, explored_bfs, seen = reachable(blocked, entry, threshold)
    if not path_ok:
        raise AssertionError('chemin 16×16 sud → seuil nord introuvable')
    entry_px = [entry[1] * TILE, entry[0] * TILE]
    threshold_px = [threshold[1] * TILE, threshold[0] * TILE]

    # Masks, layers, animation and review renders.
    magenta_out = np.zeros((SRC_H, SRC_W), dtype=np.uint8)
    magenta_out[magenta_mask(decor)] = 255
    Image.fromarray(magenta_out).save(OUT / 'masques/LGV1_magenta_brut.png')
    for name, mask in [('exterieur', exterior), ('eau', water_full), ('sol', floor_full_mask),
                       ('chemin', path_full), ('murs', walls), ('cristaux', crystals),
                       ('arche', arch), ('sol_praticable', walk_full)]:
        Image.fromarray((mask.astype(np.uint8) * 255)).save(OUT / 'masques' / f'LGV1_masque_{name}_1200x896.png')
    for name, mask in [('eau_768', water_down), ('sol_768', down_mask(floor_full_mask)),
                       ('sol_praticable_768', down_mask(walk_full))]:
        Image.fromarray(mask.astype(np.uint8) * 255).save(OUT / 'masques' / f'LGV1_masque_{name}.png')

    # Save source-derived palette swatches and its compact JSON form.
    swatch = Image.new('RGB', (12 * 24, ((len(palette) + 11) // 12) * 28), (24, 32, 42))
    draw = ImageDraw.Draw(swatch)
    for i, color in enumerate(palette):
        xx, yy = (i % 12) * 24, (i // 12) * 28
        draw.rectangle((xx, yy, xx + 22, yy + 22), fill=tuple(map(int, color)))
        draw.text((xx + 2, yy + 22), str(i), fill=(255, 255, 255))
    swatch.save(OUT / 'review/LGV1_palette_96_echantillonnee.png')
    (OUT / 'palette_reference.json').write_text(json.dumps({
        'shared_palette_rgb': palette.tolist(), 'shared_palette_meta': palette_meta,
        'crystal_palette_rgb': crystal_palette.tolist(), 'crystal_palette_meta': crystal_palette_meta,
        'water_ramp_rgb': water_palette.tolist(),
        'water_source': 'T01P02A_Frame_0..5; couleurs bleues/cyan exactes échantillonnées dans les rendus Red',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    layer_names = {
        'base_sol': 'sol_givre',
        'chemin_givre': 'chemin_givre',
        'parois_givrees': 'parois_givrees',
        'cristaux': 'cristaux',
        'arche_nord': 'arche_nord',
    }
    png_layers = []
    layer_manifest = []
    for i, (key, title) in enumerate(layer_names.items(), start=1):
        filename = f'{PFX}_{i:02d}_{title}.png'
        Image.fromarray(static_layers[key]).save(OUT / 'calques' / filename)
        png_layers.append((title, static_layers[key]))
        layer_manifest.append({'index': i, 'name': title, 'file': f'calques/{filename}',
                               'frames': 1, 'frame_length_ticks': 60,
                               'origin': 'sol_complet généré' if key in floor_classes else 'decor_magenta généré, masque segmenté en Python'})
    for i, frame in enumerate(water):
        Image.fromarray(frame).save(OUT / 'animation/eau' / f'{PFX}_00_eau_f{i:02d}.png')
    Image.fromarray(water_index).save(OUT / 'animation/eau' / f'{PFX}_00_indices_f00.png')
    layer_manifest.insert(0, {'index': 0, 'name': 'eau_lac_gele',
                              'file': 'animation/eau/LGV1_00_eau_fXX.png',
                              'frames': WATER_FRAMES, 'frame_length_ticks': WATER_TICKS,
                              'origin': 'texture animée procédurale à palette échantillonnée du Red PMDO T01P02A'})

    # Collision markers and PMDO Ground package.
    access = {'entry_px': entry_px, 'threshold_px': threshold_px,
              'entry_grid_yx': list(entry), 'threshold_grid_yx': list(threshold),
              'path_found_16x16': path_ok, 'cells_explored': int(explored_bfs),
              'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size),
              'rule': 'case bloquée si >25 % non praticable (eau, falaises froides, cristaux, arche); personnage 16×16 px'}
    scene_layers = [('00_eau_lac_gele', water[0])] + png_layers
    scenes = []
    for t in range(WATER_FRAMES):
        scene = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        scene.alpha_composite(Image.fromarray(water[t]))
        for _, layer in png_layers:
            scene.alpha_composite(Image.fromarray(layer))
        scenes.append(scene)
    scenes[0].save(OUT / 'review/LGV1_scene_t000.png')
    scenes[0].resize((W * 2, H * 2), Image.Resampling.NEAREST).save(OUT / 'review/LGV1_scene_x2.png')
    scenes[0].save(OUT / 'review/LGV1_scene_eau_animee.webp', save_all=True,
                   append_images=scenes[1:], duration=round(WATER_TICKS * 1000 / 60), loop=0, lossless=True)
    collision = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(overlay)
    for yy, xx in zip(*np.nonzero(blocked)):
        dd.rectangle([xx*TILE, yy*TILE, xx*TILE+TILE-1, yy*TILE+TILE-1], fill=(236, 53, 61, 100))
    dd.rectangle([entry_px[0], entry_px[1], entry_px[0]+15, entry_px[1]+15], outline=(60, 152, 255, 255), width=2)
    dd.rectangle([threshold_px[0], threshold_px[1], threshold_px[0]+15, threshold_px[1]+15], outline=(255, 220, 60, 255), width=2)
    # Put markers on top of a rendered scene for a readable review layer.
    collision = scenes[0].copy(); collision.alpha_composite(overlay)
    ImageDraw.Draw(collision).text((entry_px[0]+18, entry_px[1]), 'entrée', fill=(60, 152, 255, 255))
    ImageDraw.Draw(collision).text((threshold_px[0]+18, threshold_px[1]), 'seuil', fill=(255, 220, 60, 255))
    collision.save(OUT / 'review/LGV1_collisions_marqueurs.png')
    write_ora(OUT / 'LGV1_lac_de_verre_calques.ora', scene_layers, 'Lac de Verre — PMD Red × Sky — 4:3')

    refs_meta = []
    for path in RED_FILES + [SKY_FILE]:
        refs_meta.append({'file': str(path.relative_to(ROOT)), 'sha256': sha(path),
                          'size_px': list(Image.open(path).size)})
    source_refs = [
        {'repo': 'meromoonmeri/PMD-RED-PMDO-PORT', 'branch': 'main',
         'commit': '680fb85efacbde40473ef3f09dde2c0152e96f6c',
         'map': 'T01P02A (Whiscash Pond)',
         'path': 'PMDRed_PMDO_Framework/output/Visual_Renders/T01P02A_Frame_0.png',
         'url': 'https://github.com/meromoonmeri/PMD-RED-PMDO-PORT/blob/680fb85efacbde40473ef3f09dde2c0152e96f6c/PMDRed_PMDO_Framework/output/Visual_Renders/T01P02A_Frame_0.png',
         'use': 'image de référence du générateur; palette d’eau échantillonnée sur les frames 0–5'},
        {'repo': 'meromoonmeri/PMD-SKY-PMDO-PORT', 'branch': 'master',
         'commit': 'd62110a00269bdc861b8fe41b077607a80f50978',
         'map': 'D52P11A (code de preview; nom canonique non affirmé)',
         'path': 'output/Previews/d52p11a.png',
         'url': 'https://github.com/meromoonmeri/PMD-SKY-PMDO-PORT/blob/d62110a00269bdc861b8fe41b077607a80f50978/output/Previews/d52p11a.png',
         'use': 'image de référence du générateur et source de la palette froide'}
    ]
    raw_meta = [{'file': str(path.relative_to(ROOT)), 'sha256': sha(path),
                 'size_px': list(Image.open(path).size)} for path in RAW_FILES]
    manifest = {
        'lot': 'serie_sources_croisees_v1/lac_de_verre',
        'title': 'Lac de Verre', 'prefix': PFX,
        'format': '4:3 vaste', 'size_px': [W, H], 'grid_8px': [W // TILE, H // TILE],
        'method': ('échantillonnage-génération; références PMDO Red + Sky transmises au générateur; '
                   'décor et sol séparés sur magenta; segmentation Python à pleine résolution; '
                   'réduction uniforme par matière puis recadrage centré 4:3; palette partagée échantillonnée'),
        'references': source_refs, 'reference_files': refs_meta,
        'raw_inputs': raw_meta,
        'normalization': {'source_px': [SRC_W, SRC_H], 'scale_uniforme': SCALE,
                          'scaled_px': [SCALED_W, H], 'crop_x_left_right': [CROP_X, CROP_RIGHT],
                          'output_px': [W, H], 'method': 'BOX sur chaque masque et ses couleurs, puis attribution exclusive par poids maximal'},
        'segmentation': {'magenta_key': 'RGB/antialias chroma: R,B>=150; G<=130; |R-B|<=100; R-G,B-G>=55',
                         'water': 'composantes magenta non reliées au bord, aire >=120 px, dans decor_magenta',
                         'exterior': 'composantes magenta reliées aux bords du brut décor',
                         'path': 'sol_complet, luminance >205; seuil mesuré sur le brut',
                         'walls': 'luminance <148 et saturation >24, ou bande de 28 px autour des bords/eau avec saturation >64 et luminance <205',
                         'crystals': 'cyan lumineux: B>R+28, G>R+13, luminance>=182, saturation>=58',
                         'arch': 'ROI nord centrée x=505..690, y<=142; pixels non-sol (luminance<203 ou saturation>68)'},
        'palette': {'shared_colors': int(len(palette)), 'target_colors': PALETTE_COLORS,
                    'sampling': palette_meta, 'source_files': [str(RED_FILES[0].relative_to(ROOT)), str(SKY_FILE.relative_to(ROOT))],
                    'crystal_colors': int(len(crystal_palette)), 'crystal_palette_rgb': crystal_palette.tolist(),
                    'crystal_palette_sampling': crystal_palette_meta,
                    'generated_material_distance_rgb': fidelity,
                    'water_ramp_rgb': water_palette.tolist(),
                    'water_ramp_origin': 'RGB exacts échantillonnés parmi les bleus/cyans des frames Red T01P02A 0–5'},
        'water': {'frames': WATER_FRAMES, 'frame_length_ticks': WATER_TICKS,
                  'frame_ms': round(WATER_TICKS * 1000 / 60, 2), 'loop_seconds': WATER_FRAMES * WATER_TICKS / 60,
                  'animation': 'ondes horizontales légèrement déformées, 4 phases; palette échantillonnée, pas le cycle officiel'},
        'layers_bottom_to_top': layer_manifest,
        'layer_limits': 'Les calques sont des partitions générées/segmentées; certaines textures sont simplifiées. '
                        'Aucune tuile native certifiée ni géométrie cachée reconstruite.',
        'access': access,
        'pmdo': {'target': '0.8.12', 'serialization': '0.8.12.0', 'asset': ASSET,
                 'namespace': NAMESPACE, 'tex_size': 1, 'tile_px': TILE, 'banks': [],
                 'runtime_tested': False, 'warp': 'aucun; marker donjon_seuil à raccorder'},
        'art_approved': False, 'native_texture_certified': False, 'runtime_tested': False,
    }
    pmdo_meta = ground_project([('eau_lac_gele', water, WATER_TICKS)] +
                               [(layer_names[k], [static_layers[k]], 60) for k in layer_names],
                               blocked, entry_px, threshold_px, manifest)
    manifest['pmdo']['banks'] = pmdo_meta['banks']
    manifest['pmdo']['tiles_per_bank'] = pmdo_meta['tiles_per_bank']
    manifest['access']['reachable_16x16_cells'] = int(explored)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    shutil.copyfile(OUT / 'palette_reference.json', STAGE / 'palette_reference.json')
    print(json.dumps({'scene': str((OUT / 'review/LGV1_scene_t000.png').relative_to(ROOT)),
                      'entry_px': entry_px, 'threshold_px': threshold_px,
                      'route_found': path_ok, 'blocked_cells': int(blocked.sum()),
                      'palette_colors': len(palette), 'water_palette': water_palette.tolist(),
                      'fidelity': fidelity, 'banks': pmdo_meta['banks'],
                      'tiles': pmdo_meta['tiles_per_bank']}, ensure_ascii=False, indent=2))
    return manifest


if __name__ == '__main__':
    build()
