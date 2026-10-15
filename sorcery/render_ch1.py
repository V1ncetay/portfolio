"""Graphismes du Chapitre 1 : décors en couches, tuiles ombrées, animations d'ambiance.

Tout reste dans les 16 encres CPC de config.PALETTE, en 160x152 logiques (pixels Mode 0).
Le fond statique d'une salle (ciel, lointains, décor, tuiles) est peint une seule fois puis mis
en cache par Renderer ; seules les petites animations d'ambiance (flammes, étoiles qui scintillent,
gouttes, lucioles, roseaux, eau) sont redessinées à chaque frame.

Aléa 100 % déterministe : graines dérivées de zlib.crc32 / FNV (jamais hash() d'une str, salé par
processus), pour des captures d'écran reproductibles.
"""
import math
import random
import zlib

import pygame

from config import PALETTE as P, TILE, COLS, ROWS, PLAY_W, PLAY_H
from world import SOLID, FAKE, WATER

# Matrice de Bayer 4x4 : tramage ordonné (dégradés façon CPC).
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))

# Décor purement visuel ajouté au Ch.1 (en tuiles), sans toucher aux données de world.py.
EXTRA_DECOR = {
    "L4": [("menhir_brise", 7, 15)],
    "B5": [("owl", 0, 0)],
    "C1": [("banner_c", 5, 2), ("banner_c", 14, 2)],
    "C2": [("torch", 10, 3)],
    "C3": [("rack", 3, 15), ("banner_c", 11, 2)],
    "C4": [("barrels", 10, 16), ("torch", 9, 4)],
    "C5": [("banner_c", 4, 2), ("banner_c", 15, 2)],
    "C6": [("torch", 16, 8), ("banner_c", 5, 2)],
    "C7": [("torch", 11, 4), ("skeleton", 9, 14)],
    "P1": [("mirror", 2, 2), ("mirror", 7, 2), ("mirror", 14, 2)],
    "P2": [("throne", 9, 15), ("chandelier", 10, 1)],
    "P3": [("tapestry", 2, 2), ("chandelier", 12, 1)],
    "P4": [("tapestry", 4, 2), ("tapestry", 13, 2)],
}

# Flamme de torche (4 images, 4x5) : B jaune, C orange, 4 rouge, F cœur blanc.
FLAME = (
    ("..B.", ".BB.", ".BFB", "BCFC", ".C4."),
    (".B..", ".BB.", "BFB.", "CFCB", ".4C."),
    ("..B.", "..BB", ".BFB", "BCFC", ".C4."),
    ("...B", ".BB.", "BBFB", "CFBC", ".44."),
)
CANDLE = (("B", "C"), ("C", "B"), ("B", "B"), (".", "B"))


def h32(*v):
    """Hash FNV-1a 32 bits d'entiers : stable d'un processus à l'autre."""
    x = 2166136261
    for n in v:
        x = ((x ^ (n & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    x ^= x >> 13
    x = (x * 0x5BD1E995) & 0xFFFFFFFF
    return x ^ (x >> 15)


def room_seed(rid, salt=""):
    return zlib.crc32((rid + "/" + salt).encode())


class Canvas:
    """Petites primitives pixel sur une Surface (indices de palette)."""

    def __init__(self, s):
        self.s = s
        self.w, self.h = s.get_size()

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.s.set_at((x, y), P[c])

    def rect(self, x, y, w, h, c):
        if w > 0 and h > 0:
            self.s.fill(P[c], (x, y, w, h))

    def hline(self, x0, x1, y, c):
        self.rect(min(x0, x1), y, abs(x1 - x0) + 1, 1, c)

    def vline(self, x, y0, y1, c):
        self.rect(x, min(y0, y1), 1, abs(y1 - y0) + 1, c)

    def dith(self, x, y, c, level):
        """Pose c si le seuil de Bayer est sous level (0 = rien, 16 = plein)."""
        if level > BAYER[y & 3][x & 3]:
            self.px(x, y, c)

    def dith_rect(self, x0, y0, w, h, c, level):
        for y in range(max(0, y0), min(self.h, y0 + h)):
            row = BAYER[y & 3]
            for x in range(max(0, x0), min(self.w, x0 + w)):
                if level > row[x & 3]:
                    self.s.set_at((x, y), P[c])

    def gradient(self, y0, y1, stops):
        """Dégradé vertical tramé ; stops = [(t, encre), ...] avec t croissant de 0 à 1."""
        span = max(1, y1 - y0)
        for y in range(y0, y1):
            t = (y - y0) / span
            for i in range(len(stops) - 1):
                if stops[i][0] <= t <= stops[i + 1][0]:
                    (ta, ca), (tb, cb) = stops[i], stops[i + 1]
                    break
            else:
                (ta, ca), (tb, cb) = stops[-1], stops[-1]
            k = 0.0 if tb == ta else (t - ta) / (tb - ta)
            lvl = (int(k * 16 + 0.5) + 2) // 4 * 4          # 5 trames seulement : bandes nettes
            row = BAYER[y & 3]
            pa, pb = P[ca], P[cb]
            for x in range(self.w):
                self.s.set_at((x, y), pb if lvl > row[x & 3] else pa)

    def ellipse(self, cx, cy, rx, ry, c, level=16):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    if level >= 16:
                        self.px(x, y, c)
                    else:
                        self.dith(x, y, c, level)

    def art(self, x, y, rows):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch != ".":
                    self.px(x + i, y + j, int(ch, 16))


# ------------------------------------------------------------------------- grille
def solid_at(tiles, cx, cy):
    if cx < 0 or cx >= COLS or cy < 0 or cy >= ROWS:
        return True
    return tiles[cy][cx] in (SOLID, FAKE)


def free_px(tiles, x, y):
    """Le pixel (x, y) tombe-t-il dans une case vide (ni mur, ni eau) ?"""
    cx, cy = int(x) // TILE, int(y) // TILE
    if cx < 0 or cx >= COLS or cy < 0 or cy >= ROWS:
        return False
    return tiles[cy][cx] not in (SOLID, FAKE, WATER)


def free_rect(tiles, x, y, w, h):
    for cy in range(int(y) // TILE, (int(y + h) - 1) // TILE + 1):
        for cx in range(int(x) // TILE, (int(x + w) - 1) // TILE + 1):
            if not free_px(tiles, cx * TILE, cy * TILE):
                return False
    return True


def ground_y(tiles, x, y=8):
    """Premier pixel solide (ou d'eau) sous (x, y)."""
    cx = int(x) // TILE
    for cy in range(max(0, int(y) // TILE), ROWS):
        if 0 <= cx < COLS and tiles[cy][cx] in (SOLID, FAKE, WATER):
            return cy * TILE
    return PLAY_H


# ------------------------------------------------------------------------- tuiles
def paint_tile(theme, rid, tiles, cx, cy):
    """Tuile 8x8 du Ch.1 : texture variée (hash stable) + bords éclairés / ombrés."""
    s = pygame.Surface((TILE, TILE))
    cv = Canvas(s)
    hv = h32(cx, cy, room_seed(rid) & 0xFFFF)
    up = solid_at(tiles, cx, cy - 1)
    dn = solid_at(tiles, cx, cy + 1)
    lf = solid_at(tiles, cx - 1, cy)
    rt = solid_at(tiles, cx + 1, cy)
    water_up = cy > 0 and tiles[cy - 1][cx] == WATER
    top = not up and not water_up
    px = cv.px

    def r(i):
        return h32(hv, i)

    if theme == "landes":
        s.fill(P[10])
        for i in range(7):
            v = r(i)
            x, y = v % 8, (v >> 3) % 8
            px(x, y, (3, 3, 3, 0, 6, 3, 0)[i])
        if r(9) % 4 == 0:                                    # caillou
            x, y = r(10) % 6, 3 + r(11) % 4
            px(x, y, 14)
            px(x + 1, y, 14)
            px(x, y - 1, 15)
            px(x + 1, y + 1, 0)
        if top:
            for x in range(8):
                px(x, 0, 7)
                px(x, 1, 7 if (h32(hv, x) % 3) else 6)
                if h32(hv, x, 1) % 3 == 0:
                    px(x, 2, 6)
                    if h32(hv, x, 2) % 3 == 0:
                        px(x, 3, 6)
        if not dn:
            for x in range(8):
                px(x, 7, 3 if (x + cx) % 2 else 0)
        if not rt:
            for y in range(2 if top else 0, 8):
                px(7, y, 3)
        if not lf:
            for y in range(2 if top else 0, 8, 2):
                px(0, y, 12)
    elif theme == "bois":
        s.fill(P[10])
        gx = hv % 8
        for y in range(8):                                   # racines entrelacées
            px((gx + y // 3) % 8, y, 3)
            px((gx + 5 - y // 4) % 8, y, 3 if y % 3 else 0)
        for i in range(3):
            v = r(i)
            px(v % 8, (v >> 3) % 8, (6, 0, 6)[i])
        if top:
            for x in range(8):
                v = h32(hv, x)
                px(x, 0, 7 if v % 3 else 6)
                px(x, 1, 6 if v % 5 else 12)
                if v % 4 == 0:
                    px(x, 2, 6)
        if not dn:
            for x in range(8):
                px(x, 7, 0 if (x + cy) % 3 else 3)
        if not rt:
            for y in range(2 if top else 0, 8):
                px(7, y, 3)
    elif theme == "riviere":
        s.fill(P[14])
        jy = 3 + (cy % 2)
        for x in range(8):
            px(x, jy, 1)
        jx1, jx2 = r(1) % 8, (r(2) % 8)
        for y in range(0, jy):
            px(jx1, y, 1)
        for y in range(jy + 1, 8):
            px(jx2, y, 1)
        px((jx1 + 1) % 8, 0, 15)
        px((jx2 + 1) % 8, jy + 1, 15)
        if r(5) % 3 == 0:                                    # reflet humide
            px(r(6) % 8, jy + 2 + r(7) % 2, 9)
        for x in range(8):                                   # pied mouillé
            cv.dith(x, 6, 1, 6)
            cv.dith(x, 7, 1, 8)
        if top:
            for x in range(8):
                v = h32(hv, x)
                px(x, 0, 7 if v % 3 == 0 else 6)
                px(x, 1, 6)
                if v % 3 == 1:                               # mousse qui pend
                    px(x, 2, 6)
                    if v % 7 == 1:
                        px(x, 3, 6)
        if not lf:
            for y in range(2 if top else 0, 8):
                if y != jy:
                    px(0, y, 15)
        if not rt:
            for y in range(8):
                px(7, y, 1)
        if not dn:
            for x in range(8):
                px(x, 7, 0 if x % 2 else 1)
    elif theme == "chateau":
        s.fill(P[3])
        off = 0 if cy % 2 == 0 else 4
        for course, (y0, x0) in enumerate(((0, off), (4, (off + 4) % 8))):
            for x in range(8):
                px(x, y0 + 3, 0)
            for y in range(y0, y0 + 3):
                px(x0, y, 0)
            for half in range(2):                            # deux briques par rangée
                bx = (x0 + 1 + half * 4) % 8
                v = h32(hv, course, half)
                if v % 5 == 0:                               # brique sombre
                    for k in range(3):
                        for j in range(3):
                            cv.dith((bx + k) % 8, y0 + j, 0, 6)
                else:
                    px(bx, y0, 4)
                    px((bx + 1) % 8, y0, 4)
                    if v % 7 == 1:
                        px((bx + 2) % 8, y0 + 1, 12)
        if top:                                              # chaperon de pierre
            for x in range(8):
                px(x, 0, 15 if (x + cx) % 3 == 0 else 14)
                px(x, 1, 14)
                px(x, 2, 0)
        if not lf:
            for y in range(3 if top else 0, 8):
                if s.get_at((0, y))[:3] != P[0]:
                    px(0, y, 4)
        if not rt:
            for y in range(3 if top else 0, 8):
                px(7, y, 0)
        if not dn:
            for x in range(8):
                px(x, 7, 0)
    elif theme == "catacombes":
        s.fill(P[14])
        jx = 2 + r(1) % 4
        jy = 3 + (cx + cy) % 2
        for x in range(8):
            px(x, 7, 0)
            px(x, jy, 0) if x >= jx else None
        for y in range(7):
            px(jx, y, 0) if y < jy else px((jx + 3) % 8, y, 0)
        px(0, 0, 15)
        px(1, 0, 15)
        px(jx + 1, 0, 15)
        px(jx + 1, jy + 1, 15)
        for i in range(3):
            v = r(4 + i)
            px(v % 8, (v >> 3) % 7, 1)
        if not top and h32(hv, 99) % 9 == 0:                 # crâne scellé dans la paroi
            s.fill(P[0], (1, 1, 6, 6))
            cv.art(2, 2, ("FFFF", "0F0F", "FFFF", ".EE."))
        if top:
            for x in range(8):
                px(x, 0, 15 if (x + hv) % 3 else 14)
                px(x, 1, 14)
            if hv % 4 == 0:                                  # osselet
                bx = (hv >> 4) % 5
                for k in range(3):
                    px(bx + k, 0, 15)
                px(bx, 1, 15)
                px(bx + 2, 1, 15)
        if not lf:
            for y in range(8):
                if y not in (7, jy):
                    px(0, y, 15)
        if not rt:
            for y in range(8):
                px(7, y, 1)
    elif theme == "palais":
        floor = cy == ROWS - 1
        if floor:                                            # damier de marbre
            for y in range(8):
                for x in range(8):
                    on = ((cx * 8 + x) // 4 + (y // 4)) % 2
                    px(x, y, 15 if on else 2)
            for x in range(8):
                px(x, 7, 1)
        else:
            s.fill(P[9])
            x = hv % 8
            for y in range(8):                               # veine de marbre
                px(x, y, 15)
                if (hv >> y) & 1:
                    x = (x + 1) % 8
            for i in range(2):
                v = r(i)
                px(v % 8, (v >> 3) % 8, 2)
            if not rt:
                for y in range(8):
                    px(7, y, 2)
            if not dn:
                for x in range(8):
                    px(x, 7, 2)
                    px(x, 6, 2) if x % 2 else None
            if not lf:
                for y in range(8):
                    px(0, y, 15)
        if top:
            for x in range(8):
                px(x, 0, 11)
                px(x, 1, 12 if (x + cx) % 4 == 0 else 11)
                px(x, 2, 10)
    elif theme == "stonehenge":
        s.fill(P[14])
        bx, by = cx // 2, cy // 3                            # gros blocs de grès
        v = h32(bx, by, 7)
        if cx % 2 == 0 and v % 3 == 0:
            for y in range(8):
                px(0, y, 0)
        if cy % 3 == 0 and not top:
            for x in range(8):
                px(x, 0, 0)
                px(x, 1, 15) if x % 3 else None
        for i in range(5):
            w = r(i)
            px(w % 8, (w >> 3) % 8, (10, 6, 10, 1, 15)[i])
        if r(8) % 3 == 0:                                    # fissure
            x = r(9) % 6 + 1
            for y in range(2, 6):
                px(x + (y % 2), y, 0)
        if top:
            for x in range(8):
                vv = h32(hv, x)
                px(x, 0, 7 if vv % 2 else 6)
                px(x, 1, 6 if vv % 4 else 7)
                if vv % 3 == 0:
                    px(x, 2, 6)
        if not lf:
            for y in range(2 if top else 0, 8):
                px(0, y, 15)
        if not rt:
            for y in range(8):
                px(7, y, 1)
        if not dn:
            for x in range(8):
                px(x, 7, 1 if x % 2 else 0)
    elif theme == "seuil":                                   # N0 : pierre mauve veinée de lumière
        s.fill(P[5])
        off = 0 if cy % 2 == 0 else 4
        for x in range(8):
            px(x, 7, 0)
        for y in range(7):
            px(off, y, 0)
        px((off + 1) % 8, 0, 13)
        px((off + 2) % 8, 0, 13)
        if hv % 3 == 0:
            x = r(1) % 8
            for y in range(1, 7):
                px(x, y, 13 if y % 2 else 1)
                x = (x + (1 if (hv >> y) & 1 else -1)) % 8
        if top:
            for x in range(8):
                px(x, 0, 13)
                px(x, 1, 15 if (x + cx) % 4 == 0 else 13)
        if not rt:
            for y in range(8):
                px(7, y, 1)
        if not dn:
            for x in range(8):
                px(x, 7, 1)
    return s


# ------------------------------------------------------------------------- fonds
def build_room(renderer, rid, room, theme, tiles):
    """Peint le fond complet (statique) d'une salle du Ch.1 ; renvoie (surface, ambiance)."""
    s = pygame.Surface((PLAY_W, PLAY_H))
    cv = Canvas(s)
    rng = random.Random(room_seed(rid))
    amb = []
    if theme == "chateau":
        bg_chateau(cv, rng, rid, tiles, amb, room)
    else:
        BACKDROPS[theme](cv, rng, rid, tiles, amb)
    decor = list(room["decor"]) + EXTRA_DECOR.get(rid, [])
    for d in decor:
        paint_decor(cv, renderer, rid, tiles, d[0], d[1], d[2], amb)
    contact_shadows(cv, tiles)
    for cy in range(ROWS):
        for cx in range(COLS):
            if tiles[cy][cx] in (SOLID, FAKE):
                s.blit(paint_tile(theme, rid, tiles, cx, cy), (cx * TILE, cy * TILE))
    top_details(cv, theme, rid, tiles)
    return s, amb


def contact_shadows(cv, tiles):
    """Ombre portée sous et à droite des blocs : les plateformes se détachent du fond."""
    for cy in range(ROWS):
        for cx in range(COLS):
            if tiles[cy][cx] in (SOLID, FAKE, WATER):
                continue
            x0, y0 = cx * TILE, cy * TILE
            if solid_at(tiles, cx, cy - 1) and cy > 0:
                for x in range(x0, x0 + TILE):
                    cv.px(x, y0, 0)
                    cv.dith(x, y0 + 1, 0, 10)
                    cv.dith(x, y0 + 2, 0, 4)
            if solid_at(tiles, cx - 1, cy) and cx > 0:
                for y in range(y0, y0 + TILE):
                    cv.dith(x0, y, 0, 12)


def top_details(cv, theme, rid, tiles):
    """Brins d'herbe / fougères au-dessus des plateformes, racines et mousses dessous."""
    seed = room_seed(rid, "top")
    for cy in range(1, ROWS):
        for cx in range(COLS):
            if tiles[cy][cx] not in (SOLID, FAKE):
                continue
            x0, y0 = cx * TILE, cy * TILE
            above_free = free_px(tiles, x0, y0 - 1)
            below_free = cy + 1 < ROWS and free_px(tiles, x0, y0 + TILE)
            for i in range(TILE):
                v = h32(seed, cx, cy, i)
                x = x0 + i
                if above_free:
                    if theme in ("landes", "stonehenge") and v % 5 == 0:
                        cv.px(x, y0 - 1, 7 if v % 2 else 6)
                        if v % 15 == 0:
                            cv.px(x, y0 - 2, 6)
                    elif theme == "landes" and v % 31 == 3:   # bruyère
                        cv.px(x, y0 - 1, 13)
                    elif theme == "bois" and v % 6 == 0:
                        cv.px(x, y0 - 1, 6)
                        cv.px(x + (1 if v % 4 else -1), y0 - 2, 7 if v % 3 else 6)
                    elif theme == "riviere" and v % 9 == 0:
                        cv.px(x, y0 - 1, 6)
                    elif theme == "catacombes" and v % 23 == 0:
                        cv.px(x, y0 - 1, 15)                    # éclat d'os
                if below_free:
                    if theme == "bois" and v % 5 == 0:          # racines qui pendent
                        ln = 2 + v % 4
                        for k in range(ln):
                            cv.px(x + (k // 2 if v % 2 else -(k // 2)), y0 + TILE + k, 3 if k < ln - 1 else 10)
                    elif theme == "riviere" and v % 6 == 0:      # mousse dégoulinante
                        for k in range(1 + v % 3):
                            cv.px(x, y0 + TILE + k, 6)
                    elif theme == "catacombes" and v % 41 == 0:  # toile d'araignée
                        web(cv, x, y0 + TILE, 5 + v % 4, 1 if v % 2 else -1)


def web(cv, x, y, r, d):
    """Toile d'araignée en coin (d = +1 vers la droite, -1 vers la gauche)."""
    for k in range(r + 1):
        cv.dith(x + d * k, y, 14, 12)
        cv.dith(x, y + k, 14, 12)
        cv.dith(x + d * k, y + k, 14, 10)
        cv.dith(x + d * (k // 2 + k // 3), y + k, 14, 6)
    for rr in (r // 2, r):
        for k in range(rr + 1):
            cv.px(x + d * k, y + rr - k // 2 - (rr - k) // 2, 14)


def stars(cv, rng, amb, n, y0, y1, twinkle=6, cols=(15, 14, 9, 14), avoid=None):
    for i in range(n):
        x, y = rng.randrange(9, PLAY_W - 9), rng.randrange(y0, y1)
        if avoid and avoid(x, y):
            continue
        c = cols[rng.randrange(len(cols))]
        if i < twinkle:
            amb.append(("star", x, y, c, rng.randrange(0, 200)))
        else:
            cv.px(x, y, c)
            if c == 15 and rng.random() < 0.25:             # étoile en croix
                cv.dith(x - 1, y, 1, 16)
                cv.dith(x + 1, y, 1, 16)


def hills(cv, rng, base, amp, freq, body, rim=None, level=16, texture=None, top_out=None):
    ph1, ph2 = rng.uniform(0, 6.28), rng.uniform(0, 6.28)
    tops = []
    for x in range(PLAY_W):
        hgt = base - int(amp * math.sin(x * freq + ph1) + amp * 0.45 * math.sin(x * freq * 2.7 + ph2))
        tops.append(hgt)
        for y in range(hgt, PLAY_H):
            if level >= 16:
                cv.px(x, y, body)
            else:
                cv.dith(x, y, body, level)
            if texture and texture[1] > BAYER[y & 3][(x + y // 4) & 3] and (x * 7 + y * 3) % 11 == 0:
                cv.px(x, y, texture[0])
        if rim is not None and (x % 2 == 0 or hgt != tops[x - 1]):
            cv.px(x, hgt, rim)
    if top_out is not None:
        top_out.extend(tops)
    return tops


def menhir(cv, x, base, h, w):
    slant = (x * 7) % 3 - 1
    for y in range(base - h, base + 1):
        k = y - (base - h)
        inset = 2 if k < 2 else (1 if k < 5 else 0)
        if k < 3 and slant:
            inset += 1 if (slant > 0) == (k % 2 == 0) else 0
        for xx in range(x + inset, x + w - inset):
            if xx == x + inset:
                c = 15 if (y % 3) else 14
            elif xx >= x + w - inset - 2:
                c = 1 if xx == x + w - inset - 1 else 14
                if xx == x + w - inset - 2 and y % 2:
                    c = 1
            else:
                c = 14
            cv.px(xx, y, c)
    for i in range(4):                                       # lichens
        cv.px(x + 1 + (i * 3) % max(1, w - 2), base - h + 3 + i * h // 5, 6 if i % 2 else 10)
    cv.hline(x - 1, x + w, base + 1, 0)


def bg_landes(cv, rng, rid, tiles, amb):
    cv.gradient(0, 118, [(0.0, 0), (0.42, 0), (0.8, 1), (1.0, 1)])
    cv.dith_rect(0, 102, PLAY_W, 16, 5, 4)                  # lueur du couchant
    cv.dith_rect(0, 110, PLAY_W, 8, 5, 8)
    stars(cv, rng, amb, 26, 6, 60, twinkle=7)
    # nuages effilochés
    for _ in range(3):
        y = rng.randrange(30, 70)
        x = rng.randrange(-20, 140)
        w = rng.randrange(24, 50)
        for k in range(w):
            cv.dith(x + k, y, 1, 10)
            if 4 < k < w - 6:
                cv.dith(x + k, y - 1, 1, 6)
                cv.dith(x + k + 3, y + 1, 5, 3)
    far = hills(cv, rng, 106, 7, 0.05, 1, rim=5)
    near = []
    hills(cv, rng, 124, 5, 0.08, 0, top_out=near)
    for x in range(PLAY_W):                                  # lande proche : herbe sombre
        cv.px(x, near[x], 6)
        if x % 2:
            cv.px(x, near[x] - 1, 6) if h32(x, 5) % 3 == 0 else None
        for y in range(near[x] + 1, PLAY_H):
            v = h32(x, y, 21)
            if v % 7 == 0 or (y < near[x] + 4 and v % 3 == 0):
                cv.px(x, y, 6)
    # menhirs : lointains (silhouettes) et proches
    for _ in range(2):
        x = rng.randrange(14, 140)
        cv.rect(x, far[x] - 9, 3, 10, 1)
        cv.px(x, far[x] - 9, 5)
    if rid != "L4":
        for _ in range(1 + rng.randrange(2)):
            x = rng.randrange(14, 136)
            menhir(cv, x, near[x + 3] + 2, rng.randrange(18, 28), rng.randrange(6, 9))
    # touffes de bruyère / ajonc au sol
    for _ in range(14):
        x = rng.randrange(8, 150)
        y = rng.randrange(134, 143)
        if not free_px(tiles, x, y):
            continue
        heather = rng.random() < 0.6
        for k in range(-2, 3):
            hgt = 3 - abs(k) + rng.randrange(0, 2)
            for j in range(hgt):
                cv.px(x + k, y - j, 6 if (j + k) % 2 else (5 if heather else 6))
        cv.px(x, y - 3, 13 if heather else 11)
        cv.px(x + 1, y - 2, 13 if heather else 11)


def bg_bois(cv, rng, rid, tiles, amb):
    cv.s.fill(P[0])
    # rais de lune entre les arbres
    for _ in range(3):
        x0 = rng.randrange(0, 150)
        for y in range(20, 140):
            for k in range(6):
                cv.dith(x0 + k + y // 4, y, 1, 3)
    # troncs lointains
    for _ in range(8):
        x, w = rng.randrange(0, 156), rng.randrange(3, 6)
        cv.rect(x, 0, w, PLAY_H, 1)
        for y in range(0, PLAY_H, 2):
            cv.px(x + w - 1, y, 0)
    # troncs proches (écorce, nœuds, racines)
    trunks = []
    for i in range(4):
        x = 12 + i * 38 + rng.randrange(-8, 8)
        w = rng.randrange(6, 10)
        trunks.append((x, w))
        cv.rect(x, 0, w, PLAY_H, 3)
        for y in range(PLAY_H):
            cv.px(x, y, 10)
            cv.px(x + 1, y, 10 if (y // 5 + i) % 3 else 3)
            cv.px(x + w - 1, y, 0)
            cv.px(x + w - 2, y, 0 if y % 2 else 3)
            for k in range(3, w - 2, 3):                     # sillons de l'écorce
                if (y + k * 5 + i * 3) % 11 < 7:
                    cv.px(x + k, y, 0)
        for _ in range(2):
            ky = rng.randrange(40, 120)
            cv.ellipse(x + w // 2, ky, 1.5, 2, 0)
            cv.px(x + w // 2 - 1, ky - 2, 10)
        for side in (-1, 1):                                 # racines évasées
            for k in range(1, 7):
                y = PLAY_H - 8 - k
                xx = x - k if side < 0 else x + w - 1 + k
                for j in range(0, 7 - k):
                    cv.px(xx, y + j + 1, 3 if j else 10)
        for _ in range(2):                                   # branches
            by = rng.randrange(26, 70)
            d = rng.choice((-1, 1))
            ln = rng.randrange(8, 16)
            for k in range(ln):
                xx = (x - k if d < 0 else x + w + k)
                cv.px(xx, by - k // 2, 3)
                cv.px(xx, by - k // 2 + 1, 0 if k % 3 else 3)
    # canopée en couches : masses de feuillage éclairées en haut à gauche
    for layer in range(2):
        for _ in range(9):
            cx, cy = rng.randrange(-6, 166), rng.randrange(-4, 22 + layer * 8)
            rx, ry = rng.randrange(10, 18), rng.randrange(6, 10)
            for y in range(cy - ry, cy + ry + 1):
                for x in range(cx - rx, cx + rx + 1):
                    d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                    if d > 1.0:
                        continue
                    hole = h32(x // 2, y, 3) % 7 == 0
                    lit = (x - cx) / rx + (y - cy) / ry < -0.6
                    if layer == 0:
                        cv.px(x, y, 0 if hole else 6)
                    elif hole and d > 0.5:
                        cv.px(x, y, 0)
                    else:
                        cv.px(x, y, 7 if lit and h32(x, y) % 3 else 6)
            for k in range(rng.randrange(1, 4)):             # lianes
                vx = cx + rng.randrange(-rx + 2, rx - 2)
                ln = rng.randrange(6, 26)
                for j in range(ln):
                    y = cy + ry + j
                    cv.px(vx + (j // 6) % 2, y, 6)
                    if j % 5 == 2:
                        cv.px(vx + 1 + (j // 6) % 2, y, 7)
    # sous-bois : fougères et champignons
    for _ in range(10):
        x, y = rng.randrange(10, 150), 143
        if not free_px(tiles, x, y):
            continue
        if rng.random() < 0.35:
            cv.art(x, y - 3, (".44.", "4F44", ".F..", ".F.."))
        else:
            for k in range(-3, 4):
                hgt = 4 - abs(k)
                for j in range(hgt):
                    cv.px(x + k + (j if k > 0 else -j) // 2, y - j, 7 if j == hgt - 1 else 6)
    # lucioles (animées)
    for i in range(6):
        amb.append(("firefly", rng.randrange(14, 146), rng.randrange(40, 130), rng.randrange(0, 360)))
    if rid == "B5":                                          # le hibou du Cercle des hiboux
        x, w = trunks[1]
        hx, hy = x + w // 2 - 2, 46
        cv.ellipse(hx + 2, hy + 3, 3, 4, 0)
        amb.append(("owl", hx, hy, 0))
        x, w = trunks[3]
        cv.ellipse(x + w // 2, 92, 2.5, 3.5, 0)
        amb.append(("owl", x + w // 2 - 2, 89, 77))


def bg_riviere(cv, rng, rid, tiles, amb):
    cv.gradient(0, 116, [(0.0, 0), (0.45, 0), (0.85, 1), (1.0, 1)])
    cv.dith_rect(0, 104, PLAY_W, 12, 2, 2)
    mx, my = rng.randrange(30, 130), rng.randrange(20, 34)
    stars(cv, rng, amb, 24, 6, 70, twinkle=6, avoid=lambda x, y: abs(x - mx) < 10 and abs(y - my) < 12)
    moon(cv, mx, my, 6, crescent=True)
    # rive lointaine boisée (sapins)
    base = []
    hills(cv, rng, 118, 3, 0.07, 0, top_out=base)
    for _ in range(30):                                      # sapins en ombres chinoises
        x = rng.randrange(0, PLAY_W)
        h = rng.randrange(7, 18)
        y0 = base[x] - h
        for k in range(h + 2):
            half = (k // 2) % 3 + k // 6
            for j in range(-half, half + 1):
                cv.px(x + j, y0 + k, 0)
    # surface lointaine de la rivière : rides et reflet de lune
    cv.rect(0, 120, PLAY_W, 16, 1)
    for y in range(120, 136):
        for x in range(PLAY_W):
            if (x * 3 + y * 7) % 23 == 0 or (y % 3 == 0 and (x + y * 5) % 11 < 3):
                cv.px(x, y, 2)
        if y % 2 == 0:                                       # reflet : tirets horizontaux
            half = 1 + (y - 120) // 4 + h32(y, mx) % 2
            for x in range(mx - half, mx + half + 1):
                cv.px(x, y, 15 if abs(x - mx) < half - 1 else 9)
    for x in range(PLAY_W):
        cv.px(x, 120, 0 if x % 3 else 1)
    # roseaux (animés) au bord de l'eau
    for _ in range(18):
        x = rng.randrange(9, 151)
        base_y = 135
        if not free_px(tiles, x, base_y) or not free_px(tiles, x, base_y - 14):
            continue
        amb.append(("reed", x, base_y, rng.randrange(8, 15), rng.choice((-1, 0, 1)), rng.randrange(0, 100)))
    if rid == "R3":                                          # piles du pont de bois
        for x in (26, 46, 66):
            gy = ground_y(tiles, x, 112)
            for y in range(112, min(gy, 144)):
                cv.px(x, y, 10)
                cv.px(x + 1, y, 3)
            cv.hline(x - 1, x + 2, 140, 9)
    amb.append(("moonrefl", mx))


def moon(cv, mx, my, r, crescent=False):
    for y in range(my - r - 4, my + r + 5):                  # halo tramé
        for x in range(mx - r - 6, mx + r + 7):
            d = math.hypot((x - mx) / 1.0, (y - my) * 1.0 / 1.0)
            dd = math.hypot((x - mx) * 2.0 / 2.0, y - my)
            if r < dd < r + 4 and (x + y) % 2 == 0 and d < r + 4:
                cv.px(x, y, 1)
    for y in range(my - r, my + r + 1):
        for x in range(mx - r, mx + r + 1):
            if (x - mx) ** 2 + (y - my) ** 2 <= r * r:
                if crescent and (x - mx - r // 2) ** 2 + (y - my + 1) ** 2 <= (r - 1) ** 2:
                    continue
                cv.px(x, y, 15)
    if not crescent:
        for dx, dy in ((-2, -2), (1, 1), (-1, 3), (3, -2), (2, 3), (-3, 1)):
            cv.px(mx + dx, my + dy, 14)
        for y in range(my - r, my + r + 1):                  # terminateur
            for x in range(mx + r // 2, mx + r + 1):
                if (x - mx) ** 2 + (y - my) ** 2 <= r * r:
                    cv.dith(x, y, 14, 6)


def torch_spots(rid, room):
    out = []
    for d in list(room["decor"]) + EXTRA_DECOR.get(rid, []):
        if d[0] == "torch":
            out.append((d[1] * TILE + 2, d[2] * TILE + 2))
        elif d[0] == "window":
            out.append((d[1] * TILE + 5, d[2] * TILE + 6))
    return out


def light_at(spots, x, y, radius=26.0):
    best = 0.0
    for (lx, ly) in spots:
        d = math.hypot(x - lx, (y - ly) * 1.6)
        if d < radius:
            best = max(best, 1.0 - d / radius)
    return best


def bg_chateau(cv, rng, rid, tiles, amb, room=None):
    cv.s.fill(P[0])
    seed = room_seed(rid)
    spots = torch_spots(rid, room) if room else []
    for row in range(0, PLAY_H // 6 + 1):
        y0 = row * 6
        off = 0 if row % 2 == 0 else 6
        for bxi in range(-1, PLAY_W // 12 + 1):
            x0 = bxi * 12 + off
            v = h32(seed, row, bxi)
            kind = v % 23
            w = 11
            if kind == 0:                                    # brique manquante
                continue
            lit = light_at(spots, x0 + 5, y0 + 2, 34.0)
            lvl = 4 + int(lit * 14) - (4 if kind in (1, 2, 3) else 0)
            lvl = max(2, min(16, (lvl + 2) // 4 * 4))
            cv.dith_rect(x0 + 1, y0 + 1, w - 1, 3, 1, lvl)  # face de brique tramée
            cv.dith_rect(x0 + 1, y0 + 4, w - 1, 1, 1, lvl // 2)
            cv.hline(x0, x0 + w - 1, y0, 1)                  # arête haute
            cv.vline(x0, y0, y0 + 4, 1)                      # arête gauche
            if lit > 0.25 or kind % 4 == 0:
                cv.px(x0, y0, 2)
            if lit > 0.5:
                cv.hline(x0 + 1, x0 + 3, y0, 2)
            if kind == 4:                                    # fissure
                x = x0 + 3 + v % 5
                for k in range(5):
                    cv.px(x + (k % 2), y0 + k, 0)


def bg_catacombes(cv, rng, rid, tiles, amb):
    cv.s.fill(P[0])
    seed = room_seed(rid)
    y = 0
    row = 0
    while y < PLAY_H:                                        # moellons irréguliers
        h = 7 + h32(seed, row) % 3
        x = -(h32(seed, row, 1) % 12)
        k = 0
        while x < PLAY_W:
            w = 10 + h32(seed, row, k) % 9
            lvl = 4 + h32(seed, row, k, 2) % 5
            cv.dith_rect(x + 1, y + 1, w - 1, h - 1, 1, lvl)
            cv.hline(x + 1, x + w - 1, y + 1, 1)
            cv.vline(x + 1, y + 1, y + h - 1, 1)
            cv.px(x + 1, y + 1, 2) if h32(seed, row, k, 5) % 4 == 0 else None
            x += w
            k += 1
        y += h
        row += 1
    # niches d'ossuaire : rangées de crânes et d'os empilés
    for _ in range(4):
        w, h = rng.randrange(22, 40), 11
        x, y = rng.randrange(10, 150 - w), rng.randrange(12, 120)
        if not free_rect(tiles, x - 2, y - 2, w + 4, h + 4):
            continue
        cv.rect(x, y, w, h, 0)
        cv.hline(x, x + w - 1, y + h, 1)
        for k in range(0, w - 4, 6):
            if (k // 6 + x) % 3 == 1:                        # tas d'os (extrémités)
                cv.art(x + k + 1, y + 4, ("E.E.", "1EE1", "E.E.", "1EE1", "E.E."))
            else:
                cv.art(x + k + 1, y + 3, (".EE.", "EEEE", "0E0E", "EEEE", ".1E."))
        for k in range(w):                                   # os en tas au fond
            cv.dith(x + k, y + h - 1, 14, 5)
    # toiles d'araignée dans les coins
    web(cv, 8, 8, 7, 1)
    web(cv, PLAY_W - 9, 8, 7, -1)
    # gouttes qui tombent du plafond (animées)
    for i in range(3):
        x = rng.randrange(14, 146)
        y1 = ground_y(tiles, x, 9)
        if y1 > 30:
            amb.append(("drip", x, 8, y1, rng.randrange(70, 130), rng.randrange(0, 100)))
            cv.px(x, 8, 9)


def bg_palais(cv, rng, rid, tiles, amb):
    cv.s.fill(P[1])
    for y in range(PLAY_H):                                  # damas discret
        for x in range(PLAY_W):
            u, v = x % 10, y % 10
            if abs(u - 5) + abs(v - 5) == 3 and (u + v) % 2 == 0:
                cv.px(x, y, 2 if (x // 10 + y // 10) % 2 else 0)
    # frise haute
    cv.hline(0, PLAY_W, 13, 10)
    for x in range(0, PLAY_W, 4):
        cv.px(x, 12, 11)
        cv.px(x + 2, 14, 0)
    # lambris
    cv.rect(0, 118, PLAY_W, 26, 1)
    cv.dith_rect(0, 118, PLAY_W, 26, 5, 8)
    cv.hline(0, PLAY_W, 117, 13)
    cv.hline(0, PLAY_W, 118, 10)
    for x0 in range(4, PLAY_W, 18):
        cv.rect(x0, 123, 14, 17, 0)
        cv.rect(x0 + 1, 124, 12, 15, 5)
        cv.hline(x0 + 1, x0 + 13, 139, 13)
        cv.vline(x0 + 13, 124, 139, 13)
        cv.ellipse(x0 + 7, 131, 3, 4, 1)
        cv.ellipse(x0 + 7, 131, 1.5, 2.5, 13)


def bg_stonehenge(cv, rng, rid, tiles, amb):
    cv.gradient(0, 124, [(0.0, 1), (0.3, 0), (0.7, 0), (0.88, 1), (1.0, 5)])
    # voie lactée : bande diagonale tramée, plus étoilée
    for y in range(8, 90):
        for x in range(PLAY_W):
            d = abs((x - 20) * 0.45 - (y - 8))
            if d < 9:
                v = h32(x, y, 11)
                if v % 61 == 0:
                    cv.px(x, y, 14 if v % 2 else 15)
                elif (9 - d) * 0.45 > BAYER[y & 3][x & 3] and v % 3:
                    cv.px(x, y, 1)
    mx, my = rng.randrange(100, 136), rng.randrange(20, 30)
    stars(cv, rng, amb, 36, 6, 96, twinkle=9, avoid=lambda x, y: abs(x - mx) < 13 and abs(y - my) < 14)
    moon(cv, mx, my, 8)
    far = hills(cv, rng, 112, 4, 0.05, 1, rim=5)
    # trilithons lointains : silhouettes sombres liserées de lune
    for x0 in (rng.randrange(12, 50), rng.randrange(96, 130)):
        b = far[min(PLAY_W - 1, x0 + 7)] + 2
        for pxx in (x0, x0 + 11):
            cv.rect(pxx, b - 16, 4, 17, 0)
            cv.vline(pxx, b - 16, b, 1)
        cv.rect(x0 - 2, b - 20, 19, 4, 0)
        cv.hline(x0 - 2, x0 + 16, b - 20, 14)
        cv.hline(x0 - 1, x0 + 15, b - 19, 1)
    near = []
    hills(cv, rng, 130, 3, 0.09, 0, top_out=near)
    for x in range(PLAY_W):
        cv.px(x, near[x], 6)
        for y in range(near[x] + 1, PLAY_H):
            if h32(x, y, 33) % 9 == 0:
                cv.px(x, y, 6)


def bg_seuil(cv, rng, rid, tiles, amb):
    """N0 : ciel tourbillonnant au seuil du vortex (aurore mauve en spirale)."""
    cx, cy = 80, 32
    for y in range(PLAY_H):
        for x in range(PLAY_W):
            dx, dy = (x - cx) * 1.0, (y - cy) * 2.0
            d = math.hypot(dx, dy)
            a = math.atan2(dy, dx)
            band = (d * 0.12 + a * 1.2) % 3.0
            fade = max(0.0, 1.0 - d / 170.0)
            if band < 0.9 and fade * 13 * (1.0 - band) > BAYER[y & 3][x & 3]:
                cv.px(x, y, 5 if (band < 0.3 and d < 60) else 1)
            else:
                cv.px(x, y, 0)
    stars(cv, rng, amb, 30, 6, 120, twinkle=8, cols=(15, 13, 9, 14))
    for _ in range(4):                                       # rochers flottants
        x, y = rng.randrange(14, 140), rng.randrange(50, 120)
        w = rng.randrange(8, 16)
        for k in range(5):
            cv.hline(x + k, x + w - k, y + k, 1)
        cv.hline(x, x + w, y, 5)


BACKDROPS = dict(landes=bg_landes, bois=bg_bois, riviere=bg_riviere, chateau=bg_chateau,
                 catacombes=bg_catacombes, palais=bg_palais, stonehenge=bg_stonehenge, seuil=bg_seuil)


# ------------------------------------------------------------------------- décors
def paint_decor(cv, renderer, rid, tiles, kind, tx, ty, amb):
    x, y = tx * TILE, ty * TILE
    px = cv.px
    if kind == "tower":                                      # tour du sorcier (L2)
        H = PLAY_H - y - 14
        cv.rect(x, y + 6, 28, H, 14)
        for yy in range(y + 6, y + 6 + H):                   # pierres + modelé cylindrique
            rowi = (yy - y - 6) // 5
            off = 0 if rowi % 2 else 3
            if (yy - y - 6) % 5 == 0:
                cv.hline(x, x + 27, yy, 0)
            for xx in range(x + off, x + 28, 7):
                px(xx, yy, 0)
            for k in range(3):
                cv.dith(x + k, yy, 15, 10 - k * 4)
            for k in range(6):
                cv.dith(x + 27 - k, yy, 1, 16 - k * 3)
        for i in range(4):                                   # créneaux
            cv.rect(x + i * 8, y, 4, 6, 14)
            cv.px(x + i * 8, y, 15)
            cv.vline(x + i * 8 + 3, y, y + 5, 1)
        for k in range(16):                                  # toit conique bleu
            w = 32 - k * 2
            for xx in range(x - 2 + k, x - 2 + k + w):
                c = 2 if xx > x + 12 - k // 3 else 9
                if xx > x + 22 - k:
                    c = 1
                px(xx, y - 1 - k + 1, c)
        px(x + 14, y - 15, 11)
        for wy in (y + 20, y + 44):                          # fenêtres éclairées
            cv.rect(x + 10, wy - 1, 7, 11, 0)
            cv.rect(x + 11, wy, 5, 9, 11)
            cv.vline(x + 13, wy, wy + 8, 12)
            cv.hline(x + 11, x + 15, wy + 4, 12)
            cv.hline(x + 10, x + 16, wy + 10, 15)
        cv.rect(x + 9, PLAY_H - 30, 10, 22, 0)               # porte
        cv.rect(x + 10, PLAY_H - 29, 8, 21, 3)
        for k in range(0, 8, 3):
            cv.vline(x + 10 + k, PLAY_H - 29, PLAY_H - 9, 0)
        px(x + 16, PLAY_H - 19, 11)
        cv.hline(x + 9, x + 18, PLAY_H - 31, 15)
    elif kind == "window":                                   # fenêtre en ogive, nuit étoilée
        cv.rect(x - 2, y - 2, 14, 22, 14)
        cv.ellipse(x + 5, y - 2, 7, 7, 14)
        cv.rect(x, y, 10, 18, 1)
        cv.ellipse(x + 4.5, y, 5, 5.5, 1)
        for (sx, sy) in ((2, 1), (7, 6), (3, 11), (8, 14), (6, -2)):
            px(x + sx, y + sy, 15)
        cv.ellipse(x + 7, y + 3, 1.5, 2, 15)
        px(x + 6, y + 2, 1)
        for k in range(18):
            cv.dith(x, y + k, 2, 6)
        cv.vline(x + 4, y - 4, y + 17, 0)
        cv.vline(x + 5, y - 4, y + 17, 14)
        cv.hline(x, x + 9, y + 8, 0)
        cv.hline(x - 3, x + 12, y + 18, 15)
        cv.hline(x - 3, x + 12, y + 19, 0)
        for k in range(-2, 18):
            px(x - 2, y + k, 15) if k % 2 else None
            px(x + 11, y + k, 1)
    elif kind == "chains":
        for yy in range(y, y + 50):
            k = (yy - y) % 4
            if k == 0:
                px(x, yy, 14)
                px(x + 2, yy, 14)
            elif k in (1, 2):
                px(x + 1, yy, 15 if k == 1 else 14)
            else:
                px(x, yy, 1)
                px(x + 2, yy, 1)
        cv.ellipse(x + 1, y + 53, 3, 3, 14)
        cv.ellipse(x + 1, y + 53, 1.5, 1.5, 0)
        px(x - 1, y + 51, 15)
    elif kind == "column":                                   # colonne cannelée, chapiteau doré
        top, bot = y, PLAY_H - 9
        cv.rect(x - 2, top + 3, 8, bot - top - 3, 15)
        for yy in range(top + 3, bot):
            px(x - 2, yy, 14)
            px(x, yy, 9)
            px(x + 2, yy, 9)
            px(x + 4, yy, 14)
            px(x + 5, yy, 2)
        for i, (w, c) in enumerate(((12, 11), (10, 12), (8, 11))):
            cv.hline(x + 2 - w // 2, x + 1 + w // 2, top + i, c)
        px(x - 4, top + 1, 11)
        px(x + 7, top + 1, 11)
        for i, (w, c) in enumerate(((8, 11), (10, 12), (12, 11))):
            cv.hline(x + 2 - w // 2, x + 1 + w // 2, bot - 2 + i, c)
    elif kind in ("banner", "banner_c"):                     # bannière drapée
        body, dark, emblem = (4, 3, 11) if kind == "banner" else (3, 0, 11)
        cv.hline(x - 2, x + 9, y, 10)
        px(x - 3, y, 11)
        px(x + 10, y, 11)
        for yy in range(y + 1, y + 23):
            for xx in range(x, x + 8):
                c = body
                if xx == x or (xx - x) % 3 == 2:
                    c = dark if (xx - x) % 3 == 2 else body
                if xx == x + 7:
                    c = dark
                px(xx, yy, c)
            px(x + 1, yy, 11) if kind == "banner" else None
            px(x + 6, yy, 11) if kind == "banner" else None
        for k in range(4):                                   # pointe en V
            cv.hline(x + k, x + 7 - k, y + 23 + k // 2, body if k < 3 else dark)
        if kind == "banner":
            cv.rect(x + 3, y + 6, 2, 8, emblem)
            cv.rect(x + 1, y + 8, 6, 2, emblem)
            px(x + 3, y + 6, 15)
        else:                                                # tour héraldique
            cv.art(x + 1, y + 6, ("B.B.B.", "BBBBB.", ".BBB..", ".B0B..", ".BBB.."))
    elif kind == "altar":                                    # autel de Stonehenge
        cv.rect(x - 1, y + 3, 42, 13, 0)
        cv.rect(x, y + 4, 40, 12, 14)
        cv.hline(x, x + 39, y + 4, 15)
        cv.hline(x, x + 39, y + 5, 15)
        cv.hline(x, x + 39, y + 15, 1)
        cv.rect(x + 4, y + 8, 32, 6, 1)
        for i in range(4):
            cv.art(x + 6 + i * 8, y + 9, ("D.D", ".D.", "D.D"))
            amb.append(("rune", x + 7 + i * 8, y + 10, i * 13))
        cv.dith_rect(x, y + 6, 40, 2, 1, 4)
    elif kind == "torch":
        cv.rect(x, y + 9, 4, 2, 14)                          # support
        px(x, y + 9, 15)
        cv.hline(x + 1, x + 2, y + 11, 1)
        cv.rect(x + 1, y + 4, 2, 6, 10)
        cv.vline(x + 2, y + 4, y + 9, 3)
        amb.append(("torch", x, y, (tx * 7 + ty * 3) % 4))
    elif kind == "rack":                                     # râtelier d'armes (armurerie)
        cv.rect(x, y + 4, 26, 2, 10)
        cv.rect(x, y + 14, 26, 2, 10)
        for k, xx in enumerate(range(x + 2, x + 26, 6)):
            cv.vline(xx, y - 6, y + 16, 10)
            if k % 2:
                cv.art(xx - 1, y - 9, (".F.", "FEF", ".E."))
            else:
                cv.art(xx - 2, y - 4, ("EEE..", "EFE..", "EE..."))
        cv.art(x + 9, y + 6, (".EEEE.", "E2B22E", "EBBBBE", "E2B22E", ".E22E.", "..EE.."))
    elif kind == "barrels":                                  # tonneaux du cellier
        for bx, by in ((x, y + 2), (x + 12, y + 2), (x + 6, y - 9)):
            cv.ellipse(bx + 5, by + 6, 5.5, 6.5, 10)
            for k in (2, 9):
                cv.hline(bx + 1, bx + 9, by + k, 14)
            for k in range(13):
                px(bx + 1, by + k, 3) if 1 < k < 12 else None
                px(bx + 9, by + k, 3) if 1 < k < 12 else None
            px(bx + 3, by + 4, 12)
            cv.vline(bx + 5, by + 1, by + 11, 3)
    elif kind == "skeleton":                                 # squelette enchaîné (oubliettes)
        cv.vline(x + 1, y - 10, y, 14)
        cv.vline(x + 9, y - 10, y, 14)
        cv.art(x, y, ("F.......F", "F..FFF..F", ".F.F0F.F.", "..FFFFF..", "...FFF...",
                      "..F.F.F..", "..FFFFF..", "...F.F...", "..FFFFF..", "...F.F...",
                      "...F.F...", "..FF.FF.."))
    elif kind == "mirror":                                   # galerie des glaces
        cv.rect(x - 1, y - 1, 16, 34, 11)
        cv.rect(x, y, 14, 32, 12)
        cv.rect(x + 1, y + 1, 12, 30, 2)
        for k in range(30):
            cv.dith(x + 1 + (k * 12) // 30, y + 1 + k, 9, 16)
            cv.dith(x + 1 + (k * 12) // 30 + 3, y + 1 + k, 9, 8)
        for k in range(1, 13):
            cv.dith(x + k, y + 29, 1, 10)
        cv.hline(x - 1, x + 14, y - 2, 12)
        px(x + 6, y - 3, 11)
        px(x + 7, y - 3, 11)
        amb.append(("glint", x + 1, y + 1, 12, 30, (tx * 41) % 150))
    elif kind == "tapestry":
        w, h = 18, 42
        cv.hline(x - 2, x + w + 1, y, 10)
        px(x - 3, y, 11)
        px(x + w + 2, y, 11)
        cv.rect(x, y + 1, w, h, 11)
        cv.rect(x + 1, y + 2, w - 2, h - 2, 3)
        for k in range(y + 3, y + h, 4):                     # motif en losanges
            for j in range(x + 2, x + w - 2):
                if (j - x + k) % 4 == 0:
                    px(j, k, 4)
        cv.rect(x + 3, y + 8, w - 6, 22, 0)                  # licorne sur fond nuit
        cv.rect(x + 4, y + 9, w - 8, 20, 1)
        cv.art(x + 4, y + 13, ("....F.....", "...FF.....", "..FFF.F...", ".F..FFFF..",
                               "....FFFFF.", "....F.F.F.", "....F.F.F."))
        for k in range(4, w - 4, 3):
            px(x + k, y + 26, 6)
            px(x + k + 1, y + 27, 7)
        for k in range(0, w, 2):                             # franges
            px(x + k, y + h + 1, 11)
            px(x + k, y + h + 2, 12)
    elif kind == "chandelier":
        cx = x + 4
        cv.vline(cx, 8, y + 10, 14)
        for k in range(8, y + 10, 3):
            px(cx, k, 15)
        cv.hline(cx - 10, cx + 10, y + 14, 11)
        cv.hline(cx - 8, cx + 8, y + 15, 12)
        cv.hline(cx - 3, cx + 3, y + 16, 11)
        px(cx, y + 17, 11)
        px(cx, y + 18, 12)
        for dx in (-10, -5, 0, 5, 10):
            cv.vline(cx + dx, y + 11, y + 13, 15)
            amb.append(("candle", cx + dx, y + 10, (dx * 7) % 4))
    elif kind == "throne":                                   # trône royal (P2)
        cv.rect(x, y - 14, 16, 30, 11)
        cv.rect(x + 2, y - 12, 12, 18, 3)
        cv.dith_rect(x + 2, y - 12, 12, 18, 4, 4)
        cv.art(x + 1, y - 18, ("B.B..B..B.B.B.", "BBBBBBBBBBBBBB"))
        cv.rect(x - 2, y + 6, 20, 3, 12)
        cv.rect(x, y + 6, 16, 2, 4)
        cv.rect(x - 2, y + 9, 3, 7, 11)
        cv.rect(x + 15, y + 9, 3, 7, 11)
        cv.vline(x, y - 14, y + 15, 12)
        cv.vline(x + 15, y - 14, y + 15, 10)
        cv.art(x + 5, y - 8, ("..B..", ".B9B.", "BBBBB"))
    elif kind == "menhir_brise":                             # le Menhir brisé (L4)
        menhir(cv, x, y + 15, 22, 9)
        for k in range(4):                                   # cassure en biseau
            cv.hline(x + k * 2, x + 8, y - 8 + k, 0) if k < 3 else None
        for k in range(10):
            cv.hline(x + 12 + k // 3, x + 24 + k // 4, y + 7 + k // 2, 14 if k % 4 else 15)
        cv.hline(x + 12, x + 27, y + 13, 1)
        cv.hline(x + 12, x + 27, y + 14, 0)
    elif kind == "owl":
        pass                                                 # posé par bg_bois (B5)


# ------------------------------------------------------------------------- animation
def draw_ambient(b, amb, tick, tiles=None):
    """Petites animations par-dessus le fond en cache (coût : quelques centaines de pixels)."""
    set_at = b.set_at
    for a in amb:
        k = a[0]
        if k == "star":
            _, x, y, c, ph = a
            t = (tick + ph) % 200
            if t < 6:
                continue                                     # s'éteint brièvement
            set_at((x, y), P[c])
            if 20 <= t < 30:                                 # scintillement en croix
                set_at((x - 1, y), P[1])
                set_at((x + 1, y), P[1])
                set_at((x, y - 1), P[1])
                set_at((x, y + 1), P[1])
                set_at((x, y), P[15])
        elif k == "torch":
            _, x, y, ph = a
            f = FLAME[(tick // 4 + ph) % 4]
            for j, row in enumerate(f):
                for i, ch in enumerate(row):
                    if ch != ".":
                        set_at((x + i, y - 1 + j), P[int(ch, 16)])
            if (tick // 3 + ph) % 5 == 0:                    # étincelle
                set_at((x + 1 + (tick // 7) % 2, y - 3 - (tick // 3) % 3), P[12])
        elif k == "candle":
            _, x, y, ph = a
            f = CANDLE[(tick // 5 + ph) % 4]
            for j, ch in enumerate(f):
                if ch != ".":
                    set_at((x, y - 1 + j), P[int(ch, 16)])
        elif k == "firefly":
            _, x0, y0, ph = a
            t = tick + ph
            x = int(x0 + 6 * math.sin(t * 0.021 + ph))
            y = int(y0 + 4 * math.sin(t * 0.033 + ph * 0.7))
            if (t // 40) % 4 and 0 <= x < PLAY_W and 0 <= y < PLAY_H:
                set_at((x, y), P[11 if (t // 8) % 3 else 7])
        elif k == "owl":
            _, x, y, ph = a
            blink = (tick + ph) % 160 < 8
            set_at((x + 1, y + 3), P[0 if blink else 11])
            set_at((x + 3, y + 3), P[0 if blink else 11])
            set_at((x + 2, y + 4), P[12])
        elif k == "drip":
            _, x, y0, y1, period, ph = a
            t = (tick + ph) % period
            if t < 30:                                       # la goutte grossit
                set_at((x, y0 + 1), P[9 if t > 12 else 2])
            else:
                yy = y0 + 1 + ((t - 30) ** 2) // 18
                if yy < y1 - 1:
                    set_at((x, yy), P[9])
                    set_at((x, yy - 1), P[2])
                elif yy < y1 + 8:                            # éclaboussure
                    sp = (yy - y1 + 2) // 3
                    set_at((x - 1 - sp, y1 - 1 - (1 if sp < 2 else 0)), P[9])
                    set_at((x + 1 + sp, y1 - 1 - (1 if sp < 2 else 0)), P[9])
        elif k == "reed":
            _, x, base, h, lean, ph = a
            sway = math.sin((tick + ph * 7) * 0.05 + x * 0.3)
            for j in range(h):
                dx = int(round(sway * (j / h) * 1.6 + lean * j / (h * 1.5)))
                set_at((x + dx, base - j), P[6 if j % 4 else 10])
            top = base - h
            dx = int(round(sway * 1.6 + lean / 1.5))
            for j in range(3):                               # massette
                set_at((x + dx, top - j), P[3 if j else 10])
            set_at((x + dx, top - 3), P[6])
        elif k == "rune":
            _, x, y, ph = a
            on = (tick // 6 + ph) % 24 < 6
            if on:
                set_at((x, y), P[15])
                set_at((x - 1, y - 1), P[13])
                set_at((x + 1, y + 1), P[13])
        elif k == "glint":
            _, x, y, w, h, ph = a
            t = (tick + ph) % 150
            if t < w + h:
                for j in range(h):
                    i = t - j // 2
                    if 0 <= i < w:
                        set_at((x + i, y + j), P[15])
        elif k == "moonrefl":
            pass                                             # géré par l'eau


# ------------------------------------------------------------------------- eau
class Water:
    """Eau de la rivière : 8 phases pré-rendues sur une bande 160x16, puis découpées
    selon les cases d'eau de la salle (pas de set_at par pixel à chaque frame)."""

    def __init__(self, moon_x=None):
        self.frames = []
        for ph in range(8):
            s = pygame.Surface((PLAY_W, 2 * TILE))
            cv = Canvas(s)
            s.fill(P[1])
            for x in range(PLAY_W):
                w = (x + ph) % 8
                # vaguelettes de surface (2 lignes) qui défilent
                cv.px(x, 0 if w < 4 else 1, 9 if w in (0, 1) else 2)
                if w == 6:
                    cv.px(x, 0, 15)
                cv.px(x, 3 + ((x + ph * 2) % 8) // 4, 2)
                for y in range(5, 2 * TILE):                 # profondeur tramée
                    if (x * 3 + y * 5 + ph * 2) % 17 == 0:
                        cv.px(x, y, 2)
                    elif y > 10:
                        cv.dith(x, y, 0, (y - 10) * 2)
            if moon_x is not None:                           # reflet de lune qui ondule
                for y in range(2, 2 * TILE, 2):
                    half = 3 - y // 6 + (h32(y, ph) % 2)
                    sh = (h32(y, ph, 1) % 3) - 1
                    for x in range(moon_x - half + sh, moon_x + half + sh + 1):
                        cv.px(x, y, 15 if y < 6 and abs(x - moon_x - sh) < half else 9)
            self.frames.append(s)

    def draw(self, b, runs, tick):
        f = self.frames[(tick // 6) % 8]
        for (x, y, w, h, sy) in runs:
            b.blit(f, (x, y), (x, sy, w, h))


def water_runs(tiles):
    """Rectangles d'eau (x, y, w, h, y source dans la bande) groupés par ligne."""
    runs = []
    for cy in range(ROWS):
        cx = 0
        while cx < COLS:
            if tiles[cy][cx] == WATER:
                start = cx
                while cx < COLS and tiles[cy][cx] == WATER:
                    cx += 1
                surface = cy == 0 or tiles[cy - 1][start] != WATER
                runs.append((start * TILE, cy * TILE, (cx - start) * TILE, TILE, 0 if surface else TILE))
            else:
                cx += 1
    return runs
