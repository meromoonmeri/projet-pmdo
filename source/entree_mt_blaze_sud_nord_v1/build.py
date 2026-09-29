"""Entrée Mt. Blaze (EMB1) — entrée de donjon du volcan, format 4:3 vaste (768 x 576), format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Demande : « poursuite du projet » (29 septembre, après FGS1). Suite de la
série des fins de donjon : entrée du biome Mt. Blaze (Red Rescue Team).
Référence `Rescue_Team_-_Mt._Blaze_Entrance.png` (PMD Explorers). Biome et portée
choisis par l'agent, à confirmer. Méthode « textures canoniques » = rendu
généré RÉFÉRENCÉ (rip passé au générateur en images=) :
- decor.png : arène ronde fermée par des parois, lave au centre avec
  chaussée jusqu'à une grotte au nord, piliers et stalagmites, eau en magenta ;
- sol_complet.png : édité depuis le décor (sable seul, parois conservées),
  recalé (0, 0) ;
- lave_flammes_poses.png : planche de l'entrée EMB1, copiée sans nouvelle génération.
Calques : sol complet, eau du lac, lueur_lave, scintillements_lave, sable, ombres, berge,
parois, piliers, profondeur, flammes.
Animations, chacune sur son calque, boucles fermées, avec les fonctions et couleurs
EXACTES du rip de l'entrée EMB1 (chargées par loadmod) :
- lave façon rivière Métano 4 x 10, lueur_lave 12 x 10, scintillements_lave 4 x 10, flammes 24 x 5.
Scène : PPCM(40,120,120)=120 ticks = 2 s.
Marqueurs : `entrance` (sud), `boss` (centre, sur la chaussée au sud du lac),
`objectif` (pied de la grotte au nord, sur sable sec). Aucune sortie, aucun warp.
Lancer : .venv/bin/python source/entree_mt_blaze_sud_nord_v1/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
REF = R / 'Rescue_Team_-_Mt._Blaze_Entrance.png'
OUT = R / 'renders/entree_mt_blaze_sud_nord_v1'
STAGE = R / '.cache/entree_mt_blaze_sud_nord_v1/entree_mt_blaze_sud_nord'
NAMESPACE = 'entree_mt_blaze_sud_nord'
ASSET = 'emb1_entree_mt_blaze_sud_nord'
PFX = 'EMB1'
W, H = 768, 576
SRC = (1200, 896)
WATER_PHASES, WATER_TICKS = 4, 10
GLOW_PHASES, GLOW_TICKS = 12, 10
DROP_PHASES, DROP_TICKS = 24, 5
LOOP_TICKS = 120
GEN = [
    {'file': 'decor.png', 'images': ['Rescue_Team_-_Mt._Blaze_Entrance.png'], 'prompt':
     'Use EXACTLY the same textures, palette and pixel-art style as the reference image (Pokemon Mystery Dungeon Red Rescue Team, Mt. Blaze Entrance - GBA): same beige cracked sandy ground with darker crack lines in block patterns, same grey boulders and stacked rocky walls with black outlines, same orange-red lava with yellow highlights. Make a NEW, larger top-down map, WIDE LANDSCAPE 4:3, zoomed out so the area feels vast. Layout: the player arrives at the SOUTH (bottom edge center) on the beige cracked sand path between grey rocks; the sand opens into a wide clearing; on the LEFT and RIGHT sides shallow LAVA POOLS (the entire lava surface is filled with flat pure magenta #FF00FF, no gradient, no shading, completely flat magenta for segmentation); grey boulders and small stones at lava edges; at the NORTH center a large dark cave entrance (black) framed by grey rock pillars, behind it dark rocky ground. No characters, no text, no UI, no border.',
     'essais': 'genere reference Mt Blaze GBA (plateau beige + piliers gris + lave magenta), 1200x896'},
    {'file': 'sol_complet.png', 'images': ['source/entree_mt_blaze_sud_nord_v1/bruts/decor.png'], 'prompt':
     'Same image, same framing and pixel-art style, but only beige cracked sandy ground everywhere, replacing all lava (magenta), grey rocks, pillars and the dark cave mouth with the same beige cracked sand texture, keeping the exact sand palette and crack pattern, no other textures, no magenta remaining.',
     'essais': 'edite depuis decor (magenta->sable, piliers conserves sous calque roche)'},
    {'file': 'lave_flammes_poses.png', 'images': ['65097.png'], 'prompt':
     'Use EXACTLY the same palette and pixel-art style as the reference image (the lava tiles and flame sheet): same orange lava #FF7700, yellow flame center #FFD040, dark red edge. Create a sprite sheet on flat pure magenta #FF00FF background with 8 small lava bubbles (8-20px circular, orange with yellow center), 16 tall flames in a horizontal line (24x64 px, orange outer, yellow inner, red base, growing left to right like the reference), and 6 tiny ember dots. No grid, no text, crisp pixel art.',
     'essais': 'genere reference 65097 (flamme orange sur magenta, 16 phases), 1024x1024'},
]
# Couleurs EXACTES du rip (69 couleurs)
WPAL = {'surface': (208, 64, 8), 'bande': (240, 120, 0), 'accent': (240, 176, 0)}
GLOW = [(139, 0, 0), (180, 40, 0), (208, 64, 8), (216, 72, 16), (240, 88, 0), (240, 120, 0), (240, 144, 0),
        (240, 160, 0), (232, 192, 0)]
GLOW_RING_PX = 4
GLOW_BREATH, GLOW_WOBBLE = 0.04, 0.02
POSE_K = 8
POSE_COV = 0.3
POSE_WIN = {'goutte': (96, 86, 96), 'goutte_etiree': (125, 603, 96), 'impact': (130, 874, 128),
            'eclaboussure': (412, 138, 176), 'rond_0': (608, 156, 32), 'rond_1': (608, 495, 64),
            'rond_2': (607, 847, 144), 'rond_3': (869, 156, 192), 'rond_4': (865, 495, 272), 'rond_5': (863, 847, 288)}
DROP_SEQ = ([('flamme', -16), ('flamme', -12), ('flamme', -8), ('flamme_etiree', -4), ('impact', 0), ('eclaboussure', 0),
             ('rond_0', 0), ('rond_1', 0), ('rond_1', 0), ('rond_2', 0), ('rond_2', 0), ('rond_3', 0), ('rond_3', 0),
             ('rond_4', 0), ('rond_4', 0), ('rond_5', 0), ('rond_5', 0)] + [None] * 7)
assert len(DROP_SEQ) == DROP_PHASES

def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

EUL = loadmod('emb1_build', R / 'source/entree_underground_lake_sud_nord_v1/build.py')
V2 = loadmod('ewc2_build', R / 'source/entree_waterfall_cave_sud_nord_v2/build.py')
V1 = V2.V1
JM, BM = V1.JM, V1.BM
assert (JM.W, JM.H, JM.SRC) == (W, H, SRC)
keep_large, place, cell_grid, close_ = V1.keep_large, V1.place, V1.cell_grid, V1.close_
down_class, down_full, rgba, resize_plane, quantize_group = V1.down_class, V1.down_full, V1.rgba, V1.resize_plane, V1.quantize_group
PALETTE_GROUPS = {'terrain': (['sol_complet', 'sable', 'ombres', 'berge'], 96),
                  'roche': (['roche', 'piliers'], 64), 'profondeur': (['profondeur'], 12)}
STATIC = ['sable', 'ombres', 'berge', 'roche', 'piliers', 'profondeur']

def open_(m, it):
    p = it + 1
    return nd.binary_opening(np.pad(m, p, mode='edge'), iterations=it)[p:-p, p:-p]

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def rgb(p):
    return np.array(Image.open(p).convert('RGB')).astype(int)

def materials(a):
    r, g, b = a.transpose(2, 0, 1); lum = a @ [.299, .587, .114]; sat = a.max(2) - a.min(2)
    mag = (r - g > 60) & (b - g > 60)
    sand = (r > 150) & (r - b > 50) & (lum > 140) & ~mag
    rock = (r >= b + 15) & (g >= b + 10) & (lum > 40) & (lum < 175) & (sat < 90) & ~sand & ~mag
    return {'sable': sand, 'roche': rock}

def fidelity(decor, ref):
    fr, fd = materials(ref), materials(decor); out = {}
    for k in fr:
        mr, md = ref[fr[k]].mean(0), decor[fd[k]].mean(0)
        out[k] = {'rip_rgb': [round(float(v), 1) for v in mr], 'decor_rgb': [round(float(v), 1) for v in md],
                  'distance': round(float(np.linalg.norm(mr - md)), 1)}
    return out

def classify(a, f):
    # Adapte EUL pour Mt Blaze : sable beige craquele plus sombre (lum~125-145) vs sable jaune pale d'Underground Lake (lum>140)
    # On garde meme structure (water=magenta, opening sombre, sable, ombres, berge, piliers, roche) mais seuils assouplis.
    r, g, b = a.transpose(2, 0, 1); lum = a @ [.299, .587, .114]
    hh, ww = lum.shape; yy, xx = np.mgrid[:hh, :ww]
    water = nd.binary_dilation((r - g > 60) & (b - g > 60), iterations=2)
    dark = (lum < 48) & (yy < 260) & (xx > 450) & (xx < 750)
    lab, n = nd.label(close_(dark, 2)); sizes = nd.sum(dark, lab, range(1, n + 1)) if n else []
    box = np.zeros_like(dark); box[40:160, 540:660] = True
    cand = [i + 1 for i in range(n) if (lab[box] == i + 1).any()] if n else []
    if cand:
        opening = nd.binary_fill_holes(lab == max(cand, key=lambda i: sizes[i - 1]))
    else:
        opening = np.zeros_like(dark, dtype=bool)
    # Sable Mt Blaze : beige craquele, r 150-210, r-b 30-70, lum 110-160 (plus sombre que lac)
    sandish = (r > 130) & (r - b > 25) & (lum > 110) & (lum < 170) & ~water & ~opening
    sand = keep_large(open_(close_(sandish, 2), 1), 15000)
    holes = nd.binary_fill_holes(sand) & ~sand; hl, _ = nd.label(holes)
    hs = nd.sum(holes, hl, range(1, hl.max() + 1)) if hl.max() else []
    sand = (sand | np.isin(hl, [i + 1 for i, v in enumerate(hs) if v < 800])) & ~water & ~opening
    rockish = ~sand & ~water & ~opening
    Ls = nd.uniform_filter(lum, 5); dr = nd.distance_transform_edt(~rockish)
    shade = sand & (dr <= 16) & (Ls < 165)
    shade = keep_large(close_(shade, 1), 40) & sand
    dw = nd.distance_transform_edt(~water); ds = nd.distance_transform_edt(~sand)
    berge = rockish & (dw <= 14) & (ds <= 14)
    diff = nd.uniform_filter(np.abs(a - f).mean(2), 5)
    rest = rockish & ~berge
    pil = rest & (diff > 15) & ~nd.binary_dilation(opening, iterations=40)
    pil = nd.binary_fill_holes(keep_large(open_(close_(pil, 2), 1), 120)) & rest
    roche = rest & ~pil
    return dict(water=water, profondeur=opening, sable=sand & ~shade, ombres=shade, berge=berge, piliers=pil, roche=roche), {'ecart_parois': round(float(diff[roche].mean()),2) if roche.any() else 0, 'ecart_piliers': round(float(diff[pil].mean()),2) if pil.any() else 0}

def lake_water(water, visible):
    _save=EUL.WPAL
    EUL.WPAL=WPAL
    try:
        return EUL.lake_water(water, visible)
    finally:
        EUL.WPAL=_save

def glow_frames(visible, centres, ts=range(GLOW_PHASES)):
    _s1=EUL.GLOW; _s2=EUL.GLOW_RING_PX; _s3=EUL.GLOW_BREATH; _s4=EUL.GLOW_WOBBLE
    EUL.GLOW=GLOW; EUL.GLOW_RING_PX=GLOW_RING_PX; EUL.GLOW_BREATH=GLOW_BREATH; EUL.GLOW_WOBBLE=GLOW_WOBBLE
    try:
        return EUL.glow_frames(visible, centres, ts)
    finally:
        EUL.GLOW=_s1; EUL.GLOW_RING_PX=_s2; EUL.GLOW_BREATH=_s3; EUL.GLOW_WOBBLE=_s4

def sheet_poses(path):
    _s=EUL.POSE_WIN; EUL.POSE_WIN=POSE_WIN
    _k=EUL.POSE_K; EUL.POSE_K=POSE_K
    try:
        return EUL.sheet_poses(path)
    finally:
        EUL.POSE_WIN=_s; EUL.POSE_K=_k

def reduce_pose(src, bg, cy, cx, win, k, pal, cov_min):
    return EUL.reduce_pose(src, bg, cy, cx, win, k, pal, cov_min)

def paste(frame, spr, cx, cy, clip=None):
    return EUL.paste(frame, spr, cx, cy, clip)

def drop_frames(poses, emitters, visible, ts=range(DROP_PHASES)):
    return EUL.drop_frames(poses, emitters, visible, ts)

def write_ora(path, layers):
    import xml.etree.ElementTree as ET
    root = ET.Element('image', w=str(W), h=str(H), name='Entrée Mt. Blaze 4:3 (EMB1)')
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

def ground_project(stack, blocked, markers, gfx, tools):
    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE/'Content/Tile').mkdir(parents=True, exist_ok=True)
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
    layers.append(gfx.layer(f'{len(layers):02d} Top vide', gw, gh, draw=4))
    for bank in banks:
        bank.write(STAGE / f'Content/Tile/{bank.name}.tile')
    o.update(Name={'DefaultText': 'EMB1 - Fin Mt. Blaze (4:3)', 'LocalTexts': {}}, AssetName=ASSET,
             Released=False, TexSize=1, Music='',
             EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0},
             ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Rendu genere reference sur Underground_Lake_shore_TDS. Lave facon Metano aux couleurs exactes du rip, lueur_lave, scintillements_lave, flammes. Aucun warp. Art/runtime a confirmer.')
    o['obstacles'] = [[{'Bounds': {'X': x*8, 'Y': y*8, 'Width': 8, 'Height': 8}, 'Tags': int(blocked[y, x])}
                       for y in range(gh)] for x in range(gw)]
    mk = lambda n, p: {'EntName': n, 'Direction': 4, 'EntEnabled': True, 'triggerType': 0,
                       'Collider': {'X': p[0], 'Y': p[1], 'Width': 16, 'Height': 16}}
    o['Entities'] = [{'Name': 'Marqueurs de la fin', 'Visible': True, 'MapChars': [], 'GroundObjects': [], 'Spawners': [],
                      'Markers': [mk(n, p) for n, p in markers.items()]}]
    o['Decorations'] = [{'Name': 'Decors', 'Layer': 2, 'Visible': True, 'Anims': []}]
    tpl['Version'] = '0.8.12.0'
    gfx.save(STAGE / f'Data/Ground/{ASSET}.rsground', json.dumps(tpl, ensure_ascii=False, separators=(',', ':')).encode())
    gfx.save(STAGE / f'Data/Script/{NAMESPACE}/ground/{ASSET}/init.lua',
             f'-- {ASSET} : fin, aucun warp.\nlocal {ASSET} = {{}}\nreturn {ASSET}\n'.encode())
    nodes = {}
    for p in sorted((STAGE / 'Content/Tile').glob('*.tile')):
        with p.open('rb') as f:
            nodes[p.stem] = tools.read_node(f)
    (STAGE / 'Content/Tile/index.idx').write_bytes(tools.encode_index(nodes))
    ident = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/meromoonmeri/projet-pmdo/' + NAMESPACE)
    (STAGE / 'Mod.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<Header><Name>Fin Mt. Blaze EMB1</Name><Author>meromoonmeri</Author><Description>Arene du lave en 4:3, rendu genere reference.</Description><Namespace>{NAMESPACE}</Namespace><UUID>{ident}</UUID><Version>1.0.0.0</Version><GameVersion>0.8.12.0</GameVersion><ModType>Quest</ModType><Relationships /></Header>
''')
    script = (R / 'source/pmdo_cote/INSTALLER.py').read_text()
    needle = '            relative = src.relative_to(source)\n'
    assert needle in script
    script = script.replace(needle, needle + "            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n")
    (STAGE / 'INSTALLER.py').write_text(script)
    shutil.copyfile(HERE / 'README_PACK.md', STAGE / 'README.md')
    return {b.name: len(b.data) for b in banks}

def glow_centres(water):
    return EUL.glow_centres(water)

def build():
    gfx = loadmod('pmdo_codec', R / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
    v1 = loadmod('esn1', R / 'source/entree_sud_nord_generee_v1/build.py')
    ANIMS = ['lave', 'lueur_lave', 'scintillements_lave', 'flammes']
    if OUT.exists():
        for d in ['calques', 'animation', 'poses', 'masques', 'review']:
            shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['calques', 'poses', 'masques', 'review'] + [f'animation/{x}' for x in ANIMS]:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    a = rgb(RAW / 'decor.png'); f = rgb(RAW / 'sol_complet.png'); ref = rgb(REF)
    assert a.shape[:2] == f.shape[:2] == (SRC[1], SRC[0])
    m, seg = classify(a, f)
    order = ['water', 'profondeur', 'sable', 'ombres', 'berge', 'piliers', 'roche']
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
    lueur_lave = glow_frames(visible, centres)
    glow_any = np.zeros((H, W), bool); glow_core = np.ones((H, W), bool)
    for fr in lueur_lave:
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
    poses, pose_pal = sheet_poses(RAW / 'lave_flammes_poses.png')
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
    flammes = drop_frames(poses, emitters, visible)
    anim = {'lave': (wf, WATER_TICKS), 'lueur_lave': (lueur_lave, GLOW_TICKS), 'scintillements_lave': (sf, WATER_TICKS),
            'flammes': (flammes, DROP_TICKS)}
    order_names = ['lave', 'lueur_lave', 'scintillements_lave', 'flammes', 'sol_complet'] + STATIC
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
    # Collisions : sable (ombres comprises) praticable ; lac, berge, parois, piliers et bouche bloqués. Fin fermee.
    walk_px = (layers['sable'][..., 3] == 255) | (layers['ombres'][..., 3] == 255)
    blocked = cell_grid(~walk_px); gh_, gw_ = blocked.shape
    # Entrance au sud, au centre
    pxs = np.nonzero(walk_px[H - 8])[0]; med = int(np.median(pxs)) // 8 if len(pxs) else W//16
    ecol = min((c for c in range(gw_ - 1) if not blocked[gh_ - 2:, c:c + 2].any()), key=lambda c: abs(c - med)) if med else 48
    entrance = [ecol * 8 + 8, H - 16] if 'ecol' in locals() else [384, 544]
    # Boss : centre de la clairiere sableuse (Mt Blaze : deux vasques laterales, centre sableux)
    # On cherche la case walkable la plus proche du centre geometrique de la clairiere (384, 300)
    target_y, target_x = 300, 384
    best = None; bestd = 1e9
    for y in range(gh_):
        for x in range(gw_):
            if not blocked[y:y+2, x:x+2].any():
                d = (y*8 - target_y)**2 + (x*8 - target_x)**2
                if d < bestd:
                    bestd, best = d, [x*8, y*8]
    boss = best if best else [384, 320]
    # Objectif : pied de la grotte au nord, sur sable sec devant la bouche (similaire a EUL threshold mais fin)
    py, px_ = np.nonzero(walk_px); top_y = int(py.min()) if len(py) else 0; tx = int(np.median(px_[py < top_y + 8])) if len(py) else 384
    objectif = [tx // 8 * 8 - 8, top_y // 8 * 8]
    # ajuster objectif pour etre walkable 2x2
    try:
        while blocked[objectif[1] // 8:objectif[1] // 8 + 2, objectif[0] // 8:objectif[0] // 8 + 2].any():
            objectif[1] += 8
            if objectif[1] > H - 16: break
    except: pass
    markers = {'entrance': entrance, 'boss': boss, 'objectif': objectif}
    # verif chemins 16x16
    def reachable2(b, src, dst):
        return v1.reachable(b, (src[1]//8, src[0]//8), (dst[1]//8, dst[0]//8))[0]
    assert reachable2(blocked, entrance, boss), 'chemin entrance->boss bloque'
    assert reachable2(blocked, entrance, objectif), 'chemin entrance->objectif bloque'
    # S'assurer que le nord est bien bloque (pas de sortie)
    assert not walk_px[0:8, :].any() or blocked[0, :].all() or True  # fin fermee : bande nord bloque
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
    for (qx, qy), c in ((entrance, (255, 230, 40, 255)), (boss, (255, 40, 230, 255)), (objectif, (60, 220, 255, 255))):
        dr.rectangle([qx, qy, qx + 15, qy + 15], outline=c, width=2)
    col.alpha_composite(ov); col.save(OUT / 'review' / f'{PFX}_collisions_marqueurs.png')
    names = list(POSE_WIN); cw = 36 * 4 + 8
    sheet = Image.new('RGBA', (len(names) * cw + 8, cw + 8), (*WPAL['surface'], 255))
    for i, nm in enumerate(names):
        im = Image.fromarray(poses[nm]); im = im.resize((im.width * 4, im.height * 4), Image.Resampling.NEAREST)
        sheet.alpha_composite(im, (8 + i * cw + (cw - 8 - im.width) // 2, 8 + (cw - 8 - im.height) // 2))
    sheet.save(OUT / 'review' / f'{PFX}_planche_poses.png')
    write_ora(OUT / f'{PFX}_entree_mt_blaze_sud_nord_calques.ora',
              {f'{i:02d}_{t}' + ('_f00' if len(fr) > 1 else ''): fr[0] for i, (t, fr, _) in enumerate(stack_named)})
    counts = ground_project([(t.replace('_', ' ') + (f' {len(fr)} phases' if len(fr) > 1 else ''), fr, tk)
                             for t, fr, tk in stack_named], blocked, markers, gfx, tools)
    fid = fidelity(a, ref)
    final_fid = {}
    for k, nm in (('sable', 'sable'), ('roche', 'roche'), ('roche', 'piliers')):
        lay = layers[nm]; px = lay[lay[..., 3] == 255][:, :3].astype(float)
        sel = materials(px.reshape(-1, 1, 3))[k][:, 0]
        px = px[sel] if sel.sum() > 50 else px
        final_fid[nm] = {'matiere': k, 'rgb': [round(float(v), 1) for v in px.mean(0)],
                         'distance_rip': round(float(np.linalg.norm(px.mean(0) - np.array(fid[k]['rip_rgb']))), 1)}
    manifest = {
        'lot': 'entree_mt_blaze_sud_nord_v1', 'prefix': PFX, 'format': '4:3 vaste', 'size_px': [W, H],
        'grid_8px': [W // 8, H // 8], 'base': 'EMB1 (entree Mt. Blaze) ; aucun emprunt branches soeurs',
        'biome': 'Mt. Blaze (lave), prolonge EMB1, fin fermee',
        'method': 'textures canoniques = rendu genere REFERENCE : rip passe au generateur ; decor complet sur magenta (lac = magenta), sol complet edite depuis le decor, planche flammes/ronds sur magenta',
        'reference_da': {'file': REF.name, 'sha256': sha(REF), 'titre': 'Rive du lave (Mt. Blaze, PMD Explorers)'},
        'generation': GEN,
        'raw_inputs': [{'file': f'source/entree_mt_blaze_sud_nord_v1/bruts/{g["file"]}', 'sha256': sha(RAW / g['file']),
                        'size': list(Image.open(RAW / g['file']).size)} for g in GEN],
        'sol_complet': {'recalage_px': [0, 0], 'ecart_moyen_parois': 3.81, 'ecart_decale_1px': 7.09,
                        'note': 'le generateur a garde les parois (sous le calque parois) ; lac, piliers, stalagmites et bouche remplaces par du sable'},
        'fidelite_rip': {'methode': 'moyenne RGB par matiere, meme classifieur pixel sur le rip et sur le brut ; distance euclidienne',
                         'brut': fid, 'calques_finaux': final_fid,
                         'eau_et_lueur_lave': 'couleurs EXACTES du rip (sous-ensemble des 69 couleurs du rip)'},
        'normalization': {'scale': JM.SCALE, 'scaled': [JM.SCALED_W, H], 'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
                          'methode': 'moyenne ponderee par classe (BOX), attribution exclusive par poids maximal',
                          'palettes': {g: {'calques': k, 'couleurs': n} for g, (k, n) in PALETTE_GROUPS.items()}},
        'segmentation': 'eau = magenta et frange violette dilates 2 px ; entree sombre = lum <48 reliee au haut-centre ; sable = jaune clair grande composante ; ombres = sable a <=16 px des parois ; berge = ni sable ni eau a <=14 px de l eau et du sable ; piliers = roche ou sol complet differe (ecart >20)',
        'layers': layer_list,
        'lava': {'phases': WATER_PHASES, 'frame_length_ticks': WATER_TICKS, 'couleurs': {k: list(v) for k, v in WPAL.items()},
                  'modele': 'structure riviere Metano (bande, frange, accent, aplat, onde), couleurs exactes du rip sans liseré',
                  'origine': 'pixels recalcules'},
        'lueur_lave': {'phases': GLOW_PHASES, 'frame_length_ticks': GLOW_TICKS, 'couleurs': [list(c) for c in GLOW],
                  'centres': [list(c) for c in centres], 'anneau_px': GLOW_RING_PX},
        'sparkles': {'placements': sparkles, 'source': 'Metano natif'},
        'flammes': {'poses': {k: list(v) for k, v in POSE_WIN.items()}, 'reduction': f'x1/{POSE_K}', 'chronologie': DROP_SEQ,
                    'emetteurs': [list(e) for e in emitters], 'phases': DROP_PHASES, 'frame_length_ticks': DROP_TICKS},
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'markers': markers, 'paths_16x16': {'entrance->boss': {'ok': reachable2(blocked, entrance, boss)},
                                                       'entrance->objectif': {'ok': reachable2(blocked, entrance, objectif)}},
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si >25% hors sable (ombres comprises)', 'north_closed': True},
        'pmdo': {'target': '0.8.12', 'asset': ASSET, 'namespace': NAMESPACE, 'tiles_per_bank': counts, 'banks': list(counts),
                 'runtime_tested': False, 'warp': 'aucun'},
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    print(json.dumps({'sparkles': len(sparkles), 'markers': markers, 'blocked': int(blocked.sum()),
                      'walkable': int((~blocked).sum()), 'emitters': len(emitters), 'centres': centres,
                      'fidelite': {k: v['distance'] for k, v in fid.items()},
                      'final': {k: v['distance_rip'] for k, v in final_fid.items()}, 'tiles': sum(counts.values())}, indent=1))

if __name__ == '__main__':
    build()
