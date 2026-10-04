#!/usr/bin/env python3
"""Extrait l'atlas de petits tiles d'eau animés de la référence canonique T00P01.

Pré-requis : cache ROM préparé par source/outil_maps_pmdsky/recuperer_maps.py
et skytemple-files installé dans le .venv du dépôt.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MAP_BG = ROOT / ".cache/pmd-sky/files/MAP_BG"
OUT = HERE / "reference/T00P01_eau_atlas.npz"
META = HERE / "reference/T00P01_eau_atlas.json"
SOURCE_COMMIT = "c8073235b39746a7ee74e6cea16c730bd91a1e67"


def load_etude():
    path = ROOT / "source/etude_animations_canoniques_sky_v1/etude.py"
    spec = importlib.util.spec_from_file_location("zgt1_animation_etude", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Impossible de charger {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def extract() -> dict[str, object]:
    if not MAP_BG.is_dir():
        raise FileNotFoundError(
            f"Cache ROM absent : {MAP_BG}. Lancez d'abord "
            "source/outil_maps_pmdsky/recuperer_maps.py rom --only T00P01."
        )
    etude = load_etude()
    sky = etude.SkyMap(MAP_BG, "t00p01")
    if sky.loop != 72 or sky.specs != [(2, 6, 4, 0)] or sky.bpa_durs != [6] * 6:
        raise ValueError(
            f"Animation T00P01 inattendue : loop={sky.loop}, "
            f"palettes={sky.specs}, BPA={sky.bpa_durs}"
        )

    # Les crans BPL (4 ticks) et BPA (6 ticks) ne changent qu'à des ticks pairs.
    # Un échantillon tous les 2 ticks, FrameLength=2 dans PMDO, reproduit donc
    # exactement la séquence de couleur des pixels extraits sur la boucle de 72 ticks.
    ticks = np.arange(0, sky.loop, 2, dtype=np.uint16)
    frames = np.stack([sky.frame(int(t)) for t in ticks]).astype(np.uint8)
    rgb = frames[0].astype(np.int16)
    r, g, b = rgb.transpose(2, 0, 1)
    blue = (b > r + 30) & (b > g + 15) & (b > 80)
    labels, count = ndi.label(blue)
    component_sizes = np.bincount(labels.ravel())
    river_ids = [
        int(i)
        for i in np.argsort(component_sizes[1:])[::-1][:2] + 1
        if component_sizes[i] >= 5_000
    ]
    if len(river_ids) != 2:
        raise ValueError(f"T00P01 : deux segments de canal attendus, trouvés {river_ids}")
    river = np.isin(labels, river_ids)

    # Tuiles d'origine alignées sur la grille 8x8, entièrement dans l'eau du canal.
    candidates: list[tuple[int, int]] = []
    height, width = river.shape
    for y in range(0, height - 7, 8):
        for x in range(0, min(width, 320) - 7, 8):
            if float(river[y : y + 8, x : x + 8].mean()) >= 0.95:
                candidates.append((x, y))

    # Déduplique les séquences complètes, et non seulement leur image au tick zéro :
    # les pixels qui cyclent restent donc alignés entre toutes les phases.
    seen: set[bytes] = set()
    coords: list[tuple[int, int]] = []
    tiles: list[np.ndarray] = []
    for x, y in candidates:
        sequence = frames[:, y : y + 8, x : x + 8, :]
        key = hashlib.sha256(sequence.tobytes()).digest()
        if key not in seen:
            seen.add(key)
            coords.append((x, y))
            tiles.append(sequence)
    if len(tiles) < 4:
        raise ValueError(f"Atlas d'eau insuffisant : {len(tiles)} motifs uniques")

    atlas = np.stack(tiles, axis=1).astype(np.uint8)  # (36 phases, N motifs, 8, 8, RGB)
    input_names = ["t00p01.bma", "t00p01.bpc", "t00p01.bpl", "t00p011.bpa"]
    source_hashes = {name: sha256(MAP_BG / name) for name in input_names}
    metadata: dict[str, object] = {
        "reference": "T00P01",
        "source_repository": "pret/pmd-sky",
        "source_commit": SOURCE_COMMIT,
        "source_files_sha256": source_hashes,
        "reference_png": "T00P01_canonique.png",
        "source_animation": {
            "palette_index": 2,
            "palette_frames": 6,
            "palette_duration_ticks": 4,
            "bpa_frames": 6,
            "bpa_duration_ticks": 6,
            "loop_ticks": int(sky.loop),
            "sample_ticks": [int(t) for t in ticks],
            "pmdo_frame_length": 2,
            "timing_note": "Les changements BPL/BPA tombent tous sur des ticks pairs; 36 phases x 2 ticks reproduisent la boucle de 72 ticks.",
        },
        "selection": {
            "method": "Tuiles 8x8 entièrement dans les deux composantes bleues du canal; séquences de 36 phases dédupliquées.",
            "source_tile_coordinates_px": [list(p) for p in coords],
            "unique_sequences": len(coords),
            "candidate_tiles": len(candidates),
            "pixels_are_direct_source_samples": True,
        },
        "atlas_sha256": None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT,
        tiles=atlas,
        source_coords=np.asarray(coords, dtype=np.uint16),
        ticks=ticks,
    )
    metadata["atlas_sha256"] = sha256(OUT)
    META.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return metadata


if __name__ == "__main__":
    result = extract()
    print(
        f"Atlas {OUT.relative_to(ROOT)} : {result['selection']['unique_sequences']} motifs, "
        f"36 phases, boucle {result['source_animation']['loop_ticks']} ticks."
    )
