"""Boîte à outils graphique du rendu moderne : couleurs, dégradés, lumières radiales,
bruit, dessin anti-aliasé par sur-échantillonnage, polices. 100 % procédural (pygame seul).
"""
import math
import random
import zlib

import pygame


# ------------------------------------------------------------------ hasard stable
def h32(*parts):
    """Hash stable (zlib.crc32) : hash() de str est salé par processus."""
    return zlib.crc32(":".join(str(p) for p in parts).encode()) & 0xFFFFFFFF


def rng_for(*parts):
    return random.Random(h32(*parts))


def hnoise(i, seed=0):
    """Bruit 1D déterministe dans [0,1) pour un entier."""
    x = (i * 374761393 + seed * 668265263) & 0xFFFFFFFF
    x = ((x ^ (x >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((x ^ (x >> 16)) & 0xFFFF) / 65536.0


def smooth_noise(x, seed=0):
    """Bruit de valeur 1D lissé (continu) : x réel."""
    i = math.floor(x)
    f = x - i
    f = f * f * (3 - 2 * f)
    return hnoise(i, seed) * (1 - f) + hnoise(i + 1, seed) * f


def fbm(x, seed=0, octaves=3):
    v, a, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        v += smooth_noise(x * (2 ** o), seed + o * 17) * a
        tot += a
        a *= 0.5
    return v / tot


# ------------------------------------------------------------------ couleurs
def hexc(s):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def C(c):
    return hexc(c) if isinstance(c, str) else tuple(c)


def mix(c1, c2, t):
    c1, c2 = C(c1), C(c2)
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1[:3], c2[:3]))


def mul(c, k):
    c = C(c)
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


def add(c, d):
    c = C(c)
    return tuple(max(0, min(255, v + d)) for v in c[:3])


def rgba(c, a):
    c = C(c)
    return (c[0], c[1], c[2], max(0, min(255, int(a))))


def stops_at(stops, t):
    t = max(0.0, min(1.0, t))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            return mix(c0, c1, (t - p0) / max(1e-6, p1 - p0))
    return C(stops[-1][1])


# ------------------------------------------------------------------ surfaces
def opt(s):
    """convert()/convert_alpha() si un mode vidéo existe (blits bien plus rapides)."""
    try:
        if s.get_flags() & pygame.SRCALPHA:
            return s.convert_alpha()
        return s.convert()
    except pygame.error:
        return s


def surf(w, h, alpha=False, fill=None):
    s = pygame.Surface((max(1, int(w)), max(1, int(h))), pygame.SRCALPHA if alpha else 0)
    if fill is not None:
        s.fill(fill)
    return s


def vgradient(w, h, stops, alpha=False):
    s = surf(w, h, alpha)
    for y in range(int(h)):
        c = stops_at(stops, y / max(1, h - 1))
        if alpha:
            pass
        pygame.draw.line(s, c, (0, y), (w - 1, y))
    return s


def vgradient_alpha(w, h, color, a_stops):
    """Bande d'une couleur dont l'alpha suit a_stops [(t, a), ...]."""
    s = surf(w, h, True)
    color = C(color)
    for y in range(int(h)):
        t = y / max(1, h - 1)
        a = a_stops[-1][1]
        for (p0, a0), (p1, a1) in zip(a_stops, a_stops[1:]):
            if t <= p1:
                a = a0 + (a1 - a0) * (t - p0) / max(1e-6, p1 - p0)
                break
        pygame.draw.line(s, color + (int(a),), (0, y), (w - 1, y))
    return s


_RADIAL = {}


def radial(r, color, power=1.6, alpha=False, inner=1.0):
    """Disque à dégradé radial (pour BLEND_ADD si alpha=False, sinon alpha décroissant).
    Généré petit puis lissé par smoothscale (aucune bande visible)."""
    r = max(2, int(r))
    color = C(color)
    key = (r, color, round(power, 2), alpha, inner)
    s = _RADIAL.get(key)
    if s is not None:
        return s
    base = 48
    src = surf(base * 2, base * 2, alpha, (0, 0, 0, 0) if alpha else (0, 0, 0))
    for i in range(base, 0, -1):
        d = i / base
        f = max(0.0, 1.0 - d) ** power * inner
        if alpha:
            pygame.draw.circle(src, color + (int(255 * min(1, f)),), (base, base), i)
        else:
            pygame.draw.circle(src, mul(color, min(1.0, f)), (base, base), i)
    s = pygame.transform.smoothscale(src, (r * 2, r * 2))
    s = opt(s)
    if len(_RADIAL) > 600:
        _RADIAL.clear()
    _RADIAL[key] = s
    return s


def ellipse_light(rx, ry, color, power=1.6, alpha=False):
    key = ("e", int(rx), int(ry), C(color), power, alpha)
    s = _RADIAL.get(key)
    if s is None:
        s = opt(pygame.transform.smoothscale(radial(48, color, power, alpha), (max(2, int(rx * 2)), max(2, int(ry * 2)))))
        _RADIAL[key] = s
    return s


def blur(s, k=6):
    """Flou bon marché : réduction puis agrandissement lissés."""
    w, h = s.get_size()
    sw, sh = max(1, w // k), max(1, h // k)
    small = pygame.transform.smoothscale(s, (sw, sh))
    small = pygame.transform.smoothscale(small, (max(1, sw // 2), max(1, sh // 2)))
    return pygame.transform.smoothscale(small, (w, h))


def value_noise(w, h, cell, seed, lo=0, hi=255):
    """Bruit de valeur 2D (gris) : grille aléatoire lissée par smoothscale."""
    rng = random.Random(seed)
    gw, gh = max(2, int(w / cell) + 2), max(2, int(h / cell) + 2)
    g = surf(gw, gh)
    for y in range(gh):
        for x in range(gw):
            v = int(lo + (hi - lo) * rng.random())
            g.set_at((x, y), (v, v, v))
    big = pygame.transform.smoothscale(g, (int(gw * cell), int(gh * cell)))
    out = surf(w, h)
    out.blit(big, (-int(cell * 0.5), -int(cell * 0.5)))
    return out


def tint_noise(dst, cell, seed, lo, hi, mode=pygame.BLEND_MULT):
    n = value_noise(dst.get_width(), dst.get_height(), cell, seed, lo, hi)
    dst.blit(n, (0, 0), special_flags=mode)


def apply_mask(src, mask):
    """Copie de src dont l'alpha est celui de mask (mask blanc + alpha)."""
    out = src.copy() if src.get_flags() & pygame.SRCALPHA else src.convert_alpha()
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def tinted(s, color, keep_alpha=True):
    """Silhouette unie (même alpha)."""
    out = s.copy()
    out.fill(C(color) + (255,), special_flags=pygame.BLEND_RGB_MAX)
    out.fill(C(color) + (255,), special_flags=pygame.BLEND_RGB_MIN)
    return out


def brightened(s, k):
    out = s.copy()
    v = int(255 * min(1.0, k))
    out.fill((v, v, v, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return out


# ------------------------------------------------------------------ dessin anti-aliasé
class Pen:
    """Dessin en unités abstraites (u) sur une surface sur-échantillonnée."""

    def __init__(self, s, k, ox=0.0, oy=0.0, flip=False, w_units=0.0):
        self.s, self.k, self.ox, self.oy = s, k, ox, oy
        self.flip, self.wu = flip, w_units

    def P(self, x, y):
        if self.flip:
            x = self.wu - x
        return ((x + self.ox) * self.k, (y + self.oy) * self.k)

    def poly(self, color, pts):
        if len(pts) >= 3:
            pygame.draw.polygon(self.s, color, [self.P(x, y) for x, y in pts])

    def circle(self, color, x, y, r, width=0):
        cx, cy = self.P(x, y)
        pygame.draw.circle(self.s, color, (cx, cy), max(1, r * self.k), int(width * self.k) if width else 0)

    def ellipse(self, color, x, y, rx, ry, width=0):
        cx, cy = self.P(x, y)
        rect = pygame.Rect(0, 0, max(1, int(rx * 2 * self.k)), max(1, int(ry * 2 * self.k)))
        rect.center = (int(cx), int(cy))
        pygame.draw.ellipse(self.s, color, rect, int(width * self.k) if width else 0)

    def line(self, color, x0, y0, x1, y1, w=1.0):
        a, b = self.P(x0, y0), self.P(x1, y1)
        wk = max(1, int(w * self.k))
        pygame.draw.line(self.s, color, a, b, wk)
        if wk > 2:
            pygame.draw.circle(self.s, color, a, wk / 2)
            pygame.draw.circle(self.s, color, b, wk / 2)

    def lines(self, color, pts, w=1.0):
        for p, q in zip(pts, pts[1:]):
            self.line(color, p[0], p[1], q[0], q[1], w)

    def rect(self, color, x, y, w, h, r=0.0, width=0):
        x0, y0 = self.P(x, y)
        x1, y1 = self.P(x + w, y + h)
        rect = pygame.Rect(int(min(x0, x1)), int(min(y0, y1)), max(1, int(abs(x1 - x0))), max(1, int(abs(y1 - y0))))
        pygame.draw.rect(self.s, color, rect, int(width * self.k) if width else 0, border_radius=int(r * self.k))

    def arc_poly(self, cx, cy, rx, ry, a0, a1, n=16):
        return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n))
                for i in range(n + 1)]


def render_ss(w, h, fn, ss=3, bg=(0, 0, 0)):
    """Dessine fn(pen) sur une surface ss fois plus grande puis réduit (anti-aliasing)."""
    w, h = max(1, int(w)), max(1, int(h))
    big = pygame.Surface((w * ss, h * ss), pygame.SRCALPHA)
    big.fill(C(bg) + (0,))
    fn(big, ss)
    return opt(pygame.transform.smoothscale(big, (w, h)))


def star_points(cx, cy, r_out, r_in, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ------------------------------------------------------------------ polices
class _BitmapFont:
    """Repli si pygame.font est indisponible : police bitmap 5x7 du jeu, agrandie."""

    def __init__(self, size):
        import font as bf
        self.bf = bf
        self.k = max(1, size // 9)

    def size(self, text):
        n = len(self.bf.normalize(text))
        return (n * self.bf.CELL_W * self.k, self.bf.CELL_H * self.k if hasattr(self.bf, "CELL_H") else 8 * self.k)

    def get_height(self):
        return self.size("A")[1]

    def render(self, text, aa, color):
        text = self.bf.normalize(text)
        w, h = self.size(text)
        s = pygame.Surface((max(1, w), max(1, h)), pygame.SRCALPHA)
        for i, ch in enumerate(text):
            rows = self.bf.ROWS.get(ch) or self.bf.ROWS["?"]
            for y, row in enumerate(rows):
                for x, c in enumerate(row):
                    if c == "#":
                        s.fill(C(color) + (255,), (i * self.bf.CELL_W * self.k + x * self.k, y * self.k, self.k, self.k))
        return s


_FONTS = {}
_TEXT = {}


def font(size):
    size = max(8, int(size))
    f = _FONTS.get(size)
    if f is None:
        try:
            if not pygame.font.get_init():
                pygame.font.init()
            f = pygame.font.Font(None, size)
        except Exception:
            f = _BitmapFont(size)
        _FONTS[size] = f
    return f


def text_surface(s, size, color, shadow=None, glow=None, spacing=0):
    """Texte (anti-aliasé) avec ombre portée douce et halo optionnels ; mis en cache."""
    key = (s, int(size), C(color), shadow and C(shadow), glow and C(glow), spacing)
    t = _TEXT.get(key)
    if t is not None:
        return t
    f = font(size)
    if spacing:
        parts = [f.render(ch, True, C(color)) for ch in s]
        w = sum(p.get_width() for p in parts) + spacing * max(0, len(parts) - 1)
        h = max([p.get_height() for p in parts] + [1])
        base = pygame.Surface((max(1, w), h), pygame.SRCALPHA)
        x = 0
        for p in parts:
            base.blit(p, (x, 0))
            x += p.get_width() + spacing
    else:
        base = f.render(s, True, C(color))
        if not base.get_flags() & pygame.SRCALPHA:
            base = base.convert_alpha()
    pad = max(2, int(size * 0.35)) if (shadow or glow) else 0
    out = pygame.Surface((base.get_width() + pad * 2, base.get_height() + pad * 2), pygame.SRCALPHA)
    if glow:
        g = tinted(base, glow)
        gl = pygame.Surface(out.get_size(), pygame.SRCALPHA)
        gl.blit(g, (pad, pad))
        gl = blur(gl, max(2, int(size * 0.12)))
        out.blit(gl, (0, 0))
        out.blit(gl, (0, 0))
    if shadow:
        sh = tinted(base, shadow)
        sh.set_alpha(150)
        o = max(1, int(size * 0.07))
        out.blit(sh, (pad + o, pad + o))
    out.blit(base, (pad, pad))
    out = opt(out)
    if len(_TEXT) > 800:
        _TEXT.clear()
    _TEXT[key] = (out, pad)
    return out, pad


def draw_text(dst, s, x, y, size, color, align="left", shadow=(0, 0, 0), glow=None, spacing=0, alpha=255):
    t, pad = text_surface(s, size, color, shadow, glow, spacing)
    w = t.get_width() - pad * 2
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    if alpha < 255:
        t = t.copy()
        t.set_alpha(int(alpha))
    dst.blit(t, (int(x - pad), int(y - pad)))
    return w


def text_width(s, size, spacing=0):
    t, pad = text_surface(s, size, (255, 255, 255), None, None, spacing)
    return t.get_width() - pad * 2


def panel(w, h, r, top=(30, 32, 52), bottom=(14, 15, 28), alpha=200, border=(255, 255, 255), border_a=40):
    """Panneau « verre » arrondi semi-transparent avec liseré."""
    w, h = int(w), int(h)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    g = vgradient(w, h, [(0, top), (1, bottom)])
    g = g.convert_alpha() if pygame.display.get_init() and pygame.display.get_surface() else g
    m = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(m, (255, 255, 255, alpha), (0, 0, w, h), border_radius=int(r))
    s.blit(g, (0, 0))
    s.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    pygame.draw.rect(s, C(border) + (border_a,), (0, 0, w, h), max(1, int(r / 8)), border_radius=int(r))
    hl = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(hl, (255, 255, 255, 18), (2, 2, w - 4, h // 2), border_radius=int(r))
    s.blit(hl, (0, 0))
    return opt(s)
