"""Zone de réveil V2 (ZRV2) — même prairie que ZRV1, mer et fond refaits. 768 x 576 px, jour / aube / nuit.

Demande (27 septembre), après ZRV1 : « regarde l'animation de la mer V24P04A et des nuages, c'est ce que je te demandais
pour la zone réveil (faut que la zone soit multicalque) : la mer a son propre calque, le ciel, les nuages ; l'idée de la
montagne est bien mais faut que ce soit raccordé logiquement à l'horizon ; animer les nuages, pas m'en rajouter ; les
fleurs animées comme Sky Peak ; génère le reflet de la lune sur la mer et ses animations logiques ». Réponses : mer
GÉNÉRÉE avec V24P04A en référence (pas de pixels natifs), nouvelle version (ZRV1 gardée). Puis : « je veux garder le
layout de la V1, juste corrige la mer et le background, laisse la montagne, mais les nuages derrière la montagne :
la mer => montagne => nuages ».

Profondeur (du plus proche au plus loin) : prairie, mer, montagne (posée sur l'horizon), nuages (posés sur l'horizon,
derrière la montagne, qui défilent), astre, ciel.

- Prairie : calques finaux de ZRV1 relus tels quels (herbe, chemin, fleurs, rochers, buissons, sol complet), mêmes
  collisions, mêmes marqueurs. Seules les FLEURS gagnent une animation (loi du GIF Sky Peak : A B A C, 12 ticks).
- Montagne : la montagne de ZRV1, éditée par le générateur (nuages retirés, pentes prolongées jusqu'à l'horizon),
  recalée à sa place de ZRV1.
- Ciel et mer : brut généré avec V24P04A en référence ; houle (crêtes qui roulent vers la prairie) animée par la loi de
  V24P04A (12 crans x 10 ticks) avec des crêtes générées ; scintillement de l'horizon (16 crans x 4 ticks, comme les
  4 palettes animées de V24P04A) ; écume au pied de la prairie, synchronisée sur la houle.
- Nuages : banc généré, rendu périodique (256 px), qui défile derrière la montagne (256 phases x 8 ticks).
- Aube et nuit : mêmes pixels recolorés par rang de luminance sur les couleurs des bruts d'aube et de nuit de ZRV1 ;
  lune (nuit) et soleil (aube) générés ; reflet de l'astre généré par nous, animé sur la houle (12 x 10 ticks).
Lancer : .venv/bin/python source/zone_reveil_prairie_horizon_v2/build.py [--apercu]
"""
from pathlib import Path
import hashlib, importlib.util, io, json, math, shutil, sys, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
LOT = 'source/zone_reveil_prairie_horizon_v2'
V1LOT = R / 'source/zone_reveil_prairie_horizon_v1'
V1OUT = R / 'renders/zone_reveil_prairie_horizon_v1'
OUT = R / 'renders/zone_reveil_prairie_horizon_v2'
NAMESPACE = 'zone_reveil_prairie_horizon_v2'
STAGE = R / '.cache/zone_reveil_prairie_horizon_v2' / NAMESPACE
PFX = 'ZRV2'
AMB = {'jour': 'J', 'aube': 'A', 'nuit': 'N'}
ASSET = {k: f'zrv2_zone_reveil_{k}' for k in AMB}
W, H = 768, 576
YH = 116                                           # horizon (ZRV1)
V1_SCALE, V1_CROP_X = 0.642857, 1                  # brut ZRV1 (1200 x 896) -> espace final
MOUNT_CROP = (380, 0, 820, 180)                    # zone du brut ZRV1 donnée au générateur (agrandie x 2)
REFS = {'v24p04a': f'{LOT}/references/v24p04a_t000.png', 'v24p02a': f'{LOT}/references/v24p02a_t000.png',
        'skypeak': f'{LOT}/references/skypeak_gif_frame0.png', 'nuit_native': 'bgnightbackgroundpmdskyda.png',
        'gif_skypeak': '2cwdrrs469f61.gif'}
GEN = [
    {'file': 'ciel_mer_jour.png', 'images': [f'{LOT}/references/v24p04a_t000_x4.png'], 'essais': 'deuxieme generation (la premiere, '
     'identique et conforme, a ete perdue avant commit par une reinitialisation de l espace de travail) ; conforme',
     'prompt': 'Pokémon Mystery Dungeon Explorers of Sky background, pixel art, exactly the same colours, palette and pixel style as '
     'the reference image (the ocean horizon scene). Side view of the open ocean seen from a high place. The horizon is a perfectly '
     'straight horizontal line at 30 percent of the image height. Above the horizon: clear blue sky gradient only, darker blue at the '
     'top, pale near the horizon, absolutely no clouds, no mountains, no sun. Below the horizon: the ocean, a bright cyan band with '
     'many tiny white glitter sparkles right under the horizon, then horizontal bands getting deeper blue toward the bottom, with thin '
     'faint darker swell lines. No white wave crests, no foam, no land, no characters, no text.'},
    {'file': 'cretes_jour.png', 'images': [f'{LOT}/references/v24p04a_t000_x4.png'], 'essais': 'deuxieme generation (meme cas) ; '
     'conforme ; la 5e rangee (vague pleine, deferlante) n est pas utilisee',
     'prompt': 'Sprite sheet, pixel art, exactly the same colours and pixel style as the white foam wave crests in the reference image '
     '(Pokémon Mystery Dungeon Explorers of Sky ocean). On a solid flat magenta background (#FF00FF): isolated ocean wave crests seen '
     'from the side, each one a gentle double-hump wave line of white and pale cyan foam with a thin darker blue shadow under it. '
     'Arrange them in 5 rows from very small and thin (top row) to large (bottom row), 2 crests per row: left crest full foam, right '
     'crest thinner breaking foam. Well separated, nothing touching, no water background, no text.'},
    {'file': 'mer_de_nuages_jour.png', 'images': [f'{LOT}/references/v24p04a_t000_x4.png'], 'essais': 'troisieme generation : la '
     'premiere (references GIF + 232233) recopiait la prairie de Sky Peak en neige, ecartee ; la deuxieme, conforme, perdue avant '
     'commit ; celle-ci donne trois bancs empiles, seul celui du bas (base plate) est utilise',
     'prompt': 'Pixel art, same colours and pixel style as the clouds sitting on the horizon in the reference image (Pokémon Mystery '
     'Dungeon Explorers of Sky). A single long, low horizontal bank of fluffy white and pale blue-grey cumulus clouds seen far away, '
     'spanning the full image width, seamlessly tileable left to right, continuous without gaps. Its bottom edge is a perfectly '
     'straight horizontal line; its top edge is puffy billows of varying height. The bank is centred vertically; everything above '
     'and below it is solid flat magenta (#FF00FF). No sky, no sea, no mountains, no text.'},
    {'file': 'montagne_jour.png', 'images': [f'{LOT}/references/v1_montagne_x380_y0_x2.png'], 'essais': 'deuxieme essai : le premier '
     '(brut ZRV1 entier en entree) peignait une montagne geante plein cadre, ecarte (bruts/ecartes/) ; celui-ci garde le cadrage '
     '(rapport 2,444 identique a l entree)',
     'prompt': 'Edit this pixel art image, keeping the exact same framing, size and position. Keep the big snowy mountain and its lower '
     'blue ridges exactly as they are. Remove every cloud (the small clouds near the summit and the cloud band at the bottom): where '
     'the clouds covered the mountain, continue the mountain\'s slopes and ridges straight down with the same icy blue rock and snow '
     'until the very bottom edge of the image, widening naturally. Replace the sky and everything that is not mountain with solid flat '
     'magenta (#FF00FF).'},
    {'file': 'astres.png', 'images': ['source/zone_reveil_prairie_horizon_v1/bruts/decor_nuit.png',
                                      'source/zone_reveil_prairie_horizon_v1/bruts/decor_aube.png'],
     'essais': 'deuxieme generation (meme cas) ; conforme',
     'prompt': 'Pixel art sprite sheet, same pixel style and colours as the moon in the first reference image and the sun in the second '
     '(Pokémon Mystery Dungeon Explorers of Sky). On a solid flat magenta background (#FF00FF): on the left, a large round full moon, '
     'pale yellow with soft darker yellow craters and a thin light rim; on the right, a large round rising sun disk, warm golden '
     'yellow with a lighter centre. Both perfectly round, same size, well separated, no glow halo, no clouds, no text.'},
]
# ---- lois d'animation
SWELL_STEPS, SWELL_TICKS = 12, 10                  # V24P04A : BPA 12 crans x 10 ticks
GLINT_STEPS, GLINT_TICKS = 16, 4                   # V24P04A : palettes animées 16 crans x 4 ticks
GLINT_LEVELS = [1, 1, 2, 2, 1, 1, 0, 0, 0, 0, 1, 1, 2, 1, 0, 0]   # 0 éteint, 1 couleur du brut, 2 blanc
CLOUD_PERIOD, CLOUD_PAS, CLOUD_TICKS = 256, 1, 8
CLOUD_PHASES = CLOUD_PERIOD // CLOUD_PAS
CLOUD_BLEND = 24
FLOWER_TICKS = 12                                  # GIF Sky Peak : 4 images de 200 ms (A B A C)
STAR_PHASES, STAR_TICKS = 24, 5
# houle : y(u) = YH + D0 + A u + B u^2 (profil de V24P04A : 65, 106, 153 px sous l'horizon, ramené à notre mer)
SWELL_D0, SWELL_A, SWELL_B = 40, 40, 4
SWELL_PERIOD_X = 96                                # V24P04A : motif de 96 px (768 = 8 x 96)
CREST_SCALE = 0.157
SIZE_BOUNDS = [0.4, 1.2, 2.0, 2.8]                 # u < 0.4 : houle sombre ; puis tailles 1..4
ASTRE = {'nuit': {'sprite': 0, 'd': 64, 'c': (384, 34)}, 'aube': {'sprite': 1, 'd': 40, 'c': (236, 32)}}
ORDER = ['sol_complet', 'ciel', 'etoiles', 'astre', 'nuages', 'montagne', 'mer', 'scintillement', 'houle', 'reflet', 'ecume',
         'herbe', 'chemin', 'fleurs', 'rochers', 'buissons']
V1_INDEX = {'sol_complet': 0, 'herbe': 1, 'chemin': 2, 'fleurs': 3, 'rochers': 4, 'buissons': 5}


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rgb(p):
    return np.array(Image.open(p).convert('RGB')).astype(int)


def lum(a):
    a = np.asarray(a, float)
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def hsh(*v):
    h = 2166136261
    for x in v:
        h = ((h ^ (int(x) & 0xffffffff)) * 16777619) & 0xffffffff
    return h


def is_magenta(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r - g > 40) & (b - g > 40)                 # fond magenta et bords teintés de magenta


def palette_of(px, n):
    q = Image.fromarray(px.reshape(-1, 1, 3).astype('uint8')).quantize(colors=n, method=Image.Quantize.MEDIANCUT,
                                                                        dither=Image.Dither.NONE)
    return np.array(q.getpalette()[:n * 3], int).reshape(-1, 3)


def nearest(rgbs, pal):
    flat = rgbs.reshape(-1, 3).astype(int); out = np.empty_like(flat)
    for i in range(0, len(flat), 65536):
        d = ((flat[i:i + 65536, None, :] - pal[None]) ** 2).sum(2); out[i:i + 65536] = pal[d.argmin(1)]
    return out.reshape(rgbs.shape)


def down_rgba(a, fg, size, pal):
    """Réduction pondérée par la couverture (fond magenta exclu) puis couleurs ramenées à la palette du brut."""
    w = Image.fromarray((fg * 255).astype('uint8')).resize(size, Image.BOX)
    wa = np.array(w, float) / 255
    ch = [np.array(Image.fromarray((a[..., c] * fg).astype(np.float32), 'F').resize(size, Image.BOX)) for c in range(3)]
    col = np.stack(ch, -1) / np.maximum(wa[..., None], 1e-6)
    out = np.zeros((size[1], size[0], 4), 'uint8'); m = wa > 0.5
    out[m, :3] = nearest(col[m], pal); out[m, 3] = 255
    return out


def recolor_rank(layer, samples):
    """Chaque couleur du calque prend la couleur d'échantillon de même quantile de luminance (pixels pondérés)."""
    out = layer.copy(); m = layer[..., 3] == 255
    if not m.any():
        return out
    px = layer[m][:, :3].astype(int)
    cols, inv, cnt = np.unique(px, axis=0, return_inverse=True, return_counts=True)
    order = np.argsort(lum(cols), kind='stable'); cum = np.cumsum(cnt[order]); q = (cum - cnt[order] / 2) / cum[-1]
    s = samples[np.argsort(lum(samples), kind='stable')]
    tgt = np.empty_like(cols); tgt[order] = s[np.clip((q * len(s)).astype(int), 0, len(s) - 1)]
    out[m, :3] = tgt[inv.ravel()]
    return out


SKY_RAW_ROWS = {'nuit': 70, 'aube': 92}          # rangées de ciel du brut ZRV1 étalées sur les rangées 0..SKY_SPAN du ciel final
SKY_SPAN = 84


def sky_gradient(layer, amb):
    """Ciel d'aube/nuit : couleur de rangée prise dans le ciel du brut ZRV1 (dégradé vertical), tramage du ciel de jour conservé."""
    a = rgb(V1LOT / 'bruts' / f'decor_{amb}.png'); l = lum(a)
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    c = {'nuit': (600, 36, 62), 'aube': (480, 100, 48)}[amb]
    ok = ((xx - c[0]) ** 2 + (yy - c[1]) ** 2 > c[2] ** 2) & (nd.median_filter(l, 5) > l - 25)   # sans astre ni étoiles
    prof = []
    for y in range(SKY_RAW_ROWS[amb] + 1):
        px = a[y][ok[y]]; ly = lum(px)
        prof.append(px[ly <= np.percentile(ly, 40)].mean(0))                   # bas percentile : écarte les nuages
    prof = np.array(prof)
    out = layer.copy(); m = layer[..., 3] == 255
    L = lum(layer[..., :3].astype(int)).astype(float)
    for y in range(layer.shape[0]):
        r = m[y]
        if not r.any():
            continue
        t = min(1.0, y / SKY_SPAN) * SKY_RAW_ROWS[amb]
        i = int(t); f = t - i; tgt = prof[i] * (1 - f) + prof[min(i + 1, len(prof) - 1)] * f
        d = (L[y, r] - L[y, r].mean()) * 0.6
        out[y, r, :3] = np.clip(np.round(tgt[None] + d[:, None]), 0, 255).astype('uint8')
    return out


def v1_layer(amb, name):
    return np.array(Image.open(V1OUT / 'calques' / amb / f'ZRV1{AMB[amb]}_{V1_INDEX[name]:02d}_{name}.png').convert('RGBA'))


# ---------------------------------------------------------------- prairie (ZRV1)
def meadow_mask():
    u = np.zeros((H, W), bool)
    for k in ('herbe', 'chemin', 'fleurs', 'rochers', 'buissons'):
        u |= v1_layer('jour', k)[..., 3] == 255
    return nd.binary_fill_holes(u | (np.arange(H)[:, None] >= H - 16))


def flower_heads(fl):
    """Têtes de fleurs (pixels roses) du calque de jour : graines érodées, chaque pixel rose à la graine la plus proche."""
    a = fl[..., :3].astype(int); m = (fl[..., 3] == 255) & (a[..., 0] > 190) & (a[..., 0] > a[..., 1] + 30)
    seeds, n = nd.label(nd.binary_erosion(m, iterations=2))
    _, (iy, ix) = nd.distance_transform_edt(seeds == 0, return_indices=True)
    lab = np.where(m, seeds[iy, ix], 0)
    return lab, n


def flower_frames(fl, lab, n):
    """Loi du GIF Sky Peak : A B A C ; en B et C chaque tête descend de 1 px et penche de ±1 px (sens propre à la tête)."""
    head = lab > 0; leaf = (fl[..., 3] == 255) & ~head
    d, (iy, ix) = nd.distance_transform_edt(~leaf, return_indices=True)
    base = fl.copy(); fillable = head & (d <= 3)
    base[head] = 0; base[fillable] = fl[iy[fillable], ix[fillable]]
    sign = np.array([0] + [1 if hsh(i, 7) % 2 else -1 for i in range(1, n + 1)])
    ys, xs = np.nonzero(head); ids = lab[ys, xs]; order = np.argsort(ys, kind='stable')
    ys, xs, ids = ys[order], xs[order], ids[order]

    def shifted(k):
        f = base.copy(); dx = sign[ids] * k; dy = np.where(k != 0, 1, 0)
        ty, tx = np.clip(ys + dy, 0, H - 1), np.clip(xs + dx, 0, W - 1)
        f[ty, tx] = fl[ys, xs]
        return f
    A = fl.copy(); B = shifted(1); C = shifted(-1)
    return [A, B, A.copy(), C]


# ---------------------------------------------------------------- ciel et mer
def sky_sea(raw):
    """Horizon du brut = première rangée cyan sous le ciel pâle ; ciel -> [0, YH), mer -> [YH, H) au même facteur vertical."""
    hr = next(y for y in range(40, raw.shape[0] - 1)
              if raw[y, :, 0].mean() < 120 and raw[y - 1, :, 0].mean() >= 120)
    fy = YH / hr
    sky = np.array(Image.fromarray(raw[:hr].astype('uint8')).resize((W, YH), Image.NEAREST)).astype(int)
    n = int(math.ceil((H - YH) / fy)); src = raw[hr:hr + n]
    if len(src) < n:
        src = np.concatenate([src, np.repeat(src[-1:], n - len(src), 0)])
    sea = np.array(Image.fromarray(src.astype('uint8')).resize((W, H - YH), Image.NEAREST)).astype(int)
    return hr, fy, sky, sea


def glints(sea_full, sea_region):
    """Paillettes de la bande de l'horizon : pixels nettement plus clairs que leur voisinage, petits groupes."""
    l = lum(sea_full); zone = sea_region & (np.arange(H)[:, None] < YH + 40)
    sp = zone & (l > nd.median_filter(l, 7) + 22)
    lab, n = nd.label(sp); out = []
    for i, s in enumerate(nd.find_objects(lab)):
        ys, xs = np.nonzero(lab[s] == i + 1); ys += s[0].start; xs += s[1].start
        if len(ys) <= 8:
            out.append(([(int(y), int(x)) for y, x in zip(ys, xs)], hsh(int(ys.mean()), int(xs.mean()), 3) % GLINT_STEPS))
    return out


def glint_frames(gl, base_cols, white):
    frames = []
    for t in range(GLINT_STEPS):
        a = np.zeros((H, W, 4), 'uint8')
        for px, off in gl:
            lv = GLINT_LEVELS[(t + off) % GLINT_STEPS]
            for y, x in px:
                if lv:
                    a[y, x, :3] = base_cols[y, x] if lv == 1 else white; a[y, x, 3] = 255
        frames.append(a)
    return frames


# ---------------------------------------------------------------- houle (loi V24P04A)
def crest_sprites(sheet):
    fg = ~is_magenta(sheet)
    grp, n = nd.label(nd.binary_dilation(fg, iterations=14))
    boxes = []
    for i, s in enumerate(nd.find_objects(grp)):
        m = (grp[s] == i + 1) & fg[s]
        if m.sum() < 800:
            continue
        boxes.append((s, m))
    boxes.sort(key=lambda b: (b[0][0].start + b[0][0].stop) / 2)
    rows = []
    for b in boxes:
        cy = (b[0][0].start + b[0][0].stop) / 2
        if rows and abs(rows[-1][0] - cy) < 60:
            rows[-1][1].append(b)
        else:
            rows.append([cy, [b]])
    pal = palette_of(sheet[fg], 16)
    sprites = []
    for _, bs in rows[:4]:                           # 5e rangée (vague pleine) non utilisée
        bs.sort(key=lambda b: b[0][1].start)
        pair = []
        for s, m in bs[:2]:
            crop = sheet[s]; h_, w_ = m.shape
            size = (max(1, round(w_ * CREST_SCALE)), max(1, round(h_ * CREST_SCALE)))
            pair.append(down_rgba(crop, m, size, pal))
        sprites.append(pair)
    return sprites


def swell_y(u):
    return YH + SWELL_D0 + SWELL_A * u + SWELL_B * u * u


def swell_rows():
    k = 0
    while swell_y(k) < H:
        k += 1
        if swell_y(k - 1) > 300:
            break
    return k


def swell_frames(sprites, sea_region):
    """Crête k au cran s : profondeur u = k + s/12, bas du sprite en y(u), colonnes tous les 96 px ; taille selon u,
    écume pleine / mince en alternance (cran + colonne), comme les deux états alternés de V24P04A. u = k + 1 au cran 12
    = crête k + 1 au cran 0 : la boucle est fermée par construction."""
    swell_sp = []
    for sp in sprites[0]:                             # houle naissante : ombre sombre seule
        s2 = sp.copy(); m = s2[..., 3] == 255; l = lum(s2[..., :3])
        thr = np.percentile(l[m], 35) if m.any() else 0; s2[m & (l > thr)] = 0; swell_sp.append(s2)
    K = swell_rows(); frames = []
    for s in range(SWELL_STEPS):
        a = np.zeros((H, W, 4), 'uint8')
        for k in range(K - 1, -1, -1):
            u = k + s / SWELL_STEPS; y = int(round(swell_y(u)))
            cls = sum(u >= b for b in SIZE_BOUNDS)      # 0 = houle, 1..4 = tailles
            for j in range(W // SWELL_PERIOD_X):
                v = (s + j) % 2
                sp = swell_sp[v] if cls == 0 else sprites[cls - 1][v]
                h_, w_ = sp.shape[:2]; x0 = j * SWELL_PERIOD_X + SWELL_PERIOD_X // 2 - w_ // 2
                ys, xs = np.nonzero(sp[..., 3] == 255)
                ty = ys + y - h_ + 1; tx = (xs + x0) % W; ok = (ty >= YH) & (ty < H)
                a[ty[ok], tx[ok]] = sp[ys[ok], xs[ok]]
        a[~sea_region] = 0
        frames.append(a)
    return frames


def foam_frames(swell, meadow, sea_region, cols):
    """Écume au pied de la prairie : là où une crête touche le bord (6 px au-dessus), gerbe blanche de 2 px ; au cran
    suivant il en reste 1 px ; bulles (pixels isolés 3 à 5 px au-dessus) les deux crans d'après."""
    edge = np.full(W, -1)
    for x in range(W):
        c = np.nonzero(meadow[YH:, x])[0]
        if len(c):
            edge[x] = YH + c[0]
    hit = np.zeros((SWELL_STEPS, W), bool)
    for s, f in enumerate(swell):
        al = f[..., 3] == 255
        for x in range(W):
            e = edge[x]
            if e > YH + 6:
                hit[s, x] = al[e - 6:e, x].any()
    white, pale = cols
    frames = []
    for s in range(SWELL_STEPS):
        a = np.zeros((H, W, 4), 'uint8')
        for x in range(W):
            e = edge[x]
            if e <= YH + 6:
                continue
            if hit[s, x]:
                a[e - 2:e, x, :3] = white; a[e - 2:e, x, 3] = 255
            elif hit[(s - 1) % SWELL_STEPS, x]:
                a[e - 1, x, :3] = pale; a[e - 1, x, 3] = 255
            for back in (1, 2):
                if hit[(s - back) % SWELL_STEPS, x] and hsh(x, s, back) % 5 == 0:
                    yb = e - 3 - hsh(x, s) % 3; a[yb, x, :3] = pale; a[yb, x, 3] = 255
        a[~sea_region] = 0
        frames.append(a)
    return frames


# ---------------------------------------------------------------- reflet de l'astre
def reflection_bands(xc, d):
    """Bandes de reflet (générées) : sous l'astre, de l'horizon vers la prairie, plus larges et plus épaisses en approchant."""
    bands = []; y = YH + 1; i = 0
    while y < H:
        dist = y - YH; h = 1 + dist // 30; hw = d * 0.35 + dist * 0.22
        n = 1 + hsh(i, 1) % 2 + (1 if dist > 60 else 0); dashes = []
        for k in range(n):
            c = ((hsh(i, k, 2) % 1000) / 1000 * 2 - 1) * hw * 0.55
            L = hw * (0.35 + 0.5 * (hsh(i, k, 3) % 1000) / 1000)
            dashes.append((c, L, (hsh(i, k, 4) % 1000) / 1000 * 2 * math.pi, (hsh(i, k, 5) % 1000) / 1000 * 2 * math.pi))
        bands.append({'y': y, 'h': h, 'hw': hw, 'dashes': dashes})
        y += h + 1 + dist // 45; i += 1
    return bands


def reflection_frames(bands, xc, cols, sea_region):
    """Chaque trait : décalage A sin(2 pi s/12 + phi), longueur x (0,8 + 0,2 cos(...)), éteint quand sin(2 theta + phi) < -0,7.
    Couleur : cœur / milieu / bord selon la distance à l'axe. Période 12 crans : boucle fermée, calée sur la houle."""
    core, mid, edge = cols; frames = []
    for s in range(SWELL_STEPS):
        th = 2 * math.pi * s / SWELL_STEPS; a = np.zeros((H, W, 4), 'uint8')
        for b in bands:
            amp = 1 + (b['y'] - YH) / 35
            for c, L, ph, ps in b['dashes']:
                if math.sin(2 * th + ph) < -0.7:
                    continue
                cx = xc + c + amp * math.sin(th + ph); ln = L * (0.8 + 0.2 * math.cos(th + ps))
                x0, x1 = int(round(cx - ln / 2)), int(round(cx + ln / 2))
                for x in range(max(0, x0), min(W, x1 + 1)):
                    r = abs(x - xc) / max(b['hw'], 1)
                    col = core if r < 0.3 else mid if r < 0.65 else edge
                    a[b['y']:b['y'] + b['h'], x, :3] = col; a[b['y']:b['y'] + b['h'], x, 3] = 255
        a[~sea_region] = 0
        frames.append(a)
    return frames


def light_crests(frames, bands, xc, cols):
    """Les crêtes qui passent dans la colonne de reflet prennent les couleurs de l'astre (cœur / milieu)."""
    hw = np.zeros(H)
    for b in bands:
        hw[b['y']:b['y'] + b['h'] + 1 + (b['y'] - YH) // 45] = b['hw']
    xs = np.arange(W)[None, :]; inside = np.abs(xs - xc) < hw[:, None]
    out = []
    for f in frames:
        g = f.copy(); m = (g[..., 3] == 255) & inside; l = lum(g[..., :3])
        g[m & (l > 200), :3] = cols[0]; g[m & (l > 140) & (l <= 200), :3] = cols[1]
        out.append(g)
    return out


# ---------------------------------------------------------------- nuages
def cloud_strip(raw):
    fg = ~is_magenta(raw); cnt = fg.sum(1)
    bottom = max(y for y in range(raw.shape[0]) if cnt[y] > 0.9 * raw.shape[1])
    top = 490 + int(np.argmin(cnt[490:580]))            # rangée la plus vide entre les bancs du milieu et du bas
    band, m = raw[top:bottom + 1], fg[top:bottom + 1]
    m[:2] = False
    wide = CLOUD_PERIOD + CLOUD_BLEND
    size = (wide, max(1, round(m.shape[0] * wide / m.shape[1])))
    pal = palette_of(band[m], 24)
    s = down_rgba(band, m, size, pal).astype(float)
    out = s[:, :CLOUD_PERIOD].copy()
    for x in range(CLOUD_BLEND):                       # raccord : les 24 premières colonnes glissent de la suite vers le début
        w = (x + 0.5) / CLOUD_BLEND
        out[:, x] = w * s[:, x] + (1 - w) * s[:, CLOUD_PERIOD + x]
    res = np.zeros(out.shape, 'uint8'); al = out[..., 3] > 127
    res[al, :3] = nearest(out[al, :3], pal); res[al, 3] = 255
    res[-1, :, :3] = np.where(res[-1, :, 3:] == 255, res[-1, :, :3], res[-2, :, :3]); res[-1, :, 3] = 255   # base pleine
    return res, pal, {'rangees_brut': [int(top), int(bottom)], 'taille_bande': list(res.shape[1::-1])}


def cloud_frames(strip, hidden):
    h = strip.shape[0]; frames = []
    for t in range(CLOUD_PHASES):
        a = np.zeros((H, W, 4), 'uint8')
        a[YH - h:YH] = np.tile(np.roll(strip, t * CLOUD_PAS, axis=1), (1, W // CLOUD_PERIOD, 1))
        a[hidden] = 0
        frames.append(a)
    return frames


# ---------------------------------------------------------------- montagne
def mountain_layer(raw):
    fg = ~is_magenta(raw)
    fx = raw.shape[1] / ((MOUNT_CROP[2] - MOUNT_CROP[0]))            # brut généré -> brut ZRV1
    x0 = MOUNT_CROP[0] * V1_SCALE - V1_CROP_X; f = V1_SCALE / fx
    size = (round(raw.shape[1] * f), YH)
    pal = palette_of(raw[fg], 32)
    sp = down_rgba(raw, fg, size, pal)
    a = np.zeros((H, W, 4), 'uint8'); xi = int(round(x0))
    a[:YH, xi:xi + size[0]] = sp
    m = a[..., 3] == 255
    # pas de coupe verticale aux bords : on prolonge la pente de chaque flanc (droite ajustée sur la silhouette)
    rows = [y for y in range(YH) if m[y].any()]
    left = np.array([np.nonzero(m[y])[0].min() for y in rows]); right = np.array([np.nonzero(m[y])[0].max() for y in rows])
    ys = np.array(rows)
    for side, xsd, lim in (('g', left, xi), ('d', right, xi + size[0] - 1)):
        cut = np.nonzero(np.abs(xsd - lim) <= 1)[0]              # rangées où le brut touche le bord du cadre
        if not len(cut):
            continue
        c0 = cut.min(); fit = slice(max(0, c0 - 30), c0)
        pa = np.polyfit(ys[fit], xsd[fit], 1)
        src = a.copy()
        for y in ys[c0:]:
            xl = int(round(np.polyval(pa, y)))
            if side == 'g':                      # le flanc descend jusqu'à l'horizon : texture du pied recopiée en miroir
                for x in range(max(0, xl), lim):
                    a[y, x] = src[y, 2 * lim - x]
            else:
                for x in range(lim + 1, min(W, xl + 1)):
                    a[y, x] = src[y, 2 * lim - x]
    return a, {'origine_x': round(x0, 2), 'facteur': round(f, 5), 'taille': list(size)}


def astre_sprite(sheet, idx, d):
    fg = ~is_magenta(sheet); lab, n = nd.label(fg)
    objs = sorted([(s, i + 1) for i, s in enumerate(nd.find_objects(lab)) if (lab[s] == i + 1).sum() > 5000],
                  key=lambda o: o[0][1].start)
    s, i = objs[idx]; m = lab[s] == i
    return down_rgba(sheet[s], m, (d, d), palette_of(sheet[s][m], 16))


# ---------------------------------------------------------------- couleurs d'aube et de nuit (bruts ZRV1)
def amb_samples(amb):
    a = rgb(V1LOT / 'bruts' / f'decor_{amb}.png'); l = lum(a)
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    col = {'nuit': 600, 'aube': 480}[amb]                           # colonne du reflet dans le brut ZRV1
    refl = np.abs(xx - col) < 130
    blue = (a[..., 2] > a[..., 0] + 25) if amb == 'nuit' else np.ones(l.shape, bool)       # ciel d'aube rose et violet
    astre = {'nuit': (600, 36, 62), 'aube': (480, 100, 48)}[amb]                        # disque de l'astre ZRV1 exclu
    astre = (xx - astre[0]) ** 2 + (yy - astre[1]) ** 2 <= astre[2] ** 2
    sky = (yy < {'nuit': 60, 'aube': 78}[amb]) & blue & ~astre & (l < 235) & (nd.median_filter(l, 5) > l - 25)
    sea = (yy > 190) & (yy < 420) & ~refl & (l < 150) & ((a[..., 2] > a[..., 0] + 40) if amb == 'nuit' else (a[..., 2] >= a[..., 1]))   # sans reflets dorés
    crest = (yy > 190) & (yy < 420) & ~refl & (l >= 150)
    cloud = (yy > 75) & (yy < 175) & ~((xx > 430) & (xx < 780)) & (l > 90)
    mount = (yy > 30) & (yy < 150) & (xx > 470) & (xx < 740) & ~astre & ((a[..., 2] >= a[..., 0]) if amb == 'nuit' else True)
    s = {k: a[v] for k, v in {'ciel': sky, 'mer': sea, 'cretes': crest, 'nuages': cloud, 'montagne': mount}.items()}
    if len(s['cretes']) < 300:
        s['cretes'] = a[(yy > 190) & (yy < 420) & ~refl][np.argsort(l[(yy > 190) & (yy < 420) & ~refl])[-3000:]]
    assert all(len(v) > 200 for v in s.values()), {k: len(v) for k, v in s.items()}
    return {k: v.astype(int) for k, v in s.items()}


# ---------------------------------------------------------------- étoiles (ZRV1)
def star_state(off, t):
    u = (t + off) % STAR_PHASES
    return 'plein' if 4 <= u <= 11 else ('coeur' if u in (2, 3, 12, 13) else 'eteint')


def star_frames(stars):
    frames = []
    for t in range(STAR_PHASES):
        a = np.zeros((H, W, 4), 'uint8')
        for px, core, off in stars:
            st = star_state(off, t)
            for y, x, r, g, b in (px if st == 'plein' else core if st == 'coeur' else []):
                a[y, x] = (r, g, b, 255)
        frames.append(a)
    return frames


# ---------------------------------------------------------------- ORA, Ground
def write_ora(path, layers, title):
    import xml.etree.ElementTree as ET
    root = ET.Element('image', w=str(W), h=str(H), name=title)
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


def ground(amb, stack, blocked, markers, gfx, tpl):
    tpl = json.loads(json.dumps(tpl)); o = tpl['Object']; gw, gh = W // 8, H // 8; layers, banks = [], []
    for idx, title, frames, ticks in stack:
        bank = gfx.TileBank(f'{PFX}{AMB[amb]}_{idx:02d}_{title.split()[0].upper()}')
        bank.ids[bytes(256)] = (0, 0); bank.data[(0, 0)] = bytes(256)

        def cell(x, y, frames=frames, bank=bank):
            fs = []
            for a in frames:
                f = bank.add(Image.fromarray(a[y*8:y*8+8, x*8:x*8+8]), x, y)
                fs.append(f if f else {'Sheet': bank.name, 'TexLoc': {'X': 0, 'Y': 0}})
            if all(f['TexLoc'] == {'X': 0, 'Y': 0} for f in fs):
                return []
            return [fs[0]] if all(f == fs[0] for f in fs) else fs
        layers.append(gfx.layer(f'{idx:02d} {title}', gw, gh, cell, ticks)); banks.append(bank)
    layers.append(gfx.layer(f'{len(ORDER):02d} Vos elements avant-plan (Top)', gw, gh, draw=4))
    for bank in banks:
        bank.write(STAGE / f'Content/Tile/{bank.name}.tile')
    o.update(Name={'DefaultText': f'Zone de reveil V2 - prairie face a l ocean ({amb})', 'LocalTexts': {}},
             AssetName=ASSET[amb], Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None,
             ViewOffset={'X': 0, 'Y': 0}, ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment=f'PMDO 0.8.12. Zone de reveil V2 ({amb}). Prairie de ZRV1 ; mer, montagne, nuages et ciel sur des calques '
                     'separes, rendu genere reference (V24P04A pour la mer). Houle 12 x 10 ticks et scintillement 16 x 4 ticks '
                     '(lois de V24P04A), nuages 256 x 8 ticks derriere la montagne, fleurs 4 x 12 ticks (GIF Sky Peak), reflet '
                     'de l astre 12 x 10 ticks. Collisions de ZRV1. Aucun warp.')
    o['obstacles'] = [[{'Bounds': {'X': x*8, 'Y': y*8, 'Width': 8, 'Height': 8}, 'Tags': int(blocked[y, x])}
                       for y in range(gh)] for x in range(gw)]
    mk = lambda n, p: {'EntName': n, 'Direction': 4, 'EntEnabled': True, 'triggerType': 0,
                       'Collider': {'X': p[0], 'Y': p[1], 'Width': 16, 'Height': 16}}
    o['Entities'] = [{'Name': 'Entrees et vos acteurs', 'Visible': True, 'MapChars': [], 'GroundObjects': [], 'Spawners': [],
                      'Markers': [mk(n, p) for n, p in markers.items()]}]
    o['Decorations'] = [{'Name': 'Vos decorations', 'Layer': 2, 'Visible': True, 'Anims': []}]
    tpl['Version'] = '0.8.12.0'
    gfx.save(STAGE / f'Data/Ground/{ASSET[amb]}.rsground', json.dumps(tpl, ensure_ascii=False, separators=(',', ':')).encode())
    gfx.save(STAGE / f'Data/Script/{NAMESPACE}/ground/{ASSET[amb]}/init.lua',
             f'-- {ASSET[amb]} : zone de reveil V2 ({amb}), base d edition, aucun warp.\n'
             f'-- Marqueurs : reveil (au bord de la prairie, face a l ocean), entrance (sud).\n'
             f'local {ASSET[amb]} = {{}}\nreturn {ASSET[amb]}\n'.encode())
    return {b.name: len(b.data) for b in banks}


def finish_stage(tools):
    nodes = {}
    for p in sorted((STAGE / 'Content/Tile').glob('*.tile')):
        with p.open('rb') as f:
            nodes[p.stem] = tools.read_node(f)
    (STAGE / 'Content/Tile/index.idx').write_bytes(tools.encode_index(nodes))
    ident = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/meromoonmeri/guilde-treehouse-pmd/' + NAMESPACE)
    (STAGE / 'Mod.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Zone de reveil V2 - prairie face a l ocean (jour, aube, nuit) - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : premiere scene. Prairie fleurie de Sky Peak (fleurs animees) au bord d'un promontoire plat ; en contrebas l'ocean vu de cote, houle qui roule vers la prairie et horizon qui scintille (lois de V24P04A de PMD Ciel) ; la montagne posee sur l'horizon, les nuages qui defilent derriere elle ; reflet anime de la lune (nuit) et du soleil (aube). Trois Grounds : jour, aube, nuit. Pas une aventure jouable.</Description>
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


# ---------------------------------------------------------------- construction des calques
def make_all():
    """Calques et animations des trois ambiances (dictionnaires nom -> (images, ticks)) + mesures."""
    info = {}
    meadow = meadow_mask(); sea_region = (np.arange(H)[:, None] >= YH) & ~meadow
    v1_sea = np.array(Image.open(V1OUT / 'masques/ZRV1_masque_mer.png')) > 127
    info['mer_identique_zrv1'] = bool((v1_sea == sea_region).all())
    # ciel et mer
    raw_sm = rgb(RAW / 'ciel_mer_jour.png')
    hr, fy, sky, sea = sky_sea(raw_sm)
    info['ciel_mer'] = {'horizon_brut': int(hr), 'facteur_vertical': round(fy, 4), 'facteur_horizontal': round(W / raw_sm.shape[1], 4)}
    sea_full = np.zeros((H, W, 3), int); sea_full[YH:] = sea
    gl = glints(sea_full, sea_region)
    glmask = np.zeros((H, W), bool)
    for px, _ in gl:
        for y, x in px:
            glmask[y, x] = True
    plate_pal = np.unique(sea_full[sea_region & ~glmask], axis=0)
    med = np.stack([nd.median_filter(sea_full[..., c], 7) for c in range(3)], -1)
    plate = sea_full.copy(); plate[glmask] = nearest(med[glmask], plate_pal)
    info['scintillement'] = {'paillettes': len(gl), 'pixels': int(glmask.sum())}
    day = {}
    day['ciel'] = np.concatenate([np.dstack([sky, np.full((YH, W), 255)]), np.zeros((H - YH, W, 4), int)]).astype('uint8')
    day['mer'] = np.zeros((H, W, 4), 'uint8'); day['mer'][sea_region, :3] = plate[sea_region]; day['mer'][sea_region, 3] = 255
    white = sea_full[glmask][np.argmax(lum(sea_full[glmask]))] if glmask.any() else np.array([255, 255, 255])
    # montagne (ZRV1), nuages derrière
    mnt, info['montagne'] = mountain_layer(rgb(RAW / 'montagne_jour.png'))
    day['montagne'] = mnt; mmask = mnt[..., 3] == 255
    info['montagne']['base_sur_horizon'] = bool(mmask[YH - 1].any())
    strip, cpal, info['nuages'] = cloud_strip(rgb(RAW / 'mer_de_nuages_jour.png'))
    # houle
    sprites = crest_sprites(rgb(RAW / 'cretes_jour.png'))
    info['cretes'] = {'tailles_px': [[list(s.shape[1::-1]) for s in pair] for pair in sprites]}
    # fleurs : têtes (jour)
    fl_day = v1_layer('jour', 'fleurs'); lab, nheads = flower_heads(fl_day)
    info['fleurs'] = {'tetes': int(nheads)}
    # étoiles de ZRV1 (nuit), gardées si elles restent dans le ciel visible
    v1m = json.loads((V1OUT / 'manifest.json').read_text())
    sc = v1m['ambiances']['nuit']['scintillements']
    ast = np.zeros((H, W), bool)
    yy, xx = np.mgrid[:H, :W]; cx, cy = ASTRE['nuit']['c']; ast = (xx - cx) ** 2 + (yy - cy) ** 2 <= (ASTRE['nuit']['d'] / 2 + 3) ** 2
    cloud_top = YH - strip.shape[0]
    stars = []
    for px, core, off in zip(sc['pixels'], sc['coeurs'], sc['decalages']):
        if all(y < cloud_top and not mmask[y, x] and not ast[y, x] for y, x, *_ in px):
            stars.append(([tuple(p) for p in px], [tuple(p) for p in core], off))
    info['etoiles'] = {'zrv1': len(sc['pixels']), 'gardees': len(stars)}
    astres = rgb(RAW / 'astres.png')
    out = {}
    for amb in AMB:
        L = {}
        L['sol_complet'] = ([v1_layer(amb, 'sol_complet')], 60)
        for k in ('herbe', 'chemin', 'rochers', 'buissons'):
            L[k] = ([v1_layer(amb, k)], 60)
        L['fleurs'] = (flower_frames(v1_layer(amb, 'fleurs'), lab, nheads), FLOWER_TICKS)
        if amb == 'jour':
            ciel, merl, mont, strip_a, spr = day['ciel'], day['mer'], day['montagne'], strip, sprites
            gcols, gwhite = sea_full, white
        else:
            S = amb_samples(amb)
            ciel = sky_gradient(day['ciel'], amb); merl = recolor_rank(day['mer'], S['mer'])
            mont = recolor_rank(day['montagne'], S['montagne']); strip_a = recolor_rank(strip, S['nuages'])
            spr = [[recolor_rank(s, S['cretes']) for s in pair] for pair in sprites]
            glay = np.zeros((H, W, 4), 'uint8'); glay[glmask, :3] = sea_full[glmask]; glay[glmask, 3] = 255
            glay = recolor_rank(glay, S['cretes']); gcols = glay[..., :3].astype(int)
            gwhite = S['cretes'][np.argmax(lum(S['cretes']))]
        L['ciel'] = ([ciel], 60); L['mer'] = ([merl], 60); L['montagne'] = ([mont], 60)
        L['nuages'] = (cloud_frames(strip_a, mont[..., 3] == 255), CLOUD_TICKS)
        L['scintillement'] = (glint_frames(gl, gcols, gwhite), GLINT_TICKS)
        sw = swell_frames(spr, sea_region)
        crest_px = np.concatenate([s[s[..., 3] == 255][:, :3] for pair in spr for s in pair]).astype(int)
        foam_white = crest_px[np.argmax(lum(crest_px))]; foam_pale = crest_px[np.argsort(lum(crest_px))[int(len(crest_px) * 0.7)]]
        if amb in ASTRE:
            A = ASTRE[amb]; sp = astre_sprite(astres, A['sprite'], A['d'])
            al = np.zeros((H, W, 4), 'uint8'); x0, y0 = A['c'][0] - A['d'] // 2, A['c'][1] - A['d'] // 2
            al[y0:y0 + A['d'], x0:x0 + A['d']] = sp
            L['astre'] = ([al], 60)
            spx = sp[sp[..., 3] == 255][:, :3].astype(int); ls = lum(spx)
            core = spx[np.argsort(ls)[int(len(ls) * 0.92)]]; mid = spx[np.argsort(ls)[int(len(ls) * 0.6)]]
            seacol = merl[YH + 40, A['c'][0], :3].astype(int)
            edge = ((mid + seacol) / 2).round().astype(int)
            bands = reflection_bands(A['c'][0], A['d'])
            L['reflet'] = (reflection_frames(bands, A['c'][0], (core, mid, edge), sea_region), SWELL_TICKS)
            sw = light_crests(sw, bands, A['c'][0], (core, mid))
            info.setdefault('reflet', {})[amb] = {'x': A['c'][0], 'bandes': len(bands), 'couleurs': [c.tolist() for c in (core, mid, edge)]}
        if amb == 'nuit':
            L['etoiles'] = (star_frames(stars), STAR_TICKS)
        L['houle'] = (sw, SWELL_TICKS)
        L['ecume'] = (foam_frames(sw, meadow, sea_region, (foam_white, foam_pale)), SWELL_TICKS)
        out[amb] = L
    return out, info, meadow, sea_region, strip


def scene(L, tick):
    im = Image.new('RGBA', (W, H))
    for nm in ORDER:
        if nm in L:
            fr, tk = L[nm]; im.alpha_composite(Image.fromarray(fr[(tick // tk) % len(fr)]))
    return im


def build(apercu=False):
    out, info, meadow, sea_region, strip = make_all()
    if apercu:
        d = Path('/tmp/zrv2'); d.mkdir(exist_ok=True)
        for amb, L in out.items():
            for tk in (0, 30, 60):
                scene(L, tk).save(d / f'{amb}_t{tk:03d}.png')
        print(json.dumps(info, indent=1, ensure_ascii=False)[:3000]); return
    gfx = loadmod('pmdo_codec', R / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
    esn1 = loadmod('esn1', R / 'source/entree_sud_nord_generee_v1/build.py')
    if OUT.exists():
        for d in ['calques', 'animation', 'masques', 'review']:
            shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['masques', 'review']:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    if STAGE.exists():
        shutil.rmtree(STAGE)
    # accès : celui de ZRV1
    v1m = json.loads((V1OUT / 'manifest.json').read_text())
    walk = np.array(Image.open(V1OUT / 'masques/ZRV1_masque_praticable.png')) > 127
    blocked = walk.reshape(H // 8, 8, W // 8, 8).__invert__().mean((1, 3)) > 0.25
    entry, reveil = v1m['access']['entry_px'], v1m['access']['reveil_px']
    reach, explored = esn1.reachable(blocked, (entry[1] // 8, entry[0] // 8), (reveil[1] // 8, reveil[0] // 8))
    assert reach
    markers = {'reveil': reveil, 'entrance': entry}
    for nm, m in (('prairie', meadow), ('mer', sea_region)):
        Image.fromarray((m * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_{nm}.png')
    Image.fromarray(strip).save(OUT / 'masques' / f'{PFX}_jour_nuages_bande.png')
    tpl_zip = zipfile.ZipFile(R / 'mod_metano_expeditions_pmdo_0812.zip')
    tpl = json.loads(tpl_zip.read('metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground'))
    report, counts = {}, {}
    for amb, L in out.items():
        layer_list, stack = [], []
        for i, nm in enumerate(ORDER):
            if nm not in L:
                continue
            frames, ticks = L[nm]
            if len(frames) > 1:
                d = OUT / 'animation' / amb / nm; d.mkdir(parents=True, exist_ok=True)
                for t, fr in enumerate(frames):
                    Image.fromarray(fr).save(d / f'{PFX}{AMB[amb]}_{i:02d}_{nm}_f{t:03d}.png')
                layer_list.append({'index': i, 'nom': nm, 'file': f'animation/{amb}/{nm}/{PFX}{AMB[amb]}_{i:02d}_{nm}_fNNN.png',
                                   'phases': len(frames), 'ticks': ticks})
            else:
                d = OUT / 'calques' / amb; d.mkdir(parents=True, exist_ok=True)
                Image.fromarray(frames[0]).save(d / f'{PFX}{AMB[amb]}_{i:02d}_{nm}.png')
                layer_list.append({'index': i, 'nom': nm, 'file': f'calques/{amb}/{PFX}{AMB[amb]}_{i:02d}_{nm}.png', 'phases': 1, 'ticks': 60})
            stack.append((i, nm.replace('_', ' ') + (f' {len(frames)} phases' if len(frames) > 1 else ''), frames, ticks))
        step = 8
        scenes = [scene(L, tk) for tk in range(0, 480, step)]
        scenes[0].save(OUT / 'review' / f'{PFX}_{amb}_scene_t000.png')
        scenes[0].save(OUT / 'review' / f'{PFX}_{amb}_scene_animee.webp', save_all=True, append_images=scenes[1:],
                       duration=round(step * 1000 / 60), loop=0, quality=90, method=4)
        if amb == 'jour':
            col = scenes[0].copy(); ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
            for y, x in zip(*np.nonzero(blocked)):
                dr.rectangle([x*8, y*8, x*8+7, y*8+7], fill=(220, 40, 40, 90))
            for (qx, qy), c in ((entry, (255, 230, 40, 255)), (reveil, (60, 220, 255, 255))):
                dr.rectangle([qx, qy, qx + 15, qy + 15], outline=c, width=2)
            col.alpha_composite(ov); col.save(OUT / 'review' / f'{PFX}_collisions_marqueurs.png')
        write_ora(OUT / f'{PFX}_zone_reveil_{amb}_calques.ora',
                  {f'{i:02d}_{nm}' + ('_f000' if len(L[nm][0]) > 1 else ''): L[nm][0][0] for i, nm in enumerate(ORDER) if nm in L},
                  f'Zone de reveil ZRV2 ({amb})')
        counts.update(ground(amb, stack, blocked, markers, gfx, tpl))
        report[amb] = {'layers': layer_list}
    finish_stage(tools)
    manifest = {
        'lot': 'zone_reveil_prairie_horizon_v2', 'prefix': PFX, 'prefixes_banques': {k: PFX + v for k, v in AMB.items()},
        'format': '4:3 vaste', 'size_px': [W, H], 'grid_8px': [W // 8, H // 8], 'horizon_y': YH,
        'demande': 'ZRV2 : mer comme V24P04A (houle qui roule, horizon qui scintille), zone multicalque (mer, ciel, nuages, '
                   'montagne separes), montagne raccordee a l horizon, nuages de la mer de nuages animes (pas de nuages ajoutes), '
                   'fleurs animees comme Sky Peak, reflet anime de la lune ; garder le layout de ZRV1, profondeur mer -> montagne -> nuages',
        'choix': {'mer': 'generee avec V24P04A en reference (reponse de l utilisateur), animee par les lois de V24P04A',
                  'version': 'nouvelle version, ZRV1 gardee (reponse de l utilisateur)',
                  'layout': 'celui de ZRV1 (prairie, horizon, montagne, collisions, marqueurs) (demande de l utilisateur)',
                  'petits_pics': 'les petits pics sombres de la mer de nuages de ZRV1 ne sont pas repris : la mer de nuages est '
                                 'remplacee par le banc qui passe derriere la montagne'},
        'base': 'branche de session : calques de ZRV1, utilitaires de ZRV1 et d ESN1 ; etude des animations pour le rendu ROM ; '
                'aucun emprunt aux branches soeurs',
        'method': 'textures canoniques = rendu genere REFERENCE ; aucun pixel natif',
        'references': {k: {'file': v, 'sha256': sha(R / v)} for k, v in REFS.items()},
        'reference_rom': {'depot': 'pret/pmd-sky', 'commit': 'c8073235b39746a7ee74e6cea16c730bd91a1e67', 'cartes': ['v24p04a', 'v24p02a'],
                          'v24p04a': {'bpa': '12 crans x 10 ticks (houle)', 'palettes_animees': '4 palettes, 16 crans x 4 ticks '
                                      '(dont une de 4 crans), scintillement de l horizon', 'motif_horizontal_px': 96,
                                      'cretes_px_sous_horizon': [65, 106, 153]}},
        'generation': GEN,
        'raw_inputs': [{'file': f'{LOT}/bruts/{g["file"]}', 'sha256': sha(RAW / g['file']), 'size': list(Image.open(RAW / g['file']).size)}
                       for g in GEN],
        'zrv1': {'calques': {k: sha(V1OUT / 'calques/jour' / f'ZRV1J_{i:02d}_{k}.png') for k, i in V1_INDEX.items()},
                 'manifest_sha256': sha(V1OUT / 'manifest.json')},
        'mesures': info,
        'houle': {'crans': SWELL_STEPS, 'frame_length_ticks': SWELL_TICKS, 'loi_y': f'y(u) = {YH} + {SWELL_D0} + {SWELL_A} u + {SWELL_B} u^2',
                  'u': 'k + cran / 12', 'periode_x': SWELL_PERIOD_X, 'bornes_tailles': SIZE_BOUNDS, 'echelle_cretes': CREST_SCALE},
        'scintillement': {'crans': GLINT_STEPS, 'frame_length_ticks': GLINT_TICKS, 'niveaux': GLINT_LEVELS},
        'nuages': {'periode_px': CLOUD_PERIOD, 'pas_px': CLOUD_PAS, 'phases': CLOUD_PHASES, 'frame_length_ticks': CLOUD_TICKS,
                   'raccord_px': CLOUD_BLEND, 'hauteur_px': int(strip.shape[0])},
        'fleurs': {'phases': 4, 'frame_length_ticks': FLOWER_TICKS, 'loi': 'A B A C : en B et C chaque tete descend de 1 px et '
                   'penche de +1 / -1 px (sens propre a la tete) ; mesure sur le GIF Sky Peak (images 0 = 2, decalage (±1, +1))'},
        'etoiles': {'phases': STAR_PHASES, 'frame_length_ticks': STAR_TICKS},
        'astres': ASTRE,
        'ambiances': report,
        'access': {'entry_px': entry, 'reveil_px': reveil, 'path_found_16x16': reach, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'walkable_cells': int((~blocked).sum()), 'origine': 'masque praticable de ZRV1'},
        'pmdo': {'target': '0.8.12', 'namespace': NAMESPACE, 'assets': ASSET, 'tiles_per_bank': counts, 'markers': markers, 'warps': 'aucun'},
        'art_approved': False, 'runtime_tested': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(json.dumps(info, indent=1, ensure_ascii=False)[:4000])


if __name__ == '__main__':
    build(apercu='--apercu' in sys.argv)
