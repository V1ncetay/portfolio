"""Monde du mode « Classique CPC 1985 » : 40 salles reliées par des portes.

Les RÈGLES viennent de l'analyse binaire de la disquette originale (docs/ANALYSE_DSK.md) :
grille de 40 x 18 cellules de 4 x 8 px, bords d'écran = murs, portes gauches / droites
(2 de chaque côté au plus) franchies en poussant contre elles au même Y, verrous non
consommés (blason / fleur de lys, un seul sens), barrières (porte de cage verticale, trappe
horizontale) ouvertes par un objet consommé, 9 chaudrons dont 2 nocifs tirés au sort selon
le départ, 5 départs, 8 captifs, sanctuaire en cul-de-sac.

La CARTE est originale : noms, disposition des salles, graphe des portes, placement des
objets, des ennemis et des barrières ont été conçus pour cette recréation (aucun plan, tuile
ou table du jeu d'origine n'est repris ni lu).

Coordonnées en cellules : x 0..39, y 0..17 ; pour les éléments de 3 x 3 cellules (sorcier,
portes, barrières, objets, ennemis, captifs, chaudrons), (x, y) = coin haut-gauche.
Un élément posé sur un sol situé à la rangée r a donc y = r - 3 (sol par défaut : rangée 17).
"""
from config import CL_COLS, CL_ROWS, CL_CELL_W, CL_CELL_H

EMPTY, SOLID, WATER, FIRE, DECO = 0, 1, 2, 3, 4
BLOCKING = (SOLID, WATER)               # l'eau est « solide » : s'y poser = noyade (&0FD1)

# --------------------------------------------------------------------------- objets
# 17 types d'objets (rôles prouvés par le binaire, §9) ; noms et dessins originaux.
ITEMS = {
    "couronne":  dict(name="COURONNE SERTIE", art="UNE COURONNE SERTIE"),
    "fiole":     dict(name="GRANDE FIOLE", art="UNE GRANDE FIOLE"),
    "cle":       dict(name="CLE", art="UNE CLE"),
    "lys":       dict(name="FLEUR DE LYS", art="UNE FLEUR DE LYS"),
    "hache":     dict(name="HACHE", art="UNE HACHE"),
    "boulet":    dict(name="BOULET", art="UN BOULET"),
    "etoile":    dict(name="ETOILE FILANTE", art="UNE ETOILE FILANTE"),
    "parchemin": dict(name="PARCHEMIN", art="UN PARCHEMIN"),
    "calice":    dict(name="CALICE D'OR", art="UN CALICE D'OR"),
    "lyre":      dict(name="LYRE", art="UNE LYRE"),
    "blason":    dict(name="BLASON", art="UN BLASON"),
    "vin":       dict(name="COUPE DE VIN", art="UNE COUPE DE VIN"),
    "epee":      dict(name="EPEE", art="UNE EPEE"),
    "grimoire":  dict(name="GRIMOIRE", art="UN GRIMOIRE"),
    "baguette":  dict(name="BAGUETTE", art="UNE BAGUETTE"),
    "sac":       dict(name="SAC DE SORTS", art="UN SAC DE SORTS"),
    "lune":      dict(name="LUNE DU SORCIER", art="UNE LUNE DU SORCIER"),
}
LOCK_ITEM = {1: "blason", 2: "lys"}                   # verrous de porte (&1BAF, &1BB7)
WEAPON = {1: "boulet", 2: "epee", 3: "hache"}         # arme dédiée par type d'ennemi (&18B9)
SPELLS = {                                            # sorts : objet consommé (&1842)
    "etoile": [(-4, -2), (-4, 0), (-4, 2), (0, -2), (0, 2), (4, -2), (4, 0), (4, 2)],
    "sac": [(-4, 0), (4, 0), (0, -2), (0, 2)],
}                                                     # (dY, dX) par trame

# --------------------------------------------------------------------------- ennemis
# T1 poursuivant volant, T2 marcheur horizontal, T3 spectre traversant les murs (§10.1).
ENEMY_NAMES = {1: "POURSUIVANT", 2: "MARCHEUR", 3: "SPECTRE"}

ZONES = {
    "village":    "LE VILLAGE",
    "foret":      "LA FORET",
    "riviere":    "LA RIVIERE",
    "souterrain": "LES SOUTERRAINS",
    "palais":     "LE PALAIS",
    "chateau":    "LE CHATEAU",
    "cachot":     "LES CACHOTS",
    "landes":     "LES LANDES",
    "pierres":    "LES PIERRES LEVEES",
    "sanctuaire": "LE SANCTUAIRE",
}

LF, RF = (0, 14), (37, 14)          # portes au ras du sol, à gauche / à droite


def R(place, zone, doors, plat=(), water=(), fire=(), deco=(), items=(), enemies=(),
      cauldron=None, barriers=(), captive=None, goal=None, floor=True):
    return dict(place=place, zone=zone, doors=dict(doors), plat=list(plat), water=list(water),
                fire=list(fire), deco=list(deco), items=list(items), enemies=list(enemies),
                cauldron=cauldron, barriers=list(barriers), captive=captive, goal=goal, floor=floor)


# plat : (x, y, largeur[, hauteur]) ; water : (x0, x1) sur la rangée du sol ;
# fire / deco : (x, y, largeur) ; barriers : (sens V|H, x, y, objet requis).
ROOMS = {
    # ------------------------------------------------------------------ le village
    0: R("SUR LA PLACE DU VILLAGE", "village", dict(L1=LF, R1=RF),
         plat=[(8, 11, 6), (24, 9, 7), (15, 5, 6)], deco=[(2, 16, 4), (31, 16, 3)],
         items=[("cle", 25, 6), ("boulet", 10, 8)], enemies=[(1, 31, 2)]),
    1: R("PRES DU PUITS DU VILLAGE", "village", dict(L1=LF, R1=RF, R2=(37, 5)),
         plat=[(28, 8, 12), (18, 12, 5), (5, 8, 6)], cauldron=(12, 14), deco=[(24, 16, 3)],
         items=[("fiole", 6, 5), ("epee", 19, 9)], enemies=[(2, 25, 14)]),
    2: R("A LA PORTE DU VILLAGE", "village", dict(L1=LF, R1=RF, R2=(37, 4)),
         plat=[(30, 7, 10), (12, 10, 8), (21, 4, 6)], deco=[(6, 16, 3), (26, 16, 2)],
         items=[("etoile", 14, 7), ("fiole", 22, 1)], enemies=[(1, 8, 3)]),
    3: R("SUR LE CHEMIN DES LANDES", "village", dict(L1=LF, L2=(0, 5), R1=RF),
         plat=[(0, 8, 9), (14, 11, 6), (26, 7, 5)], deco=[(22, 16, 4)],
         items=[("cle", 27, 4), ("boulet", 15, 8)], enemies=[(3, 30, 9)]),
    # ------------------------------------------------------------------ la forêt
    4: R("A L'OREE DE LA FORET", "foret", dict(L1=LF, R1=RF, R2=(37, 4)),
         plat=[(30, 7, 10), (8, 12, 6), (16, 8, 6)], deco=[(22, 16, 5)],
         items=[("hache", 9, 9), ("fiole", 17, 5)], enemies=[(2, 22, 14)]),
    5: R("DANS LA CLAIRIERE", "foret", dict(L1=LF, R1=RF),
         plat=[(6, 9, 7), (27, 11, 6)], cauldron=(18, 14), deco=[(8, 16, 4)],
         items=[("blason", 7, 6), ("boulet", 28, 8)], enemies=[(1, 30, 2)]),
    6: R("SOUS LES GRANDS CHENES", "foret", dict(L1=LF, R1=RF, R2=(37, 3)),
         plat=[(31, 6, 9), (0, 7, 4, 3), (7, 7, 5, 3), (12, 0, 1, 10), (18, 12, 6), (26, 9, 2, 8)],
         barriers=[("H", 4, 7, "cle")], deco=[(14, 16, 3)],
         items=[("cle", 19, 9), ("sac", 1, 4)], enemies=[(2, 9, 14), (3, 20, 2)]),
    7: R("DANS LE BOSQUET", "foret", dict(L1=LF),
         plat=[(10, 10, 7), (20, 6, 6), (33, 13, 7)], barriers=[("V", 33, 14, "grimoire")],
         captive=(36, 14), deco=[(5, 16, 4)],
         items=[("epee", 12, 7), ("fiole", 22, 3)], enemies=[(1, 24, 9), (2, 18, 14)]),
    8: R("SUR LE SENTIER DES RONCES", "foret", dict(L2=(0, 4), R1=RF),
         plat=[(0, 7, 9), (14, 10, 5)], fire=[(12, 16, 16)],
         items=[("lys", 15, 7), ("etoile", 31, 14)], enemies=[(3, 25, 3)]),
    9: R("PRES DE LA HUTTE DE L'ERMITE", "foret", dict(L1=LF, L2=(0, 4), R1=RF),
         plat=[(0, 7, 8), (14, 9, 10), (4, 12, 5)], deco=[(26, 16, 4)],
         items=[("boulet", 16, 6), ("cle", 5, 9)], enemies=[(2, 28, 14)]),
    # ------------------------------------------------------------------ la rivière
    16: R("AU GUE DE LA RIVIERE", "riviere", dict(L1=LF, R1=RF, R2=(37, 5)),
          plat=[(31, 8, 9), (14, 10, 4), (19, 16, 3)], water=[(12, 28)], cauldron=(6, 14),
          items=[("cle", 19, 13), ("hache", 15, 7)], enemies=[(1, 22, 3)]),
    17: R("AU PIED DE LA CASCADE", "riviere", dict(L1=LF, L2=(0, 4), R1=RF),
          plat=[(0, 7, 10), (26, 0, 3, 14)], water=[(10, 22)], deco=[(15, r, 2) for r in range(0, 17)],
          barriers=[("V", 26, 14, "fiole")],
          items=[("fiole", 4, 14), ("boulet", 32, 14)], enemies=[(3, 18, 3)]),
    18: R("PRES DU VIEUX MOULIN", "riviere", dict(L1=LF, R1=RF),
          plat=[(20, 9, 14), (26, 5, 8), (32, 6, 2, 3), (10, 12, 4)], water=[(8, 16)],
          barriers=[("V", 26, 6, "vin")], captive=(29, 6),
          items=[("cle", 11, 9), ("boulet", 22, 14)], enemies=[(2, 20, 14)]),
    19: R("SUR LE PONT DE PIERRE", "riviere", dict(L1=LF, R1=RF),
          plat=[(6, 12, 28)], water=[(5, 34)],
          items=[("grimoire", 18, 9), ("etoile", 28, 9)], enemies=[(1, 20, 3), (3, 8, 2)]),
    # ------------------------------------------------------------------ les souterrains
    20: R("A L'ENTREE DES SOUTERRAINS", "souterrain", dict(L1=LF, L2=(0, 4), R1=RF),
          plat=[(0, 7, 18, 3), (21, 7, 19, 3)], barriers=[("H", 18, 7, "cle")],
          items=[("fiole", 10, 14), ("epee", 30, 4)], enemies=[(2, 26, 14)]),
    21: R("DANS LA GALERIE HUMIDE", "souterrain", dict(L1=LF, R1=RF),
          plat=[(10, 11, 8), (20, 6, 6)], cauldron=(30, 14), deco=[(4, 0, 3), (24, 0, 2)],
          items=[("cle", 12, 8), ("hache", 22, 3)], enemies=[(1, 15, 2)]),
    22: R("AU CARREFOUR DES GALERIES", "souterrain", dict(L1=LF, L2=(0, 4), R1=RF, R2=(37, 4)),
          plat=[(0, 7, 9), (31, 7, 9), (15, 11, 10)],
          items=[("fiole", 17, 8), ("boulet", 5, 14)], enemies=[(3, 20, 2), (2, 26, 14)]),
    23: R("AU BORD DE LA FOSSE ARDENTE", "souterrain", dict(L1=LF),
          plat=[(12, 10, 6), (32, 13, 8)], fire=[(10, 16, 11)],
          barriers=[("V", 32, 14, "baguette")], captive=(35, 14),
          items=[("blason", 13, 7), ("boulet", 24, 14)], enemies=[(1, 26, 4)]),
    24: R("DANS LE BOYAU", "souterrain", dict(L1=LF, R1=RF),
          plat=[(0, 0, 40, 2), (20, 2, 3, 12)], barriers=[("V", 20, 14, "cle")],
          items=[("lyre", 8, 14), ("fiole", 28, 14)], enemies=[(2, 12, 14), (3, 30, 5)]),
    25: R("A LA SORTIE DES SOUTERRAINS", "souterrain", dict(L1=LF, R1=RF, R2=(37, 4)),
          plat=[(31, 7, 9), (12, 10, 6), (22, 13, 5)],
          items=[("cle", 13, 7), ("sac", 23, 10)], enemies=[(1, 18, 3)]),
    # ------------------------------------------------------------------ le palais
    26: R("DANS LE VESTIBULE DU PALAIS", "palais", dict(L1=LF, R1=RF),
          plat=[(10, 9, 5), (25, 9, 5)], cauldron=(18, 14), deco=[(6, 13, 1), (33, 13, 1)],
          items=[("fiole", 11, 6), ("epee", 26, 6)], enemies=[(2, 28, 14)]),
    27: R("DANS LA GALERIE DES GLACES", "palais", dict(L1=LF, R1=RF, R2=(37, 3)),
          plat=[(0, 6, 20, 3), (23, 6, 17, 3)], barriers=[("H", 20, 6, "fiole")],
          items=[("baguette", 8, 14), ("hache", 30, 14)], enemies=[(3, 12, 10), (1, 26, 10)]),
    28: R("DANS LA SALLE DU TRONE", "palais", dict(L1=LF),
          plat=[(24, 14, 16, 3), (32, 10, 8), (10, 9, 6)], barriers=[("V", 32, 11, "couronne")],
          captive=(35, 11), deco=[(20, 13, 1)],
          items=[("boulet", 11, 6), ("etoile", 17, 14)], enemies=[(2, 14, 14), (3, 26, 2)]),
    29: R("SUR LE BALCON DU PALAIS", "palais", dict(L1=LF, R1=RF),
          plat=[(10, 11, 20)],
          items=[("vin", 14, 8), ("cle", 24, 8)], enemies=[(1, 30, 3)]),
    # ------------------------------------------------------------------ le château
    10: R("DANS LA COUR DU CHATEAU", "chateau", dict(L2=(0, 4), R1=RF),
          plat=[(0, 7, 9), (16, 0, 3, 14)], barriers=[("V", 16, 14, "fiole")], deco=[(8, 11, 1), (28, 11, 1)],
          items=[("fiole", 6, 14), ("boulet", 25, 14)], enemies=[(2, 30, 14)]),
    11: R("DANS LA SALLE DES GARDES", "chateau", dict(L1=LF, R1=RF),
          plat=[(12, 10, 6), (28, 7, 6)], cauldron=(22, 14), deco=[(8, 11, 1), (36, 9, 1)],
          items=[("calice", 29, 4), ("epee", 13, 7)], enemies=[(2, 16, 14), (1, 34, 3)]),
    12: R("DANS L'ARMURERIE", "chateau", dict(L1=LF, R1=RF, R2=(37, 4)),
          plat=[(25, 7, 15), (28, 0, 3, 4)], barriers=[("V", 28, 4, "cle")], deco=[(10, 11, 1)],
          items=[("hache", 10, 14), ("lys", 20, 14)], enemies=[(3, 18, 3)]),
    13: R("DANS LA CHAPELLE DU CHATEAU", "chateau", dict(L1=LF, R1=RF),
          plat=[(14, 8, 12), (17, 4, 9), (23, 5, 3, 3)], barriers=[("V", 17, 5, "lyre")],
          captive=(20, 5), deco=[(7, 11, 1), (32, 11, 1)],
          items=[("etoile", 6, 14), ("fiole", 30, 14)], enemies=[(1, 8, 3), (2, 26, 14)]),
    14: R("AU SOMMET DU DONJON", "chateau", dict(L1=LF, L2=(0, 4), R1=RF),
          plat=[(0, 7, 9), (14, 11, 8), (24, 6, 6)], deco=[(30, 13, 1)],
          items=[("cle", 16, 8), ("sac", 25, 3)], enemies=[(2, 23, 14)]),
    15: R("SUR LE CHEMIN DE RONDE", "chateau", dict(L1=LF, R1=RF),
          plat=[(0, 0, 40, 1), (6, 1, 2, 2), (16, 1, 2, 2), (26, 1, 2, 2)],
          items=[("parchemin", 20, 14), ("epee", 8, 14)], enemies=[(3, 25, 4), (1, 12, 4)]),
    # ------------------------------------------------------------------ les cachots
    30: R("DANS LES OUBLIETTES", "cachot", dict(L2=(0, 4), R1=RF),
          plat=[(0, 7, 12), (9, 0, 3, 4)], barriers=[("V", 9, 4, "cle")], cauldron=(20, 14),
          items=[("cle", 26, 14), ("boulet", 31, 14)], enemies=[(2, 14, 14)]),
    31: R("DANS LA SALLE DES SUPPLICES", "cachot", dict(L1=LF, R1=RF),
          plat=[(16, 11, 6)], fire=[(14, 16, 11)], deco=[(8, 0, 1), (30, 0, 1)],
          items=[("fiole", 17, 8), ("epee", 29, 14)], enemies=[(1, 20, 3), (3, 31, 3)]),
    32: R("DANS LA SALLE FORTE", "cachot", dict(L1=LF, R1=RF),
          plat=[(15, 9, 10), (18, 5, 7), (24, 6, 1, 3)], barriers=[("V", 18, 6, "parchemin")],
          captive=(21, 6),
          items=[("couronne", 6, 14), ("hache", 30, 14)], enemies=[(2, 25, 14), (3, 10, 2)]),
    33: R("DANS LE CACHOT NOIR", "cachot", dict(L1=LF, R1=RF),
          plat=[(14, 11, 4, 3), (21, 11, 5, 3), (14, 14, 1, 3), (25, 14, 1, 3)],
          barriers=[("H", 18, 11, "fiole")],
          items=[("lune", 20, 14), ("etoile", 5, 14)], enemies=[(1, 30, 4)]),
    # ------------------------------------------------------------------ les landes
    34: R("AU MILIEU DE LA LANDE", "landes", dict(L1=LF, R1=RF),
          plat=[(6, 10, 6), (28, 10, 6)], cauldron=(20, 14), deco=[(12, 16, 4)],
          items=[("cle", 7, 7), ("epee", 29, 7)], enemies=[(1, 12, 3)]),
    35: R("SUR LE TERTRE", "landes", dict(L1=LF, R1=RF),
          plat=[(14, 12, 12, 5), (18, 8, 6), (24, 8, 2, 4)], water=[(27, 32)],
          barriers=[("V", 18, 9, "calice")], captive=(21, 9),
          items=[("fiole", 6, 14), ("hache", 9, 14)], enemies=[(3, 30, 2)]),
    36: R("DANS LES MARAIS", "landes", dict(L1=LF, R1=RF),
          plat=[(14, 16, 12), (20, 0, 3, 13), (29, 15, 4, 2)], water=[(4, 35)],
          barriers=[("V", 20, 13, "cle")],
          items=[("sac", 15, 13), ("hache", 29, 12)], enemies=[(1, 10, 4)]),
    # ------------------------------------------------------------------ les pierres levées
    37: R("PRES DES PIERRES LEVEES", "pierres", dict(L1=LF, R1=RF),
          plat=[(14, 10, 2, 7), (22, 10, 2, 7), (14, 9, 10)], cauldron=(28, 14),
          items=[("etoile", 6, 14), ("fiole", 17, 6)], enemies=[(3, 32, 3)]),
    38: R("AU COEUR DU CERCLE DE PIERRES", "pierres", dict(R1=RF),
          plat=[(0, 13, 8), (11, 10, 20), (11, 11, 2, 6), (19, 11, 2, 6), (28, 11, 2, 6)],
          barriers=[("V", 5, 14, "lune")], captive=(2, 14),
          items=[("boulet", 14, 7), ("cle", 24, 7)], enemies=[(3, 34, 4), (1, 22, 2)]),
    # ------------------------------------------------------------------ le sanctuaire
    39: R("DANS LE SANCTUAIRE", "sanctuaire", dict(L1=LF),
          plat=[(24, 14, 6, 3), (8, 9, 4), (32, 9, 4)], goal=(25, 11), deco=[(6, 13, 1), (37, 13, 1)]),
}

# --------------------------------------------------------------------------- portes
# (salle A, porte A, salle B, porte B, verrou) ; verrou = (1|2) appliqué au sens A -> B
# seulement (le retour B -> A est libre, comme dans l'original). Toutes les liaisons sont
# réciproques. Une porte gauche (L) se franchit en poussant vers la gauche, une droite (R)
# vers la droite ; on arrive à côté de la porte de destination.
LINKS = [
    (0, "R1", 1, "L1", None), (1, "R1", 2, "L1", None), (3, "R1", 0, "L1", 1),
    (2, "R2", 39, "L1", None), (3, "L1", 34, "R1", None), (34, "L1", 35, "R1", None),
    (35, "L1", 36, "R1", None), (36, "L1", 37, "R1", None), (37, "L1", 38, "R1", None),
    (2, "R1", 4, "L1", None), (4, "R1", 5, "L1", None), (5, "R1", 6, "L1", None),
    (6, "R1", 7, "L1", None), (4, "R2", 8, "L2", 2), (8, "R1", 9, "L1", None),
    (6, "R2", 9, "L2", 2), (9, "R1", 16, "L1", None), (3, "L2", 16, "R2", None),
    (17, "L1", 16, "R1", 1), (17, "R1", 18, "L1", None), (18, "R1", 19, "L1", None),
    (19, "R1", 20, "L1", None), (17, "L2", 22, "L2", None), (20, "R1", 21, "L1", None),
    (21, "R1", 22, "L1", None), (22, "R1", 23, "L1", None), (22, "R2", 24, "L1", None),
    (24, "R1", 25, "L1", None), (25, "R1", 26, "L1", 2), (25, "R2", 30, "L2", None),
    (20, "L2", 12, "R2", None), (26, "R1", 27, "L1", None), (27, "R1", 28, "L1", None),
    (27, "R2", 29, "L1", None), (29, "R1", 14, "L2", None), (1, "R2", 10, "L2", 1),
    (10, "R1", 11, "L1", None), (11, "R1", 12, "L1", None), (12, "R1", 13, "L1", None),
    (13, "R1", 14, "L1", None), (14, "R1", 15, "L1", 2), (15, "R1", 33, "R1", None),
    (30, "R1", 31, "L1", None), (32, "L1", 31, "R1", 1), (32, "R1", 33, "L1", None),
]


def _door_table():
    """(salle, porte) -> (salle de destination, porte d'arrivée, verrou du sens aller)."""
    out = {}
    for a, sa, b, sb, lock in LINKS:
        out[(a, sa)] = (b, sb, lock)
        out[(b, sb)] = (a, sa, None)
    return out


DOOR_TO = _door_table()

# Départs (salle, x, y en cellules) et chaudrons rendus nocifs selon le départ tiré (§8.5).
STARTS = [(0, 19, 2), (9, 30, 3), (14, 18, 2), (20, 14, 12), (34, 20, 2)]
POISON = [(21, 30), (11, 26), (5, 34), (16, 37), (1, 21)]
SANCTUARY = 39
CAULDRON_ROOMS = sorted(r for r, d in ROOMS.items() if d["cauldron"])
CAPTIVE_ROOMS = sorted(r for r, d in ROOMS.items() if d["captive"])
CAPTIVE_NAMES = ["ALDRIC", "BERTRAND", "CYPRIEN", "DAMIEN", "EUDES", "FULBERT", "GODEFROY", "HUGUES"]


def barrier_list():
    """Toutes les barrières : liste de (id, salle, sens, x, y, objet)."""
    out = []
    for rid in sorted(ROOMS):
        for i, (kind, x, y, item) in enumerate(ROOMS[rid]["barriers"]):
            out.append(("%d.%d" % (rid, i), rid, kind, x, y, item))
    return out


BARRIERS = barrier_list()
BARRIER_BY_ID = {b[0]: b for b in BARRIERS}


def cage_barrier(rid):
    """La barrière qui ferme la cage du captif de la salle (la plus proche de lui)."""
    cx, cy = ROOMS[rid]["captive"]
    best = None
    for b in BARRIERS:
        if b[1] != rid:
            continue
        d = abs(b[3] - cx) + abs(b[4] - cy)
        if best is None or d < best[0]:
            best = (d, b)
    return best[1] if best else None


def item_instances():
    """Objets posés au départ : liste de (salle, type, x, y), 2 au plus par salle."""
    out = []
    for rid in sorted(ROOMS):
        for kind, x, y in ROOMS[rid]["items"]:
            out.append((rid, kind, x, y))
    return out


# --------------------------------------------------------------------------- tuiles
def build_tiles(rid):
    """Grille statique 40 x 18 (EMPTY / SOLID / WATER / FIRE / DECO)."""
    room = ROOMS[rid]
    t = [[EMPTY] * CL_COLS for _ in range(CL_ROWS)]
    if room["floor"]:
        for x in range(CL_COLS):
            t[CL_ROWS - 1][x] = SOLID
    for x0, x1 in room["water"]:
        for x in range(x0, x1 + 1):
            t[CL_ROWS - 1][x] = WATER
    for x, y, w in room["deco"]:
        for xx in range(x, x + w):
            t[y][xx] = DECO
    for x, y, w in room["fire"]:
        for xx in range(x, x + w):
            t[y][xx] = FIRE
    for p in room["plat"]:
        x, y, w = p[:3]
        h = p[3] if len(p) > 3 else 1
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if 0 <= xx < CL_COLS and 0 <= yy < CL_ROWS:
                    t[yy][xx] = SOLID
    return t


def solid_blocks(rid, open_barriers=()):
    """Blocs 3x3 dynamiques solides : portes, barrières fermées, chaudron (2 rangées basses)."""
    room = ROOMS[rid]
    cells = set()
    for x, y in room["doors"].values():
        cells |= {(x + i, y + j) for i in range(3) for j in range(3)}
    for bid, brid, kind, x, y, item in BARRIERS:
        if brid == rid and bid not in open_barriers:
            cells |= {(x + i, y + j) for i in range(3) for j in range(3)}
    if room["cauldron"]:
        x, y = room["cauldron"]
        cells |= {(x + i, y + j) for i in range(3) for j in (1, 2)}
    return cells


def collision_grid(rid, open_barriers=()):
    """Grille de collision : tuiles statiques + blocs dynamiques (marqués SOLID)."""
    t = build_tiles(rid)
    for x, y in solid_blocks(rid, open_barriers):
        if 0 <= x < CL_COLS and 0 <= y < CL_ROWS:
            t[y][x] = SOLID
    return t


def door_px(rid, slot):
    x, y = ROOMS[rid]["doors"][slot]
    return x * CL_CELL_W, y * CL_CELL_H


def arrival_cell(rid, slot):
    """Position (cellules) du sorcier qui arrive par cette porte : collé à elle, même Y."""
    x, y = ROOMS[rid]["doors"][slot]
    return (x + 3, y) if slot[0] == "L" else (x - 3, y)
