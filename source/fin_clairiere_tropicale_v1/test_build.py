"""Image/manifest/collision checks for FCT1. They do not constitute a PMDO runtime or art-approval test."""
from pathlib import Path
import hashlib, json, re, unittest, zipfile
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'renders/fin_clairiere_tropicale_v1'
M=json.loads((OUT/'manifest.json').read_text())
W,H=M['size_px']


def load(p):return np.asarray(Image.open(p).convert('RGBA'))

class FCT1Build(unittest.TestCase):
    def test_reference_and_raw_provenance(self):
        ref=M['reference'];p=ROOT/ref['file']
        self.assertTrue(p.exists());self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),ref['sha256'])
        self.assertEqual(ref['related_entry'],'ETC1')
        self.assertEqual(len(M['raw_inputs']),3)
        for row in M['raw_inputs']:
            q=ROOT/row['file'];self.assertTrue(q.exists());self.assertEqual(hashlib.sha256(q.read_bytes()).hexdigest(),row['sha256'])
            with Image.open(q) as im:self.assertEqual(im.size,(1200,896))
        self.assertIn('rendu généré référencé',M['method'])
        self.assertFalse(M['pmdo']['runtime_tested']);self.assertFalse(M['art_approved'])

    def test_user_correction_no_off_biome_assets(self):
        names=[x['name'] for x in M['layers']]
        self.assertNotIn('fruit',names);self.assertNotIn('sanctuaire',names)
        prompt=M['generation'][0]['prompt'].lower()
        self.assertIn('aucun fruit',prompt);self.assertIn('cascade',prompt);self.assertIn('uniquement au sud',prompt);self.assertIn('ni eau derrière',prompt)
        self.assertNotIn('fruit doré',M['biome'])

    def test_size_names_binary_alpha_and_magenta_absent(self):
        self.assertEqual((W,H),(768,576));self.assertEqual((W%8,H%8),(0,0))
        files=[]
        for L in M['layers']:
            if L['phases']==1: files.append(OUT/L['file'])
            else: files += [OUT/L['file'].replace('fNN',f'f{i:02d}') for i in range(L['phases'])]
        self.assertEqual(len(files),sum(L['phases'] for L in M['layers']))
        for p in files:
            a=load(p);self.assertEqual(a.shape,(H,W,4),p.name)
            self.assertLessEqual(set(np.unique(a[...,3])),{0,255},p.name)
            px=a[a[...,3]>0,:3].astype(int)
            self.assertEqual(int(((px[:,0]-px[:,1]>60)&(px[:,2]-px[:,1]>60)).sum()),0,p.name)
        # Magenta witness is a source mask, not a rendered/exported texture.
        for p in files:
            a=load(p);px=a[a[...,3]>0,:3].astype(int)
            self.assertFalse(np.any((px[:,0]>220)&(px[:,1]<30)&(px[:,2]>220)))

    def test_ground_layers_and_loop(self):
        names=[x['name'] for x in M['layers']]
        self.assertEqual(names,['sol_complet','mer_base','herbe','sable','ombres','jungle','rochers','fleurs','canopee','mer','papillons'])
        self.assertEqual(M['scene_loop_ticks'],120)
        for n in ('mer','papillons'):
            q=M['animations']['mer' if n=='mer' else 'butterflies']
            self.assertEqual((q['phases'],q['ticks_per_phase']),(24,5))
        sea=np.asarray(Image.open(OUT/'masques/FCT1_masque_eau_export.png').convert('L'))>0
        yy,xx=np.mgrid[:H,:W]
        self.assertGreater(int(sea.sum()),1000)
        self.assertFalse(sea[yy < H*0.68].any(),'water mask must remain at the southern edge')
        # Cross-check each exported water-effect frame clips to the southern water region.
        L=next(x for x in M['layers'] if x['name']=='mer')
        srcdir=ROOT/'renders/entree_clairiere_tropicale_sud_nord_v1/animation/mer'
        for i in (0,6,12,18,23):
            a=load(OUT/L['file'].replace('fNN',f'f{i:02d}'))
            self.assertFalse((a[...,3]>0)[~sea].any())
            src=load(srcdir/f'ETC1_13_mer_f{i:02d}.png');expected=np.zeros_like(src);expected[514:]=src[514:];expected[~sea]=0
            self.assertTrue(np.array_equal(a,expected),'FCT1 sea frame must reuse ETC1 pixels without resampling')
        base=load(OUT/'calques/FCT1_01_mer_base.png');px=base[base[...,3]>0,:3]
        self.assertEqual({tuple(int(v) for v in c) for c in np.unique(px,axis=0)},{(15,95,199)})

    def test_material_fidelity_is_measured_and_bounded(self):
        fid=M['fidelity_rgb']
        self.assertEqual(set(fid),{'herbe','jungle','dalles'})
        for key in fid:
            self.assertLess(fid[key]['distance'],35,key)
        self.assertGreaterEqual(M['segmentation']['classes']['eau'],10000)
        self.assertGreater(M['segmentation']['classes']['fleurs'],1000)

    def test_access_and_native_pmdo_export(self):
        access=M['access'];self.assertEqual(set(access['markers']),{'entrance','boss','objectif'})
        self.assertTrue(all(v['ok'] for v in access['path_16x16'].values()))
        for p in access['markers'].values():self.assertEqual((p[0]%8,p[1]%8),(0,0))
        stage=ROOT/'.cache/fin_clairiere_tropicale_v1/fin_clairiere_tropicale'
        ground=json.loads((stage/f'Data/Ground/{M["pmdo"]["asset"]}.rsground').read_text())['Object']
        self.assertEqual(ground['TexSize'],1);self.assertEqual(len(ground['Layers']),len(M['layers'])+1)
        self.assertEqual(ground['Layers'][-1]['Layer'],4)
        self.assertTrue((stage/'Content/Tile/index.idx').exists())
        self.assertFalse(any('warp' in str(x).lower() for ent in ground['Entities'] for x in ent.get('Markers',[])))
        self.assertFalse(M['pmdo']['runtime_tested'])

    def test_preview_and_ora_open(self):
        self.assertTrue((OUT/'review/FCT1_scene_animee.webp').exists())
        self.assertTrue((OUT/'review/FCT1_collisions_marqueurs.png').exists())
        with zipfile.ZipFile(OUT/'FCT1_fin_clairiere_calques.ora') as z:
            self.assertIn('mergedimage.png',z.namelist());self.assertIn('stack.xml',z.namelist())
        self.assertTrue((OUT/'README.md').exists())

if __name__=='__main__':unittest.main()
