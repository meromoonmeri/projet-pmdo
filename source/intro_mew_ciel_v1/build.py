"""IMW2 — « Ciel de Mew » : fond animé en boucle (768 x 576, boucle 2400 ticks = 40 s), projet PMDO 0.8.12 en calques.

Suite d'IMW1 (la cinématique vidéo) sur la même demande : « fond animé une intro d'un mew qui voyage à travers le ciel avec un soleil ».
IMW1 est une vidéo ; IMW2 est le fond de ciel de l'intro, utilisable dans PMDO (Ground, tuiles de 8 px, calques animés) :
- Mew sur place, qui flotte (bosse de 3 px) et dont la queue ondule (8 poses, 48 ticks) ; le décor défile derrière lui, donc il voyage ;
- un soleil à rayons qui tournent lentement (12 phases de 200 ticks), partiellement caché par des nuages ;
- trois plans de nuages en parallaxe (12, 24 et 36 px/s) et une mer de nuages au premier plan, tous périodiques sur la boucle ;
- des éclats de lumière derrière Mew (8 poses, 48 ticks).
Tout est dérivé de `source/intro_mew_v1/build.py` (même sprite de Mew 66 x 58 en pixels x2, mêmes nuages procéduraux). Aucune référence ROM ;
rien n'est praticable : c'est un fond de cinématique (grille entièrement bloquante, marqueurs de repère seulement). `art_approved: false`.
"""
from pathlib import Path
import hashlib, importlib.util, json, math, shutil
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
LOT = 'intro_mew_ciel_v1'
OUT = R / 'renders' / LOT
NAMESPACE = 'ciel_de_mew'
STAGE = R / '.cache' / LOT / NAMESPACE
ASSET = 'imw2_ciel_de_mew'
PFX = 'IMW2'
W, H, UP = 768, 576, 2
LW, LH = W // UP, H // UP
LOOP_TICKS = 2400
# nom : (phases, ticks par phase) — chaque cycle divise la boucle de 2400 ticks
ANIM = {'soleil': (12, 200), 'nuages_loin': (240, 10), 'nuages_moyens': (240, 10), 'mew': (8, 6), 'mer': (240, 10), 'eclats': (8, 6)}
for _k, (_p, _t) in ANIM.items():
    assert LOOP_TICKS % (_p * _t) == 0, _k
# bandes périodiques de nuages : (période logique, pas logique par phase, intervalle y, nombre de nuages, graine) -> vitesse px/s = pas * 2 * 6
CLOUD_STRIPS = {'nuages_loin': (240, 1, (40, 150), 8, 5), 'nuages_moyens': (480, 2, (90, 180), 8, 5), 'mer': (720, 3, (196, 236), 10, 5)}
SUN = (270, 118, 26)                                    # centre et rayon logiques
MEW_C = (140, 150)                                      # centre logique de Mew
SKY_TOP, SKY_HOR = (112, 150, 222), (255, 205, 150)


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


IM = loadmod('imw1_build', R / 'source/intro_mew_v1/build.py')
JM = loadmod('ejn1_outils', R / 'source/entree_jungle_sud_nord_v1/build.py')
BM = JM.BM
FV = loadmod('fvs1_fin', R / 'source/fin_vapeur_sommet_v1/build.py')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def up(a):
    return np.repeat(np.repeat(a, UP, 0), UP, 1)


def opaque(rgb):
    out = np.zeros(rgb.shape[:2] + (4,), np.uint8); out[..., :3] = rgb; out[..., 3] = 255; return out


# ------------------------------------------------------------------------------------------------------ calques
def sky_layer():
    return IM.sky_gradient(SKY_TOP, SKY_HOR)


def sun_frames(sky):
    out = []
    n_ph = ANIM['soleil'][0]
    for p in range(n_ph):
        img = IM.draw_sun(sky.copy(), SUN[0], SUN[1], SUN[2], 0.0, rot=2.0 * p / n_ph)   # 2 rayons de période : la boucle est exacte
        changed = (img != sky).any(2)
        a = np.zeros((LH, LW, 4), np.uint8); a[..., :3] = np.where(changed[..., None], img, 0); a[..., 3] = np.where(changed, 255, 0)   # RVB nul là où c'est transparent
        out.append(up(a))
    return out


def cloud_strip(P, y_range, sprs, seed, n, sea=None):
    s = np.zeros((LH, P, 4), np.uint8); rs = np.random.RandomState(seed)
    items = []
    if sea is not None:
        items += [(sea, 0, 214), (sea, 360, 214)]
    for i in range(n):
        items.append((sprs[i % len(sprs)], int(rs.uniform(0, P)), int(rs.uniform(*y_range))))
    for spr, x, y in items:
        hh, ww = spr.shape[:2]
        for dx in (-P, 0, P):                                                  # recouvrement circulaire : la bande boucle sans couture
            xs = x + dx; x0, x1 = max(0, xs), min(P, xs + ww)
            if x1 <= x0: continue
            sub = spr[:, x0 - xs:x1 - xs]; m = sub[..., 3] > 127; y1 = min(LH, y + hh)
            t = s[y:y1, x0:x1]; t[m[:y1 - y]] = sub[:y1 - y][m[:y1 - y]]
    return s


def cloud_frames(name):
    P, step, yr, n, seed = CLOUD_STRIPS[name]
    sp = IM.sprites()
    sprs = {'nuages_loin': sp['far'], 'nuages_moyens': sp['mid'], 'mer': sp['near']}[name]
    strip = cloud_strip(P, yr, sprs, seed, n, sea=sp['sea'] if name == 'mer' else None)
    ph = ANIM[name][0]
    assert P == step * ph, name                                                # une période exactement par boucle
    return [up(strip[:, (np.arange(LW) + step * t) % P]) for t in range(ph)], strip


def bob(k):
    return int(round(3 * math.sin(2 * math.pi * k / 8)))


def mew_frames():
    out = []
    for k, f in enumerate(IM.mew_frames(8)):
        a = np.zeros((LH, LW, 4), np.uint8)
        h, w = f.shape[:2]
        x0, y0 = MEW_C[0] - w // 2, MEW_C[1] - h // 2 + bob(k)
        sub = a[y0:y0 + h, x0:x0 + w]; m = f[..., 3] > 0; sub[m] = f[m]
        out.append(up(a))
    return out


SPARK = [(255, 255, 255), (255, 242, 170), (255, 196, 226)]


def spark_frames():
    """8 émissions par cycle (une toutes les 6 ticks), vie de 11 pas : l'identifiant j renaît deux fois, la boucle est exacte."""
    out = []
    for f in range(8):
        a = np.zeros((LH, LW, 4), np.uint8)
        for j in range(8):
            for gen in (0, 1):
                age = ((f - j) % 8) + 8 * gen
                if age > 10: continue
                rs = np.random.RandomState(900 + 2 * j + gen)
                te = (f - age) % 8                                             # pose de Mew à l'émission
                age_s = age * 0.1
                x = MEW_C[0] - 28 - 26 * age_s * (0.6 + rs.rand()) + rs.uniform(-4, 4)
                y = MEW_C[1] + bob(te) + 6 + rs.uniform(-14, 14) + 8 * age_s + 3 * math.sin(6 * age_s + j)
                col = SPARK[(j + gen) % 3]
                r = int(1 + 2 * (1 - age_s / 1.1))
                xi, yi = int(round(x)), int(round(y))
                pts = [(0, 0)] + [(s * i, 0) for i in range(1, r + 1) for s in (-1, 1)] + [(0, s * i) for i in range(1, r + 1) for s in (-1, 1)]
                for dx, dy in pts:
                    px, py = xi + dx, yi + dy
                    if 0 <= px < LW and 0 <= py < LH: a[py, px, :3] = col; a[py, px, 3] = 255
        out.append(up(a))
    return out


def make_stack():
    sky = sky_layer()
    st = {'ciel': [opaque(up(sky))], 'soleil': sun_frames(sky)}
    strips = {}
    for nm in ('nuages_loin', 'nuages_moyens'):
        st[nm], strips[nm] = cloud_frames(nm)
    st['mew'] = mew_frames()
    st['mer'], strips['mer'] = cloud_frames('mer')
    st['eclats'] = spark_frames()
    return st, strips


ORDER = ['ciel', 'soleil', 'nuages_loin', 'nuages_moyens', 'mew', 'mer', 'eclats']


def tick_of(nm):
    return ANIM[nm][1] if nm in ANIM else 60


# ------------------------------------------------------------------------------------------------------ Ground
def ground_project(stack, blocked, markers, gfx, tools):
    for k in ('STAGE', 'PFX', 'ASSET', 'NAMESPACE', 'HERE', 'W', 'H'):
        setattr(FV, k, globals()[k])
    counts = FV.ground_project(stack, blocked, {'entrance': markers['entrance'], 'boss': markers['mew'], 'source': markers['soleil']}, gfx, tools)
    doc_p = STAGE / f'Data/Ground/{ASSET}.rsground'
    doc = json.loads(doc_p.read_text()); o = doc['Object']
    o['Name'] = {'DefaultText': 'Ciel de Mew - fond anime (4:3)', 'LocalTexts': {}}
    o['Comment'] = ('PMDO 0.8.12. Fond de cinematique 4:3 : Mew qui vole sur place, soleil a rayons qui tournent, trois plans de nuages '
                    'en parallaxe et une mer de nuages, eclats de lumiere ; boucle de 40 s. Rien de praticable (grille bloquante), '
                    'marqueurs de repere seulement. Aucun warp.')
    for mk in o['Entities'][0]['Markers']:
        mk['EntName'] = {'boss': 'mew', 'source': 'soleil'}.get(mk['EntName'], mk['EntName'])
    gfx.save(doc_p, json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode())
    x = (STAGE / 'Mod.xml').read_text()
    assert 'Fin Vapeur (sommet de Steam Cave) 4:3' in x and 'events de vapeur animes' in x
    x = x.replace('Fin Vapeur (sommet de Steam Cave) 4:3', 'Ciel de Mew (fond anime) 4:3')
    x = x.replace("fin de donjon generee au format 4:3 (ref. Steam Cave Peak), arene, source chaude qui bouillonne, events de vapeur animes",
                  "fond de cinematique 4:3 genere : Mew en vol, soleil, nuages en parallaxe, boucle de 40 s")
    (STAGE / 'Mod.xml').write_text(x)
    return counts


def scene(stack_named, tick):
    im = Image.new('RGBA', (W, H))
    for nm, frames in stack_named:
        ph, tk = ANIM.get(nm, (1, 60))
        im.alpha_composite(Image.fromarray(frames[(tick // tk) % len(frames)] if nm in ANIM else frames[0]))
    return im


def build():
    gfx = loadmod('pmdo_codec', R / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
    if OUT.exists():
        for d in ['calques', 'animation', 'review']:
            shutil.rmtree(OUT / d, ignore_errors=True)
    for d in ['calques', 'review'] + [f'animation/{k}' for k in ANIM]:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    st, strips = make_stack()
    files = {}
    for i, nm in enumerate(ORDER):
        frames = st[nm]
        if len(frames) == 1:
            fn = f'calques/{PFX}_{i:02d}_{nm}.png'; Image.fromarray(frames[0]).save(OUT / fn)
        else:
            w = 3 if len(frames) > 100 else 2
            fn = f'animation/{nm}/{PFX}_{i:02d}_{nm}_f' + 'N' * w + '.png'
            for t, fr_ in enumerate(frames):
                Image.fromarray(fr_).save(OUT / fn.replace('N' * w, f'{t:0{w}d}'))
        files[nm] = fn
    blocked = np.ones((H // 8, W // 8), bool)                                     # fond de cinématique : rien de praticable
    markers = {'entrance': [W // 2 - 8, H - 16], 'mew': [MEW_C[0] * UP - 8, MEW_C[1] * UP - 8], 'soleil': [SUN[0] * UP - 8, SUN[1] * UP - 8]}
    named = [(nm, st[nm]) for nm in ORDER]
    n_sc = LOOP_TICKS // 10
    scenes = [scene(named, t * 10) for t in range(n_sc)]
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_t000.png')
    scenes[0].save(OUT / 'review' / f'{PFX}_scene_animee.webp', save_all=True, append_images=scenes[1:],
                   duration=round(10 * 1000 / 60), loop=0, quality=85, method=4)
    z = Image.new('RGB', (4 * 384, 288))
    for j, t in enumerate((0, 600, 1200, 1800)):
        z.paste(scene(named, t).convert('RGB').resize((384, 288), Image.NEAREST), (j * 384, 0))
    z.save(OUT / 'review' / f'{PFX}_quatre_instants.png')
    mew = np.array(Image.open(IM.HERE / 'bruts/mew_natif.png').convert('RGBA'))
    ora_layers = {f'{i:02d}_{nm}' + ('_f0' if len(st[nm]) > 1 else ''): st[nm][0] for i, nm in enumerate(ORDER)}
    BM.write_ora(OUT / f'{PFX}_ciel_de_mew_calques.ora', ora_layers)
    counts = ground_project([(nm.replace('_', ' ') + (f' {len(st[nm])} phases' if len(st[nm]) > 1 else ''), st[nm], tick_of(nm)) for nm in ORDER],
                            blocked, markers, gfx, tools)
    speeds = {nm: CLOUD_STRIPS[nm][1] * UP * 6 for nm in CLOUD_STRIPS}
    manifest = {
        'lot': LOT, 'asset': PFX, 'serie': 'Cinematiques',
        'biome': 'ciel d aube au-dessus d une mer de nuages (choisi par l agent, a confirmer)',
        'demande': ["tu peux faire fond animé une intro d'un mew qui voyage a traver le ciel avec un soleil et il voyage a travers le monde pokemon avec différent biome (une cinematique avec plusieurs map etc)"],
        'choix_agent': {'portee': "IMW1 est la cinematique video (11 cartes) ; IMW2 est son fond de ciel en boucle, au format PMDO Ground (calques et tuiles de 8 px). "
                                  "Les cartes de biome restent leurs propres projets : l'enchainement des 11 cartes n'est pas rejoue en tuiles (a confirmer)",
                        'mew': 'sprite de IMW1 (66 x 58 px natifs, 13 couleurs) en pixels x2, sur place : il flotte et sa queue ondule, le decor defile',
                        'repetition': 'les nuages lointains repetent leur motif tous les 480 px (2 fois par 768 px) : limite de la boucle de 40 s'},
        'format': '4:3 vaste', 'size_px': [W, H], 'grid_8px': [W // 8, H // 8],
        'method': 'generation procedurale (nuages, soleil, eclats, degrade de ciel trame) et sprite de Mew genere ; aucune reference ROM ; '
                  'bandes de nuages periodiques (recouvrement circulaire) decalees d un pas fixe par phase',
        'raw_inputs': [{'file': 'source/intro_mew_v1/bruts/mew_a.png', 'sha256': sha(IM.HERE / 'bruts/mew_a.png'), 'utilise': True, 'editions': 0,
                        'note': 'resample a la grille native 11,75 px (66 x 58, 13 couleurs) : bruts/mew_natif.png'}],
        'layer_order_bottom_to_top': [files[nm] for nm in ORDER],
        'ciel': {'haut': list(SKY_TOP), 'horizon': list(SKY_HOR), 'bandes': 14, 'trame': 'Bayer 4 x 4'},
        'soleil': {'centre_logique': list(SUN[:2]), 'rayon_logique': SUN[2], 'rayons': 14, 'phases': ANIM['soleil'][0], 'frame_length_ticks': ANIM['soleil'][1],
                   'loi': 'rotation de 2/12 rayon par phase : la figure (deux longueurs de rayon alternees) revient a l identique en 12 phases'},
        'nuages_loin': {'phases': 240, 'frame_length_ticks': 10, 'periode_px': CLOUD_STRIPS['nuages_loin'][0] * UP, 'pas_px': CLOUD_STRIPS['nuages_loin'][1] * UP, 'vitesse_px_s': speeds['nuages_loin']},
        'nuages_moyens': {'phases': 240, 'frame_length_ticks': 10, 'periode_px': CLOUD_STRIPS['nuages_moyens'][0] * UP, 'pas_px': CLOUD_STRIPS['nuages_moyens'][1] * UP, 'vitesse_px_s': speeds['nuages_moyens']},
        'mer': {'phases': 240, 'frame_length_ticks': 10, 'periode_px': CLOUD_STRIPS['mer'][0] * UP, 'pas_px': CLOUD_STRIPS['mer'][1] * UP, 'vitesse_px_s': speeds['mer'],
                'contenu': 'nuages proches et mer de nuages (deux copies decalees de 360 px logiques, recouvrement circulaire)'},
        'mew': {'phases': 8, 'frame_length_ticks': 6, 'centre_px': [MEW_C[0] * UP, MEW_C[1] * UP], 'bosse_px': [bob(k) * UP for k in range(8)],
                'taille_native': [int(mew.shape[1]), int(mew.shape[0])], 'couleurs': int(len(np.unique(mew[mew[..., 3] > 0][:, :3], axis=0))),
                'loi': 'pose k de la queue (onde calculee, boucle exacte), bosse round(3 sin(2 pi k / 8)) px logiques'},
        'eclats': {'phases': 8, 'frame_length_ticks': 6, 'tons': [list(c) for c in SPARK], 'emissions_par_cycle': 8, 'vie_pas': 11},
        'scene_loop_ticks': LOOP_TICKS,
        'access': {'markers': markers, 'blocked_cells': int(blocked.sum()), 'total_cells': int(blocked.size),
                   'rule': 'fond de cinematique : toute la grille est bloquante, marqueurs de repere (entrance, mew, soleil) seulement'},
        'pmdo': {'target': '0.8.12', 'asset': ASSET, 'namespace': NAMESPACE, 'tiles_per_bank': counts, 'banks': list(counts),
                 'runtime_tested': False, 'warp': 'aucun'},
        'art_approved': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(OUT / 'manifest.json', STAGE / 'manifest.json')
    print(json.dumps({'tiles': counts, 'vitesses_px_s': speeds}, indent=1))


if __name__ == '__main__':
    build()
