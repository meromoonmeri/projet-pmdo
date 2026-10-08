"""Tests du mod multicalque des fins de donjon.
À lancer après build_mod.py ; contrôles de fichiers/installation, pas test du moteur PMDO.
"""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import re
import shutil
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]


def loadmod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B = loadmod('fins_mod_build_for_tests', HERE / 'build_mod.py')
INST = B.INST
STAGE, ZIP, NS = B.STAGE, B.ZIP, B.NAMESPACE
M = json.loads((B.OUT / 'manifest.json').read_text(encoding='utf-8'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def zip_files():
    with zipfile.ZipFile(ZIP) as zf:
        roots = {name.split('/', 1)[0] for name in zf.namelist()}
        if roots != {NS}:
            raise AssertionError(f'Racines du ZIP inattendues : {roots}')
        return {name.split('/', 1)[1]: zf.read(name) for name in zf.namelist() if not name.endswith('/')}


FILES = zip_files()


class FinDonjonMod(unittest.TestCase):
    def test_serie_et_complements_exhaustifs(self):
        source_lots = {
            path.parent.name
            for path in (R / 'renders').glob('fin_*/*_projet_pmdo_0812.zip')
        }
        self.assertEqual({item['folder'] for item in B.MAPS}, source_lots)
        self.assertEqual(M['map_count'], 11)
        self.assertEqual(M['main_series_count'], 9)
        self.assertEqual(M['main_series_order'], ['FVS1', 'FCF1', 'FRP1', 'FGG2', 'FBS1', 'FJS1', 'FWC1', 'FSM1', 'FST1'])
        self.assertEqual(M['preserved_complements'], ['FGG1', 'FOC1'])
        self.assertEqual(len({row['prefix'] for row in M['maps']}), M['map_count'])
        self.assertEqual(len({row['ground_asset'] for row in M['maps']}), M['map_count'])
        self.assertFalse(M['runtime_tested'])
        self.assertFalse(M['art_approved'])
        for row in M['maps']:
            self.assertEqual(row['ground']['size_px'], [768, 576], row['prefix'])
            self.assertEqual(row['ground']['grid_8px'], [96, 72], row['prefix'])
            self.assertGreaterEqual(row['ground']['layer_count'], 7, row['prefix'])
            self.assertEqual(row['ground']['layers'][-1]['layer_id'], 4, row['prefix'])
            self.assertIn('entrance', row['ground']['markers'], row['prefix'])

    def test_conservation_octet_pour_octet_et_ensemble_exact(self):
        expected = {
            'Content/Tile/index.idx', 'Mod.xml', 'INSTALLER.py', 'README.md', 'manifest.json'
        }
        for row in M['maps']:
            source_path = R / row['source_zip']
            self.assertEqual(sha(source_path.read_bytes()), row['source_zip_sha256'], row['prefix'])
            with zipfile.ZipFile(source_path) as source:
                roots = {name.split('/', 1)[0] for name in source.namelist() if not name.endswith('/')}
                self.assertEqual(len(roots), 1, row['prefix'])
                root = next(iter(roots))
                for bank in row['tile_banks']:
                    rel = f'Content/Tile/{bank}.tile'
                    expected.add(rel)
                    self.assertEqual(FILES[rel], source.read(f'{root}/{rel}'), f'{row["prefix"]}:{bank}')
                    self.assertEqual(sha(FILES[rel]), row['tile_sha256'][bank])
                ground_rel = f'Data/Ground/{row["ground_asset"]}.rsground'
                expected.add(ground_rel)
                source_ground = source.read(f'{root}/{row["ground_source_path"]}')
                self.assertEqual(FILES[ground_rel], source_ground, row['prefix'])
                self.assertEqual(sha(source_ground), row['ground_sha256'])
                script_rel = row['script_path_in_mod']
                expected.add(script_rel)
                source_script = source.read(f'{root}/{row["source_script_path"]}')
                self.assertEqual(FILES[script_rel], source_script, row['prefix'])
                self.assertEqual(sha(source_script), row['script_sha256'])
        self.assertEqual(set(FILES), expected)  # rien de plus, rien de moins
        self.assertEqual(FILES['INSTALLER.py'], B.make_installer_bytes())
        self.assertEqual(FILES['README.md'], (B.OUT / 'README.md').read_bytes())
        self.assertEqual(FILES['manifest.json'], (B.OUT / 'manifest.json').read_bytes())
        with zipfile.ZipFile(ZIP) as zf:
            for name in zf.namelist():
                self.assertEqual(zf.getinfo(name).date_time, B.FIXED_DATE, name)
                rel = name.split('/', 1)[1]
                self.assertEqual(zf.read(name), (STAGE / rel).read_bytes(), name)
        report = json.loads((B.OUT / 'build_report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['zip_sha256'], sha(ZIP.read_bytes()))
        self.assertEqual(report['build_checks'], 'PASS')

    def test_index_fusionne_complet_et_reproductible(self):
        with tempfile.TemporaryDirectory() as temp:
            index_path = Path(temp) / 'index.idx'
            index_path.write_bytes(FILES['Content/Tile/index.idx'])
            nodes = INST.read_index(index_path)
        tile_files = {Path(name).stem: raw for name, raw in FILES.items() if name.endswith('.tile')}
        self.assertEqual(set(nodes), set(tile_files))
        self.assertEqual(len(nodes), M['tile_bank_count'])
        for name, raw in tile_files.items():
            self.assertEqual(nodes[name], INST.read_node(io.BytesIO(raw)), name)
        self.assertEqual(INST.encode_index(nodes), FILES['Content/Tile/index.idx'])
        for row in M['maps']:
            self.assertTrue(all(name.startswith(row['prefix'] + '_') for name in row['tile_banks']), row['prefix'])

    def test_grounds_calques_animations_collisions_et_references(self):
        all_tiles = {
            Path(name).stem: raw
            for name, raw in FILES.items()
            if name.startswith('Content/Tile/') and name.endswith('.tile')
        }
        locations = {name: B.tile_locations(raw) for name, raw in all_tiles.items()}
        for row in M['maps']:
            raw = FILES[f'Data/Ground/{row["ground_asset"]}.rsground']
            doc = json.loads(raw)
            obj = doc['Object']
            self.assertEqual(doc['Version'], '0.8.12.0', row['prefix'])
            self.assertEqual(obj['AssetName'], row['ground_asset'])
            self.assertEqual(obj['TexSize'], 1)
            layers = obj['Layers']
            self.assertEqual(layers[-1]['Layer'], 4, row['prefix'])  # Top conservé au-dessus des décors
            width, height = 96, 72
            self.assertEqual((len(obj['obstacles']), len(obj['obstacles'][0])), (width, height))
            self.assertEqual(len(layers), row['ground']['layer_count'])
            for layer in layers:
                self.assertEqual(len(layer['Tiles']), width, (row['prefix'], layer['Name']))
                self.assertTrue(all(len(column) == height for column in layer['Tiles']), (row['prefix'], layer['Name']))
                for x, column in enumerate(layer['Tiles']):
                    for y, cell in enumerate(column):
                        for tile in cell.get('Layers', []):
                            for frame in tile.get('Frames', []):
                                bank = frame['Sheet']
                                point = (int(frame['TexLoc']['X']), int(frame['TexLoc']['Y']))
                                self.assertIn(bank, all_tiles, (row['prefix'], bank))
                                self.assertIn(point, locations[bank], (row['prefix'], bank, point, x, y))
            info = B.ground_info(raw, {name: all_tiles[name] for name in row['tile_banks']}, row['prefix'])
            self.assertEqual(info, row['ground'], row['prefix'])
            markers = {
                marker['EntName']: marker['Collider']
                for group in obj.get('Entities', [])
                for marker in group.get('Markers', [])
            }
            self.assertEqual(set(markers), set(row['ground']['markers']), row['prefix'])
            for name, marker in markers.items():
                self.assertEqual(
                    [marker['X'], marker['Y']],
                    row['ground']['markers'][name]['xy_px'],
                    (row['prefix'], name),
                )

    def test_mod_xml_readme_galerie_et_vignettes(self):
        root = ET.fromstring(FILES['Mod.xml'])
        self.assertEqual(root.findtext('Namespace'), NS)
        self.assertEqual(root.findtext('GameVersion'), '0.8.12.0')
        self.assertEqual(root.findtext('Version'), B.VERSION)
        self.assertTrue(re.fullmatch(r'[0-9a-f-]{36}', root.findtext('UUID') or ''))
        readme = FILES['README.md'].decode('utf-8')
        self.assertIn('9 cartes de la série principale', readme)
        for row in M['maps']:
            self.assertIn(row['prefix'], readme)
            self.assertIn(f"`{row['ground_asset']}`", readme)
            self.assertIn(row['preview'], (R / f'apercu_{B.LOT}.html').read_text(encoding='utf-8'))
            self.assertTrue((R / row['preview']).is_file(), row['preview'])
            self.assertTrue((R / 'renders' / row['folder'] / 'review' / row['scene']).is_file(), row['prefix'])
        for planned in B.PLANNED:
            self.assertIn(planned, readme)
        self.assertTrue((B.OUT / 'planche_cartes.png').is_file())
        self.assertIn(B.ZIP.relative_to(R).as_posix(), (R / f'apercu_{B.LOT}.html').read_text(encoding='utf-8'))

    def test_installateur_simulation_fusion_idempotence_et_conflit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with zipfile.ZipFile(ZIP) as zf:
                zf.extractall(root)
            source = root / NS
            target = root / 'mod_existant'
            target.mkdir()
            (target / 'Mod.xml').write_text('<Header><Namespace>mod_existant</Namespace></Header>', encoding='utf-8')
            (target / 'Content/Tile').mkdir(parents=True)
            sample_name = M['maps'][0]['tile_banks'][0]
            sample_raw = FILES[f'Content/Tile/{sample_name}.tile']
            extra_name = 'BANQUE_EXISTANTE'
            (target / 'Content/Tile' / f'{extra_name}.tile').write_bytes(sample_raw)
            (target / 'Content/Tile/index.idx').write_bytes(
                INST.encode_index({extra_name: INST.read_node(io.BytesIO(sample_raw))})
            )
            installer = B.loadmod('fins_installer_test', source / 'INSTALLER.py')
            installer.install(source, target, dry_run=True)
            self.assertFalse((target / 'Data').exists())
            installer.install(source, target)
            installed_nodes = installer.read_index(target / 'Content/Tile/index.idx')
            self.assertEqual(len(installed_nodes), M['tile_bank_count'] + 1)
            self.assertIn(extra_name, installed_nodes)
            for row in M['maps']:
                self.assertTrue((target / f'Data/Ground/{row["ground_asset"]}.rsground').is_file())
                script_common = target / row['script_path_in_mod']
                script_target_ns = target / 'Data/Script/mod_existant/ground' / row['ground_asset'] / Path(row['script_path_in_mod']).name
                self.assertTrue(script_common.is_file() or script_target_ns.is_file(), row['prefix'])
            installer.install(source, target)  # la deuxième installation ne doit pas changer le mod
            ground = target / f"Data/Ground/{M['maps'][-1]['ground_asset']}.rsground"
            ground.write_bytes(ground.read_bytes() + b' ')
            with self.assertRaises(ValueError):
                installer.install(source, target)


if __name__ == '__main__':
    unittest.main()
