"""Tests → ZIP PMDO + ZIP calques → aperçu autonome à la racine.
Lancer après build.py : .venv/bin/python source/entree_mt_blaze_sud_nord_v2/package.py
"""
from pathlib import Path
import base64
import json
import re
import subprocess
import sys
import zipfile

from PIL import Image

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
OUT = R / 'renders/entree_mt_blaze_sud_nord_v2'
STAGE = R / '.cache/entree_mt_blaze_sud_nord_v2/entree_mt_blaze_sud_nord'
PFX = 'EMB2'
NAMESPACE = 'entree_mt_blaze_sud_nord_v2'
ANIMS = ('lave', 'veines_roche')
SOURCE_ASSETS = {
    'layout': HERE / 'bruts/layout_magenta.png',
    'lave': HERE / 'bruts/lave_texture_rgba.png',
    'veines_roche': HERE / 'bruts/veines_roche_rgba.png',
}
REVIEW = ('scene_t000.png', 'scene_animee.webp', 'collisions_marqueurs.png')


def zip_items(path, items):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, arcname in items:
            archive.write(source, arcname)


def data_uri(path):
    return 'data:image/png;base64,' + base64.b64encode(Path(path).read_bytes()).decode('ascii')


def image_size(path):
    with Image.open(path) as image:
        return list(image.size)


def main():
    subprocess.run([sys.executable, '-m', 'unittest', 'source.entree_mt_blaze_sud_nord_v2.test_build', '-v'], cwd=R, check=True)
    manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    project_items = [(path, f'{NAMESPACE}/' + path.relative_to(STAGE).as_posix())
                     for path in sorted(STAGE.rglob('*')) if path.is_file()]
    project_zip = OUT / f'{PFX}_projet_pmdo_0812.zip'
    zip_items(project_zip, project_items)

    layer_items = [(path, 'calques/' + path.name) for path in sorted((OUT / 'calques').glob('*.png'))]
    for anim in ANIMS:
        layer_items += [(path, f'animation/{anim}/' + path.name)
                        for path in sorted((OUT / 'animation' / anim).glob('*.png'))]
    layer_items += [(path, 'masques/' + path.name) for path in sorted((OUT / 'masques').glob('*.png'))]
    layer_items += [(path, f'sources/{path.name}') for path in SOURCE_ASSETS.values()]
    layer_items.append((HERE / 'reference/mt_blaze_reference_300x260.png',
                        'reference/mt_blaze_reference_300x260.png'))
    layer_items += [(OUT / f'{PFX}_entree_mt_blaze_calques.ora', f'{PFX}_entree_mt_blaze_calques.ora'),
                    (OUT / 'manifest.json', 'manifest.json'),
                    (OUT / 'README.md', 'README.md')]
    layer_items += [(OUT / 'review' / f'{PFX}_{name}', f'apercu/{PFX}_{name}') for name in REVIEW]
    layers_zip = OUT / f'{PFX}_calques_png_8px.zip'
    zip_items(layers_zip, layer_items)

    stack = []
    for layer in manifest['layers']:
        if layer['phases'] == 1:
            files = [OUT / layer['file']]
        else:
            files = [OUT / layer['file'].replace('fNN', f'f{phase:02d}') for phase in range(layer['phases'])]
        stack.append({'id': layer['name'], 'ticks': layer['ticks'], 'frames': [data_uri(path) for path in files]})
    data = {
        'size': manifest['size_px'],
        'loop': manifest['animation']['loop_ticks'],
        'seconds': manifest['animation']['loop_ticks'] / 60,
        'stack': stack,
        'poses': [],
        'collisions': data_uri(OUT / 'review' / f'{PFX}_collisions_marqueurs.png'),
        'entry': manifest['access']['entry_px'],
        'threshold': manifest['access']['threshold_px'],
        'sources': {
            name: {
                'uri': data_uri(path),
                'size': image_size(path),
                'label': {
                    'layout': 'Layout source — placement lave en magenta pur #FF00FF',
                    'lave': 'Texture lave RGBA — alpha défini par le key magenta exact',
                    'veines_roche': 'Texture veines rocheuses RGBA — isolée de la lave et du sentier',
                }[name],
            }
            for name, path in SOURCE_ASSETS.items()
        },
    }
    page = (HERE / 'viewer_template.html').read_text(encoding='utf-8').replace('__DATA__', json.dumps(data, ensure_ascii=False))
    preview = R / 'apercu_entree_mt_blaze_sud_nord_v2.html'
    preview.write_text(page, encoding='utf-8')

    with zipfile.ZipFile(layers_zip) as archive:
        for source in SOURCE_ASSETS.values():
            archive_name = f'sources/{source.name}'
            assert archive.read(archive_name) == source.read_bytes(), f'missing or altered package source {archive_name}'
    for source in SOURCE_ASSETS.values():
        assert data_uri(source) in page, f'preview does not embed source {source.name}'
    for path in (project_zip, layers_zip, preview):
        print(f'{path.relative_to(R)}  {path.stat().st_size / 1_000_000:.2f} Mo')


if __name__ == '__main__':
    main()
