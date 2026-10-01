"""Tests -> ZIP projet PMDO + ZIP calques PNG -> aperçu autonome racine.
.venv/bin/python source/entree_colonnes_lances_sud_nord_v1/package.py   (après build.py)
"""
from pathlib import Path
import base64, json, re, subprocess, sys, zipfile

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/entree_colonnes_lances_sud_nord_v1'
S = R / '.cache/entree_colonnes_lances_sud_nord_v1/entree_colonnes_lances_sud_nord_v1'
ANIM = ('nuages', 'rochers', 'vitrail', 'eclats')


def zipdir(path, items):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for src, arc in items:
            z.write(src, arc)


def main():
    subprocess.run([sys.executable, '-m', 'unittest', 'source.entree_colonnes_lances_sud_nord_v1.test_build'], cwd=R, check=True)
    M = json.loads((O / 'manifest.json').read_text())
    (O / 'README.md').write_text((HERE / 'README_PACK.md').read_text())
    zipdir(O / 'ECL1_projet_pmdo_0812.zip',
           [(p, 'entree_colonnes_lances_sud_nord_v1/' + p.relative_to(S).as_posix()) for p in sorted(S.rglob('*')) if p.is_file()])
    items = [(p, 'calques/' + p.name) for p in sorted((O / 'calques').glob('*.png'))]
    for sub in ANIM:
        items += [(p, f'animation/{sub}/' + p.name) for p in sorted((O / 'animation' / sub).glob('*.png'))]
    items += [(R / f'source/colonnes_lances_v1/reference/{c}.png', f'reference/{c}.png') for c in ('D30P42A', 'D28P33A')]
    items += [(O / 'review/ECL1_zoom_portique.png', 'apercu/ECL1_zoom_portique.png')]
    items += [(O / 'ECL1_colonnes_lances_calques.ora', 'ECL1_colonnes_lances_calques.ora'), (O / 'manifest.json', 'manifest.json'),
              (O / 'README.md', 'README.md'), (O / 'review/ECL1_scene_t000.png', 'apercu/ECL1_scene_t000.png'),
              (O / 'review/ECL1_scene_animee.webp', 'apercu/ECL1_scene_animee.webp'),
              (O / 'review/ECL1_collisions_marqueurs.png', 'apercu/ECL1_collisions_marqueurs.png')]
    zipdir(O / 'ECL1_calques_png_8px.zip', items)

    def uri(p):
        return 'data:image/png;base64,' + base64.b64encode(Path(p).read_bytes()).decode()
    stack = []
    for p in M['layer_order_bottom_to_top']:
        nm = re.sub(r'_fN+$', '', Path(p).stem.split('_', 2)[2]); mt = re.search(r'fN+', p)
        if mt:
            w = len(mt.group()) - 1
            stack.append({'id': nm, 'ticks': M[nm]['frame_length_ticks'],
                          'frames': [uri(O / p.replace(mt.group(), f'f{t:0{w}d}')) for t in range(M[nm]['phases'])]})
        else:
            stack.append({'id': nm, 'ticks': 60, 'frames': [uri(O / p)]})
    data = {'size': M['size_px'], 'loop': M['scene_loop_ticks'], 'stack': stack, 'surface': 'rgb(183,167,87)', 'poses': [],
            'collisions': uri(O / 'review/ECL1_collisions_marqueurs.png'), 'entry': M['access']['markers']['entrance'], 'threshold': M['access']['markers']['donjon_seuil']}
    page = (HERE / 'viewer_template.html').read_text().replace('__DATA__', json.dumps(data))
    (R / 'apercu_entree_colonnes_lances_sud_nord_v1.html').write_text(page)
    for p in [O / 'ECL1_projet_pmdo_0812.zip', O / 'ECL1_calques_png_8px.zip', R / 'apercu_entree_colonnes_lances_sud_nord_v1.html']:
        print(p.relative_to(R), round(p.stat().st_size / 1e6, 2), 'Mo')


if __name__ == '__main__':
    main()
