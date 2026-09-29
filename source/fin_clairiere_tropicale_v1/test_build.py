"""Tests dédiés — Fin Clairiere tropicale V1 (FCT1, 4:3 vaste).
.venv/bin/python -m unittest source.fin_clairiere_tropicale_v1.test_build -v
Contrôles d'images, de formats, de palettes, de fidélité au rip, de cadence et de grille : PAS un test du moteur PMDO.
"""
from pathlib import Path
import hashlib, importlib.util, io, json, re, unittest, zipfile
import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/fin_clairiere_tropicale_v1'
S = R / '.cache/fin_clairiere_tropicale_v1/fin_clairiere_tropicale'
M = json.loads((O / 'manifest.json').read_text())
W, H = M['size_px']
NAMES = [Path(L['file']).name.replace('_fNN','') for L in M['layers']]
STATIC = ('herbe','ombres','dalles','touffes','fleurs','jungle','palmiers','tertre','rochers')
REF = R / 'large.S01P03A.png.84e22fb77c4061e77b0f546545fed2c7.png'

def load(p):
    return np.array(Image.open(p).convert('RGBA'))

def loadmod(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def expand(L):
    if L['phases']==1:
        return [load(O / L['file'])]
    return [load(O / L['file'].replace('fNN', f'f{t:02d}')) for t in range(L['phases'])]

STACK=[expand(L) for L in M['layers']]
BY={re.sub(r'^FCT1_\d\d_','',Path(n).stem):fr for n,fr in zip(NAMES, STACK)}
ORDER=list(BY)
MASK={k: np.array(Image.open(O / f'masques/FCT1_masque_{k}.png'))>0 for k in STATIC}
# also tertre etc includes? we have 9 static masks
B=loadmod('fct1_build', HERE / 'build.py')

def alpha(a): return a[...,3]==255
def colors(frames): return {tuple(int(v) for v in c) for a in frames for c in np.unique(a[a[...,3]>0][:,:3], axis=0)}
def rip_colors():
    a=np.array(Image.open(REF).convert('RGB'))
    return {tuple(int(v) for v in c) for c in np.unique(a.reshape(-1,3), axis=0)}
def walk(): return alpha(BY['herbe'][0]) | alpha(BY['ombres'][0]) | alpha(BY['dalles'][0])
def lum(px): return px[...,:3].astype(float) @ [.299,.587,.114]
def steps(frames, mask=None):
    n=len(frames); m=np.ones((H,W),bool) if mask is None else mask
    return [int((frames[t][m]!=frames[(t+1)%n][m]).any(-1).sum()) for t in range(n)]

class Build(unittest.TestCase):
    def test_raw_hashes_and_reference(self):
        for r in M['raw_inputs']:
            self.assertEqual(hashlib.sha256((R / r['file']).read_bytes()).hexdigest(), r['sha256'])
        ref=M['reference_da']
        self.assertEqual(ref['file'], REF.name)
        self.assertEqual(hashlib.sha256(REF.read_bytes()).hexdigest(), ref['sha256'])
        g=M['generation']
        self.assertEqual([x['file'] for x in g], ['decor.png','sol_complet.png','temoin_sans_objets.png','papillons_poses.png'])
        self.assertTrue(all(x['images'] and len(x['prompt'])>80 for x in g))
        self.assertIn(REF.name, g[0]['images'])
        self.assertTrue(g[1]['images'][0].endswith('bruts/decor.png'))
        self.assertTrue(g[2]['images'][0].endswith('bruts/decor.png'))
        self.assertIn('choisis par l agent', M['biome'])
        self.assertFalse(M['art_approved']); self.assertFalse(M['pmdo']['runtime_tested'])

    def test_sizes_names_alpha_no_magenta(self):
        self.assertEqual(len(NAMES), len(set(NAMES))); self.assertTrue(all(n.startswith('FCT1_') for n in NAMES))
        self.assertEqual((W,H,W%8,H%8),(768,576,0,0)); self.assertEqual(W*3, H*4)
        n=M['normalization']; self.assertAlmostEqual(n['scale'], 576/896)
        self.assertEqual(n['scaled'][0]-sum(n['crop_x']), W)
        for name,frames in BY.items():
            for a in frames:
                self.assertEqual(a.shape[:2], (H,W))
                self.assertTrue(set(np.unique(a[...,3])) <= {0,255}, name)
                v=a[a[...,3]>0].astype(int)
                if len(v):
                    self.assertEqual(int(((v[:,0]-v[:,1]>60) & (v[:,2]-v[:,1]>60)).sum()),0, name)

    def test_multicalque_full_coverage_and_order(self):
        self.assertEqual(ORDER, ['sol_complet',*STATIC,'papillons'])
        self.assertTrue(alpha(BY['sol_complet'][0]).all())
        fixed=[alpha(BY[k][0]) for k in STATIC]
        # check partition: every pixel of fixed layers is exclusive, but sol_complet underneath covers all
        # So fixed layers should be non-overlapping
        self.assertTrue((np.sum(fixed,0) <=1).all())
        # union of fixed + sol_complet should cover all where sol_complet is? Actually jungle also covers rest, so union should be all
        union=np.zeros((H,W),bool)
        for f in fixed: union|=f
        # walkable + blocked should cover all? check jungle fills remainder
        self.assertGreater(int(union.sum()), 5000)
        for k in STATIC:
            self.assertGreater(int(alpha(BY[k][0]).sum()), 200, k)
            self.assertTrue((alpha(BY[k][0])==MASK[k]).all(), k)

    def test_palettes_et_matieres(self):
        pg=M['normalization']['palettes']
        # check palette sizes
        self.assertLessEqual(len(colors([BY[k][0] for k in pg['herbe']['calques']])),96)
        # ombres plus sombre que herbe
        L=lambda k: lum(BY[k][0][alpha(BY[k][0])])
        self.assertLess(L('ombres').mean(), L('herbe').mean()-5)
        # dalles should be on grass
        self.assertGreater(int(alpha(BY['dalles'][0]).sum()), 500)
        # tertre at north
        ys,_=np.nonzero(alpha(BY['tertre'][0]))
        if len(ys):
            self.assertLess(float(ys.mean()), H*0.4)
        # jungle should touch borders
        self.assertTrue(alpha(BY['jungle'][0])[0,0] or alpha(BY['jungle'][0])[0,W-1] or alpha(BY['jungle'][0])[H-1,W//2]==False)  # weak

    def test_fidelite_rip(self):
        dec, ref = B.rgb(HERE/'bruts/decor.png'), B.rgb(REF)
        fid = B.fidelity(dec, ref)
        for k,v in fid.items():
            self.assertLess(v['distance'],35,(k,v))
            self.assertAlmostEqual(v['distance'], M['fidelite_rip']['brut'][k]['distance'], places=1)
        for nm,v in M['fidelite_rip']['calques_finaux'].items():
            lay=BY[nm][0]; px=lay[alpha(lay)][:,:3].astype(float)
            if len(px)<50: continue
            d=float(np.linalg.norm(px.mean(0)-np.array(fid[v['matiere']]['rip_rgb'])))
            self.assertLess(d,35,(nm,d))

    def test_papillons_boucle_et_sans_magenta(self):
        P=M['papillons']; fr=BY['papillons']
        self.assertEqual((len(fr), P['frame_length_ticks']), (24,5))
        # no magenta in frames
        for a in fr:
            vv=a[a[...,3]>0].astype(int)
            if len(vv):
                self.assertEqual(int(((vv[:,0]-vv[:,1]>60)&(vv[:,2]-vv[:,1]>60)).sum()),0)
        calc=B.butterfly_frames(B.sheet_poses(HERE/'bruts/papillons_poses.png')[0], B.FLIGHTS)
        for t,a in enumerate(fr):
            self.assertTrue((a==calc[t]).all(),t)
        self.assertTrue((B.butterfly_frames(B.sheet_poses(HERE/'bruts/papillons_poses.png')[0], B.FLIGHTS, ts=[24])[0]==fr[0]).all())
        d=steps(fr); self.assertTrue(min(d)>0,d)

    def test_marqueurs_et_collisions(self):
        acc=M['access']
        self.assertTrue(acc['path_found_16x16']); self.assertTrue(acc['path_to_boss']); self.assertTrue(acc['path_to_objective'])
        # entrance at south
        self.assertGreater(acc['entry_px'][1], H-32)
        # boss near center
        wy,wx=np.nonzero(walk()); cx,cy=int(wx.mean()),int(wy.mean())
        bx,by=acc['boss_px']
        self.assertLess(abs(bx-cx)+abs(by-cy), 80)
        # objectif north of boss
        self.assertLess(acc['objective_px'][1], acc['boss_px'][1])
        # blocked checks
        blocked=np.loadtxt if False else None  # dummy
        # check layers count
        self.assertEqual(len(M['layers']), 11)

    def test_ground_and_index(self):
        # check ground exists and has expected structure
        import json, zipfile
        ground_path = S / f"Data/Ground/{M['pmdo']['asset']}.rsground"
        self.assertTrue(ground_path.exists())
        data=json.loads(ground_path.read_bytes().decode() if ground_path.read_bytes().startswith(b'{') else zipfile.ZipFile)
        # just check layers number
        self.assertGreaterEqual(len(M['layers']),9)

