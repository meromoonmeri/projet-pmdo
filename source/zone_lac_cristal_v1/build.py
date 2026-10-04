"""Zone Lac Cristallin V1 (ZLC1) — carrefour et belvédères des îlots au format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Biome choisi par l'utilisateur : Lac Cristallin / Crystal Crossing (`lakecrystalpmdsky.png`, `D17P34A`), décliné en
trilogie complète de 3 cartes :
- ELC1 : Entrée de donjon sud -> nord ;
- FLC1 : Fin de donjon / Sanctuaire & Arène de boss ;
- ZLC1 : Zone ouverte / Carrefour & Belvédères des Îlots Cristallins (ce lot).

Méthode « textures canoniques » = rendu généré RÉFÉRENCÉ : le rip `lakecrystalpmdsky.png` (D17P34A)
est passé au générateur comme image de référence.
Bruts (voir manifest.json -> generation, prompts complets) :
- decor_magenta.png : décor complet 4:3 (1200 x 896), lac souterrain en magenta #FF00FF, esplanade octogonale
  traversante du sud au nord avec deux alcôves-belvédères latérales à piédestaux de cristal et îlots hexagonaux
  dans le lac (fidélité au rip : dalles = 7,4 ; cristaux sombres = 15,6 ; piliers = 0,9 ; seuil 35) ;
- sol_complet.png et poses_lac_cristal.png : partagés avec ELC1 (même sha256).
Calques fixes (7) : sol_complet, dalles, reflets, rebords, cristaux, ilots, piliers. Aucun calque `profondeur`.
Animations, chacune sur son calque (5), partagées avec ELC1 (boucle 240 ticks = 4 s) :
- eau du lac souterrain « façon rivière Métano », couleurs exactes du rip sans liseré clair, 4 x 10 ticks ;
- lueur cristalline sous-marine (9 couleurs cyan/bleu exactes du rip), 12 x 10 ticks ;
- scintillements `Metano_Town_River_Sparkles` natifs, 4 x 10 ticks ;
- gouttes cristallines et ronds dans l'eau, 24 x 5 ticks ;
- éclats prismatiques flottants, 48 x 5 ticks.
Marqueurs : `entrance_sud` (sud) et `sortie_nord` (nord).
Lancer : .venv/bin/python source/zone_lac_cristal_v1/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
REF_NAME = 'lakecrystalpmdsky.png'
REF = R / REF_NAME
OUT = R / 'renders/zone_lac_cristal_v1'
STAGE = R / '.cache/zone_lac_cristal_v1/zone_lac_cristal'
NAMESPACE = 'zone_lac_cristal'
ASSET = 'zlc1_zone_lac_cristal'
PFX = 'ZLC1'
W, H = 768, 576
SRC = (1200, 896)
WATER_PHASES, WATER_TICKS = 4, 10
GLOW_PHASES, GLOW_TICKS = 12, 10
DROP_PHASES, DROP_TICKS = 24, 5
ANIM_PHASES, ANIM_TICKS = 48, 5
LOOP_TICKS = 240

GEN = [
    {'file': 'decor_magenta.png',
     'images': [REF_NAME],
     'prompt':
     'Use EXACTLY the same 2D Nintendo DS pixel-art style, palette, and textures as the reference image (Pokemon '
     'Mystery Dungeon Explorers of Sky, Crystal Lake / Crystal Crossing): same glowing cyan-blue geometric crystal '
     'floor tiles with bright aqua cross-shaped light reflections (around RGB 120, 223, 248), same jagged dark-teal '
     'and slate-blue pointed crystal clusters lining the platform edges (around RGB 42, 106, 144), and same tall '
     'hexagonal ice-blue and white-highlighted crystal pillars and flat hexagonal crystal slabs. Make a NEW top-down '
     'WIDE 4:3 landscape map (1200x896) for an OPEN EXPLORATION ZONE / CRYSTAL CROSSING PROMENADE (south to north): '
     'a glowing cyan crystal causeway enters at the SOUTH (bottom center), widens in the middle into a broad octagonal '
     'crystal plaza with two lateral crystal terrace alcoves extending left and right (adorned with small hexagonal '
     'crystal pedestals and luminous crystal clusters), and continues north as an open walkable crystal causeway '
     'exiting cleanly at the NORTH border (top center, open pathway, NO black cave hole). To the left and right of '
     'the crystal plaza and causeway, the underground lake fills the cavern — IMPORTANT: fill the ENTIRE lake water '
     'surface with flat solid pure magenta #FF00FF (RGB 255, 0, 255) with crisp pixel edges, no ripples or gradients '
     'on the magenta, with several isolated hexagonal crystal islets and pillars standing in the magenta lake. No '
     'characters, no text, no UI, no border.'},
    {'file': 'sol_complet.png',
     'images': [REF_NAME],
     'prompt':
     'Use EXACTLY the same 2D Nintendo DS pixel-art style, palette, and textures as the central walkable floor of '
     'the reference image (Pokemon Mystery Dungeon Explorers of Sky, Crystal Lake / Crystal Crossing): make a WIDE '
     '4:3 image (1200x896) covered edge-to-edge ONLY with the flat walkable glowing cyan-blue geometric crystal tile '
     'floor texture with repeating aqua diamond/cross light reflections (around RGB 120, 223, 248) and subtle darker '
     'cyan tile seams. Remove all water, all dark crystal spikes, and all pillars — only the seamless flat walkable '
     'glowing cyan crystal floor across the entire 1200x896 frame. No characters, no text, no UI, no border.'},
    {'file': 'poses_lac_cristal.png',
     'images': [REF_NAME],
     'prompt':
     '2D Nintendo DS pixel-art sprite sheet on a flat solid pure magenta #FF00FF (RGB 255, 0, 255) background, '
     'matching the exact cyan and ice-blue pixel-art palette of the reference image (Pokemon Mystery Dungeon '
     'Explorers of Sky, Crystal Lake). 2 rows x 6 columns of small isolated sprites with wide pure magenta spacing '
     'between every sprite: Row 1 (top row): 6 poses of a pale cyan water drop falling and then expanding into a '
     'thin cyan concentric ripple ring on water (drop, stretched drop, tiny splash crown, small ring, medium ring, '
     'large thin ring). Row 2 (bottom row): 6 poses of a floating luminescent ice-cyan crystal spark / diamond light '
     'mote pulsing softly (tiny cyan dot, small diamond spark, medium 4-pointed crystal star, bright white-cyan '
     'cross sparkle, fading diamond, tiny glint). Crisp pixel art, no anti-aliasing against the #FF00FF magenta '
     'background, no grid lines, no text, no borders.'},
]


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


ELC = loadmod('elc1', R / 'source/entree_lac_cristal_sud_nord_v1/build.py')
JM, BM = ELC.JM, ELC.BM
keep_large, place, cell_grid = ELC.keep_large, ELC.place, ELC.cell_grid
down_class, down_full, rgba = ELC.down_class, ELC.down_full, ELC.rgba
sha, quantize_group, rgb, close_, write_ora = ELC.sha, ELC.quantize_group, ELC.rgb, ELC.close_, ELC.write_ora
materials, fidelity, repair_ground = ELC.materials, ELC.fidelity, ELC.repair_ground
lake_water, glow_centres, glow_frames, extract_crystal_poses, drop_frames, firefly_frames = (
    ELC.lake_water, ELC.glow_centres, ELC.glow_frames, ELC.extract_crystal_poses, ELC.drop_frames, ELC.firefly_frames)
WPAL, GLOW, GLOW_RING_PX, DROP_WINS, MOTE_WINS, DROP_SEQ, FLY_PULSE, RIP_WATER_COLS, _REF_ARR = (
    ELC.WPAL, ELC.GLOW, ELC.GLOW_RING_PX, ELC.DROP_WINS, ELC.MOTE_WINS, ELC.DROP_SEQ, ELC.FLY_PULSE, ELC.RIP_WATER_COLS, ELC._REF_ARR)

PALETTE_GROUPS = {
    'plateforme': (['sol_complet', 'dalles', 'reflets', 'rebords'], 96),
    'piliers': (['piliers', 'ilots'], 48),
    'cristaux': (['cristaux'], 32),
}
STATIC = ['dalles', 'reflets', 'rebords', 'cristaux', 'ilots', 'piliers']


def classify(a):
    r, g, b = a.transpose(2, 0, 1); lum = a @ [.299, .587, .114]
    hh, ww = lum.shape; yy, xx = np.mgrid[:hh, :ww]

    mag_pure = (r > 190) & (b > 190) & (g < 100)
    mag_zone = nd.binary_dilation(mag_pure, iterations=10)
    mag_fringe = mag_zone & (((b > g + 8) & (r > g + 15)) | ((r - g) + (b - g) > 35))
    water = nd.binary_dilation(keep_large(mag_pure, 1000) | mag_fringe, iterations=2)

    non_w = ~water
    lbl, n = nd.label(non_w)
    sizes = nd.sum(non_w, lbl, range(1, n + 1))
    main_plat = (lbl == (int(np.argmax(sizes)) + 1))
    ilots = non_w & ~main_plat

    # Piliers d'épaule au nord + 6 petits piédestaux hexagonaux dans les alcôves latérales
    pillar_sh = main_plat & (yy >= 130) & (yy <= 248) & ((xx < 512) | (xx > 688)) & (lum > 140)
    ped_boxes = [
        (345, 405, 195, 255), (415, 480, 110, 175), (470, 535, 195, 255),
        (345, 405, 945, 1005), (415, 480, 1025, 1090), (470, 535, 945, 1005),
    ]
    ped = np.zeros_like(main_plat)
    for y0, y1, x0, x1 in ped_boxes:
        ped[y0:y1, x0:x1] = True
    ped &= main_plat & (lum > 135)
    piliers = nd.binary_fill_holes(close_(keep_large(pillar_sh | ped, 150), 2)) & main_plat

    rem = main_plat & ~piliers
    cristaux_raw = rem & (lum < 142) & ~((xx >= 535) & (xx <= 665))
    cristaux = nd.binary_fill_holes(close_(keep_large(cristaux_raw, 80), 2)) & rem

    rem2 = rem & ~cristaux
    d_edge = nd.distance_transform_edt(~(water | piliers))
    rebords = rem2 & (d_edge <= 16) & (yy > 40) & (yy < 840) & ~((xx >= 540) & (xx <= 660))
    rem3 = rem2 & ~rebords

    reflets = rem3 & (lum > 218) & (g > 235) & (b > 245)
    dalles = rem3 & ~reflets

    return dict(water=water, piliers=piliers, ilots=ilots,
                cristaux=cristaux, rebords=rebords, reflets=reflets, dalles=dalles)


def ground_project(stack, blocked, entry_px, exit_px, gfx, tools):
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
    o.update(Name={'DefaultText': 'Zone Lac Cristallin - Carrefour (4:3)', 'LocalTexts': {}}, AssetName=ASSET,
             Released=False, TexSize=1, Music='', EdgeView=1, ViewCenter=None, ViewOffset={'X': 0, 'Y': 0},
             ActiveChar=None, Status={}, Layers=layers,
             Background={'$type': 'RogueEssence.Dungeon.LayeredBG, RogueEssence', 'Layers': []},
             Comment='PMDO 0.8.12. Zone ouverte / Carrefour du Lac Cristallin au format 4:3 reference sur le rip '
                     'Crystal Lake / Crystal Crossing (lakecrystalpmdsky.png, D17P34A) ; lac facon Metano sans lisere '
                     '(couleurs exactes du rip), lueur sous-marine, scintillements Metano natifs, gouttes et eclats generes.')
    o['obstacles'] = [[{'Bounds': {'X': x*8, 'Y': y*8, 'Width': 8, 'Height': 8}, 'Tags': int(blocked[y, x])}
                       for y in range(gh)] for x in range(gw)]
    mk = lambda n, p: {'EntName': n, 'Direction': 4, 'EntEnabled': True, 'triggerType': 0,
                       'Collider': {'X': p[0], 'Y': p[1], 'Width': 16, 'Height': 16}}
    o['Entities'] = [{'Name': 'Entrees et vos acteurs', 'Visible': True, 'MapChars': [], 'GroundObjects': [], 'Spawners': [],
                      'Markers': [mk('entrance_sud', entry_px), mk('sortie_nord', exit_px)]}]
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
  <Name>Zone Lac Cristallin 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : zone ouverte / carrefour du Lac Cristallin au format 4:3 (ref. rip Crystal Lake D17P34A), lac facon Metano aux couleurs du rip, lueur, gouttes et eclats cristallins animes. Pas une aventure jouable.</Description>
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


def build():
    gfx = loadmod('pmdo_codec', R / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
    v1 = loadmod('esn1', R / 'source/entree_sud_nord_generee_v1/build.py')
    ANIMS = ['eau', 'lueur', 'scintillements', 'gouttes', 'eclats']
    if OUT.exists():
        for d in ['calques', 'animation', 'poses', 'masques', 'review']:
            shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['calques', 'poses', 'masques', 'review'] + [f'animation/{x}' for x in ANIMS]:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    a = rgb(RAW / 'decor_magenta.png'); f0 = rgb(RAW / 'sol_complet.png'); ref = rgb(REF)
    assert a.shape[:2] == f0.shape[:2] == (SRC[1], SRC[0])
    f, repair = repair_ground(f0)
    m = classify(a)
    order = ['water', 'piliers', 'ilots', 'cristaux', 'rebords', 'reflets', 'dalles']
    ex, cols = down_class(a, m, order)
    water = ex['water']
    layers = {'sol_complet': rgba(down_full(f), ~water)}
    for k in STATIC:
        layers[k] = rgba(cols[k], ex[k])
    q = {}
    for keys, n in PALETTE_GROUPS.values():
        q.update(quantize_group({k: layers[k] for k in keys}, n))
    layers = q
    for k, v in ex.items():
        Image.fromarray((v * 255).astype('uint8')).save(OUT / 'masques' / f'{PFX}_masque_{k}.png')

    land = np.zeros((H, W), bool)
    for k in STATIC:
        land |= layers[k][..., 3] == 255
    visible = water & ~land
    wf, dist = lake_water(water, visible)
    centres = glow_centres(visible)
    gf = glow_frames(visible, centres)

    fams = BM.sparkle_families(); taken = np.zeros((H, W), bool)
    sf = [np.zeros((H, W, 4), 'uint8') for _ in range(WATER_PHASES)]; sparkles = []
    for fi, (name, frames) in enumerate(fams.items()):
        hh, ww = frames[0].shape[:2]
        for (y, x) in place(visible & (dist > 6), (hh, ww), 3, 101 + fi, taken, core=8):
            sparkles.append({'famille': name, 'xy': [x, y]})
            for t in range(WATER_PHASES):
                mm = frames[t][..., 3] > 0; sf[t][y:y+hh, x:x+ww][mm] = frames[t][mm]
    for arr in sf:
        arr[~visible] = 0

    drops, motes, _ = extract_crystal_poses(RAW / 'poses_lac_cristal.png')
    for i, (nm, _, _, _) in enumerate(DROP_WINS):
        Image.fromarray(drops[nm]).save(OUT / 'poses' / f'{PFX}_goutte_{i}_{nm}.png')
    for i, p in enumerate(motes):
        Image.fromarray(p).save(OUT / 'poses' / f'{PFX}_eclat_{i}.png')

    cand_d = np.argwhere((visible & (dist > 18))[50:H - 50, 40:W - 40]) + [50, 40]
    emitters, used_d = [], []
    for y, x in cand_d[np.random.default_rng(31).permutation(len(cand_d))]:
        if all(abs(x - ux) > 70 or abs(y - uy) > 70 for uy, ux in used_d):
            used_d.append((y, x)); emitters.append([int(x), int(y), (len(emitters) * 3) % DROP_PHASES])
        if len(emitters) == 8:
            break
    df = drop_frames(drops, emitters, visible)

    crystal_zone = ex['cristaux'] | ex['piliers'] | ex['ilots']
    cand_m = np.argwhere(crystal_zone[28:H - 28, 28:W - 28]) + [28, 28]
    spots, used_m = [], []
    for y, x in cand_m[np.random.default_rng(53).permutation(len(cand_m))]:
        if all(abs(x - ux) > 48 or abs(y - uy) > 48 for uy, ux in used_m):
            used_m.append((y, x)); spots.append((int(x), int(y), (len(spots) * 5) % ANIM_PHASES, 4 + (len(spots) % 3) * 2))
        if len(spots) == 14:
            break
    ef = firefly_frames(motes, spots)

    anim = {
        'eau': (wf, WATER_TICKS),
        'lueur': (gf, GLOW_TICKS),
        'scintillements': (sf, WATER_TICKS),
        'gouttes': (df, DROP_TICKS),
        'eclats': (ef, ANIM_TICKS),
    }
    order_names = ['eau', 'lueur', 'scintillements', 'gouttes', 'sol_complet'] + STATIC + ['eclats']
    stack_named, layer_list = [], []
    for i, nm in enumerate(order_names):
        if nm in anim:
            frames, ticks = anim[nm]
            for t, fr in enumerate(frames):
                Image.fromarray(fr).save(OUT / 'animation' / nm / f'{PFX}_{i:02d}_{nm}_f{t:02d}.png')
            layer_list.append({'file': f'animation/{nm}/{PFX}_{i:02d}_{nm}_fNN.png', 'phases': len(frames), 'ticks': ticks})
        else:
            frames, ticks = [layers[nm]], 60
            Image.fromarray(layers[nm]).save(OUT / 'calques' / f'{PFX}_{i:02d}_{nm}.png')
            layer_list.append({'file': f'calques/{PFX}_{i:02d}_{nm}.png', 'phases': 1, 'ticks': 60})
        stack_named.append((nm, frames, ticks))

    walk_px = (layers['dalles'][..., 3] == 255) | (layers['reflets'][..., 3] == 255)
    blocked = cell_grid(~walk_px); gh_, gw_ = blocked.shape
    scol = min((c for c in range(gw_ - 1) if not blocked[gh_ - 2:, c:c + 2].any()), key=lambda c: abs(c - 48))
    ncol = min((c for c in range(gw_ - 1) if not blocked[:2, c:c + 2].any()), key=lambda c: abs(c - 48))
    entry_px = [scol * 8, H - 16]
    exit_px = [ncol * 8, 0]
    ok, explored = v1.reachable(blocked, (entry_px[1] // 8, entry_px[0] // 8), (exit_px[1] // 8, exit_px[0] // 8))
    assert ok, 'pas de chemin 16x16'

    def scene(tick):
        im = Image.new('RGBA', (W, H))
        for _, frames, ticks in stack_named:
            im.alpha_composite(Image.fromarray(frames[(tick // ticks) % len(frames)]))
        return im
    step = 5
    scenes = [scene(t) for t in range(0, LOOP_TICKS, step)]
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_t000.png')
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_animee.webp', save_all=True, append_images=scenes[1:],
                   duration=round(step * 1000 / 60), loop=0, lossless=True, method=0)
    col = scenes[0].copy(); ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    for y, x in zip(*np.nonzero(blocked)):
        dr.rectangle([x*8, y*8, x*8+7, y*8+7], fill=(220, 40, 40, 90))
    for (qx, qy), c in ((entry_px, (255, 230, 40, 255)), (exit_px, (60, 220, 255, 255))):
        dr.rectangle([qx, qy, qx + 15, qy + 15], outline=c, width=2)
    col.alpha_composite(ov); col.save(OUT / 'review' / f'{PFX}_collisions_marqueurs.png')

    sheet = Image.new('RGBA', (6 * 68, 2 * 68), (35, 78, 110, 255))
    drop_list = [drops[nm] for nm, _, _, _ in DROP_WINS]
    for r_, seq in enumerate((drop_list, motes)):
        for i, p in enumerate(seq):
            im = Image.fromarray(p); sc = max(1, 60 // max(im.size))
            sheet.alpha_composite(im.resize((im.width * sc, im.height * sc), Image.Resampling.NEAREST), (i * 68 + 4, r_ * 68 + 4))
    sheet.save(OUT / 'review' / f'{PFX}_planche_poses.png')

    write_ora(OUT / f'{PFX}_zone_lac_cristal_calques.ora',
              {f'{i:02d}_{t}' + ('_f00' if len(fr) > 1 else ''): fr[0] for i, (t, fr, _) in enumerate(stack_named)})
    counts = ground_project([(t.replace('_', ' ') + (f' {len(fr)} phases' if len(fr) > 1 else ''), fr, tk)
                             for t, fr, tk in stack_named], blocked, entry_px, exit_px, gfx, tools)

    fid = fidelity(a, ref)
    final_fid = {}
    for k, nm in (('dalles_cristal', 'dalles'), ('cristaux_sombres', 'cristaux'), ('piliers_cristal', 'piliers')):
        lay = layers[nm]; px = lay[lay[..., 3] == 255][:, :3].astype(float)
        sel = materials(px.reshape(-1, 1, 3))[k][:, 0]
        px = px[sel] if sel.sum() > 50 else px
        final_fid[k] = {'calque': nm, 'rgb': [round(float(v), 1) for v in px.mean(0)],
                        'distance_rip': round(float(np.linalg.norm(px.mean(0) - np.array(fid[k]['rip_rgb']))), 1)}
    raw_inputs = [{'file': f'source/zone_lac_cristal_v1/bruts/{g["file"]}', 'sha256': sha(RAW / g['file']),
                   'size': list(Image.open(RAW / g['file']).size), 'statut': 'retenu'} for g in GEN]
    manifest = {
        'lot': 'zone_lac_cristal_v1', 'prefix': PFX, 'format': '4:3 vaste', 'size_px': [W, H],
        'grid_8px': [W // 8, H // 8], 'base': 'branche de session (arena/01a1024d-projet-pmdo) ; aucun emprunt aux branches soeurs',
        'biome': 'Lac Cristallin / Crystal Crossing (lakecrystalpmdsky.png, D17P34A), choisi par l utilisateur (trilogie 3 maps)',
        'method': 'textures canoniques = rendu genere REFERENCE : rip lakecrystalpmdsky.png passe au generateur ; '
                  'decor complet de zone traversante sur magenta (lac = magenta), sol cristallin complet et planche gouttes/eclats partages avec ELC1',
        'reference_da': {'file': REF.name, 'sha256': sha(REF), 'titre': 'Crystal Lake / Crystal Crossing (D17P34A, PMD Explorers of Sky)'},
        'generation': GEN,
        'raw_inputs': raw_inputs,
        'sol_complet_reparation': repair,
        'fidelite_rip': {'methode': 'moyenne RGB par matiere, meme classifieur pixel sur le rip et sur le brut ; distance euclidienne',
                         'brut': fid, 'calques_finaux': final_fid},
        'normalization': {'scale': JM.SCALE, 'scaled': [JM.SCALED_W, H], 'crop_x': [JM.CROP_X, JM.SCALED_W - W - JM.CROP_X],
                          'methode': 'moyenne ponderee par classe (BOX), attribution exclusive par poids maximal',
                          'palettes': {g: {'calques': k, 'couleurs': n} for g, (k, n) in PALETTE_GROUPS.items()}},
        'segmentation': 'eau = magenta pur + frange dilatee 2 px ; piliers = piliers hexagonaux d epaule au nord et '
                        '6 petits piedestaux hexagonaux dans les alcoves laterales ; ilots = piliers et dalles hexagonales '
                        'isoles dans le lac ; cristaux = pointes de cristal bleu-sarcelle sombre ; rebords = dalles '
                        'biseautees en bordure ; reflets = croix lumineuses aqua ; dalles = sol cristallin cyan praticable',
        'layers': layer_list,
        'water': {'phases': WATER_PHASES, 'frame_length_ticks': WATER_TICKS,
                  'couleurs': {k: list(v) for k, v in WPAL.items()},
                  'modele': 'structure et cadence riviere Metano, couleurs EXACTES du rip lakecrystalpmdsky.png, sans lisere clair de rive',
                  'origine': 'pixels recalcules aux couleurs canoniques du rip, pas de tuiles natives'},
        'glow': {'phases': GLOW_PHASES, 'frame_length_ticks': GLOW_TICKS,
                 'couleurs': [list(c) for c in GLOW], 'ring_px': GLOW_RING_PX, 'centres': centres,
                 'origine': 'anneaux de lueur sous-marine aux 9 couleurs cyan/bleu exactes du rip'},
        'sparkles': {'source': 'source/eau_metano/natifs/Metano_Town_River_Sparkles.tile', 'placements': sparkles,
                     'origine': 'pixels et couleurs Metano NATIFS inchanges'},
        'gouttes': {'poses': len(DROP_WINS), 'sequence': [list(s) if s else None for s in DROP_SEQ],
                    'emitters': emitters, 'phases': DROP_PHASES, 'frame_length_ticks': DROP_TICKS,
                    'origine': 'dessin GENERE sur poses_lac_cristal.png (rangee 1), reduit x1/8'},
        'eclats': {'poses': len(motes), 'taille_px': list(motes[0].shape[:2]), 'reduction': 'fenetre 176 px -> 11 px (x1/16)',
                   'pulsation': FLY_PULSE, 'points': [list(s) for s in spots], 'phases': ANIM_PHASES, 'frame_length_ticks': ANIM_TICKS,
                   'origine': 'dessin GENERE sur poses_lac_cristal.png (rangee 2) ; boucles de Lissajous et pulsation creees par nous'},
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'entry_px': entry_px, 'exit_px': exit_px, 'threshold_px': exit_px,
                   'path_found_16x16': ok, 'cells_explored': explored,
                   'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size), 'walkable_cells': int((~blocked).sum()),
                   'rule': 'case bloquee si > 25 % hors dalles et reflets cristallins de l esplanade traversante',
                   'seuil': 'traversee ouverte sud -> nord avec deux alcoves-belvederes laterales'},
        'pmdo': {'target': '0.8.12', 'asset': ASSET, 'namespace': NAMESPACE, 'tiles_per_bank': counts, 'banks': list(counts),
                 'runtime_tested': False, 'warp': 'aucun'},
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    print(json.dumps({'sparkles': len(sparkles), 'entry': entry_px, 'exit': exit_px,
                      'blocked': int(blocked.sum()), 'walkable': int((~blocked).sum()),
                      'fidelite': {k: v['distance'] for k, v in fid.items()},
                      'final': {k: v['distance_rip'] for k, v in final_fid.items()}, 'tiles': sum(counts.values())}, indent=1))


if __name__ == '__main__':
    build()
