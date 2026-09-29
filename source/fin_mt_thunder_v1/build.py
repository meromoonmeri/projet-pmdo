"""FTH1 — Fin Mt. Thunder. Rendu généré référencé, sprites de foudre extraits du rip, Ground PMDO exportable."""
from pathlib import Path
import hashlib,importlib.util,io,json,shutil,zipfile,uuid
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as nd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]; RAW=HERE/'bruts'
OUT=ROOT/'renders/fin_mt_thunder_v1'; STAGE=ROOT/'.cache/fin_mt_thunder_v1/fin_mt_thunder'
REF=ROOT/'source/references_54d3731/thunder.png'
SHEET=ROOT/'Game Boy Advance - Pokemon Mystery Dungeon_ Red Rescue Team - Dungeon Boss Rooms - Mt. Thunder.png'
PFX='FTH1'; ASSET='fth1_fin_mt_thunder'; NS='fin_mt_thunder'
W,H,SRC=768,576,(1200,896); PHASES,TICKS,LOOP=48,5,240

def loadmod(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rgb(p):return np.asarray(Image.open(p).convert('RGB'),dtype=np.int32)

J=loadmod('fth_jungle',ROOT/'source/entree_jungle_sud_nord_v1/build.py')
DOWN,DOWNFULL,RGBA=J.down_class,J.down_full,J.rgba
ESN=loadmod('fth_access',ROOT/'source/entree_sud_nord_generee_v1/build.py'); ESN.W,ESN.H=W,H; CELL=ESN.cell_grid
Q=loadmod('fth_quantizer',ROOT/'source/entree_waterfall_cave_sud_nord_v1/build.py')
EMT=loadmod('fth_thunder_sprite_methods',ROOT/'source/entree_mt_thunder_sud_nord_v1/build.py')

# Four clouds-only strikes: sprites remain at source size, and are clipped to background clouds.
STRIKES=[(1,False,20,55,0),(3,True,704,105,8),(2,False,42,235,16),
         (4,True,704,315,24),(3,False,18,390,32),(2,True,710,10,40)]


def masks_of(a,guide):
    y=a@np.array([.299,.587,.114]); r,g,b=a.transpose(2,0,1)
    mag=((guide[...,0]>180)&(guide[...,1]<105)&(guide[...,2]>180)&
         (guide[...,0]-guide[...,1]>80)&(guide[...,2]-guide[...,1]>80))
    # Fill only missed pale-sand pixels within a narrow ring of the magenta witness.
    pale=(r>205)&(g>190)&(r-b>45)
    floor=mag|(pale&nd.binary_dilation(mag,iterations=12))
    obj=~floor; near=nd.binary_dilation(floor,iterations=155)
    # Warm sandstone/cliff pixels beside the summit; broad, pale sand itself is already in floor.
    warm=(r>g+7)&(g>b+3)&(y>45)&(y<230)
    walls=obj&near&warm
    # Isolated low olive-gray pebbles around the ground, kept visual and traversable.
    pc=obj&nd.binary_dilation(floor,iterations=12)&(b+8<g)&(r>g-12)&(y>45)&(y<190)
    lab,n=nd.label(pc,structure=np.ones((3,3),bool)); sizes=np.bincount(lab.ravel())
    ids=np.flatnonzero((sizes>=8)&(sizes<=1200)); ids=ids[ids!=0]
    pebbles=np.isin(lab,ids)&pc; walls &= ~pebbles
    cloud=~(floor|walls|pebbles)
    yy=np.indices(floor.shape)[0]
    front=cloud&(yy>=690)&(y>155)
    back=cloud&~front
    return {'sol':floor,'ombres':np.zeros_like(floor),'pierres':pebbles,'parois':walls,
            'nuages_arriere':back,'nuages_avant':front}, {
            'floor_px':int(floor.sum()),'magenta_px':int(mag.sum()),'pebble_px':int(pebbles.sum()),
            'wall_px':int(walls.sum()),'cloud_back_px':int(back.sum()),'cloud_front_px':int(front.sum()),
            'pebble_components':int(len(ids))}


def underpainting(a):
    """Flat concealed fallback sampled from dark storm sky; all visible classes overlay it."""
    y=a@np.array([.299,.587,.114]); sat=a.max(2)-a.min(2)
    s=a[:150][(y[:150]<90)&(sat[:150]<35)]
    color=np.median(s,axis=0).round().astype('uint8') if len(s) else np.array([56,49,57],dtype='uint8')
    out=np.empty((SRC[1],SRC[0],3),dtype='uint8');out[:]=color
    Image.fromarray(out).save(RAW/'fond_complet.png')
    return out.astype(np.int32),[int(v) for v in color]


def shadows(a,floor,walls):
    d=nd.distance_transform_edt(~walls); y=a@np.array([.299,.587,.114]); vals=y[floor]
    return floor&(d<22)&(y<np.percentile(vals,43))


def rgba_full(a):
    out=np.zeros((*a.shape[:2],4),dtype='uint8');out[...,:3]=a;out[...,3]=255;return out


def sprite_clip(frames,mask):
    out=[]
    for f in frames:
        a=f.copy();a[~mask]=0;out.append(a)
    return out


def write_ora(path,stack):
    import xml.etree.ElementTree as ET
    root=ET.Element('image',w=str(W),h=str(H),name='FTH1 Fin Mt. Thunder');st=ET.SubElement(root,'stack');comp=Image.new('RGBA',(W,H))
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
        for i,(name,frames,ticks) in reversed(list(enumerate(stack))):
            fn=f'data/layer{i:02d}.png';ET.SubElement(st,'layer',name=name,src=fn,x='0',y='0',opacity='1.0',visibility='visible',**{'composite-op':'svg:src-over'})
            b=io.BytesIO();Image.fromarray(frames[0]).save(b,format='PNG');z.writestr(fn,b.getvalue())
        for _,fr,_ in stack:comp.alpha_composite(Image.fromarray(fr[0]))
        b=io.BytesIO();comp.save(b,format='PNG');z.writestr('mergedimage.png',b.getvalue())
        th=comp.copy();th.thumbnail((256,256));b=io.BytesIO();th.save(b,format='PNG');z.writestr('Thumbnails/thumbnail.png',b.getvalue())
        z.writestr('stack.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True))


def ground_project(stack,blocked,markers,gfx,tools):
    if STAGE.exists():shutil.rmtree(STAGE)
    (STAGE/'Content/Tile').mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(ROOT/'mod_metano_expeditions_pmdo_0812.zip') as z:
        tpl=json.loads(z.read('metano_expeditions/Data/Ground/v50812_01_crete_sillage_jour.rsground'))
    obj=tpl['Object'];gw,gh=W//8,H//8;layers=[];banks=[]
    for i,(title,frames,ticks) in enumerate(stack):
        bank=gfx.TileBank(f'{PFX}_{i:02d}_{title.upper()}');bank.ids[bytes(256)]=(0,0);bank.data[(0,0)]=bytes(256)
        def cell(x,y,frames=frames,bank=bank):
            refs=[]
            for f in frames:
                t=bank.add(Image.fromarray(f[y*8:y*8+8,x*8:x*8+8]),x,y)
                refs.append(t or {'Sheet':bank.name,'TexLoc':{'X':0,'Y':0}})
            if all(t['TexLoc']=={'X':0,'Y':0} for t in refs):return []
            return [refs[0]] if all(t==refs[0] for t in refs) else refs
        layers.append(gfx.layer(f'{i:02d} {title}',gw,gh,cell,ticks));banks.append(bank)
    layers.append(gfx.layer(f'{len(stack):02d} Top vide',gw,gh,draw=4))
    for bank in banks:bank.write(STAGE/f'Content/Tile/{bank.name}.tile')
    obj.update(Name={'DefaultText':'FTH1 - Fin Mt. Thunder (4:3)','LocalTexts':{}},AssetName=ASSET,
      Released=False,TexSize=1,Music='',EdgeView=1,ViewCenter=None,ViewOffset={'X':0,'Y':0},ActiveChar=None,Status={},Layers=layers,
      Background={'$type':'RogueEssence.Dungeon.LayeredBG, RogueEssence','Layers':[]},
      Comment='PMDO 0.8.12. Texture en rendu genere reference sur la scene Mt. Thunder. Eclairs et Flash extraits du panneau GBA; timing compose pour FTH1, non officiel. Aucun warp. Art/runtime a confirmer.')
    obj['obstacles']=[[{'Bounds':{'X':x*8,'Y':y*8,'Width':8,'Height':8},'Tags':int(blocked[y,x])} for y in range(gh)] for x in range(gw)]
    mk=lambda n,p:{'EntName':n,'Direction':4,'EntEnabled':True,'triggerType':0,'Collider':{'X':p[0],'Y':p[1],'Width':16,'Height':16}}
    obj['Entities']=[{'Name':'Marqueurs de la fin','Visible':True,'MapChars':[],'GroundObjects':[],'Spawners':[],'Markers':[mk(n,p) for n,p in markers.items()]}]
    obj['Decorations']=[{'Name':'Decors','Layer':2,'Visible':True,'Anims':[]}];tpl['Version']='0.8.12.0'
    gfx.save(STAGE/f'Data/Ground/{ASSET}.rsground',json.dumps(tpl,ensure_ascii=False,separators=(',',':')).encode())
    gfx.save(STAGE/f'Data/Script/{NS}/ground/{ASSET}/init.lua',f'-- {ASSET}; aucun warp.\nlocal {ASSET} = {{}}\nreturn {ASSET}\n'.encode())
    nodes={}
    for p in sorted((STAGE/'Content/Tile').glob('*.tile')):
        with p.open('rb') as f:nodes[p.stem]=tools.read_node(f)
    (STAGE/'Content/Tile/index.idx').write_bytes(tools.encode_index(nodes))
    uid=uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/meromoonmeri/projet-pmdo/'+NS)
    (STAGE/'Mod.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>\n<Header><Name>Fin Mt. Thunder FTH1</Name><Author>meromoonmeri</Author><Description>Projet PMDO 0.8.12, arene du sommet de Mt. Thunder, rendu genere reference 4:3.</Description><Namespace>{NS}</Namespace><UUID>{uid}</UUID><Version>1.0.0.0</Version><GameVersion>0.8.12.0</GameVersion><ModType>Quest</ModType><Relationships /></Header>\n''')
    installer=(ROOT/'source/pmdo_cote/INSTALLER.py').read_text();needle='            relative = src.relative_to(source)\n';assert needle in installer
    (STAGE/'INSTALLER.py').write_text(installer.replace(needle,needle+"            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n"))
    shutil.copyfile(HERE/'README_PACK.md',STAGE/'README.md')
    return {b.name:len(b.data) for b in banks}


def build():
    gfx=loadmod('fth_codec',ROOT/'source/pmdo_cote/build.py');tools=loadmod('fth_index',ROOT/'source/pmdo_cote/INSTALLER.py')
    for d in ['calques','animation','masques','review','poses']:shutil.rmtree(OUT/d,ignore_errors=True);(OUT/d).mkdir(parents=True,exist_ok=True)
    for d in ['animation/eclairs','animation/lueurs']:(OUT/d).mkdir(parents=True,exist_ok=True)
    a=rgb(RAW/'decor.png');guide=rgb(RAW/'objets_magenta.png');rip=rgb(SHEET)
    assert a.shape==guide.shape==(SRC[1],SRC[0],3)
    masks,seg=masks_of(a,guide);base,bg_rgb=underpainting(a)
    sh=shadows(a,masks['sol'],masks['parois']);masks['ombres']=sh;masks['sol'] &= ~sh
    # Source render is exclusively partitioned into independent map materials; transparent magenta guide never enters.
    order=['nuages_arriere','sol','ombres','pierres','parois','nuages_avant']
    ex,cols=DOWN(a,masks,order)
    layers={'fond_complet':RGBA(DOWNFULL(base),np.ones((H,W),bool))}
    for n in order:layers[n]=RGBA(cols[n],ex[n])
    q={}
    q.update(Q.quantize_group({n:layers[n] for n in ('fond_complet','sol','ombres','pierres','parois')},96))
    q.update(Q.quantize_group({n:layers[n] for n in ('nuages_arriere','nuages_avant')},64))
    layers=q
    # Walkable classes include small loose pebbles, while the cliff and cloud sea stay blocked.
    walk=(layers['sol'][...,3]>0)|(layers['ombres'][...,3]>0)|(layers['pierres'][...,3]>0)
    blocked=CELL(~walk); free=lambda x,y:0<=x<W//8-1 and 0<=y<H//8-1 and not blocked[y:y+2,x:x+2].any()
    cand=[(x,y) for y in range(H//8) for x in range(W//8) if free(x,y)]
    ent=min((p for p in cand if p[1]>=H//8-20),key=lambda p:(abs(p[0]-W//16)+abs(p[1]-(H//8-16))))
    boss=min(cand,key=lambda p:(p[0]-W//16)**2+(p[1]-H//16)**2)
    goal=min((p for p in cand if p[1]<H//8//2),key=lambda p:(p[0]-W//16)**2+(p[1]-H//8//4)**2)
    markers={'entrance':[ent[0]*8,ent[1]*8],'boss':[boss[0]*8,boss[1]*8],'objectif':[goal[0]*8,goal[1]*8]}
    paths={}
    for key,p in [('boss',boss),('objectif',goal)]:
        ok,n=ESN.reachable(blocked,(ent[1],ent[0]),(p[1],p[0]));paths[key]={'ok':bool(ok),'explored':int(n)};assert ok,(key,markers)
    # Exact bolt/Flash pixels and swatches from the original reference's lower panel.
    bolts,flash,sw=EMT.rip_sheet(rip)
    lueurs,eclairs=EMT.anim_frames(bolts,flash,sw,strikes=STRIKES)
    cloud_clip=ex['nuages_arriere']
    lueurs=sprite_clip(lueurs,cloud_clip);eclairs=sprite_clip(eclairs,cloud_clip)
    for k,bm in bolts.items():
        pix=np.zeros((*bm.shape,4),dtype='uint8');pix[bm]=(*sw['normal'][1],255)
        Image.fromarray(pix).save(OUT/'poses'/f'{PFX}_eclair_{k}.png')
    pix=np.zeros((*flash.shape,4),dtype='uint8');pix[flash]=(*sw['normal'][0],255);Image.fromarray(pix).save(OUT/'poses'/f'{PFX}_flash.png')
    for k,m in masks.items():Image.fromarray((m*255).astype('uint8')).save(OUT/'masques'/f'{PFX}_masque_{k}.png')
    Image.fromarray((walk*255).astype('uint8')).save(OUT/'masques'/f'{PFX}_masque_praticable.png')
    static=['fond_complet','nuages_arriere','parois','sol','ombres','pierres']
    stack=[(n,[layers[n]],60) for n in static]+[('lueurs',lueurs,TICKS),('eclairs',eclairs,TICKS),('nuages_avant',[layers['nuages_avant']],60)]
    manifest_layers=[]
    for i,(n,frames,ticks) in enumerate(stack):
        folder=OUT/'animation'/n if len(frames)>1 else OUT/'calques'
        for t,im in enumerate(frames):
            fn=f'{PFX}_{i:02d}_{n}_f{t:02d}.png' if len(frames)>1 else f'{PFX}_{i:02d}_{n}.png'
            Image.fromarray(im).save(folder/fn)
        manifest_layers.append({'name':n,'file':(f'animation/{n}/{PFX}_{i:02d}_{n}_fNN.png' if len(frames)>1 else f'calques/{PFX}_{i:02d}_{n}.png'),'phases':len(frames),'ticks':ticks})
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
    ora=OUT/f'{PFX}_fin_mt_thunder_calques.ora';write_ora(ora,stack)
    counts=ground_project(stack,blocked,markers,gfx,tools)
    # Direct same classifier on source image and generated palette; tonal means are indicators, not approval.
    def mean(mask,im):
        p=im[mask];return np.round(p.mean(0),1).tolist() if len(p) else None
    ref_scene=rgb(REF); lum=a@np.array([.299,.587,.114]);r,g,b=a.transpose(2,0,1)
    rip_floor=(ref_scene[...,0]>205)&(ref_scene[...,1]>190)&(ref_scene[...,0]-ref_scene[...,2]>45)
    dec_floor=masks['sol']
    fid={'rip_sand_rgb':mean(rip_floor,ref_scene),'generated_sand_rgb':mean(dec_floor,a)}
    dist=float(np.linalg.norm(np.array(fid['rip_sand_rgb'])-np.array(fid['generated_sand_rgb'])))
    raw=[]
    for f,refname in [('decor.png',REF),('objets_magenta.png',RAW/'decor.png'),('fond_complet.png',RAW/'decor.png')]:
        p=RAW/f;raw.append({'file':f'source/fin_mt_thunder_v1/bruts/{f}','sha256':sha(p),'size':list(Image.open(p).size),'reference':str(refname.relative_to(ROOT))})
    manifest={'lot':'fin_mt_thunder_v1','prefix':PFX,'format':'4:3 vaste','size_px':[W,H],'grid_8px':[W//8,H//8],
      'biome':'sommet de Mt. Thunder au-dessus d une mer de nuages; suite FVC1, référence GBA/RRT; composition choisie par agent, à confirmer',
      'method':'rendu généré référencé sur thunder.png; rendu non natif. Guide magenta interne, jamais exporté. Éclairs/Flash extraits du panneau source exacts; timing et placement nouveaux.',
      'reference':{'scene':str(REF.relative_to(ROOT)),'sha256':sha(REF),'sprite_sheet':str(SHEET.relative_to(ROOT)),'sha256_sprite_sheet':sha(SHEET),'sprite_boxes':{str(k):list(v) for k,v in EMT.BOLTS.items()},'flash_box':list(EMT.FLASH_BOX)},
      'raw_inputs':raw,'segmentation':seg,'underpainting_rgb':bg_rgb,
      'fidelity':{'method':'distance euclidienne des moyennes RGB de sable dans rip scene et surface générée, indicative, seuil atelier 35, non pixel-perfect','rip_sand_rgb':fid['rip_sand_rgb'],'generated_sand_rgb':fid['generated_sand_rgb'],'distance':round(dist,1)},
      'normalization':{'scale':H/SRC[1],'output':[W,H],'method':'BOX pondéré par classes puis quantification par famille'},
      'layers':manifest_layers,'animation':{'phases':PHASES,'ticks':TICKS,'loop_ticks':LOOP,'strikes':STRIKES,'bolt_colors':{k:list(v) for k,v in sw.items()},'timing':'2 phases Normal, 2 Fading, puis silence; cadence composée, pas officielle'},
      'access':{'markers':markers,'paths_16x16':paths,'blocked_cells':int(blocked.sum()),'total_cells':int(blocked.size),'walkable_cells':int(walk.sum()),'no_warp':True},
      'pmdo':{'target':'0.8.12','asset':ASSET,'namespace':NS,'tiles_per_bank':counts,'runtime_tested':False},'art_approved':False}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    shutil.copyfile(HERE/'README_PACK.md',OUT/'README.md');shutil.copyfile(OUT/'manifest.json',STAGE/'manifest.json')
    print(json.dumps({'markers':markers,'paths':paths,'segmentation':seg,'sand_rgb_distance':round(dist,1),'tiles':sum(counts.values())},indent=2))

if __name__=='__main__':build()
