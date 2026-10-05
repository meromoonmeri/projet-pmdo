from __future__ import annotations

import json
from pathlib import Path
import unittest
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
RENDERS = ROOT / "renders"


class TestTrilogieZenith(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(
            (RENDERS / "trilogie_zenith_v1/manifest.json").read_text(encoding="utf-8")
        )

    def test_01_three_unique_4_3_maps_cover_entry_path_and_finale(self) -> None:
        self.assertEqual(self.manifest["roles"], ["entrée", "chemin", "fin"])
        maps = self.manifest["maps"]
        self.assertEqual(len(maps), 3)
        self.assertEqual([item["prefix"] for item in maps], ["EIZ1", "IFZ1", "FIZ1"])
        self.assertEqual(len({item["map_id"] for item in maps}), 3)
        self.assertEqual(len({item["delivery_sha256"] for item in maps}), 3)
        for item in maps:
            with self.subTest(prefix=item["prefix"]):
                self.assertEqual(item["dimensions_px"], [768, 576])
                self.assertEqual(item["walkable_cells"], item["reachable_cells"])
                self.assertGreaterEqual(len(item["animations"]), 2)
                self.assertFalse(item["art_approved"])
                self.assertFalse(item["runtime_tested"])
                self.assertTrue((ROOT / item["preview"]).is_file())
                for archive_name in (item["delivery_zip"], item["pmdo_zip"]):
                    with zipfile.ZipFile(ROOT / archive_name) as archive:
                        self.assertIsNone(archive.testzip())
        scenes = [
            RENDERS / "entree_ile_zenith_v1/EIZ1_scene_t000.png",
            RENDERS / "ile_flottante_zenith_v1/IFZ1_scene_t000.png",
            RENDERS / "fin_ile_zenith_v1/FIZ1_scene_t000.png",
        ]
        payloads = []
        for path in scenes:
            with Image.open(path) as image:
                self.assertEqual(image.size, (768, 576))
            payloads.append(path.read_bytes())
        self.assertEqual(len({hash(payload) for payload in payloads}), 3)

    def test_02_gallery_links_every_editable_delivery(self) -> None:
        gallery = (ROOT / "apercu_trilogie_zenith_v1.html").read_text(encoding="utf-8")
        self.assertIn("Trilogie du Zénith", gallery)
        for item in self.manifest["maps"]:
            self.assertIn(item["preview"], gallery)
            self.assertIn(item["delivery_zip"], gallery)
            self.assertIn(item["pmdo_zip"], gallery)


if __name__ == "__main__":
    unittest.main()
