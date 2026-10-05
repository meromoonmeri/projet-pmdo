#!/usr/bin/env python3
"""Tests d'intégrité pour `fin_bassin_chauffant_v1` (FBC1)."""
from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import unittest
import zipfile

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
RENDERS = ROOT / "renders" / "fin_bassin_chauffant_v1"


class TestFinBassinChauffant(unittest.TestCase):
    def test_01_dimensions_and_manifest(self) -> None:
        m = json.loads((RENDERS / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(m["prefix"], "FBC1")
        self.assertEqual(m["dimensions_px"], [768, 576])
        self.assertEqual(m["dimensions_tiles"], [96, 72])
        self.assertFalse(m["art_approved"])
        self.assertFalse(m["runtime_tested"])
        for k, info in m["fidelity"].items():
            self.assertLess(info["rgb_distance"], 35.0, f"Distance RGB trop élevée pour {k}: {info}")

    def test_02_sanctuary_and_closed_north_arena(self) -> None:
        sanct = np.asarray(Image.open(RENDERS / "layers" / "FBC1_10_sanctuaire.png").convert("RGBA"))
        self.assertGreater(int((sanct[..., 3] > 0).sum()), 8000)
        from source.fin_bassin_chauffant_v1.build import build_collision_grid
        grid = build_collision_grid()
        # Impasse nord : aucune case marchable sur le bord nord y=0..25
        self.assertEqual(int((grid[:26, :] == 0).sum()), 0)
        # Connectivité BFS : entrance [384, 560] -> boss [384, 312] -> objectif [384, 232]
        start = (560 // 8, 384 // 8)
        boss = (312 // 8, 384 // 8)
        obj = (232 // 8, 384 // 8)
        self.assertEqual(grid[start], 0)
        self.assertEqual(grid[boss], 0)
        self.assertEqual(grid[obj], 0)
        q = deque([start])
        seen = {start}
        while q:
            y, x = q.popleft()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < 72 and 0 <= nx < 96 and grid[ny, nx] == 0 and (ny, nx) not in seen:
                    seen.add((ny, nx))
                    q.append((ny, nx))
        self.assertIn(boss, seen)
        self.assertIn(obj, seen)

    def test_03_thermal_water_leaves_and_steam(self) -> None:
        eau0 = np.asarray(Image.open(RENDERS / "anim" / "FBC1_01_eau_thermale_f00.png").convert("RGBA"))
        eau1 = np.asarray(Image.open(RENDERS / "anim" / "FBC1_01_eau_thermale_f01.png").convert("RGBA"))
        fl0 = np.asarray(Image.open(RENDERS / "anim" / "FBC1_03_feuilles_f00.png").convert("RGBA"))
        vp0 = np.asarray(Image.open(RENDERS / "anim" / "FBC1_11_vapeur_f00.png").convert("RGBA"))
        vp6 = np.asarray(Image.open(RENDERS / "anim" / "FBC1_11_vapeur_f06.png").convert("RGBA"))
        self.assertGreater(int((eau0[..., 3] > 0).sum()), 30000)
        self.assertGreater(int(np.abs(eau0.astype(int) - eau1.astype(int)).sum()), 1000)
        self.assertGreater(int((fl0[..., 3] > 0).sum()), 150)
        self.assertGreater(int((vp0[..., 3] > 0).sum()), 500)
        self.assertGreater(int(np.abs(vp0.astype(int) - vp6.astype(int)).sum()), 1000)

    def test_04_ora_and_pmdo_packages(self) -> None:
        ora = RENDERS / "FBC1_fin_bassin_chauffant.ora"
        self.assertTrue(ora.is_file())
        mod_zip = ROOT / "mod_fin_bassin_chauffant_pmdo_0812.zip"
        self.assertTrue(mod_zip.is_file())
        with zipfile.ZipFile(mod_zip) as zf:
            names = zf.namelist()
            self.assertTrue(any(n.endswith(".rsground") for n in names))
            self.assertTrue(any(n.endswith(".tile") for n in names))


if __name__ == "__main__":
    unittest.main()
