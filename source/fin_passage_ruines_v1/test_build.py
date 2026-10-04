from __future__ import annotations

import json
from pathlib import Path
import unittest
import zipfile

import numpy as np
from PIL import Image

from source.fin_passage_ruines_v1 import build

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RENDERS = ROOT / "renders" / "fin_passage_ruines_v1"


class TestFinPassageRuines(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((RENDERS / "manifest.json").read_text(encoding="utf-8"))
        cls.reference_colors = {
            tuple(color)
            for color in np.asarray(Image.open(HERE / "references" / "P22P01A.png").convert("RGB"))
            .reshape(-1, 3)
            .tolist()
        }

    def test_01_identity_dimensions_inputs_and_review_flags(self) -> None:
        manifest = self.manifest
        self.assertEqual(manifest["prefix"], "FPR1")
        self.assertEqual(manifest["map_id"], "fin_passage_ruines_v1")
        self.assertEqual(manifest["title"], "Fin du Passage des Ruines — Sanctuaire du Cadran")
        self.assertEqual(manifest["reference"], "P22P01A")
        self.assertEqual(manifest["reference_dimensions_px"], [408, 408])
        self.assertEqual(manifest["dimensions_px"], [768, 576])
        self.assertEqual(manifest["dimensions_tiles"], [96, 72])
        self.assertEqual(manifest["tile_size_px"], [8, 8])
        self.assertEqual(manifest["palette_colors"], 109)
        self.assertEqual(manifest["loop_ticks"], 192)
        self.assertFalse(manifest["art_approved"])
        self.assertFalse(manifest["runtime_tested"])
        self.assertEqual(
            manifest["markers"],
            {"entree_sud": [384, 548], "boss": [384, 340], "objectif_cadran": [384, 152]},
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

    def test_02_fidelity_is_under_35_before_reference_quantization(self) -> None:
        expected = {"sol", "relief", "ruines", "vegetation", "scene_complete"}
        self.assertEqual(set(self.manifest["fidelity"]), expected)
        for category, info in self.manifest["fidelity"].items():
            with self.subTest(category=category):
                self.assertLess(info["rgb_distance"], 35.0)
                self.assertGreater(info["pixels"], 1000)
        self.assertLess(self.manifest["fidelity"]["sol"]["rgb_distance"], 20.0)
        self.assertLess(self.manifest["fidelity"]["scene_complete"]["rgb_distance"], 20.0)

    def test_03_layers_are_aligned_partitioned_and_palette_quantized(self) -> None:
        scene = np.asarray(Image.open(RENDERS / "FPR1_scene_t000.png").convert("RGBA"))
        self.assertEqual(scene.shape, (576, 768, 4))
        self.assertTrue(np.all(scene[..., 3] == 255))
        magenta = (scene[..., 0] > 220) & (scene[..., 2] > 220) & (scene[..., 1] < 70)
        self.assertEqual(int(magenta.sum()), 0)

        required = (
            "FPR1_00_sol_complet.png",
            "FPR1_01_sol.png",
            "FPR1_02_murs.png",
            "FPR1_03_ombres.png",
            "FPR1_04_relief.png",
            "FPR1_05_ruines.png",
            "FPR1_06_vegetation.png",
            "FPR1_07_sanctuaire.png",
            "FPR1_08_debris.png",
        )
        arrays: dict[str, np.ndarray] = {}
        for name in required:
            with self.subTest(layer=name):
                arr = np.asarray(Image.open(RENDERS / "layers" / name).convert("RGBA"))
                arrays[name] = arr
                self.assertEqual(arr.shape, (576, 768, 4))
                self.assertGreater(int((arr[..., 3] > 0).sum()), 100)
                visible_colors = {tuple(color) for color in np.unique(arr[arr[..., 3] > 0, :3], axis=0).tolist()}
                self.assertTrue(visible_colors.issubset(self.reference_colors), name)

        self.assertTrue(np.all(arrays[required[0]][..., 3] == 255))
        self.assertEqual(set(np.unique(arrays["FPR1_03_ombres.png"][..., 3]).tolist()), {0, 58})
        for name in required[1:]:
            if name == "FPR1_03_ombres.png":
                continue
            self.assertTrue(set(np.unique(arrays[name][..., 3]).tolist()).issubset({0, 255}), name)

        # The five detached decor families form one exact, non-overlapping partition.
        palette, tree = build.reference_palette()
        _, parts, _, _, opaque = build.extract_decor(palette, tree)
        masks = np.stack([part[..., 3] > 0 for part in parts.values()])
        self.assertTrue(np.array_equal(masks.any(axis=0), opaque))
        self.assertEqual(int((masks.sum(axis=0) > 1).sum()), 0)

    def test_04_collision_grid_connects_markers_and_closes_other_edges(self) -> None:
        floor = build.build_floor_mask()
        grid = build.build_collision_grid(floor)
        self.assertEqual(grid.shape, (72, 96))
        self.assertEqual(int((grid == 0).sum()), self.manifest["walkable_cells"])
        self.assertEqual(int((grid != 0).sum()), self.manifest["obstacle_cells"])
        self.assertGreater(int((grid == 0).sum()), 1400)

        marker_cells = [(point[1] // 8, point[0] // 8) for point in (build.ENTRY, build.BOSS, build.EXIT)]
        for cell in marker_cells:
            self.assertEqual(int(grid[cell]), 0)
        seen = build.reachable(grid, build.ENTRY)
        self.assertTrue(all(cell in seen for cell in marker_cells[1:]))
        self.assertEqual(len(seen), self.manifest["reachable_cells_from_entry"])
        self.assertEqual(len(seen), self.manifest["walkable_cells"])

        self.assertTrue(np.all(grid[0, :] == 1))
        self.assertTrue(np.all(grid[:, 0] == 1))
        self.assertTrue(np.all(grid[:, -1] == 1))
        south_open = np.flatnonzero(grid[-1, :] == 0).tolist()
        self.assertEqual(south_open, list(range(build.ENTRY[0] // 8 - 4, build.ENTRY[0] // 8 + 5)))

    def test_05_two_calculated_animations_are_separate_closed_loops(self) -> None:
        anim_dir = RENDERS / "anim"
        kinds = {
            "lueur_cadran": "FPR1_09_lueur_cadran_f*.png",
            "pollen_dore": "FPR1_10_pollen_dore_f*.png",
        }
        for kind, pattern in kinds.items():
            files = sorted(anim_dir.glob(pattern))
            with self.subTest(animation=kind):
                self.assertEqual(len(files), 24)
                frames = [np.asarray(Image.open(path).convert("RGBA")) for path in files]
                self.assertTrue(all(frame.shape == (576, 768, 4) for frame in frames))
                self.assertGreater(int((frames[0][..., 3] > 0).sum()), 20)
                self.assertGreater(
                    int(np.abs(frames[0].astype(np.int16) - frames[6].astype(np.int16)).sum()),
                    500,
                )
                visible = frames[0][frames[0][..., 3] > 0, :3]
                self.assertTrue({tuple(c) for c in np.unique(visible, axis=0).tolist()}.issubset(self.reference_colors))
                metadata = self.manifest["animation"][kind]
                self.assertEqual(metadata["frames"], 24)
                self.assertEqual(metadata["ticks_per_frame"], 8)
                self.assertFalse(metadata["native"])

        palette, _ = build.reference_palette()
        self.assertTrue(np.array_equal(build.make_cadran_frame(0, palette), build.make_cadran_frame(24, palette)))
        self.assertTrue(np.array_equal(build.make_pollen_frame(0, palette), build.make_pollen_frame(24, palette)))
        with Image.open(RENDERS / "FPR1_anim.png") as apng:
            self.assertEqual(apng.n_frames, 24)
            self.assertEqual(apng.info["loop"], 0)
            self.assertEqual(apng.info["duration"], 133.0)
        with Image.open(RENDERS / "FPR1_anim.webp") as webp:
            self.assertEqual(webp.n_frames, 24)

    def test_06_ora_pmdo_and_delivery_archives(self) -> None:
        ora = RENDERS / "FPR1_fin_passage_ruines.ora"
        with zipfile.ZipFile(ora) as archive:
            self.assertEqual(archive.read("mimetype").decode(), "image/openraster")
            xml = archive.read("stack.xml").decode("utf-8")
            names = archive.namelist()
            self.assertIn('visibility="hidden"', xml)
            self.assertIn("sol_complet_reference_generee", xml)
            self.assertIn("data/lueur_cadran_f00.png", names)
            self.assertIn("data/pollen_dore_f00.png", names)
            self.assertIn("data/sanctuaire_cadran.png", names)
            self.assertIn("mergedimage.png", names)
            self.assertIsNone(archive.testzip())

        preview = (ROOT / "apercu_fin_passage_ruines_v1.html").read_text(encoding="utf-8")
        self.assertIn("Fin du Passage des Ruines", preview)
        self.assertIn("#walk{z-index:50", preview)

        mod_zip = ROOT / "mod_fin_passage_ruines_pmdo_0812.zip"
        with zipfile.ZipFile(mod_zip) as archive:
            names = archive.namelist()
            self.assertEqual(len([name for name in names if name.endswith(".tile")]), 10)
            self.assertTrue(any(name.endswith("Content/Tile/index.idx") for name in names))
            ground_name = next(name for name in names if name.endswith(".rsground"))
            ground = json.loads(archive.read(ground_name))
            self.assertEqual(ground["Version"], "0.8.12.0")
            self.assertEqual(len(ground["Object"]["Layers"]), 10)
            self.assertEqual(len(ground["Object"]["obstacles"]), 96)
            self.assertEqual(len(ground["Object"]["obstacles"][0]), 72)
            markers = [marker["EntName"] for marker in ground["Object"]["Entities"][0]["Markers"]]
            self.assertEqual(markers, ["entrance", "objectif_cadran", "boss"])
            mod_name = next(name for name in names if name.endswith("Mod.xml"))
            mod_text = archive.read(mod_name).decode("utf-8")
            self.assertIn("Fin Passage des Ruines", mod_text)
            self.assertIn("P22P01A", mod_text)
            self.assertNotIn("Bassin Chauffant", mod_text)
            self.assertIsNone(archive.testzip())

        delivery = ROOT / "livrable_fin_passage_ruines_v1.zip"
        with zipfile.ZipFile(delivery) as archive:
            names = archive.namelist()
            self.assertIn("apercu_fin_passage_ruines_v1.html", names)
            self.assertIn("renders/fin_passage_ruines_v1/README.md", names)
            self.assertIn("renders/fin_passage_ruines_v1/manifest.json", names)
            self.assertTrue(any(name.endswith("FPR1_scene_t000.png") for name in names))
            self.assertTrue(any(name.endswith("FPR1_fin_passage_ruines.ora") for name in names))
            self.assertIsNone(archive.testzip())


if __name__ == "__main__":
    unittest.main()
