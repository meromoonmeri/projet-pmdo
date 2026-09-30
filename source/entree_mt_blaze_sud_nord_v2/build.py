"""Entrée Mt. Blaze (EMB2) — entrée de donjon du volcan, 4:3 vaste (768 x 576), format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Méthode propre multicalque référencée :
- decor.png : rendu généré RÉFÉRENCÉ avec Rescue_Team_-_Mt._Blaze_Entrance.png en images= (lave = magenta plat #FF00FF)
- sol_complet.png : édité depuis le décor (sable seul, 0,0)
- base (sable, ombres, berge, roche, piliers, profondeur) : segmentation pleine rés. + down_class 8px, palette commune
- lave : magma visqueux procédural (Worley périodique, dérive/pliage/gonflement/croûte, 32×15 ticks) avec rampe Mt Blaze, cohérent à la texture du rip, animation palette cycling
- veines : fissures orange dans la roche extraites du décor, texture procédurale cohérente, palette cycling 32×15
Boucle : 32×15 = 480 ticks = 8 s. Aucun warp.

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

# Palette Mt Blaze : 3 tons de croûte + 10 tons de rampe relevée sur la lave du rip (orange GBA, 151,71,39 → jaune)
MTB_CRUST = [(55, 18, 12), (95, 28, 16), (145, 45, 22)]
MTB_RAMP = [(165, 65, 30), (185, 95, 25), (205, 125, 22), (218, 140, 18), (232, 155, 12),
            (240, 170, 0), (240, 188, 12), (250, 210, 30), (255, 230, 60), (255, 255, 90)]
MTB_PAL = MTB_CRUST + MTB_RAMP  # 13 tons, index 0..12
MTB_PAL_NP = np.array(MTB_PAL, 'uint8')

GEN = [
    {'file': 'decor.png', 'images': ['Rescue_Team_-_Mt._Blaze_Entrance.png'], 'prompt':
     'Use EXACTLY the same textures, palette and pixel-art style as the reference image (Pokemon Mystery Dungeon Red Rescue Team, Mt. Blaze Entrance - GBA): same beige cracked sandy ground with darker crack lines in block patterns, same grey boulders and stacked rocky walls with black outlines, same orange-red lava with yellow highlights. Make a NEW, larger top-down map, WIDE LANDSCAPE 4:3, zoomed out so the area feels vast. Layout: the player arrives at the SOUTH (bottom edge center) on the beige cracked sand path between grey rocks; the sand opens into a wide clearing; on the LEFT and RIGHT sides shallow LAVA POOLS (the entire lava surface is filled with flat pure magenta #FF00FF, no gradient, no shading, completely flat magenta for segmentation); grey boulders and small stones at lava edges; at the NORTH center a large dark cave entrance (black) framed by grey rock pillars, behind it dark rocky ground. No characters, no text, no UI, no border.',
     'essais': 'genere reference Mt Blaze GBA (plateau beige + piliers gris + lave magenta), 1200x896'},
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

S = JM.SCALE
LOOP_TICKS = 480  # 32*15

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
    # palette cycling pour veines : index basé sur distance à la rive de la veine + bruit, puis décalage par phase
    if not vein_mask_down.any():
        return [np.zeros((H,W,4),'uint8') for _ in range(phases)]
    # distance à l'extérieur de la veine (épaisseur)
    dist = nd.distance_transform_edt(vein_mask_down)
    # bruit Worley pour variation le long de la veine
    yy,xx = np.mgrid[:H,:W].astype(float)
    # petit worley pour moduler le niveau
    try:
        f1,f2,_ = MG.worley(xx*1.0, yy*1.0, P=MG.PERIOD, cell=18, seed=9)
        q = 2*f1/(f1+f2+1e-9)
        mod = (q*1.5).astype(float)  # 0..1.5
    except Exception:
        mod = np.zeros((H,W))
    base = np.clip(dist*1.2 + mod, 0, 6)  # 0..6
    # map base -> index palette : croûte 0-2, puis ramp 3-12
    # on veut que les veines pulsent orange->jaune : base 3-8 + phase
    frames=[]
    for t in range(phases):
        # heave lent + palette cycling : on décale de t//2 pour que le cycle soit visible mais pas trop rapide
        shift = t  # 1 ton par phase
        lvl = base + shift*0.35  # léger décalage
        # aussi gonflement sinusoïdal
        lvl = lvl + 0.6*np.sin(2*np.pi*t/phases + mod*2)
        idx = np.clip(np.rint(lvl + 3).astype(int), 3, 12)  # reste dans ramp
        # plus fin : coeur plus clair
        idx = np.where(dist>1.5, np.minimum(idx+1,12), idx)
        a = np.zeros((H,W,4),'uint8')
        a[..., :3] = MTB_PAL_NP[idx]
        a[..., 3] = 255
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
    # lave visqueuse 32 phases
    mf, dist, midx = MG.magma_phases(ex['water'], visible & ex['water'], feet=(), drift=(0,1), seed=3, crust=0.12, phases=32)
    # veines 32 phases palette cycling
    vein_mask_down = ex['veines']
    vf = vein_frames(vein_mask_down, H, W, phases=32)
    # stack ordre bas->haut : lave, base, veines (veines au dessus de roche mais sous piliers? on met au dessus de piliers pour visibilité)
    # On garde : lave, sol_complet, sable, ombres, berge, roche, piliers, profondeur, veines
    # Veines sont dans la roche donc au dessus de roche/piliers
    stack_named = [('lave', mf, 15), ('sol_complet', [layers['sol_complet']], 60), ('sable', [layers['sable']],60), ('ombres', [layers['ombres']],60), ('berge', [layers['berge']],60), ('roche', [layers['roche']],60), ('piliers', [layers['piliers']],60), ('profondeur', [layers['profondeur']],60), ('veines', vf, 15)]
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
    manifest={'lot':'entree_mt_blaze_sud_nord_v2','prefix':PFX,'format':'4:3 vaste','size_px':[W,H],'grid_8px':[W//8,H//8],'biome':'Mt. Blaze (lave)','method':'rendu genere reference : decor complet sur magenta ; sol complet miroir ; base quantifiee ; lave visqueuse Worley periodique palette Mt Blaze + veines palette cycling','reference_da':{'file':REF.name,'sha256':sha(REF)},'generation':GEN,'raw_inputs':[{'file':f'source/entree_mt_blaze_sud_nord_v2/bruts/{g["file"]}','sha256':sha(RAW/g['file']),'size':list(Image.open(RAW/g['file']).size)} for g in GEN],'fidelite_rip':fid,'layers':layer_list,'lave':{'phases':32,'frame_length_ticks':15,'palette':[list(c) for c in MTB_PAL],'periode_texture':list(MG.PERIOD),'cellule':MG.CELL,'drift':'une periode (96 px) vers le sud par boucle','pieds_cascade':[],'origine':'module source/magma_visqueux/magma.py adapte palette Mt Blaze ; pixels calcules Worley periodique' },'veines':{'phases':32,'frame_length_ticks':15,'palette':[list(c) for c in MTB_PAL],'pixels':int(vein_mask_down.sum()),'origine':'veines extraites du decor (orange dans roche) + fissures Worley fines, palette cycling frame par frame' },'scene_loop_ticks':LOOP_TICKS,'access':{'markers':markers,'paths_16x16':{'entrance->boss':{'ok':reachable2(blocked,entrance,boss)},'entrance->objectif':{'ok':reachable2(blocked,entrance,objectif)}},'blocked_cells':int(blocked.sum()),'total_cells':int(blocked.size),'walkable_cells':int((~blocked).sum()),'rule':'case bloquee si >25% hors sable','north_closed':True},'pmdo':{'target':'0.8.12','asset':ASSET,'namespace':NAMESPACE,'tiles_per_bank':counts,'banks':list(counts),'runtime_tested':False,'warp':'aucun'},'art_approved':False}
    (OUT/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    shutil.copyfile(HERE / 'README_PACK.md', OUT / 'README.md')
    shutil.copyfile(OUT/'manifest.json', STAGE/'manifest.json')
    print(json.dumps({'fidelite':{k:v['distance'] for k,v in fid.items()},'markers':markers,'blocked':int(blocked.sum()),'veines_px':int(vein_mask_down.sum()),'lava_phases':len(mf),'vein_phases':len(vf)},indent=1))

if __name__=='__main__':
    build()
