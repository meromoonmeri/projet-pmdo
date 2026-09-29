"""Contrôles images, boucles, partition des calques, accès et Ground PMDO (pas un test en jeu).
Lancer : .venv/bin/python -m unittest source.entree_mt_blaze_sud_nord_v1.test_build -v
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
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
OUT = R / 'renders/entree_mt_blaze_sud_nord_v1'
RAW = HERE / 'bruts'
STAGE = R / '.cache/entree_mt_blaze_sud_nord_v1/entree_mt_blaze_sud_nord'
PFX = 'EMB1'
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


B = loadmod('emb1_build_for_tests', HERE / 'build.py')
LAYERS = {layer['name']: [read_layer(layer, t) for t in range(layer['phases'])] for layer in M['layers']}
MASKS = {path.stem.replace(PFX + '_masque_', ''): np.array(Image.open(path)) > 0
         for path in (OUT / 'masques').glob(f'{PFX}_masque_*.png')}


def alpha(array):
    return array[..., 3] == 255


def magenta_pixels(array):
    pixels = array[alpha(array), :3].astype(int)
    return ((pixels[:, 0] - pixels[:, 1] > 60) & (pixels[:, 2] - pixels[:, 1] > 60) &
            (pixels[:, 0] > 130) & (pixels[:, 2] > 130))


def scene_from_layers(tick=0):
    scene = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for record in M['layers']:
        frame = (tick // record['ticks']) % record['phases']
        scene.alpha_composite(Image.fromarray(LAYERS[record['name']][frame]))
    return np.array(scene)


class Build(unittest.TestCase):
    def test_raw_assets_and_reference_provenance(self):
        for record in M['raw_inputs']:
            path = R / record['file']
            self.assertTrue(path.is_file(), path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record['sha256'])
            with Image.open(path) as image:
                self.assertEqual(list(image.size), record['size'])
            self.assertEqual(record['size'], [1200, 896])
        self.assertEqual([item['file'] for item in M['generation']], ['decor.png', 'sol_complet.png', 'lave_texture.png'])
        self.assertEqual(M['reference_da']['files_user_supplied'], ['Rescue_Team_-_Mt._Blaze_Entrance.png', '221081.png'])
        self.assertFalse(M['reference_da']['local_copies'])
        self.assertIsNone(M['reference_da']['metric'])
        self.assertEqual(M['prefix'], PFX)
        self.assertFalse(M['art_approved'])
        self.assertFalse(M['pmdo']['runtime_tested'])
        self.assertFalse(M['tool_maps_pmdsky']['use_for_this_map'])

    def test_dimensions_names_and_binary_alpha(self):
        self.assertEqual((W, H), (768, 576))
        self.assertEqual(W * 3, H * 4)
        self.assertEqual(M['grid_8px'], [96, 72])
        self.assertEqual([record['name'] for record in M['layers']],
                         ['sol_complet', 'ombres', 'lave', 'sentier', 'eboulis', 'parois', 'piliers', 'grotte', 'lueurs', 'braises'])
        for name, frames in LAYERS.items():
            for frame in frames:
                self.assertEqual(frame.shape, (H, W, 4), name)
                self.assertTrue(set(np.unique(frame[..., 3])) <= {0, 255}, name)
                self.assertFalse(magenta_pixels(frame).any(), f'magenta residue in {name}')

    def test_static_partition_and_floor(self):
        self.assertTrue(alpha(LAYERS['sol_complet'][0]).all())
        categories = ('lave', 'sentier', 'eboulis', 'parois', 'piliers', 'grotte')
        cover = np.zeros((H, W), dtype=np.uint8)
        for name in categories:
            cover += alpha(LAYERS[name][0]).astype(np.uint8)
            self.assertGreater(int(alpha(LAYERS[name][0]).sum()), 300, name)
        self.assertTrue((cover == 1).all(), 'solid layers must form an exclusive full-frame partition')
        self.assertGreater(int(alpha(LAYERS['ombres'][0]).sum()), 100)
        self.assertEqual(int(M['segmentation']['pixels_magenta_repeints']), M['segmentation']['pixels_magenta_ecartes'])

    def test_two_lava_banks_and_clear_trail(self):
        labels, count = nd.label(MASKS['lave'], structure=np.ones((3, 3), dtype=bool))
        self.assertEqual(count, 2)
        centers = []
        for i in (1, 2):
            ys, xs = np.nonzero(labels == i)
            centers.append(float(xs.mean()))
            self.assertGreater(int(len(xs)), 5_000)
        self.assertLess(min(centers), W / 2)
        self.assertGreater(max(centers), W / 2)
        walk = MASKS['sentier']
        ys, xs = np.nonzero(walk)
        self.assertLess(int(ys.min()), H * 0.4)
        self.assertGreater(int(ys.max()), H - 24)
        self.assertGreater(float(walk[H - 20:H, W // 2 - 22:W // 2 + 22].mean()), 0.7)
        self.assertGreater(float(walk[H // 3:H // 2, W // 2 - 22:W // 2 + 22].mean()), 0.5)
        self.assertFalse((MASKS['sentier'] & MASKS['lave']).any())

    def test_animation_loops_and_visible_motion(self):
        for name in ('lave', 'lueurs', 'braises'):
            self.assertEqual(len(LAYERS[name]), 24)
            self.assertEqual(next(layer['ticks'] for layer in M['layers'] if layer['name'] == name), 10)
            self.assertTrue(any(alpha(frame).any() for frame in LAYERS[name]))
        self.assertFalse(np.array_equal(LAYERS['lave'][0], LAYERS['lave'][12]))
        self.assertFalse(np.array_equal(LAYERS['lueurs'][0], LAYERS['lueurs'][12]))
        self.assertFalse(np.array_equal(LAYERS['braises'][0], LAYERS['braises'][12]))

        source_masks, _, _ = B.classify(B.rgb(RAW / 'decor.png'))
        _, lava_colors = B.down_class(B.rgb(RAW / 'lave_texture.png'), {'lave': source_masks['lave']}, ['lave'])
        surface = B.rgba(lava_colors['lave'], MASKS['lave'])
        lava_check = B.make_lava_frames(surface, MASKS['lave'], [0, 24])
        glow_check = B.make_glow_frames(surface, MASKS['lave'], [0, 24])
        ember_check, _ = B.make_ember_frames(MASKS['lave'], [0, 24])
        for pair in (lava_check, glow_check, ember_check):
            self.assertTrue(np.array_equal(pair[0], pair[1]))
        self.assertEqual(M['animation']['loop_ticks'], 240)

    def test_collision_path_and_markers(self):
        access = M['access']
        self.assertTrue(access['path_found_16x16'])
        self.assertEqual(access['walkable_cells'] + access['blocked_cells'], 96 * 72)
        self.assertGreater(access['walkable_cells'], 500)
        ex, ey = access['entry_px']
        tx, ty = access['threshold_px']
        self.assertGreater(ey, H - 32)
        self.assertLess(ty, H * 0.4)
        blocked = np.array(Image.open(OUT / 'masques/EMB1_masque_collisions.png')) > 0
        blocked = blocked[::8, ::8]
        self.assertEqual(blocked.shape, (72, 96))
        self.assertFalse(blocked[ey // 8:ey // 8 + 2, ex // 8:ex // 8 + 2].any())
        self.assertFalse(blocked[ty // 8:ty // 8 + 2, tx // 8:tx // 8 + 2].any())
        seen, _ = B.reachable_cells(blocked, (ey // 8, ex // 8))
        self.assertTrue(seen[ty // 8, tx // 8])
        self.assertTrue((MASKS['grotte'] & MASKS['sentier']).sum() == 0)

    def test_scene_and_ora(self):
        frame = scene_from_layers(0)
        saved = load(OUT / 'review/EMB1_scene_t000.png')
        self.assertTrue(np.array_equal(frame, saved))
        with zipfile.ZipFile(OUT / 'EMB1_entree_mt_blaze_calques.ora') as archive:
            merged = np.array(Image.open(io.BytesIO(archive.read('mergedimage.png'))).convert('RGBA'))
            stack_xml = archive.read('stack.xml')
        self.assertTrue(np.array_equal(merged, saved))
        self.assertIn(b'Mt. Blaze', stack_xml)
        self.assertEqual(len(list((OUT / 'animation/lave').glob('*.png'))), 24)
        self.assertEqual(len(list((OUT / 'animation/lueurs').glob('*.png'))), 24)
        self.assertEqual(len(list((OUT / 'animation/braises').glob('*.png'))), 24)

    def test_native_ground_and_review_markers(self):
        ground_path = STAGE / f'Data/Ground/{M["pmdo"]["asset"]}.rsground'
        self.assertTrue(ground_path.is_file())
        doc = json.loads(ground_path.read_text(encoding='utf-8'))
        self.assertEqual(doc['Version'], '0.8.12.0')
        obj = doc['Object']
        self.assertEqual(len(obj['Layers']), len(M['layers']) + 1)
        self.assertIn('Top', obj['Layers'][-1]['Name'])
        markers = obj['Entities'][0]['Markers']
        self.assertEqual({marker['EntName'] for marker in markers}, {'entrance', 'donjon_seuil'})
        self.assertEqual(len(obj['obstacles']), 96)
        self.assertEqual(len(obj['obstacles'][0]), 72)
        self.assertLessEqual(M['pmdo']['max_sheet_height_px'], 2048)
        self.assertEqual(set(M['pmdo']['banks']), set(M['pmdo']['tiles_per_bank']))
        self.assertTrue((STAGE / 'Mod.xml').is_file())
        self.assertTrue((OUT / 'review/EMB1_collisions_marqueurs.png').is_file())
        self.assertTrue((OUT / 'review/EMB1_scene_animee.webp').is_file())


if __name__ == '__main__':
    unittest.main()
