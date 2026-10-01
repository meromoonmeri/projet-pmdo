"""Fin Mt. Thunder V2 (FTN1) — sommet d'orage, arène ronde et nid de pierre, 4:3 (768 x 576 px, 96 x 72 cases).

Demande : « Poursuis le projet, on va continuer avec la méthode création de map, lis les read me, outil générateur
d'image multicalque etc. » (1er octobre 2026). Fin de donjon qui prolonge l'entrée EMT1 (Mt. Thunder). Portée choisie
avec l'utilisateur parmi les fins restantes (les sœurs 01a0ed06, 01a0eecd et 01a0ef89 ont déjà une FTH1 non fusionnée :
rien n'en est repris, préfixe distinct FTN1).
Référence : `Game Boy Advance - Pokemon Mystery Dungeon_ Red Rescue Team - Dungeon Boss Rooms - Mt. Thunder.png`
(432 x 498 : scène y < 352 ; planche des éclairs, de l'arc « Flash » et des couleurs Normal / Fading dessous).
Méthode « textures canoniques » = rendu généré RÉFÉRENCÉ (rip passé au générateur en images=) :
- decor.png : arène ronde fermée par des falaises, nid de pierre plein au nord, sans bouche (1200 x 896) ;
- sol_complet.png : sable seul.
Calques : sol complet, sable, cailloux, pics, falaise (couronne de roche de l'arène), nid (pilier de pierre au nord),
ciel, nuages, lueurs, éclairs. Pas de calque de profondeur ni de seuil : la fin n'a pas de bouche.
Animations (boucles fermées, 48 x 5 ticks = 4 s), mêmes lois que l'entrée : l'arc « Flash » (lueurs) et les 4 éclairs
(pixels EXACTS de la planche, Normal 2 phases puis Fading 2 phases). La fin est plus orageuse que l'entrée : 8 frappes
par boucle, une toutes les 6 phases.
Marqueurs : entrance (sud), boss (case 2 x 2 libre la plus proche du centre de gravité du sol praticable), objectif
(case libre la plus haute de la colonne centrale, au pied du nid). Aucune sortie, aucun warp.
Lancer : .venv/bin/python source/fin_mt_thunder_v2/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
REF_NAME = 'Game Boy Advance - Pokemon Mystery Dungeon_ Red Rescue Team - Dungeon Boss Rooms - Mt. Thunder.png'
REF = R / REF_NAME
REF_SCENE_H = 352                          # la scène s'arrête en y = 352 ; en dessous, planche des éclairs sur noir
OUT = R / 'renders/fin_mt_thunder_v2'
STAGE = R / '.cache/fin_mt_thunder_v2/fin_mt_thunder'
NAMESPACE = 'fin_mt_thunder'
ASSET = 'ftn1_fin_mt_thunder'
PFX = 'FTN1'
W, H = 768, 576
SRC = (1200, 896)
PHASES, TICKS = 48, 5
LOOP_TICKS = 240
LOT = 'source/fin_mt_thunder_v2'
GEN = [
    {'file': 'decor.png', 'images': [REF_NAME], 'prompt':
     'Use EXACTLY the same textures, palette and pixel-art style as the top part of the reference image (Pokemon Mystery '
     'Dungeon Mt. Thunder summit): same pale yellow sandy ground with tiny grey pebbles, same brown rocky cliff edges '
     'with cracks, same small pointed tan rock spikes, same scalloped storm clouds in grey-purple tones (darker '
     'purple-grey clouds higher up, light grey and white clouds lower down), same dark grey storm sky. Make a NEW, '
     'larger top-down map of the very top of the mountain. WIDE LANDSCAPE 4:3, zoomed out so the summit feels vast. '
     'Layout: the player arrives at the SOUTH (bottom edge center) on a narrow sandy mountain ridge path rising out of '
     'the clouds; the path climbs north and opens into one big round-ish sandy summit arena, almost circular, fully '
     'edged all around by brown rocky cliffs, with a ring of pointed rock spikes and a few pebbles; at the NORTH (top '
     'center) the arena meets a tall solid brown rock crag shaped like a raised stone nest platform, solid rock with NO '
     'opening and NO dark hole, with a flat sandy ledge at its foot. A sea of scalloped storm clouds fills the left and '
     'right sides and the bottom corners; dark storm sky at the top corners. No lightning, no characters, no text, no '
     'UI, no border.',
     'essais': 'premier essai ; format 1200 x 896 d\'emblee (leçon de FST1 : « boss » et « cave » evites dans le prompt)'},
    {'file': 'sol_complet.png', 'images': [REF_NAME], 'prompt':
     "Fill the ENTIRE image edge to edge with only the pale yellow sandy ground texture from the reference image's "
     'summit plateau: same pale yellow sand colour, same subtle pixel-art speckle texture and faint darker patches, '
     'keep the texture detail. No pebbles, no rocks, no cliffs, no clouds, no dark areas. Wide landscape 4:3.',
     'essais': 'premier essai'},
]
# ---- Planche du rip (sous la scène) : éclairs d'une seule couleur (240,240,0), arc Flash (240,240,128).
BOLTS = {1: (372, 443, 121, 129), 2: (372, 436, 169, 185), 3: (372, 498, 219, 243), 4: (372, 475, 284, 307)}  # y0,y1,x0,x1
FLASH_BOX = (393, 401, 15, 55)
SWATCH = {'normal': ((420, 55), (420, 72)), 'fading': ((437, 55), (437, 72))}   # (pâle, vif) : centres des pastilles
# ---- Éclairs : (éclair, miroir, x gauche, y haut, décalage de phase) en coordonnées finales.
STRIKES = [(1, False, 60, 70, 0), (3, True, 690, 120, 6), (2, False, 100, 260, 12), (4, True, 665, 300, 18),
           (3, False, 30, 380, 24), (2, True, 715, 40, 30), (4, False, 40, 110, 36), (2, True, 690, 430, 42)]
CORE_OPEN, CORE_BACK = 9, 7                # noyau du sol praticable (voir build)
NORMAL_PH, FADING_PH = 2, 2                # phases locales 0-1 : Normal, 2-3 : Fading, 4-47 : rien


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


V1 = loadmod('ewc1_build', R / 'source/entree_waterfall_cave_sud_nord_v1/build.py')     # utilitaires génériques
JM, BM = V1.JM, V1.BM
assert (JM.W, JM.H, JM.SRC) == (W, H, SRC)
keep_large, cell_grid, close_ = V1.keep_large, V1.cell_grid, V1.close_
down_class, down_full, rgba, quantize_group = V1.down_class, V1.down_full, V1.rgba, V1.quantize_group
PALETTE_GROUPS = {'sable': (['sol_complet', 'sable'], 32), 'roche': (['cailloux', 'pics', 'falaise', 'nid'], 96),
                  'orage': (['ciel', 'nuages'], 32)}
STATIC = ['sable', 'cailloux', 'pics', 'falaise', 'nid', 'ciel', 'nuages']
ANIMS = ['lueurs', 'eclairs']


def open_(m, it):
    p = it + 1
    return nd.binary_opening(np.pad(m, p, mode='edge'), iterations=it)[p:-p, p:-p]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rgb(p):
    return np.array(Image.open(p).convert('RGB')).astype(int)


def lum_of(a):
    return a[..., :3].astype(float) @ [.299, .587, .114]


# ---------------------------------------------------------------- fidélité au rip (même classifieur des deux côtés)
def materials(a):
    """Sable jaune pâle, roche brune, et gris de l'orage PAR TON (ciel < 90 <= nuages sombres < 170 <= nuages clairs) :
    les nuages sont des tons discrets (64,56,64) ... (240,240,240) et une moyenne unique dépend des proportions."""
    a = a.astype(float); r, g, b = a[..., 0], a[..., 1], a[..., 2]; lum = lum_of(a); sat = a.max(-1) - a.min(-1)
    sable = (r > 200) & (g > 180) & (r - b > 60)
    grey = (sat < 30) & (lum > 20)
    return {'sable': sable, 'roche': (r > g) & (g > b) & (r - b > 25) & (lum < 185) & (lum > 60) & ~sable,
            'ciel': grey & (lum < 90), 'nuages_sombres': grey & (lum >= 90) & (lum < 170), 'nuages_clairs': grey & (lum >= 170)}


def fidelity(decor, ref):
    fr, fd = materials(ref), materials(decor); out = {}
    for k in fr:
        mr, md = ref[fr[k]].mean(0), decor[fd[k]].mean(0)
        out[k] = {'rip_rgb': [round(float(v), 1) for v in mr], 'decor_rgb': [round(float(v), 1) for v in md],
                  'distance': round(float(np.linalg.norm(mr - md)), 1)}
    return out


def fidelity_clouds_one_group(decor, ref):
    """Mesure écartée, gardée pour mémoire : tous les gris de l'orage en un seul groupe."""
    f = lambda a: ((a.max(-1) - a.min(-1)) < 30) & (lum_of(a) > 40)
    return round(float(np.linalg.norm(ref[f(ref)].mean(0) - decor[f(decor)].mean(0))), 1)


# ---------------------------------------------------------------- segmentation pleine résolution
def classify(a):
    """Seuils mesurés sur le brut (1200 x 896) :
    sable = r > 195, g > 175, r-b > 45, fermé/ouvert 2 px, > 20000 px, trous bouchés ; relief = sable + roche brune
    (r > g >= b, r-b >= 25), fermé 3 px, trous bouchés, > 50000 px ; îlots = trous du sable qui ne sont pas du sable,
    ouverts 1 px, fermés 2 px et bouchés : >= 150 px = pics (et pierres), 12 à 150 px = cailloux ; roche = relief hors
    sable ; nid = roche à y < 205 et 500 < x < 705 (le pilier de pierre du nord, plein, sans ouverture) ; falaise = le
    reste de la roche (couronne de l'arène) ; ciel = gris de lum < 90 hors relief, ouvert 3 px, relié au bord haut ;
    nuages = le reste. Les dessus des blocs de la couronne sont du même jaune que le sable : ils restent dans le
    calque sable (c'est du dessin), mais le sol PRATICABLE est calculé à part, après réduction (voir build)."""
    r, g, b = a.transpose(2, 0, 1); lum = lum_of(a)
    hh, ww = lum.shape; yy, xx = np.mgrid[:hh, :ww]
    sandc = (r > 195) & (g > 175) & (r - b > 45)
    rockc = (r > g) & (g >= b) & (r - b >= 25) & ~sandc
    sand = keep_large(open_(close_(sandc, 2), 2), 20000); sand = nd.binary_fill_holes(sand)
    land = keep_large(nd.binary_fill_holes(close_(sand | rockc, 3)), 50000)
    isl = open_(sand & ~sandc, 1)
    isl = nd.binary_fill_holes(close_(isl, 2)) & sand
    il, inn = nd.label(isl); sz = nd.sum(isl, il, range(1, inn + 1))
    pics = np.isin(il, [i + 1 for i, v in enumerate(sz) if v >= 150])
    cail = np.isin(il, [i + 1 for i, v in enumerate(sz) if 12 <= v < 150])
    rock = land & ~sand
    nid = rock & (yy < 205) & (xx > 500) & (xx < 705)
    fal = rock & ~nid
    sky = ~land
    ciel = keep_large(open_(sky & (lum < 90), 3), 2000)
    lab, _ = nd.label(ciel); t = np.unique(lab[0]); ciel = np.isin(lab, t[t > 0])
    masks = dict(pics=pics, cailloux=cail, sable=sand & ~pics & ~cail, nid=nid, falaise=fal, ciel=ciel, nuages=sky & ~ciel)
    seg = {'pics': int(sum(v >= 150 for v in sz)), 'cailloux': int(sum(12 <= v < 150 for v in sz)),
           'nid_px': int(nid.sum())}
    return masks, seg


# ---------------------------------------------------------------- sprites exacts de la planche
def rip_sheet(ref):
    """Éclairs (composante de (240,240,0) dans la boîte), arc Flash ((240,240,128)) et couleurs des pastilles."""
    sw = {k: tuple(tuple(int(v) for v in ref[y, x]) for y, x in pts) for k, pts in SWATCH.items()}
    bolts = {}
    for k, (y0, y1, x0, x1) in BOLTS.items():
        m = (ref[y0:y1, x0:x1] == sw['normal'][1]).all(-1)
        lab, n = nd.label(m, structure=np.ones((3, 3))); assert n == 1, (k, n)
        bolts[k] = m
    y0, y1, x0, x1 = FLASH_BOX
    flash = (ref[y0:y1, x0:x1] == sw['normal'][0]).all(-1)
    return bolts, flash, sw


def sprite(mask, color):
    s = np.zeros((*mask.shape, 4), 'uint8'); s[mask] = (*color, 255); return s


def strike_state(u):
    """Phase locale -> 'normal', 'fading' ou None."""
    return 'normal' if u < NORMAL_PH else 'fading' if u < NORMAL_PH + FADING_PH else None


def strike_boxes(bolts, flash, strikes=STRIKES):
    """Boîtes (x0, y0) de l'éclair et de l'arc pour chaque éclair : l'arc est centré sous le bas de l'éclair."""
    out = []
    for k, mirror, x, y, off in strikes:
        m = bolts[k][:, ::-1] if mirror else bolts[k]
        ys, xs = np.nonzero(m); yb = ys.max(); xb = int(round(xs[ys == yb].mean()))
        out.append((m, x, y, x + xb - flash.shape[1] // 2, y + yb - flash.shape[0] // 2 + 2, off))
    return out


def anim_frames(bolts, flash, sw, ts=range(PHASES), strikes=STRIKES):
    lue, ecl = [], []
    boxes = strike_boxes(bolts, flash, strikes)
    for t in ts:
        a = np.zeros((H, W, 4), 'uint8'); f = np.zeros((H, W, 4), 'uint8')
        for m, x, y, fx, fy, off in boxes:
            st = strike_state((t - off) % PHASES)
            if st:
                paste(a, sprite(m, sw[st][1]), x, y)
                paste(f, sprite(flash, sw[st][0]), fx, fy)
        lue.append(f); ecl.append(a)
    return lue, ecl


def paste(frame, spr, x0, y0):
    hh, ww = spr.shape[:2]; x0, y0 = int(x0), int(y0)
    ys0, xs0 = max(0, -y0), max(0, -x0); ys1, xs1 = min(hh, H - y0), min(ww, W - x0)
    if ys1 <= ys0 or xs1 <= xs0:
        return
    s = spr[ys0:ys1, xs0:xs1]; m = s[..., 3] > 0
    frame[y0 + ys0:y0 + ys1, x0 + xs0:x0 + xs1][m] = s[m]


# ---------------------------------------------------------------- ORA et Ground
def write_ora(path, layers):
    import xml.etree.ElementTree as ET
    root = ET.Element('image', w=str(W), h=str(H), name='Fin Mt. Thunder V2 (FTN1)')
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


def ground_project(stack, blocked, entry_px, boss_px, objective_px, gfx, tools):
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
    o.update(Name={'DefaultText': 'Fin Mt. Thunder - arene du sommet (4:3)', 'LocalTexts': {}}, AssetName=ASSET,
             Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0},
             ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Rendu genere 4:3 reference sur le rip Mt. Thunder (Red Rescue Team) ; eclairs et '
                     'lueurs animes (sprites et couleurs Normal / Fading exacts du rip). Collisions de base a '
                     'verifier. Aucune sortie ni warp. Biome choisi par l agent.')
    o['obstacles'] = [[{'Bounds': {'X': x*8, 'Y': y*8, 'Width': 8, 'Height': 8}, 'Tags': int(blocked[y, x])}
                       for y in range(gh)] for x in range(gw)]
    mk = lambda n, p: {'EntName': n, 'Direction': 4, 'EntEnabled': True, 'triggerType': 0,
                       'Collider': {'X': p[0], 'Y': p[1], 'Width': 16, 'Height': 16}}
    o['Entities'] = [{'Name': 'Entrees et vos acteurs', 'Visible': True, 'MapChars': [], 'GroundObjects': [], 'Spawners': [],
                      'Markers': [mk('entrance', entry_px), mk('boss', boss_px), mk('objectif', objective_px)]}]
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
  <Name>Fin Mt. Thunder 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : zone de fin de donjon : arrivee par une crete de sable au sud, arene ronde du sommet au-dessus des nuages d'orage, nid de pierre au nord, generee au format 4:3 (ref. rip Mt. Thunder), eclairs animes. Pas une aventure jouable.</Description>
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
        for d in ['calques', 'animation', 'poses', 'masques', 'review']:
            shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['calques', 'poses', 'masques', 'review'] + [f'animation/{x}' for x in ANIMS]:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    STAGE.parent.mkdir(parents=True, exist_ok=True)
    a, f, full = rgb(RAW / 'decor.png'), rgb(RAW / 'sol_complet.png'), rgb(REF)
    ref = full[:REF_SCENE_H]
    assert a.shape[:2] == f.shape[:2] == (SRC[1], SRC[0])
    m, seg = classify(a)
    order = ['pics', 'cailloux', 'sable', 'nid', 'falaise', 'ciel', 'nuages']
    ex, cols = down_class(a, m, order)
    layers = {'sol_complet': rgba(down_full(f), np.ones((H, W), bool))}
    for k in STATIC:
        layers[k] = rgba(cols[k], ex[k])
    q = {}
    for keys, n in PALETTE_GROUPS.values():
        q.update(quantize_group({k: layers[k] for k in keys}, n))
    layers = q
    for k, v in ex.items():
        Image.fromarray((v * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_{k}.png')
    # Sol praticable : les dessus des blocs de la couronne sont jaunes comme le sable (calque sable) mais ne se
    # marchent pas. Noyau = sable + cailloux ouverts de CORE_OPEN cases (diamant) : il retire les bandes étroites des
    # blocs ; le sol est le noyau agrandi de CORE_BACK, relié au bord sud. Le noyau est exporté (masque).
    cand = ex['sable'] | ex['cailloux']
    core = open_(cand, CORE_OPEN)
    cl, _ = nd.label(core); big = np.argmax(nd.sum(core, cl, range(1, cl.max() + 1))) + 1
    core = cl == big
    cand = cand & nd.binary_dilation(core, iterations=CORE_BACK)
    cl, _ = nd.label(cand); seed = cl[H - 1][cand[H - 1]]
    walk = np.isin(cl, np.unique(seed[seed > 0]))
    Image.fromarray((walk * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_praticable.png')
    bolts, flash, sw = rip_sheet(full)
    for k, bm in bolts.items():
        Image.fromarray(sprite(bm, sw['normal'][1])).save(OUT / 'poses' / f'{PFX}_eclair_{k}.png')
    Image.fromarray(sprite(flash, sw['normal'][0])).save(OUT / 'poses' / f'{PFX}_flash.png')
    lueurs, eclairs = anim_frames(bolts, flash, sw)
    anim = {'lueurs': lueurs, 'eclairs': eclairs}
    order_names = ['sol_complet'] + STATIC + ANIMS
    stack_named, layer_list = [], []
    for i, nm in enumerate(order_names):
        if nm in anim:
            frames, ticks = anim[nm], TICKS
            for t, fr in enumerate(frames):
                Image.fromarray(fr).save(OUT / 'animation' / nm / f'{PFX}_{i:02d}_{nm}_f{t:02d}.png')
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
    free = lambda cx, cy: 0 <= cx < gw_ - 1 and 0 <= cy < gh_ - 1 and not blocked[cy:cy + 2, cx:cx + 2].any()
    # Boss : case 2 x 2 libre la plus proche du centre de gravité du sol praticable (centre de l'arène).
    wy, wx = np.nonzero(walk); tgt = (int(wx.mean()) // 8, int(wy.mean()) // 8)
    boss_c = min(((cx, cy) for cy in range(gh_) for cx in range(gw_) if free(cx, cy)),
                 key=lambda c: (c[0] - tgt[0]) ** 2 + (c[1] - tgt[1]) ** 2)
    boss_px = [boss_c[0] * 8, boss_c[1] * 8]
    # Objectif : au pied du nid, case libre la plus haute dans la colonne centrale (+-64 px).
    mid = W // 16
    cands = [(cx, cy) for cy in range(gh_) for cx in range(mid - 8, mid + 8) if free(cx, cy)]
    top = min(cy for _, cy in cands)
    obj_c = min((c for c in cands if c[1] <= top + 1), key=lambda c: abs(c[0] - mid))
    objective_px = [obj_c[0] * 8, obj_c[1] * 8]
    reach_boss, explored = v1.reachable(blocked, (entry_px[1] // 8, entry_px[0] // 8), (boss_c[1], boss_c[0]))
    reach_obj, explored_o = v1.reachable(blocked, (entry_px[1] // 8, entry_px[0] // 8), (obj_c[1], obj_c[0]))
    assert reach_boss and reach_obj, 'pas de chemin 16x16'
    reach = bool(reach_boss and reach_obj)

    def scene(tick):
        im = Image.new('RGBA', (W, H))
        for _, frames, ticks in stack_named:
            im.alpha_composite(Image.fromarray(frames[(tick // ticks) % len(frames)]))
        return im
    step = 5
    scenes = [scene(t) for t in range(0, LOOP_TICKS, step)]
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_t000.png')
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_animee.webp', save_all=True, append_images=scenes[1:],
                   duration=round(step * 1000 / 60), loop=0, lossless=True)
    col = scenes[0].copy(); ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    for y, x in zip(*np.nonzero(blocked)):
        dr.rectangle([x*8, y*8, x*8+7, y*8+7], fill=(220, 40, 40, 90))
    for (qx, qy), c in ((entry_px, (255, 230, 40, 255)), (boss_px, (255, 60, 220, 255)), (objective_px, (60, 220, 255, 255))):
        dr.rectangle([qx, qy, qx + 15, qy + 15], outline=c, width=2)
    col.alpha_composite(ov); col.save(OUT / 'review' / f'{PFX}_collisions_marqueurs.png')
    # Planche : les 4 éclairs et l'arc, en Normal puis en Fading, x3, sur le gris des nuages sombres.
    sprites = [sprite(bolts[k], sw[s][1]) for s in ('normal', 'fading') for k in BOLTS] + \
              [sprite(flash, sw[s][0]) for s in ('normal', 'fading')]
    cw, chh = 3 * 42, 3 * 128
    sheet = Image.new('RGBA', (len(sprites) * cw + 8, chh + 16), (112, 104, 112, 255))
    for i, spr in enumerate(sprites):
        im = Image.fromarray(spr); im = im.resize((im.width * 3, im.height * 3), Image.Resampling.NEAREST)
        sheet.alpha_composite(im, (8 + i * cw + (cw - 8 - im.width) // 2, 8))
    sheet.save(OUT / 'review' / f'{PFX}_planche_poses.png')
    write_ora(OUT / f'{PFX}_fin_mt_thunder_calques.ora',
              {f'{i:02d}_{t}' + ('_f00' if len(fr) > 1 else ''): fr[0] for i, (t, fr, _) in enumerate(stack_named)})
    counts = ground_project([(t.replace('_', ' ') + (f' {len(fr)} phases' if len(fr) > 1 else ''), fr, tk)
                             for t, fr, tk in stack_named], blocked, entry_px, boss_px, objective_px, gfx, tools)
    fid = fidelity(a, ref)
    final_fid = {}
    for k, nm in (('sable', 'sable'), ('roche', 'falaise'), ('roche', 'nid'), ('ciel', 'ciel'),
                  ('nuages_sombres', 'nuages'), ('nuages_clairs', 'nuages')):
        lay = layers[nm]; px = lay[lay[..., 3] == 255][:, :3].astype(float)
        sel = materials(px.reshape(-1, 1, 3))[k][:, 0]
        px = px[sel] if sel.sum() > 50 else px
        final_fid[f'{nm}:{k}'] = {'calque': nm, 'matiere': k, 'rgb': [round(float(v), 1) for v in px.mean(0)],
                                  'distance_rip': round(float(np.linalg.norm(px.mean(0) - np.array(fid[k]['rip_rgb']))), 1)}
    boxes = strike_boxes(bolts, flash)
    manifest = {
        'lot': 'fin_mt_thunder_v2', 'prefix': PFX, 'format': '4:3 vaste', 'size_px': [W, H],
        'grid_8px': [W // 8, H // 8], 'base': 'branche de session (EWC1 et ESN1 pour les utilitaires) ; aucun emprunt aux branches soeurs',
        'biome': 'fin de donjon : arene ronde du sommet d orage au-dessus des nuages, nid de pierre au nord ; choisi par l agent avec l utilisateur (« Poursuis le projet »)',
        'method': 'textures canoniques = rendu genere REFERENCE : rip passe au generateur ; decor complet et sol complet '
                  'generes avec le rip en reference ; eclairs et arc Flash copies de la planche du rip',
        'reference_da': {'file': REF.name, 'sha256': sha(REF), 'scene_rows': [0, REF_SCENE_H],
                         'titre': 'Mt. Thunder, salle du boss (Red Rescue Team, GBA) : nom de fichier de la planche',
                         'deja_utilise': 'entree EMT1 (meme rip, meme lieu : la fin prolonge l entree) ; mt_thunder_orage_v1 sur 01a0d8a8, 01a0d9b3, 01a0d9f7 et FTH1 sur 01a0ed06, 01a0eecd, 01a0ef89 (rien repris)'},
        'generation': GEN,
        'raw_inputs': [{'file': f'{LOT}/bruts/{g["file"]}', 'sha256': sha(RAW / g['file']),
                        'size': list(Image.open(RAW / g['file']).size)} for g in GEN],
        'segmentation_mesures': seg,
        'fidelite_rip': {'methode': 'moyenne RGB par matiere, meme classifieur pixel sur la scene du rip (y < 352) et sur '
                                    'le brut ; distance euclidienne ; seuil 35 ; gris de l orage mesures PAR TON',
                         'brut': fid, 'calques_finaux': final_fid,
                         'nuages_un_seul_groupe_ecarte': {'distance': fidelity_clouds_one_group(a, ref),
                                                          'raison': 'moyenne de tons discrets ponderee par leurs proportions '
                                                                    '(ciel sombre abondant dans le rip, bas de carte blanc dans le brut) : '
                                                                    'mesure la composition, pas la couleur ; remplacee par la mesure par ton'},
                         'sol_complet': round(float(np.linalg.norm(f.reshape(-1, 3).mean(0) - np.array(fid['sable']['rip_rgb']))), 1),
                         'eclairs': 'pixels et couleurs EXACTS de la planche du rip',
                         'limites': {'nid:roche': 'LIMITE SIGNALEE : le pilier de pierre du nord est plus sombre que les falaises du rip '
                                                  '(distance 52,7 pour un seuil de 35 ; la roche de l ensemble du brut est a 26,0). '
                                                  'Layout garde, brut non regenere ; premiere amelioration possible : une generation ciblee du nid.'}},
        'normalization': {'scale': JM.SCALE, 'scaled': [JM.SCALED_W, H], 'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
                          'methode': 'moyenne ponderee par classe (BOX), attribution exclusive par poids maximal',
                          'palettes': {g: {'calques': k, 'couleurs': n} for g, (k, n) in PALETTE_GROUPS.items()}},
        'segmentation': classify.__doc__.split('\n', 1)[1].strip(),
        'layers': layer_list,
        'eclairs': {'boites_rip': {str(k): list(v) for k, v in BOLTS.items()}, 'flash_rip': list(FLASH_BOX),
                    'pastilles': {k: [list(c) for c in v] for k, v in sw.items()},
                    'couleurs': 'eclair = pastille vive (240,240,0) puis (160,152,32) ; arc = pastille pale (240,240,128) '
                                'puis (184,176,120) : interpretation des pastilles Normal / Fading (paire pale, paire vive)',
                    'frappes': [list(s) for s in STRIKES],
                    'arcs': [[int(b[3]), int(b[4])] for b in boxes],
                    'normal_phases': NORMAL_PH, 'fading_phases': FADING_PH, 'phases': PHASES, 'frame_length_ticks': TICKS,
                    'miroir': 'eclair 1 a gauche seulement ; 2 a 4 a gauche ou en miroir a droite (note de la planche)',
                    'limite': 'l eclair 3 touche le bas de la planche (y = 498) : il est peut-etre tronque',
                    'origine': 'dessin et couleurs EXACTS de la planche ; placement, cadence et arc au pied de l eclair crees par nous'},
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'entry_px': entry_px, 'boss_px': boss_px, 'objective_px': objective_px, 'path_found_16x16': reach,
                   'path_to_boss': reach_boss, 'path_to_objective': reach_obj, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si > 25 % hors praticable (noyau de sable + cailloux relie au bord sud, sans le dessus des blocs de la couronne)',
                   'noyau': {'ouverture_diamant_px': CORE_OPEN, 'reagrandissement_px': CORE_BACK},
                   'boss': 'case 2 x 2 libre la plus proche du centre de gravite du sol praticable',
                   'objectif': 'case 2 x 2 libre la plus haute de la colonne centrale (+-64 px), au pied du nid',
                   'fin': 'aucune sortie, aucun warp, pas de donjon_seuil ; le nid et la couronne sont des parois'},
        'pmdo': {'target': '0.8.12', 'asset': ASSET, 'namespace': NAMESPACE, 'tiles_per_bank': counts, 'banks': list(counts),
                 'runtime_tested': False, 'warp': 'aucun'},
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    print(json.dumps({'entry': entry_px, 'boss': boss_px, 'objectif': objective_px, 'blocked': int(blocked.sum()),
                      'walkable': int((~blocked).sum()), 'seg': seg,
                      'px': {k: int(v.sum()) for k, v in ex.items()},
                      'fidelite': {k: v['distance'] for k, v in fid.items()},
                      'final': {k: v['distance_rip'] for k, v in final_fid.items()}, 'tiles': counts}, indent=1))


if __name__ == '__main__':
    build()
