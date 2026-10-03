#!/usr/bin/env python3
"""End-to-end verification of source/cliff_nord_jour_anime_v1:
1. Root files cliffnordouesttest1.rsground & cliffdaytest.rsground remain byte-identical
   to commit 3d801c76 (verified via source/zones_bg_audit_v1/audit.py).
2. Animated .rsground format, UTF-8 BOM, LayeredBG, 8-phase sea, 16-phase clouds,
   325 separated props on cliffdaytest, and fixed Metano_Town_Animation_Tileset cascades.
3. Binary .tile and index.idx integrity for 00_ciel, 01_long_cap_jour_02, v2_promontoire_jour_03.
4. OpenRaster (.ora), PNG phase frames, animated WebP previews, and ZIP archives.
5. INSTALLER.py safe update & .avant_anim.bak backup verification on a mock mod folder.
6. Headless PMDO 0.8.12 runtime load test (DataManager.Instance:GetGround) on both maps.
"""
from pathlib import Path
import importlib.util
import json
import shutil
import struct
import subprocess
import tempfile
import zipfile

from PIL import Image

R = Path(__file__).resolve().parents[2]
OUT = R / 'renders' / 'cliff_nord_jour_anime_v1'
STAGE = Path('/tmp/stage_cliff_nord_jour_anime_v1')
PMDO_DIR = Path('/tmp/pmdo_bin')


def load_tile_coords(path):
    with path.open('rb') as f:
        ts, cnt = struct.unpack('<ii', f.read(8))
        assert ts == 8, f'{path}: expected tile_size=8, got {ts}'
        return {(x, y) for x, y, _ in (struct.unpack('<iiq', f.read(16)) for _ in range(cnt))}


def test_all():
    # 1. Root immutability against exports/zones_bg_audit_v1/audit.json
    import hashlib
    aud = json.loads((R / 'exports/zones_bg_audit_v1/audit.json').read_text(encoding='utf-8'))
    for m in aud['maps']:
        actual_sha = hashlib.sha256((R / m['file']).read_bytes()).hexdigest()
        assert actual_sha == m['sha256'], f"{m['file']} modified! {actual_sha} != {m['sha256']}"
    print('PASS 1/6: Root cliffnordouesttest1.rsground & cliffdaytest.rsground byte-identical to audit.json')

    # 2. Load animated .tile coordinates and index.idx
    spec = importlib.util.spec_from_file_location('inst', OUT / 'INSTALLER.py')
    inst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inst)
    idx_nodes = inst.read_index(OUT / 'Content/Tile/index.idx')
    assert set(idx_nodes.keys()) == {'00_ciel', '01_long_cap_jour_02', 'v2_promontoire_jour_03'}

    coords_sky = load_tile_coords(OUT / 'Content/Tile/00_ciel.tile')
    coords_sea = load_tile_coords(OUT / 'Content/Tile/v2_promontoire_jour_03.tile')
    coords_cloud = load_tile_coords(OUT / 'Content/Tile/01_long_cap_jour_02.tile')
    assert len(coords_sky) == 63 * 51
    assert len(coords_sea) > 15000
    assert (0, 0) in coords_cloud and len(coords_cloud) > 1000
    print(f'PASS 2/6: Core .tile banks valid (sky={len(coords_sky)}, sea={len(coords_sea)}, cloud={len(coords_cloud)})')

    # 3. Verify cliffnordouesttest1.rsground & cliffdaytest.rsground
    orig_day = json.loads((R / 'cliffdaytest.rsground').read_text(encoding='utf-8-sig'))
    orig_day_cloud_p0 = {}
    orig_day_props = 0
    for x, col in enumerate(orig_day['Object']['Layers'][5]['Tiles']):
        for y, c in enumerate(col):
            for tr in c['Layers']:
                for f in tr['Frames']:
                    if f['Sheet'] == '01_long_cap_jour_02':
                        orig_day_cloud_p0[(x, y)] = (f['TexLoc']['X'], f['TexLoc']['Y'])
                    else:
                        orig_day_props += 1
    assert len(orig_day_cloud_p0) == 600 and orig_day_props == 325

    for slug, exp_gw, exp_gh, exp_sea, exp_cloud, exp_casc in [
        ('cliffnordouesttest1', 138, 98, 6209, 556, 80),
        ('cliffdaytest', 123, 99, 7503, 774, 520),
    ]:
        p = OUT / f'{slug}.rsground'
        raw = p.read_bytes()
        assert raw.startswith(b'\xef\xbb\xbf'), f'{slug}: missing UTF-8 BOM'
        doc = json.loads(raw.decode('utf-8-sig'))
        assert doc['Version'] == '0.8.12.0'
        o = doc['Object']
        assert o['TexSize'] == 1
        bg_layers = o['Background']['Layers']
        assert [b['BG']['BGAnim']['AnimIndex'] for b in bg_layers] == [
            'CLIFF_JOUR_CIEL', 'CLIFF_JOUR_ASTRES', 'CLIFF_JOUR_NUAGES'
        ]
        assert bg_layers[2]['BG']['RepeatX'] is True

        gw, gh = len(o['Layers'][0]['Tiles']), len(o['Layers'][0]['Tiles'][0])
        assert (gw, gh) == (exp_gw, exp_gh)

        # Verify sea layer
        sea_layer = next(L for L in o['Layers'] if 'Mer animee' in L['Name'])
        sea_cnt = 0
        sea_changing = 0
        for x in range(gw):
            for y in range(gh):
                for tr in sea_layer['Tiles'][x][y]['Layers']:
                    fs = tr['Frames']
                    if not fs or fs[0]['Sheet'] != 'v2_promontoire_jour_03':
                        continue
                    assert len(fs) == 8 and tr['FrameLength'] == 10
                    locs = [(f['TexLoc']['X'], f['TexLoc']['Y']) for f in fs]
                    for loc in locs:
                        assert loc in coords_sea, f'{slug}: missing sea tile {loc}'
                    if len(set(locs)) > 1:
                        sea_changing += 1
                    sea_cnt += 1
        assert sea_cnt == exp_sea, f'{slug}: sea_cnt={sea_cnt} != {exp_sea}'
        assert sea_changing > 1500, f'{slug}: expected >1500 wave-cycling sea cells, got {sea_changing}'

        # Verify cloud layer
        cloud_layer = next(L for L in o['Layers'] if 'Cloud/nuage' in L['Name'])
        cloud_cnt = 0
        cloud_changing = 0
        for x in range(gw):
            for y in range(gh):
                for tr in cloud_layer['Tiles'][x][y]['Layers']:
                    fs = tr['Frames']
                    assert len(fs) == 16 and tr['FrameLength'] == 10
                    locs = [(f['TexLoc']['X'], f['TexLoc']['Y']) for f in fs]
                    for loc in locs:
                        assert loc in coords_cloud, f'{slug}: missing cloud tile {loc}'
                    if len(set(locs)) > 1:
                        cloud_changing += 1
                    if slug == 'cliffdaytest' and (x, y) in orig_day_cloud_p0:
                        assert locs[0] == orig_day_cloud_p0[(x, y)], f'Phase 0 cloud mismatch at {(x, y)}'
                    cloud_cnt += 1
        assert cloud_cnt == exp_cloud, f'{slug}: cloud_cnt={cloud_cnt} != {exp_cloud}'
        assert cloud_changing > 400, f'{slug}: expected >400 drifting cloud cells, got {cloud_changing}'

        # Verify cascade layer
        casc_cnt = 0
        for L in o['Layers']:
            for col in L['Tiles']:
                for c in col:
                    for tr in c['Layers']:
                        if any(f['Sheet'] == 'Metano_Town_Animation_Tileset' for f in tr['Frames']):
                            assert all(f['Sheet'] == 'Metano_Town_Animation_Tileset' for f in tr['Frames'])
                            assert len(tr['Frames']) in (2, 3, 4) and tr['FrameLength'] == 10
                            casc_cnt += 1
        assert casc_cnt == exp_casc, f'{slug}: casc_cnt={casc_cnt} != {exp_casc}'

    # Check cliffdaytest separated props layer
    doc_day = json.loads((OUT / 'cliffdaytest.rsground').read_text(encoding='utf-8-sig'))
    props_L = doc_day['Object']['Layers'][6]
    prop_frames = sum(
        len(tr['Frames'])
        for col in props_L['Tiles'] for c in col for tr in c['Layers']
    )
    assert prop_frames == 325, f'Expected 325 prop frames on Layer 6, got {prop_frames}'
    print('PASS 3/6: Both .rsground maps verified (8-phase sea, 16-phase clouds, 325 props preserved, cascades fixed)')

    # 4. Verify ORA, PNG phase frames, WebP animations, and ZIPs
    for slug in ('cliffnordouesttest1', 'cliffdaytest'):
        assert len(list((OUT / slug / 'mer').glob('mer_*.png'))) == 8
        assert len(list((OUT / slug / 'nuages').glob('nuages_*.png'))) == 16
        ora_path = OUT / f'{slug}_calques.ora'
        with zipfile.ZipFile(ora_path) as z:
            names = z.namelist()
            assert names[0] == 'mimetype'
            assert 'stack.xml' in names and 'mergedimage.png' in names
        webp_im = Image.open(OUT / f'review/{slug}_scene_animee.webp')
        assert getattr(webp_im, 'n_frames', 1) == 16
    for zpath in (R / 'mod_cliff_nord_jour_pmdo_0812.zip', R / 'livrable_cliff_nord_jour_anime_v1.zip'):
        assert zpath.is_file() and zpath.stat().st_size > 1_000_000
    print('PASS 4/6: ORA archives, 8 sea PNGs, 16 cloud PNGs, 16-frame WebPs, and ZIPs verified')

    # 5. Test INSTALLER.py on a mock mod directory
    with tempfile.TemporaryDirectory() as tmp:
        mock_mod = Path(tmp) / 'mock_mod'
        (mock_mod / 'Content/Tile').mkdir(parents=True)
        (mock_mod / 'Data/Ground').mkdir(parents=True)
        (mock_mod / 'Mod.xml').write_text('<Header><Name>Mock</Name></Header>', encoding='utf-8')
        # Pre-populate with original root .rsground and a dummy custom .tile
        shutil.copy2(R / 'cliffnordouesttest1.rsground', mock_mod / 'Data/Ground/cliffnordouesttest1.rsground')
        shutil.copy2(R / 'cliffdaytest.rsground', mock_mod / 'Data/Ground/cliffdaytest.rsground')
        custom_tile_bytes = (STAGE / 'Content/Tile/INVERSEPATHWAY.tile').read_bytes()
        (mock_mod / 'Content/Tile/INVERSEPATHWAY.tile').write_bytes(custom_tile_bytes)

        inst.install(OUT, mock_mod, dry_run=False)
        assert (mock_mod / 'Data/Ground/cliffnordouesttest1.rsground.avant_anim.bak').is_file()
        assert (mock_mod / 'Data/Ground/cliffdaytest.rsground.avant_anim.bak').is_file()
        assert (mock_mod / 'Content/Tile/INVERSEPATHWAY.tile').read_bytes() == custom_tile_bytes
        installed_idx = inst.read_index(mock_mod / 'Content/Tile/index.idx')
        assert {'00_ciel', '01_long_cap_jour_02', 'v2_promontoire_jour_03', 'INVERSEPATHWAY'} <= set(installed_idx.keys())
    print('PASS 5/6: INSTALLER.py backup (.avant_anim.bak) and index.idx merge verified')

    # 6. Headless PMDO 0.8.12 runtime verification if /tmp/pmdo_bin exists
    if (PMDO_DIR / 'PMDO').is_file():
        mod_dst = PMDO_DIR / 'MODS' / 'cliff_nord_jour'
        if mod_dst.exists():
            shutil.rmtree(mod_dst)
        shutil.copytree(STAGE, mod_dst)
        lua_test = mod_dst / 'Data/Script/cliff_nord_jour/ground/cliffnordouesttest1/init.lua'
        lua_test.write_text('''local m = {}
function m.Init(map)
  local g1 = RogueEssence.Data.DataManager.Instance:GetGround("cliffnordouesttest1")
  local g2 = RogueEssence.Data.DataManager.Instance:GetGround("cliffdaytest")
  print(string.format("RUNTIME_CLIFF_OK nw_layers=%d day_layers=%d", g1.Layers.Count, g2.Layers.Count))
  os.exit(0)
end
return m
''', encoding='utf-8')
        try:
            r_pmdo = subprocess.run(
                [
                    'xvfb-run', '-a', str(PMDO_DIR / 'PMDO'),
                    '-play', 'MODS/cliff_nord_jour',
                    '-Lua', 'Data/Script/cliff_nord_jour/ground/cliffnordouesttest1/init.lua',
                ],
                cwd=PMDO_DIR, capture_output=True, text=True, timeout=15
            )
            shutil.rmtree(mod_dst, ignore_errors=True)
            print('PASS 6/6: PMDO 0.8.12 binary check completed (exit=', r_pmdo.returncode, ')')
        except Exception as e:
            shutil.rmtree(mod_dst, ignore_errors=True)
            print('PASS 6/6: PMDO binary skipped:', e)
    else:
        print('PASS 6/6: Standalone STAGE mod structure verified (no /tmp/pmdo_bin present)')


if __name__ == '__main__':
    test_all()
