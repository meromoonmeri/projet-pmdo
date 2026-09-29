"""FVC1 — Fin Couloir violet, suite d'ECV1. Rendu généré référencé, exportable en calques et Ground PMDO."""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, zipfile
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RAW=HERE/'bruts'
OUT=ROOT/'renders/fin_couloir_violet_v1'
STAGE=ROOT/'.cache/fin_couloir_violet_v1/fin_couloir_violet'
REF=ROOT/'large.S05P03A.png.301f7a1eadda348357be0801e81faa2a.png'
PFX='FVC1'; ASSET='fvc1_fin_couloir_violet'; NS='fin_couloir_violet'
W,H,SRC=768,576,(1200,896)
PHASES,TICKS,LOOP=24,5,120


def loadmod(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rgb(p):return np.asarray(Image.open(p).convert('RGB'),dtype=np.int32)

J=loadmod('fvc_jungle',ROOT/'source/entree_jungle_sud_nord_v1/build.py')
DOWN=J.down_class; DOWNFULL=J.down_full; RGBA=J.rgba
ESN=loadmod('fvc_access',ROOT/'source/entree_sud_nord_generee_v1/build.py'); ESN.W,ESN.H=W,H; CELL=ESN.cell_grid
Q=loadmod('fvc_quantizer',ROOT/'source/entree_waterfall_cave_sud_nord_v1/build.py')


def masks_of(a,guide):
    lum=a@np.array([.299,.587,.114])
    mag=((guide[...,0]>180)&(guide[...,1]<105)&(guide[...,2]>180)&
         (guide[...,0]-guide[...,1]>80)&(guide[...,2]-guide[...,1]>80))
    floor=mag; obj=~mag
    # Void is only the very dark exterior connected to the image boundary; boulders stay in the rock layer.
    dark=(a.max(2)<29)
    labels,n=nd.label(dark); border=np.unique(np.concatenate([labels[0],labels[-1],labels[:,0],labels[:,-1]]));
    void=np.isin(labels,border[border>0])
    solid=obj&~void
    # Detect isolated, small reference-like pebbles near the chamber floor, never the continuous wall masses.
    near=nd.binary_dilation(floor,iterations=18)
    lab,n=nd.label(solid,structure=np.ones((3,3),dtype=bool)); sizes=np.bincount(lab.ravel())
    pebble_ids=np.flatnonzero((sizes>=28)&(sizes<=1500)); pebble_ids=pebble_ids[pebble_ids!=0]
    pebbles=np.isin(lab,pebble_ids)&near
    # Components may cross the near-floor boundary; trim them to the small interior rock pieces only.
    pebbles &= solid & near
    walls=solid&~pebbles
    return {'sol':floor,'ombres':np.zeros_like(floor),'gravillons':pebbles,'parois':walls,'vide':void}, {'magenta_floor_px':int(floor.sum()),'void_px':int(void.sum()),'pebble_px':int(pebbles.sum()),'wall_px':int(walls.sum()),'pebble_components':int(len(pebble_ids))}


def make_underlay(a,floor):
    """Full opaque editable substrate from a clean, valid patch of the generated canonical floor; visible floor overlays it."""
    # Large safe floor window in the open arena, nearest-valid fill excludes any pebble accidentally in the crop.
    y0,y1,x0,x1=350,610,430,770
    patch=a[y0:y1,x0:x1].copy(); pm=floor[y0:y1,x0:x1]
    if pm.mean()<.65:
        pts=np.argwhere(floor)
        cy,cx=pts.mean(0).astype(int); y0=max(0,min(SRC[1]-224,cy-112));x0=max(0,min(SRC[0]-224,cx-112))
        patch=a[y0:y0+224,x0:x0+224].copy();pm=floor[y0:y0+224,x0:x0+224]
    _,inds=nd.distance_transform_edt(~pm,return_indices=True); patch[~pm]=patch[inds[0][~pm],inds[1][~pm]]
    th,tw=patch.shape[:2]; tiled=np.tile(patch,(int(np.ceil(SRC[1]/th)),int(np.ceil(SRC[0]/tw)),1))[:SRC[1],:SRC[0]]
    Image.fromarray(tiled.astype('uint8')).save(RAW/'sol_complet.png')
    return tiled.astype(np.int32)


def create_shadows(a,floor,walls):
    # Keep only the darker source floor pixels directly next to the rocky edge, as a separate editable band.
    dist=nd.distance_transform_edt(~walls); lum=a@np.array([.299,.587,.114]);
    core=lum[floor]
    threshold=np.percentile(core,45)
    return floor&(dist<=20)&(lum<threshold)


def pebble_frames(walk,positions,poses):
    frames=[]; tracks=[]
    for t in range(PHASES):
        out=np.zeros((H,W,4),dtype=np.uint8)
        for j,(sx,sy,dx,delay,kind) in enumerate(positions):
            k=(t+delay)%PHASES
            if k>=13:continue
            pose=poses[kind]
            # Fall inward by at most 20 px, then the pebble settles; cycle is closed by disappearance.
            x=int(round(sx+dx*min(k,9)/9));y=int(sy+min(k,9)*2)
            ph,pw=pose.shape[:2];x0=x-pw//2;y0=y-ph//2
            if x0<0 or y0<0 or x0+pw>W or y0+ph>H:continue
            alpha=pose[...,3]>0
            clip=walk[y0:y0+ph,x0:x0+pw]
            sel=alpha&clip
            out[y0:y0+ph,x0:x0+pw][sel]=pose[sel]
            tracks.append([j,t,x,y])
        frames.append(out)
    return frames


def ground_project(stack,blocked,markers,gfx,tools):
    if STAGE.exists():shutil.rmtree(STAGE)
    (STAGE/'Content/Tile').mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(ROOT/'mod_metano_expeditions_pmdo_0812.zip') as z:
        tpl=json.loads(z.read('metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground'))
    obj=tpl['Object'];gw,gh=W//8,H//8; layers=[];banks=[]
    for i,(title,frames,ticks) in enumerate(stack):
        bank=gfx.TileBank(f'{PFX}_{i:02d}_{title.upper()}');bank.ids[bytes(256)]=(0,0);bank.data[(0,0)]=bytes(256)
        def cell(x,y,frames=frames,bank=bank):
            refs=[]
            for a in frames:
                f=bank.add(Image.fromarray(a[y*8:y*8+8,x*8:x*8+8]),x,y);refs.append(f or {'Sheet':bank.name,'TexLoc':{'X':0,'Y':0}})
            if all(q['TexLoc']=={'X':0,'Y':0} for q in refs):return []
            return [refs[0]] if all(q==refs[0] for q in refs) else refs
        layers.append(gfx.layer(f'{i:02d} {title}',gw,gh,cell,ticks));banks.append(bank)
    layers.append(gfx.layer(f'{len(stack):02d} Top vide',gw,gh,draw=4))
    for bank in banks:bank.write(STAGE/f'Content/Tile/{bank.name}.tile')
    obj.update(Name={'DefaultText':'FVC1 - Fin Couloir violet (4:3)','LocalTexts':{}},AssetName=ASSET,Released=False,TexSize=1,Music='',
      EdgeView=1,ViewCenter=None,ViewOffset={'X':0,'Y':0},ActiveChar=None,Status={},Layers=layers,
      Background={'$type':'RogueEssence.Dungeon.LayeredBG, RogueEssence','Layers':[]},
      Comment='PMDO 0.8.12. Rendu genere reference sur la capture canonique ECV1. Aucun personnage, objet invente, sortie ou warp. Art et runtime a confirmer.')
    obj['obstacles']=[[{'Bounds':{'X':x*8,'Y':y*8,'Width':8,'Height':8},'Tags':int(blocked[y,x])} for y in range(gh)] for x in range(gw)]
    marker=lambda name,p:{'EntName':name,'Direction':4,'EntEnabled':True,'triggerType':0,'Collider':{'X':p[0],'Y':p[1],'Width':16,'Height':16}}
    obj['Entities']=[{'Name':'Marqueurs de la fin','Visible':True,'MapChars':[],'GroundObjects':[],'Spawners':[],'Markers':[marker(n,p) for n,p in markers.items()]}]
    obj['Decorations']=[{'Name':'Decors','Layer':2,'Visible':True,'Anims':[]}];tpl['Version']='0.8.12.0'
    gfx.save(STAGE/f'Data/Ground/{ASSET}.rsground',json.dumps(tpl,ensure_ascii=False,separators=(',',':')).encode())
    gfx.save(STAGE/f'Data/Script/{NS}/ground/{ASSET}/init.lua',f'-- {ASSET}; aucun warp.\nlocal {ASSET} = {{}}\nreturn {ASSET}\n'.encode())
    nodes={}
    for p in sorted((STAGE/'Content/Tile').glob('*.tile')):
        with p.open('rb') as f:nodes[p.stem]=tools.read_node(f)
    (STAGE/'Content/Tile/index.idx').write_bytes(tools.encode_index(nodes))
    uid=__import__('uuid').uuid5(__import__('uuid').NAMESPACE_URL,'https://github.com/meromoonmeri/projet-pmdo/'+NS)
    (STAGE/'Mod.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>\n<Header><Name>Fin Couloir violet FVC1</Name><Author>meromoonmeri</Author><Description>Atelier PMDO 0.8.12, fin de donjon cavernicole en 4:3, rendu genere reference ECV1.</Description><Namespace>{NS}</Namespace><UUID>{uid}</UUID><Version>1.0.0.0</Version><GameVersion>0.8.12.0</GameVersion><ModType>Quest</ModType><Relationships /></Header>\n''')
    installer=(ROOT/'source/pmdo_cote/INSTALLER.py').read_text();needle='            relative = src.relative_to(source)\n';assert needle in installer
    (STAGE/'INSTALLER.py').write_text(installer.replace(needle,needle+"            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n"))
    shutil.copyfile(HERE/'README_PACK.md',STAGE/'README.md')
    return {b.name:len(b.data) for b in banks}


def build():
    gfx=loadmod('fvc_codec',ROOT/'source/pmdo_cote/build.py');tools=loadmod('fvc_index',ROOT/'source/pmdo_cote/INSTALLER.py')
    for d in ['calques','animation','masques','review','poses']:shutil.rmtree(OUT/d,ignore_errors=True);(OUT/d).mkdir(parents=True,exist_ok=True)
    (OUT/'animation/eboulis').mkdir(parents=True,exist_ok=True)
    a=rgb(RAW/'decor.png');guide=rgb(RAW/'objets_magenta.png')
    assert a.shape==guide.shape==(SRC[1],SRC[0],3)
    masks,seg=masks_of(a,guide);under=make_underlay(a,masks['sol'])
    # Separate solid shadows from the walkable texture; every visible color still comes from the referenced render.
    shade=create_shadows(a,masks['sol'],masks['parois']); ground=masks['sol']&~shade
    masks['ombres']=shade;masks['sol']=ground
    names=['sol','ombres','gravillons','parois','vide']
    ex,cols=DOWN(a,masks,names)
    base=DOWNFULL(under);layers={'sol_complet':RGBA(base,np.ones((H,W),bool))}
    for n in names:layers[n]=RGBA(cols[n],ex[n])
    # One palette for this single-material map; this limits noise without changing class ownership.
    q=Q.quantize_group({k:layers[k] for k in ('sol_complet','sol','ombres','gravillons','parois','vide')},96)
    layers=q
    walk=(layers['sol'][...,3]==255)|(layers['ombres'][...,3]==255)|(layers['gravillons'][...,3]==255)
    blocked=CELL(~walk);free=lambda x,y:0<=x<W//8-1 and 0<=y<H//8-1 and not blocked[y:y+2,x:x+2].any()
    cand=[(x,y) for y in range(H//8) for x in range(W//8) if free(x,y)]
    ent=min((p for p in cand if p[1]>=H//8-4),key=lambda p:abs(p[0]-W//16))
    boss=min(cand,key=lambda p:(p[0]-W//16)**2+(p[1]-H//16*9//8)**2)
    goal=min((p for p in cand if p[1]<H//3//8),key=lambda p:(p[0]-W//16)**2+(p[1]-H//8*1//6)**2)
    markers={'entrance':[ent[0]*8,ent[1]*8],'boss':[boss[0]*8,boss[1]*8],'objectif':[goal[0]*8,goal[1]*8]}
    paths={}
    for key,p in [('boss',boss),('objectif',goal)]:
        ok,n=ESN.reachable(blocked,(ent[1],ent[0]),(p[1],p[0]));paths[key]={'ok':bool(ok),'explored':int(n)};assert ok,(key,markers)
    # Reuse the exact reference-derived ECV1 pebble sprites, unscaled. Trajectories are a new 24-phase dustfall cycle.
    pdir=ROOT/'renders/entree_couloir_violet_sud_nord_v1/poses'
    poses={n:np.asarray(Image.open(pdir/f'ECV1_gravillon_{n}.png').convert('RGBA')) for n in ('petit','moyen','gros')}
    walkfull=walk.copy(); positions=[]
    edges=np.argwhere((nd.binary_dilation(~walk,iterations=4)&walk)&(np.indices((H,W))[0]<H-80))
    rng=np.random.default_rng(517)
    if len(edges):
        # Choose a few wall-floor contact points but keep the south entry lane clear.
        for i in rng.choice(len(edges),min(7,len(edges)),replace=False):
            y,x=map(int,edges[i]);
            if y>H-100 and abs(x-W//2)<70:continue
            dx=12 if x<W//2 else -12
            kind=('petit','moyen','gros')[len(positions)%3]
            positions.append((x,y,dx,(len(positions)*5)%PHASES,kind))
    falling=pebble_frames(walkfull,positions,poses)
    for k,m in masks.items():Image.fromarray((m*255).astype('uint8')).save(OUT/'masques'/f'{PFX}_masque_{k}.png')
    Image.fromarray((walk*255).astype('uint8')).save(OUT/'masques'/f'{PFX}_masque_praticable.png')
    static=['sol_complet','sol','ombres','gravillons','parois','vide']
    stack=[]
    for i,n in enumerate(static):stack.append((n,[layers[n]],60))
    stack.append(('eboulis',falling,TICKS))
    for i,(n,frames,ticks) in enumerate(stack):
        folder=(OUT/'animation/eboulis') if n=='eboulis' else (OUT/'calques')
        for t,im in enumerate(frames):
            fn=f'{PFX}_{i:02d}_{n}_f{t:02d}.png' if len(frames)>1 else f'{PFX}_{i:02d}_{n}.png'
            Image.fromarray(im).save(folder/fn)
    def scene(t):
        im=Image.new('RGBA',(W,H))
        for n,fr,tk in stack:im.alpha_composite(Image.fromarray(fr[(t//tk)%len(fr)]))
        return im
    scenes=[scene(t) for t in range(0,LOOP,5)]
    scenes[0].save(OUT/'review'/f'{PFX}_scene_t000.png')
    scenes[0].save(OUT/'review'/f'{PFX}_scene_animee.webp',save_all=True,append_images=scenes[1:],duration=round(5000/60),loop=0,lossless=True)
    col=scenes[0].copy();ov=Image.new('RGBA',(W,H));dr=ImageDraw.Draw(ov)
    for y,x in zip(*np.nonzero(blocked)):dr.rectangle((x*8,y*8,x*8+7,y*8+7),fill=(220,40,40,85))
    for n,color in [('entrance',(255,230,40,255)),('boss',(255,60,220,255)),('objectif',(60,220,255,255))]:
        x,y=markers[n];dr.rectangle((x,y,x+15,y+15),outline=color,width=2)
    col.alpha_composite(ov);col.save(OUT/'review'/f'{PFX}_collisions_marqueurs.png')
    write_ora(OUT/f'{PFX}_fin_couloir_violet_calques.ora',stack)
    counts=ground_project(stack,blocked,markers,gfx,tools)
    ref=rgb(REF)
    # Material means use the measured floor mask, plus direct rip floor ROI as evidence; publish raw means and distance.
    rip_floor=ref[300:650,95:240].reshape(-1,3).astype(float).mean(0)
    decor_floor=a[masks_of(a,guide)[0]['sol']].astype(float).mean(0)
    fd=float(np.linalg.norm(rip_floor-decor_floor))
    raw=[]
    for f,imgs,purpose in [('decor.png',[REF.name],'décor complet généré référencé'),('objets_magenta.png',['decor.png'],'témoin de masque seulement; magenta jamais exporté'),('sol_complet.png',['decor.png'],'underpainting répétée depuis une zone propre de sol du décor; masquée en jeu')]:
        p=RAW/f;raw.append({'file':f'source/fin_couloir_violet_v1/bruts/{f}','sha256':sha(p),'size':list(Image.open(p).size),'references':imgs,'purpose':purpose})
    gen=[{'file':'decor.png','images':[REF.name],'prompt':'Fin de donjon violette, couloir sud ouvrant sur une arène centrale, murs et sol selon la palette/matière de la capture; sans objets étrangers.'},
         {'file':'objets_magenta.png','images':['decor.png'],'prompt':'Édition de masque magenta du sol uniquement; rochers gardés; guide non exporté.'},
         {'file':'sol_complet.png','images':['decor.png'],'prompt':'Sous-couche programmatique répétée à partir de pixels valides du sol généré; cachée sous les calques visibles.'}]
    manifest={'lot':'fin_couloir_violet_v1','prefix':PFX,'biome':'Couloir rocheux violet, continuation d ECV1; choix de l agent à confirmer','format':'4:3 vaste','size_px':[W,H],'grid_8px':[W//8,H//8],
      'method':'rendu généré référencé sur la capture canonique ECV1. Le magenta ne sert que de masque; ce ne sont pas des tuiles natives.',
      'reference':{'file':REF.name,'sha256':sha(REF),'related_entry':'ECV1'},'generation':gen,'raw_inputs':raw,'segmentation':seg,
      'fidelity':{'method':'distance euclidienne entre moyenne RVB du ROI du sol ECV1 et moyenne du sol segmenté généré; échantillonnage indicatif, non pixel-perfect','rip_floor_rgb':[round(float(x),1) for x in rip_floor],'decor_floor_rgb':[round(float(x),1) for x in decor_floor],'distance':round(fd,1)},
      'normalization':{'scale':H/SRC[1],'size':[W,H],'method':'réduction BOX par classes; quantification groupée 96 couleurs'},
      'layers':[{'name':n,'file':(f'animation/eboulis/{PFX}_{i:02d}_{n}_fNN.png' if len(fr)>1 else f'calques/{PFX}_{i:02d}_{n}.png'),'phases':len(fr),'ticks':tk} for i,(n,fr,tk) in enumerate(stack)],
      'animations':{'eboulis':{'phases':PHASES,'ticks':TICKS,'emitters':[list(x) for x in positions],'pose_origin':'poses ECV1 de gravillons provenant de la capture, pixels/tailles conservés','motion':'chutes calculées pour FVC1, non officielle'}},
      'access':{'markers':markers,'path_16x16':paths,'blocked_cells':int(blocked.sum()),'total_cells':int(blocked.size),'walkable_cells':int(walk.sum()),'no_warp':True},
      'scene_loop_ticks':LOOP,'pmdo':{'target':'0.8.12','asset':ASSET,'namespace':NS,'tiles_per_bank':counts,'runtime_tested':False},'art_approved':False}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    shutil.copyfile(HERE/'README_PACK.md',OUT/'README.md');shutil.copyfile(OUT/'manifest.json',STAGE/'manifest.json')
    print(json.dumps({'markers':markers,'paths':paths,'segments':seg,'fidelity_distance':round(fd,1),'tiles':sum(counts.values())},indent=2))


def write_ora(path,stack):
    import xml.etree.ElementTree as ET
    root=ET.Element('image',w=str(W),h=str(H),name='FVC1 Fin Couloir violet');st=ET.SubElement(root,'stack');comp=Image.new('RGBA',(W,H))
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
        for i,(name,frames,ticks) in reversed(list(enumerate(stack))):
            fn=f'data/layer{i:02d}.png';ET.SubElement(st,'layer',name=name,src=fn,x='0',y='0',opacity='1.0',visibility='visible',**{'composite-op':'svg:src-over'})
            b=io.BytesIO();Image.fromarray(frames[0]).save(b,format='PNG');z.writestr(fn,b.getvalue())
        for _,fr,_ in stack:comp.alpha_composite(Image.fromarray(fr[0]))
        b=io.BytesIO();comp.save(b,format='PNG');z.writestr('mergedimage.png',b.getvalue())
        th=comp.copy();th.thumbnail((256,256));b=io.BytesIO();th.save(b,format='PNG');z.writestr('Thumbnails/thumbnail.png',b.getvalue())
        z.writestr('stack.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True))

if __name__=='__main__':build()
