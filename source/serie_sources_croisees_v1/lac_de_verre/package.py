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
    (OUT / 'README.md').write_text((HERE / 'README_PACK.md').read_text(encoding='utf-8'), encoding='utf-8')

    project_zip = OUT / 'LGV1_projet_pmdo_0812.zip'
    project_items = [(path, 'lac_de_verre_sud_nord/' + path.relative_to(STAGE).as_posix())
                     for path in sorted(STAGE.rglob('*')) if path.is_file()]
    zip_files(project_zip, project_items)

    layers_zip = OUT / 'LGV1_calques_png_8px.zip'
    layer_items = []
    for item in manifest['layers_bottom_to_top']:
        if item['index'] == 0:
            for i in range(manifest['water']['frames']):
                path = OUT / f"animation/eau/LGV1_00_eau_f{i:02d}.png"
                layer_items.append((path, f'animation/eau/{path.name}'))
            index_path = OUT / 'animation/eau/LGV1_00_indices_f00.png'
            layer_items.append((index_path, f'animation/eau/{index_path.name}'))
        else:
            path = OUT / item['file']
            layer_items.append((path, f"calques/{path.name}"))
    extras = [
        (OUT / 'LGV1_lac_de_verre_calques.ora', 'LGV1_lac_de_verre_calques.ora'),
        (OUT / 'manifest.json', 'manifest.json'),
        (OUT / 'palette_reference.json', 'palette_reference.json'),
        (OUT / 'README.md', 'README.md'),
        (OUT / 'review/LGV1_scene_t000.png', 'review/LGV1_scene_t000.png'),
        (OUT / 'review/LGV1_scene_x2.png', 'review/LGV1_scene_x2.png'),
        (OUT / 'review/LGV1_scene_eau_animee.webp', 'review/LGV1_scene_eau_animee.webp'),
        (OUT / 'review/LGV1_collisions_marqueurs.png', 'review/LGV1_collisions_marqueurs.png'),
        (OUT / 'review/LGV1_palette_96_echantillonnee.png', 'review/LGV1_palette_96_echantillonnee.png'),
    ]
    layer_items.extend(extras)
    zip_files(layers_zip, layer_items)

    payload = {
        'size': manifest['size_px'],
        'frame_ms': manifest['water']['frame_ms'],
        'water': [data_uri(OUT / f"animation/eau/LGV1_00_eau_f{i:02d}.png")
                  for i in range(manifest['water']['frames'])],
        'layers': [{'id': Path(item['file']).stem, 'name': item['name'],
                    'uri': data_uri(OUT / item['file'])}
                   for item in manifest['layers_bottom_to_top'] if item['index'] > 0],
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
