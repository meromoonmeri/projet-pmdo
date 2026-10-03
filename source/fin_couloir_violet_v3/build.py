"""Fin Couloir violet V3 (FCV3) — arène du monolithe rocheux, format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Demande : « bon avance » (3 octobre, après FCT2) : suite des fins de donjon restantes de la série dans l'ordre du mod,
prolongeant l'entrée ECV1 (Couloir violet). Biome et portée choisis par l'agent, à confirmer. Préfixe FCV3 (FCV1 et
fin_couloir_violet_v2 sont pris sur des branches sœurs).
Référence `large.S05P03A.png.301f7a1eadda348357be0801e81faa2a.png` (312 x 720, 34 couleurs), dont la partie haute est
elle-même un cul-de-sac rocheux fermé sans bouche sombre.
Méthode « textures canoniques » = rendu généré RÉFÉRENCÉ (rip passé au générateur en images=) :
- decor.png : arène fermée 4:3 (1200 x 896), arrivée au sud, grande salle semée de 6 amas de rochers, cul-de-sac
  rocheux dominé par un monolithe de pierre bleu-violet au nord (sans tunnel sombre) ;
- sol_complet.png : sol mauve seul d'ECV1 réutilisé sans nouvelle génération (même sha256) ;
- poussiere_poses.png : planche de poussière d'ECV1 réutilisée sans nouvelle génération (même sha256).
Calques : sol complet, sol, ombres, gravillons, blocs, rochers, falaise, vide. Pas de `profondeur`.
Animations, chacune sur son calque, boucles fermées, 24 x 5 ticks, avec les fonctions, gravillons du rip et poses de
poussière d'ECV1 (chargées depuis le module d'entrée) :
- eboulis : 3 gravillons relevés pixel par pixel sur le rip (couleurs EXACTES), 4 chutes décalées de 6 phases ;
- poussiere : 4 poses générées d'ECV1, un nuage à chaque impact.
Scène : PPCM(120, 120) = 120 ticks = 2 s.
Marqueurs : `entrance` (sud), `boss` (centre de la salle), `objectif` (pied du monolithe au nord).
Aucune sortie, aucun warp, pas de `donjon_seuil`.
Lancer : .venv/bin/python source/fin_couloir_violet_v3/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
REF_NAME = 'large.S05P03A.png.301f7a1eadda348357be0801e81faa2a.png'
REF = R / REF_NAME
OUT = R / 'renders/fin_couloir_violet_v3'
STAGE = R / '.cache/fin_couloir_violet_v3/fin_couloir_violet'
NAMESPACE = 'fin_couloir_violet'
ASSET = 'fcv3_fin_couloir_violet'
PFX = 'FCV3'
W, H = 768, 576
SRC = (1200, 896)
PHASES, TICKS = 24, 5
LOOP_TICKS = 120
LOT = 'source/fin_couloir_violet_v3'


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


ECV1 = loadmod('ecv1_build', R / 'source/entree_couloir_violet_sud_nord_v1/build.py')
V1 = ECV1.V1
JM, BM = ECV1.JM, ECV1.BM
assert (JM.W, JM.H, JM.SRC) == (W, H, SRC)
keep_large, cell_grid, close_, open_ = ECV1.keep_large, ECV1.cell_grid, ECV1.close_, ECV1.open_
down_class, down_full, rgba, quantize_group = ECV1.down_class, ECV1.down_full, ECV1.rgba, ECV1.quantize_group
sha, rgb, lum_of, materials, fidelity = ECV1.sha, ECV1.rgb, ECV1.lum_of, ECV1.materials, ECV1.fidelity
rip_pebbles, puff_poses, landing_spots, pebble_state, anim_frames = (
    ECV1.rip_pebbles, ECV1.puff_poses, ECV1.landing_spots, ECV1.pebble_state, ECV1.anim_frames)
PEBBLES, PUFF_WIN, PUFF_K, PUFF_COV, PUFF_COLORS = (
    ECV1.PEBBLES, ECV1.PUFF_WIN, ECV1.PUFF_K, ECV1.PUFF_COV, ECV1.PUFF_COLORS)
DROPS, FALL, BOUNCE, ROLL, VISIBLE, PUFF_AT = (
    ECV1.DROPS, ECV1.FALL, ECV1.BOUNCE, ECV1.ROLL, ECV1.VISIBLE, ECV1.PUFF_AT)

GEN = [
    {'file': 'decor.png',
     'images': [REF_NAME, 'source/entree_couloir_violet_sud_nord_v1/bruts/decor.png'],
     'prompt':
     "Use EXACTLY the same pixel-art style, palette and textures as the two reference images (Pokemon Mystery Dungeon "
     "purple rocky corridor): same mottled mauve-purple cave floor, same stacked rounded blue-violet boulders with "
     "light lilac highlights forming the walls, same dark blue vertically streaked rock cliffs along the outer edges, "
     "same small dark round pebbles on the floor near the walls, same very dark navy void at the outer corners. "
     "Create a NEW top-down closed boss cavern map in WIDE LANDSCAPE 4:3 (1200x896), zoomed out so the cavern feels "
     "vast. Layout: the player arrives at the SOUTH (bottom edge center) through a narrow mauve floor corridor "
     "between stacked blue-violet boulder walls; the corridor opens into a large wide circular cave chamber with six "
     "small clusters of blue-violet boulders standing on the floor around the sides (leaving the central arena wide "
     "open). At the NORTH (top center), there is NO dark tunnel hole and NO arch opening: instead, the northern "
     "boulder wall forms a closed semicircular cul-de-sac recess with a tall stacked blue-violet rock monolith pillar "
     "at the top center, and the mottled mauve floor leads right up to the foot of this northern rock monolith. "
     "Stacked boulder walls and dark streaked cliffs fill the left, right and top edges. No characters, no text, no "
     "UI, no border.",
     'essais': 'premier essai ; conforme (sol 10.7, roche 11.2)'},
    {'file': 'sol_complet.png',
     'images': [REF_NAME],
     'prompt':
     "REUTILISE sans nouvelle generation : sol complet d'ECV1 (source/entree_couloir_violet_sud_nord_v1/bruts/"
     "sol_complet.png, meme sha256). Prompt d'origine : Fill the ENTIRE image edge to edge with only the mottled "
     "mauve-purple cave floor texture from the reference image: same pixel-art mottled pattern, same palette and "
     "contrast, keep the texture detail. No boulders, no rocks, no pebbles, no walls, no dark areas. Wide landscape 4:3.",
     'essais': 'copie du sol_complet d ECV1 (meme biome, fond plein) : aucune generation supplementaire'},
    {'file': 'poussiere_poses.png',
     'images': [REF_NAME],
     'prompt':
     "REUTILISEE sans nouvelle generation : planche de poussiere d'ECV1 (source/entree_couloir_violet_sud_nord_v1/"
     "bruts/poussiere_poses.png, meme sha256). Prompt d'origine : Pixel-art sprite sheet on a flat pure magenta "
     "(#FF00FF) background: 6 animation poses of a small dust puff cloud rising when a pebble hits a cave floor, in a "
     "single horizontal row, evenly spaced, from a tiny puff to a larger spreading puff to faint dispersing wisps. "
     "Colours: mauve-purple and lilac greys taken from the reference image floor and rock highlights. Same pixel-art "
     "style as the reference. No floor, no shadows, no text.",
     'essais': 'copie de la planche ECV1 (meme biome, memes poses) : aucune generation supplementaire'},
]

PALETTE_GROUPS = {
    'sol': (['sol_complet', 'sol', 'ombres'], 64),
    'roche': (['gravillons', 'blocs', 'rochers', 'falaise'], 96),
    'sombre': (['vide'], 16),
}
STATIC = ['sol', 'ombres', 'gravillons', 'blocs', 'rochers', 'falaise', 'vide']
ANIMS = ['eboulis', 'poussiere']


def classify(a):
    """Seuils mesurés sur le brut (1200 x 896), sans bouche sombre (fin fermée) :
    sol = r-g lissé 5 px >= 6 et lum lissée > 45, fermé/ouvert 2 px, plus grande composante (> 20000 px), trous
    bouchés ; îlots = trous du sol qui ne sont pas du sol (ouverts 1 px) : blocs >= 600 px, gravillons 12 à 600 px ;
    ombres = sol à lum lissée < 62 à <= 30 px d'une paroi / d'un îlot ; vide = lum lissée < 24 hors sol, ouvert 4 px,
    > 3000 px, relié au bord de l'image ; falaise = paroi striée (gradient horizontal / vertical lissé 21 px > 1,5),
    fermée 6 px, > 4000 px ; rochers = le reste (parois et monolithe nord)."""
    r, g, b = a.transpose(2, 0, 1); lum = lum_of(a)
    L = nd.uniform_filter(lum, 5); rg = nd.uniform_filter(r - g, 5)
    floorc = (rg >= 6) & (L > 45)
    floor = keep_large(open_(close_(floorc, 2), 2), 20000)
    floor = nd.binary_fill_holes(floor)
    isl = open_(floor & ~floorc, 1)
    il, inn = nd.label(isl); sz = nd.sum(isl, il, range(1, inn + 1))
    blocs = np.isin(il, [i + 1 for i, v in enumerate(sz) if v >= 600])
    grav = np.isin(il, [i + 1 for i, v in enumerate(sz) if 12 <= v < 600])
    sol = floor & ~blocs & ~grav
    wall = ~floor
    db = nd.distance_transform_edt(~(wall | blocs | grav))
    omb = sol & (L < 62) & (db <= 30)
    omb = open_(close_(omb, 2), 1) & sol
    vide = keep_large(open_((L < 24) & wall, 4), 3000)
    lab, _ = nd.label(vide); edge = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    vide = np.isin(lab, edge[edge > 0])
    gx, gy = np.abs(nd.sobel(lum, 1)), np.abs(nd.sobel(lum, 0))
    an = nd.uniform_filter(gx, 21) / (nd.uniform_filter(gy, 21) + 1)
    fal = keep_large(close_((an > 1.5) & wall & ~vide, 6), 4000) & wall & ~vide
    roc = wall & ~vide & ~fal
    masks = dict(gravillons=grav, blocs=blocs, ombres=omb & ~grav & ~blocs, sol=sol & ~omb,
                 vide=vide, falaise=fal, rochers=roc)
    seg = {'blocs': int(sum(v >= 600 for v in sz)), 'gravillons': int(sum(12 <= v < 600 for v in sz)),
           'ombres_lum': round(float(lum[masks['ombres']].mean()), 1), 'sol_lum': round(float(lum[masks['sol']].mean()), 1)}
    return masks, seg


def write_ora(path, layers):
    import xml.etree.ElementTree as ET
    root = ET.Element('image', w=str(W), h=str(H), name='Fin Couloir violet V3 (FCV3)')
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
    o.update(Name={'DefaultText': 'Fin Couloir violet - arene du monolithe (4:3)', 'LocalTexts': {}}, AssetName=ASSET,
             Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0},
             ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Rendu genere 4:3 reference sur le rip Couloir rocheux violet ; eboulis animes '
                     '(gravillons exacts du rip), poussiere d ECV1 reutilisee, monolithe rocheux au nord. Collisions '
                     'de base a verifier. Aucune sortie ni warp. Biome et portee choisis par l agent.')
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
  <Name>Fin Couloir violet 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : zone de fin de donjon du Couloir rocheux violet (arene du monolithe), generee au format 4:3 (ref. rip Couloir rocheux violet), eboulis et poussiere animes. Pas une aventure jouable.</Description>
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
    a, f, ref = rgb(RAW / 'decor.png'), rgb(RAW / 'sol_complet.png'), rgb(REF)
    assert a.shape[:2] == f.shape[:2] == (SRC[1], SRC[0])
    m, seg = classify(a)
    order = ['gravillons', 'blocs', 'ombres', 'sol', 'vide', 'falaise', 'rochers']
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
    cand = ex['sol'] | ex['ombres'] | ex['gravillons']
    cl, _ = nd.label(cand); seed = cl[H - 1][cand[H - 1]]
    walk = np.isin(cl, np.unique(seed[seed > 0]))
    Image.fromarray((walk * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_praticable.png')
    pebbles = rip_pebbles(ref)
    puffs, puff_pal = puff_poses(RAW / 'poussiere_poses.png')
    for name, p in pebbles.items():
        Image.fromarray(p).save(OUT / 'poses' / f'{PFX}_gravillon_{name}.png')
    for i, p in enumerate(puffs):
        Image.fromarray(p).save(OUT / 'poses' / f'{PFX}_poussiere_{i}.png')
    spots = landing_spots(ex['sol'] | ex['ombres'], ex['rochers'] | ex['blocs'])
    eboulis, poussiere = anim_frames(pebbles, puffs, spots)
    anim = {'eboulis': eboulis, 'poussiere': poussiere}
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
    wy, wx = np.nonzero(walk); tgt = (int(wx.mean()) // 8, int(wy.mean()) // 8)
    boss_c = min(((cx, cy) for cy in range(gh_) for cx in range(gw_) if free(cx, cy)),
                 key=lambda c: (c[0] - tgt[0]) ** 2 + (c[1] - tgt[1]) ** 2)
    boss_px = [boss_c[0] * 8, boss_c[1] * 8]
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
    items = [(f'gravillon_{k}', pebbles[k]) for k in PEBBLES] + [(f'poussiere_{i}', p) for i, p in enumerate(puffs)]
    cw = 28 * 4 + 8
    sheet = Image.new('RGBA', (4 * cw + 8, 2 * cw + 8), (95, 79, 111, 255))
    for i, (_, p) in enumerate(items):
        im = Image.fromarray(p); im = im.resize((im.width * 4, im.height * 4), Image.Resampling.NEAREST)
        cx0, cy0 = 8 + (i % 4) * cw, 8 + (i // 4) * cw
        sheet.alpha_composite(im, (cx0 + (cw - 8 - im.width) // 2, cy0 + (cw - 8 - im.height) // 2))
    sheet.save(OUT / 'review' / f'{PFX}_planche_poses.png')
    write_ora(OUT / f'{PFX}_fin_couloir_violet_calques.ora',
              {f'{i:02d}_{t}' + ('_f00' if len(fr) > 1 else ''): fr[0] for i, (t, fr, _) in enumerate(stack_named)})
    counts = ground_project([(t.replace('_', ' ') + (f' {len(fr)} phases' if len(fr) > 1 else ''), fr, tk)
                             for t, fr, tk in stack_named], blocked, entry_px, boss_px, objective_px, gfx, tools)
    fid = fidelity(a, ref)
    final_fid = {}
    for k, nm in (('sol', 'sol'), ('roche', 'rochers'), ('roche', 'blocs')):
        lay = layers[nm]; px = lay[lay[..., 3] == 255][:, :3].astype(float)
        sel = materials(px.reshape(-1, 1, 3))[k][:, 0]
        px = px[sel] if sel.sum() > 50 else px
        final_fid[nm] = {'matiere': k, 'rgb': [round(float(v), 1) for v in px.mean(0)],
                         'distance_rip': round(float(np.linalg.norm(px.mean(0) - np.array(fid[k]['rip_rgb']))), 1)}
    manifest = {
        'lot': 'fin_couloir_violet_v3', 'prefix': PFX, 'format': '4:3 vaste', 'type': 'fin de donjon',
        'size_px': [W, H], 'grid_8px': [W // 8, H // 8],
        'base': 'branche de session (ECV1 pour les fonctions eboulis/poussiere et les bruts sol_complet/poussiere_poses, EWC1/ESN1 pour les utilitaires) ; aucun emprunt aux branches soeurs',
        'biome': 'fin du Couloir rocheux violet (arene du monolithe, prolonge ECV1), biome et portee choisis par l agent (« bon avance »), a confirmer',
        'method': 'textures canoniques = rendu genere REFERENCE : rip passe au generateur ; decor d arene fermee sans bouche sombre, '
                  'sol complet et planche de poussiere d ECV1 reutilises',
        'reference_da': {'file': REF.name, 'sha256': sha(REF),
                         'titre': 'Couloir rocheux violet (titre de l audit zones_bg_audit_v1 ; jeu et scene non confirmes)'},
        'generation': GEN,
        'raw_inputs': [{'file': f'{LOT}/bruts/{g["file"]}', 'sha256': sha(RAW / g['file']),
                        'size': list(Image.open(RAW / g['file']).size)} for g in GEN],
        'sol_complet': {'recalage_px': 'non applicable : texture de sol plein reutilisee d ECV1 (meme sha256)',
                        'rgb_moyen': [round(float(v), 1) for v in f.reshape(-1, 3).mean(0)],
                        'distance_rip': round(float(np.linalg.norm(f.reshape(-1, 3).mean(0) - np.array(fid['sol']['rip_rgb']))), 1)},
        'segmentation_mesures': seg,
        'fidelite_rip': {'methode': 'moyenne RGB par matiere, meme classifieur pixel sur le rip et sur le brut ; distance euclidienne ; seuil 35',
                         'brut': fid, 'calques_finaux': final_fid,
                         'eboulis': 'pixels et couleurs EXACTS du rip (3 gravillons releves sur le rip)'},
        'normalization': {'scale': JM.SCALE, 'scaled': [JM.SCALED_W, H], 'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
                          'methode': 'moyenne ponderee par classe (BOX), attribution exclusive par poids maximal',
                          'palettes': {g: {'calques': k, 'couleurs': n} for g, (k, n) in PALETTE_GROUPS.items()}},
        'segmentation': classify.__doc__.split('\n', 1)[1].strip(),
        'ombres': 'calque ombres = sol du rendu assombri au pied des parois et des blocs (separe, pas invente)',
        'layers': layer_list,
        'eboulis': {'phases': PHASES, 'frame_length_ticks': TICKS,
                    'gravillons_rip': {k: list(v) for k, v in PEBBLES.items()},
                    'chutes': [list(s) for s in spots], 'chute_dy': FALL,
                    'rebond_dy': {str(k): v for k, v in BOUNCE.items()}, 'roulement_dx': ROLL, 'visible_phases': VISIBLE,
                    'origine': 'gravillons (formes et couleurs) EXACTS du rip (fonctions d ECV1) ; chutes, rebond et roulement crees par nous'},
        'poussiere': {'fenetres': [list(w) for w in PUFF_WIN], 'reduction': f'x1/{PUFF_K}', 'couverture_min': PUFF_COV,
                      'fond': 'magenta pur et pixels teintes de magenta (r-g > 60 et b-g > 60), ni gardes ni recolores ; '
                              'seuls les pixels mauves (r-g >= 10, b-r < 40) a >= 3 px des rochers sont retenus',
                      'palette': [[int(round(c)) for c in p] for p in puff_pal],
                      'phases_par_impact': {str(k): v for k, v in PUFF_AT.items()},
                      'phases': PHASES, 'frame_length_ticks': TICKS,
                      'origine': 'planche et poses d ECV1 reutilisees (meme sha256) ; placement aux impacts cree par nous'},
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'entry_px': entry_px, 'boss_px': boss_px, 'objective_px': objective_px, 'path_found_16x16': reach,
                   'path_to_boss': reach_boss, 'path_to_objective': reach_obj, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si > 25 % hors praticable (sol, ombres, gravillons)',
                   'boss': 'case 2 x 2 libre la plus proche du centre de gravite du sol praticable',
                   'objectif': 'case 2 x 2 libre la plus haute de la colonne centrale (+-48 px), au pied du monolithe nord',
                   'fin': 'aucune sortie, aucun warp, pas de donjon_seuil ; le bord nord et les flancs sont bloques'},
        'pmdo': {'target': '0.8.12', 'asset': ASSET, 'namespace': NAMESPACE, 'tiles_per_bank': counts, 'banks': list(counts),
                 'runtime_tested': False, 'warp': 'aucun'},
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    print(json.dumps({'entry': entry_px, 'boss': boss_px, 'objectif': objective_px, 'blocked': int(blocked.sum()),
                      'walkable': int((~blocked).sum()), 'seg': seg, 'spots': spots,
                      'px': {k: int(v.sum()) for k, v in ex.items()},
                      'fidelite': {k: v['distance'] for k, v in fid.items()},
                      'final': {k: v['distance_rip'] for k, v in final_fid.items()}, 'tiles': sum(counts.values())}, indent=1))


if __name__ == '__main__':
    build()
