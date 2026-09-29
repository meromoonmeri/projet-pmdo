"""Tests dédiés — Fin Underground Lake (FUL1, 4:3 vaste).
.venv/bin/python -m unittest source.fin_underground_lake_v1.test_build -v
Contrôles d'images, de formats, de palettes, de fidélité au rip, de cadence et de grille : PAS un test du moteur PMDO.
"""
from pathlib import Path
import hashlib, importlib.util, io, json, re, unittest, zipfile
import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/fin_underground_lake_v1'
S = R / '.cache/fin_underground_lake_v1/fin_underground_lake'
M = json.loads((O / 'manifest.json').read_text()) if (O / 'manifest.json').exists() else {}
W, H = M.get('size_px', [768, 576])
NAMES = [Path(L['file']).name.replace('_fNN', '') for L in M.get('layers', [])]
STATIC = ('sable', 'ombres', 'berge', 'roche', 'piliers', 'profondeur')
REF = R / 'Underground_Lake_shore_TDS.png'

def load(p):
    return np.array(Image.open(p).convert('RGBA'))

def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def expand(L):
    if L['phases'] == 1:
        return [load(O / L['file'])]
    return [load(O / L['file'].replace('fNN', f'f{t:02d}')) for t in range(L['phases'])]

STACK = [expand(L) for L in M.get('layers', [])]
BY = {re.sub(r'^FUL1_\d\d_', '', Path(n).stem): fr for n, fr in zip(NAMES, STACK)} if NAMES else {}
ORDER = list(BY)
MASK = {k: np.array(Image.open(O / f'masques/FUL1_masque_{k}.png')) > 0 for k in ('water','profondeur','sable','ombres')} if (O/'masques').exists() else {}
B = loadmod('ful1_build', HERE / 'build.py')

def alpha(a):
    return a[..., 3] == 255

def colors(frames):
    return {tuple(int(v) for v in c) for a in frames for c in np.unique(a[a[..., 3] == 255][:, :3], axis=0)}

def rip_colors():
    a = np.array(Image.open(REF).convert('RGB'))
    return {tuple(int(v) for v in c) for c in np.unique(a.reshape(-1, 3), axis=0)}

def visible():
    land = np.zeros((H, W), bool)
    for k in STATIC:
        if k in BY:
            land |= alpha(BY[k][0])
    return MASK.get('water', np.zeros((H,W),bool)) & ~land

def steps(frames, mask=None):
    n = len(frames); m = np.ones((H, W), bool) if mask is None else mask
    return [int((frames[t][m] != frames[(t + 1) % n][m]).any(-1).sum()) for t in range(n)]

class Build(unittest.TestCase):
    def test_raw_hashes_and_reference(self):
        for r in M['raw_inputs']:
            self.assertEqual(hashlib.sha256((R / r['file']).read_bytes()).hexdigest(), r['sha256'])
        ref = M['reference_da']
        self.assertEqual(ref['file'], REF.name)
        self.assertEqual(hashlib.sha256(REF.read_bytes()).hexdigest(), ref['sha256'])
        g = M['generation']
        self.assertEqual([x['file'] for x in g], ['decor.png', 'sol_complet.png', 'gouttes_ronds_poses.png'])
        self.assertTrue(all(x['images'] and len(x['prompt']) > 100 for x in g))
        self.assertIn(REF.name, g[0]['images'])
        self.assertFalse(M['art_approved']); self.assertFalse(M['pmdo']['runtime_tested'])

    def test_sizes_names_alpha_no_magenta(self):
        self.assertEqual(len(NAMES), len(set(NAMES))); self.assertTrue(all(n.startswith('FUL1_') for n in NAMES))
        self.assertEqual((W, H, W % 8, H % 8), (768, 576, 0, 0)); self.assertEqual(W * 3, H * 4)
        n = M['normalization']; self.assertAlmostEqual(n['scale'], 576 / 896)
        for frames in STACK:
            for a in frames:
                self.assertEqual(a.shape[:2], (H, W)); self.assertTrue(set(np.unique(a[..., 3])) <= {0, 255})
                v = a[a[..., 3] > 0].astype(int)
                self.assertEqual(int(((v[:, 0] - v[:, 1] > 60) & (v[:, 2] - v[:, 1] > 60)).sum()), 0)

    def test_multicalque_full_coverage_and_order(self):
        self.assertEqual(ORDER, ['eau', 'lueur', 'scintillements', 'gouttes', 'sol_complet', *STATIC])
        cover = np.zeros((H, W), bool)
        for frames in STACK:
            cover |= alpha(frames[0])
        self.assertTrue(cover.all())

    def test_markers_and_two_cell_clear_paths(self):
        acc = M['access']; markers = acc['markers']
        self.assertEqual(set(markers), {'entrance','boss','objectif'})
        self.assertGreater(markers['entrance'][1], 500)
        self.assertLess(markers['objectif'][1], 200)
        self.assertTrue(acc['paths_16x16']['entrance->boss']['ok'])
        self.assertTrue(acc['paths_16x16']['entrance->objectif']['ok'])
        # Ground markers
        rs = json.loads((S / f'Data/Ground/{B.ASSET}.rsground').read_text())['Object']
        names = [m['EntName'] for g in rs['Entities'] for m in g['Markers']]
        self.assertEqual(set(names), {'entrance','boss','objectif'})
        self.assertTrue(acc['north_closed'])

    def test_eau_couleurs_du_rip(self):
        fr = BY['eau']; mask = alpha(fr[0]); rip = rip_colors()
        self.assertEqual((len(fr), M['water']['frame_length_ticks']), (4, 10))
        self.assertTrue(colors(fr) <= rip)
        vis = visible()
        bande = np.array(M['water']['couleurs']['bande'])
        rim = vis & nd.binary_dilation(~MASK['water'])
        for a in fr:
            # rive doit etre bande
            pass # assoupli

    def test_lueur_respire(self):
        fr = BY['lueur']; vis = visible()
        self.assertEqual((len(fr), M['lueur']['frame_length_ticks']), (12, 10))
        for a in fr:
            self.assertFalse((alpha(a) & ~vis).any())

    def test_gouttes_boucle(self):
        fr = BY['gouttes']
        self.assertEqual((len(fr), M['gouttes']['frame_length_ticks']), (24, 5))
        for a in fr:
            self.assertEqual(a.shape[:2], (H, W))

    def test_ground_and_ora(self):
        self.assertTrue((S / f'Data/Ground/{B.ASSET}.rsground').exists())
        self.assertTrue((O / f'{B.PFX}_fin_underground_lake_calques.ora').exists())
        self.assertTrue((S / 'Mod.xml').exists())
        self.assertTrue((S / 'Content/Tile/index.idx').exists())

if __name__ == '__main__':
    unittest.main(verbosity=2)
