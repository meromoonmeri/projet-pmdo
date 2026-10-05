#!/usr/bin/env python3
"""Tests d'intégrité pour `entree_bassin_chauffant_sud_nord_v1` (EBC1)."""
from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import unittest
import zipfile

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
RENDERS = ROOT / "renders" / "entree_bassin_chauffant_sud_nord_v1"
CACHE = ROOT / "source" / "entree_bassin_chauffant_sud_nord_v1" / ".cache"


class TestEntreeBassinChauffant(unittest.TestCase):
    def test_01_dimensions_and_manifest(self) -> None:
        m = json.loads((RENDERS / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(m["prefix"], "EBC1")
        self.assertEqual(m["dimensions_px"], [768, 576])
        self.assertEqual(m["dimensions_tiles"], [96, 72])
        self.assertFalse(m["art_approved"])
        self.assertFalse(m["runtime_tested"])

    def test_02_rgb_fidelity_under_35(self) -> None:
        m = json.loads((RENDERS / "manifest.json").read_text(encoding="utf-8"))
        for k, info in m["fidelity"].items():
            self.assertLess(info["rgb_distance"], 35.0, f"Distance RGB trop élevée pour {k}: {info}")

    def test_03_thermal_water_and_no_white_shore_lip(self) -> None:
        eau0 = np.asarray(Image.open(RENDERS / "anim" / "EBC1_01_eau_thermale_f00.png").convert("RGBA"))
        eau1 = np.asarray(Image.open(RENDERS / "anim" / "EBC1_01_eau_thermale_f01.png").convert("RGBA"))
        self.assertEqual(eau0.shape, (576, 768, 4))
        mask = eau0[..., 3] > 0
        self.assertGreater(int(mask.sum()), 20000)
        self.assertGreater(int(np.abs(eau0.astype(int) - eau1.astype(int)).sum()), 1000)
        # L'eau thermale est dorée-ocre (R > G > B) et sans trait blanc (pas de pixel > 225)
        mean_rgb = eau0[mask, :3].mean(0)
        self.assertGreater(mean_rgb[0], mean_rgb[1] + 15)
        self.assertGreater(mean_rgb[1], mean_rgb[2] + 60)
        self.assertEqual(int((eau0[mask, 2] > 140).sum()), 0)

    def test_04_leaves_and_steam_animations(self) -> None:
        fl0 = np.asarray(Image.open(RENDERS / "anim" / "EBC1_03_feuilles_f00.png").convert("RGBA"))
        fl6 = np.asarray(Image.open(RENDERS / "anim" / "EBC1_03_feuilles_f06.png").convert("RGBA"))
        vp0 = np.asarray(Image.open(RENDERS / "anim" / "EBC1_11_vapeur_f00.png").convert("RGBA"))
        vp6 = np.asarray(Image.open(RENDERS / "anim" / "EBC1_11_vapeur_f06.png").convert("RGBA"))
        self.assertGreater(int((fl0[..., 3] > 0).sum()), 150)
        self.assertGreater(int(np.abs(fl0.astype(int) - fl6.astype(int)).sum()), 500)
        self.assertGreater(int((vp0[..., 3] > 0).sum()), 400)
        self.assertGreater(int(np.abs(vp0.astype(int) - vp6.astype(int)).sum()), 1000)

    def test_05_bfs_connectivity_south_to_geyser_threshold(self) -> None:
        # Vérifier la connectivité piétonne de entrance [384, 560] à donjon_seuil [384, 152]
        # et qu'aucune eau ne bloque le seuil de la caverne au nord
        eau0 = np.asarray(Image.open(RENDERS / "anim" / "EBC1_01_eau_thermale_f00.png").convert("RGBA"))
        seuil_patch = eau0[130:175, 355:415, 3]
        self.assertEqual(int((seuil_patch > 0).sum()), 0, "Aucune eau ne doit bloquer le seuil de la caverne")

        from source.entree_bassin_chauffant_sud_nord_v1.build import build_collision_grid
        grid = build_collision_grid()
        start = (560 // 8, 384 // 8)
        goal = (152 // 8, 384 // 8)
        self.assertEqual(grid[start], 0)
        self.assertEqual(grid[goal], 0)
        q = deque([start])
        seen = {start}
        while q:
            y, x = q.popleft()
            if (y, x) == goal:
                break
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < 72 and 0 <= nx < 96 and grid[ny, nx] == 0 and (ny, nx) not in seen:
                    seen.add((ny, nx))
                    q.append((ny, nx))
        self.assertIn(goal, seen)

    def test_06_ora_and_pmdo_packages(self) -> None:
        ora = RENDERS / "EBC1_entree_bassin_chauffant.ora"
        self.assertTrue(ora.is_file())
        with zipfile.ZipFile(ora) as zf:
            self.assertEqual(zf.read("mimetype").decode("utf-8"), "image/openraster")
        mod_zip = ROOT / "mod_entree_bassin_chauffant_sud_nord_pmdo_0812.zip"
        self.assertTrue(mod_zip.is_file())
        with zipfile.ZipFile(mod_zip) as zf:
            names = zf.namelist()
            self.assertTrue(any(n.endswith(".rsground") for n in names))
            self.assertTrue(any(n.endswith(".tile") for n in names))


if __name__ == "__main__":
    unittest.main()
