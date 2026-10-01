"""Tests -> ZIP projet PMDO + ZIP calques PNG -> aperçu autonome à la racine.
.venv/bin/python source/intro_mew_ciel_v1/package.py   (après build.py)
"""
from pathlib import Path
import base64, json, re, subprocess, sys, zipfile

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/intro_mew_ciel_v1'
S = R / '.cache/intro_mew_ciel_v1/ciel_de_mew'
ANIM = ('soleil', 'nuages_loin', 'nuages_moyens', 'mew', 'mer', 'eclats')


def zipdir(path, items):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for src, arc in items:
            z.write(src, arc)


def main():
    (O / 'README.md').write_text('# IMW2\n\nVoir README_PACK.md.\n')
    subprocess.run([sys.executable, '-m', 'unittest', 'source.intro_mew_ciel_v1.test_build'], cwd=R, check=True)
    M = json.loads((O / 'manifest.json').read_text())
    (O / 'README.md').write_text((HERE / 'README_PACK.md').read_text())
    zipdir(O / 'IMW2_projet_pmdo_0812.zip', [(p, 'ciel_de_mew/' + p.relative_to(S).as_posix()) for p in sorted(S.rglob('*')) if p.is_file()])
    items = [(p, 'calques/' + p.name) for p in sorted((O / 'calques').glob('*.png'))]
    for sub in ANIM:
        items += [(p, f'animation/{sub}/' + p.name) for p in sorted((O / 'animation' / sub).glob('*.png'))]
    items += [(O / 'IMW2_ciel_de_mew_calques.ora', 'IMW2_ciel_de_mew_calques.ora'), (O / 'manifest.json', 'manifest.json'), (O / 'README.md', 'README.md'),
              (O / 'review/IMW2_scene_t000.png', 'apercu/IMW2_scene_t000.png'), (O / 'review/IMW2_scene_animee.webp', 'apercu/IMW2_scene_animee.webp'),
              (O / 'review/IMW2_quatre_instants.png', 'apercu/IMW2_quatre_instants.png')]
    zipdir(O / 'IMW2_calques_png_8px.zip', items)

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
    data = {'size': M['size_px'], 'loop': M['scene_loop_ticks'], 'stack': stack}
    page = (HERE / 'viewer_template.html').read_text().replace('__DATA__', json.dumps(data))
    (R / 'apercu_intro_mew_ciel.html').write_text(page)
    for p in [O / 'IMW2_projet_pmdo_0812.zip', O / 'IMW2_calques_png_8px.zip', R / 'apercu_intro_mew_ciel.html']:
        print(p.relative_to(R), round(p.stat().st_size / 1e6, 2), 'Mo')


if __name__ == '__main__':
    main()
