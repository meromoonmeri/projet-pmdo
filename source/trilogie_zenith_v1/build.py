#!/usr/bin/env python3
"""Régénère le manifeste de la Trilogie du Zénith à partir des trois lots."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "renders/trilogie_zenith_v1"

MAPS = (
    ("entrée", "entree_ile_zenith_v1", "apercu_entree_ile_zenith_v1.html",
     "livrable_entree_ile_zenith_v1.zip", "mod_entree_ile_zenith_pmdo_0812.zip"),
    ("chemin", "ile_flottante_zenith_v1", "apercu_ile_flottante_zenith_v1.html",
     "livrable_ile_flottante_zenith_v1.zip", "mod_ile_flottante_zenith_pmdo_0812.zip"),
    ("fin", "fin_ile_zenith_v1", "apercu_fin_ile_zenith_v1.html",
     "livrable_fin_ile_zenith_v1.zip", "mod_fin_ile_zenith_pmdo_0812.zip"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def build() -> dict[str, object]:
    gallery = ROOT / "apercu_trilogie_zenith_v1.html"
    if not gallery.is_file():
        raise FileNotFoundError(gallery)
    items: list[dict[str, object]] = []
    for role, folder, preview, delivery, pmdo in MAPS:
        manifest_path = ROOT / "renders" / folder / "manifest.json"
        delivery_path, pmdo_path = ROOT / delivery, ROOT / pmdo
        for path in (manifest_path, ROOT / preview, delivery_path, pmdo_path):
            if not path.is_file():
                raise FileNotFoundError(path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["dimensions_px"] != [768, 576]:
            raise ValueError(f"Format inattendu pour {folder}")
        if manifest["walkable_cells"] != manifest["reachable_cells_from_entry"]:
            raise ValueError(f"Collision non connexe pour {folder}")
        items.append({
            "role": role,
            "prefix": manifest["prefix"],
            "map_id": manifest["map_id"],
            "title": manifest["title"],
            "dimensions_px": manifest["dimensions_px"],
            "walkable_cells": manifest["walkable_cells"],
            "reachable_cells": manifest["reachable_cells_from_entry"],
            "animations": manifest["animation"],
            "total_tiles": manifest["total_tiles"],
            "fidelity": manifest["fidelity"],
            "preview": preview,
            "delivery_zip": delivery,
            "delivery_sha256": sha256(delivery_path),
            "pmdo_zip": pmdo,
            "pmdo_sha256": sha256(pmdo_path),
            "art_approved": manifest["art_approved"],
            "runtime_tested": manifest["runtime_tested"],
        })
    result: dict[str, object] = {
        "series_id": "trilogie_zenith_v1",
        "title": "Trilogie du Zénith",
        "reference": "Final Island (Red Rescue Team)",
        "roles": ["entrée", "chemin", "fin"],
        "maps": items,
        "notes": [
            "Compositions générées référencées et quantifiées, non certifiées comme tuiles natives.",
            "Animations calculées indépendamment pour chaque lot.",
            "Aucun runtime PMDO, rendu GPU ou gameplay testé.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE / "README.md", OUT / "README.md")
    (OUT / "manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("[TRILOGIE_ZENITH] OK:", ", ".join(item["prefix"] for item in items))
    return result


if __name__ == "__main__":
    build()
