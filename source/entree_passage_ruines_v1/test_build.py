from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import unittest
import zipfile

import numpy as np
from PIL import Image

from source.entree_passage_ruines_v1 import build

ROOT = Path(__file__).resolve().parents[2]
RENDERS = ROOT / "renders" / "entree_passage_ruines_v1"


class TestEntreeSentierDesRuines(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((RENDERS / "manifest.json").read_text(encoding="utf-8"))

    def test_01_dimensions_reference_and_review_flags(self) -> None:
        self.assertEqual(self.manifest["prefix"], "EPR1")
        self.assertEqual(self.manifest["title"], "Entrée du Sentier des Ruines")
        self.assertEqual(self.manifest["reference"], "P22P01A")
        self.assertEqual(self.manifest["dimensions_px"], [768, 576])
        self.assertEqual(self.manifest["dimensions_tiles"], [96, 72])
        self.assertEqual(self.manifest["tile_size_px"], [8, 8])
        self.assertEqual(self.manifest["loop_ticks"], 192)
        self.assertFalse(self.manifest["art_approved"])
        self.assertFalse(self.manifest["runtime_tested"])
        self.assertEqual(self.manifest["markers"]["entree_sud"], [384, 540])
        self.assertEqual(self.manifest["markers"]["boss"], [384, 330])
        self.assertEqual(self.manifest["markers"]["objectif_nord"], [384, 140])

    def test_02_rgb_fidelity_is_under_35(self) -> None:
        self.assertTrue(self.manifest["fidelity"])
        for category, info in self.manifest["fidelity"].items():
            with self.subTest(category=category):
                self.assertLess(info["rgb_distance"], 35.0)
                self.assertGreater(info["pixels"], 1000)

    def test_03_exported_layers_are_aligned_and_keyed(self) -> None:
        scene = np.asarray(Image.open(RENDERS / "EPR1_scene_t000.png").convert("RGBA"))
        self.assertEqual(scene.shape, (576, 768, 4))
        self.assertTrue(np.all(scene[..., 3] == 255))
        magenta = (scene[..., 0] > 235) & (scene[..., 2] > 235) & (scene[..., 1] < 30)
        self.assertEqual(int(magenta.sum()), 0)

        required = (
            "EPR1_00_sol_complet.png",
            "EPR1_01_sol.png",
            "EPR1_02_murs.png",
            "EPR1_03_ombres.png",
            "EPR1_04_ruines.png",
            "EPR1_05_vegetation.png",
            "EPR1_06_steles.png",
            "EPR1_07_debris.png",
        )
        for name in required:
            with self.subTest(layer=name):
                layer = np.asarray(Image.open(RENDERS / "layers" / name).convert("RGBA"))
                self.assertEqual(layer.shape, (576, 768, 4))
                self.assertGreater(int((layer[..., 3] > 0).sum()), 0)

        for name in required[1:]:
            if name == "EPR1_03_ombres.png":
                continue  # Ombres de contact volontairement semi-transparentes.
            layer = np.asarray(Image.open(RENDERS / "layers" / name).convert("RGBA"))
            alphas = np.unique(layer[..., 3])
            self.assertTrue(set(alphas).issubset({0, 255}), name)

    def test_04_entry_boss_and_north_arch_are_connected(self) -> None:
        palette, tree = build.reference_palette()
        _, decor_layers, components, _, _ = build.extract_decor(palette, tree)
        grid = build.build_collision_grid(build.build_floor_mask(), decor_layers, components)
        points = [build.ENTRY, build.BOSS, build.EXIT]
        cells = [(p[1] // 8, p[0] // 8) for p in points]
        for cell in cells:
            self.assertEqual(int(grid[cell]), 0)

        queue = deque([cells[0]])
        seen = {cells[0]}
        while queue:
            y, x = queue.popleft()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < 72 and 0 <= nx < 96 and grid[ny, nx] == 0 and (ny, nx) not in seen:
                    seen.add((ny, nx))
                    queue.append((ny, nx))
        self.assertTrue(all(cell in seen for cell in cells[1:]))
        self.assertGreater(int((grid == 0).sum()), 1500)

    def test_05_calculated_pollen_animates_on_a_separate_layer(self) -> None:
        anim_dir = RENDERS / "anim"
        files = sorted(anim_dir.glob("EPR1_08_pollen_dore_f*.png"))
        self.assertEqual(len(files), 24)
        frames = [np.asarray(Image.open(path).convert("RGBA")) for path in files]
        self.assertEqual(frames[0].shape, (576, 768, 4))
        self.assertGreater(int((frames[0][..., 3] > 0).sum()), 0)
        self.assertGreater(int(np.abs(frames[0].astype(np.int16) - frames[6].astype(np.int16)).sum()), 500)
        self.assertGreater(int(np.abs(frames[6].astype(np.int16) - frames[12].astype(np.int16)).sum()), 500)
        animation = self.manifest["animation"]["pollen_dore"]
        self.assertEqual(animation["frames"], 24)
        self.assertEqual(animation["ticks_per_frame"], 8)
        self.assertFalse(animation["native"])
        with Image.open(RENDERS / "EPR1_anim.png") as apng:
            self.assertEqual(apng.n_frames, 24)
            self.assertEqual(apng.info["loop"], 0)
            self.assertEqual(apng.info["duration"], 133.0)
        with Image.open(RENDERS / "EPR1_anim.webp") as webp:
            self.assertEqual(webp.n_frames, 24)

    def test_06_ora_pmdo_and_delivery_archives(self) -> None:
        ora = RENDERS / "EPR1_entree_passage_ruines.ora"
        with zipfile.ZipFile(ora) as zf:
            self.assertEqual(zf.read("mimetype").decode(), "image/openraster")
            xml = zf.read("stack.xml").decode("utf-8")
            names = zf.namelist()
            self.assertIn('visibility="hidden"', xml)
            self.assertIn("sol_complet_reference_generee", xml)
            self.assertIn("data/pollen_dore_f00.png", names)
            self.assertIn("data/arche_ruines.png", names)
            self.assertIn("mergedimage.png", names)
            self.assertIsNone(zf.testzip())

        preview = (ROOT / "apercu_entree_passage_ruines_v1.html").read_text(encoding="utf-8")
        self.assertIn("#walk{z-index:20", preview)

        mod_zip = ROOT / "mod_entree_passage_ruines_pmdo_0812.zip"
        liv_zip = ROOT / "livrable_entree_passage_ruines_v1.zip"
        with zipfile.ZipFile(mod_zip) as zf:
            names = zf.namelist()
            self.assertTrue(any(name.endswith(".rsground") for name in names))
            self.assertEqual(len([name for name in names if name.endswith(".tile")]), 8)
            ground_name = next(name for name in names if name.endswith(".rsground"))
            ground = json.loads(zf.read(ground_name))
            markers = [m["EntName"] for m in ground["Object"]["Entities"][0]["Markers"]]
            self.assertEqual(markers, ["entrance", "objectif_nord", "boss"])
            self.assertEqual(ground["Version"], "0.8.12.0")
            mod_xml = next(name for name in names if name.endswith("Mod.xml"))
            mod_text = zf.read(mod_xml).decode("utf-8")
            self.assertIn("Sentier des Ruines", mod_text)
            self.assertIn("P22P01A", mod_text)
            self.assertNotIn("Bassin Chauffant", mod_text)
            self.assertNotIn("P01P04A", mod_text)
            self.assertIsNone(zf.testzip())

        with zipfile.ZipFile(liv_zip) as zf:
            names = zf.namelist()
            self.assertIn("apercu_entree_passage_ruines_v1.html", names)
            self.assertIn("renders/entree_passage_ruines_v1/README.md", names)
            self.assertTrue(any(name.endswith("EPR1_scene_t000.png") for name in names))
            self.assertTrue(any(name.endswith("EPR1_entree_passage_ruines.ora") for name in names))
            self.assertIsNone(zf.testzip())


if __name__ == "__main__":
    unittest.main()
