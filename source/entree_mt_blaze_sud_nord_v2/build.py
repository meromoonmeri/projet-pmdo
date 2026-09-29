"""EMB2 — entrée Mt. Blaze en layout de référence, textures GBA et cycles palette canoniques.

L’illustration de base est générée avec le générateur d’images en fournissant la vignette canonique locale
« Rescue Team - Mt. Blaze Entrance » comme référence visuelle stricte : entrée au centre-haut, deux piliers, chemin sableux,
bassins latéraux, falaises et blocs. Les textures et calques restent séparés en aval.
Le layout dérivé porte un key magenta pur #FF00FF pour le placement exact de la lave. Les textures source RGBA de lave
et de veines rocheuses sont extraites séparément, puis leurs calques sont animés indépendamment. La vignette GBA est
conservée dans reference/ ; EMB1 demeure intact.

La lave garde ses pixels fixes. Ses accents, ainsi que les veines dans les roches, reprennent le cycle de palette
D41P41A étudié pour Pokémon Mystery Dungeon: Explorers of Sky : 13 crans × 10 ticks = 130 ticks. C’est une adaptation
exacte de la cadence et des tables palette PMD Ciel sur l’art Mt. Blaze GBA — pas une affirmation que ces palettes
proviennent de Red Rescue Team.

Lancer : .venv/bin/python source/entree_mt_blaze_sud_nord_v2/build.py
Puis : .venv/bin/python -m unittest source.entree_mt_blaze_sud_nord_v2.test_build -v
Puis : .venv/bin/python source/entree_mt_blaze_sud_nord_v2/package.py
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
OUT = R / 'renders/entree_mt_blaze_sud_nord_v2'
STAGE = R / '.cache/entree_mt_blaze_sud_nord_v2/entree_mt_blaze_sud_nord'
NAMESPACE = 'entree_mt_blaze_sud_nord_v2'
ASSET = 'emb2_entree_mt_blaze'
PFX = 'EMB2'
W, H = 768, 576
SRC = (1200, 896)
PHASES, TICKS = 13, 10
LOOP_TICKS = PHASES * TICKS
ANIMS = ('lave', 'veines_roche')
ORDER = ('sol_complet', 'ombres', 'lave', 'sentier', 'eboulis', 'parois', 'piliers', 'grotte', 'veines_roche')
REFERENCE = HERE / 'reference/mt_blaze_reference_300x260.png'
GENERATED_FILE = RAW / 'decor_ref_layout_imagegen.png'
DECOR_FILE = RAW / 'decor_ref_layout.png'
MAGENTA_LAYOUT_FILE = RAW / 'layout_magenta.png'
LAVA_TEXTURE_FILE = RAW / 'lave_texture_rgba.png'
VEIN_TEXTURE_FILE = RAW / 'veines_roche_rgba.png'
MAGENTA = np.array([255, 0, 255], dtype=np.uint8)
ANIMATION_REPORT = R / 'renders/etude_animations_canoniques_sky_v1/rapport.json'
GENERATION = [
    {
        'file': 'bruts/decor_ref_layout_imagegen.png',
        'source_reference': 'reference/mt_blaze_reference_300x260.png',
        'generator': 'generate_image (outil d’image Arena)',
        'image_reference_attached': True,
        'note': 'image de base créée avec le générateur d’images en attachant la vignette canonique Mt. Blaze comme référence stricte ; le build extrait ensuite les matières en calques séparés',
        'prompt': 'Faithfully redraw and expand the attached canonical Pokémon Mystery Dungeon: Red Rescue Team GBA Mt. Blaze entrance screenshot into a clean, wide 4:3 landscape pixel-art map background. Treat the attached image as a strict image reference, not loose inspiration: preserve its unmistakable composition and relative landmarks—small dark cave mouth centered near the top, two squat stepped stone pillars immediately left and right of the entrance, a wide open tan path taking up the lower middle, irregular dark burgundy lava pools hugging both side edges, short curved magma channels and orange lava seams, lavender-gray boulders and cliff walls framing both sides. Keep the same low-resolution 16-bit GBA pixel-art texture and canonical palette. Only extend the side scenery naturally to fit the wider 4:3 map; do not redesign the architecture, do not add a huge gate or arch, do not add a central stone wall, do not move the pools into the path. No characters, no text, no UI, no border, no grid.'
    },
    {'file': 'bruts/decor_ref_layout.png', 'derived_from': 'bruts/decor_ref_layout_imagegen.png',
     'note': 'composition imagegen recolorée par masque matière pour rapprocher les couleurs modales de la vignette GBA'},
    {'file': 'bruts/layout_magenta.png', 'derived_from': 'bruts/decor_ref_layout.png',
     'note': 'layout de base exact : la surface des deux bassins est remplacée par le magenta pur #FF00FF pour définir le placement de la lave'},
    {'file': 'bruts/lave_texture_rgba.png', 'derived_from': 'bruts/decor_ref_layout.png',
     'note': 'source matière dédiée et transparente ; seuls les pixels des bassins magenta restent opaques'},
    {'file': 'bruts/veines_roche_rgba.png', 'derived_from': 'bruts/decor_ref_layout.png',
     'note': 'texture overlay propre ; seules les veines dans la roche restent opaques'}
]


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


def raw_rgba(source, mask):
    """Image RGBA source plein format, transparente et noire hors du masque de matière."""
    mask = np.asarray(mask, dtype=bool)
    source = np.asarray(source, dtype=np.uint8)
    out = np.zeros((*mask.shape, 4), dtype=np.uint8)
    out[mask, :3] = source[mask]
    out[..., 3] = mask.astype(np.uint8) * 255
    return out


def largest_component(mask):
    labels, count = nd.label(mask, structure=np.ones((3, 3), dtype=bool))
    if count == 0:
        return np.zeros_like(mask, dtype=bool)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(sizes.argmax())


def classify(decor):
    """Segmentation mesurée du rendu Mt. Blaze 1200×896, tous les masques étant disjoints.

    Les pixels sable sont appris sur la couleur du chemin du rendu. Deux grands composants vin-rouge latéraux sont
    les bassins/chenaux. Les taches chaudes détachées des bassins et du sol deviennent les veines rocheuses. Le seuil
    noir central sélectionne la bouche ; les volumes neutres du portail et des éboulis sont séparés par régions.
    Le résidu forme les parois, garantissant une partition complète pour la réduction BOX.
    """
    h, w = decor.shape[:2]
    r, g, b = decor.transpose(2, 0, 1).astype(np.int16)
    yy, xx = np.mgrid[:h, :w]
    lum = decor.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)

    # Sable ocre de la référence ; la composante inférieure est le large sol praticable.
    sand = (r > 125) & (g > 85) & (g < 175) & (b > 65) & (b < 150) & (r - g > 18) & (g - b > 5)
    sand = nd.binary_closing(sand, iterations=2)
    path_candidates = sand & (yy > 450)
    path = largest_component(nd.binary_closing(path_candidates, iterations=3))
    path = nd.binary_fill_holes(path)

    # Petite bouche centrale, isolée des ombres latérales par la boîte de la porte.
    cave_candidates = (lum < 52) & (xx > 475) & (xx < 730) & (yy > 260) & (yy < 535)
    cave_labels, cave_count = nd.label(cave_candidates, structure=np.ones((3, 3), dtype=bool))
    if cave_count:
        cave_sizes = np.bincount(cave_labels.ravel())
        cave_sizes[0] = 0
        cave = nd.binary_fill_holes(nd.binary_closing(cave_labels == int(cave_sizes.argmax()), iterations=2))
    else:
        cave = np.zeros((h, w), dtype=bool)

    # Noyaux vin-rouge des deux bassins ; ne retenir que les deux grands corps latéraux.
    side = (xx < 520) | (xx > 680)
    lava_core = (r > 55) & (r - g > 30) & (r - b > 12) & (g < 100) & (b < 110) & (yy > 140) & side
    lava_core = nd.binary_closing(lava_core & ~path & ~cave, iterations=2)
    lava_labels, lava_count = nd.label(lava_core, structure=np.ones((3, 3), dtype=bool))
    lava_sizes = np.bincount(lava_labels.ravel())
    lava_sizes[0] = 0
    components = []
    for label in range(1, lava_count + 1):
        if lava_sizes[label] < 5000:
            continue
        ys, xs = np.nonzero(lava_labels == label)
        components.append({'label': label, 'pixels': int(lava_sizes[label]),
                           'bbox_xyxy': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                           'centroid_x': float(xs.mean())})
    left = [c for c in components if c['centroid_x'] < w / 2]
    right = [c for c in components if c['centroid_x'] >= w / 2]
    if not left or not right:
        raise AssertionError(f'expected left/right lava basins; components={components}')
    keep_ids = [max(left, key=lambda c: c['pixels'])['label'], max(right, key=lambda c: c['pixels'])['label']]
    core = np.isin(lava_labels, keep_ids)
    warm = (r > 50) & (r - g > 17) & (r - b > 7) & (g < 145)
    lava = core | (nd.binary_dilation(core, iterations=5) & warm)
    lava &= ~path & ~cave
    # Remove stray hot pixels detached from both banks; rock vents remain available to the vein layer.
    lava_labels2, lava_count2 = nd.label(lava, structure=np.ones((3, 3), dtype=bool))
    lava_sizes2 = np.bincount(lava_labels2.ravel())
    lava_sizes2[0] = 0
    main_ids = np.argsort(lava_sizes2[1:])[-2:] + 1
    lava = np.isin(lava_labels2, main_ids)

    # Veines chaudes dans la roche, hors chemin, hors bassins et hors halo de leur berge.
    hot = (r > 78) & (r - g > 18) & (r - b > 14) & (g < 135)
    rock_vents = hot & ~nd.binary_dilation(lava, iterations=8) & ~path & ~sand & ~cave
    vein_labels, vein_count = nd.label(rock_vents, structure=np.ones((3, 3), dtype=bool))
    vein_sizes = np.bincount(vein_labels.ravel())
    vein_ids = []
    for label in range(1, vein_count + 1):
        if vein_sizes[label] < 12:
            continue
        ys, xs = np.nonzero(vein_labels == label)
        if int(ys.max()) < 850:
            vein_ids.append(label)
    veins = np.isin(vein_labels, vein_ids)

    # Autels/colonnes autour de la porte, puis les blocs neutres des deux rives.
    spread = decor.max(-1).astype(np.int16) - decor.min(-1).astype(np.int16)
    neutral_stone = (spread < 75) & (lum > 48)
    pillar_roi = ((((xx >= 350) & (xx <= 555)) | ((xx >= 645) & (xx <= 850))) &
                  (yy >= 260) & (yy <= 590))
    pillars = neutral_stone & pillar_roi & ~lava & ~path & ~cave & ~veins
    rubble_roi = ((xx < 480) | (xx > 720)) & (yy > 190) & (yy < 620)
    rubble = neutral_stone & rubble_roi & ~lava & ~path & ~cave & ~veins & ~pillars

    walls = ~(lava | path | cave | veins | pillars | rubble)
    masks = {
        'lave': lava,
        'sentier': path & ~lava,
        'eboulis': rubble,
        'parois': walls,
        'piliers': pillars,
        'grotte': cave & ~path,
        'veines_roche': veins,
    }
    # Enlever explicitement tout recouvrement avant de vérifier la partition.
    occupied = np.zeros((h, w), dtype=bool)
    for name in ('lave', 'sentier', 'eboulis', 'piliers', 'grotte', 'veines_roche'):
        masks[name] &= ~occupied
        occupied |= masks[name]
    masks['parois'] = ~occupied
    assert np.logical_or.reduce(list(masks.values())).all()
    for i, a_name in enumerate(masks):
        for b_name in list(masks)[i + 1:]:
            assert not (masks[a_name] & masks[b_name]).any(), (a_name, b_name)

    # Sur la grille source, seules les deux banques principales sont des bassins.
    bank_labels, bank_count = nd.label(masks['lave'], structure=np.ones((3, 3), dtype=bool))
    bank_sizes = np.bincount(bank_labels.ravel())
    bank_sizes[0] = 0
    largest = sorted((int(v) for v in bank_sizes[1:]), reverse=True)[:2]
    stats = {
        'dimensions_brut': [w, h],
        'seuil_chemin_sable': {'r_min': 125, 'g_min': 85, 'g_max': 174, 'b_min': 65, 'r_moins_g': 18, 'g_moins_b': 5},
        'bassins_lave_majeurs': sorted(components, key=lambda c: c['centroid_x']),
        'composantes_lave_finales': bank_count,
        'deux_aires_lave_max_px': largest,
        'composantes_veines': len(vein_ids),
        'pixels_veines_brut': int(veins.sum()),
        'aire_masques_px': {k: int(v.sum()) for k, v in masks.items()},
    }
    return masks, stats, decor


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


def palette_fidelity_report(decor, masks, reference):
    """Compare modal RGB samples for the three visible materials; this is a palette check, not a pixel-match claim."""
    rr, rg, rb = reference.transpose(2, 0, 1).astype(np.int16)
    yy, xx = np.mgrid[:reference.shape[0], :reference.shape[1]]
    ref_masks = {
        'sentier': (xx >= 90) & (xx <= 210) & (yy >= 225) & (rr > rg) & (rg > rb * 0.85),
        'lave': (((xx < 105) | (xx > 195)) & (yy >= 70) & (yy <= 225) &
                 (rr > rg * 1.25) & (rr > rb * 1.05) & (rg < 130)),
        'roche': (((xx < 65) | (xx > 235)) & (yy < 165) &
                  ((reference.max(-1).astype(np.int16) - reference.min(-1).astype(np.int16)) < 75)),
    }
    recon_masks = {
        'sentier': masks['sentier'],
        'lave': masks['lave'],
        'roche': masks['eboulis'] | masks['parois'] | masks['piliers'],
    }
    result = {}
    for name in ('sentier', 'lave', 'roche'):
        ref_pixels = reference[ref_masks[name]]
        new_pixels = decor[recon_masks[name]]
        ref_values, ref_counts = np.unique(ref_pixels, axis=0, return_counts=True)
        new_values, new_counts = np.unique(new_pixels, axis=0, return_counts=True)
        ref_color = ref_values[int(ref_counts.argmax())].astype(np.int16)
        new_color = new_values[int(new_counts.argmax())].astype(np.int16)
        result[name] = {
            'reference_mode_rgb': ref_color.tolist(),
            'reconstruction_mode_rgb': new_color.tolist(),
            'rgb_euclidean_distance': round(float(np.linalg.norm(ref_color - new_color)), 2),
            'reference_sample_pixels': int(ref_pixels.shape[0]),
            'reconstruction_sample_pixels': int(new_pixels.shape[0]),
        }
    return result


def palette_correct_materials(decor, masks, reference):
    """Décaler les matériaux vers les couleurs modales mesurées dans la vignette GBA.

    Le déplacement RGB est constant par matériau : il conserve les motifs, ombres et hautes lumières de l’image
    générée, mais aligne la couleur modale du chemin, de la lave et de la roche sur les échantillons documentés.
    """
    report = palette_fidelity_report(decor, masks, reference)
    out = decor.astype(np.int16).copy()
    material_masks = {
        'sentier': masks['sentier'],
        'lave': masks['lave'],
        'roche': masks['eboulis'] | masks['parois'] | masks['piliers'],
    }
    for name, mask in material_masks.items():
        source_mode = np.asarray(report[name]['reconstruction_mode_rgb'], dtype=np.int16)
        target_mode = np.asarray(report[name]['reference_mode_rgb'], dtype=np.int16)
        out[mask] = np.clip(out[mask] + (target_mode - source_mode), 0, 255)
    return out.astype(np.uint8)


def canonical_d41_palettes():

    report = json.loads(ANIMATION_REPORT.read_text(encoding='utf-8'))
    records = report['cartes']['d41p41a']['palettes_animees']
    tracks = {int(item['palette']): np.asarray(item['couleurs'], dtype=np.uint8) for item in records}
    for number in (10, 11):
        assert tracks[number].shape == (13, 15, 3), (number, tracks[number].shape)
    return tracks


def make_palette_cycle_frames(surface, full_mask, dynamic_mask, track, dynamic_slots):
    """Pixels fixes, teintes remplacées par l’index exact d’une piste 13×10 ticks de D41P41A."""
    base = surface[..., :3].copy()
    dynamic_mask = np.asarray(dynamic_mask, dtype=bool) & full_mask
    slots = np.asarray(dynamic_slots, dtype=np.int16)
    ref = track[0, slots].astype(np.int16)
    pixels = base[dynamic_mask].astype(np.int16)
    if len(pixels):
        delta = pixels.astype(np.int32)[:, None, :] - ref.astype(np.int32)[None, :, :]
        distances = (delta * delta).sum(-1)
        chosen = slots[distances.argmin(1)]
    else:
        chosen = np.zeros(0, dtype=np.int16)
    frames = []
    for phase in range(PHASES):
        rgb_frame = base.copy()
        if len(chosen):
            rgb_frame[dynamic_mask] = track[phase, chosen]
        frames.append(rgba(rgb_frame.astype(np.uint8), full_mask))
    return frames, {'dynamic_pixels': int(dynamic_mask.sum()), 'palette_indices': sorted(set(map(int, chosen))),
                    'palette_frame0': track[0].astype(int).tolist()}


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
    root = ET.Element('image', w=str(W), h=str(H), name='EMB2 — Entrée Mt. Blaze sud-nord')
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
        group_size = 4 if title in ('lave', 'veines_roche') else max(1, len(frames))
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
        Comment='PMDO 0.8.12. Entree Mt. Blaze en 4:3, disposition reconstruite depuis la reference GBA : bassins lateraux, sol sableux, autels de pierre et petite bouche centrale. Lave et veines rocheuses en rotation de palette 13 x 10 ticks ; mecanique D41P41A de PMD Ciel adaptee, pas animation originale RRT. Aucun warp.'
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
    gfx = loadmod('pmdo_codec_emb2', R / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools_emb2', R / 'source/pmdo_cote/INSTALLER.py')
    if OUT.exists():
        shutil.rmtree(OUT)
    for folder in ('calques', 'animation/lave', 'animation/veines_roche', 'masques', 'review'):
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    STAGE.parent.mkdir(parents=True, exist_ok=True)

    imagegen = rgb(GENERATED_FILE)
    reference = rgb(REFERENCE)
    assert imagegen.shape == (SRC[1], SRC[0], 3)
    assert reference.shape == (260, 300, 3)
    source_masks, segmentation, _ = classify(imagegen)
    decor = palette_correct_materials(imagegen, source_masks, reference)
    Image.fromarray(decor, 'RGB').save(DECOR_FILE)
    material_palette_comparison = palette_fidelity_report(decor, source_masks, reference)

    # Étape de composition demandée : le layout source porte le key magenta exact à l’emplacement des bassins.
    layout_magenta = decor.copy()
    layout_magenta[source_masks['lave']] = MAGENTA
    Image.fromarray(layout_magenta, 'RGB').save(MAGENTA_LAYOUT_FILE)
    magenta_mask = np.all(layout_magenta == MAGENTA, axis=-1)
    assert np.array_equal(magenta_mask, source_masks['lave']), 'magenta key must equal the full-resolution lava placement'
    source_masks['lave'] = magenta_mask

    # Sources matière propres, sans pixels étrangers dans leur alpha ; les veines restent sur un calque indépendant.
    lava_texture = raw_rgba(decor, magenta_mask)
    vein_texture = raw_rgba(decor, source_masks['veines_roche'])
    Image.fromarray(lava_texture, 'RGBA').save(LAVA_TEXTURE_FILE)
    Image.fromarray(vein_texture, 'RGBA').save(VEIN_TEXTURE_FILE)

    names = list(source_masks)
    ex, colors = down_class(decor, source_masks, names)
    _, lava_colors = down_class(lava_texture[..., :3], {'lave': magenta_mask}, ['lave'])
    colors['lave'] = lava_colors['lave']
    _, vein_colors = down_class(vein_texture[..., :3], {'veines_roche': source_masks['veines_roche']}, ['veines_roche'])
    colors['veines_roche'] = vein_colors['veines_roche']

    # Le fond de travail reste de la terre sableuse de la référence ; les calques matières couvrent ensuite le décor.
    ground_base = np.empty_like(decor)
    ground_base[:] = (171, 131, 106)
    raw_path = source_masks['sentier']
    ground_base[raw_path] = decor[raw_path]
    full_ground = rgba(down_full(ground_base), np.ones((H, W), dtype=bool))
    layers = {name: rgba(colors[name], ex[name]) for name in names}

    solid = ex['eboulis'] | ex['parois'] | ex['piliers'] | ex['grotte'] | ex['veines_roche']
    shadows, shadow_mask = make_shadow(solid, ex['sentier'], ex['lave'])
    layers['ombres'] = shadows
    layers['sol_complet'] = full_ground

    # Deux palettes PMD Ciel réduites sans tramage : sable, roche et base magma gardent les couleurs du rendu GBA.
    layers.update(quantize_group({'sol_complet': layers['sol_complet'], 'sentier': layers['sentier']}, 48))
    layers.update(quantize_group({k: layers[k] for k in ('ombres', 'eboulis', 'parois', 'piliers', 'grotte')}, 112))

    tracks = canonical_d41_palettes()
    lava_mask = ex['lave']
    lava_surface = layers['lave']
    lr, lg, lb = lava_surface[..., :3].astype(np.int16).transpose(2, 0, 1)
    lava_hot = lava_mask & (lr > 112) & (lr - lg > 18) & (lr - lb > 10) & (lg < 170)
    # Palette 10 : les quatre teintes terre restent fixes dans la table canonique ; seuls les pixels chauds tournent.
    lava_frames, lava_cycle = make_palette_cycle_frames(
        lava_surface, lava_mask, lava_hot, tracks[10], list(range(0, 7)) + list(range(11, 15)))
    vein_mask = ex['veines_roche']
    vein_surface = layers['veines_roche']
    vein_frames, vein_cycle = make_palette_cycle_frames(
        vein_surface, vein_mask, vein_mask, tracks[11], list(range(4, 15)))
    assert lava_cycle['dynamic_pixels'] > 250, f'too few hot lava pixels: {lava_cycle["dynamic_pixels"]}'
    assert vein_cycle['dynamic_pixels'] > 250, f'too few rock-vein pixels: {vein_cycle["dynamic_pixels"]}'
    anim = {'lave': lava_frames, 'veines_roche': vein_frames}

    for name, mask in ex.items():
        Image.fromarray((mask * 255).astype(np.uint8)).save(OUT / 'masques' / f'{PFX}_masque_{name}.png')
    Image.fromarray((lava_hot * 255).astype(np.uint8)).save(OUT / 'masques' / f'{PFX}_masque_lave_cycle.png')
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
    Image.fromarray((blocked.repeat(8, 0).repeat(8, 1) * 255).astype(np.uint8)).save(
        OUT / 'masques' / f'{PFX}_masque_collisions.png')

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

    ora_layers = [(f'{i:02d} {name}', frame_lists[name][0]) for i, name in enumerate(ORDER)]
    ora_layers.append((f'{len(ORDER):02d} Top (vide)', np.zeros((H, W, 4), dtype=np.uint8)))
    write_ora(OUT / f'{PFX}_entree_mt_blaze_calques.ora', dict(ora_layers))
    tile_counts = make_ground_project(stack_named, blocked, entry_px, threshold_px, gfx, tools)

    raw_records = []
    for relative in [item['file'] for item in GENERATION] + ['reference/mt_blaze_reference_300x260.png']:
        raw_path = HERE / relative
        with Image.open(raw_path) as source_image:
            raw_records.append({'file': f'source/entree_mt_blaze_sud_nord_v2/{relative}',
                                'sha256': sha(raw_path), 'size': list(source_image.size), 'mode': source_image.mode})
    report_hash = sha(ANIMATION_REPORT)
    manifest = {
        'lot': 'entree_mt_blaze_sud_nord_v2',
        'prefix': PFX,
        'format': '4:3 vaste',
        'type': 'entrée de donjon — layout proche de la référence GBA',
        'size_px': [W, H],
        'grid_8px': [W // 8, H // 8],
        'base': 'branche arena/01a0ef03-projet-pmdo ; EMB1 conservé séparément',
        'reference_da': {
            'title': 'Rescue Team - Mt. Blaze Entrance — Pokémon Mystery Dungeon: Red Rescue Team (GBA)',
            'page_url': 'https://mysterydungeonwiki.com/wiki/Rescue_Team:Mt._Blaze',
            'original_image_url': 'https://mysterydungeonwiki.com/images/1/12/Rescue_Team_-_Mt._Blaze_Entrance.png',
            'local_file': 'source/entree_mt_blaze_sud_nord_v2/reference/mt_blaze_reference_300x260.png',
            'local_size_px': [300, 260],
            'sha256': sha(REFERENCE),
            'used_as': 'blueprint de disposition et source visuelle des textures roche, sable et magma',
            'fidelity_note': 'La composition est reconstruite à partir de la vignette locale ; ce n’est pas un rip pixel-par-pixel de la ROM.'
        },
        'material_palette_comparison': material_palette_comparison,
        'material_palette_comparison_note': 'les couleurs modales sont recalées par translation RGB constante à l’intérieur de chaque masque avant mesure ; distance nulle par construction, pas une mesure indépendante de fidélité pixel-à-pixel',
        'method': 'illustration générée via generate_image ; translation RGB par masque pour alignement modal ; layout source 1200×896 avec key magenta #FF00FF exact ; textures RGBA séparées de lave et veines ; cycles en calques Ground/TileLayer.Frames ; réduction BOX par matière ; Ground PMDO 0.8.12',
        'source_materials': {
            'layout': {
                'file': f'source/entree_mt_blaze_sud_nord_v2/{MAGENTA_LAYOUT_FILE.relative_to(HERE).as_posix()}',
                'size_px': [SRC[0], SRC[1]],
                'lava_key_hex': '#FF00FF',
                'lava_key_rgb': [255, 0, 255],
                'lava_placement_pixels': int(magenta_mask.sum()),
                'mask_rule': 'RGB == [255,0,255] exact, sans tolérance',
            },
            'textures': {
                'lave': {
                    'file': f'source/entree_mt_blaze_sud_nord_v2/{LAVA_TEXTURE_FILE.relative_to(HERE).as_posix()}',
                    'mode': 'RGBA', 'opaque_pixels': int((lava_texture[..., 3] == 255).sum()),
                    'alpha_source': 'key exact #FF00FF du layout_magenta.png',
                    'transparent_rgb': [0, 0, 0],
                },
                'veines_roche': {
                    'file': f'source/entree_mt_blaze_sud_nord_v2/{VEIN_TEXTURE_FILE.relative_to(HERE).as_posix()}',
                    'mode': 'RGBA', 'opaque_pixels': int((vein_texture[..., 3] == 255).sum()),
                    'alpha_source': 'masque de veines rocheuses isolé, hors lave et sentier',
                    'transparent_rgb': [0, 0, 0],
                },
            },
            'animated_layers': ['lave', 'veines_roche'],
            'palette_correction': 'translation RGB constante par masque, basée sur la couleur modale de la vignette',
            'alpha_rule': 'alpha binaire ; RGB des zones transparentes ramené à zéro',
        },
        'tool_maps_pmdsky': {
            'readme_consulted': 'source/outil_maps_pmdsky/README.md',
            'scope': 'récupération des maps/BG Pokémon Mystery Dungeon: Explorers of Sky',
            'used_as_source_for_gba_layout': False,
            'reason': 'Le décor visuel cible est Mt. Blaze de Red Rescue Team GBA ; ne pas présenter un rip de PMD Ciel comme texture GBA.'
        },
        'generation': GENERATION,
        'raw_inputs': raw_records,
        'segmentation': segmentation,
        'normalization': {
            'scale': JM.SCALE,
            'scaled': [JM.SCALED_W, H],
            'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
            'method': 'moyenne pondérée BOX par masque de matière, attribution exclusive au masque majoritaire',
            'terrain_palette_colors': 48,
            'rock_palette_colors': 112
        },
        'layers': layer_records,
        'animation': {
            'loop_ticks': LOOP_TICKS,
            'frame_length_ticks': TICKS,
            'phases': PHASES,
            'palette_source': 'D41P41A — Pokémon Mystery Dungeon: Explorers of Sky',
            'palette_report': 'renders/etude_animations_canoniques_sky_v1/rapport.json',
            'palette_report_sha256': report_hash,
            'tracks': {
                'lave': {'palette': 10, 'dynamic_pixels': lava_cycle['dynamic_pixels'],
                         'palette_indices_used': lava_cycle['palette_indices']},
                'veines_roche': {'palette': 11, 'dynamic_pixels': vein_cycle['dynamic_pixels'],
                                 'palette_indices_used': vein_cycle['palette_indices']}
            },
            'mechanic': 'positions des pixels fixes ; rotation exacte des 13 crans de palette source, 10 ticks chacun',
            'canonical_cadence_and_palette': True,
            'native_to_red_rescue_team': False,
            'note': 'Cycle PMD Ciel adapté aux matériaux GBA de la référence Mt. Blaze ; l’animation originale RRT n’est pas revendiquée.'
        },
        'segmentation_masks_px_768x576': {k: int(v.sum()) for k, v in ex.items()},
        'access': {
            'entry_px': entry_px,
            'threshold_px': threshold_px,
            'path_found_16x16': True,
            'cells_explored': explored,
            'blocked_cells': int(blocked.sum()),
            'total_cells': int(blocked.size),
            'walkable_cells': int((~blocked).sum()),
            'rule': 'case bloquée si plus de 25 % des pixels sont hors du masque de sentier praticable',
            'warp': 'aucun'
        },
        'pmdo': {
            'target': '0.8.12',
            'asset': ASSET,
            'namespace': NAMESPACE,
            'tiles_per_bank': tile_counts,
            'sheet_height_px': {name: int((count + 31) // 32 * 8) for name, count in tile_counts.items()},
            'max_sheet_height_px': max(int((count + 31) // 32 * 8) for count in tile_counts.values()),
            'banks': list(tile_counts),
            'runtime_tested': False
        },
        'art_approved': False
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    shutil.copyfile(HERE / 'README_PACK.md', OUT / 'README.md')
    print(json.dumps({'entry': entry_px, 'threshold': threshold_px,
                      'walkable_cells': int((~blocked).sum()), 'blocked_cells': int(blocked.sum()),
                      'segmentation': segmentation, 'animation': manifest['animation'], 'tiles': tile_counts,
                      'outputs': {'scene': str(OUT / 'review' / f'{PFX}_scene_t000.png'), 'project': str(STAGE)}},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    build()
