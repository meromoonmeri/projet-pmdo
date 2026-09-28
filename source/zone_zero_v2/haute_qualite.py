"""Passe « haute qualité » des routes Zone Zéro fleuries (RAF1, RAF2, RAF3).

Demande : « faut que les zone route area zero soit magnifique avec la verdure sky peak hight qualité less fleur avec plein de
couleur des cascade de la brume etc ».

Constat (GIF Sky Peak 2cwdrrs469f61.gif, 4 images de 200 ms, A B A C) : l'herbe de Sky Peak est un aplat franc (135,247,119)
semé de touffes en étoile et de fleurs rondes nettes de 7 px ; toute la prairie se balance (touffes ET fleurs) en A B A C.
Nos routes réduites x0,64 avaient une herbe floue en dégradé et des fleurs baveuses.

Ce module (appelé par build.py juste après make_all) :
- aplatit l'herbe claire du sol et du sol complet au ton Sky Peak (seulement les pixels à moins de 40 du ton dominant du lot :
  le chemin d'herbe rase reste) ; efface les restes flous (petites taches entourées d'herbe) ;
- reprend les massifs flous restés dans le sol ou classés falaises (boîtes CFG ``massifs_falaise``) ;
- redessine TOUTES les fleurs en sprites nets (8 palettes), massifs d'origine gardés dans leur couleur + massifs en plus ;
- sème des touffes en étoile (calque herbes, A B A C) ;
- ajoute des embruns au pied des cascades (24 phases) et des papillons sur des boucles fermées (48 phases).

Tout est CALCULÉ (pas de tuile native) ; seuls les tons de l'herbe, des touffes et des fleurs corail sont relevés sur le GIF.
"""
import numpy as np
from scipy import ndimage as nd

H, W = 576, 768
SKY_GRASS = (135, 247, 119)
TUFT_TONES = [(95, 183, 87), (103, 207, 95), (119, 215, 103)]       # relevés sur le GIF Sky Peak
SHADOW = (103, 207, 95)
HERBES_PHASES, HERBES_TICKS = 4, 12
EMBRUNS_PHASES, EMBRUNS_TICKS = 24, 10
PAPILLONS_PHASES, PAPILLONS_TICKS = 48, 10
BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
# palette : pétale, reflet, bord sombre, coeur (corail = tons relevés sur Sky Peak)
PALETTES = {
    'corail': ((239, 135, 119), (255, 223, 215), (191, 87, 79), (247, 175, 143)),
    'rouge': ((232, 56, 64), (255, 190, 190), (160, 24, 40), (255, 210, 90)),
    'rose': ((240, 120, 190), (255, 215, 240), (176, 64, 136), (255, 230, 120)),
    'jaune': ((248, 216, 56), (255, 250, 200), (200, 150, 24), (232, 120, 40)),
    'orange': ((248, 152, 40), (255, 224, 160), (192, 96, 16), (255, 240, 150)),
    'blanc': ((240, 244, 240), (255, 255, 255), (176, 188, 200), (248, 200, 64)),
    'bleu': ((80, 144, 240), (200, 228, 255), (40, 80, 184), (255, 240, 150)),
    'violet': ((160, 96, 224), (228, 200, 255), (96, 48, 160), (255, 220, 110)),
}
PAL_NAMES = list(PALETTES)
EMBRUN_TONES = [(255, 255, 255), (226, 240, 250), (196, 220, 240)]
WINGS = [(255, 216, 64), (255, 255, 255), (240, 120, 190), (120, 170, 255), (248, 152, 40), (160, 96, 224),
         (232, 56, 64), (150, 236, 236)]
WING_NAMES = ['jaune', 'blanc', 'rose', 'bleu', 'orange', 'violet', 'rouge', 'turquoise']

FLOWER_ROWS = ['..PPP..', '.PPPPP.', 'PPPPPPP', 'PPPPPPP', 'PPPPPPP', '.PPPPP.', '..PPP..']


# ---------------------------------------------------------------- sprites
def flower_sprite(name):
    P, Lt, D, C = PALETTES[name]
    s = np.zeros((7, 7, 4), 'uint8')
    for y, row in enumerate(FLOWER_ROWS):
        for x, ch in enumerate(row):
            if ch == 'P':
                s[y, x, :3] = P; s[y, x, 3] = 255
    m = s[..., 3] == 255
    edge = m & ~nd.binary_erosion(m)
    for y in range(7):
        for x in range(7):
            if edge[y, x] and x + y >= 7:
                s[y, x, :3] = D                                                     # bord sombre en bas à droite
    for y, x in ((1, 2), (2, 1), (1, 4), (4, 1)):
        s[y, x, :3] = Lt                                                            # reflet en damier en haut à gauche
    for y, x in ((1, 3), (3, 1), (3, 5), (5, 3)):
        s[y, x, :3] = D                                                             # 4 pétales : encoches sombres
    s[3, 3, :3] = C; s[2, 3, :3] = C
    return s


def paste(dst, spr, y, x, only_empty=False):
    h, w = spr.shape[:2]
    y0, x0 = max(0, y), max(0, x); y1, x1 = min(H, y + h), min(W, x + w)
    if y1 <= y0 or x1 <= x0:
        return
    sub = spr[y0 - y:y1 - y, x0 - x:x1 - x]; m = sub[..., 3] > 0
    if only_empty:
        m &= dst[y0:y1, x0:x1, 3] == 0
    dst[y0:y1, x0:x1][m] = sub[m]


def butterfly_sprites(wing, dark):
    body = (70, 52, 44); light = tuple(min(255, v + 60) for v in wing)
    rows_o = ['DW.b.WD', 'WLWbWLW', 'WWWbWWW', '.DWbWD.', '.WD.DW.', '.D...D.']
    rows_c = ['..WbW..', '..LbL..', '..WbW..', '...b...', '.......', '.......']
    out = []
    for rows in (rows_o, rows_c):
        o = np.zeros((6, 7, 4), 'uint8')
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch != '.':
                    o[y, x, :3] = {'W': wing, 'D': dark, 'b': body, 'L': light}[ch]; o[y, x, 3] = 255
        out.append(o)
    return tuple(out)


def tuft_sprite(k):
    """Étoile de 6 brins (5 px de haut) ; k = -1, 0, +1 : les brins du haut penchent de k px (balancement)."""
    s = np.zeros((6, 7, 4), 'uint8')
    pts = {(3, 3): 0, (2, 3): 1, (1, 3): 2, (0, 3): 2,                             # brin central
           (2, 2): 1, (1, 1): 2, (2, 4): 1, (1, 5): 2,                              # brins obliques
           (3, 1): 1, (3, 5): 1, (4, 2): 0, (4, 4): 0}                              # brins bas
    for (y, x), t in pts.items():
        xx = x + (k if y <= 1 else 0)
        s[y + 1, xx, :3] = TUFT_TONES[t]; s[y + 1, xx, 3] = 255
    return s


# ---------------------------------------------------------------- herbe
def grass_mode(layer, grass_rule):
    rgb = layer[..., :3].astype(int); m = (layer[..., 3] == 255) & grass_rule(rgb)
    cols, cnt = np.unique(rgb[m], axis=0, return_counts=True)
    return cols[np.argmax(cnt)]


def flatten_grass(layer, grass_rule, mode):
    """Aplat Sky Peak : règle herbe ET à moins de 40 du ton dominant du lot (le chemin clair reste)."""
    rgb = layer[..., :3].astype(int)
    m = (layer[..., 3] == 255) & grass_rule(rgb) & (np.sqrt(((rgb - mode) ** 2).sum(2)) < 40)
    layer[m, :3] = SKY_GRASS
    return m


def small_components(mask, n_max, n_min=1):
    lab, n = nd.label(mask)
    out = []
    for i, sl in enumerate(nd.find_objects(lab)):
        if sl is None:
            continue
        y0, y1 = max(0, sl[0].start - 3), min(H, sl[0].stop + 3); x0, x1 = max(0, sl[1].start - 3), min(W, sl[1].stop + 3)
        comp = np.zeros((H, W), bool); comp[y0:y1, x0:x1] = lab[y0:y1, x0:x1] == i + 1
        c = int(comp.sum())
        if n_min <= c <= n_max:
            out.append(comp)
    return out


def ring(comp, it=2):
    return nd.binary_dilation(comp, iterations=it) & ~comp


# ---------------------------------------------------------------- fleurs
def family(pixels):
    """Palette la plus proche (vote des pixels de pétale)."""
    if len(pixels) == 0:
        return None
    P = np.array([PALETTES[k][0] for k in PAL_NAMES], float)
    d = ((pixels[:, None, :].astype(float) - P[None]) ** 2).sum(2)
    votes = np.bincount(d.argmin(1), minlength=len(PAL_NAMES))
    return PAL_NAMES[int(votes.argmax())]


def plan_flowers(old, free, extra_ok, rng):
    """Liste de fleurs (y, x, palette, sens). Massifs d'origine : grille 7 x 8 à jeu, 22 % de trous ; massifs en plus."""
    flowers = []
    a = old[..., :3].astype(int)
    green = (a[..., 1] > a[..., 0] + 12) & (a[..., 1] > a[..., 2] + 30)
    petal_px = (old[..., 3] == 255) & ~green
    lab, n = nd.label(nd.binary_dilation(old[..., 3] == 255, iterations=2))
    fams = []
    for i, sl in enumerate(nd.find_objects(lab)):
        comp = lab[sl] == i + 1
        pal = family(a[sl][comp & petal_px[sl]])
        if pal is None:
            continue
        fams.append(pal)
        area = comp & free[sl]
        ys, xs = np.nonzero(area)
        if len(ys) < 12:
            continue
        oy, ox = sl[0].start, sl[1].start
        for y in range(ys.min(), ys.max() + 1, 7):
            for x in range(xs.min() + (4 if (y // 7) % 2 else 0), xs.max() + 1, 8):
                jy, jx = y + int(rng.integers(-1, 2)), x + int(rng.integers(-1, 2))
                if rng.random() < 0.22:
                    continue
                if 0 <= jy < area.shape[0] and 0 <= jx < area.shape[1] and area[jy, jx]:
                    flowers.append((oy + jy - 3, ox + jx - 3, pal, 1 if rng.random() < 0.5 else -1))
    # massifs en plus sur l'herbe franche : grille de 46 px, toutes les couleurs à tour de rôle
    occupied = np.zeros((H, W), bool)
    for (y, x, _, _) in flowers:
        occupied[max(0, y):y + 7, max(0, x):x + 7] = True
    near = nd.binary_dilation(occupied, iterations=14)
    k_pal = 0
    for gy in range(20, H - 20, 46):
        for gx in range(20 + (23 if (gy // 46) % 2 else 0), W - 20, 46):
            cy, cx = gy + int(rng.integers(-12, 13)), gx + int(rng.integers(-12, 13))
            if not (0 <= cy < H and 0 <= cx < W) or not extra_ok[cy, cx] or near[cy, cx] or rng.random() < 0.45:
                continue
            pal = PAL_NAMES[k_pal % len(PAL_NAMES)]; k_pal += 1
            k = int(rng.integers(3, 8))
            offs = [(0, 0), (-6, 4), (-6, -4), (1, 8), (1, -8), (7, 4), (7, -4), (-12, 0)][:k]
            for dy, dx in offs:
                y, x = cy + dy, cx + dx
                if 0 <= y < H and 0 <= x < W and extra_ok[y, x]:
                    flowers.append((y - 3, x - 3, pal, 1 if rng.random() < 0.5 else -1))
    return flowers, sorted(set(fams))


def flower_frames(flowers):
    """A B A C (loi du GIF Sky Peak) : en B et C chaque fleur descend de 1 px et penche de ±1 px (sens propre)."""
    spr = {k: flower_sprite(k) for k in PAL_NAMES}
    shadow = {}
    for k, s in spr.items():
        sh = np.zeros_like(s); sh[s[..., 3] > 0, :3] = SHADOW; sh[s[..., 3] > 0, 3] = 255; shadow[k] = sh
    order = sorted(flowers, key=lambda f: f[0])
    frames = []
    for ph, (dy, lean) in enumerate([(0, 0), (1, 1), (0, 0), (1, -1)]):
        e = np.zeros((H, W, 4), 'uint8')
        for (y, x, pal, sg) in order:
            paste(e, shadow[pal], y + 2 + dy, x + 1 + lean * sg, only_empty=True)
        for (y, x, pal, sg) in order:
            paste(e, spr[pal], y + dy, x + lean * sg)
        frames.append(e)
    return frames


# ---------------------------------------------------------------- touffes
def plan_tufts(ok, rng):
    pts = []
    for gy in range(8, H - 8, 26):
        for gx in range(8 + (13 if (gy // 26) % 2 else 0), W - 8, 26):
            y, x = gy + int(rng.integers(-5, 6)), gx + int(rng.integers(-5, 6))
            if 0 <= y < H and 0 <= x < W and ok[y, x]:
                pts.append((y, x, 1 if rng.random() < 0.5 else -1))
    return pts


def tuft_frames(pts):
    frames = []
    for k in (0, 1, 0, -1):                                                         # A B A C
        e = np.zeros((H, W, 4), 'uint8')
        for (y, x, sg) in pts:
            paste(e, tuft_sprite(k * sg), y - 3, x - 3)
        frames.append(e)
    return frames


# ---------------------------------------------------------------- embruns
RISE = 34


def foam_top(r, foam):
    """Bord haut de l'écume au pied de la chute (sinon le bas du rectangle)."""
    x0, x1 = max(0, r['x0'] - 20), min(W, r['x1'] + 20)
    ys = np.nonzero(foam[r['y0']:min(H, r['y1'] + 40), x0:x1].any(1))[0]
    return int(r['y0'] + ys.min()) if len(ys) else int(r['y1'])


def embruns_frames(rects, foam, allowed, rng):
    drops = []
    for r in rects:
        w = r['x1'] - r['x0']; n = max(28, w); top = foam_top(r, foam); r['embruns_y'] = top
        for i in range(n):
            drops.append(dict(x=float(rng.uniform(r['x0'] - 22, r['x1'] + 22)), y=float(top + rng.uniform(0, 8)),
                              off=int(rng.integers(0, EMBRUNS_PHASES)), amp=float(rng.uniform(1, 3)),
                              ph=float(rng.uniform(0, 2 * np.pi)), tone=int(rng.integers(0, 3))))
    frames = []
    for t in range(EMBRUNS_PHASES):
        e = np.zeros((H, W, 4), 'uint8')
        for d in drops:
            u = ((t + d['off']) % EMBRUNS_PHASES) / EMBRUNS_PHASES                   # 0 -> 1 sur la boucle
            y = int(round(d['y'] - RISE * u)); x = int(round(d['x'] + d['amp'] * np.sin(2 * np.pi * u + d['ph'])))
            size = 2 if u < 0.7 else 1
            for yy in range(y, y + size):
                for xx in range(x, x + size):
                    if 0 <= yy < H and 0 <= xx < W and allowed[yy, xx] and BAYER4[yy % 4, xx % 4] < 1.0 - u:
                        e[yy, xx, :3] = EMBRUN_TONES[d['tone'] if u < 0.6 else 2]; e[yy, xx, 3] = 255
        frames.append(e)
    return frames, len(drops)


# ---------------------------------------------------------------- papillons
def plan_butterflies(ok, rng, n=8):
    ys, xs = np.nonzero(ok)
    chosen = []
    if len(ys) == 0:
        return chosen
    for _ in range(4000):
        i = int(rng.integers(0, len(ys))); cy, cx = int(ys[i]), int(xs[i])
        if all((cy - c['cy']) ** 2 + (cx - c['cx']) ** 2 >= 90 ** 2 for c in chosen):
            k = len(chosen)
            chosen.append(dict(cx=cx, cy=cy, ax=int(rng.integers(14, 23)), ay=int(rng.integers(6, 11)),
                               phi=round(float(rng.uniform(0, 2 * np.pi)), 3), psi=round(float(rng.uniform(0, 2 * np.pi)), 3),
                               couleur=WING_NAMES[k % len(WINGS)]))
            if len(chosen) == n:
                break
    return chosen


def butterfly_path(f):
    out = []
    for t in range(PAPILLONS_PHASES):
        x = f['cx'] + f['ax'] * np.sin(2 * np.pi * t / PAPILLONS_PHASES + f['phi'])
        y = f['cy'] + f['ay'] * np.sin(4 * np.pi * t / PAPILLONS_PHASES + f['psi'])
        out.append([int(round(x)), int(round(y))])
    return out


def papillon_frames(bflies):
    spr = {WING_NAMES[i]: butterfly_sprites(WINGS[i], tuple(int(v * 0.6) for v in WINGS[i])) for i in range(len(WINGS))}
    paths = [butterfly_path(f) for f in bflies]
    frames = []
    for t in range(PAPILLONS_PHASES):
        e = np.zeros((H, W, 4), 'uint8')
        for f, p in zip(bflies, paths):
            x, y = p[t]
            paste(e, spr[f['couleur']][t % 2], y - 3, x - 3)
        frames.append(e)
    return frames, paths


# ---------------------------------------------------------------- passe complète
def apply(D, grass_rule, seed, boxes=()):
    rng = np.random.default_rng(seed)
    L, ex = D['layers'], D['ex']
    # 1. herbe : aplat Sky Peak (sol et sol complet)
    mode = grass_mode(L['sol'], grass_rule)
    flat_sol = flatten_grass(L['sol'], grass_rule, mode)
    flatten_grass(L['sol_complet'], grass_rule, mode)
    # 2. restes flous (petites taches entourées d'herbe franche ; le chemin est une grande composante : gardé)
    speck = (L['sol'][..., 3] == 255) & ~flat_sol & ~D['stairs']
    n_speck = 0
    for comp in small_components(speck, 60):
        if flat_sol[ring(comp)].mean() > 0.8:
            L['sol'][comp, :3] = SKY_GRASS; flat_sol |= comp; n_speck += int(comp.sum())
    old = D['layers']['fleurs'].copy()
    # 3. massifs flous classés falaises (soudés à la paroi) : boîtes relevées à la main -> rendus au sol
    fal = L['falaises']; frgb = fal[..., :3].astype(int)
    wl = fal[..., 3] == 255
    fgreen = (frgb[..., 1] > frgb[..., 0] + 25) & (frgb[..., 1] > frgb[..., 2] + 35)
    crystal = (frgb[..., 1] > frgb[..., 0] + 20) & (np.abs(frgb[..., 2] - frgb[..., 1]) < 25) & (frgb.min(2) > 150)
    islands = np.zeros((H, W), bool)
    for (x0, y0, x1, y1) in boxes:
        islands[y0:y1, x0:x1] = True
    islands &= wl & ~crystal
    fpet = islands & ~fgreen
    old[fpet] = fal[fpet]; old[fpet, 3] = 255
    fal[islands] = 0
    L['sol'][islands, :3] = SKY_GRASS; L['sol'][islands, 3] = 255
    L['sol_complet'][islands, :3] = SKY_GRASS
    ex['floor'] = ex['floor'] | islands; ex['walls'] = ex['walls'] & ~islands; flat_sol |= islands
    # 4. massifs flous restés dans le sol (pâles, sombres, grisés : ratés par la règle des pétales)
    rgb = L['sol'][..., :3].astype(int); lum = rgb @ [.299, .587, .114]; sat = rgb.max(2) - rgb.min(2)
    cand = (L['sol'][..., 3] == 255) & ~flat_sol & ~D['stairs'] & ex['floor']
    greenish = (rgb[..., 1] > rgb[..., 0] + 25) & (rgb[..., 1] > rgb[..., 2] + 35)
    brownish = (rgb[..., 0] > rgb[..., 1]) & (rgb[..., 1] > rgb[..., 2]) & (rgb[..., 0] - rgb[..., 2] > 30) & (lum < 170)
    petalish = cand & ~greenish & ~brownish & ((lum > 150) | (sat > 50))
    blurry = np.zeros((H, W), bool)
    for comp in small_components(cand, 1800, 25):
        if petalish[comp].mean() > 0.45 and flat_sol[ring(comp)].mean() > 0.55:
            blurry |= comp
    old[blurry & petalish] = L['sol'][blurry & petalish]; old[blurry & petalish, 3] = 255
    L['sol'][blurry, :3] = SKY_GRASS; flat_sol |= blurry
    # zones libres
    arb = L['arbres'][..., 3] == 255; bus = L['buissons'][..., 3] == 255
    walk_like = ex['floor'] & ~D['zone'] & ~D['trunks'] & ~D['stairs'] & ~arb & ~bus & ~D['wet'] & ~D['casc'] & ~ex['void']
    free = walk_like & flat_sol | (old[..., 3] == 255) & walk_like
    meadow = walk_like & flat_sol
    meadow_c = nd.binary_closing(meadow, iterations=3) & walk_like                 # aplat refermé (petits trous de trame)
    # 5. fleurs nettes
    extra_ok = nd.binary_erosion(meadow_c, iterations=6) & meadow
    flowers, fams_old = plan_flowers(old, free, extra_ok, rng)
    ffr = flower_frames(flowers)
    keep = walk_like | D['zone'] | D['trunks'] | arb | ex['veg'] | D['stairs']       # ombre et penché ne débordent pas sur les parois
    for f in ffr:
        f[~keep] = 0
    fmask = np.zeros((H, W), bool)
    for f in ffr:
        fmask |= f[..., 3] > 0
    under = (old[..., 3] == 255) & (L['sol'][..., 3] == 255)                          # sous les anciens massifs : herbe franche
    L['sol'][under, :3] = SKY_GRASS; flat_sol |= under
    # tiges maigres du rendu autour des anciens massifs (vertes ou brunes, sombres, petites) -> herbe franche
    rgb = L['sol'][..., :3].astype(int); lum = rgb @ [.299, .587, .114]
    stem = (L['sol'][..., 3] == 255) & ~flat_sol & ~D['stairs'] & (lum < 175) & nd.binary_dilation(old[..., 3] == 255, iterations=5)
    n_stem = 0
    for comp in small_components(stem, 150):
        L['sol'][comp, :3] = SKY_GRASS; n_stem += int(comp.sum())
    # 6. touffes (sur l'herbe franche, hors fleurs)
    tuft_ok = nd.binary_erosion(meadow_c, iterations=5) & meadow & ~nd.binary_dilation(fmask, iterations=5)
    tufts = plan_tufts(tuft_ok, rng)
    herbes = tuft_frames(tufts)
    # 7. embruns au pied des cascades
    allowed = ~ex['void'] | D['casc'] | D['wet']
    foam_any = np.zeros((H, W), bool)
    for f in D['ff']:
        foam_any |= f[..., 3] > 0
    embruns, n_drops = embruns_frames(D['rects'], foam_any | D['foam'], allowed, rng)
    # 8. papillons
    bflies = plan_butterflies(nd.binary_erosion(meadow_c, iterations=24), rng)
    papillons, trajets = papillon_frames(bflies)
    D.update(ffr=ffr, fmask=fmask, n_fleurs=len(flowers), herbes=herbes, embruns=embruns, papillons=papillons)
    cols = sorted(set(f[2] for f in flowers))
    D['hq'] = dict(ton_dominant_lot=[int(v) for v in mode], herbe_aplatie_px=int(flat_sol.sum()), restes_flous_px=n_speck, tiges_effacees_px=n_stem,
                   massifs_flous_repris_px=int(blurry.sum()), massifs_falaises_rendus_au_sol_px=int(islands.sum()),
                   boites_massifs_falaise=[list(b) for b in boxes], familles_massifs_origine=fams_old, couleurs=cols,
                   touffes=len(tufts), gouttelettes=n_drops, papillons=bflies, trajets=trajets)
    return D
