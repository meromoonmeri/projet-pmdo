"""Fin Mt. Thunder V3 (FMT3) — sommet d'orage de l'aiguille rocheuse, format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Demande : « bon avance » (3 octobre, après FCV3) : suite des fins de donjon restantes de la série dans l'ordre du mod,
prolongeant l'entrée EMT1 (Mt. Thunder). Biome et portée choisis par l'agent, à confirmer. Préfixe FMT3 (FMT1 et FTN1
sont pris sur des branches sœurs).
Référence `Game Boy Advance - Pokemon Mystery Dungeon_ Red Rescue Team - Dungeon Boss Rooms - Mt. Thunder.png`
(432 x 498), dont la partie haute (y < 352) est la salle de boss du sommet de Mt. Thunder (sans grotte).
Méthode « textures canoniques » = rendu généré RÉFÉRENCÉ (rip passé au générateur en images=) :
- decor.png : sommet fermé 4:3 (1200 x 896), arrivée au sud sur la crête, plateau à deux gradins, aiguille rocheuse
  sommitale au nord au-dessus de la mer d'orage (sans grotte sombre) ;
- sol_complet.png : sable seul d'EMT1 réutilisé sans nouvelle génération (même sha256).
Calques : sol complet, sable, cailloux, pics, falaise, piton (aiguille sommitale), ciel, nuages. Pas de `profondeur` ni
de `seuil`.
Animations, chacune sur son calque, boucles fermées, 48 x 5 ticks (4 s), avec les fonctions, éclairs, arc Flash et
couleurs Normal / Fading EXACTS de la planche chargés depuis EMT1 :
- lueurs : l'arc « Flash » du rip s'allume sur les nuages au pied de chaque éclair ;
- eclairs : les 4 éclairs du rip (6 frappes par boucle, une toutes les 8 phases ; Normal 2 phases puis Fading 2 phases).
Scène : 240 ticks = 4 s.
Marqueurs : `entrance` (sud), `boss` (centre du plateau), `objectif` (pied de l'aiguille rocheuse au nord).
Aucune sortie, aucun warp, pas de `donjon_seuil`.
Lancer : .venv/bin/python source/fin_mt_thunder_v3/build.py
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
REF_SCENE_H = 352
OUT = R / 'renders/fin_mt_thunder_v3'
STAGE = R / '.cache/fin_mt_thunder_v3/fin_mt_thunder'
NAMESPACE = 'fin_mt_thunder'
ASSET = 'fmt3_fin_mt_thunder'
PFX = 'FMT3'
W, H = 768, 576
SRC = (1200, 896)
PHASES, TICKS = 48, 5
LOOP_TICKS = 240
LOT = 'source/fin_mt_thunder_v3'


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


EMT1 = loadmod('emt1_build', R / 'source/entree_mt_thunder_sud_nord_v1/build.py')
V1 = EMT1.V1
JM, BM = EMT1.JM, EMT1.BM
assert (JM.W, JM.H, JM.SRC) == (W, H, SRC)
keep_large, cell_grid, close_, open_ = EMT1.keep_large, EMT1.cell_grid, EMT1.close_, EMT1.open_
down_class, down_full, rgba, quantize_group = EMT1.down_class, EMT1.down_full, EMT1.rgba, EMT1.quantize_group
sha, rgb, lum_of, materials, fidelity, fidelity_clouds_one_group = (
    EMT1.sha, EMT1.rgb, EMT1.lum_of, EMT1.materials, EMT1.fidelity, EMT1.fidelity_clouds_one_group)
rip_sheet, sprite, strike_state, strike_boxes, anim_frames = (
    EMT1.rip_sheet, EMT1.sprite, EMT1.strike_state, EMT1.strike_boxes, EMT1.anim_frames)
BOLTS, FLASH_BOX, SWATCH, STRIKES, NORMAL_PH, FADING_PH = (
    EMT1.BOLTS, EMT1.FLASH_BOX, EMT1.SWATCH, EMT1.STRIKES, EMT1.NORMAL_PH, EMT1.FADING_PH)

GEN = [
    {'file': 'decor.png',
     'images': ['source/entree_mt_thunder_sud_nord_v1/bruts/decor.png', REF_NAME],
     'prompt':
     "Edit the first pixel-art map, keeping the EXACT same 1200x896 wide 4:3 framing, pixel-art style, pale yellow "
     "sandy ground with tiny grey pebbles, brown rocky cliff edges, pointed tan rock spikes, scalloped storm clouds "
     "in grey-purple tones, and dark grey storm sky as the two reference images (Pokemon Mystery Dungeon Mt. Thunder "
     "summit boss room): replace the northern cave crag and dark cave hole at the top center with a CLOSED summit "
     "cliff edge overlooking the dark storm sky (NO dark cave opening, NO hole), with a tall pointed brown rock "
     "summit crag / spire standing at the top-center edge of the sandy plateau (where the boss perches) flanked by "
     "two smaller pointed tan rock spikes, and the pale yellow sand leading right up to the foot of the northern rock "
     "spire. Keep the wide two-tiered sandy summit plateau, the southern sandy ridge path rising out of the "
     "white/grey clouds at the bottom edge center, the sea of scalloped storm clouds on the left and right sides, and "
     "the dark storm sky across the top edge. No lightning bolts painted on the image, no characters, no text, no UI, "
     "no border.",
     'essais': 'premier essai ; conforme (sable 6.6, roche 16.2, ciel 10.7, nuages sombres 14.1, nuages clairs 14.2)'},
    {'file': 'sol_complet.png',
     'images': [REF_NAME],
     'prompt':
     "REUTILISE sans nouvelle generation : sol complet d'EMT1 (source/entree_mt_thunder_sud_nord_v1/bruts/"
     "sol_complet.png, meme sha256). Prompt d'origine : Fill the ENTIRE image edge to edge with only the pale yellow "
     "sandy ground texture from the reference image's summit plateau: same pale yellow sand colour, same subtle "
     "pixel-art speckle texture and faint darker patches, keep the texture detail. No pebbles, no rocks, no cliffs, "
     "no clouds, no dark areas. Wide landscape 4:3.",
     'essais': 'copie du sol_complet d EMT1 (meme biome, fond plein) : aucune generation supplementaire'},
]

PALETTE_GROUPS = {
    'sable': (['sol_complet', 'sable'], 32),
    'roche': (['cailloux', 'pics', 'falaise', 'piton'], 96),
    'orage': (['ciel', 'nuages'], 32),
}
STATIC = ['sable', 'cailloux', 'pics', 'falaise', 'piton', 'ciel', 'nuages']
ANIMS = ['lueurs', 'eclairs']


def classify(a):
    """Seuils mesurés sur le brut (1200 x 896), sans grotte sombre (sommet fermé) :
    sable = r > 195, g > 175, r-b > 45, fermé/ouvert 2 px, > 20000 px, trous bouchés ; relief = sable + roche brune
    (r > g >= b, r-b >= 20), fermé 3 px, trous bouchés, > 50000 px ; îlots = trous du sable qui ne sont pas du sable,
    ouverts 1 px, fermés 2 px et bouchés : >= 150 px = pics (et pierres moussues), 12 à 150 px = cailloux ;
    piton = aiguille rocheuse sommitale au nord (roche du relief à y < 205 et 520 < x < 680) ; falaise = le reste de la
    roche ; ciel = gris de lum < 90 hors relief, ouvert 3 px, relié au bord haut ; nuages = le reste."""
    r, g, b = a.transpose(2, 0, 1); lum = lum_of(a)
    hh, ww = lum.shape; yy, xx = np.mgrid[:hh, :ww]
    sandc = (r > 195) & (g > 175) & (r - b > 45)
    # Les deux pics latéraux de la couronne nord (x 485..545 et 655..715, y < 185) ont un flanc éclairé jaune-beige :
    # ils appartiennent au piton sommital, pas au sable praticable.
    crown_flanks = (yy < 185) & (((xx > 485) & (xx < 548)) | ((xx > 652) & (xx < 715)))
    sandc &= ~crown_flanks
    rockc = ((r > g) & (g >= b) & (r - b >= 20) & ~sandc) | (crown_flanks & (lum > 75) & ((r - b) > 20))
    sand = keep_large(open_(close_(sandc, 2), 2), 20000); sand = nd.binary_fill_holes(sand)
    land = close_(sand | rockc, 3)
    land = nd.binary_fill_holes(land)
    land = keep_large(land, 50000)
    isl = open_(sand & ~sandc, 1)
    isl = nd.binary_fill_holes(close_(isl, 2)) & sand
    il, inn = nd.label(isl); sz = nd.sum(isl, il, range(1, inn + 1))
    pics = np.isin(il, [i + 1 for i, v in enumerate(sz) if v >= 150])
    cail = np.isin(il, [i + 1 for i, v in enumerate(sz) if 12 <= v < 150])
    rock = land & ~sand
    piton = rock & (yy < 205) & (xx > 485) & (xx < 715)
    fal = rock & ~piton
    sky = ~land
    ciel = keep_large(open_(sky & (lum < 90), 3), 2000)
    lab, _ = nd.label(ciel); t = np.unique(lab[0]); ciel = np.isin(lab, t[t > 0])
    masks = dict(pics=pics, cailloux=cail, sable=sand & ~pics & ~cail, piton=piton, falaise=fal,
                 ciel=ciel, nuages=sky & ~ciel)
    ys_p, xs_p = np.nonzero(piton)
    seg = {'piton_y': [int(ys_p.min()), int(ys_p.max())], 'piton_x': [int(xs_p.min()), int(xs_p.max())],
           'pics': int(sum(v >= 150 for v in sz)), 'cailloux': int(sum(12 <= v < 150 for v in sz))}
    return masks, seg


def write_ora(path, layers):
    import xml.etree.ElementTree as ET
    root = ET.Element('image', w=str(W), h=str(H), name='Fin Mt. Thunder V3 (FMT3)')
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
    o.update(Name={'DefaultText': 'Fin Mt. Thunder - sommet d orage (4:3)', 'LocalTexts': {}}, AssetName=ASSET,
             Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0},
             ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Rendu genere 4:3 reference sur le rip Mt. Thunder (Red Rescue Team) ; eclairs et '
                     'lueurs animes (sprites et couleurs Normal / Fading exacts du rip), aiguille rocheuse sommitale '
                     'au nord. Collisions de base a verifier. Aucune sortie ni warp. Biome et portee choisis par l agent.')
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
  <Description>Projet d'edition : zone de fin de donjon de Mt. Thunder (sommet d'orage de l'aiguille rocheuse), generee au format 4:3 (ref. planche Mt. Thunder), eclairs et lueurs animes. Pas une aventure jouable.</Description>
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
    a, f, ref_all = rgb(RAW / 'decor.png'), rgb(RAW / 'sol_complet.png'), rgb(REF)
    ref = ref_all[:REF_SCENE_H]
    assert a.shape[:2] == f.shape[:2] == (SRC[1], SRC[0])
    m, seg = classify(a)
    order = ['pics', 'cailloux', 'sable', 'piton', 'falaise', 'ciel', 'nuages']
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
    cand = ex['sable'] | ex['cailloux']
    cl, _ = nd.label(cand); seed = cl[H - 1][cand[H - 1]]
    walk = np.isin(cl, np.unique(seed[seed > 0]))
    Image.fromarray((walk * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_praticable.png')
    bolts, flash, sw = rip_sheet(ref_all)
    for k, m_ in bolts.items():
        Image.fromarray(sprite(m_, sw['normal'][1])).save(OUT / 'poses' / f'{PFX}_eclair_{k}.png')
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
    # Boss : centre du plateau supérieur (y ~ 192, x ~ 384).
    tgt = (W // 16 - 1, 24)
    boss_c = min(((cx, cy) for cy in range(gh_) for cx in range(gw_) if free(cx, cy)),
                 key=lambda c: (c[0] - tgt[0]) ** 2 + (c[1] - tgt[1]) ** 2)
    boss_px = [boss_c[0] * 8, boss_c[1] * 8]
    # Objectif : au pied de l'aiguille rocheuse sommitale au nord : case libre la plus haute de la colonne centrale (+-40 px).
    mid = W // 16
    cands = [(cx, cy) for cy in range(gh_) for cx in range(mid - 5, mid + 5) if free(cx, cy)]
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
    items = [(f'eclair_{k}', sprite(bolts[k], sw['normal'][1])) for k in BOLTS] + [('flash', sprite(flash, sw['normal'][0]))]
    cw = 42 * 2 + 8; ch = 128 * 2 + 8
    sheet = Image.new('RGBA', (5 * cw + 8, ch + 8), (64, 56, 64, 255))
    for i, (_, p) in enumerate(items):
        im = Image.fromarray(p); im = im.resize((im.width * 2, im.height * 2), Image.Resampling.NEAREST)
        cx0 = 8 + i * cw
        sheet.alpha_composite(im, (cx0 + (cw - 8 - im.width) // 2, 8 + (ch - 8 - im.height) // 2))
    sheet.save(OUT / 'review' / f'{PFX}_planche_poses.png')
    write_ora(OUT / f'{PFX}_fin_mt_thunder_calques.ora',
              {f'{i:02d}_{t}' + ('_f00' if len(fr) > 1 else ''): fr[0] for i, (t, fr, _) in enumerate(stack_named)})
    counts = ground_project([(t.replace('_', ' ') + (f' {len(fr)} phases' if len(fr) > 1 else ''), fr, tk)
                             for t, fr, tk in stack_named], blocked, entry_px, boss_px, objective_px, gfx, tools)
    fid = fidelity(a, ref)
    final_fid = {}
    for key, mat, nm in (('sable', 'sable', 'sable'), ('roche', 'roche', 'falaise'), ('ciel', 'ciel', 'ciel'),
                         ('nuages_sombres', 'nuages_sombres', 'nuages'), ('nuages_clairs', 'nuages_clairs', 'nuages')):
        lay = layers[nm]; px = lay[lay[..., 3] == 255][:, :3].astype(float)
        sel = materials(px.reshape(-1, 1, 3))[mat][:, 0]
        final_fid[key] = {'calque': nm, 'matiere': mat, 'rgb': [round(float(v), 1) for v in px[sel].mean(0)],
                          'distance_rip': round(float(np.linalg.norm(px[sel].mean(0) - np.array(fid[mat]['rip_rgb']))), 1)}
    boxes = strike_boxes(bolts, flash)
    manifest = {
        'lot': 'fin_mt_thunder_v3', 'prefix': PFX, 'format': '4:3 vaste', 'type': 'fin de donjon',
        'size_px': [W, H], 'grid_8px': [W // 8, H // 8],
        'base': 'branche de session (EMT1 pour les fonctions eclairs/lueurs et le brut sol_complet, EWC1/ESN1 pour les utilitaires) ; aucun emprunt aux branches soeurs',
        'biome': 'fin de Mt. Thunder (sommet d orage de l aiguille rocheuse, prolonge EMT1), biome et portee choisis par l agent (« bon avance »), a confirmer',
        'method': 'textures canoniques = rendu genere REFERENCE : rip passe au generateur ; decor de sommet ferme sans grotte, '
                  'sol complet d EMT1 reutilise, eclairs et arc Flash releves pixel par pixel sur la planche du rip',
        'reference_da': {'file': REF.name, 'sha256': sha(REF), 'scene_rows': [0, REF_SCENE_H],
                         'titre': 'Pokemon Mystery Dungeon: Red Rescue Team - Dungeon Boss Rooms - Mt. Thunder'},
        'generation': GEN,
        'raw_inputs': [{'file': f'{LOT}/bruts/{g["file"]}', 'sha256': sha(RAW / g['file']),
                        'size': list(Image.open(RAW / g['file']).size)} for g in GEN],
        'sol_complet': {'recalage_px': 'non applicable : texture de sable plein reutilisee d EMT1 (meme sha256)',
                        'rgb_moyen': [round(float(v), 1) for v in f.reshape(-1, 3).mean(0)],
                        'distance_rip': round(float(np.linalg.norm(f.reshape(-1, 3).mean(0) - np.array(fid['sable']['rip_rgb']))), 1)},
        'segmentation_mesures': seg,
        'fidelite_rip': {'methode': 'moyenne RGB par matiere sur la partie scene du rip (y < 352), meme classifieur pixel des deux cotes ; '
                                    'les gris de l orage sont mesures par ton (ciel < 90 <= nuages sombres < 170 <= nuages clairs) ; seuil 35',
                         'brut': fid, 'calques_finaux': final_fid,
                         'nuages_un_seul_groupe_ecarte': {'distance': fidelity_clouds_one_group(a, ref),
                                                          'raison': 'moyenne unique des tons discrets (64..240) : depend des proportions ciel / nuages clairs du cadrage, pas de la palette'},
                         'eclairs': 'pixels et couleurs Normal / Fading EXACTS de la planche du rip'},
        'normalization': {'scale': JM.SCALE, 'scaled': [JM.SCALED_W, H], 'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
                          'methode': 'moyenne ponderee par classe (BOX), attribution exclusive par poids maximal',
                          'palettes': {g: {'calques': k, 'couleurs': n} for g, (k, n) in PALETTE_GROUPS.items()}},
        'segmentation': classify.__doc__.split('\n', 1)[1].strip(),
        'layers': layer_list,
        'eclairs': {'phases': PHASES, 'frame_length_ticks': TICKS,
                    'boites_rip': {str(k): list(v) for k, v in BOLTS.items()}, 'flash_rip': list(FLASH_BOX),
                    'couleurs': {k: [list(c) for c in v] for k, v in sw.items()},
                    'phases_par_frappe': {'normal': NORMAL_PH, 'fading': FADING_PH},
                    'frappes': [list(s) for s in STRIKES],
                    'arcs': [[int(b[3]), int(b[4])] for b in boxes],
                    'note_planche': 'Taken from the left side. Beside the first lightning, they all appear mirrored on the right side.',
                    'origine': 'sprites (4 eclairs + arc Flash) et couleurs Normal / Fading EXACTS de la planche du rip (fonctions d EMT1) ; '
                               'chronologie et placement crees par nous'},
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'entry_px': entry_px, 'boss_px': boss_px, 'objective_px': objective_px, 'path_found_16x16': reach,
                   'path_to_boss': reach_boss, 'path_to_objective': reach_obj, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si > 25 % hors praticable (sable, cailloux)',
                   'boss': 'case 2 x 2 libre au centre du plateau superieur',
                   'objectif': 'case 2 x 2 libre la plus haute de la colonne centrale (+-40 px), au pied de l aiguille rocheuse sommitale',
                   'fin': 'aucune sortie, aucun warp, pas de donjon_seuil ; le bord nord et les flancs sont bloques'},
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
