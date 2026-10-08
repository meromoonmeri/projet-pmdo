#!/usr/bin/env python3
"""Run tests, package the PMDO Ground and PNG layers, and build the preview page."""
from pathlib import Path
import base64
import json
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'renders/serie_sources_croisees_v1/lac_de_verre'
STAGE = ROOT / '.cache/serie_sources_croisees_v1/lac_de_verre/lac_de_verre_sud_nord'
PREVIEW = ROOT / 'apercu_serie_sources_croisees_v1.html'


def zip_files(target: Path, items: list[tuple[Path, str]]) -> None:
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, name in items:
            archive.write(path, name)


def data_uri(path: Path) -> str:
    return 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


def main() -> None:
    subprocess.run([sys.executable, '-m', 'unittest',
                    'source.serie_sources_croisees_v1.lac_de_verre.test_build', '-v'],
                   cwd=ROOT, check=True)
    manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    readme = (HERE / 'README_PACK.md').read_text(encoding='utf-8')
    (OUT / 'README.md').write_text(readme, encoding='utf-8')
    (STAGE / 'README.md').write_text(readme, encoding='utf-8')

    project_zip = OUT / 'LGV1_projet_pmdo_0812.zip'
    project_items = [(path, 'lac_de_verre_sud_nord/' + path.relative_to(STAGE).as_posix())
                     for path in sorted(STAGE.rglob('*')) if path.is_file()]
    zip_files(project_zip, project_items)

    layers_zip = OUT / 'LGV1_calques_png_8px.zip'
    layer_items = []
    water_entry = next(item for item in manifest['layers_bottom_to_top'] if item['frames'] > 1)
    for item in manifest['layers_bottom_to_top']:
        if item['frames'] > 1:
            pattern = item['file']
            for i in range(manifest['water']['frames']):
                rel = pattern.replace('fXX.png', f'f{i:02d}.png')
                path = OUT / rel
                layer_items.append((path, rel))
        else:
            path = OUT / item['file']
            layer_items.append((path, item['file']))
    extras = [
        (OUT / 'LGV1_lac_de_verre_calques.ora', 'LGV1_lac_de_verre_calques.ora'),
        (OUT / 'manifest.json', 'manifest.json'),
        (OUT / 'palette_reference.json', 'palette_reference.json'),
        (OUT / 'README.md', 'README.md'),
        (OUT / 'review/LGV1_scene_t000.png', 'review/LGV1_scene_t000.png'),
        (OUT / 'review/LGV1_scene_x2.png', 'review/LGV1_scene_x2.png'),
        (OUT / 'review/LGV1_scene_eau_source.webp', 'review/LGV1_scene_eau_source.webp'),
        (OUT / 'review/LGV1_collisions_marqueurs.png', 'review/LGV1_collisions_marqueurs.png'),
        (OUT / 'review/LGV1_palette_96_sources.png', 'review/LGV1_palette_96_sources.png'),
    ]
    layer_items.extend(extras)
    zip_files(layers_zip, layer_items)

    water_pattern = water_entry['file']
    payload = {
        'size': manifest['size_px'],
        'frame_ms': manifest['water']['frame_ms'],
        'water': [data_uri(OUT / water_pattern.replace('fXX.png', f'f{i:02d}.png'))
                  for i in range(manifest['water']['frames'])],
        'layers': [{'id': Path(item['file']).stem, 'name': item['name'],
                    'uri': data_uri(OUT / item['file'])}
                   for item in manifest['layers_bottom_to_top'] if item['frames'] == 1],
        'collision': data_uri(OUT / 'review/LGV1_collisions_marqueurs.png'),
        'entry': manifest['access']['entry_px'],
        'threshold': manifest['access']['threshold_px'],
    }
    page = (HERE / 'viewer_template.html').read_text(encoding='utf-8').replace('__DATA__', json.dumps(payload, ensure_ascii=False))
    PREVIEW.write_text(page, encoding='utf-8')
    print(json.dumps({
        'preview': str(PREVIEW.relative_to(ROOT)),
        'project_zip': {'path': str(project_zip.relative_to(ROOT)), 'bytes': project_zip.stat().st_size},
        'layers_zip': {'path': str(layers_zip.relative_to(ROOT)), 'bytes': layers_zip.stat().st_size},
        'ground_banks': len(manifest['pmdo']['banks']),
        'format': manifest['format'], 'size_px': manifest['size_px'],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
