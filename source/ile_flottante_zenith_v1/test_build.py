from __future__ import annotations

import json
from pathlib import Path
import unittest
import zipfile

import numpy as np
from PIL import Image

from source.ile_flottante_zenith_v1 import build

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RENDERS = ROOT / "renders" / "ile_flottante_zenith_v1"


class TestIleFlottanteZenith(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((RENDERS / "manifest.json").read_text(encoding="utf-8"))
        cls.reference_colors = {
            tuple(color)
            for color in np.asarray(
                Image.open(HERE / "references" / "Final_Island_RRT.png").convert("RGB")
            ).reshape(-1, 3).tolist()
        }

    def test_01_identity_dimensions_inputs_and_review_flags(self) -> None:
        manifest = self.manifest
        self.assertEqual(manifest["prefix"], "IFZ1")
        self.assertEqual(manifest["map_id"], "ile_flottante_zenith_v1")
        self.assertEqual(manifest["title"], "Île Flottante du Zénith — Couronne des Vents")
        self.assertEqual(manifest["reference"], "Final Island (Red Rescue Team)")
        self.assertEqual(manifest["reference_dimensions_px"], [480, 312])
        self.assertEqual(manifest["dimensions_px"], [768, 576])
        self.assertEqual(manifest["dimensions_tiles"], [96, 72])
        self.assertEqual(manifest["tile_size_px"], [8, 8])
        self.assertEqual(manifest["palette_colors"], 1244)
        self.assertEqual(manifest["loop_ticks"], 192)
        self.assertFalse(manifest["art_approved"])
        self.assertFalse(manifest["runtime_tested"])
        self.assertEqual(
            manifest["markers"],
            {
                "entree_sud": [384, 552], "couronne_vents": [384, 430],
                "sortie_nord": [384, 24], "belvedere_ouest": [104, 280],
                "belvedere_est": [680, 280],
            },
        )
        self.assertEqual(manifest["blocked_marker"], {"sceau_vent": [384, 382]})

        for name in ("decor_magenta.png", "fond_sans_objets.png", "sol_complet.png"):
            path = HERE / "bruts" / name
            with self.subTest(raw=name):
                with Image.open(path) as image:
                    self.assertEqual(image.size, (1200, 896))
                self.assertEqual(manifest["raw_inputs"][name], build.sha256_of(path))
        self.assertEqual(len(manifest["rejected_raws"]), 5)
        for item in manifest["rejected_raws"]:
            path = HERE / item["path"]
            with self.subTest(rejected=item["path"]):
                self.assertTrue(path.is_file())
                self.assertEqual(item["sha256"], build.sha256_of(path))
                self.assertTrue(item["reason"])

    def test_02_fidelity_is_under_35_before_quantization(self) -> None:
        expected = {"sol", "ciel", "roche_hors_contours", "vegetation", "scene_complete"}
        self.assertEqual(set(self.manifest["fidelity"]), expected)
        for category, info in self.manifest["fidelity"].items():
            with self.subTest(category=category):
                self.assertLess(info["rgb_distance"], 35.0)
                self.assertGreater(info["pixels"], 1000)
        self.assertLess(self.manifest["fidelity"]["sol"]["rgb_distance"], 30.0)
        self.assertLess(self.manifest["fidelity"]["ciel"]["rgb_distance"], 10.0)
        self.assertLess(self.manifest["fidelity"]["scene_complete"]["rgb_distance"], 30.0)

    def test_03_layers_are_aligned_partitioned_and_palette_quantized(self) -> None:
        scene = np.asarray(Image.open(RENDERS / "IFZ1_scene_t000.png").convert("RGBA"))
        self.assertEqual(scene.shape, (576, 768, 4))
        self.assertTrue(np.all(scene[..., 3] == 255))
        self.assertEqual(int(np.all(scene[..., :3] == [255, 0, 255], axis=2).sum()), 0)

        required = (
            "IFZ1_00_sol_complet.png", "IFZ1_01_fond_ciel.png", "IFZ1_02_sol.png",
            "IFZ1_03_ombres.png", "IFZ1_04_ciel_detail.png", "IFZ1_05_nuages.png",
            "IFZ1_06_falaises.png", "IFZ1_07_vegetation.png", "IFZ1_08_pierres.png",
            "IFZ1_09_monolithe.png", "IFZ1_10_ilots_lateraux.png",
            "IFZ1_11_premier_plan.png",
        )
        arrays: dict[str, np.ndarray] = {}
        for name in required:
            with self.subTest(layer=name):
                arr = np.asarray(Image.open(RENDERS / "layers" / name).convert("RGBA"))
                arrays[name] = arr
                self.assertEqual(arr.shape, (576, 768, 4))
                self.assertGreater(int((arr[..., 3] > 0).sum()), 100)
                colors = {
                    tuple(c) for c in np.unique(arr[arr[..., 3] > 0, :3], axis=0).tolist()
                }
                self.assertTrue(colors.issubset(self.reference_colors), name)

        self.assertTrue(np.all(arrays["IFZ1_00_sol_complet.png"][..., 3] == 255))
        self.assertTrue(np.all(arrays["IFZ1_01_fond_ciel.png"][..., 3] == 255))
        self.assertEqual(set(np.unique(arrays["IFZ1_03_ombres.png"][..., 3]).tolist()), {0, 46})
        for name in required[2:]:
            if name == "IFZ1_03_ombres.png":
                continue
            self.assertTrue(set(np.unique(arrays[name][..., 3]).tolist()).issubset({0, 255}), name)

        palette, tree = build.reference_palette()
        _, parts, components, _, opaque = build.extract_decor(palette, tree)
        masks = np.stack([part[..., 3] > 0 for part in parts.values()])
        self.assertEqual([item["kind"] for item in components], list(parts))
        self.assertTrue(np.array_equal(masks.any(axis=0), opaque))
        self.assertEqual(int((masks.sum(axis=0) > 1).sum()), 0)

    def test_04_two_branches_islets_and_north_south_openings(self) -> None:
        floor = build.build_floor_mask()
        grid = build.build_collision_grid(floor)
        self.assertEqual(grid.shape, (72, 96))
        self.assertEqual(int((grid == 0).sum()), self.manifest["walkable_cells"])
        self.assertEqual(int((grid != 0).sum()), self.manifest["obstacle_cells"])
        self.assertGreater(int((grid == 0).sum()), 800)

        points = (
            build.ENTRY, build.CROWN, build.EXIT, build.WEST_ISLET, build.EAST_ISLET,
            [260, 330], [520, 225],
        )
        cells = [(point[1] // 8, point[0] // 8) for point in points]
        for cell in cells:
            self.assertEqual(int(grid[cell]), 0)
        seen = build.reachable(grid, build.ENTRY)
        self.assertTrue(all(cell in seen for cell in cells[1:]))
        self.assertEqual(len(seen), self.manifest["reachable_cells_from_entry"])
        self.assertEqual(len(seen), self.manifest["walkable_cells"])
        self.assertEqual(int(grid[build.WIND_SEAL[1] // 8, build.WIND_SEAL[0] // 8]), 1)

        self.assertTrue(np.all(grid[:, 0] == 1))
        self.assertTrue(np.all(grid[:, -1] == 1))
        for edge, point in ((grid[0], build.EXIT), (grid[-1], build.ENTRY)):
            opening = np.flatnonzero(edge == 0)
            self.assertEqual(opening.tolist(), [46, 47, 48, 49])
            self.assertIn(point[0] // 8, opening.tolist())

    def test_05_wind_and_clouds_are_separate_closed_loops(self) -> None:
        anim_dir = RENDERS / "anim"
        kinds = {
            "courants_vent": "IFZ1_12_courants_vent_f*.png",
            "voiles_nuages": "IFZ1_13_voiles_nuages_f*.png",
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
        self.assertTrue(np.array_equal(build.make_wind_frame(0, palette), build.make_wind_frame(24, palette)))
        self.assertTrue(np.array_equal(build.make_cloud_frame(0, palette), build.make_cloud_frame(24, palette)))
        with Image.open(RENDERS / "IFZ1_anim.png") as apng:
            self.assertEqual(apng.n_frames, 24)
            self.assertEqual(apng.info["loop"], 0)
            self.assertEqual(apng.info["duration"], 133.0)
        with Image.open(RENDERS / "IFZ1_anim.webp") as webp:
            self.assertEqual(webp.n_frames, 24)

    def test_06_ora_pmdo_and_delivery_archives(self) -> None:
        ora = RENDERS / "IFZ1_ile_flottante_zenith.ora"
        with zipfile.ZipFile(ora) as archive:
            self.assertEqual(archive.read("mimetype").decode(), "image/openraster")
            xml = archive.read("stack.xml").decode("utf-8")
            names = archive.namelist()
            self.assertIn('visibility="hidden"', xml)
            self.assertIn("sol_complet_reference_generee", xml)
            self.assertIn("data/courants_vent_f00.png", names)
            self.assertIn("data/voiles_nuages_f00.png", names)
            self.assertIn("data/ilots_lateraux.png", names)
            self.assertIn("mergedimage.png", names)
            self.assertIsNone(archive.testzip())

        preview = (ROOT / "apercu_ile_flottante_zenith_v1.html").read_text(encoding="utf-8")
        self.assertIn("Île Flottante du Zénith", preview)
        self.assertIn("#walk{z-index:50", preview)

        with zipfile.ZipFile(ROOT / "mod_ile_flottante_zenith_pmdo_0812.zip") as archive:
            names = archive.namelist()
            self.assertEqual(len([name for name in names if name.endswith(".tile")]), 13)
            self.assertTrue(any(name.endswith("Content/Tile/index.idx") for name in names))
            ground_name = next(name for name in names if name.endswith(".rsground"))
            ground = json.loads(archive.read(ground_name))
            self.assertEqual(ground["Version"], "0.8.12.0")
            self.assertEqual(len(ground["Object"]["Layers"]), 13)
            self.assertEqual(len(ground["Object"]["obstacles"]), 96)
            self.assertEqual(len(ground["Object"]["obstacles"][0]), 72)
            markers = [
                marker["EntName"]
                for marker in ground["Object"]["Entities"][0]["Markers"]
            ]
            self.assertEqual(
                markers,
                ["entrance", "sortie_nord", "couronne_vents", "belvedere_ouest", "belvedere_est"],
            )
            mod_name = next(name for name in names if name.endswith("Mod.xml"))
            mod_text = archive.read(mod_name).decode("utf-8")
            self.assertIn("Ile Flottante du Zenith", mod_text)
            self.assertIn("Final Island RRT", mod_text)
            self.assertNotIn("Bosquet Mycelien", mod_text)
            self.assertIsNone(archive.testzip())

        with zipfile.ZipFile(ROOT / "livrable_ile_flottante_zenith_v1.zip") as archive:
            names = archive.namelist()
            self.assertIn("apercu_ile_flottante_zenith_v1.html", names)
            self.assertIn("renders/ile_flottante_zenith_v1/README.md", names)
            self.assertIn("renders/ile_flottante_zenith_v1/manifest.json", names)
            self.assertTrue(any(name.endswith("IFZ1_scene_t000.png") for name in names))
            self.assertTrue(any(name.endswith("IFZ1_ile_flottante_zenith.ora") for name in names))
            self.assertIsNone(archive.testzip())


if __name__ == "__main__":
    unittest.main()
