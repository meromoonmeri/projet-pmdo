"""Entrée Lac Cristallin — Zone Zéro sud -> nord V1 (ELC1) — format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Biome choisi par l'utilisateur : Lac Cristallin (`lakecrystalpmdsky.png`, `D17P34A`) recoloré et animé façon
**Zone Zéro (Area Zero, Pokémon Écarlate et Violet)** avec **effet reflet de profondeur dans l'eau**, décliné en
trilogie complète de 3 cartes :
- ELC1 : Entrée de donjon sud -> nord (ce lot) ;
- FLC1 : Fin de donjon / Sanctuaire & Arène de boss (avec runes du monolithe qui pulsent d'une lumière subtile) ;
- ZLC1 : Zone ouverte / Carrefour & Belvédères des Îlots Cristallins.

Méthode « textures canoniques + passe cristaux Zone Zéro & reflet profondeur » :
- decor_magenta.png : décor complet 4:3 (1200 x 896) référencé sur `lakecrystalpmdsky.png` (fidélité brute au rip :
  dalles = 8,0 ; cristaux sombres = 16,7 ; piliers = 1,5 ; seuil 35) ;
- sol_complet.png et poses_lac_cristal.png : sol complet (1200 x 896) et planche de gouttes/éclats sur magenta ;
- Passe **Cristaux Zone Zéro (Pokémon Écarlate & Violet)** (`source/zone_zero_v2/haute_qualite.py`) : les cristaux,
  piliers, îlots, rebords et dalles quittent le bleu pour adopter la base blanche nacrée / quartz-améthyste de la
  Zone Zéro (`CRISTAL_TONS`, `CRISTAL_CONTOUR`), parcourue sur un calque dédié (`reflets_tera`, 24 x 10 ticks) par
  des bandes irisées arc-en-ciel Téra (`ARC_EN_CIEL` : rouge, orange, jaune, vert, cyan, bleu, mauve, rose) ;
- Passe **Eau abyssale & Reflet de profondeur des cristaux** :
  - `eau` (4 x 10 ticks) : dégradé abyssal profond en 5 paliers (du plateau immergé `(58, 92, 134)` jusqu'à l'abîme
    sombre `(18, 34, 62)`, bande sombre `(24, 44, 76)` au contact des rives sans aucun liseré blanc) ;
  - `reflet_profondeur` (24 x 10 ticks) : sous chaque pilier, îlot, amas de cristal et rebord de plateforme, la
    silhouette verticale et les facettes nacrées des cristaux se reflètent et plongent dans l'eau sur 44 px de
    profondeur avec ondulation sinusoïdale de l'eau et tramage de Bayer.
Calques fixes (8) : sol_complet, dalles, reflets, rebords, cristaux, ilots, piliers, profondeur.
Animations, chacune sur son calque (6) :
- `eau` : dégradé abyssal et onde de rive sans liseré clair, 4 x 10 ticks ;
- `reflet_profondeur` : reflet vertical immergé des cristaux plongeant dans la profondeur de l'eau, 24 x 10 ticks ;
- `scintillements` : `Metano_Town_River_Sparkles` natifs, 4 x 10 ticks ;
- `gouttes` : gouttes cristallines et ronds dans l'eau, 24 x 5 ticks ;
- `reflets_tera` : reflets irisés arc-en-ciel Téra (Zone Zéro) sur les cristaux blancs nacrés, 24 x 10 ticks ;
- `eclats` : éclats prismatiques flottants, 48 x 5 ticks.
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
DEPTH_PHASES, DEPTH_TICKS = 24, 10   # 240 ticks : reflet de profondeur ondulant
TERA_PHASES, TERA_TICKS = 24, 10     # 240 ticks : reflets arc-en-ciel Téra (Zone Zéro)
DROP_PHASES, DROP_TICKS = 24, 5      # 120 ticks
ANIM_PHASES, ANIM_TICKS = 48, 5      # 240 ticks
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

# ---------------------------------------------------------------- Palette Cristaux Zone Zéro (Pokémon Écarlate & Violet)
# Reprise de source/zone_zero_v2/haute_qualite.py : cristaux blancs nacrés / quartz-améthyste (NON bleus) + arc-en-ciel Téra.
BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
CRISTAL_TONS = [
    (150, 156, 196), (188, 194, 226), (220, 224, 244), (240, 242, 252), (255, 255, 255)
]
CRISTAL_CONTOUR = (92, 96, 140)
CRISTAL_SOMBRE_TONS = [
    (68, 72, 114), (96, 100, 144), (138, 144, 186), (184, 190, 224), (232, 236, 250)
]
DALLE_ZERO_TONS = [
    (168, 172, 206), (196, 200, 228), (220, 222, 244), (238, 238, 252), (252, 250, 255)
]
ARC_EN_CIEL = [
    ('rouge', (255, 96, 120)), ('orange', (255, 164, 88)), ('jaune', (255, 232, 104)), ('vert', (128, 232, 140)),
    ('cyan', (104, 222, 255)), ('bleu', (122, 140, 255)), ('mauve', (192, 118, 255)), ('rose', (255, 120, 210)),
]
BANDE_PERIODE, BANDE_LARGEUR, BANDE_PAS = 96, 34, 4

# ---------------------------------------------------------------- Eau abyssale & Reflet de profondeur des cristaux
# Bande sombre au contact de la rive : (24, 44, 76) (aucun liseré clair contre les berges).
# Dégradé de profondeur vers l'abîme : du talus immergé (58, 92, 134) jusqu'au fond abyssal (18, 34, 62).
WPAL = {
    'bande': (24, 44, 76),
    'accent': (72, 108, 152),
    'talus': (58, 92, 134),
    'moyen': (42, 72, 112),
    'profond': (28, 52, 88),
    'abime': (18, 34, 62),
}
# Couleurs du reflet vertical immergé des cristaux plongeant dans l'eau (du plus proche sous la surface au plus profond).
# Tous les tons restent aquatiques et plus sombres que les cristaux émergés (aucun liseré blanc aux rives).
REFLET_EAU_TONS = [
    (118, 146, 196),   # 0 : éclat de facette immergée sous la surface (opale-saphir)
    (94, 122, 174),    # 1 : reflet cristallin clair à faible profondeur
    (72, 98, 150),     # 2 : reflet cristallin moyen dans le talus
    (52, 76, 124),     # 3 : reflet profond indigo
    (34, 54, 96),      # 4 : racine cristalline se fondant dans l'abîme
]
REFLET_MAX_DY = 48

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
    'plateforme': (['sol_complet', 'dalles', 'reflets', 'rebords'], 64),
    'piliers': (['piliers', 'ilots'], 32),
    'cristaux': (['cristaux'], 24),
    'profondeur': (['profondeur'], 12),
}
STATIC = ['dalles', 'reflets', 'rebords', 'cristaux', 'ilots', 'piliers', 'profondeur']

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


# ---------------------------------------------------------------- fidélité brute au rip (lakecrystalpmdsky.png)
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

    mag_pure = (r > 190) & (b > 190) & (g < 100)
    mag_zone = nd.binary_dilation(mag_pure, iterations=10)
    mag_fringe = mag_zone & (((b > g + 8) & (r > g + 15)) | ((r - g) + (b - g) > 35))
    water = nd.binary_dilation(keep_large(mag_pure, 1000) | mag_fringe, iterations=2)

    non_w = ~water
    lbl, n = nd.label(non_w)
    sizes = nd.sum(non_w, lbl, range(1, n + 1))
    main_plat = (lbl == (int(np.argmax(sizes)) + 1))
    ilots = non_w & ~main_plat

    dark = main_plat & (lum < 42) & (yy < 220) & (xx > 510) & (xx < 690)
    profondeur = nd.binary_fill_holes(close_(keep_large(dark, 500), 3)) & main_plat
    py_max = int(np.nonzero(profondeur)[0].max())
    seuil_walk = main_plat & (yy >= py_max - 2) & (yy <= 265) & (xx >= 530) & (xx <= 670) & ~profondeur

    pillar_zone = main_plat & ~profondeur & ~seuil_walk & (
        (yy < 200) | ((yy < 310) & ((xx < 455) | (xx > 745)))
    )
    piliers = nd.binary_fill_holes(close_(keep_large(pillar_zone, 300), 2)) & main_plat & ~profondeur & ~seuil_walk

    rem = main_plat & ~profondeur & ~piliers
    cristaux_raw = rem & (lum < 142) & ~seuil_walk
    cristaux = nd.binary_fill_holes(close_(keep_large(cristaux_raw, 80), 2)) & rem & ~seuil_walk

    rem2 = rem & ~cristaux
    d_edge = nd.distance_transform_edt(~(water | piliers))
    rebords = rem2 & (d_edge <= 18) & ~seuil_walk & (yy < 840)
    rem3 = rem2 & ~rebords

    reflets = rem3 & (lum > 218) & (g > 235) & (b > 245)
    dalles = rem3 & ~reflets

    return dict(water=water, profondeur=profondeur, piliers=piliers, ilots=ilots,
                cristaux=cristaux, rebords=rebords, reflets=reflets, dalles=dalles)


# ---------------------------------------------------------------- Passe Cristaux Zone Zéro (Pokémon Écarlate & Violet)
def grade_area_zero_layer(arr, ramp, thresholds, contour=None):
    """Recolore un calque RGBA cyan en cristal blanc nacré / quartz-améthyste de la Zone Zéro selon la luminance
    de chaque facette, en préservant 100 % du dessin des facettes et des biseaux."""
    out = np.zeros_like(arr)
    al = arr[..., 3] == 255
    if not al.any():
        return out
    rgb_f = arr[..., :3].astype(float)
    lum = rgb_f @ [.299, .587, .114]
    lvl = np.digitize(lum, thresholds)
    for k, col in enumerate(ramp):
        m = al & (lvl == k)
        out[m, :3] = col
    if contour is not None:
        edge = al & (~nd.binary_erosion(al, iterations=1) | (lum < thresholds[0] - 18))
        out[edge & (lum < thresholds[1]), :3] = contour
    out[al, 3] = 255
    return out


def apply_area_zero_crystals(layers):
    """Applique la palette Cristaux Zone Zéro (blanc nacré / opale / quartz-améthyste, non bleu) à tous les calques
    cristallins tout en laissant `profondeur` intact."""
    out = {}
    for k, arr in layers.items():
        if k == 'profondeur':
            out[k] = arr.copy()
        elif k in ('piliers', 'ilots', 'rebords', 'sanctuaire'):
            out[k] = grade_area_zero_layer(arr, CRISTAL_TONS, [135, 168, 198, 224], contour=CRISTAL_CONTOUR)
        elif k == 'cristaux':
            out[k] = grade_area_zero_layer(arr, CRISTAL_SOMBRE_TONS, [82, 104, 122, 136], contour=(52, 56, 92))
        elif k == 'reflets':
            out[k] = grade_area_zero_layer(arr, DALLE_ZERO_TONS, [210, 220, 230, 240])
        else:  # sol_complet, dalles
            out[k] = grade_area_zero_layer(arr, DALLE_ZERO_TONS, [155, 178, 198, 216])
    return out


def reflet_tera_couleur(k, level):
    base = np.array(CRISTAL_TONS[level], float); c = np.array(ARC_EN_CIEL[k][1], float)
    mix = 0.68 if level <= 2 else 0.54
    return tuple(int(v) for v in np.clip(base * (1 - mix) + c * mix, 0, 255))


def tera_prism_frames(layers, crystal_keys=('piliers', 'ilots', 'cristaux', 'rebords'), ts=range(TERA_PHASES)):
    """Bandes diagonales irisées arc-en-ciel Téra (8 couleurs de la Zone Zéro) qui glissent sur les facettes
    des cristaux blancs nacrés, avec 24 phases x 10 ticks = 240 ticks."""
    body = np.zeros((H, W), bool)
    lum = np.zeros((H, W), float)
    for k in crystal_keys:
        if k not in layers:
            continue
        a = layers[k]; m = a[..., 3] == 255
        body |= m
        lum[m] = a[m, :3].astype(float) @ [.299, .587, .114]
    level = np.digitize(lum, [130, 165, 200, 230])
    shade = {(k, lv): reflet_tera_couleur(k, lv) for k in range(8) for lv in range(5)}
    yy, xx = np.mgrid[:H, :W]
    frames = []
    for t in ts:
        e = np.zeros((H, W, 4), 'uint8')
        s = ((xx - yy) + BANDE_PAS * t) % BANDE_PERIODE
        band = s < BANDE_LARGEUR
        edge = (s < 6) | (s >= BANDE_LARGEUR - 6)
        band &= ~edge | (BAYER4[yy % 4, xx % 4] < 0.5)
        # Trame douce de Bayer à l'intérieur de la bande pour laisser respirer le cristal blanc nacré
        band &= (BAYER4[(yy + t) % 4, xx % 4] < 0.65)
        hue = (((xx + yy) // 10) + t // 3) % 8
        on = band & body & (level >= 1)
        for k in range(8):
            for lv in range(1, 5):
                m = on & (hue == k) & (level == lv)
                e[m, :3] = shade[(k, lv)]; e[m, 3] = 255
        frames.append(e)
    return frames


# ---------------------------------------------------------------- Eau abyssale & Reflet de profondeur des cristaux
def lake_water(water, visible):
    """Eau abyssale en 5 paliers de profondeur + onde de rive sans liseré clair (`bande = (24, 44, 76)` au contact)."""
    d = nd.distance_transform_edt(visible); yy, xx = np.mgrid[:H, :W]
    jag = nd.gaussian_filter(np.random.default_rng(9).random((H, W)), 1.0); jag = (jag - jag.min()) / np.ptp(jag)
    frames = []
    for t in range(WATER_PHASES):
        ph = 2 * np.pi * t / WATER_PHASES
        n = 0.6 * np.sin(yy * 0.23 + xx * 0.08 - ph) + 0.4 * np.sin(yy * 0.09 - xx * 0.19 + 1.3 - ph)
        T = 4.5 + 1.1 * n; jr = np.roll(jag, t * 2, axis=0); fringe = T + 0.6 + 2.6 * jr
        a = np.zeros((H, W, 4), 'uint8'); a[..., 3] = 255
        # Dégradé abyssal du large vers les berges cristallines
        a[..., :3] = WPAL['abime']
        a[d <= 58 + 2.0 * n, :3] = WPAL['profond']
        a[d <= 34 + 1.6 * n, :3] = WPAL['moyen']
        a[d <= 16 + 1.3 * n, :3] = WPAL['talus']
        a[d <= fringe] = (*WPAL['bande'], 255)
        a[(d <= fringe) & (jr > 0.62)] = (*WPAL['accent'], 255)
        a[d <= T] = (*WPAL['bande'], 255)
        a[~water] = 0; a[water & ~visible] = (*WPAL['bande'], 255)
        frames.append(a)
    return frames, d


def crystal_depth_reflection_frames(layers, visible, ts=range(DEPTH_PHASES)):
    """Effet reflet de profondeur dans l'eau : sous chaque pilier, îlot, amas de cristal et rebord de plateforme,
    projette verticalement vers le bas dans l'eau (`dy = 3..48 px`) la silhouette inversée et les facettes des cristaux
    émergés (plus une teinte irisée Téra atténuée sous l'eau), en préservant intégralement la bande sombre de rive
    (`d <= 2.5`) sans aucun halo ni liseré blanc autour des berges."""
    cryst_mask = np.zeros((H, W), bool)
    cryst_lum = np.zeros((H, W), float)
    for k in ('rebords', 'cristaux', 'ilots', 'piliers', 'sanctuaire'):
        if k not in layers:
            continue
        a = layers[k]; m = a[..., 3] == 255
        cryst_mask |= m
        cryst_lum[m] = a[m, :3].astype(float) @ [.299, .587, .114]

    # Distance à la rive pour préserver la bande sombre de contact (aucun pixel clair au bord des rives)
    d_shore = nd.distance_transform_edt(visible)

    # Pour chaque pixel d'eau visible (y, x), chercher en remontant vers le nord le bord inférieur du cristal/rive
    # immédiatement au-dessus dans la même colonne x, et lire la facette symétrique (y_edge - dy)
    yy, xx = np.mgrid[:H, :W]
    land_y = np.where(cryst_mask, yy, -1000)
    edge_y = np.maximum.accumulate(land_y, axis=0)
    dy = yy - edge_y                                                    # distance verticale sous la rive/cristal
    mirror_y = np.clip(edge_y - (dy * 3 // 4), 0, H - 1)
    has_mirror = (dy >= 3) & (dy <= REFLET_MAX_DY) & cryst_mask[mirror_y, xx]
    mirror_lum = np.where(has_mirror, cryst_lum[mirror_y, xx], 0.0)

    # Teintes Téra sous-marines très douces (mélangées à 28 % avec REFLET_EAU_TONS[0..1] sur les facettes claires)
    tera_sub = {
        (k, lv): tuple(int(v) for v in np.clip(
            np.array(REFLET_EAU_TONS[lv], float) * 0.72 + np.array(ARC_EN_CIEL[k][1], float) * 0.28, 0, 255
        ))
        for k in range(8) for lv in (0, 1, 2)
    }

    frames = []
    for t in ts:
        ph = 2 * np.pi * t / DEPTH_PHASES
        a = np.zeros((H, W, 4), 'uint8')
        # Ondulation horizontale de l'eau (cisaillement sinusoïdal doux du reflet vertical)
        wave = np.sin(yy * 0.34 - ph + xx * 0.05)
        dx = np.round(1.5 * wave).astype(int)
        sx = np.clip(xx + dx, 0, W - 1)

        m_ref = (
            visible
            & (d_shore > 2.2)
            & (dy[yy, sx] >= 3)
            & (dy[yy, sx] <= REFLET_MAX_DY)
            & cryst_mask[mirror_y[yy, sx], sx]
        )
        dy_w = dy[yy, sx]
        mlum_w = mirror_lum[yy, sx]

        # Niveau de profondeur (0 = facette claire sous la surface .. 4 = fondu abyssal)
        facet_lvl = np.digitize(mlum_w, [135, 175, 210, 238])          # 0..4 (4 = facette très brillante)
        depth_step = np.digitize(dy_w, [9, 18, 28, 38])                # 0..4 selon la profondeur verticale dy
        lvl = np.clip(depth_step + (2 - facet_lvl // 2), 0, 4)

        # Fondu vertical progressif par tramage de Bayer + stries d'eau horizontales
        fade = (1.0 - (dy_w.astype(float) / (REFLET_MAX_DY + 4.0))) * (0.55 + 0.12 * facet_lvl)
        ripple_gap = ((yy + int(round(t / 3))) % 6 == 0) & (dy_w > 14)
        keep = m_ref & ~ripple_gap & (BAYER4[(yy + t // 2) % 4, xx % 4] < fade)
        for lv, col in enumerate(REFLET_EAU_TONS):
            sel = keep & (lvl == lv)
            a[sel, :3] = col; a[sel, 3] = 255

        # Reflet irisé Téra immergé dans l'eau (bande réfléchie en miroir sous les grands piliers/cristaux)
        s_ref = ((sx + yy) + BANDE_PAS * t) % BANDE_PERIODE
        tera_band = (s_ref < BANDE_LARGEUR) & (BAYER4[yy % 4, sx % 4] < 0.5)
        hue = (((sx - yy) // 10) + t // 3) % 8
        for k in range(8):
            for lv in (0, 1, 2):
                sel = keep & tera_band & (lvl == lv) & (facet_lvl >= 3) & (hue == k)
                a[sel, :3] = tera_sub[(k, lv)]

        frames.append(a)
    return frames


def extract_crystal_poses(path):
    """Extrait les 6 poses de gouttes/ronds (rangée 1) et les 6 poses d'éclats cristallins (rangée 2),
    recolorées aux tons nacrés/irisés de la Zone Zéro."""
    src = rgb(path); r, g, b = src.transpose(2, 0, 1)
    bg = ((r > 180) & (b > 180) & (g < 120)) | ((r - g > 25) & (b - g > 25))
    pal_drop = np.array([
        [150, 156, 196], [172, 182, 220], [196, 204, 236], [220, 224, 244],
        [238, 240, 252], [255, 255, 255], [226, 196, 244], [192, 228, 255]
    ], float)
    pal_mote = np.array([
        [188, 194, 226], [220, 224, 244], [240, 242, 252], [255, 255, 255],
        [255, 196, 232], [216, 182, 255], [182, 236, 255], [255, 240, 188]
    ], float)
    drops = {nm: reduce_pose(src, bg, cy, cx, win, 8, pal_drop, 0.22) for nm, cy, cx, win in DROP_WINS}
    motes = [reduce_pose(src, bg, cy, cx, 176, 16, pal_mote, 0.12) for cy, cx in MOTE_WINS]
    return drops, motes, pal_mote


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
        f_has = [a[..., 3].reshape(gh, 8, gw, 8).any(axis=(1, 3)) for a in frames]
        any_cell = np.any(f_has, axis=0)
        empty_ref = {'Sheet': bank.name, 'TexLoc': {'X': 0, 'Y': 0}}

        def cell(x, y, frames=frames, bank=bank, f_has=f_has, any_cell=any_cell, empty_ref=empty_ref):
            if not any_cell[y, x]:
                return []
            if len(frames) == 1:
                f = bank.add(Image.fromarray(frames[0][y*8:y*8+8, x*8:x*8+8]), x, y)
                return [f] if f else []
            p0 = frames[0][y*8:y*8+8, x*8:x*8+8]
            if all(np.array_equal(a[y*8:y*8+8, x*8:x*8+8], p0) for a in frames[1:]):
                f = bank.add(Image.fromarray(p0), x, y)
                return [f] if f else []
            fs = []
            for t_i, a in enumerate(frames):
                if not f_has[t_i][y, x]:
                    fs.append(empty_ref)
                else:
                    f = bank.add(Image.fromarray(a[y*8:y*8+8, x*8:x*8+8]), x, y)
                    fs.append(f if f else empty_ref)
            return [fs[0]] if all(f == fs[0] for f in fs) else fs
        layers.append(gfx.layer(f'{i:02d} {title}', gw, gh, cell, ticks)); banks.append(bank)
    layers.append(gfx.layer(f'{len(layers):02d} Vos elements avant-plan (Top)', gw, gh, draw=4))
    for bank in banks:
        bank.write(STAGE / f'Content/Tile/{bank.name}.tile')
    o.update(Name={'DefaultText': 'Entree Lac Cristallin Zone Zero - sud vers nord (4:3)', 'LocalTexts': {}}, AssetName=ASSET,
             Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0},
             ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Rendu 4:3 reference sur Crystal Lake (D17P34A) recolore en cristaux blancs nacres '
                     'et reflets arc-en-ciel Tera de la Zone Zero (Pokemon Ecarlate/Violet), avec eau abyssale et '
                     'reflet de profondeur immerge des cristaux.')
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
  <Name>Entree Lac Cristallin Zone Zero 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : entree de donjon du Lac Cristallin au format 4:3, cristaux blancs nacres et reflets arc-en-ciel Tera de la Zone Zero (Pokemon Ecarlate/Violet), eau abyssale et reflet de profondeur des cristaux.</Description>
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
    ANIMS = ['eau', 'reflet_profondeur', 'scintillements', 'gouttes', 'reflets_tera', 'eclats']
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
    raw_layers = {'sol_complet': rgba(down_full(f), ~water)}
    for k in STATIC:
        raw_layers[k] = rgba(cols[k], ex[k])
    # Passe Cristaux Zone Zéro (blanc nacré / opale / quartz-améthyste, non bleu)
    layers = apply_area_zero_crystals(raw_layers)
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
    rf_depth = crystal_depth_reflection_frames(layers, visible)
    tf_tera = tera_prism_frames(layers)

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

    drops, motes, _ = extract_crystal_poses(RAW / 'poses_lac_cristal.png')
    for i, (nm, _, _, _) in enumerate(DROP_WINS):
        Image.fromarray(drops[nm]).save(OUT / 'poses' / f'{PFX}_goutte_{i}_{nm}.png')
    for i, p in enumerate(motes):
        Image.fromarray(p).save(OUT / 'poses' / f'{PFX}_eclat_{i}.png')

    cand_d = np.argwhere((visible & (dist > 18))[50:H - 50, 40:W - 40]) + [50, 40]
    emitters, used_d = [], []
    for y, x in cand_d[np.random.default_rng(23).permutation(len(cand_d))]:
        if all(abs(x - ux) > 70 or abs(y - uy) > 70 for uy, ux in used_d):
            used_d.append((y, x)); emitters.append([int(x), int(y), (len(emitters) * 3) % DROP_PHASES])
        if len(emitters) == 8:
            break
    df = drop_frames(drops, emitters, visible)

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
        'reflet_profondeur': (rf_depth, DEPTH_TICKS),
        'scintillements': (sf, WATER_TICKS),
        'gouttes': (df, DROP_TICKS),
        'reflets_tera': (tf_tera, TERA_TICKS),
        'eclats': (ef, ANIM_TICKS),
    }
    order_names = ['eau', 'reflet_profondeur', 'scintillements', 'gouttes', 'sol_complet'] + STATIC + ['reflets_tera', 'eclats']
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

    sheet = Image.new('RGBA', (6 * 68, 2 * 68), (35, 52, 84, 255))
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
    raw_inputs = [{'file': f'source/entree_lac_cristal_sud_nord_v1/bruts/{g["file"]}', 'sha256': sha(RAW / g['file']),
                   'size': list(Image.open(RAW / g['file']).size), 'statut': 'retenu'} for g in GEN]
    manifest = {
        'lot': 'entree_lac_cristal_sud_nord_v1', 'prefix': PFX, 'format': '4:3 vaste', 'size_px': [W, H],
        'grid_8px': [W // 8, H // 8], 'base': 'branche de session (arena/01a1024d-projet-pmdo) ; aucun emprunt aux branches soeurs',
        'biome': 'Lac Cristallin / Zone Zero (lakecrystalpmdsky.png + cristaux blancs nacres Area Zero Pokemon Ecarlate/Violet)',
        'method': 'textures canoniques = rendu genere REFERENCE sur lakecrystalpmdsky.png + passe Cristaux Zone Zero '
                  '(base blanche nacree/quartz-amethyste + reflets arc-en-ciel Tera) + reflet de profondeur des cristaux dans l eau',
        'reference_da': {'file': REF.name, 'sha256': sha(REF), 'titre': 'Crystal Lake / Crystal Crossing (D17P34A, PMD Explorers of Sky)'},
        'generation': GEN,
        'raw_inputs': raw_inputs,
        'sol_complet_reparation': repair,
        'fidelite_rip': {'methode': 'moyenne RGB par matiere sur le brut genere avant la passe Cristaux Zone Zero ; distance euclidienne < 35',
                         'brut': fid},
        'cristaux_zone_zero': {
            'demande': 'les cristal faut pas qu il soit bleu mais comme celle de la zone zero dans pokemon scarlet et violet stp',
            'tons_base': [list(t) for t in CRISTAL_TONS],
            'tons_sombres': [list(t) for t in CRISTAL_SOMBRE_TONS],
            'tons_dalles': [list(t) for t in DALLE_ZERO_TONS],
            'contour': list(CRISTAL_CONTOUR),
            'arc_en_ciel': {k: list(c) for k, c in ARC_EN_CIEL},
            'phases': TERA_PHASES,
            'frame_length_ticks': TERA_TICKS,
        },
        'normalization': {'scale': JM.SCALE, 'scaled': [JM.SCALED_W, H], 'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
                          'methode': 'moyenne ponderee par classe (BOX), attribution exclusive par poids maximal',
                          'palettes': {g: {'calques': k, 'couleurs': n} for g, (k, n) in PALETTE_GROUPS.items()}},
        'layers': layer_list,
        'water': {'phases': WATER_PHASES, 'frame_length_ticks': WATER_TICKS,
                  'couleurs': {k: list(v) for k, v in WPAL.items()},
                  'modele': 'degrade abyssal en 5 paliers + onde de rive sans lisere clair (bande sombre au contact)'},
        'reflet_profondeur': {'phases': DEPTH_PHASES, 'frame_length_ticks': DEPTH_TICKS,
                              'tons': [list(c) for c in REFLET_EAU_TONS], 'max_dy_px': REFLET_MAX_DY,
                              'modele': 'projection verticale inversee et racines immergees des cristaux dans l eau avec ondulation sinusoïdale et tramage de Bayer'},
        'sparkles': {'source': 'source/eau_metano/natifs/Metano_Town_River_Sparkles.tile', 'placements': sparkles,
                     'origine': 'pixels et couleurs Metano NATIFS inchanges'},
        'gouttes': {'poses': len(DROP_WINS), 'sequence': [list(s) if s else None for s in DROP_SEQ],
                    'emitters': emitters, 'phases': DROP_PHASES, 'frame_length_ticks': DROP_TICKS},
        'eclats': {'poses': len(motes), 'taille_px': list(motes[0].shape[:2]), 'pulsation': FLY_PULSE,
                   'points': [list(s) for s in spots], 'phases': ANIM_PHASES, 'frame_length_ticks': ANIM_TICKS},
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'entry_px': entry_px, 'threshold_px': threshold_px, 'path_found_16x16': ok, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si > 25 % hors dalles et reflets cristallins de la plateforme centrale'},
        'pmdo': {'target': '0.8.12', 'asset': ASSET, 'namespace': NAMESPACE, 'tiles_per_bank': counts, 'banks': list(counts),
                 'runtime_tested': False, 'warp': 'aucun'},
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    print(json.dumps({'sparkles': len(sparkles), 'entry': entry_px, 'threshold': threshold_px, 'blocked': int(blocked.sum()),
                      'walkable': int((~blocked).sum()), 'fidelite_brut': {k: v['distance'] for k, v in fid.items()},
                      'tiles': sum(counts.values())}, indent=1))


if __name__ == '__main__':
    build()
