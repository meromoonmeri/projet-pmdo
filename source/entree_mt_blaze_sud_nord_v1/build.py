"""Entrée Mt. Blaze sud → nord V1 — 4:3 vaste, 768 × 576 px (96 × 72 cases).

La composition s'appuie sur les deux références GBA fournies par l'utilisateur. Elles sont visibles dans la demande,
mais leurs copies ne sont pas disponibles dans le checkout ; le dossier outil_maps_pmdsky a été consulté et ne couvre
que PMD Explorers of Sky (aucune carte Mt. Blaze GBA n'y figure). Le décor a donc été généré depuis la description
visuelle de ces références, puis découpé en calques exclusifs.

Trois bruts générés : décor sur magenta, sol intégral, puis lave éditée dans les formes magenta. La magenta générée
est légèrement déviée (#fd00f8 environ), donc son masque utilise une tolérance couleur et garde seulement les deux
grandes composantes de lave ; aucun point magenta ne subsiste dans les exports.

Calques : sol complet, ombres, lave animée, sentier, éboulis, parois, piliers, bouche de grotte, lueurs et braises.
Lave, lueurs et braises bouclent sur 24 phases × 10 ticks = 240 ticks (4 s). Aucun test en jeu PMDO.

Lancer : .venv/bin/python source/entree_mt_blaze_sud_nord_v1/build.py
Puis : .venv/bin/python source/entree_mt_blaze_sud_nord_v1/package.py
"""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import math
import shutil
import uuid
import zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
OUT = R / 'renders/entree_mt_blaze_sud_nord_v1'
STAGE = R / '.cache/entree_mt_blaze_sud_nord_v1/entree_mt_blaze_sud_nord'
NAMESPACE = 'entree_mt_blaze_sud_nord'
ASSET = 'emb1_entree_mt_blaze'
PFX = 'EMB1'
W, H = 768, 576
SRC = (1200, 896)
PHASES, TICKS = 24, 10
LOOP_TICKS = PHASES * TICKS
ANIMS = ('lave', 'lueurs', 'braises')
ORDER = ('sol_complet', 'ombres', 'lave', 'sentier', 'eboulis', 'parois', 'piliers', 'grotte', 'lueurs', 'braises')

PROMPT_DECOR = (
    'Create a NEW, wide landscape 4:3 top-down pixel-art environment map for a classic Game Boy Advance Pokémon '
    'Mystery Dungeon dungeon entrance. Use the exact composition described: Mt. Blaze entrance, a broad worn warm-brown '
    'trail comes from the SOUTH edge at the bottom-center and leads straight north into a deep black cavern doorway '
    'centered near the TOP. The doorway is framed by a dramatic hanging basalt arch with thick vertical stone fangs '
    'and two monumental pale-grey stepped rock pillars, one on each side. Jagged dark slate cliffs fill both side edges, '
    'built from layered chunky angular stones with muted mauve-grey highlights. On both sides of the trail, vivid pools '
    'and curling streams of deep crimson-red lava sit in inset channels, their edges glowing orange and tiny yellow-hot '
    'cracks, small ember sparks. The middle path remains clear and passable, dusty terracotta earth with subtle pixel '
    'cracks and scattered small dark pebbles. Composition should feel mysterious, epic and readable, richly detailed yet '
    'clean, like lovingly hand-drawn 16-bit/GBA pixel art with crisp clusters, controlled limited palette, no blur, no 3D, '
    'no gradients, no characters, no text, no border, no interface. Keep the upper central cave mouth clearly open and very '
    'dark. Make lava channels on left and right distinct, not covering the central trail. IMPORTANT: for later animation '
    'compositing, fill every intended lava pool and channel with perfectly flat pure magenta #FF00FF, and do not draw any '
    'red/orange/yellow lava, glow, embers or reflections anywhere; all non-lava environment details should remain fully '
    'rendered in muted GBA pixel art.'
)
PROMPT_GROUND = (
    'Create an even, ground-only texture sheet that will sit below a pixel-art Mt. Blaze entrance map. Full 4:3 '
    'landscape canvas, top-down, crisp GBA-era pixel art. Match the smooth warm terracotta-brown dirt path in the '
    'reference map (burnt sienna and dusty peach). The color should be nearly uniform with only very subtle single-pixel '
    'grain and a few faint, thin natural hairline cracks spaced far apart. NO checkerboard, NO crosshatching, NO tiled '
    'pattern, NO mottled islands, NO dark patches, NO pebbles, NO objects, NO shadows, NO gradients. Every pixel is the '
    'same walkable earth material edge-to-edge. Keep the texture calm, flat, and consistent with the center path.'
)
PROMPT_LAVA = (
    'Edit the provided pixel-art map. Replace ONLY the perfectly flat bright-magenta areas with beautiful molten lava, '
    'preserving their exact shapes and positions. Keep every path, stone, wall, pillar, cave, shadow, outline and pixel '
    'outside those magenta regions unchanged. Inside the magenta channels, create GBA-era Pokémon Mystery Dungeon '
    'pixel-art lava: a deep burgundy-red base, irregular dark wine-red cooled crust islands, flowing curved scarlet and '
    'vermilion currents, thin glowing orange seams, a few tiny gold-hot fissures and pinprick sparks contained entirely '
    'inside the pools. Use crisp clustered pixels, the same scale and limited palette as the surrounding environment. '
    'Absolutely no glow or red pixels outside the original magenta shapes; do not change the path or rocks; no text or interface.'
)
GENERATION = [
    {'file': 'decor.png', 'images': [], 'prompt': PROMPT_DECOR,
     'note': 'décor 4:3 généré depuis la description visuelle des références utilisateur ; elles n’étaient pas montées comme fichiers dans le checkout'},
    {'file': 'sol_complet.png', 'images': ['decor.png'], 'prompt': PROMPT_GROUND,
     'note': 'généré comme texture intégrale de terre volcanique, palette assortie au décor'},
    {'file': 'lave_texture.png', 'images': ['decor.png'], 'prompt': PROMPT_LAVA,
     'note': 'édition générée ; seuls les pixels correspondant aux deux masques magenta du décor sont conservés'},
]
USER_REFERENCES = ['Rescue_Team_-_Mt._Blaze_Entrance.png', '221081.png']


def loadmod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Normalisation identique aux cartes sud→nord 4:3 de la série : ×(576/896), puis recadrage centré.
JM = loadmod('ejn1_utils_for_emb1', R / 'source/entree_jungle_sud_nord_v1/build.py')
assert (JM.W, JM.H, JM.SRC) == (W, H, SRC)
down_class, down_full, rgba = JM.down_class, JM.down_full, JM.rgba


def rgb(path):
    return np.array(Image.open(path).convert('RGB'), dtype=np.uint8)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def largest_component(mask):
    labels, count = nd.label(mask, structure=np.ones((3, 3), dtype=bool))
    if count == 0:
        return np.zeros_like(mask, dtype=bool)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(sizes.argmax())


def classify(decor):
    """Séparation mesurée sur les trois rendus générés (1200 × 896).

    La lave est la magenta tolérante (R>220, G<45, B>205), limitée aux deux composantes > 5 000 px. Le chemin est le
    plus grand composant terre cuite (R>90, R-G>28, R-B>30, B<145), fermé 3 px et ouvert 1 px. La bouche est le
    composant sombre contenant (600, 96) dans le rectangle central nord. Les piliers sont les pixels gris très clairs
    dans les deux boîtes latérales (x=270..445 et 755..930, y<360). Le résidu rocheux est partagé en éboulis isolés
    (composantes non liées au bord, 50..20 000 px) et parois. Ces masques, avant réduction, forment une partition.
    """
    h, w = decor.shape[:2]
    r, g, b = decor.transpose(2, 0, 1).astype(np.int16)
    yy, xx = np.mgrid[:h, :w]

    magenta = (r > 220) & (g < 45) & (b > 205) & (np.abs(r - b) < 90)
    lab, n = nd.label(magenta, structure=np.ones((3, 3), dtype=bool))
    sizes = np.bincount(lab.ravel())
    keep = np.flatnonzero(sizes >= 5000)
    keep = keep[keep != 0]
    lava = np.isin(lab, keep)
    # Keep exactly the two large banks; the 183-pixel generation speck on a rock is not lava.
    assert len(keep) == 2, f'expected two large lava pools; component sizes={sorted(sizes[1:].tolist(), reverse=True)[:8]}'
    ignored_magenta = magenta & ~lava
    decor_clean = decor.copy()
    if ignored_magenta.any():
        sy, sx = np.nonzero(ignored_magenta)
        roi = ((xx >= max(0, int(sx.min()) - 12)) & (xx <= min(w - 1, int(sx.max()) + 12)) &
               (yy >= max(0, int(sy.min()) - 12)) & (yy <= min(h - 1, int(sy.max()) + 12)))
        rock_color = (decor.max(-1).astype(np.int16) - decor.min(-1).astype(np.int16) < 70)
        rock_color &= (r > 55) & (g > 30) & (b > 30) & ~magenta & ~lava & roi
        # Repaint the isolated glitch from the nearest neutral pixels of the enclosing stone,
        # rather than copying the near-magenta edge hue back into the rock.
        if rock_color.sum() < 12:
            rock_color = roi & ~magenta & ~lava
        _, nearest = nd.distance_transform_edt(~rock_color, return_indices=True)
        decor_clean[ignored_magenta] = decor_clean[tuple(nearest[:, ignored_magenta])]

    earth = (r > 90) & (r - g > 28) & (r - b > 30) & (g > 25) & (g < 180) & (b < 145)
    earth = nd.binary_opening(nd.binary_closing(earth, iterations=3), iterations=1)
    path = largest_component(earth) & ~lava

    lum = decor.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    dark = (lum < 28) & (xx > 430) & (xx < 770) & (yy < 285)
    cave_labels, _ = nd.label(dark, structure=np.ones((3, 3), dtype=bool))
    seed_label = int(cave_labels[96, 600])
    assert seed_label > 0, f'cave seed was not dark: {decor[96,600].tolist()}'
    cave = (cave_labels == seed_label) & ~path & ~lava
    cave = nd.binary_fill_holes(cave)

    neutral = (decor.max(-1).astype(np.int16) - decor.min(-1).astype(np.int16) < 70)
    pale = (r > 165) & (g > 150) & (b > 138) & neutral
    boxes = ((xx >= 270) & (xx <= 445) | (xx >= 755) & (xx <= 930)) & (yy < 360)
    pillars = pale & boxes & ~path & ~lava & ~cave

    remainder = ~(lava | path | cave | pillars)
    labels, n = nd.label(remainder, structure=np.ones((3, 3), dtype=bool))
    border = np.zeros_like(remainder)
    border[:2] = border[-2:] = True
    border[:, :2] = border[:, -2:] = True
    touching = set(np.unique(labels[border & remainder])) - {0}
    component_sizes = np.bincount(labels.ravel())
    isolated_ids = [i for i in range(1, n + 1) if i not in touching and 50 <= component_sizes[i] <= 20000]
    rubble = np.isin(labels, isolated_ids)
    walls = remainder & ~rubble

    masks = {
        'lave': lava,
        'sentier': path,
        'eboulis': rubble,
        'parois': walls,
        'piliers': pillars,
        'grotte': cave,
    }
    assert np.logical_or.reduce(list(masks.values())).all()
    for i, a_name in enumerate(masks):
        for b_name in list(masks)[i + 1:]:
            assert not (masks[a_name] & masks[b_name]).any(), (a_name, b_name)
    stats = {
        'dimensions_brut': [w, h],
        'pixels_magenta_tolerant': int(magenta.sum()),
        'composantes_lave_retenues': [{'pixels': int(sizes[i]), 'bbox_xyxy': [int(np.nonzero(lab == i)[1].min()), int(np.nonzero(lab == i)[0].min()),
                                                                                 int(np.nonzero(lab == i)[1].max()), int(np.nonzero(lab == i)[0].max())]}
                                      for i in keep],
        'pixels_magenta_ecartes': int((magenta & ~lava).sum()),
        'composantes_eboulis': len(isolated_ids),
        'aire_masques_px': {k: int(v.sum()) for k, v in masks.items()},
    }
    stats['pixels_magenta_repeints'] = int(ignored_magenta.sum())
    return masks, stats, decor_clean


def cell_grid(blocked_pixels):
    """Case 8×8 bloquée lorsque plus de 25 % de ses pixels ne sont pas praticables."""
    return blocked_pixels.reshape(H // 8, 8, W // 8, 8).mean((1, 3)) > 0.25


def free_footprints(blocked, clearance=2):
    gh, gw = blocked.shape
    free = np.zeros_like(blocked, dtype=bool)
    for y in range(gh - clearance + 1):
        for x in range(gw - clearance + 1):
            free[y, x] = not blocked[y:y + clearance, x:x + clearance].any()
    return free


def reachable_cells(blocked, start, clearance=2):
    from collections import deque
    free = free_footprints(blocked, clearance)
    seen = np.zeros_like(free, dtype=bool)
    if not free[start]:
        return seen, 0
    q = deque([start])
    seen[start] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < free.shape[0] and 0 <= nx < free.shape[1] and free[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    return seen, int(seen.sum())


def find_markers(walkable):
    blocked = cell_grid(~walkable)
    gh, gw = blocked.shape
    center = gw // 2
    start = (gh - 2, center)
    seen, explored = reachable_cells(blocked, start)
    if not seen[start]:
        candidates = [(y, x) for y in range(gh - 2, max(-1, gh - 10), -1)
                      for x in range(max(0, center - 12), min(gw - 1, center + 13)) if not blocked[y:y + 2, x:x + 2].any()]
        if not candidates:
            raise AssertionError('No free 16×16 entrance footprint at the south edge')
        start = min(candidates, key=lambda p: (gh - p[0], abs(p[1] - center)))
        seen, explored = reachable_cells(blocked, start)
    goals = [(y, x) for y in range(0, gh - 1) for x in range(max(0, center - 12), min(gw - 1, center + 13)) if seen[y, x]]
    if not goals:
        raise AssertionError('No reachable 16×16 cave threshold')
    goal = min(goals, key=lambda p: (p[0], abs(p[1] - center)))
    return blocked, [start[1] * 8, start[0] * 8], [goal[1] * 8, goal[0] * 8], explored


def make_shadow(solid, walk, lava):
    # Petite ombre portée vers le sud-est, visible uniquement sur le sol attenant aux bords du sentier.
    moved = np.zeros_like(solid, dtype=bool)
    moved[5:, 3:] = solid[:-5, :-3]
    ground_near = nd.binary_dilation(walk | lava, iterations=10)
    mask = moved & ~solid & ground_near
    color = np.zeros((H, W, 3), dtype=np.uint8)
    color[:] = (48, 31, 41)
    return rgba(color, mask), mask


def make_lava_frames(surface, mask, phase_indices=range(PHASES)):
    y, x = np.mgrid[:H, :W]
    rgb0 = surface[..., :3].astype(np.int16)
    red, green, blue = rgb0.transpose(2, 0, 1)
    hot = mask & (red > 145) & (green > 28) & (red > blue * 1.12)
    base_wave = (x / 73.0 + y / 121.0)
    frames = []
    for raw_t in phase_indices:
        t = raw_t % PHASES
        wave = np.sin(2 * np.pi * (base_wave - t / PHASES))
        warmth = np.clip((wave + 0.25) * 0.62, 0, 1)
        rgb = rgb0.copy()
        boost = (warmth * 16).astype(np.int16)
        rgb[..., 0] = np.clip(rgb[..., 0] + boost, 0, 255)
        rgb[..., 1] = np.clip(rgb[..., 1] + np.where(hot, boost * 0.65, boost * 0.14).astype(np.int16), 0, 255)
        rgb[..., 2] = np.clip(rgb[..., 2] + np.where(hot, boost * 0.10, 0), 0, 255)
        frames.append(rgba(rgb.astype(np.uint8), mask))
    return frames


def make_glow_frames(surface, mask, phase_indices=range(PHASES)):
    y, x = np.mgrid[:H, :W]
    rgb0 = surface[..., :3].astype(np.int16)
    red, green, blue = rgb0.transpose(2, 0, 1)
    fissures = mask & (red > 150) & (green > 30) & (red > blue * 1.18)
    travel = x / 58.0 + y / 104.0
    frames = []
    for raw_t in phase_indices:
        t = raw_t % PHASES
        wave = np.sin(2 * np.pi * (travel - t / PHASES))
        lit = fissures & (wave > -0.05)
        rgb = np.zeros((H, W, 3), dtype=np.uint8)
        gain = np.clip((wave[lit] + 1.0) * 0.5, 0, 1)
        lit_colors = np.stack((np.clip(red[lit] + 14, 0, 255),
                               np.clip(green[lit] + (25 + 55 * gain), 0, 255),
                               np.clip(blue[lit] + 10, 0, 255)), axis=-1).astype(np.uint8)
        rgb[lit] = lit_colors
        frames.append(rgba(rgb, lit))
    return frames


def ember_poses():
    # Petite planche de sprites procéduraux à bords nets, issue de la palette de la lave.
    poses = []
    patterns = [
        [(3, 5, (184, 41, 25)), (3, 4, (230, 75, 24))],
        [(3, 5, (174, 34, 22)), (3, 4, (242, 105, 31)), (3, 3, (248, 175, 55))],
        [(3, 6, (195, 46, 19)), (2, 5, (239, 91, 25)), (3, 4, (255, 188, 67)), (4, 3, (255, 117, 30))],
        [(3, 6, (168, 34, 24)), (3, 5, (235, 72, 22)), (3, 4, (255, 193, 59)), (2, 3, (249, 121, 27)), (4, 2, (253, 91, 23))],
        [(3, 5, (182, 35, 22)), (3, 4, (242, 107, 27)), (2, 3, (255, 176, 47))],
        [(3, 5, (174, 36, 25)), (4, 4, (231, 81, 27))],
        [(3, 4, (185, 47, 26))],
        [(3, 5, (164, 33, 24))],
    ]
    for i, points in enumerate(patterns):
        im = Image.new('RGBA', (7, 8), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        for x, y, color in points:
            dr.point((x, y), fill=(*color, 255))
        poses.append(np.asarray(im, dtype=np.uint8))
    return poses


def make_ember_frames(lava_mask, phase_indices=range(PHASES)):
    poses = ember_poses()
    yy, xx = np.nonzero(lava_mask)
    rng = np.random.default_rng(31029)
    # Two banks contribute evenly; pick embers from actual lava pixels, never from the central trail.
    comps, count = nd.label(lava_mask, structure=np.ones((3, 3), dtype=bool))
    points = []
    for comp in range(1, count + 1):
        coords = np.argwhere(comps == comp)
        if not len(coords):
            continue
        rng.shuffle(coords)
        for i in range(14):
            j = int((i + 0.5) * len(coords) / 14) % len(coords)
            y0, x0 = coords[j]
            points.append((int(x0), int(y0), int(rng.integers(0, PHASES)), int(rng.integers(-1, 2))))
    frames = []
    for raw_t in phase_indices:
        t = raw_t % PHASES
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        for i, (x0, y0, start, sway) in enumerate(points):
            age = (t - start) % PHASES
            if age >= 9:
                continue
            pose = min(7, age)
            x = x0 + int(round(math.sin((age + i) * 0.65) * sway))
            y = y0 - age * 2
            sprite = Image.fromarray(poses[pose])
            im.alpha_composite(sprite, (x - 3, y - 7))
        frames.append(np.asarray(im, dtype=np.uint8))
    return frames, poses


def quantize_group(layers, colors):
    pixels = np.concatenate([layer[layer[..., 3] == 255][:, :3] for layer in layers.values() if (layer[..., 3] == 255).any()])
    q = Image.fromarray(pixels.reshape(-1, 1, 3), 'RGB').quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    palette = np.asarray(q.getpalette()[:colors * 3], dtype=np.uint8).reshape(-1, 3)
    result = {}
    for name, layer in layers.items():
        out = layer.copy()
        mask = out[..., 3] == 255
        if mask.any():
            indexes = np.asarray(Image.fromarray(out[..., :3], 'RGB').quantize(palette=q, dither=Image.Dither.NONE), dtype=np.uint8)
            out[..., :3] = palette[indexes]
        out[~mask] = 0
        result[name] = out
    return result


def write_ora(path, layers):
    import xml.etree.ElementTree as ET
    root = ET.Element('image', w=str(W), h=str(H), name='EMB1 — Entrée Mt. Blaze sud-nord')
    stack = ET.SubElement(root, 'stack')
    comp = Image.new('RGBA', (W, H))
    items = list(layers.items())
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('mimetype', 'image/openraster', compress_type=zipfile.ZIP_STORED)
        for i, (name, array) in reversed(list(enumerate(items))):
            filename = f'data/layer{i:02d}.png'
            ET.SubElement(stack, 'layer', name=name, src=filename, x='0', y='0', opacity='1.0', visibility='visible',
                          **{'composite-op': 'svg:src-over'})
            buffer = io.BytesIO()
            Image.fromarray(array).save(buffer, format='PNG')
            archive.writestr(filename, buffer.getvalue())
        for _, array in items:
            comp.alpha_composite(Image.fromarray(array))
        buffer = io.BytesIO()
        comp.save(buffer, format='PNG')
        archive.writestr('mergedimage.png', buffer.getvalue())
        thumb = comp.copy()
        thumb.thumbnail((256, 256))
        buffer = io.BytesIO()
        thumb.save(buffer, format='PNG')
        archive.writestr('Thumbnails/thumbnail.png', buffer.getvalue())
        archive.writestr('stack.xml', ET.tostring(root, encoding='utf-8', xml_declaration=True))


def make_ground_project(stack, blocked, entry_px, threshold_px, gfx, tools):
    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE / 'Content/Tile').mkdir(parents=True, exist_ok=True)
    (STAGE / 'Data/Ground').mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(R / 'mod_metano_expeditions_pmdo_0812.zip') as archive:
        template = json.loads(archive.read('metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground'))
    obj = template['Object']
    gw, gh = W // 8, H // 8
    layer_records, banks = [], []
    for i, (title, frames, ticks) in enumerate(stack):
        # Découper les phases en petits TileBanks évite des feuilles très hautes dans PMDO.
        # Chaque référence de frame porte son Sheet ; les frames d'une même couche peuvent donc changer de banque.
        group_size = 4 if title in ('lave', 'lueurs') else max(1, len(frames))
        bank_groups = []
        for first_phase in range(0, len(frames), group_size):
            bank = gfx.TileBank(f'{PFX}_{i:02d}_{title.upper()}_{first_phase // group_size:02d}')
            bank.ids[bytes(256)] = (0, 0)
            bank.data[(0, 0)] = bytes(256)
            bank_groups.append(bank)
            banks.append(bank)

        def cell(x, y, frames=frames, bank_groups=bank_groups, group_size=group_size):
            refs = []
            for phase, frame in enumerate(frames):
                bank = bank_groups[phase // group_size]
                image = Image.fromarray(frame[y * 8:y * 8 + 8, x * 8:x * 8 + 8])
                ref = bank.add(image, x, y)
                refs.append(ref if ref else {'Sheet': bank.name, 'TexLoc': {'X': 0, 'Y': 0}})
            if all(ref['TexLoc'] == {'X': 0, 'Y': 0} for ref in refs):
                return []
            return [refs[0]] if all(ref == refs[0] for ref in refs) else refs

        layer_records.append(gfx.layer(f'{i:02d} {title.replace("_", " ")}', gw, gh, cell, ticks))
    layer_records.append(gfx.layer(f'{len(layer_records):02d} Vos éléments avant-plan (Top)', gw, gh, draw=4))
    for bank in banks:
        bank.write(STAGE / f'Content/Tile/{bank.name}.tile')

    obj.update(
        Name={'DefaultText': 'Entree Mt. Blaze - sud vers nord (4:3)', 'LocalTexts': {}},
        AssetName=ASSET,
        Released=False,
        TexSize=1,
        Music='',
        EdgeView=1,
        ViewCenter=None,
        ViewOffset={'X': 0, 'Y': 0},
        ActiveChar=None,
        Status={},
        Layers=layer_records,
        Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
        Comment='PMDO 0.8.12. Entree Mt. Blaze generee en 4:3 depuis les references GBA fournies ; sentier sud-nord, '
                'deux canaux de lave animes, braises et lueurs. Collisions de base a verifier en jeu. Aucun warp.',
    )
    obj['obstacles'] = [[{'Bounds': {'X': x * 8, 'Y': y * 8, 'Width': 8, 'Height': 8}, 'Tags': int(blocked[y, x])}
                         for y in range(gh)] for x in range(gw)]
    marker = lambda name, point: {'EntName': name, 'Direction': 4, 'EntEnabled': True, 'triggerType': 0,
                                  'Collider': {'X': point[0], 'Y': point[1], 'Width': 16, 'Height': 16}}
    obj['Entities'] = [{'Name': 'Entrees et vos acteurs', 'Visible': True, 'MapChars': [], 'GroundObjects': [], 'Spawners': [],
                        'Markers': [marker('entrance', entry_px), marker('donjon_seuil', threshold_px)]}]
    obj['Decorations'] = [{'Name': 'Vos decorations', 'Layer': 2, 'Visible': True, 'Anims': []}]
    template['Version'] = '0.8.12.0'
    gfx.save(STAGE / f'Data/Ground/{ASSET}.rsground', json.dumps(template, ensure_ascii=False, separators=(',', ':')).encode())
    gfx.save(STAGE / f'Data/Script/{NAMESPACE}/ground/{ASSET}/init.lua',
             f'-- {ASSET} : base d edition, aucun warp.\nlocal {ASSET} = {{}}\nreturn {ASSET}\n'.encode())
    nodes = {}
    for path in sorted((STAGE / 'Content/Tile').glob('*.tile')):
        with path.open('rb') as handle:
            nodes[path.stem] = tools.read_node(handle)
    (STAGE / 'Content/Tile/index.idx').write_bytes(tools.encode_index(nodes))
    ident = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/meromoonmeri/guilde-treehouse-pmd/' + NAMESPACE)
    (STAGE / 'Mod.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Entree Mt. Blaze sud-nord 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : entree de Mt. Blaze, sentier de terre entre les falaises et deux canaux de lave, generee au format 4:3. Animations en calques separes. Pas une aventure jouable.</Description>
  <Namespace>{NAMESPACE}</Namespace>
  <UUID>{ident}</UUID>
  <Version>1.0.0.0</Version>
  <GameVersion>0.8.12.0</GameVersion>
  <ModType>Quest</ModType>
  <Relationships />
</Header>
''', encoding='utf-8')
    installer = (R / 'source/pmdo_cote/INSTALLER.py').read_text()
    needle = '            relative = src.relative_to(source)\n'
    assert needle in installer
    installer = installer.replace(needle, needle + "            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n")
    (STAGE / 'INSTALLER.py').write_text(installer, encoding='utf-8')
    shutil.copyfile(HERE / 'README_PACK.md', STAGE / 'README.md')
    return {bank.name: len(bank.data) for bank in banks}


def scene_at(stack_named, tick):
    scene = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for _, frames, ticks in stack_named:
        scene.alpha_composite(Image.fromarray(frames[(tick // ticks) % len(frames)]))
    return scene


def build():
    gfx = loadmod('pmdo_codec_emb1', R / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools_emb1', R / 'source/pmdo_cote/INSTALLER.py')
    if OUT.exists():
        shutil.rmtree(OUT)
    for folder in ('calques', 'animation/lave', 'animation/lueurs', 'animation/braises', 'poses', 'masques', 'review'):
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    STAGE.parent.mkdir(parents=True, exist_ok=True)

    decor = rgb(RAW / 'decor.png')
    ground_raw = rgb(RAW / 'sol_complet.png')
    lava_edit = rgb(RAW / 'lave_texture.png')
    assert decor.shape == ground_raw.shape == lava_edit.shape == (SRC[1], SRC[0], 3)
    source_masks, segmentation, decor_clean = classify(decor)
    names = list(source_masks)
    ex, colors = down_class(decor_clean, source_masks, names)
    _, lava_colors = down_class(lava_edit, {'lave': source_masks['lave']}, ['lave'])
    colors['lave'] = lava_colors['lave']

    full_ground = rgba(down_full(ground_raw), np.ones((H, W), dtype=bool))
    layers = {name: rgba(colors[name], ex[name]) for name in names}
    solid = ex['eboulis'] | ex['parois'] | ex['piliers'] | ex['grotte']
    shadows, shadow_mask = make_shadow(solid, ex['sentier'], ex['lave'])
    layers['ombres'] = shadows
    layers['sol_complet'] = full_ground

    # Palette restreinte et séparée : terre 48 couleurs, roches 112 couleurs, lave gardée pour son cycle propre.
    layers.update(quantize_group({'sol_complet': layers['sol_complet'], 'sentier': layers['sentier']}, 48))
    layers.update(quantize_group({k: layers[k] for k in ('ombres', 'eboulis', 'parois', 'piliers', 'grotte')}, 112))

    lava_mask = ex['lave']
    lava_surface = layers['lave']
    lava_frames = make_lava_frames(lava_surface, lava_mask)
    glow_frames = make_glow_frames(lava_surface, lava_mask)
    ember_frames, poses = make_ember_frames(lava_mask)
    anim = {'lave': lava_frames, 'lueurs': glow_frames, 'braises': ember_frames}

    for name, mask in ex.items():
        Image.fromarray((mask * 255).astype(np.uint8)).save(OUT / 'masques' / f'{PFX}_masque_{name}.png')
    Image.fromarray((shadow_mask * 255).astype(np.uint8)).save(OUT / 'masques' / f'{PFX}_masque_ombres.png')
    walk = ex['sentier']
    Image.fromarray((walk * 255).astype(np.uint8)).save(OUT / 'masques' / f'{PFX}_masque_praticable.png')

    frame_lists = {}
    layer_records = []
    for i, name in enumerate(ORDER):
        if name in anim:
            frames, ticks = anim[name], TICKS
            for phase, frame in enumerate(frames):
                Image.fromarray(frame).save(OUT / 'animation' / name / f'{PFX}_{i:02d}_{name}_f{phase:02d}.png')
            layer_records.append({'name': name, 'file': f'animation/{name}/{PFX}_{i:02d}_{name}_fNN.png',
                                  'phases': len(frames), 'ticks': ticks})
        else:
            frames, ticks = [layers[name]], 60
            filename = f'{PFX}_{i:02d}_{name}.png'
            Image.fromarray(frames[0]).save(OUT / 'calques' / filename)
            layer_records.append({'name': name, 'file': f'calques/{filename}', 'phases': 1, 'ticks': ticks})
        frame_lists[name] = frames

    blocked, entry_px, threshold_px, explored = find_markers(walk)
    assert reachable_cells(blocked, (entry_px[1] // 8, entry_px[0] // 8))[0][threshold_px[1] // 8, threshold_px[0] // 8]
    Image.fromarray((blocked.repeat(8, 0).repeat(8, 1) * 255).astype(np.uint8)).save(OUT / 'masques' / f'{PFX}_masque_collisions.png')

    stack_named = [(name, frame_lists[name], TICKS if name in ANIMS else 60) for name in ORDER]
    scene0 = scene_at(stack_named, 0)
    scene0.save(OUT / 'review' / f'{PFX}_scene_t000.png')
    scenes = [scene_at(stack_named, tick) for tick in range(0, LOOP_TICKS, 5)]
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_animee.webp', save_all=True, append_images=scenes[1:],
                   duration=round(5 * 1000 / 60), loop=0, lossless=True)

    collision_preview = scene0.copy()
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for cy, cx in zip(*np.nonzero(blocked)):
        draw.rectangle((cx * 8, cy * 8, cx * 8 + 7, cy * 8 + 7), fill=(220, 42, 45, 90))
    for point, color in ((entry_px, (255, 224, 48, 255)), (threshold_px, (50, 224, 255, 255))):
        draw.rectangle((point[0], point[1], point[0] + 15, point[1] + 15), outline=color, width=2)
    collision_preview.alpha_composite(overlay)
    collision_preview.save(OUT / 'review' / f'{PFX}_collisions_marqueurs.png')

    for i, sprite in enumerate(poses):
        Image.fromarray(sprite).save(OUT / 'poses' / f'{PFX}_braise_{i:02d}.png')
    sheet = Image.new('RGBA', (8 * 48 + 16, 80), (43, 34, 45, 255))
    dr = ImageDraw.Draw(sheet)
    for i, sprite in enumerate(poses):
        enlarged = Image.fromarray(sprite).resize((28, 32), Image.Resampling.NEAREST)
        sheet.alpha_composite(enlarged, (8 + i * 48, 8))
        dr.text((8 + i * 48, 48), f'{i}', fill=(230, 220, 205, 255))
    sheet.save(OUT / 'review' / f'{PFX}_planche_poses.png')

    ora_layers = [(f'{i:02d} {name}', frame_lists[name][0]) for i, name in enumerate(ORDER)]
    ora_layers.append((f'{len(ORDER):02d} Top (vide)', np.zeros((H, W, 4), dtype=np.uint8)))
    write_ora(OUT / f'{PFX}_entree_mt_blaze_calques.ora', dict(ora_layers))
    tile_counts = make_ground_project(stack_named, blocked, entry_px, threshold_px, gfx, tools)

    manifest = {
        'lot': 'entree_mt_blaze_sud_nord_v1',
        'prefix': PFX,
        'format': '4:3 vaste',
        'type': 'entrée de donjon',
        'size_px': [W, H],
        'grid_8px': [W // 8, H // 8],
        'base': 'branche arena/01a0ef03-projet-pmdo, parent local 6cca4a09 ; aucune récupération d’une branche sœur, aucun clonage supplémentaire de main',
        'reference_da': {
            'title': 'Mt. Blaze Entrance — Pokémon Mystery Dungeon: Red Rescue Team (GBA)',
            'files_user_supplied': USER_REFERENCES,
            'used_as': 'référence visuelle de composition, palette volcanique et architecture de l’entrée',
            'local_copies': False,
            'metric': None,
            'metric_note': 'Les pièces jointes ne sont pas présentes dans le checkout ; aucune distance pixel/RGB n’est revendiquée.',
        },
        'method': 'rendu généré multicalque 4:3 : décor magenta, terre intégrale et retouche lave ; masques exclusifs, normalisation 4:3 à 8 px, calques PMDO 0.8.12',
        'tool_maps_pmdsky': {
            'readme_consulted': 'source/outil_maps_pmdsky/README.md',
            'scope': 'outil de récupération des maps et BG de Pokémon Mystery Dungeon: Explorers of Sky',
            'use_for_this_map': False,
            'reason': 'Mt. Blaze est ici une référence Red Rescue Team GBA, hors du périmètre de cet outil ; index_rom.json ne contient aucune entrée Mt. Blaze.',
        },
        'generation': GENERATION,
        'raw_inputs': [{'file': f'source/entree_mt_blaze_sud_nord_v1/bruts/{item["file"]}',
                        'sha256': sha(RAW / item['file']), 'size': list(Image.open(RAW / item['file']).size)} for item in GENERATION],
        'segmentation': segmentation,
        'normalization': {
            'scale': JM.SCALE,
            'scaled': [JM.SCALED_W, H],
            'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
            'method': 'moyenne pondérée BOX par masque de matière, attribution exclusive au masque le plus couvrant',
            'terrain_palette_colors': 48,
            'rock_palette_colors': 112,
        },
        'layers': layer_records,
        'animation': {
            'loop_ticks': LOOP_TICKS,
            'frame_length_ticks': TICKS,
            'phases': PHASES,
            'layers': {
                'lave': 'pulsation chromatique orientée le long des chenaux, sur la texture générée ; boucle fermée',
                'lueurs': 'scintillement des fissures chaudes sur la lave, boucle fermée',
                'braises': 'sprites pixel-art procéduraux remontant des deux bassins, boucle fermée',
            },
            'official_animation': False,
        },
        'segmentation_masques_px_768x576': {k: int(v.sum()) for k, v in ex.items()},
        'access': {
            'entry_px': entry_px,
            'threshold_px': threshold_px,
            'path_found_16x16': True,
            'cells_explored': explored,
            'blocked_cells': int(blocked.sum()),
            'total_cells': int(blocked.size),
            'walkable_cells': int((~blocked).sum()),
            'rule': 'case bloquée si plus de 25 % des pixels sont hors du masque de sentier praticable',
            'warp': 'aucun',
        },
        'pmdo': {
            'target': '0.8.12',
            'asset': ASSET,
            'namespace': NAMESPACE,
            'tiles_per_bank': tile_counts,
            'sheet_height_px': {name: int((count + 31) // 32 * 8) for name, count in tile_counts.items()},
            'max_sheet_height_px': max(int((count + 31) // 32 * 8) for count in tile_counts.values()),
            'banks': list(tile_counts),
            'runtime_tested': False,
        },
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    shutil.copyfile(HERE / 'README_PACK.md', OUT / 'README.md')
    print(json.dumps({'entry': entry_px, 'threshold': threshold_px,
                      'walkable_cells': int((~blocked).sum()), 'blocked_cells': int(blocked.sum()),
                      'segmentation': segmentation, 'tiles': tile_counts,
                      'outputs': {'scene': str(OUT / 'review' / f'{PFX}_scene_t000.png'), 'project': str(STAGE)}},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    build()
