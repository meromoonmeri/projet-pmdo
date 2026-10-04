#!/usr/bin/env python3
"""FPR1 — Fin du Passage des Ruines : Sanctuaire du Cadran (768×576).

La composition est un rendu généré référencé sur P22P01A. Les couleurs finales
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
RENDERS = ROOT / "renders" / "fin_passage_ruines_v1"
CACHE = ROOT / ".cache" / "fin_passage_ruines_v1"
STAGE = CACHE / "stage" / "fin_passage_ruines"
REF_PATH = HERE / "references" / "P22P01A.png"
FULL_PATH = BRUTS / "sol_complet.png"
BG_PATH = BRUTS / "fond_sans_objets.png"
DECOR_PATH = BRUTS / "decor_magenta.png"
REJECTED_PATH = BRUTS / "ecartes" / "decor_magenta_layout_trop_proche_epr1.png"
REJECTED_FLOOR_PATH = BRUTS / "ecartes" / "sol_complet_herbe_trop_vive.png"
README_PATH = HERE / "README.md"

W, H = 768, 576
TW = TH = 8
GW, GH = W // TW, H // TH
PREFIX = "FPR1"
MAP_ID = "fin_passage_ruines_v1"
NAMESPACE = "fin_passage_ruines"
ASSET = "fpr1_fin_passage_ruines"
LOOP_TICKS = 192
FRAME_TICKS = 8
N_FRAMES = LOOP_TICKS // FRAME_TICKS
ENTRY = [384, 548]
BOSS = [384, 340]
EXIT = [384, 152]


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
    """Clé magenta pure et frange cuite ; aucune matière P22 n'utilise cette teinte."""
    r, g, b = rgb.astype(np.int16).transpose(2, 0, 1)
    return (r > 120) & (b > 120) & (r - g > 62) & (b - g > 58)


def build_floor_mask(raw_decor: np.ndarray | None = None) -> np.ndarray:
    """Sol continu sud → arène → escalier → objectif, dérivé de la clé magenta.

    Le cadran de pierre, l'escalier et le seuil sud sont des structures plates :
    ils sont explicitement rendus praticables, sans ouvrir les terrasses latérales.
    """
    raw = load_down_rgb(DECOR_PATH) if raw_decor is None else raw_decor
    floor = magenta_key(raw)
    flat = Image.fromarray((floor * 255).astype(np.uint8), "L")
    d = ImageDraw.Draw(flat)
    d.ellipse((294, 278, 474, 406), fill=255)      # cadran brisé au centre
    d.rectangle((326, 154, 442, 252), fill=255)   # grand escalier nord
    d.rectangle((334, 424, 438, 576), fill=255)   # seuil et sentier sud
    floor = np.asarray(flat) > 0
    floor = ndi.binary_closing(floor, structure=np.ones((5, 5), dtype=bool))

    # Ne conserver que la composante réellement reliée à l'entrée sud.
    labels, _ = ndi.label(floor)
    ey, ex = ENTRY[1], ENTRY[0]
    label = int(labels[ey, ex])
    if label == 0:
        # Recherche bornée du pixel de sol le plus proche si l'antialiasing a rogné le centre.
        yy, xx = np.where(floor)
        nearest = int(np.argmin((xx - ex) ** 2 + (yy - ey) ** 2))
        label = int(labels[yy[nearest], xx[nearest]])
    floor = labels == label

    # Garantir une assise 16×16 aux trois repères sans créer de nouvelle sortie.
    out = floor.copy()
    for x, y in (ENTRY, BOSS, EXIT):
        out[max(0, y - 8):min(H, y + 8), max(0, x - 8):min(W, x + 8)] = True
    return out


def _draw_sanctuary_geometry() -> np.ndarray:
    """Silhouettes des cinq pierres et de la stèle du cadran, à l'échelle finale."""
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((350, 34, 418, 139), radius=10, fill=255)
    for box in ((282, 79, 319, 151), (318, 57, 350, 143), (418, 57, 450, 143), (449, 79, 486, 151)):
        d.ellipse(box, fill=255)
    return np.asarray(im) > 0


def extract_decor(
    palette: np.ndarray, tree: cKDTree
) -> tuple[np.ndarray, dict[str, np.ndarray], list[dict[str, object]], np.ndarray, np.ndarray]:
    """Détoure le magenta et répartit chaque pixel visible entre cinq calques.

    Le grand contour est connecté ; de simples composantes ne suffisent donc pas.
    Trois familles de graines (végétation, pierre claire, roche ocre) attribuent
    spatialement les contours sombres, puis la géométrie du sanctuaire et les
    petits débris isolés prennent priorité. L'union reste exactement l'opaque.
    """
    raw = load_down_rgb(DECOR_PATH)
    key = magenta_key(raw)
    opaque = ~key
    r, g, b = raw.astype(np.int16).transpose(2, 0, 1)

    veg_seed = opaque & (g > r + 8) & (g > b + 8)
    stone_seed = opaque & ~veg_seed & (r > 105) & (g > 95) & (b > 62) & (np.abs(r - g) < 42) & ((g - b) < 92)
    rock_seed = opaque & ~veg_seed & ~stone_seed & (r > g + 8) & (g > b + 6)
    # Sécurités : chaque famille est bien représentée dans ce brut.
    if min(int(veg_seed.sum()), int(stone_seed.sum()), int(rock_seed.sum())) < 1000:
        raise ValueError("Graines de segmentation insuffisantes")

    distances = np.stack([
        ndi.distance_transform_edt(~veg_seed),
        ndi.distance_transform_edt(~stone_seed),
        ndi.distance_transform_edt(~rock_seed),
    ])
    cls = np.argmin(distances, axis=0)
    groups: dict[str, np.ndarray] = {
        "relief": opaque & (cls == 2),
        "ruines": opaque & (cls == 1),
        "vegetation": opaque & (cls == 0),
        "sanctuaire": np.zeros((H, W), dtype=bool),
        "debris": np.zeros((H, W), dtype=bool),
    }

    labels, n = ndi.label(opaque)
    components: list[dict[str, object]] = []
    sanctuary_geo = _draw_sanctuary_geometry() & opaque
    groups["sanctuaire"] |= sanctuary_geo

    # Les petites composantes seules sont des blocs épars, sauf le cadran central
    # et les pierres du sanctuaire qui restent des ruines / objets sacrés.
    for label_id in range(1, n + 1):
        comp = labels == label_id
        yy, xx = np.where(comp)
        if len(xx) == 0:
            continue
        x0, x1 = int(xx.min()), int(xx.max()) + 1
        y0, y1 = int(yy.min()), int(yy.max()) + 1
        size = int(len(xx))
        if y0 < 180 and 250 < x0 < 520 and size < 12000:
            kind = "sanctuaire"
            groups["sanctuaire"] |= comp
        elif 270 <= y0 and y1 <= 420 and 280 <= x0 and x1 <= 490:
            kind = "ruines"  # fragments du cadran central
            groups["ruines"] |= comp
        elif size < 650:
            kind = "debris"
            groups["debris"] |= comp
        else:
            overlaps = {name: int((groups[name] & comp).sum()) for name in ("relief", "ruines", "vegetation")}
            kind = max(overlaps, key=overlaps.get)
        components.append({"kind": kind, "bbox": [x0, y0, x1, y1], "pixels": size})

    # Priorités exclusives : sanctuaire, débris, ruines, végétation, relief.
    groups["debris"] &= ~groups["sanctuaire"]
    groups["ruines"] &= ~(groups["sanctuaire"] | groups["debris"])
    groups["vegetation"] &= ~(groups["sanctuaire"] | groups["debris"] | groups["ruines"])
    groups["relief"] &= ~(groups["sanctuaire"] | groups["debris"] | groups["ruines"] | groups["vegetation"])
    # Toute poussière non classée rejoint le relief ; aucun pixel ne disparaît.
    union = np.zeros((H, W), dtype=bool)
    for mask in groups.values():
        union |= mask
    groups["relief"] |= opaque & ~union
    if not np.array_equal(np.logical_or.reduce(list(groups.values())), opaque):
        raise AssertionError("Partition de décor incomplète")
    total = sum(mask.astype(np.uint8) for mask in groups.values())
    if int((total > 1).sum()) != 0:
        raise AssertionError("Chevauchement dans la partition de décor")

    decor_rgb = quantize_to_reference(raw, palette, tree)
    decor_rgba = rgb_to_rgba(decor_rgb, opaque)
    layers = {name: rgb_to_rgba(decor_rgb, mask) for name, mask in groups.items()}
    return decor_rgba, layers, components, raw, opaque


def make_pixel_shadows(palette: np.ndarray) -> np.ndarray:
    """Ombres de contact discrètes sous les pierres sacrées, sur un calque séparé."""
    low = Image.new("RGBA", (W // 2, H // 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(low, "RGBA")
    target = np.array([72, 69, 36], dtype=float)
    shade = tuple(int(v) for v in palette[np.argmin(((palette.astype(float) - target) ** 2).sum(1))])
    for cx, cy, rx, ry in ((301, 147, 19, 5), (334, 140, 17, 5), (384, 138, 31, 6), (434, 140, 17, 5), (467, 147, 19, 5)):
        d.ellipse(((cx - rx) / 2, (cy - ry) / 2, (cx + rx) / 2, (cy + ry) / 2), fill=(*shade, 58))
    return np.asarray(low.resize((W, H), Image.Resampling.NEAREST)).copy()


def _effect_colors(palette: np.ndarray) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    targets = (np.array([179, 190, 72]), np.array([222, 229, 113]), np.array([246, 240, 166]))
    return tuple(tuple(int(v) for v in palette[np.argmin(((palette.astype(float) - target) ** 2).sum(1))]) for target in targets)  # type: ignore[return-value]


def make_cadran_frame(t: int, palette: np.ndarray) -> np.ndarray:
    """Onde runique calculée ; t=N_FRAMES redonne exactement t=0."""
    t %= N_FRAMES
    dark, soft, bright = _effect_colors(palette)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    # Douze glyphes autour du cadran, réveillés successivement dans deux sens.
    for i in range(12):
        angle = 2.0 * np.pi * i / 12.0 - np.pi / 2.0
        cx = 384 + int(round(79 * np.cos(angle)))
        cy = 340 + int(round(56 * np.sin(angle)))
        phase = (t - 2 * i) % N_FRAMES
        strength = max(0.0, 1.0 - min(phase, N_FRAMES - phase) / 5.0)
        if strength <= 0:
            continue
        radius = 1 if strength < 0.72 else 2
        alpha = int(42 + 105 * strength)
        color = soft if strength < 0.78 else bright
        d.polygon([(cx, cy - radius), (cx + radius, cy), (cx, cy + radius), (cx - radius, cy)], fill=(*color, alpha))
        d.point((cx, cy), fill=(*bright, min(205, alpha + 30)))
    # L'aiguille gravée de la stèle respire avec le même cycle.
    pulse = 0.5 + 0.5 * np.cos(2.0 * np.pi * t / N_FRAMES)
    alpha = int(34 + 86 * pulse)
    d.line((384, 75, 384, 94), fill=(*dark, alpha), width=2)
    d.line((384, 75, 397, 84), fill=(*bright, alpha), width=2)
    d.ellipse((380, 71, 388, 79), outline=(*soft, alpha), width=1)
    return np.asarray(im).copy()


def make_pollen_frame(t: int, palette: np.ndarray) -> np.ndarray:
    """Pollen doré calculé, en continuité visuelle avec EPR1."""
    t %= N_FRAMES
    _, soft, bright = _effect_colors(palette)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    for i in range(10):
        u = (t / N_FRAMES + i / 10.0) % 1.0
        angle = 2.0 * np.pi * (u + 0.13 * np.sin(2.0 * np.pi * u))
        radius_x = 78 + 22 * np.sin(2.0 * np.pi * (u + i / 5.0))
        cx = 384 + int(round(radius_x * np.cos(angle)))
        cy = 314 + int(round(128 * np.sin(angle)))
        pulse = (1.0 + np.sin(2.0 * np.pi * (2.0 * u + i / 10.0))) / 2.0
        if pulse < 0.3:
            continue
        r = 1 if pulse < 0.82 else 2
        alpha = int(35 + pulse * 75)
        d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=(*soft, alpha))
        d.point((cx, cy), fill=(*bright, min(155, alpha + 20)))
    return np.asarray(im).copy()


def make_animation_frames(palette: np.ndarray) -> tuple[list[np.ndarray], list[np.ndarray]]:
    return (
        [make_cadran_frame(t, palette) for t in range(N_FRAMES)],
        [make_pollen_frame(t, palette) for t in range(N_FRAMES)],
    )


def composite(
    layers: dict[str, np.ndarray],
    cadran: np.ndarray | None = None,
    pollen: np.ndarray | None = None,
) -> np.ndarray:
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for name in ("sol", "murs", "ombres", "relief", "ruines", "vegetation", "sanctuaire", "debris"):
        out.alpha_composite(Image.fromarray(layers[name], "RGBA"))
    if cadran is not None:
        out.alpha_composite(Image.fromarray(cadran, "RGBA"))
    if pollen is not None:
        out.alpha_composite(Image.fromarray(pollen, "RGBA"))
    return np.asarray(out).copy()


def build_collision_grid(floor_mask: np.ndarray) -> np.ndarray:
    """Grille sûre pour un collider 16×16 ; seuls les bords du sud restent ouverts."""
    safe = ndi.binary_erosion(floor_mask, structure=np.ones((11, 11), dtype=bool), border_value=0)
    # Les repères sont posés sur une assise explicitement contrôlée.
    for x, y in (ENTRY, BOSS, EXIT):
        safe[max(0, y - 4):min(H, y + 5), max(0, x - 4):min(W, x + 5)] = True
    # Require most of an 8 px cell to remain inside the eroded floor so a
    # walkable tile cannot cut across a standing stone or a thin ruin wall.
    cells = safe.reshape(GH, 8, GW, 8).mean(axis=(1, 3)) >= 0.60
    grid = (~cells).astype(np.uint8)
    grid[0, :] = 1
    grid[:, 0] = 1
    grid[:, -1] = 1
    grid[-1, :] = 1
    grid[-1, ENTRY[0] // 8 - 4:ENTRY[0] // 8 + 5] = 0
    for marker in (ENTRY, BOSS, EXIT):
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
    cadran: list[np.ndarray],
    pollen: list[np.ndarray],
    merged: np.ndarray,
) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    ordered = [
        ("pollen_dore_f00", pollen[0], True),
        ("lueur_cadran_f00", cadran[0], True),
        ("debris", layers["debris"], True),
        ("sanctuaire_cadran", layers["sanctuaire"], True),
        ("vegetation", layers["vegetation"], True),
        ("ruines", layers["ruines"], True),
        ("relief", layers["relief"], True),
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
    base = loadmod("fpr1_ground_export_base", ROOT / "source/entree_bassin_chauffant_sud_nord_v1/build.py")
    base.PREFIX, base.NAMESPACE, base.ASSET = PREFIX, NAMESPACE, ASSET
    base.STAGE, base.W, base.H = STAGE, W, H
    counts = base.build_pmdo_ground_project(stack, grid, ENTRY, EXIT, gfx, tools)
    ground_path = STAGE / f"Data/Ground/{ASSET}.rsground"
    ground = json.loads(ground_path.read_text(encoding="utf-8"))
    obj = ground["Object"]
    obj["Name"] = {"DefaultText": "Fin du Passage des Ruines — Sanctuaire du Cadran", "LocalTexts": {}}
    obj["Comment"] = (
        "PMDO 0.8.12. Proposition 4:3 (768x576), référence P22P01A rendue depuis pret/pmd-sky ; "
        "composition générée et quantifiée, non certifiée comme tuiles natives."
    )
    markers = obj.get("Entities", [{}])[0].get("Markers", [])
    if len(markers) >= 2:
        markers[1]["EntName"] = "objectif_cadran"
        markers.append({
            "EntName": "boss",
            "Direction": 4,
            "EntEnabled": True,
            "triggerType": 0,
            "Collider": {"X": BOSS[0], "Y": BOSS[1], "Width": 16, "Height": 16},
        })
    ground_path.write_text(json.dumps(ground, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    mod_path = STAGE / "Mod.xml"
    if mod_path.exists():
        text = mod_path.read_text(encoding="utf-8")
        text = re.sub(r"<Name>.*?</Name>", "<Name>Fin Passage des Ruines - Sanctuaire du Cadran 0.8.12</Name>", text, count=1, flags=re.S)
        text = re.sub(
            r"<Description>.*?</Description>",
            "<Description>Projet d'edition : fin du Passage des Ruines, arene ovale et sanctuaire ferme du cadran, texture PMD Sky P22P01A, 4:3.</Description>",
            text,
            count=1,
            flags=re.S,
        )
        mod_path.write_text(text, encoding="utf-8")
    return counts


def write_viewer(html_path: Path, manifest: dict[str, object]) -> None:
    rel = "renders/fin_passage_ruines_v1"
    static = [
        ("sol", "01_sol.png", "Sol praticable"),
        ("murs", "02_murs.png", "Sous-couche du relief"),
        ("ombres", "03_ombres.png", "Ombres de contact"),
        ("relief", "04_relief.png", "Falaises et terrasses"),
        ("ruines", "05_ruines.png", "Murs, escalier et cadran"),
        ("vegetation", "06_vegetation.png", "Végétation"),
        ("sanctuaire", "07_sanctuaire.png", "Stèle et pierres sacrées"),
        ("debris", "08_debris.png", "Débris isolés"),
    ]
    layers_js = json.dumps([{"id": key, "label": label, "src": f"{rel}/layers/{PREFIX}_{code}"} for key, code, label in static], ensure_ascii=False)
    cadran_js = json.dumps([f"{rel}/anim/{PREFIX}_09_lueur_cadran_f{i:02d}.png" for i in range(N_FRAMES)])
    pollen_js = json.dumps([f"{rel}/anim/{PREFIX}_10_pollen_dore_f{i:02d}.png" for i in range(N_FRAMES)])
    rows = "".join(f"<li>{name} : {info['rgb_distance']} (moyenne RGB vers la palette)</li>" for name, info in manifest["fidelity"].items())
    frame_ms = round(FRAME_TICKS * 1000 / 60)
    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aperçu FPR1 — Sanctuaire du Cadran</title><style>
:root{{color-scheme:dark}}body{{margin:0;padding:20px;background:#15170f;color:#f1eed6;font:14px/1.45 system-ui,sans-serif}}h1{{font-size:21px;margin:0 0 5px;color:#dce579}}.meta{{color:#bfb991;margin-bottom:12px}}.row{{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}}.stage{{position:relative;width:min(768px,95vw);aspect-ratio:4/3;background:#111;border:1px solid #59663b;image-rendering:pixelated;overflow:hidden}}.stage img{{position:absolute;inset:0;width:100%;height:100%;object-fit:fill;image-rendering:pixelated}}#walk{{z-index:50;pointer-events:none}}.panel{{max-width:390px;background:#23251a;border:1px solid #4d5332;border-radius:8px;padding:12px}}button,a{{color:#dfe98a}}button{{background:#30351e;border:1px solid #737f42;border-radius:5px;padding:7px 11px;cursor:pointer}}label{{display:block;margin:5px 0}}.links{{display:flex;gap:11px;flex-wrap:wrap;margin:12px 0}}small{{color:#b9b293}}ul{{padding-left:20px}}
</style></head><body><h1>Fin du Passage des Ruines — Sanctuaire du Cadran (FPR1)</h1>
<div class="meta">768×576 px · 96×72 cases de 8 px · entrée sud → arène ovale → stèle nord fermée · lueur et pollen calculés (24×8 ticks) · source <code>P22P01A</code></div>
<div class="links"><button id="play">⏸ Pause</button><button id="walkToggle">Afficher la marche</button><span id="tick">tick 000 / {LOOP_TICKS}</span></div>
<div class="row"><div class="stage" id="stage"><img id="walk" src="{rel}/{PREFIX}_walkability.png" style="display:none;opacity:.68"></div>
<div class="panel"><strong>Calques</strong><div id="controls"></div><hr><strong>Fidélité avant quantification</strong><ul>{rows}</ul><small>Composition générée référencée, non certifiée comme tuiles natives. Animations créées pour ce lot, pas cycles ROM. Runtime PMDO non testé.</small>
<div class="links"><a href="livrable_fin_passage_ruines_v1.zip">ZIP PNG / ORA</a><a href="mod_fin_passage_ruines_pmdo_0812.zip">Projet PMDO 0.8.12</a></div></div></div>
<script>
const layers={layers_js}, cadran={cadran_js}, pollen={pollen_js};const stage=document.getElementById('stage');let nodes={{}},playing=true,idx=0;
for(const l of layers){{const im=document.createElement('img');im.src=l.src;im.dataset.layer=l.id;stage.appendChild(im);nodes[l.id]=im;}}
for(const [id,frames] of [['lueur_cadran',cadran],['pollen_dore',pollen]]){{const im=document.createElement('img');im.src=frames[0];im.dataset.layer=id;stage.appendChild(im);nodes[id]=im;}}
const controls=document.getElementById('controls');for(const l of [...layers,{{id:'lueur_cadran',label:'Lueur runique animée'}},{{id:'pollen_dore',label:'Pollen doré animé'}}]){{const lab=document.createElement('label');lab.innerHTML=`<input type="checkbox" checked> ${{l.label}}`;lab.firstChild.onchange=e=>nodes[l.id].style.display=e.target.checked?'block':'none';controls.appendChild(lab);}}
setInterval(()=>{{if(!playing)return;idx=(idx+1)%cadran.length;nodes.lueur_cadran.src=cadran[idx];nodes.pollen_dore.src=pollen[idx];document.getElementById('tick').textContent=`tick ${{String(idx*{FRAME_TICKS}).padStart(3,'0')}} / {LOOP_TICKS}`;}},{frame_ms});
document.getElementById('play').onclick=e=>{{playing=!playing;e.target.textContent=playing?'⏸ Pause':'▶ Lecture';}};let show=false;document.getElementById('walkToggle').onclick=()=>{{show=!show;document.getElementById('walk').style.display=show?'block':'none';}};
</script></body></html>"""
    html_path.write_text(html, encoding="utf-8")


def build() -> dict[str, object]:
    for path in (REF_PATH, FULL_PATH, BG_PATH, DECOR_PATH, REJECTED_PATH, REJECTED_FLOOR_PATH, README_PATH):
        if not path.is_file():
            raise FileNotFoundError(path)
    if RENDERS.exists():
        shutil.rmtree(RENDERS)
    RENDERS.mkdir(parents=True)
    shutil.copyfile(README_PATH, RENDERS / "README.md")

    palette, tree = reference_palette()
    full_raw = load_down_rgb(FULL_PATH)
    bg_raw = load_down_rgb(BG_PATH)
    decor_rgba, decor_layers, components, decor_raw, opaque = extract_decor(palette, tree)
    floor_mask = build_floor_mask(decor_raw)
    wall_mask = ~floor_mask
    bg_quant = quantize_to_reference(bg_raw, palette, tree)
    full_quant = quantize_to_reference(full_raw, palette, tree)
    full_rgba = rgb_to_rgba(full_quant, np.ones((H, W), dtype=bool))
    # Dans les régions explicitement magenta du décor, l'édition « sol complet »
    # fournit une matière plus riche et exactement cadrée. Le fond sans objets
    # reste la sous-couche des structures plates ajoutées au masque de marche.
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
    cadran_frames, pollen_frames = make_animation_frames(palette)
    grid = build_collision_grid(floor_mask)
    seen = reachable(grid, ENTRY)
    for marker in (BOSS, EXIT):
        if (marker[1] // 8, marker[0] // 8) not in seen:
            raise ValueError(f"Marqueur inaccessible : {marker}")

    fidelity = {
        "sol": palette_distance(floor_source, floor_mask, tree),
        "relief": palette_distance(decor_raw, decor_layers["relief"][..., 3] > 0, tree),
        "ruines": palette_distance(decor_raw, (decor_layers["ruines"][..., 3] > 0) | (decor_layers["sanctuaire"][..., 3] > 0), tree),
        "vegetation": palette_distance(decor_raw, decor_layers["vegetation"][..., 3] > 0, tree),
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
        ("03_ombres", "ombres"), ("04_relief", "relief"), ("05_ruines", "ruines"),
        ("06_vegetation", "vegetation"), ("07_sanctuaire", "sanctuaire"), ("08_debris", "debris"),
    ]
    for code, key in static_order:
        Image.fromarray(static[key], "RGBA").save(layer_dir / f"{PREFIX}_{code}.png")
    for i, frame in enumerate(cadran_frames):
        Image.fromarray(frame, "RGBA").save(anim_dir / f"{PREFIX}_09_lueur_cadran_f{i:02d}.png")
    for i, frame in enumerate(pollen_frames):
        Image.fromarray(frame, "RGBA").save(anim_dir / f"{PREFIX}_10_pollen_dore_f{i:02d}.png")

    frames: list[np.ndarray] = []
    for i in range(N_FRAMES):
        frame = composite(static, cadran_frames[i], pollen_frames[i])
        frames.append(frame)
        Image.fromarray(frame, "RGBA").save(RENDERS / f"{PREFIX}_scene_t{i * FRAME_TICKS:03d}.png")
    pil_frames = [Image.fromarray(frame, "RGBA") for frame in frames]
    frame_ms = round(FRAME_TICKS * 1000 / 60)
    pil_frames[0].save(RENDERS / f"{PREFIX}_anim.webp", save_all=True, append_images=pil_frames[1:], duration=frame_ms, loop=0, lossless=True)
    pil_frames[0].save(RENDERS / f"{PREFIX}_anim.png", format="PNG", save_all=True, append_images=pil_frames[1:], duration=frame_ms, loop=0, disposal=2)

    overlay = Image.fromarray(frames[0], "RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")
    for gy in range(GH):
        for gx in range(GW):
            if grid[gy, gx] == 0:
                draw.rectangle((gx * 8, gy * 8, gx * 8 + 7, gy * 8 + 7), fill=(40, 220, 100, 68))
    for x, y, color in ((ENTRY[0], ENTRY[1], (0, 255, 128, 255)), (BOSS[0], BOSS[1], (255, 211, 64, 255)), (EXIT[0], EXIT[1], (255, 84, 72, 255))):
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color)
    overlay.save(RENDERS / f"{PREFIX}_walkability.png")

    write_ora(RENDERS / f"{PREFIX}_fin_passage_ruines.ora", static, full_rgba, cadran_frames, pollen_frames, frames[0])
    gfx = loadmod("pmdo_codec_fpr1", ROOT / "source/pmdo_cote/build.py")
    tools = loadmod("index_tools_fpr1", ROOT / "source/pmdo_cote/INSTALLER.py")
    stack = [
        ("sol", [static["sol"]], 60, 0), ("murs", [static["murs"]], 60, 0),
        ("ombres", [static["ombres"]], 60, 0), ("relief", [static["relief"]], 60, 0),
        ("ruines", [static["ruines"]], 60, 0), ("vegetation", [static["vegetation"]], 60, 0),
        ("sanctuaire", [static["sanctuaire"]], 60, 0), ("debris", [static["debris"]], 60, 0),
        ("lueur_cadran (anime 24x8t)", cadran_frames, FRAME_TICKS, 0),
        ("pollen_dore (anime 24x8t)", pollen_frames, FRAME_TICKS, 0),
    ]
    bank_counts = write_pmdo_project(stack, grid, gfx, tools)

    manifest: dict[str, object] = {
        "map_id": MAP_ID,
        "title": "Fin du Passage des Ruines — Sanctuaire du Cadran",
        "prefix": PREFIX,
        "reference": "P22P01A",
        "reference_file": REF_PATH.name,
        "reference_sha256": sha256_of(REF_PATH),
        "reference_source": "pret/pmd-sky, commit c8073235b39746a7ee74e6cea16c730bd91a1e67 ; rendu MAP_BG P22P01A",
        "reference_dimensions_px": [408, 408],
        "reference_kind": "sentier de pierre dans une clairière de ruines et d'arbres",
        "dimensions_px": [W, H], "dimensions_tiles": [GW, GH], "tile_size_px": [TW, TH], "aspect_ratio": "4:3",
        "layout": "entrée sud, arène ovale, deux croissants de terrasses, escalier nord, sanctuaire fermé sans sortie",
        "loop_ticks": LOOP_TICKS,
        "animation": {
            "lueur_cadran": {"frames": N_FRAMES, "ticks_per_frame": FRAME_TICKS, "native": False},
            "pollen_dore": {"frames": N_FRAMES, "ticks_per_frame": FRAME_TICKS, "native": False},
        },
        "art_approved": False, "runtime_tested": False,
        "markers": {"entree_sud": ENTRY, "boss": BOSS, "objectif_cadran": EXIT},
        "walkable_cells": int((grid == 0).sum()), "obstacle_cells": int((grid != 0).sum()),
        "reachable_cells_from_entry": len(seen), "component_count": len(components),
        "fidelity": fidelity, "palette_colors": int(len(palette)),
        "pmdo_banks": bank_counts, "total_tiles": int(sum(bank_counts.values())),
        "layers": ["sol_complet", "sol", "murs", "ombres", "relief", "ruines", "vegetation", "sanctuaire", "debris", "lueur_cadran", "pollen_dore"],
        "raw_inputs": {
            "decor_magenta.png": sha256_of(DECOR_PATH),
            "fond_sans_objets.png": sha256_of(BG_PATH),
            "sol_complet.png": sha256_of(FULL_PATH),
        },
        "rejected_raws": [
            {
                "path": "bruts/ecartes/decor_magenta_layout_trop_proche_epr1.png",
                "sha256": sha256_of(REJECTED_PATH),
                "reason": "silhouette trop proche de l'entrée EPR1 ; remplacée par une arène ovale à terrasses asymétriques",
            },
            {
                "path": "bruts/ecartes/sol_complet_herbe_trop_vive.png",
                "sha256": sha256_of(REJECTED_FLOOR_PATH),
                "reason": "herbe centrale trop vive et distance RGB du sol 46,76 >= 35 ; recoloration guidée par P22P01A",
            },
        ],
        "notes": [
            "Composition générée avec P22P01A en référence ; terrain sur magenta puis segmentation multicalque.",
            "Tous les RGB statiques sont quantifiés vers les 109 couleurs du rip ; cela ne certifie pas des tuiles natives.",
            "Lueur du cadran et pollen sont des animations calculées pour FPR1, pas des cycles officiels récupérés.",
            "Nord, ouest et est fermés ; aucun warp configuré ; chargement et gameplay PMDO non testés.",
        ],
    }
    (RENDERS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_viewer(ROOT / "apercu_fin_passage_ruines_v1.html", manifest)

    mod_zip = ROOT / "mod_fin_passage_ruines_pmdo_0812.zip"
    with zipfile.ZipFile(mod_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file():
                archive.write(path, Path(NAMESPACE) / path.relative_to(STAGE))
    liv_zip = ROOT / "livrable_fin_passage_ruines_v1.zip"
    with zipfile.ZipFile(liv_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(RENDERS.rglob("*")):
            if path.is_file():
                archive.write(path, Path("renders/fin_passage_ruines_v1") / path.relative_to(RENDERS))
        archive.write(ROOT / "apercu_fin_passage_ruines_v1.html", "apercu_fin_passage_ruines_v1.html")

    print(
        f"[{PREFIX}] OK: {W}x{H}, walkable={manifest['walkable_cells']}, tiles={manifest['total_tiles']}, "
        f"fidelity={ {name: info['rgb_distance'] for name, info in fidelity.items()} }"
    )
    return {"manifest": manifest, "grid": grid, "layers": static, "components": components, "frame0": frames[0]}


def main() -> None:
    build()


if __name__ == "__main__":
    main()
