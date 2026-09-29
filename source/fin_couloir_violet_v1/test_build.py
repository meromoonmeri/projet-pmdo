import importlib.util
import json
import unittest
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'renders/fin_couloir_violet_v1'
STAGE=ROOT/'.cache/fin_couloir_violet_v1/fin_couloir_violet'
PFX='FVC1'


def load_build():
    p=ROOT/'source/fin_couloir_violet_v1/build.py'
    spec=importlib.util.spec_from_file_location('fvc_test_build_module',p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class FinCouloirVioletTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load_build()
        cls.manifest=json.loads((OUT/'manifest.json').read_text())

    def test_referenced_sources_and_no_magenta_in_outputs(self):
        raw=ROOT/'source/fin_couloir_violet_v1/bruts'
        self.assertTrue((raw/'decor.png').is_file())
        self.assertTrue((raw/'objets_magenta.png').is_file())
        guide=np.asarray(Image.open(raw/'objets_magenta.png').convert('RGB'))
        self.assertGreater(int(((guide[...,0]>200)&(guide[...,1]<80)&(guide[...,2]>200)).sum()),100000)
        for p in sorted((OUT/'calques').glob('*.png')):
            a=np.asarray(Image.open(p).convert('RGBA'))
            visible=a[...,3]>0
            self.assertEqual(a.shape[:2],(576,768),p.name)
            self.assertFalse(np.any(visible&(a[...,0]>245)&(a[...,1]<10)&(a[...,2]>245)),p.name)
        self.assertEqual(self.manifest['reference']['related_entry'],'ECV1')
        self.assertEqual(self.manifest['pmdo']['runtime_tested'],False)

    def test_masks_partition_geometry_and_void_is_small(self):
        seg=self.manifest['segmentation']
        self.assertGreater(seg['magenta_floor_px'],450000)
        self.assertGreater(seg['wall_px'],500000)
        self.assertGreater(seg['pebble_components'],10)
        self.assertLess(seg['void_px'],10000)
        walk=Image.open(OUT/'masques/FVC1_masque_praticable.png').convert('L')
        a=np.asarray(walk)
        self.assertEqual(a.shape,(576,768))
        self.assertGreater(int((a>0).sum()),200000)

    def test_south_boss_north_route_has_two_cell_clearance(self):
        access=self.manifest['access']
        self.assertEqual(access['markers']['entrance'][0],384)
        self.assertGreater(access['markers']['entrance'][1],500)
        self.assertLess(access['markers']['objectif'][1],180)
        self.assertEqual(access['markers']['boss'][0],384)
        for route in access['path_16x16'].values():self.assertTrue(route['ok'])
        ground=json.loads((STAGE/f'Data/Ground/{self.m.ASSET}.rsground').read_text())['Object']
        names=[m['EntName'] for layer in ground['Entities'] for m in layer['Markers']]
        self.assertEqual(set(names),{'entrance','boss','objectif'})
        self.assertEqual(ground['Layers'][-1]['Name'],'07 Top vide')
        self.assertEqual(ground['TexSize'],1)

    def test_rockfall_is_24_phase_closed_and_uses_ecv1_pose_pixels(self):
        frames=sorted((OUT/'animation/eboulis').glob('*.png'))
        self.assertEqual(len(frames),24)
        counts=[];hashes=set()
        for p in frames:
            a=np.asarray(Image.open(p).convert('RGBA'))
            self.assertEqual(a.shape,(576,768,4))
            counts.append(int((a[...,3]>0).sum()))
            hashes.add(a.tobytes())
        self.assertGreaterEqual(len(hashes),12)
        self.assertTrue(all(x>0 for x in counts))
        self.assertEqual(self.manifest['animations']['eboulis']['pose_origin'].split()[0],'poses')
        self.assertEqual(self.manifest['animations']['eboulis']['ticks'],5)

    def test_openraster_and_native_package_inputs_exist(self):
        ora=OUT/'FVC1_fin_couloir_violet_calques.ora'
        self.assertTrue(ora.is_file())
        with zipfile.ZipFile(ora) as z:
            self.assertIn('stack.xml',z.namelist());self.assertIn('mergedimage.png',z.namelist())
            merged=Image.open(z.open('mergedimage.png'))
            self.assertEqual(merged.size,(768,576))
        self.assertTrue((STAGE/'Mod.xml').is_file())
        self.assertTrue((STAGE/'Content/Tile/index.idx').is_file())
        self.assertGreater(self.manifest['pmdo']['tiles_per_bank']['FVC1_00_SOL_COMPLET'],0)
        self.assertFalse(self.manifest['access']['no_warp'] is False)


if __name__=='__main__':unittest.main(verbosity=2)
