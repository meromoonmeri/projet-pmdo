"""Zone Plage aux récifs étoilés V1 (ZPR1) — crique tropicale jour + nuit, 768 x 576 px (96 x 72 cases).

Demande : session parente arena/01a0fd01 (plan, géométrie, terre/ciel-mer jour, planches récifs) ; poursuite
session arena/01a0fdc2 : variante nuit, sol complet, build multicalque, Grounds jour + nuit, tests, aperçu.
Références DA : plage_td_scene.png / plage_td_marees.png (sable, rochers, lagon), arene_plage_pmdsky_x2.png,
nuit_pmdsky_lune_x3.png (lune, étoiles, reflet). Noms de lieu NON confirmés (titres d'inventaire).
Méthode « textures canoniques » = rendu généré RÉFÉRENCÉ (rips passés au générateur en images=) :
- terre_jour.png : terre sur magenta (baie large, essai 4 retenu) ;
- ciel_mer_jour.png : décor jour complet (retouche : magenta remplacé ; le générateur a avancé le lagon sur le
  sable mouillé, ~30-60 px : la côte de référence est celle du décor, pas le magenta) ;
- ciel_mer_nuit.png : décor nuit complet (lune, étoiles, reflet ; même avancée du lagon) ;
- recifs_roches.png : planche de 7 rochers émergés ; recifs_coraux.png : planche de 12 cases (la cervelle
  magenta, de la couleur du fond, est indétourable : écartée) ;
- sol_complet.png : sable seul (ton à 2,7 du sable du décor).
Géométrie : terre/mer/ciel depuis le magenta + le lagon peint ; matières terre segmentées sur le décor jour ;
terre nuit = terre jour recolorée (offsets médians par matière vers les tons du brut nuit : géométrie identique).
Calques jour (14 + Top) : ciel, mer, houle, scintillements, recifs, coraux, sol_complet, sable, mares, details,
ecume, rochers, palmiers, herbes. Nuit (+3) : lune, etoiles, reflets. Boucle 12 x 10 = 120 ticks = 2 s.
Marqueurs : entrance au sud, sur le chemin. Aucun warp, aucune sortie (zone, pas entrée ni fin).
Lancer : .venv/bin/python source/zone_plage_recifs_etoiles_v1/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
LOT = 'source/zone_plage_recifs_etoiles_v1'
OUT = R / 'renders/zone_plage_recifs_etoiles_v1'
STAGE = R / '.cache/zone_plage_recifs_etoiles_v1/zone_plage_recifs_etoiles'
NAMESPACE = 'zone_plage_recifs_etoiles'
ASSET = {'jour': 'zpr1_plage_recifs_jour', 'nuit': 'zpr1_plage_recifs_nuit'}
PFX = 'ZPR1'
W, H = 768, 576
SRC = (1200, 896)
PHASES, TICKS = 12, 10
LOOP_TICKS = 120
YH_J, YH_N = 237, 240                      # horizons jour / nuit (mesurés par profil, ±5 du journal)
YH_TOL = 5
SPRITE_K = 0.5                             # récifs : ×(SCALE×0.5) ≈ 0,321 (cohérence d'échelle des rochers)
DX_SEQ = [0, 1, 2, 3, 4, 5, 4, 3, 2, 1, 0, -1]   # houle : oscillation triangulaire fermée (pas de 1 partout)
BLINK = [0, 0, 0, 1, 2, 2, 1, 0, 0, 0, 0, 0]    # scintillement : 0 invisible, 1 réduit, 2 plein
STAR_SEQ = [2, 2, 1, 0, 0, 0, 1, 2, 2, 1, 0, 0] # étoiles du ciel : clignotement déphasé
assert len(DX_SEQ) == len(BLINK) == len(STAR_SEQ) == PHASES
GEN = [
    {'file': 'terre_jour.png', 'taille': [1200, 896], 'essais': 4,
     'images': ['references/guide_plage_x4_3.png', 'references/plage_td_scene.png',
                'references/arene_plage_pmdsky_x2.png'],
     'role': 'terre du jour sur magenta (essai 4 : baie large conforme au plan)',
     'prompt': 'voir generation.json (journal versionné)'},
    {'file': 'ciel_mer_jour.png', 'taille': [1200, 896], 'essais': 2,
     'images': ['bruts/terre_jour.png', '../zone_reveil_prairie_horizon_v2/bruts/ciel_mer_jour.png',
                'references/plage_td_marees.png'],
     'role': 'décor jour complet ; horizon rangée 237 ; lagon avancé sur le sable (~30-60 px)',
     'prompt': 'voir generation.json'},
    {'file': 'ciel_mer_nuit.png', 'taille': [1200, 896], 'essais': 1,
     'images': ['bruts/ciel_mer_jour.png', 'references/nuit_pmdsky_lune_x3.png'],
     'role': 'décor nuit complet (lune, étoiles, reflet) ; horizon rangée 240',
     'prompt': 'voir generation.json'},
    {'file': 'recifs_roches.png', 'taille': [1200, 896], 'essais': 1,
     'images': 'non journalisées par la session parente (commit 23cbfd1a)',
     'role': 'planche de 7 rochers de récif émergés sur magenta', 'prompt': None},
    {'file': 'recifs_coraux.png', 'taille': [1200, 896], 'essais': 1,
     'images': 'non journalisées par la session parente (commit 23cbfd1a)',
     'role': 'planche de 12 coraux sur magenta (cervelle magenta indétourable : écartée)',
     'prompt': None},
    {'file': 'sol_complet.png', 'taille': [1200, 896], 'essais': 1, 'images': ['bruts/terre_jour.png'],
     'role': 'sable seul (ton à 2,7 du sable du décor)', 'prompt': 'voir generation.json'},
]
# Sprites des planches : (nom, x0, y0, x1, y1) en pleine résolution.
ROCK_BOX = {'triple': (807, 66, 1112, 311), 'dome': (439, 88, 613, 236), 'double': (98, 96, 242, 210),
            'colonne': (68, 317, 261, 567), 'chapelet': (353, 370, 699, 536), 'dalle': (61, 666, 568, 840),
            'plateau': (725, 520, 1168, 836)}
CORAL_BOX = {'cervelle_or': (36, 52, 262, 255), 'branchu_or': (316, 25, 585, 273),
             'eventail': (622, 37, 877, 267), 'tubes': (952, 36, 1148, 267), 'coupe': (8, 361, 290, 533),
             'anemones': (316, 331, 585, 563), 'branchu_rouge': (627, 329, 872, 567),
             'branchu_bleu': (56, 652, 242, 840), 'massif_mixte': (319, 633, 579, 858),
             'eponges': (678, 676, 831, 818), 'oursin': (1036, 649, 1177, 780),
             'etoile_gde': (923, 728, 1047, 836), 'etoile_pte': (953, 672, 1031, 736)}
CORAL_DROP = {'cervelle_magenta': 'case x[900,1200] y[330,560] : ~94 % des pixels passent le test magenta '
              '(rose-mauve du fond) : indétourable'}
CORAL_SKIP = {'etoile_gde': 'doublon des étoiles de mer du décor (déjà 2 sur le sable)',
              'etoile_pte': 'doublon des étoiles de mer du décor'}
# Placement final (x, y du coin haut-gauche, espace 768 x 576). Première passe : mer entre y~155 et ~390,
# colonne du reflet de lune (x 180-355, y < 330) évitée pour les gros rochers.
REEF_PLACE = {'dalle': (408, 205), 'dome': (108, 228), 'double': (618, 258), 'triple': (455, 168),
              'colonne': (52, 282),
              'branchu_or': (386, 318), 'eventail': (238, 322), 'tubes': (528, 326),
              'cervelle_or': (128, 336), 'massif_mixte': (598, 318), 'eponges': (438, 348), 'oursin': (318, 356)}
PALETTE_GROUPS = {'ciel': (['ciel'], 24), 'mer': (['mer'], 40), 'terre': (['sol_complet', 'sable'], 96),
                  'rochers': (['rochers'], 48), 'palmiers': (['palmiers', 'herbes'], 48),
                  'mares_details': (['mares', 'details'], 32), 'recifs': (['recifs', 'coraux'], 96),
                  'astre': (['lune'], 16)}


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


V1 = loadmod('ewc1_build', R / 'source/entree_waterfall_cave_sud_nord_v1/build.py')
JM, BM = V1.JM, V1.BM
assert (JM.W, JM.H, JM.SRC, BM.W, BM.H) == (W, H, SRC, W, H)
keep_large, down_class, down_full, rgba = V1.keep_large, V1.down_class, V1.down_full, V1.rgba
place, cell_grid = BM.place, BM.cell_grid
SCALE = JM.SCALE


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rgb(p):
    return np.array(Image.open(p).convert('RGB')).astype(int)


def lum_of(a):
    return a[..., :3].astype(float) @ [.299, .587, .114]


def mag_of(a):
    r, g, b = a.transpose(2, 0, 1)
    return (r - g > 60) & (b - g > 60)


def close_(m, it):
    p = it + 1
    return nd.binary_closing(np.pad(m, p, mode='edge'), iterations=it)[p:-p, p:-p]


def open_(m, it):
    p = it + 1
    return nd.binary_opening(np.pad(m, p, mode='edge'), iterations=it)[p:-p, p:-p]


def horizon_of(a, y0=200, y1=280, x0=400, x1=800):
    """Rangée de l'horizon : plus fort gradient vertical de luminance sur la bande centrale."""
    lum = lum_of(a)[y0:y1, x0:x1]
    prof = np.abs(np.diff(lum.mean(1)))
    return y0 + int(np.argmax(prof)) + 1


# ---------------------------------------------------------------- fidélité aux références (même classifieur des deux côtés)
def materials(a):
    a = a.astype(float); r, g, b = a[..., 0], a[..., 1], a[..., 2]; lum = lum_of(a)
    sable = (r > 200) & (g > 170) & (b > 90) & (r > g) & (g > b + 40)
    roche = (r > b + 25) & (g - b < 30) & (lum < 235) & (lum > 50)
    palmier = (g > r + 10) & (g > b + 25) & (lum > 40)
    return {'sable': sable, 'roche': roche, 'palmier': palmier}


def fidelity(decor, ref):
    fr, fd = materials(ref), materials(decor); out = {}
    for k in fr:
        if not fr[k].any() or not fd[k].any():
            out[k] = {'distance': None}; continue
        mr, md = ref[fr[k]].mean(0), decor[fd[k]].mean(0)
        out[k] = {'rip_rgb': [round(float(v), 1) for v in mr], 'decor_rgb': [round(float(v), 1) for v in md],
                  'distance': round(float(np.linalg.norm(mr - md)), 1)}
    return out


# ---------------------------------------------------------------- géographie pleine résolution (magenta + lagon peint)
def classify_geo(a_dec, mag, yh, teal):
    """ciel = magenta au-dessus de l'horizon ; mer = magenta sous l'horizon + lagon peint relié ; terre = reste."""
    yy = np.mgrid[:a_dec.shape[0], :a_dec.shape[1]][0]
    ciel = mag & (yy < yh)
    sea_mag = mag & (yy >= yh)
    lag = close_(teal & ~mag & (yy >= yh) & (yy < 680), 5)
    lab, _ = nd.label(lag)
    ids = [i for i in np.unique(lab[nd.binary_dilation(sea_mag, iterations=3)]) if i]
    sea = sea_mag | np.isin(lab, ids)
    sea &= (yy >= yh)
    terre = ~(ciel | sea)
    return dict(ciel=ciel, mer=sea, terre=terre)


# ---------------------------------------------------------------- matières de la terre (sur le décor jour, masque terre)
def classify_land(a, terre, mer):
    r, g, b = a.transpose(2, 0, 1); lum = lum_of(a)
    roche0 = terre & (r > b + 25) & (g - b < 30) & (lum < 235)
    roche0 = close_(roche0, 2)
    lab, n = nd.label(roche0); sz = nd.sum(np.ones_like(lab), lab, range(1, n + 1))
    big = np.argsort(sz)[::-1][:2] + 1
    prom = np.isin(lab, big)
    rochers, coquilles = prom.copy(), np.zeros_like(prom)
    prom_dil = nd.binary_dilation(prom, iterations=15)
    for i in range(1, n + 1):
        if i in big:
            continue
        m = lab == i
        if 200 <= m.sum() <= 6000 and not (m & nd.binary_dilation(prom, iterations=5)).any() \
                and (m & prom_dil).sum() / m.sum() <= 0.6 and np.median(a[m][:, 2]) > 100:
            coquilles |= m                                     # coquille : petite, isolée, dans le sable, rose (b>100)
            continue
        rochers |= m                   # défaut = roche (petits rochers, bois flotté allongé, reflets, bruit adjacent)
    rest = terre & ~roche0
    vert = rest & (g > r + 10) & (g > b + 25) & (lum > 40)
    labv, nv = nd.label(vert); szv = nd.sum(np.ones_like(labv), labv, range(1, nv + 1))
    frondes = np.zeros_like(prom); herbes = np.zeros_like(prom)
    rock_dil = nd.binary_dilation(roche0, iterations=10)
    for i in range(1, nv + 1):
        m = labv == i
        if szv[i - 1] > 800:
            frondes |= m
        elif szv[i - 1] >= 100:
            if (m & rock_dil).sum() / m.sum() > 0.7:
                rochers |= m                                   # reflets verts pris dans la roche
            else:
                herbes |= m
    cyan = rest & (b > r + 30) & (g > r + 10) & (lum > 90)
    labc, nc = nd.label(cyan)
    mares = np.zeros_like(prom)
    for i in range(1, nc + 1):
        m = labc == i
        if 800 < m.sum() < 3000:
            mares |= nd.binary_dilation(m, iterations=8) & terre & ~roche0
    orange = rest & (r > 200) & (g > 80) & (g < 190) & (b < 130) & (r - g > 40)
    etoiles = np.zeros_like(prom)
    rock_dil2 = nd.binary_dilation(roche0, iterations=10)
    labo, no = nd.label(orange & ~nd.binary_dilation(mer, iterations=3))
    for i in range(1, no + 1):          # le sable mouillé (relié à la mer) reste du sable ; les reflets orange des
        m = labo == i                   # rochers (entourés de roche) retournent à la roche
        if 200 <= m.sum() <= 1200:
            if (m & rock_dil2).sum() / m.sum() > 0.3:
                rochers |= m
            else:
                etoiles |= m
    brun = rest & (r > g + 25) & (g > b + 25) & (lum > 90) & (lum < 210) & ~vert
    labb, nb = nd.label(brun); szb = nd.sum(np.ones_like(labb), labb, range(1, nb + 1))
    troncs = np.zeros_like(prom)
    above_green = nd.binary_dilation(frondes, iterations=40)
    for i in range(1, nb + 1):
        if szb[i - 1] < 500 or szb[i - 1] > 8000:
            continue
        m = labb == i; ys, xs = np.nonzero(m)
        if ys.max() - ys.min() > (xs.max() - xs.min()) and (m & above_green).any():
            troncs |= m
    palmiers = frondes | troncs
    details = coquilles | etoiles
    sable = terre & ~rochers & ~palmiers & ~herbes & ~mares & ~details
    return dict(sable=sable, mares=mares, details=details, rochers=rochers, palmiers=palmiers,
                herbes=herbes, coquilles=coquilles, etoiles=etoiles)


# ---------------------------------------------------------------- sprites des planches (détourage + réduction BOX + palette)
def down_sprite(path, box, scale):
    a = rgb(path); r, g, b = a.transpose(2, 0, 1)
    x0, y0, x1, y1 = box
    m = ~(((r - g > 40) & (b - g > 40)))[y0:y1, x0:x1]
    m = open_(m, 1)
    crop = a[y0:y1, x0:x1].astype(np.float32)
    h, w = m.shape; nh, nw = max(1, round(h * scale)), max(1, round(w * scale))
    mm = np.array(Image.fromarray(m.astype(np.float32), 'F').resize((nw, nh), Image.Resampling.BOX)) > 0.25
    cols = np.stack([np.array(Image.fromarray((crop[..., c] * m).astype(np.float32), 'F')
                               .resize((nw, nh), Image.Resampling.BOX)) for c in range(3)], -1)
    den = np.array(Image.fromarray(m.astype(np.float32), 'F').resize((nw, nh), Image.Resampling.BOX))
    cols = np.clip(np.round(cols / np.maximum(den, 1e-6)[..., None]), 0, 255).astype('uint8')
    pal = np.unique(crop[m][:, :3].reshape(-1, 3).astype('uint8'), axis=0).astype(float)
    cols = pal[((cols.astype(float)[..., None, :] - pal[None, None]) ** 2).sum(-1).argmin(-1)].astype('uint8')
    out = np.zeros((nh, nw, 4), 'uint8'); out[..., :3] = cols; out[..., 3] = 255; out[~mm] = 0
    return out, {'pixels': int(m.sum()), 'taille_finale': [nw, nh], 'couleurs': int(len(pal))}


# ---------------------------------------------------------------- quantification par groupe + palette réutilisable
def quantize_pal(layers, n):
    opaque = np.concatenate([l[l[..., 3] == 255][:, :3] for l in layers.values()])
    q = Image.fromarray(opaque.reshape(-1, 1, 3)).quantize(colors=n, method=Image.Quantize.MEDIANCUT,
                                                           dither=Image.Dither.NONE)
    return np.array(q.getpalette()[:n * 3], 'uint8').reshape(-1, 3), q


def snap_to(a, q):
    pal = np.array(q.getpalette()[:len(q.getpalette()) // 3 * 3], 'uint8')
    pal = pal.reshape(-1, 3).astype(float)
    out = a.copy(); m = a[..., 3] == 255
    if m.any():
        out[..., :3][m] = pal[((a[..., :3][m].astype(float)[:, None, :] - pal[None]) ** 2).sum(-1).argmin(-1)]
    out[~m] = 0
    return out


def quantize_group_pal(layers, n):
    pal, q = quantize_pal(layers, n)
    return {k: snap_to(v, q) for k, v in layers.items()}, pal


# ---------------------------------------------------------------- ORA
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


# ---------------------------------------------------------------- Ground PMDO 0.8.12 (deux ambiances dans un seul projet)
def ground_project(stacks, blocked, entry_px, gfx, tools):
    if STAGE.exists():
        shutil.rmtree(STAGE)
    with zipfile.ZipFile(R / 'mod_metano_expeditions_pmdo_0812.zip') as z:
        tpl = json.loads(z.read('metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground'))
    counts_all, banks_all = {}, []
    for amb, (asset, stack, title, comment) in stacks.items():
        o = json.loads(json.dumps(tpl['Object'])); gw, gh = W // 8, H // 8; layers = []
        for i, (titre, frames, ticks) in enumerate(stack):
            bank = gfx.TileBank(f'{PFX}{amb[0].upper()}_{i:02d}_{titre.split()[0].upper()}')
            bank.ids[bytes(256)] = (0, 0); bank.data[(0, 0)] = bytes(256)

            def cell(x, y, frames=frames, bank=bank):
                fs = []
                for a in frames:
                    f = bank.add(Image.fromarray(a[y*8:y*8+8, x*8:x*8+8]), x, y)
                    fs.append(f if f else {'Sheet': bank.name, 'TexLoc': {'X': 0, 'Y': 0}})
                if all(f['TexLoc'] == {'X': 0, 'Y': 0} for f in fs):
                    return []
                return [fs[0]] if all(f == fs[0] for f in fs) else fs
            layers.append(gfx.layer(f'{i:02d} {titre}', gw, gh, cell, ticks)); banks_all.append(bank)
        layers.append(gfx.layer(f'{len(layers):02d} Vos elements avant-plan (Top)', gw, gh, draw=4))
        o.update(Name={'DefaultText': title, 'LocalTexts': {}}, AssetName=asset, Released=False, TexSize=1,
                 Music='', EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0}, ActiveChar=None, Status={},
                 Layers=layers,
                 Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []}, Comment=comment)
        o['obstacles'] = [[{'Bounds': {'X': x*8, 'Y': y*8, 'Width': 8, 'Height': 8}, 'Tags': int(blocked[y, x])}
                           for y in range(gh)] for x in range(gw)]
        o['Entities'] = [{'Name': 'Entrees et vos acteurs', 'Visible': True, 'MapChars': [], 'GroundObjects': [],
                          'Spawners': [], 'Markers': [
                              {'EntName': 'entrance', 'Direction': 4, 'EntEnabled': True, 'triggerType': 0,
                               'Collider': {'X': entry_px[0], 'Y': entry_px[1], 'Width': 16, 'Height': 16}}]}]
        o['Decorations'] = [{'Name': 'Vos decorations', 'Layer': 2, 'Visible': True, 'Anims': []}]
        tpl['Version'] = '0.8.12.0'
        doc = {'Version': tpl['Version'], 'Object': o}
        gfx.save(STAGE / f'Data/Ground/{asset}.rsground', json.dumps(doc, ensure_ascii=False,
                                                                     separators=(',', ':')).encode())
        gfx.save(STAGE / f'Data/Script/{NAMESPACE}/ground/{asset}/init.lua',
                 f'-- {asset} : base d edition, aucun warp.\nlocal {asset} = {{}}\nreturn {asset}\n'.encode())
        counts_all[amb] = {}
    for bank in banks_all:
        bank.write(STAGE / f'Content/Tile/{bank.name}.tile')
    nodes = {}
    for p in sorted((STAGE / 'Content/Tile').glob('*.tile')):
        with p.open('rb') as f:
            nodes[p.stem] = tools.read_node(f)
    (STAGE / 'Content/Tile/index.idx').write_bytes(tools.encode_index(nodes))
    counts_all = {b.name: len(b.data) for b in banks_all}
    ident = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/meromoonmeri/guilde-treehouse-pmd/' + NAMESPACE)
    (STAGE / 'Mod.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Plage aux recifs etoiles jour/nuit 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : crique tropicale generee au format 4:3 (refs plage TD, arene plage Sky, nuit PMD), recifs et coraux, mer animee, jour et nuit. Pas une aventure jouable.</Description>
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
    return counts_all


# ---------------------------------------------------------------- main
def build():
    gfx = loadmod('pmdo_codec', R / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
    v1 = loadmod('esn1', R / 'source/entree_sud_nord_generee_v1/build.py')
    if OUT.exists():
        for d in ['calques', 'animation', 'poses', 'masques', 'review']:
            shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['calques/jour', 'calques/nuit', 'animation/jour/houle', 'animation/jour/scintillements',
              'animation/jour/ecume', 'animation/nuit/houle', 'animation/nuit/scintillements',
              'animation/nuit/ecume', 'animation/nuit/reflets', 'animation/nuit/etoiles', 'poses', 'masques',
              'review']:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    t = rgb(RAW / 'terre_jour.png'); jd = rgb(RAW / 'ciel_mer_jour.png'); nd_ = rgb(RAW / 'ciel_mer_nuit.png')
    f = rgb(RAW / 'sol_complet.png')
    assert t.shape[:2] == jd.shape[:2] == nd_.shape[:2] == f.shape[:2] == (SRC[1], SRC[0])
    yh_j, yh_n = horizon_of(jd), horizon_of(nd_)
    assert abs(yh_j - YH_J) <= YH_TOL and abs(yh_n - YH_N) <= YH_TOL, (yh_j, yh_n)
    mag = mag_of(t)
    lumj = lum_of(jd); rj, gj, bj = jd.transpose(2, 0, 1)
    teal_j = (gj > rj - 10) & (bj > rj - 20) & (lumj > 150)
    gj_ = classify_geo(jd, mag, yh_j, teal_j)
    lumn = lum_of(nd_); rn, gn, bn = nd_.transpose(2, 0, 1)
    teal_n = (bn > rn + 5) & (lumn > 40) & (lumn < 130)
    gn_ = classify_geo(nd_, mag, yh_n, teal_n)
    lag_j = int((gj_['mer'] & ~mag).sum()); lag_n = int((gn_['mer'] & ~mag).sum())
    assert 15000 < lag_j < 55000 and 15000 < lag_n < 55000, (lag_j, lag_n)  # nuit : + frange sombre du rivage
    m = classify_land(jd, gj_['terre'], gj_['mer'])
    order = ['sable', 'mares', 'details', 'rochers', 'palmiers', 'herbes']
    ex, cols = down_class(jd, m, order)
    layers_j = {'sol_complet': rgba(down_full(f), down_class(jd, {'t': gj_['terre']}, ['t'])[0]['t'])}
    for k in order:
        layers_j[k] = rgba(cols[k], ex[k])
    for k, v in ex.items():
        Image.fromarray((v * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_{k}.png')
    vis = np.zeros((H, W, 3), 'uint8') + 15
    for k, c in [('sable', (240, 230, 150)), ('mares', (80, 200, 230)), ('details', (250, 140, 200)),
                 ('rochers', (180, 70, 60)), ('palmiers', (40, 180, 50)), ('herbes', (120, 230, 120))]:
        vis[ex[k]] = c
    Image.fromarray(vis).save(OUT / 'review' / f'{PFX}_seg_terre.png')
    comp = Image.new('RGBA', (W, H))
    for k in ['sol_complet'] + order:
        comp.alpha_composite(Image.fromarray(layers_j[k]))
    comp.save(OUT / 'review' / f'{PFX}_terre_jour.png')
    print(json.dumps({'horizons': [yh_j, yh_n], 'lagon_j': lag_j, 'lagon_n': lag_n,
                      'masses': {k: int(v.sum()) for k, v in ex.items()}}, indent=1))


if __name__ == '__main__':
    build()
