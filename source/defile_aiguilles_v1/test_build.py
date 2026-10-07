import json
import sys
import unittest
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build as cpl1


class TestDefileAiguilles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = cpl1.build()
        cls.map_dir = cpl1.OUT / "maps/passage"

    def test_reference_and_exact_palette(self):
        ref = cpl1.reference_rgb()
        self.assertEqual(ref.shape, (456, 456, 3))
        self.assertEqual(len(np.unique(ref.reshape(-1, 3), axis=0)), 30)
        index = json.loads((ROOT / "source/outil_maps_pmdsky/index_rom.json").read_text(encoding="utf-8"))
        entry = next(m for m in index["maps"] if m["code"] == "D13P11A")
        self.assertEqual((entry["taille_px"], entry["frames"], entry["couches"]), ([456, 456], 1, 2))
        self.assertFalse(entry["collision"])
        self.assertFalse(entry["animation_palette"])
        extracted = ROOT / ".cache/maps_pmdsky/rom/png/D13P11A.png"
        if extracted.is_file():
            self.assertTrue(np.array_equal(ref, np.asarray(Image.open(extracted).convert("RGB"))))
        scene = np.asarray(Image.open(self.map_dir / "review/CPL1_scene_t000.png").convert("RGB"))
        source_colors = {tuple(int(v) for v in c) for c in np.unique(ref.reshape(-1, 3), axis=0)}
        scene_colors = {tuple(int(v) for v in c) for c in np.unique(scene.reshape(-1, 3), axis=0)}
        self.assertTrue(scene_colors <= source_colors)
        self.assertTrue(self.manifest["map"]["source_palette_exact"])

    def test_canvas_matches_pmdo_grid_and_is_static(self):
        self.assertEqual(self.manifest["map"]["size_px"], [456, 456])
        self.assertEqual(self.manifest["map"]["grid_8px"], [57, 57])
        self.assertEqual(self.manifest["source"]["reference_frames"], 1)
        self.assertFalse(self.manifest["runtime_tested"])
        self.assertFalse(self.manifest["art_approved"])

    def test_visual_layers_partition_rocks_and_recompose(self):
        paths = sorted((self.map_dir / "calques").glob("*.png"))
        self.assertEqual(len(paths), 4)
        arrays = [np.asarray(Image.open(p).convert("RGBA")) for p in paths]
        composed = Image.fromarray(arrays[0], "RGBA")
        for arr in arrays[1:]:
            composed.alpha_composite(Image.fromarray(arr, "RGBA"))
        expected = Image.open(self.map_dir / "review/CPL1_scene_t000.png").convert("RGBA")
        self.assertTrue(np.array_equal(np.asarray(composed), np.asarray(expected)))
        rock = np.asarray(Image.open(self.map_dir / "masques/CPL1_masque_roche.png")) > 0
        cliffs = arrays[2][..., 3] > 0
        pillars = arrays[3][..., 3] > 0
        self.assertTrue(np.array_equal(rock, cliffs | pillars))
        self.assertFalse(np.any(cliffs & pillars))

    def test_markers_have_clear_connected_16px_route(self):
        self.assertTrue(self.manifest["collision"]["north_south_path_16x16"])
        ground_path = cpl1.STAGE / f"Data/Ground/{cpl1.ASSET}.rsground"
        ground = json.loads(ground_path.read_text(encoding="utf-8"))
        obs = ground["Object"]["obstacles"]
        blocked = np.array([[bool(obs[x][y]["Tags"]) for x in range(57)] for y in range(57)])
        markers = self.manifest["collision"]["markers_px"]
        self.assertTrue(cpl1.connected(blocked, tuple(markers["entrance"]), tuple(markers["sortie"])))
        self.assertEqual({m["EntName"] for ent in ground["Object"]["Entities"] for m in ent["Markers"]},
                         {"entrance", "sortie"})

    def test_native_ground_and_tile_index(self):
        ground_path = cpl1.STAGE / f"Data/Ground/{cpl1.ASSET}.rsground"
        ground = json.loads(ground_path.read_text(encoding="utf-8"))
        self.assertEqual(ground["Version"], "0.8.12.0")
        obj = ground["Object"]
        self.assertEqual(obj["TexSize"], 1)
        self.assertEqual(len(obj["Layers"]), 5)
        self.assertEqual(len(obj["obstacles"]), 57)
        self.assertTrue(all(len(col) == 57 for col in obj["obstacles"]))
        tiles = list((cpl1.STAGE / "Content/Tile").glob("*.tile"))
        self.assertEqual(len(tiles), 4)
        self.assertTrue((cpl1.STAGE / "Content/Tile/index.idx").is_file())
        self.assertEqual(set(self.manifest["native"]["tile_banks"]), {p.stem for p in tiles})

    def test_ora_and_preview_are_editable_review_assets(self):
        ora = self.map_dir / "CPL1_calques.ora"
        with zipfile.ZipFile(ora) as z:
            names = set(z.namelist())
            self.assertIn("mimetype", names)
            self.assertIn("stack.xml", names)
            self.assertIn("mergedimage.png", names)
            self.assertEqual(len([n for n in names if n.startswith("data/layer")]), 4)
        preview = (ROOT / "apercu_defile_aiguilles_v1.html").read_text(encoding="utf-8")
        self.assertIn("Défilé des Aiguilles", preview)
        self.assertIn("Collisions / marqueurs", preview)

    def test_provenance_and_limits_are_explicit(self):
        self.assertEqual(self.manifest["source"]["canonical_reference"], cpl1.REF.name)
        self.assertEqual(self.manifest["source"]["guide_sha256"], cpl1.sha256(cpl1.GUIDE))
        self.assertTrue(any("rendu généré référencé" in x for x in self.manifest["limitations"]))
        self.assertTrue(self.manifest["collision"]["connector"]["carved"])
        self.assertEqual(self.manifest["collision"]["connector"]["width_px"], 22)
        self.assertTrue(all(x["ecart_rgb_moyen"] < 36 for x in self.manifest["map"]["palette_fidelity"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
