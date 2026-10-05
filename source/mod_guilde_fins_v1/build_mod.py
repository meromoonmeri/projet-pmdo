"""Mod PMDO 0.8.12 unique qui regroupe toutes les fins de donjon de la série (17 Grounds : des 16 biomes d'entrées + Forêt Brumeuse FFB1).
.venv/bin/python source/mod_guilde_fins_v1/build_mod.py

Aucun pixel n'est refait ici : chaque banque .tile et chaque Ground sont copiés OCTET POUR OCTET depuis le ZIP projet
versionné de son lot (`renders/<lot>/<PFX>_projet_pmdo_0812.zip`). Seuls changent :
- le namespace, commun : `guilde_fins_donjons` (les scripts de carte vont dans Data/Script/<namespace>/ground/<asset>/,
  leur contenu est inchangé : ce sont des modules autonomes nommés d'après la carte) ;
- `Content/Tile/index.idx`, fusion des index des lots (un nœud par banque, relu dans la banque elle-même) ;
- Mod.xml, README.md, manifest.json et INSTALLER.py (celui des lots, générique).

Sorties : `.cache/mod_guilde_fins_v1/guilde_fins_donjons/` (dossier du mod), puis
`renders/mod_guilde_fins_v1/guilde_fins_donjons_pmdo_0812.zip` (horodatages fixes : ZIP reproductible),
`renders/mod_guilde_fins_v1/manifest.json`, `planche_cartes.png` et la galerie `apercu_mod_guilde_fins_v1.html`.
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
LOT = 'mod_guilde_fins_v1'
NAMESPACE = 'guilde_fins_donjons'
OUT = R / 'renders' / LOT
STAGE = R / '.cache' / LOT / NAMESPACE
ZIP = OUT / f'{NAMESPACE}_pmdo_0812.zip'
FIXED_DATE = (2026, 10, 3, 12, 0, 0)
# Ordre de la série (chronologique des entrées associées). (dossier du lot, préfixe, titre court, entrée associée, image de scène)
MAPS = [
    ('fin_vapeur_sommet_v1', 'FVS1', 'Fin Vapeur (Steam Cave Peak)', 'ESN1 / ESN2', 'FVS1_scene_t000.png'),
    ('fin_cratere_fosse_v1', 'FCF1', 'Fin Cratère (Dark Crater Pit)', 'ECN1', 'FCF1_scene_t000.png'),
    ('fin_ruine_puits_v1', 'FRP1', 'Fin Ruine (Sealed Ruin Pit)', 'ERN1', 'FRP1_scene_t000.png'),
    ('fin_givre_grotte_v1', 'FGG1', 'Fin Givre V1 (grotte de glace)', 'EGN1', 'FGG1_scene_t000.png'),
    ('fin_givre_aurore_v2', 'FGG2', 'Fin Givre V2 (aurore boréale)', 'EGN1', 'FGG2_scene_t000.png'),
    ('fin_bristle_sommet_v1', 'FBS1', 'Fin Bristle (Mt. Bristle Peak)', 'EBN1', 'FBS1_scene_t000.png'),
    ('fin_jungle_sud_v1', 'FJS1', 'Fin Jungle (Southern Jungle)', 'EJN1', 'FJS1_scene_t000.png'),
    ('fin_waterfall_cave_v1', 'FWC1', 'Fin Waterfall Cave (chambre du joyau)', 'EWC1..3', 'FWC1_scene_t000.png'),
    ('fin_underground_lake_v2', 'FUL2', 'Fin Underground Lake (sanctuaire du lac)', 'EUL1', 'FUL2_scene_t000.png'),
    ('fin_mystifying_forest_v3', 'FMF3', 'Fin Mystifying Forest (sanctuaire sylvestre)', 'EMF1', 'FMF3_scene_t000.png'),
    ('fin_sables_mouvants_v1', 'FSM1', 'Fin Sables mouvants (fosse du désert)', 'EQS1', 'FSM1_scene_t000.png'),
    ('fin_star_cave_v1', 'FST1', 'Fin Star Cave (alcôve de cristal)', 'ESC1', 'FST1_scene_t000.png'),
    ('fin_clairiere_tropicale_v2', 'FCT2', 'Fin Clairière tropicale (autel du lagon)', 'ETC1', 'FCT2_scene_t000.png'),
    ('fin_couloir_violet_v3', 'FCV3', 'Fin Couloir violet (monolithe rocheux)', 'ECV1', 'FCV3_scene_t000.png'),
    ('fin_mt_thunder_v3', 'FMT3', 'Fin Mt. Thunder (sommet d\'orage)', 'EMT1', 'FMT3_scene_t000.png'),
    ('fin_jardin_secret_v2', 'FJS4', 'Fin Jardin secret V2 (stèle de Celebi)', 'EJS1 / EJS2', 'FJS4_scene_t000.png'),
    ('fin_foret_brumeuse_v1', 'FFB1', 'Fin Forêt brumeuse (stèle moussue)', 'EFB1', 'FFB1_scene_t000.png'),
]
N = len(MAPS)
EXCLUDED_STANDALONE = ['fin_ocean_kyogre_v1']  # FOC1 : arène sous-marine autonome hors série des entrées (« Pas dans le mod unique »)


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


INST = loadmod('pmdo_installer', R / 'source/pmdo_cote/INSTALLER.py')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def lot_zip(folder, pfx):
    return R / 'renders' / folder / f'{pfx}_projet_pmdo_0812.zip'


def _tmp(b):
    p = R / '.cache' / LOT / 'tmp_index.idx'; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b); return p


def read_lot(folder, pfx):
    """Contenu utile du ZIP d'un lot : banques, Ground, script, index."""
    z = zipfile.ZipFile(lot_zip(folder, pfx)); names = z.namelist(); root = names[0].split('/')[0]
    rel = {n.split('/', 1)[1]: n for n in names if not n.endswith('/')}
    tiles = {Path(k).stem: z.read(v) for k, v in rel.items() if k.startswith('Content/Tile/') and k.endswith('.tile')}
    grounds = {Path(k).stem: z.read(v) for k, v in rel.items() if k.startswith('Data/Ground/')}
    scripts = {k: z.read(v) for k, v in rel.items() if k.endswith('.lua')}
    assert len(grounds) == 1 and len(scripts) == 1, (folder, grounds.keys(), scripts.keys())
    idx = INST.read_index(_tmp(z.read(rel['Content/Tile/index.idx'])))
    assert set(idx) == set(tiles), folder
    for name, data in tiles.items():
        assert idx[name] == INST.read_node(io.BytesIO(data)), (folder, name)
    return {'root': root, 'tiles': tiles, 'ground': next(iter(grounds.items())), 'script': next(iter(scripts.items())),
            'zip_sha256': sha(lot_zip(folder, pfx).read_bytes())}


def ground_info(raw):
    o = json.loads(raw)['Object']
    layers = o['Layers']; w, h = len(layers[0]['Tiles']) * 8, len(layers[0]['Tiles'][0]) * 8
    anim = sorted({(len(t['Frames']), t['FrameLength']) for L in layers for col in L['Tiles'] for cell in col
                   for t in cell['Layers'] if len(t['Frames']) > 1})
    sheets = sorted({f['Sheet'] for L in layers for col in L['Tiles'] for cell in col for t in cell['Layers'] for f in t['Frames']})
    marks = {m['EntName']: [m['Collider']['X'], m['Collider']['Y']] for m in o['Entities'][0]['Markers']}
    blocked = sum(c['Tags'] for col in o['obstacles'] for c in col)
    return {'nom': o['Name']['DefaultText'], 'taille_px': [w, h], 'calques': len(layers), 'pistes_animees': [list(a) for a in anim],
            'banques_utilisees': sheets, 'marqueurs': marks, 'cases_bloquees': blocked, 'cases': (w // 8) * (h // 8),
            'version': json.loads(raw)['Version']}


def zipdir(path, root):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():
                zi = zipfile.ZipInfo(f'{root.name}/' + p.relative_to(root).as_posix(), FIXED_DATE)
                zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16
                z.writestr(zi, p.read_bytes(), compresslevel=6)


def mod_xml():
    uid = uuid.uuid5(uuid.NAMESPACE_URL, 'meromoonmeri/guilde-treehouse-pmd/' + NAMESPACE)
    return f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Guilde Treehouse - Fins de donjon ({N} cartes) - 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Les {N} zones de fin de donjon 4:3 de la serie Guilde Treehouse, en un seul mod : Grounds animes, collisions et marqueurs entrance / boss / objectif. Base d'edition, aucun warp, pas une aventure jouable.</Description>
  <Namespace>{NAMESPACE}</Namespace>
  <UUID>{uid}</UUID>
  <Version>1.0.0.0</Version>
  <GameVersion>0.8.12.0</GameVersion>
  <ModType>Quest</ModType>
  <Relationships />
</Header>
'''


def readme(rows):
    lines = [
        f'# Guilde Treehouse — zones de fin de donjon ({N} cartes) — mod PMDO 0.8.12', '',
        f'Ce dossier est un mod d\'édition autonome, namespace `{NAMESPACE}`. Il regroupe les **{N} zones de fin de donjon** '
        'au format **4:3 vaste (768 × 576 px)** qui prolongent la série des entrées (`guilde_entrees_sud_nord` + `EFB1`). '
        'Chaque carte est un Ground animé avec ses collisions et trois marqueurs : `entrance` (arrivée, au sud), un marqueur '
        'd\'arène centrale (`boss` ou `arene`) et un marqueur d\'objectif au nord (`objectif`, `source`, `embleme`, `cle_de_voute`, '
        '`cristal`, `belvedere`, `azurill` ou `joyau`). **Aucun warp, aucune sortie** : c\'est une base d\'édition, pas une aventure jouable.', '',
        '**Aucune carte n\'a encore été testée dans PMDO.**', '',
        '## Installer', '',
        f'- **Mod séparé** : copier le dossier `{NAMESPACE}` dans `PMDO/MODS/`, activer le mod, puis ouvrir les Grounds dans l\'éditeur (mode développeur).',
        '- **Dans un mod existant** : `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis la même commande sans `--dry-run`. '
        'L\'installeur ne remplace jamais un fichier existant différent, et fusionne l\'index des tuiles après en avoir fait une sauvegarde.', '',
        '## Cartes', '',
        '| # | Ground | Carte | Entrée associée | Taille | Calques | Animations (frames × ticks) | `entrance` | Arène / Objectif |',
        '|---|---|---|---|---|---|---|---|---|']
    for i, r in enumerate(rows, 1):
        g = r['ground']; m = g['marqueurs']
        an = ', '.join(f'{a} × {b}' for a, b in g['pistes_animees']) or '—'
        others = ', '.join(f'{k}={tuple(v)}' for k, v in m.items() if k != 'entrance')
        lines.append(f"| {i} | `{r['asset']}` | {r['titre']} | `{r['entree_associee']}` | {g['taille_px'][0]} × {g['taille_px'][1]} | "
                     f"{g['calques']} | {an} | {tuple(m.get('entrance', []))} | {others} |")
    lines += ['',
              f'Les {N} cartes sont toutes au format 4:3 vaste 768 × 576 px (96 × 72 cases de 8 px) et possèdent un calque Top vide (`Layer=4`) en dernier.', '',
              '## Limites', '',
              '- Terrains générés à partir des captures des jeux (rendu généré référencé) ; seuls les scintillements Métano sont des tuiles natives.',
              '- Les animations sont créées pour ces cartes : ce ne sont pas les animations officielles.',
              '- Collisions et marqueurs vérifiés sur la grille, pas en jeu (`art_approved: false`, `runtime_tested: false`).', '']
    return '\n'.join(lines)


def planche(rows):
    tw, th, pad, cols = 256, 192, 10, 6
    n = len(rows); rws = (n + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (tw + pad) + pad, rws * (th + 28 + pad) + pad), (20, 27, 36)); d = ImageDraw.Draw(sheet)
    fp = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    font = ImageFont.truetype(str(fp), 12) if fp.exists() else ImageFont.load_default()
    for i, r in enumerate(rows):
        im = Image.open(R / 'renders' / r['lot'] / 'review' / r['image']).convert('RGB')
        im.thumbnail((tw, th), Image.Resampling.LANCZOS)
        x, y = pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + 28 + pad)
        sheet.paste(im, (x + (tw - im.width) // 2, y + (th - im.height) // 2))
        d.text((x + 2, y + th + 5), f"{r['prefixe']}  {r['titre'][:30]}", fill=(228, 230, 242), font=font)
    return sheet


def gallery(rows):
    cards = []
    for r in rows:
        g = r['ground']; img = f"renders/{r['lot']}/review/{r['image']}"
        cards.append(f'<a class="card" href="{r["apercu"]}"><img src="{img}" loading="lazy" alt="{r["prefixe"]}">'
                     f'<b>{r["prefixe"]} — {r["titre"]}</b><span>Entrée : <code>{r["entree_associee"]}</code> · {g["taille_px"][0]}×{g["taille_px"][1]} · '
                     f'{g["calques"]} calques · <code>{r["asset"]}</code></span></a>')
    return f'''<!doctype html>
<html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mod Guilde Treehouse — {N} fins de donjon</title>
<style>
body{{background:#141b24;color:#e4e6f2;font:15px/1.55 system-ui,sans-serif;margin:0;padding:24px}}main{{max-width:1240px;margin:auto}}
h1{{font-size:30px;margin:0 0 6px}}p{{color:#b3c9d3;max-width:90ch}}code{{color:#cfe4ee}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:16px;margin-top:18px}}
.card{{display:flex;flex-direction:column;gap:4px;background:#0b141a;border:1px solid #29404c;border-radius:8px;padding:8px;color:inherit;text-decoration:none}}
.card:hover{{border-color:#e7c77f}}.card img{{width:100%;aspect-ratio:4/3;object-fit:contain;background:#081116;image-rendering:pixelated}}
.card span{{color:#9fb6c0;font-size:13px}}
</style>
<main>
<h1>Mod PMDO 0.8.12 — les {N} zones de fin de donjon (4:3)</h1>
<p>Un seul mod, namespace <code>{NAMESPACE}</code> : <a href="renders/{LOT}/{ZIP.name}" style="color:#e7c77f">{ZIP.name}</a>.
Il regroupe les {N} salles de fin de donjon qui prolongent la série des entrées (<a href="apercu_mod_guilde_entrees_v1.html" style="color:#cfe4ee">mod des entrées</a> + <code>EFB1</code>).
Chaque carte garde ses banques et son Ground octet pour octet ; l'index des tuiles est fusionné. Aucun test en jeu. Cliquer une carte pour ouvrir son aperçu animé.</p>
<div class="grid">
{chr(10).join(cards)}
</div>
</main></html>
'''


def build():
    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE / 'Content/Tile').mkdir(parents=True); (STAGE / 'Data/Ground').mkdir(parents=True)
    OUT.mkdir(parents=True, exist_ok=True)
    nodes, rows, prefixes = {}, [], set()
    for folder, pfx, titre, entree_assoc, image in MAPS:
        L = read_lot(folder, pfx)
        assert pfx not in prefixes; prefixes.add(pfx)
        for name, data in L['tiles'].items():
            assert name.startswith(pfx + '_') and name not in nodes, name
            (STAGE / 'Content/Tile' / f'{name}.tile').write_bytes(data)
            nodes[name] = INST.read_node(io.BytesIO(data))
        asset, graw = L['ground']
        dst = STAGE / 'Data/Ground' / f'{asset}.rsground'; assert not dst.exists(); dst.write_bytes(graw)
        spath, sraw = L['script']
        sd = STAGE / 'Data/Script' / NAMESPACE / 'ground' / asset / 'init.lua'; sd.parent.mkdir(parents=True); sd.write_bytes(sraw)
        info = ground_info(graw)
        assert set(info['banques_utilisees']) <= set(L['tiles']), (asset, set(info['banques_utilisees']) - set(L['tiles']))
        rows.append({'lot': folder, 'prefixe': pfx, 'titre': titre, 'entree_associee': entree_assoc, 'asset': asset, 'image': image,
                     'apercu': f'apercu_{folder}.html', 'zip_source': f'renders/{folder}/{pfx}_projet_pmdo_0812.zip',
                     'zip_source_sha256': L['zip_sha256'], 'namespace_source': L['root'], 'script_source': spath,
                     'banques': sorted(L['tiles']), 'ground': info,
                     'ground_sha256': sha(graw), 'tiles_sha256': {k: sha(v) for k, v in sorted(L['tiles'].items())}})
    (STAGE / 'Content/Tile/index.idx').write_bytes(INST.encode_index(nodes))
    (STAGE / 'Mod.xml').write_text(mod_xml())
    script = (R / 'source/pmdo_cote/INSTALLER.py').read_text()
    needle = '            relative = src.relative_to(source)\n'
    assert needle in script
    script = script.replace(needle, needle + "            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n")
    (STAGE / 'INSTALLER.py').write_text(script)
    (STAGE / 'README.md').write_text(readme(rows))
    manifest = {'lot': LOT, 'namespace': NAMESPACE, 'target': '0.8.12', 'cartes': len(rows), 'banques': len(nodes),
                'hors_serie_autonome': EXCLUDED_STANDALONE, 'runtime_tested': False, 'art_approved': False,
                'methode': 'banques et Grounds copies octet pour octet depuis les ZIP projets versionnes des lots ; index fusionne ; '
                           'scripts deplaces sous le namespace commun, contenu inchange',
                'maps': rows}
    (STAGE / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    (OUT / 'README.md').write_text(readme(rows))
    zipdir(ZIP, STAGE)
    planche(rows).save(OUT / 'planche_cartes.png')
    (R / f'apercu_{LOT}.html').write_text(gallery(rows))
    print(len(rows), 'cartes,', len(nodes), 'banques ->', ZIP.relative_to(R), round(ZIP.stat().st_size / 1e6, 1), 'Mo')


if __name__ == '__main__':
    build()
