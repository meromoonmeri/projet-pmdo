"""PVC1 — Passage des Veines Cristallines, rendu généré référencé sur D17P33A.

La composition est segmentée à partir d'un décor généré sur magenta et d'un sol complet
séparé. Tous les calques couleur sont quantifiés sans tramage dans la palette RGB exacte
du rip; les formes et les pixels restent générés, pas des tuiles natives PMD.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import math
import shutil
import uuid
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = HERE / "bruts"
REF = RAW / "D17P33A_ROM.png"
REF_ANIM = RAW / "D17P33A_animations.webp"
GUIDE = RAW / "decor_magenta.png"
FLOOR = RAW / "sol_complet.png"
OUT = ROOT / "renders/passage_veines_cristal_v1"
STAGE = ROOT / ".cache/passage_veines_cristal_v1/passage_veines_cristal"
PREFIX = "PVC1"                         # code local de travail, pas un code MAP_BG
ASSET = "pvc1_passage_veines_cristallines"
NAMESPACE = "passage_veines_cristal"
TITLE = "Passage des Veines Cristallines"
W, H, TILE = 768, 576, 8                # format 4:3 PMDO : 96 x 72 cellules
GRID_X, GRID_Y = W // TILE, H // TILE
SRC_W, SRC_H = 1200, 896
SCALE = H / SRC_H
SCALED_W = round(SRC_W * SCALE)         # 771
CROP_X = (SCALED_W - W) // 2            # 1 px à gauche, 2 px à droite
BPA1_FRAMES, BPA5_FRAMES = 6, 4
TICKS_PER_PHASE = 10
COMPOSITE_PHASES = math.lcm(BPA1_FRAMES, BPA5_FRAMES)  # 12
LOOP_TICKS = COMPOSITE_PHASES * TICKS_PER_PHASE       # 120 ticks PMDO
PREVIEW_FRAME_MS = round(1000 * TICKS_PER_PHASE / 60) # 167 ms; cadence de preview seulement
MAGENTA = (220, 60, 220)

PROMPT_DECOR = (
    "Use the attached Pokémon Mystery Dungeon D17P33A rip as a STRICT visual reference for cool blue/cyan crystal "
    "palette, faceted quartz shapes, dark navy-blue cave stone, crisp pixel-art edges, and top-down scale. Create ONE "
    "entirely new original PMD dungeon map composition, WIDE LANDSCAPE 4:3, zoomed out, full map visible, intended for "
    "a 768 by 576 pixel final map. Do not copy the reference layout: instead design a broad crystalline cavern with a "
    "wide walkable route that clearly connects the SOUTH edge to the NORTH edge, making a gentle S-curve around an "
    "offset, elongated luminous turquoise crystal vein/pool in the middle. Put jagged dark-blue mineral walls around "
    "the outer rim, several distinct pale cyan crystal clusters at the sides, and a small raised geode shelf in the upper "
    "third. Keep the walkable floor broad and unbroken, at least 15 percent of map width at its narrowest point, with no "
    "crystals on the path. Render only the map terrain and crystal formations; no characters, no text, no UI, no border, "
    "no extra background scenery. Outside the terrain silhouette must be a perfectly flat, uniform chroma-magenta "
    "background RGB #DC3CDC, with absolutely no texture or shadows on that background. Pixel-art, crisp stepped "
    "silhouettes and discrete facets, limited blue/cyan/lavender palette grounded in the reference, no photorealism, "
    "no airbrushed gradients, no soft focus."
)
PROMPT_FLOOR = (
    "Edit the attached image into the matching FULL BASE-FLOOR plate for layer compositing. Preserve the canvas aspect "
    "ratio, framing, terrain silhouette, exact south-to-north S-shaped route, and uniform pure magenta RGB #DC3CDC outside "
    "the terrain. Inside the entire map silhouette, replace every crystal cluster, crystal wall, rock wall, raised geode "
    "shelf, glowing pool, shadow and object with one continuous walkable blue-gray cave floor in the same cracked-stone "
    "pixel style as the broad path. Fill underneath all former features; do not leave holes or magenta gaps inside the map. "
    "Do not add any objects, highlights, pools or text. Keep the path's overall shape visible only through very subtle "
    "floor value variation, not through objects. This is a floor-only underlay, not a finished scene."
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def loadmod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rgb(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.uint8)


def reference_rgb() -> np.ndarray:
    a = rgb(REF)
    if a.shape != (504, 456, 3):
        raise ValueError(f"Taille D17P33A inattendue: {a.shape}")
    return a


def reference_palette(ref: np.ndarray) -> tuple[np.ndarray, Image.Image]:
    colors = np.unique(ref.reshape(-1, 3), axis=0)
    if not 1 <= len(colors) <= 256:
        raise ValueError(f"Palette D17P33A inattendue: {len(colors)} couleurs")
    pal = Image.new("P", (1, 1))
    padding = np.tile(colors[-1], 256 - len(colors)).reshape(-1).tolist()
    table = colors.reshape(-1).tolist() + padding
    pal.putpalette(table)
    return colors, pal


def quantize_exact(a: np.ndarray, palette: Image.Image) -> np.ndarray:
    im = Image.fromarray(np.asarray(a, dtype=np.uint8), "RGB")
    return np.asarray(im.quantize(palette=palette, dither=Image.Dither.NONE).convert("RGB"), dtype=np.uint8)


def magenta_mask(a: np.ndarray) -> np.ndarray:
    r, g, b = (a[..., i].astype(np.int16) for i in range(3))
    # Inclut les légers écarts du générateur aux bords, sans assimiler les cyan/bleus au magenta.
    return (r > 140) & (b > 130) & ((r - g) > 70) & ((b - g) > 60)


def resize_plane(p: np.ndarray) -> np.ndarray:
    im = Image.fromarray(np.asarray(p, dtype=np.float32), "F")
    return np.asarray(im.resize((SCALED_W, H), Image.Resampling.BOX), dtype=np.float32)[:, CROP_X:CROP_X + W]


def downsample_masked(a: np.ndarray, mask: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    weight = resize_plane(mask.astype(np.float32))
    out = np.zeros((H, W, 3), dtype=np.uint8)
    for ch in range(3):
        numerator = resize_plane(a[..., ch].astype(np.float32) * mask.astype(np.float32))
        out[..., ch] = np.clip(np.round(numerator / np.maximum(weight, 1e-6)), 0, 255).astype(np.uint8)
    return out, weight > threshold, weight


def rgba(colors: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros((H, W, 4), dtype=np.uint8)
    out[..., :3] = colors
    out[..., 3] = mask.astype(np.uint8) * 255
    out[out[..., 3] == 0, :3] = 0
    return out


def detect_features(decor: np.ndarray) -> tuple[dict[str, np.ndarray], dict]:
    h, w = decor.shape[:2]
    r, g, b = (decor[..., i].astype(np.int16) for i in range(3))
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    terrain = ~magenta_mask(decor)

    cyan = terrain & (g - r > 35) & (b - r > 50) & (g > 95) & (b > 125) & (lum > 85)
    labels, n = ndi.label(cyan, structure=np.ones((3, 3), dtype=np.uint8))
    sizes = np.bincount(labels.ravel())
    if len(sizes) <= 1:
        raise AssertionError("Aucune veine cyan détectée dans le décor généré")
    pool_id = int(np.argmax(sizes[1:]) + 1)
    pool_raw = ndi.binary_fill_holes(ndi.binary_closing(labels == pool_id, structure=np.ones((9, 9), dtype=np.uint8)))
    pool_raw &= terrain
    if int(pool_raw.sum()) < 5000:
        raise AssertionError(f"La composante de veine est trop petite: {int(pool_raw.sum())} px")

    crystal = terrain & (b - r > 42) & (g - r > 20) & (lum > 118) & ~pool_raw
    crystal = ndi.binary_opening(crystal, structure=np.ones((3, 3), dtype=np.uint8)) & terrain & ~pool_raw

    distance = ndi.distance_transform_edt(terrain)
    # ROI documentée sur le guide 1200×896: l'étagère/géode au nord-est, hors de la bordure.
    yy, xx = np.mgrid[:h, :w]
    alcove_roi = (xx >= 620) & (xx < 950) & (yy < 285)
    alcove = terrain & alcove_roi & (lum < 120) & ~pool_raw & ~crystal & (distance >= 72)
    rim = terrain & (distance < 90) & ~pool_raw & ~crystal & ~alcove

    masks = {"bordure_minerale": rim, "alcove_geode": alcove, "cristaux": crystal, "veine_lumineuse": pool_raw}
    stats = {
        "terrain_ratio": round(float(terrain.mean()), 5),
        "magenta_ratio": round(float((~terrain).mean()), 5),
        "components_cyan": int(n),
        "veine_component_id": pool_id,
        "veine_source_area_px": int(pool_raw.sum()),
        "cristaux_source_area_px": int(crystal.sum()),
        "bordure_source_area_px": int(rim.sum()),
        "alcove_source_area_px": int(alcove.sum()),
        "thresholds": {
            "magenta": "R>140, B>130, R-G>70, B-G>60",
            "veine_seed": "G-R>35, B-R>50, G>95, B>125, luminance>85; plus grande composante cyan, closing 9x9, trous remplis",
            "cristaux": "B-R>42, G-R>20, luminance>118; ouverture 3x3; hors veine",
            "bordure": "distance au magenta <90 px; hors veine/cristaux/ROI géode",
            "alcove_roi_px": [620, 0, 950, 285],
        },
    }
    return masks, {"terrain": terrain, "distance": distance, "stats": stats}


def footprint_labels(blocked: np.ndarray) -> np.ndarray:
    free = ~blocked
    anchors = free[:-1, :-1] & free[1:, :-1] & free[:-1, 1:] & free[1:, 1:]
    structure = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8)
    return ndi.label(anchors, structure=structure)[0]


def nearest_marker(blocked: np.ndarray, target_px: tuple[int, int]) -> tuple[list[int], int]:
    labels = footprint_labels(blocked)
    candidates = np.argwhere(labels > 0)
    if not len(candidates):
        raise AssertionError("Aucune case praticable pour un personnage 16×16")
    tx, ty = target_px[0] // TILE, target_px[1] // TILE
    dist2 = (candidates[:, 1] - tx) ** 2 + (candidates[:, 0] - ty) ** 2
    i = int(np.argmin(dist2))
    cy, cx = (int(v) for v in candidates[i])
    return [cx * TILE, cy * TILE], int(round(float(np.sqrt(dist2[i])) * TILE))


def connected(blocked: np.ndarray, a: tuple[int, int], b: tuple[int, int]) -> bool:
    labels = footprint_labels(blocked)
    ax, ay = a[0] // TILE, a[1] // TILE
    bx, by = b[0] // TILE, b[1] // TILE
    if min(ax, bx, ay, by) < 0 or max(ax, bx) >= labels.shape[1] or max(ay, by) >= labels.shape[0]:
        return False
    return bool(labels[ay, ax] > 0 and labels[ay, ax] == labels[by, bx])


def cell_grid(blocked_pixels: np.ndarray) -> np.ndarray:
    return blocked_pixels.reshape(GRID_Y, TILE, GRID_X, TILE).mean((1, 3)) > 0.25


def animation_ramp(colors: np.ndarray, kind: str) -> list[tuple[int, int, int]]:
    c = colors.astype(int)
    r, g, b = c.T
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if kind == "cristaux":
        mask = (g - r > 18) & (b - r > 38) & (lum > 95)
    else:
        mask = (g - r > 28) & (b - r > 42) & (lum > 105)
    candidates = c[mask]
    if len(candidates) < 4:
        candidates = c[(b - r > 25) & (lum > 80)]
    order = np.argsort(candidates @ np.array([0.299, 0.587, 0.114]))
    candidates = candidates[order]
    # Quantiles espacés dans la palette native, sans créer de couleurs étrangères au rip.
    indices = np.linspace(0, len(candidates) - 1, 4).round().astype(int)
    ramp = [tuple(int(v) for v in candidates[i]) for i in indices]
    if len(set(ramp)) < 3:
        raise AssertionError(f"Rampe canonique insuffisante pour {kind}: {ramp}")
    return ramp


def make_animation(base: np.ndarray, mask: np.ndarray, ramp: list[tuple[int, int, int]], phases: int, kind: str) -> list[np.ndarray]:
    yy, xx = np.mgrid[:H, :W]
    frames = []
    for phase in range(phases):
        if kind == "cristaux":
            wave = np.sin(2 * np.pi * ((xx + 0.57 * yy) / 176.0 - phase / phases))
            band = wave > 0.90
            highlight = ramp[-2]
        else:
            wave = np.sin(2 * np.pi * ((0.68 * xx + yy) / 210.0 - phase / phases) + 0.22 * np.sin(yy / 27.0))
            band = wave > 0.96
            highlight = ramp[-2]
        out = np.zeros((H, W, 4), dtype=np.uint8)
        out[..., :3] = base
        out[..., :3][band & mask] = highlight
        out[..., 3] = mask.astype(np.uint8) * 255
        out[out[..., 3] == 0, :3] = 0
        frames.append(out)
    # Le masque alpha stable est requis pour qu'une animation PMDO reste une suite de tuiles cohérente.
    if any(not np.array_equal(frames[0][..., 3], fr[..., 3]) for fr in frames[1:]):
        raise AssertionError(f"Masque alpha instable: {kind}")
    return frames


def compose(layers: list[tuple[str, np.ndarray]]) -> np.ndarray:
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for _, layer in layers:
        canvas.alpha_composite(Image.fromarray(layer, "RGBA"))
    return np.asarray(canvas, dtype=np.uint8)


def png_bytes(array: np.ndarray) -> bytes:
    buff = io.BytesIO()
    Image.fromarray(array, "RGBA").save(buff, "PNG", compress_level=9)
    return buff.getvalue()


def write_ora(path: Path, layers: list[tuple[str, np.ndarray]]) -> None:
    root = ET.Element("image", w=str(W), h=str(H), name=TITLE)
    stack = ET.SubElement(root, "stack")
    merged = Image.new("RGBA", (W, H))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr("mimetype", "image/openraster", compress_type=zipfile.ZIP_STORED)
        for i, (name, arr) in reversed(list(enumerate(layers))):
            filename = f"data/layer{i:02d}.png"
            ET.SubElement(stack, "layer", name=name, src=filename, x="0", y="0", opacity="1.0",
                          visibility="visible", **{"composite-op": "svg:src-over"})
            z.writestr(filename, png_bytes(arr))
        for _, arr in layers:
            merged.alpha_composite(Image.fromarray(arr, "RGBA"))
        z.writestr("mergedimage.png", png_bytes(np.asarray(merged)))
        thumb = merged.copy()
        thumb.thumbnail((256, 256), Image.Resampling.NEAREST)
        z.writestr("Thumbnails/thumbnail.png", png_bytes(np.asarray(thumb)))
        z.writestr("stack.xml", ET.tostring(root, encoding="utf-8", xml_declaration=True))


def native_layer(gfx, bank, title: str, frames: list[np.ndarray], ticks: int, draw: int):
    bank.ids[bytes(256)] = (0, 0)
    bank.data[(0, 0)] = bytes(256)

    def tile_frames(x, y):
        found = []
        for frame in frames:
            tile = Image.fromarray(frame[y*TILE:y*TILE+TILE, x*TILE:x*TILE+TILE], "RGBA")
            found.append(bank.add(tile, x, y))
        if all(f is None for f in found):
            return []
        if any(f is None for f in found):
            raise AssertionError(f"Alpha instable sur {title}, tuile {x},{y}")
        return [found[0]] if all(f == found[0] for f in found) else found

    return gfx.layer(title, GRID_X, GRID_Y, tile_frames, ticks, draw=draw)


def create_project(layer_specs: list[dict], blocked: np.ndarray, markers: dict[str, list[int]]) -> dict:
    gfx = loadmod("pmdo_codec_pvc1", ROOT / "source/pmdo_cote/build.py")
    tools = loadmod("pmdo_index_pvc1", ROOT / "source/pmdo_cote/INSTALLER.py")
    shutil.rmtree(STAGE, ignore_errors=True)
    (STAGE / "Content/Tile").mkdir(parents=True, exist_ok=True)
    (STAGE / "Data/Ground").mkdir(parents=True, exist_ok=True)
    (STAGE / f"Data/Script/{NAMESPACE}/ground/{ASSET}").mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ROOT / "mod_metano_expeditions_pmdo_0812.zip") as z:
        template = json.loads(z.read("metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground"))
    ground = json.loads(json.dumps(template))
    obj = ground["Object"]
    native_layers, banks = [], []
    for idx, spec in enumerate(layer_specs):
        bank = gfx.TileBank(f"{PREFIX}_{idx:02d}_{spec['slug'].upper()}")
        native_layers.append(native_layer(gfx, bank, f"{idx:02d} {spec['name']}", spec["frames"], spec["ticks"], idx))
        banks.append(bank)
    native_layers.append(gfx.layer(f"{len(layer_specs):02d} Top - éléments avant-plan", GRID_X, GRID_Y, draw=len(layer_specs)))
    for bank in banks:
        bank.write(STAGE / f"Content/Tile/{bank.name}.tile")
    obj.update(
        Name={"DefaultText": TITLE, "LocalTexts": {}}, AssetName=ASSET, Released=False, TexSize=1,
        Music="", EdgeView=1, ViewCenter=None, ViewOffset={"X": 0, "Y": 0}, ActiveChar=None, Status={},
        Layers=native_layers,
        Background={"$type": "RogueEssence.Dungeon.LayeredBG, RogueEssence", "Layers": []},
        Comment=("PVC1, carte d'édition PMDO 0.8.12, 768×576 px / 96×72 cellules. Composition générée référencée "
                 "sur D17P33A et quantifiée sur sa palette RGB; formes et textures non natives. Animations visuelles "
                 "générées; cadence inspirée des deux BPA canoniques (6/4 phases, 10 ticks par phase). Les marqueurs "
                 "entrance/sortie sont provisoires; aucune destination/warp n'est reliée."),
    )
    gh, gw = blocked.shape
    obj["obstacles"] = [[{"Bounds": {"X": x*TILE, "Y": y*TILE, "Width": TILE, "Height": TILE},
                           "Tags": int(blocked[y, x])} for y in range(gh)] for x in range(gw)]
    marker_obj = lambda n, p: {"EntName": n, "Direction": 4, "EntEnabled": True, "triggerType": 0,
                               "Collider": {"X": p[0], "Y": p[1], "Width": 16, "Height": 16}}
    obj["Entities"] = [{"Name": "Marqueurs de transit", "Visible": True, "MapChars": [], "GroundObjects": [],
                         "Spawners": [], "Markers": [marker_obj(name, pos) for name, pos in markers.items()]}]
    obj["Decorations"] = [{"Name": "Décorations", "Layer": 2, "Visible": True, "Anims": []}]
    ground["Version"] = "0.8.12.0"
    gfx.save(STAGE / f"Data/Ground/{ASSET}.rsground", json.dumps(ground, ensure_ascii=False, separators=(",", ":")).encode())
    (STAGE / f"Data/Script/{NAMESPACE}/ground/{ASSET}/init.lua").write_text(
        f"-- {ASSET}: Ground d'édition; aucun warp automatique.\nreturn {{}}\n", encoding="utf-8")
    nodes = {}
    for path in sorted((STAGE / "Content/Tile").glob("*.tile")):
        with path.open("rb") as f:
            nodes[path.stem] = tools.read_node(f)
    (STAGE / "Content/Tile/index.idx").write_bytes(tools.encode_index(nodes))
    project_uuid = uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/meromoonmeri/projet-pmdo/passage_veines_cristal_v1")
    (STAGE / "Mod.xml").write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>{TITLE} - PMDO 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Ground éditable guidé par D17P33A; composition générée référencée, non une extraction pixel-native.</Description>
  <Namespace>{NAMESPACE}</Namespace>
  <UUID>{project_uuid}</UUID>
  <Version>1.0.0.0</Version>
  <GameVersion>0.8.12.0</GameVersion>
  <ModType>Quest</ModType>
  <Relationships />
</Header>
''', encoding="utf-8")
    shutil.copyfile(ROOT / "source/pmdo_cote/INSTALLER.py", STAGE / "INSTALLER.py")
    (STAGE / "README.md").write_text((HERE / "README_PACK.md").read_text(encoding="utf-8"), encoding="utf-8")
    return {"tile_banks": {bank.name: len(bank.data) for bank in banks}, "layer_count": len(native_layers),
            "tile_index_nodes": len(nodes)}


def fidelity_notes(colors: np.ndarray, map_colors: list[np.ndarray]) -> dict:
    source = {tuple(int(v) for v in row) for row in colors}
    used = set()
    for a in map_colors:
        if a.ndim == 3 and a.shape[-1] == 4:
            m = a[..., 3] > 0
            used |= {tuple(int(v) for v in c) for c in np.unique(a[..., :3][m].reshape(-1, 3), axis=0)}
    return {"source_palette_exact": used <= source, "source_palette_colors": int(len(source)),
            "used_palette_colors": int(len(used)), "used_rgb_colors": [list(c) for c in sorted(used)]}


def png_mask(path: Path, mask: np.ndarray) -> None:
    Image.fromarray(mask.astype(np.uint8) * 255, "L").save(path, compress_level=9)


def write_preview(layer_specs: list[dict], collision_rgba: np.ndarray, markers: dict[str, list[int]]) -> None:
    def uri(a: np.ndarray) -> str:
        return "data:image/png;base64," + base64.b64encode(png_bytes(a)).decode("ascii")
    payload = {
        "title": TITLE, "width": W, "height": H, "loop_ticks": LOOP_TICKS,
        "layers": [{"name": s["name"], "ticks": s["ticks"], "frames": [uri(f) for f in s["frames"]]} for s in layer_specs],
        "collision": uri(collision_rgba), "markers": markers,
    }
    html = '''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Passage des Veines Cristallines — PVC1</title><style>
:root{color-scheme:dark}body{margin:0;background:#10151f;color:#e5f2ff;font:15px system-ui,sans-serif}main{max-width:1040px;margin:auto;padding:20px}h1{color:#aeeaff;margin:.15em 0}.meta{color:#b7cde0;line-height:1.55}.bar{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0;align-items:center}label{display:flex;gap:6px;align-items:center;font-size:13px}button{padding:8px 12px;border:1px solid #496b83;border-radius:8px;background:#1c2d3b;color:#e8f7ff;font:inherit}input[type=range]{width:min(320px,45vw)}.frame{padding:10px;background:#080c12;border:1px solid #31536c;border-radius:12px}canvas{display:block;width:min(100%,768px);height:auto;margin:auto;image-rendering:pixelated}.note{font-size:12px;line-height:1.55;color:#a9c1d3}
</style><main><h1>Passage des Veines Cristallines — PVC1</h1><p class="meta">768×576 px · 96×72 cellules de 8 px · D17P33A comme référence canonique. Boucle d'aperçu 12 phases; 10 ticks/phase; 120 ticks au total.</p><div class="bar" id="controls"></div><div class="frame"><canvas id="map" width="768" height="576"></canvas></div><p class="note">Composition générée référencée, puis segmentée et quantifiée sur les 96 couleurs RGB exactes du rip. Aucun pixel de texture n'est présenté comme natif. Les calques « reflets » et « veine » sont des animations générées; leur cadence suit les longueurs des BPA1 (6 phases) et BPA5 (4 phases), chacune de 10 ticks. La durée GIF/WebP n'est pas utilisée pour définir le timing PMDO. Marqueurs/collisions provisoires; aucun test PMDO runtime/GPU/gameplay ni approbation artistique n'est revendiqué.</p></main>
<script>const D=__DATA__,c=document.getElementById('map'),ctx=c.getContext('2d'),controls=document.getElementById('controls'),cache=new Map();let phase=0,playing=true,showCollision=false;const enabled=D.layers.map(()=>true);function image(src){if(!cache.has(src)){const im=new Image();im.src=src;im.onload=draw;cache.set(src,im)}return cache.get(src)}function draw(){ctx.clearRect(0,0,D.width,D.height);D.layers.forEach((L,i)=>{if(enabled[i]){const j=(phase*10/Math.max(1,L.ticks))%L.frames.length;const im=image(L.frames[Math.floor(j)]);if(im.complete&&im.naturalWidth)ctx.drawImage(im,0,0)}});if(showCollision){const im=image(D.collision);if(im.complete&&im.naturalWidth)ctx.drawImage(im,0,0)}}D.layers.forEach((L,i)=>{const lab=document.createElement('label'),cb=document.createElement('input');cb.type='checkbox';cb.checked=true;cb.onchange=()=>{enabled[i]=cb.checked;draw()};lab.append(cb,L.name);controls.append(lab)});const toggle=document.createElement('label'),cc=document.createElement('input');cc.type='checkbox';cc.onchange=()=>{showCollision=cc.checked;draw()};toggle.append(cc,'Collisions / marqueurs');controls.append(toggle);const play=document.createElement('button');play.textContent='Pause';play.onclick=()=>{playing=!playing;play.textContent=playing?'Pause':'Lecture';};controls.append(play);const range=document.createElement('input');range.type='range';range.min='0';range.max='11';range.value='0';range.oninput=()=>{phase=Number(range.value);draw()};controls.append(range);setInterval(()=>{if(playing){phase=(phase+1)%12;range.value=String(phase);draw()}},167);window.addEventListener('load',draw);draw();</script></html>'''.replace("__DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    (ROOT / "apercu_passage_veines_cristal_v1.html").write_text(html, encoding="utf-8")


def build() -> dict:
    for path in (REF, REF_ANIM, GUIDE, FLOOR):
        if not path.is_file():
            raise FileNotFoundError(path)
    ref = reference_rgb()
    colors, palette = reference_palette(ref)
    guide, floor = rgb(GUIDE), rgb(FLOOR)
    if guide.shape != (SRC_H, SRC_W, 3) or floor.shape != guide.shape:
        raise ValueError(f"Les guides doivent mesurer {SRC_W}×{SRC_H}; reçus {guide.shape} / {floor.shape}")

    features, info = detect_features(guide)
    decor_mask = info["terrain"]
    floor_mask = ~magenta_mask(floor)
    common = decor_mask & floor_mask
    union = decor_mask | floor_mask
    iou = float(common.sum() / max(1, union.sum()))
    if iou < 0.995:
        raise AssertionError(f"Silhouettes décor/sol trop différentes: IoU={iou:.6f}")

    # Fond complet : sol généré séparément. Les objets viennent du décor complet et sont superposés.
    base_rgb, base_mask, base_weight = downsample_masked(floor, common, 0.10)
    base_rgb = quantize_exact(base_rgb, palette)
    static_arrays: dict[str, np.ndarray] = {"Sol complet généré": rgba(base_rgb, base_mask)}
    masks_out: dict[str, np.ndarray] = {"terrain": base_mask}
    segment_specs = [
        ("Bordure minérale", "bordure_minerale", 0.35),
        ("Alcôve géode", "alcove_geode", 0.25),
        ("Cristaux", "cristaux", 0.18),
        ("Veine lumineuse", "veine_lumineuse", 0.18),
    ]
    color_by_key: dict[str, np.ndarray] = {}
    for name, key, threshold in segment_specs:
        mask_hr = features[key] & common
        c, m, _ = downsample_masked(guide, mask_hr, threshold)
        c = quantize_exact(c, palette)
        # Toutes les couches de détail restent dans le terrain réel; pas de pixels magenta.
        m &= base_mask
        static_arrays[name] = rgba(c, m)
        masks_out[key] = m
        color_by_key[key] = c

    # Les calques statiques sont empilés du fond vers le premier plan.
    static_order = ["Sol complet généré", "Bordure minérale", "Alcôve géode", "Cristaux", "Veine lumineuse"]
    static_layers = [(name, static_arrays[name]) for name in static_order]
    static_scene = compose(static_layers)

    crystal_mask = masks_out["cristaux"]
    pool_mask = masks_out["veine_lumineuse"]
    crystal_ramp = animation_ramp(colors, "cristaux")
    pool_ramp = animation_ramp(colors, "veine")
    crystal_frames = make_animation(color_by_key["cristaux"], crystal_mask, crystal_ramp, BPA1_FRAMES, "cristaux")
    pool_frames = make_animation(color_by_key["veine_lumineuse"], pool_mask, pool_ramp, BPA5_FRAMES, "veine")

    # Deux pistes indépendantes : 6 et 4 phases de 10 ticks, PPCM = 12 phases / 120 ticks.
    layer_specs = [
        {"name": "Sol complet généré", "slug": "SOL", "frames": [static_arrays["Sol complet généré"]], "ticks": 60, "kind": "static"},
        {"name": "Bordure minérale", "slug": "BORDURE", "frames": [static_arrays["Bordure minérale"]], "ticks": 60, "kind": "static"},
        {"name": "Alcôve géode", "slug": "ALCOVE", "frames": [static_arrays["Alcôve géode"]], "ticks": 60, "kind": "static"},
        {"name": "Cristaux", "slug": "CRISTAUX", "frames": [static_arrays["Cristaux"]], "ticks": 60, "kind": "static"},
        {"name": "Veine lumineuse", "slug": "VEINE", "frames": [static_arrays["Veine lumineuse"]], "ticks": 60, "kind": "static"},
        {"name": "Reflets des cristaux — 6 × 10 ticks", "slug": "REFLETS", "frames": crystal_frames, "ticks": TICKS_PER_PHASE, "kind": "animation", "loop_ticks": BPA1_FRAMES*TICKS_PER_PHASE},
        {"name": "Ondes de la veine — 4 × 10 ticks", "slug": "ONDES", "frames": pool_frames, "ticks": TICKS_PER_PHASE, "kind": "animation", "loop_ticks": BPA5_FRAMES*TICKS_PER_PHASE},
    ]
    scene_frames = []
    for phase in range(COMPOSITE_PHASES):
        stack = [(name, arr) for name, arr in static_layers]
        stack += [("Reflets des cristaux", crystal_frames[phase % BPA1_FRAMES]),
                  ("Ondes de la veine", pool_frames[phase % BPA5_FRAMES])]
        scene_frames.append(compose(stack))
    scene_t000 = scene_frames[0]

    # Collisions de revue : paroi, alcôve, cristaux, veine et extérieur bloqués; accès nord/sud dégagés.
    blocked_pixels = (~base_mask) | masks_out["bordure_minerale"] | masks_out["alcove_geode"] | crystal_mask | pool_mask
    # Portails d'arrivée/départ alignés sur la route centrale, sans rendre praticable le fond magenta.
    for y0, y1 in ((0, 24), (H-24, H)):
        x0, x1 = W//2 - 40, W//2 + 40
        local_terrain = base_mask[y0:y1, x0:x1]
        blocked_pixels[y0:y1, x0:x1] &= ~local_terrain
    blocked = cell_grid(blocked_pixels)
    targets = {"entrance": (W//2 - 8, H - 24), "sortie": (W//2 - 8, 8)}
    markers, adjustments = {}, {}
    for name, target in targets.items():
        markers[name], adjustments[name] = nearest_marker(blocked, target)
    route_ok = connected(blocked, tuple(markers["entrance"]), tuple(markers["sortie"]))
    if not route_ok:
        raise AssertionError(f"Pas de route praticable 16×16 entre les marqueurs: {markers}")

    # Dossiers générés. Garder les bruts et les livraisons ZIP hors du nettoyage ciblé.
    OUT.mkdir(parents=True, exist_ok=True)
    for sub in ("maps", "animation", "masques", "review"):
        shutil.rmtree(OUT / sub, ignore_errors=True)
    map_dir = OUT / "maps/passage"
    for sub in ("calques", "masques", "review"):
        (map_dir / sub).mkdir(parents=True, exist_ok=True)
    (OUT / "animation/reflets_cristaux").mkdir(parents=True, exist_ok=True)
    (OUT / "animation/ondes_veine").mkdir(parents=True, exist_ok=True)

    filename_map = {
        "Sol complet généré": "PVC1_00_sol_complet_genere.png",
        "Bordure minérale": "PVC1_01_bordure_minerale.png",
        "Alcôve géode": "PVC1_02_alcove_geode.png",
        "Cristaux": "PVC1_03_cristaux.png",
        "Veine lumineuse": "PVC1_04_veine_lumineuse.png",
        "Reflets des cristaux — 6 × 10 ticks": "PVC1_05_reflets_phase0.png",
        "Ondes de la veine — 4 × 10 ticks": "PVC1_06_ondes_phase0.png",
    }
    ora_layers = []
    for spec in layer_specs:
        arr = spec["frames"][0]
        filename = filename_map[spec["name"]]
        Image.fromarray(arr, "RGBA").save(map_dir / "calques" / filename, compress_level=9)
        ora_layers.append((spec["name"], arr))
    for i, arr in enumerate(crystal_frames):
        Image.fromarray(arr, "RGBA").save(OUT / "animation/reflets_cristaux" / f"PVC1_reflets_f{i:02d}.png", compress_level=9)
    for i, arr in enumerate(pool_frames):
        Image.fromarray(arr, "RGBA").save(OUT / "animation/ondes_veine" / f"PVC1_ondes_f{i:02d}.png", compress_level=9)
    for key, mask in masks_out.items():
        png_mask(map_dir / "masques" / f"PVC1_masque_{key}.png", mask)
    png_mask(map_dir / "masques/PVC1_masque_praticable.png", ~blocked_pixels)
    png_mask(map_dir / "masques/PVC1_masque_obstacles.png", blocked_pixels)

    Image.fromarray(scene_t000, "RGBA").save(map_dir / "review/PVC1_scene_t000.png", compress_level=9)
    webp_frames = [Image.fromarray(a, "RGBA") for a in scene_frames]
    webp_frames[0].save(map_dir / "review/PVC1_animation_12_phases.webp", format="WEBP", save_all=True,
                        append_images=webp_frames[1:], duration=PREVIEW_FRAME_MS, loop=0, lossless=True, method=6)
    collision_view = Image.fromarray(scene_t000, "RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y, x in zip(*np.nonzero(blocked)):
        draw.rectangle((x*TILE, y*TILE, x*TILE+7, y*TILE+7), fill=(235, 42, 56, 88))
    for name, (x, y) in markers.items():
        col = (255, 225, 52, 255) if name == "entrance" else (60, 222, 255, 255)
        draw.rectangle((x, y, x+15, y+15), outline=col, width=2)
    collision_view.alpha_composite(overlay)
    collision_rgba = np.asarray(overlay, dtype=np.uint8)
    collision_view.save(map_dir / "review/PVC1_collisions_marqueurs.png", compress_level=9)
    write_ora(map_dir / "PVC1_calques.ora", ora_layers)

    native = create_project(layer_specs, blocked, markers)
    used_palette = fidelity_notes(colors, [spec["frames"][0] for spec in layer_specs] + crystal_frames + pool_frames)
    if not used_palette["source_palette_exact"]:
        raise AssertionError("Une couleur hors palette D17P33A a été exportée")

    index = json.loads((ROOT / "source/outil_maps_pmdsky/index_rom.json").read_text(encoding="utf-8"))
    entry = next(m for m in index["maps"] if m["code"] == "D17P33A")
    if entry["taille_px"] != [456, 504] or entry["frames"] != 12 or entry["couches"] != 2:
        raise AssertionError(f"Métadonnées D17P33A inattendues: {entry}")
    manifest = {
        "lot": "passage_veines_cristal_v1", "prefix_local": PREFIX, "title": TITLE,
        "source": {
            "canonical_reference": REF.name, "reference_sha256": sha256(REF), "reference_size_px": [456, 504],
            "reference_rgb_colors": int(len(colors)), "reference_frames": 12, "reference_graphical_layers": 2,
            "source_repository": "pret/pmd-sky", "source_commit": "c8073235b39746a7ee74e6cea16c730bd91a1e67",
            "source_resources": ["files/MAP_BG/d17p33a.bma", "files/MAP_BG/d17p33a.bpc", "files/MAP_BG/d17p33a.bpl",
                                 "files/MAP_BG/d17p33a1.bpa", "files/MAP_BG/d17p33a5.bpa"],
            "extraction": "source/outil_maps_pmdsky/recuperer_maps.py rom --only D17P33A; skytemple-files",
            "index_entry": {"size_px": entry["taille_px"], "rendered_frames": entry["frames"],
                            "layers": entry["couches"], "collision": entry["collision"],
                            "palette_animation": entry["animation_palette"], "bpa_slots": entry["bpa"]},
            "bpa_timing": {"slot_1": {"frames": 6, "ticks_per_frame": 10, "loop_ticks": 60},
                           "slot_5": {"frames": 4, "ticks_per_frame": 10, "loop_ticks": 40},
                           "combined_frames": COMPOSITE_PHASES, "combined_loop_ticks": LOOP_TICKS,
                           "at_60_ticks_per_second_seconds": round(LOOP_TICKS / 60, 3)},
            "animation_render_sha256": sha256(REF_ANIM), "animation_render_frames": 12,
            "gallery_gif": "large.D17P33A.gif.188f8399cf4c18292d9ecdd2454bcd10.gif",
            "gallery_and_rom_frames_pixel_identical": True,
            "gallery_declared_ms_per_frame": 160, "rom_webp_declared_ms_per_frame": 167,
            "native_pixel_origin": "Aucun pixel de texture n'est prélevé. La palette RGB de 96 couleurs est la palette exacte du rip; composition, segmentation et animations visuelles sont générées.",
        },
        "generated_assets": {
            "guide": {"file": GUIDE.name, "sha256": sha256(GUIDE), "size_px": [SRC_W, SRC_H], "prompt": PROMPT_DECOR},
            "floor_underlay": {"file": FLOOR.name, "sha256": sha256(FLOOR), "size_px": [SRC_W, SRC_H], "prompt": PROMPT_FLOOR},
            "guide_floor_mask_iou": round(iou, 6),
            "normalization": {"scale_uniform": round(SCALE, 8), "scaled_size_px": [SCALED_W, H],
                              "crop_x_px": [CROP_X, SCALED_W - CROP_X - W], "resampling": "BOX pondéré par classe, puis palette D17P33A sans tramage"},
        },
        "map": {"size_px": [W, H], "grid_8px": [GRID_X, GRID_Y], "tile_px": TILE,
                "layers": [s["name"] for s in layer_specs], "segmentation": info["stats"],
                "palette": used_palette, "static_preview": "maps/passage/review/PVC1_scene_t000.png"},
        "animation": {"visuals_generated": True, "timing_basis": "BPA1/BPA5 frame counts and frame durations, not GIF/WebP timing",
                      "tracks": [{"name": "Reflets des cristaux", "frames": BPA1_FRAMES, "ticks_per_frame": TICKS_PER_PHASE,
                                  "loop_ticks": BPA1_FRAMES*TICKS_PER_PHASE},
                                 {"name": "Ondes de la veine", "frames": BPA5_FRAMES, "ticks_per_frame": TICKS_PER_PHASE,
                                  "loop_ticks": BPA5_FRAMES*TICKS_PER_PHASE}],
                      "composite_frames": COMPOSITE_PHASES, "composite_loop_ticks": LOOP_TICKS,
                      "preview_ms_per_phase": PREVIEW_FRAME_MS, "palette_colors_exact": True},
        "collision": {"method": "Extérieur, bordure minérale, alcôve, cristaux et veine bloqués; grille 8 px; cellule bloquée si plus de 25 % de pixels obstacles; ouvertures nord/sud réservées.",
                      "blocked_cells": int(blocked.sum()), "walkable_cells": int((~blocked).sum()),
                      "markers_px": markers, "marker_adjustments_px": adjustments,
                      "north_south_path_16x16": bool(route_ok)},
        "native": {"target": "PMDO 0.8.12", "namespace": NAMESPACE, "asset": ASSET, "tile_px": TILE,
                   "tile_banks": native["tile_banks"], "ground_layer_count_including_top": native["layer_count"],
                   "tile_index_nodes": native["tile_index_nodes"], "runtime_tested": False, "gpu_tested": False},
        "limitations": [
            "PVC1 est un identifiant local de lot, pas un ID MAP_BG officiel.",
            "Le décor et les matières sont des rendus générés référencés, segmentés puis quantifiés; ils ne sont pas des tuiles source pixel-natives.",
            "La palette 96 couleurs est exacte au rip D17P33A, mais une palette exacte ne certifie pas l'origine native des formes.",
            "Les effets visuels sont générés; seules les durées et longueurs des deux cycles BPA canoniques (6/4 phases, 10 ticks) servent de cadence.",
            "Les collisions et les marqueurs entrance/sortie sont provisoires; les destinations/warps, occlusions et rendu demandent une revue dans PMDO.",
            "Aucun test runtime PMDO, GPU ou gameplay n'a été effectué; l'approbation artistique reste false.",
        ],
        "art_approved": False, "runtime_tested": False, "gpu_tested": False,
    }

    # Artefacts éditables et de revue.
    for key, filename in (("terrain", "PVC1_masque_terrain.png"), ("bordure_minerale", "PVC1_masque_bordure.png"),
                          ("alcove_geode", "PVC1_masque_alcove.png"), ("cristaux", "PVC1_masque_cristaux.png"),
                          ("veine_lumineuse", "PVC1_masque_veine.png")):
        png_mask(map_dir / "masques" / filename, masks_out[key])
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(make_readme(manifest), encoding="utf-8")
    (STAGE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_preview(layer_specs, collision_rgba, markers)

    return manifest


def make_readme(m: dict) -> str:
    return f'''# {TITLE} — PVC1 (code local)

Carte 4:3 **{W}×{H} px**, {GRID_X}×{GRID_Y} cellules de 8 px (`TexSize=1`). Aperçu : [`apercu_passage_veines_cristal_v1.html`](../../apercu_passage_veines_cristal_v1.html). Build : [`source/passage_veines_cristal_v1/`](../../source/passage_veines_cristal_v1/).

- Rip canonique D17P33A : {m['source']['reference_size_px'][0]}×{m['source']['reference_size_px'][1]} px, 12 rendus, 2 couches, 96 couleurs RGB distinctes; PNG et animation WebP extraits par skytemple-files. Les 12 frames du rendu ROM et du GIF galerie sont pixel-identiques.
- Animations du rip : BPA1 = 6 frames × 10 ticks; BPA5 = 4 × 10 ticks. Le cycle combiné dure 12 phases / 120 ticks. Les durées d'affichage GIF/WebP ne définissent pas le timing du jeu.
- Le décor et le sol ont été générés séparément avec le rip comme référence, segmentés, normalisés uniformément à 768×576 puis quantifiés sans tramage dans la palette exacte du rip. **Aucun pixel de texture natif n'est copié** : formes et textures demeurent générées.
- Calques éditables : sol complet, bordure minérale, alcôve géode, cristaux, veine lumineuse, reflets (6 phases), ondes de la veine (4 phases), plus Top vide dans le Ground.
- Ground PMDO 0.8.12; collisions calculées et marqueurs `entrance` / `sortie` provisoires. Destinations/warps à relier.
- Tests unitaires, exports, ZIP et provenance : `test_build.py`, `package.py`, `manifest.json`, `SHA256SUMS.json`.

**Limites** : les animations visuelles sont générées; seules leurs cadences 6/4 × 10 ticks s'inspirent des BPA. Aucun lancement PMDO, test GPU/gameplay ni approbation artistique n'est revendiqué.
'''


if __name__ == "__main__":
    result = build()
    print(json.dumps({"prefix": result["prefix_local"], "map": result["map"]["size_px"],
                      "layers": result["map"]["layers"], "path_16px": result["collision"]["north_south_path_16x16"],
                      "blocked_cells": result["collision"]["blocked_cells"], "tile_banks": result["native"]["tile_banks"]},
                     ensure_ascii=False, indent=2))
