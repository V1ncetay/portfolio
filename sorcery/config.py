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
