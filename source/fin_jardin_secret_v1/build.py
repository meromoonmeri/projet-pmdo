"""FGS1 — Fin Jardin secret. Nouveau rendu référencé et exportable en Ground PMDO, sans recopier les sorties EJS1/EJS2."""
from pathlib import Path
import hashlib,importlib.util,io,json,shutil,zipfile,uuid
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as nd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];RAW=HERE/'bruts'
OUT=ROOT/'renders/fin_jardin_secret_v1';STAGE=ROOT/'.cache/fin_jardin_secret_v1/fin_jardin_secret'
REF=ROOT/'secretgarden.png';PFX='FGS1';ASSET='fgs1_fin_jardin_secret';NS='fin_jardin_secret'
W,H,SRC=768,576,(1200,896);PHASES,TICKS,LOOP=24,5,120

def loadmod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rgb(p):return np.asarray(Image.open(p).convert('RGB'),dtype=np.int32)
EJS=loadmod('fgs_methods',ROOT/'source/entree_jardin_secret_sud_nord_v1/build.py')
ESN=loadmod('fgs_access',ROOT/'source/entree_sud_nord_generee_v1/build.py');ESN.W,ESN.H=W,H;CELL=ESN.cell_grid


def underpainting(a,masks):
 """Programmatic hidden substrate tiled from clean generated meadow pixels, with nearest valid fill."""
 ground=masks['prairie']|masks['herbe']|masks['ombres']
 # Center of the broad meadow is far from the stump and all perimeter objects.
 y0,y1,x0,x1=380,620,455,745
 patch=a[y0:y1,x0:x1].copy();ok=ground[y0:y1,x0:x1]
 if ok.mean()<.7:
  pts=np.argwhere(ground);cy,cx=pts.mean(0).astype(int);y0=max(0,min(SRC[1]-240,cy-120));x0=max(0,min(SRC[0]-240,cx-120))
  patch=a[y0:y0+240,x0:x0+240].copy();ok=ground[y0:y0+240,x0:x0+240]
 _,idx=nd.distance_transform_edt(~ok,return_indices=True);patch[~ok]=patch[idx[0][~ok],idx[1][~ok]]
 h,w=patch.shape[:2];full=np.tile(patch,(int(np.ceil(SRC[1]/h)),int(np.ceil(SRC[0]/w)),1))[:SRC[1],:SRC[0]]
 Image.fromarray(full.astype('uint8')).save(RAW/'sol_complet.png')
 return full.astype(np.int32)


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
    t=bank.add(Image.fromarray(f[y*8:y*8+8,x*8:x*8+8]),x,y);refs.append(t or {'Sheet':bank.name,'TexLoc':{'X':0,'Y':0}})
   if all(t['TexLoc']=={'X':0,'Y':0} for t in refs):return []
   return [refs[0]] if all(t==refs[0] for t in refs) else refs
  layers.append(gfx.layer(f'{i:02d} {title}',gw,gh,cell,ticks));banks.append(bank)
 layers.append(gfx.layer(f'{len(stack):02d} Top vide',gw,gh,draw=4))
 for b in banks:b.write(STAGE/f'Content/Tile/{b.name}.tile')
 obj.update(Name={'DefaultText':'FGS1 - Fin Jardin secret (4:3)','LocalTexts':{}},AssetName=ASSET,Released=False,TexSize=1,Music='',
   EdgeView=1,ViewCenter=None,ViewOffset={'X':0,'Y':0},ActiveChar=None,Status={},Layers=layers,
   Background={'$type':'RogueEssence.Dungeon.LayeredBG, RogueEssence','Layers':[]},
   Comment='PMDO 0.8.12. Rendu genere reference sur secretgarden.png. Rayon et couleurs exacts du rip; timing compose, non officiel. Aucun temple, personnage, warp ou sortie. Art/runtime a confirmer.')
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
 (STAGE/'Mod.xml').write_text(f'''<?xml version="1.0" encoding="utf-8"?>\n<Header><Name>Fin Jardin secret FGS1</Name><Author>meromoonmeri</Author><Description>Arène du Jardin secret en 4:3, rendu généré référencé sur Explorers of Sky.</Description><Namespace>{NS}</Namespace><UUID>{uid}</UUID><Version>1.0.0.0</Version><GameVersion>0.8.12.0</GameVersion><ModType>Quest</ModType><Relationships /></Header>\n''')
 script=(ROOT/'source/pmdo_cote/INSTALLER.py').read_text();needle='            relative = src.relative_to(source)\n';assert needle in script
 (STAGE/'INSTALLER.py').write_text(script.replace(needle,needle+"            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n"))
 shutil.copyfile(HERE/'README_PACK.md',STAGE/'README.md')
 return {b.name:len(b.data) for b in banks}


def build():
 gfx=loadmod('fgs_codec',ROOT/'source/pmdo_cote/build.py');tools=loadmod('fgs_index',ROOT/'source/pmdo_cote/INSTALLER.py')
 for d in ['calques','animation','masques','review','poses']:shutil.rmtree(OUT/d,ignore_errors=True);(OUT/d).mkdir(parents=True,exist_ok=True)
 for d in ['animation/rayon','animation/lucioles']:(OUT/d).mkdir(parents=True,exist_ok=True)
 a=rgb(RAW/'decor.png');t=rgb(RAW/'temoin_sans_objets.png');ref=rgb(REF)
 assert a.shape==t.shape==(SRC[1],SRC[0],3)
 masks,seg=EJS.classify(a,t)
 objs=masks['fleurs']|masks['rochers']|masks['arbres']|(np.abs(a-t).mean(2)>10)
 align=EJS.recalage(a,t,~nd.binary_dilation(objs,iterations=4))
 full=underpainting(a,masks)
 order=['profondeur','marches','souche','fleurs','rochers','arbres','rayon','haies','fond','ombres','prairie','herbe']
 ex,cols=EJS.down_class(a,masks,order)
 layers={'sol_complet':EJS.rgba(EJS.down_full(full),np.ones((H,W),bool))}
 for n in EJS.STATIC:layers[n]=EJS.rgba(cols[n],ex[n])
 q={}
 for names,count in EJS.PALETTE_GROUPS.values():q.update(EJS.quantize_group({n:layers[n] for n in names},count))
 layers=q
 walk_candidates=ex['prairie']|ex['herbe']|ex['ombres']|ex['fleurs']|ex['marches']
 cl,_=nd.label(EJS.close_(walk_candidates,2));seed=cl[H-1][walk_candidates[H-1]]
 walk=np.isin(cl,np.unique(seed[seed>0]))&walk_candidates
 blocked=CELL(~walk);gh,gw=blocked.shape;free=lambda x,y:0<=x<gw-1 and 0<=y<gh-1 and not blocked[y:y+2,x:x+2].any()
 cand=[(x,y) for y in range(gh-1) for x in range(gw-1) if free(x,y)]
 ent=min((p for p in cand if p[1]>=gh-6),key=lambda p:(abs(p[0]-gw//2)+abs(p[1]-(gh-4))))
 boss=min(cand,key=lambda p:(p[0]-gw//2)**2+(p[1]-gh*5//8)**2)
 mouth=ex['profondeur'];yy,xx=np.nonzero(mouth);target=(int(round(xx.mean()/8)),int((yy.max()+28)//8))
 goal=min((p for p in cand if p[1]<gh//2),key=lambda p:(p[0]-target[0])**2+(p[1]-target[1])**2)
 markers={'entrance':[ent[0]*8,ent[1]*8],'boss':[boss[0]*8,boss[1]*8],'objectif':[goal[0]*8,goal[1]*8]}
 paths={}
 for k,p in [('boss',boss),('objectif',goal)]:
  ok,n=ESN.reachable(blocked,(ent[1],ent[0]),(p[1],p[0]));paths[k]={'ok':bool(ok),'explored':int(n)};assert ok,(k,markers)
 # Beam pixels stay on the exact 22-colour reference ramp. Firefly sprites/timing reuse only the method/constants.
 base_idx=EJS.ramp_index(cols['rayon']);rayon=EJS.beam_frames(base_idx,ex['rayon']);lucioles=EJS.mote_frames(EJS.MOTES)
 for n,m in masks.items():Image.fromarray((m*255).astype('uint8')).save(OUT/'masques'/f'{PFX}_masque_{n}.png')
 Image.fromarray((walk*255).astype('uint8')).save(OUT/'masques'/f'{PFX}_masque_praticable.png')
 Image.fromarray(np.where(ex['rayon'],base_idx*11,0).astype('uint8')).save(OUT/'masques'/f'{PFX}_rayon_crans.png')
 for kind,key in (('fleur','fleurs'),('rocher','rochers'),('arbre','arbres')):
  crop=EJS.rgba(cols[key],ex[key]);Image.fromarray(crop).save(OUT/'poses'/f'{PFX}_{kind}_calque.png')
 stack=[];static=['sol_complet']+EJS.STATIC
 for n in static:stack.append((n,[layers[n]],60))
 stack += [('rayon',rayon,TICKS),('lucioles',lucioles,TICKS)]
 layer_info=[]
 for i,(n,frames,ticks) in enumerate(stack):
  folder=OUT/'animation'/n if len(frames)>1 else OUT/'calques'
  for j,img in enumerate(frames):
   fn=f'{PFX}_{i:02d}_{n}_f{j:02d}.png' if len(frames)>1 else f'{PFX}_{i:02d}_{n}.png'
   Image.fromarray(img).save(folder/fn)
  layer_info.append({'name':n,'file':(f'animation/{n}/{PFX}_{i:02d}_{n}_fNN.png' if len(frames)>1 else f'calques/{PFX}_{i:02d}_{n}.png'),'phases':len(frames),'ticks':ticks})
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
 write_ora(OUT/f'{PFX}_fin_jardin_secret_calques.ora',stack)
 counts=ground_project(stack,blocked,markers,gfx,tools)
 # Use the same material classifier for the raw rip and generated image; color distances are not art approval.
 fidelite=EJS.fidelity(a,ref)
 raw=[]
 for f,src in [('decor.png',REF),('temoin_sans_objets.png',RAW/'decor.png'),('sol_complet.png',RAW/'decor.png')]:
  p=RAW/f;raw.append({'file':f'source/fin_jardin_secret_v1/bruts/{f}','sha256':sha(p),'size':list(Image.open(p).size),'reference':str(src.relative_to(ROOT))})
 gen=[{'file':'decor.png','reference':str(REF.relative_to(ROOT)),'prompt':'Large open secret garden arena, southern grass entrance, golden stump and green beam north, reference palette/materials; no unrelated props.'},
      {'file':'temoin_sans_objets.png','reference':'decor.png','prompt':'Remove trees, rocks and flowers only; preserve stump, beam, hedges and background exactly.'},
      {'file':'sol_complet.png','reference':'decor.png','prompt':'Programmatic seamless hidden meadow underlay sampled from clean generated central grass, nearest valid fill.'}]
 manifest={'lot':'fin_jardin_secret_v1','prefix':PFX,'format':'4:3 vaste','size_px':[W,H],'grid_8px':[W//8,H//8],
  'biome':'Jardin secret, capture Explorers of Sky; arène large, entrée sud, souche nord, proposition agent à confirmer',
  'method':'rendu généré référencé, pas tuiles natives. Décomposition par témoin sans objets; aucun artwork de branche sœur/main copié.',
  'reference':{'file':REF.name,'sha256':sha(REF),'source':'Explorers of Sky'},'raw_inputs':raw,'generation':gen,
  'segmentation':seg,'registration':align,'normalization':{'scale':H/SRC[1],'output':[W,H],'method':'BOX pondéré par classe; quantification par groupes'},
  'fidelity':{'method':'classifieur EJS1 identique rip/décor, distances RGB indicatives, seuil atelier 35','materials':fidelite},
  'layers':layer_info,'animation':{'rayon':{'phases':PHASES,'ticks':TICKS,'ramp_rgb':EJS.RAMP,'breath_steps':EJS.BREATH},
   'lucioles':{'phases':PHASES,'ticks':TICKS,'motes':EJS.MOTES,'colors':[EJS.DOT,EJS.GLOW,EJS.CORE]},'loop_ticks':LOOP,'official_timing':False},
  'access':{'markers':markers,'paths_16x16':paths,'blocked_cells':int(blocked.sum()),'total_cells':int(blocked.size),'walkable_cells':int(walk.sum()),'no_warp':True},
  'pmdo':{'target':'0.8.12','asset':ASSET,'namespace':NS,'tiles_per_bank':counts,'runtime_tested':False},'art_approved':False}
 (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 shutil.copyfile(HERE/'README_PACK.md',OUT/'README.md');shutil.copyfile(OUT/'manifest.json',STAGE/'manifest.json')
 print(json.dumps({'markers':markers,'paths':paths,'registration':align,'segments':seg,'fidelity':fidelite,'tiles':sum(counts.values())},ensure_ascii=False,indent=2))


def write_ora(path,stack):
 import xml.etree.ElementTree as ET
 root=ET.Element('image',w=str(W),h=str(H),name='FGS1 Fin Jardin secret');st=ET.SubElement(root,'stack');comp=Image.new('RGBA',(W,H))
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
