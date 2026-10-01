"""Intro animée « Mew voyage à travers le monde Pokémon » (IMW1) — cinématique 4:3, 768 x 576, 30 i/s, 63,5 s.

Demande : « tu peux faire fond animé une intro d'un mew qui voyage à travers le ciel avec un soleil et il voyage à travers le monde
pokémon avec différents biomes (une cinématique avec plusieurs map etc) ».

Méthode : une cinématique faite d'assets du projet, pas un nouveau décor de monde.
- Mew : un seul sprite généré (bruts/mew_a.png, pixels gros, grille 11,75 px retrouvée par autocorrélation) ré-échantillonné à sa grille
  native (66 x 58, 13 couleurs) ; 8 poses par ondulation de la queue calculée (colonnes décalées d'au plus 3 px), pas de seconde génération.
  La seconde génération a été écartée (queue enroulée sur le corps, bruts/ecartes/).
- Biomes : 11 cartes déjà livrées (leurs scènes animées `review/*_scene_animee.webp`), survolées par une caméra qui avance vers la droite
  (fenêtre 384 x 288 de la scène, rendu x2 en pixels entiers). Ombre de Mew et ombres de nuages portées sur la carte.
- Ciel : acte d'ouverture (aube, soleil qui se lève derrière une mer de nuages, 3 plans de nuages en parallaxe) et acte final (soleil
  doré, Mew qui s'éloigne dedans). Nuages, soleil, rayons, éclats : tout est procédural (aucun rip), 3 à 4 tons, pas de liseré.
- Transitions : un mur de nuages traverse l'écran ; la carte change au moment où il couvre tout.
- Lumière du jour : teinte multiplicative et lueur du soleil (mélange « écran », étagée et tramée) qui suivent le cycle aube, jour, couchant,
  nuit, aube dorée sur 63,5 s.
Tout est déterministe : le même instant donne le même cadre. `art_approved: false`, aucun test dans PMDO (ce n'est pas une map Ground).
"""
import glob, json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

R = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = R / 'renders/intro_mew_v1'
LW, LH, UP, FPS = 384, 288, 2, 30                       # canevas logique, rendu x2 = 768 x 576
DUR_INTRO, DUR_SCENE, DUR_FINALE, WALL_HALF = 8.0, 4.5, 6.0, 0.8
CRF = 21

# (clé, dossier de rendu, motif du .webp animé, départ (x, y) de la fenêtre, arrivée) — la fenêtre mesure 384 x 288 dans une scène 768 x 576
SCENES = [
    ('aube',        'zone_reveil_prairie_horizon_v2', 'ZRV2_aube_scene_animee.webp', (0, 288), (384, 0),   'Aube sur la prairie et la mer'),
    ('clairiere',   'entree_clairiere_tropicale_sud_nord_v1', '*_scene_animee.webp', (0, 0),   (384, 200), 'Clairière tropicale et rivière'),
    ('jungle',      'entree_jungle_sud_nord_v1', '*_scene_animee.webp', (0, 288), (384, 40),  'Jungle du sud'),
    ('jardin',      'entree_jardin_secret_sud_nord_v3', '*_scene_animee.webp', (0, 160), (384, 120), 'Jardin secret'),
    ('sables',      'entree_sables_mouvants_sud_nord_v1', '*_scene_animee.webp', (0, 0), (384, 288),  'Sables mouvants'),
    ('cascade',     'entree_waterfall_cave_sud_nord_v3', 'EWC3_scene_animee.webp', (0, 288), (384, 0),  'Grotte de la cascade'),
    ('tonnerre',    'entree_mt_thunder_sud_nord_v1', '*_scene_animee.webp', (0, 288), (384, 100), 'Mont Foudre au-dessus des nuages'),
    ('magma',       'entree_cratere_magma_v1', '*_scene_animee.webp', (0, 0), (384, 288), 'Cratère de magma'),
    ('givre',       'fin_givre_aurore_v2', '*_scene_animee.webp', (0, 288), (384, 0), 'Forêt de givre et aurores'),
    ('ocean',       'fin_ocean_kyogre_v1', '*_scene_animee.webp', (0, 0), (384, 288), "Fonds de l'océan"),
    ('sommet',      'colonnes_lances_v2/CLR2', 'CLR2_scene_animee.webp', (150, 288), (240, 0), 'Colonnes Lances, le sommet'),
]
SCENE_T0 = [DUR_INTRO + i * DUR_SCENE for i in range(len(SCENES))]
T_FINALE = DUR_INTRO + len(SCENES) * DUR_SCENE
T_END = T_FINALE + DUR_FINALE
N_FRAMES = int(round(T_END * FPS))

# (t, sx, sy, force de la lueur, rgb lueur, multiplicateur rgb de la scène)
TOD = [
    (0.0, 270, 330, 0.00, (255, 190, 140), (1.00, 0.92, 0.86)),
    (8.0, 330, -70, 0.30, (255, 200, 150), (1.00, 0.90, 0.82)),
    (14.0, 280, -80, 0.30, (255, 235, 190), (1.00, 0.97, 0.92)),
    (22.0, 190, -90, 0.28, (255, 250, 225), (1.00, 1.00, 1.00)),
    (31.0, 110, -80, 0.30, (255, 240, 200), (1.00, 0.97, 0.90)),
    (37.0, 40, -20, 0.40, (255, 190, 120), (1.00, 0.86, 0.72)),
    (42.0, -20, 110, 0.50, (255, 140, 80), (1.00, 0.74, 0.58)),
    (46.5, -60, 200, 0.10, (150, 160, 255), (0.70, 0.76, 0.95)),
    (51.0, -60, 200, 0.10, (150, 160, 255), (0.62, 0.70, 0.95)),
    (55.0, 192, -80, 0.22, (255, 215, 150), (1.00, 0.88, 0.72)),
    (T_END, 192, 0, 0.30, (255, 225, 160), (1.00, 0.92, 0.80)),
]


def lerp(a, b, u): return a + (b - a) * u
def clamp01(u): return min(1.0, max(0.0, u))
def smooth(u): u = clamp01(u); return u * u * (3 - 2 * u)
def ease_out(u): u = clamp01(u); return 1 - (1 - u) ** 3


def tod(t):
    for a, b in zip(TOD, TOD[1:]):
        if a[0] <= t <= b[0]:
            u = (t - a[0]) / (b[0] - a[0])
            return (lerp(a[1], b[1], u), lerp(a[2], b[2], u), lerp(a[3], b[3], u),
                    tuple(lerp(x, y, u) for x, y in zip(a[4], b[4])), tuple(lerp(x, y, u) for x, y in zip(a[5], b[5])))
    return TOD[-1][1:]


# ----------------------------------------------------------------------------------------------- Mew
MEW_NATIVE = None


def mew_native():
    global MEW_NATIVE
    if MEW_NATIVE is None:
        MEW_NATIVE = np.array(Image.open(HERE / 'bruts/mew_natif.png').convert('RGBA'))
    return MEW_NATIVE


def mew_frames(n=8, pad=4):
    """n poses de la queue : décalage vertical par colonne, onde qui voyage le long de la queue, boucle exacte."""
    src = mew_native(); h, w = src.shape[:2]
    out = []
    for k in range(n):
        ph = 2 * math.pi * k / n
        canvas = np.zeros((h + 2 * pad, w, 4), np.uint8)
        canvas[pad:pad + h] = src
        tail = np.zeros_like(canvas)
        body = canvas.copy()
        body[:pad + 31, :30] = 0                         # le haut de la queue est retiré du corps...
        for x in range(30):
            wgt = max(0.0, (22 - x) / 22) ** 1.5
            dy = int(round(3.0 * wgt * math.sin(ph - 0.22 * (22 - x))))
            col = np.zeros((h + 2 * pad, 4), np.uint8)
            col[:pad + 31] = canvas[:pad + 31, x]
            tail[:, x] = np.roll(col, dy, axis=0)
        fr = canvas.copy(); fr[:] = 0
        fr[...] = body
        m = tail[..., 3] > 0
        fr[m] = tail[m]
        out.append(fr)
    return out


def mew_pos(t):
    """Centre de Mew (px logiques) et échelle, à l'instant t."""
    if t < DUR_INTRO:
        x = -40 + 190 * ease_out((t - 0.3) / 3.4) + max(0.0, t - 3.7) * 4
        y = 138 + 6 * math.sin(2 * math.pi * t / 1.6)
        return x, y, 1.0
    if t < T_FINALE:
        return 130 + 10 * math.sin(2 * math.pi * t / 5.3), 140 + 6 * math.sin(2 * math.pi * t / 1.8), 1.0
    u = clamp01((t - T_FINALE) / DUR_FINALE)
    return lerp(130, 205, smooth(u)), lerp(150, 152, u) + 4 * math.sin(2 * math.pi * t / 1.8), 1.0 - 0.58 * smooth(u)


# ----------------------------------------------------------------------------------------------- nuages
TONES = {'blanc': (250, 250, 255), 'clair': (222, 232, 248), 'ombre': (176, 190, 222), 'creux': (150, 164, 204)}


def cloud_tones(mask, rs):
    """Tons d'un nuage selon la normale du bord (lumière en haut à gauche) et la profondeur : 4 tons, aucun liseré."""
    s = ndimage.gaussian_filter(mask.astype(float), 2.0)
    gy, gx = np.gradient(s); nrm = np.hypot(gx, gy) + 1e-6
    lit = (gx / nrm) * 0.45 + (gy / nrm) * 0.9              # normale sortante = -grad ; lumière (-0.45, -0.9) => -grad . -L = grad . L
    depth = ndimage.distance_transform_edt(mask)
    tone = np.zeros(mask.shape + (3,), np.uint8)
    tone[:] = TONES['clair']
    tone[(depth <= 9) & (lit > 0.30)] = TONES['blanc']
    tone[(depth <= 5) & (lit < -0.45)] = TONES['ombre']
    tone[(depth <= 2) & (lit < -0.85)] = TONES['creux']
    rgba = np.zeros(mask.shape + (4,), np.uint8); rgba[..., :3] = tone; rgba[..., 3] = np.where(mask, 255, 0)
    return rgba


def make_cloud(w, h, seed, flat=2):
    """Nuage en dôme : bouffées plus petites vers les bouts, dessous presque plat aux coins arrondis."""
    rs = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w]; mask = np.zeros((h, w), bool)
    base = h - 1 - flat
    for k in range(max(5, w // 9)):
        cx = rs.uniform(0.10 * w, 0.90 * w); e = abs(cx - w / 2) / (w / 2)
        r = h * rs.uniform(0.22, 0.46) * (1.0 - 0.55 * e ** 1.5)
        cy = base - r * rs.uniform(0.15, 0.85)
        mask |= (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    edge = np.abs(xx - w / 2) / (w / 2)
    mask &= yy <= base - (edge ** 4) * h * 0.30
    return cloud_tones(mask, rs)


def make_wall(w=960, h=LH, seed=11):
    """Mur de nuages de transition : coeur plein de 560 px (couvre l'écran de 384 px au milieu du passage), bords en bouffées."""
    rs = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w]; mask = np.zeros((h, w), bool)
    mask[:, 200:w - 200] = True
    for side in (0, 1):
        for _ in range(26):
            r = rs.uniform(16, 44); cy = rs.uniform(-10, h + 10)
            cx = rs.uniform(150, 215) if side == 0 else rs.uniform(w - 215, w - 150)
            mask |= (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    for _ in range(14):                                       # pièces détachées devant le mur
        r = rs.uniform(8, 20); cy = rs.uniform(0, h)
        cx = rs.choice([rs.uniform(70, 150), rs.uniform(w - 150, w - 70)])
        mask |= (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    rgba = cloud_tones(mask, rs)
    n = ndimage.gaussian_filter(rs.rand(h, w), 7.0); n = (n - n.min()) / (n.max() - n.min())
    n2 = np.roll(n, 5, axis=0)                                # des plages claires puis, juste dessous, des plages ombrées
    rgba[(n > 0.62) & (n2 <= 0.62) & mask, :3] = TONES['ombre']
    rgba[(n > 0.62) & (n2 > 0.62) & mask, :3] = TONES['blanc']
    rgba[(n < 0.30) & mask, :3] = TONES['ombre']
    return rgba


CACHE = {}


def sprites():
    if 'spr' not in CACHE:
        far = [make_cloud(w, h, 100 + i) for i, (w, h) in enumerate([(54, 18), (70, 22), (46, 16), (62, 20)])]
        mid = [make_cloud(w, h, 200 + i) for i, (w, h) in enumerate([(96, 34), (120, 40), (84, 30)])]
        near = [make_cloud(w, h, 300 + i) for i, (w, h) in enumerate([(160, 56), (190, 64), (140, 50)])]
        sea = make_cloud(LW + 140, 84, 400, flat=0)
        wall = make_wall()
        CACHE['spr'] = dict(far=far, mid=mid, near=near, sea=sea, wall=wall)
    return CACHE['spr']


def paste(dst, spr, x, y, mul=None, alpha=1.0):
    """dst (H,W,3 uint8) <- spr RGBA, coin haut-gauche (x, y) entier."""
    x, y = int(round(x)), int(round(y)); h, w = spr.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0: return
    s = spr[y0 - y:y1 - y, x0 - x:x1 - x]
    m = s[..., 3] > 127
    rgb = s[..., :3].astype(float)
    if mul is not None: rgb = rgb * np.array(mul)
    sub = dst[y0:y1, x0:x1]
    if alpha >= 1.0:
        sub[m] = np.clip(rgb[m], 0, 255).astype(np.uint8)
    else:
        sub[m] = np.clip(sub[m] * (1 - alpha) + rgb[m] * alpha, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------------------------------- ciel
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def sky_gradient(top, hor, bands=14):
    yy, xx = np.mgrid[0:LH, 0:LW]
    v = yy / (LH * 0.82)
    v = np.clip(v, 0, 1) * bands + (BAYER[yy % 4, xx % 4] - 0.5) * 0.9      # tramage 4 x 4 entre les bandes
    q = np.clip(np.floor(v), 0, bands) / bands
    out = np.zeros((LH, LW, 3), float)
    for c in range(3):
        out[..., c] = top[c] + (hor[c] - top[c]) * q ** 1.2
    return out.astype(np.uint8)


def draw_sun(img, cx, cy, r, tl, warm=(1.0, 1.0, 1.0), rot=None):
    """Soleil à 3 tons et 14 rayons qui tournent par pas de 1/3."""
    ov = Image.new('RGBA', (LW, LH), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    step = int(tl * 3) % 3 if rot is None else None
    n = 14
    for i in range(n):
        a = 2 * math.pi * (((i + step / 3.0) if rot is None else ((i + rot) % n))) / n
        w = 0.07 + (0.03 if i % 2 == 0 else 0.0)
        long = r * (2.1 if i % 2 == 0 else 1.65)
        pts = [(cx + math.cos(a - w) * r * 1.15, cy + math.sin(a - w) * r * 1.15), (cx + math.cos(a) * long, cy + math.sin(a) * long),
               (cx + math.cos(a + w) * r * 1.15, cy + math.sin(a + w) * r * 1.15)]
        d.polygon(pts, fill=(255, 238, 170, 120))
    for rr, col in ((r * 1.18, (255, 196, 110)), (r, (255, 226, 140)), (r * 0.72, (255, 248, 214))):
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col + (255,))
    a = np.array(ov); m = a[..., 3] > 0
    hard = a[..., 3] == 255
    base = img.astype(float)
    ray = m & ~hard
    base[ray] = base[ray] * 0.55 + a[ray][:, :3] * 0.45
    base[hard] = a[hard][:, :3]
    return np.clip(base, 0, 255).astype(np.uint8)


def far_layer(img, tl, y_range, speed, sprs, seed, n, mul, off=0.0):
    rs = np.random.RandomState(seed); span = LW + 200
    for i in range(n):
        spr = sprs[i % len(sprs)]
        x0 = rs.uniform(0, span); y = rs.uniform(*y_range)
        x = (x0 - speed * tl) % span - 120
        paste(img, spr, x, y, mul)


def sky_act(tl, dur, mode, t_global):
    """Acte de ciel : mode 'aube' (ouverture) ou 'dore' (finale). Retourne le canevas logique."""
    p = clamp01(tl / dur)
    if mode == 'aube':
        top = [lerp(34, 112, smooth(p * 1.1)), lerp(40, 150, smooth(p * 1.1)), lerp(104, 222, smooth(p * 1.1))]
        hor = [lerp(236, 255, p), lerp(120, 205, p), lerp(120, 150, p)]
        sx, sy, sr = 250, lerp(262, 118, smooth(p)), 24
    else:
        top = [lerp(70, 118, p), lerp(100, 150, p), lerp(170, 215, p)]
        hor = [255, lerp(190, 222, p), lerp(120, 160, p)]
        sx, sy, sr = 200, lerp(170, 150, p), lerp(34, 48, smooth(p))
    img = sky_gradient(top, hor)
    img = draw_sun(img, sx, sy, sr, tl)
    mul = tod(t_global)[4] if mode == 'aube' else (1.0, 0.95, 0.85)
    sp = sprites()
    tint = (mul[0] * (1.0 if mode == 'aube' else 1.0), mul[1], mul[2])
    far_layer(img, tl, (40, 150), 6, sp['far'], 1, 7, tint)
    far_layer(img, tl, (90, 180), 16, sp['mid'], 2, 5, tint)
    sea = sp['sea']
    if mode == 'aube':
        paste(img, sea, -((tl * 30) % 140), 214, tint)
        far_layer(img, tl, (190, 232), 52, sp['near'], 3, 4, tint)
    else:
        paste(img, sea, -((tl * 30) % 140), 226, tint)
        far_layer(img, tl, (200, 244), 52, sp['near'], 3, 4, tint)
    return img


# ----------------------------------------------------------------------------------------------- scènes animées
class SceneFrames:
    def __init__(self, folder, pattern):
        f = sorted(glob.glob(str(R / 'renders' / folder / 'review' / pattern)))
        assert f, (folder, pattern)
        im = Image.open(f[0]); self.frames, self.durs = [], []
        for i in range(im.n_frames):
            im.seek(i); self.frames.append(np.array(im.convert('RGB'))); self.durs.append(im.info.get('duration', 100))
        self.total = sum(self.durs); self.cum = np.cumsum(self.durs)
        assert self.frames[0].shape == (576, 768, 3), (folder, self.frames[0].shape)

    def at(self, t):
        ms = (t * 1000.0) % self.total
        return self.frames[int(np.searchsorted(self.cum, ms, side='right')) % len(self.frames)]


def scene_frames(i):
    key = ('scene', i)
    if key not in CACHE:
        for k in [k for k in CACHE if isinstance(k, tuple) and k[0] == 'scene' and abs(k[1] - i) > 1]:
            del CACHE[k]
        _, folder, pat = SCENES[i][:3]
        CACHE[key] = SceneFrames(folder, pat)
    return CACHE[key]


def pan_window(i, tl):
    _, _, _, a, b, _ = SCENES[i]
    u = smooth(tl / DUR_SCENE)
    x = int(round(lerp(a[0], b[0], u))); y = int(round(lerp(a[1], b[1], u)))
    return min(384, max(0, x)), min(288, max(0, y))


def glare(img, t):
    sx, sy, strength, col, _ = tod(t)
    if strength <= 0.001: return img
    yy, xx = np.mgrid[0:LH, 0:LW]
    d = np.hypot(xx - sx, yy - sy) / 300.0
    g = np.clip(1 - d, 0, 1) ** 2 * strength
    g = np.floor(g * 10 + BAYER[yy % 4, xx % 4]) / 10.0           # étagé et tramé comme du pixel art
    g = np.clip(g, 0, 1)[..., None]
    gc = np.array(col)[None, None, :]
    return (255 - (255 - img.astype(float)) * (255 - gc * g) / 255.0).clip(0, 255).astype(np.uint8)


def ellipse_mask(cx, cy, rx, ry):
    yy, xx = np.mgrid[0:LH, 0:LW]
    return ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0


def scene_act(i, t):
    tl = t - SCENE_T0[i]
    sf = scene_frames(i)
    wx, wy = pan_window(i, tl)
    img = sf.at(tl)[wy:wy + LH, wx:wx + LW].copy()
    sp = sprites()
    # ombres des nuages portées sur la carte (nuages de plan moyen, plus rapides que la carte)
    rs = np.random.RandomState(50 + i); span = LW + 260
    clouds = []
    for k in range(3):
        spr = sp['mid'][(i + k) % 3]; x0 = rs.uniform(0, span); y = rs.uniform(20, 230)
        x = (x0 - 70 * t) % span - 130
        clouds.append((spr, x, y))
    for spr, x, y in clouds:
        sh = np.zeros((LH, LW), bool)
        h, w = spr.shape[:2]
        xs, ys = int(round(x)) + 18, int(round(y)) + 40
        x0, y0, x1, y1 = max(0, xs), max(0, ys), min(LW, xs + w), min(LH, ys + h)
        if x1 > x0 and y1 > y0:
            sh[y0:y1, x0:x1] = spr[y0 - ys:y1 - ys, x0 - xs:x1 - xs, 3] > 127
            img[sh] = (img[sh] * 0.78).astype(np.uint8)
    # Mew : ombre au sol
    mx, my, ms = mew_pos(t)
    bob = my - 140
    sm = ellipse_mask(mx - 6, 232 + bob * -0.3, 24 + bob * 0.3, 6)
    img[sm] = (img[sm] * 0.66).astype(np.uint8)
    _, _, _, _, mul = tod(t)
    img = np.clip(img.astype(float) * np.array(mul), 0, 255).astype(np.uint8)
    img = glare(img, t)
    return img, clouds


def draw_mew(img, t, mul):
    mx, my, ms = mew_pos(t)
    frames = CACHE.setdefault('mew', mew_frames())
    f = frames[int(t * 10) % len(frames)]
    spr = f
    if ms < 0.999:
        pil = Image.fromarray(f); spr = np.array(pil.resize((max(1, int(round(pil.width * ms))), max(1, int(round(pil.height * ms)))), Image.NEAREST))
    paste(img, spr, mx - spr.shape[1] / 2, my - spr.shape[0] / 2, mul)


SPARK = [(255, 255, 255), (255, 242, 170), (255, 196, 226)]


def draw_sparkles(img, t, mul):
    """Éclats derrière Mew : un par 0,1 s, durée de vie 1,1 s, croix de 1 à 2 px qui rétrécit."""
    for k in range(int(max(0, t - 1.1) * 10), int(t * 10) + 1):
        te = k / 10.0; age = t - te
        if age < 0 or age > 1.1 or te < 0.3: continue
        rs = np.random.RandomState(900 + k)
        mx, my, ms = mew_pos(te)
        x = mx - 28 * ms - 26 * age * (0.6 + rs.rand()) + rs.uniform(-4, 4)
        y = my + 6 * ms + rs.uniform(-14, 14) + 8 * age + 3 * math.sin(6 * age + k)
        col = np.clip(np.array(SPARK[k % 3]) * np.array(mul), 0, 255).astype(np.uint8)
        a = int(1 + 2 * (1 - age / 1.1))
        xi, yi = int(round(x)), int(round(y))
        for dx in range(-a, a + 1):
            for dy, ok in ((0, True), (dx, abs(dx) == 0)):
                pass
        pts = [(0, 0)] + [(s * j, 0) for j in range(1, a + 1) for s in (-1, 1)] + [(0, s * j) for j in range(1, a + 1) for s in (-1, 1)]
        for dx, dy in pts:
            px, py = xi + dx, yi + dy
            if 0 <= px < LW and 0 <= py < LH: img[py, px] = col


def wall_progress(t):
    """Retourne (index de la frontière, p dans [0,1]) si t est dans une transition, sinon None."""
    bounds = [DUR_INTRO + i * DUR_SCENE for i in range(len(SCENES) + 1)]
    bounds[-1] = T_FINALE
    for k, b in enumerate(bounds):
        if abs(t - b) < WALL_HALF:
            return k, (t - (b - WALL_HALF)) / (2 * WALL_HALF)
    return None


def render(t):
    """Cadre logique 288 x 384 x 3 à l'instant t (secondes)."""
    mul = tod(t)[4]
    if t < DUR_INTRO:
        img = sky_act(t, DUR_INTRO, 'aube', t)
    elif t < T_FINALE:
        i = min(len(SCENES) - 1, int((t - DUR_INTRO) // DUR_SCENE))
        img, clouds = scene_act(i, t)
    else:
        img = sky_act(t - T_FINALE, DUR_FINALE, 'dore', t)
        mul = (1.0, 0.95, 0.85)
    if DUR_INTRO <= t < T_FINALE:                              # nuages de passage, sous Mew (plan moyen)
        for spr, x, y in clouds:
            paste(img, spr, x, y, mul)
    draw_sparkles(img, t, (1.0, 1.0, 1.0))
    draw_mew(img, t, mul if t < T_FINALE else (1.0, 0.93, 0.80))
    wp = wall_progress(t)
    if wp is not None:
        k, p = wp
        wx = lerp(LW, -960, p)
        mw = tod(t)[4]
        paste(img, sprites()['wall'], wx, 0, mw)
    # fondu d'entrée et de sortie
    if t < 0.5: img = (img * (t / 0.5)).astype(np.uint8)
    if t > T_END - 1.0: img = (img * clamp01((T_END - t) / 1.0)).astype(np.uint8)
    return img


def upscale(img): return np.repeat(np.repeat(img, UP, 0), UP, 1)


# ----------------------------------------------------------------------------------------------- sorties
def build(video=True, every=1):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'review').mkdir(exist_ok=True); (OUT / 'calques').mkdir(exist_ok=True)
    mf = mew_frames()
    strip = Image.new('RGBA', (len(mf) * mf[0].shape[1], mf[0].shape[0]))
    for i, f in enumerate(mf): strip.paste(Image.fromarray(f), (i * f.shape[1], 0))
    strip.save(OUT / 'calques/IMW1_mew_vol_8poses.png')
    sp = sprites()
    for name in ('far', 'mid', 'near'):
        for i, s in enumerate(sp[name]): Image.fromarray(s).save(OUT / f'calques/IMW1_nuage_{name}_{i}.png')
    Image.fromarray(sp['sea']).save(OUT / 'calques/IMW1_mer_de_nuages.png')
    Image.fromarray(sp['wall']).save(OUT / 'calques/IMW1_mur_de_nuages_transition.png')
    for nm, tt, mode, dur in (('aube', 7.0, 'aube', DUR_INTRO), ('dore', 0.0, 'dore', DUR_FINALE)):
        Image.fromarray(upscale(sky_act(tt, dur, mode, 7.0 if mode == 'aube' else T_FINALE + 3))).save(OUT / f'calques/IMW1_ciel_{nm}.png')
    jalons = [3.0, 6.0] + [SCENE_T0[i] + 2.2 for i in range(len(SCENES))] + [T_FINALE + 1.0, T_FINALE + 4.5]
    for t in jalons:
        Image.fromarray(upscale(render(t))).save(OUT / f'review/IMW1_t{t:05.1f}s.png')
    if video:
        import imageio
        w = imageio.get_writer(OUT / 'IMW1_intro_mew.mp4', fps=FPS, codec='libx264', quality=None, macro_block_size=1, pixelformat='yuv420p',
                               ffmpeg_params=['-crf', str(CRF), '-preset', 'slow', '-movflags', '+faststart'])
        for n in range(0, N_FRAMES, every):
            w.append_data(upscale(render(n / FPS)))
            if n % 150 == 0: print('frame', n, '/', N_FRAMES, flush=True)
        w.close()
    return jalons


def write_manifest(jalons):
    mew = mew_native(); cols = np.unique(mew[mew[..., 3] > 0][:, :3], axis=0)
    scenes = []
    for i, sc in enumerate(SCENES):
        scenes.append({'cle': sc[0], 'carte_source': sc[1], 'legende': sc[5], 't_debut_s': SCENE_T0[i], 't_fin_s': SCENE_T0[i] + DUR_SCENE,
                       'fenetre_depart_xy': list(sc[3]), 'fenetre_arrivee_xy': list(sc[4])})
    man = {
        'lot': 'intro_mew_v1', 'asset': 'IMW1', 'serie': 'Cinematiques',
        'demande': "une intro d'un mew qui voyage a travers le ciel avec un soleil et il voyage a travers le monde pokemon avec differents biomes (une cinematique avec plusieurs map)",
        'choix_agent': {'format': '4:3, 768 x 576, 30 i/s, 63,5 s', 'ordre_des_biomes': 'cycle aube, jour, couchant, nuit, aube doree ; a confirmer',
                        'cartes': 'les 11 cartes sont des maps deja livrees du projet (leurs scenes animees), pas de nouveau decor'},
        'format': {'size_px': [LW * UP, LH * UP], 'logique_px': [LW, LH], 'fps': FPS, 'frames': N_FRAMES, 'duree_s': T_END, 'zoom_entier': UP,
                   'codec': f'H.264 yuv420p, crf {CRF}'},
        'actes': [{'cle': 'ouverture_aube', 't_debut_s': 0.0, 't_fin_s': DUR_INTRO}] + [{'cle': 'carte_' + x['cle'], **{k: x[k] for k in ('t_debut_s', 't_fin_s')}} for x in scenes]
                 + [{'cle': 'finale_doree', 't_debut_s': T_FINALE, 't_fin_s': T_END}],
        'scenes': scenes,
        'transitions': {'type': 'mur de nuages', 'duree_s': 2 * WALL_HALF, 'frontieres_s': [DUR_INTRO + i * DUR_SCENE for i in range(len(SCENES))] + [T_FINALE],
                        'changement_de_carte': 'a la frontiere (le mur couvre tout l\'ecran)'},
        'mew': {'source': 'source/intro_mew_v1/bruts/mew_a.png', 'grille_px_brut': 11.75, 'taille_native': [int(mew.shape[1]), int(mew.shape[0])],
                'couleurs': int(len(cols)), 'poses_queue': 8, 'periode_s': 0.8,
                'ecarte': 'seconde generation (queue enroulee sur le corps), bruts/ecartes/'},
        'lumiere_du_jour': [{'t_s': k[0], 'soleil_xy': [k[1], k[2]], 'force_lueur': k[3], 'rgb_lueur': list(k[4]), 'multiplicateur_scene': list(k[5])} for k in TOD],
        'calques': sorted(x.name for x in (OUT / 'calques').glob('*.png')),
        'jalons_s': jalons,
        'deterministe': True, 'art_approved': False, 'runtime_tested': False,
        'reserves': ["pas une map PMDO ni un Ground : une video generee a partir de maps existantes",
                     "Mew est un sprite genere (une seule generation), jamais valide comme sprite SpriteCollab",
                     "nuages, soleil et eclats procedurals, aucune reference ROM",
                     "le mp4 est compresse (H.264, sous-echantillonnage des couleurs) : les calques PNG font foi pour les pixels"],
    }
    (OUT / 'manifest.json').write_text(json.dumps(man, indent=1, ensure_ascii=False))
    return man


if __name__ == '__main__':
    j = build(video='--no-video' not in sys.argv)
    write_manifest(j)
