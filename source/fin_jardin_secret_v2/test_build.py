"""Tests dédiés — Fin Jardin secret V2, sanctuaire de Celebi (FJS4, 4:3 vaste).
.venv/bin/python -m unittest source.fin_jardin_secret_v2.test_build -v
Contrôles d'images, de formats, de palettes, de fidélité au rip, de cadence et de grille : PAS un test du moteur PMDO.
"""
from pathlib import Path
import hashlib, importlib.util, io, json, re, unittest, zipfile
import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/fin_jardin_secret_v2'
S = R / '.cache/fin_jardin_secret_v2/fin_jardin_secret'
M = json.loads((O / 'manifest.json').read_text())
W, H = M['size_px']
NAMES = [Path(L['file']).name.replace('_fNN', '') for L in M['layers']]
STATIC = ('prairie', 'herbe', 'ombres', 'fleurs', 'rochers', 'arbres', 'haies', 'souche', 'sanctuaire', 'marches', 'fond')
REF = R / 'secretgarden.png'


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
BY = {re.sub(r'^FJS4_\d\d_', '', Path(n).stem): fr for n, fr in zip(NAMES, STACK)}
ORDER = list(BY)
MASK = {k: np.array(Image.open(O / f'masques/FJS4_masque_{k}.png')) > 0 for k in (*STATIC, 'rayon', 'embleme', 'praticable')}
B = loadmod('fjs4_build', HERE / 'build.py')


def alpha(a):
    return a[..., 3] == 255


def colors(frames):
    return {tuple(int(v) for v in c) for a in frames for c in np.unique(a[a[..., 3] > 0][:, :3], axis=0)}


def rip_colors():
    a = np.array(Image.open(REF).convert('RGB'))
    return {tuple(int(v) for v in c) for c in np.unique(a.reshape(-1, 3), axis=0)}


def lum(px):
    return px[..., :3].astype(float) @ [.299, .587, .114]


def base_idx(name='rayon'):
    return np.array(Image.open(O / f'masques/FJS4_{name}_crans.png')).astype(int) // 11


def decor():
    a1, g = B.rgb(B.RAW1 / 'decor.png'), B.rgb(HERE / 'bruts/decor_sanctuaire.png')
    return (a1, g, *B.composite(a1, g))


class Build(unittest.TestCase):
    def test_raw_hashes_and_reference(self):
        for r in M['raw_inputs']:
            self.assertEqual(hashlib.sha256((R / r['file']).read_bytes()).hexdigest(), r['sha256'])
        ref = M['reference_da']
        self.assertEqual(ref['file'], REF.name)
        self.assertEqual(hashlib.sha256(REF.read_bytes()).hexdigest(), ref['sha256'])
        g = {x['file']: x for x in M['generation']}
        self.assertEqual(g['decor.png']['images'], [REF.name])
        self.assertEqual(g['temoin_sans_objets.png']['images'], [f'{B.LOT1}/bruts/decor.png'])
        self.assertEqual(g['sol_complet.png']['images'], [f'{B.LOT1}/bruts/temoin_sans_objets.png'])
        self.assertEqual(g['decor_sanctuaire.png']['images'], [f'{B.LOT1}/bruts/decor.png', REF.name])
        self.assertEqual(g['decor_sanctuaire.png']['lot'], B.LOT)
        self.assertTrue(all(len(x['prompt']) > 100 for x in g.values()))
        ec = [x for x in M['generation'] if x.get('ecarte')]
        self.assertEqual(len(ec), 3); self.assertTrue(all('ECARTE' in x['essais'] for x in ec))
        self.assertIn('choisis par l agent', M['biome'])
        self.assertFalse(M['art_approved']); self.assertFalse(M['pmdo']['runtime_tested'])
        for k in ('temoin', 'brut_sanctuaire'):
            rg = M['recalage'][k]; self.assertLess(rg['ecart_moyen'], rg['ecart_decale_1px'], k)

    def test_sizes_names_alpha_no_magenta(self):
        self.assertEqual(len(NAMES), len(set(NAMES))); self.assertTrue(all(n.startswith('FJS4_') for n in NAMES))
        self.assertEqual((W, H, W % 8, H % 8), (768, 576, 0, 0)); self.assertEqual(W * 3, H * 4)
        n = M['normalization']; self.assertAlmostEqual(n['scale'], 576 / 896)
        self.assertEqual(n['scaled'][0] - sum(n['crop_x']), W)
        for name, frames in BY.items():
            for a in frames:
                self.assertEqual(a.shape[:2], (H, W))
                self.assertTrue(set(np.unique(a[..., 3])) <= {0, 255}, name)
                v = a[a[..., 3] > 0].astype(int)
                bad = (v[:, 0] - v[:, 1] > 60) & (v[:, 2] - v[:, 1] > 60)
                self.assertEqual(int(bad.sum()), 0, name)

    def test_multicalque_full_coverage_and_order(self):
        self.assertEqual(ORDER, ['sol_complet', *STATIC, 'embleme', 'rayon', 'lucioles'])
        self.assertTrue(alpha(BY['sol_complet'][0]).all())
        fixed = [alpha(BY[k][0]) for k in STATIC] + [MASK['rayon'], MASK['embleme']]
        self.assertTrue((np.sum(fixed, 0) == 1).all())
        for k in STATIC:
            self.assertGreater(int(alpha(BY[k][0]).sum()), 200, k)
            self.assertTrue((alpha(BY[k][0]) == MASK[k]).all(), k)
        for k in ('rayon', 'embleme'):
            for a in BY[k]:
                self.assertTrue((alpha(a) == MASK[k]).all(), k)
        sol = BY['sol_complet'][0][..., :3].astype(float).reshape(-1, 3)
        self.assertGreater(len(colors(BY['sol_complet'])), 8)
        m = sol.mean(0); self.assertGreater(m[1], m[0] + 30); self.assertGreater(m[1], m[2] + 80)

    def test_palettes_et_matieres(self):
        for g, v in M['normalization']['palettes'].items():
            self.assertLessEqual(len(colors([BY[k][0] for k in v['calques']])), v['couleurs'], g)
        L = lambda k: BY[k][0][alpha(BY[k][0])][:, :3].astype(int)
        self.assertNotIn('profondeur', BY); self.assertNotIn('seuil', BY)
        s = L('souche').mean(0); self.assertGreater(s[0], s[2] + 60)
        f = L('fond').mean(0); self.assertLess(float(lum(f)), 85); self.assertGreater(f[1], f[0] + 15)
        for k in ('prairie', 'herbe', 'ombres'):
            p = L(k).mean(0); self.assertGreater(p[1], p[0] + 30, k)
        self.assertGreater(float(lum(L('prairie')).mean()), float(lum(L('ombres')).mean()) + 25)
        self.assertLess(float(L('prairie')[:, 2].mean()), float(L('herbe')[:, 2].mean()) - 15)
        r = L('rochers').mean(0); self.assertLess(abs(r[0] - r[1]), 30); self.assertGreater(r[0], r[2] + 25)
        sg = M['segmentation_mesures']
        self.assertGreaterEqual(sg['fleurs'], 100); self.assertGreaterEqual(sg['rochers'], 15); self.assertGreaterEqual(sg['arbres'], 10)
        lab, n = nd.label(MASK['rochers']); self.assertGreaterEqual(n, 15)
        self.assertTrue((nd.binary_dilation(MASK['sanctuaire'], iterations=2) & MASK['marches']).any())
        ym, _ = np.nonzero(MASK['marches']); ys_s, _ = np.nonzero(MASK['sanctuaire'])
        self.assertGreater(ym.mean(), ys_s.mean())
        grass = MASK['prairie'] | MASK['herbe'] | MASK['ombres'] | MASK['fleurs']
        self.assertTrue((nd.binary_dilation(MASK['marches'], iterations=2) & grass).any())
        self.assertTrue(MASK['praticable'][MASK['marches']].all())
        ys, _ = np.nonzero(MASK['rayon']); self.assertEqual(int(ys.min()), 0); self.assertLess(float(ys.max()), ym.min())
        self.assertFalse((MASK['rayon'] & (MASK['souche'] | MASK['sanctuaire'] | MASK['embleme'])).any())

    def test_fidelite_rip(self):
        dec, ref = decor()[2], B.rgb(REF)
        fid = B.fidelity(dec, ref)
        self.assertEqual(set(fid), {'fond', 'herbe_claire', 'herbe', 'roche'})
        for k, v in fid.items():
            self.assertLess(v['distance'], 35, (k, v))
            self.assertAlmostEqual(v['distance'], M['fidelite_rip']['brut'][k]['distance'], places=1)
        for nm, v in M['fidelite_rip']['calques_finaux'].items():
            lay = BY[nm][0]; px = lay[alpha(lay)][:, :3].astype(float)
            sel = B.materials(px.reshape(-1, 1, 3))[v['matiere']][:, 0]
            self.assertGreater(int(sel.sum()), 50, nm)
            d = float(np.linalg.norm(px[sel].mean(0) - np.array(fid[v['matiere']]['rip_rgb'])))
            self.assertLess(d, 35, (nm, d)); self.assertAlmostEqual(d, v['distance_rip'], places=1)
        herbe = np.array(fid['herbe']['rip_rgb'])
        f = B.rgb(B.RAW1 / 'sol_complet.png').reshape(-1, 3).mean(0)
        d = float(np.linalg.norm(f - herbe)); self.assertLess(d, 35); self.assertAlmostEqual(d, M['fidelite_rip']['sol_complet'], places=1)
        for fn, dist in M['fidelite_rip']['sol_complet_ecartes'].items():
            self.assertGreater(dist, 35, fn)
            self.assertAlmostEqual(float(np.linalg.norm(B.rgb(B.RAW1 / fn).reshape(-1, 3).mean(0) - herbe)), dist, places=1)

    def test_rayon_rampe_exacte_boucle_fermee(self):
        rp = [tuple(c) for c in M['rayon']['rampe']]
        self.assertEqual(rp, [tuple(c) for c in B.RAMP]); self.assertEqual(len(rp), 22)
        self.assertTrue(set(rp) <= rip_colors())
        self.assertEqual(sorted(rp, key=lambda c: lum(np.array(c, float))), rp)
        fr = BY['rayon']; self.assertEqual((len(fr), M['layers'][-2]['ticks']), (24, 5))
        self.assertTrue(colors(fr) <= set(rp))
        bi = base_idx(); m = MASK['rayon']
        want = B.beam_frames(bi, m)
        for t in range(24):
            self.assertTrue((fr[t] == want[t]).all(), t)
        self.assertTrue((B.beam_frames(bi, m, ts=[24])[0] == fr[0]).all())
        self.assertTrue((fr[0][m][:, :3] == np.array(rp, 'uint8')[bi[m]]).all())
        idx = [B.ramp_index(f[m]).astype(int) - bi[m] for f in fr]
        self.assertEqual(max(int(np.abs(d).max()) for d in idx), M['rayon']['souffle_crans'])
        self.assertGreater(float((idx[6] > 0).mean()), 0.5); self.assertGreater(float((idx[18] < 0).mean()), 0.5)
        dark = m & (bi == 0)
        self.assertTrue(all((f[dark][:, :3] == np.array(rp[0], 'uint8')).all() for f in fr))

    def test_lucioles_couleurs_exactes_boucle_fermee(self):
        L = M['lucioles']; fr = BY['lucioles']; motes = [tuple(m) for m in L['lucioles']]
        self.assertEqual(motes, [tuple(m) for m in B.MOTES]); self.assertEqual(len(motes), 10)
        cs = {tuple(c) for c in L['couleurs']}
        self.assertTrue(cs <= set(tuple(c) for c in M['rayon']['rampe']) and cs <= rip_colors())
        self.assertTrue(colors(fr) <= cs)
        want = B.mote_frames(motes)
        for t in range(24):
            self.assertTrue((fr[t] == want[t]).all(), t)
        self.assertTrue((B.mote_frames(motes, ts=[24])[0] == fr[0]).all())
        solid = MASK['souche'] | MASK['marches'] | MASK['sanctuaire'] | MASK['embleme']
        for t in range(24):
            n = nd.label(alpha(fr[t]))[1]
            self.assertEqual(n, 10, t)
            self.assertFalse((alpha(fr[t]) & solid).any(), t)
            for m in motes:
                x, y, _ = B.mote_state(m, t); self.assertTrue(1 <= y < H - 1 and 1 <= x < W - 1)
        u = [B.mote_state(motes[0], t) for t in range(24)]
        self.assertTrue({s for *_, s in u} == {'point', 'croix'})
        self.assertTrue(all(u[i][1] == u[i - 1][1] - 2 for i in range(1, 24)))

    def test_sanctuaire_colle_sur_la_souche(self):
        a1, g, a, paste = decor()
        self.assertTrue((a[~paste] == a1[~paste]).all())
        self.assertTrue((a[paste] == g[paste]).all())
        saved = np.array(Image.open(O / 'masques/FJS4_zone_collee_pleine_resolution.png')) > 0
        self.assertTrue((saved == paste).all())
        y0, y1, x0, x1 = M['sanctuaire']['fenetre_pleine_resolution']; ys, xs = np.nonzero(paste)
        self.assertTrue(ys.min() >= y0 and ys.max() < y1 and xs.min() >= x0 and xs.max() < x1)
        self.assertEqual(int(paste.sum()), M['segmentation_mesures']['sanctuaire']['colle_px'])
        Sa, E, Mr, So = (MASK[k] for k in ('sanctuaire', 'embleme', 'marches', 'souche'))
        ty, tx = np.nonzero(Sa | E); ey, ex = np.nonzero(E); sy, sx = np.nonzero(So | Mr)
        foot = Sa & (np.arange(H)[:, None] >= ty.max() - 3)
        self.assertTrue((nd.binary_dilation(foot, iterations=2) & (So | Mr)).any())
        self.assertTrue(tx.min() >= sx.min() - 4 and tx.max() <= sx.max() + 4)
        self.assertLess(ty.mean(), sy.mean())
        self.assertLess(ty.max() - ty.min(), 80); self.assertLess(tx.max() - tx.min(), 70)
        self.assertLess(ey.min(), ty.max() - 10); self.assertLess(abs(ex.mean() - tx.mean()), 6)
        self.assertGreaterEqual(int(E.sum()), 100)
        self.assertTrue((nd.binary_dilation(E, iterations=1) & ~E & ~Sa).sum() == 0)

    def test_embleme_rampe_exacte_boucle_fermee(self):
        fr = BY['embleme']; rp = [tuple(c) for c in B.RAMP]; E = MASK['embleme']; bi = base_idx('embleme')
        self.assertEqual(len(fr), 24); self.assertTrue(colors(fr) <= set(rp) <= rip_colors())
        want = B.emblem_frames(bi, E)
        for t in range(24):
            self.assertTrue((fr[t] == want[t]).all(), t)
        self.assertTrue((B.emblem_frames(bi, E, ts=[24])[0] == fr[0]).all())
        self.assertTrue((fr[0][E][:, :3] == np.array(rp, 'uint8')[bi[E]]).all())
        steps = [int((B.ramp_index(f[E]).astype(int) - bi[E]).max()) for f in fr]
        self.assertEqual(max(steps), M['sanctuaire']['embleme']['crans_max']); self.assertEqual(steps[12], 3)
        self.assertEqual(steps, steps[:1] + steps[1:][::-1])
        self.assertTrue(all(b <= a for a, b in zip(steps[12:], steps[13:])))
        self.assertGreater(float(lum(fr[12][E]).mean()), float(lum(fr[0][E]).mean()) + 10)

    def test_ora_and_scene(self):
        with zipfile.ZipFile(O / 'FJS4_fin_jardin_secret_calques.ora') as z:
            merged = np.array(Image.open(io.BytesIO(z.read('mergedimage.png'))).convert('RGBA'))
            self.assertIn(b'Jardin secret', z.read('stack.xml'))
        sc = Image.new('RGBA', (W, H))
        for frames in STACK:
            sc.alpha_composite(Image.fromarray(frames[0]))
        self.assertTrue((np.array(sc) == merged).all())
        self.assertTrue((np.array(sc) == load(O / 'review/FJS4_scene_t000.png')).all())
        for L in M['layers']:
            self.assertEqual(M['scene_loop_ticks'] % (L['phases'] * L['ticks']) if L['phases'] > 1 else 0, 0)

    def test_access(self):
        a = M['access']; self.assertTrue(a['path_found_16x16'] and a['path_to_boss'] and a['path_to_objective'])
        ex, ey = a['entry_px']; bx, by = a['boss_px']; ox, oy = a['objective_px']
        w = MASK['praticable']
        self.assertGreater(ey, H - 64); self.assertLess(oy, H // 3)
        self.assertTrue(w[ey:ey + 16, ex:ex + 16].mean() > 0.9)
        self.assertTrue(w[by:by + 16, bx:bx + 16].mean() > 0.9)
        self.assertTrue(w[oy:oy + 16, ox:ox + 16].mean() > 0.8)
        dn = nd.distance_transform_edt(w)
        self.assertGreater(float(dn[by + 8, bx + 8]), 30)
        self.assertLess(abs(ox + 8 - W // 2), 48)
        self.assertLess(oy, by - 40)
        self.assertEqual(a['walkable_cells'] + a['blocked_cells'], (W // 8) * (H // 8))
        self.assertGreater(a['walkable_cells'], 2000)
        doc = json.loads((S / f"Data/Ground/{M['pmdo']['asset']}.rsground").read_text())
        blocked = np.array([[c['Tags'] for c in col] for col in doc['Object']['obstacles']]).T.astype(bool)
        for k in ('rochers', 'arbres', 'haies', 'souche', 'sanctuaire', 'fond'):
            cells = MASK[k].reshape(H // 8, 8, W // 8, 8).mean((1, 3)) > 0.5
            self.assertTrue(blocked[cells].all(), k)
        for px in (a['entry_px'], a['boss_px'], a['objective_px']):
            self.assertFalse(blocked[px[1] // 8:px[1] // 8 + 2, px[0] // 8:px[0] // 8 + 2].any(), px)
        self.assertTrue(blocked[:4].all()); self.assertTrue(blocked[:, :4].all() and blocked[:, -4:].all())

    def test_prefix_and_namespace_unique(self):
        for p in (R / 'source').glob('*/build.py'):
            if p.parent != HERE:
                s = p.read_text(errors='ignore')
                self.assertNotIn("PFX = 'FJS4'", s, p); self.assertNotIn("'fin_jardin_secret'", s, p)

    def test_ground_roundtrip(self):
        doc = json.loads((S / f"Data/Ground/{M['pmdo']['asset']}.rsground").read_text()); o = doc['Object']
        self.assertEqual(doc['Version'], '0.8.12.0'); self.assertEqual(len(o['Layers']), len(STACK) + 1)
        self.assertEqual(o['Layers'][-1]['Layer'], 4)
        nr = loadmod('native_reader', R / 'source/cote_v5_expeditions/audit_references.py')
        banks = {p.stem: nr.tiles(p)[1] for p in (S / 'Content/Tile').glob('*.tile')}
        self.assertEqual(set(banks), set(M['pmdo']['banks']))
        for li, (frames, L) in enumerate(zip(STACK, M['layers'])):
            for t in sorted({0, len(frames) // 2, len(frames) - 1}):
                out = np.zeros((H, W, 4), 'uint8')
                for x, col in enumerate(o['Layers'][li]['Tiles']):
                    for y, cell in enumerate(col):
                        for track in cell['Layers']:
                            if len(track['Frames']) > 1:
                                self.assertEqual((len(track['Frames']), track['FrameLength']), (len(frames), L['ticks']))
                            f = track['Frames'][t % len(track['Frames'])]
                            out[y*8:y*8+8, x*8:x*8+8] = np.array(nr.straight(banks[f['Sheet']][f['TexLoc']['X'], f['TexLoc']['Y']]))
                self.assertTrue((out == frames[t]).all(), (li, t))
        self.assertEqual(sum(w['Tags'] for c in o['obstacles'] for w in c), M['access']['blocked_cells'])
        self.assertEqual({m['EntName'] for m in o['Entities'][0]['Markers']}, {'entrance', 'boss', 'objectif'})
        self.assertEqual(len(o['Entities'][0]['Markers']), 3)
        tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
        self.assertEqual(set(tools.read_index(S / 'Content/Tile/index.idx')), set(M['pmdo']['banks']))


if __name__ == '__main__':
    unittest.main()
