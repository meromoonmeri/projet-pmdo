"""Tests LGV1 — source canonique, adaptation 4:3, eau Red et Ground PMDO.

.venv/bin/python -m unittest source.serie_sources_croisees_v1.lac_de_verre.test_build -v
Ces tests vérifient les fichiers, les grilles et les octets sérialisés; ils ne
remplacent pas un test d’exécution dans le moteur PMDO.
"""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import unittest
import zipfile

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'renders/serie_sources_croisees_v1/lac_de_verre'
STAGE = ROOT / '.cache/serie_sources_croisees_v1/lac_de_verre/lac_de_verre_sud_nord'
REFS = HERE / 'references'
MANIFEST = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
PALETTES = json.loads((OUT / 'palette_reference.json').read_text(encoding='utf-8'))
W, H = MANIFEST['size_px']
TILE = MANIFEST['pmdo']['tile_px']


def load_rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert('RGBA'))


def water_entry() -> dict:
    return next(item for item in MANIFEST['layers_bottom_to_top'] if item['frames'] > 1)


def water_frames() -> list[np.ndarray]:
    entry = water_entry()
    pattern = entry['file']
    return [load_rgba(OUT / pattern.replace('fXX.png', f'f{i:02d}.png'))
            for i in range(MANIFEST['water']['frames'])]


def static_entries() -> list[dict]:
    return [item for item in MANIFEST['layers_bottom_to_top'] if item['frames'] == 1]


def static_layers() -> list[np.ndarray]:
    return [load_rgba(OUT / item['file']) for item in static_entries()]


def loadmod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LacDeVerreBuildTests(unittest.TestCase):
    def test_sources_and_hashes(self):
        for item in MANIFEST['raw_inputs'] + MANIFEST['reference_files']:
            path = ROOT / item['file']
            self.assertTrue(path.is_file(), item['file'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item['sha256'], item['file'])
            with Image.open(path) as image:
                self.assertEqual(list(image.size), item['size_px'], item['file'])
        for item in MANIFEST['raw_inputs']:
            self.assertEqual(item['size_px'], [1200, 896])
        for item in MANIFEST['native_source_files']:
            path = ROOT / item['file']
            self.assertTrue(path.is_file(), item['file'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item['sha256'], item['file'])
            self.assertEqual(path.stat().st_size, item['size_bytes'])

    def test_native_ground_decodes_pixel_for_pixel(self):
        builder = loadmod('build_lgv1_native_test', HERE / 'build.py')
        rendered, blocked, meta = builder.render_native_d52()
        reference = Image.open(REFS / 'sky_D52P11A.png').convert('RGBA')
        self.assertTrue(np.array_equal(np.asarray(rendered), np.asarray(reference)))
        self.assertEqual(list(rendered.size), [504, 408])
        self.assertEqual(blocked.shape, (51, 63))
        self.assertTrue(meta['render_matches_reference_png'])
        self.assertEqual(meta['ground_grid'], [63, 51])
        self.assertEqual(builder.adapt_native_canvas(rendered).shape, (408, 544, 3))

    def test_raws_are_4_3_template_size_without_magenta(self):
        raw_base, raw_scene, raw_mask = [Image.open(ROOT / item['file']) for item in MANIFEST['raw_inputs']]
        self.assertEqual(raw_base.size, (1200, 896))
        self.assertEqual(raw_scene.size, (1200, 896))
        self.assertEqual(raw_mask.size, (1200, 896))
        self.assertEqual(set(np.unique(np.asarray(raw_mask))), {0, 255})
        for image in (raw_base.convert('RGB'), raw_scene.convert('RGB')):
            a = np.asarray(image).astype(np.int16)
            r, g, b = a.transpose(2, 0, 1)
            key_like = (r > 200) & (b > 200) & (g < 90)
            self.assertEqual(int(key_like.sum()), 0)

    def test_exact_4_3_normalization_and_native_pad(self):
        adapt = MANIFEST['adaptation_4_3']
        self.assertEqual(adapt['native_ground_grid'], [63, 51])
        self.assertEqual(adapt['native_ground_px'], [504, 408])
        self.assertEqual(adapt['horizontal_reflect_pad_cells_left_right'], [2, 3])
        self.assertEqual(adapt['adapted_grid'], [68, 51])
        self.assertEqual(adapt['adapted_canvas_px'], [544, 408])
        norm = MANIFEST['normalization']
        self.assertEqual(norm['source_px'], [1200, 896])
        self.assertAlmostEqual(norm['scale_uniforme'], 576 / 896)
        self.assertEqual(norm['scaled_px'], [771, 576])
        self.assertEqual(norm['crop_x_left_right'], [1, 2])
        self.assertEqual((W, H), (768, 576))
        self.assertEqual(MANIFEST['grid_8px'], [96, 72])
        self.assertEqual((W % 8, H % 8), (0, 0))
        for layer in water_frames() + static_layers():
            self.assertEqual(layer.shape, (H, W, 4))

    def test_shared_palette_has_96_exact_reference_colors(self):
        shared = {tuple(map(int, color)) for color in PALETTES['shared_palette_rgb']}
        source_water = {tuple(map(int, color)) for color in PALETTES['water_source_rgb']}
        self.assertEqual(len(shared), 96)
        self.assertGreater(len(source_water), 6)
        self.assertLess(len(source_water), 40)
        self.assertEqual(MANIFEST['palette']['shared_colors'], 96)
        self.assertTrue(MANIFEST['palette']['sampling']['all_source_colors_retained'])
        for entry, layer in zip(static_entries(), static_layers()):
            visible = layer[layer[..., 3] > 0, :3]
            colors = {tuple(map(int, c)) for c in np.unique(visible, axis=0)}
            self.assertTrue(colors <= shared, entry['name'])
        for frame in water_frames():
            visible = frame[frame[..., 3] > 0, :3]
            colors = {tuple(map(int, c)) for c in np.unique(visible, axis=0)}
            self.assertTrue(colors <= shared)
        self.assertLess(MANIFEST['palette']['source_rgb_distance']['base_D52P11A']['mean_rgb_euclidean'], 35)
        self.assertLess(MANIFEST['palette']['source_rgb_distance']['eau_T01P02A']['mean_rgb_euclidean'], 35)

    def test_water_uses_all_six_red_frames_with_a_stable_mask(self):
        frames = water_frames()
        self.assertEqual(len(frames), 6)
        mask = frames[0][..., 3] == 255
        self.assertGreater(int(mask.sum()), 5_000)
        self.assertLess(int(mask.sum()), 15_000)
        changes = []
        for i, frame in enumerate(frames):
            self.assertTrue(np.array_equal(frame[..., 3] == 255, mask))
            changes.append(int(np.any(frame[mask] != frames[(i + 1) % len(frames)][mask], axis=1).sum()))
        self.assertGreaterEqual(sum(value > 0 for value in changes), 4, changes)
        unique_frames = {hashlib.sha256(frame.tobytes()).hexdigest() for frame in frames}
        self.assertEqual(len(unique_frames), MANIFEST['water']['distinct_frames_after_export'])
        self.assertGreaterEqual(len(unique_frames), 3)
        for index, source in enumerate(MANIFEST['water']['source_frames']):
            self.assertGreater(source['water_geometry_coverage'], 0.88)
            self.assertIn('frame 0 water geometry', source['mask_source'])
            self.assertEqual(source['crop_xyxy'], [270, 226, 334, 258])
            self.assertEqual(source['file'], f'source/serie_sources_croisees_v1/lac_de_verre/references/red_T01P02A_frame{index}.png')
        self.assertEqual(MANIFEST['water']['frames'], 6)
        self.assertEqual(MANIFEST['water']['frame_length_ticks'], 10)
        self.assertEqual(MANIFEST['water']['loop_seconds'], 1.0)
        self.assertFalse(MANIFEST['runtime_tested'])

    def test_alpha_is_separate_and_scene_composites_exactly(self):
        base, = static_layers()
        self.assertTrue(np.all(base[..., 3] == 255))
        scene = load_rgba(OUT / 'review/LGV1_scene_t000.png')
        self.assertTrue(np.all(scene[..., 3] == 255))
        expected = Image.fromarray(base, 'RGBA')
        expected.alpha_composite(Image.fromarray(water_frames()[0], 'RGBA'))
        self.assertTrue(np.array_equal(np.asarray(expected), scene))
        mask = np.asarray(Image.open(OUT / 'masques/LGV1_masque_lac_768x576.png')) > 0
        self.assertTrue(np.array_equal(mask, water_frames()[0][..., 3] > 0))
        self.assertTrue(np.any(mask))

    def test_no_key_color_and_binary_layer_alpha(self):
        for entry, layer in zip(static_entries(), static_layers()):
            self.assertTrue(set(np.unique(layer[..., 3])) <= {0, 255}, entry['name'])
            visible = layer[layer[..., 3] > 0, :3].astype(int)
            magenta_like = (visible[:, 0] > 200) & (visible[:, 2] > 200) & (visible[:, 1] < 90)
            self.assertEqual(int(magenta_like.sum()), 0, entry['name'])
        for frame in water_frames():
            self.assertTrue(set(np.unique(frame[..., 3])) <= {0, 255})
            visible = frame[frame[..., 3] > 0, :3].astype(int)
            magenta_like = (visible[:, 0] > 200) & (visible[:, 2] > 200) & (visible[:, 1] < 90)
            self.assertEqual(int(magenta_like.sum()), 0)

    def test_accessibility_and_pmdo_flags(self):
        access = MANIFEST['access']
        self.assertTrue(access['path_found_16x16'])
        self.assertLess(access['entry_px'][0], access['threshold_px'][0])
        self.assertGreater(access['threshold_px'][0], W * .65)
        self.assertGreater(access['blocked_cells'], 0)
        self.assertLess(access['blocked_cells'], access['total_cells'])
        self.assertFalse(MANIFEST['art_approved'])
        self.assertFalse(MANIFEST['native_texture_certified'])
        self.assertFalse(MANIFEST['pmdo']['runtime_tested'])
        self.assertEqual(MANIFEST['pmdo']['target'], '0.8.12')
        self.assertEqual(MANIFEST['pmdo']['tex_size'], 1)

    def test_openraster_recomposes_exactly(self):
        with zipfile.ZipFile(OUT / 'LGV1_lac_de_verre_calques.ora') as archive:
            self.assertEqual(archive.read('mimetype'), b'image/openraster')
            merged = np.asarray(Image.open(io.BytesIO(archive.read('mergedimage.png'))).convert('RGBA'))
            stack = archive.read('stack.xml').decode('utf-8')
        comp = Image.fromarray(static_layers()[0], 'RGBA')
        comp.alpha_composite(Image.fromarray(water_frames()[0], 'RGBA'))
        self.assertTrue(np.array_equal(np.asarray(comp), merged))
        self.assertIn('zone_glace_D52P11A', stack)
        self.assertIn('eau_lac_T01P02A', stack)
        self.assertTrue(np.array_equal(merged, load_rgba(OUT / 'review/LGV1_scene_t000.png')))

    def test_pmdo_ground_banks_and_round_trip(self):
        asset = MANIFEST['pmdo']['asset']
        doc = json.loads((STAGE / f'Data/Ground/{asset}.rsground').read_text(encoding='utf-8'))
        obj = doc['Object']
        self.assertEqual(doc['Version'], '0.8.12.0')
        self.assertEqual(obj['TexSize'], 1)
        self.assertFalse(obj['Released'])
        self.assertEqual(len(obj['Layers']), 3)  # base + eau + Top
        self.assertEqual(obj['Layers'][-1]['Layer'], 4)
        self.assertEqual((len(obj['Layers'][0]['Tiles']), len(obj['Layers'][0]['Tiles'][0])), (96, 72))
        self.assertEqual(len(obj['obstacles']), 96)
        self.assertEqual(len(obj['obstacles'][0]), 72)
        markers = {marker['EntName']: marker for marker in obj['Entities'][0]['Markers']}
        self.assertEqual(set(markers), {'entrance', 'donjon_seuil'})
        self.assertEqual(markers['entrance']['Collider']['X'], MANIFEST['access']['entry_px'][0])
        self.assertEqual(markers['donjon_seuil']['Collider']['X'], MANIFEST['access']['threshold_px'][0])

        reader = loadmod('native_reader_lgv1', ROOT / 'source/cote_v5_expeditions/audit_references.py')
        banks = {path.stem: reader.tiles(path)[1] for path in (STAGE / 'Content/Tile').glob('*.tile')}
        self.assertEqual(set(banks), set(MANIFEST['pmdo']['banks']))
        expected_frames = [[static_layers()[0]], water_frames()]
        for layer_index, expected in enumerate(expected_frames):
            for frame_index, expected_frame in enumerate(expected):
                decoded = np.zeros((H, W, 4), dtype=np.uint8)
                for x, column in enumerate(obj['Layers'][layer_index]['Tiles']):
                    for y, cell in enumerate(column):
                        for track in cell['Layers']:
                            source_frames = track['Frames']
                            ref = source_frames[frame_index % len(source_frames)]
                            tile = reader.straight(banks[ref['Sheet']][ref['TexLoc']['X'], ref['TexLoc']['Y']])
                            decoded[y*TILE:y*TILE+TILE, x*TILE:x*TILE+TILE] = np.asarray(tile)
                self.assertTrue(np.array_equal(decoded, expected_frame), (layer_index, frame_index))
        tools = loadmod('index_tools_lgv1', ROOT / 'source/pmdo_cote/INSTALLER.py')
        self.assertEqual(set(tools.read_index(STAGE / 'Content/Tile/index.idx')), set(MANIFEST['pmdo']['banks']))
        metadata = (STAGE / 'Mod.xml').read_text(encoding='utf-8')
        self.assertIn('0.8.12.0', metadata)
        self.assertIn('D52P11A', metadata)
        self.assertNotIn('magenta', metadata.lower())
        self.assertFalse(MANIFEST['pmdo']['runtime_tested'])


if __name__ == '__main__':
    unittest.main()
