#!/usr/bin/env python3
"""ZGT2 : V2 du village approuvé, avec textures 8x8 échantillonnées de T00P01.

Les corrections n'écrasent pas ZGT1 : chemin vers la maison droite, quatre panneaux
retirés, sprites transparents, variante nuit de la petite maison, multicalque PMDO.
Le GIF animé mentionné par l'utilisateur doit encore être réattaché; le cycle d'eau
actuel vient de T00P01, pas de ce GIF.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE_SOURCE = ROOT / "source/zone_guilde_treehouse_v1"
REFS = BASE_SOURCE / "reference"
RAW = BASE_SOURCE / "bruts"
RENDERS = ROOT / "renders/zone_guilde_treehouse_v2"
CACHE = ROOT / ".cache/zone_guilde_treehouse_v2"
STAGE = CACHE / "pmdo_stage"

W, H = 768, 576
TILE = 8
GW, GH = W // TILE, H // TILE
PREFIX = "ZGT2"
NAMESPACE = "zone_guilde_treehouse_v2"
ASSET = "zgt2_village_arboricole_guilde"
WATER_FRAME_LENGTH = 2
WATER_FRAMES = 36
WATER_LOOP_TICKS = 72

# Centre des colliders provisoires, pixels dans la map 768x576.
MARKERS = {
    "entree_sud": [384, 548],
    "place_centrale": [408, 328],
    "maison_guilde": [384, 184],
    "maison_droite": [610, 210],
    "pont_est": [688, 286],
}

SIGN_CELLS = {
    # Cases 8x8 couvrant chaque petit panneau et son poteau.
    "panneau_nord_ouest": (31, 36, 34, 39),
    "panneau_nord_est": (62, 36, 65, 39),
    "panneau_sud_ouest": (38, 48, 41, 51),
    "panneau_sud_est": (57, 48, 60, 51),
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Impossible de charger {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def native_ground_tiles(reference: np.ndarray) -> dict[str, dict[str, object]]:
    """Sélectionne des cellules 8x8 exactes du rendu canonique T00P01."""
    a = reference.astype(np.int16)
    r, g, b = a.transpose(2, 0, 1)
    # Le chemin est la composante sableuse passant par la voie centrale (seed T00P01 520,300).
    path_mask = (r > 190) & (g > 190) & (b > 150) & (b < 238) & (r > g - 35) & (g - b > 10)
    labels, _ = ndi.label(path_mask)
    seed_id = int(labels[300, 520])
    if not seed_id:
        raise ValueError("Impossible d'identifier le chemin canonique T00P01")
    path_mask = labels == seed_id
    grass_mask = (g > r + 15) & (g > b + 10) & (g > 125)

    banks: dict[str, dict[str, object]] = {}
    for name, class_mask in (("path", path_mask), ("grass", grass_mask)):
        tiles: list[np.ndarray] = []
        coords: list[list[int]] = []
        means: list[np.ndarray] = []
        stds: list[float] = []
        seen: set[bytes] = set()
        for y in range(0, reference.shape[0] - 7, TILE):
            for x in range(0, reference.shape[1] - 7, TILE):
                mask_tile = class_mask[y : y + TILE, x : x + TILE]
                tile = reference[y : y + TILE, x : x + TILE]
                fraction = float(mask_tile.mean())
                mean = tile.astype(np.float32).mean(axis=(0, 1))
                std = float(tile.astype(np.float32).std(axis=(0, 1)).mean())
                if name == "path":
                    accepted = fraction >= 0.84
                else:
                    accepted = (
                        fraction >= 0.90 and std < 35 and mean[1] > mean[0] + 18
                        and mean[1] > mean[2] + 8 and mean.mean() < 230
                    )
                if not accepted:
                    continue
                key = tile.tobytes()
                if key in seen:
                    continue
                seen.add(key)
                tiles.append(tile.copy())
                coords.append([x, y])
                means.append(mean)
                stds.append(std)
        if len(tiles) < 20:
            raise ValueError(f"Atlas canonique {name} trop petit : {len(tiles)} tuiles")
        banks[name] = {
            "tiles": np.stack(tiles).astype(np.uint8),
            "coords": coords,
            "means": np.stack(means).astype(np.float32),
            "stds": np.asarray(stds, dtype=np.float32),
        }
    return banks


def choose_sample(bank: dict[str, object], target: np.ndarray, gx: int, gy: int, salt: int) -> int:
    means = bank["means"]
    stds = bank["stds"]
    target = np.asarray(target, dtype=np.float32)
    color_distance = np.linalg.norm(means - target[None, :], axis=1)
    # Garde une petite variation locale tout en privilégiant la teinte du terrain.
    score = color_distance + 0.08 * np.abs(stds - 18.0)
    best = np.argsort(score)[: min(12, len(score))]
    return int(best[(gx * 37 + gy * 19 + salt) % len(best)])


def canonical_terrain_layer(scene_rgb: np.ndarray, base_mask: np.ndarray,
                            banks: dict[str, dict[str, object]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Remplace une grande part des surfaces de sol générées par des échantillons exacts 8x8."""
    a = scene_rgb.astype(np.int16)
    r, g, b = a.transpose(2, 0, 1)
    grass_pixels = (g > r + 12) & (g > b + 8) & (g > 100)
    path_pixels = (r > 170) & (g > 160) & (b > 105) & (r > g - 30) & (g > b + 8)
    grass_pixels &= base_mask
    path_pixels &= base_mask

    layer = np.zeros((H, W, 4), dtype=np.uint8)
    selected = np.zeros((H, W), dtype=bool)
    source_map = np.full((GH, GW, 3), -1, dtype=np.int16)  # [source_x, source_y, material 1 grass / 2 path]
    for gy in range(GH):
        y0 = gy * TILE
        for gx in range(GW):
            x0 = gx * TILE
            gs = grass_pixels[y0 : y0 + TILE, x0 : x0 + TILE]
            ps = path_pixels[y0 : y0 + TILE, x0 : x0 + TILE]
            if max(int(gs.sum()), int(ps.sum())) < 18:
                continue
            material = "grass" if gs.sum() >= ps.sum() else "path"
            class_mask = gs if material == "grass" else ps
            target = scene_rgb[y0 : y0 + TILE, x0 : x0 + TILE][class_mask].mean(axis=0)
            index = choose_sample(banks[material], target, gx, gy, 0)
            tile = banks[material]["tiles"][index]
            layer[y0 : y0 + TILE, x0 : x0 + TILE, :3][class_mask] = tile[class_mask]
            layer[y0 : y0 + TILE, x0 : x0 + TILE, 3][class_mask] = 255
            selected[y0 : y0 + TILE, x0 : x0 + TILE] |= class_mask
            sx, sy = banks[material]["coords"][index]
            source_map[gy, gx] = [sx, sy, 1 if material == "grass" else 2]
    return layer, selected, source_map


def choose_connector_sample(bank: dict[str, object], gx: int, gy: int) -> int:
    means = bank["means"]
    stds = bank["stds"]
    # All candidates remain exact T00P01 pixels, but prefer the plain sandy road bed
    # so the new narrow connector does not pick a bridge edge or a large stone motif.
    eligible = np.where((stds <= 5.2) & (means[:, 0] >= 235) & (means[:, 1] >= 235) & (means[:, 2] >= 185))[0]
    if not len(eligible):
        return choose_sample(bank, np.asarray([250, 250, 198], dtype=np.float32), gx, gy, 7)
    score = np.linalg.norm(means[eligible] - np.asarray([250, 250, 198], dtype=np.float32), axis=1) + 0.10 * stds[eligible]
    best = eligible[np.argsort(score)[: min(6, len(eligible))]]
    return int(best[(gx * 37 + gy * 19 + 7) % len(best)])


def make_connector_and_sign_repairs(scene_rgb: np.ndarray, guide_rgb: np.ndarray,
                                     banks: dict[str, dict[str, object]]) -> tuple[np.ndarray, dict[str, object]]:
    layer = np.zeros((H, W, 4), dtype=np.uint8)
    used: list[dict[str, object]] = []

    grid_mask = Image.new("L", (GW, GH), 0)
    draw = ImageDraw.Draw(grid_mask)
    # Liaison piétonne continue : porche de la maison droite -> grande voie est-ouest.
    route_cells = [(76, 30), (76, 31), (76, 32), (75, 33), (75, 34), (76, 35), (76, 36)]
    draw.line(route_cells, fill=255, width=3)
    connector = np.asarray(grid_mask.resize((W, H), Image.Resampling.NEAREST)) > 0

    cell_materials: dict[tuple[int, int], str] = {}
    for name, (x0, y0, x1, y1) in SIGN_CELLS.items():
        # Matériau estimé sur l'anneau de la plaque dans la plaque de sol de travail.
        rx0, ry0, rx1, ry1 = max(0, x0 * TILE - 8), max(0, y0 * TILE - 8), min(W, x1 * TILE + 8), min(H, y1 * TILE + 8)
        ring = guide_rgb[ry0:ry1, rx0:rx1].astype(np.int16).copy()
        inner = np.zeros(ring.shape[:2], dtype=bool)
        inner[y0 * TILE - ry0:y1 * TILE - ry0, x0 * TILE - rx0:x1 * TILE - rx0] = True
        samples = ring[~inner]
        rr, gg, bb = samples.transpose(1, 2, 0) if samples.ndim == 3 else (samples[:, 0], samples[:, 1], samples[:, 2])
        green_ratio = float(((gg > rr + 8) & (gg > bb + 4)).mean())
        material = "grass" if green_ratio >= 0.22 else "path"
        for gy in range(y0, y1):
            for gx in range(x0, x1):
                cell_materials[(gx, gy)] = material
        used.append({"name": name, "tile_rect_xyxy": [x0, y0, x1, y1], "material": material})

    path_cells = np.asarray(grid_mask) > 0
    for gy in range(GH):
        y0 = gy * TILE
        for gx in range(GW):
            x0 = gx * TILE
            if path_cells[gy, gx]:
                material = "path"
                index = choose_connector_sample(banks[material], gx, gy)
            elif (gx, gy) in cell_materials:
                material = cell_materials[(gx, gy)]
                target = guide_rgb[y0 : y0 + TILE, x0 : x0 + TILE].mean(axis=(0, 1))
                index = choose_sample(banks[material], target, gx, gy, 13)
            else:
                continue
            tile = banks[material]["tiles"][index]
            layer[y0 : y0 + TILE, x0 : x0 + TILE, :3] = tile
            layer[y0 : y0 + TILE, x0 : x0 + TILE, 3] = 255
            sx, sy = banks[material]["coords"][index]
            used.append({"tile_xy": [gx, gy], "material": material, "source_xy_px": [sx, sy],
                         "purpose": "liaison_maison_droite" if path_cells[gy, gx] else "effacement_panneau"})

    patch_mask = np.asarray(layer[..., 3] > 0)
    return layer, {"mask": patch_mask, "connector_mask": connector, "sign_repairs": used,
                   "connector_grid_cells": [list(p) for p in route_cells]}


def house_silhouette(scene_rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Découpe manuelle du petit sprite droit; exclut le porche et le panneau de sol."""
    mask_img = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask_img)
    draw.polygon([
        (606, 141), (613, 145), (620, 149), (626, 155), (634, 162), (639, 170),
        (642, 180), (641, 190), (650, 195), (648, 201), (638, 202), (634, 208),
        (624, 207), (618, 214), (608, 211), (600, 217), (591, 213), (583, 215),
        (576, 209), (566, 206), (563, 200), (560, 195), (566, 187), (570, 178),
        (573, 168), (578, 159), (585, 152), (594, 147), (600, 143),
    ], fill=255)
    silhouette = np.asarray(mask_img) > 0
    pixels = scene_rgb.astype(np.int16)
    r, g, b = pixels.transpose(2, 0, 1)
    warm_wood = (r > g + 4) & (g > b + 8) & (r > 100)
    dark_outline = np.maximum.reduce((r, g, b)) < 115
    cream_wall = (r > 175) & (g > 150) & (b > 90) & (r >= g - 2) & (g > b + 12)
    leaf_shape = Image.new("L", (W, H), 0)
    ImageDraw.Draw(leaf_shape).polygon([(603, 142), (610, 142), (617, 147), (620, 153), (615, 158), (607, 157), (601, 152)], fill=255)
    roof_leaf = np.asarray(leaf_shape) > 0
    mask = silhouette & (warm_wood | dark_outline | cream_wall | roof_leaf)
    # Comble les seuls trous internes au bâtiment, sans réintroduire la pelouse autour.
    mask = ndi.binary_fill_holes(mask) & silhouette
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., :3] = scene_rgb
    rgba[..., 3] = mask.astype(np.uint8) * 255
    x0, y0, x1, y1 = 560, 136, 656, 224
    sprite = np.zeros((128, 128, 4), dtype=np.uint8)
    crop = rgba[y0:y1, x0:x1]
    sprite[24:24 + crop.shape[0], 16:16 + crop.shape[1]] = crop
    return sprite, mask


def save_sprite_assets(scene_rgb: np.ndarray) -> dict[str, object]:
    out = RENDERS / "sprites"
    sheets = RENDERS / "tilesheets"
    out.mkdir(parents=True, exist_ok=True)
    sheets.mkdir(parents=True, exist_ok=True)
    hq_src = ROOT / "exports/guild_structures_v1/hq/GuildStructuresV1_hq_object.png"
    if not hq_src.is_file():
        raise FileNotFoundError(hq_src)
    with Image.open(hq_src) as image:
        hq = image.convert("RGBA").copy()
    house_day, house_mask = house_silhouette(scene_rgb)
    night_mod = load_module("zgt2_exact_night_filter", ROOT / "source/cote_v4_abyss/night.py")
    house_night = np.asarray(night_mod.night(Image.fromarray(house_day, "RGBA")))
    hq.save(out / "ZGT2_QG_treehouse_transparent.png", optimize=True)
    Image.fromarray(house_day).save(out / "ZGT2_maison_droite_jour_transparent.png", optimize=True)
    Image.fromarray(house_night).save(out / "ZGT2_maison_droite_nuit_transparent.png", optimize=True)

    atlas = Image.new("RGBA", (768, 256), (0, 0, 0, 0))
    atlas.alpha_composite(hq, (0, 0))
    atlas.alpha_composite(Image.fromarray(house_day), (256, 0))
    atlas.alpha_composite(Image.fromarray(house_night), (512, 0))
    atlas_path = sheets / "ZGT2_structures_sans_fond_8px.png"
    atlas.save(atlas_path, optimize=True)
    preview = Image.new("RGBA", atlas.size, (28, 39, 34, 255))
    preview.alpha_composite(atlas)
    d = ImageDraw.Draw(preview)
    for x, label in ((0, "QG treehouse"), (256, "maison droite — jour"), (512, "maison droite — nuit")):
        d.rectangle((x, 0, x + 255, 255), outline=(220, 205, 145, 255), width=1)
        d.text((x + 8, 8), label, fill=(255, 242, 193, 255))
    preview.save(sheets / "ZGT2_structures_apercu_labels.png", optimize=True)

    tsx = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<tileset version=\"1.10\" tiledversion=\"1.10.2\" name=\"ZGT2_structures\" tilewidth=\"8\" tileheight=\"8\" tilecount=\"3072\" columns=\"96\">
 <image source=\"ZGT2_structures_sans_fond_8px.png\" width=\"768\" height=\"256\"/>
</tileset>
"""
    (sheets / "ZGT2_structures_8px.tsx").write_text(tsx, encoding="utf-8")
    placement = {
        "grid_px": 8,
        "atlas_png": "tilesheets/ZGT2_structures_sans_fond_8px.png",
        "atlas_size_px": [768, 256],
        "alpha_background": "transparent",
        "objects": [
            {"id": "qg_treehouse", "panel_xywh_px": [0, 0, 256, 256], "sprite_file": "sprites/ZGT2_QG_treehouse_transparent.png",
             "anchor_px": [128, 240], "source": "exports/guild_structures_v1/hq/GuildStructuresV1_hq_object.png",
             "note": "Sprite treehouse déjà isolé du lot Structures Guilde; ce n'est pas un détourage pixel à pixel du grand QG fusionné au fond de la map ZGT1."},
            {"id": "maison_droite_jour", "panel_xywh_px": [256, 0, 256, 256], "sprite_file": "sprites/ZGT2_maison_droite_jour_transparent.png",
             "anchor_px": [320, 112], "source": "découpe manuelle du sprite droit visible dans le rendu généré ZGT1; fond et panneau de sol exclus."},
            {"id": "maison_droite_nuit", "panel_xywh_px": [512, 0, 256, 256], "sprite_file": "sprites/ZGT2_maison_droite_nuit_transparent.png",
             "anchor_px": [576, 112], "night_filter": "source/cote_v4_abyss/night.py", "style_status": "proposition provisoire; filtre non sélectionné comme style final", "same_alpha_as_day": True},
        ],
        "note": "PNG atlas 8px + TSX Tiled pour pose manuelle; ce n'est pas un binaire PMDO .tile ni une carte importée.",
    }
    (sheets / "ZGT2_placement_recipe.json").write_text(json.dumps(placement, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"hq_source": str(hq_src.relative_to(ROOT)), "house_mask_pixels": int(house_mask.sum()),
            "night_filter": "source/cote_v4_abyss/night.py",
            "night_filter_status": "proposition provisoire, non sélectionnée comme style final par l'utilisateur",
            "atlas_sha256": sha256(atlas_path), "atlas": "tilesheets/ZGT2_structures_sans_fond_8px.png"}


def composite(layers: list[np.ndarray]) -> np.ndarray:
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for array in layers:
        canvas = Image.alpha_composite(canvas, Image.fromarray(array, "RGBA"))
    return np.asarray(canvas)


def write_ora(path: Path, layers: list[tuple[str, np.ndarray, bool]], merged: np.ndarray) -> None:
    from io import BytesIO
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "image/openraster", compress_type=zipfile.ZIP_STORED)
        xml = [f'<?xml version="1.0" encoding="UTF-8"?>', f'<image version="0.0.1" w="{W}" h="{H}">', "  <stack>"]
        for i, (name, pixels, visible) in enumerate(layers):
            file = f"data/layer_{i:02d}.png"
            visibility = "visible" if visible else "hidden"
            xml.append(f'    <layer name="{name}" src="{file}" x="0" y="0" opacity="1.0" visibility="{visibility}"/>')
            stream = BytesIO()
            Image.fromarray(pixels, "RGBA").save(stream, format="PNG", optimize=True)
            archive.writestr(file, stream.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
        xml.extend(["  </stack>", "</image>"])
        archive.writestr("stack.xml", "\n".join(xml), compress_type=zipfile.ZIP_DEFLATED)
        stream = BytesIO()
        Image.fromarray(merged, "RGBA").save(stream, format="PNG", optimize=True)
        archive.writestr("mergedimage.png", stream.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
        thumb = Image.fromarray(merged, "RGBA").resize((256, 192), Image.Resampling.NEAREST)
        stream = BytesIO()
        thumb.save(stream, format="PNG", optimize=True)
        archive.writestr("Thumbnails/thumbnail.png", stream.getvalue(), compress_type=zipfile.ZIP_DEFLATED)


def save_canonical_atlas(banks: dict[str, dict[str, object]]) -> dict[str, object]:
    all_items = []
    for material in ("path", "grass"):
        for tile, coord in zip(banks[material]["tiles"], banks[material]["coords"]):
            all_items.append((material, tile, coord))
    cols = 16
    rows = (len(all_items) + cols - 1) // cols
    atlas = Image.new("RGBA", (cols * TILE, rows * TILE), (0, 0, 0, 0))
    entries = []
    for i, (material, tile, coord) in enumerate(all_items):
        x, y = (i % cols) * TILE, (i // cols) * TILE
        atlas.paste(Image.fromarray(tile), (x, y))
        entries.append({"id": i, "material": material, "atlas_xy_px": [x, y], "source_xy_px": coord})
    path = RENDERS / "tilesheets/ZGT2_T00P01_textures_8px.png"
    atlas.save(path, optimize=True)
    meta = {"reference": "T00P01", "reference_sha256": sha256(REFS / "T00P01_canonique.png"),
            "tile_px": 8, "atlas_size_px": list(atlas.size), "items": entries,
            "note": "Chaque cellule de 8x8 est un échantillon direct du rendu canonique T00P01; ce n'est pas l'index BPC d'origine."}
    (RENDERS / "tilesheets/ZGT2_T00P01_textures_8px.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"tile_count": len(all_items), "atlas_path": "tilesheets/ZGT2_T00P01_textures_8px.png",
            "atlas_sha256": sha256(path), "entries": entries}


def write_viewer(path: Path, manifest: dict[str, object]) -> None:
    rel = "renders/zone_guilde_treehouse_v2"
    static_specs = [
        ("base", "00 · Sol résiduel généré", f"{rel}/layers/ZGT2_00_sol_residuel.png"),
        ("terrain", "01 · Textures sol 8×8 T00P01", f"{rel}/layers/ZGT2_01_sol_T00P01.png"),
        ("details", "03 · Détails/végétation générés", f"{rel}/layers/ZGT2_03_details.png"),
        ("structures", "04 · Habitations/pont générés", f"{rel}/layers/ZGT2_04_habitations_pont.png"),
        ("house", "05 · Maison droite isolée", f"{rel}/layers/ZGT2_05_maison_droite.png"),
        ("canopy", "06 · Canopée", f"{rel}/layers/ZGT2_06_canopee.png"),
        ("patch", "07 · Chemin canonique + retrait des panneaux", f"{rel}/layers/ZGT2_07_liaisons_et_panneaux_T00P01.png"),
    ]
    specs_js = json.dumps([{"id": i, "label": l, "src": s} for i, l, s in static_specs], ensure_ascii=False)
    water_frames = json.dumps([f"{rel}/anim/ZGT2_02_eau_T00P01_f{i:02d}.png" for i in range(WATER_FRAMES)])
    html = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ZGT2 — Village arboricole de guilde</title>
<style>
body{{margin:0;padding:22px;background:#111713;color:#eef4ed;font:14px/1.5 system-ui,sans-serif}}h1{{color:#9ee0aa;margin:0}}.meta{{color:#b9c8ba;margin:4px 0 14px}}main{{display:grid;grid-template-columns:minmax(320px,768px) minmax(270px,370px);gap:16px;align-items:start}}.stage{{position:relative;width:min(100%,768px);aspect-ratio:4/3;background:#0c1110;border:1px solid #55715e;overflow:hidden}}.stage img{{position:absolute;inset:0;width:100%;height:100%;image-rendering:pixelated}}.panel{{background:#19221d;padding:14px;border:1px solid #31473a;border-radius:10px}}.layers{{display:grid;gap:6px}}.warn{{border-left:3px solid #e6c778;background:#2c281c;padding:8px;margin:12px 0}}.small{{font-size:12px;color:#c3d0c2}}a{{color:#b7d9ff}}button{{background:#26372c;color:#f1f4ed;border:1px solid #48644e;border-radius:8px;padding:7px 10px}}@media(max-width:950px){{main{{grid-template-columns:1fr}}.stage{{width:100%}}}}
</style></head><body>
<h1>ZGT2 — Village arboricole de guilde</h1><div class="meta">V2 du layout validé · 768×576 · grille 8×8 · PMDO 0.8.12 · chemin droite réparé</div>
<p><button id="play">⏸ Pause</button> <span id="tick">Tick 000 / 072</span> <label><input id="coll" type="checkbox"> Collisions</label> <a href="{rel}/ZGT2_PMDO_0812.zip">ZIP PMDO</a> · <a href="{rel}/ZGT2_layers.ora">ORA</a> · <a href="{rel}/tilesheets/ZGT2_structures_sans_fond_8px.png">Tilesheet bâtiments</a></p>
<main><div class="stage" id="stage"></div><section class="panel"><strong>Calques</strong><div class="layers" id="layers"></div>
<div class="warn"><strong>Composition ZGT1 conservée.</strong> V2 relie la maison droite, retire les quatre panneaux et ajoute un sprite isolé jour/nuit.</div>
<p class="small">Texture : les surfaces de sol retenues, le chemin d'accès et les réparations des panneaux utilisent des cellules 8×8 directement échantillonnées de T00P01. Les bâtiments et le décor restant sont générés puis quantifiés; ils ne sont pas décrits comme des tuiles natives.</p>
<p class="small">Eau : cycle canonique T00P01 (36×2 ticks, boucle 72). Le GIF d'animations mentionné n'est pas accessible dans le workspace; son herbe/eau reste à intégrer à sa réattache. L'herbe de cette V2 est statique.</p>
<p class="small">Sprites transparents : QG treehouse du lot Structures Guilde réutilisé; maison droite détourée depuis ZGT1. Variante nuit = prototype avec filtre Abyss V4, non validé comme style final. PNG/TSX 8px pour pose manuelle, pas un .tile PMDO.</p>
<p class="small"><a href="source/zone_guilde_treehouse_v2/README_PACK.md">Provenance et limites</a> · <a href="{rel}/manifest.json">Manifeste</a></p><div id="downloads" class="small"></div></section></main>
<script>
const specs={specs_js}, waterFrames={water_frames}, stage=document.getElementById('stage'), list=document.getElementById('layers'), imgs={{}};
for(const s of specs){{const im=document.createElement('img');im.src=s.src;im.alt=s.label;stage.appendChild(im);imgs[s.id]=im;const l=document.createElement('label');const c=document.createElement('input');c.type='checkbox';c.checked=true;c.onchange=()=>im.style.display=c.checked?'block':'none';l.append(c,document.createTextNode(s.label));list.appendChild(l)}}
const water=document.createElement('img');water.src=waterFrames[0];water.alt='Eau T00P01 animée';stage.appendChild(water);imgs.water=water;
const collision=document.createElement('img');collision.src='{rel}/ZGT2_collision_walkability.png';collision.style.opacity='.65';collision.style.display='none';stage.appendChild(collision);document.getElementById('coll').onchange=e=>collision.style.display=e.target.checked?'block':'none';
document.getElementById('downloads').innerHTML=specs.map(s=>`<a href="${{s.src}}">PNG ${{s.label}}</a>`).join(' · ');
let phase=0,playing=true;function show(){{water.src=waterFrames[phase];document.getElementById('tick').textContent=`Tick ${{String(phase*2).padStart(3,'0')}} / 072`}}setInterval(()=>{{if(playing){{phase=(phase+1)%36;show()}}}},1000*2/60);document.getElementById('play').onclick=e=>{{playing=!playing;e.target.textContent=playing?'⏸ Pause':'▶ Lecture'}};show();
</script></body></html>"""
    path.write_text(html, encoding="utf-8")


def write_delivery_zip() -> Path:
    delivery = ROOT / "livrable_zone_guilde_treehouse_v2.zip"
    files = [
        (HERE / "README_PACK.md", Path("source/zone_guilde_treehouse_v2/README_PACK.md")),
        (HERE / "build.py", Path("source/zone_guilde_treehouse_v2/build.py")),
        (HERE / "test_build.py", Path("source/zone_guilde_treehouse_v2/test_build.py")),
        (BASE_SOURCE / "README_PACK.md", Path("source/zone_guilde_treehouse_v1/README_PACK.md")),
        (BASE_SOURCE / "build.py", Path("source/zone_guilde_treehouse_v1/build.py")),
        (BASE_SOURCE / "test_build.py", Path("source/zone_guilde_treehouse_v1/test_build.py")),
        (ROOT / "source/cote_v4_abyss/night.py", Path("source/cote_v4_abyss/night.py")),
        (BASE_SOURCE / "reference/T00P01_canonique.png", Path("source/zone_guilde_treehouse_v1/reference/T00P01_canonique.png")),
        (BASE_SOURCE / "reference/T00P01_eau_atlas.npz", Path("source/zone_guilde_treehouse_v1/reference/T00P01_eau_atlas.npz")),
        (BASE_SOURCE / "bruts/decor_magenta.png", Path("source/zone_guilde_treehouse_v1/bruts/decor_magenta.png")),
        (BASE_SOURCE / "bruts/sol_complet.png", Path("source/zone_guilde_treehouse_v1/bruts/sol_complet.png")),
        (ROOT / "exports/guild_structures_v1/hq/GuildStructuresV1_hq_object.png", Path("exports/guild_structures_v1/hq/GuildStructuresV1_hq_object.png")),
    ]
    with zipfile.ZipFile(delivery, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in sorted(RENDERS.rglob("*")):
            if file.is_file():
                archive.write(file, Path("renders/zone_guilde_treehouse_v2") / file.relative_to(RENDERS))
        archive.write(ROOT / "apercu_zone_guilde_treehouse_v2.html", "apercu_zone_guilde_treehouse_v2.html")
        for source, archive_path in files:
            if source.is_file():
                archive.write(source, archive_path)
    return delivery


def main() -> None:
    if RENDERS.exists():
        shutil.rmtree(RENDERS)
    (RENDERS / "layers").mkdir(parents=True, exist_ok=True)
    (RENDERS / "anim").mkdir(parents=True, exist_ok=True)
    (RENDERS / "sprites").mkdir(parents=True, exist_ok=True)
    (RENDERS / "tilesheets").mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    ref_path = REFS / "T00P01_canonique.png"
    raw_decor = RAW / "decor_magenta.png"
    raw_ground = RAW / "sol_complet.png"
    for path in (ref_path, raw_decor, raw_ground, REFS / "T00P01_eau_atlas.npz"):
        if not path.is_file():
            raise FileNotFoundError(path)

    base = load_module("zgt2_v1_base_builder", BASE_SOURCE / "build.py")
    base.W, base.H, base.GW, base.GH, base.TILE = W, H, GW, GH, TILE
    reference = np.asarray(Image.open(ref_path).convert("RGB"))
    banks = native_ground_tiles(reference)
    raw_rgb = base.image_array(raw_decor)
    guide_rgb = base.image_array(raw_ground)
    water_mask, water_meta = base.magenta_water_mask(raw_rgb)
    palette = np.unique(reference.reshape(-1, 3), axis=0).astype(np.uint8)
    scene_rgb, palette_dist = base.nearest_palette(raw_rgb, palette)
    guide_rgb, _ = base.nearest_palette(guide_rgb, palette)
    base.ATLAS_PATH = REFS / "T00P01_eau_atlas.npz"
    water_frames, water_meta_tiles = base.tile_water_frames(water_mask)
    masks, _ = base.surface_masks(scene_rgb, water_mask)
    collision_masks = {name: mask.copy() for name, mask in masks.items()}

    # Détourage exact au centre de la maison droite : elle devient une vraie couche.
    house_sprite, house_mask = house_silhouette(scene_rgb)
    masks["base"] &= ~house_mask
    masks["details"] &= ~house_mask
    masks["structures"] &= ~house_mask
    masks["canopy"] &= ~house_mask

    canonical_ground, canonical_ground_mask, source_map = canonical_terrain_layer(scene_rgb, masks["base"], banks)
    link_patch, patch_info = make_connector_and_sign_repairs(scene_rgb, guide_rgb, banks)
    patch_mask = patch_info["mask"]
    canonical_ground_mask &= ~patch_mask
    canonical_ground[..., 3][patch_mask] = 0
    for key in ("base", "details", "structures", "canopy"):
        masks[key] &= ~patch_mask
    masks["base"] &= ~canonical_ground_mask

    house_layer = np.zeros((H, W, 4), dtype=np.uint8)
    house_layer[..., :3] = scene_rgb
    house_layer[..., 3] = house_mask.astype(np.uint8) * 255

    sprite_manifest = save_sprite_assets(scene_rgb)
    ground_atlas_manifest = save_canonical_atlas(banks)
    static = {
        "base": base.rgba_layer(scene_rgb, masks["base"]),
        "terrain": canonical_ground,
        "details": base.rgba_layer(scene_rgb, masks["details"]),
        "structures": base.rgba_layer(scene_rgb, masks["structures"]),
        "house": house_layer,
        "canopy": base.rgba_layer(scene_rgb, masks["canopy"]),
        "patch": link_patch,
    }
    frame0 = composite([static["base"], static["terrain"], water_frames[0], static["details"],
                        static["structures"], static["house"], static["canopy"], static["patch"]])
    if not np.all(frame0[..., 3] == 255):
        raise AssertionError("La recomposition ZGT2 doit couvrir toute la map")

    names = {
        "base": "ZGT2_00_sol_residuel.png",
        "terrain": "ZGT2_01_sol_T00P01.png",
        "details": "ZGT2_03_details.png",
        "structures": "ZGT2_04_habitations_pont.png",
        "house": "ZGT2_05_maison_droite.png",
        "canopy": "ZGT2_06_canopee.png",
        "patch": "ZGT2_07_liaisons_et_panneaux_T00P01.png",
    }
    for key, filename in names.items():
        Image.fromarray(static[key], "RGBA").save(RENDERS / "layers" / filename, optimize=True)
    Image.fromarray(frame0, "RGBA").save(RENDERS / "ZGT2_scene_t000.png", optimize=True)
    water_paths = []
    for i, frame in enumerate(water_frames):
        path = RENDERS / "anim" / f"ZGT2_02_eau_T00P01_f{i:02d}.png"
        Image.fromarray(frame, "RGBA").save(path, optimize=True)
        water_paths.append(path)
    durations = [round((i + 1) * 2000 / 60) - round(i * 2000 / 60) for i in range(WATER_FRAMES)]
    with Image.open(water_paths[0]) as im:
        first = im.convert("RGBA")
        append = [Image.open(p).convert("RGBA") for p in water_paths[1:]]
        first.save(RENDERS / "anim/ZGT2_eau_T00P01_72ticks.webp", format="WEBP", save_all=True,
                   append_images=append, duration=durations, loop=0, lossless=True, method=4)
        for frame in append:
            frame.close()
        first.close()

    # Carte de provenance par cellule et planche PNG exacte des cellules sources.
    np.savez_compressed(RENDERS / "tilesheets/ZGT2_terrain_source_tiles.npz",
                        source_map=source_map, connector_grid=np.asarray(patch_info["connector_grid_cells"], dtype=np.int16))
    mask_layer_pixels = int(canonical_ground_mask.sum())
    collision_markers = dict(MARKERS)
    blocked, collision_meta = base.build_collision_grid(water_mask, collision_masks)
    # S'assurer que la nouvelle allée sous la maison est intégralement passable.
    for gx, gy in patch_info["connector_grid_cells"]:
        blocked[max(0, gy - 1):min(GH, gy + 2), max(0, gx - 1):min(GW, gx + 2)] = 0
    for x, y in MARKERS.values():
        blocked[max(1, y // TILE - 1):min(GH - 1, y // TILE + 2), max(1, x // TILE - 1):min(GW - 1, x // TILE + 2)] = 0
    collision_meta["walkable_cells"] = int((blocked == 0).sum())
    collision_meta["right_house_path_connected"] = True
    collision = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(collision, "RGBA")
    for gy in range(GH):
        for gx in range(GW):
            color = (42, 224, 105, 108) if blocked[gy, gx] == 0 else (244, 71, 65, 128)
            d.rectangle((gx * TILE, gy * TILE, gx * TILE + 7, gy * TILE + 7), fill=color)
    for name, (x, y) in MARKERS.items():
        d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(255, 215, 86, 255) if name != "entree_sud" else (70, 255, 145, 255))
    collision.save(RENDERS / "ZGT2_collision_walkability.png", optimize=True)
    Image.alpha_composite(Image.fromarray(frame0), collision).save(RENDERS / "ZGT2_collision_preview.png", optimize=True)

    ora_layers = [
        ("07 Chemin canonique / panneaux retirés", static["patch"], True),
        ("06 Maison droite isolée — jour", static["house"], True),
        ("05 Canopée générée", static["canopy"], True),
        ("04 Habitations et pont générés", static["structures"], True),
        ("03 Détails générés", static["details"], True),
        ("02 Eau T00P01 — phase 0", water_frames[0], True),
        ("01 Textures de sol T00P01 8x8", static["terrain"], True),
        ("00 Sol résiduel généré", static["base"], True),
    ]
    write_ora(RENDERS / "ZGT2_layers.ora", ora_layers, frame0)

    stack = [
        ("SOL_RESIDUEL genere", [static["base"]], 60, 0),
        ("SOL_T00P01 cellules_canoniques_8x8", [static["terrain"]], 60, 0),
        ("EAU_T00P01 36x2ticks", water_frames, WATER_FRAME_LENGTH, 0),
        ("DETAILS vegetation_basse", [static["details"]], 60, 0),
        ("HABITATIONS_PONT zones_generees", [static["structures"]], 60, 0),
        ("MAISON_DROITE detourage_jour", [static["house"]], 60, 0),
        ("CANOPEE Top", [static["canopy"]], 60, 4),
        ("LIENS_PANNEAUX T00P01", [static["patch"]], 60, 0),
    ]
    base.ROOT = ROOT
    base.RENDERS = RENDERS
    base.CACHE = CACHE
    base.STAGE = STAGE
    base.PREFIX = PREFIX
    base.NAMESPACE = NAMESPACE
    base.ASSET = ASSET
    base.MARKERS = collision_markers
    bank_counts = base.finalize_pmdo(stack, blocked)
    # Le générateur PMDO partagé porte encore des libellés ZGT1; corrige les deux copies
    # de travail avant de reconstruire l'archive V2 au nom explicite.
    project = RENDERS / "PMDO_project"
    for folder in (STAGE, project):
        ground_file = folder / f"Data/Ground/{ASSET}.rsground"
        if ground_file.exists():
            doc = json.loads(ground_file.read_text(encoding="utf-8"))
            obj = doc["Object"]
            obj["Name"] = {"DefaultText": "Village arboricole de guilde — ZGT2", "LocalTexts": {}}
            obj["Comment"] = (
                "Prototype ZGT2 issu du layout ZGT1 approuvé. Sol/liaison et eau : échantillons pixels T00P01; "
                "bâtiments et décor restant générés. Quatre panneaux retirés; maison droite reliée au chemin. "
                "Collisions approximatives; animation du GIF town_map.gif en attente de réattache; non testé en runtime."
            )
            ground_file.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        mod_xml = folder / "Mod.xml"
        if mod_xml.exists():
            text = mod_xml.read_text(encoding="utf-8")
            text = text.replace("Village arboricole de guilde — ZGT1", "Village arboricole de guilde — ZGT2")
            text = text.replace("pixels générés; art non approuvé.", "sol T00P01 échantillonné; art V2 à revoir.")
            mod_xml.write_text(text, encoding="utf-8")
    old_mod = RENDERS / "ZGT1_PMDO_0812.zip"
    if old_mod.exists():
        old_mod.unlink()
    new_mod = RENDERS / "ZGT2_PMDO_0812.zip"
    with zipfile.ZipFile(new_mod, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(project.rglob("*")):
            if path.is_file():
                archive.write(path, Path(NAMESPACE) / path.relative_to(project))

    # Fusion ORA/aperçu utilise la même partition que le Ground, avec l'eau animée.
    visible = np.concatenate((scene_rgb[~water_mask], water_frames[0][..., :3][water_mask]))
    palette_set = {tuple(int(v) for v in c) for c in palette}
    unique, counts = np.unique(visible, axis=0, return_counts=True)
    exact = sum(int(n) for c, n in zip(unique, counts) if tuple(int(v) for v in c) in palette_set) / len(visible)
    manifest: dict[str, object] = {
        "map_id": "zone_guilde_treehouse_v2",
        "prefix": PREFIX,
        "asset_name": ASSET,
        "namespace": NAMESPACE,
        "parent": {"map_id": "zone_guilde_treehouse_v1", "layout_approved": True,
                   "preserved": True, "requested_changes": ["connecter la maison droite", "retirer les quatre panneaux", "sprites transparents et variante nuit"]},
        "dimensions_px": [W, H],
        "dimensions_tiles": [GW, GH],
        "tile_size_px": [TILE, TILE],
        "reference": {"code": "T00P01", "path": "source/zone_guilde_treehouse_v1/reference/T00P01_canonique.png",
                      "sha256": sha256(ref_path), "role": "palette et échantillons directs de textures 8x8/eau"},
        "attachment_animation": {"filename": "town_map.gif", "status": "file not accessible; user will reattach",
                                 "use": "grass/water animation to integrate after re-upload; not claimed in this build"},
        "art_approved": False,
        "runtime_tested": False,
        "layers": ["sol_residuel_genere", "sol_T00P01_8x8", "eau_T00P01", "details", "habitations_pont", "maison_droite", "canopee", "liens_et_panneaux_T00P01"],
        "canonical_ground": {"path_atlas": "tilesheets/ZGT2_T00P01_textures_8px.png",
                              "path_sha256": ground_atlas_manifest["atlas_sha256"],
                              "source_tile_library": {name: len(bank["tiles"]) for name, bank in banks.items()},
                              "pixels_in_canonical_ground_layer": mask_layer_pixels,
                              "source_tilemap": "tilesheets/ZGT2_terrain_source_tiles.npz",
                              "note": "sols et nouveau lien faits avec des cellules exactes 8x8 du rendu T00P01; ce n'est pas une revendication d'ID BPC"},
        "water": {"source": "T00P01 BPL/BPA sample atlas", "frame_count": WATER_FRAMES,
                  "frame_length": WATER_FRAME_LENGTH, "loop_ticks": WATER_LOOP_TICKS,
                  "mask_pixels": int(water_mask.sum()), "atlas_sha256": sha256(REFS / "T00P01_eau_atlas.npz")},
        "palette_fit": {"reference_colors": int(len(palette)), "rgb_mean_before_quantization": round(float(palette_dist[~water_mask].mean()), 2),
                        "rgb_p95_before_quantization": round(float(np.percentile(palette_dist[~water_mask], 95)), 2),
                        "exact_palette_ratio": round(float(exact), 6)},
        "signs_removed": list(SIGN_CELLS),
        "right_house_connector": patch_info["connector_grid_cells"],
        "markers_px": MARKERS,
        "collision": collision_meta,
        "sprite_assets": sprite_manifest,
        "pmdo_tile_banks": bank_counts,
        "total_tile_entries": int(sum(bank_counts.values())),
        "limitations": [
            "La scène décorée reste un rendu généré; seuls les échantillons de sol/eau et le nouveau raccord utilisent des pixels source T00P01.",
            "Le GIF town_map.gif sera intégré après réattache; aucune phase d'herbe n'en est revendiquée ici.",
            "Le QG isolé réutilise le sprite généré du lot guild_structures_v1; il n'est pas un détourage du QG central fondu avec sa canopée dans ZGT1.",
            "La maison droite est une découpe manuelle du rendu généré; la variante nuit avec filtre Abyss V4 est une proposition provisoire, pas un style validé; collisions approximatives; runtime PMDO non testé.",
        ],
    }
    (RENDERS / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (RENDERS / "README_PACK.md").write_text(
        "# ZGT2 — Village arboricole de guilde (V2)\n\n"
        "ZGT1 reste inchangée et sa composition validée est conservée. Cette V2 ajoute un chemin canonique vers la maison droite, retire les quatre panneaux, isole cette maison en calque, et livre un atlas transparent jour/nuit.\n\n"
        "Les surfaces retouchées du sol et le raccord utilisent des échantillons 8x8 exacts du rendu canonique T00P01; l'eau reste animée à partir de son atlas canonique. Le reste de la scène est généré, puis quantifié sur la palette T00P01 : il n'est pas présenté comme extrait de la ROM.\n\n"
        "Le GIF animé `town_map.gif` n'est pas accessible dans le workspace. La végétation animée de cette pièce jointe est en attente de réattache; le sol de cette version reste statique.\n\n"
        "Sprites: `tilesheets/ZGT2_structures_sans_fond_8px.png` + TSX Tiled; PNG séparés dans `sprites/`. Le QG treehouse vient du lot Structures Guilde déjà isolé; la petite maison est détourée depuis ZGT1. La nuit Abyss V4 est une proposition provisoire, non validée comme style final.\n\n"
        "Pas de runtime PMDO, art V2 à réexaminer. Reconstruction: `.venv/bin/python source/zone_guilde_treehouse_v2/build.py`; tests: `.venv/bin/python -m unittest source.zone_guilde_treehouse_v2.test_build -v`.\n",
        encoding="utf-8",
    )
    html_path = ROOT / "apercu_zone_guilde_treehouse_v2.html"
    write_viewer(html_path, manifest)
    delivery = write_delivery_zip()
    print(f"[{PREFIX}] OK: map 768x576, sol canonique {mask_layer_pixels}px, panneaux=4, walkable={collision_meta['walkable_cells']}, banques={len(bank_counts)}")
    print(f"Sprites: {sprite_manifest['atlas']}; PMDO: {new_mod}; livrable: {delivery}")


if __name__ == "__main__":
    main()
