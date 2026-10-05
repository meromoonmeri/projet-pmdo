"""Tests dédiés — Fin Lac Cristallin Zone Zéro V1 (FLC1, 4:3 vaste).
.venv/bin/python -m unittest source.fin_lac_cristal_v1.test_build -v
"""
from pathlib import Path
import hashlib, importlib.util, io, json, re, unittest, zipfile
import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/fin_lac_cristal_v1'
S = R / '.cache/fin_lac_cristal_v1/fin_lac_cristal'
M = json.loads((O / 'manifest.json').read_text())
W, H = M['size_px']
NAMES = [Path(L['file']).name.replace('_fNN', '') for L in M['layers']]
STATIC = ('dalles', 'reflets', 'rebords', 'cristaux', 'ilots', 'piliers', 'sanctuaire')


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
BY = {re.sub(r'^FLC1_\d\d_', '', Path(n).stem): fr for n, fr in zip(NAMES, STACK)}
ORDER = list(BY)


def alpha(a):
    return a[..., 3] == 255


def colors(frames):
    return {tuple(int(v) for v in c) for a in frames for c in np.unique(a[a[..., 3] == 255][:, :3], axis=0)}


class Build(unittest.TestCase):
    def test_multicalque_full_coverage_and_order(self):
        self.assertEqual(
            ORDER,
            ['eau', 'reflet_profondeur', 'scintillements', 'gouttes', 'sol_complet', *STATIC, 'reflets_tera', 'runes_pulse', 'eclats']
        )
        self.assertNotIn('profondeur', ORDER)
        cover = np.zeros((H, W), bool)
        for frames in STACK:
            cover |= alpha(frames[0])
        self.assertTrue(cover.all())

    def test_cristaux_zone_zero_and_runes_pulse(self):
        for k in ('piliers', 'ilots', 'sanctuaire', 'dalles'):
            px = BY[k][0][alpha(BY[k][0])][:, :3].astype(float).mean(0)
            self.assertLess(abs(px[0] - px[1]), 16.0, (k, px))
            self.assertGreater(px[0], 160.0, (k, px))
        # Vérifier la pulsation lumineuse subtile des signes de la rune du monolithe
        rp = BY['runes_pulse']
        self.assertEqual((len(rp), M['runes_pulse']['frame_length_ticks']), (24, 10))
        sanc_mask = alpha(BY['sanctuaire'][0])
        for a in rp:
            self.assertGreater(int(alpha(a).sum()), 800)
            self.assertFalse((alpha(a) & ~sanc_mask).any())
        # La luminance moyenne de la rune monte entre t=0 (repos) et t=12 (zénith)
        lum0 = rp[0][alpha(rp[0])][:, :3].astype(float).mean()
        lum12 = rp[12][alpha(rp[12])][:, :3].astype(float).mean()
        self.assertGreater(lum12, lum0 + 20.0, (lum0, lum12))

    def test_water_depth_and_reflet_profondeur(self):
        fr = BY['eau']; mask = alpha(fr[0])
        land = np.zeros((H, W), bool)
        for k in STATIC:
            land |= alpha(BY[k][0])
        rim = mask & ~land & nd.binary_dilation(land)
        bande = np.array(M['water']['couleurs']['bande'])
        for a in fr:
            self.assertTrue((a[rim][:, :3] == bande).all())
        rf = BY['reflet_profondeur']
        self.assertEqual(len(rf), 24)
        self.assertTrue(all(int(alpha(a).sum()) > 8000 for a in rf))

    def test_ora_and_ground_roundtrip(self):
        with zipfile.ZipFile(O / 'FLC1_fin_lac_cristal_calques.ora') as z:
            merged = np.array(Image.open(io.BytesIO(z.read('mergedimage.png'))).convert('RGBA'))
        sc = Image.new('RGBA', (W, H))
        for frames in STACK:
            sc.alpha_composite(Image.fromarray(frames[0]))
        self.assertTrue((np.array(sc) == merged).all())
        self.assertTrue(M['access']['path_found_16x16'])
        doc = json.loads((S / f"Data/Ground/{M['pmdo']['asset']}.rsground").read_text()); o = doc['Object']
        self.assertEqual({m['EntName'] for m in o['Entities'][0]['Markers']}, {'entrance', 'boss', 'objectif'})
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
