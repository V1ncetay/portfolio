"""Rendu moderne : direction artistique par zone, décors en couches et terrain.

Tout est construit une fois par salle et par résolution (mis en cache par le rendu) :
ciel / mur du fond, silhouettes lointaines, plan intermédiaire, brumes, rayons de lumière,
décors fixes, ombre portée du terrain puis terrain arrondi, texturé, ombré et coiffé
(herbe, mousse, neige, corniche...). Les éléments animés sont dessinés par modern.py.
"""
import math

import pygame

from config import COLS, ROWS, TILE
from world import ROOMS, SOLID, FAKE, WATER
import modern_gfx as G
from modern_gfx import mix, mul, C


class View:
    """Correspondance pixels logiques (160x200, pixels 2:1) -> pixels écran."""

    def __init__(self, w, h):
        self.W, self.H = int(w), int(h)
        self.sx = self.W / 160.0
        self.sy = self.H / 200.0
        self.PH = int(round(152 * self.sy))
        self.cw = TILE * self.sx
        self.ch = TILE * self.sy
        self.k = self.sy                    # unité des sprites (1 u = 1 px logique vertical)

    def X(self, lx):
        return lx * self.sx

    def Y(self, ly):
        return ly * self.sy

    def cell(self, cx, cy):
        x0, y0 = int(round(cx * self.cw)), int(round(cy * self.ch))
        x1, y1 = int(round((cx + 1) * self.cw)), int(round((cy + 1) * self.ch))
        return pygame.Rect(x0, y0, x1 - x0, y1 - y0)


# --------------------------------------------------------------------------- direction artistique
# sky : dégradé du fond ; rock : (clair, profond) du terrain ; rim : liseré lumineux ;
# cap : coiffe des surfaces ; under : détails sous les plafonds ; amb : lumière ambiante
# (multipliée) ; dark_amb : idem en salle obscure ; fog : brume ; accent : couleur d'interface.
ART = {
    "landes": dict(sky=[(0, "#0d1030"), (0.42, "#36295a"), (0.78, "#9a5578"), (1, "#f0a070")],
                   rock=("#7d6a78", "#2c2236"), rim="#ffd6b0", tex="rock", cap="grass",
                   capc=("#b4e070", "#6aa850", "#3a6a3a"), under="roots", fog="#e8a0b0",
                   amb=(228, 218, 236), accent="#ffb978", motes="fireflies"),
    "bois": dict(sky=[(0, "#06140f"), (0.5, "#12382c"), (1, "#2a5a40")],
                 rock=("#6e5a48", "#231a16"), rim="#e8ffb0", tex="rock", cap="moss",
                 capc=("#9ee070", "#4e9a48", "#245a30"), under="vines", fog="#7ad0a0",
                 amb=(206, 222, 210), accent="#9ef08a", motes="fireflies"),
    "riviere": dict(sky=[(0, "#050c22"), (0.55, "#14305a"), (1, "#3a6a90")],
                    rock=("#5e6a7e", "#1a2030"), rim="#c8e8ff", tex="rock", cap="grass",
                    capc=("#88d0a0", "#3c8a70", "#1e5048"), under="roots", fog="#a0c8f0",
                    amb=(200, 214, 236), accent="#80d0ff", motes="dust"),
    "chateau": dict(sky=[(0, "#141226"), (1, "#2a2440")], bgmul=(0.5, 0.72, 0.55),
                    rock=("#b4a69c", "#3a3036"), rim="#ffe0b8", tex="brick", cap="ledge",
                    capc=("#b8aec4", "#7a7088", "#4a4258"), under="none", fog="#8070a0",
                    amb=(196, 186, 210), accent="#ffc070", motes="dust"),
    "catacombes": dict(sky=[(0, "#08080e"), (1, "#141420")], bgmul=(0.6, 0.8, 0.6),
                       rock=("#8a8478", "#24221e"), rim="#e8f0ff", tex="brick", cap="dust",
                       capc=("#c8c0a8", "#8a8270", "#5a5446"), under="drips", fog="#506070",
                       amb=(150, 150, 170), dark_amb=(16, 18, 30), accent="#a0c0e0", motes="dust"),
    "palais": dict(sky=[(0, "#1c0814"), (1, "#3a1222")], bgmul=(0.7, 0.9, 0.75),
                   rock=("#e2d6d0", "#6a5560"), rim="#fff4d0", tex="marble", cap="gold",
                   capc=("#ffd76a", "#c8902e", "#7a5418"), under="none", fog="#d07090",
                   amb=(232, 214, 214), accent="#ffd76a", motes="dust"),
    "stonehenge": dict(sky=[(0, "#030818"), (0.6, "#0e2440"), (1, "#24486a")],
                       rock=("#8a96a8", "#262c3c"), rim="#e8f8ff", tex="rock", cap="snow",
                       capc=("#f4faff", "#c8daf0", "#8aa0c0"), under="icicles", fog="#b0d8ff",
                       amb=(206, 220, 240), accent="#a8f0ff", motes="snow"),
    "antre": dict(sky=[(0, "#05020e"), (0.5, "#1a0a30"), (1, "#3a1050")],
                  rock=("#5a4a78", "#160e26"), rim="#e0b0ff", tex="rock", cap="crystal",
                  capc=("#d0a0ff", "#8a50e0", "#4a2090"), under="stalactites", fog="#a060e0",
                  amb=(200, 180, 230), accent="#d090ff", motes="sparkles"),
    "foret": dict(sky=[(0, "#0a0614"), (0.55, "#2a1a3a"), (1, "#4a5a3a")],
                  rock=("#5e5248", "#1c1618"), rim="#d8ffb0", tex="rock", cap="deadgrass",
                  capc=("#9aa870", "#5a6a48", "#33402e"), under="roots", fog="#8ac080",
                  amb=(196, 204, 196), accent="#b0f080", motes="wisps"),
    "chapelle": dict(sky=[(0, "#060a1a"), (0.6, "#16224a"), (1, "#30406a")], bgmul=(0.7, 0.85, 0.7),
                     rock=("#9c98a8", "#2c2a38"), rim="#e8f0ff", tex="brick", cap="moss",
                     capc=("#88b878", "#4a7a50", "#2a4a34"), under="vines", fog="#8098d0",
                     amb=(200, 204, 228), dark_amb=(16, 16, 30), accent="#a0b8ff", motes="dust"),
    "abime": dict(sky=[(0, "#0a0406"), (0.55, "#2a0c08"), (1, "#7a2a0c")],
                  rock=("#4a3a3a", "#120a0a"), rim="#ffb070", tex="basalt", cap="ember",
                  capc=("#ffb040", "#e05010", "#3a1a14"), under="stalactites", fog="#ff7030",
                  amb=(210, 170, 150), accent="#ff9a40", motes="embers"),
    "citadelle": dict(sky=[(0, "#060a0a"), (1, "#142020")], bgmul=(0.55, 0.8, 0.6),
                      rock=("#6a7a74", "#141c1c"), rim="#c0ffd8", tex="brick", cap="ledge",
                      capc=("#8a9a94", "#5a6a64", "#2e3a38"), under="chains", fog="#40a080",
                      amb=(170, 196, 186), dark_amb=(12, 20, 20), accent="#70f0b0", motes="dust"),
    "sanctuaire": dict(sky=[(0, "#0a0208"), (0.6, "#2a0820"), (1, "#4a0c24")], bgmul=(0.6, 0.85, 0.7),
                       rock=("#4a3448", "#140810"), rim="#ff90b0", tex="basalt", cap="obsidian",
                       capc=("#ff5070", "#90203a", "#2a0a18"), under="stalactites", fog="#c03060",
                       amb=(200, 160, 180), accent="#ff6090", motes="embers_red"),
}


def art_key(rid):
    return ROOMS[rid]["zone"]


def art(rid):
    return ART[art_key(rid)]


# --------------------------------------------------------------------------- outils de décor
def _solid(tiles, cx, cy):
    cx = min(max(cx, 0), COLS - 1)
    cy = min(max(cy, 0), ROWS - 1)
    return tiles[cy][cx] in (SOLID, FAKE)


def ridge(s, base_y, amp, scale, color, seed, rim=None, rim_w=2, step=6, sharp=0.0):
    W, H = s.get_size()
    pts = []
    for x in range(-step, W + step * 2, step):
        n = G.fbm(x / scale, seed, 4)
        if sharp:
            n = n * (1 - sharp) + sharp * (1 - abs(2 * G.smooth_noise(x / (scale * 0.6), seed + 5) - 1))
        pts.append((x, base_y - amp * n))
    poly = pts + [(W + step * 2, H), (-step, H)]
    pygame.draw.polygon(s, C(color), poly)
    if rim:
        rl = G.surf(W, H, True)
        pygame.draw.lines(rl, G.rgba(rim, 90), False, pts, rim_w)
        s.blit(rl, (0, 0))
    return pts


def fog_band(s, y, h, color, a, shape="mid"):
    W = s.get_width()
    stops = [(0, 0), (0.5, a), (1, 0)] if shape == "mid" else [(0, 0), (1, a)]
    band = G.vgradient_alpha(W, max(2, int(h)), color, stops)
    s.blit(band, (0, int(y)))


def stars(s, rng, n, y_max, colors=("#ffffff", "#cfe0ff", "#ffe8c0"), big=0.08, k=1.0):
    W = s.get_width()
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(0, y_max) ** 1.0
        b = rng.random()
        c = C(rng.choice(colors))
        r = (0.6 + b * 1.1) * k
        if b > 1 - big:
            gl = G.radial(int(6 * k + 4), mul(c, 0.5))
            s.blit(gl, (x - gl.get_width() / 2, y - gl.get_height() / 2), special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(s, mix((40, 40, 70), c, 0.4 + 0.6 * b), (x, y), max(0.8, r))


def moon(s, x, y, r, color="#fff4dc", glow="#6a5a90", crescent=0.0, sky=None):
    gl = G.radial(int(r * 5), glow, 2.2)
    s.blit(gl, (x - r * 5, y - r * 5), special_flags=pygame.BLEND_ADD)
    gl = G.radial(int(r * 2), mul(glow, 1.5), 1.5)
    s.blit(gl, (x - r * 2, y - r * 2), special_flags=pygame.BLEND_ADD)
    pygame.draw.circle(s, C(color), (x, y), r)
    shade = G.surf(r * 2 + 2, r * 2 + 2, True)
    pygame.draw.circle(shade, (120, 110, 140, 40), (r * 1.25, r * 1.2), r * 0.95)
    for i, (dx, dy, rr) in enumerate(((-0.3, -0.2, 0.22), (0.25, 0.3, 0.15), (0.1, -0.45, 0.1), (-0.4, 0.35, 0.12))):
        pygame.draw.circle(shade, (150, 140, 160, 50), (r + dx * r, r + dy * r), rr * r)
    s.blit(shade, (x - r, y - r))
    if crescent and sky:
        pygame.draw.circle(s, C(sky), (x + r * crescent, y - r * 0.25), r * 0.92)


def rays(s, origin, angles, length, width, color, alpha):
    """Rayons de lumière additifs (couleur prémultipliée), estompés avec la distance."""
    W, H = s.get_size()
    layer = G.surf(W, H)
    ox, oy = origin
    col = mul(color, alpha / 255.0)
    for a, wk in angles:
        dx, dy = math.cos(a), math.sin(a)
        nx, ny = -dy, dx
        w0, w1 = width * 0.25 * wk, width * wk
        pts = [(ox + nx * w0, oy + ny * w0), (ox - nx * w0, oy - ny * w0),
               (ox + dx * length - nx * w1, oy + dy * length - ny * w1),
               (ox + dx * length + nx * w1, oy + dy * length + ny * w1)]
        pygame.draw.polygon(layer, col, pts, 0)
    layer = G.blur(layer, 3)
    layer = G.blur(layer, 3)
    fade = G.surf(W, H)
    fl = G.ellipse_light(length, length, (255, 255, 255), 0.9)
    fade.blit(fl, (ox - length, oy - length))
    layer.blit(fade, (0, 0), special_flags=pygame.BLEND_MULT)
    s.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)


def add_glow_band(s, y, h, color, strength):
    """Lueur additive montante (lave, flammes vertes...)."""
    W = s.get_width()
    g = G.vgradient(W, max(2, int(h)), [(0, (0, 0, 0)), (1, mul(color, strength))])
    s.blit(g, (0, int(y)), special_flags=pygame.BLEND_ADD)


def blobs(s, rng, n, region, rmin, rmax, colors, alpha, blur_k=8):
    W, H = s.get_size()
    layer = G.surf(W, H, True)
    x0, y0, x1, y1 = region
    for _ in range(n):
        c = rng.choice(colors)
        r = rng.uniform(rmin, rmax)
        pygame.draw.ellipse(layer, G.rgba(c, alpha), (rng.uniform(x0, x1) - r, rng.uniform(y0, y1) - r * 0.6, r * 2, r * 1.2))
    s.blit(G.blur(layer, blur_k), (0, 0))


def tree_trunks(s, rng, n, y_top, y_bot, wmin, wmax, color, seed, branches=True, k=1.0):
    W = s.get_width()
    for i in range(n):
        x = (i + rng.uniform(0.1, 0.9)) * W / n
        w = rng.uniform(wmin, wmax)
        lean = rng.uniform(-0.06, 0.06)
        pts_l, pts_r = [], []
        steps = 12
        for j in range(steps + 1):
            t = j / steps
            y = y_top + (y_bot - y_top) * t
            ww = w * (0.7 + 0.3 * t) + (w * 0.8 * max(0, t - 0.85) / 0.15) ** 1.0
            cx = x + lean * (y_bot - y) + (G.smooth_noise(t * 3, seed + i) - 0.5) * w * 0.6
            pts_l.append((cx - ww / 2, y))
            pts_r.append((cx + ww / 2, y))
        pygame.draw.polygon(s, C(color), pts_l + pts_r[::-1])
        if branches:
            for b in range(rng.randrange(1, 4)):
                t = rng.uniform(0.1, 0.55)
                y = y_top + (y_bot - y_top) * t
                d = rng.choice((-1, 1))
                L = rng.uniform(w * 1.5, w * 3.5)
                bx = x + d * w * 0.3
                pygame.draw.line(s, C(color), (bx, y), (bx + d * L, y - L * 0.5), max(2, int(w * 0.18)))


def dead_tree(s, x, base, h, w, color, seed, k=1.0):
    """Arbre mort tordu (récursif)."""
    rng = G.rng_for("deadtree", seed)

    def branch(x0, y0, ang, length, width, depth):
        x1 = x0 + math.cos(ang) * length
        y1 = y0 + math.sin(ang) * length
        pygame.draw.line(s, C(color), (x0, y0), (x1, y1), max(1, int(width)))
        pygame.draw.circle(s, C(color), (x1, y1), max(1, width / 2))
        if depth <= 0 or length < 6 * k:
            return
        for _ in range(2 if depth > 1 else rng.randrange(1, 3)):
            branch(x1, y1, ang + rng.uniform(-0.75, 0.75), length * rng.uniform(0.55, 0.75), width * 0.62, depth - 1)

    pts = [(x - w * 0.9, base), (x - w * 0.45, base - h * 0.15), (x - w * 0.35, base - h * 0.6),
           (x - w * 0.2, base - h), (x + w * 0.2, base - h), (x + w * 0.35, base - h * 0.55),
           (x + w * 0.5, base - h * 0.12), (x + w, base)]
    pygame.draw.polygon(s, C(color), pts)
    for i in range(4):
        branch(x + rng.uniform(-w * 0.2, w * 0.2), base - h * rng.uniform(0.55, 1.0),
               -math.pi / 2 + rng.uniform(-1.1, 1.1), h * rng.uniform(0.3, 0.5), w * 0.45, 3)


def masonry(s, rect, rng, base, var, mortar, bh, bw, light_top=True, rounded=0.15, alpha=255):
    x0, y0, w, h = rect
    layer = G.surf(w, h, True)
    layer.fill(G.rgba(mortar, alpha))
    y = 0
    row = 0
    while y < h:
        x = -rng.uniform(0, bw)
        while x < w:
            ww = bw * rng.uniform(0.6, 1.4)
            c = G.add(mix(base, var, rng.random()), rng.randint(-10, 10))
            r = pygame.Rect(int(x) + 1, int(y) + 1, int(ww) - 2, int(bh) - 2)
            pygame.draw.rect(layer, G.rgba(c, alpha), r, border_radius=int(bh * rounded))
            if light_top:
                pygame.draw.line(layer, G.rgba(G.add(c, 18), alpha), (r.x + 2, r.y), (r.right - 3, r.y), max(1, int(bh * 0.06)))
                pygame.draw.line(layer, G.rgba(mul(c, 0.7), alpha), (r.x + 2, r.bottom - 1), (r.right - 3, r.bottom - 1), max(1, int(bh * 0.06)))
            x += ww
        y += bh
        row += 1
    s.blit(layer, (x0, y0))


def arch(s, x, y_top, w, h, color, alpha=255, width=0):
    r = w / 2
    layer = G.surf(w + 4, h + 4, True)
    pygame.draw.rect(layer, G.rgba(color, alpha), (2, 2 + r, w, h - r), width)
    pygame.draw.ellipse(layer, G.rgba(color, alpha), (2, 2, w, r * 2), width)
    s.blit(layer, (x - 2, y_top - 2))


def gothic_window(s, x, y, w, h, frame, glass, glow=None, k=1.0):
    """Fenêtre en ogive (centre-haut x,y)."""
    r = w / 2
    pts = [(x - r, y + h)] + [(x - r + r * (1 - math.cos(a)), y + r * 1.4 - r * 1.4 * math.sin(a))
                              for a in [i * math.pi / 2 / 8 for i in range(9)]]
    pts += [(x + r - r * (1 - math.cos(a)), y + r * 1.4 - r * 1.4 * math.sin(a))
            for a in [math.pi / 2 - i * math.pi / 2 / 8 for i in range(9)]] + [(x + r, y + h)]
    if glow:
        gl = G.ellipse_light(w * 1.6, h * 0.9, glow, 1.8)
        s.blit(gl, (x - w * 1.6, y + h * 0.55 - h * 0.9), special_flags=pygame.BLEND_ADD)
    big = [(px + (px - x) * 0.18, py - (y + h - py) * 0.06 + h * 0.03) for px, py in pts]
    pygame.draw.polygon(s, C(frame), big)
    pygame.draw.polygon(s, C(glass), pts)
    return pts


# --------------------------------------------------------------------------- fonds par zone
def bg_landes(s, V, rng, rid, a):
    W, H = s.get_size()
    stars(s, rng, 90, H * 0.45, k=V.k * 0.5)
    mx, my = W * rng.uniform(0.65, 0.85), H * rng.uniform(0.16, 0.24)
    moon(s, mx, my, V.k * 9, glow="#6a4a7a", crescent=0.0)
    seed = G.h32(rid)
    ridge(s, H * 0.62, H * 0.22, W * 0.35, "#4a3a66", seed, rim="#f0a0a0")
    fog_band(s, H * 0.48, H * 0.25, a["fog"], 70)
    # tours lointaines
    for i in range(rng.randrange(1, 3)):
        tx, tb = rng.uniform(0.1, 0.9) * W, H * 0.6
        tw, th = V.k * 6, V.k * rng.uniform(18, 30)
        pygame.draw.rect(s, C("#3a2c52"), (tx, tb - th, tw, th + H))
        pygame.draw.polygon(s, C("#3a2c52"), [(tx - tw * 0.3, tb - th), (tx + tw * 1.3, tb - th), (tx + tw / 2, tb - th - tw * 1.6)])
        pygame.draw.circle(s, C("#ffc070"), (tx + tw / 2, tb - th * 0.7), V.k * 0.9)
    ridge(s, H * 0.78, H * 0.2, W * 0.25, "#33284a", seed + 3, rim="#d08090")
    fog_band(s, H * 0.66, H * 0.3, a["fog"], 60)
    ridge(s, H * 0.95, H * 0.16, W * 0.18, "#241c36", seed + 7, rim="#a06080")


def bg_bois(s, V, rng, rid, a):
    W, H = s.get_size()
    seed = G.h32(rid)
    blobs(s, rng, 30, (0, -H * 0.1, W, H * 0.25), V.k * 8, V.k * 22, ("#0a2a1e", "#123a28", "#0e3020"), 255, 6)
    rays(s, (W * rng.uniform(0.15, 0.4), -H * 0.1), [(math.pi * 0.38 + i * 0.09, 0.5 + 0.5 * (i % 2)) for i in range(-3, 4)],
         H * 1.5, W * 0.03, "#c0f0a0", 40)
    tree_trunks(s, rng, 9, -H * 0.05, H * 1.0, V.k * 5, V.k * 9, "#1c4636", seed, k=V.k)
    fog_band(s, H * 0.3, H * 0.6, a["fog"], 50)
    tree_trunks(s, rng, 6, -H * 0.05, H * 1.0, V.k * 9, V.k * 15, "#123226", seed + 1, k=V.k)
    fog_band(s, H * 0.55, H * 0.5, a["fog"], 40)
    blobs(s, rng, 20, (0, -H * 0.05, W, H * 0.12), V.k * 10, V.k * 26, ("#06180f", "#0a2216"), 255, 5)
    tree_trunks(s, rng, 3, -H * 0.05, H * 1.0, V.k * 14, V.k * 20, "#0a1e16", seed + 2, k=V.k)


def bg_riviere(s, V, rng, rid, a):
    W, H = s.get_size()
    seed = G.h32(rid)
    stars(s, rng, 120, H * 0.5, k=V.k * 0.5)
    mx, my = W * rng.uniform(0.2, 0.8), H * 0.18
    moon(s, mx, my, V.k * 8, glow="#3a5a9a")
    ridge(s, H * 0.55, H * 0.3, W * 0.3, "#1e3456", seed, rim="#a0c8ff", sharp=0.5)
    fog_band(s, H * 0.45, H * 0.25, a["fog"], 60)
    ridge(s, H * 0.72, H * 0.15, W * 0.2, "#162a46", seed + 4, rim="#80a8e0")
    # reflet de la lune sur l'eau lointaine
    for i in range(14):
        y = H * 0.74 + i * V.k * 1.6
        w = V.k * (14 - i * 0.6) * rng.uniform(0.6, 1.2)
        pygame.draw.line(s, mix("#162a46", "#e0eaff", 0.5 - i * 0.03), (mx - w, y), (mx + w, y), max(1, int(V.k * 0.5)))
    # roseaux
    for i in range(int(W / (V.k * 3))):
        x = i * V.k * 3 + rng.uniform(0, V.k * 3)
        hh = V.k * rng.uniform(4, 14)
        lean = rng.uniform(-1, 1) * V.k * 2
        pygame.draw.line(s, C("#0e1e30"), (x, H), (x + lean, H - hh - V.k * 10), max(1, int(V.k * 0.5)))
    fog_band(s, H * 0.75, H * 0.25, a["fog"], 70, "up")


def bg_stonehenge(s, V, rng, rid, a):
    W, H = s.get_size()
    seed = G.h32(rid)
    stars(s, rng, 160, H * 0.7, k=V.k * 0.5, big=0.12)
    # aurore boréale
    layer = G.surf(W, H)
    for band, col in ((0, "#40f0a0"), (1, "#7060ff"), (2, "#40c0ff")):
        pts = []
        y0 = H * (0.18 + band * 0.08)
        for x in range(0, W + 8, 8):
            pts.append((x, y0 + H * 0.08 * math.sin(x / W * 5 + band * 1.7 + seed % 7)))
        for i in range(len(pts) - 1):
            (x0, y0_), (x1, y1_) = pts[i], pts[i + 1]
            hh = H * (0.08 + 0.06 * G.smooth_noise(x0 / W * 8, seed + band))
            pygame.draw.polygon(layer, mul(col, 0.16), [(x0, y0_), (x1, y1_), (x1, y1_ + hh), (x0, y0_ + hh)])
    layer = G.blur(G.blur(layer, 4), 3)
    s.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)
    ridge(s, H * 0.7, H * 0.12, W * 0.3, "#1a2840", seed, rim="#a0d0ff")
    # mégalithes
    base = H * 0.72
    n = 7
    for i in range(n):
        x = (i + 0.5) * W / n + rng.uniform(-W * 0.03, W * 0.03)
        hh = H * rng.uniform(0.13, 0.22)
        ww = V.k * rng.uniform(7, 11)
        col = C("#142036")
        pygame.draw.rect(s, col, (x - ww / 2, base - hh, ww, hh + H), border_radius=int(V.k * 2))
        if i % 2 == 0 and i + 1 < n:
            x2 = (i + 1.5) * W / n
            pygame.draw.rect(s, col, (x - ww / 2, base - hh - V.k * 5, x2 - x + ww, V.k * 5), border_radius=int(V.k))
    fog_band(s, H * 0.62, H * 0.3, a["fog"], 70)
    ridge(s, H * 0.9, H * 0.08, W * 0.2, "#101a2c", seed + 9, rim="#c0e0ff")


def bg_antre(s, V, rng, rid, a):
    W, H = s.get_size()
    blobs(s, rng, 26, (0, 0, W, H), V.k * 16, V.k * 50, ("#5a1a8a", "#2a2a9a", "#9a2a7a", "#1a4a8a"), 70, 10)
    stars(s, rng, 160, H, colors=("#ffffff", "#e0c0ff", "#a0e0ff"), k=V.k * 0.5, big=0.12)
    # îlots flottants
    for i in range(5):
        x, y = rng.uniform(0.05, 0.95) * W, rng.uniform(0.25, 0.75) * H
        w = V.k * rng.uniform(10, 26)
        col = mix("#120a24", "#2a1a48", rng.random())
        pts = [(x - w, y), (x + w, y), (x + w * 0.5, y + w * 0.4), (x + w * 0.1, y + w * 0.9), (x - w * 0.4, y + w * 0.35)]
        pygame.draw.polygon(s, col, pts)
        pygame.draw.line(s, mix(col, "#d0a0ff", 0.5), (x - w, y), (x + w, y), max(1, int(V.k * 0.6)))
    fog_band(s, H * 0.6, H * 0.4, a["fog"], 50, "up")


def bg_foret(s, V, rng, rid, a):
    W, H = s.get_size()
    seed = G.h32(rid)
    stars(s, rng, 50, H * 0.4, colors=("#ffe0e0", "#e0ffe0"), k=V.k * 0.5)
    mx, my = W * rng.uniform(0.2, 0.8), H * 0.2
    moon(s, mx, my, V.k * 11, color="#ffb0a0", glow="#7a2030")
    ridge(s, H * 0.62, H * 0.18, W * 0.3, "#2a2040", seed, rim="#ff9090")
    fog_band(s, H * 0.48, H * 0.3, "#80a070", 60)
    for i in range(6):
        dead_tree(s, rng.uniform(0, W), H * rng.uniform(0.85, 1.0), H * rng.uniform(0.35, 0.55),
                  V.k * rng.uniform(3, 5), "#1e1a2a", seed + i, k=V.k)
    fog_band(s, H * 0.6, H * 0.4, a["fog"], 55)
    for i in range(3):
        dead_tree(s, rng.uniform(0, W), H * 1.02, H * rng.uniform(0.5, 0.75),
                  V.k * rng.uniform(5, 7), "#100c16", seed + 20 + i, k=V.k)


def bg_abime(s, V, rng, rid, a):
    W, H = s.get_size()
    seed = G.h32(rid)
    # parois de basalte lointaines, éclairées par en dessous
    ridge(s, H * 0.35, H * 0.3, W * 0.2, "#24100c", seed, sharp=0.6)
    ridge(s, H * 0.6, H * 0.35, W * 0.15, "#1a0a08", seed + 2, rim="#ff6020", sharp=0.7)
    # stalactites du plafond
    for i in range(int(W / (V.k * 10))):
        x = i * V.k * 10 + rng.uniform(0, V.k * 8)
        hh = H * rng.uniform(0.05, 0.2)
        ww = V.k * rng.uniform(3, 7)
        pygame.draw.polygon(s, C("#140806"), [(x - ww, -1), (x + ww, -1), (x + rng.uniform(-ww, ww) * 0.3, hh)])
    # coulées lointaines
    for i in range(rng.randrange(1, 3)):
        x = rng.uniform(0.1, 0.9) * W
        layer = G.surf(W, H)
        pygame.draw.rect(layer, (110, 45, 10), (x, H * 0.1, V.k * 2.5, H))
        s.blit(G.blur(layer, 3), (0, 0), special_flags=pygame.BLEND_ADD)
    add_glow_band(s, H * 0.4, H * 0.6, "#ff5010", 0.35)
    fog_band(s, H * 0.5, H * 0.5, "#ff6020", 40, "up")


def bg_sanctuaire(s, V, rng, rid, a):
    W, H = s.get_size()
    masonry(s, (0, 0, W, H), rng, "#2a0c1c", "#1a0612", "#0c0208", V.k * 8, V.k * 22, alpha=255)
    # grand cercle runique
    cx, cy, r = W / 2, H * 0.42, H * 0.36
    layer = G.surf(W, H)
    pygame.draw.circle(layer, (70, 16, 30), (cx, cy), r, max(2, int(V.k)))
    pygame.draw.circle(layer, (50, 12, 22), (cx, cy), r * 0.86, max(1, int(V.k * 0.6)))
    for i in range(24):
        ang = i / 24 * math.tau
        pygame.draw.circle(layer, (80, 24, 40), (cx + math.cos(ang) * r * 0.93, cy + math.sin(ang) * r * 0.93), V.k * 0.8)
    s.blit(G.blur(layer, 3), (0, 0), special_flags=pygame.BLEND_ADD)
    s.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)
    for x in (W * 0.08, W * 0.92):
        pygame.draw.rect(s, C("#14060e"), (x - V.k * 8, 0, V.k * 16, H))
        pygame.draw.rect(s, C("#3a1428"), (x - V.k * 8, 0, V.k * 2, H))
    fog_band(s, H * 0.6, H * 0.4, a["fog"], 50, "up")


def _interior_base(s, V, rng, a, wall, wall2, mortar, bh_k=8, bw_k=20):
    W, H = s.get_size()
    masonry(s, (0, 0, W, H), rng, wall, wall2, mortar, V.k * bh_k, V.k * bw_k)


def bg_chateau(s, V, rng, rid, a):
    W, H = s.get_size()
    _interior_base(s, V, rng, a, "#2e2a44", "#262238", "#14121e")
    # alcôves en arc et piliers
    n = 4
    for i in range(n):
        x = (i + 0.5) * W / n
        aw = W / n * 0.5
        arch(s, x - aw / 2, H * 0.18, aw, H * 0.9, "#120f1c", 150)
        pygame.draw.rect(s, C("#3a3452"), (x + W / n * 0.5 - V.k * 4, 0, V.k * 8, H))
        pygame.draw.rect(s, C("#4a4466"), (x + W / n * 0.5 - V.k * 4, 0, V.k * 1.5, H))
    fog_band(s, H * 0.7, H * 0.3, a["fog"], 40, "up")


def bg_palais(s, V, rng, rid, a):
    W, H = s.get_size()
    s.blit(G.vgradient(W, H, [(0, "#3a1224"), (1, "#24081a")]), (0, 0))
    # panneaux dorés et damas
    n = 5
    for i in range(n):
        x0 = i * W / n + V.k * 6
        w = W / n - V.k * 12
        r = pygame.Rect(int(x0), int(H * 0.12), int(w), int(H * 0.7))
        pygame.draw.rect(s, C("#4a1830"), r, border_radius=int(V.k * 2))
        for yy in range(r.top + int(V.k * 6), r.bottom - int(V.k * 4), int(V.k * 10)):
            for xx in range(r.left + int(V.k * 6), r.right - int(V.k * 4), int(V.k * 12)):
                pts = [(xx, yy - V.k * 2.5), (xx + V.k * 2.5, yy), (xx, yy + V.k * 2.5), (xx - V.k * 2.5, yy)]
                pygame.draw.polygon(s, C("#5a2038"), pts)
        pygame.draw.rect(s, C("#b08030"), r, max(1, int(V.k * 0.7)), border_radius=int(V.k * 2))
        pygame.draw.rect(s, C("#6a4818"), r.inflate(-V.k * 3, -V.k * 3), max(1, int(V.k * 0.4)), border_radius=int(V.k * 2))
    # frise
    pygame.draw.rect(s, C("#1a0610"), (0, H * 0.05, W, V.k * 3))
    pygame.draw.line(s, C("#c89040"), (0, H * 0.05), (W, H * 0.05), max(1, int(V.k * 0.5)))
    # lustres lointains
    for i in range(2):
        x = W * (0.3 + 0.4 * i)
        gl = G.radial(int(V.k * 28), "#7a4a20", 2.0)
        s.blit(gl, (x - gl.get_width() / 2, H * 0.12 - gl.get_height() / 2), special_flags=pygame.BLEND_ADD)
    fog_band(s, H * 0.7, H * 0.3, "#ff8090", 25, "up")


def bg_catacombes(s, V, rng, rid, a):
    W, H = s.get_size()
    _interior_base(s, V, rng, a, "#1e1c24", "#18161e", "#0a0a0e", 7, 16)
    # niches de crânes (ossuaire)
    cols = 6
    for i in range(cols):
        x = (i + 0.5) * W / cols
        aw = W / cols * 0.55
        arch(s, x - aw / 2, H * 0.25, aw, H * 0.5, "#08080c", 230)
        for row in range(4):
            for j in range(4):
                sx_ = x - aw / 2 + aw * (j + 0.5) / 4
                sy_ = H * 0.25 + aw * 0.5 + row * V.k * 6
                pygame.draw.circle(s, C("#3a3630"), (sx_, sy_), V.k * 2.2)
                pygame.draw.circle(s, C("#08080c"), (sx_ - V.k * 0.8, sy_), V.k * 0.6)
                pygame.draw.circle(s, C("#08080c"), (sx_ + V.k * 0.8, sy_), V.k * 0.6)
    fog_band(s, H * 0.6, H * 0.4, a["fog"], 40, "up")


def bg_citadelle(s, V, rng, rid, a):
    W, H = s.get_size()
    _interior_base(s, V, rng, a, "#1a2624", "#141e1c", "#080c0c", 10, 26)
    n = 3
    for i in range(n):
        x = (i + 0.5) * W / n
        pygame.draw.rect(s, C("#0e1616"), (x - V.k * 9, 0, V.k * 18, H))
        pygame.draw.rect(s, C("#24302e"), (x - V.k * 9, 0, V.k * 2, H))
        for yy in range(int(V.k * 10), int(H), int(V.k * 30)):
            pygame.draw.rect(s, C("#2a3836"), (x - V.k * 10, yy, V.k * 20, V.k * 3))
    add_glow_band(s, H * 0.5, H * 0.5, "#20ff90", 0.1)
    fog_band(s, H * 0.65, H * 0.35, a["fog"], 45, "up")


def bg_chapelle(s, V, rng, rid, a):
    W, H = s.get_size()
    seed = G.h32(rid)
    stars(s, rng, 90, H * 0.6, k=V.k * 0.5)
    moon(s, W * rng.uniform(0.3, 0.7), H * 0.15, V.k * 7, glow="#3a4a8a")
    # mur en ruine : bord supérieur déchiqueté
    wall = G.surf(W, H, True)
    masonry(wall, (0, 0, W, H), rng, "#2a2c40", "#222436", "#101220", V.k * 8, V.k * 18)
    cut = G.surf(W, H, True)
    cut.fill((255, 255, 255, 255))
    pts = [(0, 0)]
    for x in range(0, W + 16, 16):
        pts.append((x, H * (0.18 + 0.22 * G.fbm(x / (W * 0.15), seed, 3))))
    pts.append((W, 0))
    pygame.draw.polygon(cut, (0, 0, 0, 0), pts)
    # brèches en ogive dans le mur
    for i in range(3):
        x = (i + 0.5) * W / 3 + rng.uniform(-W * 0.05, W * 0.05)
        ww = W * 0.11
        pygame.draw.rect(cut, (0, 0, 0, 0), (x - ww / 2, H * 0.35, ww, H * 0.4))
        pygame.draw.ellipse(cut, (0, 0, 0, 0), (x - ww / 2, H * 0.35 - ww * 0.6, ww, ww * 1.2))
    wall.blit(cut, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    sh = G.blur(G.tinted(wall, (0, 0, 0)), 6)
    sh.set_alpha(140)
    s.blit(sh, (V.k * 2, V.k * 3))
    s.blit(wall, (0, 0))
    rays(s, (W * 0.5, -H * 0.2), [(math.pi * 0.5 + i * 0.12, 0.6) for i in range(-3, 4)], H * 1.4, W * 0.035, "#a0b8ff", 30)
    fog_band(s, H * 0.6, H * 0.4, a["fog"], 45, "up")


BG = dict(landes=bg_landes, bois=bg_bois, riviere=bg_riviere, stonehenge=bg_stonehenge,
          antre=bg_antre, foret=bg_foret, abime=bg_abime, sanctuaire=bg_sanctuaire,
          chateau=bg_chateau, palais=bg_palais, catacombes=bg_catacombes,
          citadelle=bg_citadelle, chapelle=bg_chapelle)


# --------------------------------------------------------------------------- décors fixes
def paint_decor(s, V, kind, tx, ty, a, rng):
    """Partie statique des décors (les flammes, coulées, vortex sont animés par modern.py)."""
    k = V.k
    x, y = V.X(tx * TILE), V.Y(ty * TILE)
    PH = V.PH
    floor = PH - V.ch
    if kind == "tower":                                   # tour du sorcier
        w = V.X(28)
        top = y + V.Y(6)
        body = pygame.Rect(int(x), int(top), int(w), int(floor - top))
        g = G.surf(body.w, body.h)
        g.blit(G.vgradient(body.w, body.h, [(0, "#6a6080"), (1, "#3a3048")]), (0, 0))
        masonry(g, (0, 0, body.w, body.h), rng, "#5a5070", "#4a4260", "#2a2438", k * 5, k * 9, alpha=255)
        # modelé cylindrique
        for i in range(body.w):
            t = i / body.w
            v = 0.55 + 0.6 * math.sin(math.pi * (t * 0.85 + 0.1)) - 0.25 * t
            pygame.draw.line(g, (int(255 * min(1, v)),) * 3, (i, 0), (i, body.h))
        g2 = G.surf(body.w, body.h)
        masonry(g2, (0, 0, body.w, body.h), G.rng_for("tw", tx), "#8a80a0", "#746a8c", "#3a3248", k * 5, k * 9)
        g2.blit(g, (0, 0), special_flags=pygame.BLEND_MULT)
        s.blit(g2, body.topleft)
        for i in range(4):                                # créneaux
            pygame.draw.rect(s, C("#6a6084"), (x + i * w / 4, top - V.Y(5), w / 8, V.Y(5)), border_radius=int(k))
        pygame.draw.polygon(s, C("#3a3a8a"), [(x - V.X(3), top - V.Y(4)), (x + w + V.X(3), top - V.Y(4)), (x + w / 2, top - V.Y(26))])
        pygame.draw.polygon(s, C("#5a5ab8"), [(x - V.X(3), top - V.Y(4)), (x + w * 0.45, top - V.Y(4)), (x + w / 2, top - V.Y(26))])
        pygame.draw.circle(s, C("#ffd060"), (x + w / 2, top - V.Y(27)), k * 1.4)
        for wy in (top + V.Y(14), top + V.Y(38)):        # fenêtres éclairées
            r = pygame.Rect(0, 0, int(V.X(5)), int(V.Y(10)))
            r.center = (int(x + w / 2), int(wy))
            gl = G.radial(int(k * 14), "#a06020", 1.6)
            s.blit(gl, (r.centerx - gl.get_width() / 2, r.centery - gl.get_height() / 2), special_flags=pygame.BLEND_ADD)
            pygame.draw.rect(s, C("#2a1a10"), r.inflate(k, k), border_top_left_radius=int(r.w / 2), border_top_right_radius=int(r.w / 2))
            pygame.draw.rect(s, C("#ffc860"), r, border_top_left_radius=int(r.w / 2), border_top_right_radius=int(r.w / 2))
            pygame.draw.line(s, C("#a06020"), (r.centerx, r.top + 2), (r.centerx, r.bottom), max(1, int(k * 0.4)))
        d = pygame.Rect(0, 0, int(V.X(9)), int(V.Y(20)))
        d.midbottom = (int(x + w / 2), int(floor))
        pygame.draw.rect(s, C("#3a2014"), d, border_top_left_radius=int(d.w / 2), border_top_right_radius=int(d.w / 2))
        pygame.draw.rect(s, C("#5a3420"), d.inflate(-k * 1.5, -k * 1.5), border_top_left_radius=int(d.w / 2), border_top_right_radius=int(d.w / 2))
    elif kind == "window":
        cx = x + V.X(5)
        gothic_window(s, cx, y - V.Y(4), V.X(10), V.Y(22), "#3a3450", "#1a2a5a", glow="#20305a", k=k)
        pygame.draw.circle(s, C("#e8f0ff"), (cx + V.X(2), y + V.Y(3)), k * 2)
        for i in range(5):
            pygame.draw.circle(s, C("#c0d0ff"), (cx + rng.uniform(-V.X(4), V.X(4)), y + rng.uniform(0, V.Y(14))), max(1, k * 0.35))
        pygame.draw.line(s, C("#3a3450"), (cx, y - V.Y(3)), (cx, y + V.Y(18)), max(1, int(k * 0.8)))
        pygame.draw.line(s, C("#3a3450"), (cx - V.X(5), y + V.Y(8)), (cx + V.X(5), y + V.Y(8)), max(1, int(k * 0.8)))
        pygame.draw.rect(s, C("#4a4462"), (cx - V.X(7), y + V.Y(18), V.X(14), V.Y(2)), border_radius=int(k))
    elif kind == "chains":
        for i in range(int(V.Y(50) / (k * 3))):
            yy = y + i * k * 3
            if i % 2:
                pygame.draw.ellipse(s, C("#6a6878"), (x - k * 0.6, yy, k * 2.4, k * 3.6), max(1, int(k * 0.5)))
            else:
                pygame.draw.line(s, C("#8a889a"), (x + k * 0.6, yy), (x + k * 0.6, yy + k * 3.2), max(1, int(k * 0.6)))
        pygame.draw.circle(s, C("#7a7888"), (x + k * 0.6, y + V.Y(53)), k * 3, max(1, int(k * 0.8)))
    elif kind == "column":
        top, bot = y, floor - V.Y(1)
        w = V.X(6)
        g = G.surf(int(w), int(bot - top))
        for i in range(int(w)):
            t = i / max(1, w)
            v = 0.55 + 0.45 * math.sin(math.pi * t) + (0.12 if (i * 6 // int(w)) % 2 else 0)
            pygame.draw.line(g, mul("#e8e0f0", min(1.1, v)), (i, 0), (i, g.get_height()))
        s.blit(g, (x - w / 2 + V.X(2), top))
        for i, (ww, c) in enumerate(((10, "#ffd060"), (8, "#c8902e"))):
            pygame.draw.rect(s, C(c), (x + V.X(2) - V.X(ww / 2), top + i * V.Y(2), V.X(ww), V.Y(2)), border_radius=int(k * 0.6))
            pygame.draw.rect(s, C(c), (x + V.X(2) - V.X(ww / 2), bot - (i + 1) * V.Y(2), V.X(ww), V.Y(2)), border_radius=int(k * 0.6))
    elif kind == "banner":
        w, h = V.X(8), V.Y(24)
        pygame.draw.line(s, C("#c89040"), (x - V.X(2), y), (x + w + V.X(2), y), max(2, int(k)))
        pts = [(x, y), (x + w, y), (x + w, y + h), (x + w / 2, y + h - V.Y(5)), (x, y + h)]
        pygame.draw.polygon(s, C("#8a1428"), pts)
        for i in range(4):                               # plis
            xx = x + w * (i + 0.5) / 4
            pygame.draw.line(s, C("#6a0c1c" if i % 2 else "#a82038"), (xx, y + k), (xx, y + h - V.Y(4)), max(1, int(k * 0.8)))
        pygame.draw.lines(s, C("#d8a040"), False, pts[1:] + [pts[0]], max(1, int(k * 0.5)))
        cx, cy = x + w / 2, y + h * 0.42
        pygame.draw.polygon(s, C("#ffd060"), G.star_points(cx, cy, k * 3.2, k * 1.4))
    elif kind == "altar":
        w, h = V.X(40), V.Y(12)
        r = pygame.Rect(int(x), int(y + V.Y(4)), int(w), int(h))
        pygame.draw.rect(s, C("#4a5266"), r, border_radius=int(k * 1.5))
        pygame.draw.rect(s, C("#7a8498"), (r.x, r.y, r.w, k * 2), border_radius=int(k))
        pygame.draw.rect(s, C("#1a1e2a"), r.inflate(-V.X(8), -V.Y(6)).move(0, V.Y(1)), border_radius=int(k))
    elif kind == "deadtree":
        dead_tree(s, x + V.X(2), floor + k, PH - V.ch - y, V.X(3), "#1a1420", G.h32(tx, ty), k=k)
        pygame.draw.circle(s, C("#ffd040"), (x + V.X(2), y + V.Y(12)), k * 0.9)
        pygame.draw.circle(s, C("#ffd040"), (x + V.X(2) + k * 2.2, y + V.Y(12)), k * 0.9)
    elif kind == "cross":
        stone = "#7a7a8a"
        pygame.draw.rect(s, C(stone), (x + V.X(2), y, V.X(3), V.Y(16)), border_radius=int(k))
        pygame.draw.rect(s, C(stone), (x, y + V.Y(3), V.X(7), V.Y(3)), border_radius=int(k))
        pygame.draw.rect(s, C("#9a9aaa"), (x + V.X(2), y, V.X(0.8), V.Y(16)))
        pygame.draw.ellipse(s, C("#1a1a24"), (x - V.X(2), y + V.Y(14), V.X(11), V.Y(3)))
    elif kind == "citadel_far":
        col = C("#2a1a40")
        for (dx, w, h) in ((0, 6, 26), (6, 14, 16), (20, 6, 30), (26, 10, 18)):
            pygame.draw.rect(s, col, (x + V.X(dx), y + V.Y(40 - h), V.X(w), V.Y(h + 60)))
            pygame.draw.polygon(s, col, [(x + V.X(dx - 1), y + V.Y(40 - h)), (x + V.X(dx + w + 1), y + V.Y(40 - h)),
                                         (x + V.X(dx + w / 2), y + V.Y(40 - h - w * 0.9))])
        for (wx, wy) in ((2, 20), (22, 16), (23, 26), (29, 30)):
            gl = G.radial(int(k * 4), "#30a060", 1.5)
            s.blit(gl, (x + V.X(wx) - k * 4, y + V.Y(wy) - k * 4), special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(s, C("#80ffa0"), (x + V.X(wx), y + V.Y(wy)), k * 0.7)
    elif kind == "vitrail":
        cx = x + V.X(5)
        pts = gothic_window(s, cx, y - V.Y(9), V.X(11), V.Y(28), "#14141e", "#101020", glow="#402060", k=k)
        clip = G.surf(s.get_width(), s.get_height(), True)
        pygame.draw.polygon(clip, (255, 255, 255, 255), pts)
        glass = G.surf(s.get_width(), s.get_height(), True)
        cols = ("#e04040", "#ffc040", "#4060ff", "#40c060", "#c040e0", "#40d0ff")
        ys = y - V.Y(9)
        for j in range(8):
            for i in range(3):
                gx = cx - V.X(5.5) + i * V.X(11) / 3
                gy = ys + j * V.Y(28) / 8
                if rng.random() < 0.85:
                    c = rng.choice(cols)
                    pygame.draw.rect(glass, G.rgba(c, 255), (gx, gy, V.X(11) / 3, V.Y(28) / 8))
        glass.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(glass, (0, 0))
        for j in range(1, 8):
            pygame.draw.line(s, C("#14141e"), (cx - V.X(6), ys + j * V.Y(28) / 8), (cx + V.X(6), ys + j * V.Y(28) / 8), max(1, int(k * 0.5)))
        for i in range(1, 3):
            pygame.draw.line(s, C("#14141e"), (cx - V.X(5.5) + i * V.X(11) / 3, ys), (cx - V.X(5.5) + i * V.X(11) / 3, ys + V.Y(28)), max(1, int(k * 0.5)))
    elif kind == "anvil":
        pts = [(x - V.X(3), y + V.Y(8)), (x + V.X(14), y + V.Y(8)), (x + V.X(14), y + V.Y(11)),
               (x + V.X(10), y + V.Y(11)), (x + V.X(9), y + V.Y(15)), (x + V.X(12), y + V.Y(16)),
               (x + V.X(2), y + V.Y(16)), (x + V.X(5), y + V.Y(15)), (x + V.X(4), y + V.Y(11)), (x + V.X(2), y + V.Y(11))]
        pygame.draw.polygon(s, C("#3a3a44"), pts)
        pygame.draw.line(s, C("#9a9aaa"), (x - V.X(3), y + V.Y(8)), (x + V.X(14), y + V.Y(8)), max(1, int(k * 0.8)))
    elif kind == "bones":
        for i, (dx, dy) in enumerate(((0, 6), (5, 5), (2, 3), (8, 6), (10, 4))):
            c = "#d8d0b8" if i % 2 else "#a8a090"
            x0, y0 = x + V.X(dx), y + V.Y(dy)
            x1, y1 = x0 + V.X(4), y0 + V.Y(1 if i % 3 else -1)
            pygame.draw.line(s, C(c), (x0, y0), (x1, y1), max(2, int(k * 1.2)))
            for px_, py_ in ((x0, y0), (x1, y1)):
                pygame.draw.circle(s, C(c), (px_, py_ - k * 0.5), k * 0.9)
                pygame.draw.circle(s, C(c), (px_, py_ + k * 0.5), k * 0.9)
        cx, cy = x + V.X(6), y + V.Y(2)
        pygame.draw.ellipse(s, C("#e0d8c0"), (cx - k * 3.5, cy - k * 3, k * 7, k * 6))
        pygame.draw.rect(s, C("#e0d8c0"), (cx - k * 2, cy + k * 1.5, k * 4, k * 2.2), border_radius=int(k * 0.6))
        pygame.draw.circle(s, C("#1a1410"), (cx - k * 1.3, cy), k * 1.0)
        pygame.draw.circle(s, C("#1a1410"), (cx + k * 1.3, cy), k * 1.0)
    elif kind == "pentagram":
        pass                                              # animé (lueur pulsée) dans modern.py
    elif kind in ("torch", "gflame"):
        green = kind == "gflame"
        bx = x + V.X(2)
        pygame.draw.rect(s, C("#3a3440" if green else "#5a4030"), (bx - k * 1.2, y + V.Y(4), k * 2.4, V.Y(7)), border_radius=int(k * 0.6))
        pygame.draw.rect(s, C("#7a7488" if green else "#8a6a40"), (bx - k * 3, y + V.Y(3), k * 6, k * 2.2), border_radius=int(k))
        pygame.draw.rect(s, C("#5a5466"), (bx - k * 2, y + V.Y(10), k * 4, k * 1.6), border_radius=int(k * 0.5))


def light_spots(rid, V):
    """Sources de lumière fixes : (x, y, rayon, couleur, scintillement)."""
    room = ROOMS[rid]
    out = []
    for d in room["decor"]:
        kind, tx, ty = d[0], d[1], d[2]
        x, y = V.X(tx * TILE), V.Y(ty * TILE)
        if kind == "torch":
            out.append((x + V.X(2), y + V.Y(2), V.k * 46, (255, 170, 80), 1))
        elif kind == "gflame":
            out.append((x + V.X(2), y + V.Y(2), V.k * 46, (80, 255, 150), 1))
        elif kind == "window":
            out.append((x + V.X(5), y + V.Y(8), V.k * 34, (110, 140, 220), 0))
        elif kind == "vitrail":
            out.append((x + V.X(5), y + V.Y(5), V.k * 36, (200, 120, 220), 0))
        elif kind == "lavafall":
            out.append((x + V.X(2.5), V.PH * 0.5, V.k * 60, (255, 110, 30), 1))
        elif kind == "pentagram":
            out.append((x, y + V.Y(22), V.k * 50, (255, 50, 90), 1))
        elif kind == "tower":
            out.append((x + V.X(14), y + V.Y(30), V.k * 30, (255, 170, 80), 0))
        elif kind == "vortex_bas":
            out.append((x, y + V.Y(10), V.k * 40, (200, 100, 255), 1))
        elif kind == "citadel_far":
            out.append((x + V.X(16), y + V.Y(24), V.k * 30, (60, 220, 120), 0))
    return out


# --------------------------------------------------------------------------- terrain
def _gradient_cell(w, h, stops, add_mode):
    s = G.surf(w, h)
    for yy in range(h):
        t = yy / max(1, h - 1)
        v = stops(t)
        c = (int(v),) * 3
        pygame.draw.line(s, c, (0, yy), (w - 1, yy))
    return s


def texture(V, mat, W, H, seed):
    """Texture du matériau (plein cadre) : roche, briques, marbre ou basalte."""
    hi, lo = C(mat["rock"][0]), C(mat["rock"][1])
    rng = G.rng_for("tex", seed)
    kind = mat["tex"]
    t = G.surf(W, H)
    t.fill(mix(hi, lo, 0.35))
    if kind in ("brick", "marble"):
        bh = V.ch / 2
        mort = mix(lo, (0, 0, 0), 0.3)
        if kind == "marble":
            masonry(t, (0, 0, W, H), rng, mix(hi, lo, 0.1), mix(hi, lo, 0.28), mix(hi, lo, 0.6), V.ch, V.cw * 1.6, rounded=0.08)
            layer = G.surf(W, H, True)
            for _ in range(int(W * H / (V.cw * V.ch * 3))):       # veines
                x, y = rng.uniform(0, W), rng.uniform(0, H)
                pts = [(x, y)]
                for j in range(6):
                    x += rng.uniform(-V.cw * 0.3, V.cw * 0.5)
                    y += rng.uniform(-V.ch * 0.2, V.ch * 0.3)
                    pts.append((x, y))
                pygame.draw.lines(layer, (120, 90, 110, 70), False, pts, max(1, int(V.k * 0.4)))
            t.blit(layer, (0, 0))
        else:
            masonry(t, (0, 0, W, H), rng, mix(hi, lo, 0.15), mix(hi, lo, 0.4), mort, bh, V.cw * 0.9, rounded=0.2)
        G.tint_noise(t, V.cw * 1.5, seed, 200, 255)
    else:
        G.tint_noise(t, V.cw * 2.5, seed, 150, 255)
        G.tint_noise(t, V.cw * 0.6, seed + 1, 190, 255)
        layer = G.surf(W, H, True)
        # strates et galets
        for _ in range(int(W / V.cw * 2)):
            y = rng.uniform(0, H)
            x = rng.uniform(-W * 0.2, W)
            L = rng.uniform(V.cw, V.cw * 4)
            pts = [(x + L * i / 8, y + math.sin(i * 0.8 + x) * V.k * 0.8) for i in range(9)]
            pygame.draw.lines(layer, G.rgba(lo, 110), False, pts, max(1, int(V.k * 0.5)))
        for _ in range(int(W * H / (V.cw * V.ch) * 1.2)):
            x, y = rng.uniform(0, W), rng.uniform(0, H)
            r = V.k * rng.uniform(0.6, 1.8)
            c = mix(hi, lo, rng.uniform(0.0, 0.5))
            pygame.draw.ellipse(layer, G.rgba(mul(c, 0.6), 160), (x - r, y - r * 0.5, r * 2.2, r * 1.6))
            pygame.draw.ellipse(layer, G.rgba(c, 200), (x - r, y - r * 0.7, r * 2, r * 1.3))
        if kind == "basalt":
            for _ in range(int(W / V.cw * 3)):               # fissures
                x, y = rng.uniform(0, W), rng.uniform(0, H)
                pts = [(x, y)]
                for j in range(4):
                    x += rng.uniform(-V.cw * 0.4, V.cw * 0.4)
                    y += rng.uniform(0, V.ch * 0.5)
                    pts.append((x, y))
                pygame.draw.lines(layer, (10, 4, 4, 180), False, pts, max(1, int(V.k * 0.5)))
        t.blit(layer, (0, 0))
    return t


def build_terrain(V, tiles, mat, seed):
    """Couche du terrain (SRCALPHA) + masque, avec coins arrondis, ombrage et coiffes."""
    W, H = V.W, V.PH
    ss = 2
    big = pygame.Surface((W * ss, H * ss), pygame.SRCALPHA)
    r = int(min(V.cw, V.ch) * 0.42 * ss)

    def rect2(cx, cy):
        x0, y0 = int(round(cx * V.cw * ss)), int(round(cy * V.ch * ss))
        x1, y1 = int(round((cx + 1) * V.cw * ss)), int(round((cy + 1) * V.ch * ss))
        return pygame.Rect(x0, y0, x1 - x0, y1 - y0)

    solid = [[_solid(tiles, cx, cy) for cx in range(COLS)] for cy in range(ROWS)]

    def S(cx, cy):
        return _solid(tiles, cx, cy)

    white, clear = (255, 255, 255, 255), (0, 0, 0, 0)
    for cy in range(ROWS):
        for cx in range(COLS):
            if solid[cy][cx]:
                big.fill(white, rect2(cx, cy))
    corners = ((-1, -1), (1, -1), (-1, 1), (1, 1))
    for cy in range(ROWS):
        for cx in range(COLS):
            rc = rect2(cx, cy)
            for dx, dy in corners:
                px_ = rc.left if dx < 0 else rc.right - r
                py_ = rc.top if dy < 0 else rc.bottom - r
                ccx = rc.left + r if dx < 0 else rc.right - r
                ccy = rc.top + r if dy < 0 else rc.bottom - r
                if solid[cy][cx]:
                    if not S(cx + dx, cy) and not S(cx, cy + dy):          # coin convexe
                        big.fill(clear, (px_, py_, r, r))
                        pygame.draw.circle(big, white, (ccx, ccy), r)
                else:
                    if S(cx + dx, cy) and S(cx, cy + dy) and S(cx + dx, cy + dy):   # coin concave
                        big.fill(white, (px_, py_, r, r))
                        pygame.draw.circle(big, clear, (ccx, ccy), r)
    mask = pygame.transform.smoothscale(big, (W, H))

    # --- matière
    tex = texture(V, mat, W, H, seed)
    # profondeur : distance (cases) au vide le plus proche -> éclairage lissé
    INF = 99
    dist = [[0 if not solid[cy][cx] else INF for cx in range(COLS)] for cy in range(ROWS)]
    for _ in range(6):
        for cy in range(ROWS):
            for cx in range(COLS):
                if dist[cy][cx]:
                    best = dist[cy][cx]
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < COLS and 0 <= ny < ROWS:
                            best = min(best, dist[ny][nx] + 1)
                    dist[cy][cx] = best
    shade = G.surf(COLS, ROWS)
    for cy in range(ROWS):
        for cx in range(COLS):
            d = dist[cy][cx]
            v = 1.0 if d <= 1 else max(0.42, 1.0 - (d - 1) * 0.2)
            c = int(255 * v)
            shade.set_at((cx, cy), (c, c, c))
    shade = pygame.transform.smoothscale(shade, (W, H))
    tex.blit(shade, (0, 0), special_flags=pygame.BLEND_MULT)

    cw, ch = int(math.ceil(V.cw)), int(math.ceil(V.ch))
    top_hl = _gradient_cell(cw, ch, lambda t: max(0, 70 * (1 - t / 0.55)) if t < 0.55 else 0, True)
    bot_sh = _gradient_cell(cw, ch, lambda t: 255 - max(0, 130 * (t - 0.35) / 0.65), False)
    side_l = G.surf(cw, ch)
    side_r = G.surf(cw, ch)
    for i in range(cw):
        t = i / max(1, cw - 1)
        pygame.draw.line(side_l, (int(max(0, 30 * (1 - t / 0.3))),) * 3, (i, 0), (i, ch))
        pygame.draw.line(side_r, (int(255 - max(0, 90 * (t - 0.7) / 0.3)),) * 3, (i, 0), (i, ch))
    rim = C(mat["rim"])
    lw = max(1, int(V.k * 0.6))
    for cy in range(ROWS):
        for cx in range(COLS):
            if not solid[cy][cx]:
                continue
            rc = V.cell(cx, cy)
            if not S(cx, cy - 1):
                tex.blit(top_hl, rc.topleft, special_flags=pygame.BLEND_ADD)
                pygame.draw.line(tex, mix(rim, mat["rock"][0], 0.35), (rc.left, rc.top + lw // 2), (rc.right, rc.top + lw // 2), lw)
            if not S(cx, cy + 1):
                tex.blit(bot_sh, rc.topleft, special_flags=pygame.BLEND_MULT)
            if not S(cx - 1, cy):
                tex.blit(side_l, rc.topleft, special_flags=pygame.BLEND_ADD)
            if not S(cx + 1, cy):
                tex.blit(side_r, rc.topleft, special_flags=pygame.BLEND_MULT)
    terrain = G.apply_mask(tex.convert_alpha() if pygame.display.get_surface() else tex, mask)

    # --- coiffes et dessous
    rng = G.rng_for("cap", seed)
    runs_top, runs_bot = [], []
    for cy in range(ROWS):
        for want, out in ((-1, runs_top), (1, runs_bot)):
            cx = 0
            while cx < COLS:
                if solid[cy][cx] and not S(cx, cy + want):
                    x0 = cx
                    while cx < COLS and solid[cy][cx] and not S(cx, cy + want):
                        cx += 1
                    out.append((x0, cx, cy))
                else:
                    cx += 1
    caps = G.surf(W, H, True)
    for x0, x1, cy in runs_top:
        draw_cap(caps, V, mat, rng, x0, x1, cy, S, seed)
    for x0, x1, cy in runs_bot:
        if cy < ROWS - 1:
            draw_under(caps, V, mat, rng, x0, x1, cy, S, seed)
    terrain.blit(caps, (0, 0))
    return terrain, mask


def draw_cap(s, V, mat, rng, x0, x1, cy, S, seed):
    kind = mat["cap"]
    c_hi, c_mid, c_lo = (C(c) for c in mat["capc"])
    k = V.k
    left_open = not S(x0 - 1, cy)
    right_open = not S(x1, cy)
    X0 = V.X(x0 * TILE) - (k * 0.8 if left_open else 0)
    X1 = V.X(x1 * TILE) + (k * 0.8 if right_open else 0)
    Y = V.Y(cy * TILE)
    if kind in ("grass", "moss", "deadgrass"):
        thick = k * (2.6 if kind == "moss" else 2.0)
        step = max(2, int(k * 0.8))
        top, bot = [], []
        n = max(2, int((X1 - X0) / step))
        for i in range(n + 1):
            x = X0 + (X1 - X0) * i / n
            e = min(i, n - i) / max(1, n) * (X1 - X0)
            edge = min(1.0, e / (k * 3.5)) if (left_open and i < n / 2) or (right_open and i >= n / 2) else 1.0
            bump = G.fbm(x / (k * 6), seed, 2) * k * (1.2 if kind == "moss" else 0.6)
            top.append((x, Y - bump * edge + k * 0.2))
            drip = thick * (0.55 + 0.6 * G.fbm(x / (k * 3), seed + 3, 3)) * edge
            bot.append((x, Y + drip))
        pygame.draw.polygon(s, c_lo, top + bot[::-1])
        top2 = [(x, y + k * 0.15) for x, y in top]
        bot2 = [(x, Y + (y - Y) * 0.6) for x, y in bot]
        pygame.draw.polygon(s, c_mid, top2 + bot2[::-1])
        pygame.draw.lines(s, c_hi, False, top, max(1, int(k * 0.6)))
        # brins
        nb = int((X1 - X0) / (k * (0.9 if kind == "grass" else 1.6)))
        for i in range(nb):
            x = X0 + rng.uniform(k, max(k * 1.1, X1 - X0 - k))
            hgt = k * rng.uniform(1.2, 3.6) * (0.6 if kind == "moss" else 1.0)
            lean = rng.uniform(-1, 1) * k * 1.0
            col = mix(c_mid, c_hi, rng.random())
            if kind == "deadgrass":
                hgt *= 1.3
                col = mix(c_lo, c_hi, rng.random() * 0.7)
            base_y = Y + k * 0.4
            pygame.draw.polygon(s, col, [(x - k * 0.45, base_y), (x + k * 0.45, base_y), (x + lean, base_y - hgt)])
        if kind != "deadgrass":
            for i in range(int((X1 - X0) / (k * 14))):            # fleurs
                x = X0 + rng.uniform(k * 2, max(k * 2.1, X1 - X0 - k * 2))
                col = rng.choice(((255, 220, 120), (255, 150, 200), (180, 200, 255), (255, 255, 255)))
                pygame.draw.line(s, c_mid, (x, Y + k * 0.3), (x, Y - k * 2.2), max(1, int(k * 0.3)))
                pygame.draw.circle(s, col, (x, Y - k * 2.4), k * 0.75)
    elif kind == "snow":
        top, bot = [], []
        n = max(2, int((X1 - X0) / (k * 0.8)))
        for i in range(n + 1):
            x = X0 + (X1 - X0) * i / n
            t = i / n
            edge = math.sin(math.pi * min(1, max(0, t))) ** 0.35
            bump = (0.8 + 0.8 * G.fbm(x / (k * 8), seed, 2)) * k * 1.6 * edge
            top.append((x, Y - bump + k * 0.4))
            bot.append((x, Y + k * (1.0 + 1.6 * G.fbm(x / (k * 4), seed + 1, 2)) * edge))
        pygame.draw.polygon(s, c_lo, top + bot[::-1])
        pygame.draw.polygon(s, c_mid, top + [(x, y - k * 0.6) for x, y in bot[::-1]])
        pygame.draw.polygon(s, c_hi, top + [(x, (y + Y) / 2 - k * 0.8) for x, y in top[::-1]])
        for i in range(int((X1 - X0) / (k * 5))):
            x = X0 + rng.uniform(0, X1 - X0)
            pygame.draw.circle(s, (255, 255, 255), (x, Y - k * 0.3 * rng.random()), max(1, k * 0.3))
    elif kind in ("ledge", "gold", "obsidian"):
        h = k * 1.8
        r = pygame.Rect(int(X0 - k * 0.6), int(Y - k * 0.2), int(X1 - X0 + k * 1.2), int(h))
        pygame.draw.rect(s, c_lo, r.move(0, k * 0.5), border_radius=int(k * 0.8))
        pygame.draw.rect(s, c_mid, r, border_radius=int(k * 0.8))
        pygame.draw.line(s, c_hi, (r.left + k, r.top + 1), (r.right - k, r.top + 1), max(1, int(k * 0.5)))
        if kind == "gold":
            for xx in range(int(r.left + k * 3), int(r.right - k * 2), int(k * 6)):
                pygame.draw.circle(s, c_hi, (xx, r.centery + k * 0.2), k * 0.5)
        if kind == "obsidian":
            pygame.draw.line(s, (255, 60, 100), (r.left + k, r.bottom), (r.right - k, r.bottom), max(1, int(k * 0.4)))
    elif kind == "dust":
        top = []
        n = max(2, int((X1 - X0) / (k * 1.2)))
        for i in range(n + 1):
            x = X0 + (X1 - X0) * i / n
            top.append((x, Y - G.fbm(x / (k * 5), seed, 2) * k * 0.7))
        pygame.draw.polygon(s, c_mid, top + [(X1, Y + k * 1.0), (X0, Y + k * 1.0)])
        pygame.draw.lines(s, c_hi, False, top, max(1, int(k * 0.5)))
        for i in range(int((X1 - X0) / (k * 16))):                 # petits os
            x = X0 + rng.uniform(k * 3, max(k * 3.1, X1 - X0 - k * 3))
            pygame.draw.line(s, (220, 214, 196), (x - k * 1.5, Y - k * 0.4), (x + k * 1.5, Y - k * 0.8), max(1, int(k * 0.7)))
    elif kind == "ember":
        top = []
        n = max(2, int((X1 - X0) / (k * 1.0)))
        for i in range(n + 1):
            x = X0 + (X1 - X0) * i / n
            top.append((x, Y - G.fbm(x / (k * 4), seed, 2) * k * 0.6))
        pygame.draw.polygon(s, c_lo, top + [(X1, Y + k * 1.4), (X0, Y + k * 1.4)])
        glow = G.surf(int(X1 - X0 + k * 8), int(k * 6), True)
        pygame.draw.line(glow, (255, 120, 30, 200), (k * 4, k * 3), (glow.get_width() - k * 4, k * 3), max(1, int(k * 1.2)))
        s.blit(G.blur(glow, 3), (X0 - k * 4, Y - k * 3))
        pygame.draw.lines(s, c_hi, False, top, max(1, int(k * 0.5)))
        for i in range(int((X1 - X0) / (k * 4))):                  # fissures incandescentes
            x = X0 + rng.uniform(k, max(k * 1.1, X1 - X0 - k))
            pygame.draw.line(s, c_mid, (x, Y), (x + rng.uniform(-k, k), Y + k * rng.uniform(1.5, 4)), max(1, int(k * 0.4)))
    elif kind == "crystal":
        pygame.draw.line(s, c_lo, (X0, Y + k * 0.4), (X1, Y + k * 0.4), max(1, int(k * 0.8)))
        for i in range(int((X1 - X0) / (k * 5)) + 1):
            x = X0 + rng.uniform(k, max(k * 1.1, X1 - X0 - k))
            hgt = k * rng.uniform(2, 5)
            w = k * rng.uniform(0.8, 1.6)
            lean = rng.uniform(-1, 1) * k
            pts = [(x - w, Y + k * 0.5), (x - w * 0.6, Y - hgt * 0.7), (x + lean, Y - hgt), (x + w * 0.6, Y - hgt * 0.7), (x + w, Y + k * 0.5)]
            pygame.draw.polygon(s, c_mid, pts)
            pygame.draw.polygon(s, c_hi, [pts[1], pts[2], (x, Y)])
        pygame.draw.line(s, c_hi, (X0, Y), (X1, Y), max(1, int(k * 0.4)))


def draw_under(s, V, mat, rng, x0, x1, cy, S, seed):
    kind = mat["under"]
    k = V.k
    X0, X1 = V.X(x0 * TILE), V.X(x1 * TILE)
    Y = V.Y((cy + 1) * TILE)
    if kind == "none":
        return
    n = int((X1 - X0) / (k * (5 if kind in ("roots", "vines") else 6)))
    for i in range(n):
        x = X0 + rng.uniform(k * 1.5, max(k * 1.6, X1 - X0 - k * 1.5))
        if kind in ("roots", "vines"):
            L = k * rng.uniform(2, 9)
            col = (C(mat["capc"][2]) if kind == "vines" else mul(mat["rock"][1], 1.3))
            pts = [(x + math.sin(j * 0.9 + x) * k * 0.7, Y - k * 0.3 + L * j / 6) for j in range(7)]
            pygame.draw.lines(s, col, False, pts, max(1, int(k * 0.5)))
            if kind == "vines":
                for j in range(1, 6, 2):
                    px_, py_ = pts[j]
                    pygame.draw.ellipse(s, C(mat["capc"][1]), (px_ - k * 0.2, py_ - k * 0.4, k * 1.4, k * 0.9))
        elif kind in ("icicles", "stalactites"):
            L = k * rng.uniform(1.5, 5)
            w = k * rng.uniform(0.7, 1.4)
            col = C("#d8ecff") if kind == "icicles" else mul(mat["rock"][1], 1.4)
            pygame.draw.polygon(s, col, [(x - w, Y - k * 0.3), (x + w, Y - k * 0.3), (x, Y + L)])
            if kind == "icicles":
                pygame.draw.line(s, (255, 255, 255), (x - w * 0.4, Y), (x - w * 0.1, Y + L * 0.6), max(1, int(k * 0.3)))
        elif kind == "drips":
            if rng.random() < 0.5:
                L = k * rng.uniform(1, 3)
                pygame.draw.polygon(s, mul(mat["rock"][1], 1.6), [(x - k * 0.6, Y - k * 0.2), (x + k * 0.6, Y - k * 0.2), (x, Y + L)])
        elif kind == "chains":
            if rng.random() < 0.35:
                L = rng.randrange(2, 6)
                for j in range(L):
                    pygame.draw.ellipse(s, (70, 80, 80), (x - k * 0.6, Y + j * k * 1.8, k * 1.2, k * 2.0), max(1, int(k * 0.35)))


def build_background(V, rid, tiles, sprites_fn=None):
    """Fond complet d'une salle (sans les éléments animés) : retourne (surface, terrain_mask)."""
    a = art(rid)
    key = art_key(rid)
    W, H = V.W, V.PH
    rng = G.rng_for("room", rid)
    s = G.vgradient(W, H, [(p, C(c)) for p, c in a["sky"]])
    BG[key](s, V, rng, rid, a)
    # profondeur : le fond est assombri (haut/bas) pour détacher nettement le terrain
    t, m, b = a.get("bgmul", (0.85, 1.0, 0.9))
    veil = G.vgradient(W, H, [(0, mul((255, 255, 255), t)), (0.5, mul((255, 255, 255), m)), (1, mul((255, 255, 255), b))])
    s.blit(veil, (0, 0), special_flags=pygame.BLEND_MULT)
    room = ROOMS[rid]
    drng = G.rng_for("decor", rid)
    for d in room["decor"]:
        paint_decor(s, V, d[0], d[1], d[2], a, drng)
    if sprites_fn:
        sprites_fn(s)
    terrain, mask = build_terrain(V, tiles, a, G.h32("terrain", rid))
    # ombre portée + occlusion ambiante du terrain sur le fond
    sh = G.tinted(mask, (0, 0, 0))
    sh = G.blur(sh, max(4, int(V.k * 2.5)))
    sh.set_alpha(190)
    s.blit(sh, (V.k * 1.2, V.k * 2.2))
    s.blit(terrain, (0, 0))
    return G.opt(s), mask
