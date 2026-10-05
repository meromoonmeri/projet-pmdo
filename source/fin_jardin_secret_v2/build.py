"""Fin Jardin secret V2 (FJS4) — stèle sanctuaire fermée de Celebi sur la souche — 4:3 (768 x 576 px, 96 x 72 cases).

Demande : « bon avance » (3 octobre, après FCV3 et FMT3) : dernière des fins de donjon restantes de la série dans l'ordre
du mod, prolongeant les entrées Jardin secret (EJS1 / EJS2). Biome et portée choisis par l'agent, à confirmer. Préfixe
FJS4 (FJS3 et FGS1 sont pris sur des branches sœurs).
Méthode « textures canoniques » = rendu généré RÉFÉRENCÉ :
- decor_sanctuaire.png : le décor d'EJS1 édité par le générateur (images = décor EJS1 + rip `secretgarden.png`) pour
  remplacer le trou carré de la souche par une stèle sanctuaire de pierre fermée (sans trou ni porte) ornée d'un emblème
  de Celebi en relief. Comme pour EJS2, seule la zone de la stèle sanctuaire est reprise (collage local dans WIN sur le
  décor d'EJS1) : hors de cette zone, le décor est celui d'EJS1 au pixel près ;
- témoin sans objets et sol complet : ceux d'EJS1, inchangés (bruts d'EJS1, relus par chemin).
Calques : ceux d'EJS1 sans `profondeur`, plus `sanctuaire` (socle et stèle de pierre fermée sur la souche) et `embleme`
(relief lumineux de Celebi au centre de la stèle).
Animations, chacune sur son calque, boucles fermées, 24 x 5 ticks (2 s), fonctions et rampe EXACTE du rip chargées d'EJS2 :
- embleme : l'emblème de Celebi en relief sur la stèle, recoloré sur la rampe EXACTE du rayon du rip (+3 crans) ;
- rayon et lucioles : comme EJS2.
Scène : 120 ticks = 2 s.
Marqueurs : `entrance` (sud), `boss` (centre de la prairie), `objectif` (au pied des marches de la stèle au nord).
Aucune sortie, aucun warp, pas de `donjon_seuil`.
Lancer : .venv/bin/python source/fin_jardin_secret_v2/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
RAW1 = R / 'source/entree_jardin_secret_sud_nord_v1/bruts'
REF_NAME = 'secretgarden.png'
REF = R / REF_NAME
OUT = R / 'renders/fin_jardin_secret_v2'
STAGE = R / '.cache/fin_jardin_secret_v2/fin_jardin_secret'
NAMESPACE = 'fin_jardin_secret'
ASSET = 'fjs4_fin_jardin_secret'
PFX = 'FJS4'
W, H = 768, 576
SRC = (1200, 896)
PHASES, TICKS = 24, 5
LOOP_TICKS = 120
LOT1 = 'source/entree_jardin_secret_sud_nord_v1'
LOT = 'source/fin_jardin_secret_v2'


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


EJS2 = loadmod('ejs2_build', R / 'source/entree_jardin_secret_sud_nord_v2/build.py')
V1 = EJS2.V1
JM, BM = EJS2.JM, EJS2.BM
assert (JM.W, JM.H, JM.SRC) == (W, H, SRC)
keep_large, cell_grid, close_, open_ = EJS2.keep_large, EJS2.cell_grid, EJS2.close_, EJS2.open_
down_class, down_full, rgba, quantize_group = EJS2.down_class, EJS2.down_full, EJS2.rgba, EJS2.quantize_group
sha, rgb, lum_of, sdev, materials, fidelity, recalage, flower_px, composite = (
    EJS2.sha, EJS2.rgb, EJS2.lum_of, EJS2.sdev, EJS2.materials, EJS2.fidelity, EJS2.recalage, EJS2.flower_px, EJS2.composite)
ramp_index, breath, beam_frames, glow, emblem_frames, mote_state, mote_frames = (
    EJS2.ramp_index, EJS2.breath, EJS2.beam_frames, EJS2.glow, EJS2.emblem_frames, EJS2.mote_state, EJS2.mote_frames)
WIN, PASTE_DIFF, EMBLEM_GLOW, RAMP, BREATH, EDGE_STEPS, MOTES, MOTE_RISE, DOT, GLOW, CORE = (
    EJS2.WIN, EJS2.PASTE_DIFF, EJS2.EMBLEM_GLOW, EJS2.RAMP, EJS2.BREATH, EJS2.EDGE_STEPS, EJS2.MOTES, EJS2.MOTE_RISE,
    EJS2.DOT, EJS2.GLOW, EJS2.CORE)

GEN = [
    *EJS2.GEN[:5],
    {'file': 'ecartes/decor_sanctuaire_essai1_1024x1024.png', 'lot': LOT,
     'images': [f'{LOT1}/bruts/decor.png', REF_NAME], 'ecarte': True,
     'prompt':
     "Edit the first image. Keep EVERYTHING identical (same framing, same size, same hedges, trees, rocks, flowers, "
     "meadow, light beam, same pixel positions). Change ONLY the top of the big golden tree stump in the upper center: "
     "replace the square dark hole on the stump's flat top with a CLOSED sacred stone pedestal and carved forest relic "
     "shrine of Celebi standing on the flat golden wooden top of the stump (NO dark hole, NO doorway, NO opening): a "
     "small pale stone altar base on the closed wooden stump top holding a carved stone Celebi guardian stele with a "
     "glowing light-green onion-shaped Celebi emblem in relief at its center, bathed in the vertical green light beam. "
     "The wooden steps on the front of the stump stay intact and lead up to the closed sanctuary pedestal. Same Pokemon "
     "Mystery Dungeon pixel-art style, palette and shading as the second reference image. No characters, no text, no UI, "
     "no border.",
     'essais': 'ECARTE : format carre 1024x1024 (influence de la seconde image 440x440 sans rappel 4:3 en fin de prompt), non utilisable sans recadrage'},
    {'file': 'decor_sanctuaire.png', 'lot': LOT,
     'images': [f'{LOT1}/bruts/decor.png', REF_NAME],
     'prompt':
     "Edit the first wide 4:3 landscape image (1200x896). Keep the exact 4:3 wide landscape aspect ratio (1200x896) and "
     "keep EVERYTHING identical (same framing, same size, same hedges, trees, rocks, flowers, meadow, light beam, same "
     "pixel positions). Change ONLY the top of the big golden tree stump in the upper center: replace the square dark "
     "hole on the stump's flat top with a CLOSED sacred stone pedestal and carved forest relic stele of Celebi standing "
     "on the flat golden wooden top of the stump (NO dark hole, NO doorway, NO opening): a small pale stone altar base "
     "on the closed wooden stump top holding a carved stone Celebi guardian stele with a glowing light-green "
     "onion-shaped Celebi emblem in relief at its center, bathed in the vertical green light beam. The wooden steps on "
     "the front of the stump stay intact and lead up to the closed sanctuary pedestal. Same Pokemon Mystery Dungeon "
     "pixel-art style, palette and shading as the reference images. Wide landscape 4:3. No characters, no text, no UI, "
     "no border.",
     'essais': 'second essai (format 1200x896) ; conforme ; seule la zone du sanctuaire est reprise (collage local sur le decor d EJS1)'},
]


def raw_path(g):
    return R / g['lot'] / 'bruts' / g['file']


PALETTE_GROUPS = {
    'herbe': (['sol_complet', 'prairie', 'herbe', 'ombres'], 64),
    'fleurs': (['fleurs'], 24),
    'rochers': (['rochers'], 32),
    'vegetation': (['arbres', 'haies'], 96),
    'souche': (['souche', 'marches'], 48),
    'sanctuaire': (['sanctuaire'], 48),
    'fond': (['fond'], 8),
}
STATIC = ['prairie', 'herbe', 'ombres', 'fleurs', 'rochers', 'arbres', 'haies', 'souche', 'sanctuaire', 'marches', 'fond']
ANIMS = ['embleme', 'rayon', 'lucioles']


def classify(a, t, paste):
    """a : décor (collé), t : témoin sans objets d'EJS1, paste : zone du sanctuaire collée. Seuils mesurés sur le brut (1200 x 896) :
    SANCTUAIRE (FJS4, fermé sans trou ni porte) = plus grande composante de pierre beige-grise dans la zone collée
    (|r - g| <= 18, r - b >= 30, b >= 55, fermée 3 px, trous bouchés) ; emblème = pixels verts lumineux (g > r + 18,
    lum > 140) en relief au centre de la stèle (y de haut+12 à haut+72, |x - cx| <= 22), fermés 1 px ; sanctuaire = la
    stèle et son socle hors emblème ; la stèle sort du rayon ; marches = souche sous le socle de pierre (y > bas du
    socle) dans la largeur de l'ancien trou (+- 2 px) ; souche = le reste de la souche dorée (sans trou).
    Les autres calques (fond, rayon, haies, fleurs, rochers, arbres, prairie, ombres, herbe) suivent exactement EJS1/EJS2."""
    lt, la = lum_of(t), lum_of(a); hh, ww = lt.shape; yy, xx = np.mgrid[:hh, :ww]
    r, g, b = t[..., 0], t[..., 1], t[..., 2]
    fond = open_((nd.uniform_filter(lt, 5) < 85) & (g > r + 15), 3)
    lab, _ = nd.label(fond); e = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]); fond = np.isin(lab, e[e > 0])
    beam = ((g - r > 70) | (lt > 205)) & (yy < 175) & (xx > 470) & (xx < 730) & ~fond
    lab, _ = nd.label(close_(beam, 2)); rayon = np.isin(lab, np.unique(lab[0][lab[0] > 0])) & (yy < 175)
    rayon = nd.binary_fill_holes(rayon) & ~fond
    ra, ga, ba = a[..., 0], a[..., 1], a[..., 2]; beam_a = (ga - ra > 70) | (la > 205)
    d0 = nd.uniform_filter(np.abs(a - t).mean(2).astype(float), 3)
    ol0, on0 = nd.label(nd.binary_fill_holes(close_(d0 > 28, 3)) & rayon)
    for i in range(on0):
        m = ol0 == i + 1
        if m.sum() >= 30 and beam_a[m].mean() < 0.3:
            rayon &= ~m
    gold = (r >= g - 12) & (r - b > 60) & (yy > 120) & (yy < 280) & (xx > 500) & (xx < 700)
    st = nd.binary_fill_holes(keep_large(close_(gold, 4), 3000)) & ~rayon
    hole0 = open_((lt < 75) & st, 1); hl, hn = nd.label(hole0); hs = nd.sum(hole0, hl, range(1, hn + 1))
    hole0 = nd.binary_fill_holes(close_(hl == int(np.argmax(hs)) + 1, 2)) & st
    hy, hx = np.nonzero(hole0); sy, sx = np.nonzero(st)
    # --- sanctuaire fermé (FJS4)
    stone_c = paste & (np.abs(ra - ga) <= 18) & (ra - ba >= 30) & (ba >= 55)
    gl, gn = nd.label(close_(stone_c, 3))
    top = nd.binary_fill_holes(gl == int(np.argmax(nd.sum(stone_c, gl, range(1, gn + 1)))) + 1) & paste
    ys_s, xs_s = np.nonzero(top); ybase = int(ys_s.max()); scx = int(round(xs_s.mean()))
    ebox = top & (yy >= ys_s.min() + 12) & (yy <= ys_s.min() + 72) & (np.abs(xx - scx) <= 22)
    emblem = close_(ebox & (ga > ra + 18) & (la > 140), 1) & ebox
    ey, ex = np.nonzero(emblem)
    rayon &= ~top
    steps = (st | top) & (yy > ybase) & (xx >= hx.min() - 2) & (xx <= hx.max() + 2) & ~top
    sanctuaire = top & ~emblem
    st = st | top
    front = (yy > sy.max() - 10) & (yy < sy.max() + 40) & (xx > sx.min() + 20) & (xx < sx.max() - 20) & ~st
    haie = keep_large(close_((sdev(lt, 9) > 6) & ~fond & ~rayon & ~st & ~front, 3), 3000)
    haie &= nd.binary_dilation(open_(haie, 5), iterations=5)
    hol = nd.binary_fill_holes(haie) & ~haie; hl, hn = nd.label(hol); hs = nd.sum(hol, hl, range(1, hn + 1))
    haie = (haie | np.isin(hl, [i + 1 for i, v in enumerate(hs) if v < 800])) & ~fond & ~rayon & ~st & ~front
    diff = nd.uniform_filter(np.abs(a - t).mean(2).astype(float), 3)
    obj = keep_large(nd.binary_fill_holes(close_(diff > 28, 3)), 30) & ~st & ~rayon & ~fond
    ol, on = nd.label(obj); fpx = flower_px(a); fle = np.zeros_like(obj)
    for i, s in enumerate(nd.find_objects(ol)):
        m = ol[s] == i + 1
        if m.sum() < 400 and fpx[s][m].mean() >= 0.2:
            fle[s] |= m
    tan = (np.abs(ra - ga) < 30) & (ra - ba > 25) & (la > 80) & (la < 215) & obj & ~fle
    tl, tn = nd.label(nd.binary_fill_holes(close_(tan, 2)) & obj & ~fle); roc = np.zeros_like(obj); nroc = 0
    for i, s in enumerate(nd.find_objects(tl)):
        m = tl[s] == i + 1
        if m.sum() >= 150 and la[s][m].mean() > 115:
            roc[s] |= m; nroc += 1
    flat = (sdev(la, 9) < 6) & (la < 155) & (ga > ra + 30)
    shade = obj & ~fle & ~roc & flat
    arb = keep_large(obj & ~fle & ~roc & ~shade, 300)
    rest = obj & ~fle & ~roc & ~arb & ~shade
    grass = ~(fond | rayon | st | haie | fle | roc | arb)
    bl, ll = nd.uniform_filter(ba.astype(float), 5), nd.uniform_filter(la, 5)
    prairie = grass & ~shade & (bl < 50)
    omb = grass & ~prairie & ((ll < 150) | shade)
    herbe = grass & ~prairie & ~omb
    souche = st & ~steps & ~sanctuaire & ~emblem
    masks = dict(embleme=emblem, marches=steps, sanctuaire=sanctuaire, souche=souche, fleurs=fle, rochers=roc,
                 arbres=arb, haies=haie, fond=fond, rayon=rayon, ombres=omb, prairie=prairie, herbe=herbe)
    seg = {'objets': int(on), 'fleurs': int(nd.label(fle)[1]), 'rochers': nroc, 'arbres': int(nd.label(arb)[1]),
           'miettes_rendues_a_l_herbe_px': int(rest.sum()), 'souche_y': [int(sy.min()), int(sy.max())],
           'ombres_lum': round(float(la[omb].mean()), 1), 'herbe_lum': round(float(la[herbe].mean()), 1),
           'prairie_b': round(float(ba[prairie].mean()), 1),
           'sanctuaire': {'socle_bas_y': ybase, 'stele_y': [int(ys_s.min()), ybase],
                          'stele_x': [int(xs_s.min()), int(xs_s.max())],
                          'embleme_y': [int(ey.min()), int(ey.max())], 'embleme_x': [int(ex.min()), int(ex.max())],
                          'sanctuaire_px': int(sanctuaire.sum()), 'embleme_px': int(emblem.sum()),
                          'colle_px': int(paste.sum())}}
    return masks, seg


def write_ora(path, layers):
    import xml.etree.ElementTree as ET
    root = ET.Element('image', w=str(W), h=str(H), name='Fin Jardin secret V2, sanctuaire de Celebi (FJS4)')
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
    o.update(Name={'DefaultText': 'Fin Jardin secret, sanctuaire de Celebi (4:3)', 'LocalTexts': {}}, AssetName=ASSET,
             Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0},
             ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Rendu genere 4:3 reference sur le rip Jardin secret ; stele sanctuaire fermee de '
                     'Celebi sur la souche (sans trou ni porte) ; embleme, rayon et lucioles animes (rampe exacte du '
                     'rip). Collisions de base a verifier. Aucune sortie ni warp. Biome et portee choisis par l agent.')
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
  <Name>Fin Jardin secret V2, sanctuaire de Celebi, 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : zone de fin du Jardin secret avec stele sanctuaire fermee de Celebi sur la souche sous un rayon de lumiere, generee au format 4:3 (ref. rip Jardin secret), embleme, rayon et lucioles animes. Pas une aventure jouable.</Description>
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
    shutil.copyfile(HERE / 'README_PACK.md', OUT / 'README.md')
    return {b.name: len(b.data) for b in banks}


def build():
    gfx = loadmod('pmdo_codec', R / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
    v1 = loadmod('esn1', R / 'source/entree_sud_nord_generee_v1/build.py')
    if OUT.exists():
        for d in ['calques', 'animation', 'masques', 'review']:
            shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['calques', 'masques', 'review'] + [f'animation/{x}' for x in ANIMS]:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    STAGE.parent.mkdir(parents=True, exist_ok=True)
    a1, g2 = rgb(RAW1 / 'decor.png'), rgb(RAW / 'decor_sanctuaire.png')
    t, f, ref = rgb(RAW1 / 'temoin_sans_objets.png'), rgb(RAW1 / 'sol_complet.png'), rgb(REF)
    y0, y1, x0, x1 = WIN; far = np.ones(a1.shape[:2], bool); far[max(0, y0 - 20):y1 + 20, max(0, x0 - 20):x1 + 20] = False
    reg_sanc = recalage(a1, g2, far)
    a, paste = composite(a1, g2)
    Image.fromarray((paste * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_zone_collee_pleine_resolution.png')
    assert a.shape[:2] == t.shape[:2] == f.shape[:2] == (SRC[1], SRC[0])
    m, seg = classify(a, t, paste)
    objs = m['fleurs'] | m['rochers'] | m['arbres'] | (np.abs(a - t).mean(2) > 10)
    reg = {'temoin': recalage(a, t, ~nd.binary_dilation(objs | paste, iterations=4)), 'brut_sanctuaire': reg_sanc}
    order = ['embleme', 'marches', 'sanctuaire', 'souche', 'fleurs', 'rochers', 'arbres', 'rayon', 'haies', 'fond',
             'ombres', 'prairie', 'herbe']
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
    cand = ex['prairie'] | ex['herbe'] | ex['ombres'] | ex['fleurs'] | ex['marches']
    cl, _ = nd.label(close_(cand, 2)); seed = cl[H - 1][cand[H - 1]]
    walk = np.isin(cl, np.unique(seed[seed > 0])) & cand
    Image.fromarray((walk * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_praticable.png')
    base_idx = ramp_index(cols['rayon'])
    Image.fromarray(np.where(ex['rayon'], base_idx * 11, 0).astype('uint8')).save(OUT / 'masques' / f'{PFX}_rayon_crans.png')
    rayon = beam_frames(base_idx, ex['rayon'])
    emb_idx = ramp_index(cols['embleme'])
    Image.fromarray(np.where(ex['embleme'], emb_idx * 11, 0).astype('uint8')).save(OUT / 'masques' / f'{PFX}_embleme_crans.png')
    embleme = emblem_frames(emb_idx, ex['embleme'])
    lucioles = mote_frames(MOTES)
    anim = {'embleme': embleme, 'rayon': rayon, 'lucioles': lucioles}
    order_names = ['sol_complet'] + STATIC + ANIMS
    stack_named, layer_list = [], []
    for i, nm in enumerate(order_names):
        if nm in anim:
            frames, ticks = anim[nm], TICKS
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
    free = lambda cx, cy: 0 <= cx < gw_ - 1 and 0 <= cy < gh_ - 1 and not blocked[cy:cy + 2, cx:cx + 2].any()
    tgt = (W // 16 - 1, H // 16 - 1)
    boss_c = min(((cx, cy) for cy in range(gh_) for cx in range(gw_) if free(cx, cy)),
                 key=lambda c: (c[0] - tgt[0]) ** 2 + (c[1] - tgt[1]) ** 2)
    boss_px = [boss_c[0] * 8, boss_c[1] * 8]
    # Objectif : au pied des marches de la stèle sanctuaire au nord : case libre la plus haute sous le sanctuaire.
    sys_, sxs_ = np.nonzero(ex['sanctuaire'])
    scx_c = int(round(sxs_.mean())) // 8 - 1
    cands = [(cx, cy) for cy in range(int(sys_.max()) // 8, gh_) for cx in range(scx_c - 3, scx_c + 4) if free(cx, cy)]
    top_cy = min(cy for _, cy in cands)
    obj_c = min((c for c in cands if c[1] <= top_cy + 1), key=lambda c: abs(c[0] - scx_c))
    objective_px = [obj_c[0] * 8, obj_c[1] * 8]
    reach_boss, explored = v1.reachable(blocked, (entry_px[1] // 8, entry_px[0] // 8), (boss_c[1], boss_c[0]))
    reach_obj, _ = v1.reachable(blocked, (entry_px[1] // 8, entry_px[0] // 8), (obj_c[1], obj_c[0]))
    assert reach_boss and reach_obj, 'pas de chemin 16x16'
    reach = bool(reach_boss and reach_obj)

    def scene(tick):
        im = Image.new('RGBA', (W, H))
        for _, frames, ticks in stack_named:
            im.alpha_composite(Image.fromarray(frames[(tick // ticks) % len(frames)]))
        return im
    step = 5
    scenes = [scene(tk) for tk in range(0, LOOP_TICKS, step)]
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_t000.png')
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_animee.webp', save_all=True, append_images=scenes[1:],
                   duration=round(step * 1000 / 60), loop=0, lossless=True)
    col = scenes[0].copy(); ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    for y, x in zip(*np.nonzero(blocked)):
        dr.rectangle([x*8, y*8, x*8+7, y*8+7], fill=(220, 40, 40, 90))
    for (qx, qy), c in ((entry_px, (255, 230, 40, 255)), (boss_px, (255, 60, 220, 255)), (objective_px, (60, 220, 255, 255))):
        dr.rectangle([qx, qy, qx + 15, qy + 15], outline=c, width=2)
    col.alpha_composite(ov); col.save(OUT / 'review' / f'{PFX}_collisions_marqueurs.png')
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
    write_ora(OUT / f'{PFX}_fin_jardin_secret_calques.ora',
              {f'{i:02d}_{tn}' + ('_f00' if len(fr) > 1 else ''): fr[0] for i, (tn, fr, _) in enumerate(stack_named)})
    counts = ground_project([(tn.replace('_', ' ') + (f' {len(fr)} phases' if len(fr) > 1 else ''), fr, tk)
                             for tn, fr, tk in stack_named], blocked, entry_px, boss_px, objective_px, gfx, tools)
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
        'lot': 'fin_jardin_secret_v2', 'prefix': PFX, 'format': '4:3 vaste', 'type': 'fin de donjon',
        'size_px': [W, H], 'grid_8px': [W // 8, H // 8],
        'base': 'branche de session (EJS1/EJS2 pour les bruts, la rampe et les fonctions rayon/embleme/lucioles ; EWC1/ESN1 pour les utilitaires) ; aucun emprunt aux branches soeurs',
        'biome': 'fin du Jardin secret (stele sanctuaire fermee de Celebi sur la souche, prolonge EJS1/EJS2), biome et portee choisis par l agent (« bon avance »), a confirmer',
        'method': 'textures canoniques = rendu genere REFERENCE : decor EJS1 + rip passes au generateur pour la stele sanctuaire fermee ; '
                  'seule la zone du sanctuaire est collee sur le decor EJS1 ; temoin et sol complet d EJS1',
        'reference_da': {'file': REF.name, 'sha256': sha(REF),
                         'titre': 'Jardin secret (Explorers of Sky, nom de fichier ; scene non confirmee)'},
        'generation': GEN,
        'raw_inputs': [{'file': f'{g["lot"]}/bruts/{g["file"]}', 'sha256': sha(raw_path(g)),
                        'size': list(Image.open(raw_path(g)).size), 'ecarte': bool(g.get('ecarte'))} for g in GEN],
        'recalage': {**reg, 'zones': 'temoin : hors objets (ecart > 10) et hors zone collee, dilates de 4 px ; brut du sanctuaire : '
                                     'hors fenetre de la souche elargie de 20 px'},
        'sanctuaire': {'fenetre_pleine_resolution': list(WIN), 'seuil_ecart': PASTE_DIFF,
                       'collage': 'composante principale de l ecart lisse 3 px > seuil dans la fenetre, fermee 3 px, trous bouches, '
                                  'dilatee 2 px ; hors zone collee, decor EJS1 au pixel pres',
                       'embleme': {'loi': 'cran = clip(cran0 + round(3 (1 - cos(2 pi u / 24)) / 2)), u = min(t, 24 - t)',
                                   'crans_max': EMBLEM_GLOW, 'couleurs': 'rampe EXACTE du rayon du rip',
                                   'phases': PHASES, 'frame_length_ticks': TICKS}},
        'segmentation_mesures': seg,
        'fidelite_rip': {'methode': 'moyenne RGB par matiere, meme classifieur pixel sur le rip et sur le brut ; distance euclidienne ; seuil 35',
                         'brut': fid, 'calques_finaux': final_fid,
                         'sol_complet': round(float(np.linalg.norm(f.reshape(-1, 3).mean(0) - np.array(fid['herbe']['rip_rgb']))), 1),
                         'sol_complet_ecartes': {g['file']: round(float(np.linalg.norm(rgb(raw_path(g)).reshape(-1, 3).mean(0)
                                                                                      - np.array(fid['herbe']['rip_rgb']))), 1)
                                                 for g in GEN if g.get('ecarte') and g['lot'] == LOT1},
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
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'entry_px': entry_px, 'boss_px': boss_px, 'objective_px': objective_px, 'path_found_16x16': reach,
                   'path_to_boss': reach_boss, 'path_to_objective': reach_obj, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si > 25 % hors praticable (prairie, herbe, ombres, fleurs, marches relies au bord sud)',
                   'boss': 'case 2 x 2 libre au centre de la prairie',
                   'objectif': 'case 2 x 2 libre la plus haute sous la stele sanctuaire de Celebi',
                   'fin': 'aucune sortie, aucun warp, pas de donjon_seuil ; haies, arbres, souche, sanctuaire et fond bloques'},
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
                      'final': {k: v['distance_rip'] for k, v in final_fid.items()}, 'tiles': sum(counts.values())}, indent=1))


if __name__ == '__main__':
    build()
