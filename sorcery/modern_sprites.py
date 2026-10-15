"""Sprites vectoriels « HD » du rendu moderne (sorcier, ennemis, boss, objets, chaudrons...).

Chaque sprite est dessiné en unités u (1 u = 1 pixel logique vertical = V.k pixels écran),
sur une surface sur-échantillonnée puis réduite (anti-aliasing), et mis en cache par
(type, image, orientation, paramètres quantifiés). Le point d'ancrage (ox, oy) est le
décalage en u du coin haut-gauche de la boîte de collision dans le sprite.
"""
import math

import pygame

import modern_gfx as G
from modern_gfx import C, mix, mul

SS = 3                      # facteur de sur-échantillonnage


class Sprite:
    __slots__ = ("surf", "ox", "oy")

    def __init__(self, surf, ox, oy):
        self.surf, self.ox, self.oy = surf, ox, oy


def _make(k, w_u, h_u, ox, oy, fn, flip=False, outline=None):
    """Rend fn(pen) dans une surface w_u x h_u (u) ; ox/oy = origine de la hitbox (u)."""
    W, H = int(math.ceil(w_u * k)), int(math.ceil(h_u * k))

    def draw(big, ss):
        pen = G.Pen(big, k * ss, ox, oy, flip=flip, w_units=0)
        if flip:
            pen.flip = True
            pen.wu = w_u - 2 * ox      # miroir autour du centre de la surface
        fn(pen)
    surf = G.render_ss(W, H, draw, SS, bg=(20, 16, 30))
    return surf


class Pen2(G.Pen):
    pass


# =========================================================================== sorcier
ROBE = ("#4a5cf0", "#2a34a8", "#1a1e60")
ROBE_CAP = ("#3ab070", "#20784a", "#0e3a24")
CAPE = ("#c040d0", "#7a1c9a", "#3a0c50")
CAPE_CAP = ("#e0b040", "#a87018", "#5a3a08")
SKIN = "#f4c8a0"
BEARD = ("#ffffff", "#c8d0e0")
GOLD = ("#ffe070", "#d09a20")


def wizard(p, pose="stand", f=0, sway=0.0, lift=0.0, captive=False, wave=False):
    """Sorcier dans sa hitbox 12x16 u, tourné vers la droite."""
    robe = ROBE_CAP if captive else ROBE
    cape = CAPE_CAP if captive else CAPE
    ph = f / 8.0 * math.tau
    bob = 0.0
    if pose == "stand":
        bob = 0.25 * math.sin(ph)
    elif pose == "walk":
        bob = -0.35 * abs(math.sin(ph))
    tilt = 0.9 if pose == "fly" else 0.0     # le corps penche vers l'avant en vol
    y0 = bob
    # ---- cape (derrière) : part des épaules, flotte vers l'arrière
    sx, sy = 4.0, 5.2 + y0
    stream = 3.0 + 5.0 * max(0.0, sway)                 # longueur vers l'arrière
    drop = 9.5 - 5.0 * max(0.0, sway) - 3.0 * lift
    wav = math.sin(ph * 2) * 0.8
    pts = [(sx + 1.0, sy - 0.8), (sx + 3.6, sy - 0.4),
           (sx + 2.0, sy + 4.0),
           (sx - stream * 0.4, sy + drop * 0.55 + wav * 0.5),
           (sx - stream, sy + drop + wav),
           (sx - stream * 0.75 + 1.2, sy + drop * 0.98 - wav * 0.4),
           (sx - stream * 0.45 + 0.8, sy + drop * 1.05 + wav * 0.6),
           (sx - 0.4, sy + drop * 0.7),
           (sx - 1.2, sy + 1.0)]
    p.poly(C(cape[2]), [(x - 0.3, y + 0.4) for x, y in pts])
    p.poly(C(cape[1]), pts)
    p.poly(C(cape[0]), [pts[0], pts[1], (sx + 1.2, sy + 2.5), (sx - stream * 0.5, sy + drop * 0.6 + wav * 0.5), pts[8]])
    # ---- pieds
    if pose == "walk":
        a = math.sin(ph)
        p.ellipse(C("#3a2418"), 5.2 + a * 1.6, 15.6, 1.5, 0.75)
        p.ellipse(C("#5a3a24"), 7.8 - a * 1.6, 15.6, 1.5, 0.75)
    elif pose == "stand":
        p.ellipse(C("#3a2418"), 4.8, 15.7, 1.5, 0.7)
        p.ellipse(C("#5a3a24"), 8.2, 15.7, 1.5, 0.7)
    # ---- robe
    flare = 1.6 if pose == "fly" else (0.6 if pose == "walk" else 0.2)
    hem = []
    n = 7
    for i in range(n + 1):
        t = i / n
        x = 2.2 - flare + (9.6 + 2 * flare) * t
        y = 15.4 + y0 + 0.45 * math.sin(t * 9 + ph * (2 if pose != "stand" else 1))
        if pose == "fly":
            y -= 1.2 + t * 1.0
        hem.append((x + tilt * (t - 0.5), y))
    body = [(4.0 + tilt, 5.0 + y0), (9.0 + tilt, 5.0 + y0)] + hem[::-1]
    p.poly(C(robe[2]), [(x + 0.3, y + 0.3) for x, y in body])
    p.poly(C(robe[1]), body)
    lit = [(6.5 + tilt, 5.0 + y0), (9.0 + tilt, 5.0 + y0)] + [(x, y) for x, y in hem[::-1] if x > 6.8][:4] + [(7.2, hem[3][1])]
    p.poly(C(robe[0]), lit)
    for (x, y) in ((5.2, 9.5), (8.6, 12.4), (6.0, 13.6), (9.6, 9.0), (4.2, 12.0)):     # étoiles brodées
        p.poly(C(GOLD[0]), G.star_points(x + tilt * 0.5, y + y0, 0.65, 0.28))
    p.rect(C(GOLD[1]), 4.0 + tilt, 8.2 + y0, 5.4, 0.7, 0.3)                                # ceinture
    # ---- bras + baguette
    if captive and wave:
        p.line(C(robe[1]), 8.0, 6.5 + y0, 11.2, 2.5 + y0, 1.8)
        p.circle(C(SKIN), 11.4, 2.0 + y0, 0.9)
        p.line(C(robe[1]), 5.0, 6.5 + y0, 2.0, 3.0 + y0, 1.8)
        p.circle(C(SKIN), 1.8, 2.5 + y0, 0.9)
    elif captive:
        p.line(C(robe[1]), 8.0, 6.5 + y0, 10.2, 9.2 + y0, 1.8)
        p.circle(C(SKIN), 10.4, 9.6 + y0, 0.9)
    else:
        arm_y = 8.0 if pose != "fly" else 6.4
        p.line(C(robe[2]), 7.6 + tilt, 6.2 + y0, 11.0 + tilt, arm_y + y0, 2.0)
        p.line(C(robe[1]), 7.6 + tilt, 6.0 + y0, 11.0 + tilt, arm_y - 0.2 + y0, 1.6)
        p.circle(C(SKIN), 11.3 + tilt, arm_y + y0, 0.9)
        wx0, wy0 = 10.6 + tilt, arm_y + 1.6 + y0
        wx1, wy1 = 14.6 + tilt, arm_y - 3.4 + y0
        p.line(C("#5a3418"), wx0, wy0, wx1, wy1, 0.7)
        p.circle(C("#ffffff"), wx1, wy1, 0.75)
    # ---- tête
    hx, hy = 8.4 + tilt, 3.4 + y0
    p.circle(C(SKIN), hx, hy, 2.1)
    p.circle(C("#e8a888"), hx + 1.9, hy + 0.3, 0.7)                       # nez
    p.circle(C("#2a1a30"), hx + 0.9, hy - 0.3, 0.38)                      # œil
    beard = [(hx - 1.6, hy + 0.6), (hx + 2.2, hy + 0.6), (hx + 1.2, hy + 4.2), (hx + 0.2, hy + 6.4), (hx - 0.6, hy + 3.4)]
    p.poly(C(BEARD[1]), [(x - 0.2, y + 0.2) for x, y in beard])
    p.poly(C(BEARD[0]), beard)
    # ---- chapeau pointu (pointe qui fouette en arrière)
    hat_c = robe
    tipx = hx - 3.5 - 2.0 * max(0.0, sway) + 0.6 * math.sin(ph)
    tipy = hy - 9.0 + 1.2 * max(0.0, sway) + lift * 1.0
    cone = [(hx - 3.0, hy - 1.2), (hx + 2.6, hy - 1.4), (hx + 0.4, hy - 5.0), (tipx, tipy), (hx - 1.6, hy - 4.6)]
    p.poly(C(hat_c[2]), [(x + 0.2, y + 0.2) for x, y in cone])
    p.poly(C(hat_c[1]), cone)
    p.poly(C(hat_c[0]), [cone[1], cone[2], cone[3], (hx - 0.3, hy - 3.5)])
    p.ellipse(C(hat_c[2]), hx - 0.1, hy - 1.15, 4.0, 0.95)
    p.ellipse(C(hat_c[1]), hx - 0.1, hy - 1.35, 3.8, 0.75)
    p.line(C(GOLD[1]), hx - 2.5, hy - 2.0, hx + 2.2, hy - 2.2, 0.6)
    p.poly(C(GOLD[0]), G.star_points(hx - 0.6, hy - 4.4, 0.85, 0.35))


# =========================================================================== ennemis
def skull(p, f=0, **kw):
    """Crâne flottant (hitbox 14x8 u)."""
    ph = f / 8 * math.tau
    cx, cy = 7, 3.7
    jaw = 0.6 + 0.6 * (0.5 + 0.5 * math.sin(ph * 2))
    # flamme spectrale derrière
    fl = [(cx - 3.8, cy + 1), (cx - 6.5 - math.sin(ph) * 0.8, cy - 1.5), (cx - 5.2, cy + 0.2), (cx - 7.5, cy + 2.6 + math.sin(ph * 2) * 0.5), (cx - 3.5, cy + 3)]
    p.poly(C("#2a8ad0"), fl)
    p.poly(C("#80e0ff"), [(x * 0.5 + cx * 0.5 - 1.2, y) for x, y in fl])
    p.ellipse(C("#8a8478"), cx + 0.3, cy + 0.3, 4.3, 3.9)
    p.ellipse(C("#efe8d8"), cx, cy, 4.2, 3.8)
    p.ellipse(C("#ffffff"), cx - 1.2, cy - 1.6, 2.0, 1.2)
    p.rect(C("#d8d0c0"), cx - 2.2, cy + 2.6 + jaw * 0.5, 5.0, 1.6, 0.5)
    for i in range(4):
        p.rect(C("#ffffff"), cx - 1.9 + i * 1.15, cy + 2.6, 0.8, 0.9 + jaw * 0.3, 0.2)
    p.ellipse(C("#1a1020"), cx + 0.3, cy + 0.2, 1.3, 1.25)
    p.ellipse(C("#1a1020"), cx + 3.0, cy + 0.2, 1.0, 1.25)
    p.circle(C("#ff4060"), cx + 0.5, cy + 0.2, 0.45)
    p.circle(C("#ff4060"), cx + 3.0, cy + 0.2, 0.4)
    p.poly(C("#3a2a30"), [(cx + 1.6, cy + 1.3), (cx + 2.2, cy + 2.3), (cx + 1.1, cy + 2.3)])


def ghost(p, f=0, **kw):
    ph = f / 8 * math.tau
    cx = 8
    pts = []
    for i in range(13):
        a = math.pi + i / 12 * math.pi
        pts.append((cx + 6.5 * math.cos(a), 5.0 + 5.0 * math.sin(a)))
    tail = []
    for i in range(9):
        t = i / 8
        x = cx + 6.5 - 13 * t
        y = 9.6 + 0.9 * math.sin(t * 10 + ph * 2)
        tail.append((x, y))
    body = pts + tail
    p.poly((140, 200, 255, 120), [(x, y + 0.4) for x, y in body])
    p.poly((225, 240, 255, 225), body)
    p.ellipse((255, 255, 255, 255), cx - 1.5, 2.6, 3.2, 1.6)
    p.ellipse(C("#14142a"), cx + 1.6, 4.4, 1.0, 1.4)
    p.ellipse(C("#14142a"), cx + 4.2, 4.4, 0.9, 1.4)
    p.ellipse(C("#14142a"), cx + 3.0, 7.0, 1.0, 0.7 + 0.3 * math.sin(ph))
    p.ellipse((120, 180, 255, 110), cx - 4.5, 6.5, 1.0, 1.0)


def bat(p, f=0, **kw):
    ph = f / 8 * math.tau
    flap = math.sin(ph)
    cx, cy = 8, 3.0
    wing_y = -2.6 * flap
    for side in (-1, 1):
        tip = (cx + side * 8.0, cy + wing_y - 0.6)
        pts = [(cx + side * 1.2, cy - 0.4), (cx + side * 4.0, cy + wing_y * 0.7 - 1.0), tip,
               (cx + side * 6.6, cy + wing_y * 0.6 + 1.6), (cx + side * 5.0, cy + wing_y * 0.4 + 1.0),
               (cx + side * 3.6, cy + wing_y * 0.3 + 2.4), (cx + side * 2.2, cy + 1.6), (cx + side * 1.2, cy + 1.6)]
        p.poly(C("#3a1a4a"), pts)
        p.lines(C("#6a3a8a"), [pts[0], pts[1], pts[2]], 0.4)
    p.ellipse(C("#2a1236"), cx, cy + 0.9, 2.0, 2.2)
    p.poly(C("#2a1236"), [(cx - 1.6, cy - 0.6), (cx - 1.2, cy - 2.6), (cx - 0.4, cy - 0.9)])
    p.poly(C("#2a1236"), [(cx + 1.6, cy - 0.6), (cx + 1.2, cy - 2.6), (cx + 0.4, cy - 0.9)])
    p.circle(C("#ff3040"), cx - 0.7, cy + 0.4, 0.4)
    p.circle(C("#ff3040"), cx + 0.7, cy + 0.4, 0.4)


def spider(p, f=0, **kw):
    ph = f / 8 * math.tau
    cx, cy = 8, 3.6
    for side in (-1, 1):
        for i in range(4):
            a = (i - 1.5) * 0.45 + math.sin(ph + i) * 0.15
            kx, ky = cx + side * (3.2 + i * 0.3), cy - 1.6 + i * 0.6
            ex, ey = cx + side * (6.5 + math.cos(a) * 0.8), cy + 2.6 + i * 0.3 + math.sin(a) * 0.6
            p.lines(C("#1a1020"), [(cx + side * 1.2, cy + 0.2 + i * 0.3), (kx, ky), (ex, ey)], 0.6)
    p.ellipse(C("#24142c"), cx, cy + 0.6, 3.0, 2.6)
    p.ellipse(C("#4a2a5a"), cx - 0.8, cy - 0.2, 1.2, 0.8)
    p.ellipse(C("#24142c"), cx, cy - 1.8, 1.8, 1.5)
    for dx in (-0.8, -0.2, 0.4, 1.0):
        p.circle(C("#ff3050"), cx + dx, cy - 2.0, 0.3)
    p.poly(C("#c03030"), G.star_points(cx, cy + 1.0, 0.9, 0.35, 4, 0))


def fish(p, f=0, **kw):
    ph = f / 8 * math.tau
    cx, cy = 8, 3.0
    tail = math.sin(ph * 2) * 1.2
    p.poly(C("#c04020"), [(cx - 5, cy), (cx - 8, cy - 2.5 + tail * 0.4), (cx - 7.2, cy), (cx - 8, cy + 2.5 + tail * 0.4)])
    p.ellipse(C("#1a5a6a"), cx, cy, 5.6, 2.8)
    p.ellipse(C("#40b0b0"), cx + 0.2, cy - 0.6, 5.0, 1.9)
    p.ellipse(C("#e0f0e0"), cx + 0.5, cy + 1.3, 4.0, 1.0)
    p.poly(C("#e05030"), [(cx - 2, cy - 2.4), (cx + 1.5, cy - 4.0), (cx + 2.0, cy - 2.4)])
    p.circle(C("#ffffff"), cx + 3.4, cy - 0.6, 0.9)
    p.circle(C("#101010"), cx + 3.6, cy - 0.6, 0.45)
    for i in range(3):
        p.poly(C("#ffffff"), [(cx + 4.0 + i * 0.5, cy + 0.9), (cx + 4.3 + i * 0.5, cy + 1.7), (cx + 4.6 + i * 0.5, cy + 0.9)])


def guard(p, f=0, **kw):
    ph = f / 8 * math.tau
    a = math.sin(ph)
    # jambes
    p.line(C("#3a3a48"), 5.5, 10, 5.5 + a * 1.2, 14.6, 1.6)
    p.line(C("#4a4a5a"), 8.5, 10, 8.5 - a * 1.2, 14.6, 1.6)
    p.ellipse(C("#2a2a30"), 5.8 + a * 1.2, 14.9, 1.3, 0.6)
    p.ellipse(C("#2a2a30"), 8.8 - a * 1.2, 14.9, 1.3, 0.6)
    # tabard + armure
    p.rect(C("#7a8090"), 3.8, 4.8, 6.6, 6.0, 1.4)
    p.poly(C("#a01830"), [(5.0, 5.2), (9.4, 5.2), (9.8, 11.4), (7.2, 12.4), (4.6, 11.4)])
    p.poly(C("#ffd060"), G.star_points(7.2, 8.2, 1.2, 0.5))
    # lance
    p.line(C("#6a4a2a"), 11.5, -1.0, 11.5, 14.5, 0.6)
    p.poly(C("#d0d8e0"), [(11.5, -3.6), (12.4, -1.0), (10.6, -1.0)])
    p.circle(C("#c8ccd8"), 11.0, 8.0, 0.9)
    # casque
    p.circle(C("#8a90a0"), 7.4, 2.6, 2.4)
    p.rect(C("#5a6070"), 5.0, 2.0, 4.8, 2.6, 0.6)
    p.rect(C("#14141c"), 7.4, 2.6, 2.4, 0.5)
    p.poly(C("#d02040"), [(6.4, 0.6), (5.0, -1.8), (3.0, -0.2 + a * 0.3), (5.6, 0.9)])
    p.ellipse(C("#c8d0dc"), 6.6, 1.4, 1.0, 0.5)


def goule(p, f=0, **kw):
    ph = f / 8 * math.tau
    a = math.sin(ph)
    p.line(C("#3a4a3a"), 5.5, 9.5, 5.0 + a, 13.8, 1.4)
    p.line(C("#4a5a48"), 8.0, 9.5, 8.6 - a, 13.8, 1.4)
    body = [(4.0, 4.4), (9.2, 3.2), (10.2, 6.8), (9.4, 10.6), (4.4, 10.6), (3.4, 7.0)]
    p.poly(C("#4a5a44"), body)
    p.poly(C("#6a7a5a"), [(5.0, 4.4), (9.0, 3.6), (9.6, 6.4), (6.0, 7.0)])
    p.poly(C("#2a2a30"), [(3.6, 8.0), (10.0, 8.0), (10.6, 11.2), (9.0, 10.4), (7.6, 11.8), (6.0, 10.6), (4.2, 11.6)])
    p.line(C("#5a6a50"), 9.0, 5.0, 12.6, 7.4 + a * 0.6, 1.2)
    for i in range(3):
        p.line(C("#e8e0c8"), 12.6, 7.4 + a * 0.6, 13.6, 7.0 + i * 0.7 + a * 0.6, 0.3)
    p.circle(C("#5a6a50"), 9.0, 2.6, 2.2)
    p.circle(C("#e0ff40"), 10.0, 2.3, 0.5)
    p.circle(C("#e0ff40"), 8.6, 2.3, 0.45)
    p.poly(C("#1a1a14"), [(8.6, 3.6), (10.8, 3.4), (10.0, 4.4)])


def wisp(p, f=0, **kw):
    ph = f / 8 * math.tau
    cx, cy = 6, 4.2
    fl = []
    for i in range(16):
        a = i / 16 * math.tau
        r = 2.8 + (1.6 * max(0, -math.sin(a)) ** 2) * (1 + 0.3 * math.sin(ph * 2 + i))
        fl.append((cx + r * math.cos(a) * 0.8, cy + r * math.sin(a) - (1.2 * max(0, -math.sin(a)))))
    p.poly(C("#2080ff"), fl)
    p.poly(C("#60e0ff"), [(cx + (x - cx) * 0.7, cy + (y - cy) * 0.7 + 0.4) for x, y in fl])
    p.circle(C("#e8ffff"), cx, cy + 0.6, 1.5)
    p.circle(C("#103060"), cx - 0.6, cy + 0.4, 0.35)
    p.circle(C("#103060"), cx + 0.7, cy + 0.4, 0.35)


def gargouille(p, f=0, dive=False, **kw):
    ph = f / 8 * math.tau
    cx, cy = 8, 4.4
    flap = math.sin(ph) if dive else 0.0
    for side in (-1, 1):
        wy = -1.0 - 1.8 * flap if dive else -0.2
        span = 7.6 if dive else 5.2
        pts = [(cx + side * 1.6, cy - 1.0), (cx + side * span, cy + wy - 1.4), (cx + side * (span - 0.6), cy + wy + 1.0),
               (cx + side * (span - 2.4), cy + wy + 0.4), (cx + side * (span - 3.2), cy + 1.8), (cx + side * 1.6, cy + 1.4)]
        p.poly(C("#4a4a56"), pts)
        p.lines(C("#7a7a88"), pts[:3], 0.35)
    p.ellipse(C("#5a5a68"), cx, cy + 0.6, 2.6, 3.0)
    p.ellipse(C("#7a7a8a"), cx - 0.6, cy - 0.2, 1.2, 1.6)
    p.circle(C("#5a5a68"), cx + 0.4, cy - 2.4, 2.0)
    p.poly(C("#3a3a46"), [(cx - 1.0, cy - 3.6), (cx - 1.8, cy - 5.6), (cx - 0.1, cy - 4.0)])
    p.poly(C("#3a3a46"), [(cx + 1.6, cy - 3.6), (cx + 2.4, cy - 5.6), (cx + 0.9, cy - 4.0)])
    p.circle(C("#ff6020"), cx - 0.3, cy - 2.4, 0.45)
    p.circle(C("#ff6020"), cx + 1.2, cy - 2.4, 0.45)
    p.poly(C("#e8e0d0"), [(cx - 0.2, cy - 1.2), (cx + 0.2, cy - 0.4), (cx + 0.6, cy - 1.2)])
    p.line(C("#4a4a56"), cx - 1.6, cy + 3.4, cx - 1.8, cy + 4.0, 0.7)
    p.line(C("#4a4a56"), cx + 1.6, cy + 3.4, cx + 1.8, cy + 4.0, 0.7)


def bulle(p, f=0, **kw):
    ph = f / 8 * math.tau
    cx, cy = 6, 3.0
    pts = []
    for i in range(14):
        a = i / 14 * math.tau
        r = 3.0 + 0.4 * math.sin(a * 3 + ph * 2)
        pts.append((cx + r * math.cos(a) * 1.4, cy + r * math.sin(a)))
    p.poly(C("#a01808"), pts)
    p.poly(C("#ff6010"), [(cx + (x - cx) * 0.75, cy + (y - cy) * 0.75) for x, y in pts])
    p.ellipse(C("#ffe060"), cx - 0.6, cy - 0.6, 1.8, 1.1)
    p.circle(C("#2a0a04"), cx - 1.4, cy + 0.3, 0.4)
    p.circle(C("#2a0a04"), cx + 1.4, cy + 0.3, 0.4)


def necro(p, f=0, **kw):
    """Nécromancien (hitbox 40x40 u)."""
    ph = f / 8 * math.tau
    cx = 20
    # robe déchiquetée
    hem = []
    for i in range(13):
        t = i / 12
        x = cx - 15 + 30 * t
        y = 39 + (2.2 if i % 2 else -0.6) + math.sin(t * 8 + ph) * 0.8
        hem.append((x, y))
    robe = [(cx - 6, 9), (cx + 6, 9)] + hem[::-1]
    p.poly(C("#140818"), [(x + 0.6, y + 0.4) for x, y in robe])
    p.poly(C("#2a1038"), robe)
    p.poly(C("#4a1c60"), [(cx + 1, 10), (cx + 6, 9), (cx + 15, 38), (cx + 5, 38)])
    p.poly(C("#1a0a24"), [(cx - 1.4, 12), (cx + 1.4, 12), (cx + 2.4, 38), (cx - 2.4, 38)])
    for i in range(5):                                         # runes de la robe
        p.circle(C("#ff3070"), cx + (i - 2) * 2.8, 30 + (i % 2) * 2, 0.5)
    # bras décharnés + bâton
    p.line(C("#2a1038"), cx - 5, 12, cx - 12, 20, 3.4)
    p.circle(C("#c8c0b0"), cx - 12.4, 20.8, 1.3)
    p.line(C("#3a2a20"), cx - 13, 6, cx - 12, 39, 1.0)
    p.circle(C("#30ff90"), cx - 13.1, 4.8, 2.2)
    p.circle(C("#c0ffe0"), cx - 13.6, 4.2, 0.9)
    p.line(C("#2a1038"), cx + 5, 12, cx + 11, 17 + math.sin(ph) * 1.0, 3.4)
    for i in range(4):
        p.line(C("#c8c0b0"), cx + 11, 17 + math.sin(ph), cx + 13, 15.5 + i * 1.1 + math.sin(ph), 0.5)
    # capuche + crâne
    hood = [(cx - 7.5, 12), (cx - 6.5, 3.5), (cx - 2, -0.5), (cx + 3, -0.6), (cx + 7, 3.5), (cx + 7.5, 12), (cx + 3, 10), (cx - 3, 10)]
    p.poly(C("#1a0a24"), hood)
    p.poly(C("#3a1650"), [hood[2], hood[3], hood[4], (cx + 4.5, 6), (cx - 1, 1)])
    p.ellipse(C("#0a040e"), cx, 6.8, 4.2, 4.6)
    p.ellipse(C("#d8d0c0"), cx, 6.8, 3.0, 3.4)
    p.rect(C("#c8c0b0"), cx - 1.8, 9.0, 3.6, 1.6, 0.4)
    p.ellipse(C("#0a040e"), cx - 1.2, 6.4, 0.9, 1.0)
    p.ellipse(C("#0a040e"), cx + 1.2, 6.4, 0.9, 1.0)
    p.circle(C("#ff2040"), cx - 1.2, 6.5, 0.5)
    p.circle(C("#ff2040"), cx + 1.2, 6.5, 0.5)


# =========================================================================== objets
def item(p, oid):
    """Icône d'objet dans une boîte 14x10 u (centre 7,5)."""
    cx, cy = 7, 5
    gold, gold2 = C("#ffd860"), C("#b8801c")
    steel, steel2 = C("#e8eef8"), C("#8a94a8")
    wood = C("#8a5a30")
    if oid == "epee":
        p.line(steel2, cx - 3.6, cy + 3.6, cx + 3.4, cy - 3.6, 1.6)
        p.line(steel, cx - 3.2, cy + 3.0, cx + 3.4, cy - 3.6, 0.8)
        p.line(gold2, cx - 3.8, cy + 1.4, cx - 1.6, cy + 3.8, 1.2)
        p.line(C("#6a3a20"), cx - 3.4, cy + 3.4, cx - 5.0, cy + 5.0, 1.0)
        p.circle(C("#e03040"), cx - 5.2, cy + 5.0, 0.9)
    elif oid == "hache":
        p.line(wood, cx - 2.5, cy + 5, cx + 1.5, cy - 4.5, 1.1)
        p.poly(steel2, [(cx, cy - 4), (cx + 4.8, cy - 4.6), (cx + 5.6, cy - 1.0), (cx + 4.2, cy + 1.6), (cx + 0.6, cy - 0.6)])
        p.poly(steel, [(cx + 4.6, cy - 4.4), (cx + 5.6, cy - 1.0), (cx + 4.2, cy + 1.6), (cx + 3.6, cy - 1.0)])
    elif oid == "croix":
        p.rect(gold2, cx - 0.9, cy - 4.6, 2.2, 9.6, 0.5)
        p.rect(gold2, cx - 3.4, cy - 2.4, 7.2, 2.0, 0.5)
        p.rect(gold, cx - 0.9, cy - 4.6, 1.2, 9.6, 0.5)
        p.circle(C("#40a0ff"), cx + 0.2, cy - 1.4, 0.9)
    elif oid in ("torche", "cierge"):
        if oid == "torche":
            p.line(wood, cx, cy + 5, cx + 0.6, cy - 1.5, 1.4)
            p.rect(C("#5a4030"), cx - 1.0, cy - 2.4, 2.6, 1.6, 0.4)
        else:
            p.rect(C("#f0e8d8"), cx - 1.2, cy - 1.6, 2.4, 6.4, 0.6)
            p.rect(C("#c8b8a0"), cx - 2.4, cy + 4.0, 4.8, 1.0, 0.4)
        p.poly(C("#ff7020"), [(cx - 1.6, cy - 2.2), (cx + 0.2, cy - 6.8), (cx + 1.8, cy - 2.2)])
        p.poly(C("#ffe080"), [(cx - 0.7, cy - 2.2), (cx + 0.2, cy - 4.8), (cx + 1.0, cy - 2.2)])
    elif oid in ("cle", "cle_doree", "cle_os"):
        col, col2 = {"cle": (steel2, C("#5a6070")), "cle_doree": (gold, gold2), "cle_os": (C("#efe6d0"), C("#a89c88"))}[oid]
        p.circle(col2, cx - 3.0, cy, 2.4)
        p.circle(col, cx - 3.0, cy, 2.0)
        p.circle(C("#141018"), cx - 3.0, cy, 0.9)
        p.line(col, cx - 1.0, cy, cx + 5.0, cy, 1.1)
        p.rect(col, cx + 2.6, cy, 0.9, 2.0)
        p.rect(col, cx + 4.2, cy, 0.9, 2.6)
    elif oid in ("parchemin", "grimoire", "livre"):
        if oid == "parchemin":
            p.rect(C("#e8d4a0"), cx - 4, cy - 3.2, 8, 6.4, 0.6)
            p.circle(C("#c8a870"), cx - 4, cy - 3.0, 1.0)
            p.circle(C("#c8a870"), cx + 4, cy + 3.0, 1.0)
            for i in range(4):
                p.line(C("#8a6a40"), cx - 2.6, cy - 1.6 + i * 1.1, cx + 2.4 - (i % 2), cy - 1.6 + i * 1.1, 0.35)
            p.circle(C("#c02020"), cx + 2.2, cy + 2.2, 0.9)
        else:
            cov = C("#3a1a5a") if oid == "grimoire" else C("#a02028")
            p.rect(C("#f0e8d0"), cx - 3.4, cy - 3.8, 7.4, 8.4, 0.6)
            p.rect(cov, cx - 4.0, cy - 4.4, 7.4, 8.4, 0.8)
            p.rect(gold, cx - 4.0, cy - 4.4, 7.4, 8.4, 0.8, width=0.4)
            if oid == "grimoire":
                p.poly(C("#ff60a0"), G.star_points(cx - 0.3, cy - 0.2, 2.2, 0.9))
            else:
                p.circle(gold, cx - 0.3, cy - 0.2, 1.2)
    elif oid == "amulette":
        p.lines(gold2, [(cx - 3, cy - 4.6), (cx - 1.6, cy - 1.0), (cx, cy + 0.6), (cx + 1.6, cy - 1.0), (cx + 3, cy - 4.6)], 0.4)
        p.poly(gold, [(cx, cy - 0.4), (cx + 2.4, cy + 2.0), (cx, cy + 4.6), (cx - 2.4, cy + 2.0)])
        p.poly(C("#30a0ff"), [(cx, cy + 0.6), (cx + 1.4, cy + 2.0), (cx, cy + 3.6), (cx - 1.4, cy + 2.0)])
    elif oid == "harpe":
        p.lines(gold2, [(cx - 3, cy + 4.5), (cx - 3.5, cy - 2), (cx - 1, cy - 4.5), (cx + 3.5, cy - 3), (cx + 2.5, cy + 4.5), (cx - 3, cy + 4.5)], 1.0)
        for i in range(5):
            x = cx - 2.4 + i * 1.1
            p.line(C("#f0f0ff"), x, cy - 3.4 + i * 0.25, x, cy + 4.0, 0.25)
    elif oid == "bouclier":
        sh = [(cx - 4, cy - 4.4), (cx + 4, cy - 4.4), (cx + 3.6, cy + 1.6), (cx, cy + 4.8), (cx - 3.6, cy + 1.6)]
        p.poly(steel2, sh)
        p.poly(C("#2a50c0"), [(x * 0.82 + cx * 0.18, y * 0.82 + cy * 0.18 - 0.2) for x, y in sh])
        p.poly(gold, G.star_points(cx, cy - 0.6, 1.8, 0.75))
    elif oid == "anneau":
        p.circle(gold2, cx, cy + 1, 3.2)
        p.circle(gold, cx, cy + 1, 2.8)
        p.circle((0, 0, 0, 0), cx, cy + 1, 1.9)
        p.poly(C("#ff3050"), [(cx, cy - 4.0), (cx + 1.5, cy - 2.2), (cx, cy - 1.0), (cx - 1.5, cy - 2.2)])
    elif oid == "lanterne":
        p.rect(C("#4a3a2a"), cx - 2.6, cy - 3.2, 5.2, 7.4, 0.8)
        p.rect(C("#ffd060"), cx - 1.8, cy - 2.2, 3.6, 5.4, 0.6)
        p.circle(C("#fff6c0"), cx, cy + 0.4, 1.0)
        p.circle(C("#4a3a2a"), cx, cy - 4.0, 1.0, width=0.4)
    elif oid == "couronne":
        pts = [(cx - 4.4, cy + 3), (cx - 4.4, cy - 2.4), (cx - 2.2, cy - 0.4), (cx, cy - 3.6), (cx + 2.2, cy - 0.4), (cx + 4.4, cy - 2.4), (cx + 4.4, cy + 3)]
        p.poly(gold2, [(x, y + 0.4) for x, y in pts])
        p.poly(gold, pts)
        for i, col in enumerate(("#ff3050", "#30a0ff", "#40e080")):
            p.circle(C(col), cx - 2.4 + i * 2.4, cy + 1.4, 0.7)
    elif oid == "coupe":
        p.poly(gold, [(cx - 3.6, cy - 4), (cx + 3.6, cy - 4), (cx + 2.4, cy - 0.4), (cx, cy + 0.6), (cx - 2.4, cy - 0.4)])
        p.rect(gold2, cx - 0.5, cy + 0.4, 1.0, 3.0)
        p.ellipse(gold2, cx, cy + 3.8, 2.6, 0.8)
        p.ellipse(C("#c02040"), cx, cy - 3.6, 3.0, 0.6)
    elif oid == "sceptre":
        p.line(gold2, cx - 3.2, cy + 4.8, cx + 2.0, cy - 2.2, 1.0)
        p.line(gold, cx - 3.4, cy + 4.4, cx + 2.0, cy - 2.4, 0.5)
        p.circle(C("#a040ff"), cx + 2.6, cy - 3.0, 1.8)
        p.circle(C("#e8c0ff"), cx + 2.1, cy - 3.6, 0.6)
    elif oid == "orbe":
        p.ellipse(gold2, cx, cy + 3.8, 3.0, 1.0)
        p.circle(C("#2080c0"), cx, cy, 3.4)
        p.circle(C("#60d0ff"), cx - 0.5, cy - 0.4, 2.6)
        p.circle(C("#ffffff"), cx - 1.4, cy - 1.4, 0.8)
    elif oid == "talisman":
        p.poly(C("#2a6a4a"), [(cx - 3, cy - 4), (cx + 3, cy - 3.4), (cx + 3.6, cy + 3.6), (cx - 3.4, cy + 4.2)])
        p.lines(C("#80ffb0"), [(cx - 1, cy - 2), (cx + 1, cy), (cx - 1, cy + 2), (cx + 1.4, cy + 2.6)], 0.5)
    elif oid in ("potion", "coeur"):
        c1, c2 = (C("#ff4060"), C("#a01030")) if oid == "potion" else (C("#ff60a0"), C("#a02060"))
        pts = []
        for i in range(32):
            t = i / 32 * math.tau
            x = 16 * math.sin(t) ** 3
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            pts.append((cx + x * 0.27, cy + y * 0.27 + 0.4))
        p.poly(c2, [(x, y + 0.4) for x, y in pts])
        p.poly(c1, pts)
        p.ellipse(C("#ffffff"), cx - 1.6, cy - 1.6, 1.0, 0.7)
        if oid == "coeur":
            p.poly(C("#ffd060"), [(cx - 1.2, cy - 3.4), (cx, cy - 6.2), (cx + 1.2, cy - 3.4)])
    elif oid == "eclat":
        p.circle(C("#a0e8ff"), cx, cy, 4.0)
        p.circle((0, 0, 0, 0), cx + 1.8, cy - 1.0, 3.4)
        p.poly(C("#ffffff"), G.star_points(cx + 2.6, cy + 2.6, 1.2, 0.4, 4, 0))
    elif oid == "faux":
        p.line(wood, cx - 3.5, cy + 5, cx + 1.5, cy - 4.5, 1.0)
        p.poly(steel, [(cx + 1.5, cy - 4.5), (cx - 5, cy - 5.2), (cx - 6, cy - 3.0), (cx - 2, cy - 3.8), (cx + 1.0, cy - 3.2)])
    elif oid == "eau_benite":
        p.ellipse(C("#c8e0f0"), cx, cy + 1.6, 3.4, 3.2)
        p.ellipse(C("#4090ff"), cx, cy + 2.2, 2.8, 2.4)
        p.rect(C("#c8e0f0"), cx - 1.0, cy - 4.0, 2.0, 3.0)
        p.rect(C("#8a5a30"), cx - 1.2, cy - 4.8, 2.4, 1.2, 0.3)
        p.line(C("#ffffff"), cx, cy + 0.6, cx, cy + 3.6, 0.4)
        p.line(C("#ffffff"), cx - 1.0, cy + 1.6, cx + 1.0, cy + 1.6, 0.4)
    elif oid == "cloche":
        p.poly(C("#c8d0e0"), [(cx - 1.6, cy - 4), (cx + 1.6, cy - 4), (cx + 2.6, cy + 1), (cx + 4, cy + 3), (cx - 4, cy + 3), (cx - 2.6, cy + 1)])
        p.poly(C("#ffffff"), [(cx - 1.2, cy - 3.4), (cx - 0.2, cy - 3.4), (cx - 1.2, cy + 2.4), (cx - 2.4, cy + 2.4)])
        p.circle(C("#8a94a8"), cx, cy + 3.8, 0.9)
    elif oid == "marteau":
        p.line(wood, cx - 3, cy + 5, cx + 1, cy - 2.5, 1.1)
        p.rect(steel2, cx - 2.2, cy - 5.4, 6.4, 3.6, 0.6)
        p.rect(steel, cx - 2.2, cy - 5.4, 6.4, 1.2, 0.4)
    elif oid == "pentacle":
        p.circle(gold2, cx, cy, 4.4)
        p.circle(C("#3a1a08"), cx, cy, 3.7)
        pts = [(cx + 3.4 * math.cos(-math.pi / 2 + i * 4 * math.pi / 5), cy + 3.4 * math.sin(-math.pi / 2 + i * 4 * math.pi / 5)) for i in range(5)]
        p.lines(gold, pts + [pts[0]], 0.5)
    else:
        p.circle(gold, cx, cy, 3)


# =========================================================================== mobilier
def cauldron(p, full=True, **kw):
    """Chaudron (hitbox 32x12 u)."""
    liq = C("#40ff80") if full else C("#ff3040")
    p.line(C("#2a2a30"), 6, 9, 3.6, 12.4, 1.4)
    p.line(C("#2a2a30"), 26, 9, 28.4, 12.4, 1.4)
    p.ellipse(C("#16161c"), 16, 6.6, 13.5, 6.0)
    p.ellipse(C("#2e2e38"), 15.0, 5.8, 11.5, 4.6)
    p.ellipse(C("#3e3e4a"), 11.0, 5.0, 4.0, 2.0)
    p.ellipse(C("#24242c"), 16, 1.6, 14.0, 2.0)
    p.ellipse(mul(liq, 0.55), 16, 1.6, 12.4, 1.4)
    p.ellipse(liq, 16, 1.4, 11.0, 1.0)


def crucible(p, **kw):
    """Creuset de la forge (hitbox 32x12 u, s'étend vers le haut)."""
    p.rect(C("#2a2224"), 1, -3, 30, 15, 2)
    p.rect(C("#3e3236"), 2, -3, 28, 3, 1.5)
    for i in range(5):
        p.rect(C("#4a3c3e"), 2.4 + i * 5.6, 1.4, 4.8, 3.2, 0.8)
        p.rect(C("#3a2e30"), 5.2 + i * 5.6 - 2.6, 5.6, 4.8, 3.2, 0.8)
    p.ellipse(C("#100a0a"), 16, -2.6, 11, 1.6)
    p.ellipse(C("#ff8020"), 16, -2.6, 9.5, 1.1)
    p.rect(C("#120a0a"), 11, 6, 10, 6, 3)
    p.rect(C("#ff5010"), 12.5, 8, 7, 4, 2)


def cage(p, **kw):
    """Cage de fer (hitbox 32x24 u), sans le captif."""
    bar = C("#9aa0b0")
    bar2 = C("#4a4e5c")
    p.ellipse(bar2, 16, 1.8, 15, 3.0)
    p.ellipse(bar, 16, 1.4, 14, 2.4, width=0.8)
    p.circle(bar, 16, -1.6, 1.4, width=0.6)
    for i in range(8):
        x = 2.0 + i * 4.0
        p.line(bar2, x + 0.3, 2.2, x + 0.3, 21.0, 0.9)
        p.line(bar, x, 2.0, x, 21.0, 0.7)
    p.rect(bar2, 1, 11.4, 30, 1.2, 0.4)
    p.rect(C("#5a3a20"), 0, 20.8, 32, 3.2, 0.8)
    p.rect(C("#8a5a30"), 0, 20.8, 32, 1.0, 0.5)
    p.rect(C("#ffc040"), 14.4, 12.6, 3.2, 3.0, 0.6)
    p.circle(C("#3a2a10"), 16, 14.0, 0.5)


# =========================================================================== bibliothèque
class Library:
    """Cache des sprites rendus pour une échelle donnée."""

    def __init__(self, k):
        self.k = k
        self.cache = {}

    def get(self, key, w_u, h_u, ox, oy, fn, flip=False):
        ck = (key, flip)
        s = self.cache.get(ck)
        if s is None:
            surf = _make(self.k, w_u, h_u, ox, oy, fn, flip)
            s = Sprite(surf, ox, oy)
            if len(self.cache) > 1500:
                self.cache.clear()
            self.cache[ck] = s
        return s

    # -------- sorcier
    def wizard(self, pose, f, sway, lift, flip, captive=False, wave=False, white=False):
        sq = round(max(-1.0, min(1.0, sway)) * 4) / 4
        lq = round(max(-1.0, min(1.0, lift)) * 2) / 2
        key = ("wiz", pose, f % 8, sq, lq, captive, wave)
        s = self.get(key, 30, 30, 9, 11,
                     lambda p: wizard(p, pose, f % 8, sq, lq, captive, wave), flip)
        if white:
            wk = ("white",) + key + (flip,)
            w = self.cache.get(wk)
            if w is None:
                w = Sprite(G.tinted(s.surf, (255, 255, 255)), s.ox, s.oy)
                self.cache[wk] = w
            return w
        return s

    # -------- ennemis : (largeur, hauteur, marge) en u
    ENEMY = {
        "skull": (skull, 14, 8), "ghost": (ghost, 16, 10), "bat": (bat, 16, 6), "spider": (spider, 16, 7),
        "fish": (fish, 16, 6), "guard": (guard, 14, 15), "goule": (goule, 14, 14), "wisp": (wisp, 12, 7),
        "gargouille": (gargouille, 16, 8), "bulle": (bulle, 12, 6),
    }

    def enemy(self, kind, f, flip, **params):
        fn, w, h = self.ENEMY[kind]
        m = 6
        key = ("en", kind, f % 8) + tuple(sorted(params.items()))
        return self.get(key, w + m * 2, h + m * 2, m, m, lambda p: fn(p, f % 8, **params), flip)

    def necro(self, f):
        return self.get(("necro", f % 8), 52, 50, 6, 4, lambda p: necro(p, f % 8))

    def item(self, oid):
        return self.get(("item", oid), 20, 18, 3, 5, lambda p: item(p, oid))

    def cauldron(self, full):
        return self.get(("cauldron", full), 36, 16, 2, 2, lambda p: cauldron(p, full))

    def crucible(self):
        return self.get(("crucible",), 36, 20, 2, 6, lambda p: crucible(p))

    def cage(self):
        return self.get(("cage",), 36, 30, 2, 4, lambda p: cage(p))
