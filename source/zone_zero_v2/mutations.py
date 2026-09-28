"""Mutations des sorties d'une route fleurie : chacune doit faire échouer au moins un test.
.venv/bin/python source/zone_zero_v2/mutations.py raf1|raf2|raf3   (arbre propre, sorties versionnées ; restaure par git checkout)
"""
import json, re, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image

lot = sys.argv[1] if len(sys.argv) > 1 else 'raf1'; P = lot.upper(); O = Path(f'renders/zone_zero_v2/{P}')


def img(p): return np.array(Image.open(p).convert('RGBA'))
def save(p, a): Image.fromarray(a).save(p)


def man(f):
    d = json.loads((O / 'manifest.json').read_text()); f(d); (O / 'manifest.json').write_text(json.dumps(d, indent=1, ensure_ascii=False))


def m_fleurs_abac(): save(O / f'animation/fleurs/{P}_09_fleurs_f02.png', img(O / f'animation/fleurs/{P}_09_fleurs_f01.png'))
def m_brume_hors_vide():
    p = O / f'animation/brume_profonde/{P}_02_brume_profonde_f05.png'; a = img(p)
    w = np.array(Image.open(O / f'masques/{P}_masque_praticable.png')) > 0; ys, xs = np.nonzero(w); a[ys[:40], xs[:40]] = (40, 80, 96, 255); save(p, a)
def m_brume_figee():
    b = img(O / f'animation/brume_haute/{P}_03_brume_haute_f00.png')
    for t in (1, 2): save(O / f'animation/brume_haute/{P}_03_brume_haute_f{t:02d}.png', b)
def m_cascade_decalee():
    p = O / f'animation/cascades/{P}_12_cascades_f01.png'; save(p, np.roll(img(p), 8, axis=0))
def m_abime_sans_degrade():
    p = O / f'calques/{P}_01_abime.png'; a = img(p); a[a[..., 3] == 255, :3] = 150; save(p, a)
def m_arbre_sur_praticable():
    p = O / f'masques/{P}_masque_praticable.png'; t = np.array(Image.open(O / f'masques/{P}_masque_troncs.png'))
    w = np.array(Image.open(p)); w[t > 0] = 255; Image.fromarray(w).save(p)
def m_fidelite(): man(lambda d: d['fidelite']['herbe'].__setitem__('distance', 40))
def m_runtime(): man(lambda d: d['pmdo'].__setitem__('runtime_tested', True))
def m_sortie(): man(lambda d: d['access']['markers'].__setitem__('sortie', [100, 300]))
def m_bloquees(): man(lambda d: d['access'].__setitem__('blocked_cells', d['access']['blocked_cells'] + 1))
def m_brut():
    p = Path(f'source/zone_zero_v2/{lot}/bruts/decor_gouffre.png'); a = img(p); a[0, 0] = (1, 2, 3, 255); save(p, a)
def m_ecume_sur_terre():
    p = O / f'animation/ecume/{P}_13_ecume_f00.png'; a = img(p); a[560:566, 380:386] = (255, 255, 255, 255); save(p, a)
def m_magenta():
    p = O / f'calques/{P}_07_falaises.png'; a = img(p); ys, xs = np.nonzero(a[..., 3] == 255); a[ys[:5], xs[:5]] = (255, 0, 255, 255); save(p, a)
def m_rejets(): man(lambda d: d['arbres_source'].__setitem__('planches_rejetees', []))
def m_cascade_en_plus(): man(lambda d: d['cascades']['rects'].append(dict(d['cascades']['rects'][0], y0=200, y1=260)))

# ---- passe haute qualité
def m_herbes_figees(): save(O / f'animation/herbes/{P}_08_herbes_f01.png', img(O / f'animation/herbes/{P}_08_herbes_f00.png'))
def m_herbes_sur_falaise():
    p = O / f'animation/herbes/{P}_08_herbes_f00.png'; a = img(p)
    w = np.array(Image.open(O / f'masques/{P}_masque_falaises.png')) > 0; ys, xs = np.nonzero(w); a[ys[:300], xs[:300]] = (95, 183, 87, 255); save(p, a)
def m_herbe_floue():
    p = O / f'calques/{P}_06_sol.png'; a = img(p); m = (a[..., :3] == (135, 247, 119)).all(2); m[::2] = False; a[m, :3] = (128, 238, 108); save(p, a)
def m_embruns_loin():
    p = O / f'animation/embruns/{P}_14_embruns_f03.png'; a = img(p); near = np.zeros(a.shape[:2], bool)
    for c in json.loads((O / 'manifest.json').read_text())['cascades']['rects']:
        near[max(0, c['y0']):c['y1'] + 24, max(0, c['x0'] - 30):c['x1'] + 30] = True
    y, x = next((y, x) for y, x in ((300, 380), (500, 200), (300, 600), (560, 20), (100, 700)) if not near[y:y + 4, x:x + 4].any())
    a[y:y + 4, x:x + 4] = (255, 255, 255, 255); save(p, a)
def m_embruns_figes(): save(O / f'animation/embruns/{P}_14_embruns_f05.png', img(O / f'animation/embruns/{P}_14_embruns_f04.png'))
def m_papillon_saut(): man(lambda d: d['haute_qualite']['papillons']['trajets'][0][10].__setitem__(0, d['haute_qualite']['papillons']['trajets'][0][10][0] + 30))
def m_papillons_absents():
    p = O / f'animation/papillons/{P}_15_papillons_f07.png'; a = img(p); a[:] = 0; save(p, a)
def m_fleurs_monochromes(): man(lambda d: d['fleurs'].__setitem__('couleurs', ['rouge']))


res = {}
for name, f in [(k, v) for k, v in list(globals().items()) if k.startswith('m_')]:
    f()
    out = subprocess.run([sys.executable, '-m', 'unittest', f'source.zone_zero_v2.{lot}.test_build'], capture_output=True, text=True).stderr
    res[name] = sorted(set(re.findall(r'(?:FAIL|ERROR): (test_\w+)', out)))
    subprocess.run(['git', 'checkout', '-q', '--', str(O), f'source/zone_zero_v2/{lot}/bruts'])
for k, v in res.items():
    print(('OK  ' if v else 'RATE'), k, v)
sys.exit(0 if all(res.values()) else 1)
