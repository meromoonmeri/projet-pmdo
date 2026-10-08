"""Tests LGV1 — géométrie 4:3, couches, palette, accès et sérialisation PMDO.

.venv/bin/python -m unittest source.serie_sources_croisees_v1.lac_de_verre.test_build -v
Ce sont des tests de fichiers et de grille, pas un test du moteur PMDO.
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
MANIFEST = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
PALETTES = json.loads((OUT / 'palette_reference.json').read_text(encoding='utf-8'))
W, H = MANIFEST['size_px']


def load_rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert('RGBA'))


def water_frames() -> list[np.ndarray]:
    n = MANIFEST['water']['frames']
    return [load_rgba(OUT / f'animation/eau/LGV1_00_eau_f{i:02d}.png') for i in range(n)]


def static_entries() -> list[dict]:
    return MANIFEST['layers_bottom_to_top'][1:]


def static_layers() -> list[np.ndarray]:
    return [load_rgba(OUT / entry['file']) for entry in static_entries()]


def loadmod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
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

    def test_layer_export_directory_has_only_manifest_names(self):
        expected = {Path(entry['file']).name for entry in static_entries()}
        actual = {path.name for path in (OUT / 'calques').glob('*.png')}
        self.assertEqual(actual, expected)

    def test_exact_4_3_normalization_and_tile_grid(self):
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

    def test_palette_is_reference_sampled_and_layers_use_the_right_palette(self):
        shared = {tuple(c) for c in PALETTES['shared_palette_rgb']}
        crystals = {tuple(c) for c in PALETTES['crystal_palette_rgb']}
        water = {tuple(c) for c in PALETTES['water_ramp_rgb']}
        self.assertEqual(len(shared), 96)
        self.assertEqual(len(crystals), 28)
        self.assertEqual(len(water), 10)
        self.assertEqual(MANIFEST['palette']['shared_colors'], 96)
        self.assertEqual(MANIFEST['palette']['crystal_colors'], 28)
        for entry, layer in zip(static_entries(), static_layers()):
            visible = layer[layer[..., 3] > 0, :3]
            colors = {tuple(c) for c in np.unique(visible, axis=0)}
            allowed = crystals if 'cristaux' in entry['name'] else shared
            self.assertTrue(colors <= allowed, entry['name'])
        for frame in water_frames():
            visible = frame[frame[..., 3] > 0, :3]
            self.assertTrue({tuple(c) for c in np.unique(visible, axis=0)} <= water)
        # The principal generated ground material meets the documented <35 RGB fit target.
        self.assertLess(MANIFEST['palette']['generated_material_distance_rgb']['base_sol']['mean_rgb_euclidean'], 35)
        self.assertLess(MANIFEST['palette']['generated_material_distance_rgb']['cristaux']['mean_rgb_euclidean'], 35)

    def test_key_removed_and_alpha_binary(self):
        for entry, layer in zip(static_entries(), static_layers()):
            self.assertTrue(set(np.unique(layer[..., 3])) <= {0, 255}, entry['name'])
            visible = layer[layer[..., 3] > 0, :3].astype(int)
            magenta_like = (visible[:, 0] > 200) & (visible[:, 2] > 200) & (visible[:, 1] < 90)
            self.assertEqual(int(magenta_like.sum()), 0, entry['name'])
        for frame in water_frames():
            self.assertTrue(set(np.unique(frame[..., 3])) <= {0, 255})
            visible = frame[frame[..., 3] > 0, :3].astype(int)
            self.assertGreater(len(visible), 20_000)
            magenta_like = (visible[:, 0] > 200) & (visible[:, 2] > 200) & (visible[:, 1] < 90)
            self.assertEqual(int(magenta_like.sum()), 0)

    def test_water_cycle_is_stable_and_loops(self):
        frames = water_frames()
        mask = frames[0][..., 3] == 255
        self.assertGreater(int(mask.sum()), 20_000)
        changes = []
        for i, frame in enumerate(frames):
            self.assertTrue(np.array_equal(frame[..., 3] == 255, mask))
            changes.append(int(np.any(frame[mask] != frames[(i + 1) % len(frames)][mask], axis=1).sum()))
        self.assertTrue(all(v > 0 for v in changes), changes)
        self.assertLess(max(changes), 2 * min(changes) + 1, changes)
        self.assertEqual(MANIFEST['water']['frames'], 4)
        self.assertEqual(MANIFEST['water']['frame_length_ticks'], 10)
        self.assertFalse(MANIFEST['runtime_tested'])

    def test_scene_coverage_matches_land_and_water_masks(self):
        scene = load_rgba(OUT / 'review/LGV1_scene_t000.png')
        actual = scene[..., 3] > 0
        water_mask = np.asarray(Image.open(OUT / 'masques/LGV1_masque_eau_768.png')) > 0
        floor_mask = np.asarray(Image.open(OUT / 'masques/LGV1_masque_sol_768.png')) > 0
        expected = water_mask | floor_mask
        self.assertTrue(np.array_equal(actual, expected))
        self.assertTrue(np.any(~actual))  # outside-map void remains transparent

    def test_accessibility_and_pmdo_flags(self):
        access = MANIFEST['access']
        self.assertTrue(access['path_found_16x16'])
        self.assertGreater(access['entry_px'][1], H - 40)
        self.assertLess(access['threshold_px'][1], H // 3)
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
        comp = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        comp.alpha_composite(Image.fromarray(water_frames()[0]))
        for layer in static_layers():
            comp.alpha_composite(Image.fromarray(layer))
        self.assertTrue(np.array_equal(np.asarray(comp), merged))
        self.assertIn('cristaux', stack)
        self.assertTrue(np.array_equal(merged, load_rgba(OUT / 'review/LGV1_scene_t000.png')))

    def test_pmdo_ground_tile_banks_and_round_trip(self):
        asset = MANIFEST['pmdo']['asset']
        doc = json.loads((STAGE / f'Data/Ground/{asset}.rsground').read_text(encoding='utf-8'))
        obj = doc['Object']
        self.assertEqual(doc['Version'], '0.8.12.0')
        self.assertEqual(obj['TexSize'], 1)
        self.assertFalse(obj['Released'])
        self.assertEqual(len(obj['Layers']), 7)  # water + five plates + empty Top
        self.assertEqual(obj['Layers'][-1]['Layer'], 4)
        self.assertEqual((len(obj['Layers'][0]['Tiles']), len(obj['Layers'][0]['Tiles'][0])), (96, 72))
        self.assertEqual(len(obj['obstacles']), 96)
        self.assertEqual(len(obj['obstacles'][0]), 72)
        markers = {m['EntName']: m for m in obj['Entities'][0]['Markers']}
        self.assertEqual(set(markers), {'entrance', 'donjon_seuil'})
        self.assertEqual(markers['entrance']['Direction'], 4)
        self.assertEqual(markers['donjon_seuil']['Direction'], 4)
        self.assertEqual(markers['entrance']['Collider']['X'], MANIFEST['access']['entry_px'][0])
        self.assertEqual(markers['donjon_seuil']['Collider']['Y'], MANIFEST['access']['threshold_px'][1])

        reader = loadmod('native_reader_lgv1', ROOT / 'source/cote_v5_expeditions/audit_references.py')
        banks = {p.stem: reader.tiles(p)[1] for p in (STAGE / 'Content/Tile').glob('*.tile')}
        self.assertEqual(set(banks), set(MANIFEST['pmdo']['banks']))
        expected_frames = [water_frames()] + [[layer] for layer in static_layers()]
        for li, expected in enumerate(expected_frames):
            indices = [0, 1, 3] if li == 0 else [0]
            for t in indices:
                decoded = np.zeros((H, W, 4), dtype=np.uint8)
                for x, column in enumerate(obj['Layers'][li]['Tiles']):
                    for y, cell in enumerate(column):
                        for track in cell['Layers']:
                            frames = track['Frames']
                            ref = frames[t % len(frames)]
                            tile_rgba = reader.straight(banks[ref['Sheet']][ref['TexLoc']['X'], ref['TexLoc']['Y']])
                            decoded[y*8:y*8+8, x*8:x*8+8] = np.asarray(tile_rgba)
                self.assertTrue(np.array_equal(decoded, expected[t]), (li, t))
        tools = loadmod('index_tools_lgv1', ROOT / 'source/pmdo_cote/INSTALLER.py')
        self.assertEqual(set(tools.read_index(STAGE / 'Content/Tile/index.idx')), set(MANIFEST['pmdo']['banks']))
        self.assertIn('0.8.12.0', (STAGE / 'Mod.xml').read_text(encoding='utf-8'))
        self.assertFalse(MANIFEST['pmdo']['runtime_tested'])


if __name__ == '__main__':
    unittest.main()
