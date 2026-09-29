"""Run tests, package the independent FTH1 Ground/PNG layers, and create an embedded preview."""
from pathlib import Path
import base64,json,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
OUT=ROOT/'renders/fin_mt_thunder_v1';STAGE=ROOT/'.cache/fin_mt_thunder_v1/fin_mt_thunder';PFX='FTH1'
def zip_items(path,items):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p,n in items:z.write(p,n)
def uri(p):return 'data:image/png;base64,'+base64.b64encode(Path(p).read_bytes()).decode()
def main():
 subprocess.run([sys.executable,'-m','unittest','source.fin_mt_thunder_v1.test_build','-v'],cwd=ROOT,check=True)
 native=[(p,'fin_mt_thunder/'+p.relative_to(STAGE).as_posix()) for p in sorted(STAGE.rglob('*')) if p.is_file()]
 zip_items(OUT/f'{PFX}_projet_pmdo_0812.zip',native)
 items=[]
 for p in sorted((OUT/'calques').glob('*.png')):items.append((p,'calques/'+p.name))
 for name in ('eclairs','lueurs'):
  for p in sorted((OUT/'animation'/name).glob('*.png')):items.append((p,f'animation/{name}/'+p.name))
 for p in sorted((OUT/'poses').glob('*.png')):items.append((p,'poses/'+p.name))
 for p in sorted((OUT/'masques').glob('*.png')):items.append((p,'masques/'+p.name))
 for p in sorted((OUT/'review').glob('*')):items.append((p,'apercu/'+p.name))
 items += [(OUT/f'{PFX}_fin_mt_thunder_calques.ora',f'{PFX}_fin_mt_thunder_calques.ora'),(OUT/'manifest.json','manifest.json'),(OUT/'README.md','README.md'),(HERE/'GENERATION.md','GENERATION.md')]
 zip_items(OUT/f'{PFX}_calques_png_8px.zip',items)
 M=json.loads((OUT/'manifest.json').read_text());layers=[]
 for L in M['layers']:
  fs=[OUT/L['file']] if L['phases']==1 else [OUT/L['file'].replace('fNN',f'f{i:02d}') for i in range(L['phases'])]
  layers.append({'name':L['name'],'ticks':L['ticks'],'files':[uri(p) for p in fs]})
 data={'layers':layers,'collision':uri(OUT/'review/FTH1_collisions_marqueurs.png'),'loop':M['animation']['loop_ticks']}
 page=(HERE/'viewer_template.html').read_text().replace('__DATA__',json.dumps(data,ensure_ascii=False))
 (ROOT/'apercu_fin_mt_thunder_v1.html').write_text(page)
 for p in [OUT/f'{PFX}_projet_pmdo_0812.zip',OUT/f'{PFX}_calques_png_8px.zip',ROOT/'apercu_fin_mt_thunder_v1.html']:
  print(f'{p.relative_to(ROOT)} {p.stat().st_size/1e6:.2f} Mo')
if __name__=='__main__':main()
