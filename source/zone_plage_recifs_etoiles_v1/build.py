#!/usr/bin/env python3
"""ZPR1 - Zone « Plage aux récifs étoilés » (768 x 576, 4:3) : baie turquoise fermée par deux promontoires de roches rouges,
barrière de récifs, lagon, plage de sable avec palmiers, mares, coquillages ; ciel étoilé du jour à la nuit.

Méthode du rendu généré (comme ZRV2) : les bruts sont des images générées (source/<lot>/bruts/, journal : generation.json),
tout le reste est calculé ici :
  - terre_jour.png (terre sur magenta) -> sable, roches, troncs, palmes, herbes, mares, coquillages, bois flotté ;
  - ciel_mer_jour.png (ciel + mer) -> ciel et mer complets (prolongés sous la terre) ;
  - recifs_roches.png / recifs_coraux.png (planches sur magenta) -> récifs émergés et coraux vus à travers l'eau ;
  - astres.png, reflets_astres.png, banc_nuages_jour*.png : bruts de ZRV2 réutilisés tels quels (chemin + sha256) ;
  - ambiances aube / crépuscule / nuit : bruts d'ambiance (retouches générées du décor de jour) servant d'échantillons de
    couleurs (recolor_rank) ; étoiles, Voie lactée, étoile filante, scintillements, houle, écume, marée : procéduraux.
Aucun test dans le moteur PMDO : voir README.md du lot.

    ./.venv/bin/python source/zone_plage_recifs_etoiles_v1/build.py
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LOT = 'zone_plage_recifs_etoiles_v1'
PFX = 'ZPR1'
OUT = ROOT / 'renders' / LOT
CACHE = ROOT / '.cache' / LOT
BRUTS = HERE / 'bruts'
ZRV2 = ROOT / 'source/zone_reveil_prairie_horizon_v2/bruts'
W, H = 768, 576
AMBS = {'jour': 'J', 'aube': 'A', 'crepuscule': 'C', 'nuit': 'N'}
EAU_MARE = [(54, 128, 190), (66, 150, 208), (84, 172, 226), (112, 196, 240), (160, 222, 248), (222, 244, 252)]
PAL_TERRE = {'jaune': 28, 'rouge': 38, 'vert': 24, 'bleu': 12, 'neutre': 8}
# axes des troncs de palmiers relevés sur le brut ramené à 768 x 576 (haut sous la couronne -> pied), demi-largeur du couloir
TRONCS = [([(101, 384), (106, 398), (111, 412), (117, 425), (120, 433)], 5.0),
          ([(167, 383), (165, 400), (162, 415), (160, 430), (157, 450)], 5.0),
          ([(213, 378), (209, 395), (204, 410), (199, 425), (197, 428)], 5.0),
          ([(557, 378), (561, 395), (566, 410), (571, 428), (574, 440)], 5.5),
          ([(613, 394), (615, 410), (617, 425), (619, 440), (620, 455)], 5.5),
          ([(681, 374), (677, 390), (673, 405), (669, 420), (667, 431)], 4.5)]


# ---------------------------------------------------------------- outils (repris de ZRV2, copiés et non importés)
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


def hsv_arr(a):
    a = np.asarray(a, float) / 255
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1); d = mx - mn
    h = np.zeros_like(mx); m = d > 0
    rc = m & (mx == r); gc = m & (mx == g) & ~rc; bc = m & ~rc & ~gc
    h[rc] = ((g - b)[rc] / d[rc]) % 6
    h[gc] = (b - r)[gc] / d[gc] + 2
    h[bc] = (r - g)[bc] / d[bc] + 4
    return h * 60, np.where(mx > 0, d / np.maximum(mx, 1e-9), 0), mx


def palette_of(px, n):
    q = Image.fromarray(px.reshape(-1, 1, 3).astype('uint8')).quantize(colors=n, method=Image.Quantize.MEDIANCUT,
                                                                        dither=Image.Dither.NONE)
    used = np.unique(np.array(q))
    return np.array(q.getpalette(), int).reshape(-1, 3)[used]


def palette_familles(px, tailles):
    """Palette par familles de teintes (jaunes, rouges, verts, bleus, neutres) : les teintes rares (eau des mares, coquillages)
    gardent leurs propres couleurs au lieu d'être absorbées par le sable, qui domine l'image."""
    h, s, v = hsv_arr(px)
    fam = {'jaune': (h >= 36) & (h < 65) & (s >= 0.15), 'vert': (h >= 65) & (h < 160) & (s >= 0.15),
           'bleu': (h >= 160) & (h < 270) & (s >= 0.15), 'neutre': s < 0.15}
    fam['rouge'] = ~(fam['jaune'] | fam['vert'] | fam['bleu'] | fam['neutre'])
    out = []
    for k, n in tailles.items():
        if fam[k].sum():
            out.append(palette_of(px[fam[k]], min(n, max(1, len(np.unique(px[fam[k]], axis=0))))))
    return np.concatenate(out)


def nearest(rgbs, pal):
    flat = rgbs.reshape(-1, 3).astype(int); out = np.empty_like(flat)
    for i in range(0, len(flat), 65536):
        d = ((flat[i:i + 65536, None, :] - pal[None]) ** 2).sum(2); out[i:i + 65536] = pal[d.argmin(1)]
    return out.reshape(rgbs.shape)


def down_rgba(a, fg, size, pal, thr=0.5):
    """Réduction pondérée par la couverture (fond magenta exclu) puis couleurs ramenées à la palette du brut."""
    w = Image.fromarray((fg * 255).astype('uint8')).resize(size, Image.BOX)
    wa = np.array(w, float) / 255
    ch = [np.array(Image.fromarray((a[..., c] * fg).astype(np.float32), 'F').resize(size, Image.BOX)) for c in range(3)]
    col = np.stack(ch, -1) / np.maximum(wa[..., None], 1e-6)
    out = np.zeros((size[1], size[0], 4), 'uint8'); m = wa > thr
    out[m, :3] = nearest(col[m], pal); out[m, 3] = 255
    return out


def save_png(a, path):
    """PNG indexé sans perte (transparence par couleur) quand le calque a au plus 256 couleurs RGBA, sinon RGBA."""
    a = np.ascontiguousarray(a, dtype='uint8'); key = a.view('<u4').reshape(a.shape[:2])
    cols, inv = np.unique(key, return_inverse=True)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if len(cols) > 256:
        Image.fromarray(a).save(path); return
    rgba = cols.astype('<u4').view('uint8').reshape(-1, 4)
    im = Image.fromarray(inv.reshape(a.shape[:2]).astype('uint8'), 'P'); im.putpalette(rgba[:, :3].flatten().tolist())
    im.save(path, transparency=bytes(rgba[:, 3].tolist()))


def recolor_rank(layer, samples):
    """Chaque couleur du calque prend la couleur d'échantillon de même quantile de luminance (pixels pondérés)."""
    out = layer.copy(); m = layer[..., 3] == 255
    if not m.any() or len(samples) == 0:
        return out
    px = layer[m][:, :3].astype(int)
    cols, inv, cnt = np.unique(px, axis=0, return_inverse=True, return_counts=True)
    order = np.argsort(lum(cols), kind='stable'); cum = np.cumsum(cnt[order]); q = (cum - cnt[order] / 2) / cum[-1]
    s = samples[np.argsort(lum(samples), kind='stable')]
    tgt = np.empty_like(cols); tgt[order] = s[np.clip((q * len(s)).astype(int), 0, len(s) - 1)]
    out[m, :3] = tgt[inv.ravel()]
    return out


def fill_nearest(img, known):
    """Remplit les pixels non connus par la couleur du plus proche pixel connu (prolonge un calque sous la terre)."""
    idx = nd.distance_transform_edt(~known, return_distances=False, return_indices=True)
    return img[idx[0], idx[1]]


# ---------------------------------------------------------------- terre, ciel, mer
def terre_jour():
    """Terre du brut généré (1200 x 896) ramenée à 768 x 576, couleurs ramenées à la palette du brut."""
    t = rgb(BRUTS / 'terre_jour.png'); mag = is_magenta(t)
    # pixels de bord mélangés au magenta (liseré rose le long de la côte et des roches) : écartés avant la réduction
    near = nd.binary_dilation(mag, iterations=4)
    tinted = near & ~mag & (t[..., 2] - t[..., 1] > -20)
    fg = ~mag & ~tinted
    pal = palette_familles(t[fg], PAL_TERRE)
    return down_rgba(t, fg.astype(float), (W, H), pal, 0.5), pal


def ciel_mer_jour(land_a):
    """Ciel et mer du brut généré (même cadrage que la terre) ramenés à 768 x 576 au même facteur ; l'horizon est la
    première rangée cyan sous le ciel pâle. Ciel et mer sont prolongés sous la terre (aucun trou derrière les palmes)."""
    raw = rgb(BRUTS / 'ciel_mer_jour.png'); t = rgb(BRUTS / 'terre_jour.png'); land_raw = ~is_magenta(t)
    pal = palette_of(raw[~land_raw], 56)
    small = np.array(Image.fromarray(raw.astype('uint8')).resize((W, H), Image.BOX)).astype(int)
    small = nearest(small, pal)
    land = land_a[..., 3] == 255
    cx = slice(W // 3, 2 * W // 3)
    yh = next(y for y in range(60, H - 1) if small[y, cx, 0].mean() < 150 and small[y - 1, cx, 0].mean() >= 150)
    rows = np.arange(H)[:, None]
    clean = ~nd.binary_dilation(land, iterations=3)          # pixels de bord (mêlés à la terre) exclus du prolongement
    ciel_known = clean & (rows < yh)
    mer_known = clean & (rows >= yh)
    ciel = np.zeros((H, W, 4), 'uint8'); mer = np.zeros((H, W, 4), 'uint8')
    sky = fill_nearest(small, ciel_known)
    sea = fill_nearest(small, mer_known)
    ciel[:yh, :, :3] = sky[:yh]; ciel[:yh, :, 3] = 255
    mer[yh:, :, :3] = sea[yh:]; mer[yh:, :, 3] = 255
    return ciel, mer, yh, pal


# ---------------------------------------------------------------- partition de la terre en couches
CL = {'SABLE': 1, 'ROCHE': 2, 'PALME': 3, 'TRONC': 4, 'HERBE': 5, 'MARE': 6, 'COQUILLAGE': 7, 'BOIS': 8}


def classify_land(land):
    """Carte de classes de la terre (0 = pas de terre) d'après la teinte, la taille, la forme et les axes de troncs relevés."""
    m = land[..., 3] == 255; px = land[..., :3].astype(int)
    h, s, v = hsv_arr(px)
    cls = np.zeros((H, W), 'uint8')
    green = m & (h >= 65) & (h <= 150) & (s > 0.18)
    pool = m & (h >= 165) & (h <= 260) & (s > 0.15)
    sand = m & ~green & ~pool & (h >= 36) & (h <= 62) & (s >= 0.28) & (s <= 0.72) & (v >= 0.45)
    cls[m] = CL['ROCHE']; cls[sand] = CL['SABLE']; cls[pool] = CL['MARE']
    # eau : les petites composantes bleutées entourées de vert sont des reflets de palmes, les autres des mares
    lp, npool = nd.label(pool, structure=np.ones((3, 3)))
    mares = np.zeros((H, W), bool)
    for i in range(1, npool + 1):
        reg = lp == i
        ring = nd.binary_dilation(reg, iterations=2) & ~reg
        if reg.sum() < 150 or green[ring].mean() > 0.3:
            cls[reg] = CL['ROCHE']; green = green | (reg & (green[ring].mean() > 0.3))
        else:
            mares |= reg
    # mare = région complète (bord et fond gris-blanc du brut compris) ; seul le sable franc alentour reste du sable
    region = nd.binary_fill_holes(nd.binary_dilation(mares, iterations=3))
    region &= m & ~((cls == CL['SABLE']) & (v >= 0.7))
    cls[region] = CL['MARE']
    # points de sable perdus dans les roches (reflets du brut) -> roche
    ls, ns = nd.label(sand, structure=np.ones((3, 3)))
    for i, sl in enumerate(nd.find_objects(ls)):
        reg = ls == i + 1
        if reg.sum() < 250:
            ring = nd.binary_dilation(reg, iterations=2) & ~reg
            if (cls[ring] == CL['ROCHE']).mean() > 0.6:
                cls[reg] = CL['ROCHE']
    # troncs : couloir autour de chaque axe relevé, dans les pixels ni sable, ni vert, ni eau
    yy, xx = np.mgrid[:H, :W]
    body = (cls == CL['ROCHE'])
    for axe, demi in TRONCS:
        d = np.full((H, W), 1e9)
        for (x0, y0), (x1, y1) in zip(axe[:-1], axe[1:]):
            dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy
            t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / L2, 0, 1)
            d = np.minimum(d, np.hypot(xx - (x0 + t * dx), yy - (y0 + t * dy)))
        cls[(d <= demi) & body & ~green] = CL['TRONC']
    # vert : les couronnes sont les composantes de vert qui touchent le haut d'un tronc ; le reste est de l'herbe
    lab, n = nd.label(green, structure=np.ones((3, 3)))
    tops = [axe[0] for axe, _ in TRONCS]
    crown_ids = set()
    for (x0, y0) in tops:
        win = lab[max(0, y0 - 16):y0 + 2, max(0, x0 - 12):x0 + 13]
        ids = [i for i in np.unique(win) if i]
        if ids:
            crown_ids.add(max(ids, key=lambda i: (win == i).sum()))
    for i in range(1, n + 1):
        cls[lab == i] = CL['PALME'] if i in crown_ids else CL['HERBE']
    # objets posés (coquillages, étoiles de mer, bois flotté, petits rochers) : composantes hors sable
    rest = (cls == CL['ROCHE'])
    lr, nr = nd.label(rest, structure=np.ones((3, 3)))
    ar = nd.sum(rest, lr, range(1, nr + 1))
    for i, sl in enumerate(nd.find_objects(lr)):
        if ar[i] >= 2500:
            continue                                                           # grandes roches
        reg0 = lr == i + 1; reg = nd.binary_fill_holes(reg0)
        ring = nd.binary_dilation(reg, iterations=2) & ~reg
        sandring = (cls[ring] == CL['SABLE']).mean(); trunkring = (cls[ring] == CL['TRONC']).mean()
        area = int(reg.sum()); hm, sm, vm = hsv_arr(px[reg0].mean(0)[None])
        if trunkring > 0.15 and area < 250:
            c = CL['TRONC']                                                    # reste de tronc hors du couloir
        elif sandring < 0.6:
            continue                                                           # touche autre chose que du sable (côte, roches)
        elif area >= 800 and hm[0] >= 14 and 0.4 <= sm[0] <= 0.65:
            c = CL['BOIS']
        elif vm[0] >= 0.72 and area < 700:
            c = CL['COQUILLAGE']
        else:
            c = CL['ROCHE']
        cls[reg & ((cls == CL['SABLE']) | reg0)] = c
    return cls


def debug_classes(cls, path):
    pal = {0: (30, 30, 50), 1: (240, 228, 150), 2: (170, 60, 50), 3: (30, 160, 50), 4: (110, 70, 30), 5: (150, 230, 90),
           6: (80, 190, 240), 7: (255, 150, 200), 8: (200, 140, 60)}
    im = np.zeros(cls.shape + (3,), 'uint8')
    for k, c in pal.items():
        im[cls == k] = c
    Image.fromarray(im).save(path)


# ---------------------------------------------------------------- calques de terre
def partition(land, cls):
    """Calques de terre du jour (RGBA 768 x 576). Les calques du fond (sable, roches) sont complétés derrière chaque objet
    (couleur du plus proche pixel de fond) : aucune palme, herbe ou coquille ne laisse de trou quand elle bouge."""
    base = np.zeros((H, W), 'uint8'); base[cls == CL['SABLE']] = 1; base[cls == CL['ROCHE']] = 2
    known = (base > 0) | (cls == 0)
    idx = nd.distance_transform_edt(~known, return_distances=False, return_indices=True)
    near_base = base[idx[0], idx[1]]; near_col = land[idx[0], idx[1]]
    over = np.isin(cls, [CL['PALME'], CL['TRONC'], CL['HERBE'], CL['MARE'], CL['COQUILLAGE'], CL['BOIS']])
    L = {}
    for name, b in (('sable', 1), ('rochers', 2)):
        a = np.zeros((H, W, 4), 'uint8'); own = base == b; behind = over & (near_base == b)
        a[own] = land[own]; a[behind] = near_col[behind]
        L[name] = a
    for name, c in (('mares', 'MARE'), ('coquillages', 'COQUILLAGE'), ('bois_flotte', 'BOIS'), ('troncs', 'TRONC'),
                    ('palmes', 'PALME'), ('herbes', 'HERBE')):
        a = np.zeros((H, W, 4), 'uint8'); mm = cls == CL[c]; a[mm] = land[mm]; L[name] = a
    L['mares'] = recolor_rank(L['mares'], np.array(EAU_MARE))      # eau bleue (le brut, mêlé au sable, la rendait grise)
    return L


def over(dst, src):
    """Composition alpha binaire (calques opaques ou transparents)."""
    m = src[..., 3] > 0
    out = dst.copy(); out[m] = src[m]
    return out


def compose(layers, order):
    img = np.zeros((H, W, 4), 'uint8'); img[..., 3] = 255
    for n in order:
        if n in layers:
            img = over(img, layers[n])
    return img


# ---------------------------------------------------------------- récifs : sprites des planches générées
def cut_sprites(path):
    """Découpe une planche sur magenta en sprites (composantes regroupées par fermeture ; poussière ignorée)."""
    a = rgb(path); fg = ~is_magenta(a)
    lab, n = nd.label(nd.binary_dilation(fg, iterations=7), structure=np.ones((3, 3)))
    out = []
    for i, sl in enumerate(nd.find_objects(lab)):
        reg = (lab == i + 1) & fg
        if reg.sum() < 900:
            continue
        ys, xs = np.nonzero(reg); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        out.append({'rgb': a[y0:y1, x0:x1], 'fg': reg[y0:y1, x0:x1], 'box': (int(x0), int(y0), int(x1), int(y1))})
    return out, a


def name_rocks(sp):
    """Les sept récifs rocheux de la planche, repérés par leur position dans la planche."""
    names = {}
    for s_ in sp:
        x0, y0, x1, y1 = s_['box']; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; w = x1 - x0
        if cy < 330 and cx < 330:
            n = 'paire'
        elif cy < 330 and cx < 800:
            n = 'ronde'
        elif cy < 400:
            n = 'amas'
        elif cx < 330 and cy < 650:
            n = 'pic'
        elif cy < 650:
            n = 'moyen'
        elif w > 450 and cx < 600:
            n = 'banc'
        else:
            n = 'ile'
        names[n] = s_
    return names


CORAUX = ['cerveau_orange', 'ramifie_orange', 'eventail_rose', 'tubes_violets', 'table_jaune', 'anemones', 'gorgone_rouge',
          'cerveau_rose', 'ramifie_bleu', 'massif_mixte', 'trois_ronds', 'etoiles_oursin']


def name_corals(sp):
    rows = sorted(sp, key=lambda s_: (s_['box'][1] + s_['box'][3]) / 2)
    rows = [sorted(rows[i * 4:(i + 1) * 4], key=lambda s_: s_['box'][0]) for i in range(3)]
    return dict(zip(CORAUX, [s_ for r in rows for s_ in r]))


def sprite_rgba(s_, width, pal, drop_shadow=False, thr=0.45):
    """Sprite réduit à la largeur donnée (couverture pondérée, palette du brut). drop_shadow : retire l'ombre rouge sombre sous
    le liseré clair de la base (elle serait un halo rouge sur l'eau)."""
    fg = s_['fg'].copy(); a = s_['rgb']
    if drop_shadow:
        h_, sat, v_ = hsv_arr(a)
        cream = fg & (v_ > 0.82) & (sat < 0.3)
        for x in range(fg.shape[1]):
            ys = np.nonzero(cream[:, x])[0]
            if len(ys):
                fg[ys.max() + 2:, x] = False
    ys, xs = np.nonzero(fg); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    a, fg = a[y0:y1, x0:x1], fg[y0:y1, x0:x1]
    size = (max(3, int(round(width))), max(3, int(round(width * fg.shape[0] / fg.shape[1]))))
    return down_rgba(a, fg.astype(float), size, pal, thr)


def paste(layer, spr, cx, base_y):
    """Pose un sprite (RGBA) en bas-centre sur un calque plein cadre ; retourne le masque posé."""
    h_, w_ = spr.shape[:2]; x0 = int(round(cx - w_ / 2)); y0 = int(round(base_y - h_))
    m = np.zeros((H, W), bool)
    ys, xs = np.nonzero(spr[..., 3] == 255); ty, tx = ys + y0, xs + x0
    ok = (ty >= 0) & (ty < H) & (tx >= 0) & (tx < W)
    layer[ty[ok], tx[ok]] = spr[ys[ok], xs[ok]]; m[ty[ok], tx[ok]] = True
    return m


# (sprite, centre x, pied y, largeur px) : du fond vers l'avant
RECIFS = [('pic', 222, 232, 30), ('paire', 610, 226, 22), ('ronde', 330, 214, 22),
          ('ile', 268, 288, 74), ('moyen', 560, 272, 58), ('amas', 400, 268, 46),
          ('banc', 252, 326, 74), ('ronde', 506, 332, 28), ('paire', 338, 342, 20)]
# (corail, centre x, pied y, largeur px) : sous l'eau
CORAUX_POS = [('gorgone_rouge', 214, 268, 30), ('massif_mixte', 612, 266, 40), ('cerveau_orange', 304, 326, 34),
              ('table_jaune', 346, 306, 36), ('eventail_rose', 408, 330, 30), ('tubes_violets', 452, 312, 28),
              ('cerveau_rose', 484, 344, 30), ('ramifie_orange', 528, 326, 34), ('anemones', 574, 306, 34),
              ('ramifie_bleu', 290, 352, 26), ('trois_ronds', 368, 356, 22), ('etoiles_oursin', 432, 356, 24),
              ('cerveau_orange', 198, 292, 28)]
CORAIL_TEINTE = 0.20                                   # part de la couleur de la mer mêlée au corail (vu à travers l'eau)
TACHE_FONCE = 0.74                                     # eau plus sombre sous un corail (patate de corail)


def reef_assets(sea_vis):
    """Sprites de récifs posés une fois (couleurs du brut) : coraux, patates d'eau sombre, roches émergées et leurs masques.
    sea_vis : mer visible (ni terre ni calque de terre) ; rien n'est posé ailleurs."""
    sp_r, raw_r = cut_sprites(BRUTS / 'recifs_roches.png'); sp_c, raw_c = cut_sprites(BRUTS / 'recifs_coraux.png')
    rocks, corals = name_rocks(sp_r), name_corals(sp_c)
    pal_r = palette_familles(raw_r[~is_magenta(raw_r)], {'rouge': 30, 'vert': 6, 'neutre': 6, 'jaune': 6})
    pal_c = palette_familles(raw_c[~is_magenta(raw_c)], {'rouge': 26, 'jaune': 12, 'vert': 12, 'bleu': 14, 'neutre': 4})
    coral = np.zeros((H, W, 4), 'uint8'); rock = np.zeros((H, W, 4), 'uint8')
    mc, mr, patch = [], [], np.zeros((H, W), bool)
    yy, xx = np.mgrid[:H, :W]
    for nom, cx, by, w in CORAUX_POS:                  # patates : eau plus sombre sous chaque corail, bord tramé
        d = ((xx - cx) / (w * 0.80)) ** 2 + ((yy - (by - w * 0.28)) / (w * 0.42)) ** 2
        patch |= (d <= 0.62) | ((d > 0.62) & (d <= 1.0) & ((xx + yy) % 2 == 0))
    for nom, cx, by, w in CORAUX_POS:
        mc.append(paste(coral, sprite_rgba(corals[nom], w, pal_c), cx, by))
    for nom, cx, by, w in RECIFS:
        mr.append(paste(rock, sprite_rgba(rocks[nom], w, pal_r, drop_shadow=True), cx, by))
    patch &= sea_vis
    cm = np.zeros((H, W), bool)
    for m in mc:
        cm |= m
    cm &= sea_vis; coral[~cm] = 0
    rm = np.zeros((H, W), bool)
    for m in mr:
        rm |= m
    rock[~sea_vis] = 0; rm &= sea_vis
    return {'coral': coral, 'patch': patch, 'rock': rock, 'coral_mask': cm, 'rock_mask': rm, 'rock_masks': mr, 'coral_masks': mc}


def relight(layer, day_smp, amb_smp):
    """Change l'éclairage d'un calque sans perdre ses teintes propres (algues, liseré clair) : chaque couleur est multipliée par le
    rapport (couleur de l'ambiance / couleur du jour) des roches de même quantile de luminance. Rapport 1 le jour."""
    out = layer.copy(); m = layer[..., 3] == 255
    if not m.any():
        return out
    ds = day_smp[np.argsort(lum(day_smp), kind='stable')].astype(float); asm = amb_smp[np.argsort(lum(amb_smp), kind='stable')].astype(float)
    px = layer[m][:, :3].astype(float); cols, inv = np.unique(px, axis=0, return_inverse=True)
    q = np.searchsorted(lum(ds), lum(cols)) / len(ds)
    D = ds[np.clip((q * len(ds)).astype(int), 0, len(ds) - 1)]; T = asm[np.clip((q * len(asm)).astype(int), 0, len(asm) - 1)]
    ratio = np.clip((T + 8) / (D + 8), 0.2, 2.2)
    out[m, :3] = np.clip(cols * ratio, 0, 255).astype('uint8')[inv.ravel()]
    return out


def reef_ambiance(A, sea_rgb, amb, day_rock_smp, amb_rock_smp):
    """Récifs d'une ambiance : coraux vus à travers l'eau (teinte et luminosité de l'ambiance), roches par quantile de luminance."""
    tint, dim = CORAIL_AMB[amb]
    coraux = np.zeros((H, W, 4), 'uint8')
    coraux[A['patch'], :3] = np.clip(sea_rgb[A['patch']] * TACHE_FONCE, 0, 255).astype('uint8'); coraux[A['patch'], 3] = 255
    cm = A['coral_mask']
    coraux[cm, :3] = np.clip((1 - tint) * A['coral'][cm, :3] * dim + tint * sea_rgb[cm], 0, 255).astype('uint8'); coraux[cm, 3] = 255
    recifs = relight(A['rock'], day_rock_smp, amb_rock_smp)
    return coraux, recifs


# ---------------------------------------------------------------- repris à l'identique de ZRV2 (zone_reveil_prairie_horizon_v2/build.py)
# Lois et constantes : nuages (bande de 768 px, 384 phases), scintillement de l'horizon (16 x 4 ticks), étoiles (24 x 5 ticks),
# houle 12 x 10 ticks. Les planches brutes réutilisées (astres, reflets, bancs de nuages) sont copiées dans bruts/ (sha256 dans generation.json).
SWELL_STEPS, SWELL_TICKS = 12, 10                  # V24P04A : BPA 12 crans x 10 ticks
SWELL_PASSES = 2                                   # V24P04A (12 images décodées) : une crête avance de 2 rangées par cycle, 5 à 8 px par cran
GLINT_STEPS, GLINT_TICKS = 16, 4                   # V24P04A : palettes animées 16 crans x 4 ticks
GLINT_LEVELS = [1, 1, 2, 2, 1, 1, 0, 0, 0, 0, 1, 1, 2, 1, 0, 0]   # 0 éteint, 1 couleur du brut, 2 blanc
CLOUD_PERIOD, CLOUD_PAS, CLOUD_TICKS = 768, 2, 16  # période = largeur de l'écran : plus aucun nuage répété (256 px = 3 fois le même banc)
CLOUD_PHASES = CLOUD_PERIOD // CLOUD_PAS           # 384 phases ; vitesse inchangée (1 px / 8 ticks)
CLOUD_TINT = 16                                    # raccord : fondu des teintes sur 16 colonnes
CLOUD_BLEND = 0                                    # pas de fondu (il laissait des colonnes isolées) : coupe raccordée
STAR_PHASES, STAR_TICKS = 24, 5
REFLET_SPAN, REFLET_SX = 172, 0.42                 # reflets : hauteur couverte sous l'horizon, échelle horizontale
CLOUD_BASE_PX, CLOUD_FLAT_MIN, CLOUD_DOME = 17, 40, 30   # base pleine gardée (px finaux) ; sommets plats rognés -> arrondis (px du brut A)
CLOUD_S0, CLOUD_EDGE = 0.30, 0.15                  # échelle provisoire ; coupes cherchées dans les 15 % du début et de la fin de chaque banc
CLOUD_BANKS = [('banc_nuages_jour_c.png', 1.0, (0, 1200)),   # (brut, échelle relative, colonnes utilisables), mis bout à bout en boucle
               ('banc_nuages_jour.png', 1.0, (0, 360)),      # x 375-1075 : identique au brut c (copié par le générateur) -> non repris
               ('banc_nuages_jour_b.png', None, (0, 1584))]  # None : sommets ramenés à la hauteur de ceux du banc A


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


def reflet_dashes(sheet, idx):
    """Planche de reflets générée : colonne idx (0 lune, 1 aube, 2 crépuscule) -> traits (composantes) replacés sous l'astre.
    Hauteur de la colonne -> [YH + 1, YH + 1 + REFLET_SPAN] ; largeur x REFLET_SX ; épaisseur 1 px au loin, 2 px près ;
    les étincelles (composantes hautes) gardent leur forme au cinquième."""
    fg = ~is_magenta(sheet); cx_ = np.nonzero(fg.any(0))[0]
    groups = np.split(cx_, np.nonzero(np.diff(cx_) > 10)[0] + 1)
    g = groups[idx]; x0, x1 = int(g[0]), int(g[-1])
    sub, m = sheet[:, x0:x1 + 1], fg[:, x0:x1 + 1]
    rows = np.nonzero(m.any(1))[0]; ytop, ybot = int(rows.min()), int(rows.max()); axis = (x1 - x0) / 2
    pal = palette_of(sub[m], 16)
    lab, n = nd.label(m, structure=np.ones((3, 3)))
    dashes = []
    for i, sl in enumerate(nd.find_objects(lab)):
        mm = lab[sl] == i + 1
        if mm.sum() < 6:
            continue
        cy = (sl[0].start + sl[0].stop - 1) / 2; cx = (sl[1].start + sl[1].stop - 1) / 2
        v = (cy - ytop) / (ybot - ytop); h_, w_ = mm.shape
        if h_ > 18:                                   # étincelle en croix
            size = (max(3, round(w_ * 0.2)), max(3, round(h_ * 0.2))); thr = 0.3
        else:
            size = (max(1, round(w_ * REFLET_SX)), 1 if v < 0.45 else 2); thr = 0.35
        spr = down_rgba(sub[sl], mm, size, pal, thr)
        if not (spr[..., 3] == 255).any():
            continue
        dashes.append({'y': int(round(YH + 1 + v * REFLET_SPAN - size[1] / 2)), 'dx': (cx - axis) * REFLET_SX, 'spr': spr,
                       'ph': (hsh(idx, i, 11) % 1000) / 1000 * 2 * math.pi})
    return dashes, {'colonne_brut': [x0, x1], 'rangees_brut': [ytop, ybot], 'traits': len(dashes)}


def round_flat(raw, r):
    """Sommet plat de plus de CLOUD_FLAT_MIN px du brut = nuage rogné par le générateur : ses colonnes descendent
    en dôme parabolique, le liseré clair du sommet descend avec elles."""
    raw = raw.copy(); fg = ~is_magenta(raw); Wr = raw.shape[1]
    tops = np.array([int(np.argmax(fg[:, x])) for x in range(Wr)])
    runs, s0 = [], 0
    for x in range(1, Wr + 1):
        if x == Wr or tops[x] != tops[s0]:
            if x - s0 >= CLOUD_FLAT_MIN:                   # en px du brut, pour tous les bancs (B, plus fin, est plus réduit)
                runs.append((s0, x - 1, int(tops[s0])))
            s0 = x
    for x0, x1, ty in runs:
        c = (x0 + x1) / 2; hw = (x1 - x0) / 2 + 6
        for x in range(max(0, int(c - hw)), min(Wr, int(c + hw) + 1)):
            d = int(round(CLOUD_DOME * ((x - c) / hw) ** 2))
            t = int(tops[x]); d = ty + d - t          # le sommet descend jusqu'au dôme, jamais plus bas
            if d <= 0:
                continue
            n = int(round(80 / r)); col, cm = raw[t:t + n, x].copy(), fg[t:t + n, x].copy(); n = len(col)
            raw[t:t + d, x] = (255, 0, 255); fg[t:t + d, x] = False
            raw[t + d:t + n, x] = col[:n - d]; fg[t + d:t + n, x] = cm[:n - d]
    return raw, fg, runs


def bank_band(raw, r):
    """Banc du haut d'un brut : du premier pixel de nuage jusqu'à CLOUD_BASE_PX (espace final) dans la base pleine."""
    raw, fg, runs = round_flat(raw, r)
    top = int(np.nonzero(fg.any(1))[0].min())
    full = next(y for y in range(top, raw.shape[0]) if fg[y].all())
    bottom = min(raw.shape[0] - 1, full + int(round(CLOUD_BASE_PX / (CLOUD_S0 * r))))
    return raw[top:bottom + 1], fg[top:bottom + 1], runs, (top, full, bottom)


def _piece(band, m, x0, x1, sc, pal, hh):
    """Colonnes [x0, x1) du banc réduites à l'échelle sc, posées en bas d'une bande de hauteur hh."""
    x0, x1 = max(0, int(round(x0))), min(band.shape[1], int(round(x1)))
    size = (max(1, int(round((x1 - x0) * sc))), max(1, int(round(band.shape[0] * sc))))
    p = down_rgba(band[:, x0:x1], m[:, x0:x1], size, pal)
    out = np.zeros((hh, p.shape[1], 4), 'uint8'); out[hh - p.shape[0]:] = p[-hh:]
    return out


def _tops(p):
    al = p[..., 3] == 255
    return np.where(al.any(0), al.argmax(0), p.shape[0]).astype(float)


def cloud_strip(raws):
    """Bande périodique de CLOUD_PERIOD px (= largeur de l'écran : aucun nuage répété à l'écran) faite de bancs générés
    différents mis bout à bout (CLOUD_BANKS, en boucle). Chaque banc : sommets plats arrondis, échelle relative (le banc B,
    plus haut, est ramené à la hauteur des sommets du banc A), colonnes utilisables (hors copie du générateur). Raccords :
    colonnes où la silhouette du banc suivant prolonge celle du banc précédent (écart des sommets sur 8 px + écart de
    teinte + marche entre les deux colonnes jointes), puis fondu des teintes seules sur CLOUD_TINT colonnes ; l'ensemble est remis à l'échelle pour faire 768 px."""
    bands, info = [], {'bancs': []}
    ref = bank_band(raws[CLOUD_BANKS[1][0]], 1.0)[3]
    for name, r, cols in CLOUD_BANKS:
        if r is None:                                 # sommets ramenés à la hauteur de ceux du banc A
            t0, f0, _ = bank_band(raws[name], 1.0)[3]
            r = (ref[1] - ref[0]) / (f0 - t0)
        band, m, runs, rows = bank_band(raws[name], r)
        bands.append((name, r, cols, band, m))
        info['bancs'].append({'brut': name, 'echelle_relative': round(r, 4), 'colonnes_utilisables': list(cols),
                              'rangees_brut': [rows[0], rows[2]], 'sommets_arrondis': [list(x) for x in runs]})
    pal = palette_of(np.concatenate([b[3][b[4]] for b in bands]), 24)
    hh0 = max(int(round(b[3].shape[0] * CLOUD_S0 * b[1])) for b in bands)
    pre = [_piece(b[3], b[4], 0, b[3].shape[1], CLOUD_S0 * b[1], pal, hh0) for b in bands]
    n = len(bands); K = 8; joints = []
    for i in range(n):
        j = (i + 1) % n; pi, pj = pre[i], pre[j]; si = CLOUD_S0 * bands[i][1]; sj = CLOUD_S0 * bands[j][1]
        ci, cj = bands[i][2], bands[j][2]; wi = int(ci[1] * si); wj0, wj1 = int(ci[0] * si), 0
        lo_i, hi_i = int(ci[0] * si + (1 - CLOUD_EDGE) * (ci[1] - ci[0]) * si), min(pi.shape[1], int(round(bands[i][3].shape[1] * si))) - CLOUD_TINT
        hi_i = min(hi_i, int(ci[1] * si))
        lo_j, hi_j = int((cj[0] + 8) * sj), int(cj[0] * sj + CLOUD_EDGE * (cj[1] - cj[0]) * sj)   # pas contre le bord du brut
        ti, tj = _tops(pi), _tops(pj); ai, aj = pi[..., :3].astype(int), pj[..., :3].astype(int)
        best = None
        for e in range(lo_i, hi_i):
            for s in range(lo_j, hi_j):
                c = (np.abs(ti[e:e + K] - tj[s:s + K]).mean() + np.abs(ai[:, e:e + K] - aj[:, s:s + K]).mean() / 20
                     + np.abs(ti[e - 1] - tj[s]) + np.abs(ai[:, e - 1] - aj[:, s]).mean() / 20)   # et la marche entre les deux colonnes jointes
                c += 10 * ((ti[e - 1] < min(ti[e - 2], tj[s]) - 1) + (tj[s] < min(ti[e - 1], tj[s + 1]) - 1))   # colonne isolée au raccord
                if best is None or c < best[0]:
                    best = (c, e, s)
        joints.append(best)
    lens = [joints[i][1] - joints[i - 1][2] for i in range(n)]      # début du banc i = raccord (i-1 -> i)
    f = CLOUD_PERIOD / sum(lens)
    widths = [int(round(L * f)) for L in lens]; widths[-1] += CLOUD_PERIOD - sum(widths)
    hh = max(int(round(b[3].shape[0] * CLOUD_S0 * b[1] * f)) for b in bands)
    parts = []
    for i, b in enumerate(bands):
        s0 = CLOUD_S0 * b[1]; x0 = joints[i - 1][2] / s0; x1 = joints[i][1] / s0; sc = widths[i] / (x1 - x0)
        p = _piece(b[3], b[4], x0, x1 + CLOUD_TINT / sc, sc, pal, hh)
        if p.shape[1] < widths[i] + CLOUD_TINT:
            p = np.concatenate([p, np.zeros((hh, widths[i] + CLOUD_TINT - p.shape[1], 4), 'uint8')], 1)
        parts.append(p[:, :widths[i] + CLOUD_TINT].astype(float))
        info['bancs'][i]['coupe_brut'] = [int(round(x0)), int(round(x1))]; info['bancs'][i]['largeur_px'] = widths[i]
        info['bancs'][i]['ecart_raccord_suivant'] = round(float(joints[i][0]), 2)
    out = np.concatenate([p[:, :w] for p, w in zip(parts, widths)], 1)
    x = 0
    for i in range(n):                                 # raccord (i-1 -> i) au début du banc i : teintes seules
        prev = parts[i - 1]; wp = widths[i - 1]
        for k in range(CLOUD_TINT):
            w = (k + 0.5) / CLOUD_TINT; cur = out[:, x + k]; o = prev[:, wp + k]
            both = (cur[:, 3] > 0) & (o[:, 3] > 0)
            cur[both, :3] = w * cur[both, :3] + (1 - w) * o[both, :3]
        x += widths[i]
    res = np.zeros(out.shape, 'uint8'); al = out[..., 3] > 127
    res[al, :3] = nearest(out[al, :3], pal); res[al, 3] = 255
    res[-1, :, :3] = np.where(res[-1, :, 3:] == 255, res[-1, :, :3], res[-2, :, :3]); res[-1, :, 3] = 255   # base pleine
    info.update({'taille_bande': list(res.shape[1::-1]), 'echelle': round(CLOUD_S0 * f, 4)})
    return res, pal, info


def cloud_frames(strip, hidden):
    h = strip.shape[0]; frames = []
    for t in range(CLOUD_PHASES):
        a = np.zeros((H, W, 4), 'uint8')
        a[YH - h:YH] = np.tile(np.roll(strip, t * CLOUD_PAS, axis=1), (1, W // CLOUD_PERIOD, 1))
        a[hidden] = 0
        frames.append(a)
    return frames


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


# ---------------------------------------------------------------- ambiances (aube, crépuscule, nuit)
YH = 153                                            # horizon (rangée de la première bande de mer) ; vérifié par ciel_mer_jour()
ECHELLE_AMB = 1.5556                                # retouches générées : 1195 x 896 = 768 x 576 x 1,5556, alignées au pixel (0, 0)
CORAIL_AMB = {'jour': (0.20, 1.00), 'aube': (0.28, 0.92), 'crepuscule': (0.30, 0.78), 'nuit': (0.16, 0.86)}   # (teinte de l'eau, luminosité)


def amb_image(amb):
    """Retouche générée de l'ambiance ramenée à 768 x 576 (moyenne par case) : couleurs et lumière de l'ambiance."""
    return np.array(Image.open(BRUTS / f'ambiance_{amb}.png').convert('RGB').resize((W, H), Image.BOX)).astype(int)


def erode_mask(m, n=1):
    return nd.binary_erosion(m, iterations=n) if n else m


def samples_of(img, mask, erode=1):
    mk = erode_mask(mask, erode)
    if mk.sum() < 40:
        mk = mask
    return img[mk]


def ciel_ambiance(amb, ciel_day):
    """Ciel de l'ambiance : chaque rangée prend la couleur médiane de la même rangée de la retouche (les étoiles, éparses, sont
    écartées par la médiane) ; les couleurs sont ramenées à une palette de l'ambiance."""
    a = amb_image(amb)
    rows = np.array([np.median(a[y], axis=0) for y in range(YH)]).astype(int)
    out = np.zeros((H, W, 4), 'uint8'); out[:YH, :, :3] = rows[:, None, :]; out[:YH, :, 3] = 255
    pal = palette_of(rows, 40)
    out[:YH, :, :3] = nearest(out[:YH, :, :3], pal)
    return out


def mer_ambiance(amb, land, excl):
    """Mer de l'ambiance : pixels de la retouche, sauf là où se trouvent la terre et les récifs (excl) ; ces zones sont prolongées
    par le plus proche pixel de mer propre (aucun trou ni reste de récif peint sous les calques de récifs)."""
    a = amb_image(amb); rows = np.arange(H)[:, None]
    bad = nd.binary_dilation(land | excl, iterations=3)
    known = ~bad & (rows >= YH)
    sea = fill_nearest(a, known)
    pal = palette_of(a[known], 56)
    sea = nearest(sea, pal)
    out = np.zeros((H, W, 4), 'uint8'); out[YH:, :, :3] = sea[YH:]; out[YH:, :, 3] = 255
    return out


def recolor_terre(L, cls, amb):
    """Calques de terre de l'ambiance : chaque couleur prend la couleur de même quantile de luminance des pixels de la retouche
    qui portent la même classe (sable, roches, troncs, palmes...)."""
    a = amb_image(amb); out = {}
    cmap = {'sable': 'SABLE', 'rochers': 'ROCHE', 'troncs': 'TRONC', 'palmes': 'PALME', 'herbes': 'HERBE', 'mares': 'MARE',
            'coquillages': 'COQUILLAGE', 'bois_flotte': 'BOIS'}
    for nom, c in cmap.items():
        smp = samples_of(a, cls == CL[c], 1 if nom in ('sable', 'rochers', 'palmes') else 0)
        out[nom] = recolor_rank(L[nom], smp)
    out['_rocs'] = samples_of(a, cls == CL['ROCHE'], 1)
    return out


def static_layers(amb, ctx):
    """Calques statiques d'une ambiance (RGBA 768 x 576) : ciel, mer, récifs, terre."""
    land, cls, Lday, RA, rd = ctx['land'], ctx['cls'], ctx['Lday'], ctx['RA'], ctx['rd']
    if amb == 'jour':
        L = {k: v.copy() for k, v in Lday.items()}
        L['ciel'] = ctx['ciel_day']; L['mer'] = ctx['mer_day']; ra = rd
    else:
        L = recolor_terre(Lday, cls, amb); ra = L.pop('_rocs')
        L['ciel'] = ciel_ambiance(amb, ctx['ciel_day'])
        L['mer'] = mer_ambiance(amb, land[..., 3] == 255, RA['coral_mask'] | RA['rock_mask'] | RA['patch'])
    L['recifs_coraux'], L['recifs'] = reef_ambiance(RA, L['mer'][..., :3].astype(int), amb, rd, ra)
    return L


ORDER_STATIC = ['ciel', 'mer', 'recifs_coraux', 'recifs', 'sable', 'mares', 'rochers', 'coquillages', 'bois_flotte', 'troncs', 'palmes', 'herbes']


def contexte():
    land, lpal = terre_jour()
    ciel, mer, yh, spal = ciel_mer_jour(land)
    assert yh == YH, yh
    cls = classify_land(land)
    Lday = partition(land, cls)
    sea_vis = (land[..., 3] == 0) & (np.arange(H)[:, None] >= YH)
    RA = reef_assets(sea_vis)
    rd = samples_of(land[..., :3].astype(int), cls == CL['ROCHE'], 1)
    return {'land': land, 'cls': cls, 'Lday': Lday, 'RA': RA, 'rd': rd, 'ciel_day': ciel, 'mer_day': mer, 'sea_vis': sea_vis}


if __name__ == '__main__':
    CACHE.mkdir(parents=True, exist_ok=True)
    ctx = contexte()
    debug_classes(ctx['cls'], CACHE / 'classes.png')
    sheet = Image.new('RGB', (W * 2, H * 2))
    for k, amb in enumerate(AMBS):
        L = static_layers(amb, ctx); im = Image.fromarray(compose(L, ORDER_STATIC)).convert('RGB')
        im.save(CACHE / f'statique_{amb}.png'); sheet.paste(im, ((k % 2) * W, (k // 2) * H))
    sheet.save(CACHE / 'statiques_4.png')
    print('ok')
