"""Tests du mod des 4 cartes Colonnes Lances et Mew (CLR1, CLR2, ECL1, IMW2 ; toutes à confirmer).
.venv/bin/python -m unittest source.mod_guilde_colonnes_mew_v1.test_mod -v      (après build_mod.py)
Contrôles de fichiers, d'index, de références de tuiles et d'installation : PAS un test du moteur PMDO.
"""
from pathlib import Path
import hashlib, importlib.util, io, json, re, shutil, struct, tempfile, unittest, zipfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


B = loadmod('mod_build', HERE / 'build_mod.py')
INST = B.INST
STAGE, ZIP, NS = B.STAGE, B.ZIP, B.NAMESPACE
M = json.loads((B.OUT / 'manifest.json').read_text())


def sha(b):
    return hashlib.sha256(b).hexdigest()


def locs(raw):
    """Emplacements (x, y) déclarés par une banque .tile, sans décoder les images."""
    size, count = struct.unpack_from('<ii', raw)
    return {struct.unpack_from('<ii', raw, 8 + i * 16) for i in range(count)}


def zfiles():
    with zipfile.ZipFile(ZIP) as z:
        return {n.split('/', 1)[1]: z.read(n) for n in z.namelist() if not n.endswith('/')}


FILES = zfiles()


class Mod(unittest.TestCase):
    def test_toutes_les_cartes(self):
        for folder, pfx, *_ in B.MAPS:                                              # chaque lot existe, avec son ZIP projet versionné
            self.assertTrue((R / 'renders' / folder / f'{pfx}_projet_pmdo_0812.zip').is_file(), pfx)
        self.assertEqual([m[1] for m in B.MAPS], ['CLR1', 'CLR2', 'ECL1', 'IMW2'])
        self.assertEqual((M['cartes'], len(M['maps'])), (4, 4))
        v = M['validation_utilisateur']                                            # aucune validation enregistrée
        self.assertEqual(v['cartes_validees'], []); self.assertEqual(set(v['a_confirmer']), {m[1] for m in B.MAPS})
        self.assertEqual(M['namespace'], NS); self.assertFalse(M['runtime_tested'])
        self.assertIsNone(M['validation_utilisateur']['citation'])
        self.assertEqual({n.split('/')[0] for n in zipfile.ZipFile(ZIP).namelist()}, {NS})
        # la vidéo IMW1 n'est pas une carte : elle ne doit pas figurer dans le mod
        self.assertFalse(any('IMW1' in k or k.endswith('.mp4') for k in FILES))

    def test_octet_pour_octet_depuis_les_lots(self):
        expected = {'Content/Tile/index.idx', 'Mod.xml', 'INSTALLER.py', 'README.md', 'manifest.json'}
        for m in M['maps']:
            src = R / m['zip_source']; self.assertEqual(sha(src.read_bytes()), m['zip_source_sha256'], m['prefixe'])
            with zipfile.ZipFile(src) as z:
                root = z.namelist()[0].split('/')[0]
                for name in m['banques']:
                    k = f'Content/Tile/{name}.tile'; expected.add(k)
                    self.assertEqual(FILES[k], z.read(f'{root}/{k}'), name)
                k = f"Data/Ground/{m['asset']}.rsground"; expected.add(k)
                self.assertEqual(FILES[k], z.read(f'{root}/{k}'), m['asset'])
                self.assertEqual(sha(FILES[k]), m['ground_sha256'])
                k = f"Data/Script/{NS}/ground/{m['asset']}/init.lua"; expected.add(k)
                self.assertEqual(FILES[k], z.read(f"{root}/{m['script_source']}"))     # script inchangé, déplacé
        self.assertEqual(set(FILES), expected)                                             # rien de plus, rien de moins
        with zipfile.ZipFile(R / 'renders/colonnes_lances_v2/CLR2/CLR2_projet_pmdo_0812.zip') as z:
            self.assertEqual(FILES['INSTALLER.py'], z.read('colonnes_lances_sommet/INSTALLER.py'))   # installeur des lots
        with zipfile.ZipFile(ZIP) as z:                                                    # ZIP = dossier du mod
            for n in z.namelist():
                self.assertEqual(z.read(n), (STAGE / n.split('/', 1)[1]).read_bytes(), n)
                self.assertEqual(z.getinfo(n).date_time, B.FIXED_DATE)

    def test_index_fusionne(self):
        p = Path(tempfile.mkdtemp()) / 'index.idx'; p.write_bytes(FILES['Content/Tile/index.idx'])
        nodes = INST.read_index(p)
        tiles = {Path(k).stem: v for k, v in FILES.items() if k.endswith('.tile')}
        self.assertEqual(set(nodes), set(tiles)); self.assertEqual(len(nodes), M['banques'])
        for name, raw in tiles.items():
            self.assertEqual(nodes[name], INST.read_node(io.BytesIO(raw)), name)
        self.assertEqual(INST.encode_index(nodes), FILES['Content/Tile/index.idx'])
        for m in M['maps']:                                                                # préfixes : pas d'ambiguïté
            self.assertTrue(all(b.startswith(m['prefixe'] + '_') for b in m['banques']))

    def test_grounds_references_marqueurs(self):
        tiles = {Path(k).stem: locs(v) for k, v in FILES.items() if k.endswith('.tile')}
        for m in M['maps']:
            doc = json.loads(FILES[f"Data/Ground/{m['asset']}.rsground"]); o = doc['Object']
            self.assertEqual(doc['Version'], '0.8.12.0'); self.assertEqual(o['AssetName'], m['asset'])
            self.assertEqual(o['Layers'][-1]['Layer'], 4, m['asset'])                     # calque Top vide en dernier
            w, h = len(o['Layers'][0]['Tiles']), len(o['Layers'][0]['Tiles'][0])
            self.assertEqual((w * 8, h * 8), (768, 576))
            self.assertEqual((len(o['obstacles']), len(o['obstacles'][0])), (w, h))
            for L in o['Layers']:
                for col in L['Tiles']:
                    for cell in col:
                        for t in cell['Layers']:
                            for f in t['Frames']:                                          # chaque tuile citée existe
                                self.assertIn((f['TexLoc']['X'], f['TexLoc']['Y']), tiles[f['Sheet']], (m['asset'], f['Sheet']))
                                self.assertIn(f['Sheet'], m['banques'])
            marks = {k['EntName']: k['Collider'] for k in o['Entities'][0]['Markers']}
            self.assertIn('entrance', marks); self.assertIn(len(marks), (2, 3), m['asset'])    # arrivée + un ou deux repères
            self.assertTrue(all(marks['entrance']['Y'] > v['Y'] for k, v in marks.items() if k != 'entrance'), m['asset'])   # arrivée au sud, repères au nord
            self.assertEqual(m['ground']['marqueurs']['entrance'], [marks['entrance']['X'], marks['entrance']['Y']])

    def test_cartes_particulieres(self):
        by = {x['prefixe']: x for x in M['maps']}
        imw = by['IMW2']['ground']
        self.assertEqual(imw['cases_bloquees'], imw['cases'])                              # fond de cinématique : rien de praticable
        self.assertEqual(set(imw['marqueurs']), {'entrance', 'mew', 'soleil'})
        self.assertEqual(imw['calques'], 8)                                                # 7 calques + Top vide
        self.assertTrue({(240, 10), (12, 200), (8, 6)} <= {tuple(a) for a in imw['pistes_animees']})
        self.assertEqual(set(by['ECL1']['ground']['marqueurs']), {'entrance', 'donjon_seuil'})
        self.assertEqual(set(by['CLR2']['ground']['marqueurs']), {'entrance', 'autel', 'centre'})
        self.assertLess(by['ECL1']['ground']['cases_bloquees'], by['ECL1']['ground']['cases'])   # ECL1 a bien un sentier praticable
        self.assertIn('1.0.0.0', (B.STAGE / 'Mod.xml').read_text())

    def test_mod_xml_readme(self):
        root = ET.fromstring(FILES['Mod.xml'])
        self.assertEqual(root.findtext('Namespace'), NS); self.assertEqual(root.findtext('GameVersion'), '0.8.12.0')
        self.assertTrue(re.fullmatch(r'[0-9a-f-]{36}', root.findtext('UUID')))
        rd = FILES['README.md'].decode()
        for m in M['maps']:
            self.assertIn(f"`{m['asset']}`", rd)
        self.assertIn('Aucune carte n\'a encore été testée dans PMDO', rd)
        self.assertEqual((B.OUT / 'README.md').read_text(), rd)
        page = (R / f'apercu_{B.LOT}.html').read_text()
        for m in M['maps']:                                                                # la galerie pointe vers des fichiers réels
            self.assertTrue((R / m['apercu']).is_file(), m['apercu']); self.assertIn(m['apercu'], page)
            self.assertTrue((R / 'renders' / m['lot'] / 'review' / m['image']).is_file())

    def test_installeur_dans_un_mod_existant(self):
        tmp = Path(tempfile.mkdtemp()); src = tmp / NS
        with zipfile.ZipFile(ZIP) as z:
            z.extractall(tmp)
        tgt = tmp / 'mon_mod'; tgt.mkdir()
        (tgt / 'Mod.xml').write_text('<Header><Namespace>mon_mod</Namespace></Header>')
        (tgt / 'Content/Tile').mkdir(parents=True)
        other = FILES['Content/Tile/IMW2_06_ECLATS.tile']                               # une banque déjà présente, autre nom
        (tgt / 'Content/Tile/AUTRE_BANQUE.tile').write_bytes(other)
        inst = loadmod('inst_copy', src / 'INSTALLER.py')
        inst.install(src, tgt, dry_run=True)
        self.assertFalse((tgt / 'Data').exists())                                          # simulation : rien d'écrit
        inst.install(src, tgt)
        nodes = inst.read_index(tgt / 'Content/Tile/index.idx')
        self.assertEqual(len(nodes), M['banques'] + 1); self.assertIn('AUTRE_BANQUE', nodes)
        for m in M['maps']:
            self.assertTrue((tgt / f"Data/Ground/{m['asset']}.rsground").is_file())
            self.assertTrue((tgt / f"Data/Script/mon_mod/ground/{m['asset']}/init.lua").is_file() or
                            (tgt / f"Data/Script/{NS}/ground/{m['asset']}/init.lua").is_file())
        inst.install(src, tgt)                                                             # réinstaller : sans effet
        g = tgt / f"Data/Ground/{M['maps'][-1]['asset']}.rsground"; g.write_bytes(g.read_bytes() + b' ')
        with self.assertRaises(ValueError):                                                # carte éditée : protégée
            inst.install(src, tgt)
        shutil.rmtree(tmp)


if __name__ == '__main__':
    unittest.main()
