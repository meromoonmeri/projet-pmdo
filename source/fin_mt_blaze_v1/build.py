"""Fin Mt. Blaze (FMB1) — arène du cratère, 4:3 vaste (768 x 576), format 4:3 vaste (768 x 576 px, 96 x 72 cases).

Méthode propre multicalque référencée :
- decor.png : rendu généré RÉFÉRENCÉ avec images.jpg + Rescue_Team_-_Mt._Blaze_Entrance.png en images= (lave = magenta plat #FF00FF, cratère circulaire)
- sol_complet.png : édité depuis le décor (sable seul)
- base (sable, ombres, berge, roche, piliers, profondeur) : segmentation pleine rés. + down_class 8px
- lave : magma visqueux procédural (Worley, 32×15) palette Mt Blaze, palette cycling, cohérent au rip
- veines : fissures dans la roche, palette cycling 32×15
Boucle 480 ticks = 8 s. Aucun warp.

Lancer : .venv/bin/python source/fin_mt_blaze_v1/build.py
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
OUT = R / 'renders/fin_mt_blaze_v1'
STAGE = R / '.cache/fin_mt_blaze_v1/fin_mt_blaze'
NAMESPACE = 'fin_mt_blaze'
ASSET = 'fmb1_fin_mt_blaze'
PFX = 'FMB1'
W, H = 768, 576
SRC = (1200, 896)

MTB_CRUST = [(55, 18, 12), (95, 28, 16), (145, 45, 22)]
MTB_RAMP = [(165, 65, 30), (185, 95, 25), (205, 125, 22), (218, 140, 18), (232, 155, 12),
            (240, 170, 0), (240, 188, 12), (250, 210, 30), (255, 230, 60), (255, 255, 90)]
MTB_PAL = MTB_CRUST + MTB_RAMP
MTB_PAL_NP = np.array(MTB_PAL, 'uint8')

GEN = [
    {'file': 'decor.png', 'images': ['images.jpg', 'Rescue_Team_-_Mt._Blaze_Entrance.png'], 'prompt':
     'Use EXACTLY the same textures, palette and pixel-art style as the reference images (the volcano peak exterior with purple sky and the GBA Mt. Blaze Entrance): same beige cracked ground, same grey boulders, same orange-red lava. Make a NEW, larger top-down map, WIDE LANDSCAPE 4:3, zoomed out. Layout: a closed circular crater arena surrounded by grey cliffs, the player arrives at the SOUTH on beige sand; the center and NORTH are a vast LAVA CRATER (entire lava surface flat pure magenta #FF00FF, no gradient), with a small safe rock platform in the middle for the boss, and rock causeways. Grey boulders in lava, dark walls around. No characters, no text, no UI, no border.',
     'essais': 'genere reference volcan exterieur + GBA, cratere central 20% magenta, 1200x896'},
    {'file': 'sol_complet.png', 'images': ['source/fin_mt_blaze_v1/bruts/decor.png'], 'prompt':
     'Same image, same framing and pixel-art style, but only beige cracked sandy ground everywhere, replacing all lava (magenta), grey rocks and dark walls with the same beige cracked sand texture, keeping the exact sand palette, no magenta remaining.',
     'essais': 'edite depuis decor (magenta->sable, rochers sous calque roche)'},
]

def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

JM = loadmod('ejn1_outils', R / 'source/entree_jungle_sud_nord_v1/build.py')
BM = JM.BM
MG = loadmod('magma_visqueux', R / 'source/magma_visqueux/magma.py')
GR = loadmod('magma_ground', R / 'source/magma_visqueux/ground.py')
assert (JM.W, JM.H, JM.SRC) == (W, H, SRC)
MG.PAL = MTB_PAL
MG.PAL_NP = MTB_PAL_NP
MG.RIP_RAMP = MTB_RAMP
MG.CROUTE = MTB_CRUST
MG.N_RIP0 = len(MTB_CRUST)
S = JM.SCALE
LOOP_TICKS = 480

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

def classify(a, f):
    r, g, b = a.transpose(2, 0, 1); lum = a @ [.299, .587, .114]
    hh, ww = lum.shape; yy, xx = np.mgrid[:hh, :ww]
    water = nd.binary_dilation((r - g > 60) & (b - g > 60), iterations=2)
    # pour FMB1 le cratère est central, pas de grotte nord : on cherche cavité sombre si présente, sinon vide
    dark = (lum < 48) & (yy < 260) & (xx > 450) & (xx < 750)
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
    m = rock_union & (r>100) & (g<120) & (b<100) & (r - g > 20) & (r > b)
    m = nd.binary_dilation(m, iterations=1) & rock_union
    m = nd.binary_opening(m, iterations=1)
    if m.sum() < 0.005 * rock_union.sum():
        H0,W0 = a.shape[:2]
        yy, xx = np.mgrid[:H0,:W0].astype(float)
        try:
            f1,f2,_ = MG.worley(xx*0.7, yy*0.7, P=(192,96), cell=14, seed=11)
            q = 2*f1/(f1+f2+1e-9)
            fiss = (q > 0.82) & rock_union
            m = m | fiss
        except Exception:
            pass
    return m

def vein_frames(vein_mask_down, H, W, phases=32):
    if not vein_mask_down.any():
        return [np.zeros((H,W,4),'uint8') for _ in range(phases)]
    dist = nd.distance_transform_edt(vein_mask_down)
    yy,xx = np.mgrid[:H,:W].astype(float)
    try:
        f1,f2,_ = MG.worley(xx*1.0, yy*1.0, P=MG.PERIOD, cell=18, seed=11)
        q = 2*f1/(f1+f2+1e-9)
        mod = (q*1.5).astype(float)
    except Exception:
        mod = np.zeros((H,W))
    base = np.clip(dist*1.2 + mod, 0, 6)
    frames=[]
    for t in range(phases):
        shift = t
        lvl = base + shift*0.35 + 0.6*np.sin(2*np.pi*t/phases + mod*2)
        idx = np.clip(np.rint(lvl + 3).astype(int), 3, 12)
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
    mf, dist, midx = MG.magma_phases(ex['water'], visible & ex['water'], feet=(), drift=(0,1), seed=5, crust=0.12, phases=32)
    vein_mask_down = ex['veines']
    vf = vein_frames(vein_mask_down, H, W, phases=32)
    stack_named = [('lave', mf, 15), ('sol_complet', [layers['sol_complet']], 60), ('sable', [layers['sable']],60), ('ombres', [layers['ombres']],60), ('berge', [layers['berge']],60), ('roche', [layers['roche']],60), ('piliers', [layers['piliers']],60), ('profondeur', [layers['profondeur']],60), ('veines', vf, 15)]
    for i,(nm,frames,ticks) in enumerate(stack_named):
        if len(frames)==1:
            Image.fromarray(frames[0]).save(OUT/f'calques/{PFX}_{i:02d}_{nm}.png')
        else:
            for t,fr in enumerate(frames):
                d = OUT/f'animation/{nm}'
                d.mkdir(parents=True, exist_ok=True)
                Image.fromarray(fr).save(d/f'{PFX}_{i:02d}_{nm}_f{t:02d}.png')
    # collisions
    walk_px = (layers['sable'][...,3]==255) | (layers['ombres'][...,3]==255)
    blocked = BM.cell_grid(~walk_px); gh_,gw_ = blocked.shape
    # Entrance sud
    pxs = np.nonzero(walk_px[H-8])[0]; med = int(np.median(pxs))//8 if len(pxs) else W//16
    ecol = min((c for c in range(gw_-1) if not blocked[gh_-2:, c:c+2].any()), key=lambda c: abs(c-med)) if med else 48
    entrance = [ecol*8+8, H-16]
    # Boss : centre du cratère (plateforme centrale)
    # On cherche la plateforme "piliers" ou "roche" au centre ? Pour FMB1, le cratère a une petite plateforme centrale (isolée)
    # On utilise le centre géométrique 384,288 et cherche 2x2 walkable le plus proche
    # Mais pour FMB1 la plateforme est plus au nord (232) ; on cherche d'abord autour de 384,232 comme validé
    target_boss = (232, 384)  # y,x
    best=None; bestd=1e9
    for y in range(gh_):
        for x in range(gw_):
            if not blocked[y:y+2, x:x+2].any():
                d=(y*8-target_boss[0])**2 + (x*8-target_boss[1])**2
                if d<bestd:
                    bestd,best=d,[x*8,y*8]
    boss = best if best else [384,232]
    # Objectif : même plateforme légèrement décalé (comme validé [376,224])
    # On cherche walkable près de boss mais pas exactement même case
    objectif = [boss[0]-8, boss[1]-8]
    if blocked[objectif[1]//8:objectif[1]//8+2, objectif[0]//8:objectif[0]//8+2].any():
        objectif = boss[:]
    markers={'entrance':entrance,'boss':boss,'objectif':objectif}
    def reachable2(b,src,dst):
        return v1.reachable(b,(src[1]//8,src[0]//8),(dst[1]//8,dst[0]//8))[0]
    assert reachable2(blocked, entrance, boss), 'chemin entrance->boss bloque'
    assert reachable2(blocked, entrance, objectif), 'chemin entrance->objectif bloque'
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
    import xml.etree.ElementTree as ET
    root=ET.Element('image', w=str(W),h=str(H), name='Fin Mt. Blaze 4:3 (FMB1)')
    stack=ET.SubElement(root,'stack'); comp=Image.new('RGBA',(W,H))
    with zipfile.ZipFile(OUT/f'{PFX}_fin_mt_blaze_calques.ora','w', zipfile.ZIP_DEFLATED) as z:
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
    counts=GR.ground_project([(t.replace('_',' ')+(f' {len(fr)} phases' if len(fr)>1 else ''), fr, tk) for t,fr,tk in stack_named], blocked, markers, gfx, tools, stage=STAGE, pfx=PFX, asset=ASSET, namespace=NAMESPACE, here=HERE, W=W, H=H, name='Fin Mt. Blaze - Cratere 4:3 (FMB1)', comment='PMDO 0.8.12. Arene Mt. Blaze generee reference ; cratere de lave visqueuse, veines palette cycling. Aucun warp.', mod_name='Fin Mt. Blaze (FMB1) 4:3', mod_desc="Projet d'édition : fin Mt. Blaze 4:3, cratere de lave visqueuse et veines.")
    fid=fidelity(a,ref)
    layer_list=[]
    for i,(nm,frames,ticks) in enumerate(stack_named):
        if len(frames)>1:
            layer_list.append({'file':f'animation/{nm}/{PFX}_{i:02d}_{nm}_fNN.png','phases':len(frames),'ticks':ticks})
        else:
            layer_list.append({'file':f'calques/{PFX}_{i:02d}_{nm}.png','phases':1,'ticks':60})
    manifest={'lot':'fin_mt_blaze_v1','prefix':PFX,'format':'4:3 vaste','size_px':[W,H],'grid_8px':[W//8,H//8],'biome':'Mt. Blaze (cratere)','method':'rendu genere reference : decor magenta+vert ; base quantifiee ; lave visqueuse Worley palette Mt Blaze + veines palette cycling','reference_da':{'file':REF.name,'sha256':sha(REF)},'generation':GEN,'raw_inputs':[{'file':f'source/fin_mt_blaze_v1/bruts/{g["file"]}','sha256':sha(RAW/g['file']),'size':list(Image.open(RAW/g['file']).size)} for g in GEN],'fidelite_rip':fid,'layers':layer_list,'lave':{'phases':32,'frame_length_ticks':15,'palette':[list(c) for c in MTB_PAL],'periode_texture':list(MG.PERIOD),'cellule':MG.CELL,'drift':'une periode vers le sud','pieds_cascade':[],'origine':'magma_visqueux adapte Mt Blaze'},'veines':{'phases':32,'frame_length_ticks':15,'palette':[list(c) for c in MTB_PAL],'pixels':int(vein_mask_down.sum()),'origine':'veines extraites + Worley fines, palette cycling'},'scene_loop_ticks':LOOP_TICKS,'access':{'markers':markers,'paths_16x16':{'entrance->boss':{'ok':reachable2(blocked,entrance,boss)},'entrance->objectif':{'ok':reachable2(blocked,entrance,objectif)}},'blocked_cells':int(blocked.sum()),'total_cells':int(blocked.size),'walkable_cells':int((~blocked).sum()),'rule':'case bloquee si >25% hors sable','north_closed':True},'pmdo':{'target':'0.8.12','asset':ASSET,'namespace':NAMESPACE,'tiles_per_bank':counts,'banks':list(counts),'runtime_tested':False,'warp':'aucun'},'art_approved':False}
    (OUT/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    shutil.copyfile(HERE / 'README_PACK.md', OUT / 'README.md')
    shutil.copyfile(OUT/'manifest.json', STAGE/'manifest.json')
    print(json.dumps({'fidelite':{k:v['distance'] for k,v in fid.items()},'markers':markers,'blocked':int(blocked.sum()),'veines_px':int(vein_mask_down.sum()),'lava_phases':len(mf)},indent=1))

if __name__=='__main__':
    build()
