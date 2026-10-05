"""Plan de composition (aplats de couleur) donné au générateur d'images, 1024 x 768 (4:3).

.venv/bin/python source/zone_plage_recifs_etoiles_v1/guide.py      -> references/guide_plage_x4_3.png
Magenta = mer et ciel ; jaune = sable ; rouge = promontoires rocheux ; vert = palmiers et herbes ; cyan = mares.
"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import geometrie as G

K = 4 / 3


def S(pts):
    return [(x * K, y * K) for x, y in pts]


def main():
    im = Image.new('RGB', (int(G.W * K), int(G.H * K)), (255, 0, 255))
    d = ImageDraw.Draw(im)
    sable = (242, 230, 150)
    d.polygon(S([(150, 300)] + G.COTE + [(620, 300), (768, 300), (768, 576), (0, 576), (0, 300)]), fill=sable)
    d.line(S(G.COTE), fill=(214, 186, 104), width=10)                       # sable mouillé, limite de la mer
    d.polygon(S(G.CHEMIN), fill=(236, 206, 132))
    for roc in (G.ROC_G, G.ROC_D):
        d.polygon(S(roc), fill=(176, 72, 60), outline=(118, 40, 40))
    for (x, y), r in G.PETITS_ROCHERS:
        d.ellipse(S([(x - r, y - r * 0.8), (x + r, y + r * 0.8)]), fill=(170, 70, 58), outline=(118, 40, 40))
    (x0, y0), (x1, y1), e = G.BOIS_FLOTTE
    d.line(S([(x0, y0), (x1, y1)]), fill=(140, 100, 62), width=int(e * K))
    for (x, y), (rx, ry) in G.MARES:
        d.ellipse(S([(x - rx, y - ry), (x + rx, y + ry)]), fill=(84, 196, 226))
    for (px, py) in G.HERBES:
        d.ellipse(S([(px - 8, py - 6), (px + 8, py + 6)]), fill=(76, 160, 60))
    for (pied, cime) in G.PALMIERS:
        d.line(S([pied, (cime[0], cime[1] + 16)]), fill=(122, 82, 44), width=int(5 * K))
        cx, cy = cime
        d.polygon(S([(cx - 40, cy + 10), (cx - 16, cy - 8), (cx, cy - 22), (cx + 16, cy - 8), (cx + 40, cy + 10),
                     (cx + 22, cy + 22), (cx, cy + 14), (cx - 22, cy + 22)]), fill=(44, 142, 46), outline=(24, 90, 30))
    out = HERE / 'references/guide_plage_x4_3.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    print(out, im.size)


if __name__ == '__main__':
    main()
