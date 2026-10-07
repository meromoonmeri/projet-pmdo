"""CPL1 — Défilé des Aiguilles. Layout généré référencé sur D13P11A, puis Ground PMDO 0.8.12."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import shutil
import uuid
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = HERE / "bruts"
GUIDE = RAW / "CPL1_layout_reference.png"
REF = RAW / "D13P11A_ROM.png"
OUT = ROOT / "renders/defile_aiguilles_v1"
STAGE = ROOT / ".cache/defile_aiguilles_v1/defile_aiguilles"
PREFIX = "CPL1"                      # code interne du lot, pas un identifiant ROM
ASSET = "cpl1_passage_aiguilles"
NAMESPACE = "defile_aiguilles"
TITLE = "Défilé des Aiguilles"
W = H = 456                           # D13P11A: taille de rip 1:1, sans agrandissement
TILE = 8
GRID = W // TILE
MAGENTA = (220, 60, 220)

PROMPT = ("Use the attached D13P11A Pokémon Mystery Dungeon map image as the strict canonical reference for the exact "
          "sandy-gold palette, layered ochre cliff texture, rounded stone pillars, lighting, pixel scale, and top-down "
          "perspective. Create a NEW, distinct square 1:1 PMD dungeon map, not a crop, recolor, mirror, or copy of the "
          "reference. Title for our notes only: “Défilé des Aiguilles”; do not write any text in the image. The map must "
          "have a clear walkable sandy route connecting the SOUTH edge to the NORTH edge, winding in two gentle bends "
          "around a broad central rock mesa. Place tall layered cliff walls on both sides, several separated freestanding "
          "stone needles/pillars, and a few small rubble clusters; leave the route wide, continuous, and visibly clear. "
          "The north and south exits must both touch the image edge. Match the reference’s pale warm sand and muted "
          "brown/olive sandstone exactly; use crisp pixel-art forms and simple clean outlines, no smooth painterly "
          "gradients. Strictly top-down camera, square layout, no characters, no UI, no labels, no extra rivers, no water, "
          "no magenta, no border, no shadows crossing the walkable route.")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
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


def reference_rgb() -> np.ndarray:
    with Image.open(REF) as im:
        if getattr(im, "n_frames", 1) != 1:
            raise AssertionError("D13P11A n'est plus une référence statique")
        a = np.asarray(im.convert("RGB"), dtype=np.uint8)
    if a.shape != (H, W, 3):
        raise ValueError(f"Taille D13P11A inattendue: {a.shape}")
    return a


def make_palette(ref: np.ndarray):
    colors = np.unique(ref.reshape(-1, 3), axis=0)
    if len(colors) > 256:
        raise ValueError("La palette canonique dépasse 256 couleurs")
    pal = Image.new("P", (1, 1))
    table = colors.reshape(-1).tolist() + [0] * (768 - 3 * len(colors))
    pal.putpalette(table)
    return colors, pal


def reduce_and_quantize(guide: Image.Image, palette: Image.Image) -> np.ndarray:
    if guide.width != guide.height:
        raise ValueError(f"Le guide doit rester carré, reçu {guide.size}")
    reduced = guide.convert("RGB").resize((W, H), Image.Resampling.BOX)
    quantized = reduced.quantize(palette=palette, dither=Image.Dither.NONE).convert("RGB")
    return np.asarray(quantized, dtype=np.uint8)


def floor_patch(ref: np.ndarray) -> tuple[np.ndarray, list[int]]:
    r, g, b = (ref[..., i].astype(int) for i in range(3))
    sand = (r >= 210) & (g >= 175) & (b >= 100) & ((g - b) >= 25)
    best = (-1.0, 0, 0)
    for y in range(0, H - 32 + 1, TILE):
        for x in range(0, W - 32 + 1, TILE):
            score = float(sand[y:y+32, x:x+32].mean())
            if score > best[0]:
                best = (score, x, y)
    if best[0] < 0.96:
        raise AssertionError(f"Aucun patch de sable canonique assez propre: {best[0]:.3f}")
    x, y = best[1], best[2]
    return ref[y:y+32, x:x+32].copy(), [x, y, 32, 32]


def tiled_floor(patch: np.ndarray) -> np.ndarray:
    out = np.zeros((H, W, 4), dtype=np.uint8)
    rgba_patch = np.dstack((patch, np.full((32, 32), 255, dtype=np.uint8)))
    for y in range(0, H, 32):
        for x in range(0, W, 32):
            h, w = min(32, H-y), min(32, W-x)
            out[y:y+h, x:x+w] = rgba_patch[:h, :w]
    return out


def rgba(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.zeros((H, W, 4), dtype=np.uint8)
    out[..., :3] = rgb
    out[..., 3] = mask.astype(np.uint8) * 255
    out[out[..., 3] == 0, :3] = 0
    return out


def rock_mask_from_reference_palette(rgb: np.ndarray) -> np.ndarray:
    # Seuil défini sur les 30 couleurs du rip D13P11A: falaises et grès restent distincts du sable clair.
    r, g, b = (rgb[..., i].astype(np.int16) for i in range(3))
    return (r < 205) & (g < 168) & (b < 132) & ((r - g) > 12)


def split_rock_components(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    labels, count = ndi.label(mask, structure=np.ones((3, 3), dtype=np.uint8))
    cliffs = np.zeros_like(mask)
    pillars = np.zeros_like(mask)
    records = []
    for label in range(1, count + 1):
        comp = labels == label
        area = int(comp.sum())
        yy, xx = np.nonzero(comp)
        touches_edge = bool((xx.min() == 0) or (yy.min() == 0) or (xx.max() == W-1) or (yy.max() == H-1))
        kind = "falaises" if touches_edge or area >= 9000 else "piliers"
        (cliffs if kind == "falaises" else pillars)[:] |= comp
        records.append({"id": label, "kind": kind, "area_px": area,
                        "bbox_px": [int(xx.min()), int(yy.min()), int(xx.max()-xx.min()+1), int(yy.max()-yy.min()+1)],
                        "touches_edge": touches_edge})
    return cliffs, pillars, records


def cell_grid(blocked_pixels: np.ndarray) -> np.ndarray:
    return blocked_pixels.reshape(GRID, TILE, GRID, TILE).mean((1, 3)) > 0.25


def footprint_labels(blocked: np.ndarray) -> np.ndarray:
    free = ~blocked
    anchors = free[:-1, :-1] & free[1:, :-1] & free[:-1, 1:] & free[1:, 1:]
    return ndi.label(anchors, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8))[0]


def nearest_marker(blocked: np.ndarray, target: tuple[int, int]) -> tuple[list[int], int]:
    labels = footprint_labels(blocked)
    candidates = np.argwhere(labels > 0)
    if not len(candidates):
        raise AssertionError("Aucune case de sol libre 16×16")
    tx, ty = target[0] // TILE, target[1] // TILE
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


def collision_pixels(rock: np.ndarray) -> np.ndarray:
    blocked = rock.copy()
    blocked[:, :TILE] = True; blocked[:, W-TILE:] = True
    blocked[0, :] = True; blocked[-1, :] = True
    blocked[0, W//2-24:W//2+24] = False
    blocked[-1, W//2-24:W//2+24] = False
    return blocked


def connect_southern_saddle(rgb: np.ndarray, rock: np.ndarray, sand_patch: np.ndarray):
    """Open a short south-of-mesa saddle if the generated guide splits the transit route."""
    blocked_px = collision_pixels(rock)
    grid = cell_grid(blocked_px)
    targets = {"entrance": (W//2-8, H-24), "sortie": (W//2-8, 8)}
    entry, _ = nearest_marker(grid, targets["entrance"])
    exit_, _ = nearest_marker(grid, targets["sortie"])
    labels = footprint_labels(grid)
    entry_id = int(labels[entry[1]//TILE, entry[0]//TILE])
    exit_id = int(labels[exit_[1]//TILE, exit_[0]//TILE])
    if entry_id == 0 or exit_id == 0:
        raise AssertionError("Marqueur initial non praticable")
    if entry_id == exit_id:
        return rgb, rock, {"carved": False, "width_px": 0, "polyline_px": [], "from_component": exit_id, "to_component": entry_id}
    upper = np.argwhere(labels == exit_id)
    lower = np.argwhere(labels == entry_id)
    distances, indices = cKDTree(lower).query(upper, k=1)
    i = int(np.argmin(distances))
    uy, ux = (int(v) for v in upper[i])
    ly, lx = (int(v) for v in lower[int(indices[i])])
    start = (ux*TILE + TILE, uy*TILE + TILE)
    end = (lx*TILE + TILE, ly*TILE + TILE)
    # A small dog-leg goes around the mesa's south-east toe instead of through its face.
    saddle_y = min(H-24, max(start[1], end[1]) + TILE)
    points = [start, (start[0], saddle_y), (end[0], saddle_y), end]
    sand = np.indices((H, W))
    texture = sand_patch[sand[0] % sand_patch.shape[0], sand[1] % sand_patch.shape[1]]
    for width in (22, 26, 30):
        mask_image = Image.new("L", (W, H), 0)
        draw = ImageDraw.Draw(mask_image)
        draw.line(points, fill=255, width=width, joint="curve")
        radius = width // 2
        for x, y in (points[0], points[-1]):
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=255)
        corridor = np.asarray(mask_image) > 0
        rock2 = rock.copy(); rock2[corridor] = False
        rgb2 = rgb.copy(); rgb2[corridor] = texture[corridor]
        if connected(cell_grid(collision_pixels(rock2)), entry, exit_):
            return rgb2, rock2, {"carved": True, "width_px": width, "polyline_px": [list(p) for p in points],
                                 "from_component": exit_id, "to_component": entry_id,
                                 "nearest_component_gap_tiles": round(float(distances[i]), 2),
                                 "method": "rip D13P11A sand patch, repeated only inside the short south-of-mesa connector"}
    raise AssertionError("Le petit col de sable n'a pas relié les deux composantes")


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
        thumb = merged.copy(); thumb.thumbnail((256, 256), Image.Resampling.NEAREST)
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
    return gfx.layer(title, GRID, GRID, tile_frames, ticks, draw=draw)


def create_project(gfx, tools, layers: list[tuple[str, np.ndarray]], blocked: np.ndarray,
                   markers: dict[str, list[int]]) -> dict:
    shutil.rmtree(STAGE, ignore_errors=True)
    (STAGE / "Content/Tile").mkdir(parents=True, exist_ok=True)
    (STAGE / "Data/Ground").mkdir(parents=True, exist_ok=True)
    (STAGE / f"Data/Script/{NAMESPACE}/ground/{ASSET}").mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ROOT / "mod_metano_expeditions_pmdo_0812.zip") as z:
        ground = json.loads(z.read("metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground"))
    obj = json.loads(json.dumps(ground["Object"]))
    native_layers, banks = [], []
    for idx, (title, arr) in enumerate(layers):
        bank = gfx.TileBank(f"{PREFIX}_{idx:02d}_{title.split()[0].upper()}")
        native_layers.append(native_layer(gfx, bank, f"{idx:02d} {title}", [arr], 60, idx))
        banks.append(bank)
    native_layers.append(gfx.layer("04 Top - éléments avant-plan", GRID, GRID, draw=4))
    for bank in banks:
        bank.write(STAGE / f"Content/Tile/{bank.name}.tile")
    obj.update(Name={"DefaultText": TITLE, "LocalTexts": {}}, AssetName=ASSET, Released=False, TexSize=1,
               Music="", EdgeView=1, ViewCenter=None, ViewOffset={"X": 0, "Y": 0}, ActiveChar=None, Status={},
               Layers=native_layers, Background={"$type": "RogueEssence.Dungeon.LayeredBG, RogueEssence", "Layers": []},
               Comment=("Projet d'édition PMDO 0.8.12. Guide généré référencé sur le rip D13P11A; réduction à la "
                        "grille carrée 456×456 puis quantification aux couleurs du rip. Les textures générées ne sont "
                        "pas des tuiles natives originales. Marqueurs de transit; destinations à relier."))
    gh, gw = blocked.shape
    obj["obstacles"] = [[{"Bounds": {"X": x*TILE, "Y": y*TILE, "Width": TILE, "Height": TILE},
                           "Tags": int(blocked[y, x])} for y in range(gh)] for x in range(gw)]
    mk = lambda n, p: {"EntName": n, "Direction": 4, "EntEnabled": True, "triggerType": 0,
                       "Collider": {"X": p[0], "Y": p[1], "Width": 16, "Height": 16}}
    obj["Entities"] = [{"Name": "Marqueurs de transit", "Visible": True, "MapChars": [], "GroundObjects": [],
                         "Spawners": [], "Markers": [mk(name, pos) for name, pos in markers.items()]}]
    obj["Decorations"] = [{"Name": "Décorations", "Layer": 2, "Visible": True, "Anims": []}]
    ground["Version"] = "0.8.12.0"; ground["Object"] = obj
    gfx.save(STAGE / f"Data/Ground/{ASSET}.rsground", json.dumps(ground, ensure_ascii=False, separators=(",", ":")).encode())
    (STAGE / f"Data/Script/{NAMESPACE}/ground/{ASSET}/init.lua").write_text(
        f"-- {ASSET}: projet d'édition, pas de warp automatique.\nreturn {{}}\n", encoding="utf-8")
    nodes = {}
    for path in sorted((STAGE / "Content/Tile").glob("*.tile")):
        with path.open("rb") as f:
            nodes[path.stem] = tools.read_node(f)
    (STAGE / "Content/Tile/index.idx").write_bytes(tools.encode_index(nodes))
    project_uuid = uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/meromoonmeri/projet-pmdo/defile_aiguilles_v1")
    (STAGE / "Mod.xml").write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Défilé des Aiguilles - PMDO 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Ground carré d'édition, guidé par D13P11A. Texture générée référencée et quantifiée sur les couleurs du rip; pas une aventure jouable complète.</Description>
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
    return {"tile_banks": {bank.name: len(bank.data) for bank in banks}, "layer_count": len(native_layers)}


def fidelity(generated: np.ndarray, reference: np.ndarray) -> dict:
    def masks(a):
        r, g, b = (a[..., i].astype(int) for i in range(3))
        sand = (r >= 205) & (g >= 168) & (b >= 90)
        rock = (r < 205) & (g < 168) & (b < 132) & ((r - g) > 12)
        return {"sable": sand, "gres": rock}
    gm, rm = masks(generated), masks(reference)
    out = {}
    for k in gm:
        a, b = generated[gm[k]].astype(float), reference[rm[k]].astype(float)
        if not len(a) or not len(b):
            raise AssertionError(f"Classe de matière vide: {k}")
        ma, mb = a.mean(0), b.mean(0)
        out[k] = {"guide_rgb_moyen": [round(float(v), 1) for v in ma],
                  "rip_rgb_moyen": [round(float(v), 1) for v in mb],
                  "ecart_rgb_moyen": round(float(np.linalg.norm(ma-mb)), 2)}
    return out


def write_preview(layers: list[tuple[str, np.ndarray]], collision: np.ndarray, marker_data: dict) -> None:
    def uri(a):
        return "data:image/png;base64," + base64.b64encode(png_bytes(a)).decode("ascii")
    payload = {"title": TITLE, "layers": [{"name": n, "src": uri(a)} for n, a in layers],
               "collision": uri(collision)}
    html = '''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Défilé des Aiguilles — PMDO</title><style>
:root{color-scheme:dark}body{margin:0;background:#1c1914;color:#f4e4bd;font:16px system-ui,sans-serif}main{max-width:960px;margin:auto;padding:22px}h1{color:#ffe6ad}
.bar{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0}button{padding:9px 12px;border:1px solid #8b7045;border-radius:8px;background:#352b1c;color:#fff0c9;font:inherit}label{display:flex;gap:6px;align-items:center;font-size:14px}.frame{padding:12px;background:#0d0c09;border:1px solid #6b5738;border-radius:12px}canvas{display:block;width:min(100%,768px);height:auto;margin:auto;image-rendering:pixelated}.note{font-size:13px;line-height:1.55;color:#c8bb9a}
</style><main><h1>Défilé des Aiguilles</h1><p>Carte carrée 456×456 px · 57×57 cellules de 8 px · référence canonique D13P11A.</p><div class="bar" id="controls"></div><div class="frame"><canvas id="map" width="456" height="456"></canvas></div><p class="note">Textures de composition générées avec le rip comme référence puis quantifiées sur sa palette; il ne s'agit pas des tuiles source originales. Active les collisions pour la revue. Le Ground PMDO est construit, mais aucun test moteur, rendu GPU ou gameplay n'est revendiqué.</p></main>
<script>const DATA=__DATA__;const c=document.getElementById('map'),ctx=c.getContext('2d');const cache=new Map();function img(src){if(!cache.has(src)){let i=new Image();i.src=src;cache.set(src,i)}return cache.get(src)}const controls=document.getElementById('controls');const flags=DATA.layers.map(()=>true);let showCol=false;function draw(){ctx.clearRect(0,0,456,456);DATA.layers.forEach((l,i)=>{if(flags[i]){const im=img(l.src);if(im.complete&&im.naturalWidth)ctx.drawImage(im,0,0)}});if(showCol){const im=img(DATA.collision);if(im.complete&&im.naturalWidth)ctx.drawImage(im,0,0)}}DATA.layers.forEach((l,i)=>{let lab=document.createElement('label'),cb=document.createElement('input');cb.type='checkbox';cb.checked=true;cb.onchange=()=>{flags[i]=cb.checked;draw()};lab.append(cb,l.name);controls.append(lab)});let lab=document.createElement('label'),cb=document.createElement('input');cb.type='checkbox';cb.onchange=()=>{showCol=cb.checked;draw()};lab.append(cb,'Collisions / marqueurs');controls.append(lab);window.addEventListener('load',draw);draw();</script></html>'''.replace("__DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    (ROOT / "apercu_defile_aiguilles_v1.html").write_text(html, encoding="utf-8")


def build() -> dict:
    ref = reference_rgb()
    colors, palette = make_palette(ref)
    if not GUIDE.is_file():
        raise FileNotFoundError(GUIDE)
    with Image.open(GUIDE) as im:
        guide = im.convert("RGB")
    rgb = reduce_and_quantize(guide, palette)
    ref_set = {tuple(int(v) for v in row) for row in colors}
    map_set = {tuple(int(v) for v in row) for row in np.unique(rgb.reshape(-1, 3), axis=0)}
    if not map_set <= ref_set:
        raise AssertionError("Couleurs étrangères au rip après quantification")

    # Géométrie : les tons grès sombres définissent falaises/piliers; sable clair praticable.
    # La génération séparait les deux moitiés du passage. On ouvre donc un petit col
    # sous le pied sud-est de la mesa avec un patch de sable exact du rip D13P11A.
    base_patch, patch_box = floor_patch(ref)
    rock = rock_mask_from_reference_palette(rgb)
    rgb, rock, connector = connect_southern_saddle(rgb, rock, base_patch)
    cliff_mask, pillar_mask, components = split_rock_components(rock)
    if not (0.08 < rock.mean() < 0.70):
        raise AssertionError(f"Masque de grès anormal: {rock.mean():.3f}")
    blocked_pixels = collision_pixels(rock)
    blocked = cell_grid(blocked_pixels)
    targets = {"entrance": (W//2-8, H-24), "sortie": (W//2-8, 8)}
    markers, adjustments = {}, {}
    for name, point in targets.items():
        markers[name], adjustments[name] = nearest_marker(blocked, point)
    route_ok = connected(blocked, tuple(markers["entrance"]), tuple(markers["sortie"]))
    if not route_ok:
        raise AssertionError(f"Aucun passage 16×16 nord-sud: {markers}")

    base = tiled_floor(base_patch)
    floor = rgba(rgb, ~rock)
    cliffs = rgba(rgb, cliff_mask)
    pillars = rgba(rgb, pillar_mask)
    layers = [("Sol canonique D13P11A", base), ("Sable et chemin générés référencés", floor),
              ("Falaises", cliffs), ("Piliers et blocs", pillars)]
    composed = Image.fromarray(base, "RGBA")
    for _, arr in layers[1:]:
        composed.alpha_composite(Image.fromarray(arr, "RGBA"))
    scene = np.asarray(composed, dtype=np.uint8)
    fidelity_data = fidelity(rgb, ref)
    if any(x["ecart_rgb_moyen"] >= 36 for x in fidelity_data.values()):
        raise AssertionError(f"Palette trop éloignée du rip: {fidelity_data}")

    shutil.rmtree(OUT / "maps", ignore_errors=True)
    map_dir = OUT / "maps" / "passage"
    for sub in ("calques", "masques", "review"):
        (map_dir / sub).mkdir(parents=True, exist_ok=True)
    for i, (name, arr) in enumerate(layers):
        Image.fromarray(arr, "RGBA").save(map_dir / "calques" / f"{PREFIX}_{i:02d}_{name.lower().replace(' ', '_').replace('/', '_')}.png", compress_level=9)
    Image.fromarray((rock*255).astype(np.uint8), "L").save(map_dir / "masques" / f"{PREFIX}_masque_roche.png", compress_level=9)
    Image.fromarray((~blocked_pixels*255).astype(np.uint8), "L").save(map_dir / "masques" / f"{PREFIX}_masque_praticable.png", compress_level=9)
    Image.fromarray(scene, "RGBA").save(map_dir / "review" / f"{PREFIX}_scene_t000.png", compress_level=9)
    overlay = Image.fromarray(scene, "RGBA")
    marks = Image.new("RGBA", (W, H), (0, 0, 0, 0)); draw = ImageDraw.Draw(marks)
    for y, x in zip(*np.nonzero(blocked)):
        draw.rectangle((x*TILE, y*TILE, x*TILE+7, y*TILE+7), fill=(220, 40, 40, 90))
    for name, (x, y) in markers.items():
        color = (255, 225, 40, 255) if name == "entrance" else (60, 220, 255, 255)
        draw.rectangle((x, y, x+15, y+15), outline=color, width=2)
    overlay.alpha_composite(marks)
    overlay.save(map_dir / "review" / f"{PREFIX}_collisions_marqueurs.png", compress_level=9)
    write_ora(map_dir / f"{PREFIX}_calques.ora", layers)

    gfx = loadmod("pmdo_codec_cpl1", ROOT / "source/pmdo_cote/build.py")
    tools = loadmod("pmdo_index_cpl1", ROOT / "source/pmdo_cote/INSTALLER.py")
    native = create_project(gfx, tools, layers, blocked, markers)

    manifest = {
        "lot": "defile_aiguilles_v1", "prefix_local": PREFIX, "title": TITLE,
        "source": {"guide": "generated with D13P11A as canonical texture reference", "guide_file": GUIDE.name,
                    "guide_sha256": sha256(GUIDE), "guide_size_px": list(guide.size), "prompt": PROMPT,
                    "canonical_reference": REF.name, "reference_sha256": sha256(REF),
                    "reference_size_px": [W, H], "reference_frames": 1,
                    "reference_rgb_colors": int(len(colors)),
                    "rom_extraction": {"repository": "pret/pmd-sky", "commit": "c8073235b39746a7ee74e6cea16c730bd91a1e67",
                                       "resources": ["files/MAP_BG/D13P11A.bma", "files/MAP_BG/D13P11A.bpc", "files/MAP_BG/D13P11A.bpl"],
                                       "renderer": "skytemple-files via source/outil_maps_pmdsky/recuperer_maps.py rom --only D13P11A",
                                       "index_entry": {"bg_list_index": 32, "frames": 1, "layers": 2, "collision": False, "palette_animation": False},
                                       "versioned_gif_pixel_identical_to_extracted_png": True},
                    "native_pixel_origin": "palette colors and base sand patch are exact D13P11A rip pixels; cliffs/layout are generated and quantized"},
        "map": {"size_px": [W, H], "grid_8px": [GRID, GRID], "tile_px": TILE,
                "layers": [name for name, _ in layers], "base_sand_patch_px": patch_box,
                "palette_fidelity": fidelity_data, "source_palette_exact": True},
        "collision": {"method": "seuil sur la palette de grès sombre + bords latéraux fermés; ouverture nord/sud; petit col de sable canonique ajouté sous la mesa pour relier les deux tronçons générés",
                      "blocked_cells": int(blocked.sum()), "walkable_cells": int((~blocked).sum()),
                      "markers_px": markers, "marker_adjustments_px": adjustments, "north_south_path_16x16": route_ok,
                      "connector": connector, "rock_components": components},
        "native": {"target": "PMDO 0.8.12", "namespace": NAMESPACE, "asset": ASSET, "tile_px": TILE,
                   "tile_banks": native["tile_banks"], "runtime_tested": False, "gpu_tested": False},
        "limitations": ["CPL1 est un code local, pas un ID ROM.",
                        "La composition est un rendu généré référencé, non une copie pixel-perfect du rip.",
                        "La quantification rend la palette exacte mais ne rend pas les dessins générés natifs.",
                        "Un court col de sable canonique est ajouté au sud-est de la mesa pour relier les deux tronçons générés; placement à valider artistiquement.",
                        "Les collisions, exits/warps, occlusion et gameplay demandent une revue dans PMDO."],
        "art_approved": False, "runtime_tested": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(make_readme(manifest), encoding="utf-8")
    (STAGE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_preview(layers, np.asarray(marks, dtype=np.uint8), markers)
    return manifest


def make_readme(m: dict) -> str:
    return f'''# Défilé des Aiguilles — CPL1 (code interne provisoire)

Carte carrée **456×456 px**, 57×57 cellules de 8 px, guidée par le fond D13P11A. Aperçu : [`apercu_defile_aiguilles_v1.html`](../../apercu_defile_aiguilles_v1.html). Source et méthode : [`source/defile_aiguilles_v1/README.md`](../../source/defile_aiguilles_v1/README.md).

- Référence originale : `{REF.name}` (rendu ROM 456×456 px, une frame, 30 couleurs RGB distinctes, pas d'animation palette selon `index_rom.json`).
- Composition : guide généré référencé sur D13P11A, réduit à la taille carrée de la référence; couleurs quantifiées sans tramage dans les 30 couleurs du rip.
- Les couleurs de sable, de grès et le patch de base viennent du rip; les formes générées restent des rendus référencés, **pas des tuiles originales**.
- Ground PMDO 0.8.12, calques séparés (base canonique, sable/chemin générés référencés, falaises, piliers), collisions et marqueurs de transit provisoires. Un col de sable de 22 px, texturé avec un patch du rip, relie les deux tronçons sous la mesa.
- Écart RGB moyen des matières au rip : sable {m['map']['palette_fidelity']['sable']['ecart_rgb_moyen']}, grès {m['map']['palette_fidelity']['gres']['ecart_rgb_moyen']}.

Packs produits après tests : `CPL1_projet_pmdo_0812.zip` et `CPL1_calques_png_8px.zip`; empreintes : `SHA256SUMS.json`. Aucun runtime PMDO, rendu GPU ou gameplay n'est revendiqué.
'''


if __name__ == "__main__":
    result = build()
    print(json.dumps({"prefix": result["prefix_local"], "markers": result["collision"]["markers_px"],
                      "path": result["collision"]["north_south_path_16x16"], "palette": result["map"]["palette_fidelity"],
                      "rock_cells": result["collision"]["blocked_cells"]}, ensure_ascii=False, indent=2))
