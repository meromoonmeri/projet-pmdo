#!/usr/bin/env python3
"""BMF1 — Bosquet Mycélien : Clairière des Lanternes (768×576).

La composition est un rendu généré référencé sur Mushroom Forest RRT. Les couleurs finales
sont quantifiées vers la palette du rip, mais les pixels générés ne sont pas
présentés comme des tuiles natives certifiées.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BRUTS = HERE / "bruts"
RENDERS = ROOT / "renders" / "bosquet_mycelien_v1"
CACHE = ROOT / ".cache" / "bosquet_mycelien_v1"
STAGE = CACHE / "stage" / "bosquet_mycelien"
REF_PATH = HERE / "references" / "Mushroom_Forest_RRT.png"
FULL_PATH = BRUTS / "sol_complet.png"
BG_PATH = BRUTS / "fond_sans_objets.png"
DECOR_PATH = BRUTS / "decor_magenta.png"
REJECTED_FLOOR_PATH = BRUTS / "ecartes" / "sol_complet_obstacles_sur_route.png"
REJECTED_BG_PATH = BRUTS / "ecartes" / "fond_sans_objets_1194x880.png"
README_PATH = HERE / "README.md"

W, H = 768, 576
TW = TH = 8
GW, GH = W // TW, H // TH
PREFIX = "BMF1"
MAP_ID = "bosquet_mycelien_v1"
NAMESPACE = "bosquet_mycelien"
ASSET = "bmf1_bosquet_mycelien"
LOOP_TICKS = 192
FRAME_TICKS = 8
N_FRAMES = LOOP_TICKS // FRAME_TICKS
ENTRY = [384, 552]
CLEARING = [384, 470]
OBJECTIVE = [384, 112]


def loadmod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Impossible de charger {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def down_class(src: np.ndarray, h: int = H, w: int = W) -> np.ndarray:
    """Réduction nearest déterministe, sans interpolation des pixels de décor."""
    sh, sw = src.shape[:2]
    ys = ((np.arange(h) + 0.5) * sh / h).astype(int).clip(0, sh - 1)
    xs = ((np.arange(w) + 0.5) * sw / w).astype(int).clip(0, sw - 1)
    return src[np.ix_(ys, xs)].copy()


def load_down_rgb(path: Path) -> np.ndarray:
    return down_class(np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8))


def reference_palette() -> tuple[np.ndarray, cKDTree]:
    src = np.asarray(Image.open(REF_PATH).convert("RGB"), dtype=np.uint8)
    palette = np.unique(src.reshape(-1, 3), axis=0)
    return palette, cKDTree(palette.astype(np.float32))


def palette_distance(rgb: np.ndarray, mask: np.ndarray, tree: cKDTree) -> dict[str, float | int]:
    pix = rgb[mask].reshape(-1, 3).astype(np.float32)
    if len(pix) == 0:
        return {"rgb_distance": 0.0, "p95": 0.0, "pixels": 0}
    dist = tree.query(pix, k=1, workers=1)[0]
    return {
        "rgb_distance": round(float(dist.mean()), 2),
        "p95": round(float(np.percentile(dist, 95)), 2),
        "pixels": int(len(pix)),
    }


def quantize_to_reference(rgb: np.ndarray, palette: np.ndarray, tree: cKDTree) -> np.ndarray:
    pix = rgb.reshape(-1, 3).astype(np.float32)
    idx = tree.query(pix, k=1, workers=1)[1]
    return palette[idx].reshape(rgb.shape).astype(np.uint8)


def rgb_to_rgba(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros((H, W, 4), dtype=np.uint8)
    out[..., :3] = rgb
    out[..., 3] = mask.astype(np.uint8) * 255
    out[~mask, :3] = 0
    return out


def magenta_key(rgb: np.ndarray) -> np.ndarray:
    """Sélectionne uniquement la grande route magenta, pas les chapeaux roses."""
    r, g, b = rgb.astype(np.int16).transpose(2, 0, 1)
    candidate = (r > 150) & (b > 150) & (r - g > 80) & (b - g > 80)
    labels, count = ndi.label(candidate)
    if count == 0:
        raise ValueError("Aucune clé magenta détectée")
    sizes = np.bincount(labels.ravel())
    label = int(1 + np.argmax(sizes[1:]))
    key = labels == label
    if int(key.sum()) < 40_000 or not key[-1].any():
        raise ValueError("La grande route magenta sud est absente")
    return key


def build_floor_mask(raw_decor: np.ndarray | None = None) -> np.ndarray:
    """Deux branches autour de l'îlot, reliées à l'entrée et aux lanternes."""
    raw = load_down_rgb(DECOR_PATH) if raw_decor is None else raw_decor
    floor = ndi.binary_closing(magenta_key(raw), structure=np.ones((3, 3), dtype=bool))
    labels, _ = ndi.label(floor)
    label = int(labels[ENTRY[1], ENTRY[0]])
    if label == 0:
        raise ValueError("L'entrée sud n'est pas sur la route")
    floor = labels == label
    out = floor.copy()
    for x, y in (ENTRY, CLEARING, OBJECTIVE):
        out[max(0, y - 8):min(H, y + 8), max(0, x - 8):min(W, x + 8)] = True
    return out


def extract_decor(
    palette: np.ndarray, tree: cKDTree
) -> tuple[np.ndarray, dict[str, np.ndarray], list[dict[str, object]], np.ndarray, np.ndarray]:
    """Partitionne le décor en sous-bois, bois, champignons et plans spatiaux."""
    raw = load_down_rgb(DECOR_PATH)
    key = magenta_key(raw)
    opaque = ~key

    labels, count = ndi.label(opaque)
    center_label = int(labels[335, 384])
    if count < 2 or center_label == 0:
        raise ValueError("Îlot central fermé introuvable")
    island = labels == center_label
    if island[0].any() or island[-1].any() or island[:, 0].any() or island[:, -1].any():
        raise ValueError("L'îlot central touche un bord")
    outer = opaque & ~island

    r, g, b = raw.astype(np.int16).transpose(2, 0, 1)
    value = np.maximum(np.maximum(r, g), b)
    low = np.minimum(np.minimum(r, g), b)
    chroma = value - low
    fungus_seed = outer & (((value > 175) & (chroma > 24)) | ((r > 185) & (g > 145) & (b > 120)))
    wood_seed = outer & ~fungus_seed & (r > g + 12) & (b > g + 6) & (r > 65) & (b > 60) & (value < 190)
    under_seed = outer & ~fungus_seed & ~wood_seed & ((value < 155) | (b > g + 8))
    if min(int(fungus_seed.sum()), int(wood_seed.sum()), int(under_seed.sum())) < 1000:
        raise ValueError("Graines de segmentation fongique insuffisantes")

    distances = np.stack([
        ndi.distance_transform_edt(~under_seed),
        ndi.distance_transform_edt(~wood_seed),
        ndi.distance_transform_edt(~fungus_seed),
    ])
    cls = np.argmin(distances, axis=0)
    groups: dict[str, np.ndarray] = {
        "sous_bois": outer & (cls == 0),
        "bois": outer & (cls == 1),
        "champignons": outer & (cls == 2),
        "arche_nord": np.zeros((H, W), dtype=bool),
        "ilot_central": island.copy(),
        "premier_plan": np.zeros((H, W), dtype=bool),
    }

    yy, xx = np.indices((H, W))
    arch_zone = (xx >= 190) & (xx < 578) & (yy < 220)
    front_zone = yy >= 485
    groups["arche_nord"] = groups["champignons"] & arch_zone
    groups["champignons"] &= ~groups["arche_nord"]
    groups["premier_plan"] = (groups["champignons"] | groups["bois"]) & front_zone
    groups["champignons"] &= ~groups["premier_plan"]
    groups["bois"] &= ~groups["premier_plan"]

    total = sum(mask.astype(np.uint8) for mask in groups.values())
    if not np.array_equal(total > 0, opaque):
        raise AssertionError("Partition fongique incomplète")
    if int((total > 1).sum()) != 0:
        raise AssertionError("Chevauchement dans la partition fongique")

    components: list[dict[str, object]] = []
    for name, mask in groups.items():
        yy_m, xx_m = np.where(mask)
        components.append({
            "kind": name,
            "bbox": [int(xx_m.min()), int(yy_m.min()), int(xx_m.max()) + 1, int(yy_m.max()) + 1],
            "pixels": int(mask.sum()),
            "islands": int(ndi.label(mask)[1]),
        })

    decor_rgb = quantize_to_reference(raw, palette, tree)
    decor_rgba = rgb_to_rgba(decor_rgb, opaque)
    layers = {name: rgb_to_rgba(decor_rgb, mask) for name, mask in groups.items()}
    return decor_rgba, layers, components, raw, opaque


def make_pixel_shadows(palette: np.ndarray) -> np.ndarray:
    """Ombres de contact discrètes de l'îlot et des grands pieds nord."""
    low = Image.new("RGBA", (W // 2, H // 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(low, "RGBA")
    target = np.array([45, 55, 104], dtype=float)
    shade = tuple(int(v) for v in palette[np.argmin(((palette.astype(float) - target) ** 2).sum(1))])
    d.ellipse((246 / 2, 402 / 2, 522 / 2, 465 / 2), fill=(*shade, 48))
    for cx, cy, rx, ry in ((293, 203, 28, 7), (471, 201, 28, 7)):
        d.ellipse(((cx - rx) / 2, (cy - ry) / 2, (cx + rx) / 2, (cy + ry) / 2), fill=(*shade, 44))
    return np.asarray(low.resize((W, H), Image.Resampling.NEAREST)).copy()


def _effect_colors(palette: np.ndarray) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    targets = (np.array([72, 245, 233]), np.array([247, 59, 132]), np.array([255, 220, 183]))
    return tuple(
        tuple(int(v) for v in palette[np.argmin(((palette.astype(float) - target) ** 2).sum(1))])
        for target in targets
    )  # type: ignore[return-value]


def make_lantern_frame(t: int, palette: np.ndarray) -> np.ndarray:
    """Pulsations calculées des petits champignons cyan, roses et crème."""
    t %= N_FRAMES
    cyan, pink, cream = _effect_colors(palette)
    colors = (cyan, pink, cream)
    positions = (
        (348, 106), (421, 109), (347, 151), (424, 154), (300, 172),
        (469, 170), (446, 187), (327, 184), (366, 198), (405, 194),
    )
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    for i, (cx, cy) in enumerate(positions):
        phase = (t - 2 * i) % N_FRAMES
        pulse = 0.5 + 0.5 * np.cos(2.0 * np.pi * phase / N_FRAMES)
        if pulse < 0.12:
            continue
        color = colors[i % 3]
        radius = 1 if pulse < 0.72 else 2
        alpha = int(28 + 96 * pulse)
        d.ellipse((cx - radius - 1, cy - radius - 1, cx + radius + 1, cy + radius + 1), fill=(*color, alpha // 3))
        d.polygon(
            [(cx, cy - radius), (cx + radius, cy), (cx, cy + radius), (cx - radius, cy)],
            fill=(*color, min(180, alpha + 25)),
        )
    return np.asarray(im).copy()


def make_spores_frame(t: int, palette: np.ndarray) -> np.ndarray:
    """Spores calculées en trajectoires fermées autour des deux branches."""
    t %= N_FRAMES
    cyan, pink, cream = _effect_colors(palette)
    colors = (cyan, cream, pink)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    for i in range(18):
        u = (t / N_FRAMES + i / 18.0) % 1.0
        side = -1 if i % 2 == 0 else 1
        cx = 384 + side * int(round(105 + 82 * np.sin(2.0 * np.pi * (u + i * 0.03))))
        cy = 365 + int(round(165 * np.sin(2.0 * np.pi * (u + i / 9.0))))
        pulse = (1.0 + np.sin(2.0 * np.pi * (2.0 * u + i * 0.13))) / 2.0
        if pulse < 0.24:
            continue
        color = colors[i % 3]
        alpha = int(38 + 78 * pulse)
        radius = 1 if pulse < 0.85 else 2
        d.polygon(
            [(cx, cy - radius), (cx + radius, cy), (cx, cy + radius), (cx - radius, cy)],
            fill=(*color, alpha),
        )
        if radius == 2:
            d.point((cx, cy), fill=(*cream, min(170, alpha + 24)))
    return np.asarray(im).copy()


def make_animation_frames(palette: np.ndarray) -> tuple[list[np.ndarray], list[np.ndarray]]:
    return (
        [make_lantern_frame(t, palette) for t in range(N_FRAMES)],
        [make_spores_frame(t, palette) for t in range(N_FRAMES)],
    )


def composite(
    layers: dict[str, np.ndarray],
    lanterns: np.ndarray | None = None,
    spores: np.ndarray | None = None,
) -> np.ndarray:
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for name in (
        "sol", "murs", "ombres", "sous_bois", "bois", "champignons",
        "arche_nord", "ilot_central", "premier_plan",
    ):
        out.alpha_composite(Image.fromarray(layers[name], "RGBA"))
    if lanterns is not None:
        out.alpha_composite(Image.fromarray(lanterns, "RGBA"))
    if spores is not None:
        out.alpha_composite(Image.fromarray(spores, "RGBA"))
    return np.asarray(out).copy()


def build_collision_grid(floor_mask: np.ndarray) -> np.ndarray:
    """Grille sûre : les deux branches et les lanternes restent accessibles."""
    safe = ndi.binary_erosion(floor_mask, structure=np.ones((9, 9), dtype=bool), border_value=0)
    for x, y in (ENTRY, CLEARING, OBJECTIVE):
        safe[max(0, y - 4):min(H, y + 5), max(0, x - 4):min(W, x + 5)] = True
    cells = safe.reshape(GH, 8, GW, 8).mean(axis=(1, 3)) >= 0.60
    grid = (~cells).astype(np.uint8)
    grid[0, :] = 1
    grid[:, 0] = 1
    grid[:, -1] = 1
    grid[-1, :] = 1
    south = floor_mask[-8:, :].reshape(8, GW, 8).mean(axis=(0, 2)) >= 0.50
    grid[-1, south] = 0
    for marker in (ENTRY, CLEARING, OBJECTIVE):
        gx, gy = marker[0] // 8, marker[1] // 8
        grid[gy, gx] = 0
    return grid


def reachable(grid: np.ndarray, start: list[int]) -> set[tuple[int, int]]:
    from collections import deque

    cell = (start[1] // 8, start[0] // 8)
    queue = deque([cell])
    seen = {cell}
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < GH and 0 <= nx < GW and grid[ny, nx] == 0 and (ny, nx) not in seen:
                seen.add((ny, nx))
                queue.append((ny, nx))
    return seen


def write_ora(
    path: Path,
    layers: dict[str, np.ndarray],
    source_full: np.ndarray,
    lanterns: list[np.ndarray],
    spores: list[np.ndarray],
    merged: np.ndarray,
) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    ordered = [
        ("spores_f00", spores[0], True),
        ("lueurs_lanternes_f00", lanterns[0], True),
        ("premier_plan", layers["premier_plan"], True),
        ("ilot_central", layers["ilot_central"], True),
        ("arche_nord", layers["arche_nord"], True),
        ("champignons", layers["champignons"], True),
        ("bois_et_racines", layers["bois"], True),
        ("sous_bois", layers["sous_bois"], True),
        ("ombres", layers["ombres"], True),
        ("murs_fond", layers["murs"], True),
        ("sol_praticable", layers["sol"], True),
        ("sol_complet_reference_generee", source_full, False),
    ]
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "image/openraster", compress_type=zipfile.ZIP_STORED)
        xml = ['<?xml version="1.0" encoding="UTF-8"?>', f'<image version="0.0.1" w="{W}" h="{H}">', "  <stack>"]
        for name, arr, visible in ordered:
            src = f"data/{name}.png"
            vis = "visible" if visible else "hidden"
            xml.append(f'    <layer name="{name}" src="{src}" x="0" y="0" opacity="1.0" visibility="{vis}"/>')
            tmp = CACHE / f"ora_{name}.png"
            Image.fromarray(arr, "RGBA").save(tmp)
            zf.write(tmp, src, compress_type=zipfile.ZIP_DEFLATED)
            tmp.unlink(missing_ok=True)
        xml.extend(["  </stack>", "</image>"])
        zf.writestr("stack.xml", "\n".join(xml), compress_type=zipfile.ZIP_DEFLATED)
        merged_path = CACHE / "ora_merged.png"
        thumb_path = CACHE / "ora_thumb.png"
        Image.fromarray(merged, "RGBA").save(merged_path)
        Image.fromarray(merged, "RGBA").resize((256, 192), Image.Resampling.NEAREST).save(thumb_path)
        zf.write(merged_path, "mergedimage.png", compress_type=zipfile.ZIP_DEFLATED)
        zf.write(thumb_path, "Thumbnails/thumbnail.png", compress_type=zipfile.ZIP_DEFLATED)
        merged_path.unlink(missing_ok=True)
        thumb_path.unlink(missing_ok=True)


def write_pmdo_project(stack: list[tuple[str, list[np.ndarray], int, int]], grid: np.ndarray, gfx, tools) -> dict[str, int]:
    base = loadmod("bmf1_ground_export_base", ROOT / "source/entree_bassin_chauffant_sud_nord_v1/build.py")
    base.PREFIX, base.NAMESPACE, base.ASSET = PREFIX, NAMESPACE, ASSET
    base.STAGE, base.W, base.H = STAGE, W, H
    counts = base.build_pmdo_ground_project(stack, grid, ENTRY, OBJECTIVE, gfx, tools)
    ground_path = STAGE / f"Data/Ground/{ASSET}.rsground"
    ground = json.loads(ground_path.read_text(encoding="utf-8"))
    obj = ground["Object"]
    obj["Name"] = {"DefaultText": "Bosquet Mycélien — Clairière des Lanternes", "LocalTexts": {}}
    obj["Comment"] = (
        "PMDO 0.8.12. Proposition 4:3 (768x576), référence canonique Mushroom Forest "
        "de Pokémon Mystery Dungeon: Red Rescue Team ; composition générée et quantifiée, "
        "non certifiée comme tuiles natives."
    )
    markers = obj.get("Entities", [{}])[0].get("Markers", [])
    if len(markers) >= 2:
        markers[1]["EntName"] = "objectif_lanternes"
        markers.append({
            "EntName": "clairiere",
            "Direction": 4,
            "EntEnabled": True,
            "triggerType": 0,
            "Collider": {"X": CLEARING[0], "Y": CLEARING[1], "Width": 16, "Height": 16},
        })
    ground_path.write_text(json.dumps(ground, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    mod_path = STAGE / "Mod.xml"
    if mod_path.exists():
        text = mod_path.read_text(encoding="utf-8")
        text = re.sub(r"<Name>.*?</Name>", "<Name>Bosquet Mycelien - Clairiere des Lanternes 0.8.12</Name>", text, count=1, flags=re.S)
        text = re.sub(
            r"<Description>.*?</Description>",
            "<Description>Projet d'edition : bosquet fongique a deux branches et arche de champignons-lanternes, reference Mushroom Forest RRT, format 4:3.</Description>",
            text,
            count=1,
            flags=re.S,
        )
        mod_path.write_text(text, encoding="utf-8")
    return counts


def write_viewer(html_path: Path, manifest: dict[str, object]) -> None:
    rel = "renders/bosquet_mycelien_v1"
    static = [
        ("sol", "01_sol.png", "Sol praticable menthe"),
        ("murs", "02_murs.png", "Sous-couche mycélienne"),
        ("ombres", "03_ombres.png", "Ombres de contact"),
        ("sous_bois", "04_sous_bois.png", "Sous-bois indigo"),
        ("bois", "05_bois.png", "Bois et racines"),
        ("champignons", "06_champignons.png", "Champignons géants"),
        ("arche_nord", "07_arche_nord.png", "Arche des lanternes"),
        ("ilot_central", "08_ilot_central.png", "Îlot central"),
        ("premier_plan", "09_premier_plan.png", "Premier plan"),
    ]
    layers_js = json.dumps(
        [{"id": key, "label": label, "src": f"{rel}/layers/{PREFIX}_{code}"} for key, code, label in static],
        ensure_ascii=False,
    )
    lantern_js = json.dumps([f"{rel}/anim/{PREFIX}_10_lueurs_lanternes_f{i:02d}.png" for i in range(N_FRAMES)])
    spores_js = json.dumps([f"{rel}/anim/{PREFIX}_11_spores_f{i:02d}.png" for i in range(N_FRAMES)])
    rows = "".join(
        f"<li>{name} : {info['rgb_distance']} (moyenne RGB vers la palette)</li>"
        for name, info in manifest["fidelity"].items()
    )
    frame_ms = round(FRAME_TICKS * 1000 / 60)
    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aperçu BMF1 — Clairière des Lanternes</title><style>
:root{{color-scheme:dark}}body{{margin:0;padding:20px;background:#17152b;color:#f8e9ef;font:14px/1.45 system-ui,sans-serif}}h1{{font-size:21px;margin:0 0 5px;color:#79f4dc}}.meta{{color:#d5b9e8;margin-bottom:12px}}.row{{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}}.stage{{position:relative;width:min(768px,95vw);aspect-ratio:4/3;background:#20234d;border:1px solid #7c5fc0;image-rendering:pixelated;overflow:hidden}}.stage img{{position:absolute;inset:0;width:100%;height:100%;object-fit:fill;image-rendering:pixelated}}#walk{{z-index:50;pointer-events:none}}.panel{{max-width:390px;background:#242044;border:1px solid #69559b;border-radius:8px;padding:12px}}button,a{{color:#89f7e0}}button{{background:#352c5a;border:1px solid #8b6bc7;border-radius:5px;padding:7px 11px;cursor:pointer}}label{{display:block;margin:5px 0}}.links{{display:flex;gap:11px;flex-wrap:wrap;margin:12px 0}}small{{color:#c9add3}}ul{{padding-left:20px}}
</style></head><body><h1>Bosquet Mycélien — Clairière des Lanternes (BMF1)</h1>
<div class="meta">768×576 px · 96×72 cases de 8 px · entrée sud → deux branches autour de l'îlot → lanternes nord fermées · lueurs et spores calculées (24×8 ticks) · référence <code>Mushroom Forest RRT</code></div>
<div class="links"><button id="play">⏸ Pause</button><button id="walkToggle">Afficher la marche</button><span id="tick">tick 000 / {LOOP_TICKS}</span></div>
<div class="row"><div class="stage" id="stage"><img id="walk" src="{rel}/{PREFIX}_walkability.png" style="display:none;opacity:.68"></div>
<div class="panel"><strong>Calques</strong><div id="controls"></div><hr><strong>Fidélité avant quantification</strong><ul>{rows}</ul><small>Composition générée référencée, non certifiée comme tuiles natives. Animations créées pour ce lot, pas cycles ROM. Runtime PMDO non testé.</small>
<div class="links"><a href="livrable_bosquet_mycelien_v1.zip">ZIP PNG / ORA</a><a href="mod_bosquet_mycelien_pmdo_0812.zip">Projet PMDO 0.8.12</a></div></div></div>
<script>
const layers={layers_js}, lanterns={lantern_js}, spores={spores_js};const stage=document.getElementById('stage');let nodes={{}},playing=true,idx=0;
for(const l of layers){{const im=document.createElement('img');im.src=l.src;im.dataset.layer=l.id;stage.appendChild(im);nodes[l.id]=im;}}
for(const [id,frames] of [['lueurs_lanternes',lanterns],['spores',spores]]){{const im=document.createElement('img');im.src=frames[0];im.dataset.layer=id;stage.appendChild(im);nodes[id]=im;}}
const controls=document.getElementById('controls');for(const l of [...layers,{{id:'lueurs_lanternes',label:'Lueurs des lanternes'}},{{id:'spores',label:'Spores animées'}}]){{const lab=document.createElement('label');lab.innerHTML=`<input type="checkbox" checked> ${{l.label}}`;lab.firstChild.onchange=e=>nodes[l.id].style.display=e.target.checked?'block':'none';controls.appendChild(lab);}}
setInterval(()=>{{if(!playing)return;idx=(idx+1)%lanterns.length;nodes.lueurs_lanternes.src=lanterns[idx];nodes.spores.src=spores[idx];document.getElementById('tick').textContent=`tick ${{String(idx*{FRAME_TICKS}).padStart(3,'0')}} / {LOOP_TICKS}`;}},{frame_ms});
document.getElementById('play').onclick=e=>{{playing=!playing;e.target.textContent=playing?'⏸ Pause':'▶ Lecture';}};let show=false;document.getElementById('walkToggle').onclick=()=>{{show=!show;document.getElementById('walk').style.display=show?'block':'none';}};
</script></body></html>"""
    html_path.write_text(html, encoding="utf-8")


def build() -> dict[str, object]:
    for path in (
        REF_PATH, FULL_PATH, BG_PATH, DECOR_PATH,
        REJECTED_FLOOR_PATH, REJECTED_BG_PATH, README_PATH,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if RENDERS.exists():
        shutil.rmtree(RENDERS)
    RENDERS.mkdir(parents=True)
    shutil.copyfile(README_PATH, RENDERS / "README.md")

    palette, tree = reference_palette()
    full_raw = load_down_rgb(FULL_PATH)
    bg_raw = load_down_rgb(BG_PATH)
    _, decor_layers, components, decor_raw, opaque = extract_decor(palette, tree)
    floor_mask = build_floor_mask(decor_raw)
    wall_mask = ~floor_mask
    bg_quant = quantize_to_reference(bg_raw, palette, tree)
    full_quant = quantize_to_reference(full_raw, palette, tree)
    full_rgba = rgb_to_rgba(full_quant, np.ones((H, W), dtype=bool))

    original_floor = magenta_key(decor_raw)
    floor_source = bg_raw.copy()
    floor_source[original_floor] = full_raw[original_floor]
    floor_quant = bg_quant.copy()
    floor_quant[original_floor] = full_quant[original_floor]
    shadows = make_pixel_shadows(palette)

    static: dict[str, np.ndarray] = {
        "sol_complet": full_rgba,
        "sol": rgb_to_rgba(floor_quant, floor_mask),
        "murs": rgb_to_rgba(bg_quant, wall_mask),
        "ombres": shadows,
        **decor_layers,
    }
    lantern_frames, spore_frames = make_animation_frames(palette)
    grid = build_collision_grid(floor_mask)
    seen = reachable(grid, ENTRY)
    for marker in (CLEARING, OBJECTIVE):
        if (marker[1] // 8, marker[0] // 8) not in seen:
            raise ValueError(f"Marqueur inaccessible : {marker}")
    for branch in ([220, 330], [548, 330]):
        if (branch[1] // 8, branch[0] // 8) not in seen:
            raise ValueError(f"Branche inaccessible : {branch}")

    fungus_mask = np.logical_or.reduce([
        decor_layers[name][..., 3] > 0
        for name in ("champignons", "arche_nord", "ilot_central", "premier_plan")
    ])
    fidelity = {
        "sol": palette_distance(floor_source, floor_mask, tree),
        "sous_bois": palette_distance(decor_raw, decor_layers["sous_bois"][..., 3] > 0, tree),
        "bois": palette_distance(decor_raw, decor_layers["bois"][..., 3] > 0, tree),
        "champignons": palette_distance(decor_raw, fungus_mask, tree),
        "scene_complete": palette_distance(full_raw, np.ones((H, W), dtype=bool), tree),
    }
    for name, info in fidelity.items():
        if info["pixels"] < 1000 or info["rgb_distance"] >= 35:
            raise ValueError(f"Fidélité RGB insuffisante ({name}: {info})")

    layer_dir = RENDERS / "layers"
    anim_dir = RENDERS / "anim"
    layer_dir.mkdir()
    anim_dir.mkdir()
    static_order = [
        ("00_sol_complet", "sol_complet"), ("01_sol", "sol"), ("02_murs", "murs"),
        ("03_ombres", "ombres"), ("04_sous_bois", "sous_bois"), ("05_bois", "bois"),
        ("06_champignons", "champignons"), ("07_arche_nord", "arche_nord"),
        ("08_ilot_central", "ilot_central"), ("09_premier_plan", "premier_plan"),
    ]
    for code, key in static_order:
        Image.fromarray(static[key], "RGBA").save(layer_dir / f"{PREFIX}_{code}.png")
    for i, frame in enumerate(lantern_frames):
        Image.fromarray(frame, "RGBA").save(anim_dir / f"{PREFIX}_10_lueurs_lanternes_f{i:02d}.png")
    for i, frame in enumerate(spore_frames):
        Image.fromarray(frame, "RGBA").save(anim_dir / f"{PREFIX}_11_spores_f{i:02d}.png")

    frames: list[np.ndarray] = []
    for i in range(N_FRAMES):
        frame = composite(static, lantern_frames[i], spore_frames[i])
        frames.append(frame)
        Image.fromarray(frame, "RGBA").save(RENDERS / f"{PREFIX}_scene_t{i * FRAME_TICKS:03d}.png")
    pil_frames = [Image.fromarray(frame, "RGBA") for frame in frames]
    frame_ms = round(FRAME_TICKS * 1000 / 60)
    pil_frames[0].save(
        RENDERS / f"{PREFIX}_anim.webp", save_all=True, append_images=pil_frames[1:],
        duration=frame_ms, loop=0, lossless=True,
    )
    pil_frames[0].save(
        RENDERS / f"{PREFIX}_anim.png", format="PNG", save_all=True,
        append_images=pil_frames[1:], duration=frame_ms, loop=0, disposal=2,
    )

    overlay = Image.fromarray(frames[0], "RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")
    for gy in range(GH):
        for gx in range(GW):
            if grid[gy, gx] == 0:
                draw.rectangle((gx * 8, gy * 8, gx * 8 + 7, gy * 8 + 7), fill=(35, 230, 170, 72))
    for x, y, color in (
        (ENTRY[0], ENTRY[1], (0, 255, 150, 255)),
        (CLEARING[0], CLEARING[1], (255, 218, 92, 255)),
        (OBJECTIVE[0], OBJECTIVE[1], (255, 91, 174, 255)),
    ):
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color)
    overlay.save(RENDERS / f"{PREFIX}_walkability.png")

    write_ora(
        RENDERS / f"{PREFIX}_bosquet_mycelien.ora", static, full_rgba,
        lantern_frames, spore_frames, frames[0],
    )
    gfx = loadmod("pmdo_codec_bmf1", ROOT / "source/pmdo_cote/build.py")
    tools = loadmod("index_tools_bmf1", ROOT / "source/pmdo_cote/INSTALLER.py")
    stack = [
        ("sol", [static["sol"]], 60, 0), ("murs", [static["murs"]], 60, 0),
        ("ombres", [static["ombres"]], 60, 0), ("sous_bois", [static["sous_bois"]], 60, 0),
        ("bois", [static["bois"]], 60, 0), ("champignons", [static["champignons"]], 60, 0),
        ("arche_nord", [static["arche_nord"]], 60, 0),
        ("ilot_central", [static["ilot_central"]], 60, 0),
        ("premier_plan", [static["premier_plan"]], 60, 0),
        ("lueurs_lanternes (anime 24x8t)", lantern_frames, FRAME_TICKS, 0),
        ("spores (anime 24x8t)", spore_frames, FRAME_TICKS, 0),
    ]
    bank_counts = write_pmdo_project(stack, grid, gfx, tools)

    manifest: dict[str, object] = {
        "map_id": MAP_ID,
        "title": "Bosquet Mycélien — Clairière des Lanternes",
        "prefix": PREFIX,
        "reference": "Mushroom Forest (Red Rescue Team)",
        "reference_file": REF_PATH.name,
        "reference_sha256": sha256_of(REF_PATH),
        "reference_source": (
            "Pokémon Mystery Dungeon: Red Rescue Team — Friend Area Mushroom Forest ; "
            "rip Toastypk, découpe de jeu déjà archivée dans le dépôt"
        ),
        "reference_dimensions_px": [456, 336],
        "reference_kind": "clairière menthe bordée de champignons géants multicolores",
        "dimensions_px": [W, H], "dimensions_tiles": [GW, GH],
        "tile_size_px": [TW, TH], "aspect_ratio": "4:3",
        "layout": (
            "entrée sud, deux branches autour d'un îlot fongique central, corridor de lanternes "
            "et grande arche nord fermée"
        ),
        "loop_ticks": LOOP_TICKS,
        "animation": {
            "lueurs_lanternes": {"frames": N_FRAMES, "ticks_per_frame": FRAME_TICKS, "native": False},
            "spores": {"frames": N_FRAMES, "ticks_per_frame": FRAME_TICKS, "native": False},
        },
        "art_approved": False, "runtime_tested": False,
        "markers": {"entree_sud": ENTRY, "clairiere": CLEARING, "objectif_lanternes": OBJECTIVE},
        "walkable_cells": int((grid == 0).sum()), "obstacle_cells": int((grid != 0).sum()),
        "reachable_cells_from_entry": len(seen), "component_count": len(components),
        "fidelity": fidelity, "palette_colors": int(len(palette)),
        "pmdo_banks": bank_counts, "total_tiles": int(sum(bank_counts.values())),
        "layers": [
            "sol_complet", "sol", "murs", "ombres", "sous_bois", "bois", "champignons",
            "arche_nord", "ilot_central", "premier_plan", "lueurs_lanternes", "spores",
        ],
        "raw_inputs": {
            "decor_magenta.png": sha256_of(DECOR_PATH),
            "fond_sans_objets.png": sha256_of(BG_PATH),
            "sol_complet.png": sha256_of(FULL_PATH),
        },
        "rejected_raws": [
            {
                "path": "bruts/ecartes/sol_complet_obstacles_sur_route.png",
                "sha256": sha256_of(REJECTED_FLOOR_PATH),
                "reason": "première édition du sol : rangée de petits champignons ajoutée sur le passage sud",
            },
            {
                "path": "bruts/ecartes/fond_sans_objets_1194x880.png",
                "sha256": sha256_of(REJECTED_BG_PATH),
                "reason": "sortie générée en 1194x880 ; conservée avant normalisation nearest vers 1200x896",
            },
        ],
        "notes": [
            "Composition générée avec Mushroom Forest RRT en référence ; route sur magenta puis segmentation multicalque.",
            f"Tous les RGB statiques sont quantifiés vers les {len(palette)} couleurs de la référence ; cela ne certifie pas des tuiles natives.",
            "Lueurs des lanternes et spores sont des animations calculées pour BMF1, pas des cycles officiels récupérés.",
            "Nord, ouest et est fermés ; aucun warp configuré ; chargement et gameplay PMDO non testés.",
        ],
    }
    (RENDERS / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_viewer(ROOT / "apercu_bosquet_mycelien_v1.html", manifest)

    mod_zip = ROOT / "mod_bosquet_mycelien_pmdo_0812.zip"
    with zipfile.ZipFile(mod_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file():
                archive.write(path, Path(NAMESPACE) / path.relative_to(STAGE))
    liv_zip = ROOT / "livrable_bosquet_mycelien_v1.zip"
    with zipfile.ZipFile(liv_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(RENDERS.rglob("*")):
            if path.is_file():
                archive.write(path, Path("renders/bosquet_mycelien_v1") / path.relative_to(RENDERS))
        archive.write(ROOT / "apercu_bosquet_mycelien_v1.html", "apercu_bosquet_mycelien_v1.html")

    print(
        f"[{PREFIX}] OK: {W}x{H}, walkable={manifest['walkable_cells']}, "
        f"tiles={manifest['total_tiles']}, "
        f"fidelity={ {name: info['rgb_distance'] for name, info in fidelity.items()} }"
    )
    return {
        "manifest": manifest, "grid": grid, "layers": static,
        "components": components, "frame0": frames[0],
    }


def main() -> None:
    build()


if __name__ == "__main__":
    main()
