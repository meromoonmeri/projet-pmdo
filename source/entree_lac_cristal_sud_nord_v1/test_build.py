"""Tests dédiés — Entrée Lac Cristallin Zone Zéro sud -> nord V1 (ELC1, 4:3 vaste).
.venv/bin/python -m unittest source.entree_lac_cristal_sud_nord_v1.test_build -v
"""
from pathlib import Path
import hashlib, importlib.util, io, json, re, unittest, zipfile
import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/entree_lac_cristal_sud_nord_v1'
S = R / '.cache/entree_lac_cristal_sud_nord_v1/entree_lac_cristal_sud_nord'
M = json.loads((O / 'manifest.json').read_text())
W, H = M['size_px']
NAMES = [Path(L['file']).name.replace('_fNN', '') for L in M['layers']]
STATIC = ('dalles', 'reflets', 'rebords', 'cristaux', 'ilots', 'piliers', 'profondeur')


def load(p):
    return np.array(Image.open(p).convert('RGBA'))


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def expand(L):
    if L['phases'] == 1:
        return [load(O / L['file'])]
    return [load(O / L['file'].replace('fNN', f'f{t:02d}')) for t in range(L['phases'])]


STACK = [expand(L) for L in M['layers']]
BY = {re.sub(r'^ELC1_\d\d_', '', Path(n).stem): fr for n, fr in zip(NAMES, STACK)}
ORDER = list(BY)
MASK = {k: np.array(Image.open(O / f'masques/ELC1_masque_{k}.png')) > 0 for k in ('water', 'profondeur', 'dalles', 'reflets', 'piliers')}


def alpha(a):
    return a[..., 3] == 255


def colors(frames):
    return {tuple(int(v) for v in c) for a in frames for c in np.unique(a[a[..., 3] == 255][:, :3], axis=0)}


class Build(unittest.TestCase):
    def test_raw_hashes_and_reference(self):
        for r in M['raw_inputs']:
            self.assertEqual(hashlib.sha256((R / r['file']).read_bytes()).hexdigest(), r['sha256'])
        ref = M['reference_da']
        self.assertEqual(ref['file'], 'lakecrystalpmdsky.png')
        self.assertEqual(hashlib.sha256((R / ref['file']).read_bytes()).hexdigest(), ref['sha256'])
        self.assertFalse(M['art_approved']); self.assertFalse(M['pmdo']['runtime_tested'])

    def test_sizes_names_alpha_no_magenta(self):
        self.assertEqual(len(NAMES), len(set(NAMES))); self.assertTrue(all(n.startswith('ELC1_') for n in NAMES))
        self.assertEqual((W, H, W % 8, H % 8), (768, 576, 0, 0)); self.assertEqual(W * 3, H * 4)
        for frames in STACK:
            for a in frames:
                self.assertEqual(a.shape[:2], (H, W)); self.assertTrue(set(np.unique(a[..., 3])) <= {0, 255})
                v = a[a[..., 3] > 0].astype(int)
                self.assertEqual(int(((v[:, 0] > 190) & (v[:, 2] > 190) & (v[:, 1] < 100)).sum()), 0)

    def test_multicalque_full_coverage_and_order(self):
        self.assertEqual(ORDER, ['eau', 'reflet_profondeur', 'scintillements', 'gouttes', 'sol_complet', *STATIC, 'reflets_tera', 'eclats'])
        cover = np.zeros((H, W), bool)
        for frames in STACK:
            cover |= alpha(frames[0])
        self.assertTrue(cover.all())
        fixed = [alpha(BY[k][0]) for k in STATIC]
        self.assertEqual(int(np.sum(fixed, 0).max()), 1)

    def test_cristaux_zone_zero_white_and_tera_rainbow(self):
        # Les piliers et dalles ne sont plus cyan-bleu (g-r > 80), mais blancs nacrés / quartz-améthyste Zone Zéro (|r-g| <= 16)
        for k in ('piliers', 'ilots', 'dalles'):
            px = BY[k][0][alpha(BY[k][0])][:, :3].astype(float).mean(0)
            self.assertLess(abs(px[0] - px[1]), 16.0, (k, px))
            self.assertGreater(px[0], 160.0, (k, px))
        # Le calque reflets_tera contient les 8 teintes irisées de l'arc-en-ciel Téra sur 24 phases
        tf = BY['reflets_tera']
        self.assertEqual(len(tf), 24)
        self.assertGreater(len(colors(tf)), 12)
        self.assertTrue(all(int(alpha(a).sum()) > 1000 for a in tf))

    def test_water_depth_and_reflet_profondeur_sans_lisere(self):
        fr = BY['eau']; mask = alpha(fr[0])
        self.assertEqual((len(fr), M['water']['frame_length_ticks']), (4, 10))
        land = np.zeros((H, W), bool)
        for k in STATIC:
            land |= alpha(BY[k][0])
        rim = mask & ~land & nd.binary_dilation(land)
        bande = np.array(M['water']['couleurs']['bande'])
        for a in fr:
            self.assertTrue((a[rim][:, :3] == bande).all())
        rf = BY['reflet_profondeur']
        self.assertEqual((len(rf), M['reflet_profondeur']['frame_length_ticks']), (24, 10))
        self.assertTrue(all(int(alpha(a).sum()) > 8000 for a in rf))
        self.assertFalse((alpha(rf[0]) & ~mask).any())

    def test_ora_and_ground_roundtrip(self):
        with zipfile.ZipFile(O / 'ELC1_entree_lac_cristal_calques.ora') as z:
            merged = np.array(Image.open(io.BytesIO(z.read('mergedimage.png'))).convert('RGBA'))
        sc = Image.new('RGBA', (W, H))
        for frames in STACK:
            sc.alpha_composite(Image.fromarray(frames[0]))
        self.assertTrue((np.array(sc) == merged).all())
        self.assertTrue(M['access']['path_found_16x16'])
        doc = json.loads((S / f"Data/Ground/{M['pmdo']['asset']}.rsground").read_text()); o = doc['Object']
        nr = loadmod('native_reader', R / 'source/cote_v5_expeditions/audit_references.py')
        banks = {p.stem: nr.tiles(p)[1] for p in (S / 'Content/Tile').glob('*.tile')}
        for li, (frames, L) in enumerate(zip(STACK, M['layers'])):
            for t in sorted({0, len(frames) // 2, len(frames) - 1}):
                out = np.zeros((H, W, 4), 'uint8')
                for x, col in enumerate(o['Layers'][li]['Tiles']):
                    for y, cell in enumerate(col):
                        for track in cell['Layers']:
                            f = track['Frames'][t % len(track['Frames'])]
                            out[y*8:y*8+8, x*8:x*8+8] = np.array(nr.straight(banks[f['Sheet']][f['TexLoc']['X'], f['TexLoc']['Y']]))
                self.assertTrue((out == frames[t]).all(), (li, t))


if __name__ == '__main__':
    unittest.main()
