"""Rendu du mode Classique : aire de jeu 160 x 144 (cellules 4 x 8, Mode 0) et bandeau
Mode 1 sous le jeu (texte « VOUS ETES ... », ENERGIE nn%, sablier), palette de jeu d'origine.

Tous les graphismes sont procéduraux ou dessinés pour ce projet (classic_sprites.py).
"""
import math
import random

import pygame

import font
import sprites
from config import (CL_PALETTE, CL_HUD_BG, CL_CELL_W, CL_CELL_H, CL_COLS, CL_ROWS, CL_PLAY_W,
                    CL_PLAY_H, CL_HUD_Y, LOGICAL_W, LOGICAL_H, PALETTE)
import classic_world as W
import classic_sprites as CS
from render import Renderer

CP = CL_PALETTE

# Encres du bandeau Mode 1 (4 couleurs) : fond bleu + jaune, cyan, blanc.
HUD_YELLOW, HUD_CYAN, HUD_WHITE = (255, 255, 0), (0, 255, 255), (255, 255, 255)

THEMES = {
    # zone : (couleurs du sol (corps, ombre, détail), dessus, style, décor de fond)
    "village":    dict(body=(2, 10, 15), top=(8, 11), style="earth", sky=True),
    "foret":      dict(body=(10, 15, 2), top=(8, 11), style="earth", sky=True, trees=True),
    "riviere":    dict(body=(14, 15, 5), top=(11, 13), style="stone", sky=True),
    "souterrain": dict(body=(15, 14, 10), top=(14, 15), style="rock"),
    "palais":     dict(body=(12, 5, 6), top=(1, 12), style="marble"),
    "chateau":    dict(body=(14, 0, 5), top=(5, 14), style="brick"),
    "cachot":     dict(body=(10, 0, 3), top=(3, 10), style="brick"),
    "landes":     dict(body=(15, 10, 11), top=(11, 8), style="earth", sky=True),
    "pierres":    dict(body=(14, 5, 15), top=(5, 14), style="stone", sky=True),
    "sanctuaire": dict(body=(7, 5, 6), top=(5, 1), style="brick"),
}


def cl_surface(art, recolor=None):
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
            s.set_at((x, y), CP[idx] + (255,))
    return s


def nearest_ink(rgb):
    return min(range(16), key=lambda i: sum((a - b) ** 2 for a, b in zip(CP[i], rgb)))


def plus_item_art(name):
    """Dessin d'objet du mode Sorcery+ requantifié vers la palette de jeu classique."""
    rows = sprites.ITEMS[name]
    out = []
    for row in rows:
        r = ""
        for ch in row:
            r += "." if ch == "." else "%X" % nearest_ink(PALETTE[int(ch, 16)])
        out.append(r)
    return out


def _h(*v):
    x = 2166136261
    for n in v:
        x = ((x ^ (n & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return x


# Couleurs des ennemis selon la zone (variation d'aspect, même comportement).
ENEMY_RECOLOR = {
    1: {"foret": {5: 8}, "riviere": {5: 4}, "souterrain": {5: 12}, "palais": {5: 7},
        "chateau": {5: 5}, "cachot": {5: 2}, "landes": {5: 13}, "pierres": {5: 14}, "village": {5: 1}},
    2: {"palais": {10: 9}, "chateau": {10: 14}, "foret": {10: 11}, "landes": {10: 15}},
    3: {"cachot": {6: 7}, "souterrain": {6: 13}, "riviere": {6: 4}},
}


class ClassicRenderer(Renderer):
    """Réutilise la composition, le texte et les scanlines du Renderer Sorcery+."""

    def _build_dark_mask(self):
        self.dark = None

    def _build_sprites(self):
        S = {}

        def both(name, art, recolor=None):
            s = cl_surface(art, recolor)
            S[name] = s
            S[name + "_l"] = pygame.transform.flip(s, True, False)

        both("stand", CS.WIZ_STAND)
        for i, a in enumerate(CS.WIZ_WALK):
            both("walk%d" % i, a)
        for i, a in enumerate(CS.WIZ_FLY):
            both("fly%d" % i, a)
        S["wiz0"] = S["fly0"]                      # icône de fenêtre
        S["white"] = pygame.mask.from_surface(S["stand"]).to_surface(setcolor=CP[5] + (255,),
                                                                     unsetcolor=(0, 0, 0, 0))
        S["white_l"] = pygame.transform.flip(S["white"], True, False)
        cap = {6: 7, 9: 10, 1: 5}
        for i, a in enumerate(CS.CAPTIVE):
            both("captive%d" % i, a, cap)
        both("freed", CS.WIZ_FLY[0], cap)
        for zone in W.ZONES:
            for t, frames in ((1, CS.CHASER), (2, CS.WALKER), (3, CS.SPECTRE)):
                rec = ENEMY_RECOLOR[t].get(zone)
                for i, a in enumerate(frames):
                    both("e%d_%s_%d" % (t, zone, i), a, rec)
        S["door"] = cl_surface(CS.DOOR)
        for k, art in CS.EMBLEM.items():
            S["emblem%d" % k] = cl_surface(art)
        S["grille"] = cl_surface(CS.GRILLE)
        S["trappe"] = cl_surface(CS.TRAPPE)
        S["cauldron"] = cl_surface(CS.CAULDRON)
        for kind in W.ITEMS:
            art = CS.ITEM_ART.get(kind) or plus_item_art(CS.ITEM_FROM_PLUS[kind])
            S["item_" + kind] = cl_surface(art)
        self.spr = S

    # ------------------------------------------------------------------ couleurs
    def glyph(self, ch, color):
        """Accepte un indice de palette Sorcery+ ou une couleur RVB (bandeau Mode 1)."""
        key = (ch, color)
        g = self._glyphs.get(key)
        if g is None:
            rgb = color if isinstance(color, tuple) else PALETTE[color]
            rows = font.ROWS.get(ch) or font.ROWS["?"]
            g = pygame.Surface((font.GLYPH_W, font.GLYPH_H), pygame.SRCALPHA)
            for y, row in enumerate(rows):
                for x, c in enumerate(row):
                    if c == "#":
                        g.set_at((x, y), rgb + (255,))
            self._glyphs[key] = g
        return g

    # ------------------------------------------------------------------ décor
    def room_surface(self, rid):
        bg = self._bg.get(("cl", rid))
        if bg is None:
            bg = self._bg[("cl", rid)] = self._paint_room(rid)
        return bg

    def _paint_room(self, rid):
        room = W.ROOMS[rid]
        th = THEMES[room["zone"]]
        s = pygame.Surface((CL_PLAY_W, CL_PLAY_H))
        s.fill(CP[0])
        rng = random.Random(_h(rid, 77))
        tiles = W.build_tiles(rid)
        if th.get("sky"):
            for _ in range(28):
                x, y = rng.randrange(CL_PLAY_W), rng.randrange(0, 70)
                s.set_at((x, y), CP[rng.choice((14, 14, 5, 6, 12))])
            if rid % 3 == 0:
                mx, my = 20 + (rid * 37) % 120, 10 + (rid * 13) % 20
                pygame.draw.circle(s, CP[12], (mx, my), 5)
                pygame.draw.circle(s, CP[0], (mx + 2, my - 1), 4)
        if th.get("trees"):
            for i in range(5):
                x = (rid * 31 + i * 37) % 150
                pygame.draw.rect(s, CP[11], (x, 30, 3, CL_PLAY_H - 38))
                for k in range(6):
                    pygame.draw.circle(s, CP[11], (x + 1 + rng.randrange(-8, 9), 24 + rng.randrange(-8, 10)),
                                       rng.randrange(4, 8))
        self._backdrop(s, room["zone"], rid, rng, tiles)
        for cy in range(CL_ROWS):
            for cx in range(CL_COLS):
                if tiles[cy][cx] == W.SOLID:
                    self._paint_solid(s, th, tiles, cx, cy, rid)
        if room["goal"]:
            gx, gy = room["goal"]
            x, y = gx * CL_CELL_W, (gy + 3) * CL_CELL_H
            pygame.draw.rect(s, CP[1], (x - 4, y, 20, 2))
            for i in range(0, 20, 4):
                s.set_at((x - 4 + i + 1, y + 4), CP[5])
        return s

    def _backdrop(self, s, zone, rid, rng, tiles):
        """Décor de fond (non solide) propre à chaque zone, en encres sombres."""
        if zone == "souterrain":                     # stalactites
            for i in range(9):
                x, h = rng.randrange(2, 156), rng.randrange(6, 22)
                for k in range(h):
                    w = max(0, (h - k) * 3 // h)
                    pygame.draw.line(s, CP[15 if k < h - 2 else 14], (x - w, k), (x + w, k))
        elif zone == "palais":                       # colonnades
            for x in range(6 + (rid % 3) * 6, 160, 44):
                pygame.draw.rect(s, CP[9], (x, 10, 8, CL_PLAY_H - 18))
                pygame.draw.rect(s, CP[9], (x - 2, 6, 12, 4))
                for k in range(2, 8, 3):
                    pygame.draw.line(s, CP[0], (x + k, 12), (x + k, CL_PLAY_H - 10))
        elif zone in ("chateau", "sanctuaire"):      # fenêtres en arc
            for i, x in enumerate(range(18 + (rid % 2) * 20, 150, 52)):
                y = 18 + (i % 2) * 10
                if any(tiles[cy][cx] != W.EMPTY for cy in range(y // 8, (y + 30) // 8 + 1)
                       for cx in range(x // 4, (x + 15) // 4 + 1)):
                    continue                     # pas de fenêtre derrière un mur
                frame = CP[14 if zone == "chateau" else 10]
                pygame.draw.rect(s, frame, (x, y + 6, 14, 22))
                pygame.draw.ellipse(s, frame, (x, y, 14, 14))
                pygame.draw.rect(s, CP[0], (x + 2, y + 7, 10, 19))
                pygame.draw.ellipse(s, CP[0], (x + 2, y + 2, 10, 12))
                pygame.draw.line(s, frame, (x + 7, y + 2), (x + 7, y + 26))
                for _ in range(3):
                    s.set_at((x + 3 + rng.randrange(8), y + 4 + rng.randrange(18)), CP[6])
        elif zone == "cachot":                       # chaînes et pierres suintantes
            for i in range(4):
                x, h = rng.randrange(10, 150), rng.randrange(20, 60)
                for k in range(0, h, 3):
                    s.set_at((x + (k // 3) % 2, k), CP[14])
                    s.set_at((x + (k // 3) % 2, k + 1), CP[14])
                pygame.draw.circle(s, CP[14], (x, h + 2), 3, 1)
            for i in range(14):
                x, y = rng.randrange(0, 150), rng.randrange(0, 130)
                pygame.draw.rect(s, CP[10], (x, y, 7, 3))

    def _paint_solid(self, s, th, tiles, cx, cy, rid):
        x0, y0 = cx * CL_CELL_W, cy * CL_CELL_H
        body, shade, det = th["body"]
        top_c, top2 = th["top"]
        above = tiles[cy - 1][cx] if cy > 0 else W.SOLID
        exposed = above not in (W.SOLID,)
        hv = _h(cx, cy, rid)
        style = th["style"]
        for yy in range(CL_CELL_H):
            for xx in range(CL_CELL_W):
                c = body
                if style == "brick":
                    row = (y0 + yy) // 4
                    joint = (yy % 4 == 3) or ((x0 + xx + (4 if row % 2 else 0)) % 8 == 7)
                    c = shade if joint else body
                elif style == "stone":
                    joint = (yy == 7) or (xx == 3 and (cx + cy) % 2 == 0)
                    c = shade if joint else (det if (hv >> (xx + yy * 4)) & 15 == 0 else body)
                elif style == "rock":
                    n = (hv >> ((xx * 3 + yy * 5) % 28)) & 7
                    c = det if n == 0 else (shade if n < 3 else body)
                elif style == "marble":
                    c = det if (xx + yy + cx) % 7 == 0 else (shade if yy == 7 else body)
                else:  # earth
                    n = (hv >> ((xx * 5 + yy * 3) % 28)) & 7
                    c = shade if n < 2 else (det if n == 7 else body)
                s.set_at((x0 + xx, y0 + yy), CP[c])
        if exposed:
            for xx in range(CL_CELL_W):
                s.set_at((x0 + xx, y0), CP[top_c])
                if style == "earth" and (hv >> xx) & 1:
                    s.set_at((x0 + xx, y0 + 1), CP[top2])
                    if (hv >> (xx + 8)) & 3 == 0:
                        s.set_at((x0 + xx, y0 - 1), CP[top_c])
                elif style != "earth":
                    s.set_at((x0 + xx, y0 + 1), CP[top2])

    def _anim_tiles(self, b, rid, tick):
        tiles = W.build_tiles(rid) if self._tiles_rid != rid else self._tiles
        self._tiles_rid, self._tiles = rid, tiles
        zone = W.ROOMS[rid]["zone"]
        f4 = (tick // 6) % 4
        for cy in range(CL_ROWS):
            for cx in range(CL_COLS):
                k = tiles[cy][cx]
                if k == W.EMPTY or k == W.SOLID:
                    continue
                x0, y0 = cx * CL_CELL_W, cy * CL_CELL_H
                if k == W.WATER:
                    pygame.draw.rect(b, CP[9], (x0, y0, CL_CELL_W, CL_CELL_H))
                    for xx in range(CL_CELL_W):
                        w = (xx + cx * 4 + f4) % 8
                        b.set_at((x0 + xx, y0 + (0 if w < 4 else 1)), CP[4])
                        if (xx + cx + f4) % 5 == 0:
                            b.set_at((x0 + xx, y0 + 4), CP[6])
                elif k == W.FIRE:
                    f2 = (tick // 5 + cx) % 2
                    for xx in range(CL_CELL_W):
                        hgt = 3 + ((cx * 7 + xx * 3 + f2 * 5) % 5)
                        for yy in range(CL_CELL_H - hgt, CL_CELL_H):
                            c = 3 if yy > CL_CELL_H - 3 else (2 if yy > CL_CELL_H - hgt + 1 else 1)
                            b.set_at((x0 + xx, y0 + yy), CP[c])
                else:
                    self._deco(b, zone, x0, y0, cx, cy, tick)

    def _deco(self, b, zone, x0, y0, cx, cy, tick):
        f4 = (tick // 8 + cx) % 4
        if zone == "riviere":                 # cascade
            for yy in range(CL_CELL_H):
                for xx in range(CL_CELL_W):
                    c = (5, 4, 6, 9)[(yy + xx + tick // 3) % 4]
                    b.set_at((x0 + xx, y0 + yy), CP[c])
        elif zone == "souterrain":            # goutte qui tombe d'une stalactite
            pygame.draw.line(b, CP[14], (x0 + 1, y0), (x0 + 2, y0 + 2))
            dy = (tick // 2 + cx * 5) % 24
            if dy < 8:
                b.set_at((x0 + 2, y0 + 3 + dy // 2), CP[4])
        elif zone in ("chateau", "palais", "cachot", "sanctuaire"):   # torche
            pygame.draw.rect(b, CP[15], (x0 + 1, y0 + 4, 2, 4))
            fl = ((1, 2, 3), (2, 1, 3), (1, 1, 2), (2, 2, 3))[f4]
            b.set_at((x0 + 1, y0 + 3), CP[fl[0]])
            b.set_at((x0 + 2, y0 + 3), CP[fl[1]])
            b.set_at((x0 + 1 + f4 % 2, y0 + 2), CP[fl[2]])
            if f4 % 2:
                b.set_at((x0 + 2, y0 + 1), CP[1])
        else:                                 # herbes / fleurs agitées par le vent
            for xx in range(CL_CELL_W):
                h = 2 + (cx * 3 + xx) % 4
                sway = (1 if (f4 + xx) % 4 == 0 else 0)
                for yy in range(h):
                    b.set_at((x0 + min(3, xx + (sway if yy > h // 2 else 0)), y0 + 7 - yy), CP[8 if xx % 2 else 11])
            if (cx * 7) % 3 == 0:
                b.set_at((x0 + 1, y0 + 7 - 3), CP[(1, 7, 5)[cx % 3]])

    # ------------------------------------------------------------------ jeu
    def draw_game(self, g):
        self.t += 1
        b = self.base
        b.fill(CP[0])
        if not hasattr(self, "_tiles_rid"):
            self._tiles_rid, self._tiles = None, None
        b.blit(self.room_surface(g.room_id), (0, 0))
        tick = g.tick
        self._anim_tiles(b, g.room_id, tick)
        room = g.room
        zone = room["zone"]
        # portes (emblème sur la face verrouillée)
        for slot, (cx, cy) in room["doors"].items():
            x, y = cx * CL_CELL_W, cy * CL_CELL_H
            b.blit(self.spr["door"], (x, y))
            lock = W.DOOR_TO[(g.room_id, slot)][2]
            if lock:
                b.blit(self.spr["emblem%d" % lock], (x + 4, y + 7))
        # barrières fermées
        for bar in g.barriers_here():
            b.blit(self.spr["grille" if bar[2] == "V" else "trappe"], (bar[3] * CL_CELL_W, bar[4] * CL_CELL_H))
        # chaudron (tous identiques : on ne sait pas lequel est empoisonné)
        if room["cauldron"]:
            cx, cy = room["cauldron"]
            x, y = cx * CL_CELL_W, cy * CL_CELL_H
            b.blit(self.spr["cauldron"], (x, y))
            for i in range(3):
                ph = (tick // 3 + i * 5) % 14
                b.set_at((x + 3 + i * 3 + (ph // 4) % 2, y + 8 - ph // 2), CP[(5, 14, 14)[i]])
            if (tick // 4) % 3 == 0:
                b.set_at((x + 4 + (tick // 12) % 4, y + 9), CP[13])
        # captif dans sa cage, ou sorciers libérés réunis au sanctuaire
        if room["captive"] and g.room_id not in g.freed:
            cx, cy = room["captive"]
            b.blit(self.spr["captive%d" % ((tick // 12) % 2) + ("_l" if cx > 20 else "")],
                   (cx * CL_CELL_W, cy * CL_CELL_H))
        if g.room_id == W.SANCTUARY:
            spots = [(5, 14), (14, 14), (8, 6), (32, 6), (18, 14), (32, 14), (36, 14), (10, 14)]
            for i, _ in enumerate(g.freed):
                sx, sy = spots[i]
                b.blit(self.spr["captive%d" % ((tick // 10 + i) % 2)], (sx * CL_CELL_W, sy * CL_CELL_H))
        # objets posés
        for it in g.items_here():
            sp = self.spr["item_" + it["kind"]]
            b.blit(sp, (it["x"] + (12 - sp.get_width()) // 2, it["y"] + 24 - sp.get_height()))
        # ennemis
        for e in g.enemies:
            if e.dying:
                self._explosion(b, e.x + 6, e.y + 12, 16 - e.dying)
                continue
            if not e.alive:
                continue
            if e.type == 1:
                name = "e1_%s_%d" % (zone, (e.anim // 4) % 2)
                left = e.x > g.player.x
            elif e.type == 2:
                name = "e2_%s_%d" % (zone, 2 if e.turn else (e.anim // 6) % 2)
                left = e.dir < 0
            else:
                name = "e3_%s_%d" % (zone, (e.anim // 6) % 2)
                left = e.dir < 0
            sp = self.spr[name + ("_l" if left else "")]
            yo = int(2 * math.sin(e.anim * 0.25)) if e.type in (1, 3) else 0
            b.blit(sp, (e.x, e.y + yo))
        # sorts
        for s in g.spells:
            c = CP[(1, 5, 7, 4)[(tick + int(s[0])) % 4]]
            pygame.draw.rect(b, c, (int(s[0]), int(s[1]), 2, 3))
        for fa in g.freed_anims:
            b.blit(self.spr["freed"], (int(fa[0]), int(fa[1])))
            for k in range(3):
                b.set_at((int(fa[0]) + 2 + k * 4, int(fa[1]) + 26 + (tick + k) % 4), CP[(1, 5, 7)[k]])
        self._player(b, g, tick)
        self.draw_hud(g)

    def _explosion(self, b, cx, cy, t):
        r = 2 + t
        for i in range(10):
            a = i * math.pi / 5 + t * 0.2
            x = int(cx + math.cos(a) * r * 0.6)
            y = int(cy + math.sin(a) * r)
            if 0 <= x < CL_PLAY_W and 0 <= y < CL_PLAY_H:
                pygame.draw.rect(b, CP[(1, 2, 3, 5)[(i + t) % 4]], (x, y, 2, 2))

    def _player(self, b, g, tick):
        p = g.player
        left = "_l" if p.facing < 0 else ""
        if g.state == "appear":
            # matérialisation : pixels qui apparaissent progressivement
            sp = self.spr["stand" + left].copy()
            k = 1.0 - g.timer / 24.0
            rng = random.Random(tick)
            for y in range(24):
                for x in range(12):
                    if rng.random() > k:
                        sp.set_at((x, y), (0, 0, 0, 0))
            b.blit(sp, (p.x, p.y))
            return
        if g.state == "dying" and (tick // 3) % 2:
            name = "white"
        elif p.hurt and (tick // 2) % 2:
            name = "white"
        elif g.state == "drowning" or (p.landed and not p.moving):
            name = "stand"
        elif p.landed:
            name = "walk%d" % ((p.anim // 4) % 2)
        else:
            name = "fly%d" % ((p.anim // 4) % 2)
        sp = self.spr[name + left]
        if g.state == "drowning":
            # le sorcier s'enfonce : on masque la partie sous la surface
            depth = max(0, 24 - (CL_PLAY_H - 8 - p.y))
            sp = sp.subsurface((0, 0, 12, max(1, 24 - depth)))
        b.blit(sp, (p.x, p.y))

    # ------------------------------------------------------------------ bandeau
    def draw_hud(self, g):
        b = self.base
        pygame.draw.rect(b, CL_HUD_BG, (0, CL_HUD_Y, LOGICAL_W, LOGICAL_H - CL_HUD_Y))
        lines = self.status_lines(g)
        y = CL_HUD_Y + 6
        for i, l in enumerate(lines):
            self.draw_text(6, y + i * 10, l, HUD_WHITE if i == 0 else HUD_CYAN)
        if g.carried:
            sp = self.spr["item_" + g.carried["kind"]]
            pygame.draw.rect(b, CP[0], (106, CL_HUD_Y + 30, 13, 13))
            pygame.draw.rect(b, CP[6], (106, CL_HUD_Y + 30, 13, 13), 1)
            b.blit(sp, (109, CL_HUD_Y + 31 + (11 - sp.get_height())))
        low = g.energy < 25
        col = (255, 0, 0) if low and (self.t // 8) % 2 else HUD_YELLOW
        self.draw_text(6, CL_HUD_Y + 32, "ENERGIE %02d%%" % g.energy, col)
        if g.msg_t > 0 and g.msg:
            self.draw_text(6, CL_HUD_Y + 44, g.msg[:43], HUD_YELLOW)
        self._hourglass(b, g)

    @staticmethod
    def status_lines(g):
        """« VOUS ETES <lieu>, AVEC <objet>. » coupé en lignes de 42 caractères au plus."""
        what = ("AVEC " + W.ITEMS[g.carried["kind"]]["art"]) if g.carried else "LES MAINS VIDES"
        text = "VOUS ETES %s, %s." % (W.ROOMS[g.room_id]["place"], what)
        words, lines, cur = text.split(" "), [], ""
        for w in words:
            if len(cur) + len(w) + (1 if cur else 0) > 42:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w) if cur else w
        lines.append(cur)
        return lines[:3]

    def _hourglass(self, b, g):
        """Sablier (dessin original) : le sable du haut s'écoule vers le bas."""
        x0, y0, w, h = 138, CL_HUD_Y + 6, 16, 44
        frac = g.time_left / float(max(1, g.time_total))
        pygame.draw.rect(b, CP[15], (x0 - 1, y0 - 2, w + 2, 2))
        pygame.draw.rect(b, CP[15], (x0 - 1, y0 + h, w + 2, 2))
        half = h // 2
        top_rows = int(round(half * frac))
        for yy in range(h):
            d = abs(yy - half + 0.5) / half
            hw = max(1, int((w // 2 - 1) * d) + 1)
            cx = x0 + w // 2
            pygame.draw.line(b, CP[14], (cx - hw - 1, y0 + yy), (cx - hw - 1, y0 + yy))
            pygame.draw.line(b, CP[14], (cx + hw, y0 + yy), (cx + hw, y0 + yy))
            sand = False
            if yy < half:
                sand = yy >= half - top_rows
            else:
                sand = yy >= h - (half - top_rows)
            if sand:
                pygame.draw.line(b, CP[12], (cx - hw, y0 + yy), (cx + hw - 1, y0 + yy))
        if 0 < frac < 1 and g.state not in ("lost", "won") and (self.t // 2) % 2:
            pygame.draw.line(b, CP[12], (x0 + w // 2, y0 + half), (x0 + w // 2, y0 + h - 2))

    # ------------------------------------------------------------------ écrans
    def draw_title(self, tick, hiscore=0, time_min=None):
        self.t += 1
        self._sky(tick)
        b = self.base
        bands = (1, 2, 3, 7, 6, 4, 13, 8)
        s = "SORCERY"
        sx, sy = 2, 4
        x0 = (LOGICAL_W - len(s) * font.CELL_W * sx) // 2
        for i, ch in enumerate(s):
            for gy, row in enumerate(font.ROWS[ch]):
                col = CP[bands[(gy + i + tick // 6) % len(bands)]]
                for gx, c in enumerate(row):
                    if c == "#":
                        X = x0 + i * font.CELL_W * sx + gx * sx
                        Y = 10 + gy * sy
                        pygame.draw.rect(b, CL_HUD_BG, (X + 1, Y + 2, sx, sy))
                        pygame.draw.rect(b, col, (X, Y, sx, sy))
        self.center_text(44, "MODE CLASSIQUE CPC 1985", HUD_CYAN)
        wx = (tick * 0.6) % 200 - 20
        wy = 58 + 8 * math.sin(tick * 0.05)
        b.blit(self.spr["fly%d" % ((tick // 6) % 2)], (int(wx), int(wy)))
        pygame.draw.rect(b, CL_HUD_BG, (4, 94, 152, 82))
        pygame.draw.rect(b, CP[6], (4, 94, 152, 82), 1)
        lines = [
            ("GAUCHE / DROITE : SE DEPLACER", HUD_WHITE),
            ("HAUT : VOLER   (RELACHEZ : CHUTE)", HUD_WHITE),
            ("ESPACE : ECHANGER UN OBJET, FRAPPER,", HUD_WHITE),
            ("         LANCER UN SORT", HUD_WHITE),
            ("POUSSEZ CONTRE UNE PORTE POUR LA PASSER", HUD_WHITE),
            ("ESC : PAUSE      F11 : PLEIN ECRAN", HUD_WHITE),
            ("LIBEREZ LES 8 SORCIERS, PUIS REVENEZ", HUD_YELLOW),
            ("AU SANCTUAIRE AVANT LA FIN DU SABLIER", HUD_YELLOW),
        ]
        for i, (l, c) in enumerate(lines):
            self.center_text(98 + i * 9, l, c)
        if (tick // 25) % 2 == 0:
            self.center_text(180, "APPUYEZ SUR ESPACE", (0, 255, 0))
        self.center_text(191, "MEILLEUR SCORE %06d    --plus : SORCERY+" % hiscore, (255, 128, 255))

    def draw_pause(self):
        dim = pygame.Surface((CL_PLAY_W, CL_PLAY_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        self.base.blit(dim, (0, 0))
        pygame.draw.rect(self.base, CL_HUD_BG, (18, 40, 124, 64))
        pygame.draw.rect(self.base, CP[6], (18, 40, 124, 64), 1)
        self.center_text(46, "PAUSE", HUD_YELLOW, layer="lo", sx=1, sy=2)
        self.center_text(66, "LE SABLIER EST ARRETE", HUD_CYAN)
        self.center_text(79, "ESPACE : CONTINUER", HUD_WHITE)
        self.center_text(90, "ESC : ABANDONNER", HUD_WHITE)

    def _final_panel(self, g, y):
        self.center_text(y, "SORCIERS LIBERES : %d / %d" % (len(g.freed), len(W.CAPTIVE_ROOMS)), HUD_CYAN)
        self.center_text(y + 11, "SALLES VISITEES : %d / %d" % (len(g.visited), len(W.ROOMS)), HUD_CYAN)
        self.center_text(y + 22, "SCORE : %06d" % g.score, HUD_YELLOW)

    def draw_gameover(self, g, tick):
        self.t += 1
        b = self.base
        b.fill(CP[0])
        for y in range(0, 200, 2):
            if (y + tick // 2) % 8 == 0:
                pygame.draw.line(b, CP[10], (0, y), (159, y))
        sp = pygame.transform.scale(self.spr["captive%d" % ((tick // 10) % 2)], (24, 48))
        b.blit(sp, (68, 20 + int(3 * math.sin(tick * 0.08))))
        self.center_text(80, "FIN DE LA PARTIE", CP[3], layer="lo", sx=1, sy=2)
        self.center_text(104, g.lost_reason or "", HUD_WHITE)
        self._final_panel(g, 124)
        if (tick // 25) % 2 == 0:
            self.center_text(184, "ESPACE : RETOUR AU TITRE", HUD_YELLOW)

    def draw_victory(self, g, tick):
        self.t += 1
        self._sky(tick, horizon=False)
        b = self.base
        cx, cy = 74, 66
        b.blit(self.spr["stand"], (cx, cy))
        for i in range(len(g.freed)):
            a = tick * 0.03 + i * 2 * math.pi / 8
            x = cx + 40 * math.cos(a)
            y = cy + 22 * math.sin(a)
            b.blit(self.spr["captive%d" % ((tick // 8 + i) % 2)], (int(x), int(y)))
        self.center_text(12, "FELICITATIONS !", HUD_YELLOW, layer="lo", sx=1, sy=2)
        self.center_text(34, "VOUS AVEZ SAUVE LES 8 SORCIERS", HUD_WHITE)
        self._final_panel(g, 124)
        self.center_text(160, "SABLIER RESTANT : %d S (SANS BONUS)" % g.time_seconds(), HUD_CYAN)
        if (tick // 25) % 2 == 0:
            self.center_text(184, "ESPACE : RETOUR AU TITRE", HUD_YELLOW)
