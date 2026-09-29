"""Contrôles de layout, calques, cycle D41P41A, accessibilité et Ground PMDO (pas un test en jeu)."""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import unittest
import zipfile

import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
OUT = R / 'renders/entree_mt_blaze_sud_nord_v2'
STAGE = R / '.cache/entree_mt_blaze_sud_nord_v2/entree_mt_blaze_sud_nord'
REPORT = R / 'renders/etude_animations_canoniques_sky_v1/rapport.json'
PFX = 'EMB2'
M = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
W, H = M['size_px']


def load(path):
    return np.array(Image.open(path).convert('RGBA'))


def loadmod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_layer(record, phase=0):
    path = record['file']
    if record['phases'] > 1:
        path = path.replace('fNN', f'f{phase:02d}')
    return load(OUT / path)


B = loadmod('emb2_build_for_tests', HERE / 'build.py')
LAYERS = {layer['name']: [read_layer(layer, t) for t in range(layer['phases'])] for layer in M['layers']}
MASKS = {path.stem.replace(PFX + '_masque_', ''): np.array(Image.open(path)) > 0
         for path in (OUT / 'masques').glob(f'{PFX}_masque_*.png')}


def alpha(array):
    return array[..., 3] == 255


def scene_from_layers(tick=0):
    scene = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for record in M['layers']:
        frame = (tick // record['ticks']) % record['phases']
        scene.alpha_composite(Image.fromarray(LAYERS[record['name']][frame]))
    return np.array(scene)


def assert_exact_track(test, name, track_number, dynamic_mask, allowed_slots):
    track = B.canonical_d41_palettes()[track_number]
    frames = LAYERS[name]
    test.assertEqual(len(frames), 13)
    test.assertEqual(dynamic_mask.shape, (H, W))
    test.assertTrue(dynamic_mask.any())
    base = frames[0][..., :3][dynamic_mask]
    row0 = track[0, allowed_slots]
    matches = (base[:, None, :] == row0[None, :, :]).all(-1)
    test.assertTrue(matches.any(1).all(), f'{name}: frame 0 contains colours outside D41 palette {track_number}')
    indices = np.asarray(allowed_slots, dtype=np.int16)[matches.argmax(1)]
    for phase, frame in enumerate(frames):
        actual = frame[..., :3][dynamic_mask]
        expected = track[phase, indices]
        test.assertTrue(np.array_equal(actual, expected), f'{name}: phase {phase} deviates from palette {track_number}')
        test.assertTrue(np.array_equal(alpha(frame), alpha(frames[0])), f'{name}: animated geometry moved at phase {phase}')


class Build(unittest.TestCase):
    def test_sources_and_reference_provenance(self):
        for record in M['raw_inputs']:
            path = R / record['file']
            self.assertTrue(path.is_file(), path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record['sha256'])
            with Image.open(path) as image:
                self.assertEqual(list(image.size), record['size'])
        self.assertEqual(M['reference_da']['local_size_px'], [300, 260])
        self.assertTrue((R / M['reference_da']['local_file']).is_file())
        self.assertIn('Mt. Blaze Entrance', M['reference_da']['title'])
        self.assertFalse(M['art_approved'])
        self.assertFalse(M['pmdo']['runtime_tested'])
        for material in ('sentier', 'lave', 'roche'):
            self.assertLess(M['material_palette_comparison'][material]['rgb_euclidean_distance'], 15)
        self.assertFalse(M['tool_maps_pmdsky']['used_as_source_for_gba_layout'])
        self.assertEqual(M['animation']['palette_report_sha256'],
                         hashlib.sha256(REPORT.read_bytes()).hexdigest())

    def test_dimensions_layer_names_and_binary_alpha(self):
        self.assertEqual((W, H), (768, 576))
        self.assertEqual(W * 3, H * 4)
        self.assertEqual(M['grid_8px'], [96, 72])
        self.assertEqual([record['name'] for record in M['layers']],
                         ['sol_complet', 'ombres', 'lave', 'sentier', 'eboulis', 'parois',
                          'piliers', 'grotte', 'veines_roche'])
        for name, frames in LAYERS.items():
            for frame in frames:
                self.assertEqual(frame.shape, (H, W, 4), name)
                self.assertTrue(set(np.unique(frame[..., 3])) <= {0, 255}, name)

    def test_partition_floor_and_independent_veins(self):
        self.assertTrue(alpha(LAYERS['sol_complet'][0]).all())
        categories = ('lave', 'sentier', 'eboulis', 'parois', 'piliers', 'grotte', 'veines_roche')
        cover = np.zeros((H, W), dtype=np.uint8)
        for name in categories:
            mask = alpha(LAYERS[name][0])
            cover += mask.astype(np.uint8)
            self.assertGreater(int(mask.sum()), 300, name)
        self.assertTrue((cover == 1).all(), 'material layers must form an exclusive full-frame partition')
        self.assertGreater(int(alpha(LAYERS['ombres'][0]).sum()), 100)
        self.assertGreater(int(MASKS['veines_roche'].sum()), 1_000)
        self.assertFalse((MASKS['veines_roche'] & MASKS['lave']).any())
        self.assertFalse((MASKS['veines_roche'] & MASKS['sentier']).any())
        self.assertFalse((MASKS['lave_cycle'] & ~MASKS['lave']).any())

    def test_reference_layout_two_banks_open_foreground_and_cave(self):
        labels, _ = nd.label(MASKS['lave'], structure=np.ones((3, 3), dtype=bool))
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        biggest = np.argsort(sizes)[-2:]
        centers = []
        for label in biggest:
            ys, xs = np.nonzero(labels == label)
            self.assertGreater(len(xs), 5_000)
            centers.append(float(xs.mean()))
        self.assertLess(min(centers), W / 2 - 100)
        self.assertGreater(max(centers), W / 2 + 100)

        walk = MASKS['sentier']
        ys, xs = np.nonzero(walk)
        self.assertLess(ys.min(), H * 0.92)
        self.assertGreater(ys.max(), H - 24)
        self.assertGreater(float(walk[H - 32:H, W // 2 - 36:W // 2 + 36].mean()), 0.75)
        self.assertGreater(int(MASKS['grotte'].sum()), 500)
        self.assertFalse((MASKS['grotte'] & walk).any())

    def test_exact_canonical_d41_palette_cycles(self):
        self.assertEqual(M['animation']['loop_ticks'], 130)
        self.assertEqual(M['animation']['frame_length_ticks'], 10)
        self.assertEqual(M['animation']['phases'], 13)
        self.assertTrue(M['animation']['canonical_cadence_and_palette'])
        self.assertFalse(M['animation']['native_to_red_rescue_team'])
        self.assertEqual([record['phases'] for record in M['layers'] if record['name'] in ('lave', 'veines_roche')],
                         [13, 13])
        self.assertEqual([record['ticks'] for record in M['layers'] if record['name'] in ('lave', 'veines_roche')],
                         [10, 10])
        assert_exact_track(self, 'lave', 10, MASKS['lave_cycle'], list(range(0, 7)) + list(range(11, 15)))
        assert_exact_track(self, 'veines_roche', 11, MASKS['veines_roche'], list(range(4, 15)))

        # Pixels outside the hot lava indices keep the GBA material texture unchanged.
        stable = MASKS['lave'] & ~MASKS['lave_cycle']
        base = LAYERS['lave'][0][..., :3][stable]
        for phase in range(1, 13):
            self.assertTrue(np.array_equal(base, LAYERS['lave'][phase][..., :3][stable]))

    def test_collision_route_and_markers(self):
        access = M['access']
        self.assertTrue(access['path_found_16x16'])
        self.assertEqual(access['walkable_cells'] + access['blocked_cells'], 96 * 72)
        self.assertGreater(access['walkable_cells'], 500)
        ex, ey = access['entry_px']
        tx, ty = access['threshold_px']
        self.assertGreater(ey, H - 32)
        self.assertLess(ty, H * 0.60)
        blocked = np.array(Image.open(OUT / 'masques/EMB2_masque_collisions.png')) > 0
        blocked = blocked[::8, ::8]
        self.assertEqual(blocked.shape, (72, 96))
        self.assertFalse(blocked[ey // 8:ey // 8 + 2, ex // 8:ex // 8 + 2].any())
        self.assertFalse(blocked[ty // 8:ty // 8 + 2, tx // 8:tx // 8 + 2].any())
        seen, _ = B.reachable_cells(blocked, (ey // 8, ex // 8))
        self.assertTrue(seen[ty // 8, tx // 8])

    def test_scene_animation_and_ora(self):
        self.assertTrue(np.array_equal(scene_from_layers(0), load(OUT / 'review/EMB2_scene_t000.png')))
        for tick in (0, 10, 120, 130, 260):
            self.assertTrue(np.array_equal(scene_from_layers(tick), scene_from_layers(tick % 130)))
        with zipfile.ZipFile(OUT / 'EMB2_entree_mt_blaze_calques.ora') as archive:
            merged = np.array(Image.open(io.BytesIO(archive.read('mergedimage.png'))).convert('RGBA'))
            stack_xml = archive.read('stack.xml')
        self.assertTrue(np.array_equal(merged, load(OUT / 'review/EMB2_scene_t000.png')))
        self.assertIn(b'Mt. Blaze', stack_xml)
        self.assertEqual(len(list((OUT / 'animation/lave').glob('*.png'))), 13)
        self.assertEqual(len(list((OUT / 'animation/veines_roche').glob('*.png'))), 13)
        self.assertTrue((OUT / 'review/EMB2_scene_animee.webp').is_file())

    def test_native_ground_and_review_markers(self):
        ground_path = STAGE / f'Data/Ground/{M["pmdo"]["asset"]}.rsground'
        self.assertTrue(ground_path.is_file())
        doc = json.loads(ground_path.read_text(encoding='utf-8'))
        self.assertEqual(doc['Version'], '0.8.12.0')
        obj = doc['Object']
        self.assertEqual(len(obj['Layers']), len(M['layers']) + 1)
        self.assertIn('Top', obj['Layers'][-1]['Name'])
        self.assertEqual({marker['EntName'] for marker in obj['Entities'][0]['Markers']},
                         {'entrance', 'donjon_seuil'})
        self.assertEqual(len(obj['obstacles']), 96)
        self.assertEqual(len(obj['obstacles'][0]), 72)
        self.assertLessEqual(M['pmdo']['max_sheet_height_px'], 2048)
        self.assertEqual(set(M['pmdo']['banks']), set(M['pmdo']['tiles_per_bank']))
        self.assertTrue((STAGE / 'Mod.xml').is_file())
        self.assertTrue((OUT / 'review/EMB2_collisions_marqueurs.png').is_file())


if __name__ == '__main__':
    unittest.main()
