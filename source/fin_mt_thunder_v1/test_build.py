import importlib.util,json,unittest,zipfile
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'renders/fin_mt_thunder_v1'; STAGE=ROOT/'.cache/fin_mt_thunder_v1/fin_mt_thunder'; PFX='FTH1'
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class FinMtThunderTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.m=mod('fth_test_build',ROOT/'source/fin_mt_thunder_v1/build.py');cls.M=json.loads((OUT/'manifest.json').read_text())
 def test_sources_partition_and_magenta_never_exports(self):
  raw=ROOT/'source/fin_mt_thunder_v1/bruts';a=np.asarray(Image.open(raw/'decor.png').convert('RGB'));g=np.asarray(Image.open(raw/'objets_magenta.png').convert('RGB'))
  mag=(g[...,0]>180)&(g[...,1]<105)&(g[...,2]>180)&(g[...,0]-g[...,1]>80)&(g[...,2]-g[...,1]>80)
  self.assertGreater(int(mag.sum()),300000);self.assertEqual(a.shape,(896,1200,3))
  self.assertEqual(self.M['reference']['scene'],'source/references_54d3731/thunder.png')
  for p in list((OUT/'calques').glob('*.png'))+list((OUT/'animation').rglob('*.png')):
   x=np.asarray(Image.open(p).convert('RGBA'));v=x[...,3]>0
   self.assertEqual(x.shape,(576,768,4),p.name)
   self.assertFalse(np.any(v&(x[...,0]>245)&(x[...,1]<10)&(x[...,2]>245)),p.name)
  self.assertFalse(self.M['pmdo']['runtime_tested'])
 def test_surface_and_markers_accessible(self):
  A=self.M['access'];p=A['markers']
  self.assertEqual(set(p),{'entrance','boss','objectif'});self.assertEqual(p['entrance'][0],384)
  self.assertGreater(p['entrance'][1],400);self.assertLess(p['entrance'][1],500)
  self.assertEqual(p['boss'][0],384);self.assertLess(p['objectif'][1],220)
  for v in A['paths_16x16'].values():self.assertTrue(v['ok'])
  o=json.loads((STAGE/f'Data/Ground/{self.m.ASSET}.rsground').read_text())['Object']
  names=[x['EntName'] for e in o['Entities'] for x in e['Markers']]
  self.assertEqual(set(names),{'entrance','boss','objectif'});self.assertEqual(o['TexSize'],1)
  self.assertEqual(o['Layers'][-1]['Name'],'09 Top vide')
 def test_source_bolts_and_flash_pixels_exact(self):
  raw=np.asarray(Image.open(self.m.SHEET).convert('RGB'))
  bolts,flash,sw=self.m.EMT.rip_sheet(raw)
  for i,mask in bolts.items():
   pose=np.asarray(Image.open(OUT/f'poses/FTH1_eclair_{i}.png').convert('RGBA'))
   expected=np.zeros((*mask.shape,4),dtype=np.uint8);expected[mask]=(*sw['normal'][1],255)
   self.assertTrue(np.array_equal(pose,expected))
  p=np.asarray(Image.open(OUT/'poses/FTH1_flash.png').convert('RGBA'))
  expected=np.zeros((*flash.shape,4),dtype=np.uint8);expected[flash]=(*sw['normal'][0],255)
  self.assertTrue(np.array_equal(p,expected))
 def test_lightning_animation_has_48_phases_and_source_palette(self):
  for layer in ('eclairs','lueurs'):
   fs=sorted((OUT/'animation'/layer).glob('*.png'));self.assertEqual(len(fs),48)
   arrays=[np.asarray(Image.open(p).convert('RGBA')) for p in fs]
   self.assertGreaterEqual(len({a.tobytes() for a in arrays}),8)
   self.assertTrue(all(a.shape==(576,768,4) for a in arrays))
   active=[int((a[...,3]>0).sum()) for a in arrays]
   self.assertGreater(sum(v>0 for v in active),16);self.assertLess(sum(v>0 for v in active),48)
  self.assertEqual(self.M['animation']['ticks'],5);self.assertEqual(self.M['animation']['loop_ticks'],240)
 def test_openraster_native_project_and_stage(self):
  ora=OUT/'FTH1_fin_mt_thunder_calques.ora'
  with zipfile.ZipFile(ora) as z:
   self.assertIn('stack.xml',z.namelist());self.assertEqual(Image.open(z.open('mergedimage.png')).size,(768,576))
  self.assertTrue((STAGE/'Mod.xml').exists());self.assertTrue((STAGE/'Content/Tile/index.idx').exists())
  self.assertGreater(sum(self.M['pmdo']['tiles_per_bank'].values()),0)
if __name__=='__main__':unittest.main(verbosity=2)
