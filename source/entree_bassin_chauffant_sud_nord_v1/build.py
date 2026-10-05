#!/usr/bin/env python3
"""Pipeline : Entrée de donjon Bassin Chauffant sud -> nord (EBC1, 768x576, 4:3) —
méthode « textures canoniques » calée sur `bassinchauffantpmdsky.png` (P01P04A).

- Modèle de référence : `bassinchauffantpmdsky.png` (504x408, Bassin Chauffant / Hot Spring PMD Sky).
- Format final : 768x576 px (96x72 tuiles 8x8, ratio 4:3), boucle 240 ticks (4,0 s).
- Architecture de calques séparés (PNG 8 px + ORA + PMDO .rsground/.tile) :
  1. `eau_thermale`   (animé 4 x 10 ticks)  : eau thermale minérale dorée-ocre canonique (sans liseré blanc aux rives) + reflet de profondeur rocheux
  2. `remous`         (animé 4 x 12 ticks)  : ondulations concentriques chaudes à la surface des bassins
  3. `feuilles`       (animé 24 x 10 ticks) : feuilles vertes flottantes extraites de `poses_bassin_chauffant.png`
  4. `sol_complet`    (statique, masqué)    : tapis d'herbe forestière complet 768x576 sans vide
  5. `herbe`          (statique)            : herbe forestière vert profond et touffes d'herbe
  6. `chemin`         (statique)            : sentier de terre sableuse ocre et dalles de pierre plates
  7. `bordures`       (statique)            : lisières herbeuses claires et ombres de transition du sentier
  8. `rochers`        (statique)            : gros rochers bruns bordant les bassins, poteaux de bois sud et cheminées volcaniques
  9. `arbres`         (statique)            : troncs et feuillages forestiers encadrant la clairière et l'arche nord
  10. `profondeur`    (statique)            : ouverture caverneuse noire de l'arche de geyser au nord (sans eau devant)
  11. `vapeur`        (animé 24 x 10 ticks) : volutes de vapeur thermale chaude s'élevant des bassins et cheminées
  12. `brume_thermale`(animé 24 x 10 ticks) : fines gouttelettes et brume dorée chaude au-dessus de l'eau
  13. `canopee`       (statique, Top)       : cimes d'arbres en surplomb (calque Top PMDO)
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import uuid
import zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BRUTS = HERE / "bruts"
RENDERS = ROOT / "renders" / "entree_bassin_chauffant_sud_nord_v1"
CACHE = ROOT / ".cache" / "entree_bassin_chauffant_sud_nord_v1"
STAGE = CACHE / "entree_bassin_chauffant_sud_nord"

REF_PATH = ROOT / "bassinchauffantpmdsky.png"
W, H = 768, 576
TW, TH = 8, 8
GW, GH = W // TW, H // TH  # 96 x 72
PREFIX = "EBC1"
NAMESPACE = "entree_bassin_chauffant_sud_nord"
ASSET = "ebc1_entree_bassin_chauffant"
LOOP_TICKS = 240  # 24 * 10 = 240 ticks (4.0 s @ 60 fps)


def loadmod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def down_class(src: np.ndarray, h: int = H, w: int = W) -> np.ndarray:
    sh, sw = src.shape[:2]
    ys = ((np.arange(h) + 0.5) * sh / h).astype(int).clip(0, sh - 1)
    xs = ((np.arange(w) + 0.5) * sw / w).astype(int).clip(0, sw - 1)
    return src[np.ix_(ys, xs)].copy()


def quantize_step(rgb: np.ndarray, step: int = 8) -> np.ndarray:
    return ((rgb.astype(np.int32) + step // 2) // step * step).clip(0, 248).astype(np.uint8)


def _extract_poses() -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Extrait les 6 poses de feuilles flottantes (ligne 1) et 6 poses de vapeur (ligne 2)."""
    im = Image.open(BRUTS / "poses_bassin_chauffant.png").convert("RGBA")
    a = np.asarray(im).astype(np.int32)
    r, g, b, _ = a.transpose(2, 0, 1)
    mag = (r > 175) & (b > 175) & (g < 115)
    halo = ~mag & (r > g + 35) & (b > g + 35)
    fg = ~mag & ~halo

    rgba = np.zeros_like(a, dtype=np.uint8)
    rgba[..., :3] = quantize_step(a[..., :3].astype(np.uint8), 8)
    rgba[fg, 3] = 255

    # Ligne du haut : feuilles vertes (y < 460)
    fg_top = fg.copy()
    fg_top[460:, :] = False
    lbl_t, n_t = ndi.label(ndi.binary_dilation(fg_top, iterations=4))
    boxes_t = []
    for i in range(1, n_t + 1):
        m = (lbl_t == i) & fg_top
        if int(m.sum()) < 80:
            continue
        yy, xx = np.where(m)
        boxes_t.append((float(xx.mean()), int(yy.min()), int(yy.max()) + 1, int(xx.min()), int(xx.max()) + 1))
    boxes_t.sort(key=lambda x: x[0])

    leaves: list[np.ndarray] = []
    for _, y0, y1, x0, x1 in boxes_t[:6]:
        crop = rgba[y0:y1, x0:x1].copy()
        pil = Image.fromarray(crop, "RGBA").resize((12, 10), Image.NEAREST)
        arr = np.asarray(pil).copy()
        alpha = arr[..., 3] > 128
        shadow = np.roll(alpha, 1, axis=0) & ~alpha
        arr[shadow] = (143, 119, 31, 220)
        leaves.append(arr)

    # Ligne du bas : vapeur thermale (y >= 460)
    fg_bot = fg.copy()
    fg_bot[:460, :] = False
    lbl_b, n_b = ndi.label(ndi.binary_dilation(fg_bot, iterations=12))
    boxes_b = []
    for i in range(1, n_b + 1):
        m = (lbl_b == i) & fg_bot
        if int(m.sum()) < 80:
            continue
        yy, xx = np.where(m)
        boxes_b.append((float(xx.mean()), int(yy.min()), int(yy.max()) + 1, int(xx.min()), int(xx.max()) + 1))
    boxes_b.sort(key=lambda x: x[0])

    steams: list[np.ndarray] = []
    target_sizes = [(12, 12), (16, 18), (22, 22), (24, 22), (18, 24), (10, 14)]
    for idx, (_, y0, y1, x0, x1) in enumerate(boxes_b[:6]):
        crop = rgba[y0:y1, x0:x1].copy()
        tw, th = target_sizes[idx % len(target_sizes)]
        pil = Image.fromarray(crop, "RGBA").resize((tw, th), Image.NEAREST)
        arr = np.asarray(pil).copy()
        m_a = arr[..., 3] > 0
        lum = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
        edge = m_a & ~ndi.binary_erosion(m_a, iterations=1)
        arr[m_a, 3] = np.clip(lum[m_a] * 0.85, 130, 215).astype(np.uint8)
        arr[edge, 3] = 115
        steams.append(arr)

    return leaves, steams


def segment_layers() -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], np.ndarray]:
    raw_rgb = np.asarray(Image.open(BRUTS / "decor_magenta.png").convert("RGB"))
    rgb = quantize_step(down_class(raw_rgb, H, W), 8)
    r, g, b = rgb.transpose(2, 0, 1).astype(np.int32)
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    # 0. Nettoyer intégralement les 4 petits panaches de vapeur statiques sur les cheminées (y in [205..335])
    mag_raw = (r > 175) & (b > 175) & (g < 115)
    yy0, xx0 = np.mgrid[0:H, 0:W]
    chimney_steam_zone = (yy0 >= 205) & (yy0 <= 338) & (((xx0 >= 58) & (xx0 <= 192)) | ((xx0 >= 618) & (xx0 <= 718)))
    # Dans cette zone, tout pixel désaturé/gris-bleuté/blanchâtre (qui n'est ni herbe franche g > r+15 ni rocher brun franc r > b+28)
    static_steam = ~mag_raw & chimney_steam_zone & ((np.abs(r - g) < 28) & (b > 88) & ~((r > b + 30) & (r > g + 14)))
    static_steam = ndi.binary_dilation(static_steam, iterations=2) & ~mag_raw & chimney_steam_zone
    if static_steam.any():
        _, (iy, ix) = ndi.distance_transform_edt(static_steam | mag_raw, return_indices=True)
        rgb[static_steam] = rgb[iy[static_steam], ix[static_steam]]
        r, g, b = rgb.transpose(2, 0, 1).astype(np.int32)
        lum = 0.299 * r + 0.587 * g + 0.114 * b

    # 1. Bassins d'eau thermale (fond magenta #FF00FF + décontaminations de frange)
    mag_seed = (r > 175) & (b > 175) & (g < 115)
    mag_fringe = (r > g + 35) & (b > g + 35) & (b > 110)
    pool_mask = ndi.binary_propagation(mag_seed, mask=(mag_seed | mag_fringe))
    pool_mask = ndi.binary_fill_holes(pool_mask)

    # Pas de petits traits blancs au bord des rives
    near_pool = ndi.binary_dilation(pool_mask, iterations=2) & ~pool_mask
    white_lip = near_pool & (lum > 185) & (np.abs(r - g) < 22)
    if white_lip.any():
        _, (iy, ix) = ndi.distance_transform_edt(white_lip | pool_mask, return_indices=True)
        rgb[white_lip] = rgb[iy[white_lip], ix[white_lip]]
        r, g, b = rgb.transpose(2, 0, 1).astype(np.int32)
        lum = 0.299 * r + 0.587 * g + 0.114 * b

    # 2. Ouverture caverneuse noire au nord (arche de geyser, x=350..420, y=95..160)
    dark_seed = ~pool_mask & (lum < 34)
    dark_seed[168:, :] = False
    dark_seed[:, :340] = False
    dark_seed[:, 428:] = False
    profondeur_mask = ndi.binary_dilation(dark_seed, iterations=2) & ~pool_mask

    fg = ~pool_mask & ~profondeur_mask

    # 3. Verdure vs Chemin sableux vs Rochers/Cheminées/Bois
    verdure_mask = fg & (g > r + 12) & (g > b + 16)

    yy, xx = np.mgrid[0:H, 0:W]
    in_corridor = (xx >= 285) & (xx <= 485) & (yy >= 145)
    chemin_mask = fg & ~verdure_mask & in_corridor & (r > 165) & (g > 125) & (r > b + 35)
    fence_posts = in_corridor & (yy >= 425) & ((xx < 348) | (xx > 422)) & ~verdure_mask & (lum < 168)
    chemin_mask = chemin_mask & ~fence_posts
    chemin_mask = ndi.binary_closing(chemin_mask, iterations=1) & fg & ~verdure_mask & ~fence_posts

    near_chemin = ndi.binary_dilation(chemin_mask, iterations=6) & fg & ~chemin_mask
    bordures_mask = near_chemin & verdure_mask & (yy >= 145)

    near_pools_rock = ndi.binary_dilation(pool_mask, iterations=28) & (yy >= 245) & (yy <= 435)
    geyser_arch_zone = (yy >= 22) & (yy <= 185) & (xx >= 255) & (xx <= 518)
    rock_boulders_side = (
        (yy >= 120) & (yy <= 245) & ((xx <= 210) | (xx >= 555)) & ~verdure_mask & (r > g + 14) & (lum > 85)
    )

    rochers_mask = fg & ~verdure_mask & ~chemin_mask & (
        near_pools_rock | geyser_arch_zone | fence_posts | rock_boulders_side
    )

    tree_trunks = fg & ~verdure_mask & ~chemin_mask & ~rochers_mask
    bright_canopy = verdure_mask & ((g > 132) | (lum < 64))
    tree_zone = (
        (yy < 245)
        | ((yy > 405) & ((xx < 295) | (xx > 475)))
        | ((yy >= 150) & (yy <= 310) & ((xx < 355) | (xx > 415)))
    )
    canopy_foliage = verdure_mask & ~bordures_mask & tree_zone & ndi.binary_dilation(bright_canopy | tree_trunks, iterations=4)
    arbres_mask = (tree_trunks | canopy_foliage) & fg & ~chemin_mask & ~rochers_mask & ~bordures_mask

    herbe_mask = fg & ~chemin_mask & ~bordures_mask & ~rochers_mask & ~arbres_mask
    canopee_top_mask = arbres_mask & (yy < 195) & (g > r + 15) & (lum > 75)

    raw_sol = np.asarray(Image.open(BRUTS / "sol_complet.png").convert("RGB"))
    sol_rgb = down_class(raw_sol, H, W).astype(np.int32)
    sol_shift = np.clip(sol_rgb + np.array([26, 20, 6], dtype=np.int32), 0, 248).astype(np.uint8)
    sol_rgb_q = quantize_step(sol_shift, 8)
    sol_complet = np.dstack([sol_rgb_q, np.full((H, W), 255, dtype=np.uint8)])

    def to_rgba(m: np.ndarray) -> np.ndarray:
        out = np.zeros((H, W, 4), dtype=np.uint8)
        out[m, :3] = rgb[m]
        out[m, 3] = 255
        return out

    layers = {
        "sol_complet": sol_complet,
        "herbe": to_rgba(herbe_mask),
        "chemin": to_rgba(chemin_mask),
        "bordures": to_rgba(bordures_mask),
        "rochers": to_rgba(rochers_mask),
        "arbres": to_rgba(arbres_mask),
        "profondeur": to_rgba(profondeur_mask),
        "canopee": to_rgba(canopee_top_mask),
    }
    masks = {
        "pool": pool_mask,
        "herbe": herbe_mask,
        "chemin": chemin_mask,
        "bordures": bordures_mask,
        "rochers": rochers_mask,
        "arbres": arbres_mask,
        "profondeur": profondeur_mask,
    }
    return layers, masks, rgb


def _canonical_water_patch() -> np.ndarray:
    """Extrait le patch 96x128 d'eau thermale canonique directement depuis `bassinchauffantpmdsky.png`."""
    ref = np.asarray(Image.open(REF_PATH).convert("RGB")).astype(np.int32)
    patch = ref[176:272, 200:328].copy()
    r, g, b = patch.transpose(2, 0, 1)
    non_water = ~((r > 165) & (g > 140) & (b < 90) & (r > g + 15))
    if non_water.any():
        _, (iy, ix) = ndi.distance_transform_edt(non_water, return_indices=True)
        patch[non_water] = patch[iy[non_water], ix[non_water]]
    # Rendre le patch pavable sans couture par miroir 2x2
    top = np.concatenate([patch, patch[:, ::-1, :]], axis=1)
    full = np.concatenate([top, top[::-1, :, :]], axis=0)
    return full.astype(np.uint8)


def build_thermal_water_frames(
    pool_mask: np.ndarray,
    rochers_rgba: np.ndarray,
    n_frames: int = 4,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    dist = ndi.distance_transform_edt(pool_mask)
    yy, xx = np.mgrid[0:H, 0:W]
    canon_tile = _canonical_water_patch()
    th, tw = canon_tile.shape[:2]

    rock_alpha = rochers_rgba[..., 3] > 0
    submerged_rock_ref = np.zeros((H, W), dtype=bool)
    for dy in range(1, 14):
        shifted = np.roll(rock_alpha, dy, axis=0)
        shifted[:dy, :] = False
        submerged_rock_ref |= shifted & pool_mask & (dist >= 2) & (dist <= 14)

    c_left = (166.0, 342.0)
    c_right = (602.0, 342.0)
    rad_l = np.hypot(xx - c_left[0], (yy - c_left[1]) * 1.25)
    rad_r = np.hypot(xx - c_right[0], (yy - c_right[1]) * 1.25)
    rad = np.minimum(rad_l, rad_r)

    eau_frames: list[np.ndarray] = []
    remous_frames: list[np.ndarray] = []

    shifts = [(0, 0), (3, 1), (6, 2), (3, 3)]
    for f in range(n_frames):
        sx, sy = shifts[f % len(shifts)]
        tiled_rgb = canon_tile[(yy + sy) % th, (xx + sx) % tw]
        eau = np.zeros((H, W, 4), dtype=np.uint8)
        eau[pool_mask, :3] = tiled_rgb[pool_mask]
        eau[pool_mask, 3] = 255

        # Reflet de profondeur des rochers immergés au bord nord des bassins
        dither = (xx + yy + f) % 2 == 0
        eau[submerged_rock_ref & (dist <= 8)] = (159, 135, 39, 255)
        eau[submerged_rock_ref & (dist > 8) & dither] = (175, 151, 47, 255)

        # Dégradé de rive minéral sombre (aucun trait blanc au bord des rives !)
        eau[pool_mask & (dist <= 6) & dither] = (183, 159, 55, 255)
        eau[pool_mask & (dist <= 3)] = (175, 159, 39, 255)
        eau[pool_mask & (dist <= 1.5)] = (167, 143, 39, 255)
        eau_frames.append(eau)

        rem = np.zeros((H, W, 4), dtype=np.uint8)
        ring1 = pool_mask & (dist > 10) & (np.abs(np.sin(rad * 0.24 - f * 1.57)) > 0.94) & (((xx + yy) % 2) == 0)
        ring2 = pool_mask & (dist > 16) & (np.abs(np.cos(rad * 0.17 - f * 1.57)) > 0.95) & (((xx + yy) % 3) == 0)
        rem[ring1] = (207, 183, 87, 210)
        rem[ring2] = (215, 191, 95, 225)
        remous_frames.append(rem)

    return eau_frames, remous_frames


def build_leaves_and_steam_frames(
    pool_mask: np.ndarray,
    leaves_poses: list[np.ndarray],
    steam_poses: list[np.ndarray],
    n_frames: int = 24,
) -> tuple[list[np.ndarray], list[np.ndarray], list[np.ndarray]]:
    leaf_anchors = [
        (134, 326, 0), (186, 354, 2), (154, 374, 4), (212, 332, 1),
        (566, 330, 3), (618, 358, 5), (584, 376, 1), (642, 336, 4),
    ]
    steam_vents = [
        (92, 286, 0, True), (144, 266, 6, True),
        (652, 262, 12, True), (684, 286, 18, True),
        (124, 328, 3, False), (178, 344, 11, False), (218, 366, 19, False),
        (558, 342, 7, False), (612, 328, 15, False), (648, 366, 21, False),
        (294, 142, 4, True), (476, 146, 16, True),
    ]

    feuilles_frames: list[np.ndarray] = []
    vapeur_frames: list[np.ndarray] = []
    brume_frames: list[np.ndarray] = []

    for f in range(n_frames):
        ang = 2.0 * np.pi * f / n_frames
        fl_canvas = np.zeros((H, W, 4), dtype=np.uint8)
        vp_canvas = np.zeros((H, W, 4), dtype=np.uint8)
        br_canvas = np.zeros((H, W, 4), dtype=np.uint8)

        for ax, ay, p0 in leaf_anchors:
            pose_idx = (p0 + (f // 4)) % len(leaves_poses)
            spr = leaves_poses[pose_idx]
            sh, sw = spr.shape[:2]
            dx = int(round(1.6 * np.sin(ang + p0)))
            dy = int(round(1.2 * np.cos(ang + p0 * 0.7)))
            x0 = ax + dx - sw // 2
            y0 = ay + dy - sh // 2
            for sy in range(sh):
                yy = y0 + sy
                if yy < 0 or yy >= H:
                    continue
                for sx in range(sw):
                    xx = x0 + sx
                    if xx < 0 or xx >= W:
                        continue
                    if spr[sy, sx, 3] > 0 and pool_mask[yy, xx]:
                        fl_canvas[yy, xx] = spr[sy, sx]

        for vx, vy, offset, is_chimney in steam_vents:
            local_f = (f + offset) % n_frames
            pose_idx = min(len(steam_poses) - 1, (local_f * len(steam_poses)) // n_frames)
            spr = steam_poses[pose_idx]
            sh, sw = spr.shape[:2]
            rise = int(round((local_f / n_frames) * (22 if is_chimney else 16)))
            sway = int(round(2.0 * np.sin(2.0 * np.pi * local_f / n_frames + offset)))
            x0 = vx + sway - sw // 2
            y0 = vy - rise - sh // 2
            fade = 1.0
            if local_f < 3:
                fade = (local_f + 1) / 4.0
            elif local_f > n_frames - 5:
                fade = (n_frames - local_f) / 5.0
            for sy in range(sh):
                yy = y0 + sy
                if yy < 0 or yy >= H:
                    continue
                for sx in range(sw):
                    xx = x0 + sx
                    if xx < 0 or xx >= W:
                        continue
                    sa = int(spr[sy, sx, 3] * fade)
                    if sa > 20 and sa >= vp_canvas[yy, xx, 3]:
                        vp_canvas[yy, xx, :3] = spr[sy, sx, :3]
                        vp_canvas[yy, xx, 3] = sa

        rng = np.random.RandomState(20261004)
        for i in range(28):
            side = i % 2
            bx = (115 + rng.randint(0, 115)) if side == 0 else (545 + rng.randint(0, 115))
            by = 298 + rng.randint(0, 88)
            ph = (f + i * 3) % n_frames
            ry = by - int((ph * 10) // n_frames)
            rx = bx + int(round(1.5 * np.sin(2.0 * np.pi * ph / n_frames + i)))
            if 0 <= ry < H and 0 <= rx < W and pool_mask[min(H - 1, ry + 4), rx]:
                if ph % 6 in (1, 2, 3):
                    br_canvas[ry, rx] = (248, 240, 200, 210)
                    if rx + 1 < W:
                        br_canvas[ry, rx + 1] = (232, 216, 160, 165)

        feuilles_frames.append(fl_canvas)
        vapeur_frames.append(vp_canvas)
        brume_frames.append(br_canvas)

    return feuilles_frames, vapeur_frames, brume_frames


def alpha_over(dst: np.ndarray, src: np.ndarray) -> np.ndarray:
    out = dst.copy()
    sa = src[..., 3:4].astype(np.float32) / 255.0
    da = out[..., 3:4].astype(np.float32) / 255.0
    out_a = sa + da * (1.0 - sa)
    safe = np.where(out_a > 1e-6, out_a, 1.0)
    out_rgb = (src[..., :3].astype(np.float32) * sa + out[..., :3].astype(np.float32) * da * (1.0 - sa)) / safe
    out[..., :3] = np.clip(np.round(out_rgb), 0, 255).astype(np.uint8)
    out[..., 3:4] = np.clip(np.round(out_a * 255.0), 0, 255).astype(np.uint8)
    return out


def compose_tick(
    tick: int,
    static_layers: dict[str, np.ndarray],
    eau_frames: list[np.ndarray],
    remous_frames: list[np.ndarray],
    feuilles_frames: list[np.ndarray],
    vapeur_frames: list[np.ndarray],
    brume_frames: list[np.ndarray],
) -> np.ndarray:
    canvas = static_layers["sol_complet"].copy()
    for k in ("herbe", "bordures", "chemin"):
        canvas = alpha_over(canvas, static_layers[k])
    canvas = alpha_over(canvas, eau_frames[(tick // 10) % len(eau_frames)])
    canvas = alpha_over(canvas, remous_frames[(tick // 12) % len(remous_frames)])
    canvas = alpha_over(canvas, feuilles_frames[(tick // 10) % len(feuilles_frames)])
    for k in ("rochers", "arbres", "profondeur"):
        canvas = alpha_over(canvas, static_layers[k])
    canvas = alpha_over(canvas, brume_frames[(tick // 10) % len(brume_frames)])
    canvas = alpha_over(canvas, vapeur_frames[(tick // 10) % len(vapeur_frames)])
    canvas = alpha_over(canvas, static_layers["canopee"])
    return canvas


def build_collision_grid() -> np.ndarray:
    grid = np.ones((GH, GW), dtype=np.uint8)
    for gy in range(14, GH):
        y_px = gy * TW + 4
        half_w = 40 if y_px < 430 else 36
        for gx in range(GW):
            x_px = gx * TW + 4
            if abs(x_px - 384) <= half_w:
                grid[gy, gx] = 0
    return grid


def measure_fidelity(rgb: np.ndarray) -> dict[str, dict[str, object]]:
    ref = np.asarray(Image.open(REF_PATH).convert("RGB")).astype(np.int32)

    def mats(a: np.ndarray) -> dict[str, np.ndarray]:
        r, g, b = a.transpose(2, 0, 1)
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        mag = (r > 180) & (b > 180) & (g < 110)
        sky = (b > 180) & (b > r + 25) & ~mag
        dark = (lum < 32) & ~mag
        pool_w = (r > 165) & (g > 140) & (b < 88) & (r - g >= 18) & ~mag
        fg = ~mag & ~sky & ~dark & ~pool_w
        verdure = fg & (g > r + 15) & (g > b + 20)
        chemin = fg & ~verdure & (r > 195) & (g > 155) & (b >= 92) & (g - b >= 35)
        rochers = fg & ~verdure & ~chemin & (r > g + 12) & (r > b + 25) & (lum >= 55) & (lum <= 200)
        return {"verdure": verdure, "chemin": chemin, "rochers": rochers}

    mr = mats(ref)
    md = mats(rgb.astype(np.int32))
    out: dict[str, dict[str, object]] = {}
    for k in ("verdure", "chemin", "rochers"):
        cr = ref[mr[k]].mean(0)
        cd = rgb[md[k]].mean(0)
        dist = float(np.linalg.norm(cr - cd))
        out[k] = {
            "rip_mean_rgb": [round(float(x), 1) for x in cr],
            "map_mean_rgb": [round(float(x), 1) for x in cd],
            "rgb_distance": round(dist, 2),
        }
    return out


def write_ora(
    ora_path: Path,
    static_layers: dict[str, np.ndarray],
    eau_frames: list[np.ndarray],
    remous_frames: list[np.ndarray],
    feuilles_frames: list[np.ndarray],
    vapeur_frames: list[np.ndarray],
    brume_frames: list[np.ndarray],
    merged_rgba: np.ndarray,
) -> None:
    ora_layers = [
        ("canopee_top", static_layers["canopee"], True),
        ("vapeur_f00", vapeur_frames[0], True),
        ("brume_thermale_f00", brume_frames[0], True),
        ("profondeur", static_layers["profondeur"], True),
        ("arbres", static_layers["arbres"], True),
        ("rochers", static_layers["rochers"], True),
        ("feuilles_f00", feuilles_frames[0], True),
        ("remous_f00", remous_frames[0], True),
        ("eau_thermale_f00", eau_frames[0], True),
        ("chemin", static_layers["chemin"], True),
        ("bordures", static_layers["bordures"], True),
        ("herbe", static_layers["herbe"], True),
        ("sol_complet", static_layers["sol_complet"], False),
    ]
    with zipfile.ZipFile(ora_path, "w") as zf:
        zf.writestr("mimetype", "image/openraster", compress_type=zipfile.ZIP_STORED)
        stack_xml = ['<?xml version="1.0" encoding="UTF-8"?>', f'<image version="0.0.1" w="{W}" h="{H}">', "  <stack>"]
        for name, arr, vis in ora_layers:
            vis_str = "visible" if vis else "hidden"
            p = f"data/{name}.png"
            stack_xml.append(f'    <layer name="{name}" src="{p}" x="0" y="0" opacity="1.0" visibility="{vis_str}"/>')
            bio_path = CACHE / f"_ora_{name}.png"
            Image.fromarray(arr, "RGBA").save(bio_path)
            zf.write(bio_path, p, compress_type=zipfile.ZIP_DEFLATED)
            bio_path.unlink(missing_ok=True)
        stack_xml.extend(["  </stack>", "</image>"])
        zf.writestr("stack.xml", "\n".join(stack_xml), compress_type=zipfile.ZIP_DEFLATED)

        m_path = CACHE / "_ora_merged.png"
        t_path = CACHE / "_ora_thumb.png"
        Image.fromarray(merged_rgba, "RGBA").save(m_path)
        Image.fromarray(merged_rgba, "RGBA").resize((256, 192), Image.NEAREST).save(t_path)
        zf.write(m_path, "mergedimage.png", compress_type=zipfile.ZIP_DEFLATED)
        zf.write(t_path, "Thumbnails/thumbnail.png", compress_type=zipfile.ZIP_DEFLATED)
        m_path.unlink(missing_ok=True)
        t_path.unlink(missing_ok=True)


def build_pmdo_ground_project(
    stack: list[tuple[str, list[np.ndarray], int, int]],
    blocked: np.ndarray,
    entry_px: list[int],
    threshold_px: list[int],
    gfx,
    tools,
) -> dict[str, int]:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    with zipfile.ZipFile(ROOT / "mod_metano_expeditions_pmdo_0812.zip") as z:
        tpl = json.loads(z.read("metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground"))
    o = tpl["Object"]
    gw, gh = W // 8, H // 8
    layers, banks = [], []
    for i, (title, frames, ticks, draw_layer) in enumerate(stack):
        bank = gfx.TileBank(f"{PREFIX}_{i:02d}_{title.split()[0].upper()}")
        bank.ids[bytes(256)] = (0, 0)
        bank.data[(0, 0)] = bytes(256)
        f_has = [a[..., 3].reshape(gh, 8, gw, 8).any(axis=(1, 3)) for a in frames]
        any_cell = np.any(f_has, axis=0)
        empty_ref = {"Sheet": bank.name, "TexLoc": {"X": 0, "Y": 0}}

        def cell(x, y, frames=frames, bank=bank, f_has=f_has, any_cell=any_cell, empty_ref=empty_ref):
            if not any_cell[y, x]:
                return []
            if len(frames) == 1:
                f = bank.add(Image.fromarray(frames[0][y * 8 : y * 8 + 8, x * 8 : x * 8 + 8]), x, y)
                return [f] if f else []
            p0 = frames[0][y * 8 : y * 8 + 8, x * 8 : x * 8 + 8]
            if all(np.array_equal(a[y * 8 : y * 8 + 8, x * 8 : x * 8 + 8], p0) for a in frames[1:]):
                f = bank.add(Image.fromarray(p0), x, y)
                return [f] if f else []
            fs = []
            for t_i, a in enumerate(frames):
                if not f_has[t_i][y, x]:
                    fs.append(empty_ref)
                else:
                    f = bank.add(Image.fromarray(a[y * 8 : y * 8 + 8, x * 8 : x * 8 + 8]), x, y)
                    fs.append(f if f else empty_ref)
            return [fs[0]] if all(f == fs[0] for f in fs) else fs

        layers.append(gfx.layer(f"{i:02d} {title}", gw, gh, cell, ticks, draw=draw_layer))
        banks.append(bank)
    for bank in banks:
        bank.write(STAGE / f"Content/Tile/{bank.name}.tile")
    o.update(
        Name={"DefaultText": "Entree Bassin Chauffant - sud vers nord (4:3)", "LocalTexts": {}},
        AssetName=ASSET,
        Released=False,
        TexSize=1,
        Music="",
        EdgeView=1,
        ViewCenter=None,
        ViewOffset={"X": 0, "Y": 0},
        ActiveChar=None,
        Status={},
        Layers=layers,
        Background={"$type": "RogueEssence.Dungeon.LayeredBG, RogueEssence", "Layers": []},
        Comment="PMDO 0.8.12. Rendu 4:3 reference sur Hot Spring / Bassin Chauffant (P01P04A, bassinchauffantpmdsky.png).",
    )
    o["obstacles"] = [
        [{"Bounds": {"X": x * 8, "Y": y * 8, "Width": 8, "Height": 8}, "Tags": int(blocked[y, x])} for y in range(gh)]
        for x in range(gw)
    ]
    mk = lambda n, p: {
        "EntName": n,
        "Direction": 4,
        "EntEnabled": True,
        "triggerType": 0,
        "Collider": {"X": p[0], "Y": p[1], "Width": 16, "Height": 16},
    }
    o["Entities"] = [
        {
            "Name": "Entrees et vos acteurs",
            "Visible": True,
            "MapChars": [],
            "GroundObjects": [],
            "Spawners": [],
            "Markers": [mk("entrance", entry_px), mk("donjon_seuil", threshold_px)],
        }
    ]
    o["Decorations"] = [{"Name": "Vos decorations", "Layer": 2, "Visible": True, "Anims": []}]
    tpl["Version"] = "0.8.12.0"
    gfx.save(STAGE / f"Data/Ground/{ASSET}.rsground", json.dumps(tpl, ensure_ascii=False, separators=(",", ":")).encode())
    gfx.save(
        STAGE / f"Data/Script/{NAMESPACE}/ground/{ASSET}/init.lua",
        f"-- {ASSET} : base d edition, aucun warp.\nlocal {ASSET} = {{}}\nreturn {ASSET}\n".encode(),
    )
    nodes = {}
    for p in sorted((STAGE / "Content/Tile").glob("*.tile")):
        with p.open("rb") as f:
            nodes[p.stem] = tools.read_node(f)
    (STAGE / "Content/Tile/index.idx").write_bytes(tools.encode_index(nodes))
    ident = uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/meromoonmeri/guilde-treehouse-pmd/" + NAMESPACE)
    (STAGE / "Mod.xml").write_text(
        f"""<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Entree Bassin Chauffant 4:3 - Atelier 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Projet d'edition : entree de donjon du Bassin Chauffant (P01P04A) au format 4:3 (768x576), eau thermale minerale doree, feuilles flottantes et vapeur.</Description>
  <Namespace>{NAMESPACE}</Namespace>
  <UUID>{ident}</UUID>
  <Version>1.0.0.0</Version>
  <GameVersion>0.8.12.0</GameVersion>
  <ModType>Quest</ModType>
  <Relationships />
</Header>
"""
    )
    script = (ROOT / "source/pmdo_cote/INSTALLER.py").read_text()
    needle = "            relative = src.relative_to(source)\n"
    if needle in script:
        script = script.replace(needle, needle + "            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n")
    (STAGE / "INSTALLER.py").write_text(script)
    return {b.name: len(b.data) for b in banks}


def write_viewer_html(html_path: Path, manifest: dict[str, object]) -> None:
    rel = "renders/entree_bassin_chauffant_sud_nord_v1"
    frames_js = json.dumps([f"{rel}/{PREFIX}_scene_t{t:03d}.png" for t in range(0, LOOP_TICKS, 10)])
    layers_js = json.dumps(
        [
            {"id": "eau_thermale", "label": "1. Eau thermale (4×10t)", "src": f"{rel}/anim/{PREFIX}_01_eau_thermale_f00.png"},
            {"id": "remous", "label": "2. Remous (4×12t)", "src": f"{rel}/anim/{PREFIX}_02_remous_f00.png"},
            {"id": "feuilles", "label": "3. Feuilles flottantes (24×10t)", "src": f"{rel}/anim/{PREFIX}_03_feuilles_f00.png"},
            {"id": "herbe", "label": "5. Herbe forestière", "src": f"{rel}/layers/{PREFIX}_05_herbe.png"},
            {"id": "chemin", "label": "6. Sentier sableux & dalles", "src": f"{rel}/layers/{PREFIX}_06_chemin.png"},
            {"id": "bordures", "label": "7. Bordures herbeuses", "src": f"{rel}/layers/{PREFIX}_07_bordures.png"},
            {"id": "rochers", "label": "8. Rochers & cheminées", "src": f"{rel}/layers/{PREFIX}_08_rochers.png"},
            {"id": "arbres", "label": "9. Arbres & sous-bois", "src": f"{rel}/layers/{PREFIX}_09_arbres.png"},
            {"id": "profondeur", "label": "10. Seuil caverne geyser", "src": f"{rel}/layers/{PREFIX}_10_profondeur.png"},
            {"id": "vapeur", "label": "11. Vapeur thermale (24×10t)", "src": f"{rel}/anim/{PREFIX}_11_vapeur_f00.png"},
            {"id": "brume_thermale", "label": "12. Brume chaude (24×10t)", "src": f"{rel}/anim/{PREFIX}_12_brume_thermale_f00.png"},
            {"id": "canopee", "label": "13. Canopée (Top)", "src": f"{rel}/layers/{PREFIX}_13_canopee.png"},
        ]
    )
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Aperçu {PREFIX} — Entrée Bassin Chauffant (768×576, 4:3)</title>
<style>
  body {{ background:#111318; color:#e9ecf2; font-family:system-ui,sans-serif; margin:0; padding:20px; }}
  h1 {{ margin:0 0 6px; font-size:20px; color:#ffd479; }}
  .meta {{ color:#9aa4b8; font-size:13px; margin-bottom:14px; }}
  .toolbar {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:14px; }}
  button, label {{ background:#1e232d; color:#e9ecf2; border:1px solid #343d4f; border-radius:6px; padding:6px 12px; font-size:13px; cursor:pointer; }}
  .stage-wrap {{ display:flex; gap:18px; flex-wrap:wrap; align-items:flex-start; }}
  .stage {{ position:relative; width:768px; height:576px; border:2px solid #3a4254; background:#000; image-rendering:pixelated; overflow:hidden; }}
  .stage img {{ position:absolute; inset:0; width:768px; height:576px; image-rendering:pixelated; }}
  .panel {{ background:#181c24; border:1px solid #2d3546; border-radius:8px; padding:12px; max-width:360px; font-size:13px; }}
  .layer-list {{ display:grid; grid-template-columns:1fr; gap:5px; margin-top:8px; }}
</style>
</head>
<body>
  <h1>Entrée Bassin Chauffant sud → nord ({PREFIX}) — 768×576 (4:3, 96×72 tuiles 8×8)</h1>
  <div class="meta">Référence canonique : <code>bassinchauffantpmdsky.png</code> (P01P04A) · Boucle 240 ticks (4,0 s) · Eau thermale minérale dorée, feuilles flottantes & vapeur</div>
  <div class="toolbar">
    <button id="playBtn">⏸ Pause</button>
    <label><input type="checkbox" id="walkToggle"> Walkability / Marqueurs</label>
    <span id="tickInfo">Tick 000 / 240</span>
  </div>
  <div class="stage-wrap">
    <div class="stage">
      <img id="sceneImg" src="{rel}/{PREFIX}_scene_t000.png" alt="scene">
      <img id="walkImg" src="{rel}/{PREFIX}_walkability.png" alt="walk" style="display:none; opacity:0.65;">
    </div>
    <div class="panel">
      <strong>Calques séparés (PNG 8 px / ORA / PMDO)</strong>
      <div class="layer-list" id="layerList"></div>
      <hr style="border-color:#2d3546; margin:12px 0;">
      <div><strong>Fidélité RGB vs rip :</strong><br>
        Verdure : {manifest["fidelity"]["verdure"]["rgb_distance"]} px<br>
        Chemin : {manifest["fidelity"]["chemin"]["rgb_distance"]} px<br>
        Rochers : {manifest["fidelity"]["rochers"]["rgb_distance"]} px
      </div>
    </div>
  </div>
<script>
const frames = {frames_js};
const layers = {layers_js};
let idx = 0, playing = true;
const sceneImg = document.getElementById('sceneImg');
const walkImg = document.getElementById('walkImg');
const tickInfo = document.getElementById('tickInfo');
setInterval(() => {{
  if (!playing) return;
  idx = (idx + 1) % frames.length;
  sceneImg.src = frames[idx];
  tickInfo.textContent = `Tick ${{String(idx*10).padStart(3,'0')}} / 240`;
}}, 166);
document.getElementById('playBtn').onclick = (e) => {{
  playing = !playing;
  e.target.textContent = playing ? '⏸ Pause' : '▶ Lecture';
}};
document.getElementById('walkToggle').onchange = (e) => {{
  walkImg.style.display = e.target.checked ? 'block' : 'none';
}};
const list = document.getElementById('layerList');
layers.forEach(l => {{
  const a = document.createElement('a');
  a.href = l.src; a.target = '_blank'; a.style.color = '#9ecbff';
  a.textContent = l.label;
  list.appendChild(a);
}});
</script>
</body>
</html>"""
    html_path.write_text(html, encoding="utf-8")


def main() -> None:
    gfx = loadmod("pmdo_codec", ROOT / "source/pmdo_cote/build.py")
    tools = loadmod("index_tools", ROOT / "source/pmdo_cote/INSTALLER.py")

    RENDERS.mkdir(parents=True, exist_ok=True)
    (RENDERS / "layers").mkdir(parents=True, exist_ok=True)
    (RENDERS / "anim").mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    leaves_poses, steam_poses = _extract_poses()
    static_layers, masks, clean_rgb = segment_layers()
    eau_frames, remous_frames = build_thermal_water_frames(masks["pool"], static_layers["rochers"], n_frames=4)
    feuilles_frames, vapeur_frames, brume_frames = build_leaves_and_steam_frames(
        masks["pool"], leaves_poses, steam_poses, n_frames=24
    )

    static_order = [
        ("04_sol_complet", "sol_complet"),
        ("05_herbe", "herbe"),
        ("06_chemin", "chemin"),
        ("07_bordures", "bordures"),
        ("08_rochers", "rochers"),
        ("09_arbres", "arbres"),
        ("10_profondeur", "profondeur"),
        ("13_canopee", "canopee"),
    ]
    for code, key in static_order:
        Image.fromarray(static_layers[key], "RGBA").save(RENDERS / "layers" / f"{PREFIX}_{code}.png")

    for i, fr in enumerate(eau_frames):
        Image.fromarray(fr, "RGBA").save(RENDERS / "anim" / f"{PREFIX}_01_eau_thermale_f{i:02d}.png")
    for i, fr in enumerate(remous_frames):
        Image.fromarray(fr, "RGBA").save(RENDERS / "anim" / f"{PREFIX}_02_remous_f{i:02d}.png")
    for i, fr in enumerate(feuilles_frames):
        Image.fromarray(fr, "RGBA").save(RENDERS / "anim" / f"{PREFIX}_03_feuilles_f{i:02d}.png")
    for i, fr in enumerate(vapeur_frames):
        Image.fromarray(fr, "RGBA").save(RENDERS / "anim" / f"{PREFIX}_11_vapeur_f{i:02d}.png")
    for i, fr in enumerate(brume_frames):
        Image.fromarray(fr, "RGBA").save(RENDERS / "anim" / f"{PREFIX}_12_brume_thermale_f{i:02d}.png")

    frames_rgba: list[np.ndarray] = []
    for tick in range(0, LOOP_TICKS, 10):
        comp = compose_tick(
            tick, static_layers, eau_frames, remous_frames, feuilles_frames, vapeur_frames, brume_frames
        )
        frames_rgba.append(comp)
        Image.fromarray(comp, "RGBA").save(RENDERS / f"{PREFIX}_scene_t{tick:03d}.png")

    pil_frames = [Image.fromarray(f, "RGBA") for f in frames_rgba]
    pil_frames[0].save(
        RENDERS / f"{PREFIX}_anim.webp", save_all=True, append_images=pil_frames[1:], duration=166, loop=0
    )
    pil_frames[0].save(
        RENDERS / f"{PREFIX}_anim.png", save_all=True, append_images=pil_frames[1:], duration=166, loop=0
    )

    grid = build_collision_grid()
    walk_vis = frames_rgba[0].copy()
    ov = Image.fromarray(walk_vis, "RGBA")
    dr = ImageDraw.Draw(ov, "RGBA")
    for gy in range(GH):
        for gx in range(GW):
            if grid[gy, gx] == 0:
                dr.rectangle([gx * TW, gy * TH, (gx + 1) * TW - 1, (gy + 1) * TH - 1], fill=(40, 220, 100, 75))
    entrance_px = [384, 560]
    seuil_px = [384, 152]
    dr.ellipse([entrance_px[0] - 6, entrance_px[1] - 6, entrance_px[0] + 6, entrance_px[1] + 6], fill=(0, 255, 128, 255))
    dr.ellipse([seuil_px[0] - 6, seuil_px[1] - 6, seuil_px[0] + 6, seuil_px[1] + 6], fill=(255, 80, 80, 255))
    ov.save(RENDERS / f"{PREFIX}_walkability.png")

    ora_path = RENDERS / f"{PREFIX}_entree_bassin_chauffant.ora"
    write_ora(
        ora_path,
        static_layers,
        eau_frames,
        remous_frames,
        feuilles_frames,
        vapeur_frames,
        brume_frames,
        frames_rgba[0],
    )

    stack = [
        ("eau_thermale (anime 4x10t)", eau_frames, 10, 0),
        ("remous (anime 4x12t)", remous_frames, 12, 0),
        ("feuilles (anime 24x10t)", feuilles_frames, 10, 0),
        ("sol_complet (base)", [static_layers["sol_complet"]], 60, 0),
        ("herbe", [static_layers["herbe"]], 60, 0),
        ("chemin", [static_layers["chemin"]], 60, 0),
        ("bordures", [static_layers["bordures"]], 60, 0),
        ("rochers", [static_layers["rochers"]], 60, 0),
        ("arbres", [static_layers["arbres"]], 60, 0),
        ("profondeur", [static_layers["profondeur"]], 60, 0),
        ("vapeur (anime 24x10t)", vapeur_frames, 10, 0),
        ("brume_thermale (anime 24x10t)", brume_frames, 10, 0),
        ("canopee (Top)", [static_layers["canopee"]], 60, 4),
    ]
    bank_counts = build_pmdo_ground_project(stack, grid, entrance_px, seuil_px, gfx, tools)

    fidelity = measure_fidelity(clean_rgb)
    manifest = {
        "map_id": "entree_bassin_chauffant_sud_nord_v1",
        "prefix": PREFIX,
        "reference": "bassinchauffantpmdsky.png",
        "reference_code": "P01P04A",
        "reference_sha256": sha256_of(REF_PATH),
        "dimensions_px": [W, H],
        "dimensions_tiles": [GW, GH],
        "tile_size_px": [TW, TH],
        "aspect_ratio": "4:3",
        "loop_ticks": LOOP_TICKS,
        "art_approved": False,
        "runtime_tested": False,
        "markers": {
            "entrance": entrance_px,
            "donjon_seuil": seuil_px,
        },
        "walkable_cells": int((grid == 0).sum()),
        "fidelity": fidelity,
        "pmdo_banks": bank_counts,
        "total_tiles": int(sum(bank_counts.values())),
        "layers": [s[0].split()[0] for s in stack],
    }
    (RENDERS / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    html_path = ROOT / "apercu_entree_bassin_chauffant_sud_nord_v1.html"
    write_viewer_html(html_path, manifest)

    mod_zip = ROOT / "mod_entree_bassin_chauffant_sud_nord_pmdo_0812.zip"
    with zipfile.ZipFile(mod_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(STAGE.rglob("*")):
            if p.is_file():
                zf.write(p, Path(NAMESPACE) / p.relative_to(STAGE))

    liv_zip = ROOT / "livrable_entree_bassin_chauffant_sud_nord_v1.zip"
    with zipfile.ZipFile(liv_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(RENDERS.rglob("*")):
            if p.is_file():
                zf.write(p, Path("renders/entree_bassin_chauffant_sud_nord_v1") / p.relative_to(RENDERS))
        zf.write(html_path, html_path.name)

    print(
        f"[{PREFIX}] OK: {W}x{H} ({GW}x{GH}), walkable={(grid == 0).sum()}, "
        f"tiles={manifest['total_tiles']}, fidelity={ {k: v['rgb_distance'] for k, v in fidelity.items()} }"
    )


if __name__ == "__main__":
    main()
