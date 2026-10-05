#!/usr/bin/env python3
"""Restaure des lots retirés du dernier état par l'allègement du 2 octobre 2026 (bibliothèque standard seulement).

    python3 source/restaurer_lot.py --liste [motif]            # lots archivés : date, taille, dépendances de build
    python3 source/restaurer_lot.py LOT [LOT ...]              # restaure renders/LOT, son ZIP voisin et son aperçu
    python3 source/restaurer_lot.py --avec-dependances LOT     # + les lots archivés que ses scripts lisent (indicatif)
    python3 source/restaurer_lot.py --prefixe world_map        # tous les lots dont le nom commence par ce préfixe
    python3 source/restaurer_lot.py --a-sec LOT                # montre ce qui serait restauré, sans rien télécharger
    python3 source/restaurer_lot.py --tout                     # TOUT (≈ 4,2 Go) : à éviter en session Arena

Les fichiers reviennent aux mêmes chemins, octet pour octet, depuis le commit d'archive du manifeste
`source/allegement_2026-10-02.json` (aucun historique n'a été réécrit). La récupération est partielle : seuls les
fichiers demandés sont téléchargés. Une base d'objets annexe est tenue dans `.cache/archive_pmdo/` (ignorée par Git) ;
la configuration du dépôt principal n'est pas modifiée.

Les fichiers restaurés restent NON SUIVIS et sont ajoutés à `.git/info/exclude` : un `git add -A` ne les recommit pas
par erreur. Pour re-versionner un lot volontairement, retirer ses lignes de `.git/info/exclude` puis `git add`.
"""
from pathlib import Path
import argparse, difflib, json, os, subprocess, sys

R = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name('allegement_2026-10-02.json')
ODB = R / '.cache' / 'archive_pmdo'
MARQUE = "# restauré depuis l'archive d'allègement (non suivi volontairement) : source/restaurer_lot.py"


def git(*args, gd=None, check=True):
    cmd = ['git'] + (['--git-dir', str(gd)] if gd else []) + [str(a) for a in args]
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', LC_ALL='C', GIT_LITERAL_PATHSPECS='1')
    p = subprocess.run(cmd, cwd=R, env=env, text=True, capture_output=True)
    if check and p.returncode:
        sys.exit(f"git {' '.join(map(str, args[:3]))}… a échoué : {(p.stderr or p.stdout).strip()[:400]}")
    return p


def mo(octets):
    return f'{octets / 1e6:,.1f} Mo'.replace(',', ' ')


def choisir(M, args):
    lots = M['lots']
    noms = []
    if args.tout:
        noms = sorted(lots)
    for pre in args.prefixe or []:
        noms += [l for l in sorted(lots) if l.startswith(pre)]
    for l in args.lots:
        if l not in lots:
            proches = difflib.get_close_matches(l, lots, n=4)
            sys.exit(f"Lot archivé inconnu : {l}" + (f"\nVouliez-vous dire : {', '.join(proches)} ?" if proches else
                                                    "\nVoir : python3 source/restaurer_lot.py --liste"))
        noms.append(l)
    if args.avec_dependances:                       # fermeture transitive sur « lit » (indicatif)
        vus, pile = set(), list(noms)
        while pile:
            l = pile.pop()
            if l in vus:
                continue
            vus.add(l)
            pile += [d for d in lots[l].get('lit', []) if d in lots]
        noms = sorted(vus)
    return sorted(dict.fromkeys(noms))


def base_objets(sha, url):
    """Base annexe (init + remote + récupération partielle du seul commit d'archive)."""
    gd = ODB / '.git'
    if not gd.exists():
        ODB.mkdir(parents=True, exist_ok=True)
        git('init', '-q', str(ODB))
        git('remote', 'add', 'origin', url, gd=gd)
    alt = R / '.git' / 'objects'                    # réutilise les objets déjà présents dans le dépôt principal
    if alt.is_dir():
        (gd / 'objects' / 'info').mkdir(parents=True, exist_ok=True)
        (gd / 'objects' / 'info' / 'alternates').write_text(str(alt) + '\n')
    if git('cat-file', '-e', f'{sha}^{{tree}}', gd=gd, check=False).returncode:
        print(f'Récupération des métadonnées du commit {sha[:8]} (quelques secondes, ~1 Mo)…')
        git('fetch', '-q', '--depth=1', '--filter=blob:none', 'origin', sha, gd=gd)
    return gd


def exclure(chemins):
    exc = R / '.git' / 'info' / 'exclude'
    if not (R / '.git').is_dir():
        print("(.git n'est pas un dossier : exclusion locale non ajoutée, ne pas faire de `git add -A`)")
        return
    exc.parent.mkdir(parents=True, exist_ok=True)
    texte = exc.read_text() if exc.exists() else ''
    ajout = []
    for c in chemins:
        ligne = '/' + c + ('/' if (R / c).is_dir() else '')
        if ligne not in texte.splitlines():
            ajout.append(ligne)
    if ajout:
        with exc.open('a') as f:
            if MARQUE not in texte:
                f.write(('' if texte.endswith('\n') or not texte else '\n') + MARQUE + '\n')
            f.write('\n'.join(ajout) + '\n')


def main():
    ap = argparse.ArgumentParser(description="Restaure des lots archivés (voir ALLEGEMENT.md).")
    ap.add_argument('lots', nargs='*', help='noms de lots (ex. cendres_palette_raccord_v4)')
    ap.add_argument('--liste', nargs='?', const='', metavar='MOTIF', help='liste les lots archivés (filtre texte facultatif)')
    ap.add_argument('--prefixe', action='append', help='restaure tous les lots commençant par ce préfixe')
    ap.add_argument('--avec-dependances', action='store_true', help='ajoute les lots lus par les scripts du lot (indicatif)')
    ap.add_argument('--a-sec', action='store_true', help='affiche le plan sans rien télécharger')
    ap.add_argument('--tout', action='store_true', help='restaure tous les lots archivés (≈ 4,2 Go)')
    ap.add_argument('--commit', help="commit d'archive (défaut : celui du manifeste)")
    args = ap.parse_args()
    M = json.loads(MANIFEST.read_text(encoding='utf-8'))
    lots = M['lots']

    if args.liste is not None:
        sel = [l for l in sorted(lots) if args.liste in l]
        print(f"{len(sel)} lot(s) archivé(s) sur {len(lots)} — commit d'archive {M['commit_archive'][:8]}")
        for l in sel:
            v = lots[l]
            lit = f"  lit : {', '.join(v['lit'])}" if v.get('lit') else ''
            print(f"{l:44s} {v['derniere_modif']}  {mo(v['octets']):>10s}  {v['fichiers']:6d} fichiers{lit}")
        return
    noms = choisir(M, args)
    if not noms:
        ap.error('indiquez au moins un lot (ou --liste, --prefixe, --tout)')
    chemins = sorted({c for l in noms for c in lots[l]['chemins']})
    octets = sum(lots[l]['octets'] for l in noms)
    fichiers = sum(lots[l]['fichiers'] for l in noms)
    print(f"{len(noms)} lot(s), {fichiers} fichiers, {mo(octets)} :")
    for l in noms:
        print(f"  {l:44s} {mo(lots[l]['octets']):>10s}")
    if args.a_sec:
        print('Chemins :', *chemins, sep='\n  ')
        return
    sha = args.commit or M['commit_archive']
    url = git('remote', 'get-url', 'origin', check=False).stdout.strip() or M['depot'] + '.git'
    gd = base_objets(sha, url)
    attendu = git('ls-tree', '-r', '-l', '-z', sha, '--', *chemins, gd=gd).stdout.split('\0')
    fichiers_attendus = {}
    for rec in filter(None, attendu):
        meta, chemin = rec.split('\t', 1)
        fichiers_attendus[chemin] = int(meta.split()[3])
    if not fichiers_attendus:
        sys.exit("Aucun fichier trouvé dans le commit d'archive pour ces chemins (mauvais --commit ?).")
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_WORK_TREE=str(R), GIT_LITERAL_PATHSPECS='1')
    print(f'Restauration de {len(fichiers_attendus)} fichiers depuis {sha[:8]}…')
    p = subprocess.run(['git', '--git-dir', str(gd), 'checkout', '-q', sha, '--', *chemins], cwd=R, env=env,
                       text=True, capture_output=True)
    if p.returncode:
        sys.exit(f"Échec de la restauration : {(p.stderr or p.stdout).strip()[:500]}")
    manque = [c for c, t in fichiers_attendus.items() if not (R / c).is_file() or (R / c).stat().st_size != t]
    if manque:
        sys.exit(f"{len(manque)} fichier(s) absent(s) ou de taille inattendue, par exemple : {manque[:3]}")
    exclure(chemins)
    print(f"OK : {len(fichiers_attendus)} fichiers restaurés, vérifiés (présence et taille), non suivis par Git.")
    if any(lots[l].get('lit') for l in noms) and not args.avec_dependances:
        print("Note : certains de ces lots lisent d'autres lots archivés pour être reconstruits ; "
              "ajouter --avec-dependances si besoin.")


if __name__ == '__main__':
    main()
