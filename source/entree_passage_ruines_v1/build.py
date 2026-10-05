#!/usr/bin/env python3
"""EPR1 — Entrée du Sentier des Ruines (768×576, 4:3).

Composition nouvelle guidée par le rendu canonique PMD Sky ``P22P01A``.
Les pixels générés ne sont pas certifiés comme tuiles natives.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import uuid
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BRUTS = HERE / "bruts"
RENDERS = ROOT / "renders" / "entree_passage_ruines_v1"
CACHE = ROOT / ".cache" / "entree_passage_ruines_v1"
STAGE = CACHE / "stage" / "entree_passage_ruines"
REF_PATH = HERE / "references" / "P22P01A.png"
FULL_PATH = BRUTS / "sol_complet.png"
BG_PATH = BRUTS / "fond_sans_objets.png"
DECOR_PATH = BRUTS / "decor_magenta.png"

W, H = 768, 576
TW = TH = 8
GW, GH = W // TW, H // TH
PREFIX = "EPR1"
MAP_ID = "entree_passage_ruines_v1"
NAMESPACE = "entree_passage_ruines"
ASSET = "epr1_entree_passage_ruines"
LOOP_TICKS = 192
FRAME_TICKS = 8
N_FRAMES = LOOP_TICKS // FRAME_TICKS
ENTRY = [384, 540]
BOSS = [384, 330]
EXIT = [384, 140]


def loadmod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Impossible de charger {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def down_class(src: np.ndarray, h: int = H, w: int = W) -> np.ndarray:
    """Échantillonnage nearest déterministe (même méthode que les cartes PMDO 4:3)."""
    sh, sw = src.shape[:2]
    ys = ((np.arange(h) + 0.5) * sh / h).astype(int).clip(0, sh - 1)
    xs = ((np.arange(w) + 0.5) * sw / w).astype(int).clip(0, sw - 1)
    return src[np.ix_(ys, xs)].copy()


def load_down_rgb(path: Path) -> np.ndarray:
    return down_class(np.asarray(Image.open(path).convert("RGB")))


def patch_outer_top(rgb: np.ndarray) -> np.ndarray:
    """Le brut EPR1 remplit déjà la toile entière : conserver ses bords exacts."""
    return rgb.copy()


def build_floor_mask() -> np.ndarray:
    """Aire ouverte du sentier : clairière centrale, arche nord et accès sud."""
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    rects = [
        (136, 156, 632, 462),      # clairière praticable entre les ruines latérales
        (300, 82, 468, 198),       # passage ouvert et dais sous l'arche nord
        (315, 430, 453, 576),      # sentier d'entrée sud
    ]
    for x0, y0, x1, y1 in rects:
        d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
    return np.asarray(mask) > 0


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


def extract_decor(
    palette: np.ndarray, tree: cKDTree
) -> tuple[np.ndarray, dict[str, np.ndarray], list[dict[str, object]], np.ndarray, np.ndarray]:
    """Key magenta and split the connected generated props into architectural groups."""
    raw = load_down_rgb(DECOR_PATH)
    r, g, b = raw.astype(np.int16).transpose(2, 0, 1)
    key = (r > 120) & (b > 120) & (r - g > 64) & (b - g > 60)
    opaque = ~key
    labels, n = ndi.label(opaque)
    groups: dict[str, np.ndarray] = {
        "ruines": np.zeros((H, W), dtype=bool),
        "vegetation": np.zeros((H, W), dtype=bool),
        "steles": np.zeros((H, W), dtype=bool),
        "debris": np.zeros((H, W), dtype=bool),
    }
    components: list[dict[str, object]] = []
    assigned = np.zeros((H, W), dtype=bool)
    for label_id in range(1, n + 1):
        component = labels == label_id
        yy, xx = np.where(component)
        if len(xx) < 20:
            continue
        x0, x1 = int(xx.min()), int(xx.max()) + 1
        y0, y1 = int(yy.min()), int(yy.max()) + 1
        w, h = x1 - x0, y1 - y0
        if y0 < 20 and w > 650 and h > 180:
            kind = "ruines"  # paroi nord, arche, arbres/rochers arrière
        elif y0 > 285 and (x0 < 330 or x1 > 438) and (w > 150 or h > 120):
            kind = "vegetation"  # berges de blocs, arbres et racines de premier plan
        elif y0 > 285 and 55 <= w <= 135 and 65 <= h <= 125:
            kind = "steles"  # deux monolithes cassés sur les côtés de la clairière
        else:
            kind = "debris"  # pierres isolées et petits raccords
        groups[kind] |= component
        assigned |= component
        components.append({"kind": kind, "bbox": [x0, y0, x1, y1], "pixels": int(len(xx))})
    groups["debris"] |= opaque & ~assigned
    decor_rgb = quantize_to_reference(raw, palette, tree)
    decor_rgba = rgb_to_rgba(decor_rgb, opaque)
    layers = {name: rgb_to_rgba(decor_rgb, mask) for name, mask in groups.items()}
    return decor_rgba, layers, components, raw, opaque


def make_pixel_shadows(components: list[dict[str, object]], palette: np.ndarray) -> np.ndarray:
    """Ombres de contact discrètes sous les stèles, dessinées en pixels de 2 px."""
    scale = 2
    low = Image.new("RGBA", (W // scale, H // scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(low, "RGBA")
    target = np.array([70, 83, 42], dtype=float)
    shade = tuple(int(v) for v in palette[np.argmin(((palette.astype(float) - target) ** 2).sum(1))])
    for item in components:
        if item["kind"] != "steles":
            continue
        x0, _, x1, y1 = item["bbox"]
        center_x = (x0 + x1) / 2
        width = min(48, max(28, int((x1 - x0) * 0.52)))
        height = 8
        center_y = y1 - 2
        box = (
            (center_x - width / 2) / scale,
            (center_y - height / 2) / scale,
            (center_x + width / 2) / scale,
            (center_y + height / 2) / scale,
        )
        d.ellipse(box, fill=(*shade, 52))
    return np.asarray(low.resize((W, H), Image.Resampling.NEAREST)).copy()


def make_pollen_frames(palette: np.ndarray) -> list[np.ndarray]:
    """Poussières lumineuses calculées depuis la palette, non extraites du cycle ROM."""
    soft_target = np.array([218, 229, 112], dtype=float)
    bright_target = np.array([246, 240, 165], dtype=float)
    soft = tuple(int(v) for v in palette[np.argmin(((palette.astype(float) - soft_target) ** 2).sum(1))])
    bright = tuple(int(v) for v in palette[np.argmin(((palette.astype(float) - bright_target) ** 2).sum(1))])
    frames: list[np.ndarray] = []
    for t in range(N_FRAMES):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im, "RGBA")
        for i in range(8):
            phase = (t / N_FRAMES + i / 8.0) * 2.0 * np.pi
            cx = 384 + int(round(76 * np.cos(phase)))
            cy = 307 + int(round(112 * np.sin(phase)))
            pulse = (1.0 + np.sin(2.0 * np.pi * (t / 12.0 + i / 8.0))) / 2.0
            if pulse < 0.28:
                continue
            radius = 1 if pulse < 0.8 else 2
            alpha = int(38 + pulse * 76)
            d.polygon([(cx, cy - radius), (cx + radius, cy), (cx, cy + radius), (cx - radius, cy)], fill=(*soft, alpha))
            d.point((cx, cy), fill=(*bright, min(150, alpha + 16)))
        frames.append(np.asarray(im).copy())
    return frames


def composite(layers: dict[str, np.ndarray], pollen: np.ndarray | None = None) -> np.ndarray:
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for name in ("sol", "murs", "ombres", "ruines", "vegetation", "steles", "debris"):
        out.alpha_composite(Image.fromarray(layers[name], "RGBA"))
    if pollen is not None:
        out.alpha_composite(Image.fromarray(pollen, "RGBA"))
    return np.asarray(out).copy()


def build_collision_grid(floor_mask: np.ndarray, decor_masks: dict[str, np.ndarray], components: list[dict[str, object]]) -> np.ndarray:
    """0 = marchable, 1 = obstacle/mur ; accès continu sud → arche nord."""
    centers = floor_mask[4::8, 4::8]
    walk = centers[:GH, :GW].copy()
    obstacle_pixels = np.zeros((H, W), dtype=bool)
    for name in ("ruines", "vegetation", "steles", "debris"):
        obstacle_pixels |= decor_masks[name][..., 3] > 0
    yy, xx = np.indices((H, W))
    # L'arche est un passage ouvert : préserver un couloir de dix cases au centre.
    open_axis = (xx >= 344) & (xx < 424) & (yy >= 88)
    obstacle_pixels &= ~open_axis
    obstacle_cells = obstacle_pixels.reshape(GH, 8, GW, 8).any(axis=(1, 3))
    walk &= ~obstacle_cells
    grid = (~walk).astype(np.uint8)
    for marker in (ENTRY, BOSS, EXIT):
        x, y = marker[0] // 8, marker[1] // 8
        if grid[y, x] != 0:
            raise ValueError(f"Marqueur non praticable: {marker}")
    return grid


def write_ora(path: Path, layers: dict[str, np.ndarray], source_full: np.ndarray, pollen_frames: list[np.ndarray], merged: np.ndarray) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    ordered = [
        ("pollen_dore_f00", pollen_frames[0], True),
        ("debris", layers["debris"], True),
        ("steles", layers["steles"], True),
        ("vegetation_rochers", layers["vegetation"], True),
        ("arche_ruines", layers["ruines"], True),
        ("ombres", layers["ombres"], True),
        ("bords_herbeux", layers["murs"], True),
        ("sentier_sol", layers["sol"], True),
        ("sol_complet_reference_generee", source_full, False),
    ]
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "image/openraster", compress_type=zipfile.ZIP_STORED)
        stack_xml = ['<?xml version="1.0" encoding="UTF-8"?>', f'<image version="0.0.1" w="{W}" h="{H}">', "  <stack>"]
        for name, arr, visible in ordered:
            src = f"data/{name}.png"
            vis = "visible" if visible else "hidden"
            stack_xml.append(f'    <layer name="{name}" src="{src}" x="0" y="0" opacity="1.0" visibility="{vis}"/>')
            tmp = CACHE / f"ora_{name}.png"
            Image.fromarray(arr, "RGBA").save(tmp)
            zf.write(tmp, src, compress_type=zipfile.ZIP_DEFLATED)
            tmp.unlink(missing_ok=True)
        stack_xml.extend(["  </stack>", "</image>"])
        zf.writestr("stack.xml", "\n".join(stack_xml), compress_type=zipfile.ZIP_DEFLATED)
        merged_path = CACHE / "ora_merged.png"
        thumb_path = CACHE / "ora_thumb.png"
        Image.fromarray(merged, "RGBA").save(merged_path)
        Image.fromarray(merged, "RGBA").resize((256, 192), Image.Resampling.NEAREST).save(thumb_path)
        zf.write(merged_path, "mergedimage.png", compress_type=zipfile.ZIP_DEFLATED)
        zf.write(thumb_path, "Thumbnails/thumbnail.png", compress_type=zipfile.ZIP_DEFLATED)
        merged_path.unlink(missing_ok=True)
        thumb_path.unlink(missing_ok=True)


def write_pmdo_project(stack: list[tuple[str, list[np.ndarray], int, int]], grid: np.ndarray, gfx, tools) -> dict[str, int]:
    base = loadmod("epr1_ground_export_base", ROOT / "source/entree_bassin_chauffant_sud_nord_v1/build.py")
    base.PREFIX, base.NAMESPACE, base.ASSET = PREFIX, NAMESPACE, ASSET
    base.STAGE, base.W, base.H = STAGE, W, H
    counts = base.build_pmdo_ground_project(stack, grid, ENTRY, EXIT, gfx, tools)
    ground_path = STAGE / f"Data/Ground/{ASSET}.rsground"
    ground = json.loads(ground_path.read_text(encoding="utf-8"))
    obj = ground["Object"]
    obj["Name"] = {"DefaultText": "Entrée du Sentier des Ruines (4:3)", "LocalTexts": {}}
    obj["Comment"] = (
        "PMDO 0.8.12. Nouvelle proposition 4:3 (768x576), textures de référence P22P01A "
        "rendues depuis pret/pmd-sky ; illustration générée, non certifiée native."
    )
    markers = obj.get("Entities", [{}])[0].get("Markers", [])
    if len(markers) >= 2:
        markers[1]["EntName"] = "objectif_nord"
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
        text = re.sub(
            r"<Name>.*?</Name>",
            "<Name>Entree Sentier des Ruines 4:3 - Atelier 0.8.12</Name>",
            text,
            count=1,
            flags=re.S,
        )
        text = re.sub(
            r"<Description>.*?</Description>",
            "<Description>Projet d'edition : entree d'un sentier de ruines ouvert, texture canonique PMD Sky P22P01A, 4:3 (768x576), clairiere centrale et arche nord.</Description>",
            text,
            count=1,
            flags=re.S,
        )
        mod_path.write_text(text, encoding="utf-8")
    return counts


def write_viewer(html_path: Path, manifest: dict[str, object]) -> None:
    rel = "renders/entree_passage_ruines_v1"
    src_layers = [
        ("sol", "01_sol.png", "Sol et sentier"),
        ("murs", "02_murs.png", "Bords et relief"),
        ("ombres", "03_ombres.png", "Ombres de contact"),
        ("ruines", "04_ruines.png", "Arche et ruines arrière"),
        ("vegetation", "05_vegetation.png", "Rochers, arbres et racines"),
        ("steles", "06_steles.png", "Stèles brisées"),
        ("debris", "07_debris.png", "Pierres isolées"),
    ]
    layers_js = json.dumps([{"id": k, "label": label, "src": f"{rel}/layers/{PREFIX}_{code}"} for k, code, label in src_layers], ensure_ascii=False)
    frames_js = json.dumps([f"{rel}/anim/{PREFIX}_08_pollen_dore_f{i:02d}.png" for i in range(N_FRAMES)])
    fidelity_rows = "".join(
        f"<li>{name} : {info['rgb_distance']} (moyenne RGB vers la palette du rip)</li>"
        for name, info in manifest["fidelity"].items()
    )
    frame_ms = round(FRAME_TICKS * 1000 / 60)
    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aperçu EPR1 — Sentier des Ruines</title>
<style>
:root{{color-scheme:dark}}body{{margin:0;padding:20px;background:#171610;color:#f3edcf;font:14px/1.45 system-ui,sans-serif}}h1{{font-size:20px;margin:0 0 5px;color:#d9dc77}}.meta{{color:#c0b78f;margin-bottom:14px}}.row{{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}}.stage{{position:relative;width:min(768px,95vw);aspect-ratio:4/3;background:#111;border:1px solid #59633c;image-rendering:pixelated;overflow:hidden}}.stage img{{position:absolute;inset:0;width:100%;height:100%;image-rendering:pixelated;object-fit:fill}}#walk{{z-index:20;pointer-events:none}}.panel{{max-width:380px;background:#242219;border:1px solid #4a432d;border-radius:8px;padding:12px}}button,a{{color:#dbe184}}button{{background:#333820;border:1px solid #788448;border-radius:5px;padding:7px 11px;cursor:pointer}}label{{display:block;margin:5px 0}}.links{{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}}small{{color:#b8b08f}}ul{{padding-left:20px}}
</style></head><body>
<h1>Entrée du Sentier des Ruines — EPR1</h1>
<div class="meta">768×576 px · 96×72 tuiles 8×8 · entrée sud → boss clairière → objectif sous l'arche nord · pollen doré calculé (24×8 ticks) · source : <code>P22P01A</code> (408×408)</div>
<div class="links"><button id="play">⏸ Pause</button><button id="walkToggle">Afficher la marche</button><span id="tick">tick 000 / 192</span></div>
<div class="row"><div class="stage" id="stage"><img id="walk" src="{rel}/{PREFIX}_walkability.png" style="display:none;opacity:.68"></div>
<div class="panel"><strong>Calques transparents</strong><div id="controls"></div><hr><strong>Fidélité de palette</strong><ul>{fidelity_rows}</ul><small>Distance RGB moyenne &lt; 35 sur les catégories listées. Art non approuvé comme tuiles natives ; runtime PMDO non testé.</small>
<div class="links"><a href="livrable_entree_passage_ruines_v1.zip">ZIP PNG/ORA/manifest</a><a href="mod_entree_passage_ruines_pmdo_0812.zip">ZIP PMDO 0.8.12</a></div>
</div></div>
<script>
const rel={json.dumps(rel)}, layers={layers_js}, frames={frames_js};
const stage=document.getElementById('stage'); let nodes={{}}, playing=true, idx=0, showWalk=false;
for(const l of layers){{const im=document.createElement('img');im.src=l.src;im.dataset.layer=l.id;stage.appendChild(im);nodes[l.id]=im;}}
const anim=document.createElement('img');anim.src=frames[0];anim.dataset.layer='pollen_dore';stage.appendChild(anim);nodes.pollen_dore=anim;
const controls=document.getElementById('controls');
for(const l of [...layers,{{id:'pollen_dore',label:'Pollen lumineux calculé'}}]){{const lab=document.createElement('label');lab.innerHTML=`<input type="checkbox" checked> ${{l.label}}`;lab.firstChild.onchange=e=>nodes[l.id].style.display=e.target.checked?'block':'none';controls.appendChild(lab);}}
setInterval(()=>{{if(!playing)return;idx=(idx+1)%frames.length;anim.src=frames[idx];document.getElementById('tick').textContent=`tick ${{String(idx*{FRAME_TICKS}).padStart(3,'0')}} / {LOOP_TICKS}`; }},{frame_ms});
document.getElementById('play').onclick=e=>{{playing=!playing;e.target.textContent=playing?'⏸ Pause':'▶ Lecture';}};
document.getElementById('walkToggle').onclick=()=>{{showWalk=!showWalk;document.getElementById('walk').style.display=showWalk?'block':'none';}};
</script></body></html>"""
    html_path.write_text(html, encoding="utf-8")


def build() -> dict[str, object]:
    if not REF_PATH.is_file() or not FULL_PATH.is_file() or not BG_PATH.is_file() or not DECOR_PATH.is_file():
        raise FileNotFoundError("Rip canonique ou un des trois bruts générés manquant")
    render_readme = RENDERS / "README.md"
    render_readme_text = render_readme.read_text(encoding="utf-8") if render_readme.is_file() else None
    if RENDERS.exists():
        shutil.rmtree(RENDERS)
    RENDERS.mkdir(parents=True, exist_ok=True)
    if render_readme_text is not None:
        (RENDERS / "README.md").write_text(render_readme_text, encoding="utf-8")
    palette, tree = reference_palette()
    full_raw = patch_outer_top(load_down_rgb(FULL_PATH))
    bg_raw = patch_outer_top(load_down_rgb(BG_PATH))
    floor_mask = build_floor_mask()
    wall_mask = ~floor_mask
    full_rgba = rgb_to_rgba(quantize_to_reference(full_raw, palette, tree), np.ones((H, W), dtype=bool))
    bg_quant = quantize_to_reference(bg_raw, palette, tree)
    floor = rgb_to_rgba(bg_quant, floor_mask)
    walls = rgb_to_rgba(bg_quant, wall_mask)
    decor_rgba, decor_layers, components, decor_raw, opaque = extract_decor(palette, tree)
    shadows = make_pixel_shadows(components, palette)

    static = {
        "sol_complet": full_rgba,
        "sol": floor,
        "murs": walls,
        "ombres": shadows,
        "ruines": decor_layers["ruines"],
        "vegetation": decor_layers["vegetation"],
        "steles": decor_layers["steles"],
        "debris": decor_layers["debris"],
    }
    pollen_frames = make_pollen_frames(palette)
    grid = build_collision_grid(floor_mask, decor_layers, components)

    fidelity = {
        "sol": palette_distance(bg_raw, floor_mask, tree),
        "murs": palette_distance(bg_raw, wall_mask, tree),
        "decors": palette_distance(decor_raw, opaque, tree),
        "scene_complete": palette_distance(full_raw, np.ones((H, W), dtype=bool), tree),
    }
    for name in ("sol", "murs", "decors", "scene_complete"):
        if fidelity[name]["rgb_distance"] >= 35:
            raise ValueError(f"Fidélité RGB insuffisante ({name}: {fidelity[name]})")

    RENDERS.mkdir(parents=True, exist_ok=True)
    layer_dir = RENDERS / "layers"
    anim_dir = RENDERS / "anim"
    layer_dir.mkdir(parents=True, exist_ok=True)
    anim_dir.mkdir(parents=True, exist_ok=True)
    static_order = [
        ("00_sol_complet", "sol_complet"),
        ("01_sol", "sol"),
        ("02_murs", "murs"),
        ("03_ombres", "ombres"),
        ("04_ruines", "ruines"),
        ("05_vegetation", "vegetation"),
        ("06_steles", "steles"),
        ("07_debris", "debris"),
    ]
    for code, key in static_order:
        Image.fromarray(static[key], "RGBA").save(layer_dir / f"{PREFIX}_{code}.png")
    for i, frame in enumerate(pollen_frames):
        Image.fromarray(frame, "RGBA").save(anim_dir / f"{PREFIX}_08_pollen_dore_f{i:02d}.png")

    frames: list[np.ndarray] = []
    for t, pollen in enumerate(pollen_frames):
        frame = composite(static, pollen)
        frames.append(frame)
        Image.fromarray(frame, "RGBA").save(RENDERS / f"{PREFIX}_scene_t{t * FRAME_TICKS:03d}.png")
    pil_frames = [Image.fromarray(f, "RGBA") for f in frames]
    frame_ms = round(FRAME_TICKS * 1000 / 60)
    pil_frames[0].save(RENDERS / f"{PREFIX}_anim.webp", save_all=True, append_images=pil_frames[1:], duration=frame_ms, loop=0, lossless=True)
    pil_frames[0].save(RENDERS / f"{PREFIX}_anim.png", format="PNG", save_all=True, append_images=pil_frames[1:], duration=frame_ms, loop=0, disposal=2)

    overlay = Image.fromarray(frames[0], "RGBA")
    d = ImageDraw.Draw(overlay, "RGBA")
    for gy in range(GH):
        for gx in range(GW):
            if grid[gy, gx] == 0:
                d.rectangle((gx * 8, gy * 8, gx * 8 + 7, gy * 8 + 7), fill=(40, 220, 100, 68))
    for x, y, color in (
        (ENTRY[0], ENTRY[1], (0, 255, 128, 255)),
        (BOSS[0], BOSS[1], (255, 211, 64, 255)),
        (EXIT[0], EXIT[1], (255, 84, 72, 255)),
    ):
        d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color)
    overlay.save(RENDERS / f"{PREFIX}_walkability.png")

    ora_layers = {
        "sol_complet": static["sol_complet"],
        "sol": static["sol"],
        "murs": static["murs"],
        "ombres": static["ombres"],
        "ruines": static["ruines"],
        "vegetation": static["vegetation"],
        "steles": static["steles"],
        "debris": static["debris"],
    }
    write_ora(RENDERS / f"{PREFIX}_entree_passage_ruines.ora", ora_layers, full_rgba, pollen_frames, frames[0])

    gfx = loadmod("pmdo_codec_epr1", ROOT / "source/pmdo_cote/build.py")
    tools = loadmod("index_tools_epr1", ROOT / "source/pmdo_cote/INSTALLER.py")
    stack = [
        ("sol", [static["sol"]], 60, 0),
        ("murs", [static["murs"]], 60, 0),
        ("ombres", [static["ombres"]], 60, 0),
        ("ruines", [static["ruines"]], 60, 0),
        ("vegetation", [static["vegetation"]], 60, 0),
        ("steles", [static["steles"]], 60, 0),
        ("debris", [static["debris"]], 60, 0),
        ("pollen_dore (anime 24x8t)", pollen_frames, FRAME_TICKS, 0),
    ]
    bank_counts = write_pmdo_project(stack, grid, gfx, tools)

    manifest: dict[str, object] = {
        "map_id": MAP_ID,
        "title": "Entrée du Sentier des Ruines",
        "prefix": PREFIX,
        "reference": "P22P01A",
        "reference_file": REF_PATH.name,
        "reference_sha256": sha256_of(REF_PATH),
        "reference_source": "pret/pmd-sky, commit c8073235b39746a7ee74e6cea16c730bd91a1e67; rendu MAP_BG P22P01A",
        "reference_dimensions_px": [408, 408],
        "reference_kind": "sentier de pierre dans une clairière de ruines et d'arbres",
        "dimensions_px": [W, H],
        "dimensions_tiles": [GW, GH],
        "tile_size_px": [TW, TH],
        "aspect_ratio": "4:3",
        "loop_ticks": LOOP_TICKS,
        "animation": {"pollen_dore": {"frames": N_FRAMES, "ticks_per_frame": FRAME_TICKS, "native": False}},
        "art_approved": False,
        "runtime_tested": False,
        "markers": {"entree_sud": ENTRY, "boss": BOSS, "objectif_nord": EXIT},
        "walkable_cells": int((grid == 0).sum()),
        "obstacle_cells": int((grid != 0).sum()),
        "component_count": len(components),
        "fidelity": fidelity,
        "palette_colors": int(len(palette)),
        "pmdo_banks": bank_counts,
        "total_tiles": int(sum(bank_counts.values())),
        "layers": ["sol_complet", "sol", "murs", "ombres", "ruines", "vegetation", "steles", "debris", "pollen_dore"],
        "notes": [
            "Composition générée référencée sur le rendu PMD Sky P22P01A ; décor détouré sur magenta.",
            "Couleurs ramenées à la palette RGB du rip ; métriques calculées avant quantification.",
            "Pollen animé calculé depuis la palette, pas extrait d'une animation native.",
            "Textures et géométrie proposées, non certifiées natives ; runtime PMDO non testé.",
        ],
    }
    (RENDERS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path = ROOT / "apercu_entree_passage_ruines_v1.html"
    write_viewer(html_path, manifest)

    mod_zip = ROOT / "mod_entree_passage_ruines_pmdo_0812.zip"
    with zipfile.ZipFile(mod_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(STAGE.rglob("*")):
            if p.is_file():
                zf.write(p, Path(NAMESPACE) / p.relative_to(STAGE))
    liv_zip = ROOT / "livrable_entree_passage_ruines_v1.zip"
    with zipfile.ZipFile(liv_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(RENDERS.rglob("*")):
            if p.is_file():
                zf.write(p, Path("renders/entree_passage_ruines_v1") / p.relative_to(RENDERS))
        zf.write(html_path, html_path.name)

    result = {
        "manifest": manifest,
        "grid": grid,
        "components": components,
        "layers": static,
        "frame0": frames[0],
    }
    print(
        f"[{PREFIX}] OK: {W}x{H} ({GW}x{GH}), walkable={manifest['walkable_cells']}, "
        f"components={len(components)}, tiles={manifest['total_tiles']}, "
        f"fidelity={ {k: v['rgb_distance'] for k, v in fidelity.items()} }"
    )
    return result


def main() -> None:
    build()


if __name__ == "__main__":
    main()
