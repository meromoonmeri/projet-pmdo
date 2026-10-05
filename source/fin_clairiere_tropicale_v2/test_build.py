"""Tests dédiés — Fin Clairière tropicale V2 (FCT2, 4:3 vaste).
.venv/bin/python -m unittest source.fin_clairiere_tropicale_v2.test_build -v
Contrôles d'images, de formats, de palettes, de fidélité au rip, de cadence et de grille : PAS un test du moteur PMDO.
"""
from pathlib import Path
import hashlib, importlib.util, io, json, re, unittest, zipfile
import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/fin_clairiere_tropicale_v2'
S = R / '.cache/fin_clairiere_tropicale_v2/fin_clairiere_tropicale'
M = json.loads((O / 'manifest.json').read_text())
W, H = M['size_px']
NAMES = [Path(L['file']).name.replace('_fNN', '') for L in M['layers']]
STATIC = ('herbe', 'ombres', 'dalles', 'touffes', 'fleurs', 'jungle', 'palmiers', 'tertre', 'autel', 'rive')
REF = R / 'large.S01P03A.png.84e22fb77c4061e77b0f546545fed2c7.png'


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
BY = {re.sub(r'^FCT2_\d\d_', '', Path(n).stem): fr for n, fr in zip(NAMES, STACK)}
ORDER = list(BY)
MASK = {k: np.array(Image.open(O / f'masques/FCT2_masque_{k}.png')) > 0 for k in (*STATIC, 'mer', 'praticable')}
B = loadmod('fct2_build', HERE / 'build.py')
ETC1 = loadmod('etc1_build', R / 'source/entree_clairiere_tropicale_sud_nord_v1/build.py')


def alpha(a):
    return a[..., 3] == 255


def colors(frames):
    return {tuple(int(v) for v in c) for a in frames for c in np.unique(a[a[..., 3] > 0][:, :3], axis=0)}


def rip_colors():
    a = np.array(Image.open(REF).convert('RGB'))
    return {tuple(int(v) for v in c) for c in np.unique(a.reshape(-1, 3), axis=0)}


def lum(px):
    return px[..., :3].astype(float) @ [.299, .587, .114]


def poses():
    return {k: load(O / f'poses/FCT2_{k}.png') for k in M['papillons']['poses']}


class Build(unittest.TestCase):
    def test_raw_hashes_reference_and_discarded(self):
        for r in M['raw_inputs']:
            self.assertEqual(hashlib.sha256((R / r['file']).read_bytes()).hexdigest(), r['sha256'])
        ref = M['reference_da']
        self.assertEqual(ref['file'], REF.name)
        self.assertEqual(hashlib.sha256(REF.read_bytes()).hexdigest(), ref['sha256'])
        g = M['generation']
        self.assertEqual([x['file'] for x in g], [
            'ecartes/decor_magenta_essai1_jungle_sombre.png', 'decor_magenta.png',
            'sol_complet.png', 'temoin_sans_objets.png', 'papillons_poses.png'])
        self.assertTrue(all(x['images'] and len(x['prompt']) > 100 for x in g))
        for i in (0, 1, 2, 4):
            self.assertIn(REF.name, g[i]['images'])
        for i in (2, 3):
            self.assertTrue(g[i]['images'][0].endswith('bruts/decor_magenta.png'))
        self.assertTrue(g[1]['images'][0].endswith('ecartes/decor_magenta_essai1_jungle_sombre.png'))
        self.assertIn('flat pure magenta', g[1]['prompt'])
        # Planche de papillons identique à celle d'ETC1
        self.assertEqual(
            hashlib.sha256((HERE / 'bruts/papillons_poses.png').read_bytes()).hexdigest(),
            hashlib.sha256((R / 'source/entree_clairiere_tropicale_sud_nord_v1/bruts/papillons_poses.png').read_bytes()).hexdigest())
        self.assertTrue(g[0]['ecarte'])
        self.assertGreater(M['fidelite_rip']['brut_ecarte']['jungle']['distance'], 35)
        self.assertEqual([r['ecarte'] for r in M['raw_inputs']], [True, False, False, False, False])
        self.assertNotIn("rgb(RAW / 'ecartes", Path(HERE / 'build.py').read_text().split('def build')[1].split('ecarte = ')[0])
        self.assertIn('choisis par l agent', M['biome'])
        self.assertFalse(M['art_approved']); self.assertFalse(M['pmdo']['runtime_tested'])

    def test_recalages(self):
        a, f, t = (B.rgb(HERE / f'bruts/{n}.png') for n in ('decor_magenta', 'sol_complet', 'temoin_sans_objets'))
        m, _ = B.classify(a, t)
        clair = nd.binary_erosion(m['herbe'], iterations=6)
        rs = B.recalage(a, f, clair)
        rt = B.recalage(a, t, clair)
        self.assertEqual(rs, {k: M['recalage']['sol_complet'][k] for k in rs})
        self.assertEqual(rt, {k: M['recalage']['temoin'][k] for k in rt})
        self.assertLess(rs['ecart_moyen'], 8)
        self.assertLess(rt['ecart_moyen'], 8)
        sol = BY['sol_complet'][0][alpha(BY['sol_complet'][0])][:, :3].astype(float)
        self.assertGreater(sol.mean(0)[1], sol.mean(0)[2] + 90)
        self.assertGreater(len(colors(BY['sol_complet'])), 12)

    def test_sizes_names_alpha_no_magenta(self):
        self.assertEqual(len(NAMES), len(set(NAMES))); self.assertTrue(all(n.startswith('FCT2_') for n in NAMES))
        self.assertEqual((W, H, W % 8, H % 8), (768, 576, 0, 0)); self.assertEqual(W * 3, H * 4)
        n = M['normalization']; self.assertAlmostEqual(n['scale'], 576 / 896)
        self.assertEqual(n['scaled'][0] - sum(n['crop_x']), W)
        for name, frames in BY.items():
            for a in frames:
                self.assertEqual(a.shape[:2], (H, W))
                self.assertTrue(set(np.unique(a[..., 3])) <= {0, 255}, name)
                v = a[a[..., 3] > 0].astype(int)
                bad = (v[:, 0] - v[:, 1] > 60) & (v[:, 2] - v[:, 1] > 60)
                if name == 'fleurs':
                    self.assertLess(int(bad.sum()), 60, name)
                else:
                    self.assertEqual(int(bad.sum()), 0, name)

    def test_multicalque_full_coverage_and_order(self):
        self.assertEqual(ORDER, ['sol_complet', *STATIC, 'mer', 'papillons'])
        self.assertTrue(alpha(BY['sol_complet'][0]).all())
        fixed = [alpha(BY[k][0]) for k in STATIC] + [alpha(BY['mer'][0])]
        self.assertTrue((np.sum(fixed, 0) == 1).all())
        for k in STATIC:
            self.assertGreater(int(alpha(BY[k][0]).sum()), 500, k)
            self.assertTrue((alpha(BY[k][0]) == MASK[k]).all(), k)
        for a in BY['mer']:
            self.assertTrue((alpha(a) == MASK['mer']).all())

    def test_palettes_et_matieres(self):
        for g, v in M['normalization']['palettes'].items():
            self.assertLessEqual(len(colors([BY[k][0] for k in v['calques']])), v['couleurs'], g)
        L = lambda k: BY[k][0][alpha(BY[k][0])][:, :3].astype(int)
        self.assertNotIn('profondeur', BY)
        f = L('fleurs'); self.assertGreater(float(((f.max(1) - f.min(1)) > 150).mean()), 0.15)
        d = L('dalles').mean(0); self.assertGreater(d[0], d[2] + 60); self.assertGreater(d[0], d[1])
        self.assertGreater(L('herbe').mean(0)[1], L('jungle').mean(0)[1] + 60)
        au = L('autel').mean(0); self.assertGreater(au[0], au[2] + 45)
        lab, n = nd.label(MASK['palmiers']); self.assertGreaterEqual(n, 6)
        lab, n = nd.label(MASK['fleurs']); self.assertGreaterEqual(n, 15)
        self.assertTrue((nd.binary_dilation(MASK['autel'], iterations=3) & MASK['tertre']).any())
        self.assertTrue((nd.binary_dilation(MASK['mer'], iterations=2) & MASK['rive']).any())

    def test_ombres_au_pied_du_tertre_et_de_l_autel(self):
        L = lambda k: lum(BY[k][0][alpha(BY[k][0])])
        self.assertLess(L('ombres').mean(), L('herbe').mean() - 15)
        o = BY['ombres'][0][alpha(BY['ombres'][0])][:, :3].astype(int)
        self.assertGreater(float((o[:, 1] > o[:, 2] + 40).mean()), 0.8)
        base = nd.distance_transform_edt(~(MASK['tertre'] | MASK['autel']))
        self.assertLessEqual(float(base[MASK['ombres']].max()), 45 * 576 / 896 + 2)

    def test_fidelite_rip(self):
        dec, ref = B.rgb(HERE / 'bruts/decor_magenta.png'), B.rgb(REF)
        fid = B.fidelity(dec, ref)
        for k, v in fid.items():
            self.assertLess(v['distance'], 35, (k, v))
            self.assertAlmostEqual(v['distance'], M['fidelite_rip']['brut'][k]['distance'], places=1)
        for nm, v in M['fidelite_rip']['calques_finaux'].items():
            lay = BY[nm][0]; px = lay[alpha(lay)][:, :3].astype(float)
            sel = B.materials(px.reshape(-1, 1, 3))[v['matiere']][:, 0]
            px = px[sel] if sel.sum() > 50 else px
            d = float(np.linalg.norm(px.mean(0) - np.array(fid[v['matiere']]['rip_rgb'])))
            self.assertLess(d, 35, (nm, d)); self.assertAlmostEqual(d, v['distance_rip'], places=1)

    def test_mer_profil_exact_du_rip_sans_lisere_clair(self):
        Me = M['mer']; fr = BY['mer']; water = MASK['mer']
        self.assertEqual((len(fr), Me['frame_length_ticks'], Me['pas_px'] * len(fr)), (24, 5, Me['periode_px']))
        self.assertEqual((B.WAVE_COL, B.WAVE_Y0, B.WAVE_P, B.CREST_X, B.BANDE, B.CALME),
                         (ETC1.WAVE_COL, ETC1.WAVE_Y0, ETC1.WAVE_P, ETC1.CREST_X, ETC1.BANDE, ETC1.CALME))
        self.assertTrue(colors(fr) <= rip_colors())
        ref = B.rgb(REF); prof, crest = B.wave_model(ref)
        self.assertEqual([list(c) for c in prof], Me['profil'])
        self.assertEqual(crest, Me['crete'])
        calc, d = B.sea_frames(water, prof, crest)
        for t, a in enumerate(fr):
            self.assertTrue((a == calc[t]).all(), t)
            # Contre la rive (d <= 2) : uniquement la bande sombre du rip, aucun liseré clair
            shore = water & (d <= B.SHORE_BAND)
            self.assertEqual({tuple(int(v) for v in c) for c in np.unique(a[shore][:, :3], axis=0)}, {B.BANDE})
        self.assertTrue((B.sea_frames(water, prof, crest, ts=[24])[0][0] == fr[0]).all())
        for t in range(24):
            self.assertGreater(int((fr[t][water] != fr[(t + 1) % 24][water]).any(-1).sum()), 1000, t)

    def test_papillons_poses_etc1_et_boucle_fermee(self):
        P = M['papillons']; fr = BY['papillons']; ps = poses()
        self.assertEqual((len(fr), P['frame_length_ticks']), (24, 5))
        self.assertEqual(P['poses'], {k: list(v) for k, v in ETC1.POSE_WIN.items()})
        for k, p in ps.items():
            p_etc = load(R / f'renders/entree_clairiere_tropicale_sud_nord_v1/poses/ETC1_{k}.png')
            self.assertTrue((p == p_etc).all(), k)
        calc = B.butterfly_frames(ps, [tuple(fl) for fl in P['vols']])
        for t, a in enumerate(fr):
            self.assertTrue((a == calc[t]).all(), t)
            self.assertGreater(int(alpha(a).sum()), 40, t)
        self.assertTrue((B.butterfly_frames(ps, [tuple(fl) for fl in P['vols']], ts=[24])[0] == fr[0]).all())
        for t in range(24):
            self.assertGreater(int((fr[t] != fr[(t + 1) % 24]).any(-1).sum()), 20, t)

    def test_ora_and_scene(self):
        with zipfile.ZipFile(O / 'FCT2_fin_clairiere_tropicale_calques.ora') as z:
            merged = np.array(Image.open(io.BytesIO(z.read('mergedimage.png'))).convert('RGBA'))
            self.assertIn(b'Clairiere tropicale', z.read('stack.xml'))
        sc = Image.new('RGBA', (W, H))
        for frames in STACK:
            sc.alpha_composite(Image.fromarray(frames[0]))
        self.assertTrue((np.array(sc) == merged).all())
        self.assertTrue((np.array(sc) == load(O / 'review/FCT2_scene_t000.png')).all())
        for L in M['layers']:
            self.assertEqual(M['scene_loop_ticks'] % (L['phases'] * L['ticks']) if L['phases'] > 1 else 0, 0)

    def test_access(self):
        a = M['access']; self.assertTrue(a['path_found_16x16'] and a['path_to_boss'] and a['path_to_objective'])
        ex, ey = a['entry_px']; bx, by = a['boss_px']; ox, oy = a['objective_px']
        w = MASK['praticable']
        self.assertGreater(ey, H - 64); self.assertLess(oy, H // 3)
        self.assertTrue(w[ey:ey + 16, ex:ex + 16].mean() > 0.7)
        self.assertTrue(w[by:by + 16, bx:bx + 16].mean() > 0.9)
        self.assertTrue(w[oy:oy + 16, ox:ox + 16].mean() > 0.7)
        dn = nd.distance_transform_edt(w)
        self.assertGreater(float(dn[by + 8, bx + 8]), 40)
        self.assertLess(abs(ox + 8 - W // 2), 64)
        self.assertLess(oy, by - 80)
        self.assertEqual(a['walkable_cells'] + a['blocked_cells'], (W // 8) * (H // 8))
        self.assertGreater(a['walkable_cells'], 1200)
        doc = json.loads((S / f"Data/Ground/{M['pmdo']['asset']}.rsground").read_text())
        blocked = np.array([[c['Tags'] for c in col] for col in doc['Object']['obstacles']]).T.astype(bool)
        for k in ('mer', 'jungle', 'tertre', 'autel', 'rive'):
            cells = MASK[k].reshape(H // 8, 8, W // 8, 8).mean((1, 3)) > 0.5
            self.assertTrue(blocked[cells].all(), k)
        for px in (a['entry_px'], a['boss_px'], a['objective_px']):
            self.assertFalse(blocked[px[1] // 8:px[1] // 8 + 2, px[0] // 8:px[0] // 8 + 2].any(), px)
        self.assertTrue(blocked[:4].all()); self.assertTrue(blocked[:, :4].all() and blocked[:, -4:].all())

    def test_prefix_and_namespace_unique(self):
        for p in (R / 'source').glob('*/build.py'):
            if p.parent != HERE:
                s = p.read_text(errors='ignore')
                self.assertNotIn("PFX = 'FCT2'", s, p); self.assertNotIn("'fin_clairiere_tropicale'", s, p)

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
