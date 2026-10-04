#!/usr/bin/env python3
"""
Automated verification suite for `cliff_nord_jour_anime_v1`:
Verifies that:
1. Root `cliffnordouesttest1.rsground` and `cliffdaytest.rsground` are byte-identical to their audited SHA-256 hashes.
2. No cliff, object, or existing animation layer is touched, renamed, split, or re-ordered in either `.rsground`.
3. No proxy `.tile` files are generated for cliff, terrain, or object sheets.
4. Cloud wrap overlay (`LayeredBG` / `MapBG` with `RepeatX = True`, `BGMovement = (-4, 0)`) is properly configured and its `.dir` sheets decode losslessly.
5. Sea animation on `Layers[1]` (`v2_promontoire_jour_03`) is canonically built from PMD Sky Port (`source/falaises_cotieres_nues/reference_ciel_mer.png`, Pelipper Post Office: 5 `far_sea` phases + 10 `near_sea` phases, `FrameLength = 10`).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RENDERS = ROOT / "renders/cliff_nord_jour_anime_v1"

sys.path.insert(0, str(ROOT / "source/pmdo_cote"))
spec_build = importlib.util.spec_from_file_location("cliff_build", HERE / "build.py")
B = importlib.util.module_from_spec(spec_build)
spec_build.loader.exec_module(B)

spec_verify = importlib.util.spec_from_file_location("pmdo_verify", ROOT / "source/pmdo_cote/verify.py")
V = importlib.util.module_from_spec(spec_verify)
spec_verify.loader.exec_module(V)


class TestCliffNordJourAnimeV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.nw_orig = json.loads((ROOT / "cliffnordouesttest1.rsground").read_bytes().decode("utf-8-sig"))
        cls.day_orig = json.loads((ROOT / "cliffdaytest.rsground").read_bytes().decode("utf-8-sig"))
        cls.nw_out_raw = (RENDERS / "Data/Ground/cliffnordouesttest1.rsground").read_bytes()
        cls.day_out_raw = (RENDERS / "Data/Ground/cliffdaytest.rsground").read_bytes()
        cls.nw_out = json.loads(cls.nw_out_raw.decode("utf-8-sig"))
        cls.day_out = json.loads(cls.day_out_raw.decode("utf-8-sig"))
        cls.manifest = json.loads((RENDERS / "manifest.json").read_text(encoding="utf-8"))

    def test_01_root_files_immutable(self) -> None:
        for fn, expected in B.EXPECTED_ROOT_SHA256.items():
            actual = hashlib.sha256((ROOT / fn).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, f"Root {fn} SHA-256 changed!")

    def test_02_utf8_bom_and_pmdo_0812_version(self) -> None:
        self.assertTrue(self.nw_out_raw.startswith(b"\xef\xbb\xbf"))
        self.assertTrue(self.day_out_raw.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(self.nw_out["Version"], "0.8.12.0")
        self.assertEqual(self.day_out["Version"], "0.8.12.0")

    def test_03_cliffnordouesttest1_cliff_and_object_layers_untouched(self) -> None:
        orig_o = self.nw_orig["Object"]
        out_o = self.nw_out["Object"]
        self.assertEqual(len(out_o["Layers"]), 4)
        self.assertEqual([l["Name"] for l in out_o["Layers"]], [l["Name"] for l in orig_o["Layers"]])
        # Layer 2 (New Layer = cliff/terrain) and Layer 3 (Layer 3 = cliff/waterfalls) must be 100% untouched
        self.assertEqual(out_o["Layers"][2], orig_o["Layers"][2])
        self.assertEqual(out_o["Layers"][3], orig_o["Layers"][3])
        # Layer 1 cell (10, 86) Altere_Pond_Cliffs must be untouched
        self.assertEqual(
            out_o["Layers"][1]["Tiles"][10][86],
            orig_o["Layers"][1]["Tiles"][10][86],
        )
        self.assertEqual(out_o["obstacles"], orig_o["obstacles"])
        self.assertEqual(out_o["Entities"], orig_o["Entities"])
        self.assertEqual(out_o["Decorations"], orig_o["Decorations"])

    def test_04_cliffdaytest_cliff_and_object_layers_untouched(self) -> None:
        orig_o = self.day_orig["Object"]
        out_o = self.day_out["Object"]
        self.assertEqual(len(out_o["Layers"]), 6)
        self.assertEqual([l["Name"] for l in out_o["Layers"]], [l["Name"] for l in orig_o["Layers"]])
        # Layers 2, 3, 4 (cliffs, objects, waterfalls/animations) must be 100% untouched
        self.assertEqual(out_o["Layers"][2], orig_o["Layers"][2])
        self.assertEqual(out_o["Layers"][3], orig_o["Layers"][3])
        self.assertEqual(out_o["Layers"][4], orig_o["Layers"][4])
        # Layer 0 non-sky cells (Altere_Pond_Cliffs at (47,83) and CanyonCamp at (50..51,73..74)) must be untouched
        self.assertEqual(out_o["Layers"][0]["Tiles"][47][83], orig_o["Layers"][0]["Tiles"][47][83])
        for x in (50, 51):
            for y in (73, 74):
                self.assertEqual(out_o["Layers"][0]["Tiles"][x][y], orig_o["Layers"][0]["Tiles"][x][y])
        # Layer 5 (Cloud/nuage): all 325 object cells must be preserved in place on Layer 5
        orig_l5 = orig_o["Layers"][5]
        out_l5 = out_o["Layers"][5]
        preserved_objs = 0
        for x in range(len(orig_l5["Tiles"])):
            for y in range(len(orig_l5["Tiles"][0])):
                orig_non_cloud = [
                    f
                    for tl in orig_l5["Tiles"][x][y]["Layers"]
                    for f in tl["Frames"]
                    if f["Sheet"] != "01_long_cap_jour_02"
                ]
                out_frames = [
                    f
                    for tl in out_l5["Tiles"][x][y]["Layers"]
                    for f in tl["Frames"]
                ]
                self.assertEqual(out_frames, orig_non_cloud, f"Layer 5 mismatch at ({x}, {y})")
                preserved_objs += len(out_frames)
        self.assertEqual(preserved_objs, 325)
        self.assertEqual(out_o["obstacles"], orig_o["obstacles"])
        self.assertEqual(out_o["Entities"], orig_o["Entities"])
        self.assertEqual(out_o["Decorations"], orig_o["Decorations"])

    def test_05_cloud_wrap_and_starry_night_configured_in_layered_bg(self) -> None:
        for slug, doc, expected_sky, expected_stars, expected_cloud, expected_y in [
            (
                "cliffnordouesttest1",
                self.nw_out,
                "CLIFF_NORD_OUEST_CIEL",
                "CLIFF_NORD_OUEST_ETOILES",
                "CLIFF_NORD_OUEST_NUAGES",
                216,
            ),
            (
                "cliffdaytest",
                self.day_out,
                "CLIFF_DAY_CIEL",
                "CLIFF_DAY_ETOILES",
                "CLIFF_DAY_NUAGES",
                0,
            ),
        ]:
            bg = doc["Object"]["Background"]
            self.assertEqual(bg["$type"], "RogueEssence.Dungeon.LayeredBG, RogueEssence")
            self.assertEqual(len(bg["Layers"]), 3)
            sky_bg = bg["Layers"][0]["BG"]
            star_bg = bg["Layers"][1]["BG"]
            cloud_bg = bg["Layers"][2]["BG"]

            self.assertEqual(sky_bg["BGAnim"]["AnimIndex"], expected_sky)
            self.assertEqual(sky_bg["BGAnim"]["FrameTime"], 1)
            self.assertFalse(sky_bg["RepeatX"])
            self.assertFalse(sky_bg["RepeatY"])
            self.assertEqual(sky_bg["BGMovement"], {"X": 0, "Y": 0})
            self.assertEqual(sky_bg["Parallax"], "1, 1")

            self.assertEqual(star_bg["BGAnim"]["AnimIndex"], expected_stars)
            self.assertEqual(star_bg["BGAnim"]["FrameTime"], 5)
            self.assertFalse(star_bg["RepeatX"])
            self.assertFalse(star_bg["RepeatY"])
            self.assertEqual(star_bg["BGMovement"], {"X": 0, "Y": 0})
            self.assertEqual(star_bg["MapLoc"], {"X": 0, "Y": 0})
            self.assertEqual(star_bg["Parallax"], "1, 1")

            self.assertEqual(cloud_bg["BGAnim"]["AnimIndex"], expected_cloud)
            self.assertTrue(cloud_bg["RepeatX"], f"{slug} cloud RepeatX must be True")
            self.assertFalse(cloud_bg["RepeatY"])
            self.assertEqual(cloud_bg["BGMovement"], {"X": -4, "Y": 0})
            self.assertEqual(cloud_bg["MapLoc"], {"X": 0, "Y": expected_y})
            self.assertEqual(cloud_bg["Parallax"], "1, 1")

    def test_06_canonical_pmdsky_sea_animation_and_tile_bank(self) -> None:
        # Only v2_promontoire_jour_03.tile may exist in Content/Tile/ (no fake cliff/object .tile files)
        tile_files = [p.name for p in (RENDERS / "Content/Tile").glob("*.tile")]
        self.assertEqual(tile_files, ["v2_promontoire_jour_03.tile"])

        # Decode v2_promontoire_jour_03.tile via independent verifier V.read_tile
        decoded_tiles = V.read_tile(RENDERS / "Content/Tile/v2_promontoire_jour_03.tile")
        sea_sheets, sea_info = B.build_canonical_pmdsky_sea_sheets()
        self.assertEqual(sea_info["far_sea_distinct_frames"], 5)
        self.assertEqual(sea_info["near_sea_distinct_frames"], 10)
        self.assertEqual(sea_info["frame_0_max_diff_vs_v2_promontoire_jour_03"], 0)

        # Verify every sea cell in both maps has 10 frames, FrameLength=10, and decodes losslessly
        for slug, orig_doc, out_doc, expected_count in [
            ("cliffnordouesttest1", self.nw_orig, self.nw_out, 6209),
            ("cliffdaytest", self.day_orig, self.day_out, 7503),
        ]:
            orig_l1 = orig_doc["Object"]["Layers"][1]
            out_l1 = out_doc["Object"]["Layers"][1]
            count = 0
            for x in range(len(out_l1["Tiles"])):
                for y in range(len(out_l1["Tiles"][0])):
                    for orig_tl, out_tl in zip(orig_l1["Tiles"][x][y]["Layers"], out_l1["Tiles"][x][y]["Layers"]):
                        if orig_tl["Frames"] and orig_tl["Frames"][0]["Sheet"] == "v2_promontoire_jour_03":
                            tx = orig_tl["Frames"][0]["TexLoc"]["X"]
                            ty = orig_tl["Frames"][0]["TexLoc"]["Y"]
                            self.assertEqual(out_tl["FrameLength"], 10)
                            self.assertEqual(len(out_tl["Frames"]), 10)
                            # Phase 0 preserves exact (tx, ty)
                            self.assertEqual(
                                out_tl["Frames"][0],
                                {"Sheet": "v2_promontoire_jour_03", "TexLoc": {"X": tx, "Y": ty}},
                            )
                            # Every phase f=0..9 must exist in decoded_tiles and match sea_sheets[f]
                            for f_idx, fr in enumerate(out_tl["Frames"]):
                                loc = (fr["TexLoc"]["X"], fr["TexLoc"]["Y"])
                                self.assertIn(loc, decoded_tiles)
                                expected_tile = B.premult_arr(
                                    sea_sheets[f_idx][ty * 8 : (ty + 1) * 8, tx * 8 : (tx + 1) * 8]
                                )
                                actual_tile = np.array(decoded_tiles[loc])
                                self.assertTrue(
                                    np.array_equal(actual_tile, expected_tile),
                                    f"{slug} sea tile mismatch at ({x},{y}) frame {f_idx}",
                                )
                            count += 1
            self.assertEqual(count, expected_count)

    def test_07_bg_dir_files_and_zip_archive(self) -> None:
        for name, expected_size in [
            ("CLIFF_NORD_OUEST_CIEL", (1104, 784)),
            ("CLIFF_NORD_OUEST_NUAGES", (1440, 208)),
            ("CLIFF_DAY_CIEL", (984, 792)),
            ("CLIFF_DAY_NUAGES", (984, 312)),
        ]:
            im = V.read_dir(RENDERS / f"Content/BG/{name}.dir")
            self.assertEqual(im.size, expected_size)

        zip_path = RENDERS / "cliff_nord_jour_anime_pmdo_0812.zip"
        self.assertTrue(zip_path.exists())
        with zipfile.ZipFile(zip_path) as zf:
            self.assertIsNone(zf.testzip())
            names = set(zf.namelist())
            self.assertEqual(
                names,
                {
                    "Data/Ground/cliffnordouesttest1.rsground",
                    "Data/Ground/cliffdaytest.rsground",
                    "Content/Tile/v2_promontoire_jour_03.tile",
                    "Content/BG/CLIFF_NORD_OUEST_CIEL.dir",
                    "Content/BG/CLIFF_NORD_OUEST_ETOILES.dir",
                    "Content/BG/CLIFF_NORD_OUEST_NUAGES.dir",
                    "Content/BG/CLIFF_DAY_CIEL.dir",
                    "Content/BG/CLIFF_DAY_ETOILES.dir",
                    "Content/BG/CLIFF_DAY_NUAGES.dir",
                    "INSTALLER.py",
                    "README.md",
                    "manifest.json",
                },
            )

        self.assertFalse(self.manifest["art_approved"])
        self.assertFalse(self.manifest["runtime_tested"])

    def test_08_awakening_night_sky_moon_and_twinkling_stars(self) -> None:
        import io
        import struct

        z2_astre = np.array(Image.open(B.ZRV2_MOON_PATH).convert("RGBA"))
        ays, axs = np.where(z2_astre[:, :, 3] > 0)
        expected_moon = z2_astre[ays.min() : ays.max() + 1, axs.min() : axs.max() + 1]
        self.assertEqual(expected_moon.shape, (64, 64, 4))

        for slug, star_dir_name, expected_w, expected_star_h, moon_center in [
            ("cliffnordouesttest1", "CLIFF_NORD_OUEST_ETOILES", 1104, 344, (552, 110)),
            ("cliffdaytest", "CLIFF_DAY_ETOILES", 984, 272, (480, 80)),
        ]:
            # Verify moon sprite on 00_ciel_bg.png matches ZRV2N_03_astre.png
            sky_arr = np.array(Image.open(RENDERS / f"{slug}/calques/00_ciel_bg.png").convert("RGBA"))
            mcx, mcy = moon_center
            mx0, my0 = mcx - 32, mcy - 32
            moon_crop = sky_arr[my0 : my0 + 64, mx0 : mx0 + 64]
            moon_mask = expected_moon[:, :, 3] == 255
            self.assertTrue(
                np.array_equal(moon_crop[moon_mask, :3], expected_moon[moon_mask, :3]),
                f"{slug} moon pixels do not match ZRV2N_03_astre.png",
            )
            # Verify top sky row matches ZRV2N_01_ciel.png night navy [0, 0, 78]
            self.assertEqual(sky_arr[0, 10, :3].tolist(), [0, 0, 78])

            # Verify 24-frame DirSheet binary structure of CLIFF_*_ETOILES.dir
            raw_dir = (RENDERS / f"Content/BG/{star_dir_name}.dir").read_bytes()
            png_len = struct.unpack("<q", raw_dir[:8])[0]
            atlas = Image.open(io.BytesIO(raw_dir[8 : 8 + png_len])).convert("RGBA")
            tile_w, tile_h, dirs, total_frames = struct.unpack("<4i", raw_dir[8 + png_len :])
            self.assertEqual((tile_w, tile_h, dirs, total_frames), (expected_w, expected_star_h, 0, 24))
            self.assertEqual(atlas.size, (expected_w * 3, expected_star_h * 8))
            self.assertLessEqual(atlas.size[0], 4096)
            self.assertLessEqual(atlas.size[1], 4096)

            # Verify all 24 exported star PNG frames exist and vary across the twinkling cycle
            star_pngs = [
                np.array(Image.open(RENDERS / f"{slug}/etoiles/etoiles_{i:02d}.png").convert("RGBA"))
                for i in range(24)
            ]
            distinct_hashes = {hashlib.sha256(a.tobytes()).hexdigest() for a in star_pngs}
            self.assertGreaterEqual(len(distinct_hashes), 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
