"""Tests dédiés — Fin Jardin secret V1 (FJA1, 4:3 vaste, feuilles / fleurs Halcyon / pétales).
.venv/bin/python -m unittest source.fin_jardin_secret_v1.test_build -v
Contrôles d'images, de formats, de palettes, de fidélité au rip, de cadence et de grille : PAS un test du moteur PMDO.
"""
from pathlib import Path
import hashlib, importlib.util, io, json, re, unittest, zipfile
import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/fin_jardin_secret_v1'
S = R / '.cache/fin_jardin_secret_v1/fin_jardin_secret'
M = json.loads((O / 'manifest.json').read_text())
W, H = M['size_px']
NAMES = [Path(L['file']).name.replace('_fNN', '') for L in M['layers']]
EJS = R / 'source/entree_jardin_secret_sud_nord_v1/bruts'
STATIC = ('prairie', 'herbe', 'ombres', 'fleurs', 'rochers', 'arbres', 'haies', 'souche', 'marches', 'profondeur', 'fond')
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
BY = {re.sub(r'^FJA1_\d\d_', '', Path(n).stem): fr for n, fr in zip(NAMES, STACK)}
ORDER = list(BY)
MASK = {k: np.array(Image.open(O / f'masques/FJA1_masque_{k}.png')) > 0 for k in (*STATIC, 'rayon', 'praticable')}
B = loadmod('fja1_build', HERE / 'build.py')


def alpha(a):
    return a[..., 3] == 255


def colors(frames):
    return {tuple(int(v) for v in c) for a in frames for c in np.unique(a[a[..., 3] > 0][:, :3], axis=0)}


def rip_colors():
    a = np.array(Image.open(REF).convert('RGB'))
    return {tuple(int(v) for v in c) for c in np.unique(a.reshape(-1, 3), axis=0)}


def lum(px):
    return px[..., :3].astype(float) @ [.299, .587, .114]


def base_idx():
    return np.array(Image.open(O / 'masques/FJA1_rayon_crans.png')).astype(int) // 11


class Build(unittest.TestCase):
    def test_raw_hashes_and_reference(self):
        for r in M['raw_inputs']:
            self.assertEqual(hashlib.sha256((R / r['file']).read_bytes()).hexdigest(), r['sha256'])
        ref = M['reference_da']
        self.assertEqual(ref['file'], REF.name)
        self.assertEqual(hashlib.sha256(REF.read_bytes()).hexdigest(), ref['sha256'])
        g = {x['file']: x for x in M['generation']}
        self.assertEqual(g['decor.png']['images'], [REF.name, 'source/entree_jardin_secret_sud_nord_v1/bruts/decor.png'])   # rip + décor EJS1
        self.assertEqual(g['temoin_sans_objets.png']['images'], [f'{B.LOT}/bruts/decor.png'])
        self.assertEqual((HERE / 'bruts/sol_complet.png').read_bytes(), (EJS / 'sol_complet.png').read_bytes())   # copie d'EJS1
        self.assertNotEqual((HERE / 'bruts/decor.png').read_bytes(), (EJS / 'decor.png').read_bytes())          # décor nouveau
        self.assertTrue(all(len(x['prompt']) > 100 for x in g.values()))
        ec = [x for x in M['generation'] if x.get('ecarte')]
        self.assertEqual(len(ec), 0)
        self.assertIn('choisi par l agent', M['biome'])
        self.assertFalse(M['art_approved']); self.assertFalse(M['pmdo']['runtime_tested'])
        rg = M['recalage']['temoin']; self.assertLess(rg['ecart_moyen'], rg['ecart_decale_1px'])   # témoin bien calé

    def test_sizes_names_alpha_no_magenta(self):
        self.assertEqual(len(NAMES), len(set(NAMES))); self.assertTrue(all(n.startswith('FJA1_') for n in NAMES))
        self.assertEqual((W, H, W % 8, H % 8), (768, 576, 0, 0)); self.assertEqual(W * 3, H * 4)   # 4:3
        n = M['normalization']; self.assertAlmostEqual(n['scale'], 576 / 896)
        self.assertEqual(n['scaled'][0] - sum(n['crop_x']), W)
        for name, frames in BY.items():
            for a in frames:
                self.assertEqual(a.shape[:2], (H, W))
                self.assertTrue(set(np.unique(a[..., 3])) <= {0, 255}, name)
                v = a[a[..., 3] > 0].astype(int)
                bad = (v[:, 0] - v[:, 1] > 60) & (v[:, 2] - v[:, 1] > 60)
                if name == 'fleurs_halcyon':          # fleurs natives Halcyon : pétales violets légitimes (couleurs de l'atlas)
                    continue
                self.assertEqual(int(bad.sum()), 0, name)

    def test_multicalque_full_coverage_and_order(self):
        self.assertEqual(ORDER, ['sol_complet', *STATIC, 'fleurs_halcyon', 'petales', 'feuilles', 'rayon', 'lucioles'])
        self.assertTrue(alpha(BY['sol_complet'][0]).all())
        fixed = [alpha(BY[k][0]) for k in STATIC] + [MASK['rayon']]
        self.assertTrue((np.sum(fixed, 0) == 1).all())                      # calques fixes + rayon : partition exacte
        for k in STATIC:
            self.assertGreater(int(alpha(BY[k][0]).sum()), 200, k)
            self.assertTrue((alpha(BY[k][0]) == MASK[k]).all(), k)
        for a in BY['rayon']:
            self.assertTrue((alpha(a) == MASK['rayon']).all())
        sol = BY['sol_complet'][0][..., :3].astype(float).reshape(-1, 3)
        self.assertGreater(len(colors(BY['sol_complet'])), 8)               # texture, pas un aplat
        m = sol.mean(0); self.assertGreater(m[1], m[0] + 30); self.assertGreater(m[1], m[2] + 80)   # herbe verte

    def test_palettes_et_matieres(self):
        for g, v in M['normalization']['palettes'].items():
            self.assertLessEqual(len(colors([BY[k][0] for k in v['calques']])), v['couleurs'], g)
        L = lambda k: BY[k][0][alpha(BY[k][0])][:, :3].astype(int)
        self.assertLess(float(np.median(lum(L('profondeur')))), 75)                     # trou sombre
        s = L('souche').mean(0); self.assertGreater(s[0], s[2] + 60)                     # souche dorée
        f = L('fond').mean(0); self.assertLess(float(lum(f)), 85); self.assertGreater(f[1], f[0] + 15)
        for k in ('prairie', 'herbe', 'ombres'):
            p = L(k).mean(0); self.assertGreater(p[1], p[0] + 30, k)
        self.assertGreater(float(lum(L('prairie')).mean()), float(lum(L('ombres')).mean()) + 25)
        self.assertLess(float(L('prairie')[:, 2].mean()), float(L('herbe')[:, 2].mean()) - 15)   # prairie plus jaune
        r = L('rochers').mean(0); self.assertLess(abs(r[0] - r[1]), 30); self.assertGreater(r[0], r[2] + 25)  # roche beige
        sg = M['segmentation_mesures']
        self.assertGreaterEqual(sg['fleurs'], 100); self.assertGreaterEqual(sg['rochers'], 1); self.assertGreaterEqual(sg['arbres'], 4)
        lab, n = nd.label(MASK['rochers']); self.assertGreaterEqual(n, 1)
        # La souche : trou dans la souche, marches juste dessous qui touchent le trou et l'herbe.
        self.assertTrue((nd.binary_dilation(MASK['profondeur'], iterations=2) & MASK['souche']).any())
        self.assertTrue((nd.binary_dilation(MASK['profondeur'], iterations=2) & MASK['marches']).any())
        ym, _ = np.nonzero(MASK['marches']); yp, _ = np.nonzero(MASK['profondeur'])
        self.assertGreater(ym.mean(), yp.mean())
        grass = MASK['prairie'] | MASK['herbe'] | MASK['ombres'] | MASK['fleurs']
        self.assertTrue((nd.binary_dilation(MASK['marches'], iterations=2) & grass).any())
        self.assertTrue(MASK['praticable'][MASK['marches']].all())
        # Rayon en haut, au-dessus de la souche, relié au bord haut ; jamais sur la souche.
        ys, _ = np.nonzero(MASK['rayon']); self.assertEqual(int(ys.min()), 0); self.assertLess(float(ys.max()), yp.min())
        self.assertFalse((MASK['rayon'] & (MASK['souche'] | MASK['profondeur'])).any())

    def test_fidelite_rip(self):
        dec, ref = B.rgb(HERE / 'bruts/decor.png'), B.rgb(REF)
        fid = B.fidelity(dec, ref)
        self.assertEqual(set(fid), {'fond', 'herbe_claire', 'herbe', 'roche'})
        for k, v in fid.items():
            self.assertLess(v['distance'], 35, (k, v))
            self.assertAlmostEqual(v['distance'], M['fidelite_rip']['brut'][k]['distance'], places=1)
        for nm, v in M['fidelite_rip']['calques_finaux'].items():
            lay = BY[nm][0]; px = lay[alpha(lay)][:, :3].astype(float)
            sel = B.materials(px.reshape(-1, 1, 3))[v['matiere']][:, 0]
            self.assertGreater(int(sel.sum()), 50, nm)                    # la matière est bien présente
            d = float(np.linalg.norm(px[sel].mean(0) - np.array(fid[v['matiere']]['rip_rgb'])))
            self.assertLess(d, 35, (nm, d)); self.assertAlmostEqual(d, v['distance_rip'], places=1)
        herbe = np.array(fid['herbe']['rip_rgb'])
        f = B.rgb(HERE / 'bruts/sol_complet.png').reshape(-1, 3).mean(0)
        d = float(np.linalg.norm(f - herbe)); self.assertLess(d, 35); self.assertAlmostEqual(d, M['fidelite_rip']['sol_complet'], places=1)
        for fn, dist in M['fidelite_rip']['sol_complet_ecartes'].items():   # écartés : non conformes, gardés, pas retouchés
            self.assertGreater(dist, 35, fn)
            self.assertAlmostEqual(float(np.linalg.norm(B.rgb(HERE / 'bruts' / fn).reshape(-1, 3).mean(0) - herbe)), dist, places=1)

    def test_rayon_rampe_exacte_boucle_fermee(self):
        rp = [tuple(c) for c in M['rayon']['rampe']]
        self.assertEqual(rp, [tuple(c) for c in B.RAMP]); self.assertEqual(len(rp), 22)
        self.assertTrue(set(rp) <= rip_colors())                                        # couleurs EXACTES du rip
        self.assertEqual(sorted(rp, key=lambda c: lum(np.array(c, float))), rp)         # rampe sombre -> claire
        fr = BY['rayon']; self.assertEqual((len(fr), M['layers'][-2]['ticks']), (24, 7))
        self.assertTrue(colors(fr) <= set(rp))
        bi = base_idx(); m = MASK['rayon']
        want = B.beam_frames(bi, m)
        for t in range(24):
            self.assertTrue((fr[t] == want[t]).all(), t)
        self.assertTrue((B.beam_frames(bi, m, ts=[24])[0] == fr[0]).all())             # 24 = 0 : boucle fermée
        self.assertTrue((fr[0][m][:, :3] == np.array(rp, 'uint8')[bi[m]]).all())       # phase 0 = rayon du rendu
        idx = [B.ramp_index(f[m]).astype(int) - bi[m] for f in fr]
        self.assertEqual(max(int(np.abs(d).max()) for d in idx), M['rayon']['souffle_crans'])   # souffle de 2 crans
        self.assertGreater(float((idx[6] > 0).mean()), 0.5); self.assertGreater(float((idx[18] < 0).mean()), 0.5)
        dark = m & (bi == 0)                                                            # bords contre le fond : figés
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
        self.assertTrue((B.mote_frames(motes, ts=[24])[0] == fr[0]).all())             # 24 = 0
        solid = MASK['profondeur'] | MASK['souche'] | MASK['marches']
        for t in range(24):
            n, k = nd.label(alpha(fr[t]))[1], 0
            self.assertEqual(n, 10, t)                                                   # 10 lucioles, jamais fondues
            self.assertFalse((alpha(fr[t]) & solid).any(), t)                            # jamais sur la souche ni le trou
            for m in motes:
                x, y, _ = B.mote_state(m, t); self.assertTrue(1 <= y < H - 1 and 1 <= x < W - 1)
        u = [B.mote_state(motes[0], t) for t in range(24)]
        self.assertTrue({s for *_, s in u} == {'point', 'croix'})
        self.assertTrue(all(u[i][1] == u[i - 1][1] - 2 for i in range(1, 24)))            # montée de 2 px par phase

    def test_feuilles_houle_phase0_exacte(self):
        L = M['feuilles']; fr = BY['feuilles']; self.assertEqual((len(fr), M['layers'][ORDER.index('feuilles')]['ticks']), (8, 7))
        lab = np.array(Image.open(O / 'masques/FJA1_feuilles_amas.png')).astype(int); self.assertGreaterEqual(int(lab.max()), 100)
        self.assertEqual(L['amas'], int(lab.max())); self.assertEqual(L['pixels_deplaces'], int((lab > 0).sum()))
        want = B.leaf_frames(fr[0], lab)
        for t in range(8):
            self.assertTrue((fr[t] == want[t]).all(), t)
        self.assertTrue((B.leaf_frames(fr[0], lab, ts=[8])[0] == fr[0]).all())          # 8 = 0 : boucle fermée
        # Phase 0 : calque fixe + feuilles = calque d'origine (sha256 enregistré avant retrait des amas).
        for k in ('arbres', 'haies'):
            base = Image.fromarray(BY[k][0]); top = fr[0].copy(); top[~MASK[k]] = 0; base.alpha_composite(Image.fromarray(top))
            self.assertEqual(hashlib.sha256(np.array(base).tobytes()).hexdigest(), L['sha256_origine_quantifie'][k], k)
        canopy = MASK['arbres'] | MASK['haies']; cs = colors(BY['arbres'] + BY['haies'])
        base_cols = colors([BY['arbres'][0], BY['haies'][0]])
        self.assertTrue(colors(fr) <= base_cols)                                        # couleurs du feuillage, aucune nouvelle
        for t, a in enumerate(fr):
            self.assertTrue((alpha(a) <= canopy).all(), t)                              # jamais hors du feuillage
        # Amplitude : au plus 2 px, et les amas bougent vraiment (au moins la moitié change de place sur la boucle).
        moved = 0; objs = nd.find_objects(lab)
        for i, sl in enumerate(objs):
            ys, xs = np.nonzero(lab[sl] == i + 1); cx = int(round((xs + sl[1].start).mean()))
            sh = [B.leaf_shift(cx, t) for t in range(8)]
            self.assertTrue(all(abs(dx) <= 2 and abs(dy) <= 2 for dx, dy in sh)); self.assertEqual(sh[0], (0, 0))
            moved += any(s_ != (0, 0) for s_ in sh)
        self.assertGreater(moved, 0.5 * len(objs))
        self.assertTrue(any((fr[t] != fr[0]).any() for t in range(1, 8)))
        # La houle va d'ouest en est : deux amas éloignés de 110 px (un quart d'onde) ne sont pas en phase.
        self.assertNotEqual([B.leaf_shift(100, t) for t in range(8)], [B.leaf_shift(210, t) for t in range(8)])

    def test_fleurs_halcyon_natives(self):
        L = M['fleurs_halcyon']; fr = BY['fleurs_halcyon']
        atlas_p = R / L['fichier_local']; self.assertEqual(hashlib.sha256(atlas_p.read_bytes()).hexdigest(), L['sha256_source'])
        atlas = load(atlas_p); self.assertEqual(atlas.shape, (24, 72, 4))
        poses = [atlas[:, i * 24:(i + 1) * 24] for i in range(3)]
        for i, p in enumerate(poses):
            self.assertTrue((load(O / f'poses/FJA1_fleur_halcyon_{i}.png') == p).all())      # pixels natifs, sans retouche
        self.assertEqual((L['sequence'], L['frame_length_ticks'], len(fr)), ([0, 1, 0, 2], 14, 4))
        self.assertEqual(M['layers'][ORDER.index('fleurs_halcyon')]['ticks'], 14)
        cl = [tuple(c) for c in L['touffes']]; self.assertEqual(len(cl), 14)
        self.assertTrue(colors(fr) <= colors([atlas]))                                          # aucune couleur ajoutée
        for t, a in enumerate(fr):
            self.assertEqual(set(np.unique(a[..., 3])), {0, 255})
            for i, (x, y) in enumerate(cl):
                spr = poses[[0, 1, 0, 2][(t + i) % 4]]; m = spr[..., 3] == 255
                self.assertTrue((a[y:y + 24, x:x + 24][m] == spr[m]).all(), (t, i))
        sil = poses[0][..., 3] == 255
        for (x, y) in cl:
            self.assertTrue(MASK['praticable'][y:y + 24, x:x + 24][sil].all())                  # sur le sol praticable
            self.assertFalse((MASK['rayon'] | MASK['profondeur'] | MASK['fond'])[y:y + 24, x:x + 24].any())
            self.assertLess(float(MASK['prairie'][y:y + 24, x:x + 24].mean()), 0.25)          # pas au centre de l'arène
        d = [np.hypot(a[0] - b[0], a[1] - b[1]) for i, a in enumerate(cl) for b in cl[i + 1:]]
        self.assertGreaterEqual(min(d), 52)
        self.assertEqual(len({a.tobytes() for a in fr}), 4)                                      # 4 images distinctes
        self.assertTrue(all(len({a[y:y + 24, x:x + 24].tobytes() for a in fr}) >= 2 for x, y in cl))   # chaque touffe bouge
        self.assertGreater(len({(i + 0) % 4 for i in range(len(cl))}), 1)                        # phases décalées

    def test_petales_couleurs_exactes_chute(self):
        L = M['petales']; fr = BY['petales']; cs = {tuple(v) for v in L['couleurs'].values()}
        self.assertEqual((len(fr), M['layers'][ORDER.index('petales')]['ticks']), (24, 14))
        self.assertTrue(cs <= rip_colors() and colors(fr) <= cs)                                 # couleurs EXACTES du rip
        self.assertEqual(len(cs), 3)
        petals = [tuple(p) for p in L['petales']]; self.assertGreaterEqual(len(petals), 30)
        want = B.petal_frames(petals)
        for t in range(24):
            self.assertTrue((fr[t] == want[t]).all(), t)
        self.assertTrue((B.petal_frames(petals, ts=[24])[0] == fr[0]).all())                    # 24 = 0
        bad = MASK['fond'] | MASK['rayon']
        for t, a in enumerate(fr):
            self.assertFalse((alpha(a) & bad).any(), t)                                          # ni sur le fond ni dans le rayon
            lab, n = nd.label(alpha(a), structure=np.ones((3, 3)))
            self.assertTrue(all(v <= 4 for v in nd.sum(alpha(a), lab, range(1, n + 1))), t)     # pétales de 4 px au plus
            self.assertGreater(int(alpha(a).sum()), 30)
        for p in petals:
            ys = [B.petal_pos(p, u)[1] for u in range(24)]; xs = [B.petal_pos(p, u)[0] for u in range(24)]
            self.assertTrue(all(0 <= ys[i + 1] - ys[i] <= 1 for i in range(23)))                 # il tombe, sans remonter
            self.assertGreaterEqual(ys[-1] - ys[0], 18)
            self.assertGreaterEqual(abs(xs[-1] - xs[0]) , 10)                                    # et dérive
            self.assertEqual((B.petal_shape(0), B.petal_shape(23)), ('point', 'point'))          # naît et finit à 1 px
        self.assertEqual(set(L['formes']), {'carre', 'barre_h', 'barre_v', 'point'})
        self.assertGreater(len({p[3] for p in petals}), 2)                                       # trois couleurs en rotation

    def test_boucle_commune_336(self):
        self.assertEqual(M['scene_loop_ticks'], 336)
        for L in M['layers']:
            if L['phases'] > 1:
                self.assertEqual(336 % (L['phases'] * L['ticks']), 0, L['file'])

    def test_ora_and_scene(self):
        with zipfile.ZipFile(O / 'FJA1_fin_jardin_secret_calques.ora') as z:
            merged = np.array(Image.open(io.BytesIO(z.read('mergedimage.png'))).convert('RGBA'))
            self.assertIn(b'Jardin secret', z.read('stack.xml'))
        sc = Image.new('RGBA', (W, H))
        for frames in STACK:
            sc.alpha_composite(Image.fromarray(frames[0]))
        self.assertTrue((np.array(sc) == merged).all())
        self.assertTrue((np.array(sc) == load(O / 'review/FJA1_scene_t000.png')).all())
        for L in M['layers']:
            self.assertEqual(M['scene_loop_ticks'] % (L['phases'] * L['ticks']) if L['phases'] > 1 else 0, 0)

    def test_access(self):
        a = M['access']; self.assertTrue(a['path_found_16x16'] and a['path_to_boss'] and a['path_to_objective'])
        ex, ey = a['entry_px']; bx, by = a['boss_px']; ox, oy = a['objective_px']
        self.assertGreater(ey, H - 64)
        self.assertTrue(MASK['praticable'][ey:ey + 16, ex:ex + 16].mean() > 0.9)     # arrivée par l'allée sud
        wy, wx = np.nonzero(MASK['praticable'] & (np.mgrid[:H, :W][0] < H * 72 // 100))
        self.assertLess(float(np.hypot(bx - wx.mean(), by - wy.mean())), 24)         # boss au cœur de l'arène
        self.assertTrue(MASK['praticable'][by:by + 16, bx:bx + 16].all())
        self.assertTrue(MASK['praticable'][oy:oy + 16, ox:ox + 16].all())
        dm = nd.distance_transform_edt(~MASK['marches'])
        self.assertLess(float(dm[oy:oy + 16, ox:ox + 16].min()), 12)                 # objectif au pied des marches
        self.assertLess(oy, by - 80); self.assertLess(abs(ox - W // 2), 40)          # au nord, sous la souche
        self.assertGreater(by, H // 3); self.assertLess(by, H * 3 // 4)
        self.assertEqual(a['walkable_cells'] + a['blocked_cells'], (W // 8) * (H // 8))
        self.assertGreater(a['walkable_cells'], 1500)
        doc = json.loads((S / f"Data/Ground/{M['pmdo']['asset']}.rsground").read_text())
        blocked = np.array([[c['Tags'] for c in col] for col in doc['Object']['obstacles']]).T.astype(bool)
        for k in ('profondeur', 'souche', 'rochers', 'arbres', 'haies', 'fond', 'rayon'):
            cells = MASK[k].reshape(H // 8, 8, W // 8, 8).mean((1, 3)) > 0.5
            self.assertTrue(blocked[cells].all(), k)
        cells = MASK['praticable'].reshape(H // 8, 8, W // 8, 8).mean((1, 3)) == 1
        self.assertFalse(blocked[cells].any())
        for k in ('rochers', 'arbres', 'haies', 'fond', 'rayon', 'souche', 'profondeur'):
            self.assertFalse((MASK['praticable'] & MASK[k]).any(), k)
        # La grande prairie centrale et l'herbe sont presque entièrement praticables.
        # (seuil prairie 0,85 : avec la prairie relevée à b < 66, des poches de lisière contre les haies, coupées de l'arène
        # par les arbres, restent bloquées ; l'herbe, elle, reste à 0,95.)
        for k, v in (('prairie', 0.85), ('herbe', 0.95)):
            self.assertGreater(float(MASK['praticable'][MASK[k]].mean()), v, k)

    def test_prefix_and_namespace_unique(self):
        for p in (R / 'source').glob('*/build.py'):
            if p.parent != HERE:
                s = p.read_text(errors='ignore')
                self.assertNotIn("PFX = 'FJA1'", s, p); self.assertNotIn("'fin_jardin_secret'", s, p)

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
        tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
        self.assertEqual(set(tools.read_index(S / 'Content/Tile/index.idx')), set(M['pmdo']['banks']))


if __name__ == '__main__':
    unittest.main()
