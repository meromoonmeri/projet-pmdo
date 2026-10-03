#!/usr/bin/env python3
"""Animate the clouds (nuages) and the sea (mer) on the Ground layers of
cliffnordouesttest1.rsground and cliffdaytest.rsground for PMDO 0.8.12.

- Keeps the root cliffnordouesttest1.rsground and cliffdaytest.rsground byte-identical
  to commit 3d801c76 (as required by source/zones_bg_audit_v1/audit.py).
- Animates the Sea layer (sheet 'v2_promontoire_jour_03') across all 8 canonical
  palette-cycled ocean phases (jour_mer_00..07.png, FrameLength=10 ticks = 1.33s loop).
- Animates the Clouds layer ('Cloud/nuage', sheet '01_long_cap_jour_02') across 16
  seamless multi-altitude wind-drift phases (FrameLength=10 ticks = 2.67s loop),
  preserving 100% of the user's cloud tiles at phase 0 in cliffdaytest and adding
  a 3-tier canonical Guild/Sharpedo cloud layer above the horizon in cliffnordouesttest1.
- Cleanly separates the 325 prop/object tiles that were mixed into 'Cloud/nuage'
  in cliffdaytest onto their own 'Objets Decor (ex-Cloud/nuage)' layer so zero props
  are lost.
- Also animates the static/incomplete Metano_Town_Animation_Tileset cascade/water
  tiles on Layer 3 of cliffnordouesttest1 (80 tiles -> 4 phases, FrameLength=10)
  and Layer 4 of cliffdaytest (520 tiles -> clean 3/4-phase loops, FrameLength=10),
  and configures LayeredBG (CLIFF_JOUR_CIEL, CLIFF_JOUR_ASTRES, CLIFF_JOUR_NUAGES).
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import io
import json
import math
import shutil
import struct
import time
import uuid
import zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

R = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = R / 'renders' / 'cliff_nord_jour_anime_v1'
STAGE = Path('/tmp/stage_cliff_nord_jour_anime_v1')
NAMESPACE = 'cliff_nord_jour'

SEA_PHASES = 8
SEA_TICKS = 10       # 8 * 10 = 80 ticks (1.33 s at 60 fps)
CLOUD_PHASES = 16
CLOUD_TICKS = 10     # 16 * 10 = 160 ticks (2.67 s at 60 fps, exact 2x sea loop)
LOOP_TICKS = 160


def loadmod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def premult_arr(arr):
    """Premultiply RGBA uint8 array in-place-compatible numpy manner."""
    a = arr.astype(np.uint16)
    a[:, :, :3] = (a[:, :, :3] * a[:, :, 3:4]) // 255
    return a.astype(np.uint8)


def load_tile_coords(path):
    """Return dict {(tx, ty): file_offset} from a PMDO .tile file without decoding PNGs."""
    with path.open('rb') as f:
        ts, cnt = struct.unpack('<ii', f.read(8))
        return {(x, y): off for x, y, off in (struct.unpack('<iiq', f.read(16)) for _ in range(cnt))}


def load_tile_subset(path, wanted_coords=None):
    """Decode only wanted_coords (or all if None) from a PMDO .tile file -> {(tx, ty): ndarray(8,8,4)}."""
    with path.open('rb') as f:
        ts, cnt = struct.unpack('<ii', f.read(8))
        entries = [struct.unpack('<iiq', f.read(16)) for _ in range(cnt)]
        tiles = {}
        for x, y, off in entries:
            if wanted_coords is not None and (x, y) not in wanted_coords:
                continue
            f.seek(off)
            ln = struct.unpack('<q', f.read(8))[0]
            im = Image.open(io.BytesIO(f.read(ln))).convert('RGBA')
            tiles[(x, y)] = np.array(im)
    return tiles


def write_ora(path, named_layers):
    """Write an OpenRaster (.ora) archive from ordered (name, RGBA ndarray) pairs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    first = next(iter(named_layers.values()))
    h, w = first.shape[:2]
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('mimetype', 'image/openraster', compress_type=zipfile.ZIP_STORED)
        stack_xml = []
        merged = Image.new('RGBA', (w, h))
        for i, (nm, arr) in enumerate(named_layers.items()):
            im = Image.fromarray(arr)
            merged.alpha_composite(im)
            buf = io.BytesIO()
            im.save(buf, format='PNG')
            arc = f'data/{i:02d}_{nm}.png'
            z.writestr(arc, buf.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
            stack_xml.append((nm, arc))
        layers_str = '\n'.join(
            f'    <layer name="{nm}" src="{arc}" x="0" y="0" opacity="1.0" visibility="visible"/>'
            for nm, arc in reversed(stack_xml)
        )
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<image version="0.0.3" w="{w}" h="{h}">
  <stack>
{layers_str}
  </stack>
</image>'''
        z.writestr('stack.xml', xml.encode('utf-8'), compress_type=zipfile.ZIP_DEFLATED)
        mbuf = io.BytesIO()
        merged.save(mbuf, format='PNG')
        z.writestr('mergedimage.png', mbuf.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
        tbuf = io.BytesIO()
        merged.resize((256, max(1, round(256 * h / w))), Image.Resampling.NEAREST).save(tbuf, format='PNG')
        z.writestr('Thumbnails/thumbnail.png', tbuf.getvalue(), compress_type=zipfile.ZIP_DEFLATED)


def build_sea_bank(gfx, sea_arrs):
    """Build v2_promontoire_jour_03.tile preserving phase 0 at exact (tx, ty) in ty=0..127
    and deduplicating phases 1..7 at ty>=128. Also return phase_locs[p][(tx, ty)]."""
    bank = gfx.TileBank('v2_promontoire_jour_03', preserve_layout=True)
    pm_arrs = [premult_arr(a) for a in sea_arrs]
    a0 = pm_arrs[0]
    th, tw = a0.shape[0] // 8, a0.shape[1] // 8

    p0_locs = {}
    for ty in range(th):
        row = a0[ty * 8:ty * 8 + 8]
        for tx in range(tw):
            blk = row[:, tx * 8:tx * 8 + 8]
            if blk[:, :, 3].any():
                raw = blk.tobytes()
                bank.data[(tx, ty)] = raw
                bank.ids.setdefault(raw, (tx, ty))
                p0_locs[(tx, ty)] = {'Sheet': bank.name, 'TexLoc': {'X': tx, 'Y': ty}}

    next_idx = 0
    phase_locs = [p0_locs]
    for p in range(1, SEA_PHASES):
        ap = pm_arrs[p]
        ploc = {}
        for ty in range(th):
            row = ap[ty * 8:ty * 8 + 8]
            for tx in range(tw):
                blk = row[:, tx * 8:tx * 8 + 8]
                if not blk[:, :, 3].any():
                    continue
                raw = blk.tobytes()
                if raw not in bank.ids:
                    loc = (next_idx % 32, 128 + next_idx // 32)
                    next_idx += 1
                    bank.ids[raw] = loc
                    bank.data[loc] = raw
                loc = bank.ids[raw]
                ploc[(tx, ty)] = {'Sheet': bank.name, 'TexLoc': {'X': loc[0], 'Y': loc[1]}}
        phase_locs.append(ploc)
    return bank, phase_locs


def build_cliffnordouest_cloud_base(w_tiles, h_tiles, nuages_arr):
    """Build Phase 0 cloud canvas and exact (x, y) -> (tx, ty) tile map for
    cliffnordouesttest1 (138x98 tiles = 1104x784 px, sea horizon at y=53 tiles = 424 px)."""
    canvas = np.zeros((h_tiles * 8, w_tiles * 8, 4), dtype=np.uint8)
    tile_map = {}
    placements = [
        # High-altitude band (y_tile = 6..14, y_px = 48..112)
        (4, 5, 19, 6,   4,  7),
        (145, 3, 19, 8, 44,  6),
        (34, 2, 12, 8,  86,  7),
        (4, 5, 19, 6,  115,  8),
        # Mid-altitude band (y_tile = 22..30, y_px = 176..240)
        (115, 10, 15, 7, 14, 22),
        (63, 9, 12, 6,   58, 23),
        (91, 4, 12, 6,   98, 22),
        # Horizon band right above sea y=53 (y_tile = 44..52, y_px = 352..416)
        (145, 3, 19, 8,   2, 44),
        (115, 10, 15, 7, 36, 45),
        (4, 5, 19, 6,    68, 46),
        (34, 2, 12, 8,  102, 44),
        (63, 9, 12, 6,  123, 46),
    ]
    for sx0, sy0, cw, ch, dx0, dy0 in placements:
        for dy in range(ch):
            for dx in range(cw):
                tx, ty = sx0 + dx, sy0 + dy
                mx, my = dx0 + dx, dy0 + dy
                if 0 <= mx < w_tiles and 0 <= my < h_tiles:
                    blk = nuages_arr[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]
                    if blk[:, :, 3].any():
                        canvas[my * 8:my * 8 + 8, mx * 8:mx * 8 + 8] = blk
                        tile_map[(mx, my)] = (tx, ty)
    return canvas, tile_map


def extract_cliffdaytest_cloud_base(L_cloud, nuages_arr):
    """Extract the exact 600 cloud tiles (Sheet=='01_long_cap_jour_02') and the 325 prop
    tiles from Layer 5 ('Cloud/nuage') of cliffdaytest.rsground."""
    w_tiles, h_tiles = len(L_cloud['Tiles']), len(L_cloud['Tiles'][0])
    canvas = np.zeros((h_tiles * 8, w_tiles * 8, 4), dtype=np.uint8)
    tile_map = {}
    props_layer = copy.deepcopy(L_cloud)
    props_layer['Name'] = 'Objets Decor (ex-Cloud/nuage)'

    for x in range(w_tiles):
        for y in range(h_tiles):
            kept_trs = []
            for tr in L_cloud['Tiles'][x][y]['Layers']:
                cloud_frames = [f for f in tr['Frames'] if f['Sheet'] == '01_long_cap_jour_02']
                other_frames = [f for f in tr['Frames'] if f['Sheet'] != '01_long_cap_jour_02']
                if cloud_frames:
                    tx, ty = cloud_frames[0]['TexLoc']['X'], cloud_frames[0]['TexLoc']['Y']
                    canvas[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = nuages_arr[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]
                    tile_map[(x, y)] = (tx, ty)
                if other_frames:
                    tr_copy = copy.deepcopy(tr)
                    tr_copy['Frames'] = other_frames
                    kept_trs.append(tr_copy)
            props_layer['Tiles'][x][y]['Layers'] = kept_trs
            if not kept_trs:
                props_layer['Tiles'][x][y]['NeighborCode'] = -1
    return canvas, tile_map, props_layer


def animate_cloud_canvas(base_rgba):
    """Generate 16 seamless wind-drift cloud frames (RGBA ndarrays) from base_rgba.
    Phase 0 is 100% pixel-identical to base_rgba."""
    h, w = base_rgba.shape[:2]
    alpha = base_rgba[:, :, 3] > 0
    dilated = ndimage.binary_dilation(alpha, structure=np.ones((13, 13)))
    lbl, num = ndimage.label(dilated)

    clusters = []
    ys_all = np.nonzero(alpha)[0]
    y_min, y_max = int(ys_all.min()), int(ys_all.max())
    span = max(1, y_max - y_min)

    for c in range(1, num + 1):
        mask = (lbl == c) & alpha
        if not mask.any():
            continue
        ys, xs = np.nonzero(mask)
        y_mean = float(ys.mean())
        rel = (y_mean - y_min) / span
        if rel < 0.36:
            amp = -10.0
        elif rel < 0.72:
            amp = +12.0
        else:
            amp = -8.0
        clusters.append((ys, xs, amp))

    frames = []
    for p in range(CLOUD_PHASES):
        if p == 0:
            frames.append(base_rgba.copy())
            continue
        s = math.sin(2.0 * math.pi * p / CLOUD_PHASES)
        out = np.zeros_like(base_rgba)
        for ys, xs, amp in clusters:
            dx = round(amp * s)
            nx = (xs + dx) % w
            out[ys, nx] = base_rgba[ys, xs]
        frames.append(out)
    assert np.array_equal(frames[0], base_rgba)
    return frames


def init_cloud_bank(gfx, nuages_arr):
    """Initialize 01_long_cap_jour_02.tile with (0, 0) = transparent 8x8 tile
    and (tx, ty) in ty=0..25 = exact original tiles from jour_nuages.png."""
    bank = gfx.TileBank('01_long_cap_jour_02', preserve_layout=True)
    bank.data[(0, 0)] = bytes(256)
    bank.ids[bytes(256)] = (0, 0)
    pm = premult_arr(nuages_arr)
    th, tw = pm.shape[0] // 8, pm.shape[1] // 8
    assert (tw, th) == (180, 26)
    for ty in range(th):
        row = pm[ty * 8:ty * 8 + 8]
        for tx in range(tw):
            blk = row[:, tx * 8:tx * 8 + 8]
            if blk[:, :, 3].any():
                raw = blk.tobytes()
                bank.data[(tx, ty)] = raw
                bank.ids.setdefault(raw, (tx, ty))
    bank._next_extra = 0
    return bank


def build_cloud_map_layer(gfx, bank, cloud_frames, p0_tile_map, name='Cloud/nuage'):
    """Build a PMDO MapLayer for the 16-phase cloud animation using bank
    ('01_long_cap_jour_02'). Vectorized tile extraction."""
    pm_frames = [premult_arr(a) for a in cloud_frames]
    h_px, w_px = pm_frames[0].shape[:2]
    gw, gh = w_px // 8, h_px // 8
    anim_cells = 0

    def cell_frames(x, y):
        nonlocal anim_cells
        y0, x0 = y * 8, x * 8
        # Quick check if any phase has non-zero alpha in this 8x8 block
        if not any(pm[y0:y0 + 8, x0:x0 + 8, 3].any() for pm in pm_frames):
            return []
        fs = []
        for p, pm in enumerate(pm_frames):
            blk = pm[y0:y0 + 8, x0:x0 + 8]
            if not blk[:, :, 3].any():
                fs.append({'Sheet': bank.name, 'TexLoc': {'X': 0, 'Y': 0}})
            elif p == 0 and (x, y) in p0_tile_map:
                tx, ty = p0_tile_map[(x, y)]
                fs.append({'Sheet': bank.name, 'TexLoc': {'X': tx, 'Y': ty}})
            else:
                raw = blk.tobytes()
                if raw not in bank.ids:
                    idx = bank._next_extra
                    bank._next_extra += 1
                    loc = (idx % 32, 26 + idx // 32)
                    bank.ids[raw] = loc
                    bank.data[loc] = raw
                loc = bank.ids[raw]
                fs.append({'Sheet': bank.name, 'TexLoc': {'X': loc[0], 'Y': loc[1]}})
        anim_cells += 1
        return fs

    layer_obj = gfx.layer(name, gw, gh, cell_frames, CLOUD_TICKS)
    return layer_obj, anim_cells


def fix_metano_anim_tiles(layer_obj, anim_coords):
    """Animate static or incomplete Metano_Town_Animation_Tileset cells on a layer
    with clean 3- or 4-phase cycles and FrameLength=10."""
    fixed_count = 0
    for col in layer_obj['Tiles']:
        for cell in col:
            for tr in cell['Layers']:
                if not any(f['Sheet'] == 'Metano_Town_Animation_Tileset' for f in tr['Frames']):
                    continue
                valid = [(f['TexLoc']['X'], f['TexLoc']['Y'])
                         for f in tr['Frames']
                         if f['Sheet'] == 'Metano_Town_Animation_Tileset']
                if not valid:
                    continue
                bx, by = valid[0]
                if 62 <= by <= 71 or 29 <= by <= 40:
                    dx, n_phases = 9, 4
                elif 22 <= by <= 28:
                    dx, n_phases = 8, 4
                elif 13 <= by <= 20:
                    dx, n_phases = 6, 3
                elif 1 <= by <= 4:
                    dx, n_phases = 4, 3
                else:
                    xs = sorted(set(vx for vx, _ in valid))
                    dx = (xs[1] - xs[0]) if len(xs) >= 2 else 9
                    n_phases = 4
                while bx - dx >= 1 and (bx - dx, by) in anim_coords:
                    bx -= dx
                seq = [
                    {'Sheet': 'Metano_Town_Animation_Tileset', 'TexLoc': {'X': bx + k * dx, 'Y': by}}
                    for k in range(n_phases)
                    if (bx + k * dx, by) in anim_coords
                ]
                if len(seq) >= 2:
                    tr['Frames'] = seq
                    tr['FrameLength'] = 10
                    fixed_count += 1
    return fixed_count


def add_arr_to_bank(bank, arr):
    """Fast numpy population of a preserve_layout TileBank from an RGBA ndarray."""
    pm = premult_arr(arr)
    th, tw = pm.shape[0] // 8, pm.shape[1] // 8
    for ty in range(th):
        row = pm[ty * 8:ty * 8 + 8]
        for tx in range(tw):
            blk = row[:, tx * 8:tx * 8 + 8]
            if blk[:, :, 3].any():
                raw = blk.tobytes()
                bank.data[(tx, ty)] = raw
                bank.ids.setdefault(raw, (tx, ty))


def render_static_layers_preview(doc, repo_sheets, fallback_fn):
    """Render each layer of doc into RGBA ndarrays using numpy slicing."""
    o = doc['Object']
    gw, gh = len(o['Layers'][0]['Tiles']), len(o['Layers'][0]['Tiles'][0])
    w, h = gw * 8, gh * 8
    out = {}
    for idx, L in enumerate(o['Layers']):
        canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        for x in range(gw):
            for y in range(gh):
                for tr in L['Tiles'][x][y]['Layers']:
                    if not tr['Frames']:
                        continue
                    f0 = tr['Frames'][0]
                    s = f0['Sheet']
                    tx, ty = f0['TexLoc']['X'], f0['TexLoc']['Y']
                    blk = None
                    if s in repo_sheets:
                        src = repo_sheets[s]
                        if isinstance(src, dict):
                            blk = src.get((tx, ty))
                        else:
                            if tx * 8 + 8 <= src.shape[1] and ty * 8 + 8 <= src.shape[0]:
                                blk = src[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]
                    if blk is None:
                        blk = fallback_fn(s, x, y, tx, ty)
                    if blk is not None and blk[:, :, 3].any():
                        canvas.alpha_composite(Image.fromarray(blk), (x * 8, y * 8))
        out[idx] = np.array(canvas)
    return out


def build():
    t0 = time.time()
    gfx = loadmod('pmdo_codec', R / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')

    if OUT.exists():
        shutil.rmtree(OUT)
    if STAGE.exists():
        shutil.rmtree(STAGE)
    for sub in ['cliffnordouesttest1/mer', 'cliffnordouesttest1/nuages', 'cliffnordouesttest1/calques',
                'cliffdaytest/mer', 'cliffdaytest/nuages', 'cliffdaytest/calques',
                'Content/Tile', 'Content/BG', 'review']:
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    for sub in ['Content/Tile', 'Content/BG', 'Data/Ground', f'Data/Script/{NAMESPACE}/ground']:
        (STAGE / sub).mkdir(parents=True, exist_ok=True)

    # 1. Load canonical sky, clouds, and 8-phase sea from sprites/cote_dix_zones/fonds/
    sky_full = Image.open(R / 'sprites/cote_dix_zones/fonds/jour_ciel.png').convert('RGBA')
    astres_full = Image.open(R / 'sprites/cote_dix_zones/fonds/jour_astres.png').convert('RGBA')
    nuages_im = Image.open(R / 'sprites/cote_dix_zones/fonds/jour_nuages.png').convert('RGBA')
    nuages_arr = np.array(nuages_im)
    sea_imgs = [
        Image.open(R / f'sprites/cote_dix_zones/fonds/jour_mer_{i:02d}.png').convert('RGBA')
        for i in range(SEA_PHASES)
    ]
    sea_arrs = [np.array(im) for im in sea_imgs]

    # Write LayeredBG .dir files
    for kind, im in [('CIEL', sky_full), ('ASTRES', astres_full), ('NUAGES', nuages_im)]:
        for base_dir in (OUT, STAGE):
            gfx.write_dir(base_dir / f'Content/BG/CLIFF_JOUR_{kind}.dir', im)

    # Build 00_ciel.tile (63x51 tiles = 504x408 px)
    sky_504_arr = np.array(sky_full)[:51 * 8, :63 * 8]
    sky_bank = gfx.TileBank('00_ciel', preserve_layout=True)
    add_arr_to_bank(sky_bank, sky_504_arr)

    # Build 8-phase sea bank v2_promontoire_jour_03.tile
    sea_bank, sea_phase_locs = build_sea_bank(gfx, sea_arrs)

    # Initialize 16-phase cloud bank 01_long_cap_jour_02.tile
    cloud_bank = init_cloud_bank(gfx, nuages_arr)

    # Load Metano_Town_Animation_Tileset coordinates
    anim_coords = set(load_tile_coords(R / 'source/eau_metano/natifs/Metano_Town_Animation_Tileset.tile').keys())

    # ---------------------------------------------------------
    # Process Map 1: cliffnordouesttest1.rsground (138x98 tiles = 1104x784 px)
    # ---------------------------------------------------------
    orig_nw_path = R / 'cliffnordouesttest1.rsground'
    doc_nw = json.loads(orig_nw_path.read_text(encoding='utf-8-sig'))
    o_nw = doc_nw['Object']
    gw_nw, gh_nw = len(o_nw['Layers'][0]['Tiles']), len(o_nw['Layers'][0]['Tiles'][0])
    assert (gw_nw, gh_nw) == (138, 98)

    L0_nw = o_nw['Layers'][0]
    L0_nw['Name'] = '00 Ciel (00_ciel)'
    # Fill top sky rows y=0..25 and harmonize sky gradient above sea horizon y=53
    # (using Y=0..6 deep blue sky gradient like cliffdaytest so there is no cyan band above the sea)
    for x in range(gw_nw):
        for y in range(53):
            ty_sky = max(0, y - 46)
            L0_nw['Tiles'][x][y] = gfx.auto([{'Sheet': '00_ciel', 'TexLoc': {'X': x % 63, 'Y': ty_sky}}], 60)

    nw_cloud_base, nw_cloud_p0_map = build_cliffnordouest_cloud_base(gw_nw, gh_nw, nuages_arr)
    nw_cloud_frames = animate_cloud_canvas(nw_cloud_base)
    nw_cloud_layer, nw_cloud_anim_cells = build_cloud_map_layer(
        gfx, cloud_bank, nw_cloud_frames, nw_cloud_p0_map, name='01 Cloud/nuage (16 phases)'
    )

    L_sea_nw = o_nw['Layers'][1]
    L_sea_nw['Name'] = '02 Mer animee (8 phases)'
    nw_sea_anim_cells = 0
    nw_sea_frames_rgba = [np.zeros((gh_nw * 8, gw_nw * 8, 4), dtype=np.uint8) for _ in range(SEA_PHASES)]
    for x in range(gw_nw):
        for y in range(gh_nw):
            for tr in L_sea_nw['Tiles'][x][y]['Layers']:
                if tr['Frames'] and tr['Frames'][0]['Sheet'] == 'v2_promontoire_jour_03':
                    tx = tr['Frames'][0]['TexLoc']['X']
                    ty = tr['Frames'][0]['TexLoc']['Y']
                    tr['FrameLength'] = SEA_TICKS
                    tr['Frames'] = [sea_phase_locs[p][(tx, ty)] for p in range(SEA_PHASES)]
                    nw_sea_anim_cells += 1
                    for p in range(SEA_PHASES):
                        nw_sea_frames_rgba[p][y * 8:y * 8 + 8, x * 8:x * 8 + 8] = sea_arrs[p][ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]

    nw_cascade_fixed = fix_metano_anim_tiles(o_nw['Layers'][3], anim_coords)
    o_nw['Layers'][2]['Name'] = '03 Falaises et promontoire'
    o_nw['Layers'][3]['Name'] = '04 Chemins et cascade animee'
    o_nw['Layers'] = [L0_nw, nw_cloud_layer, L_sea_nw, o_nw['Layers'][2], o_nw['Layers'][3]]
    o_nw['Background'] = {
        '$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence',
        'Layers': [
            {'BG': gfx.background('CLIFF_JOUR_CIEL')},
            {'BG': gfx.background('CLIFF_JOUR_ASTRES')},
            {'BG': gfx.background('CLIFF_JOUR_NUAGES', 0, -4, True)},
        ],
    }

    # ---------------------------------------------------------
    # Process Map 2: cliffdaytest.rsground (123x99 tiles = 984x792 px)
    # ---------------------------------------------------------
    orig_day_path = R / 'cliffdaytest.rsground'
    doc_day = json.loads(orig_day_path.read_text(encoding='utf-8-sig'))
    o_day = doc_day['Object']
    gw_day, gh_day = len(o_day['Layers'][0]['Tiles']), len(o_day['Layers'][0]['Tiles'][0])
    assert (gw_day, gh_day) == (123, 99)

    o_day['Layers'][0]['Name'] = '00 Ciel (00_ciel)'
    L_sea_day = o_day['Layers'][1]
    L_sea_day['Name'] = '01 Mer animee (8 phases)'
    day_sea_anim_cells = 0
    day_sea_frames_rgba = [np.zeros((gh_day * 8, gw_day * 8, 4), dtype=np.uint8) for _ in range(SEA_PHASES)]
    for x in range(gw_day):
        for y in range(gh_day):
            for tr in L_sea_day['Tiles'][x][y]['Layers']:
                if tr['Frames'] and tr['Frames'][0]['Sheet'] == 'v2_promontoire_jour_03':
                    tx = tr['Frames'][0]['TexLoc']['X']
                    ty = tr['Frames'][0]['TexLoc']['Y']
                    tr['FrameLength'] = SEA_TICKS
                    tr['Frames'] = [sea_phase_locs[p][(tx, ty)] for p in range(SEA_PHASES)]
                    day_sea_anim_cells += 1
                    for p in range(SEA_PHASES):
                        day_sea_frames_rgba[p][y * 8:y * 8 + 8, x * 8:x * 8 + 8] = sea_arrs[p][ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]

    day_cloud_base, day_cloud_p0_map, day_props_layer = extract_cliffdaytest_cloud_base(
        o_day['Layers'][5], nuages_arr
    )
    assert len(day_cloud_p0_map) == 600
    day_cloud_frames = animate_cloud_canvas(day_cloud_base)
    day_cloud_layer, day_cloud_anim_cells = build_cloud_map_layer(
        gfx, cloud_bank, day_cloud_frames, day_cloud_p0_map, name='Cloud/nuage (16 phases)'
    )

    day_cascade_fixed = fix_metano_anim_tiles(o_day['Layers'][4], anim_coords)
    o_day['Layers'][2]['Name'] = '02 Falaises et relief'
    o_day['Layers'][3]['Name'] = '03 Objets et vegetation'
    o_day['Layers'][4]['Name'] = '04 Cascades et eau animee'
    day_props_layer['Name'] = '06 Objets Decor (ex-Cloud/nuage)'

    o_day['Layers'] = [
        o_day['Layers'][0],
        L_sea_day,
        o_day['Layers'][2],
        o_day['Layers'][3],
        o_day['Layers'][4],
        day_cloud_layer,
        day_props_layer,
    ]
    o_day['Background'] = {
        '$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence',
        'Layers': [
            {'BG': gfx.background('CLIFF_JOUR_CIEL')},
            {'BG': gfx.background('CLIFF_JOUR_ASTRES')},
            {'BG': gfx.background('CLIFF_JOUR_NUAGES', 0, -4, True)},
        ],
    }

    print(f'[{time.time()-t0:.1f}s] Writing core .tile banks and .rsground files...', flush=True)
    for b in (sky_bank, sea_bank, cloud_bank):
        b.write(OUT / f'Content/Tile/{b.name}.tile')
        b.write(STAGE / f'Content/Tile/{b.name}.tile')

    for slug, doc in [('cliffnordouesttest1', doc_nw), ('cliffdaytest', doc_day)]:
        raw_bytes = ('\ufeff' + json.dumps(doc, ensure_ascii=False, separators=(',', ':'))).encode('utf-8')
        (OUT / f'{slug}.rsground').write_bytes(raw_bytes)
        (STAGE / f'Data/Ground/{slug}.rsground').write_bytes(raw_bytes)
        lua = f'-- {slug} : nuages et mer animes.\nlocal {slug} = {{}}\nreturn {slug}\n'.encode('utf-8')
        (STAGE / f'Data/Script/{NAMESPACE}/ground/{slug}/init.lua').parent.mkdir(parents=True, exist_ok=True)
        (STAGE / f'Data/Script/{NAMESPACE}/ground/{slug}/init.lua').write_bytes(lua)

    for p in range(SEA_PHASES):
        Image.fromarray(nw_sea_frames_rgba[p]).save(OUT / f'cliffnordouesttest1/mer/mer_{p:02d}.png')
        Image.fromarray(day_sea_frames_rgba[p]).save(OUT / f'cliffdaytest/mer/mer_{p:02d}.png')
    for p in range(CLOUD_PHASES):
        Image.fromarray(nw_cloud_frames[p]).save(OUT / f'cliffnordouesttest1/nuages/nuages_{p:02d}.png')
        Image.fromarray(day_cloud_frames[p]).save(OUT / f'cliffdaytest/nuages/nuages_{p:02d}.png')

    print(f'[{time.time()-t0:.1f}s] Preparing standalone STAGE .tile banks...', flush=True)
    # Collect exact (tx, ty) coordinates needed per sheet across both maps
    needed_by_sheet = {}
    for doc in (doc_nw, doc_day):
        for L in doc['Object']['Layers']:
            for col in L['Tiles']:
                for cell in col:
                    for tr in cell['Layers']:
                        for f in tr['Frames']:
                            needed_by_sheet.setdefault(f['Sheet'], set()).add((f['TexLoc']['X'], f['TexLoc']['Y']))

    repo_tile_sources = {
        'Altere_Pond_Cliffs': R / 'source/antre_harmonie_v3/references/Altere_Pond_Cliffs.tile',
        'Altere_Pond_Objects': R / 'source/antre_harmonie_v3/references/Altere_Pond_Objects.tile',
        'Altere_Pond_Objects_Under': R / 'source/antre_harmonie_v3/references/Altere_Pond_Objects_Under.tile',
        'Metano_Inn_Objects': R / 'source/cafe_spinda_revisite_v7/references/Metano_Inn_Objects.tile',
        'Metano_Town_Animation_Tileset': R / 'source/eau_metano/natifs/Metano_Town_Animation_Tileset.tile',
        'Metano_Town_Cliffs': R / 'source/falaises_metano/natifs/Metano_Town_Cliffs.tile',
        'Metano_Town_Objects': R / 'source/amp_plains_fleurie_v1/references/Metano_Town_Objects.tile',
    }
    repo_sheets_preview = {
        '00_ciel': sky_504_arr,
        '01_long_cap_jour_02': nuages_arr,
        'v2_promontoire_jour_03': sea_arrs[0],
    }
    for sname, spath in repo_tile_sources.items():
        shutil.copyfile(spath, STAGE / f'Content/Tile/{sname}.tile')
        repo_sheets_preview[sname] = load_tile_subset(spath, needed_by_sheet.get(sname, set()))

    repo_png_sources = {
        '13_avancee_basse_gauche_terrain': R / 'renders/caps_terrasses_v4/13_avancee_basse_gauche_terrain.png',
        'terrain': R / 'renders/references_calques_v2/falaises/02/terrain.png',
        'terrain (2)': R / 'renders/references_calques_v2/falaises/01/terrain.png',
        'terrain (3)': R / 'renders/references_calques_v2/falaises/03/terrain.png',
        'terrain (4)': R / 'renders/references_calques_v2/falaises/08/terrain.png',
    }
    for sname, spath in repo_png_sources.items():
        arr = np.array(Image.open(spath).convert('RGBA'))
        repo_sheets_preview[sname] = arr
        tb = gfx.TileBank(sname, preserve_layout=True)
        for tx, ty in needed_by_sheet.get(sname, set()):
            if ty * 8 + 8 <= arr.shape[0] and tx * 8 + 8 <= arr.shape[1]:
                blk = premult_arr(arr[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8])
                if blk[:, :, 3].any():
                    raw = blk.tobytes()
                    tb.data[(tx, ty)] = raw
                    tb.ids.setdefault(raw, (tx, ty))
        tb.write(STAGE / f'Content/Tile/{sname}.tile')

    # Decode only the small 16x16 grass/cliff patch needed for proxy fallback in standalone STAGE
    grass_patch = load_tile_subset(
        R / 'source/falaises_metano/natifs/Metano_Town_Base.tile',
        {(x, 80 + y) for x in range(16) for y in range(16)},
    )
    im02_flip = np.fliplr(repo_sheets_preview['terrain'])

    def proxy_tile_arr(sheet, x, y, tx, ty):
        if sheet in ('INVERSEPATHWAY', 'CLIFF MIROR-Photoroom'):
            if y >= 76:
                return grass_patch.get((x % 16, 80 + (y % 16)))
            if ty * 8 + 8 <= im02_flip.shape[0] and tx * 8 + 8 <= im02_flip.shape[1]:
                blk = im02_flip[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]
                if blk[:, :, 3].any():
                    return blk
        return grass_patch.get((x % 16, 80 + (y % 16)))

    user_local_sheets = [
        'Metano_Altere_Transition_Base',
        'INVERSEPATHWAY',
        'CLIFF MIROR-Photoroom',
        'Metano_Town_Trimmed',
        'Metano_Town_Animated',
        'CanyonCamp',
        'P01P01A_layer1',
    ]
    for sname in user_local_sheets:
        tb = gfx.TileBank(sname, preserve_layout=True)
        tb.data[(0, 0)] = bytes(256)
        tb.ids[bytes(256)] = (0, 0)
        for tx, ty in needed_by_sheet.get(sname, set()):
            blk = proxy_tile_arr(sname, tx, ty, tx, ty)
            if blk is not None:
                pm_blk = premult_arr(blk)
                raw = pm_blk.tobytes()
                tb.data[(tx, ty)] = raw
                tb.ids.setdefault(raw, (tx, ty))
        tb.write(STAGE / f'Content/Tile/{sname}.tile')

    stage_nodes = {}
    for p in sorted((STAGE / 'Content/Tile').glob('*.tile')):
        with p.open('rb') as f:
            stage_nodes[p.stem] = tools.read_node(f)
    (STAGE / 'Content/Tile/index.idx').write_bytes(tools.encode_index(stage_nodes))

    out_nodes = {}
    for p in sorted((OUT / 'Content/Tile').glob('*.tile')):
        with p.open('rb') as f:
            out_nodes[p.stem] = tools.read_node(f)
    (OUT / 'Content/Tile/index.idx').write_bytes(tools.encode_index(out_nodes))

    print(f'[{time.time()-t0:.1f}s] Rendering layer previews, WebP animations, and ORA...', flush=True)
    nw_layers_rgba = render_static_layers_preview(doc_nw, repo_sheets_preview, proxy_tile_arr)
    day_layers_rgba = render_static_layers_preview(doc_day, repo_sheets_preview, proxy_tile_arr)

    nw_ora_dict = {
        '00_ciel': nw_layers_rgba[0],
        '01_nuages_f00': nw_cloud_frames[0],
        '02_mer_f00': nw_sea_frames_rgba[0],
        '03_falaises_promontoire': nw_layers_rgba[3],
        '04_chemins_cascade': nw_layers_rgba[4],
    }
    for k, arr in nw_ora_dict.items():
        Image.fromarray(arr).save(OUT / f'cliffnordouesttest1/calques/{k}.png')
    write_ora(OUT / 'cliffnordouesttest1_calques.ora', nw_ora_dict)

    day_ora_dict = {
        '00_ciel': day_layers_rgba[0],
        '01_mer_f00': day_sea_frames_rgba[0],
        '02_falaises_relief': day_layers_rgba[2],
        '03_objets_vegetation': day_layers_rgba[3],
        '04_cascades_eau': day_layers_rgba[4],
        '05_nuages_f00': day_cloud_frames[0],
        '06_objets_decor': day_layers_rgba[6],
    }
    for k, arr in day_ora_dict.items():
        Image.fromarray(arr).save(OUT / f'cliffdaytest/calques/{k}.png')
    write_ora(OUT / 'cliffdaytest_calques.ora', day_ora_dict)

    nw_scenes, day_scenes = [], []
    for step_idx in range(CLOUD_PHASES):
        sea_p = step_idx % SEA_PHASES
        cloud_p = step_idx % CLOUD_PHASES

        im_nw = Image.fromarray(nw_layers_rgba[0].copy())
        im_nw.alpha_composite(Image.fromarray(nw_cloud_frames[cloud_p]))
        im_nw.alpha_composite(Image.fromarray(nw_sea_frames_rgba[sea_p]))
        im_nw.alpha_composite(Image.fromarray(nw_layers_rgba[3]))
        im_nw.alpha_composite(Image.fromarray(nw_layers_rgba[4]))
        nw_scenes.append(im_nw)

        im_day = Image.fromarray(day_layers_rgba[0].copy())
        im_day.alpha_composite(Image.fromarray(day_sea_frames_rgba[sea_p]))
        im_day.alpha_composite(Image.fromarray(day_layers_rgba[2]))
        im_day.alpha_composite(Image.fromarray(day_layers_rgba[3]))
        im_day.alpha_composite(Image.fromarray(day_layers_rgba[4]))
        im_day.alpha_composite(Image.fromarray(day_cloud_frames[cloud_p]))
        im_day.alpha_composite(Image.fromarray(day_layers_rgba[6]))
        day_scenes.append(im_day)

    nw_scenes[0].save(OUT / 'review/cliffnordouesttest1_scene_t000.png')
    nw_scenes[0].save(
        OUT / 'review/cliffnordouesttest1_scene_animee.webp',
        save_all=True, append_images=nw_scenes[1:], duration=167, loop=0, lossless=True
    )
    day_scenes[0].save(OUT / 'review/cliffdaytest_scene_t000.png')
    day_scenes[0].save(
        OUT / 'review/cliffdaytest_scene_animee.webp',
        save_all=True, append_images=day_scenes[1:], duration=167, loop=0, lossless=True
    )

    pose_sheet = Image.new('RGBA', (960, 560), (14, 24, 38, 255))
    dr = ImageDraw.Draw(pose_sheet)
    dr.text((16, 12), 'MER ANIMEE (v2_promontoire_jour_03) — 8 phases cycle palette (FrameLength=10 ticks)', fill=(184, 221, 154, 255))
    for p in range(SEA_PHASES):
        crop = sea_imgs[p].crop((0, 144, 220, 320)).resize((110, 88), Image.Resampling.NEAREST)
        pose_sheet.alpha_composite(crop, (16 + p * 116, 36))
        dr.text((16 + p * 116, 128), f'Mer phase {p:02d}', fill=(220, 230, 240, 255))

    dr.text((16, 156), 'NUAGES ANIMES (01_long_cap_jour_02) — 16 phases derive eolienne multi-altitude (FrameLength=10 ticks)', fill=(184, 221, 154, 255))
    for p in range(CLOUD_PHASES):
        col_i = p % 4
        row_i = p // 4
        crop = Image.fromarray(day_cloud_frames[p]).crop((0, 32, 960, 304)).resize((224, 68), Image.Resampling.NEAREST)
        bg_box = Image.new('RGBA', (224, 68), (52, 122, 198, 255))
        bg_box.alpha_composite(crop)
        pose_sheet.alpha_composite(bg_box, (16 + col_i * 234, 182 + row_i * 90))
        dr.text((22 + col_i * 234, 186 + row_i * 90), f'Nuages {p:02d}', fill=(255, 255, 255, 255))
    pose_sheet.save(OUT / 'review/planche_phases_mer_nuages.png')

    ident = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/meromoonmeri/projet-pmdo/' + NAMESPACE)
    mod_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Cliff Nord-Ouest et Cliff Day - Nuages et Mer Animes (0.8.12)</Name>
  <Author>meromoonmeri</Author>
  <Description>Animation des calques de nuages (16 phases) et de mer (8 phases) pour cliffnordouesttest1.rsground et cliffdaytest.rsground sous PMDO 0.8.12.</Description>
  <Namespace>{NAMESPACE}</Namespace>
  <UUID>{ident}</UUID>
  <Version>1.0.0.0</Version>
  <GameVersion>0.8.12.0</GameVersion>
  <ModType>Quest</ModType>
  <Relationships />
</Header>
'''
    (STAGE / 'Mod.xml').write_text(mod_xml, encoding='utf-8')

    installer_code = '''#!/usr/bin/env python3
"""Installe ou met a jour les calques animes de nuages et de mer pour
cliffnordouesttest1.rsground et cliffdaytest.rsground dans un mod PMDO 0.8.12 existant.

- Sauvegarde automatiquement (.avant_anim.bak) les fichiers .rsground, .tile et index.idx
  existants avant de les mettre a jour.
- Ne remplace JAMAIS vos autres feuilles .tile personnalisees (terrain, INVERSEPATHWAY, etc.).
- Reconstruit Content/Tile/index.idx avec les nouvelles banques animees.

Usage :
  python INSTALLER.py "CHEMIN/VERS/PMDO/MODS/VOTRE_MOD" --dry-run
  python INSTALLER.py "CHEMIN/VERS/PMDO/MODS/VOTRE_MOD"
"""
import argparse
from pathlib import Path
import shutil
import struct

CORE_TILES = {'00_ciel.tile', '01_long_cap_jour_02.tile', 'v2_promontoire_jour_03.tile'}
CORE_GROUNDS = {'cliffnordouesttest1.rsground', 'cliffdaytest.rsground'}


def exact(stream, size):
    data = stream.read(size)
    if len(data) != size:
        raise ValueError('Fichier binaire tronque')
    return data


def read_string(stream):
    size = 0
    for shift in range(0, 35, 7):
        byte = exact(stream, 1)[0]
        size |= (byte & 127) << shift
        if byte < 128:
            return exact(stream, size).decode('utf-8')
    raise ValueError('Longueur .NET invalide')


def write_string(value):
    raw = value.encode('utf-8')
    size, header = len(raw), bytearray()
    while size >= 128:
        header.append((size & 127) | 128)
        size >>= 7
    return bytes(header) + bytes([size]) + raw


def read_node(stream):
    header = exact(stream, 8)
    tile_size, count = struct.unpack('<ii', header)
    if tile_size <= 0 or not 0 <= count <= 10_000_000:
        raise ValueError('En-tete TileIndexNode invalide')
    return header + exact(stream, count * 16)


def read_index(path):
    if not path.exists():
        return {}
    with path.open('rb') as f:
        count = struct.unpack('<i', exact(f, 4))[0]
        nodes = {}
        for _ in range(count):
            name = read_string(f)
            nodes[name] = read_node(f)
        return nodes


def encode_index(nodes):
    return struct.pack('<i', len(nodes)) + b''.join(write_string(k) + nodes[k] for k in sorted(nodes))


def install(source, target, dry_run=False):
    source, target = Path(source).resolve(), Path(target).resolve()
    if not (target / 'Mod.xml').is_file():
        raise ValueError('Choisir la racine du mod contenant Mod.xml.')

    updates = []
    for tname in sorted(CORE_TILES):
        src = source / 'Content/Tile' / tname
        if src.is_file():
            updates.append((src, target / 'Content/Tile' / tname, True))
    for src in sorted((source / 'Content/Tile').glob('*.tile')):
        if src.name not in CORE_TILES:
            dst = target / 'Content/Tile' / src.name
            if not dst.exists():
                updates.append((src, dst, False))
    for src in sorted((source / 'Content/BG').glob('*.dir')):
        updates.append((src, target / 'Content/BG' / src.name, True))
    for gname in sorted(CORE_GROUNDS):
        src = source / 'Data/Ground' / gname
        if not src.is_file():
            src = source / gname
        if src.is_file():
            updates.append((src, target / 'Data/Ground' / gname, True))

    print(f'{len(updates)} fichiers a installer/mettre a jour dans {target}')
    if dry_run:
        for src, dst, _ in updates:
            print('  [DRY-RUN]', dst.relative_to(target))
        return

    for src, dst, overwrite in updates:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            if not overwrite:
                continue
            if dst.read_bytes() != src.read_bytes():
                bak = dst.with_suffix(dst.suffix + '.avant_anim.bak')
                if not bak.exists():
                    shutil.copy2(dst, bak)
        shutil.copy2(src, dst)

    idx_path = target / 'Content/Tile/index.idx'
    nodes = read_index(idx_path)
    for tile in sorted((target / 'Content/Tile').glob('*.tile')):
        with tile.open('rb') as f:
            nodes[tile.stem] = read_node(f)
    new_idx = encode_index(nodes)
    if idx_path.exists() and idx_path.read_bytes() != new_idx:
        bak = idx_path.with_suffix('.idx.avant_anim.bak')
        if not bak.exists():
            shutil.copy2(idx_path, bak)
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_bytes(new_idx)
    print(f'Installation terminee : index.idx mis a jour ({len(nodes)} feuilles .tile).')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('target', help='Chemin du mod PMDO cible (dossier contenant Mod.xml)')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    install(Path(__file__).resolve().parent, Path(args.target), args.dry_run)
'''
    (STAGE / 'INSTALLER.py').write_text(installer_code, encoding='utf-8')
    (OUT / 'INSTALLER.py').write_text(installer_code, encoding='utf-8')

    readme_text = """# Cliff Nord-Ouest & Cliff Day — Nuages et Mer Animés (PMDO 0.8.12)

## Ce qui a été animé
1. **`cliffnordouesttest1.rsground` (`138 × 98` cases = `1104 × 784` px)** :
   - **Calque `01 Cloud/nuage (16 phases)`** (`01_long_cap_jour_02.tile`) : 16 phases de dérive éolienne multi-altitude sans saut de boucle (`FrameLength = 10` ticks = `2,67 s`), placé au-dessus du ciel `00_ciel` et derrière la mer/falaise. Le haut du ciel (`y = 0..25`) a également été complété avec `00_ciel`.
   - **Calque `02 Mer animee (8 phases)`** (`v2_promontoire_jour_03.tile`) : les `6 209` cases de mer passent de 1 frame fixe aux **8 phases canoniques** (`jour_mer_00..07.png`, `FrameLength = 10` ticks = `1,33 s`).
   - **Calque `04 Chemins et cascade animee`** (`Metano_Town_Animation_Tileset.tile`) : les `80` cases d'eau/cascade Métano en bas à droite (`x = 90..97, y = 88..97`) passent de 1 frame fixe à leurs **4 phases natives** (`FrameLength = 10`).
   - **`Background` (`LayeredBG`)** : configuré avec `CLIFF_JOUR_CIEL`, `CLIFF_JOUR_ASTRES` et `CLIFF_JOUR_NUAGES` (`RepeatX = true`, `-4 px/s`).

2. **`cliffdaytest.rsground` (`123 × 99` cases = `984 × 792` px)** :
   - **Calque `01 Mer animee (8 phases)`** (`v2_promontoire_jour_03.tile`) : les `7 503` cases de mer passent de 1 frame fixe aux **8 phases canoniques** (`FrameLength = 10` ticks = `1,33 s`).
   - **Calque `Cloud/nuage (16 phases)`** (`01_long_cap_jour_02.tile`) : la phase 0 conserve à 100 % les `600` tuiles de nuages posées sur la carte (`y = 5..38`), animées sur **16 phases** fluides multi-altitudes (`FrameLength = 10` ticks = `2,67 s`).
   - **Calque `06 Objets Decor (ex-Cloud/nuage)`** : les `325` tuiles d'objets/décors (`Altere_Pond_Objects`, `Metano_Town_Objects`, `Metano_Town_Trimmed`, `Metano_Inn_Objects`) qui étaient mélangées dans `Cloud/nuage` sont isolées proprement sur leur propre calque au-dessus afin qu'aucun décor ne bouge avec les nuages ni ne soit perdu.
   - **Calque `04 Cascades et eau animee`** (`Metano_Town_Animation_Tileset.tile`) : les `520` tuiles d'eau/cascades Métano ont été nettoyées (suppression des frames vides `""` qui faisaient clignoter l'eau, restauration des phases intermédiaires `dx = 6 / 8 / 9`, cadence ramenée de `60` à `10` ticks).

## Installation dans votre projet PMDO 0.8.12 existant
Fermez PMDO, puis lancez :
```bash
python INSTALLER.py "CHEMIN/VERS/PMDO/MODS/VOTRE_MOD"
```
Le script met à jour `cliffnordouesttest1.rsground`, `cliffdaytest.rsground`, `00_ciel.tile`, `01_long_cap_jour_02.tile`, `v2_promontoire_jour_03.tile` et reconstruit `Content/Tile/index.idx` sans toucher à vos autres feuilles `.tile` (`INVERSEPATHWAY.tile`, `terrain.tile`, etc.), avec sauvegarde automatique `.avant_anim.bak`.
"""
    (STAGE / 'README.md').write_text(readme_text, encoding='utf-8')
    (OUT / 'README.md').write_text(readme_text, encoding='utf-8')

    manifest = {
        'lot': 'cliff_nord_jour_anime_v1',
        'pmdo_version': '0.8.12.0',
        'namespace': NAMESPACE,
        'art_approved': False,
        'runtime_tested': False,
        'originals_preserved_immutable': {
            'cliffnordouesttest1.rsground': sha256(orig_nw_path),
            'cliffdaytest.rsground': sha256(orig_day_path),
        },
        'sea_animation': {
            'sheet': 'v2_promontoire_jour_03',
            'phases': SEA_PHASES,
            'frame_length_ticks': SEA_TICKS,
            'loop_ticks': SEA_PHASES * SEA_TICKS,
            'source_files': [f'sprites/cote_dix_zones/fonds/jour_mer_{p:02d}.png' for p in range(SEA_PHASES)],
            'unique_tiles_in_bank': len(sea_bank.data),
        },
        'cloud_animation': {
            'sheet': '01_long_cap_jour_02',
            'phases': CLOUD_PHASES,
            'frame_length_ticks': CLOUD_TICKS,
            'loop_ticks': CLOUD_PHASES * CLOUD_TICKS,
            'source_file': 'sprites/cote_dix_zones/fonds/jour_nuages.png',
            'motion': 'derive eolienne sinusoidale multi-altitude sans saut de boucle (-10 px, +12 px, -8 px)',
            'unique_tiles_in_bank': len(cloud_bank.data),
        },
        'maps': {
            'cliffnordouesttest1': {
                'grid_8px': [gw_nw, gh_nw],
                'size_px': [gw_nw * 8, gh_nw * 8],
                'sea_animated_cells': nw_sea_anim_cells,
                'cloud_animated_cells': nw_cloud_anim_cells,
                'cascade_animated_cells': nw_cascade_fixed,
                'layers': [L['Name'] for L in o_nw['Layers']],
                'sha256': sha256(OUT / 'cliffnordouesttest1.rsground'),
            },
            'cliffdaytest': {
                'grid_8px': [gw_day, gh_day],
                'size_px': [gw_day * 8, gh_day * 8],
                'sea_animated_cells': day_sea_anim_cells,
                'cloud_animated_cells': day_cloud_anim_cells,
                'cloud_phase0_preserved_tiles': len(day_cloud_p0_map),
                'props_separated_from_cloud_layer': 325,
                'cascade_animated_cells': day_cascade_fixed,
                'layers': [L['Name'] for L in o_day['Layers']],
                'sha256': sha256(OUT / 'cliffdaytest.rsground'),
            },
        },
    }
    for base_dir in (OUT, STAGE, HERE):
        (base_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print(f'[{time.time()-t0:.1f}s] Packaging ZIPs...', flush=True)
    mod_zip_paths = [
        OUT / 'mod_cliff_nord_jour_pmdo_0812.zip',
        R / 'mod_cliff_nord_jour_pmdo_0812.zip',
    ]
    with zipfile.ZipFile(mod_zip_paths[0], 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(STAGE.rglob('*')):
            if p.is_file():
                z.write(p, f'{NAMESPACE}/{p.relative_to(STAGE).as_posix()}')
    shutil.copyfile(mod_zip_paths[0], mod_zip_paths[1])

    livrable_zip = R / 'livrable_cliff_nord_jour_anime_v1.zip'
    with zipfile.ZipFile(livrable_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file() and p.name != 'mod_cliff_nord_jour_pmdo_0812.zip':
                z.write(p, f'cliff_nord_jour_anime_v1/{p.relative_to(OUT).as_posix()}')

    print(f'[{time.time()-t0:.1f}s] BUILD OK:', json.dumps(manifest['maps'], indent=2))


if __name__ == '__main__':
    build()
