from __future__ import annotations

import json
from collections import deque
from pathlib import Path
import unittest
import zipfile

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "renders/zone_guilde_treehouse_v2"
REF = ROOT / "source/zone_guilde_treehouse_v1/reference/T00P01_canonique.png"


def rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"))


def pmdo_blocked() -> np.ndarray:
    ground = OUT / "PMDO_project/Data/Ground/zgt2_village_arboricole_guilde.rsground"
    doc = json.loads(ground.read_text(encoding="utf-8"))
    cols = doc["Object"]["obstacles"]
    return np.asarray([[cell["Tags"] for cell in col] for col in cols], dtype=np.uint8).T


class TestZoneGuildeTreehouseV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))

    def test_01_scope_and_provenance_are_honest(self):
        self.assertEqual(self.manifest["prefix"], "ZGT2")
        self.assertTrue(self.manifest["parent"]["preserved"])
        self.assertTrue(self.manifest["parent"]["layout_approved"])
        self.assertFalse(self.manifest["art_approved"])
        self.assertFalse(self.manifest["runtime_tested"])
        self.assertIn("not accessible", self.manifest["attachment_animation"]["status"])
        self.assertEqual(self.manifest["water"]["loop_ticks"], 72)

    def test_02_layers_recompose_to_scene(self):
        names = [
            "layers/ZGT2_00_sol_residuel.png",
            "layers/ZGT2_01_sol_T00P01.png",
            "anim/ZGT2_02_eau_T00P01_f00.png",
            "layers/ZGT2_03_details.png",
            "layers/ZGT2_04_habitations_pont.png",
            "layers/ZGT2_05_maison_droite.png",
            "layers/ZGT2_06_canopee.png",
            "layers/ZGT2_07_liaisons_et_panneaux_T00P01.png",
        ]
        canvas = Image.new("RGBA", (768, 576), (0, 0, 0, 0))
        for name in names:
            canvas = Image.alpha_composite(canvas, Image.fromarray(rgba(OUT / name)))
        np.testing.assert_array_equal(np.asarray(canvas), rgba(OUT / "ZGT2_scene_t000.png"))
        self.assertTrue(np.all(rgba(OUT / "ZGT2_scene_t000.png")[..., 3] == 255))

    def test_03_all_four_signs_are_covered_by_canonical_patch(self):
        patch = rgba(OUT / "layers/ZGT2_07_liaisons_et_panneaux_T00P01.png")
        cells = {
            "nord_ouest": (31, 36, 34, 39),
            "nord_est": (62, 36, 65, 39),
            "sud_ouest": (38, 48, 41, 51),
            "sud_est": (57, 48, 60, 51),
        }
        for name, (x0, y0, x1, y1) in cells.items():
            alpha = patch[y0 * 8 : y1 * 8, x0 * 8 : x1 * 8, 3]
            self.assertTrue(np.all(alpha == 255), name)
        self.assertEqual(len(self.manifest["signs_removed"]), 4)

    def test_04_right_house_path_is_continuous_and_walkable(self):
        patch = rgba(OUT / "layers/ZGT2_07_liaisons_et_panneaux_T00P01.png")[..., 3] > 0
        labels, _ = ndi.label(patch)
        coords = self.manifest["right_house_connector"]
        self.assertGreater(len(coords), 4)
        route_component = labels[coords[0][1] * 8 + 4, coords[0][0] * 8 + 4]
        self.assertNotEqual(route_component, 0)
        self.assertTrue(all(labels[y * 8 + 4, x * 8 + 4] == route_component for x, y in coords))
        blocked = pmdo_blocked()
        start_px = self.manifest["markers_px"]["maison_droite"]
        end_px = self.manifest["markers_px"]["place_centrale"]
        start = (start_px[1] // 8, start_px[0] // 8)
        goal = (end_px[1] // 8, end_px[0] // 8)
        q = deque([start])
        seen = {start}
        while q:
            y, x = q.popleft()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (y + dy, x + dx)
                if 0 <= nxt[0] < blocked.shape[0] and 0 <= nxt[1] < blocked.shape[1] and blocked[nxt] == 0 and nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        self.assertIn(goal, seen)

    def test_05_source_texture_atlas_is_pixel_exact(self):
        meta = json.loads((OUT / "tilesheets/ZGT2_T00P01_textures_8px.json").read_text(encoding="utf-8"))
        atlas = rgba(OUT / "tilesheets/ZGT2_T00P01_textures_8px.png")
        reference = rgba(REF)[..., :3]
        self.assertGreater(len(meta["items"]), 150)
        for item in meta["items"]:
            ax, ay = item["atlas_xy_px"]
            sx, sy = item["source_xy_px"]
            np.testing.assert_array_equal(atlas[ay : ay + 8, ax : ax + 8, :3], reference[sy : sy + 8, sx : sx + 8])
        source_map = np.load(OUT / "tilesheets/ZGT2_terrain_source_tiles.npz", allow_pickle=False)["source_map"]
        self.assertEqual(source_map.shape, (72, 96, 3))
        self.assertGreater(int(np.sum(source_map[..., 2] > 0)), 100)

    def test_06_transparent_day_and_night_sprites(self):
        day = rgba(OUT / "sprites/ZGT2_maison_droite_jour_transparent.png")
        night = rgba(OUT / "sprites/ZGT2_maison_droite_nuit_transparent.png")
        self.assertEqual(day.shape, (128, 128, 4))
        np.testing.assert_array_equal(day[..., 3], night[..., 3])
        self.assertGreater(int(np.sum(day[..., 3] == 0)), 10000)
        self.assertTrue(np.any(day[..., :3][day[..., 3] > 0] != night[..., :3][night[..., 3] > 0]))
        atlas = rgba(OUT / "tilesheets/ZGT2_structures_sans_fond_8px.png")
        self.assertEqual(atlas.shape, (256, 768, 4))
        self.assertTrue(np.any(atlas[..., 3] == 0))
        self.assertTrue((OUT / "tilesheets/ZGT2_structures_8px.tsx").is_file())

    def test_07_pmdo_project_and_zip_are_well_formed(self):
        ground = OUT / "PMDO_project/Data/Ground/zgt2_village_arboricole_guilde.rsground"
        self.assertTrue(ground.is_file())
        doc = json.loads(ground.read_text(encoding="utf-8"))
        self.assertEqual(doc["Version"], "0.8.12.0")
        self.assertEqual(doc["Object"]["Name"]["DefaultText"], "Village arboricole de guilde — ZGT2")
        self.assertEqual(len(doc["Object"]["Layers"]), 8)
        with zipfile.ZipFile(OUT / "ZGT2_PMDO_0812.zip") as archive:
            names = archive.namelist()
            self.assertTrue(any(name.endswith("zgt2_village_arboricole_guilde.rsground") for name in names))
            self.assertTrue(any(name.endswith("Content/Tile/ZGT2_00_SOL_RESIDUEL.tile") for name in names))
            self.assertTrue(any(name.endswith("Content/Tile/ZGT2_07_LIENS_PANNEAUX.tile") for name in names))
        with zipfile.ZipFile(OUT / "ZGT2_layers.ora") as archive:
            self.assertIn("stack.xml", archive.namelist())
            self.assertIn("mergedimage.png", archive.namelist())

    def test_08_zgt1_is_preserved_and_v2_asset_is_present(self):
        v1 = ROOT / "renders/zone_guilde_treehouse_v1/ZGT1_scene_t000.png"
        v1_manifest = json.loads((v1.parent / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(v1.is_file())
        self.assertTrue(v1_manifest["art_approved"])
        self.assertTrue((ROOT / "livrable_zone_guilde_treehouse_v2.zip").is_file())


if __name__ == "__main__":
    unittest.main()
