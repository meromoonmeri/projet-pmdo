from __future__ import annotations

import json
from pathlib import Path
import unittest
import zipfile

import numpy as np
from PIL import Image

from source.fin_ile_zenith_v1 import build

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RENDERS = ROOT / "renders" / "fin_ile_zenith_v1"


class TestFinIleZenith(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((RENDERS / "manifest.json").read_text(encoding="utf-8"))
        cls.reference_colors = {
            tuple(color)
            for color in np.asarray(Image.open(HERE / "references/Final_Island_RRT.png").convert("RGB"))
            .reshape(-1, 3).tolist()
        }

    def test_01_identity_inputs_fidelity_and_flags(self) -> None:
        manifest = self.manifest
        self.assertEqual(manifest["prefix"], "FIZ1")
        self.assertEqual(manifest["map_id"], "fin_ile_zenith_v1")
        self.assertEqual(manifest["series_role"], "fin")
        self.assertEqual(manifest["dimensions_px"], [768, 576])
        self.assertEqual(manifest["dimensions_tiles"], [96, 72])
        self.assertEqual(manifest["palette_colors"], 1244)
        self.assertFalse(manifest["art_approved"])
        self.assertFalse(manifest["runtime_tested"])
        self.assertEqual(manifest["blocked_area"], {"autel_central": [342, 180, 430, 330]})
        self.assertEqual(
            manifest["markers"],
            {
                "entree_sud": [384, 552], "boss": [384, 360],
                "objectif_sanctuaire": [350, 128], "observatoire_ouest": [100, 280],
                "observatoire_est": [680, 280],
            },
        )
        for name in ("decor_magenta.png", "fond_sans_objets.png", "sol_complet.png"):
            path = HERE / "bruts" / name
            with self.subTest(raw=name):
                with Image.open(path) as image:
                    self.assertEqual(image.size, (1200, 896))
                self.assertEqual(manifest["raw_inputs"][name], build.sha256_of(path))
        for name, info in manifest["fidelity"].items():
            with self.subTest(material=name):
                self.assertLess(info["rgb_distance"], 35)
                self.assertGreater(info["pixels"], 1000)

    def test_02_layers_partition_and_reference_palette(self) -> None:
        scene = np.asarray(Image.open(RENDERS / "FIZ1_scene_t000.png").convert("RGBA"))
        self.assertEqual(scene.shape, (576, 768, 4))
        self.assertTrue(np.all(scene[..., 3] == 255))
        self.assertEqual(int(np.all(scene[..., :3] == [255, 0, 255], axis=2).sum()), 0)
        names = (
            "FIZ1_00_sol_complet.png", "FIZ1_01_fond_ciel.png", "FIZ1_02_sol.png",
            "FIZ1_03_ombres.png", "FIZ1_04_ciel_detail.png", "FIZ1_05_nuages.png",
            "FIZ1_06_falaises.png", "FIZ1_07_vegetation.png", "FIZ1_08_pierres.png",
            "FIZ1_09_sanctuaire.png", "FIZ1_10_ilots_lateraux.png", "FIZ1_11_premier_plan.png",
        )
        for name in names:
            with self.subTest(layer=name):
                arr = np.asarray(Image.open(RENDERS / "layers" / name).convert("RGBA"))
                self.assertEqual(arr.shape, (576, 768, 4))
                self.assertGreater(int((arr[..., 3] > 0).sum()), 100)
                colors = {tuple(c) for c in np.unique(arr[arr[..., 3] > 0, :3], axis=0).tolist()}
                self.assertTrue(colors.issubset(self.reference_colors))
        palette, tree = build.reference_palette()
        _, parts, components, _, opaque = build.extract_decor(palette, tree)
        masks = np.stack([part[..., 3] > 0 for part in parts.values()])
        self.assertEqual([item["kind"] for item in components], list(parts))
        self.assertTrue(np.array_equal(masks.any(axis=0), opaque))
        self.assertEqual(int((masks.sum(axis=0) > 1).sum()), 0)

    def test_03_arena_observatories_objective_and_blocked_altar(self) -> None:
        grid = build.build_collision_grid(build.build_floor_mask())
        self.assertEqual(grid.shape, (72, 96))
        self.assertEqual(int((grid == 0).sum()), self.manifest["walkable_cells"])
        points = (
            build.ENTRY, build.ARENA, build.OBJECTIVE, build.WEST_OBSERVATORY,
            build.EAST_OBSERVATORY, build.LEFT_CRESCENT, build.RIGHT_CRESCENT,
        )
        seen = build.reachable(grid, build.ENTRY)
        for point in points:
            cell = point[1] // 8, point[0] // 8
            self.assertEqual(int(grid[cell]), 0)
            self.assertIn(cell, seen)
        self.assertEqual(len(seen), self.manifest["walkable_cells"])
        x1, y1, x2, y2 = build.ALTAR_BOX
        self.assertTrue(np.all(grid[y1 // 8:y2 // 8 + 1, x1 // 8:x2 // 8 + 1] == 1))
        self.assertTrue(np.all(grid[0] == 1))
        self.assertTrue(np.all(grid[:, 0] == 1))
        self.assertTrue(np.all(grid[:, -1] == 1))
        self.assertEqual(np.flatnonzero(grid[-1] == 0).tolist(), [46, 47, 48, 49])

    def test_04_animations_are_independent_closed_loops(self) -> None:
        kinds = {
            "halo_sanctuaire": "FIZ1_12_halo_sanctuaire_f*.png",
            "voiles_nuages": "FIZ1_13_voiles_nuages_f*.png",
        }
        for kind, pattern in kinds.items():
            files = sorted((RENDERS / "anim").glob(pattern))
            self.assertEqual(len(files), 24)
            frames = [np.asarray(Image.open(path).convert("RGBA")) for path in files]
            self.assertGreater(int((frames[0][..., 3] > 0).sum()), 20)
            self.assertGreater(int(np.abs(frames[0].astype(np.int16) - frames[6].astype(np.int16)).sum()), 500)
            colors = {tuple(c) for c in np.unique(frames[0][frames[0][..., 3] > 0, :3], axis=0).tolist()}
            self.assertTrue(colors.issubset(self.reference_colors))
            self.assertEqual(self.manifest["animation"][kind]["frames"], 24)
            self.assertFalse(self.manifest["animation"][kind]["native"])
        palette, _ = build.reference_palette()
        self.assertTrue(np.array_equal(build.make_halo_frame(0, palette), build.make_halo_frame(24, palette)))
        self.assertTrue(np.array_equal(build.make_cloud_frame(0, palette), build.make_cloud_frame(24, palette)))
        with Image.open(RENDERS / "FIZ1_anim.png") as apng:
            self.assertEqual(apng.n_frames, 24)
            self.assertEqual(apng.info["loop"], 0)
        with Image.open(RENDERS / "FIZ1_anim.webp") as webp:
            self.assertEqual(webp.n_frames, 24)

    def test_05_ora_pmdo_and_delivery_archives(self) -> None:
        with zipfile.ZipFile(RENDERS / "FIZ1_fin_ile_zenith.ora") as archive:
            self.assertEqual(archive.read("mimetype").decode(), "image/openraster")
            self.assertIn('visibility="hidden"', archive.read("stack.xml").decode("utf-8"))
            self.assertIn("data/halo_sanctuaire_f00.png", archive.namelist())
            self.assertIsNone(archive.testzip())
        preview = (ROOT / "apercu_fin_ile_zenith_v1.html").read_text(encoding="utf-8")
        self.assertIn("Sanctuaire des Alizés", preview)
        with zipfile.ZipFile(ROOT / "mod_fin_ile_zenith_pmdo_0812.zip") as archive:
            names = archive.namelist()
            self.assertEqual(len([name for name in names if name.endswith(".tile")]), 13)
            ground = json.loads(archive.read(next(name for name in names if name.endswith(".rsground"))))
            self.assertEqual(ground["Version"], "0.8.12.0")
            self.assertEqual(len(ground["Object"]["Layers"]), 13)
            markers = [m["EntName"] for m in ground["Object"]["Entities"][0]["Markers"]]
            self.assertEqual(markers, ["entrance", "objectif_sanctuaire", "boss", "observatoire_ouest", "observatoire_est"])
            self.assertIsNone(archive.testzip())
        with zipfile.ZipFile(ROOT / "livrable_fin_ile_zenith_v1.zip") as archive:
            self.assertIn("apercu_fin_ile_zenith_v1.html", archive.namelist())
            self.assertIsNone(archive.testzip())


if __name__ == "__main__":
    unittest.main()
