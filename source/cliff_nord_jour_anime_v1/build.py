#!/usr/bin/env python3
"""
Rebuild the canonical PMD Sky Port sea animation and cloud wrap overlay for:
  - cliffnordouesttest1.rsground (138x98 cells = 1104x784 px)
  - cliffdaytest.rsground        (123x99 cells = 984x792 px)

Strict constraints enforced by this script:
1. Root files `/cliffnordouesttest1.rsground` and `/cliffdaytest.rsground` remain
   100% untouched (verified by SHA-256 before and after).
2. NO cliff layer, object layer, or existing object/waterfall animation is modified,
   renamed, split, or re-ordered:
   - In `cliffnordouesttest1.rsground`:
     * `Layers[2]` (`New Layer`: `terrain`, `Metano_Altere_Transition_Base`,
       `terrain (4)`, `terrain (3)`, `terrain (2)`, `INVERSEPATHWAY`) is 100% untouched.
     * `Layers[3]` (`Layer 3`: `INVERSEPATHWAY`, `Metano_Town_Animation_Tileset`) is 100% untouched.
     * `Layers[1]` (`Layer 1`): the 1 cell `(10, 86)` referencing `Altere_Pond_Cliffs` is 100% untouched.
   - In `cliffdaytest.rsground`:
     * `Layers[2]` (`Layer 2`: `13_avancee_basse_gauche_terrain`, `Metano_Town_Cliffs`,
       `INVERSEPATHWAY`, `CLIFF MIROR-Photoroom`) is 100% untouched.
     * `Layers[3]` (`Layer 4`: `Metano_Town_Objects`) is 100% untouched.
     * `Layers[4]` (`Layer 3`: `P01P01A_layer1`, `Metano_Town_Animation_Tileset`,
       `CanyonCamp`, `Metano_Town_Animated`, `Metano_Town_Objects`) is 100% untouched.
     * `Layers[0]` (`New Layer`): the 1 cell of `Altere_Pond_Cliffs` and 4 cells of
       `CanyonCamp` are 100% untouched.
     * `Layers[5]` (`Cloud/nuage`): all 325 object cells (`Altere_Pond_Objects`,
       `Altere_Pond_Objects_Under`, `Metano_Town_Objects`, `Metano_Town_Trimmed`,
       `Metano_Inn_Objects`) remain 100% untouched in place on `Layers[5]`.
   - No `.tile` files are generated for cliff/terrain/object sheets: ONLY
     `Content/Tile/v2_promontoire_jour_03.tile` (the animated sea bank) is shipped.
3. Cloud wrap overlay:
   - Configured natively in `Object["Background"]` as `RogueEssence.Dungeon.LayeredBG, RogueEssence`
     with static sky (`CLIFF_NORD_OUEST_CIEL` / `CLIFF_DAY_CIEL`, `RepeatX = False`,
     `BGMovement = {"X": 0, "Y": 0}`) followed by the wrapping cloud overlay
     (`CLIFF_NORD_OUEST_NUAGES` / `CLIFF_DAY_NUAGES`, `RepeatX = True`, `RepeatY = False`,
     `BGMovement = {"X": -4, "Y": 0}`, `Parallax = "1, 1"`).
   - Static `00_ciel` cells on `Layers[0]` and static `01_long_cap_jour_02` cloud cells
     on `Layers[5]` are cleared so `LayeredBG` is visible behind the tile layers without
     static cloud duplication.
4. Canonical PMD Sky Port (`source/falaises_cotieres_nues/reference_ciel_mer.png`,
   Pelipper Post Office) sea animation on `Layers[1]`:
   - Extracts all 5 canonical `far_sea` wave strips (`(544+56*f, 224, 592+56*f, 352)`,
     `48x128` px) and all 10 canonical `near_sea` wave strips (`(824+56*f, 224, 872+56*f, 392)`,
     `48x168` px) from `reference_ciel_mer.png`.
   - Reconstructs the 10-frame canonical `1312x1024` px sea sheet series (`f = 0..9`,
     where frame 0 is pixel-identical across all `1312x1024` pixels to
     `sprites/cote_dix_zones/fonds/jour_mer_00.png` = `v2_promontoire_jour_03`).
   - Encodes `Content/Tile/v2_promontoire_jour_03.tile` in native RogueEssence `TileSheet`
     binary format (via `source/pmdo_cote/build.py`), keeping Phase 0 at its exact `(tx, ty)`
     coordinates in `ty = 0..127` and deduplicating Phases `1..9` at `ty >= 128`, and
     animates every `v2_promontoire_jour_03` cell on `Layers[1]` across the 10 frames
     (`FrameLength = 10` ticks = 166.7 ms/phase at 60 Hz).
"""

from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import io
import json
import shutil
import struct
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RENDERS = ROOT / "renders/cliff_nord_jour_anime_v1"

EXPECTED_ROOT_SHA256 = {
    "cliffnordouesttest1.rsground": "2cb10918d6bfa8ed687c1412b2d2e7c4aebc545049b9d2d76eb7c16fdb632f19",
    "cliffdaytest.rsground": "6567e19df7a073758d8d52ad1491460067a2dccc1c0d03aa0d1c72b5592e4d2f",
}

REF_PELIPPER_PATH = ROOT / "source/falaises_cotieres_nues/reference_ciel_mer.png"
REF_PELIPPER_SHA256 = "f2de3cabdc6edafbdcebeeee1fd9cb3ee6f6bf2ffcf7ae1b6d3c749e13d1c456"
MER00_PATH = ROOT / "sprites/cote_dix_zones/fonds/jour_mer_00.png"
NUAGES_PATH = ROOT / "sprites/cote_dix_zones/fonds/jour_nuages.png"
FALAISE_CIEL_PATH = ROOT / "source/cote_dix_zones/reference_autre_agent/source__falaise__ciel_jour_native.png"

SEA_BANK_NAME = "v2_promontoire_jour_03"
SEA_FRAME_COUNT = 10
SEA_FRAME_LENGTH = 10  # 10 ticks at 60 Hz = 166.67 ms/frame (1.667 s per 10-frame loop)
CLOUD_SPEED_PX_S = -4


def loadmod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_root_immutability() -> None:
    for filename, expected in EXPECTED_ROOT_SHA256.items():
        actual = sha256_file(ROOT / filename)
        assert actual == expected, f"Root file {filename} modified: {actual} != {expected}"


def premult_arr(arr: np.ndarray) -> np.ndarray:
    a = arr.astype(np.uint16)
    a[:, :, :3] = (a[:, :, :3] * a[:, :, 3:4]) // 255
    return a.astype(np.uint8)


def save_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGBA").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(save_png_bytes(image))


def load_tile_subset(path: Path, wanted_coords: set[tuple[int, int]] | None = None) -> dict[tuple[int, int], np.ndarray]:
    """Decode only `wanted_coords` from a native PMDO `.tile` file -> {(tx, ty): ndarray(8,8,4)}."""
    with path.open("rb") as f:
        ts, cnt = struct.unpack("<ii", f.read(8))
        assert ts == 8, f"Unexpected tile size {ts} in {path}"
        entries = [struct.unpack("<iiq", f.read(16)) for _ in range(cnt)]
        tiles: dict[tuple[int, int], np.ndarray] = {}
        for x, y, off in entries:
            if wanted_coords is not None and (x, y) not in wanted_coords:
                continue
            f.seek(off)
            (ln,) = struct.unpack("<q", f.read(8))
            im = Image.open(io.BytesIO(f.read(ln))).convert("RGBA")
            tiles[(x, y)] = np.array(im)
    return tiles


def build_canonical_pmdsky_sea_sheets() -> tuple[list[np.ndarray], dict]:
    """
    Build the 10 canonical 1312x1024 sea sheets from PMD Sky Pelipper Post Office
    (`source/falaises_cotieres_nues/reference_ciel_mer.png`) in the exact coordinate
    space of `v2_promontoire_jour_03` (`sprites/cote_dix_zones/fonds/jour_mer_00.png`).

    - `far_sea` has 5 canonical 48x128 strips at (544+56*f, 224, 592+56*f, 352) -> placed at y=144..272 (ty=18..33)
    - `near_sea` has 10 canonical 48x168 strips at (824+56*f, 224, 872+56*f, 392) -> placed at y=272..1024 (ty>=34)
    - Frame 0 (`far_idx=0, near_idx=0`) is 100% pixel-identical to `jour_mer_00.png` (`v2_promontoire_jour_03`).
    """
    ref = Image.open(REF_PELIPPER_PATH).convert("RGBA")
    fars = [ref.crop((544 + 56 * f, 224, 592 + 56 * f, 352)) for f in range(5)]
    nears = [ref.crop((824 + 56 * f, 224, 872 + 56 * f, 392)) for f in range(10)]

    w, h, out_h = 1312, 816, 1024
    horizon_v1 = 208
    sheets: list[np.ndarray] = []

    for f in range(SEA_FRAME_COUNT):
        far_strip = fars[f % 5]
        near_strip = nears[f]
        layer = Image.new("RGBA", (w, h))
        for xx in range(0, w, 48):
            layer.paste(far_strip, (xx, horizon_v1))
        for yy in range(horizon_v1 + 128, h, 168):
            for xx in range(0, w, 48):
                layer.paste(near_strip, (xx, yy))

        # Apply exact V2 promontoire shift (+152 px) and cote_dix_zones row mapping (+216 px)
        sea_v2 = Image.new("RGBA", (w, h))
        sea_v2.paste(layer, (0, 152))
        a = np.array(sea_v2)
        rows = np.arange(out_h) + 216
        rows[rows >= h] = h - 256 + (rows[rows >= h] - h) % 256
        moved = a[rows, :w].copy()
        moved[:144] = 0
        sheets.append(moved)

    mer00 = np.array(Image.open(MER00_PATH).convert("RGBA"))
    diff0 = int(np.max(np.abs(sheets[0].astype(int) - mer00.astype(int))))
    assert diff0 == 0, f"Frame 0 differs from jour_mer_00.png by {diff0}"

    far_hashes = {hashlib.sha256(sheets[f][144:272].tobytes()).hexdigest() for f in range(5)}
    near_hashes = {hashlib.sha256(sheets[f][272:440].tobytes()).hexdigest() for f in range(10)}
    assert len(far_hashes) == 5, f"Expected 5 distinct far_sea frames, got {len(far_hashes)}"
    assert len(near_hashes) == 10, f"Expected 10 distinct near_sea frames, got {len(near_hashes)}"

    info = {
        "reference_path": "source/falaises_cotieres_nues/reference_ciel_mer.png",
        "reference_sha256": sha256_file(REF_PELIPPER_PATH),
        "far_sea_rects": [[544 + 56 * f, 224, 592 + 56 * f, 352] for f in range(5)],
        "near_sea_rects": [[824 + 56 * f, 224, 872 + 56 * f, 392] for f in range(10)],
        "far_sea_distinct_frames": len(far_hashes),
        "near_sea_distinct_frames": len(near_hashes),
        "total_animation_frames": SEA_FRAME_COUNT,
        "frame_length_ticks_60hz": SEA_FRAME_LENGTH,
        "frame_0_max_diff_vs_v2_promontoire_jour_03": diff0,
    }
    return sheets, info


def build_pmdo_sea_bank(gfx, sea_sheets: list[np.ndarray], needed_coords: set[tuple[int, int]]):
    """
    Build `v2_promontoire_jour_03.tile` using `source/pmdo_cote/build.py`'s native `TileBank`:
    - Preserves Phase 0 at the exact `(tx, ty)` coordinates in `ty = 0..127` for every
      `(tx, ty)` referenced by `cliffnordouesttest1` and `cliffdaytest`.
    - Deduplicates Phases `1..9` at `ty >= 128` (`cols = 32`).
    """
    bank = gfx.TileBank(SEA_BANK_NAME, preserve_layout=True)
    pm_sheets = [premult_arr(s) for s in sea_sheets]

    p0_locs: dict[tuple[int, int], dict] = {}
    a0 = pm_sheets[0]
    for tx, ty in sorted(needed_coords):
        blk = a0[ty * 8 : (ty + 1) * 8, tx * 8 : (tx + 1) * 8]
        assert blk[:, :, 3].any(), f"Empty sea tile at {(tx, ty)}"
        raw = blk.tobytes()
        bank.data[(tx, ty)] = raw
        bank.ids.setdefault(raw, (tx, ty))
        p0_locs[(tx, ty)] = {"Sheet": bank.name, "TexLoc": {"X": tx, "Y": ty}}

    next_idx = 0
    phase_locs: list[dict[tuple[int, int], dict]] = [p0_locs]
    for f in range(1, SEA_FRAME_COUNT):
        af = pm_sheets[f]
        ploc: dict[tuple[int, int], dict] = {}
        for tx, ty in sorted(needed_coords):
            blk = af[ty * 8 : (ty + 1) * 8, tx * 8 : (tx + 1) * 8]
            raw = blk.tobytes()
            if raw not in bank.ids:
                loc = (next_idx % 32, 128 + next_idx // 32)
                next_idx += 1
                bank.ids[raw] = loc
                bank.data[loc] = raw
            loc = bank.ids[raw]
            ploc[(tx, ty)] = {"Sheet": bank.name, "TexLoc": {"X": loc[0], "Y": loc[1]}}
        phase_locs.append(ploc)

    return bank, phase_locs


def build_sky_source_504x408() -> np.ndarray:
    im = Image.open(FALAISE_CIEL_PATH).convert("RGBA")
    arr = np.array(im)
    assert arr.shape == (408, 480, 4)
    col = arr[:, -1:, :]
    pad = np.repeat(col, 504 - 480, axis=1)
    out = np.concatenate([arr, pad], axis=1)
    assert out.shape == (408, 504, 4)
    return out


def reconstruct_map_sky_from_layer0(doc: dict, sky_src: np.ndarray, fill_top_with_row0: bool = True) -> Image.Image:
    l0 = doc["Object"]["Layers"][0]
    w_cells, h_cells = len(l0["Tiles"]), len(l0["Tiles"][0])
    canvas = np.zeros((h_cells * 8, w_cells * 8, 4), dtype=np.uint8)
    if fill_top_with_row0:
        canvas[: 26 * 8, :, :] = sky_src[0, 0]
    for x in range(w_cells):
        for y in range(h_cells):
            for tl in l0["Tiles"][x][y]["Layers"]:
                for f in tl["Frames"]:
                    if f["Sheet"] == "00_ciel":
                        tx, ty = f["TexLoc"]["X"], f["TexLoc"]["Y"]
                        canvas[y * 8 : (y + 1) * 8, x * 8 : (x + 1) * 8] = sky_src[
                            ty * 8 : (ty + 1) * 8, tx * 8 : (tx + 1) * 8
                        ]
    return Image.fromarray(canvas, "RGBA")


def reconstruct_cliffdaytest_cloud_strip(doc: dict) -> Image.Image:
    nuages_src = np.array(Image.open(NUAGES_PATH).convert("RGBA"))
    l5 = doc["Object"]["Layers"][5]
    w_cells = len(l5["Tiles"])
    h_strip_cells = 39  # y=0..38 (312 px, right down to the horizon)
    canvas = np.zeros((h_strip_cells * 8, w_cells * 8, 4), dtype=np.uint8)
    count = 0
    for x in range(w_cells):
        for y in range(len(l5["Tiles"][0])):
            for tl in l5["Tiles"][x][y]["Layers"]:
                for f in tl["Frames"]:
                    if f["Sheet"] == "01_long_cap_jour_02":
                        assert y < h_strip_cells
                        tx, ty = f["TexLoc"]["X"], f["TexLoc"]["Y"]
                        canvas[y * 8 : (y + 1) * 8, x * 8 : (x + 1) * 8] = nuages_src[
                            ty * 8 : (ty + 1) * 8, tx * 8 : (tx + 1) * 8
                        ]
                        count += 1
    assert count == 600, f"Expected 600 cloud cells in cliffdaytest, got {count}"
    assert int(np.sum(canvas[:, 0, 3])) == 0 and int(np.sum(canvas[:, -1, 3])) == 0
    return Image.fromarray(canvas, "RGBA")


def load_repo_preview_sheets(docs: list[dict]) -> dict[str, dict[tuple[int, int], np.ndarray] | np.ndarray]:
    """
    Load canonical `.tile` and `.png` sheets available in the repo ONLY in memory
    for rendering preview images in `renders/` and `apercu_cliff_nord_jour_anime_v1.html`.
    Never writes `.tile` files for cliff/terrain/object sheets.
    """
    needed_by_sheet: dict[str, set[tuple[int, int]]] = {}
    for doc in docs:
        for layer in doc["Object"]["Layers"]:
            for col in layer["Tiles"]:
                for cell in col:
                    for tl in cell["Layers"]:
                        for f in tl["Frames"]:
                            needed_by_sheet.setdefault(f["Sheet"], set()).add(
                                (f["TexLoc"]["X"], f["TexLoc"]["Y"])
                            )

    repo_tile_sources = {
        "Altere_Pond_Cliffs": ROOT / "source/antre_harmonie_v3/references/Altere_Pond_Cliffs.tile",
        "Altere_Pond_Objects": ROOT / "source/antre_harmonie_v3/references/Altere_Pond_Objects.tile",
        "Altere_Pond_Objects_Under": ROOT / "source/antre_harmonie_v3/references/Altere_Pond_Objects_Under.tile",
        "Metano_Inn_Objects": ROOT / "source/cafe_spinda_revisite_v7/references/Metano_Inn_Objects.tile",
        "Metano_Town_Animation_Tileset": ROOT / "source/eau_metano/natifs/Metano_Town_Animation_Tileset.tile",
        "Metano_Town_Cliffs": ROOT / "source/falaises_metano/natifs/Metano_Town_Cliffs.tile",
        "Metano_Town_Objects": ROOT / "source/amp_plains_fleurie_v1/references/Metano_Town_Objects.tile",
    }
    sheets: dict[str, dict[tuple[int, int], np.ndarray] | np.ndarray] = {}
    for sname, spath in repo_tile_sources.items():
        if spath.exists() and sname in needed_by_sheet:
            sheets[sname] = load_tile_subset(spath, needed_by_sheet[sname])

    repo_png_sources = {
        "13_avancee_basse_gauche_terrain": ROOT / "renders/caps_terrasses_v4/13_avancee_basse_gauche_terrain.png",
        "terrain": ROOT / "renders/references_calques_v2/falaises/02/terrain.png",
        "terrain (2)": ROOT / "renders/references_calques_v2/falaises/01/terrain.png",
        "terrain (3)": ROOT / "renders/references_calques_v2/falaises/03/terrain.png",
        "terrain (4)": ROOT / "renders/references_calques_v2/falaises/08/terrain.png",
    }
    for sname, spath in repo_png_sources.items():
        if spath.exists():
            sheets[sname] = np.array(Image.open(spath).convert("RGBA"))
    return sheets


def render_untouched_layers_preview(
    doc: dict,
    layer_indices: list[int],
    repo_sheets: dict[str, dict[tuple[int, int], np.ndarray] | np.ndarray],
) -> Image.Image:
    layers = doc["Object"]["Layers"]
    w_cells, h_cells = len(layers[0]["Tiles"]), len(layers[0]["Tiles"][0])
    out = Image.new("RGBA", (w_cells * 8, h_cells * 8), (0, 0, 0, 0))
    for li in layer_indices:
        layer = layers[li]
        layer_im = Image.new("RGBA", (w_cells * 8, h_cells * 8), (0, 0, 0, 0))
        for x in range(w_cells):
            for y in range(h_cells):
                for tl in layer["Tiles"][x][y]["Layers"]:
                    if not tl["Frames"]:
                        continue
                    f0 = tl["Frames"][0]
                    sname = f0["Sheet"]
                    tx, ty = f0["TexLoc"]["X"], f0["TexLoc"]["Y"]
                    blk = None
                    if sname in repo_sheets:
                        src = repo_sheets[sname]
                        if isinstance(src, dict):
                            blk = src.get((tx, ty))
                        else:
                            if ty * 8 + 8 <= src.shape[0] and tx * 8 + 8 <= src.shape[1]:
                                blk = src[ty * 8 : (ty + 1) * 8, tx * 8 : (tx + 1) * 8]
                    if blk is not None and blk[:, :, 3].any():
                        layer_im.alpha_composite(Image.fromarray(blk, "RGBA"), (x * 8, y * 8))
        out = Image.alpha_composite(out, layer_im)
    return out


def render_sea_layer_frames(
    orig_sea_layer: dict,
    sea_sheets: list[np.ndarray],
    repo_sheets: dict[str, dict[tuple[int, int], np.ndarray] | np.ndarray],
) -> list[Image.Image]:
    """Render all 10 frames of `Layers[1]` (the sea layer) in unpremultiplied RGBA."""
    w_cells, h_cells = len(orig_sea_layer["Tiles"]), len(orig_sea_layer["Tiles"][0])
    frames: list[Image.Image] = []
    for f_idx in range(SEA_FRAME_COUNT):
        canvas = np.zeros((h_cells * 8, w_cells * 8, 4), dtype=np.uint8)
        sheet_arr = sea_sheets[f_idx]
        for x in range(w_cells):
            for y in range(h_cells):
                for tl in orig_sea_layer["Tiles"][x][y]["Layers"]:
                    if not tl["Frames"]:
                        continue
                    fr = tl["Frames"][0]
                    sname = fr["Sheet"]
                    tx, ty = fr["TexLoc"]["X"], fr["TexLoc"]["Y"]
                    if sname == "v2_promontoire_jour_03":
                        canvas[y * 8 : (y + 1) * 8, x * 8 : (x + 1) * 8] = sheet_arr[
                            ty * 8 : (ty + 1) * 8, tx * 8 : (tx + 1) * 8
                        ]
                    elif sname in repo_sheets:
                        src = repo_sheets[sname]
                        blk = src.get((tx, ty)) if isinstance(src, dict) else src[ty * 8 : (ty + 1) * 8, tx * 8 : (tx + 1) * 8]
                        if blk is not None:
                            canvas[y * 8 : (y + 1) * 8, x * 8 : (x + 1) * 8] = blk
        frames.append(Image.fromarray(canvas, "RGBA"))
    return frames


def render_cloud_wrap_at(strip: Image.Image, map_size: tuple[int, int], map_loc_y: int, shift_px: int) -> Image.Image:
    w, h = map_size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sw = strip.width
    start_x = (shift_px % sw) - sw
    for x in range(start_x, w, sw):
        out.alpha_composite(strip, (x, map_loc_y))
    return out


def transform_rsground(
    gfx,
    map_slug: str,
    orig_doc: dict,
    phase_locs: list[dict[tuple[int, int], dict]],
    sky_bg_name: str,
    cloud_bg_name: str,
    cloud_map_loc_y: int,
) -> tuple[dict, dict]:
    """
    Transform a copy of `orig_doc`:
    - Leave all cliff, object, and existing animation layers 100% untouched.
    - Enable the `LayeredBG` cloud wrap overlay (`RepeatX = True`, `BGMovement = (-4, 0)`).
    - Animate ONLY `v2_promontoire_jour_03` cells on `Layers[1]` using the 10-frame
      canonical PMD Sky Port (`reference_ciel_mer.png`) sea animation.
    """
    doc = copy.deepcopy(orig_doc)
    doc["Version"] = "0.8.12.0"
    obj = doc["Object"]

    # 1. Configure native LayeredBG (static sky + wrapping cloud overlay)
    obj["Background"] = {
        "$type": "RogueEssence.Dungeon.LayeredBG, RogueEssence",
        "Layers": [
            {"BG": gfx.background(sky_bg_name, 0, 0, False)},
            {"BG": gfx.background(cloud_bg_name, cloud_map_loc_y, CLOUD_SPEED_PX_S, True)},
        ],
    }

    # 2. Clear ONLY `00_ciel` cells on Layer 0 so Layer 0 does not occlude LayeredBG,
    #    preserving any cliff/camp cells (`Altere_Pond_Cliffs`, `CanyonCamp`) on Layer 0.
    l0 = obj["Layers"][0]
    w_cells, h_cells = len(l0["Tiles"]), len(l0["Tiles"][0])
    cleared_sky_cells = 0
    preserved_l0_cells = 0
    for x in range(w_cells):
        for y in range(h_cells):
            cell = l0["Tiles"][x][y]
            new_tls = []
            for tl in cell["Layers"]:
                kept_frames = [f for f in tl["Frames"] if f["Sheet"] != "00_ciel"]
                if len(kept_frames) < len(tl["Frames"]):
                    cleared_sky_cells += len(tl["Frames"]) - len(kept_frames)
                if kept_frames:
                    tl_copy = copy.deepcopy(tl)
                    tl_copy["Frames"] = kept_frames
                    new_tls.append(tl_copy)
                    preserved_l0_cells += len(kept_frames)
            cell["Layers"] = new_tls

    # 3. Animate ONLY `v2_promontoire_jour_03` cells on Layer 1 (mer), preserving any
    #    other sheet references (such as `Altere_Pond_Cliffs` at (10, 86) in cliffnordouesttest1).
    l1 = obj["Layers"][1]
    animated_sea_cells = 0
    preserved_l1_cells = 0
    for x in range(w_cells):
        for y in range(h_cells):
            cell = l1["Tiles"][x][y]
            for tl in cell["Layers"]:
                if len(tl["Frames"]) == 1 and tl["Frames"][0]["Sheet"] == "v2_promontoire_jour_03":
                    tx = tl["Frames"][0]["TexLoc"]["X"]
                    ty = tl["Frames"][0]["TexLoc"]["Y"]
                    tl["FrameLength"] = SEA_FRAME_LENGTH
                    tl["Frames"] = [phase_locs[f][(tx, ty)] for f in range(SEA_FRAME_COUNT)]
                    animated_sea_cells += 1
                else:
                    preserved_l1_cells += len(tl["Frames"])

    # 4. In cliffdaytest, clear ONLY `01_long_cap_jour_02` static cloud cells on Layer 5 (`Cloud/nuage`),
    #    preserving all 325 object cells (`Altere_Pond_Objects`, `Altere_Pond_Objects_Under`,
    #    `Metano_Town_Objects`, `Metano_Town_Trimmed`, `Metano_Inn_Objects`) untouched in place.
    cleared_cloud_cells = 0
    preserved_l5_object_cells = 0
    if len(obj["Layers"]) > 5:
        l5 = obj["Layers"][5]
        for x in range(w_cells):
            for y in range(h_cells):
                cell = l5["Tiles"][x][y]
                new_tls = []
                for tl in cell["Layers"]:
                    kept_frames = [f for f in tl["Frames"] if f["Sheet"] != "01_long_cap_jour_02"]
                    if len(kept_frames) < len(tl["Frames"]):
                        cleared_cloud_cells += len(tl["Frames"]) - len(kept_frames)
                    if kept_frames:
                        tl_copy = copy.deepcopy(tl)
                        tl_copy["Frames"] = kept_frames
                        new_tls.append(tl_copy)
                        preserved_l5_object_cells += len(kept_frames)
                cell["Layers"] = new_tls

    # 5. Strictly assert that ALL cliff, object, and existing animation layers are 100% untouched!
    untouched_indices = [2, 3] if map_slug == "cliffnordouesttest1" else [2, 3, 4]
    for idx in untouched_indices:
        assert obj["Layers"][idx] == orig_doc["Object"]["Layers"][idx], (
            f"{map_slug} Layer {idx} ({obj['Layers'][idx]['Name']}) was modified!"
        )
    assert [l["Name"] for l in obj["Layers"]] == [l["Name"] for l in orig_doc["Object"]["Layers"]]
    assert len(obj["Layers"]) == len(orig_doc["Object"]["Layers"])
    assert obj["obstacles"] == orig_doc["Object"]["obstacles"]
    assert obj["Entities"] == orig_doc["Object"]["Entities"]
    assert obj["Decorations"] == orig_doc["Object"]["Decorations"]

    stats = {
        "map_slug": map_slug,
        "dimensions_cells": [w_cells, h_cells],
        "dimensions_px": [w_cells * 8, h_cells * 8],
        "layer_count": len(obj["Layers"]),
        "layer_names": [l["Name"] for l in obj["Layers"]],
        "untouched_layer_indices": untouched_indices,
        "cleared_static_sky_cells_layer0": cleared_sky_cells,
        "preserved_non_sky_cells_layer0": preserved_l0_cells,
        "animated_sea_cells_layer1": animated_sea_cells,
        "preserved_non_sea_cells_layer1": preserved_l1_cells,
        "cleared_static_cloud_cells_layer5": cleared_cloud_cells,
        "preserved_object_cells_layer5": preserved_l5_object_cells,
        "background_layers": [
            {
                "anim_index": entry["BG"]["BGAnim"]["AnimIndex"],
                "map_loc": entry["BG"]["MapLoc"],
                "movement": entry["BG"]["BGMovement"],
                "repeat_x": entry["BG"]["RepeatX"],
                "repeat_y": entry["BG"]["RepeatY"],
                "parallax": entry["BG"]["Parallax"],
            }
            for entry in obj["Background"]["Layers"]
        ],
    }
    return doc, stats


def write_ora(path: Path, size: tuple[int, int], layers: list[tuple[str, Image.Image]]) -> None:
    w, h = size
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr("mimetype", b"image/openraster", compress_type=zipfile.ZIP_STORED)
        stack_xml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<image version="0.0.3" w="{w}" h="{h}" xres="72" yres="72">',
            ' <stack name="root">',
        ]
        for idx, (name, im) in enumerate(reversed(layers)):
            real_idx = len(layers) - 1 - idx
            rel = f"data/{real_idx:02d}_{name}.png"
            zf.writestr(rel, save_png_bytes(im))
            stack_xml.append(
                f'  <layer name="{name}" src="{rel}" x="0" y="0" opacity="1.0" visibility="visible" composite-op="svg:src-over"/>'
            )
        stack_xml.append(" </stack>")
        stack_xml.append("</image>")
        zf.writestr("stack.xml", "\n".join(stack_xml).encode("utf-8"))

        merged = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        for _, im in layers:
            merged = Image.alpha_composite(merged, im)
        zf.writestr("mergedimage.png", save_png_bytes(merged))
        thumb = merged.copy()
        thumb.thumbnail((256, 256), Image.Resampling.NEAREST)
        zf.writestr("Thumbnails/thumbnail.png", save_png_bytes(thumb))


def image_to_webp_data_uri(im: Image.Image) -> str:
    buf = io.BytesIO()
    im.convert("RGBA").save(buf, format="WEBP", lossless=True, exact=True, method=4)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def build_viewer_html(viewer_path: Path, maps_payload: list[dict], sea_info: dict) -> None:
    payload_json = json.dumps(
        {
            "maps": maps_payload,
            "sea_info": sea_info,
            "cloud_speed_px_s": CLOUD_SPEED_PX_S,
            "sea_frame_count": SEA_FRAME_COUNT,
            "sea_frame_length_ticks": SEA_FRAME_LENGTH,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    html = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cliff Nord Jour Animé · Mer canonique PMD Sky Port & Wrap Nuages</title>
<style>
:root {{
  color-scheme: dark;
  --bg: #0b1420;
  --panel: #132235;
  --line: #29425c;
  --text: #ebf1f5;
  --muted: #9cb3c9;
  --accent: #7fd4ff;
  --ok: #9be28f;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 14px/1.5 system-ui, -apple-system, sans-serif;
}}
header {{
  padding: 20px 28px;
  border-bottom: 1px solid var(--line);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}}
h1 {{ font-size: 22px; margin: 2px 0; }}
.eyebrow {{ font-size: 11px; letter-spacing: 1.8px; text-transform: uppercase; color: var(--accent); }}
.badge {{
  border: 1px solid var(--line);
  background: var(--panel);
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  color: var(--ok);
}}
main {{
  display: grid;
  grid-template-columns: 320px 1fr;
  min-height: calc(100vh - 85px);
}}
aside {{
  padding: 20px;
  border-right: 1px solid var(--line);
  background: var(--panel);
  display: flex;
  flex-direction: column;
  gap: 18px;
}}
.label {{
  display: block;
  font-size: 11px;
  letter-spacing: 1.3px;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 8px;
}}
select, button {{
  font: inherit;
  color: var(--text);
  background: #1b314a;
  border: 1px solid #355679;
  border-radius: 6px;
  padding: 8px 10px;
}}
select {{ width: 100%; }}
button {{ cursor: pointer; }}
button:hover, button.active {{ border-color: var(--accent); color: var(--accent); }}
.row {{ display: flex; gap: 8px; }}
.row > * {{ flex: 1; }}
label.check {{
  display: flex;
  gap: 8px;
  align-items: center;
  margin: 6px 0;
  font-size: 13px;
  cursor: pointer;
}}
.stage {{ padding: 20px; min-width: 0; display: flex; flex-direction: column; gap: 14px; }}
.topbar {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }}
.topbar h2 {{ margin: 0; font-size: 18px; }}
.viewport {{
  overflow: auto;
  max-height: 75vh;
  background: repeating-conic-gradient(#1f2f3f 0% 25%, #162330 0% 50%) 50% / 16px 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px;
}}
canvas {{ display: block; image-rendering: pixelated; }}
.card {{
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: rgba(11, 20, 32, 0.55);
  font-size: 12.5px;
}}
.card h3 {{ margin: 0 0 6px; font-size: 13px; color: var(--accent); }}
.card ul {{ margin: 6px 0 0; padding-left: 18px; }}
code {{ color: var(--ok); }}
@media (max-width: 860px) {{
  main {{ grid-template-columns: 1fr; }}
  aside {{ border-right: 0; border-bottom: 1px solid var(--line); }}
}}
</style>
</head>
<body>
<header>
  <div>
    <div class="eyebrow">PMDO 0.8.12 · Animation Canonique Pelipper Post Office</div>
    <h1>Cliff Nord Jour Animé — Mer PMD Sky Port (10 phases) & Wrap Nuages</h1>
  </div>
  <span class="badge">Calques falaise, objets & animations 100 % intacts · runtime_tested: false</span>
</header>
<main>
  <aside>
    <section>
      <label class="label" for="mapSelect">Carte (.rsground)</label>
      <select id="mapSelect"></select>
      <p id="mapMeta" style="font-size:12px;color:var(--muted);margin:6px 0 0"></p>
    </section>
    <section>
      <span class="label">Contrôle d'animation (60 Hz)</span>
      <div class="row">
        <button id="playBtn" class="active">Pause</button>
        <button id="stepBtn">+1 phase mer</button>
        <button id="resetBtn">Tick 0</button>
      </div>
      <p id="tickStatus" style="font-size:12px;color:var(--muted);margin:8px 0 0"></p>
    </section>
    <section>
      <label class="label" for="zoomSelect">Zoom</label>
      <select id="zoomSelect">
        <option value="fit">Ajuster à la fenêtre</option>
        <option value="1">1× (pixels natifs)</option>
        <option value="2">2× (pixels doublés)</option>
      </select>
      <label class="check"><input type="checkbox" id="gridToggle">Grille 8×8 px</label>
    </section>
    <section>
      <span class="label">Calques affichés</span>
      <label class="check"><input type="checkbox" id="showSky" checked>LayeredBG 0 · Ciel fixe</label>
      <label class="check"><input type="checkbox" id="showClouds" checked>LayeredBG 1 · Nuages wrap (−4 px/s, RepeatX)</label>
      <label class="check"><input type="checkbox" id="showSea" checked>Layer 1 · Mer canonique PMD Sky Port (10 phases)</label>
      <label class="check"><input type="checkbox" id="showCliffs" checked>Layers 2..N · Falaise & objets (100 % intacts)</label>
    </section>
    <section class="card">
      <h3>Intégrité garantie</h3>
      <ul>
        <li><strong>Falaise & objets :</strong> aucun calque de falaise, d'objet ou d'animation existante n'est modifié, renommé ou déplacé (<code>assert out == orig</code>).</li>
        <li><strong>Nuages :</strong> uniquement activés en <code>LayeredBG</code> / <code>MapBG</code> (<code>RepeatX: true</code>, <code>BGMovement: (-4, 0)</code>).</li>
        <li><strong>Mer :</strong> animée canoniquement depuis <code>reference_ciel_mer.png</code> (Pelipper Post Office : 5 phases <code>far_sea</code> + 10 phases <code>near_sea</code>, <code>FrameLength: 10</code>).</li>
      </ul>
    </section>
  </aside>
  <div class="stage">
    <div class="topbar">
      <h2 id="stageTitle">Chargement…</h2>
      <a href="renders/cliff_nord_jour_anime_v1/cliff_nord_jour_anime_pmdo_0812.zip" download style="color:var(--accent)">Télécharger cliff_nord_jour_anime_pmdo_0812.zip ↓</a>
    </div>
    <div class="viewport" id="viewport">
      <canvas id="sceneCanvas"></canvas>
    </div>
    <div class="card" id="layerSummary"></div>
  </div>
</main>
<script>
const DATA = {payload_json};
const el = id => document.getElementById(id);
const canvas = el('sceneCanvas');
const ctx = canvas.getContext('2d');

let selectedMap = 0;
let tick = 0;
let playing = true;
let lastTime = null;
const loaded = {{}};

function loadImage(src) {{
  return new Promise((resolve, reject) => {{
    const im = new Image();
    im.onload = () => resolve(im);
    im.onerror = reject;
    im.src = src;
  }});
}}

async function ensureMapLoaded(idx) {{
  if (loaded[idx]) return loaded[idx];
  const m = DATA.maps[idx];
  const sky = await loadImage(m.sky_webp);
  const clouds = await loadImage(m.cloud_strip_webp);
  const cliffs = await loadImage(m.untouched_cliffs_webp);
  const sea = await Promise.all(m.sea_frames_webp.map(loadImage));
  loaded[idx] = {{ sky, clouds, cliffs, sea }};
  return loaded[idx];
}}

function applyZoom() {{
  const m = DATA.maps[selectedMap];
  const z = el('zoomSelect').value;
  const vp = el('viewport');
  const scale = z === 'fit'
    ? Math.min(1, (vp.clientWidth - 24) / m.width, (window.innerHeight * 0.72) / m.height)
    : Number(z);
  canvas.style.width = Math.round(m.width * scale) + 'px';
  canvas.style.height = Math.round(m.height * scale) + 'px';
}}

function render() {{
  const m = DATA.maps[selectedMap];
  const assets = loaded[selectedMap];
  if (!assets) return;
  if (canvas.width !== m.width || canvas.height !== m.height) {{
    canvas.width = m.width;
    canvas.height = m.height;
  }}
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, m.width, m.height);

  if (el('showSky').checked) {{
    ctx.drawImage(assets.sky, 0, 0);
  }}
  if (el('showClouds').checked) {{
    const sw = assets.clouds.width;
    const shift = Math.floor((DATA.cloud_speed_px_s * tick) / 60);
    const startX = ((shift % sw) + sw) % sw - sw;
    for (let x = startX; x < m.width; x += sw) {{
      ctx.drawImage(assets.clouds, x, m.cloud_map_loc_y);
    }}
  }}
  const seaPhase = Math.floor(tick / DATA.sea_frame_length_ticks) % DATA.sea_frame_count;
  if (el('showSea').checked) {{
    ctx.drawImage(assets.sea[seaPhase], 0, 0);
  }}
  if (el('showCliffs').checked) {{
    ctx.drawImage(assets.cliffs, 0, 0);
  }}
  if (el('gridToggle').checked) {{
    ctx.strokeStyle = 'rgba(255,255,255,0.18)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = 0.5; x < m.width; x += 8) {{ ctx.moveTo(x, 0); ctx.lineTo(x, m.height); }}
    for (let y = 0.5; y < m.height; y += 8) {{ ctx.moveTo(0, y); ctx.lineTo(m.width, y); }}
    ctx.stroke();
  }}
  const shiftPx = Math.floor((-DATA.cloud_speed_px_s * tick) / 60) % assets.clouds.width;
  el('tickStatus').textContent = `Tick ${{tick}} (60 Hz) · Mer phase ${{seaPhase + 1}}/10 (far_sea ${{(seaPhase % 5) + 1}}/5, near_sea ${{seaPhase + 1}}/10) · Nuages wrap ${{shiftPx}}/${{assets.clouds.width}} px`;
}}

async function selectMap(idx) {{
  selectedMap = idx;
  const m = DATA.maps[idx];
  el('stageTitle').textContent = `${{m.slug}}.rsground (${{m.width}} × ${{m.height}} px · ${{m.width / 8}} × ${{m.height / 8}} cases)`;
  el('mapMeta').textContent = `${{m.animated_sea_cells}} cases de mer animées · Calques falaise/objets (${{m.untouched_layers.join(', ')}}) 100 % intacts`;
  el('layerSummary').innerHTML = `<h3>Structure de <code>${{m.slug}}.rsground</code></h3>` +
    `<p><strong>Background (LayeredBG) :</strong> <code>${{m.sky_bg}}</code> (fixe) + <code>${{m.cloud_bg}}</code> (<code>RepeatX: true</code>, <code>BGMovement: (-4, 0)</code>, <code>MapLoc.Y: ${{m.cloud_map_loc_y}}</code>).</p>` +
    `<p><strong>Layer 1 (mer) :</strong> <code>${{m.animated_sea_cells}}</code> cases <code>v2_promontoire_jour_03</code> animées sur 10 phases canoniques Pelipper Post Office (<code>FrameLength: 10</code>, Phase 0 conservée aux coordonnées exactes <code>(tx, ty)</code>).</p>` +
    `<p><strong>Calques falaise, objets et animations (${{m.untouched_layers.join(', ')}}) :</strong> strictement identiques à l'original octet pour octet.</p>`;
  await ensureMapLoaded(idx);
  applyZoom();
  render();
}}

DATA.maps.forEach((m, i) => {{
  const opt = document.createElement('option');
  opt.value = i;
  opt.textContent = `${{m.slug}}.rsground (${{m.width}}×${{m.height}} px)`;
  el('mapSelect').appendChild(opt);
}});

el('mapSelect').onchange = e => selectMap(Number(e.target.value));
el('zoomSelect').onchange = applyZoom;
window.addEventListener('resize', applyZoom);
['gridToggle', 'showSky', 'showClouds', 'showSea', 'showCliffs'].forEach(id => {{
  el(id).onchange = render;
}});
el('playBtn').onclick = () => {{
  playing = !playing;
  el('playBtn').textContent = playing ? 'Pause' : 'Lecture';
  el('playBtn').classList.toggle('active', playing);
}};
el('stepBtn').onclick = () => {{
  playing = false;
  el('playBtn').textContent = 'Lecture';
  el('playBtn').classList.remove('active');
  tick += DATA.sea_frame_length_ticks;
  render();
}};
el('resetBtn').onclick = () => {{
  tick = 0;
  render();
}};

selectMap(0);
function loop(ts) {{
  if (lastTime !== null && playing) {{
    const dt = Math.min((ts - lastTime) / 1000, 0.1);
    tick += Math.max(1, Math.round(dt * 60));
    render();
  }}
  lastTime = ts;
  requestAnimationFrame(loop);
}}
requestAnimationFrame(loop);
</script>
</body>
</html>
"""
    viewer_path.write_text(html, encoding="utf-8")


def main() -> None:
    verify_root_immutability()

    gfx = loadmod("pmdo_codec", ROOT / "source/pmdo_cote/build.py")

    if RENDERS.exists():
        shutil.rmtree(RENDERS)
    RENDERS.mkdir(parents=True, exist_ok=True)

    # 1. Load both original .rsground documents
    nw_orig_raw = (ROOT / "cliffnordouesttest1.rsground").read_bytes()
    day_orig_raw = (ROOT / "cliffdaytest.rsground").read_bytes()
    nw_orig = json.loads(nw_orig_raw.decode("utf-8-sig"))
    day_orig = json.loads(day_orig_raw.decode("utf-8-sig"))

    # Collect exact (tx, ty) coordinates referenced on `v2_promontoire_jour_03` across both maps
    needed_sea_coords: set[tuple[int, int]] = set()
    for doc in (nw_orig, day_orig):
        l1 = doc["Object"]["Layers"][1]
        for col in l1["Tiles"]:
            for cell in col:
                for tl in cell["Layers"]:
                    for f in tl["Frames"]:
                        if f["Sheet"] == "v2_promontoire_jour_03":
                            needed_sea_coords.add((f["TexLoc"]["X"], f["TexLoc"]["Y"]))

    # 2. Build the 10 canonical PMD Sky Port (`reference_ciel_mer.png`) sea sheets (1312x1024)
    #    and encode `Content/Tile/v2_promontoire_jour_03.tile` in native RogueEssence TileSheet format
    sea_sheets, sea_info = build_canonical_pmdsky_sea_sheets()
    sea_bank, phase_locs = build_pmdo_sea_bank(gfx, sea_sheets, needed_sea_coords)

    tile_dir = RENDERS / "Content/Tile"
    tile_dir.mkdir(parents=True, exist_ok=True)
    sea_bank.write(tile_dir / f"{SEA_BANK_NAME}.tile")

    # 3. Build sky and cloud wrap .dir assets for both maps using native `gfx.write_dir`
    sky_src = build_sky_source_504x408()
    nw_sky_im = reconstruct_map_sky_from_layer0(nw_orig, sky_src, fill_top_with_row0=True)
    nw_cloud_strip = Image.open(NUAGES_PATH).convert("RGBA")  # 1440x208 canonical cloud wrap strip
    nw_cloud_map_loc_y = 216  # Places the 208px cloud band at y=216..424 right above the y=424 sea horizon

    day_sky_im = reconstruct_map_sky_from_layer0(day_orig, sky_src, fill_top_with_row0=False)
    day_cloud_strip = reconstruct_cliffdaytest_cloud_strip(day_orig)  # 984x312 exact user cloud placement
    day_cloud_map_loc_y = 0

    bg_dir = RENDERS / "Content/BG"
    bg_dir.mkdir(parents=True, exist_ok=True)
    gfx.write_dir(bg_dir / "CLIFF_NORD_OUEST_CIEL.dir", nw_sky_im)
    gfx.write_dir(bg_dir / "CLIFF_NORD_OUEST_NUAGES.dir", nw_cloud_strip)
    gfx.write_dir(bg_dir / "CLIFF_DAY_CIEL.dir", day_sky_im)
    gfx.write_dir(bg_dir / "CLIFF_DAY_NUAGES.dir", day_cloud_strip)

    # 4. Transform both .rsground documents (leaving all cliff/object/animation layers untouched)
    nw_doc, nw_stats = transform_rsground(
        gfx,
        "cliffnordouesttest1",
        nw_orig,
        phase_locs,
        sky_bg_name="CLIFF_NORD_OUEST_CIEL",
        cloud_bg_name="CLIFF_NORD_OUEST_NUAGES",
        cloud_map_loc_y=nw_cloud_map_loc_y,
    )
    day_doc, day_stats = transform_rsground(
        gfx,
        "cliffdaytest",
        day_orig,
        phase_locs,
        sky_bg_name="CLIFF_DAY_CIEL",
        cloud_bg_name="CLIFF_DAY_NUAGES",
        cloud_map_loc_y=day_cloud_map_loc_y,
    )

    # 5. Write updated .rsground files with UTF-8 BOM
    ground_dir = RENDERS / "Data/Ground"
    ground_dir.mkdir(parents=True, exist_ok=True)
    for slug, doc in [("cliffnordouesttest1", nw_doc), ("cliffdaytest", day_doc)]:
        encoded = "\ufeff" + json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
        raw_bytes = encoded.encode("utf-8")
        (ground_dir / f"{slug}.rsground").write_bytes(raw_bytes)
        (RENDERS / f"{slug}.rsground").write_bytes(raw_bytes)

    # 6. Load in-memory repo tilesets ONLY for preview images/HTML
    repo_sheets = load_repo_preview_sheets([nw_orig, day_orig])

    viewer_maps = []
    map_configs = [
        (
            "cliffnordouesttest1",
            nw_orig,
            nw_doc,
            nw_stats,
            nw_sky_im,
            nw_cloud_strip,
            nw_cloud_map_loc_y,
            [2, 3],
        ),
        (
            "cliffdaytest",
            day_orig,
            day_doc,
            day_stats,
            day_sky_im,
            day_cloud_strip,
            day_cloud_map_loc_y,
            [0, 2, 3, 4, 5],
        ),
    ]

    for slug, orig_doc, doc, stats, sky_im, cloud_strip, cloud_y, preview_layer_indices in map_configs:
        mdir = RENDERS / slug
        w_px, h_px = stats["dimensions_px"]
        sea_frames = render_sea_layer_frames(orig_doc["Object"]["Layers"][1], sea_sheets, repo_sheets)
        untouched_preview = render_untouched_layers_preview(doc, preview_layer_indices, repo_sheets)
        cloud_t0 = render_cloud_wrap_at(cloud_strip, (w_px, h_px), cloud_y, 0)

        save_png(sky_im, mdir / "calques/00_ciel_bg.png")
        save_png(cloud_strip, mdir / "calques/01_nuages_wrap_strip.png")
        save_png(cloud_t0, mdir / "calques/01_nuages_wrap_t000.png")
        save_png(untouched_preview, mdir / "calques/03_falaise_objets_intacts_apercu.png")
        for f_idx, sf in enumerate(sea_frames):
            save_png(sf, mdir / f"mer/mer_{f_idx:02d}.png")
        save_png(sea_frames[0], mdir / "calques/02_mer_pmdsky_f00.png")

        write_ora(
            RENDERS / f"{slug}_calques.ora",
            (w_px, h_px),
            [
                ("00_ciel_bg", sky_im),
                ("01_nuages_wrap_t000", cloud_t0),
                ("02_mer_pmdsky_f00", sea_frames[0]),
                ("03_falaise_objets_intacts_apercu", untouched_preview),
            ],
        )

        anim_frames: list[Image.Image] = []
        for f_idx in range(SEA_FRAME_COUNT):
            tick = f_idx * SEA_FRAME_LENGTH
            shift = (CLOUD_SPEED_PX_S * tick) // 60
            cloud_frame = render_cloud_wrap_at(cloud_strip, (w_px, h_px), cloud_y, shift)
            scene = Image.alpha_composite(sky_im, cloud_frame)
            scene = Image.alpha_composite(scene, sea_frames[f_idx])
            scene = Image.alpha_composite(scene, untouched_preview)
            if f_idx == 0:
                save_png(scene, RENDERS / f"review/{slug}_scene_t000.png")
            anim_frames.append(scene)

        webp_path = RENDERS / f"review/{slug}_scene_animee.webp"
        webp_path.parent.mkdir(parents=True, exist_ok=True)
        anim_frames[0].save(
            webp_path,
            save_all=True,
            append_images=anim_frames[1:],
            duration=167,
            loop=0,
            lossless=True,
            method=4,
        )

        viewer_maps.append(
            {
                "slug": slug,
                "width": w_px,
                "height": h_px,
                "sky_bg": stats["background_layers"][0]["anim_index"],
                "cloud_bg": stats["background_layers"][1]["anim_index"],
                "cloud_map_loc_y": cloud_y,
                "animated_sea_cells": stats["animated_sea_cells_layer1"],
                "untouched_layers": [
                    f"Layer {i} ({doc['Object']['Layers'][i]['Name']})"
                    for i in stats["untouched_layer_indices"]
                ],
                "sky_webp": image_to_webp_data_uri(sky_im),
                "cloud_strip_webp": image_to_webp_data_uri(cloud_strip),
                "untouched_cliffs_webp": image_to_webp_data_uri(untouched_preview),
                "sea_frames_webp": [image_to_webp_data_uri(im) for im in sea_frames],
            }
        )

    # 7. Build contact sheet of the 10 canonical PMD Sky Port sea frames
    board = Image.new("RGB", (1240, 520), "#0e1a28")
    draw = ImageDraw.Draw(board)
    draw.text(
        (16, 12),
        "PMD Sky Port (Pelipper Post Office) - 10 phases canoniques de mer (5 far_sea + 10 near_sea) & wrap nuages",
        fill="#ebf1f5",
    )
    for f_idx in range(SEA_FRAME_COUNT):
        col = f_idx % 5
        row = f_idx // 5
        x0 = 16 + col * 244
        y0 = 42 + row * 230
        crop = Image.fromarray(sea_sheets[f_idx][144:384, :240], "RGBA")
        bg_tile = Image.new("RGBA", crop.size, (18, 34, 53, 255))
        comp = Image.alpha_composite(bg_tile, crop).convert("RGB")
        board.paste(comp, (x0, y0 + 18))
        draw.text(
            (x0, y0),
            f"Phase {f_idx:02d} (far {f_idx % 5 + 1}/5, near {f_idx + 1}/10)",
            fill="#9be28f",
        )
    save_png(board, RENDERS / "review/planche_10_phases_mer_pmdsky.png")

    # 8. Copy canonical PMDO index merger INSTALLER.py and write README.md + manifest.json
    shutil.copyfile(ROOT / "source/pmdo_cote/INSTALLER.py", RENDERS / "INSTALLER.py")
    readme_text = """# Cliff Nord Jour Animé (`cliffnordouesttest1` & `cliffdaytest`) — Mer canonique PMD Sky Port & Wrap Nuages

Ce lot applique **uniquement** les deux animations demandées sur `cliffnordouesttest1.rsground` et `cliffdaytest.rsground` :

1. **Aucun calque de falaise, d'objet ou d'animation existante n'est touché, renommé ou déplacé** :
   - Dans `cliffnordouesttest1.rsground` : `Layers[2]` (`New Layer`) et `Layers[3]` (`Layer 3`) sont **100 % identiques octet pour octet** à l'original (ainsi que la case `Altere_Pond_Cliffs` sur `Layers[1]`).
   - Dans `cliffdaytest.rsground` : `Layers[2]` (`Layer 2`), `Layers[3]` (`Layer 4`), `Layers[4]` (`Layer 3`), les 5 cases `Altere_Pond_Cliffs` / `CanyonCamp` sur `Layers[0]` et les **325 cases d'objets** (`Altere_Pond_Objects`, `Altere_Pond_Objects_Under`, `Metano_Town_Objects`, `Metano_Town_Trimmed`, `Metano_Inn_Objects`) sur `Layers[5]` (`Cloud/nuage`) sont **100 % identiques octet pour octet** à l'original.
   - Aucune banque `.tile` factice/proxy n'est générée pour les falaises ou les objets : seule `Content/Tile/v2_promontoire_jour_03.tile` est livrée.

2. **Nuages : uniquement le wrap overlay activé (`LayeredBG` / `MapBG`)** :
   - `Object["Background"]` est configuré en `RogueEssence.Dungeon.LayeredBG, RogueEssence` avec :
     - Ciel fixe (`CLIFF_NORD_OUEST_CIEL` / `CLIFF_DAY_CIEL`, `RepeatX = false`, `BGMovement = (0, 0)`, `Parallax = "1, 1"`).
     - Nuages en wrap horizontal (`CLIFF_NORD_OUEST_NUAGES` / `CLIFF_DAY_NUAGES`, `RepeatX = true`, `RepeatY = false`, `BGMovement = (-4, 0)`, `Parallax = "1, 1"`).
   - Les tuiles statiques `00_ciel` sur `Layers[0]` et `01_long_cap_jour_02` sur `Layers[5]` sont vidées pour que le `LayeredBG` soit visible derrière les calques de tuiles sans doublon statique.

3. **Mer (`Layers[1]`) : animation canonique PMD Sky Port (`reference_ciel_mer.png`, Pelipper Post Office)** :
   - Extrait les **5 bandes `far_sea`** (`(544+56*f, 224, 592+56*f, 352)`, `48×128` px) et les **10 bandes `near_sea`** (`(824+56*f, 224, 872+56*f, 392)`, `48×168` px) de `source/falaises_cotieres_nues/reference_ciel_mer.png`.
   - Construit les 10 phases canoniques `1312×1024` px dans le repère exact de `v2_promontoire_jour_03` (`0` pixel d'écart sur la phase 0 face à `sprites/cote_dix_zones/fonds/jour_mer_00.png`).
   - Encode `Content/Tile/v2_promontoire_jour_03.tile` au format binaire natif `TileSheet` de RogueEssence (Phase 0 conservée aux coordonnées `(tx, ty)` exactes dans `ty = 0..127`, phases `1..9` dédupliquées dans `ty >= 128`) et anime les `6209` cases de mer de `cliffnordouesttest1.rsground` et les `7503` cases de mer de `cliffdaytest.rsground` sur 10 phases (`FrameLength = 10` ticks à 60 Hz).

## Limites honnêtes
- `art_approved: false`
- `runtime_tested: false` (aucun test d'ouverture dans l'exécutable PMDO n'a été effectué dans cet environnement).
"""
    (RENDERS / "README.md").write_text(readme_text, encoding="utf-8")

    manifest = {
        "id": "cliff_nord_jour_anime_v1",
        "pmdo_version": "0.8.12.0",
        "art_approved": False,
        "runtime_tested": False,
        "root_originals_untouched": EXPECTED_ROOT_SHA256,
        "sea_animation": {
            **sea_info,
            "tile_bank": f"Content/Tile/{SEA_BANK_NAME}.tile",
            "total_encoded_8x8_tiles": len(sea_bank.data),
            "unique_8x8_patterns": len(sea_bank.ids),
        },
        "maps": {
            "cliffnordouesttest1": nw_stats,
            "cliffdaytest": day_stats,
        },
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    (HERE / "manifest.json").write_bytes(manifest_bytes)
    (RENDERS / "manifest.json").write_bytes(manifest_bytes)

    zip_path = RENDERS / "cliff_nord_jour_anime_pmdo_0812.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rel in [
            "Data/Ground/cliffnordouesttest1.rsground",
            "Data/Ground/cliffdaytest.rsground",
            f"Content/Tile/{SEA_BANK_NAME}.tile",
            "Content/BG/CLIFF_NORD_OUEST_CIEL.dir",
            "Content/BG/CLIFF_NORD_OUEST_NUAGES.dir",
            "Content/BG/CLIFF_DAY_CIEL.dir",
            "Content/BG/CLIFF_DAY_NUAGES.dir",
            "INSTALLER.py",
            "README.md",
            "manifest.json",
        ]:
            p = RENDERS / rel
            info = zipfile.ZipInfo(rel, (2026, 10, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, p.read_bytes(), compresslevel=6)

    shutil.copyfile(zip_path, ROOT / "livrable_cliff_nord_jour_anime_v1.zip")
    build_viewer_html(ROOT / "apercu_cliff_nord_jour_anime_v1.html", viewer_maps, manifest["sea_animation"])

    verify_root_immutability()
    print(
        f"Build complete: {len(sea_bank.data)} tiles ({len(sea_bank.ids)} unique) in {SEA_BANK_NAME}.tile, "
        f"nw={nw_stats['animated_sea_cells_layer1']} sea cells, day={day_stats['animated_sea_cells_layer1']} sea cells."
    )


if __name__ == "__main__":
    main()
