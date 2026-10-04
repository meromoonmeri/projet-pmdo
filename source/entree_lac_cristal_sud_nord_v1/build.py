"""Entrée Lac Cristallin sud -> nord V1 (ELC1) — format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Biome choisi par l'utilisateur : Lac Cristallin / Crystal Crossing (`lakecrystalpmdsky.png`, `D17P34A`), décliné en
trilogie complète de 3 cartes :
- ELC1 : Entrée de donjon sud -> nord (ce lot) ;
- FLC1 : Fin de donjon / Sanctuaire & Arène de boss ;
- ZLC1 : Zone ouverte / Carrefour & Belvédères des Îlots Cristallins.

Méthode « textures canoniques » = rendu généré RÉFÉRENCÉ : le rip `lakecrystalpmdsky.png` (D17P34A)
est passé au générateur comme image de référence.
Bruts (voir manifest.json -> generation, prompts complets) :
- decor_magenta.png : décor complet 4:3 (1200 x 896), lac souterrain peint en magenta #FF00FF, chaussée et esplanade
  de dalles cristallines cyan au centre, îlots hexagonaux dans le lac, arche de piliers de cristal et ouverture
  sombre au nord (fidélité au rip : dalles = 8,0 ; cristaux sombres = 16,7 ; piliers = 1,5 ; seuil 35) ;
- sol_complet.png : dallage cristallin cyan complet (1200 x 896) généré depuis le rip (distance dalles = 9,2 < 35) ;
- poses_lac_cristal.png : planche sur magenta #FF00FF de gouttes/ronds d'eau cristalline (rangée 1, 6 poses) et
  d'éclats prismatiques luminescents (rangée 2, 6 poses).
Normalisation UNIFORME x(576/896) puis recadrage centré à 768 ; réduction par classe (down_class).
Calques fixes (8) : sol_complet, dalles, reflets, rebords, cristaux, ilots, piliers, profondeur.
Animations, chacune sur son calque (5) :
- eau du lac souterrain « façon rivière Métano », COULEURS EXACTES du rip `lakecrystalpmdsky.png` sans liseré clair
  contre les rives (`bande = (55, 103, 143)` touche la rive), 4 x 10 ticks ;
- lueur cristalline sous-marine : cœur + 8 anneaux aux 9 couleurs cyan/bleu exactes du rip qui respirent, 12 x 10 ticks ;
- scintillements `Metano_Town_River_Sparkles` NATIFS, 4 x 10 ticks ;
- gouttes cristallines qui tombent et ronds dans l'eau : 6 poses générées réduites x1/8, 24 x 5 ticks ;
- éclats prismatiques flottants : 6 poses générées réduites à 11 x 11 px, pulsation et boucles de Lissajous, 48 x 5 ticks.
Scène : PPCM(40, 120, 240) = 240 ticks = 4 s.
Lancer : .venv/bin/python source/entree_lac_cristal_sud_nord_v1/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
REF_NAME = 'lakecrystalpmdsky.png'
REF = R / REF_NAME
OUT = R / 'renders/entree_lac_cristal_sud_nord_v1'
STAGE = R / '.cache/entree_lac_cristal_sud_nord_v1/entree_lac_cristal_sud_nord'
NAMESPACE = 'entree_lac_cristal_sud_nord'
ASSET = 'elc1_entree_lac_cristal'
PFX = 'ELC1'
W, H = 768, 576                      # 4:3, 96 x 72 cases
SRC = (1200, 896)
WATER_PHASES, WATER_TICKS = 4, 10
GLOW_PHASES, GLOW_TICKS = 12, 10     # 120 ticks
DROP_PHASES, DROP_TICKS = 24, 5      # 120 ticks
ANIM_PHASES, ANIM_TICKS = 48, 5      # 240 ticks = 4 s
LOOP_TICKS = 240

GEN = [
    {'file': 'decor_magenta.png',
     'images': [REF_NAME],
     'prompt':
     'Use EXACTLY the same 2D Nintendo DS pixel-art style, palette, and textures as the reference image (Pokemon '
     'Mystery Dungeon Explorers of Sky, Crystal Lake / Crystal Crossing): same glowing cyan-blue geometric crystal '
     'floor tiles with bright aqua cross-shaped light reflections (around RGB 120, 223, 248), same jagged dark-teal '
     'and slate-blue pointed crystal clusters lining the platform edges (around RGB 42, 106, 144), and same tall '
     'hexagonal ice-blue and white-highlighted crystal pillars and flat hexagonal crystal slabs emerging from the '
     'water. Make a NEW top-down WIDE 4:3 landscape map (1200x896) for a DUNGEON ENTRANCE (south to north): the '
     'player arrives at the SOUTH (bottom center) on a glowing cyan crystal causeway bordered by jagged dark-teal '
     'crystal spikes; the causeway opens into a wide central crystal platform; at the NORTH (top center) of the '
     'platform stands a grand archway carved into giant hexagonal cyan crystal pillars with a pitch-black cavern '
     'doorway (RGB 8, 12, 20) in the center, and the walkable crystal floor reaches the dark doorway completely dry '
     'with NO water in front of it. To the left and right of the central crystal platform, a vast underground lake '
     'fills the cavern — IMPORTANT: fill the ENTIRE lake water surface with flat solid pure magenta #FF00FF '
     '(RGB 255, 0, 255) with crisp pixel edges, no ripples, no caustics, and no gradients on the magenta, while '
     'placing several isolated hexagonal cyan crystal pillars and flat hexagonal crystal islets standing inside the '
     'magenta lake on both sides. No characters, no text, no UI, no border.'},
    {'file': 'sol_complet.png',
     'images': [REF_NAME],
     'prompt':
     'Use EXACTLY the same 2D Nintendo DS pixel-art style, palette, and textures as the central walkable floor of '
     'the reference image (Pokemon Mystery Dungeon Explorers of Sky, Crystal Lake / Crystal Crossing): make a WIDE '
     '4:3 image (1200x896) covered edge-to-edge ONLY with the flat walkable glowing cyan-blue geometric crystal tile '
     'floor texture with repeating aqua diamond/cross light reflections (around RGB 120, 223, 248) and subtle darker '
     'cyan tile seams. Remove all water, all dark crystal spikes, and all pillars — only the seamless flat walkable '
     'glowing cyan crystal floor across the entire 1200x896 frame. No characters, no text, no UI, no border.'},
    {'file': 'poses_lac_cristal.png',
     'images': [REF_NAME],
     'prompt':
     '2D Nintendo DS pixel-art sprite sheet on a flat solid pure magenta #FF00FF (RGB 255, 0, 255) background, '
     'matching the exact cyan and ice-blue pixel-art palette of the reference image (Pokemon Mystery Dungeon '
     'Explorers of Sky, Crystal Lake). 2 rows x 6 columns of small isolated sprites with wide pure magenta spacing '
     'between every sprite: Row 1 (top row): 6 poses of a pale cyan water drop falling and then expanding into a '
     'thin cyan concentric ripple ring on water (drop, stretched drop, tiny splash crown, small ring, medium ring, '
     'large thin ring). Row 2 (bottom row): 6 poses of a floating luminescent ice-cyan crystal spark / diamond light '
     'mote pulsing softly (tiny cyan dot, small diamond spark, medium 4-pointed crystal star, bright white-cyan '
     'cross sparkle, fading diamond, tiny glint). Crisp pixel art, no anti-aliasing against the #FF00FF magenta '
     'background, no grid lines, no text, no borders.'},
]

# Couleurs EXACTES de l'eau du rip lakecrystalpmdsky.png (mesurées dans la bordure d'eau du rip).
# Bande sombre contre la rive : (55, 103, 143) ; surface : (55, 111, 151) ; maille caustique : (47, 151, 191).
# Aucun liseré blanc/clair contre la rive (contrainte utilisateur : bande sombre au contact des berges/cristaux).
WPAL = {'surface': (55, 111, 151), 'bande': (55, 103, 143), 'accent': (47, 151, 191)}

# Lueur sous-marine : cœur + 8 anneaux aux 9 couleurs cyan/bleu EXACTES présentes dans lakecrystalpmdsky.png.
GLOW = [
    (135, 223, 239), (119, 207, 231), (103, 183, 215),
    (79, 167, 215),  (63, 159, 191),  (55, 135, 183),
    (47, 135, 183),  (47, 127, 175),  (47, 119, 167),
]
GLOW_RING_PX = 4
GLOW_BREATH, GLOW_WOBBLE = 0.04, 0.02

# Fenêtres des 6 poses de gouttes/ronds (rangée 1) et des 6 poses d'éclats cristallins (rangée 2) sur poses_lac_cristal.png.
DROP_WINS = [
    ('goutte', 175, 122, 128),
    ('goutte_etiree', 180, 363, 160),
    ('eclaboussure', 180, 602, 128),
    ('rond_0', 180, 850, 144),
    ('rond_1', 180, 1091, 192),
    ('rond_2', 180, 1332, 240),
]
MOTE_WINS = [
    (539, 121), (540, 363), (538, 604), (539, 850), (538, 1091), (538, 1333)
]
DROP_SEQ = (
    [('goutte', -18), ('goutte', -12), ('goutte_etiree', -6), ('goutte_etiree', -2),
     ('eclaboussure', 0), ('eclaboussure', 0),
     ('rond_0', 0), ('rond_0', 0), ('rond_0', 0),
     ('rond_1', 0), ('rond_1', 0), ('rond_1', 0), ('rond_1', 0),
     ('rond_2', 0), ('rond_2', 0), ('rond_2', 0), ('rond_2', 0)] + [None] * 7
)
assert len(DROP_SEQ) == DROP_PHASES


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
reduce_pose, FLY_PULSE, firefly_frames = EMF.reduce_pose, EMF.FLY_PULSE, EMF.firefly_frames


def paste(frame, spr, cx, cy, clip=None):
    hh, ww = spr.shape[:2]; y0, x0 = int(round(cy)) - hh // 2, int(round(cx)) - ww // 2
    ys0, xs0 = max(0, -y0), max(0, -x0); ys1, xs1 = min(hh, H - y0), min(ww, W - x0)
    if ys1 <= ys0 or xs1 <= xs0:
        return
    s = spr[ys0:ys1, xs0:xs1]; m = s[..., 3] > 0
    if clip is not None:
        m &= clip[y0 + ys0:y0 + ys1, x0 + xs0:x0 + xs1]
    frame[y0 + ys0:y0 + ys1, x0 + xs0:x0 + xs1][m] = s[m]

PALETTE_GROUPS = {
    'plateforme': (['sol_complet', 'dalles', 'reflets', 'rebords'], 96),
    'piliers': (['piliers', 'ilots'], 48),
    'cristaux': (['cristaux'], 32),
    'profondeur': (['profondeur'], 12),
}
STATIC = ['dalles', 'reflets', 'rebords', 'cristaux', 'ilots', 'piliers', 'profondeur']

# Couleurs d'eau exactes de la bordure du rip lakecrystalpmdsky.png (pour les exclure lors de la mesure des cristaux).
_REF_ARR = rgb(REF)
_WBOX = np.zeros(_REF_ARR.shape[:2], bool)
_WBOX[:50, :] = True; _WBOX[:, :20] = True; _WBOX[:, -20:] = True
RIP_WATER_COLS = np.unique(_REF_ARR[_WBOX].reshape(-1, 3), axis=0)
_WATER_LUT = np.zeros(256 * 256 * 256, bool)
for _c in RIP_WATER_COLS:
    _r0, _r1 = max(0, int(_c[0]) - 2), min(255, int(_c[0]) + 2) + 1
    _g0, _g1 = max(0, int(_c[1]) - 2), min(255, int(_c[1]) + 2) + 1
    _b0, _b1 = max(0, int(_c[2]) - 2), min(255, int(_c[2]) + 2) + 1
    _rr, _gg, _bb = np.mgrid[_r0:_r1, _g0:_g1, _b0:_b1]
    _WATER_LUT[(_rr << 16) | (_gg << 8) | _bb] = True


def open_(m, it):
    p = it + 1
    return nd.binary_opening(np.pad(m, p, mode='edge'), iterations=it)[p:-p, p:-p]


# ---------------------------------------------------------------- fidélité au rip (lakecrystalpmdsky.png)
def materials(a):
    a_i = a.astype(int)
    r, g, b = a_i.transpose(2, 0, 1); lum = a_i @ [.299, .587, .114]
    mag = (r - g > 60) & (b - g > 60)
    dark = (lum < 32) & ~mag
    is_w = _WATER_LUT[(r << 16) | (g << 8) | b]
    fg = ~mag & ~dark & ~is_w
    dalles = fg & (lum > 155) & (b > 205) & (g > 180)
    cristaux = fg & (lum <= 135)
    piliers = fg & ~dalles & ~cristaux
    return {'dalles_cristal': dalles, 'cristaux_sombres': cristaux, 'piliers_cristal': piliers}


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
    """Remplace tout pixel sombre ou magenta éventuel par un pavage du cœur cristallin f[280:620, 360:840]."""
    r, g, b = f.transpose(2, 0, 1); lum = f @ [.299, .587, .114]
    bad = (lum < 95) | (b < 150) | ((r > 190) & (b > 190) & (g < 100))
    bad = nd.binary_dilation(bad, iterations=2)
    out = f.copy(); patch = f[280:620, 360:840]
    ph, pw = patch.shape[:2]; yy, xx = np.nonzero(bad)
    out[yy, xx] = patch[yy % ph, xx % pw]
    return out, {'pixels_remplaces': int(bad.sum()), 'patch_source': [360, 280, 840, 620]}


# ---------------------------------------------------------------- segmentation (pleine résolution 1200 x 896)
def classify(a):
    r, g, b = a.transpose(2, 0, 1); lum = a @ [.299, .587, .114]
    hh, ww = lum.shape; yy, xx = np.mgrid[:hh, :ww]

    # 1. Eau : magenta pur + frange violette dans un rayon de 10 px, dilatée de 2 px
    mag_pure = (r > 190) & (b > 190) & (g < 100)
    mag_zone = nd.binary_dilation(mag_pure, iterations=10)
    mag_fringe = mag_zone & (((b > g + 8) & (r > g + 15)) | ((r - g) + (b - g) > 35))
    water = nd.binary_dilation(keep_large(mag_pure, 1000) | mag_fringe, iterations=2)

    # 2. Plateforme principale centrale vs îlots hexagonaux isolés dans le lac
    non_w = ~water
    lbl, n = nd.label(non_w)
    sizes = nd.sum(non_w, lbl, range(1, n + 1))
    main_plat = (lbl == (int(np.argmax(sizes)) + 1))
    ilots = non_w & ~main_plat

    # 3. Profondeur (ouverture sombre de la grotte au nord) et seuil praticable juste devant
    dark = main_plat & (lum < 42) & (yy < 220) & (xx > 510) & (xx < 690)
    profondeur = nd.binary_fill_holes(close_(keep_large(dark, 500), 3)) & main_plat
    py_max = int(np.nonzero(profondeur)[0].max())
    seuil_walk = main_plat & (yy >= py_max - 2) & (yy <= 265) & (xx >= 530) & (xx <= 670) & ~profondeur

    # 4. Piliers hexagonaux et arche cristalline du nord
    pillar_zone = main_plat & ~profondeur & ~seuil_walk & (
        (yy < 200) | ((yy < 310) & ((xx < 455) | (xx > 745)))
    )
    piliers = nd.binary_fill_holes(close_(keep_large(pillar_zone, 300), 2)) & main_plat & ~profondeur & ~seuil_walk

    # 5. Cristaux sombres (pointes bleu-sarcelle foncé sur le pourtour et rosettes intérieures)
    rem = main_plat & ~profondeur & ~piliers
    cristaux_raw = rem & (lum < 142) & ~seuil_walk
    cristaux = nd.binary_fill_holes(close_(keep_large(cristaux_raw, 80), 2)) & rem & ~seuil_walk

    # 6. Rebords biseautés de la plateforme
    rem2 = rem & ~cristaux
    d_edge = nd.distance_transform_edt(~(water | piliers))
    rebords = rem2 & (d_edge <= 18) & ~seuil_walk & (yy < 840)
    rem3 = rem2 & ~rebords

    # 7. Dalles cristallines praticables vs reflets aqua lumineux (praticables aussi)
    reflets = rem3 & (lum > 218) & (g > 235) & (b > 245)
    dalles = rem3 & ~reflets

    return dict(water=water, profondeur=profondeur, piliers=piliers, ilots=ilots,
                cristaux=cristaux, rebords=rebords, reflets=reflets, dalles=dalles)


# ---------------------------------------------------------------- animations d'eau, lueur, gouttes et éclats
def lake_water(water, visible):
    """Eau du lac cristallin : structure rivière Métano (4 x 10 ticks), couleurs exactes du rip lakecrystalpmdsky.png,
    sans liseré clair contre les rives (`bande = (55, 103, 143)` touche la rive)."""
    d = nd.distance_transform_edt(visible); yy, xx = np.mgrid[:H, :W]
    jag = nd.gaussian_filter(np.random.default_rng(9).random((H, W)), 1.0); jag = (jag - jag.min()) / np.ptp(jag)
    frames = []
    for t in range(WATER_PHASES):
        ph = 2 * np.pi * t / WATER_PHASES
        n = 0.6 * np.sin(yy * 0.23 + xx * 0.08 - ph) + 0.4 * np.sin(yy * 0.09 - xx * 0.19 + 1.3 - ph)
        T = 4.5 + 1.1 * n; jr = np.roll(jag, t * 2, axis=0); fringe = T + 0.6 + 2.6 * jr
        a = np.zeros((H, W, 4), 'uint8'); a[..., 3] = 255; a[..., :3] = WPAL['surface']
        a[d <= fringe] = (*WPAL['bande'], 255)
        a[(d <= fringe) & (jr > 0.62)] = (*WPAL['accent'], 255)
        a[d <= T] = (*WPAL['bande'], 255)
        a[~water] = 0; a[water & ~visible] = (*WPAL['bande'], 255)
        frames.append(a)
    return frames, d


def glow_centres(visible):
    """Deux foyers de lueur cristalline sous-marine (bassin gauche et bassin droit), au large des berges."""
    centres = []
    for x0, x1 in ((0, W // 2 - 40), (W // 2 + 40, W)):
        sub = np.zeros_like(visible); sub[90:H - 90, x0:x1] = visible[90:H - 90, x0:x1]
        dt = nd.distance_transform_edt(sub)
        cy, cx = np.unravel_index(int(np.argmax(dt)), dt.shape)
        centres.append([int(cx), int(cy), 54, 42])
    return centres


def glow_frames(visible, centres, ts=range(GLOW_PHASES)):
    yy, xx = np.mgrid[:H, :W]; frames = []
    for t in ts:
        ph = 2 * np.pi * t / GLOW_PHASES; a = np.zeros((H, W, 4), 'uint8')
        for cx, cy, rx, ry in centres:
            dx, dy = (xx - cx) / rx, (yy - cy) / ry
            rho = np.hypot(dx, dy) * (1 + GLOW_WOBBLE * np.sin(5 * np.arctan2(dy, dx) - ph)) / (1 + GLOW_BREATH * np.sin(ph))
            core = rho < 1
            ring = np.ceil(nd.distance_transform_edt(~core) / GLOW_RING_PX).astype(int)
            for i, c in enumerate(GLOW):
                a[visible & (ring == i)] = (*c, 255)
        frames.append(a)
    return frames


def extract_crystal_poses(path):
    """Extrait les 6 poses de gouttes/ronds (rangée 1) et les 6 poses d'éclats cristallins (rangée 2)."""
    src = rgb(path); r, g, b = src.transpose(2, 0, 1)
    bg = ((r > 180) & (b > 180) & (g < 120)) | ((r - g > 25) & (b - g > 25))
    fg_px = src[~bg]
    q = Image.fromarray(fg_px.reshape(-1, 1, 3).astype('uint8')).quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    pal = np.array(q.getpalette()[:24], float).reshape(-1, 3)
    drops = {nm: reduce_pose(src, bg, cy, cx, win, 8, pal, 0.22) for nm, cy, cx, win in DROP_WINS}
    motes = [reduce_pose(src, bg, cy, cx, 176, 16, pal, 0.12) for cy, cx in MOTE_WINS]
    return drops, motes, pal


def drop_frames(poses, emitters, visible, ts=range(DROP_PHASES)):
    frames = [np.zeros((H, W, 4), 'uint8') for _ in ts]
    for cx, cy, off in emitters:
        for i, t in enumerate(ts):
            st = DROP_SEQ[(t + off) % DROP_PHASES]
            if st is None:
                continue
            name, dy = st
            paste(frames[i], poses[name], cx, cy + dy, None if name.startswith('goutte') else visible)
    return frames


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
    o.update(Name={'DefaultText': 'Entree Lac Cristallin - sud vers nord (4:3)', 'LocalTexts': {}}, AssetName=ASSET,
             Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0},
             ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Rendu genere 4:3 reference sur le rip Crystal Lake / Crystal Crossing '
                     '(lakecrystalpmdsky.png, D17P34A) ; lac facon Metano sans lisere (couleurs exactes du rip), '
                     'lueur cristalline sous-marine, scintillements Metano natifs, gouttes et eclats generes. '
                     'Collisions de base a verifier. Seuil non raccorde.')
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
  <Name>Entree Lac Cristallin sud-nord 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : entree de donjon du Lac Cristallin au format 4:3 (ref. rip Crystal Lake D17P34A), lac facon Metano aux couleurs du rip, lueur, gouttes et eclats cristallins animes. Pas une aventure jouable.</Description>
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
    ANIMS = ['eau', 'lueur', 'scintillements', 'gouttes', 'eclats']
    if OUT.exists():
        for d in ['calques', 'animation', 'poses', 'masques', 'review']:
            shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['calques', 'poses', 'masques', 'review'] + [f'animation/{x}' for x in ANIMS]:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    a = rgb(RAW / 'decor_magenta.png'); f0 = rgb(RAW / 'sol_complet.png'); ref = rgb(REF)
    assert a.shape[:2] == f0.shape[:2] == (SRC[1], SRC[0])
    f, repair = repair_ground(f0)
    m = classify(a)
    order = ['water', 'profondeur', 'piliers', 'ilots', 'cristaux', 'rebords', 'reflets', 'dalles']
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
    centres = glow_centres(visible)
    gf = glow_frames(visible, centres)

    fams = BM.sparkle_families(); taken = np.zeros((H, W), bool)
    sf = [np.zeros((H, W, 4), 'uint8') for _ in range(WATER_PHASES)]; sparkles = []
    for fi, (name, frames) in enumerate(fams.items()):
        hh, ww = frames[0].shape[:2]
        for (y, x) in place(visible & (dist > 6), (hh, ww), 3, 81 + fi, taken, core=8):
            sparkles.append({'famille': name, 'xy': [x, y]})
            for t in range(WATER_PHASES):
                mm = frames[t][..., 3] > 0; sf[t][y:y+hh, x:x+ww][mm] = frames[t][mm]
    for arr in sf:
        arr[~visible] = 0

    drops, motes, pose_pal = extract_crystal_poses(RAW / 'poses_lac_cristal.png')
    for i, (nm, _, _, _) in enumerate(DROP_WINS):
        Image.fromarray(drops[nm]).save(OUT / 'poses' / f'{PFX}_goutte_{i}_{nm}.png')
    for i, p in enumerate(motes):
        Image.fromarray(p).save(OUT / 'poses' / f'{PFX}_eclat_{i}.png')

    # Gouttes : 8 points d'impact sur l'eau visible loin des berges
    cand_d = np.argwhere((visible & (dist > 18))[50:H - 50, 40:W - 40]) + [50, 40]
    emitters, used_d = [], []
    for y, x in cand_d[np.random.default_rng(23).permutation(len(cand_d))]:
        if all(abs(x - ux) > 70 or abs(y - uy) > 70 for uy, ux in used_d):
            used_d.append((y, x)); emitters.append([int(x), int(y), (len(emitters) * 3) % DROP_PHASES])
        if len(emitters) == 8:
            break
    df = drop_frames(drops, emitters, visible)

    # Éclats prismatiques : 14 points au-dessus des cristaux, piliers et îlots
    crystal_zone = (ex['cristaux'] | ex['piliers'] | ex['ilots']) & ~nd.binary_dilation(ex['profondeur'], iterations=6)
    cand_m = np.argwhere(crystal_zone[28:H - 28, 28:W - 28]) + [28, 28]
    spots, used_m = [], []
    for y, x in cand_m[np.random.default_rng(37).permutation(len(cand_m))]:
        if all(abs(x - ux) > 48 or abs(y - uy) > 48 for uy, ux in used_m):
            used_m.append((y, x)); spots.append((int(x), int(y), (len(spots) * 5) % ANIM_PHASES, 4 + (len(spots) % 3) * 2))
        if len(spots) == 14:
            break
    ef = firefly_frames(motes, spots)

    anim = {
        'eau': (wf, WATER_TICKS),
        'lueur': (gf, GLOW_TICKS),
        'scintillements': (sf, WATER_TICKS),
        'gouttes': (df, DROP_TICKS),
        'eclats': (ef, ANIM_TICKS),
    }
    order_names = ['eau', 'lueur', 'scintillements', 'gouttes', 'sol_complet'] + STATIC + ['eclats']
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

    walk_px = (layers['dalles'][..., 3] == 255) | (layers['reflets'][..., 3] == 255)
    blocked = cell_grid(~walk_px); gh_, gw_ = blocked.shape
    pxs = np.nonzero(walk_px[H - 8])[0]; med = int(np.median(pxs)) // 8
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
                   duration=round(step * 1000 / 60), loop=0, lossless=True, method=0)
    col = scenes[0].copy(); ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    for y, x in zip(*np.nonzero(blocked)):
        dr.rectangle([x*8, y*8, x*8+7, y*8+7], fill=(220, 40, 40, 90))
    for (qx, qy), c in ((entry_px, (255, 230, 40, 255)), (threshold_px, (60, 220, 255, 255))):
        dr.rectangle([qx, qy, qx + 15, qy + 15], outline=c, width=2)
    col.alpha_composite(ov); col.save(OUT / 'review' / f'{PFX}_collisions_marqueurs.png')

    sheet = Image.new('RGBA', (6 * 68, 2 * 68), (35, 78, 110, 255))
    drop_list = [drops[nm] for nm, _, _, _ in DROP_WINS]
    for r_, seq in enumerate((drop_list, motes)):
        for i, p in enumerate(seq):
            im = Image.fromarray(p); sc = max(1, 60 // max(im.size))
            sheet.alpha_composite(im.resize((im.width * sc, im.height * sc), Image.Resampling.NEAREST), (i * 68 + 4, r_ * 68 + 4))
    sheet.save(OUT / 'review' / f'{PFX}_planche_poses.png')

    write_ora(OUT / f'{PFX}_entree_lac_cristal_calques.ora',
              {f'{i:02d}_{t}' + ('_f00' if len(fr) > 1 else ''): fr[0] for i, (t, fr, _) in enumerate(stack_named)})
    counts = ground_project([(t.replace('_', ' ') + (f' {len(fr)} phases' if len(fr) > 1 else ''), fr, tk)
                             for t, fr, tk in stack_named], blocked, entry_px, threshold_px, gfx, tools)

    fid = fidelity(a, ref)
    final_fid = {}
    for k, nm in (('dalles_cristal', 'dalles'), ('cristaux_sombres', 'cristaux'), ('piliers_cristal', 'piliers')):
        lay = layers[nm]; px = lay[lay[..., 3] == 255][:, :3].astype(float)
        sel = materials(px.reshape(-1, 1, 3))[k][:, 0]
        px = px[sel] if sel.sum() > 50 else px
        final_fid[k] = {'calque': nm, 'rgb': [round(float(v), 1) for v in px.mean(0)],
                        'distance_rip': round(float(np.linalg.norm(px.mean(0) - np.array(fid[k]['rip_rgb']))), 1)}
    raw_inputs = [{'file': f'source/entree_lac_cristal_sud_nord_v1/bruts/{g["file"]}', 'sha256': sha(RAW / g['file']),
                   'size': list(Image.open(RAW / g['file']).size), 'statut': 'retenu'} for g in GEN]
    manifest = {
        'lot': 'entree_lac_cristal_sud_nord_v1', 'prefix': PFX, 'format': '4:3 vaste', 'size_px': [W, H],
        'grid_8px': [W // 8, H // 8], 'base': 'branche de session (arena/01a1024d-projet-pmdo) ; aucun emprunt aux branches soeurs',
        'biome': 'Lac Cristallin / Crystal Crossing (lakecrystalpmdsky.png, D17P34A), choisi par l utilisateur (trilogie 3 maps)',
        'method': 'textures canoniques = rendu genere REFERENCE : rip lakecrystalpmdsky.png passe au generateur ; '
                  'decor complet sur magenta (lac = magenta), sol cristallin complet et planche gouttes/eclats sur magenta',
        'reference_da': {'file': REF.name, 'sha256': sha(REF), 'titre': 'Crystal Lake / Crystal Crossing (D17P34A, PMD Explorers of Sky)'},
        'generation': GEN,
        'raw_inputs': raw_inputs,
        'sol_complet_reparation': repair,
        'fidelite_rip': {'methode': 'moyenne RGB par matiere, meme classifieur pixel sur le rip et sur le brut ; distance euclidienne',
                         'brut': fid, 'calques_finaux': final_fid},
        'normalization': {'scale': JM.SCALE, 'scaled': [JM.SCALED_W, H], 'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
                          'methode': 'moyenne ponderee par classe (BOX), attribution exclusive par poids maximal',
                          'palettes': {g: {'calques': k, 'couleurs': n} for g, (k, n) in PALETTE_GROUPS.items()}},
        'segmentation': 'eau = magenta pur + frange dilatee 2 px ; profondeur = ouverture sombre (lum<42) au nord ; '
                        'piliers = arche cristalline et couronne de piliers hexagonaux au nord ; ilots = piliers et dalles '
                        'hexagonales isoles dans le lac ; cristaux = pointes de cristal bleu-sarcelle sombre (lum<142) ; '
                        'rebords = dalles biseautees en bordure de plateforme ; reflets = croix lumineuses aqua (lum>218) ; '
                        'dalles = sol cristallin cyan praticable',
        'layers': layer_list,
        'water': {'phases': WATER_PHASES, 'frame_length_ticks': WATER_TICKS,
                  'couleurs': {k: list(v) for k, v in WPAL.items()},
                  'modele': 'structure et cadence riviere Metano, couleurs EXACTES du rip lakecrystalpmdsky.png, sans lisere clair de rive',
                  'origine': 'pixels recalcules aux couleurs canoniques du rip, pas de tuiles natives'},
        'glow': {'phases': GLOW_PHASES, 'frame_length_ticks': GLOW_TICKS,
                 'couleurs': [list(c) for c in GLOW], 'ring_px': GLOW_RING_PX, 'centres': centres,
                 'origine': 'anneaux de lueur sous-marine aux 9 couleurs cyan/bleu exactes du rip'},
        'sparkles': {'source': 'source/eau_metano/natifs/Metano_Town_River_Sparkles.tile', 'placements': sparkles,
                     'origine': 'pixels et couleurs Metano NATIFS inchanges'},
        'gouttes': {'poses': len(DROP_WINS), 'sequence': [list(s) if s else None for s in DROP_SEQ],
                    'emitters': emitters, 'phases': DROP_PHASES, 'frame_length_ticks': DROP_TICKS,
                    'origine': 'dessin GENERE sur poses_lac_cristal.png (rangee 1), reduit x1/8'},
        'eclats': {'poses': len(motes), 'taille_px': list(motes[0].shape[:2]), 'reduction': 'fenetre 176 px -> 11 px (x1/16)',
                   'pulsation': FLY_PULSE, 'points': [list(s) for s in spots], 'phases': ANIM_PHASES, 'frame_length_ticks': ANIM_TICKS,
                   'origine': 'dessin GENERE sur poses_lac_cristal.png (rangee 2) ; boucles de Lissajous et pulsation creees par nous'},
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'entry_px': entry_px, 'threshold_px': threshold_px, 'path_found_16x16': ok, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si > 25 % hors dalles et reflets cristallins de la plateforme centrale',
                   'seuil': 'bout nord de la plateforme cristalline, au pied sec de l ouverture sombre sous l arche de cristal'},
        'pmdo': {'target': '0.8.12', 'asset': ASSET, 'namespace': NAMESPACE, 'tiles_per_bank': counts, 'banks': list(counts),
                 'runtime_tested': False, 'warp': 'aucun'},
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    print(json.dumps({'sparkles': len(sparkles), 'entry': entry_px, 'threshold': threshold_px, 'blocked': int(blocked.sum()),
                      'walkable': int((~blocked).sum()), 'drops': len(emitters), 'motes': len(spots), 'repair': repair,
                      'fidelite': {k: v['distance'] for k, v in fid.items()},
                      'final': {k: v['distance_rip'] for k, v in final_fid.items()}, 'tiles': sum(counts.values())}, indent=1))


if __name__ == '__main__':
    build()
