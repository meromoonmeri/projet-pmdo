from __future__ import annotations

import json
from pathlib import Path
import unittest
import zipfile

import numpy as np
from PIL import Image

from source.entree_ile_zenith_v1 import build

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RENDERS = ROOT / "renders" / "entree_ile_zenith_v1"


class TestEntreeIleZenith(unittest.TestCase):
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
        self.assertEqual(manifest["prefix"], "EIZ1")
        self.assertEqual(manifest["map_id"], "entree_ile_zenith_v1")
        self.assertEqual(manifest["series_role"], "entrée")
        self.assertEqual(manifest["dimensions_px"], [768, 576])
        self.assertEqual(manifest["dimensions_tiles"], [96, 72])
        self.assertEqual(manifest["tile_size_px"], [8, 8])
        self.assertEqual(manifest["palette_colors"], 1244)
        self.assertFalse(manifest["art_approved"])
        self.assertFalse(manifest["runtime_tested"])
        self.assertEqual(manifest["rejected_raws"], [])
        self.assertEqual(
            manifest["markers"],
            {
                "entree_sud": [384, 552], "palier_bas": [384, 430],
                "seuil_portail": [384, 105], "belvedere_ouest": [86, 285],
                "belvedere_est": [687, 285],
            },
        )
        for name in ("decor_magenta.png", "fond_sans_objets.png", "sol_complet.png"):
            path = HERE / "bruts" / name
            with self.subTest(raw=name):
                with Image.open(path) as image:
                    self.assertEqual(image.size, (1200, 896))
                self.assertEqual(manifest["raw_inputs"][name], build.sha256_of(path))
        self.assertEqual(
            set(manifest["fidelity"]),
            {"sol", "ciel", "roche_hors_contours", "vegetation", "scene_complete"},
        )
        for name, info in manifest["fidelity"].items():
            with self.subTest(material=name):
                self.assertLess(info["rgb_distance"], 35)
                self.assertGreater(info["pixels"], 1000)

    def test_02_layers_partition_and_reference_palette(self) -> None:
        scene = np.asarray(Image.open(RENDERS / "EIZ1_scene_t000.png").convert("RGBA"))
        self.assertEqual(scene.shape, (576, 768, 4))
        self.assertTrue(np.all(scene[..., 3] == 255))
        self.assertEqual(int(np.all(scene[..., :3] == [255, 0, 255], axis=2).sum()), 0)
        names = (
            "EIZ1_00_sol_complet.png", "EIZ1_01_fond_ciel.png", "EIZ1_02_sol.png",
            "EIZ1_03_ombres.png", "EIZ1_04_ciel_detail.png", "EIZ1_05_nuages.png",
            "EIZ1_06_falaises.png", "EIZ1_07_vegetation.png", "EIZ1_08_pierres.png",
            "EIZ1_09_portail.png", "EIZ1_10_ilots_lateraux.png", "EIZ1_11_premier_plan.png",
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

    def test_03_two_branches_lookouts_and_only_south_open(self) -> None:
        grid = build.build_collision_grid(build.build_floor_mask())
        self.assertEqual(grid.shape, (72, 96))
        self.assertEqual(int((grid == 0).sum()), self.manifest["walkable_cells"])
        points = (
            build.ENTRY, build.LANDING, build.GATE, build.WEST_LOOKOUT, build.EAST_LOOKOUT,
            build.LEFT_BRANCH, build.RIGHT_BRANCH,
        )
        seen = build.reachable(grid, build.ENTRY)
        for point in points:
            cell = point[1] // 8, point[0] // 8
            self.assertEqual(int(grid[cell]), 0)
            self.assertIn(cell, seen)
        self.assertEqual(len(seen), self.manifest["walkable_cells"])
        self.assertTrue(np.all(grid[0] == 1))
        self.assertTrue(np.all(grid[:, 0] == 1))
        self.assertTrue(np.all(grid[:, -1] == 1))
        self.assertEqual(np.flatnonzero(grid[-1] == 0).tolist(), [45, 46, 47, 48, 49, 50])

    def test_04_animations_are_independent_closed_loops(self) -> None:
        kinds = {
            "runes_portail": "EIZ1_12_runes_portail_f*.png",
            "voiles_nuages": "EIZ1_13_voiles_nuages_f*.png",
        }
        for kind, pattern in kinds.items():
            files = sorted((RENDERS / "anim").glob(pattern))
            self.assertEqual(len(files), 24)
            frames = [np.asarray(Image.open(path).convert("RGBA")) for path in files]
            self.assertGreater(int((frames[0][..., 3] > 0).sum()), 20)
            self.assertGreater(int(np.abs(frames[0].astype(np.int16) - frames[6].astype(np.int16)).sum()), 500)
            colors = {tuple(c) for c in np.unique(frames[0][frames[0][..., 3] > 0, :3], axis=0).tolist()}
            self.assertTrue(colors.issubset(self.reference_colors))
            self.assertEqual(self.manifest["animation"][kind]["ticks_per_frame"], 8)
            self.assertFalse(self.manifest["animation"][kind]["native"])
        palette, _ = build.reference_palette()
        self.assertTrue(np.array_equal(build.make_portal_frame(0, palette), build.make_portal_frame(24, palette)))
        self.assertTrue(np.array_equal(build.make_cloud_frame(0, palette), build.make_cloud_frame(24, palette)))
        with Image.open(RENDERS / "EIZ1_anim.png") as apng:
            self.assertEqual(apng.n_frames, 24)
            self.assertEqual(apng.info["loop"], 0)
        with Image.open(RENDERS / "EIZ1_anim.webp") as webp:
            self.assertEqual(webp.n_frames, 24)

    def test_05_ora_pmdo_and_delivery_archives(self) -> None:
        with zipfile.ZipFile(RENDERS / "EIZ1_entree_ile_zenith.ora") as archive:
            self.assertEqual(archive.read("mimetype").decode(), "image/openraster")
            self.assertIn('visibility="hidden"', archive.read("stack.xml").decode("utf-8"))
            self.assertIn("data/runes_portail_f00.png", archive.namelist())
            self.assertIsNone(archive.testzip())
        preview = (ROOT / "apercu_entree_ile_zenith_v1.html").read_text(encoding="utf-8")
        self.assertIn("Portail des Alizés", preview)
        with zipfile.ZipFile(ROOT / "mod_entree_ile_zenith_pmdo_0812.zip") as archive:
            names = archive.namelist()
            self.assertEqual(len([name for name in names if name.endswith(".tile")]), 13)
            ground = json.loads(archive.read(next(name for name in names if name.endswith(".rsground"))))
            self.assertEqual(ground["Version"], "0.8.12.0")
            self.assertEqual(len(ground["Object"]["Layers"]), 13)
            markers = [m["EntName"] for m in ground["Object"]["Entities"][0]["Markers"]]
            self.assertEqual(markers, ["entrance", "seuil_portail", "palier_bas", "belvedere_ouest", "belvedere_est"])
            self.assertIsNone(archive.testzip())
        with zipfile.ZipFile(ROOT / "livrable_entree_ile_zenith_v1.zip") as archive:
            self.assertIn("apercu_entree_ile_zenith_v1.html", archive.namelist())
            self.assertIsNone(archive.testzip())


if __name__ == "__main__":
    unittest.main()
