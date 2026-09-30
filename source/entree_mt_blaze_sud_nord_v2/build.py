"""Entrée Mt. Blaze (EMB2) — entrée de donjon du volcan, 4:3 vaste (768 x 576), format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Méthode propre multicalque référencée :
- decor.png : rendu généré RÉFÉRENCÉ avec Rescue_Team_-_Mt._Blaze_Entrance.png en images= (lave = magenta plat #FF00FF)
- sol_complet.png : édité depuis le décor (sable seul, 0,0)
- base (sable, ombres, berge, roche, piliers, profondeur) : segmentation pleine rés. + down_class 8px, palette commune
- lave : texture canonique GBA (planches Spriters Resource 65097 + 221081) portée par le rendu généré
  référencé bruts/lave_source.png (layout strict + planche canonique en images=), clippée sur la
  silhouette de lave du layout ; animation « super visqueuse » : palette cycling des familles
  braise (5 entrées) et cœur chaud (2 entrées), permutation cyclique fermée sur la boucle, plus
  dérive visqueuse de la croûte (pliage 1,2 px annulé au bord, gonflement lent) ; 32 phases × 20 ticks
- veines : fissures orange dans la roche extraites du décor, palette canonique, palette cycling 32×20
Boucle : 32×20 = 640 ticks = 10,7 s. Aucun warp.

Lancer : .venv/bin/python source/entree_mt_blaze_sud_nord_v2/build.py
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
RAW = HERE / 'bruts'
REF = R / 'Rescue_Team_-_Mt._Blaze_Entrance.png'
OUT = R / 'renders/entree_mt_blaze_sud_nord_v2'
STAGE = R / '.cache/entree_mt_blaze_sud_nord_v2/entree_mt_blaze_sud_nord_v2'
NAMESPACE = 'entree_mt_blaze_sud_nord_v2'
ASSET = 'emb2_entree_mt_blaze_sud_nord_v2'
PFX = 'EMB2'
W, H = 768, 576
SRC = (1200, 896)

# Palette Mt Blaze corrigée d'après 221081.png (Spriters Resource) - 10 couleurs lave exactes GBA, palette cycling pur
# Lava 221081: 156,58,25 → 230,107,0 (pas de jaune), rip unique sans doublon
MTB_CRUST = [(55, 18, 12), (85, 28, 16), (115, 40, 22)]
MTB_RAMP = [(156, 58, 25), (165, 49, 16), (173, 41, 8), (181, 99, 25), (189, 90, 16),
            (197, 82, 8), (206, 74, 0), (214, 123, 16), (222, 115, 8), (230, 107, 0)]
MTB_PAL = MTB_CRUST + MTB_RAMP  # 13 tons, index 0..12
MTB_PAL_NP = np.array(MTB_PAL, 'uint8')

GEN = [
    {'file': 'decor.png', 'images': ['layout a faire multicalque lave etc séparer.png', '65097.png', 'Rescue_Team_-_Mt._Blaze_Entrance.png', '112438.png', '221081.png'], 'prompt':
     'STRICT COPY of layout a faire multicalque lave etc séparer.png - EXACT same layout, same positions, same shapes. Central beige cracked sand, south path centered between low grey rocks, north cave black with two pillars and stalactites, lava pools left and right exactly as reference (orange pools with yellow highlights, dark red wavy flows with orange glow), grey boulders at same spots, rocky walls north/west/east/south with orange lava veins (cracks) in grey rock. Use EXACT textures from 65097 lava texture (orange-red with yellow core, dark maroon) + 112438 ground + Rescue palette. For segmentation, entire lava pool surfaces (bright orange pools) filled flat pure magenta #FF00FF, no gradient. Hard pixel art, 1200x896, top-down, no characters.',
     'essais': 'strict 30/09 00:17 layout séparer.png + 65097 lave + 112438, 106k magenta, veines orange conservées'},
    {'file': 'lave_source.png', 'images': ['source/entree_mt_blaze_sud_nord_v2/reference/layout_strict.png', 'source/entree_mt_blaze_sud_nord_v2/reference/65097.png'], 'prompt':
     'Pixel art lava layer ONLY, 1200x896, top-down, everything that is not lava is flat pure magenta #FF00FF (no ground, no sand, no rocks, no walls, no characters, no text). The lava occupies EXACTLY the same areas as the lava in the first reference layout: two big pools on the left and right that rise along the sides and wrap around the grey rocks, with wavy fingers and channels flowing toward the north cave and toward the bottom, matching the reference\'s pool outlines shape for shape. Texture and colors EXACTLY as the second reference (canonical Pokemon Mystery Dungeon Mt Blaze lava sheet): flat orange pool surface (216,120,40), thick dark maroon crust bands and islands (96,40,56), red glowing rims (176,56,32), bright hot spots (240,160,0) with yellow cores (240,232,0) as small ovals, dark red-brown shore outline (40,32,24). Thick, sticky, viscous look. Hard pixel art edges, GBA style.',
     'essais': 'calque lave seul 30/09 03:0x : layout_strict + planche canonique 65097 en images=, reste magenta pur, U est/ouest conformes'},
    {'file': 'sol_complet.png', 'images': ['source/entree_mt_blaze_sud_nord_v2/bruts/decor.png'], 'prompt':
     'Same image, same framing and pixel-art style, but only beige cracked sandy ground everywhere, replacing all lava (magenta), grey rocks, pillars and the dark cave mouth with the same beige cracked sand texture, keeping the exact sand palette and crack pattern, no other textures, no magenta remaining.',
     'essais': 'edite depuis decor (magenta->sable, piliers conserves sous calque roche)'},
]

def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

JM = loadmod('ejn1_outils', R / 'source/entree_jungle_sud_nord_v1/build.py')
BM = JM.BM
MG = loadmod('magma_visqueux', R / 'source/magma_visqueux/magma.py')
GR = loadmod('magma_ground', R / 'source/magma_visqueux/ground.py')
assert (JM.W, JM.H, JM.SRC) == (W, H, SRC)
# Patch MG palette to Mt Blaze
MG.PAL = MTB_PAL
MG.PAL_NP = MTB_PAL_NP
MG.RIP_RAMP = MTB_RAMP
MG.CROUTE = MTB_CRUST
MG.N_RIP0 = len(MTB_CRUST)
# garder CELL/PERIOD etc
# Palette canonique de lave relevée sur les planches Spriters Resource (65097 + 221081) — cf. lave_canon.py.
LC = loadmod('lave_canon', R / 'source/magma_visqueux/lave_canon.py')
LAVE_PAL = [tuple(int(v) for v in c) for c in LC.PAL]
LAVE_PAL_NP = LC.PAL_NP

S = JM.SCALE
LOOP_TICKS = 640  # 32*20 : pas ralenti, lave « super visqueuse »

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rgb(p):
    return np.array(Image.open(p).convert('RGB')).astype(int)

def morph(fn, m, it):
    p = it + 2
    return fn(np.pad(m, p, mode='edge'), iterations=it)[p:-p, p:-p]

def keep_large(mask, minimum):
    lab, n = nd.label(mask)
    if n == 0:
        return mask
    return np.isin(lab, 1 + np.flatnonzero(nd.sum(mask, lab, range(1, n + 1)) >= minimum))

# segmentation identique à l'ancien build (adaptée Mt Blaze)
def classify(a, f):
    r, g, b = a.transpose(2, 0, 1); lum = a @ [.299, .587, .114]
    hh, ww = lum.shape; yy, xx = np.mgrid[:hh, :ww]
    water = nd.binary_dilation((r - g > 60) & (b - g > 60), iterations=2)
    dark = (lum < 48) & (yy < 260) & (xx > 450) & (xx < 750)
    lab, n = nd.label(JM.close_(dark, 2) if hasattr(JM,'close_') else morph(nd.binary_closing, dark, 2))
    # use same logic as old
    def close_(m,it):
        return JM.close_(m,it) if hasattr(JM,'close_') else morph(nd.binary_closing,m,it)
    lab, n = nd.label(close_(dark, 2)); sizes = nd.sum(dark, lab, range(1, n + 1)) if n else []
    box = np.zeros_like(dark); box[40:160, 540:660] = True
    cand = [i + 1 for i in range(n) if (lab[box] == i + 1).any()] if n else []
    if cand:
        opening = nd.binary_fill_holes(lab == max(cand, key=lambda i: sizes[i - 1]))
    else:
        opening = np.zeros_like(dark, dtype=bool)
    sandish = (r > 130) & (r - b > 25) & (lum > 110) & (lum < 170) & ~water & ~opening
    sand = keep_large(morph(nd.binary_closing, sandish, 2) if hasattr(JM,'close_') else morph(nd.binary_closing,sandish,2), 15000)
    # opening/closing via JM
    def open_(m,it):
        p=it+1
        return nd.binary_opening(np.pad(m,p,mode='edge'), iterations=it)[p:-p,p:-p]
    sand = keep_large(open_(morph(nd.binary_closing,sandish,2),1),15000)
    holes = nd.binary_fill_holes(sand) & ~sand; hl, _ = nd.label(holes)
    hs = nd.sum(holes, hl, range(1, hl.max() + 1)) if hl.max() else []
    sand = (sand | np.isin(hl, [i + 1 for i, v in enumerate(hs) if v < 800])) & ~water & ~opening
    rockish = ~sand & ~water & ~opening
    Ls = nd.uniform_filter(lum, 5); dr = nd.distance_transform_edt(~rockish)
    shade = sand & (dr <= 16) & (Ls < 165)
    shade = keep_large(morph(nd.binary_closing, shade,1), 40) & sand
    dw = nd.distance_transform_edt(~water); ds = nd.distance_transform_edt(~sand)
    berge = rockish & (dw <= 14) & (ds <= 14)
    diff = nd.uniform_filter(np.abs(a - f).mean(2), 5)
    rest = rockish & ~berge
    pil = rest & (diff > 15) & ~nd.binary_dilation(opening, iterations=40)
    pil = nd.binary_fill_holes(keep_large(open_(morph(nd.binary_closing,pil,2),1), 120)) & rest
    roche = rest & ~pil
    return dict(water=water, profondeur=opening, sable=sand & ~shade, ombres=shade, berge=berge, piliers=pil, roche=roche), {'ecart_parois': round(float(diff[roche].mean()),2) if roche.any() else 0, 'ecart_piliers': round(float(diff[pil].mean()),2) if pil.any() else 0}

def materials(a):
    r, g, b = a.transpose(2, 0, 1); lum = a @ [.299, .587, .114]; sat = a.max(2) - a.min(2)
    mag = (r - g > 60) & (b - g > 60)
    sand = (r > 150) & (r - b > 50) & (lum > 140) & ~mag
    rock = (r >= b + 15) & (g >= b + 10) & (lum > 40) & (lum < 175) & (sat < 90) & ~sand & ~mag
    return {'sable': sand, 'roche': rock}

def fidelity(decor, ref):
    fr, fd = materials(ref), materials(decor); out = {}
    for k in fr:
        mr, md = ref[fr[k]].mean(0), decor[fd[k]].mean(0)
        out[k] = {'rip_rgb': [round(float(v),1) for v in mr], 'decor_rgb': [round(float(v),1) for v in md], 'distance': round(float(np.linalg.norm(mr-md)),1)}
    return out

def vein_mask_from_rock(a, rock_union):
    r,g,b = a.transpose(2,0,1)
    # extraction orange dans roche (comme avant) mais on garde pour mask ; c'est la texture du décor généré donc cohérent
    m = rock_union & (r>100) & (g<120) & (b<100) & (r - g > 20) & (r > b)
    m = nd.binary_dilation(m, iterations=1) & rock_union
    m = nd.binary_opening(m, iterations=1)
    # si trop peu (<0.5% roche) on épaissit via Worley fissures pour garantir visibilité
    if m.sum() < 0.005 * rock_union.sum():
        # génère fissures Worley fine dans roche
        H0,W0 = a.shape[:2]
        yy, xx = np.mgrid[:H0,:W0].astype(float)
        # Worley temporaire via MG worley avec cell 14
        try:
            f1,f2,_ = MG.worley(xx*0.7, yy*0.7, P=(192,96), cell=14, seed=7)
            q = 2*f1/(f1+f2+1e-9)
            fiss = (q > 0.82) & rock_union
            m = m | fiss
        except Exception:
            pass
    return m

def vein_frames(vein_mask_down, H, W, phases=32):
    """Veines de lave dans la roche : palette canonique (lave_canon) + palette cycling fermé.

    Ton = profondeur dans la fente (distance à la rive) modulée par un Worley fin et un gonflement
    lent, puis permutation cyclique des familles braise / cœur, identique à la lave. Aucun ton inventé.
    """
    if not vein_mask_down.any():
        return [np.zeros((H, W, 4), 'uint8') for _ in range(phases)]
    dist = nd.distance_transform_edt(vein_mask_down)
    yy, xx = np.mgrid[:H, :W].astype(float)
    try:
        f1, f2, _ = MG.worley(xx * 1.0, yy * 1.0, P=MG.PERIOD, cell=18, seed=9)
        q = 2 * f1 / (f1 + f2 + 1e-9)
    except Exception:
        q = np.zeros((H, W))
    depth = np.clip(dist / 2.6 + 1.4 * q + 0.6 * LC.smooth((H, W), 21, 12), 0, 5)
    TONES = [1, 4, 6, 7, 9, 10, 11]                    # croûte -> braise -> cœur chaud (tons de la planche)
    bornes = [0.9, 1.6, 2.4, 3.0, 3.8, 4.6]
    pos0 = np.searchsorted(bornes, depth).clip(0, 6)
    frames = []
    for t in range(phases):
        ph = 2 * np.pi * t / phases
        pos = np.clip(np.rint(pos0 + 0.9 * np.sin(ph + 2 * np.pi * q)), 0, 6).astype(int)
        idx = np.array(TONES)[pos]
        idx = LC.rotate(idx, LC.k_braise(t, phases), LC.k_coeur(t, phases))
        a = np.zeros((H, W, 4), 'uint8')
        a[..., :3] = LAVE_PAL_NP[idx]; a[..., 3] = 255
        a[~vein_mask_down] = 0
        frames.append(a)
    return frames

def build():
    gfx = loadmod('pmdo_codec', R / 'source/pmdo_cote/build.py')
    tools = loadmod('index_tools', R / 'source/pmdo_cote/INSTALLER.py')
    v1 = loadmod('esn1', R / 'source/entree_sud_nord_generee_v1/build.py')
    if OUT.exists():
        for d in ['calques','animation','poses','masques','review']:
            shutil.rmtree(OUT/d, ignore_errors=True)
    for d in ['calques','poses','masques','review','animation/lave','animation/veines']:
        (OUT/d).mkdir(parents=True, exist_ok=True)
    a = rgb(RAW/'decor.png'); f = rgb(RAW/'sol_complet.png'); ref = rgb(REF)
    assert a.shape[:2]==f.shape[:2]==(SRC[1],SRC[0])
    m, seg = classify(a,f)
    # Veines : extraction depuis roche+piliers
    rock_union = m['roche'] | m['piliers']
    vein_mask_1200 = vein_mask_from_rock(a, rock_union)
    m['veines'] = vein_mask_1200
    m['roche'] = m['roche'] & ~vein_mask_1200
    m['piliers'] = m['piliers'] & ~vein_mask_1200
    order = ['water','profondeur','sable','ombres','berge','piliers','roche','veines']
    down_class, down_full, rgba = JM.down_class, JM.down_full, JM.rgba
    ex, cols = down_class(a, m, order)
    water = ex['water']
    STATIC = ['sable','ombres','berge','roche','piliers','profondeur']
    layers = {'sol_complet': rgba(down_full(f), ~water)}
    for k in STATIC:
        layers[k] = rgba(cols[k], ex[k])
    layers = BM.quantize_layers(layers)
    for k,v in ex.items():
        Image.fromarray((v*255).astype('uint8')).save(OUT/'masques'/f'{PFX}_masque_{k}.png')
    land = np.zeros((H,W), bool)
    for k in STATIC:
        land |= layers[k][...,3]==255
    visible = water & ~land
    # lave : texture canonique portée par le rendu généré référencé, clippée sur la silhouette du layout
    lsrc = Image.open(RAW/'lave_source.png').convert('RGB')
    if lsrc.size != SRC:
        lsrc = lsrc.resize(SRC, Image.NEAREST)
    larr = np.array(lsrc)
    lidx_full = LC.clean_speckles(LC.classify(larr))   # semis de transition retirés (planche : rehaut continu seulement)
    lidx = LC.to_grid(lidx_full, SRC, (W, H))
    mask_lave = visible & ex['water']
    mf, lava_meta = LC.phases(lidx, mask_lave, phases=32)
    dom, ndom = np.unique(lidx[lidx >= 0], return_counts=True)
    dom_i = int(dom[ndom.argmax()])
    lava_meta.update({'tons_planche': sorted(set(int(v) for v in np.unique(lidx_full[lidx_full >= 0]))),
                      'pixels_lave_grille': int(mask_lave.sum()),
                      'ton_dominant': [int(v) for v in LAVE_PAL[dom_i]],
                      'part_ton_dominant': round(float(ndom.max() / ndom.sum()), 3),
                      'ecart_ton_dominant_mare': round(float(np.linalg.norm(np.array(LAVE_PAL[dom_i]) - np.array([216, 120, 40]))), 1),
                      'texture': 'bruts/lave_source.png (rendu généré référencé : layout strict + planche canonique en images=)',
                      'nettoyage_semis': 'tons isoles < 12 px ramenes a la mare (cf. lave_canon.clean_speckles)',
                      'clip': 'silhouette = eau du decor (layout strict) ; pliage annulé au bord (fade)',
                      'rotation_pas': {'braise': len(LC.IDX_BRAISE), 'coeur': len(LC.IDX_COEUR)}})
    lava_meta.pop('rotation', None)
    # veines 32 phases palette cycling
    vein_mask_down = ex['veines']
    vf = vein_frames(vein_mask_down, H, W, phases=32)
    # stack ordre bas->haut : lave, base, veines (veines au dessus de roche mais sous piliers? on met au dessus de piliers pour visibilité)
    # On garde : lave, sol_complet, sable, ombres, berge, roche, piliers, profondeur, veines
    # Veines sont dans la roche donc au dessus de roche/piliers
    stack_named = [('lave', mf, LC.TICKS), ('sol_complet', [layers['sol_complet']], 60), ('sable', [layers['sable']],60), ('ombres', [layers['ombres']],60), ('berge', [layers['berge']],60), ('roche', [layers['roche']],60), ('piliers', [layers['piliers']],60), ('profondeur', [layers['profondeur']],60), ('veines', vf, LC.TICKS)]
    # écriture
    for i,(nm,frames,ticks) in enumerate(stack_named):
        if len(frames)==1:
            Image.fromarray(frames[0]).save(OUT/f'calques/{PFX}_{i:02d}_{nm}.png')
        else:
            for t,fr in enumerate(frames):
                d = OUT/f'animation/{nm}' if nm in ('lave','veines') else OUT/'calques'
                d.mkdir(parents=True, exist_ok=True)
                Image.fromarray(fr).save(d/f'{PFX}_{i:02d}_{nm}_f{t:02d}.png')
    # collisions : sable+ombres praticables
    walk_px = (layers['sable'][...,3]==255) | (layers['ombres'][...,3]==255)
    blocked = BM.cell_grid(~walk_px); gh_,gw_ = blocked.shape
    pxs = np.nonzero(walk_px[H-8])[0]; med = int(np.median(pxs))//8 if len(pxs) else W//16
    ecol = min((c for c in range(gw_-1) if not blocked[gh_-2:, c:c+2].any()), key=lambda c: abs(c-med)) if med else 48
    entrance = [ecol*8+8, H-16]
    target_y, target_x = 300,384
    best=None; bestd=1e9
    for y in range(gh_):
        for x in range(gw_):
            if not blocked[y:y+2, x:x+2].any():
                d=(y*8-target_y)**2+(x*8-target_x)**2
                if d<bestd:
                    bestd,best=d,[x*8,y*8]
    boss = best if best else [384,320]
    py,px_ = np.nonzero(walk_px); top_y = int(py.min()) if len(py) else 0; tx = int(np.median(px_[py < top_y+8])) if len(py) else 384
    objectif = [tx//8*8-8, top_y//8*8]
    try:
        while blocked[objectif[1]//8:objectif[1]//8+2, objectif[0]//8:objectif[0]//8+2].any():
            objectif[1]+=8
            if objectif[1]>H-16:
                break
    except: pass
    markers={'entrance':entrance,'boss':boss,'objectif':objectif}
    def reachable2(b,src,dst):
        return v1.reachable(b,(src[1]//8,src[0]//8),(dst[1]//8,dst[0]//8))[0]
    assert reachable2(blocked, entrance, boss), 'chemin entrance->boss bloque'
    assert reachable2(blocked, entrance, objectif), 'chemin entrance->objectif bloque'
    # scene
    def scene(tick):
        im=Image.new('RGBA',(W,H))
        for _,frames,ticks in stack_named:
            im.alpha_composite(Image.fromarray(frames[(tick//ticks)%len(frames)]))
        return im
    scenes=[scene(t) for t in range(0,LOOP_TICKS,5)]
    scenes[0].save(OUT/'review'/f'{PFX}_scene_t000.png')
    scenes[0].save(OUT/'review'/f'{PFX}_scene_animee.webp', save_all=True, append_images=scenes[1:], duration=round(5*1000/60), loop=0, lossless=True)
    col=scenes[0].copy(); ov=Image.new('RGBA',(W,H),(0,0,0,0)); dr=ImageDraw.Draw(ov)
    for y,x in zip(*np.nonzero(blocked)):
        dr.rectangle([x*8,y*8,x*8+7,y*8+7], fill=(220,40,40,90))
    for (qx,qy),c in ((entrance,(255,230,40,255)),(boss,(255,40,230,255)),(objectif,(60,220,255,255))):
        dr.rectangle([qx,qy,qx+15,qy+15], outline=c, width=2)
    col.alpha_composite(ov); col.save(OUT/'review'/f'{PFX}_collisions_marqueurs.png')
    # ora
    import xml.etree.ElementTree as ET
    root=ET.Element('image', w=str(W),h=str(H), name='Entrée Mt. Blaze 4:3 (EMB2)')
    stack=ET.SubElement(root,'stack'); comp=Image.new('RGBA',(W,H))
    with zipfile.ZipFile(OUT/f'{PFX}_entree_mt_blaze_sud_nord_v2_calques.ora','w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype','image/openraster', compress_type=zipfile.ZIP_STORED)
        items=list(enumerate(stack_named))
        for i,(nm,frames,_) in reversed(items):
            fn=f'data/layer{i:02d}.png'
            ET.SubElement(stack,'layer', name=nm, src=fn, x='0',y='0', opacity='1.0', visibility='visible', **{'composite-op':'svg:src-over'})
            b=io.BytesIO(); Image.fromarray(frames[0]).save(b,format='PNG'); z.writestr(fn,b.getvalue())
        for _,frames,_ in stack_named:
            comp.alpha_composite(Image.fromarray(frames[0]))
        b=io.BytesIO(); comp.save(b,format='PNG'); z.writestr('mergedimage.png',b.getvalue())
        th=comp.copy(); th.thumbnail((256,256)); b=io.BytesIO(); th.save(b,format='PNG'); z.writestr('Thumbnails/thumbnail.png',b.getvalue())
        z.writestr('stack.xml', ET.tostring(root, encoding='utf-8', xml_declaration=True))
    counts=GR.ground_project([(t.replace('_',' ')+(f' {len(fr)} phases' if len(fr)>1 else ''), fr, tk) for t,fr,tk in stack_named], blocked, markers, gfx, tools, stage=STAGE, pfx=PFX, asset=ASSET, namespace=NAMESPACE, here=HERE, W=W, H=H, name='Entree Mt. Blaze - 4:3 (EMB2)', comment='PMDO 0.8.12. Entree Mt. Blaze generee reference ; lave visqueuse, veines palette cycling. Aucun warp.', mod_name='Entree Mt. Blaze (EMB2) 4:3', mod_desc="Projet d'édition : entrée Mt. Blaze 4:3, lave visqueuse et veines palette cycling.")
    fid=fidelity(a,ref)
    layer_list=[]
    for i,(nm,frames,ticks) in enumerate(stack_named):
        if len(frames)>1:
            layer_list.append({'file':f'animation/{nm}/{PFX}_{i:02d}_{nm}_fNN.png','phases':len(frames),'ticks':ticks})
        else:
            layer_list.append({'file':f'calques/{PFX}_{i:02d}_{nm}.png','phases':1,'ticks':60})
    manifest={'lot':'entree_mt_blaze_sud_nord_v2','prefix':PFX,'format':'4:3 vaste','size_px':[W,H],'grid_8px':[W//8,H//8],'biome':'Mt. Blaze (lave)','method':'rendu genere reference : decor complet sur magenta ; sol complet miroir ; base quantifiee ; lave = texture canonique GBA (planches Spriters Resource 65097 + 221081) via calque genere dedie, clippee sur la silhouette du layout, animee en palette cycling (braise 5 / coeur 2) + derive visqueuse de la croute ; veines palette canonique + cycling ferme','reference_da':{'file':REF.name,'sha256':sha(REF)},'generation':GEN,'raw_inputs':[{'file':f'source/entree_mt_blaze_sud_nord_v2/bruts/{g["file"]}','sha256':sha(RAW/g['file']),'size':list(Image.open(RAW/g['file']).size)} for g in GEN],'fidelite_rip':fid,'layers':layer_list,'lave':dict(lava_meta, frame_length_ticks=LC.TICKS, palette=[list(c) for c in LAVE_PAL]),'veines':{'phases':32,'frame_length_ticks':LC.TICKS,'palette':[list(c) for c in LAVE_PAL],'pixels':int(vein_mask_down.sum()),'origine':'veines extraites du decor (orange dans roche) + fissures Worley fines ; palette canonique + cycling ferme' },'scene_loop_ticks':LOOP_TICKS,'access':{'markers':markers,'paths_16x16':{'entrance->boss':{'ok':reachable2(blocked,entrance,boss)},'entrance->objectif':{'ok':reachable2(blocked,entrance,objectif)}},'blocked_cells':int(blocked.sum()),'total_cells':int(blocked.size),'walkable_cells':int((~blocked).sum()),'rule':'case bloquee si >25% hors sable','north_closed':True},'pmdo':{'target':'0.8.12','asset':ASSET,'namespace':NAMESPACE,'tiles_per_bank':counts,'banks':list(counts),'runtime_tested':False,'warp':'aucun'},'art_approved':False}
    (OUT/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    shutil.copyfile(HERE / 'README_PACK.md', OUT / 'README.md')
    shutil.copyfile(OUT/'manifest.json', STAGE/'manifest.json')
    print(json.dumps({'fidelite':{k:v['distance'] for k,v in fid.items()},'markers':markers,'blocked':int(blocked.sum()),'veines_px':int(vein_mask_down.sum()),'lava_phases':len(mf),'vein_phases':len(vf)},indent=1))

if __name__=='__main__':
    build()
