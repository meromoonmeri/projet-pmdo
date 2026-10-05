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
import io
import shutil
import uuid
import zipfile
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
CLOUD_BASE_PX, CLOUD_FLAT_MIN, CLOUD_DOME = 17, 40, 30
CLOUD_SINK = 22                                    # ZPR1 : rangées du bas du banc cachées derrière l'horizon (nuages au-delà de la mer)   # base pleine gardée (px finaux) ; sommets plats rognés -> arrondis (px du brut A)
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


# ---------------------------------------------------------------- astres, étoiles, Voie lactée, étoile filante
REFLET_SPAN = 200                                  # le reflet descend jusqu'au rivage de la baie (horizon 153 -> côte 366)
Y_SHORE = 366
HOULE_PASSES, HOULE_K = 1, 7                       # une crête avance d'un intervalle par cycle de 12 crans ; 7 crêtes de l'horizon au rivage
ASTRE = {'jour': {'sprite': 1, 'd': 40, 'c': (600, 52)}, 'aube': {'sprite': 1, 'd': 54, 'c': (470, 100)},
         'crepuscule': {'sprite': 1, 'd': 64, 'c': (560, 98)}, 'nuit': {'sprite': 0, 'd': 56, 'c': (470, 60)}}
RAMPE_SOLEIL = {'aube': [(255, 250, 228), (255, 232, 170), (255, 205, 140), (252, 168, 124), (240, 130, 118)],
                'crepuscule': [(255, 238, 170), (255, 205, 100), (255, 160, 70), (240, 100, 56), (200, 56, 60)]}
HALO = {'jour': ((255, 255, 235), 0.16, 12), 'aube': ((255, 214, 170), 0.30, 26), 'crepuscule': ((255, 150, 80), 0.34, 30),
        'nuit': ((150, 165, 235), 0.22, 18)}
LUMIERE = {'jour': (235, 250, 255), 'aube': (255, 226, 226), 'crepuscule': (255, 190, 150), 'nuit': (140, 172, 232)}   # reflets clairs sur l'eau
GAIN_EAU = {'jour': 1.0, 'aube': 0.9, 'crepuscule': 0.85, 'nuit': 0.6}
ETOILES = {'jour': (0, 14), 'aube': (46, 16), 'crepuscule': (110, 34), 'nuit': (440, 96)}   # (fixes, scintillantes) : à confirmer
ETOILE_K = {'jour': 0.34, 'aube': 0.72, 'crepuscule': 0.86, 'nuit': 1.0}                    # contraste avec le ciel
VOIE_DENSITE = {'jour': 0.0, 'aube': 0.10, 'crepuscule': 0.20, 'nuit': 1.0}
FILANTE = {'crepuscule': (0.7, (96, 26)), 'nuit': (1.0, (150, 20))}                         # (éclat, départ) ; une par cycle de 72 x 5 ticks
FILANTE_PHASES = 72


REFLET_COL = {'nuit': 0, 'aube': 1, 'crepuscule': 2}                # colonne de la planche de reflets (ZRV2)


def astre_sprite(sheet, idx, d):
    """Astre de la planche ZRV2 (0 lune à gauche, 1 soleil à droite) réduit au diamètre d (palette de 16 couleurs du sprite)."""
    fg = ~is_magenta(sheet); lab, n = nd.label(fg)
    objs = sorted([(s_, i + 1) for i, s_ in enumerate(nd.find_objects(lab)) if (lab[s_] == i + 1).sum() > 5000],
                  key=lambda o: o[0][1].start)
    s_, i = objs[idx]; m = lab[s_] == i
    return down_rgba(sheet[s_], m, (d, d), palette_of(sheet[s_][m], 16))


def astre_layer(amb, sheet, sky_rgb):
    """Astre (planche ZRV2), recoloré aube/crépuscule en cinq anneaux, avec un halo tramé ; posé sur le ciel."""
    A = ASTRE[amb]; d = A['d']; sp = astre_sprite(sheet, A['sprite'], d)
    if amb in RAMPE_SOLEIL:
        yy, xx = np.mgrid[:d, :d]; rn = np.hypot(yy - (d - 1) / 2, xx - (d - 1) / 2) / (d / 2)
        ring = np.clip((rn * 5).astype(int), 0, 4); m_ = sp[..., 3] == 255
        for k in range(5):
            sp[m_ & (ring == k), :3] = RAMPE_SOLEIL[amb][k]
    out = np.zeros((H, W, 4), 'uint8'); cx, cy = A['c']
    yy, xx = np.mgrid[:H, :W]; r = np.hypot(xx - cx, yy - cy)
    col, k, rad = HALO[amb]
    for lo, hi, mod in ((d / 2 + 1, d / 2 + 1 + rad * 0.45, 2), (d / 2 + 1 + rad * 0.45, d / 2 + 1 + rad, 4)):
        ring = (r > lo) & (r <= hi) & (yy < YH)
        pat = ((xx + yy) % 2 == 0) if mod == 2 else ((xx % 2 == 0) & (yy % 2 == 0))
        sel = ring & pat
        base = sky_rgb[sel].astype(float)
        out[sel, :3] = np.clip(base + (np.array(col) - base) * (k if mod == 2 else k * 0.7), 0, 255).astype('uint8'); out[sel, 3] = 255
    x0, y0 = cx - d // 2, cy - d // 2
    ys, xs = np.nonzero(sp[..., 3] == 255); ty, tx = ys + y0, xs + x0; ok = (ty >= 0) & (ty < H) & (tx >= 0) & (tx < W)
    out[ty[ok], tx[ok]] = sp[ys[ok], xs[ok]]
    out[YH:] = 0                                       # le calque de mer, au-dessus, cache le bas ; on ne garde rien sous l'horizon
    return out


def _value_noise(shape, cells, seed):
    rng = np.random.default_rng(seed); g = rng.random((cells[1] + 2, cells[0] + 2))
    return nd.zoom(g, (shape[0] / cells[1], shape[1] / cells[0]), order=1)[:shape[0], :shape[1]]


def star_field(amb, ciel_rgb, land_mask, astre_mask):
    """Étoiles du ciel (hasard fixé) : fixes (calque statique) et scintillantes (24 phases x 5 ticks, états plein / cœur / éteint).
    Plus nombreuses en haut ; ni sur la terre, ni sur l'astre et son halo. Teinte = ciel + (étoile - ciel) x contraste de l'ambiance."""
    nfix, nsc = ETOILES[amb]; K = ETOILE_K[amb]
    rng = np.random.default_rng(1000 + hsh(list(AMBS).index(amb), 7) % 1000)
    blocked = land_mask | nd.binary_dilation(astre_mask, iterations=4); blocked[YH - 3:] = True
    occ = np.zeros((H, W), bool); pts = []
    yy = np.arange(YH - 3)
    wy = (1 - yy / YH) ** 1.25 + 0.12; wy = wy / wy.sum()
    tries = 0
    while len(pts) < nfix + nsc and tries < 40000:
        tries += 1
        y = int(rng.choice(yy, p=wy)); x = int(rng.integers(3, W - 3))
        if blocked[y, x] or occ[max(0, y - 3):y + 4, max(0, x - 3):x + 4].any():
            continue
        occ[y, x] = True; pts.append((y, x))
    pal = [(255, 255, 255), (255, 255, 255), (255, 255, 255), (205, 222, 255), (255, 242, 205)]
    fixes = np.zeros((H, W, 4), 'uint8'); twink = []
    for i, (y, x) in enumerate(pts):
        base = np.array(pal[int(rng.integers(len(pal)))], float); sky = ciel_rgb[y, x].astype(float)
        def tone(f):
            return tuple(int(v) for v in np.clip(sky + (base - sky) * K * f, 0, 255))
        if i < nfix:
            f = float(rng.choice([0.55, 0.75, 1.0], p=[0.5, 0.35, 0.15])); fixes[y, x, :3] = tone(f); fixes[y, x, 3] = 255
        else:
            big = rng.random() < 0.42
            c1, c2 = tone(1.0), tone(0.55)
            core = [(y, x, *c2)]
            if big:
                px = [(y, x, *c1)] + [(y + dy, x + dx, *tone(0.62)) for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
                                      if 0 <= y + dy < YH - 2 and 0 <= x + dx < W]
                core = [(y, x, *c1)]
            else:
                px = [(y, x, *c1)]
            twink.append((px, core, int(rng.integers(STAR_PHASES))))
    return fixes, twink


def voie_lactee(amb, ciel_rgb, land_mask, astre_mask):
    """Voie lactée : bande diagonale de poussière d'étoiles (points d'une couleur, jamais de flou), plus dense au cœur."""
    dens = VOIE_DENSITE[amb]; out = np.zeros((H, W, 4), 'uint8')
    if dens <= 0:
        return out
    rng = np.random.default_rng(77); yy, xx = np.mgrid[:H, :W]
    th = math.radians(-22); nx, ny = -math.sin(th), math.cos(th)          # normale de la bande
    dist = (xx - 268) * nx + (yy - 78) * ny
    prof = np.exp(-(dist / 34.0) ** 2)
    lane = 1 - 0.55 * np.exp(-((dist - 9) / 5.0) ** 2)                     # filament sombre le long de la bande
    noise = _value_noise((H, W), (14, 9), 5) * 0.8 + _value_noise((H, W), (40, 28), 6) * 0.5
    p = dens * 0.5 * prof * lane * np.clip(noise, 0, 1.2)
    on = (rng.random((H, W)) < p) & ~land_mask & ~nd.binary_dilation(astre_mask, iterations=8) & (yy < YH - 3)
    cols = np.array([(118, 118, 205), (150, 150, 226), (192, 202, 246), (228, 192, 236), (255, 255, 255)], float)
    pick = np.minimum((rng.random((H, W)) ** 1.8 * 5).astype(int) + (prof > 0.7), 4)
    K = ETOILE_K[amb]; sky = ciel_rgb.astype(float)
    out[on, :3] = np.clip(sky[on] + (cols[pick[on]] - sky[on]) * K * 0.8, 0, 255).astype('uint8'); out[on, 3] = 255
    return out


def etoile_filante(amb, land_mask):
    """Étoile filante : 12 images de passage dans un cycle de 72 x 5 ticks (6 s), tête blanche et queue qui s'éteint."""
    empty = np.zeros((H, W, 4), 'uint8'); frames = [empty] * FILANTE_PHASES
    if amb not in FILANTE:
        return None
    k, (x0, y0) = FILANTE[amb]; v = (7.4, 2.6)
    for i in range(12):
        a = np.zeros((H, W, 4), 'uint8'); frames[10 + i] = a
        hx, hy = x0 + v[0] * i, y0 + v[1] * i
        for j in range(0, 22):
            t = j / 21; px, py = int(round(hx - v[0] * t * 2.4)), int(round(hy - v[1] * t * 2.4))
            if not (0 <= px < W and 0 <= py < YH - 4) or land_mask[py, px]:
                continue
            if j > 4 and j % 2:
                continue
            c = np.array([255, 255, 255], float) * (1 - t) + np.array([120, 150, 235], float) * t
            a[py, px, :3] = np.clip(c * (0.55 + 0.45 * k), 0, 255).astype('uint8'); a[py, px, 3] = 255
    return frames


def cloud_ramp(strip, amb, sky_rgb):
    """Nuages de l'ambiance : chaque couleur du banc de jour prend la couleur de même quantile de luminance sur une rampe
    ombre -> milieu -> lumière tirée du ciel de l'horizon (les nuages n'ont pas de retouche générée)."""
    if amb == 'jour':
        return strip
    sh = sky_rgb[YH - 6, W // 2].astype(float); mid = sky_rgb[YH - 40, W // 2].astype(float)
    mixc = lambda a, b, t: np.array(a, float) * (1 - t) + np.array(b, float) * t
    anchors = {'aube': (mixc(mid, (122, 92, 150), 0.55), mixc(sh, (255, 255, 255), 0.42), mixc((255, 238, 222), sh, 0.3)),
               'crepuscule': (mixc(mid, (60, 28, 86), 0.6), mixc(sh, (240, 110, 80), 0.45), mixc((255, 205, 130), sh, 0.25)),
               'nuit': (mixc(sh, (6, 8, 40), 0.55), mixc(sh, (82, 96, 168), 0.6), mixc((150, 162, 220), sh, 0.2))}[amb]
    out = strip.copy(); m = strip[..., 3] == 255
    px = strip[m][:, :3].astype(int); cols, inv, cnt = np.unique(px, axis=0, return_inverse=True, return_counts=True)
    order = np.argsort(lum(cols), kind='stable'); cum = np.cumsum(cnt[order]); q = np.empty(len(cols)); q[order] = (cum - cnt[order] / 2) / cum[-1]
    lo, md, hi = anchors
    tgt = np.where((q < 0.55)[:, None], lo + (md - lo) * (q / 0.55)[:, None], md + (hi - md) * ((q - 0.55) / 0.45)[:, None])
    out[m, :3] = np.clip(tgt, 0, 255).astype('uint8')[inv.ravel()]
    return out


# ---------------------------------------------------------------- mer : houle, caustiques, écume, marée
def sea_geometry(sea_vis):
    """ys(x) : dernière rangée de mer visible dans chaque colonne (-1 si aucune) ; lissée."""
    ys = np.full(W, -1, int)
    for x in range(W):
        col = sea_vis[YH:, x]
        if col[0]:
            nz = np.nonzero(~col)[0]; ys[x] = YH + (nz[0] if len(nz) else len(col)) - 1
    ok = ys >= 0
    sm = ys.copy(); f = nd.uniform_filter1d(nd.median_filter(ys.astype(float), 15), 9)
    sm[ok] = np.round(f[ok]).astype(int)
    return sm


def houle_frames(sea_rgb, sea_vis, dist_land, ys, amb, tvals=None):
    """Crêtes de houle en arcs qui épousent la baie : la crête de profondeur u est à y = YH + (ys(x) - YH) u^1,7. Le dessin ne
    dépend que de (x, u), donc la boucle de 12 crans est exacte. Les crêtes sont continues (une colonne rejoint la suivante), ne
    sont tracées que là où la pente du rivage reste douce (elles se brisent contre les falaises) et s'éteignent (tramé) près du rivage."""
    g = GAIN_EAU[amb]; hi = np.array(LUMIERE[amb], float); frames = []
    xs = np.arange(W); fade = np.clip((dist_land - 30) / 16, 0, 1)
    slope = np.abs(np.gradient(ys.astype(float))); douce = (ys >= 0) & (slope < 0.75)
    for s in (range(SWELL_STEPS) if tvals is None else tvals):
        a = np.zeros((H, W, 4), 'uint8')
        for k in range(-1, HOULE_K + 1):
            u = (k + HOULE_PASSES * s / SWELL_STEPS) / HOULE_K
            if not 0.03 < u < 0.985:
                continue
            thr = 0.72 - 1.55 * u; th = 1 if u < 0.33 else (2 if u < 0.72 else 3)
            n = np.sin(xs * 0.071 + 9.0 * u) + np.sin(xs * 0.033 - 6.3 * u + 1.3) + 0.6 * np.sin(xs * 0.19 + 17 * u)
            yc = np.round(YH + (ys - YH) * u ** 1.7).astype(int)
            for x in np.nonzero(douce & (n > thr))[0]:
                nx = min(x + 1, W - 1); y_a, y_b = yc[x], (yc[nx] if douce[nx] else yc[x])
                for y in range(min(y_a, y_b), max(y_a, y_b) + th):
                    if y >= H or not sea_vis[y, x] or ((x * 7 + y * 13) % 16) / 16 >= fade[y, x]:
                        continue
                    r = y - min(y_a, y_b)
                    amt = g * (0.20 + 0.48 * u ** 0.8) * (1.28 if r == 0 else 0.86)
                    base = sea_rgb[y, x].astype(float)
                    a[y, x, :3] = np.clip(base + (hi - base) * min(amt, 0.95), 0, 255).astype('uint8'); a[y, x, 3] = 255
        frames.append(a)
    return frames


def reflet_frames_zpr(dashes, xc, sea_vis, tvals=None):
    """Reflet de l'astre : chaque trait oscille de A sin(phi), phi = 2 pi (passes s / 12 - 7 u), u = profondeur ; s'éteint un instant
    quand sin(2 phi + phase propre) < -0,85. Boucle fermée."""
    frames = []
    for s in (range(SWELL_STEPS) if tvals is None else tvals):
        a = np.zeros((H, W, 4), 'uint8')
        for d in dashes:
            u = min(max((d['y'] - YH) / (Y_SHORE - YH), 0), 1)
            ph = 2 * math.pi * (HOULE_PASSES * s / SWELL_STEPS - HOULE_K * u)      # phase liée à la crête : 1 passage par cycle de 12 crans
            if math.sin(2 * ph + d['ph']) < -0.85:
                continue
            sp = d['spr']; h_, w_ = sp.shape[:2]; amp = 1 + (d['y'] - YH) / 45
            x0 = int(round(xc + d['dx'] + amp * math.sin(ph) - w_ / 2))
            ys, xs = np.nonzero(sp[..., 3] == 255); ty, tx = ys + d['y'], xs + x0
            ok = (ty >= YH) & (ty < H) & (tx >= 0) & (tx < W)
            a[ty[ok], tx[ok]] = sp[ys[ok], xs[ok]]
        a[~sea_vis] = 0
        frames.append(a)
    return frames


def caustiques(sea_rgb, sea_vis, dist_sand, amb, n=12, tvals=None):
    """Lumière qui danse sur le fond du lagon : réseau de points clairs (produit de deux ondes), 12 crans en boucle exacte."""
    zone = sea_vis & (dist_sand < 72) & (dist_sand > 3) & (np.arange(H)[:, None] > YH + 110); yy, xx = np.mgrid[:H, :W]
    g = {'jour': 0.40, 'aube': 0.32, 'crepuscule': 0.30, 'nuit': 0.26}[amb]; hi = np.array(LUMIERE[amb], float); frames = []
    for t in (range(n) if tvals is None else tvals):
        p1 = 2 * math.pi * t / n; p2 = 2 * p1
        v = np.sin(0.165 * xx + 0.105 * yy + p1) * np.sin(0.131 * xx - 0.173 * yy + p2) + 0.25 * np.sin(0.41 * xx + 0.07 * yy - p1)
        on = zone & (v > 0.80) & (((xx * 3 + yy * 5) % 4) != 0)
        a = np.zeros((H, W, 4), 'uint8'); base = sea_rgb[on].astype(float)
        a[on, :3] = np.clip(base + (hi - base) * g, 0, 255).astype('uint8'); a[on, 3] = 255
        frames.append(a)
    return frames


def ecume_recifs(masks, sea_vis, sea_rgb, amb, n=12, tvals=None):
    """Écume qui bat contre chaque récif : anneau de 1 à 5 px dont la densité respire (phase propre à chaque récif)."""
    d_all = np.full((H, W), 99.0); own = np.zeros((H, W), int)
    for i, m in enumerate(masks):
        d = nd.distance_transform_edt(~m)
        better = d < d_all; d_all[better] = d[better]; own[better] = i
    yy, xx = np.mgrid[:H, :W]; hv = (((xx * 1103515245 + yy * 12345 + 99991) >> 7) % 997) / 997.0
    hi = np.array(LUMIERE[amb], float); white = np.array([255, 255, 255], float) * 0.55 + hi * 0.45 if amb != 'jour' else np.array([252, 254, 255], float)
    ph = np.array([(hsh(i, 5) % 100) / 100 for i in range(len(masks))]); frames = []
    zone = sea_vis & (d_all >= 1) & (d_all <= 5.5)
    for t in (range(n) if tvals is None else tvals):
        thr = 0.98 - 0.17 * d_all + 0.28 * np.sin(2 * math.pi * (t / n + ph[own]))
        on = zone & (hv < thr)
        a = np.zeros((H, W, 4), 'uint8'); base = sea_rgb[on].astype(float)
        w = np.where(d_all[on] <= 2.2, 0.92 if amb == 'jour' else 0.62, 0.5 if amb == 'jour' else 0.32)[:, None] * GAIN_EAU[amb] ** 0.5
        a[on, :3] = np.clip(base + (white - base) * w, 0, 255).astype('uint8'); a[on, 3] = 255
        frames.append(a)
    return frames


def maree(cls, sea_vis, sand_rgb, sea_rgb, amb, n=18, A=7.0, tvals=None):
    """Marée sur la plage (bandes de la planche TD « Beach & Path » : ligne d'écume mouchetée, sable mouillé, eau claire) : le front
    avance de 0 à A px sur le sable puis recule, 18 crans en boucle exacte ; la phase varie un peu le long du rivage."""
    dsea = nd.distance_transform_edt(~sea_vis)
    sand = (cls == CL['SABLE']) & (dsea <= A + 8)
    yy, xx = np.mgrid[:H, :W]; hv = (((xx * 2654435761 + yy * 40503 + 7) >> 9) % 1013) / 1013.0
    shallow = fill_nearest(sea_rgb, sea_vis).astype(float); hi = np.array(LUMIERE[amb], float)
    foam = np.array([255, 255, 255], float) if amb == 'jour' else np.array([255, 255, 255], float) * 0.5 + hi * 0.5
    wet_k = {'jour': (0.84, (176, 120, 44)), 'aube': (0.80, (120, 90, 120)), 'crepuscule': (0.78, (150, 70, 70)), 'nuit': (0.72, (30, 50, 90))}[amb]
    adv = lambda t: A * (0.5 - 0.5 * np.cos(2 * math.pi * t / n + 0.011 * xx))
    frames = []
    for t in (range(n) if tvals is None else tvals):
        a_t = adv(t); prev = np.maximum.reduce([adv((t - j) % n) for j in range(0, 5)])
        a = np.zeros((H, W, 4), 'uint8')
        under = sand & (dsea <= a_t)
        wetm = sand & (dsea > a_t + 1.5) & (dsea <= prev + 3.0)
        fm = sand & (dsea > a_t) & (dsea <= a_t + 1.5) & (hv < 0.78)
        base = sand_rgb.astype(float)
        a[wetm, :3] = np.clip(base[wetm] * wet_k[0] + np.array(wet_k[1], float) * (1 - wet_k[0]), 0, 255).astype('uint8'); a[wetm, 3] = 255
        a[under, :3] = np.clip(shallow[under] * 0.82 + base[under] * 0.18 + (hi - shallow[under]) * 0.10 * GAIN_EAU[amb], 0, 255).astype('uint8'); a[under, 3] = 255
        a[fm, :3] = np.clip(base[fm] * 0.25 + foam * 0.75 * (0.7 + 0.3 * GAIN_EAU[amb]), 0, 255).astype('uint8'); a[fm, 3] = 255
        frames.append(a)
    return frames


# ---------------------------------------------------------------- végétation, mares, lueur
def sway(layer, comps_dil, amp, n, ph_fn, tvals=None):
    """Cisaillement horizontal d'un calque par composante : chaque rangée glisse de A sin(phi) (1 au sommet, 0 à la base) ; n phases."""
    base = layer[..., 3] == 255
    lab, nc = nd.label(nd.binary_dilation(base, iterations=comps_dil) if comps_dil else base, structure=np.ones((3, 3)))   # iterations=0 dilaterait sans fin
    al = layer[..., 3] == 255; boxes = nd.find_objects(lab); frames = []
    for t in (range(n) if tvals is None else tvals):
        a = np.zeros((H, W, 4), 'uint8')
        for i, sl in enumerate(boxes):
            y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop; mm = (lab[sl] == i + 1) & al[sl]
            ph = 2 * math.pi * (t / n + ph_fn(i, x0, y0))
            for y in range(y0, y1):
                w = 1 - (y - y0) / max(1, (y1 - 1 - y0))
                dx = int(round(amp * math.sin(ph) * w))
                row = np.nonzero(mm[y - y0])[0]
                if not len(row):
                    continue
                dx = max(dx, -int(row.min() + x0)); dx = min(dx, W - 1 - int(row.max() + x0))      # aucun pixel ne sort de l'image
                tx = row + x0 + dx; ok = (tx >= 0) & (tx < W)
                a[y, tx[ok]] = layer[y, row[ok] + x0]
        frames.append(a)
    return frames


def reflets_mares(mares_layer, amb, n=8):
    """Éclats d'eau dans les mares (8 phases x 10 ticks) ; la nuit elles reflètent les étoiles."""
    m = mares_layer[..., 3] == 255; ys, xs = np.nonzero(nd.binary_erosion(m, iterations=1))
    rng = np.random.default_rng(31); sel = rng.choice(len(ys), size=min(26, len(ys)), replace=False) if len(ys) else []
    col = {'jour': (255, 255, 255), 'aube': (255, 240, 235), 'crepuscule': (255, 214, 170), 'nuit': (214, 228, 255)}[amb]
    off = rng.integers(n, size=len(sel)); frames = []
    for t in range(n):
        a = np.zeros((H, W, 4), 'uint8')
        for j, k in enumerate(sel):
            if (t + off[j]) % n in (0, 1, 2):
                a[ys[k], xs[k], :3] = col; a[ys[k], xs[k], 3] = 255
        frames.append(a)
    return frames


def lueur_nuit(coral_masks, coral_rgb, sea_vis, dist_land, n=12, tvals=None):
    """Nuit : les coraux luisent (anneaux de 1 à 3 px, densité qui respire) et le plancton scintille dans le lagon (3 crans sur 12)."""
    frames = []; yy, xx = np.mgrid[:H, :W]; hv = (((xx * 1103515245 + yy * 12345 + 4242) >> 7) % 991) / 991.0
    rings = []
    for i, m in enumerate(coral_masks):
        if not m.any():
            continue
        d = nd.distance_transform_edt(~m); ring = (d >= 1) & (d <= 3.4) & sea_vis
        c = coral_rgb[m][:, :3].astype(float); c = c[np.argmax(c.max(1) - c.min(1))]
        c = np.clip(c * 0.55 + 255 * 0.45 * (c / max(1.0, c.max())), 0, 255)       # couleur du corail, éclaircie, jamais blanche
        rings.append((ring, d, c, (hsh(i, 9) % 100) / 100))
    rng = np.random.default_rng(9); zone = np.argwhere(sea_vis & (dist_land > 4) & (dist_land < 80) & (np.arange(H)[:, None] > YH + 90))
    pl = zone[rng.choice(len(zone), size=min(70, len(zone)), replace=False)]; off = rng.integers(n, size=len(pl))
    for t in (range(n) if tvals is None else tvals):
        a = np.zeros((H, W, 4), 'uint8')
        for ring, d, c, ph in rings:
            p = (0.60 - 0.17 * d) * (0.62 + 0.38 * math.sin(2 * math.pi * (t / n + ph)))
            on = ring & (hv < p); a[on, :3] = c.astype('uint8'); a[on, 3] = 255
        for j, (y, x) in enumerate(pl):
            if (t + off[j]) % n in (0, 1, 2):
                a[y, x, :3] = (150, 255, 235); a[y, x, 3] = 255
        frames.append(a)
    return frames


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


# ---------------------------------------------------------------- assemblage des 26 calques de chaque ambiance
ORDER = ['ciel', 'voie_lactee', 'etoiles_fixes', 'etoiles', 'etoile_filante', 'astre', 'nuages', 'mer', 'recifs_coraux',
         'lagon_reflets', 'houle', 'scintillement', 'reflet', 'lueur', 'recifs', 'recifs_ecume', 'sable', 'ecume_rivage',
         'mares', 'mares_reflets', 'rochers', 'coquillages', 'bois_flotte', 'troncs', 'palmes', 'herbes']
TICKS = {'etoiles': STAR_TICKS, 'etoile_filante': STAR_TICKS, 'nuages': CLOUD_TICKS, 'lagon_reflets': SWELL_TICKS, 'houle': SWELL_TICKS,
         'scintillement': GLINT_TICKS, 'reflet': SWELL_TICKS, 'lueur': SWELL_TICKS, 'recifs_ecume': SWELL_TICKS, 'ecume_rivage': 8,
         'mares_reflets': SWELL_TICKS, 'palmes': SWELL_TICKS, 'herbes': 12}


class LazySeq:
    """Suite d'images calculées à la demande (les 384 images des nuages ne tiennent pas toutes en mémoire)."""
    def __init__(self, n, fn):
        self.n, self.fn = n, fn

    def __len__(self):
        return self.n

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[j] for j in range(*i.indices(self.n))]
        return self.fn(i % self.n)

    def __iter__(self):
        for i in range(self.n):
            yield self.fn(i)


def cloud_frame(strip, t, hidden):
    h = strip.shape[0] - CLOUD_SINK; a = np.zeros((H, W, 4), 'uint8')
    a[YH - h:YH] = np.tile(np.roll(strip, t * CLOUD_PAS, axis=1)[:h], (1, W // CLOUD_PERIOD, 1)); a[hidden] = 0
    return a


def make_shared(ctx):
    """Données communes aux quatre ambiances (distances, géométrie de la baie, planches réutilisées, bande de nuages du jour)."""
    global NUAGES_H
    land_mask = ctx['land'][..., 3] == 255; sea_vis = ctx['sea_vis']
    strip, cpal, cinfo = cloud_strip({k: rgb(BRUTS / k) for k, _, _ in CLOUD_BANKS})
    NUAGES_H = strip.shape[0] - CLOUD_SINK
    cinfo.update({'periode_px': CLOUD_PERIOD, 'pas_px': CLOUD_PAS, 'phases': CLOUD_PHASES, 'frame_length_ticks': CLOUD_TICKS,
                  'hauteur_px': NUAGES_H, 'rangees_cachees_sous_horizon': CLOUD_SINK})
    return {'dist_land': nd.distance_transform_edt(~land_mask), 'dist_sand': nd.distance_transform_edt(ctx['cls'] != CL['SABLE']),
            'ys': sea_geometry(sea_vis), 'astres': rgb(BRUTS / 'astres.png'), 'refl_sheet': rgb(BRUTS / 'reflets_astres.png'),
            'strip': strip, 'info_nuages': cinfo}


def make_all(ctx, only=None, shared=None):
    """Calques (nom -> (images, ticks)) d'une ambiance (only) ou des quatre ; retourne aussi les mesures."""
    land, cls, RA = ctx['land'], ctx['cls'], ctx['RA']
    land_mask = land[..., 3] == 255; sea_vis = ctx['sea_vis']
    sh = shared or make_shared(ctx)
    dist_land, dist_sand, ys, astres, refl_sheet, strip = (sh[k] for k in ('dist_land', 'dist_sand', 'ys', 'astres', 'refl_sheet', 'strip'))
    out, info = {}, {'nuages': sh['info_nuages'], 'horizon_y': YH}
    for amb in ([only] if only else AMBS):
        S = static_layers(amb, ctx); L = {}; inf = {}
        ciel = S['ciel']; sky = ciel[..., :3].astype(int)
        sea_full = S['mer'][..., :3].astype(int)
        # scintillement de l'horizon : paillettes retirées de la plaque, rendues par le calque animé
        gl = glints(sea_full, sea_vis); glmask = np.zeros((H, W), bool)
        for px, _ in gl:
            for y, x in px:
                glmask[y, x] = True
        mer = S['mer'].copy()
        if glmask.any():
            plate_pal = np.unique(sea_full[sea_vis & ~glmask], axis=0)
            med = np.stack([nd.median_filter(sea_full[..., c], 7) for c in range(3)], -1)
            mer[glmask, :3] = nearest(med[glmask], plate_pal)
        mer_rgb = mer[..., :3].astype(int)
        inf['paillettes'] = {'groupes': len(gl), 'pixels': int(glmask.sum())}
        L['ciel'] = ([ciel], 60); L['mer'] = ([mer], 60)
        al = astre_layer(amb, astres, sky); L['astre'] = ([al], 60); amask = al[..., 3] > 0
        fixes, twink = star_field(amb, sky, land_mask, amask)
        if fixes[..., 3].any():
            L['etoiles_fixes'] = ([fixes], 60)
        L['etoiles'] = (star_frames(twink), STAR_TICKS)
        inf['etoiles'] = {'fixes': int((fixes[..., 3] > 0).sum()), 'scintillantes': len(twink)}
        vl = voie_lactee(amb, sky, land_mask, amask)
        if vl[..., 3].any():
            L['voie_lactee'] = ([vl], 60)
        fl = etoile_filante(amb, land_mask)
        if fl is not None:
            L['etoile_filante'] = (fl, STAR_TICKS)
        strip_a = cloud_ramp(strip, amb, sky)
        L['nuages'] = (LazySeq(CLOUD_PHASES, lambda t, sa=strip_a: cloud_frame(sa, t, land_mask)), CLOUD_TICKS)
        L['recifs_coraux'] = ([S['recifs_coraux']], 60)
        L['lagon_reflets'] = (caustiques(mer_rgb, sea_vis, dist_sand, amb), SWELL_TICKS)
        L['houle'] = (houle_frames(mer_rgb, sea_vis, dist_land, ys, amb), SWELL_TICKS)
        gwhite = sea_full[glmask][np.argmax(lum(sea_full[glmask]))] if glmask.any() else np.array([255, 255, 255])
        L['scintillement'] = (glint_frames(gl, sea_full, gwhite), GLINT_TICKS)
        if amb != 'jour':
            dashes, rinfo = reflet_dashes(refl_sheet, REFLET_COL[amb]); inf['reflet'] = {'x': ASTRE[amb]['c'][0], **rinfo}
            L['reflet'] = (reflet_frames_zpr(dashes, ASTRE[amb]['c'][0], sea_vis), SWELL_TICKS)
        if amb == 'nuit':
            L['lueur'] = (lueur_nuit(RA['coral_masks'], RA['coral'], sea_vis, dist_land), SWELL_TICKS)
        L['recifs'] = ([S['recifs']], 60)
        L['recifs_ecume'] = (ecume_recifs(RA['rock_masks'], sea_vis, mer_rgb, amb), SWELL_TICKS)
        L['sable'] = ([S['sable']], 60)
        L['ecume_rivage'] = (maree(cls, sea_vis, S['sable'][..., :3], mer_rgb, amb), 8)
        L['mares'] = ([S['mares']], 60); L['mares_reflets'] = (reflets_mares(S['mares'], amb), SWELL_TICKS)
        for k in ('rochers', 'coquillages', 'bois_flotte', 'troncs'):
            L[k] = ([S[k]], 60)
        L['palmes'] = (sway(S['palmes'], 1, 2.0, 12, lambda i, x0, y0: (hsh(i, 3) % 100) / 100), SWELL_TICKS)
        L['herbes'] = (sway(S['herbes'], 0, 1.4, 8, lambda i, x0, y0: (hsh(i, 4) % 100) / 100), 12)
        out[amb] = {k: L[k] for k in ORDER if k in L}; info[amb] = inf
    if only:
        return out[only], info[only]
    return out, info


def scene(L, tick):
    im = Image.new('RGBA', (W, H))
    for nm in ORDER:
        if nm in L:
            fr, tk = L[nm]; im.alpha_composite(Image.fromarray(fr[(tick // tk) % len(fr)]))
    return im


# ---------------------------------------------------------------- export : ORA, projet Ground PMDO 0.8.12, masques, aperçus
NAMESPACE = 'zone_plage_recifs_etoiles_v1'
STAGE = ROOT / '.cache' / LOT / NAMESPACE
ASSET = {k: f'zpr1_plage_recifs_{k}' for k in AMBS}
MARQUEURS = {'plage': (376, 392), 'entrance': (376, 552)}          # (x, y) haut-gauche des repères de 16 x 16 : bord de l'eau, sortie sud
RANGEES = lambda: None


def loadmod(name, path):
    import importlib.util
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def write_ora(path, layers, title):
    import io, zipfile
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


def cases(frames):
    """Accès rapide aux cases de 8 x 8 de toutes les phases d'un calque : retourne (get(x, y) -> liste d'images 8 x 8 ou None)."""
    if isinstance(frames, LazySeq):                                   # nuages : on ne garde que la bande utile (rangées multiples de 8)
        y0 = (YH - NUAGES_H) // 8 * 8; y1 = (YH + 7) // 8 * 8
        st = np.stack([f[y0:y1] for f in frames])
        act = (st[..., 3] > 0).any(0)

        def get(x, y):
            if not (y0 <= y * 8 < y1):
                return None
            sl = (slice(y * 8 - y0, y * 8 - y0 + 8), slice(x * 8, x * 8 + 8))
            if not act[sl].any():
                return None
            return [st[(slice(None),) + sl][t] for t in range(len(st))]
        return get
    act = np.zeros((H, W), bool)
    for a in frames:
        act |= a[..., 3] > 0
    cell_act = act.reshape(H // 8, 8, W // 8, 8).any((1, 3))

    def get(x, y):
        if not cell_act[y, x]:
            return None
        return [a[y * 8:y * 8 + 8, x * 8:x * 8 + 8] for a in frames]
    return get


def ground(amb, stack, blocked, markers, gfx, tpl):
    tpl = json.loads(json.dumps(tpl)); o = tpl['Object']; gw, gh = W // 8, H // 8; layers, banks = [], []
    for idx, title, frames, ticks in stack:
        bank = gfx.TileBank(f'{PFX}{AMBS[amb]}_{idx:02d}_{title.split()[0].upper()}')
        bank.ids[bytes(256)] = (0, 0); bank.data[(0, 0)] = bytes(256)
        get = cases(frames)

        def cell(x, y, get=get, bank=bank):
            arrs = get(x, y)
            if arrs is None:
                return []
            fs = []
            for a in arrs:
                f = bank.add(Image.fromarray(np.ascontiguousarray(a)), x, y)
                fs.append(f if f else {'Sheet': bank.name, 'TexLoc': {'X': 0, 'Y': 0}})
            if all(f['TexLoc'] == {'X': 0, 'Y': 0} for f in fs):
                return []
            return [fs[0]] if all(f == fs[0] for f in fs) else fs
        layers.append(gfx.layer(f'{idx:02d} {title}', gw, gh, cell, ticks)); banks.append(bank)
    layers.append(gfx.layer(f'{len(ORDER):02d} Vos elements avant-plan (Top)', gw, gh, draw=4))
    for bank in banks:
        bank.write(STAGE / f'Content/Tile/{bank.name}.tile')
    o.update(Name={'DefaultText': f'Plage aux recifs etoiles ZPR1 ({amb})', 'LocalTexts': {}},
             AssetName=ASSET[amb], Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None,
             ViewOffset={'X': 0, 'Y': 0}, ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment=f'PMDO 0.8.12. Plage aux recifs etoiles ZPR1 ({amb}). Baie fermee par deux promontoires rouges, recifs et coraux, lagon, '
                     'plage ; ciel etoile du jour a la nuit sur des calques separes (ciel, Voie lactee, etoiles, etoile filante, astre, nuages). '
                     'Rendu genere reference. Houle 12 x 10 ticks, scintillement 16 x 4, etoiles 24 x 5, nuages 384 x 16, maree 18 x 8. '
                     'Collisions par cellule de 8 px. Aucun warp.')
    o['obstacles'] = [[{'Bounds': {'X': x * 8, 'Y': y * 8, 'Width': 8, 'Height': 8}, 'Tags': int(blocked[y, x])}
                       for y in range(gh)] for x in range(gw)]
    mk = lambda n, p: {'EntName': n, 'Direction': 4, 'EntEnabled': True, 'triggerType': 0,
                       'Collider': {'X': p[0], 'Y': p[1], 'Width': 16, 'Height': 16}}
    o['Entities'] = [{'Name': 'Entrees et vos acteurs', 'Visible': True, 'MapChars': [], 'GroundObjects': [], 'Spawners': [],
                      'Markers': [mk(n, p) for n, p in markers.items()]}]
    o['Decorations'] = [{'Name': 'Vos decorations', 'Layer': 2, 'Visible': True, 'Anims': []}]
    tpl['Version'] = '0.8.12.0'
    gfx.save(STAGE / f'Data/Ground/{ASSET[amb]}.rsground', json.dumps(tpl, ensure_ascii=False, separators=(',', ':')).encode())
    gfx.save(STAGE / f'Data/Script/{NAMESPACE}/ground/{ASSET[amb]}/init.lua',
             f'-- {ASSET[amb]} : plage aux recifs etoiles ZPR1 ({amb}), base d edition, aucun warp.\n'
             f'-- Marqueurs : plage (bord de l eau), entrance (sortie sud).\n'
             f'local {ASSET[amb]} = {{}}\nreturn {ASSET[amb]}\n'.encode())
    return {b.name: len(b.data) for b in banks}


def finish_stage(tools):
    import shutil, uuid
    nodes = {}
    for p in sorted((STAGE / 'Content/Tile').glob('*.tile')):
        with p.open('rb') as f:
            nodes[p.stem] = tools.read_node(f)
    (STAGE / 'Content/Tile/index.idx').write_bytes(tools.encode_index(nodes))
    ident = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/meromoonmeri/guilde-treehouse-pmd/' + NAMESPACE)
    (STAGE / 'Mod.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Plage aux recifs etoiles ZPR1 (jour, aube, crepuscule, nuit) - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : une baie turquoise fermee par deux promontoires de roches rouges, barriere de recifs et coraux, lagon, plage de sable avec palmiers, mares et coquillages. Ciel etoile du jour a la nuit (Voie lactee, etoiles qui scintillent, etoile filante, lune, soleil, nuages), houle, reflets, maree. Quatre cartes Ground (une par ambiance), 26 calques animes chacune. Rendu genere, non teste dans PMDO.</Description>
  <Namespace>{NAMESPACE}</Namespace>
  <UUID>{ident}</UUID>
  <Version>1.0.0.0</Version>
  <GameVersion>0.8.12.0</GameVersion>
  <ModType>Quest</ModType>
  <Relationships />
</Header>
''')
    script = (ROOT / 'source/pmdo_cote/INSTALLER.py').read_text()
    needle = '            relative = src.relative_to(source)\n'
    assert needle in script
    script = script.replace(needle, needle + "            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n")
    (STAGE / 'INSTALLER.py').write_text(script)
    shutil.copyfile(HERE / 'README_PACK.md', STAGE / 'README.md')


def collisions(land, cls):
    """Cellules de 8 px bloquées : mer et ciel, roches, troncs de palmiers, bois flotté (plus d'un quart de la cellule)."""
    block = (land[..., 3] != 255) | np.isin(cls, [CL['ROCHE'], CL['TRONC'], CL['BOIS']])
    return block.reshape(H // 8, 8, W // 8, 8).mean((1, 3)) > 0.25, block


NUAGES_H = 76 - CLOUD_SINK                                          # hauteur visible de la bande de nuages (rangées sous le sommet)


def make_amb(ctx, amb, shared):
    """Les calques d'UNE ambiance (nom -> (images, ticks)) ; voir make_all."""
    return make_all(ctx, only=amb, shared=shared)


def export(ctx, only=None):
    import io, shutil
    from PIL import ImageDraw
    gfx = loadmod('pmdo_codec', ROOT / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools', ROOT / 'source/pmdo_cote/INSTALLER.py')
    esn1 = loadmod('esn1', ROOT / 'source/entree_sud_nord_generee_v1/build.py')
    for d in ['calques', 'animation', 'masques', 'review']:
        shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['masques', 'review']:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    if STAGE.exists():
        shutil.rmtree(STAGE)
    land, cls = ctx['land'], ctx['cls']
    blocked, block = collisions(land, cls)
    entry, plage = MARQUEURS['entrance'], MARQUEURS['plage']
    reach, explored = esn1.reachable(blocked, (entry[1] // 8, entry[0] // 8), (plage[1] // 8, plage[0] // 8))
    assert reach, 'aucun chemin entre la sortie sud et la plage'
    sea_vis = ctx['sea_vis']; RA = ctx['RA']
    for nm, m in (('mer', sea_vis), ('terre', land[..., 3] == 255), ('praticable', ~block), ('recifs', RA['rock_mask'] | RA['coral_mask'])):
        Image.fromarray((m * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_{nm}.png')
    debug_classes(cls, OUT / 'masques' / f'{PFX}_classes_terre.png')
    tpl_zip = zipfile.ZipFile(ROOT / 'mod_metano_expeditions_pmdo_0812.zip')
    tpl = json.loads(tpl_zip.read('metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground'))
    shared = make_shared(ctx)
    report, counts, info, scenes0 = {}, {}, {'nuages': shared['info_nuages'], 'horizon_y': YH}, {}
    for amb in AMBS:
        L, inf = make_all(ctx, only=amb, shared=shared); info[amb] = inf
        layer_list, stack = [], []
        for i, nm in enumerate(ORDER):
            if nm not in L:
                continue
            frames, ticks = L[nm]
            if len(frames) > 1:
                d = OUT / 'animation' / amb / nm; d.mkdir(parents=True, exist_ok=True)
                for t, fr in enumerate(frames):
                    save_png(fr, d / f'{PFX}{AMBS[amb]}_{i:02d}_{nm}_f{t:03d}.png')
                layer_list.append({'index': i, 'nom': nm, 'file': f'animation/{amb}/{nm}/{PFX}{AMBS[amb]}_{i:02d}_{nm}_fNNN.png',
                                   'phases': len(frames), 'ticks': ticks})
            else:
                d = OUT / 'calques' / amb; d.mkdir(parents=True, exist_ok=True)
                save_png(frames[0], d / f'{PFX}{AMBS[amb]}_{i:02d}_{nm}.png')
                layer_list.append({'index': i, 'nom': nm, 'file': f'calques/{amb}/{PFX}{AMBS[amb]}_{i:02d}_{nm}.png', 'phases': 1, 'ticks': 60})
            stack.append((i, nm.replace('_', ' ') + (f' {len(frames)} phases' if len(frames) > 1 else ''), frames, ticks))
        step = 8
        sc = [scene(L, tk) for tk in range(0, 480, step)]
        sc[0].save(OUT / 'review' / f'{PFX}_{amb}_scene_t000.png'); scenes0[amb] = sc[0].copy()
        sc[0].save(OUT / 'review' / f'{PFX}_{amb}_scene_animee.webp', save_all=True, append_images=sc[1:],
                   duration=round(step * 1000 / 60), loop=0, quality=84, method=4)
        if amb == 'jour':
            col = sc[0].copy(); ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
            for y, x in zip(*np.nonzero(blocked)):
                dr.rectangle([x * 8, y * 8, x * 8 + 7, y * 8 + 7], fill=(220, 40, 40, 90))
            for (qx, qy), c in ((entry, (255, 230, 40, 255)), (plage, (60, 220, 255, 255))):
                dr.rectangle([qx, qy, qx + 15, qy + 15], outline=c, width=2)
            col.alpha_composite(ov); col.save(OUT / 'review' / f'{PFX}_collisions_marqueurs.png')
        write_ora(OUT / f'{PFX}_plage_recifs_{amb}_calques.ora',
                  {f'{i:02d}_{nm}' + ('_f000' if len(L[nm][0]) > 1 else ''): L[nm][0][0] for i, nm in enumerate(ORDER) if nm in L},
                  f'Plage aux recifs etoiles ZPR1 ({amb})')
        counts.update(ground(amb, stack, blocked, MARQUEURS, gfx, tpl))
        report[amb] = {'layers': layer_list}
        del L, stack, sc
    quatre = Image.new('RGB', (W * 2, H * 2))
    for k, a in enumerate(AMBS):
        quatre.paste(scenes0[a].convert('RGB'), ((k % 2) * W, (k // 2) * H))
    quatre.save(OUT / 'review' / f'{PFX}_quatre_ambiances_t000.png')
    finish_stage(tools)
    return report, counts, info, blocked, reach, explored


def main(apercu=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    ctx = contexte()
    if apercu:
        debug_classes(ctx['cls'], CACHE / 'classes.png')
        sh = make_shared(ctx); d = CACHE / 'apercu'; d.mkdir(exist_ok=True)
        for amb in AMBS:
            L, inf = make_all(ctx, only=amb, shared=sh)
            for tk in (0, 60):
                scene(L, tk).save(d / f'{amb}_t{tk:03d}.png')
        return
    report, counts, info, blocked, reach, explored = export(ctx)
    gen = json.loads((HERE / 'generation.json').read_text(encoding='utf-8'))
    raws = sorted(p for p in BRUTS.glob('*.png') if p.name != 'terre_jour_baie_etroite.png')
    refs = sorted((HERE / 'references').glob('*.png'))
    manifest = {
        'lot': LOT, 'prefix': PFX, 'prefixes_banques': {k: PFX + v for k, v in AMBS.items()},
        'format': '4:3 vaste', 'size_px': [W, H], 'grid_8px': [W // 8, H // 8], 'horizon_y': YH,
        'demande': "j'aimerais une zone magnifique en bord de plage avec ciel étoilée dans les différent temps avec des recif etc multicalque",
        'interpretation_a_confirmer': {
            'zone': 'une baie de plage fermée par deux promontoires de roches rouges, sable, palmiers, mares, coquillages (choix de l agent)',
            'recifs': 'sept récifs rocheux émergés (barrière et récifs isolés) et treize patates de corail vues à travers l eau',
            'temps': 'quatre ambiances : jour, aube, crépuscule, nuit',
            'ciel_etoile': "étoiles à tous les temps, lecture littérale de « ciel étoilé dans les différents temps » : jour environ 14 très pâles, "
                           'aube 62, crépuscule 144, nuit 536 (440 fixes + 96 scintillantes) avec Voie lactée et étoile filante ; effectifs = constantes ETOILES',
            'multicalque': '26 calques par ambiance (24 le jour), chaque élément sur son propre calque, plus un calque Top vide'},
        'method': 'rendu généré (terre, ciel et mer, planches de récifs, ambiances) + calculs ; aucun pixel natif ; texture canonique = rendu généré référence',
        'generation': gen,
        'raw_inputs': [{'file': f'source/{LOT}/bruts/{p.name}', 'sha256': sha(p), 'size': list(Image.open(p).size)} for p in raws],
        'references': {p.name: {'file': f'source/{LOT}/references/{p.name}', 'sha256': sha(p)} for p in refs},
        'reutilise_de_zrv2': {k: sha(BRUTS / k) for k in ('astres.png', 'reflets_astres.png', 'banc_nuages_jour.png', 'banc_nuages_jour_b.png', 'banc_nuages_jour_c.png')},
        'mesures': info,
        'recifs': {'roches': [{'sprite': n, 'x': x, 'pied_y': y, 'largeur_px': w} for n, x, y, w in RECIFS],
                   'coraux': [{'sprite': n, 'x': x, 'pied_y': y, 'largeur_px': w} for n, x, y, w in CORAUX_POS],
                   'teinte_et_luminosite_par_ambiance': CORAIL_AMB},
        'etoiles': {'phases': STAR_PHASES, 'frame_length_ticks': STAR_TICKS, 'effectifs_fixes_scintillantes': ETOILES, 'contraste': ETOILE_K,
                    'voie_lactee_densite': VOIE_DENSITE, 'filante': {'phases': FILANTE_PHASES, 'ticks': STAR_TICKS, 'ambiances': sorted(FILANTE)}},
        'astres': ASTRE,
        'houle': {'crans': SWELL_STEPS, 'frame_length_ticks': SWELL_TICKS, 'crêtes': HOULE_K, 'loi': 'la crête de profondeur u est à y = YH + (ys(x) - YH) u^1,7 ; u = (k + s / 12) / 7 ; '
                  'elle épouse la baie ; dessin fonction de (x, u) seulement : boucle exacte'},
        'scintillement': {'crans': GLINT_STEPS, 'frame_length_ticks': GLINT_TICKS, 'niveaux': GLINT_LEVELS},
        'reflet': {'crans': SWELL_STEPS, 'frame_length_ticks': SWELL_TICKS, 'portee_px': REFLET_SPAN},
        'maree': {'phases': 18, 'frame_length_ticks': 8, 'avance_max_px': 7.0, 'source': 'bandes de references/plage_td_marees.png : ligne d écume mouchetée, sable mouillé, eau claire'},
        'vegetation': {'palmes': {'phases': 12, 'ticks': SWELL_TICKS, 'amplitude_px': 2.0}, 'herbes': {'phases': 8, 'ticks': 12, 'amplitude_px': 1.4}},
        'ambiances': report,
        'access': {'markers_px': MARQUEURS, 'path_found_16x16': reach, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'walkable_cells': int((~blocked).sum())},
        'pmdo': {'target': '0.8.12', 'namespace': NAMESPACE, 'assets': ASSET, 'tiles_per_bank': counts, 'markers': MARQUEURS, 'warps': 'aucun'},
        'art_approved': False, 'runtime_tested': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print('manifest ok;', {k: len(v['layers']) for k, v in report.items()}, 'cellules bloquées', int(blocked.sum()))


if __name__ == '__main__':
    main(apercu='--apercu' in sys.argv)
