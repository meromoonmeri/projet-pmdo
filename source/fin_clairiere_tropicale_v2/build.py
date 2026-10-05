"""Fin Clairière tropicale V2 (FCT2) — arène du sanctuaire du lagon, format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Demande : « passons a la suite » (3 octobre, après la trilogie Forêt Brumeuse EFB1/FFB1/ZFB1) : reprise des quatre
fins de donjon restantes de la série dans l'ordre du mod, en commençant par Clairière tropicale (prolonge l'entrée
ETC1). Biome et portée choisis par l'agent, à confirmer. Préfixe FCT2 (FTC1 et FCT1 sont pris sur des branches sœurs).
Référence `large.S01P03A.png.84e22fb77c4061e77b0f546545fed2c7.png` (456 x 456).
Méthode « textures canoniques » = rendu généré RÉFÉRENCÉ (rip passé au générateur en images=) :
- decor_magenta.png : arène fermée 4:3 (1200 x 896), arrivée au sud, deux vasques de lagon en magenta pur #FF00FF
  bordées d'une rive de terre, tertre rocheux et autel-sanctuaire de pierre sculptée au nord (sans bouche sombre) ;
  édité depuis un premier essai écarté (jungle trop sombre 46,8 > 35 et coins plats ; gardé dans bruts/ecartes/)
  avec le rip en seconde référence ;
- sol_complet.png : herbe claire seule sur toute la surface, éditée depuis le décor conforme (recalée (0, 0)) ;
- temoin_sans_objets.png : décor sans palmiers, fleurs, touffes ni cailloux (recalé (0, 0)) ;
- papillons_poses.png : planche 2 x 6 d'ETC1 réutilisée sans nouvelle génération (même sha256).
Calques : sol complet, herbe, ombres, dalles, touffes, fleurs, jungle, palmiers, tertre, autel, rive.
Animations, chacune sur son calque, boucles fermées, 24 x 5 ticks, avec les fonctions, profil de vague et poses
d'ETC1 (chargées depuis le module d'entrée) :
- mer : vagues du rip (profil de 48 px et crête relevés pixel par pixel, couleurs EXACTES) dans les deux vasques,
  uniquement la bande sombre du rip au contact de la rive (aucun liseré clair) ;
- papillons : poses générées d'ETC1 ; battement 8 phases, vol en huit fermé sur 24 phases autour de l'arène.
Scène : PPCM(120, 120) = 120 ticks = 2 s.
Marqueurs : `entrance` (sud), `boss` (centre de l'arène), `objectif` (pied de l'autel-sanctuaire au nord).
Aucune sortie, aucun warp, pas de `donjon_seuil`.
Lancer : .venv/bin/python source/fin_clairiere_tropicale_v2/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
REF_NAME = 'large.S01P03A.png.84e22fb77c4061e77b0f546545fed2c7.png'
REF = R / REF_NAME
OUT = R / 'renders/fin_clairiere_tropicale_v2'
STAGE = R / '.cache/fin_clairiere_tropicale_v2/fin_clairiere_tropicale'
NAMESPACE = 'fin_clairiere_tropicale'
ASSET = 'fct2_fin_clairiere_tropicale'
PFX = 'FCT2'
W, H = 768, 576
SRC = (1200, 896)
PHASES, TICKS = 24, 5
LOOP_TICKS = 120
LOT = 'source/fin_clairiere_tropicale_v2'


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


ETC1 = loadmod('etc1_build', R / 'source/entree_clairiere_tropicale_sud_nord_v1/build.py')
V1 = ETC1.V1
JM, BM = ETC1.JM, ETC1.BM
assert (JM.W, JM.H, JM.SRC) == (W, H, SRC)
keep_large, cell_grid, close_, open_ = ETC1.keep_large, ETC1.cell_grid, ETC1.close_, ETC1.open_
down_class, down_full, rgba, quantize_group = ETC1.down_class, ETC1.down_full, ETC1.rgba, ETC1.quantize_group
sha, rgb, lum_of = ETC1.sha, ETC1.rgb, ETC1.lum_of
materials, fidelity, recalage, flower_px = ETC1.materials, ETC1.fidelity, ETC1.recalage, ETC1.flower_px
wave_model, sea_frames, sheet_poses, butterfly_frames = (
    ETC1.wave_model, ETC1.sea_frames, ETC1.sheet_poses, ETC1.butterfly_frames)
WAVE_COL, WAVE_Y0, WAVE_P, CREST_X, WAVE_STEP = (
    ETC1.WAVE_COL, ETC1.WAVE_Y0, ETC1.WAVE_P, ETC1.CREST_X, ETC1.WAVE_STEP)
BANDE, CALME, SHORE_BAND, SHORE_CALM = ETC1.BANDE, ETC1.CALME, ETC1.SHORE_BAND, ETC1.SHORE_CALM
POSE_K, POSE_COV, POSE_WIN, FLAP = ETC1.POSE_K, ETC1.POSE_COV, ETC1.POSE_WIN, ETC1.FLAP

FLIGHTS = [
    ('orange', 305, 240, 32, 14, 0),
    ('jaune', 465, 240, 32, 14, 7),
    ('jaune', 310, 325, 32, 14, 13),
    ('orange', 460, 325, 32, 14, 19),
]
assert PHASES % len(FLAP) == 0

GEN = [
    {'file': 'ecartes/decor_magenta_essai1_jungle_sombre.png',
     'images': [REF_NAME, 'source/entree_clairiere_tropicale_sud_nord_v1/bruts/decor_magenta.png'],
     'ecarte': True,
     'prompt':
     "Use EXACTLY the same pixel-art style, soft muted light yellow-green clearing grass with fine blade texture, "
     "dark green dense jungle bushes with leafy outlines, coconut palm trees, bright red/yellow/cyan/pink hibiscus "
     "flower clusters, tan sandy stepping-stone slabs, small grey pebbles, and brown earth bank cliff edges as the "
     "two reference images (Pokemon Mystery Dungeon tropical clearing). Create a NEW top-down boss arena map in WIDE "
     "LANDSCAPE 4:3 (1200x896), zoomed out so the area feels vast. Layout: CLOSED boss room (NO sea at the bottom "
     "edge, NO wooden jetty, NO dark cave hole). The player arrives from the SOUTH edge center through a wide "
     "corridor of soft muted light yellow-green grass with a trail of tan stepping-stone slabs between dense "
     "dark-green jungle bushes. The path opens into a large round central grass clearing (boss arena). On the LEFT "
     "and RIGHT sides of the clearing are two tropical lagoon pools recessed into the clearing with brown earth bank "
     "cliff edges along their top shore, and their water surface filled completely with flat solid pure magenta "
     "#FF00FF (no waves, no white foam line). At the NORTH top-center of the clearing stands a closed brown earth "
     "and rock sanctuary mound overgrown with dense jungle bushes, with a carved tan stone shrine pedestal built "
     "into its front face (NO dark cave opening); the grass and stepping-stone slabs lead right up to the foot of "
     "this northern stone shrine mound. Four coconut palm trees, colorful hibiscus flower clusters, small green bush "
     "tufts and small grey pebbles are placed around the clearing edges away from the center. Dense dark green "
     "jungle fills all outer borders. No characters, no signpost, no text, no UI, no border.",
     'essais': 'ECARTE : jungle trop sombre (75.2,114.1,22.9) contre (103.8,138.7,50.7) sur le rip, distance '
               '46.8 > 35, et quatre coins exterieurs en aplat vert sombre. Composition gardee comme base de '
               'l edition suivante'},
    {'file': 'decor_magenta.png',
     'images': [f'{LOT}/bruts/ecartes/decor_magenta_essai1_jungle_sombre.png', REF_NAME],
     'prompt':
     "Edit the first pixel-art map, keeping the EXACT same framing (1200x896), layout, central grass clearing, stone "
     "shrine in the north mound, stepping stones, palm trees, flowers, and the two flat pure magenta #FF00FF lagoon "
     "pools: (1) Fill the four flat dark corners at the outer edges with dense textured leafy jungle bushes so the "
     "jungle foliage covers the entire outer border with no flat dark background corners; (2) Recolour all the "
     "jungle bushes to match the second reference image's exact softer, slightly lighter olive-green jungle foliage "
     "palette (less dark, slightly warmer muted green). Keep the clearing grass, stepping stones, north stone shrine "
     "mound, and flat #FF00FF magenta pools untouched. No text, no border.",
     'essais': 'premier essai d edition ; conforme (herbe 24.2, jungle 16.8, dalles 15.4)'},
    {'file': 'sol_complet.png',
     'images': [f'{LOT}/bruts/decor_magenta.png', REF_NAME],
     'prompt':
     "Edit the first pixel-art map, same 1200x896 framing and exact same pixel-art style: replace ALL the jungle "
     "bushes, palm trees, flower clusters, bush tufts, grey pebbles, lagoon pools, earth banks, stone shrine mound, "
     "and stepping stones with the exact same soft muted light yellow-green clearing grass with fine blade texture "
     "so the entire 1200x896 image is covered in seamless clearing grass only. Keep the exact grass pixels inside "
     "the existing clearing untouched at (0,0) alignment. No rocks, no bushes, no water, no text, no border.",
     'essais': 'premier essai ; recale (0, 0)'},
    {'file': 'temoin_sans_objets.png',
     'images': [f'{LOT}/bruts/decor_magenta.png'],
     'prompt':
     "Edit this pixel-art map, keeping the EXACT same 1200x896 framing and pixel-art style at (0,0) alignment: "
     "remove every coconut palm tree, every colorful flower cluster, every small green bush tuft, and every small "
     "grey pebble, replacing each removed object with the background immediately around it (either the dense green "
     "jungle bushes or the soft light yellow-green clearing grass). Keep the northern brown earth and rock mound, "
     "the carved stone shrine pedestal, the tan stepping-stone slabs, the two flat pure magenta #FF00FF lagoon "
     "pools, and their brown earth bank cliff edges 100% identical to the original image. No text, no border.",
     'essais': 'premier essai ; temoin de segmentation recale (0, 0), jamais exporte'},
    {'file': 'papillons_poses.png',
     'images': [REF_NAME],
     'prompt':
     "REUTILISEE sans nouvelle generation : planche de l'entree ETC1 (source/entree_clairiere_tropicale_sud_nord_v1/"
     "bruts/papillons_poses.png, meme sha256), fenetres et reduction inchangees. Prompt d'origine : Pixel-art sprite "
     "sheet on a flat pure magenta #FF00FF background, same pixel style and bright colors as the reference (Pokemon "
     "Mystery Dungeon tropical clearing). 2 rows of 6 small separate sprites, evenly spaced. Row 1: a small "
     "orange-red butterfly seen from above flapping its wings, six poses from wings wide open to wings closed and "
     "back. Row 2: a small bright yellow butterfly seen from above, same six flapping poses. Dark outlines, hard "
     "pixel edges, no text.",
     'essais': 'copie de la planche ETC1 (meme biome, memes poses) : aucune generation supplementaire'},
]

PALETTE_GROUPS = {
    'herbe': (['sol_complet', 'herbe', 'ombres'], 96),
    'dalles_touffes': (['dalles', 'touffes'], 64),
    'fleurs': (['fleurs'], 48),
    'vegetation': (['jungle', 'palmiers'], 96),
    'terre_pierre': (['tertre', 'autel', 'rive'], 64),
}
STATIC = ['herbe', 'ombres', 'dalles', 'touffes', 'fleurs', 'jungle', 'palmiers', 'tertre', 'autel', 'rive']
ANIMS = ['mer', 'papillons']


def classify(a, t):
    """a : décor, t : témoin sans objets. Seuils mesurés sur le brut :
    mer = deux vasques magenta (> 5000 px) + filet clair/rose d'anti-aliasing à <= 7 px du magenta ;
    objets = écart décor / témoin lissé 3 px > 26, fermé 4 px, trous bouchés ; palmiers > 2500 px (6 cocotiers) ;
    fleurs = >= 5 % de pixels de fleur saturés ; le reste = touffes et cailloux ;
    rive = parois de terre brune au-dessus des deux vasques (dw < 95, y 240..560) ;
    tertre et autel = massif de terre et de roche au nord (y < 300, x 340..860), dont l'autel-sanctuaire de pierre
    sculptée au centre (y 130..258, x 552..648) est isolé sur son propre calque `autel` ;
    dalles = dalles de sable dans la clairière et le couloir sud (y > 255, 30 à 4000 px) ;
    herbe = lum lissée 9 px > 175 ; ombres = herbe assombrie au pied du tertre et de l'autel ; jungle = le reste."""
    r, g, b = a.transpose(2, 0, 1); lum = lum_of(a)
    hh, ww = lum.shape; yy, xx = np.mgrid[:hh, :ww]
    mag = (r - g > 60) & (b - g > 60)
    water = keep_large(mag, 5000)
    filet = (((b > g - 15) & (lum > 120)) | ((r - g > 20) & (b - g > 10))) & nd.binary_dilation(water, iterations=7) & ~water
    water |= filet
    diff = nd.uniform_filter(np.abs(a - t).mean(2).astype(float), 3)
    obj = keep_large(nd.binary_fill_holes(close_(diff > 26, 4)), 60) & ~water
    ol, on = nd.label(obj); fpx = flower_px(a)
    pal, fle, tou = (np.zeros_like(obj) for _ in range(3)); kinds = {'palmiers': 0, 'fleurs': 0, 'touffes': 0}
    for i, s in enumerate(nd.find_objects(ol)):
        m = ol[s] == i + 1
        if m.sum() > 2500:
            pal[s] |= m; kinds['palmiers'] += 1
        elif fpx[s][m].mean() > 0.05:
            fle[s] |= m; kinds['fleurs'] += 1
        else:
            tou[s] |= m; kinds['touffes'] += 1
    dw = nd.distance_transform_edt(~water)
    grassy = (g > r) & (g - b > 65) & (lum > 150)
    bankc = (r > g + 5) & (r - b > 25) & ~water & ~obj & (dw < 95) & (yy > 240) & (yy < 560) & ((xx < 400) | (xx > 800))
    rive = keep_large(close_(bankc, 3), 2000)
    rive = nd.binary_fill_holes(rive | water) & ~water & ~obj & ~grassy & (dw < 95) & (yy > 240) & (yy < 560)
    rive = keep_large(open_(rive, 1), 1500)
    rockc = (r > g + 3) & (r - b > 35) & (yy < 300) & (xx > 340) & (xx < 860) & ~water & ~obj & ~rive
    tertre_all = keep_large(nd.binary_fill_holes(close_(rockc, 4)), 15000) & ~obj & ~water & ~rive
    shrine_box = (yy >= 130) & (yy <= 258) & (xx >= 552) & (xx <= 648)
    autel = tertre_all & shrine_box
    tertre = tertre_all & ~autel
    dal = (r >= g) & (r - b > 55) & (lum > 140) & ~tertre & ~autel & ~obj & ~rive & ~water & (yy > 255)
    dal = nd.binary_fill_holes(close_(dal, 2)) & ~tertre & ~autel & ~water
    dl, dn = nd.label(dal); ds = nd.sum(dal, dl, range(1, dn + 1))
    dal = np.isin(dl, [i + 1 for i, v in enumerate(ds) if 30 <= v <= 4000])
    her = (nd.uniform_filter(lum, 9) > 175) & ~water & ~tertre & ~autel & ~rive
    her = keep_large(open_(close_(her, 3), 3), 20000)
    her = nd.binary_fill_holes(her) & ~obj & ~dal & ~water & ~rive & ~tertre & ~autel
    sd = np.sqrt(np.maximum(nd.uniform_filter(lum ** 2, 7) - nd.uniform_filter(lum, 7) ** 2, 0))
    Ls = nd.uniform_filter(lum, 5); db = nd.distance_transform_edt(~(tertre | autel))
    free = ~(obj | dal | her | water | rive | tertre | autel)
    omb = (g > r) & (g - b > 55) & (Ls > 120) & (Ls < 188) & (db <= 45) & (sd < 14) & free
    omb = close_(omb, 2) & free
    ol2, _ = nd.label(omb); tch = np.unique(ol2[nd.binary_dilation(her | dal, iterations=2) & omb])
    omb = np.isin(ol2, tch[tch > 0])
    ys_a, xs_a = np.nonzero(autel); ay0, ay1 = int(ys_a.min()), int(ys_a.max()); ax0, ax1 = int(xs_a.min()), int(xs_a.max())
    front = (yy > ay1) & (yy < ay1 + 40) & (xx >= ax0) & (xx <= ax1)
    omb |= front & free & ~omb
    jungle = ~(water | pal | fle | tou | rive | tertre | autel | dal | her | omb)
    masks = dict(mer=water, palmiers=pal, fleurs=fle, touffes=tou, rive=rive,
                 tertre=tertre, autel=autel, dalles=dal, ombres=omb, herbe=her, jungle=jungle)
    seg = {'objets': int(on), 'objets_par_type': kinds, 'filet_clair_rendu_a_l_eau_px': int(filet.sum()),
           'autel_y': [ay0, ay1], 'autel_x': [ax0, ax1],
           'ombres_lum': round(float(lum[omb].mean()), 1), 'herbe_lum': round(float(lum[her].mean()), 1)}
    return masks, seg


def write_ora(path, layers):
    import xml.etree.ElementTree as ET
    root = ET.Element('image', w=str(W), h=str(H), name='Fin Clairiere tropicale V2 (FCT2)')
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
    o.update(Name={'DefaultText': 'Fin Clairiere tropicale - sanctuaire du lagon (4:3)', 'LocalTexts': {}},
             AssetName=ASSET, Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None,
             ViewOffset={'X': 0, 'Y': 0}, ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Rendu genere 4:3 reference sur le rip Clairiere tropicale ; deux vasques de lagon '
                     'animees (profil et couleurs exacts du rip, bande sombre contre la rive), papillons d ETC1 '
                     'reutilises, autel-sanctuaire de pierre au nord. Collisions de base a verifier. Aucune sortie '
                     'ni warp. Biome et portee choisis par l agent.')
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
  <Name>Fin Clairiere tropicale 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : zone de fin de donjon de la Clairiere tropicale (arene du sanctuaire du lagon), generee au format 4:3 (ref. rip Clairiere tropicale), vasques de lagon et papillons animes. Pas une aventure jouable.</Description>
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
        for d in ['calques', 'animation', 'poses', 'masques', 'review']:
            shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['calques', 'poses', 'masques', 'review'] + [f'animation/{x}' for x in ANIMS]:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    STAGE.parent.mkdir(parents=True, exist_ok=True)
    a, f, tm, ref = (rgb(RAW / 'decor_magenta.png'), rgb(RAW / 'sol_complet.png'),
                     rgb(RAW / 'temoin_sans_objets.png'), rgb(REF))
    assert a.shape[:2] == f.shape[:2] == tm.shape[:2] == (SRC[1], SRC[0])
    m, seg = classify(a, tm)
    clair = nd.binary_erosion(m['herbe'], iterations=6)
    reg = {'sol_complet': recalage(a, f, clair),
           'temoin': recalage(a, tm, clair)}
    order = ['mer', 'palmiers', 'fleurs', 'touffes', 'rive', 'autel', 'tertre', 'dalles', 'ombres', 'herbe', 'jungle']
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
    water = ex['mer']
    # Praticable : herbe, ombres, dalles et touffes reliées au couloir sud.
    cand = ex['herbe'] | ex['ombres'] | ex['dalles'] | ex['touffes']
    cl, _ = nd.label(cand); seed = cl[H - 1, np.nonzero(cand[H - 1])[0]]
    walk = np.isin(cl, np.unique(seed[seed > 0]))
    Image.fromarray((walk * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_praticable.png')
    prof, crest = wave_model(ref)
    mer, dshore = sea_frames(water, prof, crest)
    poses, pose_pal = sheet_poses(RAW / 'papillons_poses.png')
    for name, p in poses.items():
        Image.fromarray(p).save(OUT / 'poses' / f'{PFX}_{name}.png')
    papillons = butterfly_frames(poses, FLIGHTS)
    anim = {'mer': mer, 'papillons': papillons}
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
    # Collisions : case bloquée si > 25 % hors praticable.
    blocked = cell_grid(~walk); gh_, gw_ = blocked.shape
    pxs = np.nonzero(walk[H - 8])[0]; med = int(np.median(pxs)) // 8
    ecol = min((c for c in range(gw_ - 1) if not blocked[gh_ - 2:, c:c + 2].any()), key=lambda c: abs(c - med))
    entry_px = [ecol * 8, H - 16]
    free = lambda cx, cy: 0 <= cx < gw_ - 1 and 0 <= cy < gh_ - 1 and not blocked[cy:cy + 2, cx:cx + 2].any()
    # Boss : case 2 x 2 libre la plus proche du centre de la clairière (entre les deux lagons, y ~ 296).
    tgt = (W // 16 - 1, 36)
    boss_c = min(((cx, cy) for cy in range(gh_) for cx in range(gw_) if free(cx, cy)),
                 key=lambda c: (c[0] - tgt[0]) ** 2 + (c[1] - tgt[1]) ** 2)
    boss_px = [boss_c[0] * 8, boss_c[1] * 8]
    # Objectif : au pied de l'autel-sanctuaire au nord : case libre la plus haute de la colonne centrale (+-48 px).
    mid = W // 16
    cands = [(cx, cy) for cy in range(gh_) for cx in range(mid - 6, mid + 6) if free(cx, cy)]
    top = min(cy for _, cy in cands)
    obj_c = min((c for c in cands if c[1] <= top + 1), key=lambda c: abs(c[0] - (mid - 1)))
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
    names = list(POSE_WIN); cw = 15 * 6 + 8
    sheet = Image.new('RGBA', (6 * cw + 8, 2 * cw + 8), (191, 215, 103, 255))
    for i, nm in enumerate(names):
        im = Image.fromarray(poses[nm]); im = im.resize((im.width * 6, im.height * 6), Image.Resampling.NEAREST)
        cx0, cy0 = 8 + (i % 6) * cw, 8 + (i // 6) * cw
        sheet.alpha_composite(im, (cx0 + (cw - 8 - im.width) // 2, cy0 + (cw - 8 - im.height) // 2))
    sheet.save(OUT / 'review' / f'{PFX}_planche_poses.png')
    write_ora(OUT / f'{PFX}_fin_clairiere_tropicale_calques.ora',
              {f'{i:02d}_{t}' + ('_f00' if len(fr) > 1 else ''): fr[0] for i, (t, fr, _) in enumerate(stack_named)})
    counts = ground_project([(t.replace('_', ' ') + (f' {len(fr)} phases' if len(fr) > 1 else ''), fr, tk)
                             for t, fr, tk in stack_named], blocked, entry_px, boss_px, objective_px, gfx, tools)
    fid = fidelity(a, ref)
    final_fid = {}
    for k, nm in (('herbe', 'herbe'), ('jungle', 'jungle'), ('dalles', 'dalles')):
        lay = layers[nm]; px = lay[lay[..., 3] == 255][:, :3].astype(float)
        sel = materials(px.reshape(-1, 1, 3))[k][:, 0]
        px = px[sel] if sel.sum() > 50 else px
        final_fid[nm] = {'matiere': k, 'rgb': [round(float(v), 1) for v in px.mean(0)],
                         'distance_rip': round(float(np.linalg.norm(px.mean(0) - np.array(fid[k]['rip_rgb']))), 1)}
    ecarte = rgb(RAW / GEN[0]['file'])
    manifest = {
        'lot': 'fin_clairiere_tropicale_v2', 'prefix': PFX, 'format': '4:3 vaste', 'type': 'fin de donjon',
        'size_px': [W, H], 'grid_8px': [W // 8, H // 8],
        'base': 'branche de session (ETC1 pour les fonctions mer/papillons et la planche, EWC1/ESN1 pour les utilitaires) ; aucun emprunt aux branches soeurs',
        'biome': 'fin de la Clairiere tropicale (arene du sanctuaire du lagon, prolonge ETC1), biome et portee choisis par l agent (« passons a la suite »), a confirmer',
        'method': 'textures canoniques = rendu genere REFERENCE : rip passe au generateur ; decor complet lagons en magenta, '
                  'herbe complete et temoin sans objets edites depuis le decor, planche papillons d ETC1 reutilisee',
        'reference_da': {'file': REF.name, 'sha256': sha(REF),
                         'titre': 'Clairiere tropicale et rive (titre de l audit zones_bg_audit_v1 ; jeu et scene non confirmes)'},
        'generation': GEN,
        'raw_inputs': [{'file': f'{LOT}/bruts/{g["file"]}', 'sha256': sha(RAW / g['file']),
                        'size': list(Image.open(RAW / g['file']).size), 'ecarte': bool(g.get('ecarte'))} for g in GEN],
        'recalage': {**reg, 'zones': 'herbe de la clairiere erodee de 6 px'},
        'segmentation_mesures': seg,
        'fidelite_rip': {'methode': 'moyenne RGB par matiere, meme classifieur pixel sur le rip et sur le brut ; distance euclidienne ; seuil 35',
                         'brut': fid, 'calques_finaux': final_fid,
                         'brut_ecarte': fidelity(ecarte, ref),
                         'mer': 'couleurs EXACTES du rip (test : sous-ensemble des couleurs du rip)'},
        'normalization': {'scale': JM.SCALE, 'scaled': [JM.SCALED_W, H], 'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
                          'methode': 'moyenne ponderee par classe (BOX), attribution exclusive par poids maximal',
                          'palettes': {g: {'calques': k, 'couleurs': n} for g, (k, n) in PALETTE_GROUPS.items()}},
        'segmentation': classify.__doc__.split('\n', 1)[1].strip(),
        'ombres': 'calque ombres = herbe du rendu assombrie au pied du tertre et de l autel (separee, pas inventee)',
        'layers': layer_list,
        'mer': {'phases': PHASES, 'frame_length_ticks': TICKS, 'profil': [list(c) for c in prof], 'periode_px': WAVE_P,
                'profil_source': f'rip, colonne x = {WAVE_COL}, rangees {WAVE_Y0}..{WAVE_Y0 + WAVE_P - 1}',
                'crete': crest, 'crete_source': f'rip, premiere rangee (215,231,247) par colonne, x = {CREST_X[0]}..{CREST_X[1] - 1}',
                'pas_px': WAVE_STEP, 'sens': 'vers le nord (la rive)', 'bande_rive': list(BANDE), 'calme': list(CALME),
                'rive_px': {'bande': SHORE_BAND, 'calme': SHORE_CALM},
                'liseré': 'aucun : uniquement la bande sombre du rip contre la rive',
                'origine': 'profil, crete et couleurs EXACTS du rip (fonctions d ETC1) ; defilement dans les deux vasques cree par nous'},
        'papillons': {'poses': {k: list(v) for k, v in POSE_WIN.items()}, 'reduction': f'x1/{POSE_K}', 'couverture_min': POSE_COV,
                      'fond': 'magenta pur et pixels teintes de magenta (r-g > 60 et b-g > 60), ni gardes ni recolores ; '
                              'chaque fenetre ne garde que la composante qui contient son centre (voisins exclus)',
                      'palette': [[int(round(c)) for c in p] for p in pose_pal], 'battement': FLAP,
                      'vols': [list(fl) for fl in FLIGHTS], 'phases': PHASES, 'frame_length_ticks': TICKS,
                      'origine': 'planche et poses d ETC1 reutilisees (meme sha256) ; trajectoires autour de l arene creees par nous'},
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'entry_px': entry_px, 'boss_px': boss_px, 'objective_px': objective_px, 'path_found_16x16': reach,
                   'path_to_boss': reach_boss, 'path_to_objective': reach_obj, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si > 25 % hors praticable (herbe, ombres, dalles, touffes reliees)',
                   'boss': 'case 2 x 2 libre au centre de la clairiere entre les deux lagons',
                   'objectif': 'case 2 x 2 libre la plus haute de la colonne centrale (+-48 px), au pied de l autel-sanctuaire',
                   'fin': 'aucune sortie, aucun warp, pas de donjon_seuil ; le bord nord et les flancs sont bloques'},
        'pmdo': {'target': '0.8.12', 'asset': ASSET, 'namespace': NAMESPACE, 'tiles_per_bank': counts, 'banks': list(counts),
                 'runtime_tested': False, 'warp': 'aucun'},
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    print(json.dumps({'entry': entry_px, 'boss': boss_px, 'objectif': objective_px, 'blocked': int(blocked.sum()),
                      'walkable': int((~blocked).sum()), 'seg': seg, 'reg': reg,
                      'px': {k: int(v.sum()) for k, v in ex.items()},
                      'fidelite': {k: v['distance'] for k, v in fid.items()},
                      'final': {k: v['distance_rip'] for k, v in final_fid.items()}, 'tiles': sum(counts.values())}, indent=1))


if __name__ == '__main__':
    build()
