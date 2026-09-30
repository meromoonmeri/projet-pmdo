"""Tests dédiés — Entrée Mt. Blaze (EMB2, 4:3 vaste, magma visqueux).
.venv/bin/python -m unittest source.entree_mt_blaze_sud_nord_v2.test_build -v
"""
from pathlib import Path
import hashlib, importlib.util, io, json, unittest, zipfile
import numpy as np
from scipy import ndimage
from PIL import Image

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/entree_mt_blaze_sud_nord_v2'
S = R / '.cache/entree_mt_blaze_sud_nord_v2/entree_mt_blaze_sud_nord_v2'
M = json.loads((O / 'manifest.json').read_text()) if (O / 'manifest.json').exists() else {}
W, H = M.get('size_px', [768,576])
# layers are in manifest['layers'] but also check order
def load(p):
    return np.array(Image.open(p).convert('RGBA'))
def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def name_of(p):
    return Path(p).stem.split('_',2)[2].replace('_fNN','')

if M:
    ORDER = [name_of(L['file']) for L in M['layers']]
    PH = {name_of(L['file']): L['phases'] for L in M['layers']}
    TK = {name_of(L['file']): L['ticks'] for L in M['layers']}
    STACK = {}
    for L in M['layers']:
        nm = name_of(L['file'])
        if 'fNN' in L['file']:
            STACK[nm] = [load(O / L['file'].replace('fNN', f'f{t:02d}')) for t in range(L['phases'])]
        else:
            STACK[nm] = [load(O / L['file'])]
    MG = loadmod('magma_visqueux', R / 'source/magma_visqueux/magma.py')
    # patch palette to MTB for checking colors
    B = loadmod('emb2_build', HERE / 'build.py')
    PAL = {tuple(c) for c in B.MTB_PAL}
else:
    ORDER=[]; PH={}; TK={}; STACK={}; PAL=set()

MASK = {k: np.array(Image.open(O / f'masques/EMB2_masque_{k}.png'))>0 for k in ('water','profondeur','sable','ombres') } if (O/'masques').exists() else {}

def alpha(a):
    return a[...,3]==255
def colors(a):
    return {tuple(int(v) for v in c) for c in np.unique(a[alpha(a)][:, :3], axis=0)}

class Build(unittest.TestCase):
    def test_raw_hashes_and_reference(self):
        for r in M['raw_inputs']:
            self.assertEqual(hashlib.sha256((R / r['file']).read_bytes()).hexdigest(), r['sha256'])
        ref=M['reference_da']
        self.assertEqual(ref['file'],'Rescue_Team_-_Mt._Blaze_Entrance.png')
        self.assertEqual(hashlib.sha256((R / ref['file']).read_bytes()).hexdigest(), ref['sha256'])
        g=M['generation']
        self.assertEqual([x['file'] for x in g], ['decor.png','sol_complet.png'])
        self.assertTrue(all(x['images'] and len(x['prompt'])>100 for x in g))
        self.assertIn('Rescue_Team_-_Mt._Blaze_Entrance.png', g[0]['images'])
        self.assertFalse(M['art_approved']); self.assertFalse(M['pmdo']['runtime_tested'])

    def test_sizes_names_alpha_no_magenta(self):
        self.assertEqual(len(ORDER), len(set(ORDER)))
        self.assertTrue(all(Path(L['file']).name.startswith('EMB2_') for L in M['layers']))
        self.assertEqual((W,H,W%8,H%8),(768,576,0,0))
        for frames in STACK.values():
            for a in frames:
                self.assertEqual(a.shape[:2], (H,W))
                self.assertTrue(set(np.unique(a[...,3])) <= {0,255})
                v=a[alpha(a)].astype(int)
                # plus de magenta plat (lave segmentée)
                self.assertEqual(int(((v[:,0]-v[:,1]>60) & (v[:,2]-v[:,1]>60)).sum()),0)

    def test_multicalque_full_coverage_and_order(self):
        self.assertEqual(ORDER, ['lave','sol_complet','sable','ombres','berge','roche','piliers','profondeur','veines'])
        cover=np.zeros((H,W), bool)
        for frames in STACK.values():
            cover|=alpha(frames[0])
        self.assertTrue(cover.all())

    def test_lave_visqueuse_palette_cycling(self):
        fr=STACK['lave']
        self.assertEqual((PH['lave'], TK['lave']), (32,15))
        # couleur dans palette Mt Blaze
        for a in fr:
            self.assertTrue(colors(a) <= PAL)
        # mouvement : chaque phase change
        # visible = lava & ~land
        land=np.zeros((H,W), bool)
        for k in ('sable','ombres','berge','roche','piliers','profondeur'):
            if k in STACK:
                land|=alpha(STACK[k][0])
        vis = MASK.get('water', np.zeros((H,W),bool)) & ~land
        ch=[float((fr[t][vis] != fr[(t+1)%32][vis]).any(1).mean()) for t in range(32)]
        self.assertGreater(min(ch), 0.15)
        self.assertLess(max(ch)-min(ch), 0.12)

    def test_veines_palette_cycling(self):
        fr=STACK['veines']
        self.assertEqual((PH['veines'], TK['veines']), (32,15))
        self.assertTrue(sum((a[...,3]==255).sum() for a in fr) > 200)
        for a in fr:
            self.assertTrue(colors(a) <= PAL)
        # au moins 50% des pixels changent entre phases (palette cycling)
        m=alpha(fr[0])
        if m.any():
            diff = float((fr[0][m] != fr[16][m]).any(1).mean())
            self.assertGreater(diff, 0.3)

    def test_markers_and_paths(self):
        acc=M['access']; markers=acc['markers']
        self.assertEqual(set(markers), {'entrance','boss','objectif'})
        self.assertGreater(markers['entrance'][1], 500)
        self.assertLess(markers['objectif'][1], 250)
        self.assertTrue(acc['paths_16x16']['entrance->boss']['ok'])
        self.assertTrue(acc['paths_16x16']['entrance->objectif']['ok'])
        rs=json.loads((S / f'Data/Ground/{M["pmdo"]["asset"]}.rsground').read_text())['Object']
        names=[m['EntName'] for g in rs['Entities'] for m in g['Markers']]
        self.assertEqual(set(names), {'entrance','boss','objectif'})

    def test_ground_and_ora(self):
        self.assertTrue((S / f'Data/Ground/{M["pmdo"]["asset"]}.rsground').exists())
        self.assertTrue((O / f'EMB2_entree_mt_blaze_sud_nord_v2_calques.ora').exists())
        self.assertTrue((S / 'Mod.xml').exists())
        self.assertTrue((S / 'Content/Tile/index.idx').exists())
        # boucle fermée
        for k in ('lave','veines'):
            self.assertEqual(M['scene_loop_ticks'] % (PH[k]*TK[k]), 0)
        self.assertEqual(M['scene_loop_ticks'], 480)

if __name__=='__main__':
    unittest.main(verbosity=2)
