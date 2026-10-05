"""Fin Mystifying Forest V3 (FMF3) — sanctuaire de la forêt mystique, format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Demande : « alors ........... » (3 octobre, après FUL2) : dernière des fins de donjon de la série d'entrées dans l'ordre
du mod, prolongeant l'entrée EMF1 (Mystifying Forest). Biome et portée choisis par l'agent, à confirmer. Préfixe FMF3
(FMF1 et FMF2 sont pris sur une branche sœur non fusionnée).
Référence `Mystifying_Forest_entrance_TDS.png` (PMD Explorers). Méthode « textures canoniques » = rendu généré RÉFÉRENCÉ
(rip passé au générateur en images=) :
- decor_magenta.png : clairière fermée 4:3 (1200 x 896), arrivée au sud sur le chemin rose-brun, arène centrale dégagée
  entourée d'un anneau de chemin (mare en magenta #FF00FF à l'ouest), et au nord, au bout du chemin, un autel-sanctuaire
  de pierre moussue encadré de racines et de houppiers (sans ouverture sombre) ;
- sol_complet.png et feuilles_lucioles_poses.png : réutilisés d'EMF1 sans nouvelle génération (même sha256).
Calques : eau, scintillements, sol complet, herbe, chemin, herbes hautes, rochers, arbres, sanctuaire, feuilles,
lucioles. Pas de calque `profondeur`.
Animations, chacune sur son calque, boucles fermées (240 ticks = 4 s), fonctions et constantes chargées depuis EMF1 :
- eau : mare façon rivière Métano, couleurs Métano exactes, SANS liseré de rive (water_phases d'EWC2), 4 x 10 ticks ;
- scintillements : `Metano_Town_River_Sparkles.tile` natifs, 4 x 10 ticks ;
- feuilles : poses générées d'EMF1 (palette des houppiers), 48 x 5 ticks ;
- lucioles : poses générées d'EMF1, 48 x 5 ticks.
Marqueurs : `entrance` (sud), `boss` (centre de la clairière), `objectif` (au pied de l'autel-sanctuaire au nord).
Aucune sortie, aucun warp, pas de `donjon_seuil`.
Lancer : .venv/bin/python source/fin_mystifying_forest_v3/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
REF_NAME = 'Mystifying_Forest_entrance_TDS.png'
REF = R / REF_NAME
OUT = R / 'renders/fin_mystifying_forest_v3'
STAGE = R / '.cache/fin_mystifying_forest_v3/fin_mystifying_forest'
NAMESPACE = 'fin_mystifying_forest'
ASSET = 'fmf3_fin_mystifying_forest'
PFX = 'FMF3'
W, H = 768, 576
SRC = (1200, 896)
WATER_PHASES, WATER_TICKS = 4, 10
ANIM_PHASES, ANIM_TICKS = 48, 5
LOOP_TICKS = 240
LOT = 'source/fin_mystifying_forest_v3'


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


EMF1 = loadmod('emf1_build', R / 'source/entree_mystifying_forest_sud_nord_v1/build.py')
V2, V1 = EMF1.V2, EMF1.V1
JM, BM, PAL = EMF1.JM, EMF1.BM, EMF1.PAL
assert (JM.W, JM.H, JM.SRC) == (W, H, SRC)
keep_large, place, cell_grid, close_, open_ = EMF1.keep_large, EMF1.place, EMF1.cell_grid, EMF1.close_, EMF1.open_
down_class, down_full, rgba, resize_plane, quantize_group = (
    EMF1.down_class, EMF1.down_full, EMF1.rgba, EMF1.resize_plane, EMF1.quantize_group)
sha, rgb, repair_ground, materials, fidelity = (
    EMF1.sha, EMF1.rgb, EMF1.repair_ground, EMF1.materials, EMF1.fidelity)
sheet_poses, reduce_pose, paste, leaf_frames, firefly_frames = (
    EMF1.sheet_poses, EMF1.reduce_pose, EMF1.paste, EMF1.leaf_frames, EMF1.firefly_frames)
LEAF_FALL, FLY_PULSE = EMF1.LEAF_FALL, EMF1.FLY_PULSE

GEN = [
    {'file': 'decor_magenta.png',
     'images': ['source/entree_mystifying_forest_sud_nord_v1/bruts/decor_magenta.png', REF_NAME],
     'prompt':
     "Edit the first wide 4:3 landscape pixel-art map (1200x896). Keep the exact 4:3 wide landscape aspect ratio "
     "(1200x896) and keep the exact same pixel-art style, palette, bright green grass with fine blades, pinkish-brown "
     "dirt path, huge dark green trees with pale twisted exposed roots, grey-green mossy boulders, dark green tall "
     "grass patches, and flat pure magenta #FF00FF pond on the left. Make ONLY two changes for a closed end-of-dungeon "
     "forest sanctuary room: (1) at the top center (NORTH), close the black opening between the trees with dense dark "
     "green tree canopies, twisted roots, and a mossy grey-green stone sanctuary monolith / altar at the northern end "
     "of the pinkish-brown dirt path (NO black opening, NO dark hole at the top edge); (2) remove the single central "
     "tree standing in the middle of the clearing and replace it with open bright green meadow grass and the "
     "pinkish-brown dirt path so the center of the clearing forms a wide open boss arena. Wide landscape 4:3. No "
     "characters, no text, no UI, no border.",
     'essais': 'premier essai ; conforme (herbe 7.2, chemin 9.5, feuillage_sombre 2.5, roche_racines 13.8)'},
    {'file': 'sol_complet.png',
     'images': ['source/entree_mystifying_forest_sud_nord_v1/bruts/decor_magenta.png'],
     'prompt':
     "REUTILISE sans nouvelle generation : sol complet d'EMF1 (source/entree_mystifying_forest_sud_nord_v1/bruts/"
     "sol_complet.png, meme sha256). Prompt d'origine : Same image, same size and pixel-art style, but showing only the "
     "plain bright green grass ground everywhere (the trees, path, rocks, dark grass and pink pond are all removed and "
     "replaced by that same grass).",
     'essais': 'copie du sol_complet d EMF1 (meme biome, repare par repair_ground) : aucune generation supplementaire'},
    {'file': 'feuilles_lucioles_poses.png',
     'images': [REF_NAME],
     'prompt':
     "REUTILISE sans nouvelle generation : planche de poses d'EMF1 (source/entree_mystifying_forest_sud_nord_v1/bruts/"
     "feuilles_lucioles_poses.png, meme sha256). Prompt d'origine : Sprite sheet on a flat pure magenta #FF00FF "
     "background, in EXACTLY the pixel-art style and colors of the reference image (Pokemon Mystery Dungeon Explorers "
     "of Sky forest). 2 rows x 6 columns of separate small sprites. Row 1: a single green leaf (same greens as the tree "
     "canopies) falling and fluttering, 6 rotation poses. Row 2: a small glowing firefly light mote (pale yellow-green "
     "glow), 6 poses from dim to bright to dim. Each sprite isolated and centered in its cell, wide magenta spacing, no "
     "overlap, no text, no grid lines.",
     'essais': 'copie de la planche de poses d EMF1 : aucune generation supplementaire'},
]

PALETTE_GROUPS = {
    'terrain': (['sol_complet', 'herbe', 'chemin', 'herbes_hautes'], 96),
    'arbres': (['arbres'], 40),
    'rochers': (['rochers', 'sanctuaire'], 24),
}
STATIC = ['herbe', 'chemin', 'herbes_hautes', 'rochers', 'arbres', 'sanctuaire']


def classify(a):
    r, g, b = a.transpose(2, 0, 1); lum = a @ [.299, .587, .114]; sat = a.max(2) - a.min(2)
    hh, ww = lum.shape; yy, xx = np.mgrid[:hh, :ww]
    mag = (r > g * 1.5) & (b > g * 1.3) & (r > 150) & (b > 130)
    water = nd.binary_dilation(mag, iterations=2)
    bg = nd.uniform_filter(b / np.maximum(g, 1), 11); L = nd.uniform_filter(lum, 11)
    # Sanctuaire nord : autel de pierre moussue dans la boîte (52 <= y < 222, 554 <= x <= 646).
    sanc_box = (yy >= 52) & (yy < 222) & (xx >= 554) & (xx <= 646)
    sanctuaire = nd.binary_fill_holes(close_(sanc_box & (lum > 45) & ~((r >= g - 4) & (r - b > 12) & (yy > 205)), 2)) & sanc_box
    # Chemin (avec anneau central autour de l'îlot d'herbe) : seuls les petits trous (< 800 px) sont bouchés.
    path0 = keep_large(open_(close_((r >= g - 4) & (r - b > 12) & (lum > 118) & (lum < 215) & ~water & ~sanctuaire, 2), 1), 5000)
    pholes = nd.binary_fill_holes(path0) & ~path0; phl, _ = nd.label(pholes)
    psizes = nd.sum(pholes, phl, range(1, phl.max() + 1)) if phl.max() else []
    path = (path0 | np.isin(phl, [i + 1 for i, v in enumerate(psizes) if v < 800])) & ~water & ~sanctuaire
    pale = (sat < 60) & (lum > 95) & ~path & ~water & ~sanctuaire
    pale = keep_large(close_(pale, 1), 30) & ~path & ~water & ~sanctuaire
    yk, xk = np.mgrid[-7:8, -7:8]; disk = (xk ** 2 + yk ** 2) <= 49
    seed = nd.binary_opening(np.pad(pale, 9, mode='edge'), structure=disk)[9:-9, 9:-9]
    blobs = keep_large(nd.binary_dilation(seed, iterations=3) & pale, 250)
    bl, _ = nd.label(blobs); rocks0 = np.zeros_like(blobs)
    for i, sl in enumerate(nd.find_objects(bl), 1):
        comp = bl[sl] == i; px = a[sl][comp]
        if (px[:, 0] - px[:, 2]).mean() < 10:
            rocks0[sl] |= comp
    rocks0 = nd.binary_fill_holes(close_(rocks0, 3)) & ~water & ~sanctuaire & ~path
    clear = (L > 92) & (bg < 0.64) & (xx >= 50) & (xx < 1150) & ~path & ~water & ~sanctuaire & ~rocks0
    clear = open_(close_(clear, 2), 2)
    cl, _ = nd.label(clear); touch = set(np.unique(cl[nd.binary_dilation(path, iterations=4) & clear])) - {0}
    walk = keep_large(np.isin(cl, list(touch)), 2000)
    U = close_(walk | path, 3)
    holes = nd.binary_fill_holes(U) & ~U; hl, _ = nd.label(holes)
    sizes = nd.sum(holes, hl, range(1, hl.max() + 1)) if hl.max() else []
    small = np.isin(hl, [i + 1 for i, v in enumerate(sizes) if v < 1200])
    walk = (U | small) & (xx >= 50) & (xx < 1150) & ~path & ~water & ~sanctuaire & ~rocks0
    nonwalk = ~(water | sanctuaire | path | walk)
    rocks = rocks0 & nonwalk
    hd = nd.uniform_filter((lum > 115).astype(float), 15)
    canopy = nonwalk & ~rocks & (((bg > 0.74) & (L < 110)) | (hd > 0.12) | ((yy < 200) & (xx > 470) & (xx < 730) & (lum < 75)))
    canopy = nd.binary_fill_holes(keep_large(open_(close_(canopy, 3), 3), 1500)) & nonwalk & ~rocks
    trees = keep_large((canopy | (pale & nonwalk)) & ~rocks & nonwalk, 1500)
    tall = nonwalk & ~trees & ~rocks
    return dict(water=water, sanctuaire=sanctuaire, herbe=walk, chemin=path, herbes_hautes=tall, rochers=rocks, arbres=trees)


def write_ora(path, layers):
    import xml.etree.ElementTree as ET
    root = ET.Element('image', w=str(W), h=str(H), name='Fin Mystifying Forest V3 (FMF3)')
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
    o.update(Name={'DefaultText': 'Fin Mystifying Forest - sanctuaire de la foret (4:3)', 'LocalTexts': {}}, AssetName=ASSET,
             Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0},
             ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Rendu genere 4:3 reference sur le rip Mystifying Forest ; mare facon Metano sans '
                     'lisere (couleurs Metano exactes), scintillements Metano natifs, feuilles et lucioles generees, '
                     'autel sanctuaire au nord. Collisions de base a verifier. Aucune sortie ni warp. Biome et portee '
                     'choisis par l agent.')
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
  <Name>Fin Mystifying Forest 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : zone de fin de donjon de Mystifying Forest (sanctuaire de la foret mystique), generee au format 4:3 (ref. rip Mystifying Forest), mare facon Metano, feuilles et lucioles animees. Pas une aventure jouable.</Description>
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
    ANIMS = ['eau', 'scintillements', 'feuilles', 'lucioles']
    if OUT.exists():
        for d in ['calques', 'animation', 'poses', 'masques', 'review']:
            shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['calques', 'poses', 'masques', 'review'] + [f'animation/{x}' for x in ANIMS]:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    STAGE.parent.mkdir(parents=True, exist_ok=True)
    a = rgb(RAW / 'decor_magenta.png'); f0 = rgb(RAW / 'sol_complet.png'); ref = rgb(REF)
    assert a.shape[:2] == f0.shape[:2] == (SRC[1], SRC[0])
    f, repair = repair_ground(f0)
    m = classify(a)
    order = ['water', 'sanctuaire', 'chemin', 'rochers', 'arbres', 'herbes_hautes', 'herbe']
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
    wf, dist = V2.water_phases(water, visible)
    fams = BM.sparkle_families(); taken = np.zeros((H, W), bool)
    sf = [np.zeros((H, W, 4), 'uint8') for _ in range(WATER_PHASES)]; sparkles = []
    for fi, (name, frames) in enumerate(fams.items()):
        hh, ww = frames[0].shape[:2]
        for (y, x) in place(visible & (dist > 4), (hh, ww), 2, 61 + fi, taken, core=8):
            sparkles.append({'famille': name, 'xy': [x, y]})
            for t in range(WATER_PHASES):
                mm = frames[t][..., 3] > 0; sf[t][y:y+hh, x:x+ww][mm] = frames[t][mm]
    for arr in sf:
        arr[~visible] = 0
    src, bgm, rows = sheet_poses(RAW / 'feuilles_lucioles_poses.png')
    assert len(rows) >= 2 and len(rows[0]) == 6 and len(rows[1]) == 6, [len(r_) for r_ in rows]
    tree_pal = np.unique(layers['arbres'][ex['arbres']][:, :3], axis=0).astype(float)
    leaves = [reduce_pose(src, bgm, cy, cx, 120, 12, tree_pal, 0.3) for cy, cx, _, _ in rows[0]]
    fly_px = np.concatenate([src[sl][mm] for _, _, sl, mm in rows[1]])
    qf = Image.fromarray(fly_px.reshape(-1, 1, 3).astype('uint8')).quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    fly_pal = np.array(qf.getpalette()[:24], float).reshape(-1, 3)
    flies = [reduce_pose(src, bgm, cy, cx, 72, 12, fly_pal, 0.3) for cy, cx, _, _ in rows[1]]
    for i, p in enumerate(leaves):
        Image.fromarray(p).save(OUT / 'poses' / f'{PFX}_feuille_{i}.png')
    for i, p in enumerate(flies):
        Image.fromarray(p).save(OUT / 'poses' / f'{PFX}_luciole_{i}.png')
    walk_px = (layers['herbe'][..., 3] == 255) | (layers['chemin'][..., 3] == 255)
    Image.fromarray((walk_px * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_praticable.png')
    can = ex['arbres']; edge = can & ~nd.binary_erosion(can, iterations=2) & np.roll(walk_px, -6, axis=0)
    rng = np.random.default_rng(5); cand = np.argwhere(edge[40:H - 70, 30:W - 30]) + [40, 30]
    starts, used = [], []
    for y, x in cand[rng.permutation(len(cand))]:
        if all(abs(x - ux) > 60 or abs(y - uy) > 60 for uy, ux in used):
            used.append((y, x)); starts.append((int(x), int(y) - 4, (len(starts) * 8) % ANIM_PHASES, 1 if len(starts) % 2 else -1))
        if len(starts) == 8:
            break
    feuilles = leaf_frames(leaves, starts, np.ones((H, W), bool))
    darkish = (ex['herbes_hautes'] | (ex['arbres'] & nd.binary_dilation(walk_px, iterations=10)))
    darkish &= ~nd.binary_dilation(ex['water'], iterations=4)
    cand = np.argwhere(darkish[24:H - 24, 24:W - 24]) + [24, 24]; spots, used = [], []
    for y, x in cand[np.random.default_rng(8).permutation(len(cand))]:
        if all(abs(x - ux) > 48 or abs(y - uy) > 48 for uy, ux in used):
            used.append((y, x)); spots.append((int(x), int(y), (len(spots) * 5) % ANIM_PHASES, 4 + (len(spots) % 3) * 2))
        if len(spots) == 14:
            break
    lucioles = firefly_frames(flies, spots)
    anim = {'eau': (wf, WATER_TICKS), 'scintillements': (sf, WATER_TICKS), 'feuilles': (feuilles, ANIM_TICKS),
            'lucioles': (lucioles, ANIM_TICKS)}
    order_names = ['eau', 'scintillements', 'sol_complet'] + STATIC + ['feuilles', 'lucioles']
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
    blocked = cell_grid(~walk_px); gh_, gw_ = blocked.shape
    pth = layers['chemin'][..., 3] == 255
    pxs = np.nonzero(pth[H - 8])[0]; med = int(np.median(pxs)) // 8
    ecol = min((c for c in range(gw_ - 1) if not blocked[gh_ - 2:, c:c + 2].any()), key=lambda c: abs(c - med))
    entry_px = [ecol * 8, H - 16]
    free_c = lambda cx, cy: 0 <= cx < gw_ - 1 and 0 <= cy < gh_ - 1 and not blocked[cy:cy + 2, cx:cx + 2].any()
    tgt = (W // 16 - 1, H // 16 - 1)
    boss_c = min(((cx, cy) for cy in range(gh_) for cx in range(gw_) if free_c(cx, cy)),
                 key=lambda c: (c[0] - tgt[0]) ** 2 + (c[1] - tgt[1]) ** 2)
    boss_px = [boss_c[0] * 8, boss_c[1] * 8]
    sys_, sxs_ = np.nonzero(ex['sanctuaire'])
    scx_c = int(round(sxs_.mean())) // 8 - 1
    cands = [(cx, cy) for cy in range(int(sys_.max()) // 8, gh_) for cx in range(scx_c - 3, scx_c + 4) if free_c(cx, cy)]
    top_cy = min(cy for _, cy in cands)
    obj_c = min((c for c in cands if c[1] <= top_cy + 1), key=lambda c: abs(c[0] - scx_c))
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
    sheet = Image.new('RGBA', (6 * 28 + 8, 2 * 28 + 8), (18, 42, 34, 255))
    for r_, (arr, sc) in enumerate([(leaves, 2), (flies, 3)]):
        for i, p in enumerate(arr):
            im = Image.fromarray(p); im = im.resize((im.width * sc, im.height * sc), Image.Resampling.NEAREST)
            sheet.alpha_composite(im, (8 + i * 28 + (20 - im.width) // 2, 8 + r_ * 28 + (20 - im.height) // 2))
    sheet.save(OUT / 'review' / f'{PFX}_planche_poses.png')
    write_ora(OUT / f'{PFX}_fin_mystifying_forest_calques.ora',
              {f'{i:02d}_{t}' + ('_f00' if len(fr) > 1 else ''): fr[0] for i, (t, fr, _) in enumerate(stack_named)})
    counts = ground_project([(t.replace('_', ' ') + (f' {len(fr)} phases' if len(fr) > 1 else ''), fr, tk)
                             for t, fr, tk in stack_named], blocked, entry_px, boss_px, objective_px, gfx, tools)
    fid = fidelity(a, ref)
    final_fid = {}
    for k, nm in (('herbe', 'herbe'), ('chemin', 'chemin'), ('feuillage_sombre', 'arbres'), ('roche_racines', 'rochers')):
        lay = layers[nm]; px = lay[lay[..., 3] == 255][:, :3].astype(float)
        sel = materials(px.reshape(-1, 1, 3))[k][:, 0]
        px = px[sel] if sel.sum() > 50 else px
        final_fid[k] = {'calque': nm, 'rgb': [round(float(v), 1) for v in px.mean(0)],
                        'distance_rip': round(float(np.linalg.norm(px.mean(0) - np.array(fid[k]['rip_rgb']))), 1)}
    manifest = {
        'lot': 'fin_mystifying_forest_v3', 'prefix': PFX, 'format': '4:3 vaste', 'type': 'fin de donjon',
        'size_px': [W, H], 'grid_8px': [W // 8, H // 8],
        'base': 'branche de session (EMF1 pour l eau, les feuilles, les lucioles et les bruts sol_complet/poses ; EWC2/EWC1/ESN1 pour les utilitaires) ; aucun emprunt aux branches soeurs',
        'biome': 'fin de Mystifying Forest (sanctuaire de la foret mystique, prolonge EMF1), biome et portee choisis par l agent (« alors ........... »), a confirmer',
        'method': 'textures canoniques = rendu genere REFERENCE : rip passe au generateur ; mare en magenta sur le decor, '
                  'autel sanctuaire au nord (sans ouverture sombre), sol complet et planche de poses d EMF1 reutilises',
        'reference_da': {'file': REF.name, 'sha256': sha(REF)},
        'generation': GEN,
        'raw_inputs': [{'file': f'{LOT}/bruts/{g["file"]}', 'sha256': sha(RAW / g['file']),
                        'size': list(Image.open(RAW / g['file']).size)} for g in GEN],
        'reparation_sol_complet': repair,
        'fidelite_rip': {'methode': 'moyenne RGB par matiere, meme classifieur pixel sur le rip et sur le brut ; distance euclidienne ; seuil 20',
                         'brut': fid, 'calques_finaux': final_fid},
        'normalization': {'scale': JM.SCALE, 'scaled': [JM.SCALED_W, H], 'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
                          'methode': 'moyenne ponderee par classe (BOX), attribution exclusive par poids maximal',
                          'palettes': {g: {'calques': k, 'couleurs': n} for g, (k, n) in PALETTE_GROUPS.items()}},
        'layers': layer_list,
        'water': {'style': 'facon riviere Metano, SANS lisere clair de rive (water_phases d EWC2), couleurs Metano exactes',
                  'couleurs': {k: list(PAL[k]) for k in ('surface', 'bande', 'inter', 'accent')},
                  'phases': WATER_PHASES, 'frame_length_ticks': WATER_TICKS},
        'sparkles': {'source': 'source/eau_metano/natifs/Metano_Town_River_Sparkles.tile',
                     'phases': WATER_PHASES, 'frame_length_ticks': WATER_TICKS, 'placements': sparkles},
        'feuilles': {'source': f'{LOT}/bruts/feuilles_lucioles_poses.png', 'poses': 6, 'taille_pose_px': [10, 10],
                     'palette': 'palette du calque arbres', 'departs': [list(s) for s in starts],
                     'phases_chute': LEAF_FALL, 'phases': ANIM_PHASES, 'frame_length_ticks': ANIM_TICKS,
                     'origine': 'poses generees d EMF1 reutilisees, trajectoires et cadence creees par nous'},
        'lucioles': {'source': f'{LOT}/bruts/feuilles_lucioles_poses.png', 'poses': 6, 'taille_pose_px': [6, 6],
                     'palette': [[int(x) for x in c] for c in fly_pal], 'points': [list(s) for s in spots],
                     'pulsation': FLY_PULSE, 'phases': ANIM_PHASES, 'frame_length_ticks': ANIM_TICKS,
                     'origine': 'poses generees d EMF1 reutilisees, trajectoires et cadence creees par nous'},
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'entry_px': entry_px, 'boss_px': boss_px, 'objective_px': objective_px, 'path_found_16x16': reach,
                   'path_to_boss': reach_boss, 'path_to_objective': reach_obj, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si > 25 % hors praticable (herbe claire + chemin)',
                   'boss': 'case 2 x 2 libre au centre de la clairiere',
                   'objectif': 'case 2 x 2 libre la plus haute sous l autel sanctuaire au nord',
                   'fin': 'aucune sortie, aucun warp, pas de donjon_seuil ; le bord nord et les flancs sont bloques'},
        'pmdo': {'target': '0.8.12', 'asset': ASSET, 'namespace': NAMESPACE, 'tiles_per_bank': counts, 'banks': list(counts),
                 'runtime_tested': False, 'warp': 'aucun'},
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    print(json.dumps({'entry': entry_px, 'boss': boss_px, 'objectif': objective_px, 'blocked': int(blocked.sum()),
                      'walkable': int((~blocked).sum()), 'px': {k: int(v.sum()) for k, v in ex.items()},
                      'fidelite': {k: v['distance'] for k, v in fid.items()},
                      'final': {k: v['distance_rip'] for k, v in final_fid.items()}, 'tiles': sum(counts.values())}, indent=1))


if __name__ == '__main__':
    build()
