"""IMW3 — « Traversée » : intro de Mew dans l'esprit de l'ouverture d'Explorers of Sky (Treasure Town, intro), 4:3, 768 x 576, 30 i/s, 28 s.

Demande : « pour l'introduction faut quelque chose de ce genre » (capture de la ressource Spriters Resource « Treasure Town (Intro) » : un grand
décor vertical peint avec un soleil et des nuages en haut et une vue aérienne du monde en bas, un Pokémon qui vole en grossissant, des pétales,
des anneaux de lumière). Le fichier joint n'était plus dans le bac à sable : je n'ai travaillé que d'après l'image vue dans la conversation,
sans rien mesurer dessus ni la copier.

Méthode : une cinématique, comme IMW1, mais avec le principe de l'ouverture du jeu :
- un seul grand décor vertical généré (bruts/fond_vertical.png, 768 x 1376) : ciel, soleil et nuages en haut, mer, montagnes enneigées, désert,
  volcan, plateaux et forêt avec un village en bas. La caméra le parcourt de haut en bas (défilement sous-pixel, courbe douce) ;
- Mew peint, généré en deux poses (bruts/mew_peint_a.png, mew_peint_b.png : seule la queue change), détouré du magenta, redimensionné en continu
  pour qu'il surgisse du soleil en grossissant, puis s'éloigne au-dessus du monde ; la queue fait des allers-retours entre les deux poses ;
- ajouts procéduraux : lueur et étoile du soleil qui pulsent, anneaux de lumière qui partent du soleil et de Mew, voiles de nuages qui dérivent,
  pétales qui tournent en trois dimensions (8 poses de retournement, 4 tailles, 2 plans) ;
- fondu d'entrée, éclat blanc et fondu de sortie.
Tout est déterministe. `art_approved: false`. Ce n'est pas une map PMDO : IMW1 et IMW2 sont conservés.
"""
from pathlib import Path
import hashlib, json, math, sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
OUT = R / 'renders/intro_mew_traversee_v1'
RAW = HERE / 'bruts'
W, H, FPS = 768, 576, 30
T_END = 28.0
N_FRAMES = int(round(T_END * FPS))
CAM_MAX = 800                                    # défilement total en px (décor 1376 de haut, fenêtre 576)
SUN_XY = (384, 232)                              # centre du soleil dans le décor
# (t_début, t_fin, nom)
ACTS = [(0.0, 9.0, 'Le soleil : Mew surgit de la lumière'), (9.0, 22.0, 'La descente vers le monde'), (22.0, 28.0, 'Le village, puis le grand envol')]


def lerp(a, b, u): return a + (b - a) * u
def clamp01(u): return min(1.0, max(0.0, u))
def smooth(u): u = clamp01(u); return u * u * (3 - 2 * u)
def smoother(u): u = clamp01(u); return u * u * u * (u * (6 * u - 15) + 10)


# ------------------------------------------------------------------------------------------------------ Mew peint
def key_mew(path):
    """Détourage du fond magenta : seuil, frange rose retirée sur 2 px, bords adoucis."""
    a = np.array(Image.open(path).convert('RGB')).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    bg = (r > 170) & (b > 170) & (g < 125) & (np.abs(r - b) < 70)
    near = ndimage.binary_dilation(bg, iterations=2)
    bg2 = bg | (near & (b - g > 45))
    fg = ~bg2
    lab, n = ndimage.label(fg)
    if n > 1:
        sizes = ndimage.sum(fg, lab, range(1, n + 1)); fg = lab == (1 + int(np.argmax(sizes)))
    fg = ndimage.binary_fill_holes(fg)
    al = ndimage.gaussian_filter(fg.astype(float), 0.7)
    out = np.zeros(a.shape[:2] + (4,), np.uint8)
    out[..., :3] = a; out[..., 3] = np.clip(al * 255, 0, 255).astype(np.uint8)
    out[~fg & (al < 0.02)] = 0
    return out


_MEW = {}


def mew_sources():
    if 'ab' not in _MEW:
        A = key_mew(RAW / 'mew_peint_a.png'); B = key_mew(RAW / 'mew_peint_b.png')
        al = np.maximum(A[..., 3], B[..., 3]); ys, xs = np.nonzero(al > 8)
        y0, y1, x0, x1 = ys.min() - 4, ys.max() + 5, xs.min() - 4, xs.max() + 5
        _MEW['ab'] = (A[y0:y1, x0:x1], B[y0:y1, x0:x1])
    return _MEW['ab']


def mew_blend(w):
    """Pose intermédiaire : fondu entre les poses A et B (seule la queue diffère), en alpha prémultiplié."""
    A, B = mew_sources()
    pa = A.astype(float); pb = B.astype(float)
    aa, ab = pa[..., 3:] / 255, pb[..., 3:] / 255
    al = aa * (1 - w) + ab * w
    rgb = (pa[..., :3] * aa * (1 - w) + pb[..., :3] * ab * w) / np.maximum(al, 1e-4)
    return np.dstack([np.clip(rgb, 0, 255), np.clip(al * 255, 0, 255)]).astype(np.uint8)


def rotate_rgba(im, ang):
    """Rotation en alpha prémultiplié : pas de frange sombre sur les bords."""
    return im.convert('RGBa').rotate(ang, resample=Image.BICUBIC, expand=True).convert('RGBA')


def resize_rgba(arr, size):
    im = Image.fromarray(arr, 'RGBA').convert('RGBa').resize(size, Image.LANCZOS).convert('RGBA')
    return im


def mew_state(t):
    """(cx, cy) écran, échelle, angle (degrés), poids de la queue, opacité."""
    wag = 0.5 - 0.5 * math.cos(2 * math.pi * t / 0.9)
    if t < 9.0:                                              # surgit du soleil
        u = clamp01((t - 0.8) / 6.7)
        sc = 0.03 + (0.50 - 0.03) * u ** 1.7
        x = lerp(SUN_XY[0], 330, smooth(u)); y = lerp(SUN_XY[1], 360, smooth(u)) - 46 * math.sin(math.pi * u)
        ang = lerp(-14, -4, smooth(u)) + 2.5 * math.sin(2 * math.pi * t / 2.2)
        hover = max(0.0, t - 7.5)
        y += 5 * math.sin(2 * math.pi * hover / 1.8)
        op = clamp01((t - 0.8) / 0.6)
        return x, y, sc, ang, wag, op
    if t < 22.0:                                             # descente
        v = smooth((t - 9.0) / 13.0)
        x = lerp(330, 520, v) + 16 * math.sin(2 * math.pi * t / 3.1)
        y = 360 + 46 * math.sin(math.pi * v) - 30 * v + 7 * math.sin(2 * math.pi * t / 1.8)
        sc = lerp(0.50, 0.27, v)
        ang = lerp(-4, 9, v) + 3 * math.sin(2 * math.pi * t / 2.6)
        return x, y, sc, ang, wag, 1.0
    v = (t - 22.0) / 6.0                                     # grand envol vers le haut à droite
    x = 520 + 330 * v ** 1.6 + 10 * math.sin(2 * math.pi * t / 1.7)
    y = 360 - 300 * v ** 1.6
    sc = lerp(0.27, 0.07, clamp01(v) ** 1.2)
    return x, y, sc, lerp(9, -22, v), wag, 1.0 - clamp01((v - 0.7) / 0.3)


# ------------------------------------------------------------------------------------------------------ décor et lumière
_BG = {}


def background():
    if 'bg' not in _BG:
        im = Image.open(RAW / 'fond_vertical.png').convert('RGB'); assert im.size == (768, 1376), im.size
        _BG['bg'] = np.array(im).astype(np.float32)
    return _BG['bg']


def cam_y(t):
    if t < 9.0: return 0.0
    if t < 22.0: return CAM_MAX * smoother((t - 9.0) / 13.0)
    return float(CAM_MAX)


def bg_frame(y):
    bg = background(); y0 = int(math.floor(y)); f = y - y0
    a = bg[y0:y0 + H]; b = bg[min(y0 + 1, bg.shape[0] - H):min(y0 + 1, bg.shape[0] - H) + H]
    return a * (1 - f) + b * f


def yy_xx():
    if 'g' not in _BG:
        _BG['g'] = np.mgrid[0:H, 0:W].astype(np.float32)
    return _BG['g']


def screen_add(img, layer, strength=1.0):
    """Mélange « écran » : 255 - (255 - img)(255 - layer * s) / 255."""
    l = np.clip(layer * strength, 0, 255)
    return 255 - (255 - img) * (255 - l) / 255.0


def sun_light(img, t, y):
    sy = SUN_XY[1] - y
    if sy < -420 or sy > H + 420: return img
    yy, xx = yy_xx()
    d = np.hypot(xx - SUN_XY[0], yy - sy)
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t / 3.2)
    glow = np.exp(-(d / (95 + 22 * pulse)) ** 2) * (150 + 70 * pulse)
    ang = np.arctan2(yy - sy, xx - SUN_XY[0]) + 0.05 * t
    star = (np.abs(np.cos(4 * ang)) ** 40) * np.exp(-d / 150.0) * (120 + 60 * pulse)          # étoile à 8 branches qui tourne lentement
    L = (glow + star)[..., None] * np.array([1.0, 0.97, 0.88])
    return screen_add(img, L, 1.0)


def ring_layer(img, cx, cy, r, w, a, color=(210, 235, 255)):
    yy, xx = yy_xx()
    d = np.hypot(xx - cx, yy - cy)
    m = np.exp(-((d - r) / w) ** 2) * a
    inner = np.exp(-((d - r * 0.93) / (w * 1.6)) ** 2) * a * 0.35               # second anneau, plus large et pâle (les cercles de la ressource)
    L = (m + inner)[..., None] * np.array(color)[None, None, :]
    return screen_add(img, L, 1.0)


def rings(img, t, y):
    sy = SUN_XY[1] - y
    for k in range(5):                                                         # un anneau parti du soleil toutes les 2 s, durée de vie 3 s
        age = t - (0.4 + 2.0 * k)
        if 0 <= age <= 3.0 and sy > -400:
            u = age / 3.0
            img = ring_layer(img, SUN_XY[0], sy, 40 + 520 * smooth(u), 12 + 10 * u, 0.55 * (1 - u) ** 1.5)
    age = t - 7.4                                                              # éclat quand Mew arrive
    if 0 <= age <= 1.6:
        x, yv, *_ = mew_state(7.4)
        u = age / 1.6
        img = ring_layer(img, x, yv, 30 + 330 * smooth(u), 9 + 8 * u, 0.7 * (1 - u) ** 1.3, (255, 235, 245))
    return img


_CLOUD = {}


def cloud_veil():
    """Voiles de nuages flous, périodiques en x (1100 px)."""
    if 'v' not in _CLOUD:
        rs = np.random.RandomState(21); P, Hh = 1100, 720
        m = np.zeros((Hh, P), np.float32); yy, xx = np.mgrid[0:Hh, 0:P]
        for _ in range(16):
            cx, cy = rs.uniform(0, P), rs.uniform(40, 600); rx, ry = rs.uniform(90, 230), rs.uniform(14, 38)
            for dx in (-P, 0, P):
                m = np.maximum(m, np.exp(-(((xx - cx - dx) / rx) ** 2 + ((yy - cy) / ry) ** 2) ** 1.0) * rs.uniform(0.35, 0.8))
        _CLOUD['v'] = ndimage.gaussian_filter(m, 6.0)
    return _CLOUD['v']


def clouds(img, t, y):
    if y > 700: return img
    v = cloud_veil(); P = v.shape[1]
    yo = int(y * 1.25)                                                          # parallaxe : les voiles défilent plus vite que le décor
    if yo >= v.shape[0] - 10: return img
    cols = (np.arange(W) + int(t * 14)) % P
    rows = slice(yo, min(v.shape[0], yo + H)); part = v[rows][:, cols]
    pad = np.zeros((H, W), np.float32); pad[:part.shape[0]] = part
    return img * (1 - pad[..., None] * 0.55) + 255.0 * pad[..., None] * 0.55


# ------------------------------------------------------------------------------------------------------ pétales
PETAL_SIZES = [12, 18, 28, 42]
_PET = {}


def petal_sprite(size, k):
    """Un pétale (goutte) retourné autour de son axe : 8 poses, 3 tons, dessiné en x4 puis réduit."""
    key = (size, k)
    if key in _PET: return _PET[key]
    S = 4; cw = size * 2 * S
    from PIL import ImageDraw
    im = Image.new('RGBA', (cw, cw), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = cw // 2; L = size * S; th = 2 * math.pi * k / 8; sx = abs(math.cos(th)) * 0.85 + 0.15
    pts = []
    for i in range(41):
        a = math.pi * i / 40
        pts.append((math.sin(a) * L * 0.34 * sx * (0.55 + 0.45 * math.sin(a)) , -L * 0.5 + L * i / 40))
    left = [(c - p[0], c + p[1]) for p in pts]; right = [(c + p[0], c + p[1]) for p in reversed(pts)]
    poly = left + right
    back = math.cos(th) < 0
    # palette rose sakura : face claire, dos plus soutenu (comme les pétales PMD Sky de l'intro)
    base = (240, 120, 150) if back else (255, 210, 222)
    hi = (255, 240, 245) if not back else (250, 170, 190)
    d.polygon(poly, fill=base + (255,))
    # éclat au bord supérieur (lumière)
    shade = Image.new('RGBA', (cw, cw), (0, 0, 0, 0)); sd = ImageDraw.Draw(shade)
    sd.polygon([(c, c - L * 0.5), (c + L * 0.36 * sx, c - L * 0.18), (c, c - L * 0.02), (c - L * 0.36 * sx, c - L * 0.18)], fill=hi + (180,))
    # ombre sous le pétale
    sd.polygon([(c + L * 0.25 * sx, c), (c + L * 0.4 * sx, c + L * 0.5), (c, c + L * 0.5), (c + L * 0.05 * sx, c + L * 0.1)], fill=(210, 80, 120, 110))
    mask = Image.new('L', (cw, cw), 0); ImageDraw.Draw(mask).polygon(poly, fill=255)
    im.alpha_composite(Image.composite(shade, Image.new('RGBA', (cw, cw), (0, 0, 0, 0)), mask))
    d.line([(c, c - L * 0.45), (c, c + L * 0.48)], fill=(200, 80, 115, 190), width=max(1, S // 2))
    im = im.convert('RGBa').resize((cw // S, cw // S), Image.LANCZOS).convert('RGBA')
    _PET[key] = im
    return im


def petals(img, t):
    """60 pétales en deux plans (30 petits derrière Mew, 30 gros devant), vent vers l'arrière, trajectoire périodique modulo l'écran."""
    rs = np.random.RandomState(77); base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')
    ramp = smooth((t - 4.5) / 3.0) * (1 - smooth((t - 26.0) / 1.8))
    if ramp <= 0.01: return img, None
    front = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for i in range(60):
        z = i % 2                                                               # 0 : plan arrière, 1 : plan avant (grands)
        size = PETAL_SIZES[(i // 2) % 2 + 2 * z]
        x0, y0 = rs.uniform(0, W + 160), rs.uniform(0, H + 160)
        vx, vy = -rs.uniform(70, 160) * (1.4 if z else 0.8), rs.uniform(10, 55)
        ph, sw, sp = rs.uniform(0, 6.28), rs.uniform(14, 40), rs.uniform(1.5, 4.0)
        x = (x0 + vx * t + sw * math.sin(sp * t * 0.6 + ph)) % (W + 160) - 80
        y = (y0 + vy * t + 12 * math.sin(sp * t + ph)) % (H + 160) - 80
        k = int(t * sp * 2 + ph * 3) % 8
        spr = rotate_rgba(petal_sprite(size, k), math.degrees(0.6 * math.sin(sp * t + ph)) + ph * 20)
        al = int(255 * ramp * (0.95 if z else 0.8))
        layer = front if z else base
        s2 = spr.copy(); s2.putalpha(spr.getchannel('A').point(lambda v, al=al: v * al // 255))
        layer.paste(s2, (int(x - spr.width / 2), int(y - spr.height / 2)), s2)           # paste accepte les coordonnées négatives
    return np.array(base.convert('RGB')).astype(np.float32), front


def draw_mew(img, t):
    x, y, sc, ang, w, op = mew_state(t)
    if op <= 0.01 or sc <= 0.005: return img
    A, B = mew_sources(); h, wd = A.shape[:2]
    spr = resize_rgba(mew_blend(w), (max(2, int(round(wd * sc))), max(2, int(round(h * sc)))))
    spr = rotate_rgba(spr, ang)
    if op < 0.999:
        a = spr.getchannel('A').point(lambda v, o=op: int(v * o)); spr.putalpha(a)
    base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')
    sh = Image.new('RGBA', spr.size, (255, 250, 235, 0))                          # halo clair derrière Mew, plus fort quand il surgit du soleil
    halo = spr.getchannel('A').filter(ImageFilter.GaussianBlur(max(2, 14 * sc + 4)))
    glow = clamp01(1.0 - (t - 0.8) / 7.0) * 0.8 + 0.18
    sh.putalpha(halo.point(lambda v, g=glow: int(v * g * 0.55)))
    base.paste(sh, (int(x - spr.width / 2), int(y - spr.height / 2)), sh)
    base.paste(spr, (int(x - spr.width / 2), int(y - spr.height / 2)), spr)
    return np.array(base.convert('RGB')).astype(np.float32)


def vignette(img):
    yy, xx = yy_xx()
    d = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    return img * (1 - 0.10 * np.clip(d - 0.6, 0, 1) ** 1.6)[..., None]


def render(t):
    """Cadre 576 x 768 x 3 (uint8) à l'instant t."""
    y = cam_y(t)
    img = bg_frame(y)
    img = clouds(img, t, y)
    img = sun_light(img, t, y)
    img = rings(img, t, y)
    img, front = petals(img, t)
    img = draw_mew(img, t)
    if front is not None:
        base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA'); base.alpha_composite(front)
        img = np.array(base.convert('RGB')).astype(np.float32)
    img = vignette(img)
    if t > 25.6:                                                                # éclat blanc puis fondu de sortie
        u = smooth((t - 25.6) / 1.6); img = img * (1 - u) + 255.0 * u
        if t > 27.0: img = img * (1 - smooth((t - 27.0) / 1.0))
    if t < 1.2:
        u = smooth(t / 1.2)
        img = img * u + np.array([35, 60, 110], np.float32)[None, None, :] * (1 - u)
    return np.clip(img, 0, 255).astype(np.uint8)


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(video=True):
    OUT.mkdir(parents=True, exist_ok=True)
    for d in ('calques', 'review'):
        (OUT / d).mkdir(exist_ok=True)
    A, B = mew_sources()
    Image.fromarray(A).save(OUT / 'calques/IMW3_mew_pose_A.png'); Image.fromarray(B).save(OUT / 'calques/IMW3_mew_pose_B.png')
    Image.fromarray(mew_blend(0.5)).save(OUT / 'calques/IMW3_mew_pose_AB.png')
    Image.open(RAW / 'fond_vertical.png').convert('RGB').save(OUT / 'calques/IMW3_fond_vertical.png')
    sheet = Image.new('RGBA', (8 * 100, 4 * 100), (60, 70, 110, 255))
    for r, s in enumerate(PETAL_SIZES):
        for k in range(8):
            sp = petal_sprite(s, k); sheet.alpha_composite(sp, (k * 100 + 50 - sp.width // 2, r * 100 + 50 - sp.height // 2))
    sheet.save(OUT / 'calques/IMW3_petales_8poses_4tailles.png')
    jalons = [0.5, 2.0, 4.0, 6.0, 7.8, 9.5, 12.0, 15.0, 18.0, 21.0, 23.0, 24.5, 26.0, 27.0, 27.6]
    for t in jalons:
        Image.fromarray(render(t)).save(OUT / f'review/IMW3_t{t:05.1f}s.png')
    if video:
        import imageio
        w = imageio.get_writer(OUT / 'IMW3_traversee.mp4', fps=FPS, codec='libx264', quality=None, macro_block_size=1, pixelformat='yuv420p',
                               ffmpeg_params=['-crf', '19', '-preset', 'slow', '-movflags', '+faststart'])
        for n in range(N_FRAMES):
            w.append_data(render(n / FPS))
            if n % 120 == 0: print('frame', n, '/', N_FRAMES, flush=True)
        w.close()
    A_, B_ = mew_sources()
    man = {
        'lot': 'intro_mew_traversee_v1', 'asset': 'IMW3', 'serie': 'Cinematiques',
        'demande': ["pour l'introduction faut quelque chose de ce genre (capture : Treasure Town (Intro), Explorers of Sky, Spriters Resource)"],
        'choix_agent': {'portee': "une cinematique video, dans l'esprit de l'ouverture du jeu (grand decor vertical parcouru de haut en bas, personnage qui "
                                  "grossit, petales, anneaux de lumiere) ; IMW1 (11 cartes) et IMW2 (fond Ground) sont conserves ; a confirmer",
                        'reference': "le fichier joint n'etait plus dans le bac a sable : travail d'apres l'image vue dans la conversation, rien mesure ni copie"},
        'format': {'size_px': [W, H], 'fps': FPS, 'frames': N_FRAMES, 'duree_s': T_END, 'codec': 'H.264 yuv420p, crf 19'},
        'actes': [{'t_debut_s': a, 't_fin_s': b, 'legende': n} for a, b, n in ACTS],
        'decor': {'fichier': 'source/intro_mew_traversee_v1/bruts/fond_vertical.png', 'sha256': sha(RAW / 'fond_vertical.png'), 'taille': [768, 1376],
                  'defilement_px': CAM_MAX, 'soleil_xy': list(SUN_XY), 'editions': 0},
        'mew': {'poses': ['bruts/mew_peint_a.png', 'bruts/mew_peint_b.png'], 'sha256': [sha(RAW / 'mew_peint_a.png'), sha(RAW / 'mew_peint_b.png')],
                'taille_decoupe': [int(A_.shape[1]), int(A_.shape[0])], 'note': 'pose B generee depuis A : seule la queue differe ; fondu A-B pour la queue',
                'periode_queue_s': 0.9},
        'effets': {'petales': {'nombre': 60, 'tailles_px': PETAL_SIZES, 'poses': 8, 'plans': 2}, 'anneaux': 'du soleil toutes les 2 s (5), un au moment de l arrivee de Mew',
                   'voiles_nuages': 'flous, periodiques, parallaxe x1,25', 'lueur_soleil': 'etoile a 8 branches et halo qui pulsent (3,2 s)'},
        'jalons_s': jalons, 'deterministe': True, 'art_approved': False, 'runtime_tested': False,
        'reserves': ['pas une map PMDO : une video', 'decor et Mew generes (peinture), jamais valides comme assets de jeu ; Mew non valide SpriteCollab',
                     'style de la ressource Treasure Town imite, pas reproduit', 'mp4 compresse : les PNG de calques font foi'],
    }
    (OUT / 'manifest.json').write_text(json.dumps(man, ensure_ascii=False, indent=2) + '\n')
    return jalons


if __name__ == '__main__':
    build(video='--no-video' not in sys.argv)
