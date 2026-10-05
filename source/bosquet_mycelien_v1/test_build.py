from __future__ import annotations

import json
from pathlib import Path
import unittest
import zipfile

import numpy as np
from PIL import Image

from source.bosquet_mycelien_v1 import build

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RENDERS = ROOT / "renders" / "bosquet_mycelien_v1"


class TestBosquetMycelien(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((RENDERS / "manifest.json").read_text(encoding="utf-8"))
        cls.reference_colors = {
            tuple(color)
            for color in np.asarray(Image.open(HERE / "references" / "Mushroom_Forest_RRT.png").convert("RGB"))
            .reshape(-1, 3)
            .tolist()
        }

    def test_01_identity_dimensions_inputs_and_review_flags(self) -> None:
        manifest = self.manifest
        self.assertEqual(manifest["prefix"], "BMF1")
        self.assertEqual(manifest["map_id"], "bosquet_mycelien_v1")
        self.assertEqual(manifest["title"], "Bosquet Mycélien — Clairière des Lanternes")
        self.assertEqual(manifest["reference"], "Mushroom Forest (Red Rescue Team)")
        self.assertEqual(manifest["reference_dimensions_px"], [456, 336])
        self.assertEqual(manifest["dimensions_px"], [768, 576])
        self.assertEqual(manifest["dimensions_tiles"], [96, 72])
        self.assertEqual(manifest["tile_size_px"], [8, 8])
        self.assertEqual(manifest["palette_colors"], 93)
        self.assertEqual(manifest["loop_ticks"], 192)
        self.assertFalse(manifest["art_approved"])
        self.assertFalse(manifest["runtime_tested"])
        self.assertEqual(
            manifest["markers"],
            {"entree_sud": [384, 552], "clairiere": [384, 470], "objectif_lanternes": [384, 112]},
        )

        for name in ("decor_magenta.png", "fond_sans_objets.png", "sol_complet.png"):
            path = HERE / "bruts" / name
            with self.subTest(raw=name):
                with Image.open(path) as image:
                    self.assertEqual(image.size, (1200, 896))
                self.assertEqual(manifest["raw_inputs"][name], build.sha256_of(path))
        rejected = manifest["rejected_raws"]
        self.assertEqual(len(rejected), 2)
        for item in rejected:
            path = HERE / item["path"]
            with self.subTest(rejected=item["path"]):
                self.assertTrue(path.is_file())
                self.assertEqual(item["sha256"], build.sha256_of(path))

    def test_02_fidelity_is_under_35_before_quantization(self) -> None:
        expected = {"sol", "sous_bois", "bois", "champignons", "scene_complete"}
        self.assertEqual(set(self.manifest["fidelity"]), expected)
        for category, info in self.manifest["fidelity"].items():
            with self.subTest(category=category):
                self.assertLess(info["rgb_distance"], 35.0)
                self.assertGreater(info["pixels"], 1000)
        self.assertLess(self.manifest["fidelity"]["sol"]["rgb_distance"], 30.0)
        self.assertLess(self.manifest["fidelity"]["scene_complete"]["rgb_distance"], 25.0)

    def test_03_layers_are_aligned_partitioned_and_palette_quantized(self) -> None:
        scene = np.asarray(Image.open(RENDERS / "BMF1_scene_t000.png").convert("RGBA"))
        self.assertEqual(scene.shape, (576, 768, 4))
        self.assertTrue(np.all(scene[..., 3] == 255))
        self.assertEqual(int(np.all(scene[..., :3] == np.array([255, 0, 255]), axis=2).sum()), 0)

        required = (
            "BMF1_00_sol_complet.png", "BMF1_01_sol.png", "BMF1_02_murs.png",
            "BMF1_03_ombres.png", "BMF1_04_sous_bois.png", "BMF1_05_bois.png",
            "BMF1_06_champignons.png", "BMF1_07_arche_nord.png",
            "BMF1_08_ilot_central.png", "BMF1_09_premier_plan.png",
        )
        arrays: dict[str, np.ndarray] = {}
        for name in required:
            with self.subTest(layer=name):
                arr = np.asarray(Image.open(RENDERS / "layers" / name).convert("RGBA"))
                arrays[name] = arr
                self.assertEqual(arr.shape, (576, 768, 4))
                self.assertGreater(int((arr[..., 3] > 0).sum()), 100)
                colors = {tuple(c) for c in np.unique(arr[arr[..., 3] > 0, :3], axis=0).tolist()}
                self.assertTrue(colors.issubset(self.reference_colors), name)

        self.assertTrue(np.all(arrays[required[0]][..., 3] == 255))
        self.assertTrue(set(np.unique(arrays["BMF1_03_ombres.png"][..., 3]).tolist()).issubset({0, 44, 48}))
        for name in required[1:]:
            if name == "BMF1_03_ombres.png":
                continue
            self.assertTrue(set(np.unique(arrays[name][..., 3]).tolist()).issubset({0, 255}), name)

        palette, tree = build.reference_palette()
        _, parts, components, _, opaque = build.extract_decor(palette, tree)
        masks = np.stack([part[..., 3] > 0 for part in parts.values()])
        self.assertEqual([item["kind"] for item in components], list(parts))
        self.assertTrue(np.array_equal(masks.any(axis=0), opaque))
        self.assertEqual(int((masks.sum(axis=0) > 1).sum()), 0)

    def test_04_two_branches_connect_markers_and_only_south_is_open(self) -> None:
        floor = build.build_floor_mask()
        grid = build.build_collision_grid(floor)
        self.assertEqual(grid.shape, (72, 96))
        self.assertEqual(int((grid == 0).sum()), self.manifest["walkable_cells"])
        self.assertEqual(int((grid != 0).sum()), self.manifest["obstacle_cells"])
        self.assertGreater(int((grid == 0).sum()), 800)

        points = (build.ENTRY, build.CLEARING, build.OBJECTIVE, [220, 330], [548, 330])
        cells = [(point[1] // 8, point[0] // 8) for point in points]
        for cell in cells:
            self.assertEqual(int(grid[cell]), 0)
        seen = build.reachable(grid, build.ENTRY)
        self.assertTrue(all(cell in seen for cell in cells[1:]))
        self.assertEqual(len(seen), self.manifest["reachable_cells_from_entry"])
        self.assertEqual(len(seen), self.manifest["walkable_cells"])

        self.assertEqual(int(grid[335 // 8, 384 // 8]), 1)  # cœur de l'îlot central
        self.assertTrue(np.all(grid[0, :] == 1))
        self.assertTrue(np.all(grid[:, 0] == 1))
        self.assertTrue(np.all(grid[:, -1] == 1))
        south_open = np.flatnonzero(grid[-1, :] == 0)
        self.assertGreaterEqual(len(south_open), 8)
        self.assertTrue(np.all(np.diff(south_open) == 1))
        self.assertIn(build.ENTRY[0] // 8, south_open.tolist())

    def test_05_lanterns_and_spores_are_separate_closed_loops(self) -> None:
        anim_dir = RENDERS / "anim"
        kinds = {
            "lueurs_lanternes": "BMF1_10_lueurs_lanternes_f*.png",
            "spores": "BMF1_11_spores_f*.png",
        }
        for kind, pattern in kinds.items():
            files = sorted(anim_dir.glob(pattern))
            with self.subTest(animation=kind):
                self.assertEqual(len(files), 24)
                frames = [np.asarray(Image.open(path).convert("RGBA")) for path in files]
                self.assertTrue(all(frame.shape == (576, 768, 4) for frame in frames))
                self.assertGreater(int((frames[0][..., 3] > 0).sum()), 5)
                self.assertGreater(
                    int(np.abs(frames[0].astype(np.int16) - frames[6].astype(np.int16)).sum()),
                    500,
                )
                colors = {
                    tuple(c)
                    for c in np.unique(frames[0][frames[0][..., 3] > 0, :3], axis=0).tolist()
                }
                self.assertTrue(colors.issubset(self.reference_colors))
                metadata = self.manifest["animation"][kind]
                self.assertEqual(metadata["frames"], 24)
                self.assertEqual(metadata["ticks_per_frame"], 8)
                self.assertFalse(metadata["native"])

        palette, _ = build.reference_palette()
        self.assertTrue(np.array_equal(build.make_lantern_frame(0, palette), build.make_lantern_frame(24, palette)))
        self.assertTrue(np.array_equal(build.make_spores_frame(0, palette), build.make_spores_frame(24, palette)))
        with Image.open(RENDERS / "BMF1_anim.png") as apng:
            self.assertEqual(apng.n_frames, 24)
            self.assertEqual(apng.info["loop"], 0)
            self.assertEqual(apng.info["duration"], 133.0)
        with Image.open(RENDERS / "BMF1_anim.webp") as webp:
            self.assertEqual(webp.n_frames, 24)

    def test_06_ora_pmdo_and_delivery_archives(self) -> None:
        ora = RENDERS / "BMF1_bosquet_mycelien.ora"
        with zipfile.ZipFile(ora) as archive:
            self.assertEqual(archive.read("mimetype").decode(), "image/openraster")
            xml = archive.read("stack.xml").decode("utf-8")
            names = archive.namelist()
            self.assertIn('visibility="hidden"', xml)
            self.assertIn("sol_complet_reference_generee", xml)
            self.assertIn("data/lueurs_lanternes_f00.png", names)
            self.assertIn("data/spores_f00.png", names)
            self.assertIn("data/ilot_central.png", names)
            self.assertIn("mergedimage.png", names)
            self.assertIsNone(archive.testzip())

        preview = (ROOT / "apercu_bosquet_mycelien_v1.html").read_text(encoding="utf-8")
        self.assertIn("Bosquet Mycélien", preview)
        self.assertIn("#walk{z-index:50", preview)

        with zipfile.ZipFile(ROOT / "mod_bosquet_mycelien_pmdo_0812.zip") as archive:
            names = archive.namelist()
            self.assertEqual(len([name for name in names if name.endswith(".tile")]), 11)
            self.assertTrue(any(name.endswith("Content/Tile/index.idx") for name in names))
            ground_name = next(name for name in names if name.endswith(".rsground"))
            ground = json.loads(archive.read(ground_name))
            self.assertEqual(ground["Version"], "0.8.12.0")
            self.assertEqual(len(ground["Object"]["Layers"]), 11)
            self.assertEqual(len(ground["Object"]["obstacles"]), 96)
            self.assertEqual(len(ground["Object"]["obstacles"][0]), 72)
            markers = [marker["EntName"] for marker in ground["Object"]["Entities"][0]["Markers"]]
            self.assertEqual(markers, ["entrance", "objectif_lanternes", "clairiere"])
            mod_name = next(name for name in names if name.endswith("Mod.xml"))
            mod_text = archive.read(mod_name).decode("utf-8")
            self.assertIn("Bosquet Mycelien", mod_text)
            self.assertIn("Mushroom Forest RRT", mod_text)
            self.assertNotIn("Bassin Chauffant", mod_text)
            self.assertIsNone(archive.testzip())

        with zipfile.ZipFile(ROOT / "livrable_bosquet_mycelien_v1.zip") as archive:
            names = archive.namelist()
            self.assertIn("apercu_bosquet_mycelien_v1.html", names)
            self.assertIn("renders/bosquet_mycelien_v1/README.md", names)
            self.assertIn("renders/bosquet_mycelien_v1/manifest.json", names)
            self.assertTrue(any(name.endswith("BMF1_scene_t000.png") for name in names))
            self.assertTrue(any(name.endswith("BMF1_bosquet_mycelien.ora") for name in names))
            self.assertIsNone(archive.testzip())


if __name__ == "__main__":
    unittest.main()
