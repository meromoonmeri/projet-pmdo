"""Tests -> ZIP projet PMDO + ZIP calques PNG -> aperçu autonome racine.
.venv/bin/python source/zone_plage_recifs_etoiles_v1/package.py   (après build.py)
"""
from pathlib import Path
import base64, io, json, shutil, subprocess, sys, zipfile

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
LOT = 'zone_plage_recifs_etoiles_v1'
O = R / 'renders' / LOT
NS = LOT
S = R / '.cache' / LOT / NS
PFX = 'ZPR1'
AMB = {'jour': 'J', 'aube': 'A', 'crepuscule': 'C', 'nuit': 'N'}
PAGE = R / f'apercu_{LOT}.html'


def zipdir(path, items):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for src, arc in items:
            z.write(src, arc)


def uri_img(a):
    b = io.BytesIO(); Image.fromarray(a).save(b, format='PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def uri(p):
    return 'data:image/png;base64,' + base64.b64encode(Path(p).read_bytes()).decode()


def main():
    subprocess.run([sys.executable, '-m', 'unittest', f'source.{LOT}.test_build'], cwd=R, check=True)
    shutil.copyfile(HERE / 'README_PACK.md', O / 'README.md')
    M = json.loads((O / 'manifest.json').read_text())
    zipdir(O / f'{PFX}_projet_pmdo_0812.zip', [(p, f'{NS}/' + p.relative_to(S).as_posix()) for p in sorted(S.rglob('*')) if p.is_file()])
    items = [(p, p.relative_to(O).as_posix()) for p in sorted((O / 'calques').rglob('*.png'))]
    items += [(p, p.relative_to(O).as_posix()) for p in sorted((O / 'animation').rglob('*.png'))]
    items += [(p, 'masques/' + p.name) for p in sorted((O / 'masques').glob('*.png'))]
    items += [(O / f'{PFX}_plage_recifs_{a}_calques.ora', f'{PFX}_plage_recifs_{a}_calques.ora') for a in AMB]
    items += [(O / 'manifest.json', 'manifest.json'), (O / 'README.md', 'README.md')]
    items += [(p, 'apercu/' + p.name) for p in sorted((O / 'review').iterdir())]
    zipdir(O / f'{PFX}_calques_png_8px.zip', items)
    W, H = M['size_px']; N = M['mesures']['nuages']; YH = M['horizon_y']
    pool, index = [], {}

    def add(u):
        if u not in index:
            index[u] = len(pool); pool.append(u)
        return index[u]
    data = {'size': M['size_px'], 'amb': {}, 'nuages': N, 'horizon': YH, 'collisions': uri(O / f'review/{PFX}_collisions_marqueurs.png')}
    for a in AMB:
        out = []
        for x in M['ambiances'][a]['layers']:
            base = {'index': x['index'], 'nom': x['nom'], 'ticks': x['ticks'], 'phases': x['phases']}
            if x['nom'] == 'nuages':                       # la bande défile en JS ; les pixels masqués par la terre sont repris d'une autre phase
                h = N['hauteur_px']; ph = N['phases'] // 2; sh = ph * N['pas_px']
                c1 = np.array(Image.open(O / x['file'].replace('fNNN', 'f000')).convert('RGBA'))[YH - h:YH]
                c2 = np.array(Image.open(O / x['file'].replace('fNNN', f'f{ph:03d}')).convert('RGBA'))[YH - h:YH]
                full = c1[:, :N['periode_px']].copy(); part = np.roll(c2[:, :N['periode_px']], -sh, axis=1)
                m = (full[..., 3] == 0) & (part[..., 3] > 0); full[m] = part[m]
                out.append({**base, 'kind': 'nuages', 'img': add(uri_img(full))})
            elif x['phases'] == 1:
                out.append({**base, 'kind': 'fixe', 'img': add(uri(O / x['file']))})
            else:
                out.append({**base, 'kind': 'anim', 'frames': [add(uri(O / x['file'].replace('fNNN', f'f{t:03d}'))) for t in range(x['phases'])]})
        data['amb'][a] = out
    data['pool'] = pool
    PAGE.write_text((HERE / 'viewer_template.html').read_text().replace('__DATA__', json.dumps(data)))
    for p in [O / f'{PFX}_projet_pmdo_0812.zip', O / f'{PFX}_calques_png_8px.zip', PAGE]:
        print(p.relative_to(R), round(p.stat().st_size / 1e6, 2), 'Mo')
    print('images uniques dans l\'aperçu :', len(pool))


if __name__ == '__main__':
    main()
