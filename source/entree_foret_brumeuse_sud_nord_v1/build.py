"""Entrée Forêt Brumeuse sud -> nord V1 (EFB1) — format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Biome choisi par l'utilisateur : Forêt Brumeuse (Foggy Forest, D08P11A / P21P02A), décliné en 3 layouts :
- EFB1 : Entrée de donjon sud -> nord (ce lot) ;
- FFB1 : Fin de donjon / Arène de boss ;
- ZFB1 : Zone ouverte / Camp de base & panorama.

Méthode « textures canoniques » = rendu généré RÉFÉRENCÉ : le rip `Foggy_Forest_Base_Camp_TDS.png` (D08P11A)
est passé au générateur comme image de référence.
Bruts (voir manifest.json -> generation et bruts_ecartes, prompts complets) :
- bruts/ecartes/decor_herbe_pale_v0.png : premier jet 4:3 dont l'herbe de clairière était trop pâle (dist_rip = 47,3 > 35),
  conservé mais écarté du build ;
- decor_magenta.png : décor complet 4:3 (1200 x 896) recoloré à partir du premier jet et du rip (dist_rip herbe = 18,5,
  chemin = 6,8, feuillage = 5,5), ruisseau peint en magenta #FF00FF ;
- sol_complet.png : herbe complète éditée depuis le décor et le rip ;
- poses_foret_brumeuse.png : planche de feuilles (rangée 1, 6 poses) et de lucioles (rangée 2, 6 poses) sur magenta.
Normalisation UNIFORME x(576/896) puis recadrage centré à 768 ; réduction par classe (down_class).
Calques fixes (10) : sol_complet, herbe, chemin, fleurs, rochers, buissons, herbes_hautes, parois, arbres, profondeur.
Animations, chacune sur son calque (4) :
- eau du ruisseau « façon rivière Métano », COULEURS MÉTANO EXACTES, sans liseré clair (water_phases d'EWC2), 4 x 10 ticks ;
- scintillements Metano_Town_River_Sparkles NATIFS, 4 x 10 ticks ;
- feuilles qui tombent : 6 poses générées réduites à 10 x 10 px, 48 x 5 ticks ;
- lucioles : 6 poses générées réduites à 6 x 6 px, pulsation et boucles de Lissajous, 48 x 5 ticks.
Scène : PPCM(40, 240) = 240 ticks = 4 s.
Lancer : .venv/bin/python source/entree_foret_brumeuse_sud_nord_v1/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
REF = R / 'Foggy_Forest_Base_Camp_TDS.png'
OUT = R / 'renders/entree_foret_brumeuse_sud_nord_v1'
STAGE = R / '.cache/entree_foret_brumeuse_sud_nord_v1/entree_foret_brumeuse_sud_nord'
NAMESPACE = 'entree_foret_brumeuse_sud_nord'
ASSET = 'efb1_entree_foret_brumeuse'
PFX = 'EFB1'
W, H = 768, 576                      # 4:3, 96 x 72 cases
SRC = (1200, 896)
WATER_PHASES, WATER_TICKS = 4, 10
ANIM_PHASES, ANIM_TICKS = 48, 5      # 240 ticks = 4 s ; multiple exact de 4 x 10 = 40 ticks
LOOP_TICKS = 240
GEN = [
    {'file': 'decor_magenta.png',
     'images': ['source/entree_foret_brumeuse_sud_nord_v1/bruts/ecartes/decor_herbe_pale_v0.png', 'Foggy_Forest_Base_Camp_TDS.png'],
     'prompt':
     'Edit the first image (the 4:3 dungeon entrance map) so that its color palette and shading match EXACTLY the '
     'second reference image (Foggy Forest Base Camp from Pokemon Mystery Dungeon Explorers of Sky): make the clearing '
     'grass the EXACT same medium-deep warm olive-green (around RGB 133, 182, 113, not pale pastel green), keep the same '
     'earthy tan dirt path, same dark sage-green tree canopies with lime-yellow highlights, same mossy stone arch with '
     'pitch-black doorway at the north, and keep the stream on the left filled with flat solid pure magenta #FF00FF '
     '(RGB 255, 0, 255) with crisp pixel edges. Keep the exact same layout, framing, and 2D DS pixel-art details.'},
    {'file': 'sol_complet.png',
     'images': ['source/zone_foret_brumeuse_camp_v1/bruts/decor_magenta.png', 'Foggy_Forest_Base_Camp_TDS.png'],
     'prompt':
     'Edit the first image: keep the exact same 4:3 size (1200x896) and 2D Nintendo DS pixel-art texture from the second '
     'reference image (Foggy Forest Base Camp), but remove EVERYTHING except the flat walkable green forest grass ground: '
     'no trees, no tents, no bushes, no dirt paths, no rocks, no flowers, no water, no magenta. The entire image must be '
     'covered edge-to-edge with seamless medium-bright green forest grass texture with subtle darker green grass blades '
     'and tiny clover speckles, uniform lighting across the whole frame.'},
    {'file': 'poses_foret_brumeuse.png',
     'images': ['Foggy_Forest_Base_Camp_TDS.png'],
     'prompt':
     '2D pixel-art sprite sheet on a flat solid pure magenta #FF00FF (RGB 255, 0, 255) background, matching the exact '
     'pixel-art palette and style of the reference image (Pokemon Mystery Dungeon Explorers of Sky, Foggy Forest). '
     '2 rows x 6 columns of small isolated sprites with wide pure magenta spacing between every sprite: '
     'Row 1 (top row): 6 poses of a single small sage-green and lime-green forest leaf tumbling and fluttering as it falls '
     '(tilted left, flat, tilted right, curling, flipping, gentle glide). '
     'Row 2 (bottom row): 6 poses of a glowing pale-yellow and misty-cyan forest firefly / mist spore pulsing softly '
     '(tiny dim speck, small glow, medium warm yellow-green orb, bright core with soft pixel halo, fading glow, tiny spark). '
     'Crisp pixel art, no anti-aliasing against the #FF00FF magenta background, no grid lines, no text, no borders.'},
]
ECARTES = [
    {'file': 'source/entree_foret_brumeuse_sud_nord_v1/bruts/ecartes/decor_herbe_pale_v0.png',
     'images': ['Foggy_Forest_Base_Camp_TDS.png'],
     'statut': 'ecarte',
     'raison': 'Herbe de clairiere trop pale sur le premier jet (RGB [160.5, 196.8, 148.7], distance euclidienne 47.3 > 35 '
               'par rapport a l herbe du rip Foggy_Forest_Base_Camp_TDS.png [133.1, 182.1, 113.1]). Recolore avec le rip '
               'en seconde reference pour produire bruts/decor_magenta.png (distance herbe = 18.5 < 35). Non lu par build.py.'}
]


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


W1 = loadmod('ewc1', R / 'source/entree_waterfall_cave_sud_nord_v1/build.py')
V2 = loadmod('ewc2', R / 'source/entree_waterfall_cave_sud_nord_v2/build.py')
EMF = loadmod('emf1', R / 'source/entree_mystifying_forest_sud_nord_v1/build.py')
JM, BM = W1.JM, W1.BM
assert (W1.W, W1.H, W1.SRC) == (W, H, SRC)
keep_large, place, cell_grid = BM.keep_large, BM.place, BM.cell_grid
down_class, down_full, rgba = JM.down_class, JM.down_full, JM.rgba
sha, quantize_group, rgb, close_, write_ora = W1.sha, W1.quantize_group, W1.rgb, W1.close_, W1.write_ora
PAL = V2.PAL
sheet_poses, reduce_pose, paste = EMF.sheet_poses, EMF.reduce_pose, EMF.paste

PALETTE_GROUPS = {
    'terrain': (['sol_complet', 'herbe', 'chemin', 'fleurs', 'buissons', 'herbes_hautes'], 96),
    'arbres': (['arbres'], 40),
    'rochers': (['rochers', 'parois'], 24),
    'profondeur': (['profondeur'], 12),
}


def open_(m, it):
    p = it + 1
    return nd.binary_opening(np.pad(m, p, mode='edge'), iterations=it)[p:-p, p:-p]


# ---------------------------------------------------------------- fidélité au rip (Foggy_Forest_Base_Camp_TDS.png)
def materials(a):
    r, g, b = a.transpose(2, 0, 1); lum = a @ [.299, .587, .114]
    mag = (r > 200) & (b > 200) & (g < 90)
    return {
        'herbe': ~mag & (g > r + 20) & (g > b + 30) & (lum > 140),
        'chemin': ~mag & (np.abs(r - g) <= 22) & (r - b > 14) & (lum > 110) & (lum < 205),
        'feuillage': ~mag & (g > r + 15) & (g > b + 15) & (lum >= 55) & (lum <= 140),
    }


def fidelity(dec, ref):
    dm, rm = materials(dec), materials(ref); out = {}
    for k in dm:
        d, r = dec[dm[k]].mean(0), ref[rm[k]].mean(0)
        out[k] = {'decor_rgb': [round(float(x), 1) for x in d], 'rip_rgb': [round(float(x), 1) for x in r],
                  'distance': round(float(np.linalg.norm(d - r)), 1),
                  'pixels_decor': int(dm[k].sum()), 'pixels_rip': int(rm[k].sum())}
    return out


# ---------------------------------------------------------------- réparation de sol_complet.png
def repair_ground(f):
    """Remplace tout pixel non-herbe éventuel par un pavage du coeur herbeux central f[380:560, 380:820]."""
    r, g, b = f.transpose(2, 0, 1); lum = f @ [.299, .587, .114]
    bad = (lum < 75) | (g < r + 8) | ((r > 200) & (b > 200) & (g < 90))
    bad = nd.binary_dilation(bad, iterations=2)
    out = f.copy(); patch = f[380:560, 380:820]
    ph, pw = patch.shape[:2]; yy, xx = np.nonzero(bad)
    out[yy, xx] = patch[yy % ph, xx % pw]
    return out, {'pixels_remplaces': int(bad.sum()), 'patch_source': [380, 380, 820, 560]}


# ---------------------------------------------------------------- segmentation (pleine résolution 1200 x 896)
def classify(a):
    r, g, b = a.transpose(2, 0, 1); lum = a @ [.299, .587, .114]
    hh, ww = lum.shape; yy, xx = np.mgrid[:hh, :ww]

    # 1. Eau : magenta pur + toute frange anti-aliasée dans un rayon de 10 px, dilatée de 2 px
    mag_pure = (r > 200) & (b > 200) & (g < 90)
    mag_zone = nd.binary_dilation(mag_pure, iterations=10)
    mag_fringe = mag_zone & (((b > g + 8) & (r > g + 15)) | ((r - g) + (b - g) > 35))
    water = nd.binary_dilation(keep_large(mag_pure, 2000) | mag_fringe, iterations=2)

    # 2. Profondeur (ouverture sombre au nord) et parois (arche rocheuse moussue, hors seuil du chemin sous la bouche)
    dark = (lum < 58) & (yy < 220) & (xx > 500) & (xx < 700) & ~water
    profondeur = nd.binary_fill_holes(close_(keep_large(dark, 500), 3))
    py_max = int(np.nonzero(profondeur)[0].max())
    under_mouth = (yy >= py_max - 2) & (xx >= 562) & (xx <= 638)
    arch_box = (yy >= 45) & (yy < 205) & (xx >= 505) & (xx < 695) & ~profondeur & ~under_mouth & ~water
    arch_stone = arch_box & ~((g > r + 14) & (g > b + 14))
    parois = nd.binary_fill_holes(close_(keep_large(arch_stone, 400), 3)) & ~profondeur & ~under_mouth & ~water
    used = water | profondeur | parois

    # 3. Chemin de terre ocre (du bord sud jusqu'au seuil nord)
    path_raw = (np.abs(r - g) <= 22) & (r - b > 14) & (lum > 112) & (lum < 205) & ~used
    chemin = nd.binary_fill_holes(keep_large(open_(close_(path_raw, 3), 2), 8000)) & ~used
    used |= chemin

    # 4. Herbe de la clairière centrale
    L = nd.uniform_filter(lum.astype(float), 9)
    G_R = nd.uniform_filter((g - r).astype(float), 9)
    G_B = nd.uniform_filter((g - b).astype(float), 9)
    clear_grass = (L > 136) & (G_R > 16) & (G_B > 25) & ~used
    clear_grass = keep_large(open_(close_(clear_grass, 3), 2), 8000) & ~used
    clearing_hull = nd.binary_fill_holes(close_(clear_grass | chemin | water | parois, 15))
    in_clearing = clearing_hull & ~used & ~clear_grass

    # 5. Fleurs et rochers dans la clairière et sur son pourtour
    non_green = (in_clearing | nd.binary_dilation(clear_grass, iterations=6)) & ~used & ~((g > r + 12) & (g > b + 14))
    isl = close_(non_green, 3) & ~used
    ilab, _ = nd.label(isl)
    fleurs = np.zeros_like(water); rochers = np.zeros_like(water)
    for i, sl in enumerate(nd.find_objects(ilab), 1):
        comp = ilab[sl] == i; sz = comp.sum()
        if sz < 25 or sz > 12000:
            continue
        px = a[sl][comp]; pr, pg, pb = px[:, 0], px[:, 1], px[:, 2]; psat = px.max(1) - px.min(1)
        petal_frac = (((pr > pg + 18) & (psat > 42)) | ((pb >= pg - 2) & (pr >= pg - 4) & (psat > 15))).mean()
        if (petal_frac > 0.12 and sz < 900) or sz < 220:
            fleurs[sl] |= nd.binary_dilation(nd.binary_fill_holes(comp), iterations=2) & ~used[sl]
        elif pr.mean() > 118:
            rochers[sl] |= nd.binary_dilation(nd.binary_fill_holes(comp), iterations=1) & ~used[sl]
    fleurs &= ~used & ~clear_grass; used |= fleurs
    rochers &= ~used & ~clear_grass; used |= rochers

    # 6. Buissons ronds dans la clairière
    bush_cand = in_clearing & ~used & (g > r + 10)
    blab, _ = nd.label(close_(bush_cand, 2))
    buissons = np.zeros_like(water)
    for i, sl in enumerate(nd.find_objects(blab), 1):
        comp = blab[sl] == i
        if 120 <= comp.sum() <= 9000:
            buissons[sl] |= nd.binary_fill_holes(comp)
    buissons &= ~used; used |= buissons

    herbe = (clear_grass | (in_clearing & ~used)) & ~used
    used |= herbe

    # 7. Couronne forestière : arbres (houppiers + troncs) vs herbes hautes de sous-bois
    rem = ~used
    std_lum = nd.uniform_filter(np.abs(lum - L), 15)
    bright_d = nd.uniform_filter((lum > 142).astype(float), 21)
    dark_d = nd.uniform_filter((lum < 88).astype(float), 17)
    trunk = (r > g - 8) & (r - b > 12) & (lum < 135)
    tree_raw = rem & ((bright_d > 0.04) | (dark_d > 0.12) | (std_lum > 11.5) | trunk)
    arbres = nd.binary_fill_holes(keep_large(close_(tree_raw, 4), 1500)) & rem
    herbes_hautes = rem & ~arbres

    return dict(water=water, profondeur=profondeur, parois=parois, chemin=chemin, fleurs=fleurs,
                rochers=rochers, buissons=buissons, herbe=herbe, arbres=arbres, herbes_hautes=herbes_hautes)


# ---------------------------------------------------------------- animations créées
LEAF_FALL = 30
FLY_PULSE = EMF.FLY_PULSE
leaf_frames = EMF.leaf_frames
firefly_frames = EMF.firefly_frames


# ---------------------------------------------------------------- Ground PMDO 0.8.12
def ground_project(stack, blocked, entry_px, threshold_px, gfx, tools):
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
    o.update(Name={'DefaultText': 'Entree Foret Brumeuse - sud vers nord (4:3)', 'LocalTexts': {}}, AssetName=ASSET,
             Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0},
             ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Rendu genere 4:3 reference sur le rip Foggy Forest Base Camp (D08P11A) ; ruisseau '
                     'facon Metano sans lisere (couleurs Metano exactes), scintillements Metano natifs, feuilles et '
                     'lucioles generees. Collisions de base a verifier. Seuil non raccorde.')
    o['obstacles'] = [[{'Bounds': {'X': x*8, 'Y': y*8, 'Width': 8, 'Height': 8}, 'Tags': int(blocked[y, x])}
                       for y in range(gh)] for x in range(gw)]
    mk = lambda n, p: {'EntName': n, 'Direction': 4, 'EntEnabled': True, 'triggerType': 0,
                       'Collider': {'X': p[0], 'Y': p[1], 'Width': 16, 'Height': 16}}
    o['Entities'] = [{'Name': 'Entrees et vos acteurs', 'Visible': True, 'MapChars': [], 'GroundObjects': [], 'Spawners': [],
                      'Markers': [mk('entrance', entry_px), mk('donjon_seuil', threshold_px)]}]
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
  <Name>Entree Foret Brumeuse sud-nord 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : entree de donjon de la Foret Brumeuse au format 4:3 (ref. rip Foggy Forest Base Camp), ruisseau facon Metano, feuilles et lucioles animees. Pas une aventure jouable.</Description>
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
    return {b.name: len(b.data) for b in banks}


# ---------------------------------------------------------------- main
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
    a = rgb(RAW / 'decor_magenta.png'); f0 = rgb(RAW / 'sol_complet.png'); ref = rgb(REF)
    assert a.shape[:2] == f0.shape[:2] == (SRC[1], SRC[0])
    f, repair = repair_ground(f0)
    m = classify(a)
    order = ['water', 'profondeur', 'parois', 'chemin', 'fleurs', 'rochers', 'buissons', 'herbe', 'arbres', 'herbes_hautes']
    ex, cols = down_class(a, m, order)
    water = ex['water']
    static = ['herbe', 'chemin', 'fleurs', 'rochers', 'buissons', 'herbes_hautes', 'parois', 'arbres', 'profondeur']
    layers = {'sol_complet': rgba(down_full(f), ~water)}
    for k in static:
        layers[k] = rgba(cols[k], ex[k])
    q = {}
    for keys, n in PALETTE_GROUPS.values():
        q.update(quantize_group({k: layers[k] for k in keys}, n))
    layers = q
    for k, v in ex.items():
        Image.fromarray((v * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_{k}.png')
    land = np.zeros((H, W), bool)
    for k in static:
        land |= layers[k][..., 3] == 255
    visible = water & ~land
    wf, dist = V2.water_phases(water, visible)                          # Métano exactes, sans liseré de rive
    fams = BM.sparkle_families(); taken = np.zeros((H, W), bool)
    sf = [np.zeros((H, W, 4), 'uint8') for _ in range(WATER_PHASES)]; sparkles = []
    for fi, (name, frames) in enumerate(fams.items()):
        hh, ww = frames[0].shape[:2]
        for (y, x) in place(visible & (dist > 4), (hh, ww), 2, 71 + fi, taken, core=8):
            sparkles.append({'famille': name, 'xy': [x, y]})
            for t in range(WATER_PHASES):
                mm = frames[t][..., 3] > 0; sf[t][y:y+hh, x:x+ww][mm] = frames[t][mm]
    for arr in sf:
        arr[~visible] = 0
    # Poses générées : feuilles (palette des arbres), lucioles (couleurs propres réduites à 8, sans frange magenta).
    src, bgm, rows = sheet_poses(RAW / 'poses_foret_brumeuse.png')
    assert len(rows) >= 2 and len(rows[0]) == 6 and len(rows[1]) == 6, [len(r_) for r_ in rows]
    bgm_clean = bgm | ((src[..., 0] - src[..., 1] > 20) & (src[..., 2] - src[..., 1] > 20))
    bgm_fly = bgm_clean | (src[..., 1] < src[..., 0] + 5) | (src[..., 1] < src[..., 2])
    tree_pal = np.unique(layers['arbres'][ex['arbres']][:, :3], axis=0).astype(float)
    leaves = [reduce_pose(src, bgm_clean, cy, cx, 120, 12, tree_pal, 0.25) for cy, cx, _, _ in rows[0]]
    fly_px = np.concatenate([src[sl][mm & ~bgm_fly[sl]] for _, _, sl, mm in rows[1]])
    qf = Image.fromarray(fly_px.reshape(-1, 1, 3).astype('uint8')).quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    fly_pal = np.array(qf.getpalette()[:24], float).reshape(-1, 3)
    flies = [reduce_pose(src, bgm_fly, cy, cx, 96, 16, fly_pal, 0.25) for cy, cx, _, _ in rows[1]]
    for i, p in enumerate(leaves):
        Image.fromarray(p).save(OUT / 'poses' / f'{PFX}_feuille_{i}.png')
    for i, p in enumerate(flies):
        Image.fromarray(p).save(OUT / 'poses' / f'{PFX}_luciole_{i}.png')
    # Feuilles : départs sous le bord inférieur des houppiers qui dominent l'herbe ou le chemin.
    walk_px = (layers['herbe'][..., 3] == 255) | (layers['chemin'][..., 3] == 255) | (layers['fleurs'][..., 3] == 255)
    can = ex['arbres']; edge = can & ~nd.binary_erosion(can, iterations=2) & np.roll(walk_px | ex['herbes_hautes'], -6, axis=0)
    rng = np.random.default_rng(11); cand = np.argwhere(edge[40:H - 70, 30:W - 30]) + [40, 30]
    starts, used = [], []
    for y, x in cand[rng.permutation(len(cand))]:
        if all(abs(x - ux) > 60 or abs(y - uy) > 60 for uy, ux in used):
            used.append((y, x)); starts.append((int(x), int(y) - 4, (len(starts) * 6) % ANIM_PHASES, 1 if len(starts) % 2 else -1))
        if len(starts) == 8:
            break
    feuilles = leaf_frames(leaves, starts, np.ones((H, W), bool))
    # Lucioles : lisière ombragée autour de la clairière et des herbes hautes.
    darkish = (ex['herbes_hautes'] | (ex['arbres'] & nd.binary_dilation(walk_px, iterations=10)))
    darkish &= ~nd.binary_dilation(ex['water'] | ex['profondeur'], iterations=4)
    cand = np.argwhere(darkish[24:H - 24, 24:W - 24]) + [24, 24]; spots, used = [], []
    for y, x in cand[np.random.default_rng(14).permutation(len(cand))]:
        if all(abs(x - ux) > 48 or abs(y - uy) > 48 for uy, ux in used):
            used.append((y, x)); spots.append((int(x), int(y), (len(spots) * 5) % ANIM_PHASES, 4 + (len(spots) % 3) * 2))
        if len(spots) == 14:
            break
    lucioles = firefly_frames(flies, spots)
    # Exports
    anim = {'eau': (wf, WATER_TICKS), 'scintillements': (sf, WATER_TICKS), 'feuilles': (feuilles, ANIM_TICKS),
            'lucioles': (lucioles, ANIM_TICKS)}
    order_names = ['eau', 'scintillements', 'sol_complet'] + static + ['feuilles', 'lucioles']
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
    # Collisions : herbe de la clairière + chemin + petites fleurs.
    blocked = cell_grid(~walk_px); gh_, gw_ = blocked.shape
    pth = layers['chemin'][..., 3] == 255
    pxs = np.nonzero(pth[H - 8])[0]; med = int(np.median(pxs)) // 8
    ecol = min((c for c in range(gw_ - 1) if not blocked[gh_ - 2:, c:c + 2].any()), key=lambda c: abs(c - med))
    entry_px = [ecol * 8, H - 16]
    cy_, cx_ = np.nonzero(ex['profondeur'])
    ccx = int((cx_.min() + cx_.max()) // 2)
    north = int(np.nonzero(walk_px[:, ccx])[0].min())
    threshold_px = [ccx // 8 * 8 - 8, (north + 7) // 8 * 8]
    while blocked[threshold_px[1] // 8:threshold_px[1] // 8 + 2, threshold_px[0] // 8:threshold_px[0] // 8 + 2].any():
        threshold_px[1] += 8
    ok, explored = v1.reachable(blocked, (entry_px[1] // 8, entry_px[0] // 8), (threshold_px[1] // 8, threshold_px[0] // 8))
    assert ok, 'pas de chemin 16x16'

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
    for (qx, qy), c in ((entry_px, (255, 230, 40, 255)), (threshold_px, (60, 220, 255, 255))):
        dr.rectangle([qx, qy, qx + 15, qy + 15], outline=c, width=2)
    col.alpha_composite(ov); col.save(OUT / 'review' / f'{PFX}_collisions_marqueurs.png')
    sheet = Image.new('RGBA', (6 * 68, 2 * 68), (60, 110, 60, 255))
    for r_, seq in enumerate((leaves, flies)):
        for i, p in enumerate(seq):
            im = Image.fromarray(p); sc = 60 // max(im.size)
            sheet.alpha_composite(im.resize((im.width * sc, im.height * sc), Image.Resampling.NEAREST), (i * 68 + 4, r_ * 68 + 4))
    sheet.save(OUT / 'review' / f'{PFX}_planche_poses.png')
    write_ora(OUT / f'{PFX}_entree_foret_brumeuse_calques.ora',
              {f'{i:02d}_{t}' + ('_f00' if len(fr) > 1 else ''): fr[0] for i, (t, fr, _) in enumerate(stack_named)})
    counts = ground_project([(t.replace('_', ' ') + (f' {len(fr)} phases' if len(fr) > 1 else ''), fr, tk)
                             for t, fr, tk in stack_named], blocked, entry_px, threshold_px, gfx, tools)
    fid = fidelity(a, ref)
    final_fid = {}
    for k, nm in (('herbe', 'herbe'), ('chemin', 'chemin'), ('feuillage', 'arbres')):
        lay = layers[nm]; px = lay[lay[..., 3] == 255][:, :3].astype(float)
        sel = materials(px.reshape(-1, 1, 3))[k][:, 0]
        px = px[sel] if sel.sum() > 50 else px
        final_fid[k] = {'calque': nm, 'rgb': [round(float(v), 1) for v in px.mean(0)],
                        'distance_rip': round(float(np.linalg.norm(px.mean(0) - np.array(fid[k]['rip_rgb']))), 1)}
    raw_inputs = [{'file': f'source/entree_foret_brumeuse_sud_nord_v1/bruts/{g["file"]}', 'sha256': sha(RAW / g['file']),
                   'size': list(Image.open(RAW / g['file']).size), 'statut': 'retenu'} for g in GEN]
    for ec in ECARTES:
        raw_inputs.append({'file': ec['file'], 'sha256': sha(R / ec['file']),
                           'size': list(Image.open(R / ec['file']).size), 'statut': 'ecarte'})
    manifest = {
        'lot': 'entree_foret_brumeuse_sud_nord_v1', 'prefix': PFX, 'format': '4:3 vaste', 'size_px': [W, H],
        'grid_8px': [W // 8, H // 8], 'base': 'branche de session (arena/01a1024d-projet-pmdo) ; aucun emprunt aux branches soeurs',
        'biome': 'Foret Brumeuse (Foggy Forest, D08P11A / P21P02A), choisi par l utilisateur (les 3 layouts)',
        'method': 'textures canoniques = rendu genere REFERENCE : rip Foggy_Forest_Base_Camp_TDS.png passe au generateur ; '
                  'decor complet sur magenta (ruisseau = magenta), herbe complete editee depuis le decor, planche '
                  'feuilles/lucioles sur magenta',
        'reference_da': {'file': REF.name, 'sha256': sha(REF), 'titre': 'Foggy Forest Base Camp (D08P11A, PMD Explorers)'},
        'generation': GEN,
        'bruts_ecartes': ECARTES,
        'raw_inputs': raw_inputs,
        'sol_complet_reparation': repair,
        'fidelite_rip': {'methode': 'moyenne RGB par matiere, meme classifieur pixel sur le rip et sur le brut ; distance euclidienne',
                         'brut': fid, 'calques_finaux': final_fid},
        'normalization': {'scale': JM.SCALE, 'scaled': [JM.SCALED_W, H], 'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
                          'methode': 'moyenne ponderee par classe (BOX), attribution exclusive par poids maximal',
                          'palettes': {g: {'calques': k, 'couleurs': n} for g, (k, n) in PALETTE_GROUPS.items()}},
        'segmentation': 'eau = magenta pur + frange dilatee 2 px ; profondeur = ouverture sombre (lum<58) au nord ; '
                        'parois = arche rocheuse moussue encadrant la profondeur ; chemin = ocre-beige (|r-g|<=22, r-b>14), '
                        'grande composante du sud au nord ; herbe = herbe vert olive claire de la clairiere ; fleurs = petits '
                        'massifs floraux corail/lavande dans la clairiere ; rochers = blocs ocre/gris en bordure ; buissons = '
                        'massifs ronds vert sombre dans la clairiere ; arbres = houppiers vert sauge/lime + troncs ; '
                        'herbes_hautes = sous-bois restant',
        'layers': layer_list,
        'water': {'phases': WATER_PHASES, 'frame_length_ticks': WATER_TICKS,
                  'couleurs': {k: list(v) for k, v in PAL.items() if k != 'clair'},
                  'modele': 'structure et cadence riviere Metano, couleurs Metano EXACTES, sans lisere de rive (water_phases d EWC2)',
                  'origine': 'pixels recalcules, pas de tuiles natives'},
        'sparkles': {'source': 'source/eau_metano/natifs/Metano_Town_River_Sparkles.tile', 'placements': sparkles,
                     'origine': 'pixels et couleurs Metano NATIFS inchanges (aplat de surface retire)'},
        'feuilles': {'poses': len(leaves), 'taille_px': list(leaves[0].shape[:2]), 'reduction': 'fenetre 120 px -> 10 px (x1/12)',
                     'palette': 'couleurs du calque arbres', 'departs': [list(s) for s in starts],
                     'chute_phases': LEAF_FALL, 'phases': ANIM_PHASES, 'frame_length_ticks': ANIM_TICKS,
                     'origine': 'dessin GENERE ; trajectoires (chute ~37 px, balancement +/- 6 px) et chronologie creees par nous'},
        'lucioles': {'poses': len(flies), 'taille_px': list(flies[0].shape[:2]), 'reduction': 'fenetre 96 px -> 6 px (x1/16)',
                     'palette': '8 couleurs tirees des lucioles generees', 'pulsation': FLY_PULSE,
                     'points': [list(s) for s in spots], 'phases': ANIM_PHASES, 'frame_length_ticks': ANIM_TICKS,
                     'origine': 'dessin GENERE ; boucles de Lissajous et pulsation creees par nous'},
        'shadows': 'pas de calque d ombres separe : les zones sombres du rendu sont des houppiers, des buissons ou des '
                   'herbes hautes ; l ouverture sombre au nord forme le calque profondeur',
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'entry_px': entry_px, 'threshold_px': threshold_px, 'path_found_16x16': ok, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si > 25 % hors herbe de la clairiere, chemin et fleurs',
                   'seuil': 'bout nord du chemin, au pied de l arche rocheuse moussue et de l ouverture sombre'},
        'pmdo': {'target': '0.8.12', 'asset': ASSET, 'namespace': NAMESPACE, 'tiles_per_bank': counts, 'banks': list(counts),
                 'runtime_tested': False, 'warp': 'aucun'},
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    print(json.dumps({'sparkles': len(sparkles), 'entry': entry_px, 'threshold': threshold_px, 'blocked': int(blocked.sum()),
                      'walkable': int((~blocked).sum()), 'leaves': len(starts), 'flies': len(spots), 'repair': repair,
                      'fidelite': {k: v['distance'] for k, v in fid.items()},
                      'final': {k: v['distance_rip'] for k, v in final_fid.items()}, 'tiles': sum(counts.values())}, indent=1))


if __name__ == '__main__':
    build()
