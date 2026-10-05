#!/usr/bin/env python3
"""EIZ1 — Entrée de l’Île du Zénith : Portail des Alizés (768×576).

La composition est un rendu généré référencé sur Final Island RRT. Les couleurs
finales sont quantifiées vers la palette du rip, mais les pixels générés ne sont
pas présentés comme des tuiles natives certifiées.
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
RENDERS = ROOT / "renders" / "entree_ile_zenith_v1"
CACHE = ROOT / ".cache" / "entree_ile_zenith_v1"
STAGE = CACHE / "stage" / "entree_ile_zenith"
REF_PATH = HERE / "references" / "Final_Island_RRT.png"
FULL_PATH = BRUTS / "sol_complet.png"
BG_PATH = BRUTS / "fond_sans_objets.png"
DECOR_PATH = BRUTS / "decor_magenta.png"
README_PATH = HERE / "README.md"

W, H = 768, 576
TW = TH = 8
GW, GH = W // TW, H // TH
PREFIX = "EIZ1"
MAP_ID = "entree_ile_zenith_v1"
NAMESPACE = "entree_ile_zenith"
ASSET = "eiz1_entree_ile_zenith"
LOOP_TICKS = 192
FRAME_TICKS = 8
N_FRAMES = LOOP_TICKS // FRAME_TICKS
ENTRY = [384, 552]
LANDING = [384, 430]
GATE = [384, 105]
WEST_LOOKOUT = [86, 285]
EAST_LOOKOUT = [687, 285]
LEFT_BRANCH = [270, 230]
RIGHT_BRANCH = [505, 230]


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


def _magenta_labels(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Étiquette les surfaces de clé sans confondre les ombres violettes."""
    r, g, b = rgb.astype(np.int16).transpose(2, 0, 1)
    candidate = (r > 150) & (b > 150) & (r - g > 80) & (b - g > 80)
    labels, count = ndi.label(candidate)
    if count == 0:
        raise ValueError("Aucune clé magenta détectée")
    sizes = np.bincount(labels.ravel())
    return labels, sizes


def magenta_key(rgb: np.ndarray) -> np.ndarray:
    """Route principale et deux belvédères peints sur la clé magenta."""
    labels, sizes = _magenta_labels(rgb)
    keep = [label for label in range(1, len(sizes)) if int(sizes[label]) >= 250]
    key = np.isin(labels, keep)
    if int(key.sum()) < 70_000 or not key[-1].any():
        raise ValueError("La clé magenta de l'entrée du Zénith est absente")
    return key


def build_floor_mask(raw_decor: np.ndarray | None = None) -> np.ndarray:
    """Deux branches, deux belvédères et un seuil nord reliés à l'arrivée sud."""
    raw = load_down_rgb(DECOR_PATH) if raw_decor is None else raw_decor
    floor = magenta_key(raw)
    image = Image.fromarray((floor.astype(np.uint8) * 255), "L")
    draw = ImageDraw.Draw(image)
    for rect in (
        (110, 255, 184, 313),   # pont ouest
        (588, 255, 664, 313),   # pont est
        (268, 148, 315, 205),   # marches de la branche ouest
    ):
        draw.rectangle(rect, fill=255)
    floor = ndi.binary_closing(np.asarray(image) > 0, structure=np.ones((3, 3), dtype=bool))
    labels, count = ndi.label(floor)
    label = int(labels[ENTRY[1], ENTRY[0]])
    if count != 1 or label == 0:
        raise ValueError("L'entrée du Zénith n'est pas une composante unique")
    floor = labels == label
    for x, y in (ENTRY, LANDING, GATE, WEST_LOOKOUT, EAST_LOOKOUT, LEFT_BRANCH, RIGHT_BRANCH):
        floor[max(0, y - 8):min(H, y + 8), max(0, x - 8):min(W, x + 8)] = True
    return floor


def extract_decor(
    palette: np.ndarray, tree: cKDTree
) -> tuple[np.ndarray, dict[str, np.ndarray], list[dict[str, object]], np.ndarray, np.ndarray]:
    """Partition exclusive du ciel et des plans de l'île flottante."""
    raw = load_down_rgb(DECOR_PATH)
    key = magenta_key(raw)
    opaque = ~key
    r, g, b = raw.astype(np.int16).transpose(2, 0, 1)
    value = np.maximum.reduce([r, g, b])
    low = np.minimum.reduce([r, g, b])
    chroma = value - low
    yy, xx = np.indices((H, W))

    vegetation = opaque & (g > r + 20) & (g > b + 12)
    clouds = (
        opaque & ~vegetation & (r > 175) & (g > 185) & (b > 190) & (yy > 220)
    )
    sky = (
        opaque & ~vegetation & ~clouds & (b > r + 30) & (g > r + 20)
        & (g > 120) & (b > 145)
    )
    stones = (
        opaque & ~vegetation & ~clouds & ~sky & (value > 140) & (chroma < 75)
    )
    rock = opaque & ~(vegetation | clouds | sky | stones)

    groups: dict[str, np.ndarray] = {
        "ciel_detail": sky.copy(),
        "nuages": clouds.copy(),
        "falaises": rock.copy(),
        "vegetation": vegetation.copy(),
        "pierres": stones.copy(),
        "portail": np.zeros((H, W), dtype=bool),
        "ilots_lateraux": np.zeros((H, W), dtype=bool),
        "premier_plan": np.zeros((H, W), dtype=bool),
    }
    terrain = rock | vegetation | stones
    portal_zone = (xx >= 420) & (xx < 590) & (yy < 230)
    side_zone = ((xx < 190) | (xx >= 580)) & (yy >= 145) & (yy < 425)
    front_zone = (yy >= 430) & (xx >= 180) & (xx < 595)
    groups["portail"] = terrain & portal_zone
    groups["ilots_lateraux"] = terrain & side_zone & ~groups["portail"]
    groups["premier_plan"] = (
        terrain & front_zone & ~groups["portail"] & ~groups["ilots_lateraux"]
    )
    moved = groups["portail"] | groups["ilots_lateraux"] | groups["premier_plan"]
    groups["falaises"] &= ~moved
    groups["vegetation"] &= ~moved
    groups["pierres"] &= ~moved

    total = sum(mask.astype(np.uint8) for mask in groups.values())
    if not np.array_equal(total > 0, opaque):
        raise AssertionError("Partition de l'île flottante incomplète")
    if int((total > 1).sum()) != 0:
        raise AssertionError("Chevauchement dans la partition de l'île flottante")

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
    """Ombres de contact légères sous les pierres dressées de la couronne."""
    low_img = Image.new("RGBA", (W // 2, H // 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(low_img, "RGBA")
    target = np.array([82, 93, 104], dtype=float)
    shade = tuple(int(v) for v in palette[np.argmin(((palette.astype(float) - target) ** 2).sum(1))])
    for cx, cy, rx, ry in (
        (286, 99, 15, 4), (489, 109, 16, 4), (567, 160, 17, 5),
        (217, 411, 17, 5), (548, 399, 14, 4),
    ):
        draw.ellipse(
            ((cx - rx) / 2, (cy - ry) / 2, (cx + rx) / 2, (cy + ry) / 2),
            fill=(*shade, 46),
        )
    return np.asarray(low_img.resize((W, H), Image.Resampling.NEAREST)).copy()


def _effect_colors(palette: np.ndarray) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    targets = (np.array([113, 180, 208]), np.array([181, 225, 239]), np.array([240, 249, 250]))
    return tuple(
        tuple(int(v) for v in palette[np.argmin(((palette.astype(float) - target) ** 2).sum(1))])
        for target in targets
    )  # type: ignore[return-value]


def make_portal_frame(t: int, palette: np.ndarray) -> np.ndarray:
    """Runes ascendantes autour des deux piliers du portail des Alizés."""
    t %= N_FRAMES
    dark, soft, bright = _effect_colors(palette)
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    anchors = ((474, 100), (536, 150), (404, 90))
    for pillar, (ax, ay) in enumerate(anchors):
        for i in range(7):
            u = (t / N_FRAMES + i / 7.0 + pillar * 0.19) % 1.0
            y = ay + 88 - int(round(u * 116))
            x = ax + int(round(8 * np.sin(2 * np.pi * (u + pillar / 3))))
            pulse = (1 + np.sin(2 * np.pi * (u * 2 + pillar * 0.23))) / 2
            if pulse < 0.20:
                continue
            color = bright if i % 3 == 0 else soft
            alpha = int(36 + 90 * pulse)
            draw.line((x - 2, y, x, y - 2, x + 2, y, x, y + 2, x - 2, y), fill=(*color, alpha), width=1)
    return np.asarray(image).copy()


def make_cloud_frame(t: int, palette: np.ndarray) -> np.ndarray:
    """Voiles de nuages périodiques : décalage de 8 px sur une période de 192 px."""
    t %= N_FRAMES
    dark, soft, bright = _effect_colors(palette)
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    shift = (t * 8) % 192
    for family, (y, color, alpha) in enumerate(((92, soft, 30), (468, bright, 34), (526, dark, 28))):
        for base in range(-192, W + 192, 192):
            cx = base + shift + family * 57
            draw.ellipse((cx - 24, y - 4, cx + 24, y + 5), fill=(*color, alpha))
            draw.ellipse((cx - 8, y - 9, cx + 16, y + 4), fill=(*color, alpha))
    return np.asarray(image).copy()


def make_animation_frames(palette: np.ndarray) -> tuple[list[np.ndarray], list[np.ndarray]]:
    return (
        [make_portal_frame(t, palette) for t in range(N_FRAMES)],
        [make_cloud_frame(t, palette) for t in range(N_FRAMES)],
    )


def composite(
    layers: dict[str, np.ndarray],
    wind: np.ndarray | None = None,
    clouds: np.ndarray | None = None,
) -> np.ndarray:
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for name in (
        "fond_ciel", "sol", "ombres", "ciel_detail", "nuages", "falaises",
        "vegetation", "pierres", "portail", "ilots_lateraux", "premier_plan",
    ):
        out.alpha_composite(Image.fromarray(layers[name], "RGBA"))
    if clouds is not None:
        out.alpha_composite(Image.fromarray(clouds, "RGBA"))
    if wind is not None:
        out.alpha_composite(Image.fromarray(wind, "RGBA"))
    return np.asarray(out).copy()


def build_collision_grid(floor_mask: np.ndarray) -> np.ndarray:
    """Collisions 8 px : arrivée sud, deux branches, belvédères et seuil nord."""
    safe = ndi.binary_erosion(floor_mask, structure=np.ones((9, 9), dtype=bool), border_value=0)
    markers = (ENTRY, LANDING, GATE, WEST_LOOKOUT, EAST_LOOKOUT, LEFT_BRANCH, RIGHT_BRANCH)
    for x, y in markers:
        safe[max(0, y - 4):min(H, y + 5), max(0, x - 4):min(W, x + 5)] = True
    cells = safe.reshape(GH, 8, GW, 8).mean(axis=(1, 3)) >= 0.60
    grid = (~cells).astype(np.uint8)
    grid[:, 0] = 1
    grid[:, -1] = 1
    grid[0, :] = 1
    grid[-1, :] = 1
    edge = floor_mask[-8:].reshape(8, GW, 8).mean(axis=(0, 2)) >= 0.50
    grid[-1, edge] = 0
    for marker in markers:
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
    wind: list[np.ndarray],
    clouds: list[np.ndarray],
    merged: np.ndarray,
) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    ordered = [
        ("runes_portail_f00", wind[0], True),
        ("voiles_nuages_f00", clouds[0], True),
        ("premier_plan", layers["premier_plan"], True),
        ("ilots_lateraux", layers["ilots_lateraux"], True),
        ("portail_central", layers["portail"], True),
        ("pierres_dressees", layers["pierres"], True),
        ("vegetation", layers["vegetation"], True),
        ("falaises", layers["falaises"], True),
        ("nuages_statiques", layers["nuages"], True),
        ("ciel_detail", layers["ciel_detail"], True),
        ("ombres", layers["ombres"], True),
        ("sol_praticable", layers["sol"], True),
        ("fond_ciel", layers["fond_ciel"], True),
        ("sol_complet_reference_generee", source_full, False),
    ]
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "image/openraster", compress_type=zipfile.ZIP_STORED)
        xml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<image version="0.0.1" w="{W}" h="{H}">',
            "  <stack>",
        ]
        for name, array, visible in ordered:
            src = f"data/{name}.png"
            visibility = "visible" if visible else "hidden"
            xml.append(
                f'    <layer name="{name}" src="{src}" x="0" y="0" '
                f'opacity="1.0" visibility="{visibility}"/>'
            )
            tmp = CACHE / f"ora_{name}.png"
            Image.fromarray(array, "RGBA").save(tmp)
            archive.write(tmp, src, compress_type=zipfile.ZIP_DEFLATED)
            tmp.unlink(missing_ok=True)
        xml.extend(["  </stack>", "</image>"])
        archive.writestr("stack.xml", "\n".join(xml), compress_type=zipfile.ZIP_DEFLATED)
        merged_path = CACHE / "ora_merged.png"
        thumb_path = CACHE / "ora_thumb.png"
        Image.fromarray(merged, "RGBA").save(merged_path)
        Image.fromarray(merged, "RGBA").resize((256, 192), Image.Resampling.NEAREST).save(thumb_path)
        archive.write(merged_path, "mergedimage.png", compress_type=zipfile.ZIP_DEFLATED)
        archive.write(thumb_path, "Thumbnails/thumbnail.png", compress_type=zipfile.ZIP_DEFLATED)
        merged_path.unlink(missing_ok=True)
        thumb_path.unlink(missing_ok=True)


def write_pmdo_project(
    stack: list[tuple[str, list[np.ndarray], int, int]],
    grid: np.ndarray,
    gfx,
    tools,
) -> dict[str, int]:
    base = loadmod("eiz1_ground_export_base", ROOT / "source/entree_bassin_chauffant_sud_nord_v1/build.py")
    base.PREFIX, base.NAMESPACE, base.ASSET = PREFIX, NAMESPACE, ASSET
    base.STAGE, base.W, base.H = STAGE, W, H
    counts = base.build_pmdo_ground_project(stack, grid, ENTRY, GATE, gfx, tools)
    ground_path = STAGE / f"Data/Ground/{ASSET}.rsground"
    ground = json.loads(ground_path.read_text(encoding="utf-8"))
    obj = ground["Object"]
    obj["Name"] = {"DefaultText": "Entrée de l'Île du Zénith — Portail des Alizés", "LocalTexts": {}}
    obj["Comment"] = (
        "PMDO 0.8.12. Entrée 4:3 (768x576), référence Final Island de Pokémon "
        "Mystery Dungeon: Red Rescue Team ; composition générée et quantifiée, "
        "non certifiée comme tuiles natives."
    )
    markers = obj.get("Entities", [{}])[0].get("Markers", [])
    if len(markers) >= 2:
        markers[1]["EntName"] = "seuil_portail"
        for name, point in (
            ("palier_bas", LANDING), ("belvedere_ouest", WEST_LOOKOUT),
            ("belvedere_est", EAST_LOOKOUT),
        ):
            markers.append({
                "EntName": name, "Direction": 4, "EntEnabled": True,
                "triggerType": 0,
                "Collider": {"X": point[0], "Y": point[1], "Width": 16, "Height": 16},
            })
    ground_path.write_text(json.dumps(ground, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    mod_path = STAGE / "Mod.xml"
    if mod_path.exists():
        text = mod_path.read_text(encoding="utf-8")
        text = re.sub(r"<Name>.*?</Name>", "<Name>Entree Ile du Zenith - Portail des Alizes 0.8.12</Name>", text, count=1, flags=re.S)
        text = re.sub(
            r"<Description>.*?</Description>",
            "<Description>Projet d'edition : entree flottante a deux branches, belvederes et portail des Alizes, reference Final Island RRT, format 4:3.</Description>",
            text, count=1, flags=re.S,
        )
        mod_path.write_text(text, encoding="utf-8")
    return counts


def write_viewer(html_path: Path, manifest: dict[str, object]) -> None:
    rel = "renders/entree_ile_zenith_v1"
    static = [
        ("fond_ciel", "01_fond_ciel.png", "Fond de ciel"),
        ("sol", "02_sol.png", "Sol praticable"),
        ("ombres", "03_ombres.png", "Ombres de contact"),
        ("ciel_detail", "04_ciel_detail.png", "Détails du ciel"),
        ("nuages", "05_nuages.png", "Nuages statiques"),
        ("falaises", "06_falaises.png", "Falaises flottantes"),
        ("vegetation", "07_vegetation.png", "Herbe de bordure"),
        ("pierres", "08_pierres.png", "Pierres dressées"),
        ("portail", "09_portail.png", "Portail central"),
        ("ilots_lateraux", "10_ilots_lateraux.png", "Îlots latéraux"),
        ("premier_plan", "11_premier_plan.png", "Premier plan"),
    ]
    layers_js = json.dumps(
        [{"id": key, "label": label, "src": f"{rel}/layers/{PREFIX}_{code}"} for key, code, label in static],
        ensure_ascii=False,
    )
    wind_js = json.dumps([f"{rel}/anim/{PREFIX}_12_runes_portail_f{i:02d}.png" for i in range(N_FRAMES)])
    clouds_js = json.dumps([f"{rel}/anim/{PREFIX}_13_voiles_nuages_f{i:02d}.png" for i in range(N_FRAMES)])
    rows = "".join(
        f"<li>{name} : {info['rgb_distance']} (moyenne RGB vers la palette)</li>"
        for name, info in manifest["fidelity"].items()
    )
    frame_ms = round(FRAME_TICKS * 1000 / 60)
    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aperçu EIZ1 — Portail des Alizés</title><style>
:root{{color-scheme:dark}}body{{margin:0;padding:20px;background:#132638;color:#edfaff;font:14px/1.45 system-ui,sans-serif}}h1{{font-size:21px;margin:0 0 5px;color:#dce98e}}.meta{{color:#b5d9ea;margin-bottom:12px}}.row{{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}}.stage{{position:relative;width:min(768px,95vw);aspect-ratio:4/3;background:#29c7e9;border:1px solid #81b4ca;image-rendering:pixelated;overflow:hidden}}.stage img{{position:absolute;inset:0;width:100%;height:100%;object-fit:fill;image-rendering:pixelated}}#walk{{z-index:50;pointer-events:none}}.panel{{max-width:390px;background:#1a3348;border:1px solid #557f95;border-radius:8px;padding:12px}}button,a{{color:#dce98e}}button{{background:#264b61;border:1px solid #78a6b9;border-radius:5px;padding:7px 11px;cursor:pointer}}label{{display:block;margin:5px 0}}.links{{display:flex;gap:11px;flex-wrap:wrap;margin:12px 0}}small{{color:#b6cdd8}}ul{{padding-left:20px}}
</style></head><body><h1>Entrée de l’Île du Zénith — Portail des Alizés (EIZ1)</h1>
<div class="meta">768×576 px · 96×72 cases de 8 px · arrivée sud → deux branches et belvédères → seuil du portail · runes et nuages calculés (24×8 ticks) · référence <code>Final Island RRT</code></div>
<div class="links"><button id="play">⏸ Pause</button><button id="walkToggle">Afficher la marche</button><span id="tick">tick 000 / {LOOP_TICKS}</span></div>
<div class="row"><div class="stage" id="stage"><img id="walk" src="{rel}/{PREFIX}_walkability.png" style="display:none;opacity:.68"></div>
<div class="panel"><strong>Calques</strong><div id="controls"></div><hr><strong>Fidélité avant quantification</strong><ul>{rows}</ul><small>Composition générée référencée, non certifiée comme tuiles natives. Animations créées pour ce lot, pas cycles ROM. Runtime PMDO non testé.</small>
<div class="links"><a href="livrable_entree_ile_zenith_v1.zip">ZIP PNG / ORA</a><a href="mod_entree_ile_zenith_pmdo_0812.zip">Projet PMDO 0.8.12</a></div></div></div>
<script>
const layers={layers_js}, wind={wind_js}, clouds={clouds_js};const stage=document.getElementById('stage');let nodes={{}},playing=true,idx=0;
for(const l of layers){{const im=document.createElement('img');im.src=l.src;im.dataset.layer=l.id;stage.appendChild(im);nodes[l.id]=im;}}
for(const [id,frames] of [['runes_portail',wind],['voiles_nuages',clouds]]){{const im=document.createElement('img');im.src=frames[0];im.dataset.layer=id;stage.appendChild(im);nodes[id]=im;}}
const controls=document.getElementById('controls');for(const l of [...layers,{{id:'runes_portail',label:'Runes du portail'}},{{id:'voiles_nuages',label:'Voiles de nuages'}}]){{const lab=document.createElement('label');lab.innerHTML=`<input type="checkbox" checked> ${{l.label}}`;lab.firstChild.onchange=e=>nodes[l.id].style.display=e.target.checked?'block':'none';controls.appendChild(lab);}}
setInterval(()=>{{if(!playing)return;idx=(idx+1)%wind.length;nodes.runes_portail.src=wind[idx];nodes.voiles_nuages.src=clouds[idx];document.getElementById('tick').textContent=`tick ${{String(idx*{FRAME_TICKS}).padStart(3,'0')}} / {LOOP_TICKS}`;}},{frame_ms});
document.getElementById('play').onclick=e=>{{playing=!playing;e.target.textContent=playing?'⏸ Pause':'▶ Lecture';}};let show=false;document.getElementById('walkToggle').onclick=()=>{{show=!show;document.getElementById('walk').style.display=show?'block':'none';}};
</script></body></html>"""
    html_path.write_text(html, encoding="utf-8")


def build() -> dict[str, object]:
    for path in (REF_PATH, FULL_PATH, BG_PATH, DECOR_PATH, README_PATH):
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
    original_floor = magenta_key(decor_raw)
    render_floor = floor_mask | original_floor
    bg_quant = quantize_to_reference(bg_raw, palette, tree)
    full_quant = quantize_to_reference(full_raw, palette, tree)
    full_rgba = rgb_to_rgba(full_quant, np.ones((H, W), dtype=bool))
    floor_source = bg_raw.copy()
    floor_source[render_floor] = full_raw[render_floor]
    floor_quant = bg_quant.copy()
    floor_quant[render_floor] = full_quant[render_floor]
    static: dict[str, np.ndarray] = {
        "sol_complet": full_rgba,
        "fond_ciel": rgb_to_rgba(bg_quant, np.ones((H, W), dtype=bool)),
        "sol": rgb_to_rgba(floor_quant, render_floor),
        "ombres": make_pixel_shadows(palette),
        **decor_layers,
    }
    portal_frames, cloud_frames = make_animation_frames(palette)
    grid = build_collision_grid(floor_mask)
    seen = reachable(grid, ENTRY)
    markers = (LANDING, GATE, WEST_LOOKOUT, EAST_LOOKOUT, LEFT_BRANCH, RIGHT_BRANCH)
    for marker in markers:
        if (marker[1] // 8, marker[0] // 8) not in seen:
            raise ValueError(f"Marqueur inaccessible : {marker}")
    if len(seen) != int((grid == 0).sum()):
        raise ValueError("La grille de l'entrée contient une composante isolée")

    r, g, b = decor_raw.astype(np.int16).transpose(2, 0, 1)
    value = np.maximum.reduce([r, g, b])
    vegetation_material = opaque & (g > r + 20) & (g > b + 12)
    rock_family = np.logical_or.reduce([
        decor_layers[name][..., 3] > 0
        for name in ("falaises", "portail", "ilots_lateraux", "premier_plan")
    ])
    rock_material = rock_family & (value > 65)
    fidelity = {
        "sol": palette_distance(floor_source, render_floor, tree),
        "ciel": palette_distance(bg_raw, np.ones((H, W), dtype=bool), tree),
        "roche_hors_contours": palette_distance(decor_raw, rock_material, tree),
        "vegetation": palette_distance(decor_raw, vegetation_material, tree),
        "scene_complete": palette_distance(full_raw, np.ones((H, W), dtype=bool), tree),
    }
    for name, info in fidelity.items():
        if info["pixels"] < 1000 or info["rgb_distance"] >= 35:
            raise ValueError(f"Fidélité RGB insuffisante ({name}: {info})")

    layer_dir, anim_dir = RENDERS / "layers", RENDERS / "anim"
    layer_dir.mkdir(); anim_dir.mkdir()
    static_order = [
        ("00_sol_complet", "sol_complet"), ("01_fond_ciel", "fond_ciel"),
        ("02_sol", "sol"), ("03_ombres", "ombres"),
        ("04_ciel_detail", "ciel_detail"), ("05_nuages", "nuages"),
        ("06_falaises", "falaises"), ("07_vegetation", "vegetation"),
        ("08_pierres", "pierres"), ("09_portail", "portail"),
        ("10_ilots_lateraux", "ilots_lateraux"), ("11_premier_plan", "premier_plan"),
    ]
    for code, key in static_order:
        Image.fromarray(static[key], "RGBA").save(layer_dir / f"{PREFIX}_{code}.png")
    for i, frame in enumerate(portal_frames):
        Image.fromarray(frame, "RGBA").save(anim_dir / f"{PREFIX}_12_runes_portail_f{i:02d}.png")
    for i, frame in enumerate(cloud_frames):
        Image.fromarray(frame, "RGBA").save(anim_dir / f"{PREFIX}_13_voiles_nuages_f{i:02d}.png")

    frames: list[np.ndarray] = []
    for i in range(N_FRAMES):
        frame = composite(static, portal_frames[i], cloud_frames[i])
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
                draw.rectangle((gx * 8, gy * 8, gx * 8 + 7, gy * 8 + 7), fill=(45, 220, 135, 70))
    for x, y, color in (
        (ENTRY[0], ENTRY[1], (0, 255, 150, 255)),
        (LANDING[0], LANDING[1], (255, 218, 92, 255)),
        (GATE[0], GATE[1], (255, 92, 92, 255)),
        (WEST_LOOKOUT[0], WEST_LOOKOUT[1], (116, 220, 255, 255)),
        (EAST_LOOKOUT[0], EAST_LOOKOUT[1], (116, 220, 255, 255)),
    ):
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color)
    overlay.save(RENDERS / f"{PREFIX}_walkability.png")

    write_ora(RENDERS / f"{PREFIX}_entree_ile_zenith.ora", static, full_rgba, portal_frames, cloud_frames, frames[0])
    gfx = loadmod("pmdo_codec_eiz1", ROOT / "source/pmdo_cote/build.py")
    tools = loadmod("index_tools_eiz1", ROOT / "source/pmdo_cote/INSTALLER.py")
    stack = [
        ("fond_ciel", [static["fond_ciel"]], 60, 0), ("sol", [static["sol"]], 60, 0),
        ("ombres", [static["ombres"]], 60, 0), ("ciel_detail", [static["ciel_detail"]], 60, 0),
        ("nuages", [static["nuages"]], 60, 0), ("falaises", [static["falaises"]], 60, 0),
        ("vegetation", [static["vegetation"]], 60, 0), ("pierres", [static["pierres"]], 60, 0),
        ("portail", [static["portail"]], 60, 0), ("ilots_lateraux", [static["ilots_lateraux"]], 60, 0),
        ("premier_plan", [static["premier_plan"]], 60, 0),
        ("runes_portail (anime 24x8t)", portal_frames, FRAME_TICKS, 0),
        ("voiles_nuages (anime 24x8t)", cloud_frames, FRAME_TICKS, 0),
    ]
    bank_counts = write_pmdo_project(stack, grid, gfx, tools)

    manifest: dict[str, object] = {
        "map_id": MAP_ID, "title": "Entrée de l’Île du Zénith — Portail des Alizés",
        "prefix": PREFIX, "series": "Trilogie du Zénith", "series_role": "entrée",
        "reference": "Final Island (Red Rescue Team)", "reference_file": REF_PATH.name,
        "reference_sha256": sha256_of(REF_PATH),
        "reference_source": "Pokémon Mystery Dungeon: Red Rescue Team — Friend Area Final Island ; capture déjà archivée dans le dépôt",
        "reference_dimensions_px": [480, 312],
        "dimensions_px": [W, H], "dimensions_tiles": [GW, GH], "tile_size_px": [8, 8], "aspect_ratio": "4:3",
        "layout": "arrivée sud, palier, deux branches autour d'un puits de ciel, deux belvédères et portail nord",
        "loop_ticks": LOOP_TICKS,
        "animation": {
            "runes_portail": {"frames": N_FRAMES, "ticks_per_frame": FRAME_TICKS, "native": False},
            "voiles_nuages": {"frames": N_FRAMES, "ticks_per_frame": FRAME_TICKS, "native": False},
        },
        "art_approved": False, "runtime_tested": False,
        "markers": {"entree_sud": ENTRY, "palier_bas": LANDING, "seuil_portail": GATE, "belvedere_ouest": WEST_LOOKOUT, "belvedere_est": EAST_LOOKOUT},
        "walkable_cells": int((grid == 0).sum()), "obstacle_cells": int((grid != 0).sum()),
        "reachable_cells_from_entry": len(seen), "component_count": len(components),
        "fidelity": fidelity, "palette_colors": int(len(palette)),
        "pmdo_banks": bank_counts, "total_tiles": int(sum(bank_counts.values())),
        "layers": ["sol_complet", "fond_ciel", "sol", "ombres", "ciel_detail", "nuages", "falaises", "vegetation", "pierres", "portail", "ilots_lateraux", "premier_plan", "runes_portail", "voiles_nuages"],
        "raw_inputs": {"decor_magenta.png": sha256_of(DECOR_PATH), "fond_sans_objets.png": sha256_of(BG_PATH), "sol_complet.png": sha256_of(FULL_PATH)},
        "rejected_raws": [],
        "notes": [
            "Composition générée avec Final Island RRT en référence ; route peinte sur magenta puis segmentée.",
            f"Tous les RGB statiques sont quantifiés vers les {len(palette)} couleurs de la référence ; cela ne certifie pas des tuiles natives.",
            "Runes et voiles de nuages sont calculés pour EIZ1, pas récupérés comme cycles officiels.",
            "Seuil nord sans warp configuré ; chargement et gameplay PMDO non testés.",
        ],
    }
    (RENDERS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_viewer(ROOT / "apercu_entree_ile_zenith_v1.html", manifest)
    mod_zip = ROOT / "mod_entree_ile_zenith_pmdo_0812.zip"
    with zipfile.ZipFile(mod_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file(): archive.write(path, Path(NAMESPACE) / path.relative_to(STAGE))
    delivery_zip = ROOT / "livrable_entree_ile_zenith_v1.zip"
    with zipfile.ZipFile(delivery_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(RENDERS.rglob("*")):
            if path.is_file(): archive.write(path, Path("renders/entree_ile_zenith_v1") / path.relative_to(RENDERS))
        archive.write(ROOT / "apercu_entree_ile_zenith_v1.html", "apercu_entree_ile_zenith_v1.html")
    print(f"[{PREFIX}] OK: {W}x{H}, walkable={manifest['walkable_cells']}, tiles={manifest['total_tiles']}, fidelity={ {name: info['rgb_distance'] for name, info in fidelity.items()} }")
    return {"manifest": manifest, "grid": grid, "layers": static, "components": components, "frame0": frames[0]}


def main() -> None:
    build()


if __name__ == "__main__":
    main()
