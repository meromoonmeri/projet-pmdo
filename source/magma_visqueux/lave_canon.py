"""Lave canonique Mt. Blaze (GBA, Pokémon Mystery Dungeon Red Rescue Team).

Source des tons : planches Spriters Resource relevées pixel par pixel —
`65097.png` (Mt Blaze Dungeon Tiles, rip ToastyPK : piscine, croûtes, bulles, coulures, swatch)
et `221081.png` (Mt. Blaze Entrance, re-rip à palette unique faite pour l'animation par cycling).
Tous les tons ci-dessous sont EXACTEMENT des valeurs présentes dans ces planches : rien n'est inventé.

Animation « super visqueuse », en deux composantes séparées et vérifiables :

1. **Palette cycling** (conforme à la planche, aucun pixel inventé) : les tons de la famille braise
   (152,0,0 → 216,72,16, 5 entrées) et de la famille cœur chaud (240,128,88 → 240,232,0, 3 entrées)
   tournent sur place par permutation cyclique. Une permutation *dans* chaque famille ⇒ la quantité de
   pixels braise et la quantité de pixels cœur chaud sont invariantes d'une phase à l'autre : c'est le
   cycling de la GBA, pas un redessin. Sur ce lot le pas est ralenti à 20 ticks par phase (10,7 s la
   boucle) pour l'effet visqueux.
2. **Dérive visqueuse** (boucle fermée) : la matière (croûtes marron, plaques claires, mare) est portée
   par un champ de pliage très lent — deux ondes qui voyagent, une oscillation par boucle — plus un
   gonflement qui éclaircit les plaques puis les laisse retomber. L'amplitude est annulée près du bord
   (`fade` sur la distance à la silhouette) : la silhouette de la couche reste EXACTEMENT celle du
   layout, phase après phase, et la boucle se referme (phase 32 ≡ phase 0).

Aucune image de lave n'est peinte à la main : la texture vient du rendu généré référencé
(`bruts/lave_source.png`, obtenu avec le layout strict + la planche canonique en `images=`), la palette
et l'animation viennent des planches canoniques.
"""
import numpy as np
from PIL import Image
from scipy import ndimage as nd

# ---------------------------------------------------------------- palette relevée sur les planches
CONTOUR = (40, 32, 24)                                  # liseré sombre de rive (bas de la mare de 65097)
CROUTE = [(96, 40, 56), (136, 96, 88)]                  # 1 plaque marron, 2 croûte claire (hérisse de 65097)
RAMPE = [(152, 0, 0),                                   # 3 rouge sombre
         (176, 56, 32),                                 # 4 rouge braise (liseré de mare)
         (208, 56, 0),                                  # 5 orange-rouge (bord de coulure)
         (208, 64, 8),                                  # 6 orangé
         (216, 72, 16),                                 # 7 orangé clair
         (216, 120, 40),                                # 8 SURFACE DE MARE (à plat dans la planche)
         (240, 128, 88),                                # 9 chair chaude (rehaut de la mare)
         (240, 160, 0),                                 # 10 cœur chaud
         (240, 232, 0)]                                 # 11 jaune incandescent
PAL = [CONTOUR] + CROUTE + RAMPE                        # 12 tons, index 0..11
PAL_NP = np.array(PAL, 'uint8')
N_PAL = len(PAL)

IDX_CROUTE = [1, 2]                                     # gonflement 1 <-> 2, jamais tournée
IDX_MARE = [8]                                          # surface de mare : À PLAT, hors cycling (comme la planche)
IDX_BRAISE = [3, 4, 5, 6, 7]                            # famille cycling 5
IDX_COEUR = [10, 11]                                    # famille cycling 2 (cœurs lumineux des coulures)

PHASES, TICKS = 32, 20                                  # 640 ticks = 10,7 s : pas ralenti, « super visqueuse »
AMP = 0.8                                               # amplitude du pliage, en pixels du rendu final (grille 8 px)


# ---------------------------------------------------------------- classement des pixels d'une planche
def lavamask(a):
    """Vrai là où le pixel appartient à la famille chaude de la lave (rouge/orange/marron de lave),
    faux pour le magenta de segmentation et pour la roche grise-violacée (b >= g)."""
    a = a.astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mag = (r - g > 60) & (b - g > 60)
    chaud = (r - g >= 30) & (r >= 80)
    sombre = (r <= 64) & (g >= b + 4) & (r - g >= 6)
    return (mag | ~(chaud | sombre)) == False                        # ni magenta ni roche


def classify(a, tol=46):
    """Index de palette (0..11) par pixel, -1 pour ce qui n'est pas de la lave."""
    a = a.astype(int)
    d = np.linalg.norm(a[:, :, None, :] - PAL_NP[None, None, :, :].astype(int), axis=3)
    idx = d.argmin(2)
    return np.where(lavamask(a) & (d.min(2) <= tol), idx, -1).astype(np.int8)


def clean_speckles(idx, tones=(9,), min_size=12, merge_to=None):
    """Retire les tons isolés en semis (pixels de transition) : la planche canonique n'emploie la chair
    chaude (240,128,88) qu'en rehaut continu de coulure, jamais en pointillé. Les paquets plus petits que
    `min_size` sont ramenés au ton voisin (`merge_to`, par défaut la surface de mare)."""
    out = idx.copy()
    for tn in tones:
        m = out == tn
        lab, n = nd.label(m, np.ones((3, 3), bool))
        if not n:
            continue
        sizes = np.bincount(lab.ravel(), minlength=n + 1)
        small = np.isin(lab, [i for i in range(1, n + 1) if sizes[i] < min_size]) & m
        out[small] = int(merge_to if merge_to is not None else IDX_MARE[0])
    return out


def to_grid(idx, src, out, n_pal=N_PAL):
    """Descente pleine résolution -> grille finale : classe majoritaire par bloc, ton majoritaire dans la classe."""
    sw, sh = src
    ow, oh = out
    cover = []
    for i in range(n_pal):
        cover.append(np.asarray(Image.fromarray((idx == i).astype('float32'), 'F').resize((ow, oh), Image.BOX)))
    cover.append(np.asarray(Image.fromarray((idx < 0).astype('float32'), 'F').resize((ow, oh), Image.BOX)))
    code = np.stack(cover).argmax(0)
    return np.where(code == n_pal, -1, code).astype(np.int8)


# ---------------------------------------------------------------- champs lents
def smooth(shape, seed, sigma):
    f = nd.gaussian_filter(np.random.default_rng(seed).random(shape), sigma, mode='nearest')
    return (f - f.mean()) / (f.std() + 1e-9)


def _bilinear(field, u, v):
    H, W = field.shape
    u = np.clip(u, 0, W - 1.001); v = np.clip(v, 0, H - 1.001)
    x0 = np.floor(u).astype(int); y0 = np.floor(v).astype(int)
    fx = u - x0; fy = v - y0
    x1 = np.minimum(x0 + 1, W - 1); y1 = np.minimum(y0 + 1, H - 1)
    return (field[y0, x0] * (1 - fx) * (1 - fy) + field[y0, x1] * fx * (1 - fy) +
            field[y1, x0] * (1 - fx) * fy + field[y1, x1] * fx * fy)


def k_braise(t, phases=PHASES):
    return (t * len(IDX_BRAISE)) // phases


def k_coeur(t, phases=PHASES):
    return (t * len(IDX_COEUR)) // phases


def rotate(idx, kb, kc):
    """Permutation cyclique DANS chaque famille (identité ailleurs) : palette cycling pur."""
    out = idx.copy()
    b, c = np.array(IDX_BRAISE), np.array(IDX_COEUR)
    m = np.isin(idx, b)
    out[m] = b[(np.searchsorted(b, idx[m]) + kb) % len(b)]
    m = np.isin(idx, c)
    out[m] = c[(np.searchsorted(c, idx[m]) + kc) % len(c)]
    return out


def phases(base, mask, phases=PHASES, amp=AMP, seed=5):
    """Phases RGBA de la lave (H x W final). `base` = index de ton par pixel (-1 hors matière),
    `mask` = silhouette définitive (issue du layout). Retourne (frames, meta)."""
    H, W = mask.shape
    b = base.astype(np.int16).copy()
    b[(b < 0) & mask] = int(IDX_MARE[0])                             # sous la silhouette : mare canonique à plat
    b[~mask] = 0
    d = nd.distance_transform_edt(mask)
    fade = np.clip(d / 7.0, 0, 1)                                    # pliage nul au bord : silhouette intacte
    g1, g2 = smooth((H, W), seed + 1, 26), smooth((H, W), seed + 2, 26)
    psi = np.pi * (smooth((H, W), seed + 3, 18) + 1)                 # phase locale du gonflement
    yy, xx = np.mgrid[:H, :W].astype(float)
    frames, rots = [], []
    for t in range(phases):
        ph = 2 * np.pi * t / phases
        u = xx + fade * amp * (np.sin(2 * np.pi * yy / 97.0 + ph) + 0.6 * g1 * np.cos(ph))
        v = yy + fade * amp * (np.cos(2 * np.pi * xx / 123.0 - ph) + 0.6 * g2 * np.sin(ph))
        tone = _bilinear(b.astype('float32'), u, v)
        # gonflement : les plaques de croûte s'éclaircissent puis retombent ; la mare respire d'un ton
        heave = np.sin(ph + psi)
        tone = np.where(np.isin(np.rint(tone).astype(int), IDX_CROUTE),
                        np.where(heave > 0.55, np.maximum(tone, 2.0), np.minimum(tone, 1.0)), tone)
        # rehaut chaud (9) : uniquement liseré de 2 px autour des plaques de croûte, quand la bosse monte
        plaque = np.isin(np.rint(tone).astype(int), IDX_CROUTE)
        liseré = nd.binary_dilation(plaque, iterations=2) & ~plaque
        tone = np.where(liseré & (heave > 0.55), 9.0, np.where(liseré & (heave < -0.75), 7.0, tone))
        idx = np.clip(np.rint(tone).astype(int), 0, N_PAL - 1)
        idx = rotate(idx, k_braise(t, phases), k_coeur(t, phases))   # palette cycling fermé sur la boucle
        a = np.zeros((H, W, 4), 'uint8')
        a[..., :3] = PAL_NP[idx]; a[..., 3] = 255
        a[~mask] = 0
        frames.append(a)
        rots.append({'t': t, 'k_braise': int(k_braise(t, phases)), 'k_coeur': int(k_coeur(t, phases))})
    meta = {'phases': phases, 'ticks': TICKS, 'amp_px': amp,
            'familles': {'braise': len(IDX_BRAISE), 'coeur': len(IDX_COEUR)},
            'palette': [list(map(int, c)) for c in PAL], 'rotation': rots,
            'origine': 'planches Spriters Resource 65097 (lot ToastyPK) + 221081 (re-rip palette unique)'}
    return frames, meta
