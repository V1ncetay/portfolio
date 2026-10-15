"""Données du monde (tables déclaratives) : zones, salles, objets, portes, captifs, ennemis.

Coordonnées des salles en tuiles 8x8 : x 0..19, y 0..18 (ligne 18 = sol, ligne 0 = plafond).
Les bords sont des murs, percés automatiquement aux sorties :
  - sorties E/O : lignes EW_ROWS ; sorties N/S : colonnes NS_COLS.
Plateformes : (x, y, largeur, hauteur[, type]) ; type FAKE = faux mur (passage secret).
Ennemis : (type, x, y[, paramètre]) ; objets/captifs/chaudrons : position en tuiles.

Deux chapitres (Sorcery+) : chaque zone porte son chapitre (1 par défaut). Les deux graphes
de salles sont disjoints ; on passe de l'un à l'autre par le vortex (`gate`) de N0.
Le Chapitre 2 est décrit dans la seconde moitié du fichier.
"""
from config import COLS, ROWS, TILE

EMPTY, SOLID, FAKE, WATER = 0, 1, 2, 3

EW_ROWS = tuple(range(12, 18))
NS_COLS = tuple(range(8, 12))
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
DELTA = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}

# --------------------------------------------------------------------------- zones
ZONES = {
    "landes":     dict(name="LES LANDES", theme="landes"),
    "bois":       dict(name="LES BOIS", theme="bois"),
    "riviere":    dict(name="LA RIVIERE", theme="riviere"),
    "chateau":    dict(name="LE CHATEAU", theme="chateau"),
    "catacombes": dict(name="LES CATACOMBES", theme="catacombes"),
    "palais":     dict(name="LE PALAIS", theme="palais"),
    "stonehenge": dict(name="STONEHENGE", theme="stonehenge"),
    "antre":      dict(name="L'ANTRE", theme="antre"),
    # Chapitre 2 : le monde du Nécromancien
    "foret":      dict(name="LA FORET MAUDITE", theme="foret", chapter=2),
    "chapelle":   dict(name="LA CHAPELLE EN RUINE", theme="chapelle", chapter=2),
    "abime":      dict(name="L'ABIME DE FEU", theme="lave", chapter=2),
    "citadelle":  dict(name="LA CITADELLE", theme="citadelle", chapter=2),
    "sanctuaire": dict(name="LE SANCTUAIRE", theme="antre", chapter=2),
}

# --------------------------------------------------------------------------- ennemis
# move : sine (crâne), chase (fantôme), erratic (chauve-souris), yoyo (araignée),
#        jump (poisson), patrol (garde). drain = énergie perdue par tick de contact.
ENEMY_TYPES = {
    "skull":  dict(name="CRANE", w=7, h=8, move="sine", speed=0.6, drain=0.30, killed_by=("epee",)),
    "ghost":  dict(name="FANTOME", w=8, h=10, move="chase", speed=0.28, drain=0.35, killed_by=("croix",)),
    "bat":    dict(name="CHAUVE-SOURIS", w=8, h=6, move="erratic", speed=0.9, drain=0.25,
                   killed_by=("torche", "cierge")),
    "spider": dict(name="ARAIGNEE", w=8, h=7, move="yoyo", speed=0.5, drain=0.30, killed_by=("hache",)),
    "fish":   dict(name="POISSON", w=8, h=6, move="jump", speed=3.0, drain=0.40, killed_by=()),
    "guard":  dict(name="GARDE", w=7, h=15, move="patrol", speed=0.45, drain=0.35, killed_by=("epee",)),
    # Chapitre 2. stalk : marche au sol vers le joueur ; orbit : tourne autour de son point
    # d'apparition (paramètre = rayon en tuiles) ; swoop : perché, plonge sur le joueur.
    "goule":      dict(name="GOULE", w=7, h=14, move="stalk", speed=0.35, drain=0.35, killed_by=("faux",)),
    "wisp":       dict(name="FEU FOLLET", w=6, h=7, move="orbit", speed=0.035, drain=0.30,
                       killed_by=("eau_benite",)),
    "gargouille": dict(name="GARGOUILLE", w=8, h=8, move="swoop", speed=1.3, drain=0.40, killed_by=("marteau",)),
    "bulle":      dict(name="BULLE DE LAVE", w=6, h=6, move="jump", speed=3.2, drain=0.60, killed_by=()),
}

# --------------------------------------------------------------------------- objets
# kind : arme / cle / indice / captif (objet de libération) / relique / potion
OBJECTS = {
    "epee":      dict(name="EPEE", kind="arme", room="L4", at=(16, 17)),
    "hache":     dict(name="HACHE", kind="arme", room="B4", at=(4, 17)),
    "croix":     dict(name="CROIX", kind="arme", room="K4", at=(15, 5)),
    "torche":    dict(name="TORCHE", kind="arme", room="K3", at=(4, 17)),
    "cle":       dict(name="CLE", kind="cle", room="C3", at=(10, 6)),
    "cle_doree": dict(name="CLE DOREE", kind="cle", room="P3", at=(3, 8)),
    "parchemin": dict(name="PARCHEMIN", kind="indice", room="S4", at=(17, 17),
                      text="LE SCEPTRE, CACHE AU FOND DES BOIS, OUVRE LE VORTEX"),
    "amulette":  dict(name="AMULETTE", kind="captif", room="L1", at=(15, 9)),
    "harpe":     dict(name="HARPE", kind="captif", room="B6", at=(9, 6)),
    "bouclier":  dict(name="BOUCLIER", kind="captif", room="R3", at=(14, 9)),
    "anneau":    dict(name="ANNEAU", kind="captif", room="C6", at=(16, 4)),
    "lanterne":  dict(name="LANTERNE", kind="captif", room="C4", at=(3, 17)),
    "couronne":  dict(name="COURONNE", kind="captif", room="K2", at=(15, 4)),
    "livre":     dict(name="LIVRE", kind="captif", room="P1", at=(15, 17)),
    "coupe":     dict(name="COUPE", kind="captif", room="S1", at=(3, 17)),
    "sceptre":   dict(name="SCEPTRE", kind="relique", room="B1", at=(3, 17)),
    "orbe":      dict(name="ORBE", kind="relique", room="S2", at=(10, 11)),
    "talisman":  dict(name="TALISMAN", kind="relique", room="L6", at=(16, 8)),
    "potion_1":  dict(name="COEUR", kind="potion", room="B2", at=(4, 7), energy=40),
    "potion_2":  dict(name="COEUR", kind="potion", room="R4", at=(2, 15), energy=40),
    "potion_3":  dict(name="COEUR", kind="potion", room="K1", at=(16, 17), energy=40),
    "potion_4":  dict(name="COEUR", kind="potion", room="P4", at=(16, 17), energy=40),
}
FINAL_WEAPON = "sceptre"           # la seule des trois reliques qui ouvre le vortex (fin du Ch.1)
BOSS_HITS = 3                      # Sorcery+ : 3 exemplaires de l'arme requis (Ch.2)
BOSS_WEAPON_KIND = "pentacle"      # chaque coup consomme un pentacle
LIGHT_ITEMS = ("torche", "cierge")  # éclairent les salles obscures

# --------------------------------------------------------------------------- portes
# Une porte bouche la sortie `dir` de `room` (et la sortie opposée de la salle voisine).
# key = objet qui l'ouvre au contact ; need_freed = nombre de sorciers à libérer.
DOORS = {
    "porte_bois":  dict(name="PORTE DE BOIS", room="L3", dir="E", key="hache", style="bois"),
    "barriere":    dict(name="BARRIERE RUNIQUE", room="L2", dir="N", key="torche", style="rune"),
    "trappe":      dict(name="TRAPPE", room="C5", dir="S", key="cle", style="trappe"),
    "herse":       dict(name="HERSE", room="R4", dir="E", key="cle", style="herse"),
    "porte_doree": dict(name="PORTE DOREE", room="P4", dir="N", key="cle_doree", style="or"),
    "portail":     dict(name="PORTAIL MAUDIT", room="S1", dir="N", key=None, need_freed=8, style="portail"),
}

# --------------------------------------------------------------------------- captifs
# Cage de 2x3 tuiles posée en (x, y) (coin haut-gauche), sur une tuile solide.
CAPTIVES = {
    "aldric":   dict(name="ALDRIC", room="B5", at=(14, 15), item="amulette"),
    "berenice": dict(name="BERENICE", room="R2", at=(8, 11), item="harpe"),
    "cedric":   dict(name="CEDRIC", room="C2", at=(14, 15), item="bouclier"),
    "dorian":   dict(name="DORIAN", room="C7", at=(14, 15), item="anneau"),
    "elwyn":    dict(name="ELWYN", room="K5", at=(4, 15), item="lanterne"),
    "fergus":   dict(name="FERGUS", room="P2", at=(9, 9), item="couronne"),
    "gwen":     dict(name="GWEN", room="S3", at=(9, 15), item="livre"),
    "hector":   dict(name="HECTOR", room="L5", at=(9, 15), item="coupe"),
}

START = dict(room="L2", at=(6, 14))
START2 = dict(room="F1", at=(5, 14))

# --------------------------------------------------------------------------- salles
# cauldrons : (x, y, "plein"|"maudit") ; chaudron de 2x2 tuiles.
# lava : comme l'eau (2 rangées du bas) mais rendue en lave et plus douloureuse ; dans ces
# salles, la sortie S éventuelle reste un gouffre ouvert. gate : vortex vers un autre chapitre.
def R(name, zone, grid, exits, plat=(), enemies=(), cauldrons=(), decor=(), dark=False,
      water=False, boss=None, lava=False, gate=None):
    return dict(name=name, zone=zone, grid=grid, exits=exits, plat=list(plat),
                enemies=list(enemies), cauldrons=list(cauldrons), decor=list(decor),
                dark=dark, water=water or lava, lava=lava, boss=boss, gate=gate)


ROOMS = {
    # ---------------------------------------------------------------- Les Bois
    "B1": R("CLAIRIERE SECRETE", "bois", (0, 3), dict(E="B2", S="B4"),
            plat=[(1, 9, 6, 1), (6, 10, 1, 8, FAKE), (9, 6, 5, 1), (14, 11, 4, 1)],
            enemies=[("spider", 16, 1, 8), ("bat", 11, 4)]),
    "B2": R("BOIS SOMBRE", "bois", (1, 3), dict(W="B1", E="B3", S="B5"),
            plat=[(3, 8, 4, 1), (13, 8, 4, 1), (7, 12, 6, 1)],
            enemies=[("spider", 10, 1, 9), ("skull", 4, 4)]),
    "B3": R("OREE DU BOIS", "bois", (2, 3), dict(W="B2", E="L1"),
            plat=[(5, 10, 3, 1), (12, 7, 4, 1), (9, 14, 2, 4)],
            enemies=[("bat", 9, 5), ("spider", 15, 1, 10)]),
    "B4": R("CHENE CREUX", "bois", (0, 4), dict(N="B1", E="B5"),
            plat=[(2, 12, 4, 1), (12, 10, 5, 1), (14, 5, 3, 1)],
            enemies=[("spider", 17, 1, 7), ("skull", 9, 7)]),
    "B5": R("CERCLE DES HIBOUX", "bois", (1, 4), dict(W="B4", N="B2", E="B6"),
            plat=[(3, 9, 4, 1), (11, 6, 4, 1)],
            enemies=[("bat", 6, 4), ("spider", 17, 1, 10)]),
    "B6": R("RONCES", "bois", (2, 4), dict(W="B5", E="L4"),
            plat=[(8, 7, 4, 1), (3, 13, 3, 1), (14, 12, 3, 1)],
            enemies=[("spider", 15, 1, 7), ("skull", 5, 4)]),
    # ---------------------------------------------------------------- Les Landes
    "L1": R("LANDE VENTEUSE", "landes", (3, 3), dict(W="B3", E="L2", S="L4"),
            plat=[(3, 7, 4, 1), (14, 10, 4, 1), (5, 15, 2, 3)],
            enemies=[("skull", 8, 5)]),
    "L2": R("TOUR DU SORCIER", "landes", (4, 3), dict(W="L1", E="L3", S="L5", N="S4"),
            plat=[(13, 9, 5, 1), (1, 6, 3, 1)],
            cauldrons=[(3, 16, "plein")], decor=[("tower", 14, 2)]),
    "L3": R("CHEMIN DU CHATEAU", "landes", (5, 3), dict(W="L2", E="C1", S="L6"),
            plat=[(4, 9, 4, 1), (10, 5, 4, 1), (14, 13, 3, 1)],
            enemies=[("skull", 10, 11)]),
    "L4": R("MENHIR BRISE", "landes", (3, 4), dict(N="L1", E="L5", W="B6", S="R1"),
            plat=[(3, 6, 3, 1), (14, 9, 3, 1), (13, 13, 2, 5)],
            enemies=[("skull", 6, 10), ("bat", 12, 4)]),
    "L5": R("PUITS DES LANDES", "landes", (4, 4), dict(W="L4", E="L6", N="L2"),
            plat=[(2, 10, 4, 1), (14, 10, 4, 1), (7, 6, 6, 1)],
            enemies=[("skull", 4, 4), ("ghost", 16, 3)]),
    "L6": R("ROCHER NOIR", "landes", (5, 4), dict(W="L5", N="L3", S="R3"),
            plat=[(3, 9, 3, 1), (15, 9, 3, 1), (5, 14, 2, 4)],
            enemies=[("bat", 10, 6), ("skull", 12, 12)]),
    # ---------------------------------------------------------------- La Rivière
    "R1": R("LE GUE", "riviere", (3, 5), dict(N="L4", E="R2"), water=True,
            plat=[(1, 15, 5, 4), (9, 12, 6, 1)],
            enemies=[("fish", 12, 0), ("skull", 8, 6)]),
    "R2": R("RIVIERE GRISE", "riviere", (4, 5), dict(W="R1", E="R3"), water=True,
            plat=[(7, 14, 5, 3), (2, 9, 4, 1), (14, 9, 4, 1)],
            enemies=[("fish", 4, 0), ("fish", 15, 0), ("bat", 10, 4)]),
    "R3": R("PONT DE BOIS", "riviere", (5, 5), dict(W="R2", N="L6", E="R4"), water=True,
            plat=[(3, 13, 6, 1), (13, 10, 4, 1)],
            enemies=[("fish", 10, 0), ("skull", 9, 5)]),
    "R4": R("L'ECLUSE", "riviere", (6, 5), dict(W="R3", E="C7"), water=True,
            plat=[(1, 16, 4, 3), (15, 16, 4, 3), (8, 10, 4, 1)],
            enemies=[("fish", 10, 0), ("ghost", 14, 3)]),
    # ---------------------------------------------------------------- Le Château
    "C1": R("PORTE DU CHATEAU", "chateau", (6, 3), dict(W="L3", E="C2", N="P4", S="C4"),
            plat=[(3, 9, 4, 1), (13, 9, 4, 1)],
            cauldrons=[(15, 16, "plein")], decor=[("torch", 2, 4), ("torch", 17, 4)],
            enemies=[("skull", 10, 6)]),
    "C2": R("GRANDE SALLE", "chateau", (7, 3), dict(W="C1", E="C3", S="C5"),
            plat=[(2, 10, 5, 1), (8, 6, 4, 1)], decor=[("window", 4, 3), ("window", 15, 3)],
            enemies=[("ghost", 4, 3), ("skull", 10, 10)]),
    "C3": R("ARMURERIE", "chateau", (8, 3), dict(W="C2", E="K1", S="C6"),
            plat=[(8, 7, 5, 1), (2, 11, 3, 1)], decor=[("torch", 15, 5)],
            enemies=[("skull", 14, 11), ("bat", 4, 4)]),
    "C4": R("CELLIER", "chateau", (6, 4), dict(N="C1", E="C5"),
            plat=[(6, 12, 3, 1), (12, 8, 5, 1)], decor=[("window", 3, 4)],
            enemies=[("ghost", 15, 4), ("skull", 8, 9)]),
    "C5": R("SALLE DE LA TRAPPE", "chateau", (7, 4), dict(W="C4", N="C2", E="C6", S="C7"),
            plat=[(2, 8, 4, 1), (14, 8, 4, 1)], decor=[("torch", 9, 4)],
            enemies=[("skull", 10, 12), ("bat", 10, 4)]),
    "C6": R("TOUR EST", "chateau", (8, 4), dict(W="C5", N="C3"),
            plat=[(14, 5, 5, 1), (4, 10, 4, 1), (9, 14, 3, 1)], decor=[("window", 10, 3)],
            enemies=[("skull", 9, 9), ("ghost", 3, 3)]),
    "C7": R("OUBLIETTES", "chateau", (7, 5), dict(N="C5", W="R4"),
            plat=[(3, 7, 4, 1), (10, 11, 3, 1)], decor=[("chains", 6, 1), ("chains", 16, 1)],
            enemies=[("ghost", 15, 4), ("bat", 6, 4)]),
    # ---------------------------------------------------------------- Les Catacombes (sombres)
    "K1": R("ESCALIER DES MORTS", "catacombes", (9, 3), dict(W="C3", E="K2", S="K3"), dark=True,
            plat=[(4, 10, 3, 1), (13, 6, 4, 1)],
            enemies=[("ghost", 10, 4), ("skull", 8, 13)]),
    "K2": R("OSSUAIRE", "catacombes", (10, 3), dict(W="K1", S="K4"), dark=True,
            plat=[(14, 5, 4, 1), (4, 9, 4, 1)],
            enemies=[("ghost", 5, 3), ("bat", 12, 10)]),
    "K3": R("CRYPTE", "catacombes", (9, 4), dict(N="K1", E="K4"), dark=True,
            plat=[(6, 7, 4, 1), (13, 11, 4, 1)], cauldrons=[(13, 16, "maudit")],
            enemies=[("bat", 10, 5), ("skull", 5, 12)]),
    "K4": R("TOMBEAU DU ROI", "catacombes", (10, 4), dict(W="K3", N="K2", S="K5"), dark=True,
            plat=[(14, 6, 4, 1), (5, 12, 3, 1)], cauldrons=[(3, 16, "plein")],
            enemies=[("ghost", 8, 3), ("skull", 14, 13)]),
    "K5": R("L'ABIME", "catacombes", (10, 5), dict(N="K4"), dark=True,
            plat=[(12, 8, 4, 1), (7, 12, 3, 1)],
            enemies=[("ghost", 14, 4), ("bat", 9, 5), ("skull", 12, 14)]),
    # ---------------------------------------------------------------- Le Palais
    "P4": R("VESTIBULE DU PALAIS", "palais", (6, 2), dict(S="C1", W="P3", N="P2"),
            plat=[(3, 10, 4, 1), (13, 10, 4, 1)], decor=[("column", 2, 1), ("column", 17, 1)],
            enemies=[("guard", 14, 17), ("bat", 5, 4)]),
    "P3": R("SALLE DES GARDES", "palais", (5, 2), dict(E="P4", N="P1"),
            plat=[(2, 9, 4, 1), (13, 9, 5, 1)], decor=[("banner", 8, 2), ("banner", 15, 2)],
            enemies=[("guard", 6, 17), ("guard", 15, 8)]),
    "P1": R("GALERIE DES GLACES", "palais", (5, 1), dict(S="P3", W="S2"),
            plat=[(5, 8, 4, 1), (13, 12, 4, 1)], decor=[("column", 11, 1), ("column", 17, 1)],
            enemies=[("guard", 4, 17), ("ghost", 5, 3)]),
    "P2": R("SALLE DU TRONE", "palais", (6, 1), dict(S="P4"),
            plat=[(7, 12, 6, 1), (2, 7, 3, 1), (15, 7, 3, 1)], decor=[("banner", 5, 2), ("banner", 14, 2)],
            enemies=[("guard", 3, 17), ("guard", 16, 17)]),
    # ---------------------------------------------------------------- Stonehenge
    "S4": R("ALLEE DES PIERRES", "stonehenge", (4, 2), dict(S="L2", W="S3", N="S2"),
            plat=[(14, 12, 2, 6), (3, 7, 4, 1), (13, 5, 4, 1)],
            enemies=[("ghost", 8, 5)]),
    "S3": R("CERCLE DE PIERRES", "stonehenge", (3, 2), dict(E="S4", N="S1"),
            plat=[(3, 13, 2, 5), (15, 13, 2, 5), (4, 9, 3, 1)],
            enemies=[("bat", 5, 4), ("skull", 12, 6)]),
    "S2": R("PIERRE COUCHEE", "stonehenge", (4, 1), dict(S="S4", W="S1", E="P1"),
            plat=[(8, 12, 5, 1), (3, 14, 2, 4), (15, 14, 2, 4)],
            enemies=[("ghost", 15, 4), ("bat", 6, 6)]),
    "S1": R("AUTEL DE STONEHENGE", "stonehenge", (3, 1), dict(E="S2", S="S3", N="N0"),
            plat=[(2, 8, 4, 1), (14, 8, 4, 1)], cauldrons=[(15, 16, "plein")],
            decor=[("altar", 7, 15)],
            enemies=[("skull", 10, 6), ("ghost", 16, 3)]),
    # ---------------------------------------------------------------- Fin du Chapitre 1
    # Le vortex (4x4 tuiles) n'admet que le porteur du Sceptre : il mène au Chapitre 2.
    "N0": R("SEUIL DU VORTEX", "antre", (3, 0), dict(S="S1"),
            plat=[(2, 12, 4, 1), (14, 12, 4, 1), (7, 7, 6, 1)],
            gate=dict(at=(8, 2), size=(4, 4), key="sceptre", to=2)),
}


# ===========================================================================
# CHAPITRE 2 (Sorcery+) : le monde du Nécromancien, 28 écrans.
# Faits vérifiés : +28 écrans, décors inédits, on y collecte des cœurs, le Nécromancien
# y est vaincu avec TROIS exemplaires d'un objet dont seuls DEUX existent : le troisième
# se fabrique. Tout le reste (carte, noms, objets, recette) est une proposition [I].
# ===========================================================================
OBJECTS.update({
    # Le Sceptre se brise en franchissant le vortex : son éclat attend à l'arrivée (F1).
    "eclat":      dict(name="ECLAT DE LUNE", kind="ingredient", room="F1", at=(14, 9)),
    "faux":       dict(name="FAUX", kind="arme", room="F7", at=(11, 6)),
    "eau_benite": dict(name="EAU BENITE", kind="arme", room="A1", at=(4, 12)),
    "cierge":     dict(name="CIERGE", kind="arme", room="A2", at=(10, 10)),
    "cloche":     dict(name="CLOCHE D'ARGENT", kind="ingredient", room="A5", at=(9, 3)),
    "grimoire":   dict(name="GRIMOIRE", kind="indice", room="A6", at=(4, 8),
                       text="3 PENTACLES ! FONDEZ ARGENT ET LUNE AU CREUSET"),
    "marteau":    dict(name="MARTEAU", kind="arme", room="V2", at=(3, 11)),
    "cle_os":     dict(name="CLE D'OS", kind="cle", room="X6", at=(15, 12)),
    # Les deux seuls pentacles du monde... et le troisième, forgé au creuset (crafted).
    "pentacle_1": dict(name="PENTACLE", kind="pentacle", room="V4", at=(9, 12), sprite="pentacle"),
    "pentacle_2": dict(name="PENTACLE", kind="pentacle", room="X7", at=(15, 10), sprite="pentacle"),
    "pentacle_3": dict(name="PENTACLE", kind="pentacle", room="V5", at=(15, 17), sprite="pentacle",
                       crafted="creuset"),
})
# Les 8 cœurs sacrés : ramassés au contact (pas portés), +15 d'énergie chacun.
for _i, (_room, _at) in enumerate((("F3", (3, 5)), ("F4", (14, 7)), ("A3", (15, 10)), ("A4", (14, 6)),
                                    ("V1", (8, 7)), ("V6", (15, 7)), ("X8", (14, 8)), ("X3", (4, 6))), 1):
    OBJECTS["coeur_%d" % _i] = dict(name="COEUR SACRE", kind="coeur", room=_room, at=_at,
                                    energy=15, sprite="coeur")
HEARTS = [oid for oid, o in OBJECTS.items() if o["kind"] == "coeur"]

DOORS.update({
    "ronces":    dict(name="RONCES NOIRES", room="F2", dir="N", key="faux", style="ronces"),
    "flammes":   dict(name="MUR DE FLAMMES", room="F6", dir="S", key="eau_benite", style="flammes"),
    "fissure":   dict(name="MUR FISSURE", room="V3", dir="E", key="marteau", style="fissure"),
    "grille_os": dict(name="GRILLE D'OS", room="X5", dir="N", key="cle_os", style="os"),
    "sceau":     dict(name="SCEAU DES COEURS", room="X4", dir="N", key=None,
                      need_hearts=len(HEARTS), style="sceau"),
})

# Fabrication : on dépose chaque ingrédient (porté) en touchant la station ; quand tous y
# sont, l'objet `makes` apparaît à sa position (OBJECTS[makes]["at"]).
CRAFTS = {
    "creuset": dict(name="CREUSET", room="V5", at=(12, 16), needs=("cloche", "eclat"), makes="pentacle_3"),
}

CHAPTER_START = {1: START, 2: START2}

ROOMS.update({
    # ---------------------------------------------------------------- La Forêt maudite
    "F1": R("CLAIRIERE DU VORTEX", "foret", (1, 2), dict(W="F3", E="F2", S="F5"),
            plat=[(3, 8, 4, 1), (12, 10, 5, 1)], decor=[("deadtree", 2, 9), ("vortex_bas", 9, 1)],
            enemies=[("wisp", 9, 6, 3)]),
    "F2": R("SENTIER DES PENDUS", "foret", (2, 2), dict(W="F1", E="F7", S="F6", N="A2"),
            plat=[(2, 9, 4, 1), (14, 9, 4, 1)], decor=[("deadtree", 13, 10), ("deadtree", 4, 10)],
            enemies=[("goule", 15, 17), ("wisp", 9, 8, 3)]),
    "F3": R("BOSQUET DES ECHOS", "foret", (0, 2), dict(E="F1", S="F4"),
            plat=[(1, 6, 6, 1), (6, 1, 1, 5, FAKE), (11, 9, 5, 1), (14, 14, 3, 1)],
            decor=[("deadtree", 8, 10)],
            enemies=[("wisp", 13, 5, 3), ("goule", 5, 17)]),
    "F4": R("MARAIS DES FEUX", "foret", (0, 3), dict(N="F3", E="F5"),
            plat=[(4, 12, 4, 1), (12, 8, 5, 1), (2, 6, 3, 1)], decor=[("deadtree", 15, 9)],
            enemies=[("wisp", 8, 6, 3), ("goule", 12, 17)]),
    "F5": R("RACINES NOIRES", "foret", (1, 3), dict(N="F1", W="F4", E="F6"),
            plat=[(3, 9, 4, 1), (13, 10, 4, 1)], cauldrons=[(9, 16, "plein")],
            decor=[("deadtree", 15, 11)],
            enemies=[("goule", 16, 17), ("bat", 6, 5)]),
    "F6": R("TOMBES OUBLIEES", "foret", (2, 3), dict(N="F2", W="F5", S="V2"),
            plat=[(2, 10, 4, 1), (14, 8, 4, 1), (4, 16, 1, 2), (15, 16, 1, 2)],
            decor=[("cross", 6, 14), ("cross", 13, 14)],
            enemies=[("gargouille", 15, 7), ("goule", 9, 17)]),
    "F7": R("LISIERE NOIRE", "foret", (3, 2), dict(W="F2"),
            plat=[(3, 10, 4, 1), (10, 7, 4, 1), (15, 12, 3, 1)],
            decor=[("citadel_far", 12, 4), ("deadtree", 6, 11)],
            enemies=[("goule", 6, 17), ("wisp", 14, 5, 2)]),
    # ---------------------------------------------------------------- La Chapelle en ruine
    "A1": R("PARVIS EN RUINE", "chapelle", (1, 1), dict(E="A2", N="A4"),
            plat=[(3, 13, 3, 1), (12, 9, 4, 1), (5, 6, 3, 1)], decor=[("vitrail", 15, 3)],
            enemies=[("goule", 15, 17), ("gargouille", 13, 8)]),
    "A2": R("NEF EFFONDREE", "chapelle", (2, 1), dict(W="A1", E="A3", S="F2"),
            plat=[(7, 11, 6, 1), (2, 8, 3, 1), (15, 8, 3, 1)],
            decor=[("vitrail", 4, 2), ("vitrail", 15, 2)],
            enemies=[("wisp", 5, 5, 3), ("goule", 3, 17)]),
    "A3": R("CHOEUR BRISE", "chapelle", (3, 1), dict(W="A2", N="A6"),
            plat=[(13, 11, 5, 1), (3, 8, 4, 1)], decor=[("vitrail", 9, 2), ("cross", 9, 14)],
            enemies=[("wisp", 10, 7, 3), ("gargouille", 4, 7)]),
    "A4": R("CRYPTE DES MOINES", "chapelle", (1, 0), dict(S="A1", E="A5"), dark=True,
            plat=[(3, 10, 4, 1), (13, 7, 4, 1), (12, 13, 2, 1)],
            enemies=[("goule", 5, 17), ("bat", 10, 5)]),
    "A5": R("LE CLOCHER", "chapelle", (2, 0), dict(W="A4", E="A6"),
            plat=[(7, 4, 6, 1), (2, 13, 3, 1), (14, 10, 3, 1), (3, 7, 3, 1)],
            decor=[("vitrail", 9, 8)],
            enemies=[("gargouille", 4, 6), ("gargouille", 15, 9), ("bat", 10, 8)]),
    "A6": R("BIBLIOTHEQUE", "chapelle", (3, 0), dict(W="A5", S="A3"),
            plat=[(2, 9, 5, 1), (13, 12, 5, 1), (9, 6, 3, 1)], decor=[("vitrail", 15, 3)],
            enemies=[("wisp", 13, 5, 3), ("goule", 15, 17)]),
    # ---------------------------------------------------------------- L'Abîme de feu (lave)
    "V1": R("BORD DE L'ABIME", "abime", (1, 4), dict(E="V2", S="V4"), lava=True,
            plat=[(1, 14, 5, 3), (13, 12, 4, 1), (7, 8, 4, 1)],
            enemies=[("bulle", 15, 0), ("wisp", 12, 5, 3)]),
    "V2": R("PORTE DES FLAMMES", "abime", (2, 4), dict(N="F6", W="V1", E="V3", S="V5"), lava=True,
            plat=[(2, 12, 4, 1), (14, 12, 4, 1)], decor=[("lavafall", 3, 1)],
            enemies=[("bulle", 5, 0), ("bulle", 15, 0), ("wisp", 14, 6, 3)]),
    "V3": R("PONT DE BASALTE", "abime", (3, 4), dict(W="V2", E="X7", S="V6"), lava=True,
            plat=[(1, 15, 6, 1), (12, 15, 7, 1), (14, 6, 3, 1)],
            enemies=[("bulle", 7, 0), ("gargouille", 15, 5)]),
    "V4": R("ILE DE BASALTE", "abime", (1, 5), dict(N="V1", E="V5"), lava=True,
            plat=[(7, 13, 6, 4), (2, 9, 3, 1), (15, 10, 3, 1)],
            enemies=[("bulle", 3, 0), ("bulle", 16, 0), ("wisp", 10, 6, 3)]),
    "V5": R("LA FORGE NOIRE", "abime", (2, 5), dict(W="V4", N="V2", E="V6"),
            plat=[(2, 10, 4, 1), (14, 8, 4, 1)],
            decor=[("lavafall", 2, 1), ("lavafall", 17, 1), ("anvil", 4, 16)],
            enemies=[("gargouille", 15, 7), ("wisp", 7, 6, 3)]),
    "V6": R("PUITS DE FEU", "abime", (3, 5), dict(W="V5", N="V3"), lava=True,
            plat=[(1, 15, 5, 1), (8, 11, 3, 1), (14, 8, 4, 1)],
            enemies=[("bulle", 7, 0), ("bulle", 13, 0), ("wisp", 12, 4, 2)]),
    # ---------------------------------------------------------------- La Citadelle : cryptes (obscures)
    "X7": R("CRYPTE FISSUREE", "citadelle", (4, 4), dict(W="V3", E="X8", N="X5"), dark=True,
            plat=[(3, 9, 4, 1), (13, 11, 4, 1), (8, 15, 4, 1)], decor=[("bones", 4, 17)],
            enemies=[("goule", 5, 17), ("bat", 10, 5)]),
    "X8": R("OSSUAIRE NOIR", "citadelle", (5, 4), dict(W="X7", N="X6"), dark=True,
            plat=[(12, 9, 5, 1), (3, 12, 4, 1)], decor=[("bones", 7, 17), ("bones", 14, 17)],
            enemies=[("goule", 15, 17), ("wisp", 6, 5, 3)]),
    "X5": R("ESCALIER D'OS", "citadelle", (4, 3), dict(S="X7", E="X6", N="X1"), dark=True,
            plat=[(2, 15, 3, 1), (4, 11, 3, 1), (13, 9, 3, 1)],
            enemies=[("gargouille", 14, 8), ("bat", 6, 5)]),
    "X6": R("CAVEAU DU GARDIEN", "citadelle", (5, 3), dict(W="X5", S="X8"), dark=True,
            plat=[(13, 13, 5, 1), (3, 9, 4, 1)], decor=[("bones", 3, 17)],
            enemies=[("goule", 5, 17), ("gargouille", 4, 8)]),
    # ---------------------------------------------------------------- La Citadelle : étages
    "X1": R("COUR DE LA CITADELLE", "citadelle", (4, 2), dict(S="X5", E="X2", N="X3"),
            plat=[(2, 10, 4, 1), (14, 10, 4, 1), (8, 6, 4, 1)],
            decor=[("gflame", 3, 4), ("gflame", 16, 4)],
            enemies=[("gargouille", 15, 9), ("goule", 4, 17)]),
    "X2": R("REMPARTS", "citadelle", (5, 2), dict(W="X1", N="X4"),
            plat=[(3, 9, 4, 1), (12, 6, 4, 1)], cauldrons=[(14, 16, "plein")],
            decor=[("gflame", 8, 4)],
            enemies=[("wisp", 8, 9, 3), ("gargouille", 13, 5)]),
    "X3": R("TOUR DES GARGOUILLES", "citadelle", (4, 1), dict(S="X1", E="X4"),
            plat=[(3, 7, 3, 1), (14, 7, 3, 1), (13, 12, 4, 1)],
            enemies=[("gargouille", 15, 6), ("gargouille", 14, 11), ("wisp", 10, 4, 2)]),
    "X4": R("ANTICHAMBRE", "citadelle", (5, 1), dict(W="X3", S="X2", N="N1"),
            plat=[(2, 10, 4, 1), (14, 10, 4, 1)], decor=[("gflame", 4, 4), ("gflame", 15, 4)],
            enemies=[("goule", 15, 17), ("wisp", 5, 5, 2)]),
    # ---------------------------------------------------------------- Finale
    "N1": R("SANCTUAIRE DU NECROMANCIEN", "sanctuaire", (5, 0), dict(S="X4"),
            plat=[(2, 12, 4, 1), (14, 12, 4, 1), (7, 7, 6, 1)], decor=[("pentagram", 10, 3)],
            boss=dict(anchors=[(3, 3), (15, 3), (9, 9), (3, 13), (15, 13)])),
})


# --------------------------------------------------------------------------- helpers
def door_sides(did):
    """Les deux côtés (salle, direction) d'une porte."""
    d = DOORS[did]
    other = ROOMS[d["room"]]["exits"][d["dir"]]
    return [(d["room"], d["dir"]), (other, OPPOSITE[d["dir"]])]


def doors_in_room(rid):
    out = []
    for did in DOORS:
        for room, direction in door_sides(did):
            if room == rid:
                out.append((did, direction))
    return out


def door_for_exit(rid, direction):
    for did, dr in doors_in_room(rid):
        if dr == direction:
            return did
    return None


def opening_cells(direction):
    if direction == "E":
        return [(COLS - 1, r) for r in EW_ROWS]
    if direction == "W":
        return [(0, r) for r in EW_ROWS]
    if direction == "N":
        return [(c, 0) for c in NS_COLS]
    return [(c, ROWS - 1) for c in NS_COLS]


def build_tiles(rid):
    """Construit la grille de tuiles statique d'une salle (sans les portes)."""
    room = ROOMS[rid]
    t = [[EMPTY] * COLS for _ in range(ROWS)]
    for x in range(COLS):
        t[0][x] = SOLID
        t[ROWS - 1][x] = SOLID
    for y in range(ROWS):
        t[y][0] = SOLID
        t[y][COLS - 1] = SOLID
    for direction in room["exits"]:
        for cx, cy in opening_cells(direction):
            t[cy][cx] = EMPTY
    if room["water"]:
        gap = NS_COLS if "S" in room["exits"] else ()     # gouffre vers la salle du dessous
        for x in range(COLS):
            if x in gap:
                continue
            t[ROWS - 2][x] = WATER
            t[ROWS - 1][x] = WATER
    for p in room["plat"]:
        x, y, w, h = p[:4]
        kind = p[4] if len(p) > 4 else SOLID
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if 0 <= xx < COLS and 0 <= yy < ROWS:
                    t[yy][xx] = kind
    return t


def zone_theme(rid):
    return ZONES[ROOMS[rid]["zone"]]["theme"]


def room_chapter(rid):
    return ZONES[ROOMS[rid]["zone"]].get("chapter", 1)


def gate_rect(gate):
    (tx, ty), (w, h) = gate["at"], gate["size"]
    return (tx * TILE, ty * TILE, w * TILE, h * TILE)
