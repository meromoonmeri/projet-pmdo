"""FCT1 — fin de Clairière tropicale, suite d'ETC1. Rendu généré référencé, 4:3 PMDO.

Bruts créés à partir du rip de Clairière tropicale (ETC1) : décor, sol complet et édition sur magenta qui sert
uniquement de témoin de segmentation. Les pixels d'objets viennent du décor retenu, pas du témoin. Aucun tile natif
n'est revendiqué. Construction, export PNG/ORA/Ground et collisions reproductibles par ce script.
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = HERE / 'bruts'
OUT = ROOT / 'renders/fin_clairiere_tropicale_v1'
STAGE = ROOT / '.cache/fin_clairiere_tropicale_v1/fin_clairiere_tropicale'
REF = ROOT / 'large.S01P03A.png.84e22fb77c4061e77b0f546545fed2c7.png'
PFX, ASSET, NS = 'FCT1', 'fct1_fin_clairiere_tropicale', 'fin_clairiere_tropicale'
W, H, SRC = 768, 576, (1200, 896)
PHASES, TICKS, LOOP = 24, 5, 120


def loadmod(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

# Le normaliseur par classes est le même que les maps PMDO 4:3 déjà livrées.
JM = loadmod('fct1_jungle_utils', ROOT / 'source/entree_jungle_sud_nord_v1/build.py')
JM.BM.W, JM.BM.H = W, H
DOWNSCALE, DOWNFULL, RGBA = JM.down_class, JM.down_full, JM.rgba
CELL_GRID = JM.cell_grid
ESN = loadmod('fct1_access', ROOT / 'source/entree_sud_nord_generee_v1/build.py')
ETC = loadmod('fct1_etc1', ROOT / 'source/entree_clairiere_tropicale_sud_nord_v1/build.py')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rgb(path): return np.asarray(Image.open(path).convert('RGB'), dtype=np.int32)


def classify(a, objguide):
    """Class masks at original 1200x896. The magenta edit is a segmentation witness, not final source art."""
    r, g, b = a.transpose(2, 0, 1)
    mag = ((objguide[..., 0] > 180) & (objguide[..., 1] < 110) & (objguide[..., 2] > 180) &
           (objguide[..., 0] - objguide[..., 1] > 90) & (objguide[..., 2] - objguide[..., 1] > 90))
    ground = mag
    lum = a @ [.299, .587, .114]
    # The magenta guide marks the open grass floor; the canonical tan stepping stones remain visible as objects.
    obj = ~mag
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    path_area = (xx > 390) & (xx < 810) & (yy > 70)
    path_stones = obj & path_area & (r > g + 12) & (g > b + 16) & (lum > 125)
    sand = path_stones
    grass = ground
    # The only liquid is a contiguous southern sea band. Infer its shoreline from the first blue sea pixel per column;
    # fill below that edge so bright wave crests do not create holes in the water mask.
    blue = (b > r + 35) & (b > g - 20) & (yy > 760)
    first=[]
    for x in range(a.shape[1]):
        q=np.flatnonzero(blue[:,x]);first.append(float(q.min()) if len(q) else np.nan)
    valid=np.flatnonzero(np.isfinite(first)); rows=np.interp(np.arange(a.shape[1]),valid,np.asarray(first)[valid])
    rows=nd.median_filter(rows,size=51)
    sea_region=yy >= rows[None,:]
    water = obj & sea_region & ~path_stones
    # Saturated canonical flower clusters, with their shadows/green leaves remaining in the vegetation layer.
    sat = a.max(2) - a.min(2)
    flower_color = (((r > g + 32) & (r > b + 18)) | ((b > r + 20) & (b > g + 5)) |
                    ((r > 180) & (g > 145) & (r > g + 5) & (g > b + 35)))
    flowers = obj & (sat > 48) & flower_color & ~water & ~path_stones
    # Foreground border foliage is isolated so it can be rendered above the player layer (Top remains empty).
    canopy = obj & (yy >= 748) & ~water & ~flowers & ~path_stones
    # Small neutral pebbles and stones, excluding the tan path stones and southern sea.
    neutral = (a.max(2) - a.min(2) < 55) & (lum > 115)
    rock_area = (yy > 220) & (xx > 140) & (xx < 1060)
    rocks = obj & neutral & rock_area & ~water & ~flowers & ~canopy & ~path_stones
    vegetation = obj & ~water & ~flowers & ~rocks & ~canopy & ~path_stones
    masks = {'herbe': grass, 'sable': sand, 'eau': water, 'jungle': vegetation,
             'fleurs': flowers, 'rochers': rocks, 'canopee': canopy}
    # Hard partition: no source pixel is assigned twice; all object pixels and all ground pixels are represented.
    vals = list(masks.values())
    assert all(not (vals[i] & vals[j]).any() for i in range(len(vals)) for j in range(i + 1, len(vals)))
    assert np.logical_or.reduce(vals).all()
    return masks, {'ground_px': int(ground.sum()), 'object_px': int(obj.sum()), 'magenta_witness_px': int(mag.sum()),
                   'classes': {k: int(v.sum()) for k,v in masks.items()},
                   'unclassified_ground_px': int((ground & ~(grass | sand)).sum())}


def shadow_layer(decor, masks):
    """Subtle dark pixels actually present in the generated ground around object edges, isolated as an editable layer."""
    ground = masks['herbe'] | masks['sable']; obj = ~ground
    near = nd.binary_dilation(obj, iterations=10) & ground
    lum = decor @ [.299, .587, .114]
    # Use source ground tones only where they are darker than local full-ground witness; preserve exact source pixels.
    full = rgb(RAW / 'sol_complet.png') @ [.299, .587, .114]
    dark = near & (lum + 12 < full) & (lum > 20)
    return nd.binary_opening(dark, iterations=1)


def canonical_sea_frames(mask):
    """Reuse the ETC1 sea cycle: wave pixels/palette come from the canonical rip, not a new AI water texture."""
    srcdir=ROOT/'renders/entree_clairiere_tropicale_sud_nord_v1/animation/mer'
    frames=[]
    for t in range(PHASES):
        src=np.asarray(Image.open(srcdir/f'ETC1_13_mer_f{t:02d}.png').convert('RGBA'))
        out=np.zeros((H,W,4),dtype=np.uint8)
        # Keep the 62 px at the bottom of the exact ETC1 wave layout; align it to FCT1's generated south shoreline.
        out[514:]=src[514:]
        out[~mask]=0
        frames.append(out)
    palette=sorted({tuple(int(v) for v in c) for a in frames for c in np.unique(a[a[...,3]>0,:3],axis=0)})
    assert len(frames)==PHASES and all(a.shape==(H,W,4) for a in frames)
    return frames,palette


def butterflies():
    """Reuse the generated ETC1 pose sheet; closed eight-flight paths are newly composed, poses are unchanged."""
    pose_dir=ROOT/'renders/entree_clairiere_tropicale_sud_nord_v1/poses'
    poses={c:[np.asarray(Image.open(pose_dir/f'ETC1_{c}_{i}.png').convert('RGBA')) for i in range(6)]
           for c in ('jaune','orange')}
    flights=[('orange',235,330,62,34,0),('jaune',520,355,55,28,8),('orange',390,235,45,24,15)]
    frames=[]; tracks=[]
    for t in range(PHASES):
        canvas=np.zeros((H,W,4),dtype=np.uint8); positions=[]
        for color,cx,cy,ax,ay,off in flights:
            u=2*np.pi*(t+off)/PHASES
            x=int(round(cx+ax*np.sin(u))); y=int(round(cy+ay*np.sin(2*u)))
            pose=poses[color][((t+off)//2)%6]
            ph,pw=pose.shape[:2]; x0=x-pw//2; y0=y-ph//2
            m=pose[...,3]>0; canvas[y0:y0+ph,x0:x0+pw][m]=pose[m]
            positions.append([x,y])
        frames.append(canvas); tracks.append(positions)
    return frames,tracks


def write_ora(path, stack):
    import xml.etree.ElementTree as ET
    root=ET.Element('image',w=str(W),h=str(H),name='FCT1 Fin Clairiere tropicale'); st=ET.SubElement(root,'stack')
    comp=Image.new('RGBA',(W,H))
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
        for i,(name,frames,ticks) in reversed(list(enumerate(stack))):
            fn=f'data/layer{i:02d}.png'; ET.SubElement(st,'layer',name=name,src=fn,x='0',y='0',opacity='1.0',visibility='visible',**{'composite-op':'svg:src-over'})
            buf=io.BytesIO(); Image.fromarray(frames[0]).save(buf,format='PNG'); z.writestr(fn,buf.getvalue())
        for _,frames,_ in stack: comp.alpha_composite(Image.fromarray(frames[0]))
        for name,im in [('mergedimage.png',comp)]:
            buf=io.BytesIO(); im.save(buf,format='PNG'); z.writestr(name,buf.getvalue())
        th=comp.copy();th.thumbnail((256,256));buf=io.BytesIO();th.save(buf,format='PNG');z.writestr('Thumbnails/thumbnail.png',buf.getvalue())
        z.writestr('stack.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True))


def ground_project(stack, blocked, markers, gfx, tools):
    if STAGE.exists(): shutil.rmtree(STAGE)
    with zipfile.ZipFile(ROOT/'mod_metano_expeditions_pmdo_0812.zip') as z:
        tpl=json.loads(z.read('metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground'))
    obj=tpl['Object']; gw,gh=W//8,H//8; native_layers=[]; banks=[]
    for i,(title,frames,ticks) in enumerate(stack):
        bank=gfx.TileBank(f'{PFX}_{i:02d}_{title.upper()}'); bank.ids[bytes(256)]=(0,0);bank.data[(0,0)]=bytes(256)
        def cell(x,y,frames=frames,bank=bank):
            refs=[]
            for arr in frames:
                ref=bank.add(Image.fromarray(arr[y*8:y*8+8,x*8:x*8+8]),x,y)
                refs.append(ref or {'Sheet':bank.name,'TexLoc':{'X':0,'Y':0}})
            if all(v['TexLoc']=={'X':0,'Y':0} for v in refs): return []
            return [refs[0]] if all(v==refs[0] for v in refs) else refs
        native_layers.append(gfx.layer(f'{i:02d} {title}',gw,gh,cell,ticks));banks.append(bank)
    native_layers.append(gfx.layer(f'{len(stack):02d} Top vide',gw,gh,draw=4))
    for bank in banks: bank.write(STAGE/f'Content/Tile/{bank.name}.tile')
    obj.update(Name={'DefaultText':'FCT1 - Fin Clairiere tropicale (4:3)','LocalTexts':{}},AssetName=ASSET,Released=False,
               TexSize=1,Music='',EdgeView=1,ViewCenter=None,ViewOffset={'X':0,'Y':0},ActiveChar=None,Status={},Layers=native_layers,
               Background={'$type':'RogueEssence.Dungeon.LayeredBG, RogueEssence','Layers':[]},
               Comment='PMDO 0.8.12. Rendu genere reference sur le rip canonique ETC1. Calques et collisions de base; aucune sortie ni warp. Art non approuve, runtime non teste.')
    obj['obstacles']=[[{'Bounds':{'X':x*8,'Y':y*8,'Width':8,'Height':8},'Tags':int(blocked[y,x])} for y in range(gh)] for x in range(gw)]
    marker=lambda name,p:{'EntName':name,'Direction':4,'EntEnabled':True,'triggerType':0,'Collider':{'X':p[0],'Y':p[1],'Width':16,'Height':16}}
    obj['Entities']=[{'Name':'Marqueurs de la fin','Visible':True,'MapChars':[],'GroundObjects':[],'Spawners':[],
                      'Markers':[marker(n,p) for n,p in markers.items()]}]
    obj['Decorations']=[{'Name':'Decorations','Layer':2,'Visible':True,'Anims':[]}]
    tpl['Version']='0.8.12.0'
    gfx.save(STAGE/f'Data/Ground/{ASSET}.rsground',json.dumps(tpl,ensure_ascii=False,separators=(',',':')).encode())
    gfx.save(STAGE/f'Data/Script/{NS}/ground/{ASSET}/init.lua',f'-- {ASSET}; aucun warp.\nlocal {ASSET} = {{}}\nreturn {ASSET}\n'.encode())
    nodes={}
    for p in sorted((STAGE/'Content/Tile').glob('*.tile')):
        with p.open('rb') as f:nodes[p.stem]=tools.read_node(f)
    (STAGE/'Content/Tile/index.idx').write_bytes(tools.encode_index(nodes))
    uid=uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/meromoonmeri/projet-pmdo/'+NS)
    (STAGE/'Mod.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>\n<Header><Name>Fin Clairiere tropicale FCT1</Name><Author>meromoonmeri</Author><Description>Atelier PMDO 0.8.12, arene finale tropicale en 4:3, calques separables, animations creees.</Description><Namespace>{NS}</Namespace><UUID>{uid}</UUID><Version>1.0.0.0</Version><GameVersion>0.8.12.0</GameVersion><ModType>Quest</ModType><Relationships /></Header>\n''')
    installer=(ROOT/'source/pmdo_cote/INSTALLER.py').read_text(); needle='            relative = src.relative_to(source)\n'
    assert needle in installer
    installer=installer.replace(needle,needle+"            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n")
    (STAGE/'INSTALLER.py').write_text(installer)
    shutil.copyfile(HERE/'README_PACK.md',STAGE/'README.md')
    return {b.name:len(b.data) for b in banks}


def build():
    gfx=loadmod('fct1_codec',ROOT/'source/pmdo_cote/build.py'); tools=loadmod('fct1_index',ROOT/'source/pmdo_cote/INSTALLER.py')
    for sub in ['calques','animation','masques','review','poses']:
        shutil.rmtree(OUT/sub,ignore_errors=True);(OUT/sub).mkdir(parents=True,exist_ok=True)
    for sub in ['animation/reflets_eau','animation/reflet_objectif']:(OUT/sub).mkdir(parents=True,exist_ok=True)
    for sub in ['eau','papillons']:(OUT/'animation'/sub).mkdir(parents=True,exist_ok=True)
    a=rgb(RAW/'decor.png'); f=rgb(RAW/'sol_complet.png'); guide=rgb(RAW/'objets_magenta.png'); ref=rgb(REF)
    assert a.shape==f.shape==guide.shape==(SRC[1],SRC[0],3)
    masks,seg=classify(a,guide)
    names=['herbe','sable','eau','jungle','fleurs','rochers','canopee']
    ex,cols=DOWNSCALE(a,masks,names)
    layers={'sol_complet':RGBA(DOWNFULL(f),np.ones((H,W),bool))}
    for n in names: layers[n]=RGBA(cols[n],ex[n])
    # Shadows are sampled from the actual decor, only where they sit next to foreground masses.
    sm=shadow_layer(a,masks); smx,scols=DOWNSCALE(a,{'ombres':sm},['ombres']);layers['ombres']=RGBA(scols['ombres'],smx['ombres'])
    # Restrained palettes per material family, alpha remains binary.
    grp={}
    for keys,limit in [(['sol_complet','herbe','sable','ombres'],96),(['eau','jungle','fleurs','rochers','canopee'],128)]:
        grp.update(ETC.quantize_group({k:layers[k] for k in keys},limit))
    layers=grp
    # Discard the generated water RGB. Keep only its shoreline mask, fill from the canonical rip palette, and reuse ETC1's
    # exact reference-derived wave pixels/profile for the animated layer.
    watermask=layers['eau'][...,3]==255
    del layers['eau']
    base=np.zeros((H,W,4),dtype=np.uint8);base[watermask]=(*ETC.BANDE,255);layers['mer_base']=base
    mer_frames,waterpal=canonical_sea_frames(watermask)
    bf,tracks=butterflies()
    # save editable masks
    for n,m in masks.items():Image.fromarray((m*255).astype('uint8')).save(OUT/'masques'/f'{PFX}_masque_{n}.png')
    Image.fromarray((watermask*255).astype('uint8')).save(OUT/'masques'/f'{PFX}_masque_eau_export.png')
    walk=(layers['herbe'][...,3]==255)|(layers['sable'][...,3]==255)|(layers['ombres'][...,3]==255)
    # Slightly soften false blockages from small generated flowers/texture specks but keep walls blocked.
    blocked=CELL_GRID(~walk)
    # Entry at south, boss in the open arena, objective at the north end of the canonical stepping-stone path.
    free=lambda x,y: 0<=x<W//8-1 and 0<=y<H//8-1 and not blocked[y:y+2,x:x+2].any()
    candidates=[(x,y) for y in range(H//8) for x in range(W//8) if free(x,y)]
    entry_c=min((p for p in candidates if p[1]>=H//8-4),key=lambda p:abs(p[0]-W//16))
    boss_c=min(candidates,key=lambda p:(p[0]-W//16)**2+(p[1]-(H//8*5//8))**2)
    obj_c=min((p for p in candidates if p[1]<H//8//2),key=lambda p:(p[0]-W//16)**2+(p[1]-H//8//4)**2)
    markers={'entrance':[entry_c[0]*8,entry_c[1]*8],'boss':[boss_c[0]*8,boss_c[1]*8],'objectif':[obj_c[0]*8,obj_c[1]*8]}
    paths={}
    for key,c in [('boss',boss_c),('objectif',obj_c)]:
        ok,n=ESN.reachable(blocked,(entry_c[1],entry_c[0]),(c[1],c[0]));paths[key]={'ok':bool(ok),'explored':int(n)}
        assert ok,('16x16 access blocked',key,markers)
    stack=[]
    static=['sol_complet','mer_base','herbe','sable','ombres','jungle','rochers','fleurs','canopee']
    anim={'mer':mer_frames,'papillons':bf}
    ticks={'mer':TICKS,'papillons':TICKS}
    order=static+list(anim)
    for i,n in enumerate(order):
        frames=anim[n] if n in anim else [layers[n]]; tk=ticks.get(n,60)
        stack.append((n,frames,tk))
        folder=(OUT/'animation'/n) if n in anim else (OUT/'calques')
        folder.mkdir(parents=True,exist_ok=True)
        for t,arr in enumerate(frames):
            fn=f'{PFX}_{i:02d}_{n}_f{t:02d}.png' if len(frames)>1 else f'{PFX}_{i:02d}_{n}.png'
            Image.fromarray(arr).save(folder/fn)
    def scene(tick):
        out=Image.new('RGBA',(W,H))
        for _,frames,tk in stack:out.alpha_composite(Image.fromarray(frames[(tick//tk)%len(frames)]))
        return out
    scenes=[scene(t) for t in range(0,LOOP,5)]
    scenes[0].save(OUT/'review'/f'{PFX}_scene_t000.png')
    scenes[0].save(OUT/'review'/f'{PFX}_scene_animee.webp',save_all=True,append_images=scenes[1:],duration=round(5*1000/60),loop=0,lossless=True)
    coll=scenes[0].copy();ov=Image.new('RGBA',(W,H));d=ImageDraw.Draw(ov)
    for y,x in zip(*np.nonzero(blocked)):d.rectangle((x*8,y*8,x*8+7,y*8+7),fill=(220,40,40,90))
    for k,c in [('entrance',(255,230,40,255)),('boss',(255,60,220,255)),('objectif',(60,220,255,255))]:
        x,y=markers[k];d.rectangle((x,y,x+15,y+15),outline=c,width=2)
    coll.alpha_composite(ov);coll.save(OUT/'review'/f'{PFX}_collisions_marqueurs.png')
    write_ora(OUT/f'{PFX}_fin_clairiere_calques.ora',stack)
    static_layers=[(n,frames,tk) for n,frames,tk in stack]
    counts=ground_project(static_layers,blocked,markers,gfx,tools)
    fid=ETC.fidelity(a,ref)
    raw=[]
    for fn,images,purpose in [('decor.png',[REF.name],'décor complet référencé'),('sol_complet.png',[f'source/fin_clairiere_tropicale_v1/bruts/decor.png'],'témoin terrain complet édité depuis le décor'),('objets_magenta.png',[f'source/fin_clairiere_tropicale_v1/bruts/decor.png'],'témoin de segmentation magenta; jamais exporté comme texture')]:
        p=RAW/fn;raw.append({'file':f'source/fin_clairiere_tropicale_v1/bruts/{fn}','sha256':sha(p),'size':list(Image.open(p).size),'references':images,'purpose':purpose})
    manifest={'lot':'fin_clairiere_tropicale_v1','prefix':PFX,'biome':'Clairière tropicale, prolongement de l entrée ETC1; choix agent à confirmer',
      'format':'4:3 vaste','size_px':[W,H],'grid_8px':[W//8,H//8],
      'method':'Textures canoniques = rendu généré référencé sur le rip PMD Sky de Clairière tropicale. Le témoin magenta sert uniquement à segmenter; ce ne sont ni des pixels natifs ni des tuiles canoniques.',
      'reference':{'file':REF.name,'sha256':sha(REF),'related_entry':'ETC1'},'generation':[
       {'file':'decor.png','images':[REF.name],'prompt':'Carte 4:3 de fin de donjon tropicale référencée sur la capture PMD Sky: arène centrale dégagée en herbe, chemin de dalles canoniques et mer à bandes bleues uniquement au sud; végétation/palmiers/fleurs dans les mêmes textures et palette. Aucun fruit, autel, cascade, rivière ni eau derrière la carte.'},
       {'file':'sol_complet.png','images':['decor.png'],'prompt':'Édition alignée du décor, sous-couche complète herbe/sable; objets et mer retirés.'},
       {'file':'objets_magenta.png','images':['decor.png'],'prompt':'Édition du même layout, sol herbeux ouvert remplacé par magenta pur, mer sud, dalles et végétation gardées; témoin de segmentation uniquement.'}],
      'raw_inputs':raw,'segmentation':seg,'fidelity_rgb':fid,
      'normalization':{'scale':H/SRC[1],'target':[W,H],'method':'moyenne pondérée par classe BOX, gagnant de poids maximal; couleurs quantifiées par groupes terrain/objets'},
      'layers':[{'name':n,'file':(f'animation/{n}/' if len(fr)>1 else 'calques/')+f'{PFX}_{i:02d}_{n}_fNN.png' if len(fr)>1 else f'calques/{PFX}_{i:02d}_{n}.png','phases':len(fr),'ticks':tk} for i,(n,fr,tk) in enumerate(stack)],
      'animations':{'mer':{'phases':PHASES,'ticks_per_phase':TICKS,'palette_sampled_from_render':waterpal,'origin':'pixels/profil de vagues repris sans resampling depuis le calque ETC1, lui-même construit avec les couleurs et la crête du rip; cadence et déroulement non officiels'},
                    'butterflies':{'phases':PHASES,'ticks_per_phase':TICKS,'tracks_px':tracks,'origin':'poses magenta générées et déjà découpées pour ETC1, réutilisées sans modification; trajectoires composées pour FCT1'}},
      'scene_loop_ticks':LOOP,'access':{'markers':markers,'path_16x16':paths,'blocked_cells':int(blocked.sum()),'total_cells':int(blocked.size),'rule':'case bloquée si >25% non praticable; herbe/sable/ombres praticables','warp':'aucun'},
      'pmdo':{'target':'0.8.12','asset':ASSET,'namespace':NS,'tiles_per_bank':counts,'runtime_tested':False},'art_approved':False}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    shutil.copyfile(HERE/'README_PACK.md',OUT/'README.md');shutil.copyfile(OUT/'manifest.json',STAGE/'manifest.json')
    print(json.dumps({'markers':markers,'paths':paths,'fidelity':fid,'segmentation':seg,'layers':{k:int(v[...,3].sum()/255) for k,v in layers.items()},'tiles':sum(counts.values())},indent=2))

if __name__=='__main__':build()
