from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import unittest
import zipfile

import numpy as np
from PIL import Image

from source.fin_chateau_ancien_v1 import build

ROOT = Path(__file__).resolve().parents[2]
RENDERS = ROOT / "renders" / "fin_chateau_ancien_v1"


class TestFinChateauAncien(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((RENDERS / "manifest.json").read_text(encoding="utf-8"))

    def test_01_dimensions_and_manifest_flags(self) -> None:
        self.assertEqual(self.manifest["prefix"], "FAC1")
        self.assertEqual(self.manifest["dimensions_px"], [768, 576])
        self.assertEqual(self.manifest["dimensions_tiles"], [96, 72])
        self.assertEqual(self.manifest["tile_size_px"], [8, 8])
        self.assertFalse(self.manifest["art_approved"])
        self.assertFalse(self.manifest["runtime_tested"])
        self.assertEqual(self.manifest["reference"], "oldcastlepmd.png")
        self.assertEqual(self.manifest["markers"]["boss"], [384, 280])

    def test_02_rgb_fidelity_is_under_35(self) -> None:
        for category, info in self.manifest["fidelity"].items():
            with self.subTest(category=category):
                self.assertLess(info["rgb_distance"], 35.0)
                self.assertGreater(info["pixels"], 1000)

    def test_03_layers_and_scene_have_expected_alpha(self) -> None:
        scene = np.asarray(Image.open(RENDERS / "FAC1_scene_t000.png").convert("RGBA"))
        self.assertEqual(scene.shape, (576, 768, 4))
        self.assertTrue(np.all(scene[..., 3] == 255))
        magenta = (scene[..., 0] > 235) & (scene[..., 2] > 235) & (scene[..., 1] < 30)
        self.assertEqual(int(magenta.sum()), 0)
        required = (
            "FAC1_00_sol_complet.png",
            "FAC1_01_sol.png",
            "FAC1_02_murs.png",
            "FAC1_03_ombres.png",
            "FAC1_04_ornements.png",
            "FAC1_05_coffres.png",
        )
        optional = ("FAC1_06_statues_rails.png", "FAC1_07_appliques.png")
        for name in required + optional:
            with self.subTest(layer=name):
                layer = np.asarray(Image.open(RENDERS / "layers" / name).convert("RGBA"))
                self.assertEqual(layer.shape, (576, 768, 4))
                if name in required:
                    self.assertGreater(int((layer[..., 3] > 0).sum()), 100)

    def test_04_entrance_boss_and_goal_are_connected(self) -> None:
        palette, tree = build.reference_palette()
        _, decor_layers, components, _, _ = build.extract_decor(palette, tree)
        grid = build.build_collision_grid(build.build_floor_mask(), decor_layers, components)
        points = [build.ENTRY, build.BOSS, build.EXIT]
        cells = [(p[1] // 8, p[0] // 8) for p in points]
        for cell in cells:
            self.assertEqual(int(grid[cell]), 0)
        q = deque([cells[0]])
        seen = {cells[0]}
        while q:
            y, x = q.popleft()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < 72 and 0 <= nx < 96 and grid[ny, nx] == 0 and (ny, nx) not in seen:
                    seen.add((ny, nx))
                    q.append((ny, nx))
        self.assertTrue(all(cell in seen for cell in cells[1:]))
        self.assertGreater(int((grid == 0).sum()), 1500)

    def test_05_gold_glints_animate_on_their_own_layer(self) -> None:
        f0 = np.asarray(Image.open(RENDERS / "anim" / "FAC1_08_reflets_or_f00.png").convert("RGBA"))
        f6 = np.asarray(Image.open(RENDERS / "anim" / "FAC1_08_reflets_or_f06.png").convert("RGBA"))
        f12 = np.asarray(Image.open(RENDERS / "anim" / "FAC1_08_reflets_or_f12.png").convert("RGBA"))
        self.assertEqual(f0.shape, (576, 768, 4))
        self.assertGreater(int((f0[..., 3] > 0).sum()), 0)
        self.assertGreater(int(np.abs(f0.astype(np.int16) - f6.astype(np.int16)).sum()), 500)
        self.assertGreater(int(np.abs(f6.astype(np.int16) - f12.astype(np.int16)).sum()), 500)
        self.assertEqual(self.manifest["animation"]["reflets_or"]["frames"], 24)
        self.assertEqual(self.manifest["animation"]["reflets_or"]["ticks_per_frame"], 10)

    def test_06_ora_and_pmdo_packages(self) -> None:
        ora = RENDERS / "FAC1_fin_chateau_ancien.ora"
        with zipfile.ZipFile(ora) as zf:
            self.assertEqual(zf.read("mimetype").decode(), "image/openraster")
            xml = zf.read("stack.xml").decode("utf-8")
            self.assertIn('visibility="hidden"', xml)
            self.assertIn("sol_complet_reference_generee", xml)
            self.assertIn("data/reflets_or_f00.png", zf.namelist())

        mod_zip = ROOT / "mod_fin_chateau_ancien_pmdo_0812.zip"
        liv_zip = ROOT / "livrable_fin_chateau_ancien_v1.zip"
        with zipfile.ZipFile(mod_zip) as zf:
            names = zf.namelist()
            self.assertTrue(any(n.endswith(".rsground") for n in names))
            self.assertTrue(any(n.endswith(".tile") for n in names))
            ground_name = next(n for n in names if n.endswith(".rsground"))
            ground = json.loads(zf.read(ground_name))
            markers = [m["EntName"] for m in ground["Object"]["Entities"][0]["Markers"]]
            self.assertEqual(markers, ["entrance", "objectif_nord", "boss"])
            self.assertEqual(ground["Version"], "0.8.12.0")
            self.assertIsNone(zf.testzip())
        with zipfile.ZipFile(liv_zip) as zf:
            names = zf.namelist()
            self.assertIn("apercu_fin_chateau_ancien_v1.html", names)
            self.assertTrue(any(n.endswith("FAC1_scene_t000.png") for n in names))
            self.assertIsNone(zf.testzip())


if __name__ == "__main__":
    unittest.main()
