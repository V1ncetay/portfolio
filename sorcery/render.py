"""Rendu procédural façon Amstrad CPC Mode 0 (160x200, 16 couleurs, pixels 2:1).

Deux couches : `base` (160x200, graphismes) et `text` (320x200, texte du HUD façon
Mode 1), mises à l'échelle 6x3 et 3x3 vers une surface 960x600 + scanlines.
"""
import math
import random

import pygame

from config import (PALETTE, LOGICAL_W, LOGICAL_H, TEXT_W, TEXT_H, WINDOW_W, WINDOW_H, TILE,
                    COLS, ROWS, PLAY_W, PLAY_H, HUD_Y, ENERGY_MAX, TIME_LIMIT_MIN)
import font
import sprites
from world import (ROOMS, OBJECTS, DOORS, CAPTIVES, ZONES, SOLID, FAKE, WATER, zone_theme,
                   doors_in_room, opening_cells)
from game import ITEM_W, ITEM_H, CAGE_W, CAGE_H, CAULDRON_W, CAULDRON_H

P = PALETTE


def C(i):
    return P[i]


def art_surface(art, recolor=None):
    h = len(art)
    w = max(len(r) for r in art)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(art):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            idx = int(ch, 16)
            if recolor:
                idx = recolor.get(idx, idx)
            s.set_at((x, y), P[idx] + (255,))
    return s


def silhouette(surf, color):
    """Version unie du sprite (clignotement de dégâts)."""
    return pygame.mask.from_surface(surf).to_surface(setcolor=P[color] + (255,), unsetcolor=(0, 0, 0, 0))


def _h(*v):
    x = 2166136261
    for n in v:
        x = ((x ^ (n & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return x


# ------------------------------------------------------------------------- tuiles
def paint_tile(theme, cx, cy, top, seed=0):
    s = pygame.Surface((TILE, TILE))
    hv = _h(cx, cy, seed)

    def px(x, y, c):
        s.set_at((x, y), P[c])

    if theme == "landes":
        s.fill(P[10])
        for i in range(5):
            r = _h(hv, i)
            px(r % 8, (r >> 3) % 8, 3 if i % 2 else 0)
        if top:
            for x in range(8):
                px(x, 0, 7)
                px(x, 1, 7 if (x + cx) % 3 else 6)
                if (x * 5 + cx) % 4 == 0:
                    px(x, 2, 6)
    elif theme == "bois":
        s.fill(P[10])
        gx = hv % 8
        for y in range(8):
            px((gx + y // 3) % 8, y, 3)
            px((gx + 4 + y // 4) % 8, y, 3)
        px((hv >> 4) % 8, (hv >> 8) % 8, 0)
        if top:
            for x in range(8):
                px(x, 0, 7 if (x + cx) % 2 else 6)
                px(x, 1, 6)
                if (x + hv) % 3 == 0:
                    px(x, 2, 6)
    elif theme == "riviere":
        s.fill(P[14])
        for i in range(4):
            r = _h(hv, i)
            px(r % 8, (r >> 3) % 8, 0)
        px((hv >> 6) % 8, (hv >> 9) % 8, 15)
        if top:
            for x in range(8):
                px(x, 0, 6 if (x + cx) % 3 else 7)
                px(x, 1, 15 if x % 2 else 14)
    elif theme == "chateau":
        s.fill(P[3])
        off = 0 if cy % 2 == 0 else 4
        for x in range(8):
            px(x, 3, 0)
            px(x, 7, 0)
        for y in range(3):
            px((off) % 8, y, 0)
            px((off + 4) % 8, y + 4, 0)
        px((off + 1) % 8, 0, 4)
        px((off + 5) % 8, 4, 4)
        if top:
            for x in range(8):
                px(x, 0, 14)
                px(x, 1, 15 if x % 4 == 0 else 14)
    elif theme == "catacombes":
        s.fill(P[14])
        off = 0 if cy % 2 == 0 else 4
        for x in range(8):
            px(x, 7, 0)
        px((off + 7) % 8, 0, 0)
        for y in range(7):
            px((off + 7) % 8, y, 0)
        px((off + 0) % 8, 0, 15)
        px((off + 1) % 8, 0, 15)
        r = hv % 7
        px((r + 2) % 7, (hv >> 5) % 6 + 1, 0)
        if top:
            for x in range(8):
                px(x, 0, 15 if x % 2 else 14)
    elif theme == "palais":
        s.fill(P[9])
        d = hv % 8
        for i in range(8):
            px((d + i) % 8, i, 15)
        px((d + 3) % 8, (hv >> 3) % 8, 2)
        px((d + 4) % 8, ((hv >> 3) + 1) % 8, 2)
        if top:
            for x in range(8):
                px(x, 0, 11)
                px(x, 1, 12 if x % 2 else 11)
    elif theme == "stonehenge":
        s.fill(P[14])
        for i in range(6):
            r = _h(hv, i)
            px(r % 8, (r >> 3) % 8, 15 if i < 3 else 0)
        if top:
            for x in range(8):
                px(x, 0, 7 if (x + cx) % 2 else 6)
                px(x, 1, 6)
    else:  # antre
        s.fill(P[3])
        x = hv % 8
        for y in range(8):
            px(x, y, 13 if y % 3 else 0)
            x = (x + (1 if (hv >> y) & 1 else -1)) % 8
        if top:
            for x in range(8):
                px(x, 0, 12)
                px(x, 1, 4 if x % 2 else 12)
    return s


class Renderer:
    def __init__(self):
        self.base = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.text = pygame.Surface((TEXT_W, TEXT_H), pygame.SRCALPHA)
        self.out = pygame.Surface((WINDOW_W, WINDOW_H))
        self.scanlines = True
        self.scan = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        for y in range(2, WINDOW_H, 3):
            pygame.draw.line(self.scan, (0, 0, 0, 80), (0, y), (WINDOW_W - 1, y))
        self._glyphs = {}
        self._bg = {}
        self.t = 0
        self._build_sprites()
        self._build_dark_mask()
        rng = random.Random(42)
        self.stars = []
        while len(self.stars) < 45:
            x, y = rng.randrange(0, 160), rng.randrange(0, 90)
            if 4 <= y <= 54 and 14 <= x <= 146:
                continue          # pas d'étoiles sous le logo et le sous-titre
            self.stars.append((x, y, rng.choice((15, 14, 9, 11)), rng.randrange(0, 60)))

    # ------------------------------------------------------------------ sprites
    def _build_sprites(self):
        S = {}

        def both(name, art, recolor=None):
            s = art_surface(art, recolor)
            S[name] = s
            S[name + "_l"] = pygame.transform.flip(s, True, False)

        for i, a in enumerate(sprites.WIZARD):
            both("wiz%d" % i, a)
        both("wiz_stand", sprites.WIZARD_STAND)
        cap = {2: 6, 9: 7}
        for i, a in enumerate(sprites.WIZARD):
            both("cap%d" % i, a, cap)
        both("cap_stand", sprites.WIZARD_STAND, cap)
        S["wiz_white"] = silhouette(S["wiz0"], 15)
        S["wiz_white_l"] = pygame.transform.flip(S["wiz_white"], True, False)
        for i, a in enumerate(sprites.NECRO):
            sm = art_surface(a)
            S["necro_small%d" % i] = sm
            S["necro%d" % i] = pygame.transform.scale(sm, (sm.get_width() * 2, sm.get_height() * 2))
        S["necro_white"] = silhouette(S["necro0"], 15)
        for name, frames in (("skull", sprites.SKULL), ("ghost", sprites.GHOST), ("bat", sprites.BAT),
                             ("spider", sprites.SPIDER), ("fish", sprites.FISH), ("guard", sprites.GUARD),
                             ("fireball", sprites.FIREBALL), ("cauldron", sprites.CAULDRON)):
            for i, a in enumerate(frames):
                both("%s%d" % (name, i), a)
        for i, a in enumerate(sprites.CAULDRON):
            both("cauldron_m%d" % i, a, {7: 4})
        for oid, art in sprites.ITEMS.items():
            rows = list(art)
            while len(rows) < ITEM_H:
                rows.insert(0, "." * 7)
            S["item_" + oid] = art_surface(rows)
        S["free_on"] = art_surface(sprites.FREE_ICON)
        S["free_off"] = art_surface(sprites.FREE_ICON, {6: 14, 8: 14, 15: 14})
        self.spr = S

    def item_sprite(self, oid):
        kind = OBJECTS[oid]["kind"]
        return self.spr["item_potion" if kind == "potion" else "item_" + oid]

    def _build_dark_mask(self):
        w, h = PLAY_W * 2, PLAY_H * 2
        m = pygame.Surface((w, h), pygame.SRCALPHA)
        m.fill((0, 0, 0, 255))
        rx, ry = 27.0, 46.0
        cx, cy = w // 2, h // 2
        for y in range(int(cy - ry * 1.4), int(cy + ry * 1.4) + 1):
            for x in range(int(cx - rx * 1.4), int(cx + rx * 1.4) + 1):
                d = math.hypot((x - cx) / rx, (y - cy) / ry)
                if d < 1.0 or (d < 1.3 and (x + y) % 2 == 0) or (d < 1.4 and x % 2 == 0 and y % 2 == 0):
                    m.set_at((x, y), (0, 0, 0, 0))
        self.dark = m

    # ------------------------------------------------------------------ texte
    def glyph(self, ch, color):
        key = (ch, color)
        g = self._glyphs.get(key)
        if g is None:
            rows = font.ROWS.get(ch) or font.ROWS["?"]
            g = pygame.Surface((font.GLYPH_W, font.GLYPH_H), pygame.SRCALPHA)
            for y, row in enumerate(rows):
                for x, c in enumerate(row):
                    if c == "#":
                        g.set_at((x, y), P[color] + (255,))
            self._glyphs[key] = g
        return g

    def text_width(self, s, sx=1):
        return len(font.normalize(s)) * font.CELL_W * sx

    def draw_text(self, x, y, s, color=15, layer="hi", sx=1, sy=1, shadow=None):
        dest = self.text if layer == "hi" else self.base
        s = font.normalize(s)
        for i, ch in enumerate(s):
            if ch == " ":
                continue
            gx = x + i * font.CELL_W * sx
            for col, ox, oy in (((shadow, 1, 1),) if shadow is not None else ()) + ((color, 0, 0),):
                g = self.glyph(ch, col)
                if sx != 1 or sy != 1:
                    g = pygame.transform.scale(g, (font.GLYPH_W * sx, font.GLYPH_H * sy))
                dest.blit(g, (gx + ox * sx, y + oy * sy))

    def center_text(self, y, s, color=15, layer="hi", sx=1, sy=1, shadow=None):
        w = TEXT_W if layer == "hi" else LOGICAL_W
        self.draw_text((w - self.text_width(s, sx)) // 2, y, s, color, layer, sx, sy, shadow)

    # ------------------------------------------------------------------ salle
    def room_bg(self, rid, tiles):
        bg = self._bg.get(rid)
        if bg is not None:
            return bg
        theme = zone_theme(rid)
        room = ROOMS[rid]
        s = pygame.Surface((PLAY_W, PLAY_H))
        rng = random.Random(_h(len(rid), ord(rid[0]), ord(rid[1])))
        self._paint_background(s, theme, rng, tiles)
        for d in room["decor"]:
            self._paint_decor(s, d[0], d[1], d[2])
        for cy in range(ROWS):
            for cx in range(COLS):
                k = tiles[cy][cx]
                if k in (SOLID, FAKE):
                    above = tiles[cy - 1][cx] if cy > 0 else SOLID
                    top = above not in (SOLID, FAKE) and above != WATER
                    s.blit(paint_tile(theme, cx, cy, top, len(rid)), (cx * TILE, cy * TILE))
        self._bg[rid] = s
        return s

    def _paint_background(self, s, theme, rng, tiles):
        def dither(rect, c1, c2):
            x0, y0, w, h = rect
            for y in range(y0, y0 + h):
                for x in range(x0, x0 + w):
                    if (x + y) % 2 == 0:
                        s.set_at((x, y), P[c2])
                    else:
                        s.set_at((x, y), P[c1])

        if theme in ("landes", "riviere"):
            s.fill(P[0])
            for _ in range(28):
                s.set_at((rng.randrange(8, 152), rng.randrange(8, 90)), P[rng.choice((15, 14, 9))])
            # collines lointaines
            base = 128
            ph1, ph2 = rng.uniform(0, 6.28), rng.uniform(0, 6.28)
            for x in range(PLAY_W):
                hgt = int(14 + 8 * math.sin(x * 0.045 + ph1) + 4 * math.sin(x * 0.11 + ph2))
                pygame.draw.line(s, P[1], (x, base - hgt), (x, PLAY_H))
            if theme == "riviere":
                for x in range(8, 152, 7):
                    hh = rng.randrange(6, 14)
                    pygame.draw.line(s, P[6], (x, 136 - hh), (x, 136))
                    s.set_at((x, 136 - hh), P[10])
        elif theme == "bois":
            s.fill(P[0])
            for _ in range(6):
                x = rng.randrange(6, 146)
                w = rng.randrange(3, 6)
                pygame.draw.rect(s, P[3], (x, 0, w, PLAY_H))
                pygame.draw.line(s, P[10], (x, 0), (x, PLAY_H))
                for _ in range(3):
                    by = rng.randrange(20, 120)
                    pygame.draw.line(s, P[3], (x, by), (x - rng.randrange(4, 10), by - 6))
            for _ in range(14):
                cx, cy = rng.randrange(0, 160), rng.randrange(0, 40)
                pygame.draw.ellipse(s, P[6], (cx - 10, cy - 6, 20, 12))
                for _ in range(6):
                    s.set_at((cx + rng.randrange(-8, 8), cy + rng.randrange(-4, 4)), P[7])
            for _ in range(5):
                s.set_at((rng.randrange(10, 150), rng.randrange(50, 130)), P[11])
        elif theme == "chateau":
            s.fill(P[0])
            for y in range(0, PLAY_H, 6):
                off = 0 if (y // 6) % 2 == 0 else 6
                pygame.draw.line(s, P[1], (0, y), (PLAY_W, y))
                for x in range(off, PLAY_W, 12):
                    pygame.draw.line(s, P[1], (x, y), (x, y + 5))
        elif theme == "catacombes":
            s.fill(P[0])
            for y in range(0, PLAY_H, 8):
                off = 0 if (y // 8) % 2 == 0 else 8
                for x in range(off, PLAY_W, 16):
                    pygame.draw.rect(s, P[1], (x, y, 16, 8), 1)
            for _ in range(5):
                x, y = rng.randrange(16, 140), rng.randrange(16, 120)
                pygame.draw.rect(s, P[0], (x - 1, y - 1, 9, 9))
                s.blit(self.spr["skull0"], (x, y))
        elif theme == "palais":
            s.fill(P[1])
            for x in range(0, PLAY_W, 4):
                for y in range(0, PLAY_H, 4):
                    if (x // 4 + y // 4) % 2 == 0:
                        s.set_at((x, y), P[2])
        elif theme == "stonehenge":
            s.fill(P[0])
            dither((0, 0, PLAY_W, 22), 5, 1)
            dither((0, 22, PLAY_W, 18), 1, 0)
            pygame.draw.ellipse(s, P[15], (122, 44, 10, 18))
            pygame.draw.ellipse(s, P[0], (125, 43, 10, 18))
            for _ in range(20):
                s.set_at((rng.randrange(8, 152), rng.randrange(50, 100)), P[rng.choice((15, 14))])
            for x in range(PLAY_W):
                hgt = int(12 + 6 * math.sin(x * 0.07))
                pygame.draw.line(s, P[1], (x, 130 - hgt), (x, PLAY_H))
            # trilithons lointains (silhouettes)
            for x0 in (rng.randrange(14, 50), rng.randrange(90, 128)):
                for px_ in (x0, x0 + 14):
                    pygame.draw.rect(s, P[14], (px_, 96, 5, 48))
                    pygame.draw.line(s, P[0], (px_ + 4, 96), (px_ + 4, 143))
                pygame.draw.rect(s, P[14], (x0 - 2, 90, 23, 6))
                pygame.draw.line(s, P[15], (x0 - 2, 90), (x0 + 20, 90))
        else:  # antre
            s.fill(P[0])
            for y in range(PLAY_H):
                for x in range(PLAY_W):
                    if (x * 7 + y * 3) % 29 == 0 or ((x + y) % 2 == 0 and y > 132) or \
                            ((x + y) % 4 == 0 and y > 120):
                        s.set_at((x, y), P[3])
            for _ in range(12):
                x, y = rng.randrange(10, 150), rng.randrange(10, 140)
                pygame.draw.line(s, P[5], (x, y), (x + rng.randrange(-6, 6), y + rng.randrange(4, 12)))

    def _paint_decor(self, s, kind, tx, ty):
        x, y = tx * TILE, ty * TILE
        if kind == "tower":
            pygame.draw.rect(s, P[14], (x, y + 6, 28, PLAY_H - y - 14))
            for yy in range(y + 6, PLAY_H - 8, 5):
                off = 0 if (yy // 5) % 2 else 3
                pygame.draw.line(s, P[0], (x, yy), (x + 27, yy))
                for xx in range(x + off, x + 28, 7):
                    pygame.draw.line(s, P[0], (xx, yy), (xx, yy + 4))
            for i in range(4):
                pygame.draw.rect(s, P[14], (x + i * 8, y, 4, 6))
            pygame.draw.polygon(s, P[2], [(x - 2, y), (x + 30, y), (x + 14, y - 14)])
            pygame.draw.rect(s, P[11], (x + 11, y + 20, 5, 9))
            pygame.draw.rect(s, P[11], (x + 11, y + 44, 5, 9))
            pygame.draw.rect(s, P[0], (x + 10, PLAY_H - 30, 8, 22))
        elif kind == "window":
            pygame.draw.rect(s, P[2], (x, y, 10, 18))
            pygame.draw.ellipse(s, P[2], (x, y - 5, 10, 10))
            pygame.draw.line(s, P[0], (x + 5, y - 4), (x + 5, y + 17))
            pygame.draw.line(s, P[0], (x, y + 8), (x + 9, y + 8))
            s.set_at((x + 2, y + 3), P[15])
        elif kind == "chains":
            for yy in range(y, y + 50, 3):
                s.set_at((x + (yy // 3) % 2, yy), P[14])
            pygame.draw.circle(s, P[14], (x + 1, y + 52), 3, 1)
        elif kind == "column":
            pygame.draw.rect(s, P[15], (x - 1, y, 6, PLAY_H - y - 8))
            pygame.draw.line(s, P[9], (x + 1, y), (x + 1, PLAY_H - 9))
            pygame.draw.rect(s, P[11], (x - 3, y, 10, 3))
            pygame.draw.rect(s, P[11], (x - 3, PLAY_H - 11, 10, 3))
        elif kind == "banner":
            pygame.draw.rect(s, P[4], (x, y, 8, 22))
            pygame.draw.polygon(s, P[1], [(x, y + 22), (x + 8, y + 22), (x + 4, y + 17)])
            pygame.draw.rect(s, P[11], (x - 1, y, 10, 2))
            pygame.draw.rect(s, P[11], (x + 3, y + 7, 2, 6))
            pygame.draw.rect(s, P[11], (x + 1, y + 9, 6, 2))
        elif kind == "altar":
            pygame.draw.rect(s, P[14], (x, y + 4, 40, 12))
            pygame.draw.rect(s, P[15], (x, y + 4, 40, 2))
            pygame.draw.rect(s, P[0], (x + 4, y + 8, 32, 6))
            for i in range(0, 40, 8):
                s.set_at((x + i + 4, y + 10), P[13])

    # ------------------------------------------------------------------ jeu
    def draw_game(self, g):
        self.t += 1
        b = self.base
        b.fill(P[0])
        b.set_clip((0, 0, PLAY_W, PLAY_H))
        rid = g.room_id
        room = ROOMS[rid]
        b.blit(self.room_bg(rid, g.tiles[rid]), (0, 0))
        tick = g.tick
        # décor animé : torches
        for d in room["decor"]:
            if d[0] == "torch":
                x, y = d[1] * TILE, d[2] * TILE
                pygame.draw.rect(b, P[10], (x + 1, y + 4, 2, 6))
                f = (tick // 4) % 3
                b.set_at((x + 1 + (f == 1), y + 1), P[11])
                pygame.draw.rect(b, P[12], (x, y + 2, 4, 2))
                b.set_at((x + 1 + f % 2, y + 3), P[4])
        # eau animée
        if room["water"]:
            for cy in range(ROWS):
                for cx in range(COLS):
                    if g.tiles[rid][cy][cx] == WATER:
                        self._water(b, cx, cy, tick, g.tiles[rid])
        # portes
        for did, direction in doors_in_room(rid):
            if did not in g.doors_open:
                for cx, cy in opening_cells(direction):
                    self._door(b, DOORS[did].get("style"), cx, cy, direction, tick)
        # chaudrons
        for c in room["cauldrons"]:
            r = g.cauldron_rect(c)
            name = "cauldron%d" if c[2] == "plein" else "cauldron_m%d"
            b.blit(self.spr[name % ((tick // 10) % 2)], (r[0], r[1]))
        # captifs
        for cid, c in CAPTIVES.items():
            if c["room"] == rid and cid not in g.freed:
                self._cage(b, g.cage_rect(c), tick, cid)
        # objets
        for oid, it in g.items_here():
            sp = self.item_sprite(oid)
            y = it["y"]
            if OBJECTS[oid]["kind"] == "potion":
                y += (tick // 12) % 2
            b.blit(sp, (int(it["x"]), int(y)))
        # ennemis
        for e in g.enemies:
            if not e.active:
                continue
            if e.kind == "spider":
                pygame.draw.line(b, P[14], (int(e.x) + 3, e.thread_top), (int(e.x) + 3, int(e.y)))
            frames = 2 if e.kind not in ("fish",) else 1
            fr = (tick // (6 if e.kind == "bat" else 12) + id(e) % 2) % frames
            name = "%s%d" % (e.kind, fr)
            if e.vx < 0 and e.kind in ("skull", "guard", "fish", "ghost"):
                name += "_l"
            if e.kind == "fish" and e.vy > 0:
                sp = pygame.transform.flip(self.spr[name], False, True)
            else:
                sp = self.spr[name]
            if g.grace and (tick // 3) % 2:
                continue
            b.blit(sp, (int(e.x), int(e.y)))
        # boss
        bo = g.boss
        if bo and not bo.dead:
            self._boss(b, bo, tick)
        for fb in g.fireballs:
            b.blit(self.spr["fireball%d" % ((fb.t // 4) % 2)], (int(fb.x), int(fb.y)))
        # sorciers libérés qui s'envolent
        for fa in g.freed_anims:
            if (fa[2] // 2) % 3:
                b.blit(self.spr["cap%d" % ((fa[2] // 6) % 2)], (int(fa[0]), int(fa[1])))
        # joueur
        self._player(b, g, tick)
        # particules
        for pt in g.particles:
            if 0 <= pt[0] < PLAY_W and 0 <= pt[1] < PLAY_H:
                b.set_at((int(pt[0]), int(pt[1])), P[pt[5] if pt[4] > 8 else 14])
        # obscurité
        if room["dark"] and g.carried != "torche":
            cx, cy = g.player.center()
            b.blit(self.dark, (int(cx) - PLAY_W, int(cy) - PLAY_H))
        b.set_clip(None)
        self.draw_hud(g)

    def _water(self, b, cx, cy, tick, tiles):
        x, y = cx * TILE, cy * TILE
        pygame.draw.rect(b, P[1], (x, y, TILE, TILE))
        surface = cy == 0 or tiles[cy - 1][cx] != WATER
        for i in range(TILE):
            ph = (x + i + tick // 6) % 8
            if surface:
                b.set_at((x + i, y + (1 if ph < 4 else 0)), P[9 if ph in (0, 1) else 2])
                b.set_at((x + i, y + 3 + (ph // 4)), P[2])
            else:
                if (x + i + y + tick // 10) % 6 == 0:
                    b.set_at((x + i, y + 2 + (i % 4)), P[2])

    def _door(self, b, style, cx, cy, direction, tick):
        x, y = cx * TILE, cy * TILE
        if style == "bois":
            pygame.draw.rect(b, P[10], (x, y, 8, 8))
            pygame.draw.line(b, P[3], (x + 3, y), (x + 3, y + 7))
            pygame.draw.line(b, P[0], (x, y + 7), (x + 7, y + 7))
            b.set_at((x + 1, y + 3), P[11])
            b.set_at((x + 6, y + 3), P[11])
        elif style == "rune":
            pygame.draw.rect(b, P[5], (x, y, 8, 8))
            on = (tick // 8 + cx) % 4
            col = P[13] if on else P[9]
            pygame.draw.line(b, col, (x + 1, y + 1), (x + 6, y + 6))
            pygame.draw.line(b, col, (x + 6, y + 1), (x + 1, y + 6))
        elif style == "trappe":
            pygame.draw.rect(b, P[10], (x, y, 8, 8))
            pygame.draw.line(b, P[0], (x, y + 3), (x + 7, y + 3))
            pygame.draw.line(b, P[0], (x + 7, y), (x + 7, y + 7))
            b.set_at((x + 3, y + 1), P[14])
            b.set_at((x + 3, y + 5), P[14])
        elif style == "herse":
            pygame.draw.rect(b, P[0], (x, y, 8, 8))
            for i in (1, 4, 7):
                pygame.draw.line(b, P[14], (x + i, y), (x + i, y + 7))
            pygame.draw.line(b, P[14], (x, y + 4), (x + 7, y + 4))
            b.set_at((x + 4, y + 7), P[15])
        elif style == "or":
            pygame.draw.rect(b, P[11], (x, y, 8, 8))
            pygame.draw.rect(b, P[12], (x + 1, y + 1, 6, 6), 1)
            b.set_at((x + 3, y + 3), P[15])
        else:  # portail
            for yy in range(8):
                for xx in range(8):
                    v = (xx + yy * 2 + tick // 3 + cx * 3) % 6
                    b.set_at((x + xx, y + yy), P[(13, 5, 0, 5, 13, 15)[v]])

    def _cage(self, b, r, tick, cid):
        x, y = int(r[0]), int(r[1])
        fr = (tick // 20 + len(cid)) % 2
        name = "cap%d" % fr if fr else "cap_stand"
        b.blit(self.spr[name + ("_l" if len(cid) % 2 else "")], (x + 4, y + 5))
        for i in range(0, CAGE_W, 3):
            pygame.draw.line(b, P[14], (x + i, y + 2), (x + i, y + CAGE_H - 1))
        pygame.draw.rect(b, P[10], (x, y, CAGE_W, 2))
        pygame.draw.rect(b, P[10], (x, y + CAGE_H - 2, CAGE_W, 2))
        b.set_at((x + CAGE_W // 2, y - 1), P[10])

    def _boss(self, b, bo, tick):
        x, y = int(bo.x), int(bo.y)
        if bo.phase == "dying":
            if (tick // 2) % 2:
                b.blit(self.spr["necro_white"], (x, y))
            return
        if bo.phase in ("appear", "vanish"):
            prog = bo.timer / bo.FADE
            vis = prog if bo.phase == "vanish" else 1 - prog
            # apparition en lignes (effet "raster")
            sp = self.spr["necro%d" % ((tick // 10) % 2)]
            for row in range(sp.get_height()):
                if (row * 37 % 20) / 20.0 < vis:
                    b.blit(sp, (x, y + row), (0, row, sp.get_width(), 1))
            return
        if bo.invuln and (tick // 3) % 2:
            b.blit(self.spr["necro_white"], (x, y))
        else:
            b.blit(self.spr["necro%d" % ((tick // 10) % 2)], (x, y))

    def _player(self, b, g, tick):
        p = g.player
        if g.state == "dying" and (tick // 3) % 2:
            return
        left = "_l" if p.facing < 0 else ""
        if p.hurt and (tick // 2) % 2:
            name = "wiz_white"
        elif p.landed and not p.moving:
            name = "wiz_stand"
        else:
            name = "wiz%d" % ((p.anim // 6) % 2)
        b.blit(self.spr[name + left], (int(p.x) - 1, int(p.y) - 2))
        # objet porté, tenu devant le sorcier (petit)
        if g.carried:
            sp = self.item_sprite(g.carried)
            small = pygame.transform.scale(sp, (4, 6))
            hx = int(p.x) + (6 if p.facing > 0 else -4)
            b.blit(small, (hx, int(p.y) + 7))

    # ------------------------------------------------------------------ HUD
    def draw_hud(self, g):
        b = self.base
        pygame.draw.rect(b, P[0], (0, HUD_Y, LOGICAL_W, LOGICAL_H - HUD_Y))
        pygame.draw.line(b, P[2], (0, HUD_Y), (LOGICAL_W - 1, HUD_Y))
        pygame.draw.line(b, P[1], (0, HUD_Y + 1), (LOGICAL_W - 1, HUD_Y + 1))
        # énergie
        y0 = HUD_Y + 4
        self.draw_text(4, y0, "ENERGIE", 15)
        frac = max(0.0, g.energy / ENERGY_MAX)
        segs = 10
        lit = int(math.ceil(frac * segs - 1e-6))
        for i in range(segs):
            col = 7 if i >= 6 else (11 if i >= 3 else 4)
            if i < lit:
                c = col
                if frac < 0.25 and (self.t // 8) % 2:
                    c = 15
            else:
                c = 1
            pygame.draw.rect(b, P[c], (26 + i * 5, y0, 4, 7))
        # temps (sablier en barre)
        self.draw_text(168, y0, "TEMPS", 15)
        tf = g.time_left / max(1, g.time_total)
        pygame.draw.rect(b, P[1], (100, y0, 40, 7))
        pygame.draw.rect(b, P[11] if tf > 0.2 else P[4], (100, y0, int(40 * tf), 7))
        s = g.time_seconds()
        self.draw_text(288, y0, "%02d:%02d" % (s // 60, s % 60), 11 if tf > 0.2 else 4)
        # objet porté
        y1 = HUD_Y + 15
        self.draw_text(4, y1 + 1, "OBJET", 15)
        pygame.draw.rect(b, P[1], (19, y1 - 1, 11, 12), 1)
        if g.carried:
            b.blit(self.item_sprite(g.carried), (21, y1))
            self.draw_text(66, y1 + 1, OBJECTS[g.carried]["name"], 11)
        else:
            self.draw_text(66, y1 + 1, "-", 14)
        # captifs libérés
        self.draw_text(168, y1 + 1, "LIBRES", 15)
        for i, cid in enumerate(CAPTIVES):
            b.blit(self.spr["free_on" if cid in g.freed else "free_off"], (106 + i * 6, y1 + 1))
        # score + salle
        y2 = HUD_Y + 28
        self.draw_text(4, y2, "SCORE %06d" % g.score, 9)
        name = ROOMS[g.room_id]["name"]
        self.draw_text(316 - self.text_width(name), y2, name, 13)
        # message
        y3 = HUD_Y + 39
        if g.msg_t > 0 and g.msg:
            self.center_text(y3, g.msg, g.msg_color)
        else:
            z = ZONES[ROOMS[g.room_id]["zone"]]["name"]
            self.center_text(y3, "- %s -" % z, 5)

    # ------------------------------------------------------------------ écrans
    def _sky(self, tick, horizon=True):
        b = self.base
        b.fill(P[0])
        for x, y, c, ph in self.stars:
            if (tick + ph) % 90 < 80:
                b.set_at((x, y), P[c])
        if horizon:
            pygame.draw.ellipse(b, P[15], (140, 58, 10, 18))
            pygame.draw.ellipse(b, P[0], (143, 57, 10, 18))
        if horizon:
            for x in range(LOGICAL_W):
                hgt = int(10 + 6 * math.sin(x * 0.06) + 3 * math.sin(x * 0.21))
                pygame.draw.line(b, P[1], (x, 90 - hgt), (x, 92))
            # silhouette de château
            for (x, w, h) in ((112, 6, 16), (118, 14, 10), (132, 6, 18)):
                pygame.draw.rect(b, P[1], (x, 92 - h, w, h))
                for i in range(0, w, 3):
                    pygame.draw.rect(b, P[1], (x + i, 92 - h - 2, 2, 2))

    def draw_title(self, tick, hiscore=0, time_min=TIME_LIMIT_MIN):
        self.t += 1
        self._sky(tick)
        b = self.base
        bands = (11, 12, 4, 13, 5, 2, 9, 7)
        s = "SORCERY"
        sx, sy = 2, 4
        x0 = (LOGICAL_W - len(s) * font.CELL_W * sx) // 2
        for i, ch in enumerate(s):
            rows = font.ROWS[ch]
            for gy, row in enumerate(rows):
                col = bands[(gy + i + tick // 6) % len(bands)]
                for gx, c in enumerate(row):
                    if c == "#":
                        X = x0 + i * font.CELL_W * sx + gx * sx
                        Y = 10 + gy * sy
                        pygame.draw.rect(b, P[1], (X + 1, Y + 2, sx, sy))
                        pygame.draw.rect(b, P[col], (X, Y, sx, sy))
        self.center_text(44, "UNE RECREATION HOMMAGE (CPC 1985)", 9)
        # sorcier qui vole
        wx = (tick * 0.6) % 200 - 20
        wy = 60 + 8 * math.sin(tick * 0.05)
        b.blit(self.spr["wiz%d" % ((tick // 6) % 2)], (int(wx), int(wy)))
        for k in range(1, 6):
            tx = int(wx - k * 5)
            ty = int(60 + 8 * math.sin((tick - k * 8) * 0.05)) + 14
            if 0 <= tx < 160:
                b.set_at((tx, ty), P[(11, 13, 9, 15, 5)[(k + tick // 3) % 5]])
        # panneau des contrôles
        pygame.draw.rect(b, P[1], (6, 96, 148, 78))
        pygame.draw.rect(b, P[2], (6, 96, 148, 78), 1)
        lines = [
            ("FLECHES / ZQSD / WASD : SE DEPLACER", 15),
            ("HAUT : VOLER      BAS : PLONGER", 15),
            ("ESPACE : PRENDRE / ECHANGER / POSER", 15),
            ("ESC : PAUSE      F11 : PLEIN ECRAN", 15),
            ("", 15),
            ("LIBEREZ LES 8 SORCIERS CAPTIFS AVEC", 11),
            ("LE BON OBJET, PUIS DETRUISEZ LE", 11),
            ("NECROMANCIEN. TEMPS LIMITE : %d MIN" % time_min, 11),
        ]
        for i, (l, c) in enumerate(lines):
            self.center_text(100 + i * 9, l, c)
        if (tick // 25) % 2 == 0:
            self.center_text(178, "APPUYEZ SUR ESPACE", 7)
        self.center_text(190, "MEILLEUR SCORE %06d" % hiscore, 13)

    def draw_pause(self):
        dim = pygame.Surface((PLAY_W, PLAY_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        self.base.blit(dim, (0, 0))
        pygame.draw.rect(self.base, P[1], (20, 50, 120, 50))
        pygame.draw.rect(self.base, P[2], (20, 50, 120, 50), 1)
        self.center_text(56, "PAUSE", 11, layer="lo", sx=1, sy=2)
        self.center_text(78, "ESPACE : CONTINUER", 15)
        self.center_text(88, "ESC : ABANDONNER LA PARTIE", 15)

    def draw_gameover(self, g, tick):
        self.t += 1
        b = self.base
        b.fill(P[0])
        for y in range(0, 200, 2):
            if (y + tick // 2) % 8 == 0:
                pygame.draw.line(b, P[3], (0, y), (159, y))
        big = pygame.transform.scale(self.spr["necro_small%d" % ((tick // 8) % 2)], (30, 60))
        b.blit(big, (65, 18 + int(3 * math.sin(tick * 0.08))))
        self.center_text(88, "LE NECROMANCIEN", 13, layer="lo", sx=1, sy=2, shadow=5)
        self.center_text(108, "TRIOMPHE", 4, layer="lo", sx=2, sy=3, shadow=3)
        self.center_text(140, g.lost_reason or "", 15)
        self.center_text(152, "SORCIERS LIBERES : %d / %d" % (len(g.freed), len(CAPTIVES)), 7)
        self.center_text(164, "SCORE : %06d" % g.score, 9)
        if (tick // 25) % 2 == 0:
            self.center_text(184, "ESPACE : RETOUR AU TITRE", 11)

    def draw_victory(self, g, tick):
        self.t += 1
        self._sky(tick, horizon=False)
        b = self.base
        bands = (11, 12, 11, 15, 9, 7)
        s = "VICTOIRE !"
        x0 = (LOGICAL_W - len(s) * font.CELL_W * 2) // 2
        for i, ch in enumerate(s):
            for gy, row in enumerate(font.ROWS[ch]):
                col = bands[(gy + tick // 5) % len(bands)]
                for gx, c in enumerate(row):
                    if c == "#":
                        pygame.draw.rect(b, P[col], (x0 + i * 12 + gx * 2, 10 + gy * 3, 2, 3))
        # ronde des sorciers libérés autour du héros
        cx, cy = 76, 72
        b.blit(self.spr["wiz_stand"], (cx, cy))
        for i, cid in enumerate(CAPTIVES):
            a = tick * 0.03 + i * 2 * math.pi / len(CAPTIVES)
            x = cx + 34 * math.cos(a)
            y = cy + 19 * math.sin(a)
            sp = self.spr["cap%d" % ((tick // 6 + i) % 2) + ("_l" if math.sin(a) > 0 else "")]
            if cid in g.freed:
                b.blit(sp, (int(x), int(y)))
        self.center_text(40, "LE NECROMANCIEN EST DETRUIT", 15)
        self.center_text(118, "LES SORCIERS SONT LIBRES ! (%d/%d)" % (len(g.freed), len(CAPTIVES)), 7)
        self.center_text(132, "BONUS TEMPS : %d" % g.time_bonus, 11)
        self.center_text(144, "SCORE FINAL : %06d" % g.score, 9)
        if (tick // 25) % 2 == 0:
            self.center_text(184, "ESPACE : RETOUR AU TITRE", 11)

    # ------------------------------------------------------------------ composition
    def compose(self):
        pygame.transform.scale(self.base, (WINDOW_W, WINDOW_H), self.out)
        self.out.blit(pygame.transform.scale(self.text, (WINDOW_W, WINDOW_H)), (0, 0))
        if self.scanlines:
            self.out.blit(self.scan, (0, 0))
        self.text.fill((0, 0, 0, 0))
        return self.out

    def present(self, screen):
        screen.blit(self.compose(), (0, 0))
