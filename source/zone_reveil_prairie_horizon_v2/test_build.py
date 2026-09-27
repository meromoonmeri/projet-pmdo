"""Tests dédiés — Zone de réveil V2 (ZRV2) : layout de ZRV1, mer V24P04A, ciel / nuages / montagne séparés.
.venv/bin/python -m unittest source.zone_reveil_prairie_horizon_v2.test_build -v
Contrôles d'images, de lois d'animation, de boucles, de profondeur et de grille : PAS un test du moteur PMDO.
"""
from pathlib import Path
import hashlib, importlib.util, io, json, math, unittest, zipfile
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/zone_reveil_prairie_horizon_v2'
V1 = R / 'renders/zone_reveil_prairie_horizon_v1'
M = json.loads((O / 'manifest.json').read_text())
W, H = M['size_px']


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


B = loadmod('zrv2_build', HERE / 'build.py')
S = B.STAGE
YH = B.YH


def load(p):
    return np.array(Image.open(p).convert('RGBA'))


def alpha(a):
    return a[..., 3] > 0


LAYERS = {amb: {L['nom']: L for L in M['ambiances'][amb]['layers']} for amb in B.AMB}


def frame(amb, nom, t=0):
    L = LAYERS[amb][nom]
    return load(O / (L['file'] if L['phases'] == 1 else L['file'].replace('fNNN', f'f{t:03d}')))


def frames(amb, nom):
    return [frame(amb, nom, t) for t in range(LAYERS[amb][nom]['phases'])]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


SEA = np.array(Image.open(O / 'masques/ZRV2_masque_mer.png')) > 127
MEADOW = np.array(Image.open(O / 'masques/ZRV2_masque_prairie.png')) > 127
_ALL = {}


def rebuilt():
    if not _ALL:
        _ALL['out'], _ALL['info'], _ALL['meadow'], _ALL['sea'], _ALL['strip'] = B.make_all()
    return _ALL


class Build(unittest.TestCase):
    def test_bruts_references_et_prompts(self):
        for r in M['raw_inputs']:
            self.assertEqual(sha(R / r['file']), r['sha256'], r['file'])
        for k, v in M['references'].items():
            self.assertEqual(sha(R / v['file']), v['sha256'], k)
        g = {x['file']: x for x in M['generation']}
        self.assertEqual(set(g), {'ciel_mer_jour.png', 'cretes_jour.png', 'mer_de_nuages_jour.png', 'montagne_jour.png', 'astres.png'})
        for k in ('ciel_mer_jour.png', 'cretes_jour.png', 'mer_de_nuages_jour.png'):        # mer du jeu V24P04A en référence
            self.assertTrue(any('v24p04a' in i for i in g[k]['images']), k)
        self.assertTrue(any('v1_montagne' in i for i in g['montagne_jour.png']['images']))  # la montagne de ZRV1
        self.assertFalse(M['art_approved']); self.assertFalse(M['runtime_tested'])

    def test_exports_reproduits(self):
        """make_all() redonne exactement chaque image exportée (toutes les phases de tous les calques)."""
        out = rebuilt()['out']
        for amb, L in out.items():
            self.assertEqual([n for n in B.ORDER if n in L], list(LAYERS[amb]), amb)
            for nom, (fr, tk) in L.items():
                self.assertEqual((len(fr), tk if len(fr) > 1 else 60), (LAYERS[amb][nom]['phases'], LAYERS[amb][nom]['ticks']))
                for t, f in enumerate(fr):
                    self.assertTrue((f == frame(amb, nom, t)).all(), (amb, nom, t))

    def test_layout_de_zrv1(self):
        """Prairie, mer, collisions et marqueurs : ceux de ZRV1, sans changement."""
        self.assertTrue(M['mesures']['mer_identique_zrv1'])
        self.assertTrue((SEA == (np.array(Image.open(V1 / 'masques/ZRV1_masque_mer.png')) > 127)).all())
        for amb, a in B.AMB.items():
            for k, i in B.V1_INDEX.items():
                v1 = load(V1 / f'calques/{amb}/ZRV1{a}_{i:02d}_{k}.png')
                self.assertTrue((frame(amb, k, 0) == v1).all(), (amb, k))                 # fleurs : phase A = ZRV1
        v1m = json.loads((V1 / 'manifest.json').read_text())
        self.assertEqual(M['access']['entry_px'], v1m['access']['entry_px'])
        self.assertEqual(M['access']['reveil_px'], v1m['access']['reveil_px'])
        self.assertEqual(M['access']['blocked_cells'], v1m['access']['blocked_cells'])

    def test_multicalque_et_profondeur(self):
        """Ciel, nuages, montagne, mer séparés ; de l'avant vers l'arrière : mer -> montagne -> nuages."""
        o = B.ORDER
        self.assertLess(o.index('ciel'), o.index('nuages')); self.assertLess(o.index('nuages'), o.index('montagne'))
        self.assertLess(o.index('montagne'), o.index('mer')); self.assertLess(o.index('mer'), o.index('herbe'))
        for amb in B.AMB:
            sky, mont, mer = alpha(frame(amb, 'ciel')), alpha(frame(amb, 'montagne')), alpha(frame(amb, 'mer'))
            self.assertTrue(sky[:YH].all()); self.assertFalse(sky[YH:].any())
            self.assertTrue((mer == SEA).all()); self.assertFalse(mont[YH:].any())
            for nom in ('scintillement', 'houle', 'reflet', 'ecume'):
                if nom in LAYERS[amb]:
                    for f in frames(amb, nom):
                        self.assertTrue((alpha(f) <= SEA).all(), (amb, nom))
            for t in range(0, B.CLOUD_PHASES, 8):
                c = alpha(frame(amb, 'nuages', t))
                self.assertFalse((c & mont).any(), (amb, t))                               # derrière la montagne
                self.assertFalse(c[YH:].any())

    def test_montagne_raccordee_a_l_horizon(self):
        m = alpha(frame('jour', 'montagne'))
        self.assertTrue(m[YH - 1].any())                                                   # la base touche l'horizon
        rows = [y for y in range(YH) if m[y].any()]
        left = np.array([np.nonzero(m[y])[0].min() for y in rows]); right = np.array([np.nonzero(m[y])[0].max() for y in rows])
        self.assertTrue((np.diff(left) <= 0).all()); self.assertTrue((np.diff(right) >= 0).all())   # flancs qui s'élargissent
        # pas de bord vertical : sur les 20 rangées du pied, chaque flanc avance d'au moins 1 px toutes les 2 rangées
        self.assertGreaterEqual(left[-21] - left[-1], 10); self.assertGreaterEqual(right[-1] - right[-21], 10)
        for e in (left[-40:], right[-40:]):                                                # aucun pan vertical de 4 rangées
            same = np.diff(e) == 0
            self.assertFalse(any(same[i:i + 3].all() for i in range(len(same) - 2)))
        self.assertLess(rows[0], 30)                                                       # sommet haut (celui de ZRV1)

    def test_nuages_defilent_boucle_fermee(self):
        strip = load(O / 'masques/ZRV2_jour_nuages_bande.png')
        self.assertEqual(strip.shape[1], B.CLOUD_PERIOD); self.assertEqual(W % B.CLOUD_PERIOD, 0)
        self.assertEqual(B.CLOUD_PHASES * B.CLOUD_PAS % B.CLOUD_PERIOD, 0)
        self.assertTrue((strip == rebuilt()['strip']).all())
        self.assertTrue(alpha(strip)[-1].all())                                           # le banc est posé sur l'horizon
        # raccord : la bande est continue en boucle (écart moyen entre la dernière et la première colonne comme ailleurs)
        a = strip[..., :3].astype(int); d = np.abs(np.diff(a, axis=1)).mean(); seam = np.abs(a[:, 0] - a[:, -1]).mean()
        self.assertLess(seam, d * 2.5)
        mont = alpha(frame('jour', 'montagne')); want = B.cloud_frames(strip, mont)
        for t in (0, 1, 100, 255):
            self.assertTrue((want[t] == frame('jour', 'nuages', t)).all(), t)
        self.assertTrue((np.roll(strip, B.CLOUD_PHASES * B.CLOUD_PAS, axis=1) == strip).all())    # phase 256 = phase 0
        self.assertFalse((frame('jour', 'nuages', 0) == frame('jour', 'nuages', 1)).all())

    def test_houle_loi_v24p04a(self):
        self.assertEqual((B.SWELL_STEPS, B.SWELL_TICKS, B.GLINT_STEPS, B.GLINT_TICKS), (12, 10, 16, 4))
        self.assertEqual(len(B.GLINT_LEVELS), B.GLINT_STEPS); self.assertEqual(W % B.SWELL_PERIOD_X, 0)
        hmax = max(s[1] for pair in M['mesures']['cretes']['tailles_px'] for s in pair)
        ymax = int(np.nonzero(SEA.any(1))[0].max()); K = B.swell_rows()
        # la dernière crête sort de la mer avant de disparaître : aucun saut à la boucle
        self.assertGreater(B.swell_y(K - 1) - hmax + 1, ymax)
        # les crêtes grandissent en descendant (tailles croissantes)
        widths = [s[0][0] for s in M['mesures']['cretes']['tailles_px']]
        self.assertEqual(widths, sorted(widths))
        # loi de profondeur : bas des crêtes du cran s en y(k + s/12), dans la mer pleine largeur
        top_meadow = int(np.nonzero(MEADOW.any(1))[0].min())
        for amb in B.AMB:
            fr = frames(amb, 'houle'); self.assertEqual(len(fr), 12)
            for s, f in enumerate(fr):
                a = alpha(f)
                want = {int(round(B.swell_y(k + s / 12))) for k in range(K)}
                bottoms = {y for y in range(YH, top_meadow) if a[y].any() and not a[y + 1].any()}
                # rangées transparentes au pied des sprites : le bas visible est au plus 3 px au-dessus de y(u)
                self.assertTrue(all(any(0 <= w - y <= 3 for w in want) for y in bottoms), (amb, s, sorted(bottoms), sorted(want)))
                self.assertGreaterEqual(len(bottoms), 1)
                # motif horizontal de 96 px (deux états alternés -> 192) au-dessus de la prairie
                self.assertTrue((f[YH:top_meadow] == np.roll(f[YH:top_meadow], 192, axis=1)).all() if amb == 'jour' else True)
            self.assertFalse((fr[0] == fr[1]).all())
        self.assertTrue((frames('jour', 'houle')[0][YH:top_meadow] != 0).any())

    def test_scintillement_horizon(self):
        for amb in B.AMB:
            fr = frames(amb, 'scintillement'); self.assertEqual(len(fr), 16)
            for f in fr:
                ys = np.nonzero(alpha(f).any(1))[0]
                if len(ys):
                    self.assertGreaterEqual(ys.min(), YH); self.assertLess(ys.max(), YH + 40)    # bande de l'horizon
            n = [int(alpha(f).sum()) for f in fr]
            self.assertGreater(max(n) - min(n), 0)

    def test_reflet_astre(self):
        self.assertNotIn('reflet', LAYERS['jour']); self.assertNotIn('astre', LAYERS['jour'])
        for amb in ('aube', 'nuit'):
            A = B.ASTRE[amb]; xc = A['c'][0]
            ast = alpha(frame(amb, 'astre')); mont = alpha(frame(amb, 'montagne'))
            fr = frames(amb, 'reflet'); self.assertEqual(len(fr), B.SWELL_STEPS)
            self.assertEqual(LAYERS[amb]['reflet']['ticks'], B.SWELL_TICKS)                   # calé sur la houle
            bands = B.reflection_bands(xc, A['d'])
            for f in fr:
                ys, xs = np.nonzero(alpha(f))
                self.assertGreater(len(ys), 200)
                self.assertTrue((np.abs(xs - xc) <= max(b['hw'] for b in bands) * 1.2 + 10).all())   # colonne sous l'astre
                mer = frame(amb, 'mer')
                self.assertGreater(B.lum(f[alpha(f)][:, :3]).mean(), B.lum(mer[SEA][:, :3]).mean() + 40)
            self.assertFalse((fr[0] == fr[3]).all())
            ys, xs = np.nonzero(ast); self.assertLess(ys.max(), YH)
            if amb == 'nuit':
                self.assertTrue((ast & mont).any())                                          # la lune derrière le sommet
            else:
                vis = ast & ~mont
                for t in range(0, B.CLOUD_PHASES, 32):
                    vis = vis & ~alpha(frame(amb, 'nuages', t))
                self.assertGreater(vis.sum(), 0.6 * ast.sum())                                # soleil levant bien visible

    def test_fleurs_sky_peak(self):
        for amb in B.AMB:
            fr = frames(amb, 'fleurs'); self.assertEqual(len(fr), 4); self.assertEqual(LAYERS[amb]['fleurs']['ticks'], 12)
            self.assertTrue((fr[0] == fr[2]).all()); self.assertFalse((fr[0] == fr[1]).all()); self.assertFalse((fr[1] == fr[3]).all())
            for f in fr:
                self.assertTrue(set(np.unique(f[..., 3])) <= {0, 255})

    def test_etoiles_nuit(self):
        fr = frames('nuit', 'etoiles'); self.assertEqual(len(fr), B.STAR_PHASES)
        mont = alpha(frame('nuit', 'montagne')); cloud_top = YH - load(O / 'masques/ZRV2_jour_nuages_bande.png').shape[0]
        for f in fr:
            a = alpha(f); self.assertFalse((a & mont).any()); self.assertFalse(a[cloud_top:].any())
        self.assertGreaterEqual(M['mesures']['etoiles']['gardees'], 6)

    def test_couleurs_aube_nuit(self):
        d = B.lum(frame('jour', 'mer')[SEA][:, :3]).mean(); n = B.lum(frame('nuit', 'mer')[SEA][:, :3]).mean()
        self.assertLess(n, d - 60)                                                          # la mer de nuit est sombre
        aube = frame('aube', 'mer')[SEA][:, :3].astype(int)
        self.assertGreater(float((aube[:, 2] >= aube[:, 1]).mean()), 0.9)                   # aube : mer ardoise / violette
        sky = frame('aube', 'ciel')[:YH, :, :3].astype(int)
        self.assertGreater(sky[80, :, 1].mean(), sky[5, :, 1].mean() + 10)                 # aube : dégradé vers le rose clair
        night = frame('nuit', 'ciel')[:YH, :, :3].astype(int)
        self.assertTrue((night[..., 2] > night[..., 0]).mean() > 0.95)                       # nuit : ciel bleu nuit

    def test_access_et_collisions(self):
        a = M['access']; self.assertTrue(a['path_found_16x16'])
        walk = np.array(Image.open(V1 / 'masques/ZRV1_masque_praticable.png')) > 127
        for amb in B.AMB:
            doc = json.loads((S / f"Data/Ground/{B.ASSET[amb]}.rsground").read_text(encoding='utf-8-sig'))
            blocked = np.array([[c['Tags'] for c in col] for col in doc['Object']['obstacles']]).T.astype(bool)
            self.assertEqual(int(blocked.sum()), a['blocked_cells'])
            cells = SEA.reshape(H // 8, 8, W // 8, 8).mean((1, 3)) > 0.5
            self.assertTrue(blocked[cells].all()); self.assertTrue(blocked[:YH // 8].all())
            self.assertFalse(blocked[walk.reshape(H // 8, 8, W // 8, 8).mean((1, 3)) == 1].any())
            mk = {m['EntName']: m for m in doc['Object']['Entities'][0]['Markers']}
            self.assertEqual(set(mk), {'reveil', 'entrance'})
            self.assertEqual([mk['reveil']['Collider']['X'], mk['reveil']['Collider']['Y']], a['reveil_px'])

    def test_ora_et_scenes(self):
        for amb in B.AMB:
            with zipfile.ZipFile(O / f'ZRV2_zone_reveil_{amb}_calques.ora') as z:
                merged = np.array(Image.open(io.BytesIO(z.read('mergedimage.png'))).convert('RGBA'))
                self.assertEqual(sum(1 for n in z.namelist() if n.startswith('data/layer')), len(LAYERS[amb]))
            comp = Image.new('RGBA', (W, H))
            for nom in LAYERS[amb]:
                comp.alpha_composite(Image.fromarray(frame(amb, nom, 0)))
            self.assertTrue((np.array(comp) == merged).all(), amb)
            self.assertTrue((load(O / f'review/ZRV2_{amb}_scene_t000.png') == merged).all(), amb)

    def test_prefixe_et_namespace_uniques(self):
        for p in (R / 'source').glob('*/build*.py'):
            if p.parent != HERE:
                s = p.read_text(errors='ignore')
                self.assertNotIn("PFX = 'ZRV2'", s, p); self.assertNotIn("'zone_reveil_prairie_horizon_v2'", s, p)
        names = [p.name for p in (O / 'calques').rglob('*.png')] + [p.name for p in (O / 'animation').rglob('*.png')]
        self.assertEqual(len(names), len(set(names)))
        v1 = {p.name for p in (V1 / 'calques').rglob('*.png')} | {p.name for p in (V1 / 'animation').rglob('*.png')}
        self.assertFalse(set(names) & v1)

    def test_ground_roundtrip(self):
        nr = loadmod('native_reader', R / 'source/cote_v5_expeditions/audit_references.py')
        banks = {p.stem: nr.tiles(p)[1] for p in (S / 'Content/Tile').glob('*.tile')}
        self.assertEqual(set(banks), set(M['pmdo']['tiles_per_bank']))
        tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
        self.assertEqual(set(tools.read_index(S / 'Content/Tile/index.idx')), set(banks))
        for amb in B.AMB:
            doc = json.loads((S / f"Data/Ground/{B.ASSET[amb]}.rsground").read_text(encoding='utf-8-sig')); o = doc['Object']
            self.assertEqual(doc['Version'], '0.8.12.0'); self.assertEqual(len(o['Layers']), len(LAYERS[amb]) + 1)
            self.assertEqual(o['Layers'][-1]['Layer'], 4)
            for li, (nom, L) in enumerate(LAYERS[amb].items()):
                n = L['phases']
                for t in sorted({0, n // 2, n - 1}):
                    want = frame(amb, nom, t); out = np.zeros((H, W, 4), 'uint8')
                    for x, col in enumerate(o['Layers'][li]['Tiles']):
                        for y, cell in enumerate(col):
                            for track in cell['Layers']:
                                if len(track['Frames']) > 1:
                                    self.assertEqual((len(track['Frames']), track['FrameLength']), (n, L['ticks']))
                                f = track['Frames'][t % len(track['Frames'])]
                                out[y*8:y*8+8, x*8:x*8+8] = np.array(nr.straight(banks[f['Sheet']][f['TexLoc']['X'], f['TexLoc']['Y']]))
                    self.assertTrue((out == want).all(), (amb, nom, t))


if __name__ == '__main__':
    unittest.main()
