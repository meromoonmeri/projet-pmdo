"""Packager — Fin Forêt Brumeuse V1 (FFB1, 4:3).
Lancer : .venv/bin/python source/fin_foret_brumeuse_v1/package.py
"""
from pathlib import Path
import base64, io, json, zipfile
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/fin_foret_brumeuse_v1'
STAGE = R / '.cache/fin_foret_brumeuse_v1/fin_foret_brumeuse'
HTML = R / 'apercu_fin_foret_brumeuse_v1.html'
ZIP_ART = R / 'livrable_fin_foret_brumeuse_v1.zip'
ZIP_MOD = R / 'mod_fin_foret_brumeuse_pmdo_0812.zip'


def uri(p):
    return 'data:image/png;base64,' + base64.b64encode(Path(p).read_bytes()).decode()


def collision_overlay(m):
    w, h = m['size_px']
    doc = json.loads((STAGE / f"Data/Ground/{m['pmdo']['asset']}.rsground").read_text())
    blocked = np.array([[c['Tags'] for c in col] for col in doc['Object']['obstacles']]).T
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    for y, x in zip(*np.nonzero(blocked)):
        dr.rectangle([x*8, y*8, x*8+7, y*8+7], fill=(220, 40, 40, 95))
    for k, c in (('entry_px', (255, 230, 40, 255)), ('boss_px', (255, 140, 40, 255)), ('objective_px', (60, 220, 255, 255))):
        qx, qy = m['access'][k]
        dr.rectangle([qx, qy, qx + 15, qy + 15], outline=c, width=2)
    b = io.BytesIO(); im.save(b, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def main():
    m = json.loads((O / 'manifest.json').read_text())
    stack = []
    for L in m['layers']:
        frames = [O / L['file']] if L['phases'] == 1 else [O / L['file'].replace('fNN', f'f{t:02d}') for t in range(L['phases'])]
        stack.append({'id': Path(L['file']).stem.replace('_fNN', ''), 'ticks': L['ticks'], 'frames': [uri(p) for p in frames]})
    poses = []
    for k in ('feuille', 'luciole'):
        for i in range(6):
            p = O / f'poses/FFB1_{k}_{i}.png'; im = Image.open(p)
            poses.append({'id': f'{k} {i}', 'w': im.width, 'h': im.height, 'uri': uri(p)})
    data = {'size': m['size_px'], 'loop': m['scene_loop_ticks'], 'entry': m['access']['entry_px'],
            'surface': '#3c6e3c', 'stack': stack, 'poses': poses, 'collisions': collision_overlay(m)}
    tpl = (HERE / 'viewer_template.html').read_text()
    HTML.write_text(tpl.replace('__DATA__', json.dumps(data, separators=(',', ':'))))

    with zipfile.ZipFile(ZIP_ART, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(O.rglob('*')):
            if p.is_file():
                z.write(p, Path('fin_foret_brumeuse_v1') / p.relative_to(O))
        for p in sorted((HERE / 'bruts').rglob('*.png')):
            z.write(p, Path('fin_foret_brumeuse_v1/bruts') / p.relative_to(HERE / 'bruts'))
        z.write(HTML, Path('fin_foret_brumeuse_v1') / HTML.name)

    with zipfile.ZipFile(ZIP_MOD, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(STAGE.rglob('*')):
            if p.is_file():
                z.write(p, Path('fin_foret_brumeuse') / p.relative_to(STAGE))
    print(json.dumps({'html_kb': round(HTML.stat().st_size / 1024, 1),
                      'art_zip_kb': round(ZIP_ART.stat().st_size / 1024, 1),
                      'mod_zip_kb': round(ZIP_MOD.stat().st_size / 1024, 1)}))


if __name__ == '__main__':
    main()
