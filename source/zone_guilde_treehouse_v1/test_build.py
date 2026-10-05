from __future__ import annotations

from collections import deque
from io import BytesIO
import json
from pathlib import Path
import struct
import unittest
import zipfile

import numpy as np
from PIL import Image

from source.zone_guilde_treehouse_v1 import build
from source.pmdo_cote import INSTALLER

ROOT = Path(__file__).resolve().parents[2]
RENDERS = ROOT / "renders/zone_guilde_treehouse_v1"


def rgba_array(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGBA")).copy()


class TestZoneGuildeTreehouse(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((RENDERS / "manifest.json").read_text(encoding="utf-8"))
        cls.mod_zip = RENDERS / "ZGT1_PMDO_0812.zip"

    def test_01_dimensions_provenance_and_review_flags(self) -> None:
        m = self.manifest
        self.assertEqual(m["prefix"], "ZGT1")
        self.assertEqual(m["dimensions_px"], [768, 576])
        self.assertEqual(m["dimensions_tiles"], [96, 72])
        self.assertEqual(m["tile_size_px"], [8, 8])
        self.assertTrue(m["art_approved"])
        self.assertIn("Composition V1", m["art_approval_scope"])
        self.assertFalse(m["runtime_tested"])
        self.assertEqual(m["reference"]["code"], "T00P01")
        self.assertEqual(m["reference"]["sha256"], build.sha256(build.REF_PATH))
        self.assertFalse(m["generated_sources"]["decor_magenta"]["pixels_native_rip"])
        self.assertFalse(m["generated_sources"]["sol_complet"]["pixels_native_rip"])
        with Image.open(build.REF_PATH) as reference:
            self.assertEqual(reference.size, (960, 720))

    def test_02_scene_is_crisp_and_uses_reference_palette(self) -> None:
        scene = rgba_array(RENDERS / "ZGT1_scene_t000.png")
        with Image.open(build.REF_PATH) as reference_image:
            reference = np.asarray(reference_image.convert("RGB"))
        palette = {tuple(int(v) for v in p) for p in np.unique(reference.reshape(-1, 3), axis=0)}
        self.assertEqual(scene.shape, (576, 768, 4))
        self.assertTrue(np.all(scene[..., 3] == 255))
        self.assertTrue(all(tuple(int(v) for v in c) in palette for c in np.unique(scene[..., :3].reshape(-1, 3), axis=0)))
        magenta = (scene[..., 0] > 235) & (scene[..., 2] > 235) & (scene[..., 1] < 35)
        self.assertEqual(int(magenta.sum()), 0)
        self.assertEqual(self.manifest["palette_fit"]["exact_palette_ratio"], 1.0)
        self.assertLess(self.manifest["palette_fit"]["rgb_mean"], 20.0)
        self.assertLess(self.manifest["palette_fit"]["rgb_p95"], 35.0)

    def test_03_layer_masks_partition_and_recompose(self) -> None:
        paths = [
            RENDERS / "layers/ZGT1_00_sol_residuel.png",
            RENDERS / "anim/ZGT1_01_eau_T00P01_f00.png",
            RENDERS / "layers/ZGT1_02_details.png",
            RENDERS / "layers/ZGT1_03_habitations_pont.png",
            RENDERS / "layers/ZGT1_04_canopee.png",
        ]
        arrays = [rgba_array(path) for path in paths]
        self.assertTrue(all(a.shape == (576, 768, 4) for a in arrays))
        coverage = sum((a[..., 3] > 0).astype(np.uint8) for a in arrays)
        self.assertTrue(np.all(coverage == 1), "Les calques éditables doivent partitionner la scène sans trou ni doublon")
        composite = Image.new("RGBA", (768, 576), (0, 0, 0, 0))
        for array in arrays:
            composite = Image.alpha_composite(composite, Image.fromarray(array))
        expected = rgba_array(RENDERS / "ZGT1_scene_t000.png")
        self.assertTrue(np.array_equal(np.asarray(composite), expected))
        partition = self.manifest["layer_partition_pixels"]
        self.assertGreater(partition["base"], 100_000)
        self.assertGreater(partition["canopy"], 50_000)
        self.assertGreater(partition["structures"], 10_000)

    def test_04_canonical_water_cycle_and_mask(self) -> None:
        phase_ids = (0, 1, 2, 6, 18, 35)
        frames = [rgba_array(RENDERS / f"anim/ZGT1_01_eau_T00P01_f{i:02d}.png") for i in phase_ids]
        self.assertTrue(all(f.shape == (576, 768, 4) for f in frames))
        masks = [f[..., 3] > 0 for f in frames]
        self.assertTrue(all(np.array_equal(masks[0], mask) for mask in masks[1:]))
        by_phase = dict(zip(phase_ids, frames))
        self.assertGreater(int(np.abs(by_phase[0].astype(np.int16) - by_phase[2].astype(np.int16)).sum()), 500)
        self.assertGreater(int(np.abs(by_phase[0].astype(np.int16) - by_phase[18].astype(np.int16)).sum()), 500)
        water = self.manifest["water"]
        self.assertEqual(water["frame_count"], 36)
        self.assertEqual(water["frame_length"], 2)
        self.assertEqual(water["loop_ticks"], 72)
        self.assertEqual(len(water["source_sample_coordinates_px"]), 11)
        self.assertEqual(water["mask"]["pixels"], int(masks[0].sum()))
        with np.load(build.ATLAS_PATH, allow_pickle=False) as atlas:
            self.assertEqual(atlas["tiles"].shape, (36, 11, 8, 8, 3))
            self.assertTrue(np.array_equal(atlas["ticks"], np.arange(0, 72, 2)))
        with Image.open(RENDERS / "anim/ZGT1_eau_T00P01_72ticks.webp") as webp:
            self.assertGreaterEqual(getattr(webp, "n_frames", 1), 6)

    def test_05_markers_and_walkability_are_connected(self) -> None:
        with zipfile.ZipFile(self.mod_zip) as archive:
            ground_name = next(name for name in archive.namelist() if name.endswith(".rsground"))
            obj = json.loads(archive.read(ground_name))["Object"]
        obstacles = obj["obstacles"]
        grid = np.asarray([[obstacles[x][y]["Tags"] for x in range(96)] for y in range(72)], dtype=np.uint8)
        self.assertEqual(grid.shape, (72, 96))
        self.assertGreater(int((grid == 0).sum()), 2_000)
        points = self.manifest["markers_px"]
        cells = {name: (point[1] // 8, point[0] // 8) for name, point in points.items()}
        for name, (y, x) in cells.items():
            with self.subTest(marker=name):
                self.assertEqual(int(grid[y, x]), 0)
        queue = deque([cells["entree_sud"]])
        seen = {cells["entree_sud"]}
        while queue:
            y, x = queue.popleft()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < 72 and 0 <= nx < 96 and grid[ny, nx] == 0 and (ny, nx) not in seen:
                    seen.add((ny, nx))
                    queue.append((ny, nx))
        self.assertTrue(all(cell in seen for cell in cells.values()))
        overlay = rgba_array(RENDERS / "ZGT1_collision_walkability.png")
        self.assertEqual(overlay.shape, (576, 768, 4))
        self.assertTrue(np.all(overlay[..., 3] > 0))
        self.assertEqual(set(np.unique(overlay[..., 3])) <= {108, 128, 255}, True)

    def test_06_native_pmdo_bundle_is_well_formed(self) -> None:
        with zipfile.ZipFile(self.mod_zip) as archive:
            names = archive.namelist()
            self.assertTrue(any(name.endswith(".rsground") for name in names))
            self.assertTrue(any(name.endswith(".tile") for name in names))
            self.assertIn("zone_guilde_treehouse/Mod.xml", names)
            self.assertIn("zone_guilde_treehouse/Content/Tile/index.idx", names)
            self.assertIsNone(archive.testzip())
            ground_name = next(name for name in names if name.endswith(".rsground"))
            obj_doc = json.loads(archive.read(ground_name))
            self.assertEqual(obj_doc["Version"], "0.8.12.0")
            obj = obj_doc["Object"]
            self.assertEqual(obj["AssetName"], build.ASSET)
            self.assertEqual(len(obj["Layers"]), 5)
            self.assertTrue(any(layer["Layers"] and layer["Layers"][0]["FrameLength"] == 2
                                for xcol in obj["Layers"][1]["Tiles"] for layer in xcol))
            markers = [m["EntName"] for m in obj["Entities"][0]["Markers"]]
            self.assertEqual(markers, list(self.manifest["markers_px"].keys()))
            header = archive.read("zone_guilde_treehouse/Mod.xml").decode("utf-8")
            self.assertIn("0.8.12.0", header)
            self.assertIn("zone_guilde_treehouse", header)

            tile_names = [name for name in names if name.endswith(".tile")]
            self.assertEqual(len(tile_names), 5)
            for name in tile_names:
                with self.subTest(tile=name):
                    self.assertGreater(len(INSTALLER.read_node(BytesIO(archive.read(name)))), 8)

            # L'index sérialisé doit référencer les cinq banques décodables.
            stream = BytesIO(archive.read("zone_guilde_treehouse/Content/Tile/index.idx"))
            count = struct.unpack("<i", stream.read(4))[0]
            self.assertEqual(count, 5)
            indexed = {}
            for _ in range(count):
                key = INSTALLER.read_string(stream)
                indexed[key] = INSTALLER.read_node(stream)
            self.assertEqual(set(indexed), set(self.manifest["pmdo_tile_banks"]))
            self.assertEqual(stream.read(), b"")

    def test_07_openraster_and_collision_preview(self) -> None:
        ora_path = RENDERS / "ZGT1_layers.ora"
        with zipfile.ZipFile(ora_path) as archive:
            self.assertEqual(archive.read("mimetype").decode("ascii"), "image/openraster")
            stack = archive.read("stack.xml").decode("utf-8")
            self.assertIn('visibility="hidden"', stack)
            self.assertIn("Support : sol complet généré", stack)
            self.assertIn("Eau — échantillons T00P01", stack)
            merged = np.asarray(Image.open(BytesIO(archive.read("mergedimage.png"))).convert("RGBA"))
        scene = rgba_array(RENDERS / "ZGT1_scene_t000.png")
        self.assertTrue(np.array_equal(merged, scene))
        collision_preview = rgba_array(RENDERS / "ZGT1_collision_walkability_apercu.png")
        self.assertTrue(np.all(collision_preview[..., 3] == 255))
        self.assertTrue((ROOT / "apercu_zone_guilde_treehouse_v1.html").is_file())
        self.assertTrue((RENDERS / "README_PACK.md").is_file())
        with zipfile.ZipFile(ROOT / "livrable_zone_guilde_treehouse_v1.zip") as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn("apercu_zone_guilde_treehouse_v1.html", archive.namelist())
            self.assertIn("source/zone_guilde_treehouse_v1/bruts/decor_magenta.png", archive.namelist())
            self.assertIn("renders/zone_guilde_treehouse_v1/ZGT1_PMDO_0812.zip", archive.namelist())


if __name__ == "__main__":
    unittest.main()
