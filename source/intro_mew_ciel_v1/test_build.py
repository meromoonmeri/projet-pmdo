"""Tests dédiés — Ciel de Mew (IMW2), fond animé en boucle 4:3. .venv/bin/python -m unittest source.intro_mew_ciel_v1.test_build -v
Contrôles d'images, de boucle, de mouvement, de grille et d'aller-retour Ground : PAS un test du moteur PMDO. Lancer build.py avant."""
from pathlib import Path
import hashlib, importlib.util, json, re, unittest
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/intro_mew_ciel_v1'
S = R / '.cache/intro_mew_ciel_v1/ciel_de_mew'
M = json.loads((O / 'manifest.json').read_text())
W, H = M['size_px']
ANIM = ('soleil', 'nuages_loin', 'nuages_moyens', 'mew', 'mer', 'eclats')
PH = {k: M[k]['phases'] for k in ANIM}
TK = {k: M[k]['frame_length_ticks'] for k in ANIM}


def load(p): return np.array(Image.open(p).convert('RGBA'))


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def name_of(p): return re.sub(r'_fN+$', '', Path(p).stem.split('_', 2)[2])


def expand(p):
    mt = re.search(r'fN+', p)
    if mt:
        w = len(mt.group()) - 1
        return [load(O / p.replace(mt.group(), f'f{t:0{w}d}')) for t in range(PH[name_of(p)])]
    return [load(O / p)]


ORDER = M['layer_order_bottom_to_top']
NAMES = [name_of(p) for p in ORDER]
STACK = {n: expand(p) for n, p in zip(NAMES, ORDER)}
B = loadmod('imw2_build', HERE / 'build.py')


def alpha(a): return a[..., 3] == 255


def colors(a, m=None):
    m = alpha(a) if m is None else m
    return {tuple(int(v) for v in c) for c in np.unique(a[m][:, :3], axis=0)}


class Ciel(unittest.TestCase):
    def test_ordre_formats_alpha(self):
        self.assertEqual(NAMES, ['ciel', 'soleil', 'nuages_loin', 'nuages_moyens', 'mew', 'mer', 'eclats'])
        self.assertEqual((W, H), (768, 576)); self.assertEqual(M['grid_8px'], [96, 72])
        for n, fr in STACK.items():
            for a in fr:
                self.assertEqual(a.shape, (H, W, 4)); self.assertEqual(set(np.unique(a[..., 3])) - {0, 255}, set(), n)
                self.assertFalse(((a[..., 0] > 235) & (a[..., 1] < 40) & (a[..., 2] > 235) & alpha(a)).any(), n)   # pas de magenta
        self.assertTrue(alpha(STACK['ciel'][0]).all())
        for n in ('soleil', 'nuages_loin', 'nuages_moyens', 'mew', 'mer', 'eclats'):
            self.assertTrue((~alpha(STACK[n][0])).any(), n)
        self.assertLessEqual(len(colors(STACK['ciel'][0])), 40)
        self.assertEqual(M['scene_loop_ticks'], 2400)

    def test_cycles_divisent_la_boucle(self):
        for n in ANIM:
            self.assertEqual((len(STACK[n]), M[n]['frame_length_ticks']), (PH[n], B.ANIM[n][1]))
            self.assertEqual(2400 % (PH[n] * TK[n]), 0, n)
        self.assertEqual((PH['mew'], TK['mew'], PH['eclats'], TK['eclats']), (8, 6, 8, 6))

    def test_nuages_parallaxe_et_boucle_exacte(self):
        sp = {}
        for n in ('nuages_loin', 'nuages_moyens', 'mer'):
            fr = STACK[n]; s = M[n]['pas_px']; P = M[n]['periode_px']
            self.assertEqual(s * PH[n], P)                                                  # une période exactement par boucle
            self.assertEqual(M[n]['vitesse_px_s'], s * 6)
            sp[n] = s
            for t in (0, 57, 119, len(fr) - 1):
                a, b = fr[t], fr[(t + 1) % len(fr)]
                self.assertTrue((a[:, s:] == b[:, :W - s]).all(), (n, t))                    # chaque phase décale de s px vers la gauche, y compris le raccord de boucle
            self.assertTrue(len({f.tobytes() for f in fr}) > 200, n)
        self.assertEqual([sp['nuages_loin'], sp['nuages_moyens'], sp['mer']], [2, 4, 6])    # vitesses 12 / 24 / 36 px/s : plus c'est proche, plus ça va vite
        fr = STACK['nuages_loin'][0]; P = M['nuages_loin']['periode_px']
        self.assertTrue((fr[:, :W - P] == fr[:, P:]).all())                                  # le motif lointain se répète tous les 480 px (réserve documentée)

    def test_soleil(self):
        fr = STACK['soleil']; cx, cy, r = B.SUN[0] * 2, B.SUN[1] * 2, B.SUN[2] * 2
        self.assertEqual(len({f.tobytes() for f in fr}), 12)                                # 12 phases distinctes
        sky = B.sky_layer()
        a = B.IM.draw_sun(sky.copy(), B.SUN[0], B.SUN[1], B.SUN[2], 0.0, rot=2.0)
        b = B.IM.draw_sun(sky.copy(), B.SUN[0], B.SUN[1], B.SUN[2], 0.0, rot=0.0)
        self.assertTrue((a == b).all())                                                     # rotation de 2 rayons = figure identique : la boucle est exacte
        for f in fr:
            ys, xs = np.nonzero(alpha(f))
            self.assertLess(float(np.hypot(xs - cx, ys - cy).max()), r * 2.2 + 4)
            self.assertGreater(len(ys), 6000)
            self.assertTrue((f[cy - 6:cy + 6, cx - 6:cx + 6, :3] == (255, 248, 214)).all())   # cœur du disque

    def test_mew(self):
        fr = STACK['mew']; f8 = B.IM.mew_frames(8); nat = B.IM.mew_native()
        self.assertEqual(len({f.tobytes() for f in fr}), 8)
        cols = {tuple(int(v) for v in c) for c in np.unique(nat[nat[..., 3] > 0][:, :3], axis=0)}
        self.assertLessEqual(len(cols), 15); self.assertEqual(M['mew']['couleurs'], len(cols))
        for k, a in enumerate(fr):
            self.assertTrue(colors(a) <= cols, k)
            h, w = f8[k].shape[:2]
            x0, y0 = B.MEW_C[0] - w // 2, B.MEW_C[1] - h // 2 + B.bob(k)
            ref = np.zeros((288, 384, 4), np.uint8); sub = ref[y0:y0 + h, x0:x0 + w]; m = f8[k][..., 3] > 0; sub[m] = f8[k][m]
            self.assertTrue((a == np.repeat(np.repeat(ref, 2, 0), 2, 1)).all(), k)           # sprite natif en pixels x2, rien d'autre
        self.assertEqual([b // 2 for b in M['mew']['bosse_px']], [B.bob(k) for k in range(8)])
        self.assertEqual(min(B.bob(k) for k in range(8)), -3); self.assertEqual(max(B.bob(k) for k in range(8)), 3)
        ys, xs = np.nonzero(alpha(fr[0]))
        self.assertTrue(xs.min() > 150 and xs.max() < 400 and ys.min() > 200 and ys.max() < 400)

    def test_eclats(self):
        fr = STACK['eclats']; tones = {tuple(c) for c in M['eclats']['tons']}
        self.assertEqual(len({f.tobytes() for f in fr}), 8)
        for k, a in enumerate(fr):
            self.assertTrue(colors(a) <= tones); ys, xs = np.nonzero(alpha(a))
            self.assertGreater(len(xs), 20)
            self.assertLess(int(xs.max()), B.MEW_C[0] * 2 + 10)                              # derrière Mew (qui regarde à droite)
            self.assertTrue(ys.min() > 150 and ys.max() < 400)

    def test_scene_boucle_et_composition(self):
        named = [(n, STACK[n]) for n in NAMES]
        a0 = B.scene(named, 0); a_end = B.scene(named, 2400)
        self.assertTrue((np.array(a0) == np.array(a_end)).all())                            # tick 2400 = tick 0 : boucle exacte
        self.assertFalse((np.array(a0) == np.array(B.scene(named, 1200))).all())
        ref = Image.new('RGBA', (W, H))
        for n in NAMES: ref.alpha_composite(Image.fromarray(STACK[n][0]))
        self.assertTrue((np.array(ref) == np.array(Image.open(O / 'review/IMW2_scene_t000.png').convert('RGBA'))).all())
        wb = Image.open(O / 'review/IMW2_scene_animee.webp'); self.assertEqual((wb.size, wb.n_frames), ((768, 576), 240))
        wb.seek(120); got = np.array(wb.convert('RGB')).astype(int); want = np.array(B.scene(named, 1200).convert('RGB')).astype(int)
        self.assertLess(float(np.abs(got - want).mean()), 6.0)

    def test_manifeste_honnete(self):
        self.assertFalse(M['art_approved']); self.assertFalse(M['pmdo']['runtime_tested'])
        raw = M['raw_inputs'][0]
        self.assertEqual(hashlib.sha256((R / raw['file']).read_bytes()).hexdigest(), raw['sha256'])
        self.assertEqual(M['access']['blocked_cells'], M['access']['total_cells'])           # rien de praticable
        self.assertIn('IMW1', M['choix_agent']['portee']); self.assertIn('repetition', M['choix_agent'])
        self.assertNotIn('references_da', M)                                                 # aucune référence ROM

    def test_ground_aller_retour(self):
        doc = json.loads((S / f"Data/Ground/{M['pmdo']['asset']}.rsground").read_text()); o = doc['Object']
        self.assertEqual(doc['Version'], '0.8.12.0'); self.assertEqual(len(o['Layers']), len(NAMES) + 1)
        nr = loadmod('native_reader', R / 'source/cote_v5_expeditions/audit_references.py')
        banks = {p.stem: nr.tiles(p)[1] for p in (S / 'Content/Tile').glob('*.tile')}
        self.assertEqual(set(banks), set(M['pmdo']['banks']))
        for li, n in enumerate(NAMES):
            frames = STACK[n]; ticks = TK.get(n, 60)
            for t in sorted({0, len(frames) // 2, len(frames) - 1}):
                out = np.zeros((H, W, 4), 'uint8')
                for x, col in enumerate(o['Layers'][li]['Tiles']):
                    for y, cell in enumerate(col):
                        for track in cell['Layers']:
                            if len(track['Frames']) > 1:
                                self.assertEqual((len(track['Frames']), track['FrameLength']), (len(frames), ticks))
                            f = track['Frames'][t % len(track['Frames'])]
                            out[y*8:y*8+8, x*8:x*8+8] = np.array(nr.straight(banks[f['Sheet']][f['TexLoc']['X'], f['TexLoc']['Y']]))
                self.assertTrue((out == frames[t]).all(), (n, t))
        self.assertEqual(sum(w['Tags'] for c in o['obstacles'] for w in c), M['access']['blocked_cells'])
        self.assertEqual([m['EntName'] for m in o['Entities'][0]['Markers']], ['entrance', 'mew', 'soleil'])
        tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
        self.assertEqual(set(tools.read_index(S / 'Content/Tile/index.idx')), set(M['pmdo']['banks']))
        self.assertNotIn('warp', (S / f"Data/Script/{M['pmdo']['namespace']}/ground/{M['pmdo']['asset']}/init.lua").read_text().replace('aucun warp', ''))
        mod = (S / 'Mod.xml').read_text(); self.assertIn('Ciel de Mew', mod); self.assertIn(M['pmdo']['namespace'], mod); self.assertNotIn('Vapeur', mod)


if __name__ == '__main__':
    unittest.main()
