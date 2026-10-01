"""Mod PMDO 0.8.12 unique qui regroupe toutes les FINS de donjon de la série (16 Grounds, nord de chaque entrée).
.venv/bin/python source/mod_guilde_fins_v1/build_mod.py

Demande : « bon la suite » (1er octobre 2026, après le mod v2 des entrées). Choix de l'agent, à confirmer : même méthode que
`source/mod_guilde_entrees_v2/build_mod.py`, appliquée aux fins. Aucune validation de l'utilisateur n'est enregistrée pour les fins.

Aucun pixel n'est refait ici : chaque banque .tile et chaque Ground sont copiés OCTET POUR OCTET depuis le ZIP projet
versionné de son lot (`renders/<lot>/<PFX>_projet_pmdo_0812.zip`). Seuls changent :
- le namespace, commun : `guilde_fins_donjon` (les scripts de carte vont dans Data/Script/<namespace>/ground/<asset>/,
  leur contenu est inchangé) ;
- `Content/Tile/index.idx`, fusion des index des lots (un nœud par banque, relu dans la banque elle-même) ;
- Mod.xml, README.md, manifest.json et INSTALLER.py (celui des lots, générique).
Les versions successives d'une même fin sont toutes conservées (FGG1 et FGG2, FCO1 et FCO2).

Sorties : `.cache/mod_guilde_fins_v1/guilde_fins_donjon/`, puis `renders/mod_guilde_fins_v1/guilde_fins_donjon_pmdo_0812.zip`
(horodatages fixes), `manifest.json`, `planche_cartes.png` et la galerie `apercu_mod_guilde_fins_v1.html`.
"""
from pathlib import Path
import hashlib, importlib.util, io, json, shutil, uuid, zipfile

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
LOT = 'mod_guilde_fins_v1'
NAMESPACE = 'guilde_fins_donjon'
OUT = R / 'renders' / LOT
STAGE = R / '.cache' / LOT / NAMESPACE
ZIP = OUT / f'{NAMESPACE}_pmdo_0812.zip'
FIXED_DATE = (2026, 10, 1, 12, 0, 0)
# Ordre de la série (chronologique). (dossier du lot, préfixe, titre court, format, image de scène)
MAPS = [
    ('fin_vapeur_sommet_v1', 'FVS1', 'Vapeur (sommet)', 'FVS1_scene_t000.png'),
    ('fin_cratere_fosse_v1', 'FCF1', 'Cratère (fosse)', 'FCF1_scene_t000.png'),
    ('fin_ruine_puits_v1', 'FRP1', 'Ruine (puits scellé)', 'FRP1_scene_t000.png'),
    ('fin_givre_grotte_v1', 'FGG1', 'Givre, grotte de cristal', 'FGG1_scene_t000.png'),
    ('fin_givre_aurore_v2', 'FGG2', 'Givre V2 (aurore)', 'FGG2_scene_t000.png'),
    ('fin_bristle_sommet_v1', 'FBS1', 'Bristle (sommet)', 'FBS1_scene_t000.png'),
    ('fin_jungle_sud_v1', 'FJS1', 'Jungle sud', 'FJS1_scene_t000.png'),
    ('fin_waterfall_cave_v1', 'FWC1', 'Waterfall Cave', 'FWC1_scene_t000.png'),
    ('fin_ocean_kyogre_v1', 'FOC1', 'Océan de Kyogre', 'FOC1_scene_t000.png'),
    ('fin_sables_mouvants_v1', 'FSM1', 'Sables mouvants', 'FSM1_scene_t000.png'),
    ('fin_star_cave_v1', 'FST1', 'Star Cave', 'FST1_scene_t000.png'),
    ('fin_clairiere_tropicale_v1', 'FTC1', 'Clairière tropicale', 'FTC1_scene_t000.png'),
    ('fin_couloir_violet_v1', 'FCO1', 'Couloir violet', 'FCO1_scene_t000.png'),
    ('fin_couloir_violet_v2', 'FCO2', 'Couloir violet V2', 'FCO2_scene_t000.png'),
    ('fin_mt_thunder_v1', 'FTH1', 'Mt. Thunder', 'FTH1_scene_t000.png'),
    ('fin_jardin_secret_v1', 'FJA1', 'Jardin secret (végétation animée)', 'FJA1_scene_t000.png'),
]
N = len(MAPS)
VALIDATION = {'date': None, 'citation': None,
              'portee': 'aucune validation de l utilisateur enregistree pour les fins ; verifications de fichiers uniquement, aucun test en jeu PMDO',
              'cartes_validees': [], 'a_confirmer': [m[1] for m in MAPS]}


def loadmod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


INST = loadmod('pmdo_installer', R / 'source/pmdo_cote/INSTALLER.py')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def lot_zip(folder, pfx):
    return R / 'renders' / folder / f'{pfx}_projet_pmdo_0812.zip'


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
    for name, data in tiles.items():                              # l'index du lot est bien celui de ses banques
        assert idx[name] == INST.read_node(io.BytesIO(data)), (folder, name)
    return {'root': root, 'tiles': tiles, 'ground': next(iter(grounds.items())), 'script': next(iter(scripts.items())),
            'zip_sha256': sha(lot_zip(folder, pfx).read_bytes())}


def _tmp(b):
    p = R / '.cache' / LOT / 'tmp_index.idx'; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b); return p


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
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():
                zi = zipfile.ZipInfo(f'{root.name}/' + p.relative_to(root).as_posix(), FIXED_DATE)
                zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16
                z.writestr(zi, p.read_bytes(), compresslevel=9)


def mod_xml():
    uid = uuid.uuid5(uuid.NAMESPACE_URL, 'meromoonmeri/guilde-treehouse-pmd/' + NAMESPACE)
    return f'''<?xml version="1.0" encoding="utf-8"?>
<Header>
  <Name>Guilde Treehouse - Fins de donjon ({N} cartes) - 0.8.12</Name>
  <Author>meromoonmeri</Author>
  <Description>Les {N} fins de donjon de la serie Guilde Treehouse, en un seul mod : Grounds animes, collisions et marqueurs entrance / boss / objectif (selon la fin). Base d'edition, aucun warp, pas une aventure jouable.</Description>
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
        f'# Guilde Treehouse — fins de donjon ({N} cartes) — mod PMDO 0.8.12', '',
        f'Ce dossier est un mod d\'édition autonome, namespace `{NAMESPACE}`. Il regroupe les **{N} fins de donjon** de la série, au nord de '
        'chaque entrée sud → nord (mod `guilde_entrees_sud_nord`). Chaque carte est un Ground animé 768 × 576, avec ses collisions et ses marqueurs : '
        '`entrance` (arrivée, au sud) et un ou deux repères au nord (`boss` et `objectif`, ou le repère propre à la fin). **Aucun warp** : c\'est une '
        'base d\'édition, pas une aventure jouable. Les versions successives d\'une même fin sont conservées (FGG1 et FGG2, FCO1 et FCO2).', '',
        '**Aucune validation de l\'utilisateur n\'est enregistrée pour les fins** : elles sont toutes à confirmer. **Aucune carte n\'a encore été testée dans PMDO.**', '',
        '## Installer', '',
        f'- **Mod séparé** : copier le dossier `{NAMESPACE}` dans `PMDO/MODS/`, activer le mod, puis ouvrir les Grounds dans l\'éditeur (mode développeur).',
        '- **Dans un mod existant** : `python INSTALLER.py /chemin/PMDO/MODS/mon_mod --dry-run`, puis la même commande sans `--dry-run`. '
        'L\'installeur ne remplace jamais un fichier existant différent, et fusionne l\'index des tuiles après en avoir fait une sauvegarde.', '',
        '## Cartes', '',
        '| # | Ground | Fin | Calques | Animations (frames × ticks) | Marqueurs |',
        '|---|---|---|---|---|---|']
    for i, r in enumerate(rows, 1):
        g = r['ground']
        an = ', '.join(f'{a} × {b}' for a, b in g['pistes_animees']) or '—'
        mk = ', '.join(f'`{k}` {tuple(v)}' for k, v in sorted(g['marqueurs'].items(), key=lambda kv: -kv[1][1]))
        lines.append(f"| {i} | `{r['asset']}` | {r['titre']} | {g['calques']} | {an} | {mk} |")
    lines += ['', 'Toutes les cartes font 768 × 576 (96 × 72 cases de 8 px). Chaque carte a un calque Top vide (`Layer=4`) en dernier.', '',
              '## Scripts', '',
              f'Chaque carte a son script `Data/Script/{NAMESPACE}/ground/<carte>/init.lua`, copié tel quel depuis son lot.', '',
              '## Limites', '',
              '- Terrains générés à partir de captures des jeux (rendu généré référencé) ; les rendus générés ne sont pas des tuiles natives, sauf les fleurs Halcyon de FJA1 (Palikadude/Halcyon, attribution à ses auteurs).',
              '- Les animations sont créées pour ces cartes : ce ne sont pas les animations officielles.',
              '- Collisions et marqueurs vérifiés sur la grille, pas en jeu. Aucun marqueur n\'est raccordé à un donjon ou à un boss réel.', '']
    return '\n'.join(lines)


def planche(rows):
    tw, th, pad, cols = 256, 192, 10, 6
    n = len(rows); rws = (n + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (tw + pad) + pad, rws * (th + 28 + pad) + pad), (20, 27, 36)); d = ImageDraw.Draw(sheet)
    fp = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')        # police à accents (celle par défaut n'en a pas)
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
                     f'<b>{r["prefixe"]} — {r["titre"]}</b><span>{g["taille_px"][0]}×{g["taille_px"][1]} · {g["calques"]} calques · '
                     f'<code>{r["asset"]}</code></span></a>')
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
<h1>Mod PMDO 0.8.12 — les {N} fins de donjon</h1>
<p>Un seul mod, namespace <code>{NAMESPACE}</code> : <a href="renders/{LOT}/{ZIP.name}" style="color:#e7c77f">{ZIP.name}</a>.
Chaque carte garde ses banques et son Ground octet pour octet ; l'index des tuiles est fusionné. Aucune fin n'est encore validée
artistiquement (toutes à confirmer). Aucun test en jeu. Cliquer une carte pour ouvrir son aperçu animé.</p>
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
    for folder, pfx, titre, image in MAPS:
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
        rows.append({'lot': folder, 'prefixe': pfx, 'titre': titre, 'asset': asset, 'image': image,
                     'apercu': f'apercu_{folder}.html', 'zip_source': f'renders/{folder}/{pfx}_projet_pmdo_0812.zip',
                     'zip_source_sha256': L['zip_sha256'], 'namespace_source': L['root'], 'script_source': spath,
                     'banques': sorted(L['tiles']), 'ground': info,
                     'ground_sha256': sha(graw), 'tiles_sha256': {k: sha(v) for k, v in sorted(L['tiles'].items())}})
    (STAGE / 'Content/Tile/index.idx').write_bytes(INST.encode_index(nodes))
    (STAGE / 'Mod.xml').write_text(mod_xml())
    # Installeur des lots (tous sauf ESN1) : celui de source/pmdo_cote, corrigé pour ne pas copier index.idx comme un fichier
    # ordinaire (sinon une réinstallation le voit en conflit). Même correctif que dans les build.py des lots.
    script = (R / 'source/pmdo_cote/INSTALLER.py').read_text()
    needle = '            relative = src.relative_to(source)\n'
    assert needle in script
    script = script.replace(needle, needle + "            if relative.as_posix() == 'Content/Tile/index.idx':\n                continue\n")
    (STAGE / 'INSTALLER.py').write_text(script)
    (STAGE / 'README.md').write_text(readme(rows))
    manifest = {'lot': LOT, 'namespace': NAMESPACE, 'target': '0.8.12', 'cartes': len(rows), 'banques': len(nodes),
                'validation_utilisateur': VALIDATION, 'runtime_tested': False,
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
