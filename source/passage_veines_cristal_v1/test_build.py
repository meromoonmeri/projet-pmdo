from __future__ import annotations

import json
import sys
import unittest
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build as pvc1


class TestPassageVeinesCristallines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = pvc1.build()
        cls.map_dir = pvc1.OUT / "maps/passage"

    def test_rom_rip_and_gallery_frames_are_pixel_identical(self):
        ref = pvc1.reference_rgb()
        self.assertEqual(ref.shape, (504, 456, 3))
        self.assertEqual(len(np.unique(ref.reshape(-1, 3), axis=0)), 96)
        index = json.loads((ROOT / "source/outil_maps_pmdsky/index_rom.json").read_text(encoding="utf-8"))
        entry = next(m for m in index["maps"] if m["code"] == "D17P33A")
        self.assertEqual((entry["taille_px"], entry["frames"], entry["couches"]), ([456, 504], 12, 2))
        self.assertFalse(entry["collision"])
        self.assertFalse(entry["animation_palette"])
        self.assertEqual(entry["bpa"], ["D17P33A1", None, None, None, "D17P33A5", None, None, None])
        gallery = ROOT / "large.D17P33A.gif.188f8399cf4c18292d9ecdd2454bcd10.gif"
        with Image.open(gallery) as gif, Image.open(pvc1.REF_ANIM) as rom_anim:
            self.assertEqual((gif.size, gif.n_frames), ((456, 504), 12))
            self.assertEqual((rom_anim.size, rom_anim.n_frames), ((456, 504), 12))
            for i, (a, b) in enumerate(zip(ImageSequence.Iterator(gif), ImageSequence.Iterator(rom_anim))):
                self.assertTrue(np.array_equal(np.asarray(a.convert("RGBA")), np.asarray(b.convert("RGBA"))), f"frame {i}")
        self.assertTrue(self.manifest["source"]["gallery_and_rom_frames_pixel_identical"])

    def test_canvas_palette_and_magenta_are_correctly_handled(self):
        self.assertEqual(self.manifest["map"]["size_px"], [768, 576])
        self.assertEqual(self.manifest["map"]["grid_8px"], [96, 72])
        self.assertEqual(self.manifest["generated_assets"]["guide"]["size_px"], [1200, 896])
        self.assertGreater(self.manifest["generated_assets"]["guide_floor_mask_iou"], 0.995)
        self.assertTrue(self.manifest["map"]["palette"]["source_palette_exact"])
        self.assertEqual(self.manifest["map"]["palette"]["source_palette_colors"], 96)
        scene = np.asarray(Image.open(self.map_dir / "review/PVC1_scene_t000.png").convert("RGBA"))
        self.assertEqual(scene.shape, (576, 768, 4))
        self.assertGreater(float((scene[..., 3] > 0).mean()), 0.70)
        source_colors = {tuple(int(v) for v in c) for c in np.unique(pvc1.reference_rgb().reshape(-1, 3), axis=0)}
        used_colors = {tuple(int(v) for v in c) for c in np.unique(scene[..., :3][scene[..., 3] > 0].reshape(-1, 3), axis=0)}
        self.assertTrue(used_colors <= source_colors)
        self.assertNotIn((220, 60, 220), used_colors)

    def test_editable_layers_and_ora_recompose_the_scene(self):
        paths = sorted((self.map_dir / "calques").glob("*.png"))
        self.assertEqual(len(paths), 7)
        arrays = [np.asarray(Image.open(p).convert("RGBA")) for p in paths]
        composed = Image.new("RGBA", (pvc1.W, pvc1.H))
        for arr in arrays:
            composed.alpha_composite(Image.fromarray(arr, "RGBA"))
        expected = np.asarray(Image.open(self.map_dir / "review/PVC1_scene_t000.png").convert("RGBA"))
        self.assertTrue(np.array_equal(np.asarray(composed), expected))
        ora = self.map_dir / "PVC1_calques.ora"
        with zipfile.ZipFile(ora) as z:
            names = set(z.namelist())
            self.assertIn("mimetype", names)
            self.assertIn("stack.xml", names)
            self.assertIn("mergedimage.png", names)
            self.assertEqual(len([n for n in names if n.startswith("data/layer")]), 7)
            merged = np.asarray(Image.open(z.open("mergedimage.png")).convert("RGBA"))
            self.assertTrue(np.array_equal(merged, expected))

    def test_two_generated_animation_tracks_match_rom_cycle_lengths(self):
        anim = self.manifest["animation"]
        self.assertEqual(anim["tracks"][0]["frames"], 6)
        self.assertEqual(anim["tracks"][0]["ticks_per_frame"], 10)
        self.assertEqual(anim["tracks"][0]["loop_ticks"], 60)
        self.assertEqual(anim["tracks"][1]["frames"], 4)
        self.assertEqual(anim["tracks"][1]["ticks_per_frame"], 10)
        self.assertEqual(anim["tracks"][1]["loop_ticks"], 40)
        self.assertEqual(anim["composite_frames"], 12)
        self.assertEqual(anim["composite_loop_ticks"], 120)
        crystal = sorted((pvc1.OUT / "animation/reflets_cristaux").glob("*.png"))
        pool = sorted((pvc1.OUT / "animation/ondes_veine").glob("*.png"))
        self.assertEqual((len(crystal), len(pool)), (6, 4))
        for paths in (crystal, pool):
            frames = [np.asarray(Image.open(p).convert("RGBA")) for p in paths]
            self.assertTrue(all(np.array_equal(frames[0][..., 3], f[..., 3]) for f in frames[1:]))
            self.assertGreater(len({f.tobytes() for f in frames}), 1)
        webp = self.map_dir / "review/PVC1_animation_12_phases.webp"
        with Image.open(webp) as im:
            self.assertEqual((im.size, im.n_frames), ((768, 576), 12))
            im.seek(0)
            frame0 = np.asarray(im.convert("RGBA"))
        expected = np.asarray(Image.open(self.map_dir / "review/PVC1_scene_t000.png").convert("RGBA"))
        self.assertTrue(np.array_equal(frame0, expected))

    def test_collision_grid_has_a_connected_16px_north_south_route(self):
        self.assertTrue(self.manifest["collision"]["north_south_path_16x16"])
        self.assertGreater(self.manifest["collision"]["walkable_cells"], 1500)
        self.assertGreater(self.manifest["collision"]["blocked_cells"], 1000)
        ground_path = pvc1.STAGE / f"Data/Ground/{pvc1.ASSET}.rsground"
        ground = json.loads(ground_path.read_text(encoding="utf-8"))
        obs = ground["Object"]["obstacles"]
        self.assertEqual(len(obs), 96)
        blocked = np.array([[bool(obs[x][y]["Tags"]) for x in range(96)] for y in range(72)])
        markers = self.manifest["collision"]["markers_px"]
        self.assertTrue(pvc1.connected(blocked, tuple(markers["entrance"]), tuple(markers["sortie"])))
        self.assertEqual({m["EntName"] for ent in ground["Object"]["Entities"] for m in ent["Markers"]},
                         {"entrance", "sortie"})
        self.assertEqual({m["Collider"]["Width"] for ent in ground["Object"]["Entities"] for m in ent["Markers"]}, {16})

    def test_ground_tiles_and_index_are_well_formed(self):
        ground_path = pvc1.STAGE / f"Data/Ground/{pvc1.ASSET}.rsground"
        ground = json.loads(ground_path.read_text(encoding="utf-8"))
        self.assertEqual(ground["Version"], "0.8.12.0")
        obj = ground["Object"]
        self.assertEqual(obj["TexSize"], 1)
        self.assertEqual(len(obj["Layers"]), 8)  # 7 visuels + Top vide
        self.assertEqual(len(obj["obstacles"]), 96)
        self.assertTrue(all(len(col) == 72 for col in obj["obstacles"]))
        tile_files = list((pvc1.STAGE / "Content/Tile").glob("*.tile"))
        self.assertEqual(len(tile_files), 7)
        # Les couches animées du Ground portent réellement 6 et 4 images, 10 ticks/image.
        for layer_idx, expected_frames in ((5, 6), (6, 4)):
            cells = obj["Layers"][layer_idx]["Tiles"]
            animated = []
            for col in cells:
                for tile in col:
                    for anim in tile.get("Layers", []):
                        if len(anim.get("Frames", [])) == expected_frames:
                            animated.append(anim)
            self.assertTrue(animated, f"couche {layer_idx} sans animation {expected_frames} frames")
            self.assertTrue(all(a["FrameLength"] == 10 for a in animated))
        self.assertTrue((pvc1.STAGE / "Content/Tile/index.idx").is_file())
        tools = pvc1.loadmod("pvc1_index_test", ROOT / "source/pmdo_cote/INSTALLER.py")
        nodes = {}
        for path in tile_files:
            with path.open("rb") as f:
                nodes[path.stem] = tools.read_node(f)
        self.assertEqual(set(nodes), {p.stem for p in tile_files})
        self.assertTrue((pvc1.STAGE / "Mod.xml").is_file())
        self.assertTrue((pvc1.STAGE / "INSTALLER.py").is_file())

    def test_provenance_and_limits_are_explicit(self):
        self.assertEqual(self.manifest["source"]["canonical_reference"], pvc1.REF.name)
        self.assertTrue(self.manifest["source"]["native_pixel_origin"].startswith("Aucun pixel"))
        self.assertTrue(self.manifest["animation"]["visuals_generated"])
        self.assertTrue(any("ne sont pas des tuiles" in x for x in self.manifest["limitations"]))
        self.assertFalse(self.manifest["runtime_tested"])
        self.assertFalse(self.manifest["gpu_tested"])
        self.assertFalse(self.manifest["art_approved"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
