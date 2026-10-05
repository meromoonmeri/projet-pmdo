#!/usr/bin/env python3
"""FAC1 — Fin Château Ancien, Salle du Trésor (768×576, 4:3).

Composition nouvelle depuis le rip canonique ``oldcastlepmd.png``. Les propositions
IA ne sont pas certifiées comme tuiles natives : manifest art_approved/runtime_tested=False.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
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
RENDERS = ROOT / "renders" / "fin_chateau_ancien_v1"
CACHE = ROOT / ".cache" / "fin_chateau_ancien_v1"
STAGE = CACHE / "stage" / "fin_chateau_ancien"
REF_PATH = ROOT / "oldcastlepmd.png"
FULL_PATH = BRUTS / "sol_complet.png"
BG_PATH = BRUTS / "fond_sans_objets.png"
DECOR_PATH = BRUTS / "decor_magenta.png"

W, H = 768, 576
TW = TH = 8
GW, GH = W // TW, H // TH
PREFIX = "FAC1"
MAP_ID = "fin_chateau_ancien_v1"
NAMESPACE = "fin_chateau_ancien"
ASSET = "fac1_fin_chateau_ancien"
LOOP_TICKS = 240
FRAME_TICKS = 10
N_FRAMES = LOOP_TICKS // FRAME_TICKS
ENTRY = [384, 520]
BOSS = [384, 280]
EXIT = [384, 165]


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
    """Prolonge la pierre sous les fines marges claires du rendu généré."""
    out = rgb.copy()
    out[:18, 32:736] = out[18:36, 32:736]
    out[:, :32] = out[:, 32:64][:, ::-1]
    out[:, 736:] = out[:, 704:736][:, ::-1]
    return out


def build_floor_mask() -> np.ndarray:
    """Polygones du plancher praticable : arène centrale et deux seuils."""
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    rects = [
        (132, 138, 636, 470),      # vaste arène centrale autour du médaillon
        (286, 92, 482, 210),       # dais / approche de la porte nord
        (307, 430, 461, 548),      # couloir d'entrée sud
        (307, 548, 461, 576),      # seuil sud
        (36, 153, 132, 472),       # alcôves latérales gauches
        (636, 153, 732, 472),      # alcôves latérales droites
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
    """Détoure le magenta et classe les props par composantes, sans crop rectangulaire opaque."""
    raw = load_down_rgb(DECOR_PATH)
    r, g, b = raw.astype(np.int16).transpose(2, 0, 1)
    # Key strict + frange magenta : l'or et l'inox n'ont pas simultanément R/B élevés
    # et G très bas ; les pixels roses d'antialiasing sont eux aussi rejetés.
    key = (r > 120) & (b > 120) & (r - g > 64) & (b - g > 60)
    opaque = ~key
    labels, n = ndi.label(opaque)
    groups: dict[str, np.ndarray] = {
        "porte_medaille": np.zeros((H, W), dtype=bool),
        "coffres": np.zeros((H, W), dtype=bool),
        "statues_rails": np.zeros((H, W), dtype=bool),
        "appliques": np.zeros((H, W), dtype=bool),
        "autres": np.zeros((H, W), dtype=bool),
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
        if w >= 120 and h >= 120:
            kind = "porte_medaille"  # large médaillon central
        elif y0 < 110 and w >= 65 and h >= 60:
            kind = "porte_medaille"
        elif h >= 120 and w < 65:
            kind = "statues_rails"
        elif h >= 68 and 34 <= w <= 90:
            kind = "statues_rails"
        elif w < 23 and h < 34:
            kind = "appliques"
        elif 24 <= w <= 55 and 22 <= h <= 55:
            kind = "coffres"
        else:
            kind = "autres"
        groups[kind] |= component
        assigned |= component
        components.append({"kind": kind, "bbox": [x0, y0, x1, y1], "pixels": int(len(xx))})
    # Tout pixel non-magenta est conservé, même une petite pièce d'ornement isolée.
    groups["autres"] |= opaque & ~assigned
    decor_rgb = quantize_to_reference(raw, palette, tree)
    decor_rgba = rgb_to_rgba(decor_rgb, opaque)
    layers = {name: rgb_to_rgba(decor_rgb, mask) for name, mask in groups.items()}
    return decor_rgba, layers, components, raw, opaque


def make_pixel_shadows(components: list[dict[str, object]], palette: np.ndarray) -> np.ndarray:
    """Ombres courtes discrètes, dessinées sur grille 8 px derrière les props."""
    low = Image.new("RGBA", (GW, GH), (0, 0, 0, 0))
    d = ImageDraw.Draw(low, "RGBA")
    # Brun doré sombre prélevé dans la palette source, avec une opacité modérée.
    cand = palette[(palette[:, 0] > palette[:, 1]) & (palette[:, 1] > palette[:, 2] + 8)]
    if len(cand) == 0:
        shade = (92, 75, 42)
    else:
        target = np.array([104, 84, 42], dtype=float)
        shade = tuple(int(v) for v in cand[np.argmin(((cand.astype(float) - target) ** 2).sum(1))])
    for item in components:
        kind = item["kind"]
        if kind not in {"coffres", "statues_rails"}:
            continue
        x0, y0, x1, y1 = item["bbox"]
        gx0, gy0, gx1, gy1 = x0 / 8, y0 / 8, x1 / 8, y1 / 8
        if kind == "coffres":
            box = (gx0 + 0.35, gy1 - 0.35, gx1 - 0.35, gy1 + 0.7)
            alpha = 72
        elif (y1 - y0) > 120:  # rails : ombre limitée au pied
            box = (gx0 + 0.45, gy1 - 1.0, gx1 - 0.45, gy1 + 0.55)
            alpha = 55
        else:  # statues : petite ellipse sous la base
            box = (gx0 + 0.65, gy1 - 0.55, gx1 - 0.65, gy1 + 0.7)
            alpha = 75
        if box[2] > box[0] and box[3] > box[1]:
            d.ellipse(box, fill=(*shade, alpha))
    return np.asarray(low.resize((W, H), Image.Resampling.NEAREST)).copy()


def make_gold_glints(palette: np.ndarray) -> list[np.ndarray]:
    """Boucle décorative calculée avec deux tons du rip (pas une animation native)."""
    gold = palette[(palette[:, 0] >= palette[:, 1] - 2) & (palette[:, 1] > palette[:, 2] + 14) & (palette[:, 0] > 145)]
    if len(gold) == 0:
        gold = palette
    lum = gold[:, 0] * 0.299 + gold[:, 1] * 0.587 + gold[:, 2] * 0.114
    bright = tuple(int(v) for v in gold[int(np.argmax(lum))])
    warm_target = np.array([215, 176, 80], dtype=float)
    warm = tuple(int(v) for v in gold[np.argmin(((gold.astype(float) - warm_target) ** 2).sum(1))])
    frames: list[np.ndarray] = []
    for t in range(N_FRAMES):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im, "RGBA")
        for i in range(4):
            phase = (t / N_FRAMES + i / 4.0) * 2.0 * np.pi
            cx = 384 + int(round(69 * np.cos(phase)))
            cy = 275 + int(round(57 * np.sin(phase)))
            pulse = (1.0 + np.sin(2.0 * np.pi * (t / 12.0 + i / 4.0))) / 2.0
            if pulse < 0.34:
                continue
            radius = 1 if pulse < 0.76 else 2
            alpha = int(72 + pulse * 116)
            d.polygon([(cx, cy - radius), (cx + radius, cy), (cx, cy + radius), (cx - radius, cy)], fill=(*warm, alpha))
            d.point((cx, cy), fill=(*bright, min(225, alpha + 18)))
        frames.append(np.asarray(im).copy())
    return frames


def composite(layers: dict[str, np.ndarray], glints: np.ndarray | None = None) -> np.ndarray:
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for name in ("sol", "murs", "ombres", "porte_medaille", "coffres", "statues_rails", "appliques", "autres"):
        out.alpha_composite(Image.fromarray(layers[name], "RGBA"))
    if glints is not None:
        out.alpha_composite(Image.fromarray(glints, "RGBA"))
    return np.asarray(out).copy()


def build_collision_grid(floor_mask: np.ndarray, decor_masks: dict[str, np.ndarray], components: list[dict[str, object]]) -> np.ndarray:
    """0 = marchable, 1 = obstacle/mur. L'axe sud→nord doit rester continu."""
    centers = floor_mask[4::8, 4::8]
    walk = centers[:GH, :GW].copy()
    yy, xx = np.indices((H, W))
    # Le médaillon est un motif de sol, tandis que les montants de la porte
    # restent solides ; on garde une ouverture de 7 cases vers le marqueur nord.
    medallion_walkable = (xx >= 304) & (xx < 465) & (yy >= 210) & (yy < 348)
    north_approach = (xx >= 356) & (xx < 412) & (yy >= 152) & (yy < 192)
    arch_obstacles = (decor_masks["porte_medaille"][..., 3] > 0) & ~(medallion_walkable | north_approach)
    obstacle_pixels = (
        (decor_masks["coffres"][..., 3] > 0)
        | (decor_masks["statues_rails"][..., 3] > 0)
        | (decor_masks["autres"][..., 3] > 0)
        | arch_obstacles
    )
    obstacle_cells = obstacle_pixels.reshape(GH, 8, GW, 8).any(axis=(1, 3))
    walk &= ~obstacle_cells
    grid = (~walk).astype(np.uint8)
    # Les marqueurs sont posés juste à l'intérieur des seuils dégagés.
    for marker in (ENTRY, BOSS, EXIT):
        x, y = marker[0] // 8, marker[1] // 8
        if grid[y, x] != 0:
            raise ValueError(f"Marqueur non praticable: {marker}")
    return grid


def write_ora(path: Path, layers: dict[str, np.ndarray], source_full: np.ndarray, glints: list[np.ndarray], merged: np.ndarray) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    ordered = [
        ("reflets_or_f00", glints[0], True),
        ("ornements_et_portes", layers["porte_medaille"], True),
        ("coffres", layers["coffres"], True),
        ("statues_et_rails", layers["statues_rails"], True),
        ("appliques", layers["appliques"], True),
        ("autres_decors", layers["autres"], True),
        ("ombres", layers["ombres"], True),
        ("murs_architecture", layers["murs"], True),
        ("sol", layers["sol"], True),
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
    base = loadmod("eac1_ground_export_base", ROOT / "source/entree_bassin_chauffant_sud_nord_v1/build.py")
    base.PREFIX, base.NAMESPACE, base.ASSET = PREFIX, NAMESPACE, ASSET
    base.STAGE, base.W, base.H = STAGE, W, H
    counts = base.build_pmdo_ground_project(stack, grid, ENTRY, EXIT, gfx, tools)
    ground_path = STAGE / f"Data/Ground/{ASSET}.rsground"
    ground = json.loads(ground_path.read_text(encoding="utf-8"))
    obj = ground["Object"]
    obj["Name"] = {"DefaultText": "Fin Château Ancien — Salle du Trésor (4:3)", "LocalTexts": {}}
    obj["Comment"] = (
        "PMDO 0.8.12. Proposition 4:3 (768x576) référencée sur oldcastlepmd.png ; "
        "textures recolorées à la palette du rip, illustration non certifiée native."
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
        text = text.replace("Entree Bassin Chauffant 4:3 - Atelier 0.8.12", "Fin Chateau Ancien 4:3 - Atelier 0.8.12")
        text = text.replace(
            "Projet d'edition : entree de donjon du Bassin Chauffant (P01P04A) au format 4:3 (768x576), eau thermale minerale doree, feuilles flottantes et vapeur.",
            "Projet d'edition : fin de donjon, Salle du Tresor du Chateau Ancien (rip oldcastlepmd.png), 4:3 (768x576), arene centrale et tresor nord.",
        )
        mod_path.write_text(text, encoding="utf-8")
    return counts


def write_viewer(html_path: Path, manifest: dict[str, object]) -> None:
    rel = "renders/fin_chateau_ancien_v1"
    src_layers = [
        ("sol", "01_sol.png", "Sol — dallage clair"),
        ("murs", "02_murs.png", "Murs et architecture"),
        ("ombres", "03_ombres.png", "Ombres des coffres et statues"),
        ("porte", "04_ornements.png", "Portes, médaille et appliques"),
        ("coffres", "05_coffres.png", "Coffres au trésor"),
        ("statues", "06_statues_rails.png", "Statues et rails"),
        ("appliques", "07_appliques.png", "Appliques murales"),
        ("autres", "07b_autres.png", "Autres ornements"),
    ]
    layers_js = json.dumps([{"id": k, "label": label, "src": f"{rel}/layers/{PREFIX}_{code}"} for k, code, label in src_layers], ensure_ascii=False)
    frames_js = json.dumps([f"{rel}/anim/{PREFIX}_08_reflets_or_f{i:02d}.png" for i in range(N_FRAMES)])
    fidelity_rows = "".join(
        f"<li>{name} : {info['rgb_distance']} (moyenne RGB vers la palette du rip)</li>"
        for name, info in manifest["fidelity"].items()
    )
    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aperçu FAC1 — Château Ancien</title>
<style>
:root{{color-scheme:dark}}body{{margin:0;padding:20px;background:#171610;color:#f3edcf;font:14px/1.45 system-ui,sans-serif}}h1{{font-size:20px;margin:0 0 5px;color:#f0cf70}}.meta{{color:#c0b78f;margin-bottom:14px}}.row{{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}}.stage{{position:relative;width:min(768px,95vw);aspect-ratio:4/3;background:#111;border:1px solid #665a31;image-rendering:pixelated;overflow:hidden}}.stage img{{position:absolute;inset:0;width:100%;height:100%;image-rendering:pixelated;object-fit:fill}}.panel{{max-width:380px;background:#242219;border:1px solid #4a432d;border-radius:8px;padding:12px}}button,a{{color:#f4d880}}button{{background:#3a3420;border:1px solid #81713d;border-radius:5px;padding:7px 11px;cursor:pointer}}label{{display:block;margin:5px 0}}.links{{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}}small{{color:#b8b08f}}ul{{padding-left:20px}}
</style></head><body>
<h1>Fin Château Ancien — Salle du Trésor (FAC1)</h1>
<div class="meta">768×576 px · 96×72 tuiles 8×8 · entrée sud → objectif nord · reflets d’or calculés (24×10 ticks) · source : <code>oldcastlepmd.png</code> (408×408)</div>
<div class="links"><button id="play">⏸ Pause</button><button id="walkToggle">Afficher la marche</button><span id="tick">tick 000 / 240</span></div>
<div class="row"><div class="stage" id="stage"><img id="walk" src="{rel}/{PREFIX}_walkability.png" style="display:none;opacity:.68"></div>
<div class="panel"><strong>Calques transparents</strong><div id="controls"></div><hr><strong>Fidélité de palette</strong><ul>{fidelity_rows}</ul><small>Distance RGB moyenne &lt; 35 sur les catégories listées. Art non approuvé comme tuiles natives ; runtime PMDO non testé.</small>
<div class="links"><a href="livrable_fin_chateau_ancien_v1.zip">ZIP PNG/ORA/manifest</a><a href="mod_fin_chateau_ancien_pmdo_0812.zip">ZIP PMDO 0.8.12</a></div>
</div></div>
<script>
const rel={json.dumps(rel)}, layers={layers_js}, frames={frames_js};
const stage=document.getElementById('stage'); let nodes={{}}, playing=true, idx=0, showWalk=false;
for(const l of layers){{const im=document.createElement('img');im.src=l.src;im.dataset.layer=l.id;stage.appendChild(im);nodes[l.id]=im;}}
const anim=document.createElement('img');anim.src=frames[0];anim.dataset.layer='reflets_or';stage.appendChild(anim);nodes.reflets_or=anim;
const controls=document.getElementById('controls');
for(const l of [...layers,{{id:'reflets_or',label:'Reflets d’or animés'}}]){{const lab=document.createElement('label');lab.innerHTML=`<input type="checkbox" checked> ${{l.label}}`;lab.firstChild.onchange=e=>nodes[l.id].style.display=e.target.checked?'block':'none';controls.appendChild(lab);}}
setInterval(()=>{{if(!playing)return;idx=(idx+1)%frames.length;anim.src=frames[idx];document.getElementById('tick').textContent=`tick ${{String(idx*10).padStart(3,'0')}} / 240`; }},166);
document.getElementById('play').onclick=e=>{{playing=!playing;e.target.textContent=playing?'⏸ Pause':'▶ Lecture';}};
document.getElementById('walkToggle').onclick=()=>{{showWalk=!showWalk;document.getElementById('walk').style.display=showWalk?'block':'none';}};
</script></body></html>"""
    html_path.write_text(html, encoding="utf-8")


def build() -> dict[str, object]:
    if not REF_PATH.is_file() or not FULL_PATH.is_file() or not BG_PATH.is_file() or not DECOR_PATH.is_file():
        raise FileNotFoundError("Rip canonique ou un des trois bruts générés manquant")
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
        "porte_medaille": decor_layers["porte_medaille"],
        "coffres": decor_layers["coffres"],
        "statues_rails": decor_layers["statues_rails"],
        "appliques": decor_layers["appliques"],
        "autres": decor_layers["autres"],
    }
    glints = make_gold_glints(palette)
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
        ("04_ornements", "porte_medaille"),
        ("05_coffres", "coffres"),
        ("06_statues_rails", "statues_rails"),
        ("07_appliques", "appliques"),
        ("07b_autres", "autres"),
    ]
    for code, key in static_order:
        Image.fromarray(static[key], "RGBA").save(layer_dir / f"{PREFIX}_{code}.png")
    for i, frame in enumerate(glints):
        Image.fromarray(frame, "RGBA").save(anim_dir / f"{PREFIX}_08_reflets_or_f{i:02d}.png")

    frames: list[np.ndarray] = []
    for t, sparkle in enumerate(glints):
        frame = composite(static, sparkle)
        frames.append(frame)
        Image.fromarray(frame, "RGBA").save(RENDERS / f"{PREFIX}_scene_t{t * FRAME_TICKS:03d}.png")
    pil_frames = [Image.fromarray(f, "RGBA") for f in frames]
    pil_frames[0].save(RENDERS / f"{PREFIX}_anim.webp", save_all=True, append_images=pil_frames[1:], duration=166, loop=0, lossless=True)
    pil_frames[0].save(RENDERS / f"{PREFIX}_anim.png", format="PNG", save_all=True, append_images=pil_frames[1:], duration=166, loop=0, disposal=2)

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
        "porte_medaille": static["porte_medaille"],
        "coffres": static["coffres"],
        "statues_rails": static["statues_rails"],
        "appliques": static["appliques"],
        "autres": static["autres"],
    }
    write_ora(RENDERS / f"{PREFIX}_fin_chateau_ancien.ora", ora_layers, full_rgba, glints, frames[0])

    gfx = loadmod("pmdo_codec_eac1", ROOT / "source/pmdo_cote/build.py")
    tools = loadmod("index_tools_eac1", ROOT / "source/pmdo_cote/INSTALLER.py")
    stack = [
        ("sol", [static["sol"]], 60, 0),
        ("murs", [static["murs"]], 60, 0),
        ("ombres", [static["ombres"]], 60, 0),
        ("ornements", [static["porte_medaille"]], 60, 0),
        ("coffres", [static["coffres"]], 60, 0),
        ("statues_rails", [static["statues_rails"]], 60, 0),
        ("appliques", [static["appliques"]], 60, 0),
        ("autres", [static["autres"]], 60, 0),
        ("reflets_or (anime 24x10t)", glints, FRAME_TICKS, 0),
    ]
    bank_counts = write_pmdo_project(stack, grid, gfx, tools)

    manifest: dict[str, object] = {
        "map_id": MAP_ID,
        "title": "Fin Château Ancien — Salle du Trésor",
        "prefix": PREFIX,
        "reference": REF_PATH.name,
        "reference_sha256": sha256_of(REF_PATH),
        "reference_dimensions_px": [408, 408],
        "reference_kind": "intérieur, salle dorée / ancien château",
        "dimensions_px": [W, H],
        "dimensions_tiles": [GW, GH],
        "tile_size_px": [TW, TH],
        "aspect_ratio": "4:3",
        "loop_ticks": LOOP_TICKS,
        "animation": {"reflets_or": {"frames": N_FRAMES, "ticks_per_frame": FRAME_TICKS, "native": False}},
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
        "layers": ["sol", "murs", "ombres", "porte_medaille", "coffres", "statues_rails", "appliques", "autres", "reflets_or"],
        "notes": [
            "Composition générée référencée, détourage des objets par fond magenta.",
            "Couleurs ramenées à la palette RGB du rip ; métriques calculées avant quantification.",
            "Textures et géométrie proposées, non certifiées natives ; runtime PMDO non testé.",
        ],
    }
    (RENDERS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path = ROOT / "apercu_fin_chateau_ancien_v1.html"
    write_viewer(html_path, manifest)

    mod_zip = ROOT / "mod_fin_chateau_ancien_pmdo_0812.zip"
    with zipfile.ZipFile(mod_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(STAGE.rglob("*")):
            if p.is_file():
                zf.write(p, Path(NAMESPACE) / p.relative_to(STAGE))
    liv_zip = ROOT / "livrable_fin_chateau_ancien_v1.zip"
    with zipfile.ZipFile(liv_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(RENDERS.rglob("*")):
            if p.is_file():
                zf.write(p, Path("renders/fin_chateau_ancien_v1") / p.relative_to(RENDERS))
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
