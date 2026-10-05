"""Géométrie de la zone « Plage aux récifs étoilés » (ZPR1) : 768 x 576 px.

Ces coordonnées servent (1) à dessiner le plan donné au générateur d'images (guide.py) et (2) de repères pour les
contrôles. Le décor de terre (sable, roches, palmiers) est celui du brut généré : les masques praticables en sont
tirés, ces polygones ne sont qu'un guide de composition.
"""
W, H = 768, 576

# bord mer du promontoire gauche / droit (du haut de l'écran vers le fond de la baie)
TETE_G = [(0, 150), (40, 160), (80, 190), (110, 225), (140, 262), (176, 296), (214, 326)]
TETE_D = [(768, 160), (728, 170), (690, 200), (656, 236), (628, 270), (596, 304), (560, 332)]
# côte de sable au fond de la baie (limite mer / sable)
COTE = [(214, 326), (260, 352), (320, 366), (384, 372), (440, 368), (500, 356), (560, 332)]
ROC_G = TETE_G + [(200, 380), (170, 430), (130, 470), (60, 500), (0, 500)]
ROC_D = TETE_D + [(580, 380), (610, 430), (650, 470), (710, 500), (768, 500)]

# palmiers : (pied, cime)
PALMIERS = [((118, 432), (98, 352)), ((160, 450), (170, 362)), ((198, 426), (214, 344)),
            ((574, 440), (556, 360)), ((618, 454), (614, 372)), ((666, 432), (684, 350))]
PETITS_ROCHERS = [((300, 482), 15), ((472, 470), 13), ((398, 542), 11), ((250, 410), 9)]
BOIS_FLOTTE = ((236, 512), (312, 530), 8)           # tronc échoué : extrémités et épaisseur
MARES = [((340, 442), (26, 12)), ((476, 512), (22, 10))]
HERBES = [(100, 470), (214, 462), (150, 500), (560, 470), (668, 474), (620, 500), (330, 400), (452, 404)]
CHEMIN = [(364, 576), (404, 576), (396, 470), (372, 470)]       # sable passant, du sud vers le centre
ENTREE = (376, 552)                                  # marqueur d'entrée (sud), 16 x 16
