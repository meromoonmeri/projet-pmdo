"""Packaging IMW3 « Traversée » : tests, README, aperçu HTML et pack zip. Lancer après build.py : .venv/bin/python source/intro_mew_traversee_v1/package.py"""
import json, subprocess, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/intro_mew_traversee_v1'

(O / 'README.md').write_text('# IMW3 — Traversée\n\nVoir README_PACK.md.\n')
r = subprocess.run([sys.executable, '-m', 'unittest', 'source.intro_mew_traversee_v1.test_build'], cwd=R, capture_output=True, text=True)
print(r.stderr[-600:])
assert r.returncode == 0, 'tests en échec'
(O / 'README.md').write_text((HERE / 'README_PACK.md').read_text())
M = json.loads((O / 'manifest.json').read_text())
ch = [(a['t_debut_s'], a['legende']) for a in M['actes']] + [(25.6, 'Éclat blanc et envol')]
arrets = sorted(p.name for p in (O / 'review').glob('IMW3_t*.png'))
h = (HERE / 'viewer_template.html').read_text().replace('__CHAPITRES__', json.dumps(ch, ensure_ascii=False)).replace('__ARRETS__', json.dumps(arrets))
(R / 'apercu_intro_mew_traversee.html').write_text(h)
z = O / 'IMW3_traversee_pack.zip'
with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
    for p in ['IMW3_traversee.mp4', 'manifest.json', 'README.md'] + [f'calques/{x.name}' for x in sorted((O / 'calques').glob('*.png'))] + [f'review/{x}' for x in arrets]:
        zf.write(O / p, p)
print(z.name, round(z.stat().st_size / 1e6, 2), 'Mo')
print('apercu_intro_mew_traversee.html', round((R / 'apercu_intro_mew_traversee.html').stat().st_size / 1e3), 'ko')
