"""Run FCT1 validations, package the native PMDO project/layer PNGs and write its local preview."""
from pathlib import Path
import json, subprocess, sys, zipfile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'renders/fin_clairiere_tropicale_v1'
STAGE=ROOT/'.cache/fin_clairiere_tropicale_v1/fin_clairiere_tropicale'
PFX='FCT1'


def zip_items(dest, items):
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for src,arc in items:z.write(src,arc)


def main():
    subprocess.run([sys.executable,'-m','unittest','source.fin_clairiere_tropicale_v1.test_build','-v'],cwd=ROOT,check=True)
    M=json.loads((OUT/'manifest.json').read_text())
    native=[(p,'fin_clairiere_tropicale/'+p.relative_to(STAGE).as_posix()) for p in sorted(STAGE.rglob('*')) if p.is_file()]
    zip_items(OUT/f'{PFX}_projet_pmdo_0812.zip',native)
    items=[]
    for L in M['layers']:
        if L['phases']==1:files=[OUT/L['file']]
        else:files=[OUT/L['file'].replace('fNN',f'f{i:02d}') for i in range(L['phases'])]
        folder='calques' if L['phases']==1 else f'animation/{L["name"]}'
        items += [(p,folder+'/'+p.name) for p in files]
    items += [(p,'masques/'+p.name) for p in sorted((OUT/'masques').glob('*.png'))]
    items += [(p,'review/'+p.name) for p in sorted((OUT/'review').glob('*')) if p.is_file()]
    items += [(OUT/f'{PFX}_fin_clairiere_calques.ora',f'{PFX}_fin_clairiere_calques.ora'),
              (OUT/'manifest.json','manifest.json'),(OUT/'README.md','README.md')]
    zip_items(OUT/f'{PFX}_calques_png_8px.zip',items)
    data={'layers':[],'collision':f'/renders/fin_clairiere_tropicale_v1/review/{PFX}_collisions_marqueurs.png'}
    for L in M['layers']:
        files=([L['file']] if L['phases']==1 else [L['file'].replace('fNN',f'f{i:02d}') for i in range(L['phases'])])
        data['layers'].append({'name':L['name'],'ticks':L['ticks'],'files':['/renders/fin_clairiere_tropicale_v1/'+p for p in files]})
    page=(HERE/'viewer_template.html').read_text().replace('__DATA__',json.dumps(data,ensure_ascii=False))
    (ROOT/'apercu_fin_clairiere_tropicale_v1.html').write_text(page)
    print(f'Pack PMDO: {OUT/(PFX+"_projet_pmdo_0812.zip")}')
    print(f'Calques: {OUT/(PFX+"_calques_png_8px.zip")}')
    print(f'Aperçu: {ROOT/"apercu_fin_clairiere_tropicale_v1.html"}')

if __name__=='__main__':main()
