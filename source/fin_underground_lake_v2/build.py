"""Fin Underground Lake V2 (FUL2) — sanctuaire du lac souterrain, format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Demande : « alors ........... » (3 octobre, après FCV3, FMT3 et FJS4) : suite des fins de donjon de la série d'entrées
dans l'ordre du mod, prolongeant l'entrée EUL1 (Underground Lake). Biome et portée choisis par l'agent, à confirmer.
Préfixe FUL2 (FUL1 est pris sur des branches sœurs non fusionnées).
Référence `Underground_Lake_shore_TDS.png` (PMD Explorers). Méthode « textures canoniques » = rendu généré RÉFÉRENCÉ
(rip passé au générateur en images=) :
- decor_magenta.png : grotte fermée 4:3 (1200 x 896), arrivée au sud, plateforme d'arène de sable au centre entre les
  deux bassins du lac souterrain en magenta #FF00FF, et au nord, au bout de la chaussée sèche, un monolithe-sanctuaire
  de pierre sculptée adossé à la paroi fermée (sans bouche sombre) ;
- sol_complet.png et gouttes_ronds_poses.png : réutilisés d'EUL1 sans nouvelle génération (même sha256).
Calques : eau, lueur, scintillements, gouttes, sol complet, sable, ombres, berge, roche, piliers, sanctuaire. Pas de
calque `profondeur`.
Animations, chacune sur son calque, boucles fermées (120 ticks = 2 s), fonctions et constantes chargées depuis EUL1 :
- eau : structure rivière Métano (4 x 10 ticks), couleurs EXACTES du rip, sans liseré clair de rive ;
- lueur : cœur + 8 anneaux aux 9 couleurs exactes du rip qui respirent (12 x 10 ticks) ;
- scintillements : `Metano_Town_River_Sparkles.tile` natifs sur le cœur de la lueur (4 x 10 ticks) ;
- gouttes : gouttes qui tombent et ronds dans l'eau (24 x 5 ticks).
Marqueurs : `entrance` (sud), `boss` (centre de la plateforme de sable), `objectif` (au pied du sanctuaire au nord).
Aucune sortie, aucun warp, pas de `donjon_seuil`.
Lancer : .venv/bin/python source/fin_underground_lake_v2/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
REF_NAME = 'Underground_Lake_shore_TDS.png'
REF = R / REF_NAME
OUT = R / 'renders/fin_underground_lake_v2'
STAGE = R / '.cache/fin_underground_lake_v2/fin_underground_lake'
NAMESPACE = 'fin_underground_lake'
ASSET = 'ful2_fin_underground_lake'
PFX = 'FUL2'
W, H = 768, 576
SRC = (1200, 896)
WATER_PHASES, WATER_TICKS = 4, 10
GLOW_PHASES, GLOW_TICKS = 12, 10
DROP_PHASES, DROP_TICKS = 24, 5
LOOP_TICKS = 120
LOT = 'source/fin_underground_lake_v2'


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


EUL1 = loadmod('eul1_build', R / 'source/entree_underground_lake_sud_nord_v1/build.py')
V2, V1 = EUL1.V2, EUL1.V1
JM, BM = EUL1.JM, EUL1.BM
assert (JM.W, JM.H, JM.SRC) == (W, H, SRC)
keep_large, place, cell_grid, close_, open_ = EUL1.keep_large, EUL1.place, EUL1.cell_grid, EUL1.close_, EUL1.open_
down_class, down_full, rgba, resize_plane, quantize_group = (
    EUL1.down_class, EUL1.down_full, EUL1.rgba, EUL1.resize_plane, EUL1.quantize_group)
sha, rgb, materials, fidelity = EUL1.sha, EUL1.rgb, EUL1.materials, EUL1.fidelity
lake_water, glow_frames, glow_centres, sheet_poses, reduce_pose, paste, drop_frames = (
    EUL1.lake_water, EUL1.glow_frames, EUL1.glow_centres, EUL1.sheet_poses, EUL1.reduce_pose, EUL1.paste, EUL1.drop_frames)
WPAL, GLOW, GLOW_RING_PX, GLOW_BREATH, GLOW_WOBBLE, POSE_K, POSE_COV, POSE_WIN, DROP_SEQ = (
    EUL1.WPAL, EUL1.GLOW, EUL1.GLOW_RING_PX, EUL1.GLOW_BREATH, EUL1.GLOW_WOBBLE, EUL1.POSE_K, EUL1.POSE_COV,
    EUL1.POSE_WIN, EUL1.DROP_SEQ)

GEN = [
    {'file': 'decor_magenta.png',
     'images': ['source/entree_underground_lake_sud_nord_v1/bruts/decor_magenta.png', REF_NAME],
     'prompt':
     "Edit the first wide 4:3 landscape pixel-art map (1200x896). Keep the exact 4:3 wide landscape aspect ratio "
     "(1200x896) and keep the exact same pixel-art style, palette, olive-khaki bumpy cave rock walls, pale yellow "
     "stippled sand, tall rock pillars, small pointed stalagmites, and flat pure magenta #FF00FF underground lake "
     "basins on the left and right. Make ONLY two changes for an end-of-dungeon sanctuary room: (1) at the top center "
     "(NORTH), replace the black cave tunnel opening with a CLOSED olive-khaki bumpy rock wall and a tall carved rock "
     "monolith / stalagmite sanctuary shrine standing at the northern tip of the sandy causeway (NO black hole, NO dark "
     "doorway, NO tunnel); (2) widen the middle of the sandy causeway slightly into a rounded sandy arena platform "
     "between the left and right magenta lake basins while keeping the two tall rock pillars and small stalagmites in "
     "the magenta water. Wide landscape 4:3. No characters, no text, no UI, no border.",
     'essais': 'premier essai ; conforme (sable 9.6, roche 6.2)'},
    {'file': 'sol_complet.png',
     'images': ['source/entree_underground_lake_sud_nord_v1/bruts/decor_magenta.png'],
     'prompt':
     "REUTILISE sans nouvelle generation : sol complet d'EUL1 (source/entree_underground_lake_sud_nord_v1/bruts/"
     "sol_complet.png, meme sha256). Prompt d'origine : Same image, same framing and pixel-art style, but only plain "
     "pale yellow sand ground everywhere, nothing else.",
     'essais': 'copie du sol_complet d EUL1 (meme biome, parois recalees 0, 0) : aucune generation supplementaire'},
    {'file': 'gouttes_ronds_poses.png',
     'images': [REF_NAME],
     'prompt':
     "REUTILISE sans nouvelle generation : planche de poses d'EUL1 (source/entree_underground_lake_sud_nord_v1/bruts/"
     "gouttes_ronds_poses.png, meme sha256). Prompt d'origine : Pixel-art sprite sheet on a flat pure magenta #FF00FF "
     "background, same style and colors as the reference. 2 rows of 6 small separate sprites. Row 1: a pale blue water "
     "drop falling then splashing. Row 2: a thin pale blue ripple ring growing from small to large. Sprites well "
     "separated, no text.",
     'essais': 'copie de la planche de poses d EUL1 : aucune generation supplementaire'},
]

PALETTE_GROUPS = {
    'terrain': (['sol_complet', 'sable', 'ombres', 'berge'], 96),
    'roche': (['roche', 'piliers', 'sanctuaire'], 64),
}
STATIC = ['sable', 'ombres', 'berge', 'roche', 'piliers', 'sanctuaire']


def classify(a, f):
    """a : décor (sans bouche sombre, monolithe sanctuaire au nord), f : sol complet d'EUL1 (parois recalées (0, 0))."""
    r, g, b = a.transpose(2, 0, 1); lum = a @ [.299, .587, .114]
    hh, ww = lum.shape; yy, xx = np.mgrid[:hh, :ww]
    water = nd.binary_dilation((r - g > 60) & (b - g > 60), iterations=2)
    sandish = (r > 150) & (r - b > 50) & (lum > 140) & ~water
    sand = keep_large(open_(close_(sandish, 2), 1), 20000)
    holes = nd.binary_fill_holes(sand) & ~sand; hl, _ = nd.label(holes)
    hs = nd.sum(holes, hl, range(1, hl.max() + 1)) if hl.max() else []
    sand = (sand | np.isin(hl, [i + 1 for i, v in enumerate(hs) if v < 300])) & ~water
    rockish = ~sand & ~water
    Ls = nd.uniform_filter(lum, 5); dr = nd.distance_transform_edt(~rockish)
    shade = keep_large(close_(sand & (dr <= 16) & (Ls < 187), 1), 60) & sand
    dw = nd.distance_transform_edt(~water); ds = nd.distance_transform_edt(~sand)
    berge = rockish & (dw <= 14) & (ds <= 14)
    diff = nd.uniform_filter(np.abs(a - f).mean(2), 5)
    rest = rockish & ~berge
    sanc_box = (yy >= 24) & (yy < 208) & (xx >= 568) & (xx <= 632)
    sanctuaire = nd.binary_fill_holes(close_(rest & sanc_box & (diff > 14), 2)) & rest
    pil = rest & ~sanctuaire & (diff > 20) & ~(yy < 220)
    pil = nd.binary_fill_holes(keep_large(open_(close_(pil, 2), 1), 150)) & rest & ~sanctuaire
    roche = rest & ~pil & ~sanctuaire
    ys_s, xs_s = np.nonzero(sanctuaire)
    return dict(water=water, sanctuaire=sanctuaire, sable=sand & ~shade, ombres=shade, berge=berge, piliers=pil,
                roche=roche), {'ecart_parois': round(float(diff[roche].mean()), 2),
                               'ecart_piliers': round(float(diff[pil].mean()), 2),
                               'sanctuaire_y': [int(ys_s.min()), int(ys_s.max())],
                               'sanctuaire_x': [int(xs_s.min()), int(xs_s.max())]}


def write_ora(path, layers):
    import xml.etree.ElementTree as ET
    root = ET.Element('image', w=str(W), h=str(H), name='Fin Underground Lake V2 (FUL2)')
    stack = ET.SubElement(root, 'stack'); comp = Image.new('RGBA', (W, H))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype', 'image/openraster', compress_type=zipfile.ZIP_STORED)
        items = list(layers.items())
        for i, (name, a) in reversed(list(enumerate(items))):
            fn = f'data/layer{i:02d}.png'
            ET.SubElement(stack, 'layer', name=name, src=fn, x='0', y='0', opacity='1.0', visibility='visible',
                          **{'composite-op': 'svg:src-over'})
            b = io.BytesIO(); Image.fromarray(a).save(b, format='PNG'); z.writestr(fn, b.getvalue())
        for _, a in items:
            comp.alpha_composite(Image.fromarray(a))
        b = io.BytesIO(); comp.save(b, format='PNG'); z.writestr('mergedimage.png', b.getvalue())
        th = comp.copy(); th.thumbnail((256, 256)); b = io.BytesIO(); th.save(b, format='PNG')
        z.writestr('Thumbnails/thumbnail.png', b.getvalue())
        z.writestr('stack.xml', ET.tostring(root, encoding='utf-8', xml_declaration=True))


def ground_project(stack, blocked, entry_px, boss_px, objective_px, gfx, tools):
    if STAGE.exists():
        shutil.rmtree(STAGE)
    with zipfile.ZipFile(R / 'mod_metano_expeditions_pmdo_0812.zip') as z:
        tpl = json.loads(z.read('metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground'))
    o = tpl['Object']; gw, gh = W // 8, H // 8; layers, banks = [], []
    for i, (title, frames, ticks) in enumerate(stack):
        bank = gfx.TileBank(f'{PFX}_{i:02d}_{title.split()[0].upper()}')
        bank.ids[bytes(256)] = (0, 0); bank.data[(0, 0)] = bytes(256)

        def cell(x, y, frames=frames, bank=bank):
            fs = []
            for a in frames:
                f = bank.add(Image.fromarray(a[y*8:y*8+8, x*8:x*8+8]), x, y)
                fs.append(f if f else {'Sheet': bank.name, 'TexLoc': {'X': 0, 'Y': 0}})
            if all(f['TexLoc'] == {'X': 0, 'Y': 0} for f in fs):
                return []
            return [fs[0]] if all(f == fs[0] for f in fs) else fs
        layers.append(gfx.layer(f'{i:02d} {title}', gw, gh, cell, ticks)); banks.append(bank)
    layers.append(gfx.layer(f'{len(layers):02d} Vos elements avant-plan (Top)', gw, gh, draw=4))
    for bank in banks:
        bank.write(STAGE / f'Content/Tile/{bank.name}.tile')
    o.update(Name={'DefaultText': 'Fin Underground Lake - sanctuaire du lac (4:3)', 'LocalTexts': {}}, AssetName=ASSET,
             Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0},
             ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Rendu genere 4:3 reference sur le rip Underground Lake ; lac facon Metano aux '
                     'couleurs exactes du rip sans lisere clair, lueur du lac animee, scintillements Metano natifs, '
                     'gouttes et ronds generes, monolithe sanctuaire au nord. Collisions de base a verifier. Aucune '
                     'sortie ni warp. Biome et portee choisis par l agent.')
    o['obstacles'] = [[{'Bounds': {'X': x*8, 'Y': y*8, 'Width': 8, 'Height': 8}, 'Tags': int(blocked[y, x])}
                       for y in range(gh)] for x in range(gw)]
    mk = lambda n, p: {'EntName': n, 'Direction': 4, 'EntEnabled': True, 'triggerType': 0,
                       'Collider': {'X': p[0], 'Y': p[1], 'Width': 16, 'Height': 16}}
    o['Entities'] = [{'Name': 'Entrees et vos acteurs', 'Visible': True, 'MapChars': [], 'GroundObjects': [], 'Spawners': [],
                      'Markers': [mk('entrance', entry_px), mk('boss', boss_px), mk('objectif', objective_px)]}]
    o['Decorations'] = [{'Name': 'Vos decorations', 'Layer': 2, 'Visible': True, 'Anims': []}]
    tpl['Version'] = '0.8.12.0'
    gfx.save(STAGE / f'Data/Ground/{ASSET}.rsground', json.dumps(tpl, ensure_ascii=False, separators=(',', ':')).encode())
    gfx.save(STAGE / f'Data/Script/{NAMESPACE}/ground/{ASSET}/init.lua',
             f'-- {ASSET} : base d edition, aucun warp.\nlocal {ASSET} = {{}}\nreturn {ASSET}\n'.encode())
    nodes = {}
    for p in sorted((STAGE / 'Content/Tile').glob('*.tile')):
        with p.open('rb') as f:
            nodes[p.stem] = tools.read_node(f)
    (STAGE / 'Content/Tile/index.idx').write_bytes(tools.encode_index(nodes))
    ident = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/meromoonmeri/guilde-treehouse-pmd/' + NAMESPACE)
    (STAGE / 'Mod.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Fin Underground Lake 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : zone de fin de donjon d'Underground Lake (sanctuaire du lac souterrain), generee au format 4:3 (ref. rip Underground Lake), lac facon Metano, lueur, gouttes et ronds animes. Pas une aventure jouable.</Description>
  <Namespace>{NAMESPACE}</Namespace>
  <UUID>{ident}</UUID>
  <Version>1.0.0.0</Version>
  <GameVersion>0.8.12.0</GameVersion>
  <ModType>Quest</ModType>
  <Relationships />
</Header>
''')
    script = (R / 'source/pmdo_cote/INSTALLER.py').read_text()
    needle = '            relative = src.relative_to(source)\n'
    assert needle in script
    script = script.replace(needle, needle + "            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n")
    (STAGE / 'INSTALLER.py').write_text(script)
    shutil.copyfile(HERE / 'README_PACK.md', STAGE / 'README.md')
    shutil.copyfile(HERE / 'README_PACK.md', OUT / 'README.md')
    return {b.name: len(b.data) for b in banks}


def build():
    gfx = loadmod('pmdo_codec', R / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
    v1 = loadmod('esn1', R / 'source/entree_sud_nord_generee_v1/build.py')
    ANIMS = ['eau', 'lueur', 'scintillements', 'gouttes']
    if OUT.exists():
        for d in ['calques', 'animation', 'poses', 'masques', 'review']:
            shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['calques', 'poses', 'masques', 'review'] + [f'animation/{x}' for x in ANIMS]:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    STAGE.parent.mkdir(parents=True, exist_ok=True)
    a = rgb(RAW / 'decor_magenta.png'); f = rgb(RAW / 'sol_complet.png'); ref = rgb(REF)
    assert a.shape[:2] == f.shape[:2] == (SRC[1], SRC[0])
    m, seg = classify(a, f)
    order = ['water', 'sanctuaire', 'sable', 'ombres', 'berge', 'piliers', 'roche']
    ex, cols = down_class(a, m, order)
    water = ex['water']
    layers = {'sol_complet': rgba(down_full(f), ~water)}
    for k in STATIC:
        layers[k] = rgba(cols[k], ex[k])
    q = {}
    for keys, n in PALETTE_GROUPS.values():
        q.update(quantize_group({k: layers[k] for k in keys}, n))
    layers = q
    for k, v in ex.items():
        Image.fromarray((v * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_{k}.png')
    land = np.zeros((H, W), bool)
    for k in STATIC:
        land |= layers[k][..., 3] == 255
    visible = water & ~land
    wf, dist = lake_water(water, visible)
    centres = glow_centres(water)
    lueur = glow_frames(visible, centres)
    glow_any = np.zeros((H, W), bool); glow_core = np.ones((H, W), bool)
    for fr in lueur:
        glow_any |= fr[..., 3] == 255
        glow_core &= (fr[..., :3] == GLOW[0]).all(-1) & (fr[..., 3] == 255)
    free = visible & (dist > 4) & nd.binary_erosion(glow_core, iterations=2)
    fams = BM.sparkle_families(); taken = np.zeros((H, W), bool)
    sf = [np.zeros((H, W, 4), 'uint8') for _ in range(WATER_PHASES)]; sparkles = []
    for fi, (name, frames) in enumerate(fams.items()):
        hh, ww = frames[0].shape[:2]
        for (y, x) in place(free, (hh, ww), 2, 71 + fi, taken, core=8):
            sparkles.append({'famille': name, 'xy': [x, y]})
            for t in range(WATER_PHASES):
                mm = frames[t][..., 3] > 0; sf[t][y:y+hh, x:x+ww][mm] = frames[t][mm]
    for arr in sf:
        arr[~visible] = 0
    poses, pose_pal = sheet_poses(RAW / 'gouttes_ronds_poses.png')
    for name, p in poses.items():
        Image.fromarray(p).save(OUT / 'poses' / f'{PFX}_{name}.png')
    fall_ok = visible & (dist > 6)
    ok = visible & (dist > 20) & ~nd.binary_dilation(glow_any, iterations=10) & ~taken
    for s in range(1, 19):
        ok &= np.roll(fall_ok, s, axis=0)
    cand = np.argwhere(ok); emitters, used = [], []
    for y, x in cand[np.random.default_rng(12).permutation(len(cand))]:
        if all(abs(x - ux) > 56 or abs(y - uy) > 56 for uy, ux in used):
            used.append((y, x)); emitters.append((int(x), int(y), (len(emitters) * 3) % DROP_PHASES))
        if len(emitters) == 8:
            break
    gouttes = drop_frames(poses, emitters, visible)
    anim = {'eau': (wf, WATER_TICKS), 'lueur': (lueur, GLOW_TICKS), 'scintillements': (sf, WATER_TICKS),
            'gouttes': (gouttes, DROP_TICKS)}
    order_names = ['eau', 'lueur', 'scintillements', 'gouttes', 'sol_complet'] + STATIC
    stack_named, layer_list = [], []
    for i, nm in enumerate(order_names):
        if nm in anim:
            frames, ticks = anim[nm]
            for t, fr in enumerate(frames):
                Image.fromarray(fr).save(OUT / 'animation' / nm / f'{PFX}_{i:02d}_{nm}_f{t:02d}.png')
            layer_list.append({'file': f'animation/{nm}/{PFX}_{i:02d}_{nm}_fNN.png', 'phases': len(frames), 'ticks': ticks})
        else:
            frames, ticks = [layers[nm]], 60
            Image.fromarray(layers[nm]).save(OUT / 'calques' / f'{PFX}_{i:02d}_{nm}.png')
            layer_list.append({'file': f'calques/{PFX}_{i:02d}_{nm}.png', 'phases': 1, 'ticks': 60})
        stack_named.append((nm, frames, ticks))
    walk_px = (layers['sable'][..., 3] == 255) | (layers['ombres'][..., 3] == 255)
    Image.fromarray((walk_px * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_praticable.png')
    blocked = cell_grid(~walk_px); gh_, gw_ = blocked.shape
    pxs = np.nonzero(walk_px[H - 8])[0]; med = int(np.median(pxs)) // 8
    ecol = min((c for c in range(gw_ - 1) if not blocked[gh_ - 2:, c:c + 2].any()), key=lambda c: abs(c - med))
    entry_px = [ecol * 8, H - 16]
    free_c = lambda cx, cy: 0 <= cx < gw_ - 1 and 0 <= cy < gh_ - 1 and not blocked[cy:cy + 2, cx:cx + 2].any()
    tgt = (W // 16 - 1, 42)
    boss_c = min(((cx, cy) for cy in range(gh_) for cx in range(gw_) if free_c(cx, cy)),
                 key=lambda c: (c[0] - tgt[0]) ** 2 + (c[1] - tgt[1]) ** 2)
    boss_px = [boss_c[0] * 8, boss_c[1] * 8]
    mid = W // 16
    cands = [(cx, cy) for cy in range(gh_) for cx in range(mid - 5, mid + 5) if free_c(cx, cy)]
    top_cy = min(cy for _, cy in cands)
    obj_c = min((c for c in cands if c[1] <= top_cy + 1), key=lambda c: abs(c[0] - (mid - 1)))
    objective_px = [obj_c[0] * 8, obj_c[1] * 8]
    reach_boss, explored = v1.reachable(blocked, (entry_px[1] // 8, entry_px[0] // 8), (boss_c[1], boss_c[0]))
    reach_obj, _ = v1.reachable(blocked, (entry_px[1] // 8, entry_px[0] // 8), (obj_c[1], obj_c[0]))
    assert reach_boss and reach_obj, 'pas de chemin 16x16'
    reach = bool(reach_boss and reach_obj)

    def scene(tick):
        im = Image.new('RGBA', (W, H))
        for _, frames, ticks in stack_named:
            im.alpha_composite(Image.fromarray(frames[(tick // ticks) % len(frames)]))
        return im
    step = 5
    scenes = [scene(t) for t in range(0, LOOP_TICKS, step)]
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_t000.png')
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_animee.webp', save_all=True, append_images=scenes[1:],
                   duration=round(step * 1000 / 60), loop=0, lossless=True)
    col = scenes[0].copy(); ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    for y, x in zip(*np.nonzero(blocked)):
        dr.rectangle([x*8, y*8, x*8+7, y*8+7], fill=(220, 40, 40, 90))
    for (qx, qy), c in ((entry_px, (255, 230, 40, 255)), (boss_px, (255, 60, 220, 255)), (objective_px, (60, 220, 255, 255))):
        dr.rectangle([qx, qy, qx + 15, qy + 15], outline=c, width=2)
    col.alpha_composite(ov); col.save(OUT / 'review' / f'{PFX}_collisions_marqueurs.png')
    cell_s = 36 * 2 + 8; sheet = Image.new('RGBA', (5 * cell_s + 8, 2 * cell_s + 8), (*WPAL['surface'], 255))
    for i, name in enumerate(POSE_WIN):
        p = poses[name]; im = Image.fromarray(p); im = im.resize((im.width * 2, im.height * 2), Image.Resampling.NEAREST)
        cx0 = 8 + (i % 5) * cell_s; cy0 = 8 + (i // 5) * cell_s
        sheet.alpha_composite(im, (cx0 + (cell_s - 8 - im.width) // 2, cy0 + (cell_s - 8 - im.height) // 2))
    sheet.save(OUT / 'review' / f'{PFX}_planche_poses.png')
    write_ora(OUT / f'{PFX}_fin_underground_lake_calques.ora',
              {f'{i:02d}_{t}' + ('_f00' if len(fr) > 1 else ''): fr[0] for i, (t, fr, _) in enumerate(stack_named)})
    counts = ground_project([(t.replace('_', ' ') + (f' {len(fr)} phases' if len(fr) > 1 else ''), fr, tk)
                             for t, fr, tk in stack_named], blocked, entry_px, boss_px, objective_px, gfx, tools)
    fid = fidelity(a, ref)
    final_fid = {}
    for k, nm in (('sable', 'sable'), ('roche', 'roche'), ('roche', 'piliers'), ('roche', 'sanctuaire')):
        lay = layers[nm]; px = lay[lay[..., 3] == 255][:, :3].astype(float)
        sel = materials(px.reshape(-1, 1, 3))[k][:, 0]
        px = px[sel] if sel.sum() > 50 else px
        final_fid[nm] = {'matiere': k, 'rgb': [round(float(v), 1) for v in px.mean(0)],
                         'distance_rip': round(float(np.linalg.norm(px.mean(0) - np.array(fid[k]['rip_rgb']))), 1)}
    zone_parois = np.zeros(a.shape[:2], bool)
    zone_parois[250:850, :80] = zone_parois[250:850, 1120:] = zone_parois[:60, 200:450] = zone_parois[:60, 750:1000] = True
    err_parois = round(float(np.abs(a.astype(float) - f.astype(float))[zone_parois].mean()), 2)
    manifest = {
        'lot': 'fin_underground_lake_v2', 'prefix': PFX, 'format': '4:3 vaste', 'type': 'fin de donjon',
        'size_px': [W, H], 'grid_8px': [W // 8, H // 8],
        'base': 'branche de session (EUL1 pour l eau, la lueur, les gouttes et les bruts sol_complet/poses ; EWC2/EWC1/ESN1 pour les utilitaires) ; aucun emprunt aux branches soeurs',
        'biome': 'fin d Underground Lake (sanctuaire du lac souterrain, prolonge EUL1), biome et portee choisis par l agent (« alors ........... »), a confirmer',
        'method': 'textures canoniques = rendu genere REFERENCE : rip passe au generateur ; lac en magenta sur le decor, '
                  'monolithe sanctuaire au nord (sans bouche sombre), sol complet et planche de gouttes d EUL1 reutilises',
        'reference_da': {'file': REF.name, 'sha256': sha(REF)},
        'generation': GEN,
        'raw_inputs': [{'file': f'{LOT}/bruts/{g["file"]}', 'sha256': sha(RAW / g['file']),
                        'size': list(Image.open(RAW / g['file']).size)} for g in GEN],
        'sol_complet': {'ecart_moyen_parois': err_parois, 'recalage_px': [0, 0],
                        'note': 'sol complet d EUL1 reutilise (meme sha256) : parois gardees au pixel pres hors zone nord'},
        'segmentation_mesures': seg,
        'fidelite_rip': {'methode': 'moyenne RGB par matiere, meme classifieur pixel sur le rip et sur le brut ; distance euclidienne ; seuil 20',
                         'brut': fid, 'calques_finaux': final_fid,
                         'eau_et_lueur': 'couleurs EXACTES du rip (test : sous-ensemble des 69 couleurs du rip)'},
        'normalization': {'scale': JM.SCALE, 'scaled': [JM.SCALED_W, H], 'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
                          'methode': 'moyenne ponderee par classe (BOX), attribution exclusive par poids maximal',
                          'palettes': {g: {'calques': k, 'couleurs': n} for g, (k, n) in PALETTE_GROUPS.items()}},
        'layers': layer_list,
        'water': {'style': 'structure de water_phases d EWC2 (bande contre rive, frange dentelee, aplat ; aucun lisere clair), couleurs exactes du rip',
                  'couleurs': {k: list(v) for k, v in WPAL.items()}, 'phases': WATER_PHASES, 'frame_length_ticks': WATER_TICKS},
        'lueur': {'couleurs': [list(c) for c in GLOW], 'anneau_px': GLOW_RING_PX, 'respiration': GLOW_BREATH,
                  'ondulation': GLOW_WOBBLE, 'centres': [list(c) for c in centres], 'phases': GLOW_PHASES,
                  'frame_length_ticks': GLOW_TICKS, 'origine': 'couleurs exactes du rip ; animation creee par nous'},
        'sparkles': {'source': 'source/eau_metano/natifs/Metano_Town_River_Sparkles.tile',
                     'phases': WATER_PHASES, 'frame_length_ticks': WATER_TICKS, 'placements': sparkles,
                     'zone': 'coeur de la lueur uniquement'},
        'gouttes': {'source': f'{LOT}/bruts/gouttes_ronds_poses.png', 'reduction': POSE_K, 'couverture_min': POSE_COV,
                    'poses': {k: list(v) for k, v in POSE_WIN.items()}, 'palette': [[int(x) for x in c] for c in pose_pal],
                    'emetteurs': [list(e) for e in emitters], 'phases': DROP_PHASES, 'frame_length_ticks': DROP_TICKS,
                    'origine': 'planche generee d EUL1 reutilisee, trajectoires et cadence creees par nous'},
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'entry_px': entry_px, 'boss_px': boss_px, 'objective_px': objective_px, 'path_found_16x16': reach,
                   'path_to_boss': reach_boss, 'path_to_objective': reach_obj, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si > 25 % hors sable praticable (sable + ombres)',
                   'boss': 'case 2 x 2 libre au centre de la plateforme de sable',
                   'objectif': 'case 2 x 2 libre la plus haute de la chaussee centrale (+-40 px), au pied du monolithe sanctuaire',
                   'fin': 'aucune sortie, aucun warp, pas de donjon_seuil ; le bord nord et les flancs sont bloques'},
        'pmdo': {'target': '0.8.12', 'asset': ASSET, 'namespace': NAMESPACE, 'tiles_per_bank': counts, 'banks': list(counts),
                 'runtime_tested': False, 'warp': 'aucun'},
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    print(json.dumps({'entry': entry_px, 'boss': boss_px, 'objectif': objective_px, 'blocked': int(blocked.sum()),
                      'walkable': int((~blocked).sum()), 'seg': seg,
                      'px': {k: int(v.sum()) for k, v in ex.items()},
                      'fidelite': {k: v['distance'] for k, v in fid.items()},
                      'final': {k: v['distance_rip'] for k, v in final_fid.items()}, 'tiles': sum(counts.values())}, indent=1))


if __name__ == '__main__':
    build()
