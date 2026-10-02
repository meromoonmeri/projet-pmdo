"""Tests dédiés — Plage aux récifs étoilés (ZPR1) : calques, récifs, ciel étoilé aux quatre moments, lois d'animation, boucles, grille.
.venv/bin/python -m unittest source.zone_plage_recifs_etoiles_v1.test_build -v
Contrôles d'images, de lois d'animation, de boucles et de grille : PAS un test du moteur PMDO ni une validation artistique.
"""
from pathlib import Path
import hashlib, importlib.util, io, json, math, unittest, zipfile
import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
LOT = 'zone_plage_recifs_etoiles_v1'
O = R / 'renders' / LOT
M = json.loads((O / 'manifest.json').read_text())
W, H = M['size_px']


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


B = loadmod('zpr1_build', HERE / 'build.py')
S = B.STAGE
YH = B.YH
AMBS = list(B.AMBS)


def load(p):
    return np.array(Image.open(p).convert('RGBA'))


LAYERS = {amb: {L['nom']: L for L in M['ambiances'][amb]['layers']} for amb in AMBS}


def frame(amb, nom, t=0):
    L = LAYERS[amb][nom]
    return load(O / (L['file'] if L['phases'] == 1 else L['file'].replace('fNNN', f'f{t:03d}')))


def frames(amb, nom):
    return [frame(amb, nom, t) for t in range(LAYERS[amb][nom]['phases'])]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


SEA = np.array(Image.open(O / f'masques/{B.PFX}_masque_mer.png')) > 127
LAND = np.array(Image.open(O / f'masques/{B.PFX}_masque_terre.png')) > 127
WALK = np.array(Image.open(O / f'masques/{B.PFX}_masque_praticable.png')) > 127
_C = {}


def ctx():
    if 'ctx' not in _C:
        _C['ctx'] = B.contexte(); _C['sh'] = B.make_shared(_C['ctx'])
    return _C['ctx'], _C['sh']


def lum(a):
    return B.lum(a.astype(float))


class Build(unittest.TestCase):
    def test_bruts_references_et_prompts(self):
        for r in M['raw_inputs']:
            self.assertEqual(sha(R / r['file']), r['sha256'], r['file'])
        for k, v in M['references'].items():
            self.assertEqual(sha(R / v['file']), v['sha256'], k)
        for k, h in M['reutilise_de_zrv2'].items():
            self.assertEqual(sha(R / 'source/zone_reveil_prairie_horizon_v2/bruts' / k), h, k)
            self.assertEqual(sha(B.BRUTS / k), h, k)
        g = {x['file']: x for x in M['generation']}
        for f in ('terre_jour', 'ciel_mer_jour', 'recifs_roches', 'recifs_coraux', 'ambiance_aube', 'ambiance_crepuscule', 'ambiance_nuit'):
            self.assertIn(f'bruts/{f}.png', g, f); self.assertGreater(len(g[f'bruts/{f}.png']['prompt']), 100, f)
        for f in ('aube', 'crepuscule', 'nuit'):
            self.assertIn('EXACTLY the same', g[f'bruts/ambiance_{f}.png']['prompt'])
            self.assertEqual(g[f'bruts/ambiance_{f}.png']['images'][0], 'bruts/decor_jour_pour_ambiances.png')
        self.assertEqual(g['bruts/decor_jour_pour_ambiances.png']['essais'], 0)             # entrée calculée, pas une génération
        self.assertFalse(M['art_approved']); self.assertFalse(M['runtime_tested'])
        for amb in ('aube', 'crepuscule', 'nuit'):                                          # retouches alignées au pixel avec le décor de jour
            self.assertEqual(Image.open(B.BRUTS / f'ambiance_{amb}.png').size, (1195, 896))

    def test_decor_jour_pour_ambiances_reproduit(self):
        """Le décor envoyé au générateur se recalcule exactement, sauf les 7 373 pixels des roches de récifs (recolorées à l'époque)."""
        c, _ = ctx()
        L = B.static_layers('jour', c)
        comp = B.compose(L, B.ORDER_STATIC)[..., :3]
        have = np.array(Image.open(B.BRUTS / 'decor_jour_pour_ambiances.png').convert('RGB')).astype(int)
        self.assertEqual(have.shape, (900, 1200, 3))
        ys = ((np.arange(H) + 0.5) * 900 / H).astype(int); xs = ((np.arange(W) + 0.5) * 1200 / W).astype(int)
        diff = (have[ys][:, xs] != comp).any(2)
        self.assertTrue(((~diff) | c['RA']['rock_mask']).all())                         # aucune différence hors des roches de récifs
        self.assertLess(diff.sum(), 0.02 * W * H)
        want = np.array(Image.fromarray(comp).resize((1200, 900), Image.NEAREST)).astype(int)
        big = np.array(Image.fromarray((c['RA']['rock_mask'] * 255).astype('uint8')).resize((1200, 900), Image.NEAREST)) > 0
        self.assertTrue(((want == have).all(2) | big).all())                            # idem à l'échelle du fichier (1200 x 900)

    def test_exports_reproduits(self):
        """make_all() redonne exactement chaque image exportée (toutes les phases de tous les calques des quatre ambiances)."""
        c, sh = ctx()
        for amb in AMBS:
            L, inf = B.make_all(c, only=amb, shared=sh)
            self.assertEqual([n for n in B.ORDER if n in L], list(LAYERS[amb]), amb)
            for nom, (fr, tk) in L.items():
                self.assertEqual((len(fr), tk if len(fr) > 1 else 60), (LAYERS[amb][nom]['phases'], LAYERS[amb][nom]['ticks']), (amb, nom))
                for t, f in enumerate(fr):
                    self.assertTrue((f == frame(amb, nom, t)).all(), (amb, nom, t))
            del L

    def test_multicalque_grille_et_alpha(self):
        self.assertEqual((W, H, YH), (768, 576, 153)); self.assertEqual((W % 8, H % 8), (0, 0))
        counts = {a: len(LAYERS[a]) for a in AMBS}
        self.assertEqual(counts, {'jour': 21, 'aube': 24, 'crepuscule': 25, 'nuit': 26})
        for amb in AMBS:
            names = list(LAYERS[amb]); idx = [LAYERS[amb][n]['index'] for n in names]
            self.assertEqual(idx, [B.ORDER.index(n) for n in names]); self.assertEqual(idx, sorted(idx))
            for nom in names:
                for t in sorted({0, LAYERS[amb][nom]['phases'] - 1}):
                    a = frame(amb, nom, t)
                    self.assertEqual(a.shape, (H, W, 4)); self.assertTrue(set(np.unique(a[..., 3])) <= {0, 255}, (amb, nom))
                    if nom != 'etoile_filante' or t == 12:
                        self.assertTrue((a[..., 3] > 0).any(), (amb, nom, t))
        for must in ('ciel', 'mer', 'astre', 'nuages', 'recifs_coraux', 'recifs', 'sable', 'palmes', 'troncs', 'herbes', 'mares', 'rochers'):
            for amb in AMBS:
                self.assertIn(must, LAYERS[amb])

    def test_ciel_mer_et_horizon(self):
        for amb in AMBS:
            ciel, mer = frame(amb, 'ciel')[..., 3] > 0, frame(amb, 'mer')[..., 3] > 0
            self.assertTrue(ciel[:YH].all() and not ciel[YH:].any(), amb)
            self.assertTrue(mer[YH:].all() and not mer[:YH].any(), amb)               # calques complets, prolongés sous la terre
        sky, sea = frame('jour', 'ciel'), frame('jour', 'mer')
        self.assertGreater(lum(sky[YH - 1, W // 2, :3]), lum(sea[YH, W // 2, :3]) + 40)   # horizon : ciel pâle au-dessus, mer sombre dessous
        self.assertTrue(SEA[YH:, W // 2].any()); self.assertFalse(SEA[:YH].any())

    def test_partition_de_la_terre(self):
        c, _ = ctx(); land, cls, L = c['land'], c['cls'], c['Lday']
        cov = np.zeros((H, W), bool)
        for n in ('sable', 'rochers', 'mares', 'coquillages', 'bois_flotte', 'troncs', 'palmes', 'herbes'):
            cov |= L[n][..., 3] == 255
        la = land[..., 3] == 255
        self.assertTrue((cov | ~la).all())                                              # tout pixel de terre est dans un calque
        base = (L['sable'][..., 3] == 255) | (L['rochers'][..., 3] == 255)
        dsea = nd.distance_transform_edt(la)                                            # distance à la mer
        for n in ('palmes', 'herbes', 'mares', 'coquillages', 'bois_flotte'):          # rien ne se voit à travers quand ça bouge (sauf près de l'eau : le ciel et la mer sont complets)
            m = (L[n][..., 3] == 255) & la & (dsea > 20)
            self.assertTrue(base[m].all(), n)
        day = B.compose(L, ['sable', 'mares', 'rochers', 'coquillages', 'bois_flotte', 'troncs', 'palmes', 'herbes'])
        ok = la & (cls != B.CL['MARE'])
        self.assertGreater((day[..., :3][ok] == land[..., :3][ok]).all(1).mean(), 0.999)   # les calques recomposent la terre du brut
        for n in B.CL:
            self.assertGreater((cls == B.CL[n]).sum(), 300, n)

    def test_recifs_et_coraux(self):
        r, c_ = M['recifs']['roches'], M['recifs']['coraux']
        self.assertEqual((len(r), len(c_)), (9, 13))                                    # 7 sprites de roches (certains posés deux fois), 12 de corail (un posé deux fois)
        self.assertEqual(len({x['sprite'] for x in r}), 7); self.assertEqual(len({x['sprite'] for x in c_}), 12)
        for amb in AMBS:
            rec, cor = frame(amb, 'recifs')[..., 3] > 0, frame(amb, 'recifs_coraux')[..., 3] > 0
            self.assertFalse((rec & ~SEA).any(), amb); self.assertFalse((cor & ~SEA).any(), amb)   # dans l'eau, jamais sur la terre
            self.assertGreater(rec.sum(), 3000); self.assertGreater(cor.sum(), 5000)
            self.assertLess(LAYERS[amb]['recifs_coraux']['index'], LAYERS[amb]['recifs']['index'])   # coraux sous les roches
            self.assertLess(LAYERS[amb]['mer']['index'], LAYERS[amb]['recifs_coraux']['index'])
        lab, n = nd.label(frame('jour', 'recifs')[..., 3] > 0, structure=np.ones((3, 3)))
        self.assertGreaterEqual(n, 7)
        c, _ = ctx(); cj, cn = frame('jour', 'recifs_coraux'), frame('nuit', 'recifs_coraux'); m = c['RA']['coral_mask']
        self.assertLess(lum(cn[m][:, :3]).mean(), 0.9 * lum(cj[m][:, :3]).mean())      # les coraux (sprites) s'assombrissent la nuit
        rj = frame('jour', 'recifs'); rn = frame('nuit', 'recifs'); mm = rj[..., 3] > 0
        self.assertTrue(((rj[mm][:, :3].astype(int) - rn[mm][:, :3]).std(0) > 8).all())  # les roches changent de lumière
        self.assertTrue((rj[..., 3] == rn[..., 3]).all())                               # mais pas de forme

    def test_etoiles_aux_quatre_moments(self):
        c, _ = ctx(); land = c['land'][..., 3] == 255
        n_fix = {a: int((frame(a, 'etoiles_fixes')[..., 3] > 0).sum()) if 'etoiles_fixes' in LAYERS[a] else 0 for a in AMBS}
        n_tw = {a: M['mesures'][a]['etoiles']['scintillantes'] for a in AMBS}
        self.assertEqual(n_fix, {a: M['mesures'][a]['etoiles']['fixes'] for a in AMBS})
        self.assertEqual(n_fix, {'jour': 0, 'aube': 46, 'crepuscule': 110, 'nuit': 440}); self.assertEqual(n_tw, {'jour': 14, 'aube': 16, 'crepuscule': 34, 'nuit': 96})
        tot = [n_fix[a] + n_tw[a] for a in AMBS]; self.assertEqual(tot, sorted(tot))     # plus d'étoiles à mesure que le ciel s'assombrit
        for amb in AMBS:
            sky = frame(amb, 'ciel')[..., :3].astype(float); ast = frame(amb, 'astre')[..., 3] > 0
            allpx = np.zeros((H, W), bool)
            fr = frames(amb, 'etoiles'); self.assertEqual(len(fr), B.STAR_PHASES)
            for f in fr:
                allpx |= f[..., 3] > 0
            if n_fix[amb]:
                allpx |= frame(amb, 'etoiles_fixes')[..., 3] > 0
            ys, xs = np.nonzero(allpx)
            self.assertTrue((ys < YH - 3).all(), amb); self.assertFalse(land[ys, xs].any(), amb)
            self.assertFalse((nd.binary_dilation(ast, iterations=3)[ys, xs]).any(), amb)
            df = np.abs(frame(amb, 'etoiles')[..., :3].astype(float) - sky)
            on = frame(amb, 'etoiles')[..., 3] > 0
        contr = {}
        for amb in AMBS:
            sky = frame(amb, 'ciel')[..., :3].astype(float)
            tw = np.zeros((H, W), bool)
            for f in frames(amb, 'etoiles'):
                tw |= f[..., 3] > 0
            best = max(np.abs(f[..., :3].astype(float) - sky)[f[..., 3] > 0].mean() for f in frames(amb, 'etoiles') if (f[..., 3] > 0).any())
            contr[amb] = best
        self.assertLess(contr['jour'], contr['aube']); self.assertLess(contr['aube'], contr['nuit'])
        # états : sur 24 phases, chaque étoile est pleine 8 phases, cœur 4, éteinte 12
        for off in range(B.STAR_PHASES):
            st = [B.star_state(off, t) for t in range(B.STAR_PHASES)]
            self.assertEqual((st.count('plein'), st.count('coeur'), st.count('eteint')), (8, 4, 12))
        self.assertEqual(LAYERS['nuit']['etoiles']['ticks'], 5)

    def test_voie_lactee_et_etoile_filante(self):
        self.assertNotIn('voie_lactee', LAYERS['jour'])
        cnt = {a: int((frame(a, 'voie_lactee')[..., 3] > 0).sum()) for a in ('aube', 'crepuscule', 'nuit')}
        self.assertLess(cnt['aube'], cnt['crepuscule']); self.assertLess(cnt['crepuscule'], cnt['nuit']); self.assertGreater(cnt['nuit'], 1500)
        ys, xs = np.nonzero(frame('nuit', 'voie_lactee')[..., 3] > 0)
        self.assertLess(np.corrcoef(xs, ys)[0, 1], -0.4)                                # bande diagonale : monte vers la droite
        self.assertTrue((ys < YH - 3).all())
        self.assertNotIn('etoile_filante', LAYERS['jour']); self.assertNotIn('etoile_filante', LAYERS['aube'])
        for amb in ('crepuscule', 'nuit'):
            fr = frames(amb, 'etoile_filante'); self.assertEqual(len(fr), B.FILANTE_PHASES)
            act = [t for t, f in enumerate(fr) if (f[..., 3] > 0).any()]
            self.assertEqual(act, list(range(10, 22)))                                  # douze images de passage, puis le ciel reste vide
            heads = [np.nonzero(fr[t][..., 3] > 0)[1].max() for t in act]
            self.assertEqual(heads, sorted(heads)); self.assertGreater(heads[-1] - heads[0], 60)
            for t in act:
                self.assertTrue((np.nonzero(fr[t][..., 3] > 0)[0] < YH - 4).all())

    def test_astres_et_reflets(self):
        for amb in AMBS:
            A = B.ASTRE[amb]; a = frame(amb, 'astre'); m = a[..., 3] > 0
            ys, xs = np.nonzero(m); self.assertTrue((ys < YH).all(), amb)
            cx, cy = A['c']; disc = ((np.arange(W)[None, :] - cx) ** 2 + (np.arange(H)[:, None] - cy) ** 2) <= (A['d'] / 2 + 1) ** 2
            solid = m & disc; self.assertGreater(solid.sum(), 0.5 * np.pi * (A['d'] / 2) ** 2 * (0.5 if amb in ('aube', 'crepuscule') else 0.9))
        for amb in ('aube', 'crepuscule', 'nuit'):
            fr = frames(amb, 'reflet'); self.assertEqual(len(fr), 12)
            xs = np.concatenate([np.nonzero(f[..., 3] > 0)[1] for f in fr]); ax = B.ASTRE[amb]['c'][0]
            self.assertLess(abs(np.median(xs) - ax), 8)                                 # le reflet est sous l'astre
            ys = np.concatenate([np.nonzero(f[..., 3] > 0)[0] for f in fr]); self.assertTrue(((ys >= YH) & (ys <= YH + B.REFLET_SPAN + 2)).all())
            self.assertFalse(any(((f[..., 3] > 0) & ~SEA).any() for f in fr))
            self.assertGreater(len({f.tobytes() for f in fr}), 8)
        self.assertNotIn('reflet', LAYERS['jour'])
        c, sh = ctx(); sea = c['sea_vis']
        L, _ = B.make_all(c, only='nuit', shared=sh)
        dashes, _ = B.reflet_dashes(sh['refl_sheet'], B.REFLET_COL['nuit'])
        f0, f12 = B.reflet_frames_zpr(dashes, 470, sea, tvals=[0, 12])
        self.assertTrue((f0 == f12).all())                                              # boucle exacte

    def test_houle_en_arcs_boucle_exacte(self):
        c, sh = ctx(); S_ = B.static_layers('jour', c); mer = S_['mer'][..., :3].astype(int)
        f0, f12 = B.houle_frames(mer, c['sea_vis'], sh['dist_land'], sh['ys'], 'jour', tvals=[0, 12])
        self.assertTrue((f0 == f12).all())                                              # la 13e image est la 1re
        fr = frames('jour', 'houle'); self.assertEqual((len(fr), LAYERS['jour']['houle']['ticks']), (12, 10))
        self.assertTrue(all((f[..., 3] > 0).sum() > 800 for f in fr)); self.assertEqual(len({f.tobytes() for f in fr}), 12)
        for f in fr:
            self.assertFalse(((f[..., 3] > 0) & ~SEA).any())
        # les crêtes descendent vers le rivage : le centre de gravité vertical monte d'un cran à l'autre (une crête avance de 1/7 en 12 crans)
        cy = [np.nonzero(f[..., 3] > 0)[0].mean() for f in fr]
        self.assertGreater(max(cy) - min(cy), 3)
        # arcs : au centre de la baie les crêtes proches du rivage sont plus basses qu'aux flancs
        ys = sh['ys']; self.assertGreater(ys[W // 2], ys[200] + 40)
        # loi de profondeur : y = YH + (ys - YH) u^1,7
        u = np.array([(k + 0) / B.HOULE_K for k in range(1, B.HOULE_K)]); yy = YH + (ys[W // 2] - YH) * u ** 1.7
        self.assertTrue((np.diff(yy) > 0).all()); self.assertTrue((np.diff(np.diff(yy)) > 0).all())   # intervalles qui grandissent vers le rivage

    def test_scintillement_horizon(self):
        for amb in AMBS:
            fr = frames(amb, 'scintillement'); self.assertEqual((len(fr), LAYERS[amb]['scintillement']['ticks']), (B.GLINT_STEPS, B.GLINT_TICKS))
            for f in fr:
                ys, xs = np.nonzero(f[..., 3] > 0); self.assertTrue(((ys >= YH) & (ys < YH + 40)).all()); self.assertTrue(SEA[ys, xs].all())
            n = [int((f[..., 3] > 0).sum()) for f in fr]; self.assertGreater(max(n), min(n))
        self.assertEqual(sum(B.GLINT_LEVELS) % 1, 0)

    def test_nuages_defilent_boucle_fermee(self):
        N = M['mesures']['nuages']
        self.assertEqual((N['periode_px'], N['pas_px'], N['phases'], N['frame_length_ticks']), (768, 2, 384, 16))
        self.assertEqual(N['phases'] * N['pas_px'], N['periode_px']); self.assertEqual(N['rangees_cachees_sous_horizon'], 22)
        h = N['hauteur_px']
        for amb in AMBS:
            f0 = frame(amb, 'nuages', 0); a0 = f0[..., 3] > 0
            rows = np.nonzero(a0.any(1))[0]; self.assertGreaterEqual(rows.min(), YH - h); self.assertLess(rows.max(), YH)   # base cachée derrière l'horizon
            self.assertFalse(((a0) & LAND).any(), amb)
            for t in (1, 100, 383):
                ft = frame(amb, 'nuages', t)
                want = np.roll(f0, 2 * t, axis=1); free = ~LAND[None][0]
                got = ft[YH - h:YH]; exp = want[YH - h:YH]; ok = free[YH - h:YH] & ~np.roll(LAND, 2 * t, axis=1)[YH - h:YH]
                self.assertTrue((got[ok] == exp[ok]).all(), (amb, t))                   # la bande glisse de 2 px par cran (hors terre)
        strips = {a: B.cloud_ramp(B.cloud_strip({k: B.rgb(B.BRUTS / k) for k, _, _ in B.CLOUD_BANKS})[0], a, frame(a, 'ciel')[..., :3].astype(int)) for a in ('jour', 'nuit')}
        self.assertEqual(strips['jour'].shape[1], 768)
        self.assertLess(lum(strips['nuit'][..., :3][strips['nuit'][..., 3] > 0]).mean(), 0.5 * lum(strips['jour'][..., :3][strips['jour'][..., 3] > 0]).mean())

    def test_recifs_ecume_et_lagon_boucle_exacte(self):
        c, sh = ctx(); RA = c['RA']; S_ = B.static_layers('nuit', c); mer = S_['mer'][..., :3].astype(int)
        a0, a12 = B.ecume_recifs(RA['rock_masks'], c['sea_vis'], mer, 'nuit', tvals=[0, 12]); self.assertTrue((a0 == a12).all())
        b0, b12 = B.caustiques(mer, c['sea_vis'], sh['dist_sand'], 'nuit', tvals=[0, 12]); self.assertTrue((b0 == b12).all())
        d0, d12 = B.lueur_nuit(RA['coral_masks'], RA['coral'], c['sea_vis'], sh['dist_land'], tvals=[0, 12]); self.assertTrue((d0 == d12).all())
        for amb in AMBS:
            for nom, n in (('recifs_ecume', 12), ('lagon_reflets', 12)):
                fr = frames(amb, nom); self.assertEqual(len(fr), n); self.assertGreater(len({f.tobytes() for f in fr}), 6)
                for f in fr:
                    self.assertFalse(((f[..., 3] > 0) & ~SEA).any(), (amb, nom))
            # l'écume reste à 1..5 px des récifs, jamais dessus
            rec = frame(amb, 'recifs')[..., 3] > 0; d = nd.distance_transform_edt(~rec)
            for f in frames(amb, 'recifs_ecume'):
                dd = d[f[..., 3] > 0]; self.assertGreaterEqual(dd.min(), 1); self.assertLessEqual(dd.max(), 5.6)
        self.assertNotIn('lueur', LAYERS['jour']); self.assertIn('lueur', LAYERS['nuit'])
        lu = frames('nuit', 'lueur'); self.assertEqual(len(lu), 12); self.assertGreater(len({f.tobytes() for f in lu}), 8)

    def test_maree_sur_la_plage(self):
        n = [LAYERS[a]['ecume_rivage']['phases'] for a in AMBS]; self.assertEqual(n, [18] * 4)
        self.assertEqual({LAYERS[a]['ecume_rivage']['ticks'] for a in AMBS}, {8})
        c, sh = ctx(); sand = c['cls'] == B.CL['SABLE']; dsea = nd.distance_transform_edt(~SEA)
        for amb in AMBS:
            fr = frames(amb, 'ecume_rivage'); cnt = np.array([(f[..., 3] > 0).sum() for f in fr])
            self.assertTrue((nd.binary_dilation(sand, iterations=0)[np.nonzero(np.any([f[..., 3] > 0 for f in fr], 0))]).all(), amb)   # seulement sur le sable
            ys, xs = np.nonzero(np.any([f[..., 3] > 0 for f in fr], 0)); self.assertLessEqual(dsea[ys, xs].max(), 7 + 8 + 1)
            self.assertGreater(len({f.tobytes() for f in fr}), 14)
            self.assertGreater(cnt.max(), 1.15 * cnt.min())                              # le front avance puis recule
        mer = B.static_layers('jour', c)['mer'][..., :3].astype(int); sd = B.static_layers('jour', c)['sable'][..., :3]
        f0, f18 = B.maree(c['cls'], c['sea_vis'], sd, mer, 'jour', tvals=[0, 18]); self.assertTrue((f0 == f18).all())

    def test_vegetation_palmes_et_herbes(self):
        c, _ = ctx(); S_ = B.static_layers('jour', c)
        for nom, amp, n in (('palmes', 2, 12), ('herbes', 2, 8)):
            fr = frames('jour', nom); self.assertEqual(len(fr), n); st = S_[nom][..., 3] > 0
            self.assertGreater(len({f.tobytes() for f in fr}), n - 3)
            for f in fr:
                m = f[..., 3] > 0; self.assertLessEqual(abs(int(m.sum()) - int(st.sum())), 0.01 * st.sum(), nom)   # le cisaillement garde les pixels (à 1 % près : deux couronnes voisines peuvent se toucher)
                for y in np.nonzero(st.any(1))[0]:
                    sx = np.nonzero(st[y])[0]; fx = np.nonzero(m[y])[0]
                    self.assertLessEqual(abs(fx.mean() - sx.mean()), amp + 0.01, (nom, y))
        self.assertEqual(LAYERS['jour']['troncs']['phases'], 1)                           # les troncs ne bougent pas
        # sommet de la couronne : amplitude maximale ; pied : nulle
        st = S_['palmes'][..., 3] > 0; ys = np.nonzero(st.any(1))[0]; top, bot = ys.min(), ys.max()
        fr = frames('jour', 'palmes'); sh_top = max(abs(np.nonzero(f[top])[0].mean() - np.nonzero(st[top])[0].mean()) for f in [g[..., 3] > 0 for g in fr])
        self.assertGreater(sh_top, 0.5)
        zero = max(abs(np.nonzero(f[bot])[0].mean() - np.nonzero(st[bot])[0].mean()) for f in [g[..., 3] > 0 for g in fr])
        self.assertLess(zero, 0.01)
        a0, a12 = B.sway(S_['palmes'], 1, 2.0, 12, lambda i, x0, y0: (B.hsh(i, 3) % 100) / 100, tvals=[0, 12]); self.assertTrue((a0 == a12).all())

    def test_couleurs_des_ambiances(self):
        sky = {a: frame(a, 'ciel')[:YH, :, :3].astype(float) for a in AMBS}; sea = {a: frame(a, 'mer')[YH:, :, :3].astype(float) for a in AMBS}
        self.assertLess(lum(sky['nuit']).mean(), 0.35 * lum(sky['jour']).mean()); self.assertLess(lum(sky['nuit']).mean(), lum(sky['crepuscule']).mean())
        self.assertLess(lum(sea['nuit']).mean(), 0.5 * lum(sea['jour']).mean())
        hz = {a: sky[a][YH - 4, W // 2] for a in AMBS}
        self.assertGreater(hz['crepuscule'][0], hz['crepuscule'][2] + 60)                  # horizon du crépuscule : orange
        self.assertGreater(hz['aube'][0], hz['aube'][2] + 10)                              # horizon de l'aube : pêche
        self.assertGreater(sky['nuit'][5, W // 2][2], sky['nuit'][5, W // 2][0] + 20)      # haut de la nuit : bleu nuit
        sand = {a: frame(a, 'sable')[..., :3][frame(a, 'sable')[..., 3] > 0].astype(float) for a in AMBS}
        self.assertLess(lum(sand['nuit']).mean(), lum(sand['jour']).mean()); self.assertGreater(sand['jour'][:, 0].mean(), sand['jour'][:, 2].mean() + 40)
        self.assertGreater(sand['nuit'][:, 2].mean(), sand['nuit'][:, 0].mean())            # sable bleuté au clair de lune
        pal = {a: frame(a, 'palmes')[..., :3][frame(a, 'palmes')[..., 3] > 0].astype(float) for a in AMBS}
        self.assertLess(lum(pal['crepuscule']).mean(), 0.7 * lum(pal['jour']).mean())      # palmes en silhouette au crépuscule

    def test_access_et_collisions(self):
        a = M['access']; self.assertTrue(a['path_found_16x16'])
        self.assertEqual({k: tuple(v) for k, v in a['markers_px'].items()}, {'plage': (376, 392), 'entrance': (376, 552)})
        walkc = WALK.reshape(H // 8, 8, W // 8, 8).mean((1, 3))
        for amb in AMBS:
            doc = json.loads((S / f"Data/Ground/{B.ASSET[amb]}.rsground").read_text(encoding='utf-8-sig'))
            blocked = np.array([[c['Tags'] for c in col] for col in doc['Object']['obstacles']]).T.astype(bool)
            self.assertEqual(blocked.shape, (H // 8, W // 8)); self.assertEqual(int(blocked.sum()), a['blocked_cells'])
            cells = SEA.reshape(H // 8, 8, W // 8, 8).mean((1, 3)) > 0.5
            self.assertTrue(blocked[cells].all()); self.assertTrue(blocked[:YH // 8].all())           # mer et ciel bloqués
            self.assertFalse(blocked[walkc == 1].any())                                               # jamais bloquée si entièrement praticable
            mk = {m['EntName']: m for m in doc['Object']['Entities'][0]['Markers']}
            self.assertEqual(set(mk), {'plage', 'entrance'})
            for n, p in a['markers_px'].items():
                self.assertEqual([mk[n]['Collider']['X'], mk[n]['Collider']['Y']], p)
                self.assertFalse(blocked[p[1] // 8:p[1] // 8 + 2, p[0] // 8:p[0] // 8 + 2].any(), n)
        c, _ = ctx()
        for k in ('ROCHE', 'TRONC', 'BOIS'):                                                         # roches, troncs, bois flotté : bloqués
            m = (c['cls'] == B.CL[k]).reshape(H // 8, 8, W // 8, 8).mean((1, 3)) > 0.5
            self.assertTrue(blocked[m].all(), k)
        for k in ('SABLE', 'MARE', 'HERBE', 'COQUILLAGE'):                                           # sable, mares, herbes, coquillages : praticables
            m = (c['cls'] == B.CL[k]).reshape(H // 8, 8, W // 8, 8).mean((1, 3)) > 0.9
            self.assertFalse(blocked[m].any(), k)
        esn1 = B.loadmod('esn1', R / 'source/entree_sud_nord_generee_v1/build.py')
        reach, _ = esn1.reachable(blocked, (552 // 8, 376 // 8), (392 // 8, 376 // 8)); self.assertTrue(reach)

    def test_ora_et_scenes(self):
        for amb in AMBS:
            with zipfile.ZipFile(O / f'{B.PFX}_plage_recifs_{amb}_calques.ora') as z:
                merged = np.array(Image.open(io.BytesIO(z.read('mergedimage.png'))).convert('RGBA'))
                self.assertEqual(sum(1 for n in z.namelist() if n.startswith('data/layer')), len(LAYERS[amb]))
                self.assertEqual(z.namelist()[0], 'mimetype')
            comp = Image.new('RGBA', (W, H))
            for nom in LAYERS[amb]:
                comp.alpha_composite(Image.fromarray(frame(amb, nom, 0)))
            self.assertTrue((np.array(comp) == merged).all(), amb)
            self.assertTrue((load(O / f'review/{B.PFX}_{amb}_scene_t000.png') == merged).all(), amb)
        q = load(O / f'review/{B.PFX}_quatre_ambiances_t000.png'); self.assertEqual(q.shape[:2], (2 * H, 2 * W))

    def test_prefixe_et_namespace_uniques(self):
        for p in (R / 'source').glob('*/build*.py'):
            if p.parent != HERE:
                s = p.read_text(errors='ignore')
                self.assertNotIn("PFX = 'ZPR1'", s, p); self.assertNotIn("'zone_plage_recifs_etoiles_v1'", s, p)
        names = [p.name for p in (O / 'calques').rglob('*.png')] + [p.name for p in (O / 'animation').rglob('*.png')]
        self.assertEqual(len(names), len(set(names))); self.assertTrue(all(n.startswith('ZPR1') for n in names))
        banks = set(M['pmdo']['tiles_per_bank']); self.assertEqual(len(banks), sum(len(LAYERS[a]) for a in AMBS))
        self.assertTrue(all(b.startswith('ZPR1') for b in banks)); self.assertEqual(len(set(M['pmdo']['assets'].values())), 4)

    def test_ground_roundtrip(self):
        nr = loadmod('native_reader', R / 'source/cote_v5_expeditions/audit_references.py')
        banks = {p.stem: nr.tiles(p)[1] for p in (S / 'Content/Tile').glob('*.tile')}
        self.assertEqual(set(banks), set(M['pmdo']['tiles_per_bank']))
        tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
        self.assertEqual(set(tools.read_index(S / 'Content/Tile/index.idx')), set(banks))
        cache = {}

        def tile(sheet, x, y):
            k = (sheet, x, y)
            if k not in cache:
                cache[k] = np.array(nr.straight(banks[sheet][x, y]))
            return cache[k]
        for amb in AMBS:
            doc = json.loads((S / f"Data/Ground/{B.ASSET[amb]}.rsground").read_text(encoding='utf-8-sig')); o = doc['Object']
            self.assertEqual(doc['Version'], '0.8.12.0'); self.assertEqual(len(o['Layers']), len(LAYERS[amb]) + 1)
            self.assertEqual(o['Layers'][-1]['Layer'], 4); self.assertEqual(o['AssetName'], B.ASSET[amb])
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
                                out[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = tile(f['Sheet'], f['TexLoc']['X'], f['TexLoc']['Y'])
                    self.assertTrue((out == want).all(), (amb, nom, t))


if __name__ == '__main__':
    unittest.main()
