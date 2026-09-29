import importlib.util,json,unittest,zipfile
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'renders/fin_jardin_secret_v1';STAGE=ROOT/'.cache/fin_jardin_secret_v1/fin_jardin_secret';PFX='FGS1'
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class FinJardinSecretTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.m=mod('fgs_test_build',ROOT/'source/fin_jardin_secret_v1/build.py');cls.M=json.loads((OUT/'manifest.json').read_text())
 def test_new_reference_and_witness_alignment(self):
  raw=ROOT/'source/fin_jardin_secret_v1/bruts';a=np.asarray(Image.open(raw/'decor.png').convert('RGB'));t=np.asarray(Image.open(raw/'temoin_sans_objets.png').convert('RGB'))
  self.assertEqual(a.shape,(896,1200,3));self.assertEqual(t.shape,a.shape)
  self.assertEqual(self.M['reference']['file'],'secretgarden.png')
  self.assertEqual(self.M['registration']['ecart_decale_1px']>self.M['registration']['ecart_moyen'],True)
  self.assertGreater(self.M['segmentation']['fleurs'],10);self.assertGreater(self.M['segmentation']['rochers'],5);self.assertGreater(self.M['segmentation']['arbres'],5)
 def test_magenta_never_leaks_and_layers_are_4_3(self):
  for p in list((OUT/'calques').glob('*.png'))+list((OUT/'animation').rglob('*.png')):
   a=np.asarray(Image.open(p).convert('RGBA'));v=a[...,3]>0
   self.assertEqual(a.shape,(576,768,4),p.name)
   self.assertFalse(np.any(v&(a[...,0]>245)&(a[...,1]<10)&(a[...,2]>245)),p.name)
  self.assertGreater(self.M['access']['walkable_cells'],1000)
 def test_markers_and_two_cell_clear_paths(self):
  a=self.M['access'];p=a['markers'];self.assertEqual(set(p),{'entrance','boss','objectif'})
  self.assertEqual(p['entrance'][0],384);self.assertGreater(p['entrance'][1],450)
  self.assertEqual(p['boss'][0],384);self.assertLess(p['objectif'][1],300)
  self.assertTrue(all(v['ok'] for v in a['paths_16x16'].values()))
  o=json.loads((STAGE/f'Data/Ground/{self.m.ASSET}.rsground').read_text())['Object']
  names=[m['EntName'] for g in o['Entities'] for m in g['Markers']]
  self.assertEqual(set(names),{'entrance','boss','objectif'});self.assertEqual(o['TexSize'],1)
  self.assertEqual(o['Layers'][-1]['Name'],'14 Top vide')
 def test_beam_and_fireflies_use_reference_ramp_and_loop(self):
  for name in ('rayon','lucioles'):
   fs=sorted((OUT/'animation'/name).glob('*.png'));self.assertEqual(len(fs),24)
   arr=[np.asarray(Image.open(p).convert('RGBA')) for p in fs]
   self.assertGreaterEqual(len({a.tobytes() for a in arr}),5 if name=='rayon' else 20)
   self.assertTrue(all(a.shape==(576,768,4) for a in arr))
  pal={tuple(c) for c in self.M['animation']['rayon']['ramp_rgb']}
  for p in (OUT/'animation/rayon').glob('*.png'):
   a=np.asarray(Image.open(p).convert('RGBA'));colors={tuple(c) for c in a[a[...,3]>0,:3]}
   self.assertTrue(colors<=pal)
  self.assertEqual(self.M['animation']['loop_ticks'],120)
 def test_openraster_and_pmdo_bundle_inputs(self):
  with zipfile.ZipFile(OUT/'FGS1_fin_jardin_secret_calques.ora') as z:
   self.assertIn('stack.xml',z.namelist());self.assertEqual(Image.open(z.open('mergedimage.png')).size,(768,576))
  self.assertTrue((STAGE/'Mod.xml').exists());self.assertTrue((STAGE/'Content/Tile/index.idx').exists())
  self.assertGreater(sum(self.M['pmdo']['tiles_per_bank'].values()),0)
  self.assertFalse(self.M['pmdo']['runtime_tested'])
if __name__=='__main__':unittest.main(verbosity=2)
