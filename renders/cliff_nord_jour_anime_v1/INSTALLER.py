#!/usr/bin/env python3
"""Installe ou met a jour les calques animes de nuages et de mer pour
cliffnordouesttest1.rsground et cliffdaytest.rsground dans un mod PMDO 0.8.12 existant.

- Sauvegarde automatiquement (.avant_anim.bak) les fichiers .rsground, .tile et index.idx
  existants avant de les mettre a jour.
- Ne remplace JAMAIS vos autres feuilles .tile personnalisees (terrain, INVERSEPATHWAY, etc.).
- Reconstruit Content/Tile/index.idx avec les nouvelles banques animees.

Usage :
  python INSTALLER.py "CHEMIN/VERS/PMDO/MODS/VOTRE_MOD" --dry-run
  python INSTALLER.py "CHEMIN/VERS/PMDO/MODS/VOTRE_MOD"
"""
import argparse
from pathlib import Path
import shutil
import struct

CORE_TILES = {'00_ciel.tile', '01_long_cap_jour_02.tile', 'v2_promontoire_jour_03.tile'}
CORE_GROUNDS = {'cliffnordouesttest1.rsground', 'cliffdaytest.rsground'}


def exact(stream, size):
    data = stream.read(size)
    if len(data) != size:
        raise ValueError('Fichier binaire tronque')
    return data


def read_string(stream):
    size = 0
    for shift in range(0, 35, 7):
        byte = exact(stream, 1)[0]
        size |= (byte & 127) << shift
        if byte < 128:
            return exact(stream, size).decode('utf-8')
    raise ValueError('Longueur .NET invalide')


def write_string(value):
    raw = value.encode('utf-8')
    size, header = len(raw), bytearray()
    while size >= 128:
        header.append((size & 127) | 128)
        size >>= 7
    return bytes(header) + bytes([size]) + raw


def read_node(stream):
    header = exact(stream, 8)
    tile_size, count = struct.unpack('<ii', header)
    if tile_size <= 0 or not 0 <= count <= 10_000_000:
        raise ValueError('En-tete TileIndexNode invalide')
    return header + exact(stream, count * 16)


def read_index(path):
    if not path.exists():
        return {}
    with path.open('rb') as f:
        count = struct.unpack('<i', exact(f, 4))[0]
        nodes = {}
        for _ in range(count):
            name = read_string(f)
            nodes[name] = read_node(f)
        return nodes


def encode_index(nodes):
    return struct.pack('<i', len(nodes)) + b''.join(write_string(k) + nodes[k] for k in sorted(nodes))


def install(source, target, dry_run=False):
    source, target = Path(source).resolve(), Path(target).resolve()
    if not (target / 'Mod.xml').is_file():
        raise ValueError('Choisir la racine du mod contenant Mod.xml.')

    updates = []
    for tname in sorted(CORE_TILES):
        src = source / 'Content/Tile' / tname
        if src.is_file():
            updates.append((src, target / 'Content/Tile' / tname, True))
    for src in sorted((source / 'Content/Tile').glob('*.tile')):
        if src.name not in CORE_TILES:
            dst = target / 'Content/Tile' / src.name
            if not dst.exists():
                updates.append((src, dst, False))
    for src in sorted((source / 'Content/BG').glob('*.dir')):
        updates.append((src, target / 'Content/BG' / src.name, True))
    for gname in sorted(CORE_GROUNDS):
        src = source / 'Data/Ground' / gname
        if not src.is_file():
            src = source / gname
        if src.is_file():
            updates.append((src, target / 'Data/Ground' / gname, True))

    print(f'{len(updates)} fichiers a installer/mettre a jour dans {target}')
    if dry_run:
        for src, dst, _ in updates:
            print('  [DRY-RUN]', dst.relative_to(target))
        return

    for src, dst, overwrite in updates:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            if not overwrite:
                continue
            if dst.read_bytes() != src.read_bytes():
                bak = dst.with_suffix(dst.suffix + '.avant_anim.bak')
                if not bak.exists():
                    shutil.copy2(dst, bak)
        shutil.copy2(src, dst)

    idx_path = target / 'Content/Tile/index.idx'
    nodes = read_index(idx_path)
    for tile in sorted((target / 'Content/Tile').glob('*.tile')):
        with tile.open('rb') as f:
            nodes[tile.stem] = read_node(f)
    new_idx = encode_index(nodes)
    if idx_path.exists() and idx_path.read_bytes() != new_idx:
        bak = idx_path.with_suffix('.idx.avant_anim.bak')
        if not bak.exists():
            shutil.copy2(idx_path, bak)
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_bytes(new_idx)
    print(f'Installation terminee : index.idx mis a jour ({len(nodes)} feuilles .tile).')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('target', help='Chemin du mod PMDO cible (dossier contenant Mod.xml)')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    install(Path(__file__).resolve().parent, Path(args.target), args.dry_run)
