"""Entrée Jardin secret sud -> nord V3 (EJS3) — EJS2 (temple de Celebi) + végétation animée, 4:3 (768 x 576 px).

Demande : « rajoute un calque de mouvement de feuille et des animation de fleur palika halcyon et des petale de fleur »,
puis « lance toi » (1er octobre, après FJA1). L'entrée EJS2 reste intacte : EJS3 en reprend les bruts (relus par chemin,
jamais copiés) et toute la segmentation, et ajoute les trois calques de la fin FJA1 :
- feuilles : amas de feuilles des arbres et des haies, retirés des calques fixes et redessinés décalés (houle d'ouest en
  est ; la phase 0 redonne le calque d'origine, sha256) ; 8 x 7 ticks ;
- fleurs_halcyon : touffes NATIVES de Palikadude/Halcyon (Vast_Steppe_Flower_Animations, séquence 0 / 1 / 0 / 2 à
  14 ticks), posées à 8 px au moins du temple, de la souche et des marches ;
- petales : couleurs EXACTES des fleurs du rip, qui tombent des touffes ; 24 x 14 ticks.
Emblème, rayon et lucioles passent à 24 x 7 ticks (EJS2 : 5) : la boucle commune est de 336 ticks (5,6 s).
Marqueurs inchangés : `entrance`, `donjon_seuil` (porte du temple). Aucun warp.
Lancer : .venv/bin/python source/entree_jardin_secret_sud_nord_v3/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = R / 'source/entree_jardin_secret_sud_nord_v2/bruts'      # bruts d'EJS2 (decor_temple.png), relus
RAW1 = R / 'source/entree_jardin_secret_sud_nord_v1/bruts'              # bruts d'EJS1, relus
REF_NAME = 'secretgarden.png'
REF = R / REF_NAME
OUT = R / 'renders/entree_jardin_secret_sud_nord_v3'
STAGE = R / '.cache/entree_jardin_secret_sud_nord_v3/entree_jardin_secret_sud_nord_v3'
NAMESPACE = 'entree_jardin_secret_sud_nord_v3'
ASSET = 'ejs3_entree_jardin_secret_temple'
PFX = 'EJS3'
W, H = 768, 576
SRC = (1200, 896)
PHASES, TICKS = 24, 7                      # emblème, rayon, lucioles : 24 x 7 ticks = 168 (EJS2 : 24 x 5)
LOOP_TICKS = 336                           # = 2 x 168 = 6 x 56 (feuilles 8 x 7, fleurs 4 x 14) = 14 x 24 (pétales)
LOT1 = 'source/entree_jardin_secret_sud_nord_v1'
LOT2 = 'source/entree_jardin_secret_sud_nord_v2'
LOT = 'source/entree_jardin_secret_sud_nord_v3'
GEN = [
    {'file': 'decor.png', 'lot': LOT1, 'images': [REF_NAME], 'prompt':
     'Use EXACTLY the same textures, palette and pixel-art style as the reference image (Pokemon Mystery Dungeon secret '
     'garden): same light yellow-green meadow grass with small tufts, same rounded bushy hedge borders, same round leafy '
     'trees, same tan-brown boulders, same small white, yellow and pink flowers, same big golden tree stump with a square '
     'dark hole and wooden steps, same vertical bright green light beam falling from the top edge, same dark green '
     'background. Make a NEW, larger top-down map. WIDE LANDSCAPE 4:3, zoomed out so the garden feels vast. Layout: the '
     'player arrives at the SOUTH (bottom edge center) on a grass path between bushy hedges; the path opens into a wide '
     'meadow with a few boulders, trees and flower patches; at the NORTH (top center) the big tree stump with its dark '
     'hole and steps, the green light beam falling from the top edge onto it, flowers around it, and the grass leads '
     'right up to the steps. Dark green background around the hedges. No characters, no text, no UI, no border.',
     'essais': 'premier essai ; conforme'},
    {'file': 'temoin_sans_objets.png', 'lot': LOT1, 'images': [f'{LOT1}/bruts/decor.png'], 'prompt':
     'Same image, same framing and exact same pixel-art style. Remove every round leafy tree (with its trunk and shadow), '
     'every boulder and rock, and every small flower: replace them with the same meadow grass around them. Keep the bushy '
     'hedge borders, the big golden tree stump with its dark hole and steps, the green light beam, the light grass path '
     'and the dark green background exactly as they are. No text, no border.',
     'essais': 'premier essai ; temoin de segmentation, jamais exporte'},
    {'file': 'ecartes/sol_complet_essai1_touffes.png', 'lot': LOT1, 'images': [f'{LOT1}/bruts/decor.png'], 'ecarte': True, 'prompt':
     'Same image, same framing and pixel-art style, but only the plain medium yellow-green meadow grass with its small '
     'grass tufts everywhere, covering the whole image edge to edge, keep the texture detail, nothing else.',
     'essais': 'ECARTE : grosses touffes hautes, vert acide (148.5,178.3,28.6), distance 43.2 > 35 a l herbe du rip'},
    {'file': 'ecartes/sol_complet_essai2_plaques.png', 'lot': LOT1, 'images': [REF_NAME], 'ecarte': True, 'prompt':
     'Fill the ENTIRE image edge to edge with only the medium yellow-green meadow grass from the reference image (the '
     'grass around the flowers and trees, with its fine texture and a few tiny grass tufts), same pixel-art style, same '
     'palette and contrast. No tall grass clumps, no bushes, no trees, no rocks, no flowers, no path, no dark areas. '
     'Wide landscape 4:3.',
     'essais': 'ECARTE : plaques tramees, (151.2,193.5,48.3), distance 45.7 > 35 a l herbe du rip'},
    {'file': 'sol_complet.png', 'lot': LOT1, 'images': [f'{LOT1}/bruts/temoin_sans_objets.png'], 'prompt':
     'Same image, same framing and exact same pixel-art style. Replace the bushy hedges, the tree stump, the green light '
     'beam, the light central grass and the dark green background with the same medium green meadow grass that is between '
     'the hedges and the light path, with its small grass tufts, so that the whole image is only that medium meadow '
     'grass, edge to edge. No text, no border.',
     'essais': 'troisieme essai ; conforme (121.7,174.9,52.6), distance 11.0 a l herbe du rip'},
    {'file': 'decor_temple.png', 'lot': LOT2, 'images': [f'{LOT1}/bruts/decor.png', REF_NAME], 'prompt':
     'Edit the first image. Keep EVERYTHING identical (same framing, same size, same hedges, trees, rocks, flowers, meadow, '
     'light beam, same pixel positions). Change ONLY the top of the big golden tree stump in the upper center: replace the '
     'square dark hole on the stump\'s flat top with a tiny miniature shrine temple standing on the stump top, the secret '
     'guardian shrine of Celebi. The little temple fits entirely on the stump top: small pale stone base, two tiny wooden '
     'pillars, a small curved green leaf-colored roof, an open dark doorway facing the viewer at the front, and a tiny carved '
     'Celebi emblem (onion-shaped head with two antennae and small wings, light green) on the pediment above the door. The '
     'wooden steps on the front of the stump stay and lead up to the temple doorway. Same Pokemon Mystery Dungeon pixel-art '
     'style, palette and shading as the second reference image. No text.',
     'essais': 'premier essai ; conforme ; seule la zone du temple est reprise (collage local sur le decor d EJS1)'},
]
USED = [g for g in GEN if not g.get('ecarte')]


def raw_path(g):
    return R / g['lot'] / 'bruts' / g['file']


# ---- Temple : fenêtre de la souche (pleine résolution) où l'on reprend le brut du temple.
WIN = (60, 280, 500, 700)                # y0, y1, x0, x1
PASTE_DIFF = 22                          # écart (lissé 3 px) décor EJS1 / brut du temple qui délimite le temple
EMBLEM_GLOW = 3                          # l'emblème s'éclaire de 3 crans de rampe au milieu de la boucle
# ---- Rayon : rampe relevée sur le rip (zone y < 95, x 130-280, couleurs vertes du rayon, par luminance croissante ;
# les tons beiges des rochers de la même zone sont exclus).
RAMP = [(47, 95, 55), (47, 103, 55), (55, 119, 55), (63, 135, 55), (63, 151, 55), (63, 167, 55), (71, 183, 63),
        (79, 199, 71), (79, 215, 71), (87, 223, 71), (95, 231, 71), (95, 239, 71), (103, 247, 79), (111, 255, 87),
        (127, 255, 95), (151, 255, 111), (175, 255, 127), (191, 255, 135), (207, 255, 151), (231, 255, 199),
        (239, 255, 223), (255, 255, 255)]
BREATH = 2                     # amplitude du souffle, en crans de rampe
EDGE_STEPS = 6                 # les 6 premiers crans (bords sombres) sont atténués : pas d'arête contre le fond
# ---- Lucioles : (x0, y0, décalage de phase, amplitude x). Montée de 2 px par phase, oscillation sur 12 phases.
MOTES = [(336, 128, 0, 2), (434, 132, 6, 2), (344, 96, 12, 3), (428, 90, 18, 3), (346, 60, 3, 2), (428, 56, 15, 2),
         (196, 214, 4, 3), (566, 206, 10, 3), (170, 310, 16, 3), (610, 300, 22, 3)]
MOTE_RISE = 2
DOT, GLOW, CORE = (207, 255, 151), (231, 255, 199), (255, 255, 255)


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


V1 = loadmod('ewc1_build', R / 'source/entree_waterfall_cave_sud_nord_v1/build.py')     # utilitaires génériques
JM, BM = V1.JM, V1.BM
assert (JM.W, JM.H, JM.SRC) == (W, H, SRC)
keep_large, cell_grid, close_ = V1.keep_large, V1.cell_grid, V1.close_
down_class, down_full, rgba, quantize_group = V1.down_class, V1.down_full, V1.rgba, V1.quantize_group
PALETTE_GROUPS = {'herbe': (['sol_complet', 'prairie', 'herbe', 'ombres'], 64), 'fleurs': (['fleurs'], 24),
                  'rochers': (['rochers'], 32), 'vegetation': (['arbres', 'haies'], 96),
                  'souche': (['souche', 'marches', 'profondeur'], 48), 'temple': (['temple'], 48),
                  'fond': (['fond'], 8)}
STATIC = ['prairie', 'herbe', 'ombres', 'fleurs', 'rochers', 'arbres', 'haies', 'souche', 'temple', 'marches', 'profondeur',
          'fond']
ANIMS = ['fleurs_halcyon', 'petales', 'feuilles', 'embleme', 'rayon', 'lucioles']


def open_(m, it):
    p = it + 1
    return nd.binary_opening(np.pad(m, p, mode='edge'), iterations=it)[p:-p, p:-p]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rgb(p):
    return np.array(Image.open(p).convert('RGB')).astype(int)


def lum_of(a):
    return a[..., :3].astype(float) @ [.299, .587, .114]


def sdev(l, k):
    return np.sqrt(np.maximum(nd.uniform_filter(l ** 2, k) - nd.uniform_filter(l, k) ** 2, 0))


# ---------------------------------------------------------------- fidélité au rip (même classifieur des deux côtés)
def materials(a):
    """Fond vert sombre, herbe claire (prairie), herbe moyenne, roche beige."""
    a = a.astype(float); r, g, b = a[..., 0], a[..., 1], a[..., 2]; lum = lum_of(a)
    return {'fond': (lum < 85) & (g > r + 20) & (g > b + 15) & (lum > 55),
            'herbe_claire': (g > 185) & (r > 130) & (b < 120) & (g > r + 30),
            'herbe': (g > 140) & (g <= 185) & (g > r + 30) & (g > b + 60),
            'roche': (r >= g - 15) & (r - b > 25) & (lum > 90) & (lum < 200) & (np.abs(r - g) < 30)}


def fidelity(decor, ref):
    fr, fd = materials(ref), materials(decor); out = {}
    for k in fr:
        mr, md = ref[fr[k]].mean(0), decor[fd[k]].mean(0)
        out[k] = {'rip_rgb': [round(float(v), 1) for v in mr], 'decor_rgb': [round(float(v), 1) for v in md],
                  'distance': round(float(np.linalg.norm(mr - md)), 1)}
    return out


def recalage(a, o, zone):
    err = {(dy, dx): float(np.abs(a - np.roll(np.roll(o, dy, 0), dx, 1))[zone].mean())
           for dy in (-1, 0, 1) for dx in (-1, 0, 1)}
    assert min(err, key=err.get) == (0, 0), err
    return {'ecart_moyen': round(err[(0, 0)], 2), 'ecart_decale_1px': round(min(v for k, v in err.items() if k != (0, 0)), 2)}


# ---------------------------------------------------------------- segmentation pleine résolution
def flower_px(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return ((r > 200) & (g < 160)) | (lum_of(a) > 225) | ((r > 200) & (g > 180) & (b < 110))


def composite(a1, g):
    """Colle sur le décor d'EJS1 (a1) la seule zone du temple du brut g. Retourne (décor collé, masque collé)."""
    hh, ww = a1.shape[:2]; yy, xx = np.mgrid[:hh, :ww]; y0, y1, x0, x1 = WIN
    win = (yy >= y0) & (yy < y1) & (xx >= x0) & (xx < x1)
    d = nd.uniform_filter(np.abs(g - a1).mean(2).astype(float), 3)
    lab, n = nd.label(close_((d > PASTE_DIFF) & win, 3)); s = nd.sum(np.ones_like(lab), lab, range(1, n + 1))
    paste = nd.binary_dilation(nd.binary_fill_holes(lab == int(np.argmax(s)) + 1), iterations=2) & win
    out = a1.copy(); out[paste] = g[paste]
    return out, paste


def classify(a, t, paste):
    """a : décor (collé), t : témoin sans objets d'EJS1, paste : zone du temple collée. Seuils mesurés sur le brut (1200 x 896) :
    TEMPLE (EJS2) = zone collée au-dessus du bas du socle de pierre (plus grande composante grise : saturation < 30,
    lum 120-235) ; porte = lum < 70 dans cette zone, plus grande composante, trous bouchés (c'est la profondeur, à la place
    du trou) ; marches = souche du témoin et temple sous la porte, dans la largeur de l'ancien trou (+- 2 px) : parvis de
    pierre et escalier de bois ; emblème = pixels clairs (lum > 165, g > r + 15) du fronton, dans une boîte de 24 x 18 px
    au-dessus de la porte, fermés 1 px ; le temple et la porte sortent du rayon.
    fond = lum lissée 5 px du témoin < 85, vert (g > r + 15), ouvert 3 px, relié au bord ; rayon = pixels du témoin
    très verts (g - r > 70) ou très clairs (lum > 205), y < 175, x 470-730, hors fond, fermés 2 px, reliés au bord haut ;
    souche = doré (r >= g - 12, r - b > 60) au haut-centre, fermé 4 px, > 3000 px, trous bouchés ; profondeur = lum < 75
    dans la souche, ouverte 1 px, plus grande composante ; marches = toute la souche sous le trou, dans
    sa largeur (+- 2 px), barreaux clairs et creux compris (sinon l'escalier ne rejoint pas l'herbe) ; haies = témoin texturé (écart-type 9 px > 6), fermé 3 px, > 3000 px, ouvert 5 px puis redilaté (les lisières
    fines, comme l'arc entre prairie et allée, ne sont pas des haies), petits trous (< 800 px) bouchés,
    rien dans la zone dégagée sous la souche ; objets = écart décor / témoin lissé 3 px > 28, fermé 3 px, trous bouchés,
    >= 30 px : fleurs = composantes < 400 px à >= 20 % de pixels de fleur ; rochers = beige (|r-g| < 30, r-b > 25) fermé
    2 px, trous bouchés, >= 150 px, lum moyenne > 115 (les troncs, plus sombres, restent aux arbres) ; ombres portées =
    herbe plate sombre (écart-type < 6, lum < 155, g > r + 30) ; arbres = le reste des objets (>= 300 px) ; herbe hors
    objets : prairie = b lissé 5 px < 50 (jaune), ombres = lum lissée 5 px < 150, herbe = le reste. Les composantes d'objets du décor (diff > 28) posées sur le rayon du témoin
    et dont moins de 30 % des pixels ont la couleur du rayon dans le décor (le rocher à gauche du faisceau) sortent du rayon."""
    lt, la = lum_of(t), lum_of(a); hh, ww = lt.shape; yy, xx = np.mgrid[:hh, :ww]
    r, g, b = t[..., 0], t[..., 1], t[..., 2]
    fond = open_((nd.uniform_filter(lt, 5) < 85) & (g > r + 15), 3)
    lab, _ = nd.label(fond); e = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]); fond = np.isin(lab, e[e > 0])
    beam = ((g - r > 70) | (lt > 205)) & (yy < 175) & (xx > 470) & (xx < 730) & ~fond
    lab, _ = nd.label(close_(beam, 2)); rayon = np.isin(lab, np.unique(lab[0][lab[0] > 0])) & (yy < 175)
    rayon = nd.binary_fill_holes(rayon) & ~fond
    ra, ga = a[..., 0], a[..., 1]; beam_a = (ga - ra > 70) | (lum_of(a) > 205)
    d0 = nd.uniform_filter(np.abs(a - t).mean(2).astype(float), 3)
    ol0, on0 = nd.label(nd.binary_fill_holes(close_(d0 > 28, 3)) & rayon)
    for i in range(on0):                    # objets du décor posés sur le rayon du témoin (rocher) : hors rayon
        m = ol0 == i + 1
        if m.sum() >= 30 and beam_a[m].mean() < 0.3:
            rayon &= ~m
    gold = (r >= g - 12) & (r - b > 60) & (yy > 120) & (yy < 280) & (xx > 500) & (xx < 700)
    st = nd.binary_fill_holes(keep_large(close_(gold, 4), 3000)) & ~rayon
    hole = open_((lt < 75) & st, 1); hl, hn = nd.label(hole); hs = nd.sum(hole, hl, range(1, hn + 1))
    hole = nd.binary_fill_holes(close_(hl == int(np.argmax(hs)) + 1, 2)) & st
    hy, hx = np.nonzero(hole); sy, sx = np.nonzero(st)
    # --- temple (EJS2)
    sat = a.max(2) - a.min(2)
    grey = paste & (sat < 30) & (la > 120) & (la < 235); gl, gn = nd.label(grey)
    stone = gl == int(np.argmax(nd.sum(grey, gl, range(1, gn + 1)))) + 1
    ybase = int(np.nonzero(stone)[0].max()); top = paste & (yy <= ybase)
    dm = top & (la < 70); dl, dn = nd.label(dm)
    door = nd.binary_fill_holes(dl == int(np.argmax(nd.sum(dm, dl, range(1, dn + 1)))) + 1)
    dy, dx = np.nonzero(door); dcx = int(round(dx.mean()))
    ebox = top & (yy >= dy.min() - 26) & (yy < dy.min() - 8) & (np.abs(xx - dcx) <= 12)
    emblem = close_(ebox & (la > 165) & (a[..., 1] > a[..., 0] + 15), 1) & ebox
    rayon &= ~top
    steps = (st | top) & (yy > dy.max()) & (xx >= hx.min() - 2) & (xx <= hx.max() + 2) & ~door   # parvis + escalier
    temple = top & ~door & ~steps & ~emblem
    hole = door; st = st | top
    front = (yy > sy.max() - 10) & (yy < sy.max() + 40) & (xx > sx.min() + 20) & (xx < sx.max() - 20) & ~st
    haie = keep_large(close_((sdev(lt, 9) > 6) & ~fond & ~rayon & ~st & ~front, 3), 3000)
    haie &= nd.binary_dilation(open_(haie, 5), iterations=5)     # lisières fines (arc prairie / allée) : pas des haies
    hol = nd.binary_fill_holes(haie) & ~haie; hl, hn = nd.label(hol); hs = nd.sum(hol, hl, range(1, hn + 1))
    haie = (haie | np.isin(hl, [i + 1 for i, v in enumerate(hs) if v < 800])) & ~fond & ~rayon & ~st & ~front
    diff = nd.uniform_filter(np.abs(a - t).mean(2).astype(float), 3)
    obj = keep_large(nd.binary_fill_holes(close_(diff > 28, 3)), 30) & ~st & ~rayon & ~fond
    ol, on = nd.label(obj); fpx = flower_px(a); fle = np.zeros_like(obj)
    for i, s in enumerate(nd.find_objects(ol)):
        m = ol[s] == i + 1
        if m.sum() < 400 and fpx[s][m].mean() >= 0.2:
            fle[s] |= m
    ra, ga, ba = a[..., 0], a[..., 1], a[..., 2]
    tan = (np.abs(ra - ga) < 30) & (ra - ba > 25) & (la > 80) & (la < 215) & obj & ~fle
    tl, tn = nd.label(nd.binary_fill_holes(close_(tan, 2)) & obj & ~fle); roc = np.zeros_like(obj); nroc = 0
    for i, s in enumerate(nd.find_objects(tl)):
        m = tl[s] == i + 1
        if m.sum() >= 150 and la[s][m].mean() > 115:
            roc[s] |= m; nroc += 1
    flat = (sdev(la, 9) < 6) & (la < 155) & (ga > ra + 30)
    shade = obj & ~fle & ~roc & flat
    arb = keep_large(obj & ~fle & ~roc & ~shade, 300)
    rest = obj & ~fle & ~roc & ~arb & ~shade                      # miettes : rendues à l'herbe
    grass = ~(fond | rayon | st | haie | fle | roc | arb)
    bl, ll = nd.uniform_filter(ba.astype(float), 5), nd.uniform_filter(la, 5)
    prairie = grass & ~shade & (bl < 50)
    omb = grass & ~prairie & ((ll < 150) | shade)
    herbe = grass & ~prairie & ~omb
    souche = st & ~hole & ~steps & ~temple & ~emblem
    masks = dict(profondeur=hole, marches=steps, souche=souche, temple=temple, embleme=emblem, fleurs=fle, rochers=roc, arbres=arb, haies=haie,
                 fond=fond, rayon=rayon, ombres=omb, prairie=prairie, herbe=herbe)
    seg = {'objets': int(on), 'fleurs': int(nd.label(fle)[1]), 'rochers': nroc, 'arbres': int(nd.label(arb)[1]),
           'miettes_rendues_a_l_herbe_px': int(rest.sum()), 'trou_y': [int(hy.min()), int(hy.max())],
           'trou_x': [int(hx.min()), int(hx.max())], 'souche_y': [int(sy.min()), int(sy.max())],
           'ombres_lum': round(float(la[omb].mean()), 1), 'herbe_lum': round(float(la[herbe].mean()), 1),
           'prairie_b': round(float(ba[prairie].mean()), 1),
           'temple': {'socle_bas_y': ybase, 'porte_y': [int(dy.min()), int(dy.max())], 'porte_x': [int(dx.min()), int(dx.max())],
                      'temple_px': int(temple.sum()), 'embleme_px': int(emblem.sum()), 'colle_px': int(paste.sum())}}
    return masks, seg


# ---------------------------------------------------------------- rayon : rampe exacte du rip
def ramp_index(px):
    """Indice du cran de rampe le plus proche (distance RGB) pour chaque pixel."""
    rp = np.array(RAMP, float)
    return ((px[..., None, :3].astype(float) - rp) ** 2).sum(-1).argmin(-1)


def breath(t):
    return int(round(BREATH * np.sin(2 * np.pi * t / PHASES)))


def beam_frames(base_idx, mask, ts=range(PHASES)):
    rp = np.array(RAMP, 'uint8'); frames = []
    w = np.minimum(1.0, base_idx / EDGE_STEPS)
    for t in ts:
        idx = np.clip(np.round(base_idx + breath(t) * w), 0, len(RAMP) - 1).astype(int)
        a = np.zeros((H, W, 4), 'uint8'); a[mask, :3] = rp[idx[mask]]; a[mask, 3] = 255
        frames.append(a)
    return frames


def glow(t):
    """Crans ajoutés à l'emblème à la phase t : 0 à la phase 0, EMBLEM_GLOW à la phase 12. Calculé sur min(t, 24 - t) :
    aller-retour exactement symétrique (sinon l'arrondi de 1,4999... et 1,5000... le rendait bancal)."""
    u = t % PHASES; u = min(u, PHASES - u)
    return int(round(EMBLEM_GLOW * (1 - np.cos(2 * np.pi * u / PHASES)) / 2))


def emblem_frames(base_idx, mask, ts=range(PHASES)):
    rp = np.array(RAMP, 'uint8'); frames = []
    for t in ts:
        idx = np.clip(base_idx + glow(t), 0, len(RAMP) - 1)
        a = np.zeros((H, W, 4), 'uint8'); a[mask, :3] = rp[idx[mask]]; a[mask, 3] = 255
        frames.append(a)
    return frames


# ---------------------------------------------------------------- lucioles
def mote_state(m, t):
    """(x, y, forme) de la luciole m à la phase t ; forme 'point' (1 px) ou 'croix' (croix de 3 x 3)."""
    x0, y0, off, ax = m; u = (t + off) % PHASES
    x = x0 + int(round(ax * np.sin(2 * np.pi * u / 12))); y = y0 - MOTE_RISE * u
    shape = 'croix' if 3 <= u <= 20 and u % 4 in (0, 1) else 'point'
    return x, y, shape


def mote_frames(motes, ts=range(PHASES)):
    frames = []
    for t in ts:
        a = np.zeros((H, W, 4), 'uint8')
        for m in motes:
            x, y, shape = mote_state(m, t)
            if shape == 'croix':
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    a[y + dy, x + dx] = (*GLOW, 255)
                a[y, x] = (*CORE, 255)
            else:
                a[y, x] = (*DOT, 255)
        frames.append(a)
    return frames


# ---------------------------------------------------------------- végétation animée : feuilles, fleurs Halcyon, pétales
LEAF_PHASES, LEAF_TICKS = 8, 7
FLOWER_SEQ, FLOWER_TICKS = [0, 1, 0, 2], 14              # séquence NATIVE Halcyon (TexLoc 0 / 3 / 0 / 6 à 14 ticks)
PETAL_PHASES, PETAL_TICKS = 24, 14
TK = {'embleme': TICKS, 'rayon': TICKS, 'lucioles': TICKS, 'feuilles': LEAF_TICKS, 'fleurs_halcyon': FLOWER_TICKS, 'petales': PETAL_TICKS}
LEAF_ZONES = ('arbres', 'haies')
LEAF_AMP, LEAF_WAVE = 0.9, 220.0                            # amplitude (px) et longueur d'onde (px) de la houle d'ouest en est
LEAF_SIZE, LEAF_ERODE, LEAF_CONTRAST, LEAF_KEEP = (2, 12), 3, 14, 3   # amas de 2 à 12 px, intérieur : érosion 3 px, un amas sur 3
FLOWER_ATLAS = R / 'source/amp_plains_fleurie_v1/references/Vast_Steppe_Flower_Animations.png'
CLUMPS, CLUMP_MIN_DIST = 14, 52
PETAL_COLORS = {'blanc': (247, 255, 231), 'jaune': (239, 207, 103), 'rose': (223, 127, 119)}   # EXACTES, fleurs du rip
PETAL_ORDER = ['rose', 'blanc', 'jaune']
PETAL_SHAPES = {'carre': [(0, 0), (1, 0), (0, 1), (1, 1)], 'barre_h': [(0, 0), (1, 0)], 'barre_v': [(0, 0), (0, 1)], 'point': [(0, 0)]}


def leaf_shift(cx, t):
    """Décalage (dx, dy) de l'amas de centre x = cx à la phase t : houle d'ouest en est, nulle à la phase 0, fermée à 8."""
    f = lambda tt: LEAF_AMP * np.sin(2 * np.pi * (tt / LEAF_PHASES + cx / LEAF_WAVE))
    g = lambda tt: LEAF_AMP * np.sin(2 * np.pi * (tt / LEAF_PHASES + cx / LEAF_WAVE + 0.25))
    return int(np.round(f(t))) - int(np.round(f(0))), int(np.round(g(t))) - int(np.round(g(0)))


def extract_leaves(layers):
    """Pour arbres et haies (déjà quantifiés) : amas de feuilles claires = pixels du feuillage plus clairs que la moyenne
    locale 7 x 7 du feuillage (+ 14 de luminance), composantes 8-connexes de 2 à 12 px entièrement à l'intérieur du
    feuillage (érodé de 3 px, carré 3 x 3 : un décalage de 2 px en diagonale reste dedans), un amas sur trois (hachage de la position). Les pixels des amas sont retirés du calque fixe
    (remplacés par la couleur du feuillage voisin, rabattue sur la palette du calque) et redessinés par le calque
    `feuilles`. Renvoie (calques fixes, phase 0 du calque feuilles, étiquettes des amas, sha256 des originaux)."""
    f0 = np.zeros((H, W, 4), 'uint8'); lab_all = np.zeros((H, W), 'uint16'); nid = 0; origin = {}
    for name in LEAF_ZONES:
        a = layers[name].copy(); origin[name] = hashlib.sha256(layers[name].tobytes()).hexdigest()
        m = a[..., 3] == 255; lum = lum_of(a)
        mean = nd.uniform_filter(np.where(m, lum, 0), 7) / np.maximum(nd.uniform_filter(m.astype(float), 7), 1e-6)
        hi = m & (lum > mean + LEAF_CONTRAST) & nd.binary_erosion(m, structure=np.ones((3, 3), bool), iterations=LEAF_ERODE)
        lab, n = nd.label(hi, structure=np.ones((3, 3))); removed = np.zeros((H, W), bool)
        for i, sl in enumerate(nd.find_objects(lab)):
            ys, xs = np.nonzero(lab[sl] == i + 1); ys, xs = ys + sl[0].start, xs + sl[1].start
            if not LEAF_SIZE[0] <= len(ys) <= LEAF_SIZE[1] or (int(xs.mean()) * 7 + int(ys.mean()) * 13) % LEAF_KEEP:
                continue
            nid += 1; lab_all[ys, xs] = nid; removed[ys, xs] = True
        rest = m & ~removed
        num = np.stack([nd.uniform_filter(np.where(rest, a[..., c], 0).astype(float), 9) for c in range(3)], -1)
        den = np.maximum(nd.uniform_filter(rest.astype(float), 9), 1e-6)[..., None]
        near = num / den; pal = np.unique(a[rest][:, :3], axis=0).astype(float)
        snap = pal[((near[removed][:, None, :] - pal[None]) ** 2).sum(-1).argmin(-1)].astype('uint8')
        f0[removed] = a[removed]; a[removed, :3] = snap; layers[name] = a
    return layers, f0, lab_all, origin


def leaf_frames(f0, lab, ts=range(LEAF_PHASES)):
    """Calque `feuilles` : chaque amas de la phase 0 décalé de leaf_shift(x moyen, t)."""
    frames = []; objs = nd.find_objects(lab)
    for t in ts:
        a = np.zeros((H, W, 4), 'uint8')
        for i, sl in enumerate(objs):
            if sl is None:
                continue
            ys, xs = np.nonzero(lab[sl] == i + 1); ys, xs = ys + sl[0].start, xs + sl[1].start
            dx, dy = leaf_shift(int(round(xs.mean())), t)
            a[ys + dy, xs + dx] = f0[ys, xs]
        frames.append(a)
    return frames


def halcyon_poses():
    atlas = Image.open(FLOWER_ATLAS).convert('RGBA')
    return [np.array(atlas.crop((i * 24, 0, i * 24 + 24, 24))) for i in range(3)]


def place_clumps(poses, walk, ex):
    """Touffes natives 24 x 24 posées là où tous leurs pixels opaques sont sur le sol praticable (érodé de 2 px), hors
    prairie claire du centre (< 25 % de la boîte), hors rayon et profondeur, au moins CLUMP_MIN_DIST px entre elles :
    échantillonnage du point le plus éloigné, départ au candidat le plus proche de (150, 200)."""
    ok = nd.binary_erosion(walk, iterations=2) & ~ex['rayon'] & ~ex['profondeur'] & ~nd.binary_dilation(
        ex['marches'] | ex['temple'] | ex['souche'] | ex['embleme'], iterations=8); sil = poses[0][..., 3] == 255
    cand = []
    for y in range(8, H - 32, 4):
        for x in range(8, W - 32, 4):
            if ok[y:y + 24, x:x + 24][sil].all() and ex['prairie'][y:y + 24, x:x + 24].mean() < 0.25:
                cand.append((x, y))
    cand = np.array(cand); chosen = [tuple(cand[((cand - (150, 200)) ** 2).sum(1).argmin()])]
    while len(chosen) < CLUMPS:
        d = np.min([((cand - c) ** 2).sum(1) for c in chosen], axis=0); j = int(d.argmax())
        assert d[j] >= CLUMP_MIN_DIST ** 2, (len(chosen), d[j])
        chosen.append(tuple(cand[j]))
    return sorted((int(x), int(y)) for x, y in chosen)


def flower_frames(poses, clumps, ts=range(len(FLOWER_SEQ))):
    frames = []
    for t in ts:
        a = np.zeros((H, W, 4), 'uint8')
        for i, (x, y) in sorted(enumerate(clumps), key=lambda e: e[1][1]):      # le plus bas devant
            spr = poses[FLOWER_SEQ[(t + i) % len(FLOWER_SEQ)]]; m = spr[..., 3] == 255
            a[y:y + 24, x:x + 24][m] = spr[m]
        frames.append(a)
    return frames


def petal_shape(u):
    """Forme du pétale à la phase de vie u (0-23) : 1 px à la naissance et à la fin, puis il culbute (carré, barre h, carré, barre v)."""
    if u < 2 or u > 21:
        return 'point'
    return ['carre', 'barre_h', 'carre', 'barre_v'][u % 4] if 6 <= u <= 17 else ('barre_h' if u % 2 else 'barre_v')


def petal_pos(p, u):
    x0, y0, off, color, dirx = p
    return x0 + int(round(1.1 * dirx * u)) + int(round(2 * np.sin(2 * np.pi * u / 12 + off))), y0 + int(round(0.9 * u))


def petal_frames(petals, ts=range(PETAL_PHASES)):
    frames = []
    for t in ts:
        a = np.zeros((H, W, 4), 'uint8')
        for p in petals:
            u = (t + p[2]) % PETAL_PHASES; x, y = petal_pos(p, u); col = PETAL_COLORS[p[3]]
            for dx, dy in PETAL_SHAPES[petal_shape(u)]:
                a[y + dy, x + dx] = (*col, 255)
        frames.append(a)
    return frames


def make_petals(clumps, ex):
    """Deux pétales par touffe (têtes de fleur à (x + 9, y + 7) et (x + 15, y + 9), départs décalés de 12 phases) et dix
    pétales partis de fleurs du décor (tirage fixe, graine 7). Couleurs EXACTES des fleurs du rip, en rotation. Un
    pétale dont le trajet touche le fond, le rayon, le temple, la souche ou sort de l'image est écarté."""
    rng = np.random.default_rng(7); petals = []; k = 0
    for i, (x, y) in enumerate(clumps):
        for j, (hx, hy) in enumerate(((9, 7), (15, 9))):
            petals.append((x + hx, y + hy, (i * 5 + 12 * j) % PETAL_PHASES, PETAL_ORDER[k % 3], 1)); k += 1
    fy, fx = np.nonzero(ex['fleurs']); pick = rng.choice(len(fy), 10, replace=False)
    for q in sorted(pick):
        petals.append((int(fx[q]), int(fy[q]), int(rng.integers(PETAL_PHASES)), PETAL_ORDER[k % 3], 1 if k % 4 else -1)); k += 1
    bad = ex['fond'] | ex['rayon'] | ex['temple'] | ex['souche'] | ex['embleme']; good = []
    for p in petals:
        pts = [petal_pos(p, u) for u in range(PETAL_PHASES)]
        if all(0 <= x < W - 2 and 0 <= y < H - 2 and not bad[y:y + 2, x:x + 2].any() for x, y in pts):
            good.append(p)
    return good, len(petals) - len(good)


def sheet_vegetation(poses):
    """Planche de contrôle x6 : 3 dessins natifs Halcyon, formes de pétale (3 couleurs), exemple d'amas de feuilles."""
    sh = Image.new('RGBA', (3 * 24 * 6 + 4 * 10, 24 * 6 + 20 + 80), (121, 174, 52, 255)); d = ImageDraw.Draw(sh)
    for i, p in enumerate(poses):
        sh.alpha_composite(Image.fromarray(p).resize((144, 144), Image.Resampling.NEAREST), (10 + i * 154, 10))
    x = 10
    for cn in PETAL_ORDER:
        for sn, cells in PETAL_SHAPES.items():
            for dx, dy in cells:
                d.rectangle([x + dx * 12, 164 + dy * 12, x + dx * 12 + 11, 164 + dy * 12 + 11], fill=(*PETAL_COLORS[cn], 255))
            x += 36
        x += 18
    return sh


def write_ora(path, layers):
    import xml.etree.ElementTree as ET
    root = ET.Element('image', w=str(W), h=str(H), name='Entree Jardin secret sud-nord V3, temple de Celebi et vegetation (EJS3)')
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
    o.update(Name={'DefaultText': 'Entree Jardin secret, temple de Celebi - sud vers nord (4:3)', 'LocalTexts': {}}, AssetName=ASSET,
             Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0},
             ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Rendu genere 4:3 reference sur le rip Jardin secret ; temple miniature de Celebi sur '
                     'la souche, porte = entree ; embleme, rayon et lucioles animes (rampe exacte du rip). Collisions de base a verifier. Seuil non raccorde. '
                     'Biome choisi par l agent.')
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
  <Name>Entree Jardin secret V2, temple de Celebi, sud-nord 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : arrivee par une allee au sud, grande prairie fleurie, temple miniature de Celebi sur la souche, sous un rayon de lumiere, au nord, genere au format 4:3 (ref. rip Jardin secret), embleme, rayon et lucioles animes. Pas une aventure jouable.</Description>
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
    if OUT.exists():
        for d in ['calques', 'animation', 'masques', 'review', 'poses']:
            shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['calques', 'masques', 'review', 'poses'] + [f'animation/{x}' for x in ANIMS]:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    STAGE.parent.mkdir(parents=True, exist_ok=True)
    a1, g2 = rgb(RAW1 / 'decor.png'), rgb(RAW / 'decor_temple.png')
    t, f, ref = rgb(RAW1 / 'temoin_sans_objets.png'), rgb(RAW1 / 'sol_complet.png'), rgb(REF)
    y0, y1, x0, x1 = WIN; far = np.ones(a1.shape[:2], bool); far[max(0, y0 - 20):y1 + 20, max(0, x0 - 20):x1 + 20] = False
    reg_temple = recalage(a1, g2, far)                        # brut du temple calé (0, 0) sur le décor d'EJS1
    a, paste = composite(a1, g2)
    Image.fromarray((paste * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_zone_collee_pleine_resolution.png')
    assert a.shape[:2] == t.shape[:2] == f.shape[:2] == (SRC[1], SRC[0])
    m, seg = classify(a, t, paste)
    objs = m['fleurs'] | m['rochers'] | m['arbres'] | (np.abs(a - t).mean(2) > 10)
    reg = {'temoin': recalage(a, t, ~nd.binary_dilation(objs | paste, iterations=4)), 'brut_temple': reg_temple}
    order = ['profondeur', 'embleme', 'marches', 'temple', 'souche', 'fleurs', 'rochers', 'arbres', 'rayon', 'haies', 'fond', 'ombres',
             'prairie', 'herbe']
    ex, cols = down_class(a, m, order)
    layers = {'sol_complet': rgba(down_full(f), np.ones((H, W), bool))}
    for k in STATIC:
        layers[k] = rgba(cols[k], ex[k])
    q = {}
    for keys, n in PALETTE_GROUPS.values():
        q.update(quantize_group({k: layers[k] for k in keys}, n))
    layers = q
    layers, leaf0, leaf_lab, leaf_origin = extract_leaves(layers)
    Image.fromarray(leaf_lab).save(OUT / 'masques' / f'{PFX}_feuilles_amas.png')
    for k, v in ex.items():
        Image.fromarray((v * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_{k}.png')
    mouth = ex['profondeur']
    cand = ex['prairie'] | ex['herbe'] | ex['ombres'] | ex['fleurs'] | ex['marches']
    cl, _ = nd.label(close_(cand, 2)); seed = cl[H - 1][cand[H - 1]]   # liserés < 4 px (contours d'arbres/haies) franchis
    walk = np.isin(cl, np.unique(seed[seed > 0])) & cand
    Image.fromarray((walk * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_praticable.png')
    base_idx = ramp_index(cols['rayon'])
    Image.fromarray(np.where(ex['rayon'], base_idx * 11, 0).astype('uint8')).save(OUT / 'masques' / f'{PFX}_rayon_crans.png')
    rayon = beam_frames(base_idx, ex['rayon'])
    emb_idx = ramp_index(cols['embleme'])
    Image.fromarray(np.where(ex['embleme'], emb_idx * 11, 0).astype('uint8')).save(OUT / 'masques' / f'{PFX}_embleme_crans.png')
    embleme = emblem_frames(emb_idx, ex['embleme'])
    lucioles = mote_frames(MOTES)
    feuilles = leaf_frames(leaf0, leaf_lab)
    hposes = halcyon_poses()
    for i, hp in enumerate(hposes):
        Image.fromarray(hp).save(OUT / 'poses' / f'{PFX}_fleur_halcyon_{i}.png')
    clumps = place_clumps(hposes, walk, ex)
    fleurs_h = flower_frames(hposes, clumps)
    petals, dropped = make_petals(clumps, ex)
    petales = petal_frames(petals)
    sheet_vegetation(hposes).save(OUT / 'review' / f'{PFX}_planche_vegetation.png')
    anim = {'fleurs_halcyon': fleurs_h, 'petales': petales, 'feuilles': feuilles, 'embleme': embleme, 'rayon': rayon, 'lucioles': lucioles}
    order_names = ['sol_complet'] + STATIC + ANIMS
    stack_named, layer_list = [], []
    for i, nm in enumerate(order_names):
        if nm in anim:
            frames, ticks = anim[nm], TK[nm]
            for tt, fr in enumerate(frames):
                Image.fromarray(fr).save(OUT / 'animation' / nm / f'{PFX}_{i:02d}_{nm}_f{tt:02d}.png')
            layer_list.append({'file': f'animation/{nm}/{PFX}_{i:02d}_{nm}_fNN.png', 'phases': len(frames), 'ticks': ticks})
        else:
            frames, ticks = [layers[nm]], 60
            Image.fromarray(layers[nm]).save(OUT / 'calques' / f'{PFX}_{i:02d}_{nm}.png')
            layer_list.append({'file': f'calques/{PFX}_{i:02d}_{nm}.png', 'phases': 1, 'ticks': 60})
        stack_named.append((nm, frames, ticks))
    blocked = cell_grid(~walk); gh_, gw_ = blocked.shape
    pxs = np.nonzero(walk[H - 8])[0]; med = int(np.median(pxs)) // 8
    ecol = min((c for c in range(gw_ - 1) if not blocked[gh_ - 2:, c:c + 2].any()), key=lambda c: abs(c - med))
    entry_px = [ecol * 8, H - 16]
    dys, dxs = np.nonzero(mouth)
    tx = int(round(dxs.mean())) // 8 * 8 - 8
    threshold_px = [tx, int(dys.max()) // 8 * 8]
    while blocked[threshold_px[1] // 8:threshold_px[1] // 8 + 2, threshold_px[0] // 8:threshold_px[0] // 8 + 2].any():
        threshold_px[1] += 8
    reach, explored = v1.reachable(blocked, (entry_px[1] // 8, entry_px[0] // 8), (threshold_px[1] // 8, threshold_px[0] // 8))
    assert reach, 'pas de chemin 16x16'

    def scene(tick):
        im = Image.new('RGBA', (W, H))
        for _, frames, ticks in stack_named:
            im.alpha_composite(Image.fromarray(frames[(tick // ticks) % len(frames)]))
        return im
    step = 7
    scenes = [scene(tk) for tk in range(0, LOOP_TICKS, step)]
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_t000.png')
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_animee.webp', save_all=True, append_images=scenes[1:],
                   duration=round(step * 1000 / 60), loop=0, lossless=True)
    col = scenes[0].copy(); ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    for y, x in zip(*np.nonzero(blocked)):
        dr.rectangle([x*8, y*8, x*8+7, y*8+7], fill=(220, 40, 40, 90))
    for (qx, qy), c in ((entry_px, (255, 230, 40, 255)), (threshold_px, (60, 220, 255, 255))):
        dr.rectangle([qx, qy, qx + 15, qy + 15], outline=c, width=2)
    col.alpha_composite(ov); col.save(OUT / 'review' / f'{PFX}_collisions_marqueurs.png')
    # Planche : rampe du rayon (22 crans) et formes des lucioles, x8.
    sheet = Image.new('RGBA', (22 * 24 + 16, 24 + 16 + 56), (47, 87, 55, 255)); d = ImageDraw.Draw(sheet)
    for i, c in enumerate(RAMP):
        d.rectangle([8 + i * 24, 8, 8 + i * 24 + 21, 31], fill=(*c, 255))
    for j, shape in enumerate(['point', 'croix']):
        spr = np.zeros((5, 5, 4), 'uint8')
        if shape == 'croix':
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                spr[2 + dy, 2 + dx] = (*GLOW, 255)
            spr[2, 2] = (*CORE, 255)
        else:
            spr[2, 2] = (*DOT, 255)
        sheet.alpha_composite(Image.fromarray(spr).resize((40, 40), Image.Resampling.NEAREST), (8 + j * 56, 44))
    sheet.save(OUT / 'review' / f'{PFX}_planche_poses.png')
    write_ora(OUT / f'{PFX}_entree_jardin_secret_calques.ora',
              {f'{i:02d}_{tn}' + ('_f00' if len(fr) > 1 else ''): fr[0] for i, (tn, fr, _) in enumerate(stack_named)})
    counts = ground_project([(tn.replace('_', ' ') + (f' {len(fr)} phases' if len(fr) > 1 else ''), fr, tk)
                             for tn, fr, tk in stack_named], blocked, entry_px, threshold_px, gfx, tools)
    fid = fidelity(a, ref)
    final_fid = {}
    for k, nm in (('herbe_claire', 'prairie'), ('herbe', 'ombres'), ('herbe_claire', 'herbe'), ('roche', 'rochers'),
                  ('fond', 'fond')):
        lay = layers[nm]; px = lay[lay[..., 3] == 255][:, :3].astype(float)
        sel = materials(px.reshape(-1, 1, 3))[k][:, 0]
        px = px[sel] if sel.sum() > 50 else px
        final_fid[nm] = {'matiere': k, 'rgb': [round(float(v), 1) for v in px.mean(0)],
                         'distance_rip': round(float(np.linalg.norm(px.mean(0) - np.array(fid[k]['rip_rgb']))), 1)}
    manifest = {
        'lot': 'entree_jardin_secret_sud_nord_v3', 'prefix': PFX, 'format': '4:3 vaste', 'size_px': [W, H],
        'grid_8px': [W // 8, H // 8], 'base': 'branche de session (EWC1 et ESN1 pour les utilitaires) ; aucun emprunt aux branches soeurs',
        'biome': 'jardin secret d EJS1, avec le temple miniature de Celebi sur la souche (demande de l utilisateur) ; EJS1 choisi par l agent',
        'method': 'textures canoniques = rendu genere REFERENCE : decor EJS1 + rip passes au generateur pour le temple ; '
                  'seule la zone du temple est collee sur le decor EJS1 ; temoin et sol complet d EJS1',
        'reference_da': {'file': REF.name, 'sha256': sha(REF),
                         'titre': 'Jardin secret (Explorers of Sky, nom de fichier ; scene non confirmee)'},
        'generation': GEN,
        'raw_inputs': [{'file': f'{g["lot"]}/bruts/{g["file"]}', 'sha256': sha(raw_path(g)),
                        'size': list(Image.open(raw_path(g)).size), 'ecarte': bool(g.get('ecarte'))} for g in GEN],
        'recalage': {**reg, 'zones': 'temoin : hors objets (ecart > 10) et hors zone collee, dilates de 4 px ; brut du temple : '
                                     'hors fenetre de la souche elargie de 20 px'},
        'temple': {'demande': 'Je veux un petit temple miniature qui tiens sur la buche celebi gardien secret',
                   'choix_agent_a_confirmer': ['nouvelle version EJS2, EJS1 intacte', 'la porte du temple devient l entree du donjon',
                                               'Celebi en embleme sur le fronton, pas de sprite'],
                   'fenetre_pleine_resolution': list(WIN), 'seuil_ecart': PASTE_DIFF,
                   'collage': 'composante principale de l ecart lisse 3 px > seuil dans la fenetre, fermee 3 px, trous bouches, '
                              'dilatee 2 px ; hors zone collee, decor EJS1 au pixel pres',
                   'embleme': {'loi': 'cran = clip(cran0 + round(3 (1 - cos(2 pi u / 24)) / 2)), u = min(t, 24 - t)', 'crans_max': EMBLEM_GLOW,
                               'couleurs': 'rampe EXACTE du rayon du rip', 'phases': PHASES, 'frame_length_ticks': TICKS}},
        'segmentation_mesures': seg,
        'fidelite_rip': {'methode': 'moyenne RGB par matiere, meme classifieur pixel sur le rip et sur le brut ; distance euclidienne ; seuil 35',
                         'brut': fid, 'calques_finaux': final_fid,
                         'sol_complet': round(float(np.linalg.norm(f.reshape(-1, 3).mean(0) - np.array(fid['herbe']['rip_rgb']))), 1),
                         'sol_complet_ecartes': {g['file']: round(float(np.linalg.norm(rgb(raw_path(g)).reshape(-1, 3).mean(0)
                                                                                      - np.array(fid['herbe']['rip_rgb']))), 1)
                                                 for g in GEN if g.get('ecarte')},
                         'rayon_lucioles': 'couleurs EXACTES du rip (test : sous-ensemble des couleurs du rip)'},
        'normalization': {'scale': JM.SCALE, 'scaled': [JM.SCALED_W, H], 'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
                          'methode': 'moyenne ponderee par classe (BOX), attribution exclusive par poids maximal',
                          'palettes': {g: {'calques': k, 'couleurs': n} for g, (k, n) in PALETTE_GROUPS.items()}},
        'segmentation': classify.__doc__.split('\n', 1)[1].strip(),
        'ombres': 'calque ombres = herbe du rendu assombrie au pied des haies, des arbres et des rochers (separee, pas inventee)',
        'layers': layer_list,
        'rayon': {'rampe': [list(c) for c in RAMP], 'rampe_source': 'rip, zone y < 95, x 130-280, verts du rayon par luminance',
                  'souffle_crans': BREATH, 'bords_attenues_crans': EDGE_STEPS, 'phases': PHASES, 'frame_length_ticks': TICKS,
                  'loi': 'cran = clip(cran0 + round(2 sin(2 pi t / 24)) x min(1, cran0 / 6))',
                  'origine': 'forme du rayon GENEREE ; couleurs EXACTES du rip ; souffle cree par nous'},
        'lucioles': {'lucioles': [list(mo) for mo in MOTES], 'montee_px_par_phase': MOTE_RISE, 'couleurs': [list(DOT), list(GLOW), list(CORE)],
                     'formes': 'point 1 px (phases 0-2, 21-23 et 2 phases sur 4), croix 3 x 3 (2 phases sur 4)',
                     'phases': PHASES, 'frame_length_ticks': TICKS,
                     'origine': 'couleurs EXACTES du rayon du rip ; formes, trajets et cadence crees par nous'},
        'feuilles': {'zones': list(LEAF_ZONES), 'amas': int(leaf_lab.max()), 'pixels_deplaces': int((leaf_lab > 0).sum()),
                     'selection': 'composantes 8-connexes de 2 a 12 px, plus claires que la moyenne locale 7 x 7 (+ 14 de luminance), '
                                  'a l interieur du feuillage erode de 3 px, un amas sur trois (hachage de la position)',
                     'houle': 'dx = round(0,9 sin(2 pi (t / 8 + x / 220))) - (valeur a t = 0), meme loi decalee d un quart de periode pour dy',
                     'amplitude_px': LEAF_AMP, 'longueur_onde_px': LEAF_WAVE, 'phases': LEAF_PHASES, 'frame_length_ticks': LEAF_TICKS,
                     'sha256_origine_quantifie': leaf_origin, 'phase_0': 'calque fixe + feuilles phase 0 = calque d origine (test, sha256)',
                     'origine': 'pixels EXACTS du decor genere ; houle creee par nous'},
        'fleurs_halcyon': {'source': 'Palikadude/Halcyon, Vast_Steppe_Flower_Animations (commit 1522c7a8b7a34d70078e11ed605b21d563b0dc51)',
                           'fichier_local': 'source/amp_plains_fleurie_v1/references/Vast_Steppe_Flower_Animations.png',
                           'sha256_source': sha(FLOWER_ATLAS), 'dessins': 3, 'taille': [24, 24], 'sequence': FLOWER_SEQ,
                           'frame_length_ticks': FLOWER_TICKS, 'phases': len(FLOWER_SEQ), 'touffes': [list(c) for c in clumps],
                           'decalage_de_phase': 'touffe i : sequence decalee de i % 4',
                           'origine': 'pixels et sequence NATIFS Halcyon (attribution Palikadude et artistes) ; placement cree par nous, '
                                      'aucune redistribution generale deduite'},
        'petales': {'petales': [list(p_) for p_ in petals], 'ecartes': dropped, 'couleurs': {k_: list(v_) for k_, v_ in PETAL_COLORS.items()},
                    'formes': {k_: v_ for k_, v_ in PETAL_SHAPES.items()}, 'phases': PETAL_PHASES, 'frame_length_ticks': PETAL_TICKS,
                    'trajet': 'x = x0 + round(1,1 dir u) + round(2 sin(2 pi u / 12 + decalage)), y = y0 + round(0,9 u), u = vie (0-23)',
                    'origine': 'couleurs EXACTES des fleurs du rip (zone y 105-200) ; formes, trajets et cadence crees par nous'},
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'entry_px': entry_px, 'threshold_px': threshold_px, 'path_found_16x16': reach, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si > 25 % hors praticable (prairie, herbe, ombres, fleurs, marches et parvis relies au bord sud)',
                   'seuil': 'premiere case 2 x 2 libre sous la porte du temple'},
        'pmdo': {'target': '0.8.12', 'asset': ASSET, 'namespace': NAMESPACE, 'tiles_per_bank': counts, 'banks': list(counts),
                 'runtime_tested': False, 'warp': 'aucun'},
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    print(json.dumps({'entry': entry_px, 'threshold': threshold_px, 'blocked': int(blocked.sum()),
                      'walkable': int((~blocked).sum()), 'seg': seg, 'reg': reg,
                      'px': {k: int(v.sum()) for k, v in ex.items()},
                      'fidelite': {k: v['distance'] for k, v in fid.items()},
                      'final': {k: v['distance_rip'] for k, v in final_fid.items()}, 'tiles': counts}, indent=1))


if __name__ == '__main__':
    build()
