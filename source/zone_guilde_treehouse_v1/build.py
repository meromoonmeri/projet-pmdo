#!/usr/bin/env python3
"""Pipeline ZGT1 : village arboricole de guilde (prototype 4:3 pour PMDO 0.8.12).

La scène décorée et sa plaque de sol sont des rendus générés, pas des extractions de
la ROM. La palette et les petites tuiles d'eau animées proviennent de la référence
canonique T00P01 ; le layout et les pixels de la nouvelle scène restent originaux.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import uuid
import zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = HERE / "bruts"
REFERENCE = HERE / "reference"
RENDERS = ROOT / "renders/zone_guilde_treehouse_v1"
CACHE = ROOT / ".cache/zone_guilde_treehouse_v1"
STAGE = CACHE / "pmdo_stage"

W, H = 768, 576
TILE = 8
GW, GH = W // TILE, H // TILE
PREFIX = "ZGT1"
NAMESPACE = "zone_guilde_treehouse"
ASSET = "zgt1_village_arboricole_guilde"
WATER_FRAME_LENGTH = 2
WATER_FRAMES = 36
WATER_LOOP_TICKS = WATER_FRAME_LENGTH * WATER_FRAMES

REF_PATH = REFERENCE / "T00P01_canonique.png"
ATLAS_PATH = REFERENCE / "T00P01_eau_atlas.npz"
RAW_DECOR = SOURCE / "decor_magenta.png"
RAW_GROUND = SOURCE / "sol_complet.png"

# Repères de travail en pixels (centre du collider); la carte et ces positions
# restent expérimentales jusqu'à validation du layout.
MARKERS = {
    "entree_sud": [384, 548],
    "place_centrale": [408, 328],
    "maison_guilde": [384, 184],
    "pont_est": [688, 286],
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
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def image_array(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB").resize((W, H), Image.Resampling.LANCZOS)).copy()


def nearest_palette(rgb: np.ndarray, palette: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    tree = cKDTree(palette.astype(np.float32))
    distances, ids = tree.query(rgb.reshape(-1, 3).astype(np.float32), workers=-1)
    remapped = palette[ids].reshape(rgb.shape).astype(np.uint8)
    return remapped, distances.reshape(rgb.shape[:2]).astype(np.float32)


def magenta_water_mask(rgb: np.ndarray) -> tuple[np.ndarray, dict[str, object]]:
    r, g, b = rgb.astype(np.int16).transpose(2, 0, 1)
    candidate = (r >= 145) & (b >= 145) & (g <= 125) & (np.abs(r - b) <= 105)
    labels, count = ndi.label(candidate)
    sizes = np.bincount(labels.ravel())
    selected = [int(i) for i in range(1, count + 1) if sizes[i] >= 700]
    if len(selected) < 2:
        raise ValueError(f"Canal magenta non détecté comme prévu : {len(selected)} composantes")
    mask = np.isin(labels, selected)
    components = []
    for label_id in selected:
        yy, xx = np.where(labels == label_id)
        components.append({
            "pixels": int(len(xx)),
            "bbox_xyxy": [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1],
        })
    return mask, {"components": components, "pixels": int(mask.sum())}


def draw_polygons(polygons: list[list[tuple[int, int]]]) -> np.ndarray:
    im = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(im)
    for polygon in polygons:
        draw.polygon(polygon, fill=255)
    return np.asarray(im) > 0


def surface_masks(rgb: np.ndarray, water: np.ndarray) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Partitionne les pixels générés en couches éditables, sans prétendre à un rip d'objets."""
    a = rgb.astype(np.int16)
    r, g, b = a.transpose(2, 0, 1)
    median = ndi.median_filter(a, size=(3, 3, 1))
    detail_score = np.max(np.abs(a - median), axis=2)
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b)

    # Canopée et végétation texturée : classe visuelle, pas détourage certifié de sprites.
    green = (g >= r + 4) & (g >= b - 2) & (lum > 42)
    canopy = green & (detail_score >= 12) & ~water

    # Zones de bâtiments/pont générées, annotées à la main sur le rendu réduit.
    structure_zones = draw_polygons([
        # Grand arbre-maison de guilde (toit, branches et tronc).
        [(245, 47), (267, 34), (291, 49), (313, 40), (338, 51), (358, 39),
         (387, 50), (415, 61), (441, 85), (445, 112), (430, 130), (416, 153),
         (390, 169), (362, 178), (328, 174), (300, 166), (276, 153), (257, 136),
         (245, 116), (248, 92)],
        # Maisons arboricoles ouest et est.
        [(91, 119), (101, 106), (119, 111), (138, 116), (158, 121), (176, 136),
         (184, 154), (181, 178), (168, 196), (148, 205), (126, 202), (108, 189),
         (98, 170), (93, 148)],
        [(552, 119), (563, 106), (581, 110), (600, 112), (620, 121), (636, 139),
         (641, 163), (634, 186), (619, 202), (595, 203), (576, 193), (562, 176),
         (555, 151)],
        # Pont en bois à l'est.
        [(649, 267), (725, 267), (728, 307), (649, 307)],
        # Groupes de caisses et clôtures sud-ouest / sud-est.
        [(120, 405), (211, 405), (211, 505), (120, 505)],
        [(548, 397), (640, 397), (640, 498), (548, 498)],
    ])
    warm_wood = (r > g + 17) & (g > b + 8) & (lum < 225)
    dark_outline = np.maximum.reduce((r, g, b)) < 118
    cream_detail = (r > 155) & (g > 133) & (r > g + 4) & (g > b + 14) & (detail_score >= 7)
    structure = structure_zones & (warm_wood | dark_outline | cream_detail | (detail_score >= 24))
    structure &= ~water
    canopy &= ~structure

    # Détails fins restants : pierres, fleurs, lampes, poteaux et textures de surface.
    detail = (detail_score >= 14) & ~water & ~structure & ~canopy
    masks = {
        "canopy": canopy,
        "structures": structure,
        "details": detail,
        "base": ~(water | canopy | structure | detail),
    }
    return masks, detail_score


def tile_water_frames(water_mask: np.ndarray) -> tuple[list[np.ndarray], dict[str, object]]:
    with np.load(ATLAS_PATH, allow_pickle=False) as data:
        atlas = data["tiles"].astype(np.uint8)
        sample_coords = data["source_coords"].astype(int).tolist()
        ticks = data["ticks"].astype(int).tolist()
    if atlas.shape[0] != WATER_FRAMES or atlas.shape[2:4] != (TILE, TILE) or atlas.shape[-1] != 3:
        raise ValueError(f"Atlas inattendu : {atlas.shape}")
    if atlas.shape[0] != len(ticks) or ticks != list(range(0, WATER_LOOP_TICKS, WATER_FRAME_LENGTH)):
        raise ValueError(f"Cadence de l'atlas incohérente : {ticks}")

    out: list[np.ndarray] = []
    sample_count = atlas.shape[1]
    for phase in range(WATER_FRAMES):
        frame = np.zeros((H, W, 4), dtype=np.uint8)
        frame[..., 3][water_mask] = 255
        for gy in range(GH):
            y0 = gy * TILE
            for gx in range(GW):
                x0 = gx * TILE
                alpha_tile = water_mask[y0 : y0 + TILE, x0 : x0 + TILE]
                if not alpha_tile.any():
                    continue
                # Choix spatial déterministe parmi les vrais motifs du canal source.
                sample_id = (gx * 17 + gy * 31 + gx * gy * 3) % sample_count
                tile = atlas[phase, sample_id]
                frame[y0 : y0 + TILE, x0 : x0 + TILE, :3] = tile
        out.append(frame)
    return out, {"source_sample_coordinates_px": sample_coords, "sample_count": int(sample_count), "ticks": ticks}


def rgba_layer(rgb: np.ndarray, alpha_mask: np.ndarray) -> np.ndarray:
    out = np.zeros((H, W, 4), dtype=np.uint8)
    out[..., :3] = rgb
    out[..., 3] = alpha_mask.astype(np.uint8) * 255
    return out


def composite_layers(base: np.ndarray, water: np.ndarray, details: np.ndarray,
                     structures: np.ndarray, canopy: np.ndarray) -> np.ndarray:
    # Les partitions de terrain sont disjointes ; le canal est une vraie couche alpha.
    canvas = np.zeros((H, W, 4), dtype=np.uint8)
    for layer in (base, water, details, structures, canopy):
        canvas = np.asarray(Image.alpha_composite(Image.fromarray(canvas), Image.fromarray(layer)))
    return canvas


def cell_fraction(mask: np.ndarray) -> np.ndarray:
    return mask.reshape(GH, TILE, GW, TILE).mean(axis=(1, 3))


def build_corridor_mask() -> np.ndarray:
    im = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(im)
    # Grandes allées générées : entrée sud -> place -> maison de guilde,
    # traversée est-ouest -> pont, plus les deux embranchements des maisons.
    draw.line([(384, 575), (384, 470), (394, 398), (408, 344)], fill=255, width=34)
    draw.ellipse((330, 266, 486, 410), fill=255)
    draw.line([(408, 338), (405, 280), (392, 238), (384, 210)], fill=255, width=30)
    draw.line([(0, 286), (178, 286), (330, 286), (498, 286), (649, 286), (727, 286)], fill=255, width=28)
    draw.line([(336, 286), (254, 245), (195, 214), (157, 205)], fill=255, width=25)
    draw.line([(488, 286), (548, 248), (593, 221), (618, 211)], fill=255, width=25)
    # Petites cours devant les portes, sans rendre l'intérieur des bâtiments praticable.
    draw.ellipse((128, 176, 158, 208), fill=255)
    draw.ellipse((602, 190, 636, 222), fill=255)
    return np.asarray(im) > 0


def build_collision_grid(water: np.ndarray, masks: dict[str, np.ndarray]) -> tuple[np.ndarray, dict[str, object]]:
    water_cells = cell_fraction(water) >= 0.08
    canopy_cells = cell_fraction(masks["canopy"]) >= 0.22
    structure_cells = cell_fraction(masks["structures"]) >= 0.18
    blocked = water_cells | canopy_cells | structure_cells

    # Les bords d'image sont hors map. Le chemin sud reste accessible jusqu'au repère.
    blocked[0, :] = True
    blocked[-1, :] = True
    blocked[:, 0] = True
    blocked[:, -1] = True

    corridor = build_corridor_mask()
    corridor_cells = cell_fraction(corridor) >= 0.08
    blocked[corridor_cells & ~water_cells] = False

    # Le petit tablier du pont est au-dessus de la rivière et ne doit pas être bloqué.
    bx0, by0, bx1, by1 = 650 // TILE, 268 // TILE, 725 // TILE, 305 // TILE
    blocked[by0:by1 + 1, bx0:bx1 + 1] = False

    # Les marqueurs sont des repères d'édition; leurs cases doivent rester accessibles.
    for x, y in MARKERS.values():
        cx, cy = x // TILE, y // TILE
        blocked[max(1, cy - 1):min(GH - 1, cy + 2), max(1, cx - 1):min(GW - 1, cx + 2)] = False
    return blocked.astype(np.uint8), {
        "water_cells": int(water_cells.sum()),
        "canopy_cells": int(canopy_cells.sum()),
        "structure_cells": int(structure_cells.sum()),
        "walkable_cells": int((blocked == 0).sum()),
        "collision_note": "Blocage approximatif sur eau/canopée/bâtis; allées et pont clarifiés manuellement.",
    }


def marker_record(name: str, point: list[int]) -> dict[str, object]:
    return {
        "EntName": name,
        "Direction": 4,
        "EntEnabled": True,
        "triggerType": 0,
        "Collider": {"X": point[0] - 8, "Y": point[1] - 8, "Width": 16, "Height": 16},
    }


def write_ora(path: Path, layers: list[tuple[str, np.ndarray, bool]], merged: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "image/openraster", compress_type=zipfile.ZIP_STORED)
        xml = [f'<?xml version="1.0" encoding="UTF-8"?>', f'<image version="0.0.1" w="{W}" h="{H}">', "  <stack>"]
        for index, (name, pixels, visible) in enumerate(layers):
            filename = f"data/layer_{index:02d}.png"
            visibility = "visible" if visible else "hidden"
            xml.append(f'    <layer name="{name}" src="{filename}" x="0" y="0" opacity="1.0" visibility="{visibility}"/>')
            from io import BytesIO
            stream = BytesIO()
            Image.fromarray(pixels, "RGBA").save(stream, format="PNG", optimize=True)
            archive.writestr(filename, stream.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
        xml.extend(["  </stack>", "</image>"])
        archive.writestr("stack.xml", "\n".join(xml), compress_type=zipfile.ZIP_DEFLATED)
        from io import BytesIO
        stream = BytesIO()
        Image.fromarray(merged, "RGBA").save(stream, format="PNG", optimize=True)
        archive.writestr("mergedimage.png", stream.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
        thumb = Image.fromarray(merged, "RGBA").resize((256, 192), Image.Resampling.NEAREST)
        stream = BytesIO()
        thumb.save(stream, format="PNG", optimize=True)
        archive.writestr("Thumbnails/thumbnail.png", stream.getvalue(), compress_type=zipfile.ZIP_DEFLATED)


def write_viewer(path: Path, manifest: dict[str, object]) -> None:
    rel = "renders/zone_guilde_treehouse_v1"
    layer_specs = [
        ("base", "00 · Sol résiduel généré", f"{rel}/layers/ZGT1_00_sol_residuel.png"),
        ("water", "01 · Eau · échantillon T00P01 animé", f"{rel}/anim/ZGT1_01_eau_T00P01_f00.png"),
        ("details", "02 · Détails & végétation basse", f"{rel}/layers/ZGT1_02_details.png"),
        ("structures", "03 · Habitations & pont", f"{rel}/layers/ZGT1_03_habitations_pont.png"),
        ("canopy", "04 · Canopée / premier plan", f"{rel}/layers/ZGT1_04_canopee.png"),
    ]
    layer_json = json.dumps([{"id": i, "label": l, "src": s} for i, l, s in layer_specs], ensure_ascii=False)
    water_frames = json.dumps([f"{rel}/anim/ZGT1_01_eau_T00P01_f{i:02d}.png" for i in range(WATER_FRAMES)])
    html = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ZGT1 — Village arboricole de guilde</title>
<style>
:root {{ color-scheme:dark; --bg:#101614; --panel:#18211d; --line:#31453a; --mint:#99e1ad; --gold:#e7c982; }}
* {{ box-sizing:border-box }} body {{ margin:0; background:var(--bg); color:#eef4ed; font:14px/1.5 system-ui,sans-serif; padding:22px; }}
h1 {{ margin:0; color:var(--mint); font-size:22px; }} .sub {{ color:#b3c2b6; margin:4px 0 16px; }}
.toolbar {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:12px; }}
button, .pill {{ border:1px solid var(--line); border-radius:8px; color:inherit; background:var(--panel); padding:7px 11px; }}
button {{ cursor:pointer }} a {{ color:#b4d8ff }}
main {{ display:grid; grid-template-columns:minmax(320px,768px) minmax(260px,360px); gap:16px; align-items:start; }}
.stage {{ position:relative; width:min(100%,768px); aspect-ratio:4/3; background:#0c1110; border:1px solid #587361; image-rendering:pixelated; overflow:hidden; }}
.stage img {{ position:absolute; inset:0; width:100%; height:100%; object-fit:fill; image-rendering:pixelated; }}
.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; }}
.layer-list {{ display:grid; gap:6px; margin:8px 0 14px; }} .layer-list label {{ display:flex; align-items:center; gap:8px; }}
.small {{ color:#bdcbbf; font-size:12px; }} .warning {{ border-left:3px solid var(--gold); padding:8px 10px; background:#27251c; margin:12px 0; }}
@media(max-width:900px) {{ main {{ grid-template-columns:1fr; }} .stage {{ width:100%; }} }}
</style></head>
<body>
<h1>ZGT1 — Village arboricole de guilde</h1>
<div class="sub">Prototype 4:3 · 768×576 px · 96×72 tuiles de 8 px · PMDO 0.8.12 · référence visuelle T00P01</div>
<div class="toolbar">
  <button id="play">⏸ Pause</button><span class="pill" id="tick">Tick 000 / 072</span>
  <label class="pill"><input type="checkbox" id="collision"> Collisions</label>
  <a class="pill" href="{rel}/ZGT1_PMDO_0812.zip">ZIP PMDO</a>
  <a class="pill" href="{rel}/ZGT1_layers.ora">ORA éditable</a>
</div>
<main>
  <div class="stage" id="stage"></div>
  <section class="panel">
    <strong>Calques</strong><div class="layer-list" id="layers"></div>
    <div class="warning"><strong>Composition V1 validée par l’utilisateur.</strong> Cette version reste inchangée; une V2 est demandée pour relier la maison droite, retirer les panneaux et fournir les sprites séparés.</div>
    <p class="small"><strong>Provenance :</strong> les pixels de la scène et du sol sont générés, pas extraits du jeu. La palette est quantifiée sur T00P01; l'eau utilise des tuiles 8×8 directement échantillonnées dans le canal canonique T00P01. La géométrie du village, les bâtiments, le pont, les collisions et les marqueurs sont de nouvelles propositions.</p>
    <p class="small">Boucle d'eau : {WATER_FRAMES} phases, FrameLength={WATER_FRAME_LENGTH}, période {WATER_LOOP_TICKS} ticks. Celle-ci combine les crans BPL et BPA de T00P01 avec leur cadence exacte; elle ne réutilise pas le layout natif.</p>
    <p class="small">Distance moyenne des couleurs générées à la palette T00P01 la plus proche : {manifest['palette_fit']['rgb_mean']:.2f} RGB; p95 {manifest['palette_fit']['rgb_p95']:.2f}. Part des couleurs visibles appartenant à la palette de référence : {manifest['palette_fit']['exact_palette_ratio']:.1%}.</p>
    <p class="small"><a href="source/zone_guilde_treehouse_v1/README_PACK.md">Méthode et limites</a> · <a href="{rel}/manifest.json">Manifeste</a></p>
    <div id="layerLinks" class="small"></div>
  </section>
</main>
<script>
const specs = {layer_json};
const frames = {water_frames};
const stage = document.getElementById('stage');
const layerList = document.getElementById('layers');
const imgById = {{}};
for (const s of specs) {{
  const img = document.createElement('img'); img.src = s.src; img.alt = s.label; img.dataset.layer = s.id;
  stage.appendChild(img); imgById[s.id] = img;
  const label = document.createElement('label');
  const box = document.createElement('input'); box.type='checkbox'; box.checked=true;
  box.onchange = () => {{ img.style.display = box.checked ? 'block' : 'none'; }};
  label.append(box, document.createTextNode(s.label)); layerList.appendChild(label);
}}
const collision = document.createElement('img'); collision.src='{rel}/ZGT1_collision_walkability.png'; collision.style.display='none'; collision.style.opacity='.65'; collision.alt='Walkability'; stage.appendChild(collision);
document.getElementById('collision').onchange = e => collision.style.display=e.target.checked?'block':'none';
document.getElementById('layerLinks').innerHTML = specs.map(s=>`<a href="${{s.src}}">PNG ${{s.label}}</a>`).join(' · ');
let phase=0, playing=true;
const tick=document.getElementById('tick');
function setPhase() {{ imgById.water.src=frames[phase]; tick.textContent=`Tick ${{String(phase*{WATER_FRAME_LENGTH}).padStart(3,'0')}} / {WATER_LOOP_TICKS}`; }}
setInterval(()=>{{ if(!playing)return; phase=(phase+1)%frames.length; setPhase(); }}, 1000*{WATER_FRAME_LENGTH}/60);
document.getElementById('play').onclick=e=>{{ playing=!playing; e.target.textContent=playing?'⏸ Pause':'▶ Lecture'; }};
setPhase();
</script>
</body></html>"""
    path.write_text(html, encoding="utf-8")


def finalize_pmdo(stack: list[tuple[str, list[np.ndarray], int, int]], blocked: np.ndarray) -> dict[str, int]:
    ground_builder = load_module(
        "zgt1_ground_project_builder", ROOT / "source/entree_bassin_chauffant_sud_nord_v1/build.py"
    )
    gfx = load_module("zgt1_pmdo_codec", ROOT / "source/pmdo_cote/build.py")
    tools = load_module("zgt1_pmdo_installer", ROOT / "source/pmdo_cote/INSTALLER.py")
    ground_builder.ROOT = ROOT
    ground_builder.STAGE = STAGE
    ground_builder.PREFIX = PREFIX
    ground_builder.NAMESPACE = NAMESPACE
    ground_builder.ASSET = ASSET
    ground_builder.W = W
    ground_builder.H = H
    bank_counts = ground_builder.build_pmdo_ground_project(
        stack, blocked, MARKERS["entree_sud"], MARKERS["maison_guilde"], gfx, tools
    )

    ground_path = STAGE / f"Data/Ground/{ASSET}.rsground"
    doc = json.loads(ground_path.read_text(encoding="utf-8"))
    obj = doc["Object"]
    obj["Name"] = {"DefaultText": "Village arboricole de guilde — ZGT1", "LocalTexts": {}}
    obj["AssetName"] = ASSET
    obj["Released"] = False
    obj["Comment"] = (
        "Composition ZGT1 approuvée par l'utilisateur; décor généré, non présenté comme extraction native. "
        "Palette référencée sur T00P01; tuiles d'eau 8x8 échantillonnées dans le canal T00P01 et animées "
        "à sa cadence BPL/BPA. Collisions approximatives; maison droite et panneaux à corriger en V2; "
        "marqueurs d'édition sans warp ni script de gameplay; runtime PMDO non testé."
    )
    obj["EdgeView"] = 1
    obj["Entities"] = [{
        "Name": "Repères de travail — aucun personnage ni warp",
        "Visible": True,
        "MapChars": [],
        "GroundObjects": [],
        "Spawners": [],
        "Markers": [marker_record(name, point) for name, point in MARKERS.items()],
    }]
    obj["obstacles"] = [
        [{"Bounds": {"X": x * TILE, "Y": y * TILE, "Width": TILE, "Height": TILE}, "Tags": int(blocked[y, x])}
         for y in range(GH)]
        for x in range(GW)
    ]
    doc["Version"] = "0.8.12.0"
    ground_path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    mod_path = STAGE / "Mod.xml"
    mod_uuid = uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/meromoonmeri/projet-pmdo/" + NAMESPACE)
    mod_path.write_text(
        f"""<?xml version=\"1.0\" encoding=\"utf-8\"?>
<Header>
  <Name>Village arboricole de guilde — ZGT1 (prototype 0.8.12)</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'édition PMDO 768x576 inspiré visuellement de T00P01. Composition ZGT1 approuvée; pixels générés; runtime non testé.</Description>
  <Namespace>{NAMESPACE}</Namespace>
  <UUID>{mod_uuid}</UUID>
  <Version>1.0.0.0</Version>
  <GameVersion>0.8.12.0</GameVersion>
  <ModType>Quest</ModType>
  <Relationships />
</Header>
""",
        encoding="utf-8",
    )
    script = (ROOT / "source/pmdo_cote/INSTALLER.py").read_text(encoding="utf-8")
    needle = "            relative = src.relative_to(source)\n"
    if needle in script and "relative.as_posix() == 'Content/Tile/index.idx'" not in script:
        script = script.replace(
            needle,
            needle + "            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n",
        )
    (STAGE / "INSTALLER.py").write_text(script, encoding="utf-8")
    project = RENDERS / "PMDO_project"
    shutil.copytree(STAGE, project, dirs_exist_ok=True)
    mod_zip = RENDERS / "ZGT1_PMDO_0812.zip"
    with zipfile.ZipFile(mod_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(project.rglob("*")):
            if path.is_file():
                archive.write(path, Path(NAMESPACE) / path.relative_to(project))
    return {key: int(value) for key, value in bank_counts.items()}


def write_manifest_and_readme(manifest: dict[str, object]) -> None:
    (RENDERS / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (RENDERS / "README_PACK.md").write_text(
        "# ZGT1 — Village arboricole de guilde\n\n"
        "Carte PMDO 0.8.12, 768×576 px (96×72 cases de 8×8). Composition V1 approuvée par l'utilisateur le 4 octobre 2026; les corrections demandées sont conservées pour V2.\n\n"
        "- Aperçu : `../../apercu_zone_guilde_treehouse_v1.html`\n"
        "- Projet Ground/Tile directement inspectable : `PMDO_project/`\n"
        "- Mod PMDO : `ZGT1_PMDO_0812.zip`\n"
        "- Calques PNG et animation d'eau : `layers/` et `anim/`\n"
        "- Projet éditable : `ZGT1_layers.ora`\n\n"
        "Les pixels de `bruts/decor_magenta.png` et `bruts/sol_complet.png` sont des rendus générés. "
        "Ils ne sont pas présentés comme des extractions de tuiles de la ROM. La scène non aquatique est "
        "quantifiée sur les 134 couleurs de la référence T00P01. Le canal magenta sert de masque; les 11 "
        "motifs de tuiles d'eau 8×8 sont des échantillons directs du canal canonique T00P01, réassemblés "
        "dans une forme nouvelle. Les 36 phases à FrameLength=2 reproduisent la boucle BPL/BPA de 72 ticks.\n\n"
        "Les calques séparent le résiduel de sol généré, les détails, les zones bâties, la canopée et l'eau. "
        "Les surfaces de sol générées ne sont pas des sprites natifs découpés. Collisions et repères sont "
        "des propositions d'édition; il n'y a ni warp, ni personnage, ni test d'exécution PMDO.\n\n"
        "Reconstruction : `.venv/bin/python source/zone_guilde_treehouse_v1/build.py`; tests : "
        "`.venv/bin/python -m unittest source.zone_guilde_treehouse_v1.test_build -v`.\n",
        encoding="utf-8",
    )


def write_delivery_zip() -> Path:
    delivery = ROOT / "livrable_zone_guilde_treehouse_v1.zip"
    source_files = [
        HERE / "README_PACK.md",
        HERE / "build.py",
        HERE / "extract_water_atlas.py",
        HERE / "test_build.py",
        *sorted((HERE / "bruts").glob("*.png")),
        *sorted((HERE / "reference").iterdir()),
    ]
    with zipfile.ZipFile(delivery, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(RENDERS.rglob("*")):
            if path.is_file():
                archive.write(path, Path("renders/zone_guilde_treehouse_v1") / path.relative_to(RENDERS))
        archive.write(ROOT / "apercu_zone_guilde_treehouse_v1.html", "apercu_zone_guilde_treehouse_v1.html")
        for path in source_files:
            if path.is_file():
                archive.write(path, Path("source/zone_guilde_treehouse_v1") / path.relative_to(HERE))
    return delivery


def main() -> None:
    for required in (REF_PATH, ATLAS_PATH, RAW_DECOR, RAW_GROUND):
        if not required.is_file():
            raise FileNotFoundError(required)
    if RENDERS.exists():
        shutil.rmtree(RENDERS)
    RENDERS.mkdir(parents=True, exist_ok=True)
    (RENDERS / "layers").mkdir(parents=True, exist_ok=True)
    (RENDERS / "anim").mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    reference = np.asarray(Image.open(REF_PATH).convert("RGB"))
    palette = np.unique(reference.reshape(-1, 3), axis=0).astype(np.uint8)
    raw_decor = image_array(RAW_DECOR)
    raw_ground = image_array(RAW_GROUND)
    water, water_meta = magenta_water_mask(raw_decor)
    scene_rgb, distances = nearest_palette(raw_decor, palette)
    guide_rgb, _ = nearest_palette(raw_ground, palette)
    masks, detail_score = surface_masks(scene_rgb, water)
    water_frames, atlas_meta = tile_water_frames(water)

    layers = {
        "base": rgba_layer(scene_rgb, masks["base"]),
        "details": rgba_layer(scene_rgb, masks["details"]),
        "structures": rgba_layer(scene_rgb, masks["structures"]),
        "canopy": rgba_layer(scene_rgb, masks["canopy"]),
    }
    # Un terrain-support généré reste livré dans les sources, mais n'est pas la base
    # visible de la scène décorée (les deux bruts ne sont pas pixel-alignés partout).
    guide = rgba_layer(guide_rgb, ~water)
    scene0 = composite_layers(layers["base"], water_frames[0], layers["details"], layers["structures"], layers["canopy"])
    if not np.array_equal(scene0[..., 3], np.full((H, W), 255, dtype=np.uint8)):
        raise AssertionError("La recomposition contient des pixels transparents")

    # Exports PNG RGBA des couches statiques et des phases d'eau.
    names = {
        "base": "ZGT1_00_sol_residuel.png",
        "details": "ZGT1_02_details.png",
        "structures": "ZGT1_03_habitations_pont.png",
        "canopy": "ZGT1_04_canopee.png",
    }
    for key, filename in names.items():
        Image.fromarray(layers[key], "RGBA").save(RENDERS / "layers" / filename, optimize=True)
    Image.fromarray(guide, "RGBA").save(RENDERS / "layers" / "ZGT1_guide_sol_complet_non_utilise.png", optimize=True)
    water_paths = []
    for index, frame in enumerate(water_frames):
        filename = f"ZGT1_01_eau_T00P01_f{index:02d}.png"
        Image.fromarray(frame, "RGBA").save(RENDERS / "anim" / filename, optimize=True)
        water_paths.append(RENDERS / "anim" / filename)
    Image.fromarray(scene0, "RGBA").save(RENDERS / "ZGT1_scene_t000.png", optimize=True)

    durations_ms = [
        round((i + 1) * WATER_FRAME_LENGTH * 1000 / 60) - round(i * WATER_FRAME_LENGTH * 1000 / 60)
        for i in range(WATER_FRAMES)
    ]
    first = Image.open(water_paths[0]).convert("RGBA")
    appends = [Image.open(path).convert("RGBA") for path in water_paths[1:]]
    first.save(
        RENDERS / "anim/ZGT1_eau_T00P01_72ticks.webp",
        format="WEBP", save_all=True, append_images=appends,
        duration=durations_ms, loop=0, lossless=True, method=4,
    )
    for image in appends:
        image.close()
    first.close()

    # ORA : ordre top -> bottom; la plaque de sol alternative est masquée.
    ora_layers = [
        ("04 Canopée / premier plan", layers["canopy"], True),
        ("03 Habitations et pont — zones générées", layers["structures"], True),
        ("02 Détails et végétation basse", layers["details"], True),
        ("01 Eau — échantillons T00P01 (phase 0)", water_frames[0], True),
        ("00 Sol résiduel de la scène générée", layers["base"], True),
        ("Support : sol complet généré, non aligné partout", guide, False),
    ]
    write_ora(RENDERS / "ZGT1_layers.ora", ora_layers, scene0)

    blocked, collision_meta = build_collision_grid(water, masks)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    for gy in range(GH):
        for gx in range(GW):
            color = (42, 224, 105, 108) if blocked[gy, gx] == 0 else (244, 71, 65, 128)
            draw.rectangle((gx * TILE, gy * TILE, gx * TILE + 7, gy * TILE + 7), fill=color)
    for name, (x, y) in MARKERS.items():
        color = (70, 255, 145, 255) if name == "entree_sud" else (255, 211, 85, 255)
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color)
    overlay.save(RENDERS / "ZGT1_collision_walkability.png", optimize=True)
    Image.alpha_composite(Image.fromarray(scene0), overlay).save(
        RENDERS / "ZGT1_collision_walkability_apercu.png", optimize=True
    )

    stack = [
        ("SOL_RESIDUEL genere", [layers["base"]], 60, 0),
        ("EAU_T00P01 36x2ticks", water_frames, WATER_FRAME_LENGTH, 0),
        ("DETAILS vegetation_basse", [layers["details"]], 60, 0),
        ("HABITATIONS_PONT zones_generees", [layers["structures"]], 60, 0),
        ("CANOPEE Top", [layers["canopy"]], 60, 4),
    ]
    bank_counts = finalize_pmdo(stack, blocked)

    palette_set = {tuple(int(v) for v in color) for color in palette}
    visible_rgb = np.concatenate((scene_rgb[~water], water_frames[0][..., :3][water]))
    unique_visible, visible_counts = np.unique(visible_rgb, axis=0, return_counts=True)
    exact_count = sum(
        int(count) for color, count in zip(unique_visible, visible_counts)
        if tuple(int(v) for v in color) in palette_set
    )
    exact_ratio = exact_count / len(visible_rgb)
    fit = {
        "reference_palette_colors": int(len(palette)),
        "rgb_mean": round(float(distances[~water].mean()), 2),
        "rgb_median": round(float(np.median(distances[~water])), 2),
        "rgb_p95": round(float(np.percentile(distances[~water], 95)), 2),
        "rgb_max": round(float(distances[~water].max()), 2),
        "exact_palette_ratio": round(float(exact_ratio), 6),
        "metric_note": "Distance RGB du rendu généré réduit à la couleur T00P01 la plus proche, avant quantification; ce n'est pas une comparaison de layout.",
    }
    manifest: dict[str, object] = {
        "map_id": "zone_guilde_treehouse_v1",
        "prefix": PREFIX,
        "asset_name": ASSET,
        "namespace": NAMESPACE,
        "dimensions_px": [W, H],
        "dimensions_tiles": [GW, GH],
        "tile_size_px": [TILE, TILE],
        "aspect_ratio": "4:3",
        "reference": {
            "code": "T00P01",
            "path": "source/zone_guilde_treehouse_v1/reference/T00P01_canonique.png",
            "sha256": sha256(REF_PATH),
            "render_size_px": list(Image.open(REF_PATH).size),
            "role": "reference visuelle/palette et source d'échantillons d'eau; le layout n'est pas repris",
        },
        "generated_sources": {
            "decor_magenta": {"path": str(RAW_DECOR.relative_to(ROOT)), "sha256": sha256(RAW_DECOR), "pixels_native_rip": False},
            "sol_complet": {"path": str(RAW_GROUND.relative_to(ROOT)), "sha256": sha256(RAW_GROUND), "pixels_native_rip": False},
        },
        "art_approved": True,
        "art_approval_scope": "Composition V1 validée par l'utilisateur le 2026-10-04; le défaut de liaison de la maison droite et le retrait des panneaux sont des corrections V2, sans écrasement de V1.",
        "runtime_tested": False,
        "water": {
            "method": "Masque magenta issu du rendu généré; motifs 8x8 directs du canal T00P01, réassemblés dans une géométrie générée.",
            "atlas_path": "source/zone_guilde_treehouse_v1/reference/T00P01_eau_atlas.npz",
            "atlas_sha256": sha256(ATLAS_PATH),
            "frame_count": WATER_FRAMES,
            "frame_length": WATER_FRAME_LENGTH,
            "loop_ticks": WATER_LOOP_TICKS,
            "source_sample_coordinates_px": atlas_meta["source_sample_coordinates_px"],
            "mask": water_meta,
        },
        "palette_fit": fit,
        "layers": ["sol_residuel", "eau_T00P01", "details", "habitations_pont", "canopee_top"],
        "layer_partition_pixels": {key: int(mask.sum()) for key, mask in masks.items()},
        "markers_px": MARKERS,
        "collision": collision_meta,
        "pmdo_tile_banks": bank_counts,
        "total_unique_tiles": int(sum(bank_counts.values())),
        "limitations": [
            "Les bruts de scène et de sol sont générés et ne sont pas des extractions natives.",
            "Le contenu des couches de décor est une segmentation de travail, pas un détourage certifié de sprites.",
            "Les collisions et repères sont approximatifs; aucun warp, spawn ou gameplay n'est configuré.",
            "Aucun lancement dans PMDO n'a encore été effectué; validation artistique en attente.",
        ],
    }
    write_manifest_and_readme(manifest)
    write_viewer(ROOT / "apercu_zone_guilde_treehouse_v1.html", manifest)
    delivery_zip = write_delivery_zip()

    print(
        f"[{PREFIX}] OK: {W}x{H} ({GW}x{GH}), eau={int(water.sum())} px, "
        f"palette={len(palette)} couleurs, walkable={collision_meta['walkable_cells']}, "
        f"tiles={manifest['total_unique_tiles']}, banques={len(bank_counts)}"
    )
    print(f"Projet PMDO : {RENDERS / 'ZGT1_PMDO_0812.zip'}")
    print(f"Livrable complet : {delivery_zip}")


if __name__ == "__main__":
    main()
