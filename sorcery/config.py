"""Constantes globales du jeu Sorcery (recréation)."""

# Résolution logique "Mode 0" du CPC : 160x200, pixels 2:1 (larges).
LOGICAL_W, LOGICAL_H = 160, 200
# Couche texte "Mode 1" (320x200) superposée pour un HUD lisible.
TEXT_W, TEXT_H = 320, 200
WINDOW_W, WINDOW_H = 960, 600          # 6x3 par pixel Mode 0

TILE = 8
COLS, ROWS = 20, 19                     # zone de jeu 160x152
PLAY_W, PLAY_H = COLS * TILE, ROWS * TILE
HUD_Y = PLAY_H                          # bandeau de statut 152..199

TICK_HZ = 50                            # logique fixe 50 Hz
TICK_S = 1.0 / TICK_HZ

TIME_LIMIT_MIN = 30                     # compte à rebours global [I]
TIME_LIMIT_CH2_MIN = 20                 # nouveau compte à rebours du Chapitre 2 [I]
CHAPTER_SCREEN_TICKS = 500              # écran « CHAPITRE 2 » (10 s max, Espace pour passer)
ENERGY_MAX = 100.0

# Physique (px logiques par tick à 50 Hz) [I] : spec = 2/1/2 px par frame à 25 Hz.
SPEED_X = 1.0
SPEED_UP = 1.0
SPEED_FALL = 0.5
SPEED_DOWN = 1.0

# Score [I]
SCORE_KILL = 100
SCORE_FREE = 500
SCORE_BOSS = 5000
SCORE_TIME_PER_S = 10
SCORE_HEART = 250
SCORE_CRAFT = 500

# Palette CPC : 16 encres choisies parmi les 27 couleurs matérielles.
PALETTE = [
    (0, 0, 0),        # 0 noir
    (0, 0, 128),      # 1 bleu
    (0, 0, 255),      # 2 bleu vif
    (128, 0, 0),      # 3 rouge
    (255, 0, 0),      # 4 rouge vif
    (128, 0, 255),    # 5 mauve
    (0, 128, 0),      # 6 vert
    (0, 255, 0),      # 7 vert vif
    (255, 128, 128),  # 8 rose
    (0, 255, 255),    # 9 cyan vif
    (128, 128, 0),    # A jaune (olive / brun)
    (255, 255, 0),    # B jaune vif
    (255, 128, 0),    # C orange
    (255, 0, 255),    # D magenta vif
    (128, 128, 128),  # E gris
    (255, 255, 255),  # F blanc vif
]


# ===========================================================================
# Mode « Classique CPC 1985 » (par défaut) : valeurs prouvées par l'analyse binaire de la
# disquette originale (docs/ANALYSE_DSK.md, adresses entre parenthèses). La logique classique
# tourne à la cadence du jeu original, 37,5 Hz (une itération toutes les 8 interruptions à
# 300 Hz, &07FC) : toutes les vitesses et dégâts ci-dessous sont donc « par trame » d'origine,
# sans facteur de conversion. Le mode Sorcery+ (--plus) garde sa logique à 50 Hz.
# ===========================================================================
CL_FRAME_HZ = 37.5                      # trames de jeu par seconde (§7.1)
CL_FRAME_S = 1.0 / CL_FRAME_HZ
CL_CELL_W, CL_CELL_H = 4, 8             # cellule de collision 4x8 px Mode 0 (§8.1)
CL_COLS, CL_ROWS = 40, 18               # 40 x 18 cellules = 160 x 144 (§8.1)
CL_PLAY_W, CL_PLAY_H = CL_COLS * CL_CELL_W, CL_ROWS * CL_CELL_H
CL_HUD_Y = CL_PLAY_H                    # bandeau Mode 1 sous le jeu, lignes 144..199
CL_ROOMS = 40                           # 40 salles reliées par des portes (§8.1)
CL_CAPTIVES = 8                         # 8 sorciers captifs (§10.2)

CL_SPRITE_W, CL_SPRITE_H = 12, 24       # sorcier, ennemis, portes, barrières : 3x3 cellules (§7.2)
CL_X_MAX, CL_Y_MAX = 148, 120           # butées : bords d'écran = murs (&1195, &11D2)
CL_SPEED_X = 2                          # px Mode 0 par trame, sans inertie (&0F4B, &0F8A)
CL_SPEED_UP = 2                         # lignes par trame, joystick haut (&0F3A)
CL_SPEED_FALL = 2                       # chute à vitesse constante, pas de commande « bas » (&0FC9)

CL_ENERGY_MAX = 99                      # énergie BCD, départ 99 (&07F1)
CL_TIME_VBL = 640 * 72                  # sablier : 640 octets effacés, 1 toutes les 72 VBL (&1BF2)
CL_TIME_S = CL_TIME_VBL / 50.0          # = 921,6 s = 15 min 22 s
CL_TIME_FRAMES = int(round(CL_TIME_S * CL_FRAME_HZ))   # 34 560 trames à 37,5 Hz

# Dégâts : fraction /256 retranchée d'un accumulateur à chaque trame ; chaque retenue = -1
# point d'énergie (&1ACF, &106E).
CL_DMG_T1, CL_DMG_T2, CL_DMG_T3 = 75, 60, 50      # par type d'ennemi (§10.1)
CL_DMG_FIRE = 50                                  # case « feu » sous les pieds (&1048)
CL_CAULDRON_GOOD = 1                    # +1 énergie par trame jusqu'à 99 (&14A1)
CL_CAULDRON_BAD = 2                     # -1 par VBL, 2 VBL par trame (&14FE)
CL_CONTACT_DY, CL_CONTACT_DX = 18, 9    # contact ennemi / portée de ramassage (&1AB3, &17C5)
CL_CAPTIVE_DY, CL_CAPTIVE_DX = 22, 10   # toucher un captif (&19E0)
CL_CAULDRON_DX = 4                      # posé sur le chaudron : Y = Ychaudron - 16, |dX| <= 4
CL_SPELL_DY, CL_SPELL_DX = 4, 2         # projectiles de sort : 4 lignes / 2 px par trame (&1D07)
CL_ENEMY_SPEED = {1: (1, 1), 2: (1, 0), 3: (2, 1)}  # (px X, lignes Y) par trame (§10.1)

# Barème (§11) : aucun bonus de temps.
CL_SCORE_ROOM = 500                     # première visite d'une salle (&0B79)
CL_SCORE_PICKUP = 250                   # premier ramassage d'un objet (&1807)
CL_SCORE_KILL = 1000                    # ennemi tué à l'arme (&18FD)
CL_SCORE_SPELL = 500                    # ennemi tué par un sort (&1909)
CL_SCORE_FREE = 2000                    # sorcier libéré (&1A0E)
CL_SCORE_TIME_PER_S = 0

# Palette de jeu (encres 0-15, &1CB2) et fond du bandeau Mode 1 (encre 0 bleue, &44).
CL_PALETTE = [
    (0, 0, 0), (255, 255, 0), (255, 128, 0), (255, 0, 0),
    (0, 255, 255), (255, 255, 255), (128, 128, 255), (255, 128, 255),
    (0, 255, 0), (0, 128, 128), (128, 0, 0), (0, 128, 0),
    (255, 255, 128), (0, 255, 128), (128, 128, 128), (128, 128, 0),
]
CL_HUD_BG = (0, 0, 128)
