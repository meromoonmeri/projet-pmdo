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


def reef_layers(sea_rgb):
    """Calques de récifs du jour : coraux vus à travers l'eau (teintés de la couleur de la mer) et roches émergées."""
    sp_r, raw_r = cut_sprites(BRUTS / 'recifs_roches.png'); sp_c, raw_c = cut_sprites(BRUTS / 'recifs_coraux.png')
    rocks, corals = name_rocks(sp_r), name_corals(sp_c)
    pal_r = palette_familles(raw_r[np.concatenate([s_['fg'].ravel() for s_ in sp_r])[:0].size and None or ~is_magenta(raw_r)],
                             {'rouge': 30, 'vert': 6, 'neutre': 6, 'jaune': 6})
    pal_c = palette_familles(raw_c[~is_magenta(raw_c)], {'rouge': 26, 'jaune': 12, 'vert': 12, 'bleu': 14, 'neutre': 4})
    coraux = np.zeros((H, W, 4), 'uint8'); recifs = np.zeros((H, W, 4), 'uint8')
    masks_c, masks_r = [], []
    yy, xx = np.mgrid[:H, :W]
    for nom, cx, by, w in CORAUX_POS:                  # patates : eau plus sombre sous chaque corail, bord tramé
        d = ((xx - cx) / (w * 0.80)) ** 2 + ((yy - (by - w * 0.28)) / (w * 0.42)) ** 2
        core = d <= 0.62; ring = (d > 0.62) & (d <= 1.0) & ((xx + yy) % 2 == 0)
        pm = (core | ring) & (sea_rgb[..., 2] > 0)
        coraux[pm, :3] = np.clip(sea_rgb[pm] * TACHE_FONCE, 0, 255).astype('uint8'); coraux[pm, 3] = 255
    for nom, cx, by, w in CORAUX_POS:
        spr = sprite_rgba(corals[nom], w, pal_c)
        m = paste(coraux, spr, cx, by); masks_c.append(m)
    # teinte « vu à travers l'eau » : le corail prend une part de la couleur de la mer à cet endroit
    mc = np.zeros((H, W), bool)
    for m in masks_c:
        mc |= m
    coraux[mc, :3] = np.clip((1 - CORAIL_TEINTE) * coraux[mc, :3] + CORAIL_TEINTE * sea_rgb[mc], 0, 255).astype('uint8')
    for nom, cx, by, w in RECIFS:
        spr = sprite_rgba(rocks[nom], w, pal_r, drop_shadow=True)
        masks_r.append(paste(recifs, spr, cx, by))
    return coraux, recifs, masks_c, masks_r, (rocks, corals)


if __name__ == '__main__':
    CACHE.mkdir(parents=True, exist_ok=True)
    land, lpal = terre_jour()
    ciel, mer, yh, spal = ciel_mer_jour(land)
    print('horizon y =', yh)
    cls = classify_land(land)
    debug_classes(cls, CACHE / 'classes.png')
    L = partition(land, cls); L['ciel'] = ciel; L['mer'] = mer
    ORDER0 = ['ciel', 'mer', 'sable', 'mares', 'rochers', 'coquillages', 'bois_flotte', 'troncs', 'palmes', 'herbes']
    Image.fromarray(compose(L, ORDER0)).convert('RGB').save(CACHE / 'jour_terre_mer.png')
    coraux, recifs, mc, mr, (rocks, corals) = reef_layers(mer[..., :3].astype(int))
    L['recifs_coraux'] = coraux; L['recifs'] = recifs
    print('sprites roches', sorted(rocks), 'coraux', len(corals))
    ORDER1 = ['ciel', 'mer', 'recifs_coraux', 'recifs', 'sable', 'mares', 'rochers', 'coquillages', 'bois_flotte', 'troncs', 'palmes', 'herbes']
    comp = compose(L, ORDER1)
    Image.fromarray(comp).convert('RGB').save(CACHE / 'jour_recifs.png')
    # image d'entrée donnée au générateur pour retoucher les ambiances (mise à l'échelle 1200 x 900, sans lissage)
    Image.fromarray(comp[..., :3]).resize((1200, 900), Image.NEAREST).save(BRUTS / 'decor_jour_pour_ambiances.png')
    print('ok')
