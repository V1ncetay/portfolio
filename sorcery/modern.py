"""Rendu « moderne » (par défaut) : haute résolution native, éclairage dynamique, particules,
sprites vectoriels lissés, positions interpolées entre les ticks logiques, transitions.

Le rendu ne fait que LIRE l'état du jeu (game.Game) : la logique 50 Hz, les collisions et les
données des salles sont strictement inchangées. Le rendu CPC reste disponible (render.py).
API identique à render.Renderer : draw_title / draw_chapter / draw_game / draw_pause /
draw_gameover / draw_victory / compose / present, plus pre_tick() et `alpha` (interpolation).
"""
import math
import random

import pygame

from config import TILE, COLS, ROWS, ENERGY_MAX, TIME_LIMIT_MIN, TICK_S, PLAY_W, PLAY_H
from world import (ROOMS, OBJECTS, DOORS, CAPTIVES, ZONES, WATER, HEARTS, CRAFTS, LIGHT_ITEMS,
                   BOSS_HITS, doors_in_room, opening_cells, gate_rect)
from game import ITEM_W, ITEM_H, CAGE_W, CAGE_H
import modern_gfx as G
import modern_world as MW
import modern_sprites as MS
from modern_gfx import C, mix, mul

ASPECT = 1.6
LM = 4                                  # résolution réduite de la carte de lumière

# couleurs « modernes » pour les indices de palette CPC des étincelles du jeu
SPARK = {0: (60, 60, 80), 1: (80, 110, 255), 2: (90, 140, 255), 3: (220, 60, 60), 4: (255, 80, 70),
         5: (190, 90, 255), 6: (70, 220, 120), 7: (120, 255, 150), 8: (255, 160, 170), 9: (110, 240, 255),
         10: (220, 190, 90), 11: (255, 230, 110), 12: (255, 150, 50), 13: (255, 100, 220), 14: (190, 190, 210),
         15: (255, 255, 255)}

ITEM_GLOW = {"arme": (180, 200, 255), "cle": (255, 220, 120), "indice": (255, 230, 170), "captif": (120, 255, 170),
             "relique": (210, 130, 255), "potion": (255, 70, 110), "coeur": (255, 90, 190), "ingredient": (150, 230, 255),
             "pentacle": (255, 210, 90)}


def fit(sw, sh):
    w = min(sw, int(sh * ASPECT))
    h = int(w / ASPECT)
    return max(320, w), max(200, h)


# =========================================================================== particules
class Particles:
    """Particules purement visuelles (aucun effet sur le jeu). Coordonnées en pixels écran.
    p = [x, y, vx, vy, age, life, size, color, kind, seed]
    kind : spark (additif), mote (luciole), ember, smoke (alpha), snow, dust, drip, ring."""

    def __init__(self):
        self.items = []
        self.rng = random.Random(7)

    def clear(self):
        self.items = []

    def add(self, x, y, vx, vy, life, size, color, kind="spark"):
        if len(self.items) < 900:
            self.items.append([x, y, vx, vy, 0.0, life, size, color, kind, self.rng.random() * 100])

    def burst(self, x, y, color, n, speed, life, size, kind="spark", up=0.0):
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            v = speed * r.uniform(0.25, 1.0)
            self.add(x, y, math.cos(a) * v, math.sin(a) * v - up, life * r.uniform(0.6, 1.2),
                     size * r.uniform(0.6, 1.3), color, kind)

    def update(self, dt, W, H, k):
        out = []
        for p in self.items:
            p[4] += dt
            if p[4] >= p[5]:
                continue
            kind = p[8]
            if kind == "spark":
                p[3] += 60 * k * dt
                p[2] *= (1 - 1.5 * dt)
            elif kind == "mote":
                p[2] += math.sin(p[4] * 1.7 + p[9]) * 6 * k * dt
                p[3] += math.cos(p[4] * 1.3 + p[9] * 2) * 6 * k * dt
                p[2] *= (1 - 0.8 * dt)
                p[3] *= (1 - 0.8 * dt)
            elif kind == "ember":
                p[2] += math.sin(p[4] * 3 + p[9]) * 10 * k * dt
                p[3] -= 4 * k * dt
            elif kind == "smoke":
                p[6] += 4 * k * dt
                p[3] *= (1 - 0.6 * dt)
            elif kind == "snow":
                p[2] = math.sin(p[4] * 1.2 + p[9]) * 4 * k
            elif kind == "drip":
                p[3] += 120 * k * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            if -50 < p[0] < W + 50 and -60 < p[1] < H + 40:
                out.append(p)
        self.items = out

    def draw(self, dst, glow_dst=None):
        for p in self.items:
            x, y, age, life, size, color, kind = p[0], p[1], p[4], p[5], p[6], p[7], p[8]
            t = age / life
            if kind in ("spark", "ember", "mote", "ring"):
                if kind == "mote":
                    f = (0.5 + 0.5 * math.sin(age * 3 + p[9])) * min(1.0, t * 4, (1 - t) * 4)
                else:
                    f = (1 - t) ** 1.2
                lvl = max(1, min(8, int(f * 8 + 0.5)))
                r = max(2, int(size * 2.2))
                spr = G.radial(r, mul(color, lvl / 8.0), 1.8)
                dst.blit(spr, (x - r, y - r), special_flags=pygame.BLEND_ADD)
                if size > 1.5 and lvl > 3:
                    core = G.radial(max(2, int(size * 0.7)), mul((255, 255, 255), lvl / 10.0), 1.0)
                    dst.blit(core, (x - core.get_width() / 2, y - core.get_height() / 2), special_flags=pygame.BLEND_ADD)
            elif kind == "smoke":
                a = (1 - t) * min(1.0, t * 6)
                lvl = max(1, min(8, int(a * 8 + 0.5)))
                r = max(2, int(size))
                spr = G.radial(r, color, 1.3, alpha=True, inner=lvl / 14.0)
                dst.blit(spr, (x - r, y - r))
            elif kind in ("snow", "dust", "drip"):
                a = min(1.0, t * 5, (1 - t) * 5)
                lvl = max(1, min(8, int(a * 8 + 0.5)))
                r = max(1, int(size))
                spr = G.radial(r + 1, color, 0.9, alpha=True, inner=lvl / 8.0 * (0.55 if kind == "dust" else 1.0))
                dst.blit(spr, (x - r, y - r))


# =========================================================================== rendu
class ModernRenderer:
    name = "modern"

    def __init__(self, size=(1280, 800)):
        self.scanlines = False                 # compatibilité avec la touche F2 (sans effet ici)
        self.alpha = 1.0
        self.prev = None
        self.parts = Particles()
        self.t = 0
        self._size = None
        self.set_size(size)
        self.cur_room = None
        self.last_time = None
        self.shake = 0.0
        self.sway = 0.0
        self.lift = 0.0
        self.squash = 0.0
        self.was_landed = True
        self.prev_alive = []
        self.prev_carried = None
        self.prev_hurt = 0
        self.prev_boss_hp = None
        self.trans = None                      # (surface, t0, direction)
        self.msg_key = None
        self.msg_t0 = 0.0
        self.room_t0 = 0.0
        self.spawn_acc = 0.0
        self.trail_acc = 0.0
        self.frame_ms = []

    # ------------------------------------------------------------------ résolution
    def set_size(self, size):
        w, h = fit(*size)
        if self._size == (w, h):
            return
        self._size = (w, h)
        self.V = MW.View(w, h)
        V = self.V
        self.canvas = G.opt(pygame.Surface((w, h)))
        self.play = G.opt(pygame.Surface((w, V.PH)))
        self.last_play = G.opt(pygame.Surface((w, V.PH)))
        self.lm = pygame.Surface((max(1, w // LM), max(1, V.PH // LM)))
        self.lm_big = G.opt(pygame.Surface((w, V.PH)))
        self.lib = MS.Library(V.k)
        self.bg = {}
        self.water = {}
        self.static = {}
        self._hud_bg = None
        self._vig = None
        self._screen_bg = {}
        self.parts.clear()
        self.cur_room = None

    def ensure_size(self, screen_size):
        if fit(*screen_size) != self._size:
            self.set_size(screen_size)

    # ------------------------------------------------------------------ interpolation
    def pre_tick(self, g):
        """Appelé juste avant chaque tick logique : mémorise les positions précédentes."""
        if g is None or g.state == "chapter":
            self.prev = None
            return
        self.prev = dict(room=g.room_id, p=(g.player.x, g.player.y),
                         e=[(e.x, e.y) for e in g.enemies],
                         b=(g.boss.x, g.boss.y) if g.boss else None,
                         fb={id(f): (f.x, f.y) for f in g.fireballs})

    def _lerp(self, prev, cur, snap=12.0):
        if prev is None or self.alpha >= 1.0:
            return cur
        if abs(cur[0] - prev[0]) > snap or abs(cur[1] - prev[1]) > snap:
            return cur
        a = self.alpha
        return (prev[0] + (cur[0] - prev[0]) * a, prev[1] + (cur[1] - prev[1]) * a)

    # ------------------------------------------------------------------ caches de salle
    def room_bg(self, rid, g):
        bg = self.bg.get(rid)
        if bg is None:
            bg, mask = MW.build_background(self.V, rid, g.tiles[rid])
            if len(self.bg) > 24:
                self.bg.clear()
                self.water.clear()
            self.bg[rid] = bg
            self.water[rid] = self._build_water(rid, g.tiles[rid])
        return bg

    def _build_water(self, rid, tiles):
        room = ROOMS[rid]
        if not room["water"]:
            return None
        V = self.V
        runs = []
        cy = ROWS - 2
        cx = 0
        while cx < COLS:
            if tiles[cy][cx] == WATER:
                x0 = cx
                while cx < COLS and tiles[cy][cx] == WATER:
                    cx += 1
                runs.append((x0, cx))
            else:
                cx += 1
        lava = room["lava"]
        bodies = []
        for x0, x1 in runs:
            r = pygame.Rect(int(x0 * V.cw), int(cy * V.ch), int((x1 - x0) * V.cw + 1), V.PH - int(cy * V.ch))
            if lava:
                body = G.vgradient(r.w, r.h, [(0, (255, 170, 60)), (0.25, (240, 90, 20)), (1, (120, 20, 6))])
                G.tint_noise(body, V.k * 6, G.h32(rid, x0), 170, 255)
                body = G.opt(body)
            else:
                body = G.vgradient_alpha(r.w, r.h, (40, 120, 170), [(0, 150), (1, 230)])
                deep = G.vgradient(r.w, r.h, [(0, (40, 110, 160)), (1, (10, 30, 60))]).convert_alpha()
                deep.blit(body, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                body = deep
                body.set_alpha(None)
            bodies.append((r, body))
        return dict(lava=lava, runs=runs, bodies=bodies)

    # ------------------------------------------------------------------ dessin du jeu
    def draw_game(self, g):
        self.t += 1
        V = self.V
        k = V.k
        rid = g.room_id
        room = ROOMS[rid]
        a = MW.art(rid)
        now = (g.tick + self.alpha) * TICK_S
        dt = 0.0 if self.last_time is None else max(0.0, min(0.1, now - self.last_time))
        self.last_time = now
        if rid != self.cur_room:
            self._enter_room(g, rid, a, now)
        play = self.play
        play.blit(self.room_bg(rid, g), (0, 0))
        self.lights = []
        self.glows = []
        tick = g.tick
        # ---- particules ambiantes
        self._ambient(g, a, dt)
        self.parts.update(dt, V.W, V.PH, k)
        # ---- décors animés
        for d in room["decor"]:
            self._decor_anim(play, d, now)
        for (x, y, r, col, fl) in self._spots:
            f = 1.0 + (0.12 * math.sin(now * 9 + x) + 0.08 * math.sin(now * 23 + y)) * fl
            self.lights.append((x, y, r * f, col, 0.9))
        # ---- eau / lave
        self._liquid(play, rid, now)
        # ---- portes
        for did, direction in doors_in_room(rid):
            if did not in g.doors_open:
                self._door(play, did, DOORS[did].get("style"), direction, now)
        # ---- chaudrons
        for c in room["cauldrons"]:
            self._cauldron(play, g.cauldron_rect(c), c[2] == "plein", now, c[0])
        if room.get("gate"):
            x, y, w, h = gate_rect(room["gate"])
            self._vortex(play, V.X(x + w / 2), V.Y(y + h / 2), V.X(w / 2) * 0.95, V.Y(h / 2) * 1.05, now)
        for cid, c in CRAFTS.items():
            if c["room"] == rid:
                self._creuset(play, g, cid, c, now)
        for cid, c in CAPTIVES.items():
            if c["room"] == rid and cid not in g.freed:
                self._cage(play, g.cage_rect(c), now, cid)
        # ---- objets
        for oid, it in g.items_here():
            self._item(play, oid, it, now)
        # ---- ennemis
        self._enemies(play, g, now, dt)
        # ---- boss + boules de feu
        if g.boss and not g.boss.dead:
            self._boss(play, g, now)
        for fb in g.fireballs:
            prev = self.prev["fb"].get(id(fb)) if self.prev and self.prev["room"] == rid else None
            x, y = self._lerp(prev, (fb.x, fb.y))
            px, py = V.X(x + 2), V.Y(y + 2)
            self.glows.append((px, py, k * 9, (255, 120, 40)))
            self.lights.append((px, py, k * 26, (255, 120, 40), 1.0))
            pygame.draw.circle(play, (255, 240, 200), (px, py), k * 1.6)
            if self.parts.rng.random() < min(1.0, dt * 40):
                self.parts.add(px, py, self.parts.rng.uniform(-6, 6) * k, self.parts.rng.uniform(-6, 6) * k, 0.4, k * 1.0, (255, 120, 40), "spark")
        # ---- sorciers libérés qui s'envolent
        for fa in g.freed_anims:
            fx, fy, ft = V.X(fa[0] + 4), V.Y(fa[1]), fa[2]
            spr = self.lib.wizard("fly", ft // 3, 0.6, 1.0, False, captive=True)
            s = spr.surf
            if ft > 80:
                s = s.copy()
                s.set_alpha(int(255 * max(0, (120 - ft) / 40)))
            play.blit(s, (fx - s.get_width() / 2, fy - spr.oy * k))
            self.glows.append((fx, fy + k * 6, k * 14, (120, 255, 170)))
            if self.parts.rng.random() < min(1.0, dt * 30):
                self.parts.add(fx + self.parts.rng.uniform(-3, 3) * k, fy + k * 14, 0, 10 * k, 0.8, k * 0.9, (140, 255, 180), "spark")
        # ---- joueur
        self._player(play, g, now, dt)
        # ---- étincelles du jeu (logique) + particules
        for pt in g.particles:
            col = SPARK.get(pt[5], (255, 255, 255))
            r = int(k * (1.2 if pt[4] > 8 else 0.8) * 2.2)
            spr = G.radial(max(2, r), col, 1.6)
            play.blit(spr, (V.X(pt[0]) - r, V.Y(pt[1]) - r), special_flags=pygame.BLEND_ADD)
        self.parts.draw(play)
        self._events(g, now)
        # ---- lumière
        self._lighting(play, g, a, room, now)
        for x, y, r, col in self.glows:
            spr = G.radial(max(2, int(r)), col, 1.9)
            play.blit(spr, (x - spr.get_width() / 2, y - spr.get_height() / 2), special_flags=pygame.BLEND_ADD)
        # ---- brume de premier plan
        self._fog(play, a, now)
        # ---- transition entre salles
        if self.trans:
            surf, t0, direction = self.trans
            u = (now - t0) / 0.32 if now >= t0 else 1.0
            if u >= 1.0:
                self.trans = None
            else:
                e = u * u * (3 - 2 * u)
                dx, dy = {"E": (-1, 0), "W": (1, 0), "N": (0, 1), "S": (0, -1)}.get(direction, (0, 0))
                surf.set_alpha(int(255 * (1 - e)))
                play.blit(surf, (dx * e * V.W * 0.12, dy * e * V.PH * 0.12))
        self._toast(play, g, now)
        if g.state == "dying":
            red = pygame.Surface(play.get_size())
            red.fill((60, 0, 10))
            play.blit(red, (0, 0), special_flags=pygame.BLEND_ADD)
        self.last_play.blit(play, (0, 0))
        # ---- composition (tremblement de caméra)
        self.shake *= math.exp(-dt * 9)
        ox = oy = 0
        if self.shake > 0.3:
            ox = (G.smooth_noise(now * 35, 3) - 0.5) * 2 * self.shake
            oy = (G.smooth_noise(now * 35, 9) - 0.5) * 2 * self.shake
        cv = self.canvas
        cv.fill((8, 8, 14))
        cv.blit(play, (int(ox), int(oy)))
        self.draw_hud(g, now)

    # ------------------------------------------------------------------ entrée dans une salle
    def _enter_room(self, g, rid, a, now):
        old = self.cur_room
        if old is not None and old in ROOMS:
            p = g.player
            direction = None
            ex = ROOMS[old]["exits"]
            for d, target in ex.items():
                if target == rid:
                    direction = d
            if direction:
                self.trans = (self.last_play.copy(), now, direction)
        self.cur_room = rid
        self.room_t0 = now
        self._spots = MW.light_spots(rid, self.V)
        self.parts.clear()
        self.parts.rng.seed(G.h32("parts", rid))
        self.prev_alive = [e.alive for e in g.enemies]
        self.prev_boss_hp = g.boss.hp if g.boss else None
        # pré-remplissage de l'ambiance (captures déterministes)
        for _ in range(60):
            self._ambient(g, a, 0.1, warm=True)
            self.parts.update(0.1, self.V.W, self.V.PH, self.V.k)

    def _ambient(self, g, a, dt, warm=False):
        V = self.V
        k = V.k
        r = self.parts.rng
        kind = a.get("motes")
        room = ROOMS[g.room_id]
        rate = {"fireflies": 3.0, "dust": 5.0, "snow": 14.0, "sparkles": 6.0, "embers": 10.0,
                "embers_red": 7.0, "wisps": 3.0}.get(kind, 0)
        if room["dark"]:
            rate *= 0.6
        self.spawn_acc += dt * rate
        W, H = V.W, V.PH
        while self.spawn_acc >= 1.0:
            self.spawn_acc -= 1.0
            if kind == "fireflies":
                self.parts.add(r.uniform(0, W), r.uniform(H * 0.2, H * 0.95), 0, 0, r.uniform(4, 8), k * r.uniform(0.9, 1.4),
                               (200, 255, 120) if a is not MW.ART["landes"] else (255, 220, 120), "mote")
            elif kind == "wisps":
                self.parts.add(r.uniform(0, W), r.uniform(H * 0.3, H), 0, 0, r.uniform(4, 8), k * r.uniform(1.0, 1.6),
                               (120, 255, 190), "mote")
            elif kind == "dust":
                self.parts.add(r.uniform(0, W), r.uniform(0, H), r.uniform(-3, 3) * k, r.uniform(-1, 2) * k,
                               r.uniform(5, 9), k * r.uniform(0.3, 0.6), (230, 225, 210), "dust")
            elif kind == "snow":
                self.parts.add(r.uniform(-20, W), -10, 0, r.uniform(8, 16) * k, r.uniform(8, 14), k * r.uniform(0.35, 0.8),
                               (255, 255, 255), "snow")
            elif kind == "sparkles":
                self.parts.add(r.uniform(0, W), r.uniform(0, H), 0, -r.uniform(1, 4) * k, r.uniform(1.5, 3), k * r.uniform(0.6, 1.2),
                               r.choice(((210, 140, 255), (140, 200, 255), (255, 160, 240))), "mote")
            elif kind in ("embers", "embers_red"):
                col = (255, 130, 40) if kind == "embers" else (255, 60, 100)
                self.parts.add(r.uniform(0, W), H + 5, 0, -r.uniform(10, 24) * k, r.uniform(3, 6), k * r.uniform(0.5, 1.0), col, "ember")
        if not warm and g.tick % 2 == 0 and ROOMS[g.room_id]["zone"] in ("catacombes", "riviere") and r.random() < dt * 1.5:
            self.parts.add(r.uniform(V.cw, W - V.cw), V.ch * 1.1, 0, 0, 1.2, k * 0.5, (150, 200, 255), "drip")

    # ------------------------------------------------------------------ événements visuels
    def _events(self, g, now):
        V = self.V
        k = V.k
        P = self.parts
        if len(self.prev_alive) == len(g.enemies):
            for i, e in enumerate(g.enemies):
                if self.prev_alive[i] and not e.alive:
                    cx, cy = V.X(e.x + e.w / 2), V.Y(e.y + e.h / 2)
                    P.burst(cx, cy, (190, 170, 230), 14, 30 * k, 1.0, k * 4.0, "smoke", up=8 * k)
                    P.burst(cx, cy, (255, 240, 200), 24, 60 * k, 0.7, k * 1.2, "spark")
                    self.shake = max(self.shake, k * 1.2)
        self.prev_alive = [e.alive for e in g.enemies]
        p = g.player
        pcx, pcy = V.X(p.x + 3), V.Y(p.y + 8)
        if g.carried and g.carried != self.prev_carried:
            col = ITEM_GLOW.get(OBJECTS[g.carried]["kind"], (255, 255, 255))
            P.burst(pcx, pcy, col, 22, 45 * k, 0.8, k * 1.1, "spark", up=10 * k)
        self.prev_carried = g.carried
        if p.hurt and p.hurt > self.prev_hurt:
            self.shake = max(self.shake, k * 1.6)
            P.burst(pcx, pcy, (255, 90, 90), 8, 40 * k, 0.5, k * 1.0, "spark")
        self.prev_hurt = p.hurt
        if g.boss is not None:
            if self.prev_boss_hp is not None and g.boss.hp < self.prev_boss_hp:
                self.shake = max(self.shake, k * 4)
                P.burst(V.X(g.boss.x + 10), V.Y(g.boss.y + 20), (255, 120, 220), 40, 90 * k, 1.0, k * 1.5, "spark")
            self.prev_boss_hp = g.boss.hp

    # ------------------------------------------------------------------ lumière
    def _lighting(self, play, g, a, room, now):
        V = self.V
        k = V.k
        lm = self.lm
        dark = room["dark"]
        lit = g.carried in LIGHT_ITEMS
        if dark:
            amb = a.get("dark_amb", (14, 14, 24))
            if lit:
                amb = mix(amb, (90, 76, 66), 0.8)
        else:
            amb = a["amb"]
        lm.fill(amb)
        p = g.player
        px, py = self._ppos
        cx, cy = V.X(px + 3), V.Y(py + 7)
        if dark:
            if lit:
                rx = V.W * 0.42
                spr = G.ellipse_light(rx / LM, rx * 0.9 / LM, (255, 200, 140), 0.8)
            else:
                spr = G.ellipse_light(V.X(30) / LM, V.Y(50) / LM, (235, 225, 255), 0.65)
            lm.blit(spr, (cx / LM - spr.get_width() / 2, cy / LM - spr.get_height() / 2), special_flags=pygame.BLEND_ADD)
        else:
            self.lights.append((cx, cy, k * 34, (120, 110, 160), 1.0))
        for (x, y, r, col, inten) in self.lights:
            rq = max(2, int(r / LM / 2) * 2)
            spr = G.radial(rq, mul(col, inten), 1.4)
            lm.blit(spr, (x / LM - rq, y / LM - rq), special_flags=pygame.BLEND_ADD)
        if self._vig is None or self._vig.get_size() != lm.get_size():
            self._vig = self._vignette(lm.get_size())
        lm.blit(self._vig, (0, 0), special_flags=pygame.BLEND_MULT)
        pygame.transform.smoothscale(lm, play.get_size(), self.lm_big)
        play.blit(self.lm_big, (0, 0), special_flags=pygame.BLEND_MULT)

    @staticmethod
    def _vignette(size):
        w, h = size
        v = pygame.Surface((w, h))
        v.fill((255, 255, 255))
        edge = G.radial(48, (255, 255, 255), 0.35)
        big = pygame.transform.smoothscale(edge, (int(w * 1.5), int(h * 1.9)))
        v.fill((150, 150, 160))
        v.blit(big, (w / 2 - big.get_width() / 2, h / 2 - big.get_height() / 2), special_flags=pygame.BLEND_ADD)
        return v

    def _fog(self, play, a, now):
        V = self.V
        key = ("fog", MW.art_key(self.cur_room))
        fog = self.static.get(key)
        if fog is None:
            w = V.W * 2
            h = int(V.PH * 0.32)
            fog = G.surf(w, h, True)
            rng = G.rng_for("fog", key)
            col = C(a["fog"])
            for i in range(40):
                x = rng.uniform(0, w)
                r = rng.uniform(V.k * 14, V.k * 34)
                y = h * rng.uniform(0.45, 1.1)
                for dx in (-w, 0, w):
                    pygame.draw.ellipse(fog, G.rgba(col, 26), (x + dx - r, y - r * 0.4, r * 2, r * 0.8))
            fog = G.blur(fog, 6)
            fog = G.opt(fog)
            self.static[key] = fog
        off = (now * V.k * 4) % (V.W)
        y = V.PH - fog.get_height()
        play.blit(fog, (-off, y))

    # ------------------------------------------------------------------ décors animés
    def _flame(self, dst, x, y, h, now, seed, cols):
        """Flamme vectorielle (x, y = base)."""
        k = self.V.k
        for i, (col, sc) in enumerate(zip(cols, (1.0, 0.7, 0.42))):
            hh = h * sc * (1 + 0.15 * math.sin(now * 13 + seed + i))
            ww = h * 0.36 * sc
            sway = math.sin(now * 7 + seed * 1.3) * ww * 0.35
            pts = [(x - ww, y), (x - ww * 0.8, y - hh * 0.4), (x + sway, y - hh), (x + ww * 0.8, y - hh * 0.4), (x + ww, y),
                   (x, y + ww * 0.5)]
            pygame.draw.polygon(dst, col, pts)

    def _decor_anim(self, play, d, now):
        V = self.V
        k = V.k
        kind, tx, ty = d[0], d[1], d[2]
        x, y = V.X(tx * TILE), V.Y(ty * TILE)
        if kind in ("torch", "gflame"):
            green = kind == "gflame"
            bx, by = x + V.X(2), y + V.Y(3.5)
            cols = ((40, 160, 90), (110, 255, 160), (230, 255, 240)) if green else ((230, 80, 30), (255, 170, 50), (255, 245, 200))
            self._flame(play, bx, by, k * 7, now, tx * 3.1, cols)
            self.glows.append((bx, by - k * 3, k * 14, (60, 200, 110) if green else (200, 110, 40)))
            if self.parts.rng.random() < 0.15:
                self.parts.add(bx, by - k * 5, self.parts.rng.uniform(-3, 3) * k, -self.parts.rng.uniform(8, 16) * k, 1.0,
                               k * 0.6, (120, 255, 160) if green else (255, 150, 50), "ember")
        elif kind == "lavafall":
            key = ("lavafall",)
            strip = self.static.get(key)
            w = int(V.X(5))
            top = int(y)
            h = int(V.PH - V.ch - top)
            if strip is None or strip.get_height() < h * 2:
                strip = G.surf(w, h * 2)
                rng = G.rng_for("lava")
                strip.blit(G.vgradient(w, h * 2, [(0, (255, 120, 20)), (1, (255, 90, 10))]), (0, 0))
                for i in range(int(h * 2 / (k * 2))):
                    yy = i * k * 2 + rng.uniform(0, k)
                    xx = rng.uniform(0, w)
                    ln = rng.uniform(k * 3, k * 10)
                    pygame.draw.line(strip, (255, 220, 120), (xx, yy), (xx, yy + ln), max(1, int(k * rng.uniform(0.4, 1.0))))
                    pygame.draw.line(strip, (200, 50, 10), (rng.uniform(0, w), yy), (rng.uniform(0, w), yy + ln), max(1, int(k * 0.6)))
                pygame.draw.rect(strip, (150, 40, 10), (0, 0, max(1, int(k * 0.8)), h * 2))
                pygame.draw.rect(strip, (150, 40, 10), (w - max(1, int(k * 0.8)), 0, max(1, int(k * 0.8)), h * 2))
                strip = G.opt(strip)
                self.static[key] = strip
            off = int((now * k * 40) % h)
            play.blit(strip, (x, top), (0, h - off, w, h))
            self.glows.append((x + w / 2, top + h * 0.5, k * 18, (180, 60, 10)))
            self.glows.append((x + w / 2, V.PH - V.ch, k * 16, (255, 120, 30)))
            if self.parts.rng.random() < 0.3:
                self.parts.add(x + w / 2, V.PH - V.ch, self.parts.rng.uniform(-20, 20) * k, -self.parts.rng.uniform(10, 30) * k, 0.8, k * 0.8, (255, 160, 60), "spark")
        elif kind == "vortex_bas":
            self._vortex(play, x, y + V.Y(10), V.X(7), V.Y(10), now, faint=True)
        elif kind == "pentagram":
            cx, cy, ry = x, y + V.Y(22), V.Y(22)
            rx = V.X(ry / V.sy / 2 + 4)
            pulse = 0.6 + 0.4 * math.sin(now * 2.5)
            key = ("penta", int(rx), int(ry))
            sp = self.static.get(key)
            if sp is None:
                w, h = int(rx * 2 + k * 8), int(ry * 2 + k * 8)
                sp = G.surf(w, h)
                pts = [(w / 2 + rx * math.cos(-math.pi / 2 + i * 4 * math.pi / 5), h / 2 + ry * math.sin(-math.pi / 2 + i * 4 * math.pi / 5)) for i in range(5)]
                pygame.draw.ellipse(sp, (255, 40, 90), (w / 2 - rx - k, h / 2 - ry - k, 2 * rx + 2 * k, 2 * ry + 2 * k), max(1, int(k * 0.8)))
                pygame.draw.lines(sp, (255, 40, 90), True, pts, max(1, int(k * 0.8)))
                sp = pygame.transform.smoothscale(G.blur(sp, 2), (w, h))
                sp.blit(sp, (0, 0), special_flags=pygame.BLEND_ADD)
                pygame.draw.lines(sp, (255, 160, 190), True, pts, max(1, int(k * 0.35)))
                sp = G.opt(sp)
                self.static[key] = sp
            lvl = int(pulse * 6) / 6.0
            key2 = key + (lvl,)
            sp2 = self.static.get(key2)
            if sp2 is None:
                sp2 = sp.copy()
                sp2.fill(mul((255, 255, 255), lvl), special_flags=pygame.BLEND_MULT)
                self.static[key2] = sp2
            play.blit(sp2, (cx - sp2.get_width() / 2, cy - sp2.get_height() / 2), special_flags=pygame.BLEND_ADD)

    def _vortex(self, play, cx, cy, rx, ry, now, faint=False):
        V = self.V
        k = V.k
        key = ("vortex", int(rx), int(ry), faint)
        base = self.static.get(key)
        if base is None:
            R = int(max(rx, ry))
            size = R * 2 + 4

            def draw(big, ss):
                c = size * ss / 2
                for arm in range(4):
                    pts_o, pts_i = [], []
                    for i in range(40):
                        t = i / 39
                        ang = arm * math.tau / 4 + t * 4.6
                        r = R * ss * (0.08 + 0.92 * t)
                        wdt = 0.22 * (1 - t * 0.5)
                        pts_o.append((c + math.cos(ang) * r, c + math.sin(ang) * r))
                        pts_i.append((c + math.cos(ang - wdt) * r * 0.9, c + math.sin(ang - wdt) * r * 0.9))
                    col = (170, 90, 255, 230) if not faint else (130, 70, 200, 140)
                    pygame.draw.polygon(big, col, pts_o + pts_i[::-1])
            base = G.render_ss(size, size, draw, 2, bg=(120, 60, 200))
            self.static[key] = base
        ang = (now * 140) % 360
        rot = pygame.transform.rotate(base, -ang)
        rot = pygame.transform.smoothscale(rot, (int(rot.get_width() * rx / max(rx, ry)), int(rot.get_height() * ry / max(rx, ry))))
        if not faint:
            hole = G.ellipse_light(rx * 1.05, ry * 1.05, (20, 6, 40), 0.6, alpha=True)
            play.blit(hole, (cx - hole.get_width() / 2, cy - hole.get_height() / 2))
        play.blit(rot, (cx - rot.get_width() / 2, cy - rot.get_height() / 2), special_flags=pygame.BLEND_ADD)
        self.glows.append((cx, cy, max(rx, ry) * (0.7 if not faint else 0.5), (90, 40, 160)))
        self.lights.append((cx, cy, max(rx, ry) * 2.2, (190, 110, 255), 1.0 if not faint else 0.6))
        if not faint:
            pygame.draw.circle(play, (255, 240, 255), (cx, cy), k * (1.2 + 0.4 * math.sin(now * 8)))
            if self.parts.rng.random() < 0.5:
                a = self.parts.rng.uniform(0, math.tau)
                self.parts.add(cx + math.cos(a) * rx * 1.3, cy + math.sin(a) * ry * 1.3, -math.cos(a) * rx * 1.2,
                               -math.sin(a) * ry * 1.2, 0.8, k * 0.9, (220, 160, 255), "mote")

    # ------------------------------------------------------------------ eau / lave
    def _liquid(self, play, rid, now):
        w = self.water.get(rid)
        if not w:
            return
        V = self.V
        k = V.k
        lava = w["lava"]
        for (r, body) in w["bodies"]:
            top = r.top + k * 1.0
            play.blit(body, (r.left, top))
            pts = []
            n = max(2, int(r.w / (k * 2)))
            for i in range(n + 1):
                x = r.left + r.w * i / n
                yy = top + math.sin(x / (k * 7) + now * (2.2 if not lava else 1.2)) * k * 0.7 + math.sin(x / (k * 3.1) - now * 3.3) * k * 0.35
                pts.append((x, yy))
            col = (255, 230, 140) if lava else (150, 220, 255)
            pygame.draw.polygon(play, (255, 140, 40) if lava else (60, 150, 200), pts + [(r.right, top + k * 2), (r.left, top + k * 2)])
            pygame.draw.lines(play, col, False, pts, max(1, int(k * 0.6)))
            if lava:
                for i in range(int(r.w / (k * 10)) + 1):
                    ph = (now * 0.6 + G.hnoise(i, r.left)) % 1.0
                    x = r.left + (i + 0.5) * k * 10 + math.sin(now + i) * k * 2
                    if x < r.right:
                        rr = k * (0.6 + 1.6 * math.sin(math.pi * ph))
                        pygame.draw.circle(play, (255, 220, 120), (x, top + k * (1.5 + 3 * G.hnoise(i, 7))), rr)
                for i in range(0, int(r.w), int(k * 26)):
                    self.lights.append((r.left + i + k * 13, top, k * 40, (255, 110, 30), 1.0))
                self.glows.append((r.centerx, top + k * 2, min(r.w, V.W) * 0.35, (90, 30, 6)))
                if self.parts.rng.random() < 0.25:
                    self.parts.add(self.parts.rng.uniform(r.left, r.right), top, 0, -self.parts.rng.uniform(10, 25) * k, 2.0, k * 0.7, (255, 140, 40), "ember")
            else:
                for i in range(int(r.w / (k * 9))):
                    x = r.left + ((i * 37.7 + now * k * 6) % r.w)
                    pygame.draw.line(play, (210, 240, 255), (x, top + k * (2 + (i % 3))), (x + k * 2.5, top + k * (2 + (i % 3))), max(1, int(k * 0.4)))
                self.lights.append((r.centerx, top, min(r.w, V.W) * 0.3, (60, 120, 160), 0.6))

    # ------------------------------------------------------------------ portes
    def _door(self, play, did, style, direction, now):
        V = self.V
        k = V.k
        cells = opening_cells(direction)
        r0 = V.cell(*cells[0])
        r1 = V.cell(*cells[-1])
        r = r0.union(r1)
        vert = direction in ("E", "W")
        key = ("door", style, direction, r.w, r.h)
        base = self.static.get(key)
        if base is None:
            base = self._door_base(style, r.w, r.h, vert)
            self.static[key] = base
        play.blit(base, r.topleft)
        if style in ("rune", "portail", "sceau"):
            col = {"rune": (170, 90, 255), "portail": (255, 80, 220), "sceau": (255, 60, 90)}[style]
            pulse = 0.5 + 0.5 * math.sin(now * 3)
            self.glows.append((r.centerx, r.centery, max(r.w, r.h) * (0.35 + 0.1 * pulse), mul(col, 0.5)))
            self.lights.append((r.centerx, r.centery, max(r.w, r.h) * 1.2, col, 0.8))
            n = 6
            for i in range(n):
                t = ((now * 0.5 + i / n) % 1.0)
                if vert:
                    x, y = r.left + r.w * (0.2 + 0.6 * G.hnoise(i, 3)), r.bottom - t * r.h
                else:
                    x, y = r.left + t * r.w, r.top + r.h * (0.2 + 0.6 * G.hnoise(i, 3))
                spr = G.radial(int(k * 2.5), mul(col, math.sin(math.pi * t)), 1.5)
                play.blit(spr, (x - spr.get_width() / 2, y - spr.get_height() / 2), special_flags=pygame.BLEND_ADD)
        elif style == "flammes":
            n = 5 if vert else 7
            for i in range(n):
                if vert:
                    bx, by = r.centerx + math.sin(i * 1.7) * r.w * 0.2, r.top + r.h * (i + 1) / n
                else:
                    bx, by = r.left + r.w * (i + 0.5) / n, r.bottom
                self._flame(play, bx, by, (r.h / n * 1.6) if vert else r.h * 1.4, now, i * 2.3,
                            ((220, 60, 20), (255, 150, 40), (255, 240, 180)))
            self.glows.append((r.centerx, r.centery, max(r.w, r.h) * 0.45, (160, 70, 20)))
            self.lights.append((r.centerx, r.centery, max(r.w, r.h) * 1.4, (255, 130, 50), 1.0))

    def _door_base(self, style, w, h, vert):
        k = self.V.k
        s = G.surf(w, h, True)
        L = h if vert else w                                # longueur
        T = w if vert else h                                # épaisseur

        def R(a, b, c, d):                                  # rect en coordonnées (le long, travers)
            return pygame.Rect(int(c), int(a), int(d), int(b)) if vert else pygame.Rect(int(a), int(c), int(b), int(d))

        if style in ("bois", "trappe"):
            pygame.draw.rect(s, (70, 40, 22), (0, 0, w, h), border_radius=int(k * 1.5))
            n = max(3, int(L / (k * 6)))
            for i in range(n):
                rr = R(i * L / n + k * 0.4, L / n - k * 0.8, k * 0.6, T - k * 1.2)
                pygame.draw.rect(s, mix((140, 90, 50), (110, 70, 40), (i % 2) * 0.6), rr, border_radius=int(k))
                pygame.draw.line(s, (170, 120, 70), rr.topleft, (rr.right, rr.top) if vert else (rr.left, rr.bottom), max(1, int(k * 0.4)))
            for t in (0.2, 0.8):
                band = R(L * t - k, k * 2.2, 0, T)
                pygame.draw.rect(s, (70, 70, 80), band, border_radius=int(k * 0.6))
                for u in (0.25, 0.75):
                    c = band.center
                    cxy = (band.left + band.w * u, band.centery) if vert else (band.centerx, band.top + band.h * u)
                    pygame.draw.circle(s, (180, 180, 190), cxy, k * 0.6)
        elif style == "herse":
            s.fill((10, 10, 14, 160))
            n = max(3, int(T / (k * 3)))
            for i in range(int(L / (k * 4)) + 1):
                rr = R(i * k * 4, k * 1.1, 0, T)
                pygame.draw.rect(s, (90, 92, 104), rr)
            for j in range(n):
                rr = R(0, L, j * T / n + T / n * 0.3, k * 1.3)
                pygame.draw.rect(s, (130, 134, 150), rr, border_radius=int(k * 0.5))
        elif style == "or":
            pygame.draw.rect(s, (200, 150, 40), (0, 0, w, h), border_radius=int(k * 2))
            pygame.draw.rect(s, (255, 215, 100), (k, k, w - 2 * k, h - 2 * k), max(1, int(k * 0.8)), border_radius=int(k * 1.5))
            pygame.draw.rect(s, (150, 100, 20), (k * 2.5, k * 2.5, w - 5 * k, h - 5 * k), max(1, int(k * 0.5)), border_radius=int(k))
            pygame.draw.circle(s, (80, 200, 255), (w / 2, h / 2), k * 2.2)
            pygame.draw.circle(s, (220, 250, 255), (w / 2 - k * 0.6, h / 2 - k * 0.6), k * 0.7)
        elif style in ("rune", "portail", "sceau"):
            col = {"rune": (120, 60, 220), "portail": (200, 50, 170), "sceau": (180, 30, 60)}[style]
            layer = G.surf(w, h, True)
            pygame.draw.rect(layer, G.rgba(col, 150), (0, 0, w, h), border_radius=int(min(w, h) * 0.4))
            s.blit(layer, (0, 0))
            pygame.draw.rect(s, G.rgba(mix(col, (255, 255, 255), 0.5), 220), (0, 0, w, h), max(1, int(k * 0.6)), border_radius=int(min(w, h) * 0.4))
            n = max(2, int(L / (k * 8)))
            for i in range(n):
                c = R(L * (i + 0.5) / n, 0, T / 2, 0).topleft
                c = (c[0], c[1])
                if style == "sceau":
                    pts = []
                    for j in range(24):
                        t = j / 24 * math.tau
                        x = 16 * math.sin(t) ** 3
                        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
                        pts.append((c[0] + x * k * 0.12, c[1] + y * k * 0.12))
                    pygame.draw.polygon(s, (255, 150, 170), pts, max(1, int(k * 0.4)))
                else:
                    pygame.draw.polygon(s, G.rgba((255, 220, 255), 230), G.star_points(c[0], c[1], k * 2.0, k * 0.8), max(1, int(k * 0.4)))
        elif style == "ronces":
            rng = G.rng_for("ronces", w, h)
            for i in range(int(L / (k * 1.5))):
                a0 = rng.uniform(0, L)
                pts = []
                for j in range(6):
                    pts.append(R(a0 + j * k * rng.uniform(-2, 2), 0, rng.uniform(0, T), 0).topleft)
                pygame.draw.lines(s, (40, 20, 40), False, pts, max(1, int(k * 0.9)))
                for (px_, py_) in pts[1:-1]:
                    pygame.draw.polygon(s, (180, 70, 200), [(px_, py_ - k * 0.8), (px_ + k * 1.2, py_), (px_, py_ + k * 0.8)])
        elif style == "fissure":
            pygame.draw.rect(s, (120, 116, 126), (0, 0, w, h), border_radius=int(k * 1.2))
            MW.masonry(s, (0, 0, w, h), G.rng_for("fiss", w), (130, 126, 136), (110, 106, 118), (60, 56, 66), k * 4, k * 6)
            rng = G.rng_for("crack", w, h)
            x, y = w * 0.5, 0
            pts = [(x, y)]
            while y < h:
                x = max(k, min(w - k, x + rng.uniform(-k * 2, k * 2)))
                y += k * rng.uniform(1.5, 3)
                pts.append((x, y))
            pygame.draw.lines(s, (20, 18, 24), False, pts, max(2, int(k * 0.8)))
        elif style == "os":
            s.fill((14, 10, 10, 170))
            for i in range(int(L / (k * 5)) + 1):
                rr = R(i * k * 5, k * 1.3, 0, T)
                pygame.draw.rect(s, (220, 210, 190), rr, border_radius=int(k * 0.6))
            for j in range(2):
                rr = R(0, L, T * (0.25 + 0.5 * j) - k * 0.7, k * 1.4)
                pygame.draw.rect(s, (235, 228, 210), rr, border_radius=int(k * 0.7))
        else:
            pygame.draw.rect(s, (100, 100, 110), (0, 0, w, h))
        return G.opt(s)

    # ------------------------------------------------------------------ mobilier
    def _cauldron(self, play, r, full, now, seed):
        V = self.V
        k = V.k
        x, y = V.X(r[0]), V.Y(r[1])
        cx = x + V.X(8)
        # feu dessous
        self._flame(play, cx - k * 4, y + V.Y(12), k * 3, now, seed, ((200, 60, 20), (255, 150, 40), (255, 240, 190)))
        self._flame(play, cx + k * 4, y + V.Y(12), k * 2.6, now, seed + 3, ((200, 60, 20), (255, 150, 40), (255, 240, 190)))
        spr = self.lib.cauldron(full)
        play.blit(spr.surf, (cx - spr.surf.get_width() / 2, y - spr.oy * k))
        liq = (90, 255, 140) if full else (255, 60, 80)
        for i in range(3):
            t = (now * 0.9 + i * 0.37 + seed * 0.13) % 1.0
            bx = cx + (i - 1) * k * 7 + math.sin(now * 2 + i) * k
            pygame.draw.circle(play, mix(liq, (255, 255, 255), 0.4), (bx, y + k * 1.2 - t * k * 2), k * (0.4 + 0.8 * t), max(1, int(k * 0.3)))
        self.glows.append((cx, y + k, k * 13, mul(liq, 0.45)))
        self.lights.append((cx, y, k * 40, liq, 0.8))
        self.lights.append((cx, y + V.Y(12), k * 20, (255, 140, 50), 0.6))
        if self.parts.rng.random() < 0.18:
            self.parts.add(cx + self.parts.rng.uniform(-8, 8) * k, y, self.parts.rng.uniform(-2, 2) * k, -self.parts.rng.uniform(6, 12) * k,
                           2.2, k * 2.0, mix(liq, (230, 230, 230), 0.6), "smoke")

    def _creuset(self, play, g, cid, c, now):
        V = self.V
        k = V.k
        r = g.craft_rect(c)
        x, y = V.X(r[0]), V.Y(r[1])
        cx = x + V.X(8)
        inside = g.craft_in[cid]
        done = c["makes"] in g.crafted
        spr = self.lib.crucible()
        play.blit(spr.surf, (cx - spr.surf.get_width() / 2, y - spr.oy * k))
        hot = (120, 220, 255) if done else ((255, 150, 40) if inside else (200, 70, 20))
        self.glows.append((cx, y - k * 2, k * 12, mul(hot, 0.6)))
        self.lights.append((cx, y, k * 44, hot, 1.0))
        if not done:
            n = len(c["needs"])
            for i, need in enumerate(c["needs"]):
                ix = cx + (i - (n - 1) / 2) * k * 11
                iy = y - k * 12 + math.sin(now * 2 + i) * k * 0.8
                isp = self.lib.item(OBJECTS[need].get("sprite", need))
                s = pygame.transform.smoothscale(isp.surf, (int(isp.surf.get_width() * 0.7), int(isp.surf.get_height() * 0.7)))
                if need in inside:
                    self.glows.append((ix, iy, k * 6, (120, 200, 255)))
                else:
                    s = s.copy()
                    s.set_alpha(90)
                bubble = G.radial(int(k * 6), (20, 20, 30), 1.0, alpha=True, inner=0.7)
                play.blit(bubble, (ix - bubble.get_width() / 2, iy - bubble.get_height() / 2))
                play.blit(s, (ix - s.get_width() / 2, iy - s.get_height() / 2))

    def _cage(self, play, r, now, cid):
        V = self.V
        k = V.k
        x, y = V.X(r[0]), V.Y(r[1])
        cx = x + V.X(CAGE_W / 2)
        ks = sum(map(ord, cid))
        t = (now * 50 + ks * 13) % 240
        flip = (t // 120) % 2 == 1
        wave = (40 <= t < 70 or 160 <= t < 175) and int(t / 6) % 2 == 0
        pygame.draw.line(play, (120, 120, 135), (cx, y - V.Y(6)), (cx, y), max(1, int(k * 0.6)))
        cap = self.lib.wizard("stand", int(now * 6) % 8, 0, 0, flip, captive=True, wave=wave)
        play.blit(cap.surf, (cx - cap.surf.get_width() / 2, y + V.Y(6) - cap.oy * k))
        cg = self.lib.cage()
        play.blit(cg.surf, (cx - cg.surf.get_width() / 2, y - cg.oy * k))
        self.lights.append((cx, y + V.Y(12), k * 22, (120, 255, 170), 0.5))

    def _item(self, play, oid, it, now):
        V = self.V
        k = V.k
        o = OBJECTS[oid]
        y = it["y"]
        bob = 0.0
        if o["kind"] in ("potion", "coeur"):
            bob = math.sin(now * 3 + it["x"]) * 1.2
        else:
            bob = math.sin(now * 2 + it["x"]) * 0.5 - 0.5
        cx = V.X(it["x"] + ITEM_W / 2)
        cy = V.Y(y + ITEM_H / 2 + bob)
        col = ITEM_GLOW.get(o["kind"], (255, 255, 255))
        spr = self.lib.item("potion" if o["kind"] == "potion" else o.get("sprite", oid))
        halo = G.radial(int(k * 9), mul(col, 0.35), 1.5)
        play.blit(halo, (cx - halo.get_width() / 2, cy - halo.get_height() / 2), special_flags=pygame.BLEND_ADD)
        sh = G.ellipse_light(k * 5, k * 1.2, (0, 0, 0), 1.0, alpha=True)
        play.blit(sh, (cx - sh.get_width() / 2, V.Y(it["y"] + ITEM_H) - sh.get_height() / 2))
        play.blit(spr.surf, (cx - spr.surf.get_width() / 2, cy - spr.surf.get_height() / 2))
        self.lights.append((cx, cy, k * 18, col, 0.6))
        if self.parts.rng.random() < 0.04:
            self.parts.add(cx + self.parts.rng.uniform(-5, 5) * k, cy + self.parts.rng.uniform(-4, 4) * k, 0, -k * 4, 0.9, k * 0.8, col, "mote")
        if oid in ("torche", "cierge"):
            self.lights.append((cx, cy - k * 4, k * 30, (255, 160, 70), 0.9))

    # ------------------------------------------------------------------ ennemis / boss
    def _enemies(self, play, g, now, dt):
        V = self.V
        k = V.k
        same = self.prev and self.prev["room"] == g.room_id and len(self.prev["e"]) == len(g.enemies)
        for ei, e in enumerate(g.enemies):
            if not e.active:
                continue
            x, y = self._lerp(self.prev["e"][ei] if same else None, (e.x, e.y))
            kind = e.kind
            fast = kind in ("bat", "wisp") or (kind == "gargouille" and getattr(e, "state", "") != "perch")
            f = int(now * (16 if fast else 8) + ei * 3) % 8
            flip = e.vx < 0 and kind in ("skull", "guard", "fish", "ghost", "goule", "gargouille")
            params = {}
            if kind == "gargouille":
                params["dive"] = getattr(e, "state", "perch") != "perch"
            spr = self.lib.enemy(kind, f, flip, **params)
            s = spr.surf
            if kind in ("fish", "bulle") and e.vy > 0:
                s = pygame.transform.flip(s, False, True)
            cx = V.X(x + e.w / 2)
            top = V.Y(y)
            if kind == "spider":
                pygame.draw.aaline(play, (200, 200, 220), (V.X(x + 4), V.Y(e.thread_top)), (V.X(x + 4), top + k * 2))
            if g.grace and (g.tick // 3) % 2:
                s = s.copy()
                s.set_alpha(110)
            # ombre portée douce au sol pour les marcheurs
            if kind in ("guard", "goule"):
                sh = G.ellipse_light(k * 6, k * 1.2, (0, 0, 0), 1.0, alpha=True)
                play.blit(sh, (cx - sh.get_width() / 2, V.Y(y + e.h) - sh.get_height() / 2))
            sy = top - spr.oy * k
            if kind in ("fish", "bulle") and e.vy > 0:
                sy = top - (s.get_height() / k - spr.oy - e.h) * k
            play.blit(s, (cx - s.get_width() / 2, sy))
            if kind == "wisp":
                self.glows.append((cx, top + V.Y(e.h / 2), k * 10, (40, 120, 200)))
                self.lights.append((cx, top, k * 30, (80, 200, 255), 1.0))
            elif kind == "bulle":
                self.glows.append((cx, top + V.Y(e.h / 2), k * 10, (200, 80, 10)))
                self.lights.append((cx, top, k * 30, (255, 120, 30), 1.0))
            elif kind == "skull":
                self.lights.append((cx, top, k * 16, (90, 180, 255), 0.6))
            elif kind == "ghost":
                self.lights.append((cx, top, k * 18, (150, 200, 255), 0.5))

    def _boss(self, play, g, now):
        V = self.V
        k = V.k
        bo = g.boss
        prev = self.prev["b"] if self.prev and self.prev["room"] == g.room_id else None
        x, y = self._lerp(prev, (bo.x, bo.y))
        f = int(now * 6) % 8
        spr = self.lib.necro(f)
        s = spr.surf
        cx = V.X(x + bo.w / 2)
        top = V.Y(y)
        vis = 1.0
        if bo.phase in ("appear", "vanish"):
            prog = bo.timer / bo.FADE
            vis = prog if bo.phase == "vanish" else 1 - prog
        if bo.phase == "dying":
            vis = bo.timer / 120.0
            if int(now * 20) % 2:
                s = self.lib.cache.get(("necro_white",))
                if s is None:
                    s = G.tinted(spr.surf, (255, 255, 255))
                    self.lib.cache[("necro_white",)] = s
            if self.parts.rng.random() < 0.6:
                self.parts.add(cx + self.parts.rng.uniform(-14, 14) * k, top + self.parts.rng.uniform(0, 40) * k, 0, -k * 10, 1.4, k * 4, (150, 60, 200), "smoke")
        elif bo.invuln and int(now * 16) % 2:
            s = self.lib.cache.get(("necro_white",))
            if s is None:
                s = G.tinted(spr.surf, (255, 255, 255))
                self.lib.cache[("necro_white",)] = s
        if vis < 1.0:
            sc = 0.6 + 0.4 * vis
            s = pygame.transform.smoothscale(s, (max(1, int(s.get_width() * sc)), s.get_height()))
            s.set_alpha(int(255 * vis))
            if self.parts.rng.random() < 0.7:
                a = self.parts.rng.uniform(0, math.tau)
                self.parts.add(cx + math.cos(a) * k * 18, top + k * 20 + math.sin(a) * k * 18, -math.cos(a) * k * 20, -math.sin(a) * k * 20, 0.7, k * 1.0, (200, 100, 255), "spark")
        # aura
        self.glows.append((cx, top + V.Y(20), k * 26 * vis, (70, 20, 90)))
        play.blit(s, (cx - s.get_width() / 2, top - spr.oy * k))
        self.glows.append((cx - V.X(6.5), top + k * 4.8, k * 7 * vis, (40, 200, 110)))
        self.lights.append((cx, top + k * 10, k * 60, (200, 70, 255), vis))
        self.lights.append((cx - V.X(6.5), top + k * 4.8, k * 30, (60, 255, 140), vis))
        self.glows.append((cx, top + k * 6.5, k * 4 * vis, (255, 40, 60)))

    # ------------------------------------------------------------------ joueur
    def _player(self, play, g, now, dt):
        V = self.V
        k = V.k
        p = g.player
        prev = self.prev["p"] if self.prev and self.prev["room"] == g.room_id else None
        x, y = self._lerp(prev, (p.x, p.y))
        self._ppos = (x, y)
        vx = (p.x - prev[0]) if prev else 0.0
        vy = (p.y - prev[1]) if prev else 0.0
        if g.state == "dying" and int(now * 16) % 2:
            return
        if p.landed and not p.moving:
            pose, f = "stand", int(now * 3) % 8
        elif p.landed:
            pose, f = "walk", (p.anim // 4) % 8
        else:
            pose, f = "fly", (p.anim // 3) % 8
        # cape : traînée selon la vitesse (lissée)
        target_sway = min(1.0, abs(vx) * 0.6 + (0.5 if pose == "fly" else 0.0))
        target_lift = 1.0 if vy < -0.2 else (-1.0 if vy > 0.2 else 0.0)
        a = min(1.0, dt * 8) if dt else 1.0
        self.sway += (target_sway - self.sway) * a
        self.lift += (target_lift - self.lift) * a
        # écrasement à l'atterrissage, étirement en montée
        if p.landed and not self.was_landed:
            self.squash = 1.0
            self.parts.burst(V.X(x + 3), V.Y(y + 16), (200, 190, 220), 6, 18 * k, 0.5, k * 2.0, "smoke", up=4 * k)
        self.was_landed = p.landed
        self.squash = max(0.0, self.squash - dt * 6)
        sqx = 1 + 0.14 * self.squash
        sqy = 1 - 0.14 * self.squash
        if pose == "fly" and vy < -0.2:
            sqx, sqy = sqx * 0.96, sqy * 1.04
        white = bool(p.hurt) and int(now * 25) % 2 == 0
        spr = self.lib.wizard(pose, f, self.sway, self.lift, p.facing < 0, white=white)
        s = spr.surf
        if abs(sqx - 1) > 0.01 or abs(sqy - 1) > 0.01:
            s = pygame.transform.smoothscale(s, (int(s.get_width() * sqx), int(s.get_height() * sqy)))
        cx = V.X(x + 3)
        foot = V.Y(y + 16)
        # ombre au sol
        if p.landed:
            sh = G.ellipse_light(k * 6.5, k * 1.4, (0, 0, 0), 1.0, alpha=True)
            play.blit(sh, (cx - sh.get_width() / 2, foot - sh.get_height() / 2))
        top = foot - (spr.surf.get_height() - (30 - 11 - 16) * k) * sqy
        top = foot - (16 + 11) * k * sqy
        play.blit(s, (cx - s.get_width() / 2, top))
        # extrémité lumineuse de la baguette
        d = -1 if p.facing < 0 else 1
        arm_y = 6.4 if pose == "fly" else 8.0
        wx = cx + d * (14.6 + (0.9 if pose == "fly" else 0) - 6) * k
        wy = foot - (16 - (arm_y - 3.4)) * k
        tw = 0.8 + 0.2 * math.sin(now * 9)
        self.glows.append((wx, wy, k * 5 * tw, (120, 160, 255)))
        self.lights.append((cx, foot - k * 8, k * 30, (140, 150, 255), 0.7))
        # objet porté
        if g.carried:
            o = OBJECTS[g.carried]
            isp = self.lib.item("potion" if o["kind"] == "potion" else o.get("sprite", g.carried))
            sm = self.static.get(("held", g.carried))
            if sm is None:
                sm = pygame.transform.smoothscale(isp.surf, (int(isp.surf.get_width() * 0.62), int(isp.surf.get_height() * 0.62)))
                self.static[("held", g.carried)] = sm
            hx = cx + d * k * 7.5
            hy = foot - k * 7 + math.sin(now * 4) * k * 0.4
            col = ITEM_GLOW.get(o["kind"], (255, 255, 255))
            self.glows.append((hx, hy, k * 5, mul(col, 0.5)))
            play.blit(sm, (hx - sm.get_width() / 2, hy - sm.get_height() / 2))
            if g.carried in LIGHT_ITEMS:
                self.lights.append((hx, hy, k * 60, (255, 170, 80), 1.0))
                self._flame(play, hx + d * k * 0.3, hy - k * 2.2, k * 3, now, 1.0, ((230, 80, 30), (255, 170, 50), (255, 245, 200)))
        # traînée magique en vol
        if pose == "fly":
            self.trail_acc += dt * (40 if vy < 0 else 18)
            while self.trail_acc >= 1:
                self.trail_acc -= 1
                r = self.parts.rng
                col = r.choice(((140, 150, 255), (220, 120, 255), (255, 220, 120), (120, 230, 255)))
                self.parts.add(cx + r.uniform(-4, 4) * k - d * k * 2, foot - k * r.uniform(0, 3), r.uniform(-6, 6) * k,
                               r.uniform(8, 20) * k, r.uniform(0.5, 1.0), k * r.uniform(0.7, 1.2), col, "spark")

    # ------------------------------------------------------------------ messages
    def _toast(self, play, g, now):
        V = self.V
        k = V.k
        if g.msg_t > 0 and g.msg:
            key = (g.msg, g.msg_color)
            if key != self.msg_key:
                self.msg_key = key
                self.msg_t0 = now
            appear = min(1.0, (now - self.msg_t0) / 0.25)
            fade = min(1.0, g.msg_t / 20.0)
            a = appear * fade
            col = SPARK.get(g.msg_color, (255, 255, 255))
            size = int(k * 5.2)
            tw = G.text_width(g.msg, size, 1)
            pw, ph = tw + k * 14, k * 9
            key2 = ("toast", int(pw), int(ph))
            pan = self.static.get(key2)
            if pan is None:
                pan = G.panel(pw, ph, ph / 2, (26, 24, 44), (12, 12, 24), 215, (255, 255, 255), 50)
                self.static[key2] = pan
            ease = 1 - (1 - appear) ** 3
            y = k * 3 + (ease - 1) * k * 8
            pan2 = pan
            if a < 1:
                pan2 = pan.copy()
                pan2.set_alpha(int(255 * a))
            play.blit(pan2, (V.W / 2 - pw / 2, y))
            pygame.draw.circle(play, col, (V.W / 2 - pw / 2 + k * 5, y + ph / 2), k * 1.2)
            G.draw_text(play, g.msg, V.W / 2 + k * 2, y + ph / 2 - size * 0.36, size, col, "center", spacing=1, alpha=255 * a)
        else:
            self.msg_key = None
        # nom de la salle à l'entrée
        dtr = now - self.room_t0
        if dtr < 2.6:
            a = min(1.0, dtr / 0.3, (2.6 - dtr) / 0.6)
            name = ROOMS[g.room_id]["name"]
            zone = ZONES[ROOMS[g.room_id]["zone"]]["name"]
            acc = C(MW.art(g.room_id)["accent"])
            G.draw_text(play, zone, k * 10, V.PH - k * 21, int(k * 4.2), acc, spacing=2, alpha=200 * a)
            G.draw_text(play, name, k * 10, V.PH - k * 16.5, int(k * 7), (255, 255, 255), glow=mul(acc, 0.6), alpha=255 * a)

    # ------------------------------------------------------------------ HUD
    def _hud_static(self):
        V = self.V
        k = V.k
        W, H, PH = V.W, V.H, V.PH
        hh = H - PH
        s = G.surf(W, hh)
        s.blit(G.vgradient(W, hh, [(0, (22, 20, 36)), (1, (10, 10, 18))]), (0, 0))
        pygame.draw.line(s, (90, 80, 140), (0, 0), (W, 0), max(1, int(k * 0.4)))
        glow = G.vgradient(W, int(k * 6), [(0, (40, 34, 70)), (1, (0, 0, 0))])
        s.blit(glow, (0, 0), special_flags=pygame.BLEND_ADD)
        m = k * 4
        # cartes
        self._cards = {}
        layout = [("energy", m, m, W * 0.36, hh - 2 * m), ("item", W * 0.36 + 2 * m, m, W * 0.2, hh - 2 * m),
                  ("quest", W * 0.56 + 3 * m, m, W * 0.26, hh - 2 * m), ("time", W * 0.82 + 4 * m, m, W * 0.18 - 5 * m, hh - 2 * m)]
        for name, x, y, w, h in layout:
            pan = G.panel(w, h, k * 4, (34, 32, 56), (18, 18, 32), 235, (255, 255, 255), 30)
            s.blit(pan, (x, y))
            self._cards[name] = pygame.Rect(int(x), int(y), int(w), int(h))
        return G.opt(s)

    def draw_hud(self, g, now):
        V = self.V
        k = V.k
        cv = self.canvas
        if self._hud_bg is None:
            self._hud_bg = self._hud_static()
        y0 = V.PH
        cv.blit(self._hud_bg, (0, y0))
        cards = {n: r.move(0, y0) for n, r in self._cards.items()}
        acc = C(MW.art(g.room_id)["accent"])
        lab = int(k * 4.0)
        # ---- énergie
        r = cards["energy"]
        pad = k * 5
        G.draw_text(cv, "ENERGIE", r.x + pad, r.y + pad * 0.8, lab, (190, 185, 220), spacing=2)
        frac = max(0.0, min(1.0, g.energy / ENERGY_MAX))
        G.draw_text(cv, "%d%%" % round(frac * 100), r.right - pad, r.y + pad * 0.8, lab, (255, 255, 255), "right")
        bar = pygame.Rect(int(r.x + pad), int(r.y + pad * 2.4), int(r.w - pad * 2), int(k * 7))
        pygame.draw.rect(cv, (10, 10, 18), bar, border_radius=bar.h // 2)
        fw = int(bar.w * frac)
        if fw > 2:
            key = ("ebar", bar.w, bar.h)
            grad = self.static.get(key)
            if grad is None:
                grad = G.surf(bar.w, bar.h, True)
                for i in range(bar.w):
                    t = i / bar.w
                    c = G.stops_at([(0, (255, 60, 80)), (0.35, (255, 190, 60)), (0.7, (120, 240, 120)), (1, (80, 230, 200))], t)
                    pygame.draw.line(grad, c, (i, 0), (i, bar.h))
                hl = G.vgradient_alpha(bar.w, bar.h, (255, 255, 255), [(0, 110), (0.5, 0), (1, 0)])
                grad.blit(hl, (0, 0))
                mask = G.surf(bar.w, bar.h, True)
                pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, bar.w, bar.h), border_radius=bar.h // 2)
                grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                self.static[key] = grad
            m2 = self.static.get(("emask", fw, bar.h))
            if m2 is None:
                m2 = G.surf(bar.w, bar.h, True)
                pygame.draw.rect(m2, (255, 255, 255, 255), (0, 0, fw, bar.h), border_radius=bar.h // 2)
                if len(self.static) > 400:
                    self.static = {kk: vv for kk, vv in self.static.items() if kk[0] not in ("emask",)}
                self.static[("emask", fw, bar.h)] = m2
            part = grad.copy()
            part.blit(m2, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            cv.blit(part, bar.topleft)
            if frac < 0.25:
                pulse = 0.5 + 0.5 * math.sin(now * 8)
                gl = G.radial(int(bar.h * 1.6), mul((255, 40, 60), 0.6 * pulse), 1.5)
                cv.blit(gl, (bar.x + fw - gl.get_width() / 2, bar.centery - gl.get_height() / 2), special_flags=pygame.BLEND_ADD)
        # score
        G.draw_text(cv, "SCORE", r.x + pad, bar.bottom + k * 4, lab, (190, 185, 220), spacing=2)
        G.draw_text(cv, "%06d" % g.score, r.x + pad + k * 18, bar.bottom + k * 2.6, int(k * 6.5), (255, 255, 255), glow=mul(acc, 0.5))
        G.draw_text(cv, "CH.%d" % g.chapter, r.right - pad, bar.bottom + k * 4, lab, acc, "right", spacing=2)
        # ---- objet porté
        r = cards["item"]
        G.draw_text(cv, "OBJET", r.x + pad, r.y + pad * 0.8, lab, (190, 185, 220), spacing=2)
        slot = pygame.Rect(0, 0, int(k * 17), int(k * 17))
        slot.midleft = (int(r.x + pad), int(r.centery + k * 3))
        pygame.draw.rect(cv, (12, 12, 22), slot, border_radius=int(k * 3))
        pygame.draw.rect(cv, mul(acc, 0.7) if g.carried else (60, 60, 90), slot, max(1, int(k * 0.5)), border_radius=int(k * 3))
        if g.carried:
            o = OBJECTS[g.carried]
            isp = self.lib.item("potion" if o["kind"] == "potion" else o.get("sprite", g.carried))
            col = ITEM_GLOW.get(o["kind"], (255, 255, 255))
            gl = G.radial(int(k * 8), mul(col, 0.35), 1.5)
            cv.blit(gl, (slot.centerx - gl.get_width() / 2, slot.centery - gl.get_height() / 2), special_flags=pygame.BLEND_ADD)
            cv.blit(isp.surf, (slot.centerx - isp.surf.get_width() / 2, slot.centery - isp.surf.get_height() / 2))
            name = o["name"]
            size = int(k * 4.6)
            while size > 8 and G.text_width(name, size) > r.right - slot.right - pad * 1.6:
                size -= 1
            G.draw_text(cv, name, slot.right + k * 3, slot.centery - size * 0.4, size, (255, 255, 255))
        else:
            G.draw_text(cv, "VIDE", slot.right + k * 3, slot.centery - lab * 0.4, lab, (110, 110, 140), spacing=2)
        # ---- quête : captifs (Ch.1) ou cœurs (Ch.2)
        r = cards["quest"]
        if g.chapter == 2:
            G.draw_text(cv, "COEURS SACRES", r.x + pad, r.y + pad * 0.8, lab, (190, 185, 220), spacing=2)
            G.draw_text(cv, "%d/%d" % (len(g.hearts), len(HEARTS)), r.right - pad, r.y + pad * 0.8, lab, (255, 140, 200), "right")
            icons = [("coeur", oid in g.hearts) for oid in HEARTS]
        else:
            G.draw_text(cv, "SORCIERS LIBRES", r.x + pad, r.y + pad * 0.8, lab, (190, 185, 220), spacing=2)
            G.draw_text(cv, "%d/%d" % (len(g.freed), len(CAPTIVES)), r.right - pad, r.y + pad * 0.8, lab, (140, 255, 180), "right")
            icons = [("cap", cid in g.freed) for cid in CAPTIVES]
        n = len(icons)
        cw = (r.w - pad * 2) / n
        for i, (kind, on) in enumerate(icons):
            ic = self._hud_icon(kind, on)
            ix = r.x + pad + cw * (i + 0.5)
            iy = r.centery + k * 4
            if on:
                gl = G.radial(int(k * 6), (60, 120, 80) if kind == "cap" else (120, 40, 90), 1.5)
                cv.blit(gl, (ix - gl.get_width() / 2, iy - gl.get_height() / 2), special_flags=pygame.BLEND_ADD)
            cv.blit(ic, (ix - ic.get_width() / 2, iy - ic.get_height() / 2))
        # pentacles restants (boss)
        # ---- temps : anneau
        r = cards["time"]
        tf = g.time_left / max(1, g.time_total)
        s = g.time_seconds()
        rad = min(r.w, r.h) * 0.36
        cx, cy = r.centerx, r.centery
        key = ("ring", int(rad))
        ring = self.static.get(key)
        if ring is None:
            def draw(big, ss):
                pygame.draw.circle(big, (12, 12, 22, 255), (big.get_width() / 2, big.get_height() / 2), rad * ss, int(k * 1.6 * ss))
            ring = G.render_ss(rad * 2 + 4, rad * 2 + 4, draw, 3)
            self.static[key] = ring
        cv.blit(ring, (cx - ring.get_width() / 2, cy - ring.get_height() / 2))
        low = tf < 0.2
        col = (255, 90, 90) if low else (255, 210, 110)
        steps = max(2, int(80 * tf))
        pts = [(cx + math.sin(-i / 80 * math.tau) * -rad * 0, 0) for i in range(0)]
        for i in range(steps):
            a0 = -math.pi / 2 + (i / 80) * math.tau
            a1 = -math.pi / 2 + ((i + 1.1) / 80) * math.tau
            pygame.draw.line(cv, col, (cx + math.cos(a0) * rad, cy + math.sin(a0) * rad),
                             (cx + math.cos(a1) * rad, cy + math.sin(a1) * rad), max(2, int(k * 1.3)))
        ae = -math.pi / 2 + tf * math.tau
        gl = G.radial(int(k * 4), mul(col, 0.7), 1.5)
        cv.blit(gl, (cx + math.cos(ae) * rad - gl.get_width() / 2, cy + math.sin(ae) * rad - gl.get_height() / 2), special_flags=pygame.BLEND_ADD)
        G.draw_text(cv, "%02d:%02d" % (s // 60, s % 60), cx, cy - k * 3.6, int(k * 6), col if low else (255, 255, 255), "center")
        G.draw_text(cv, "TEMPS", cx, cy + k * 3.2, int(k * 3.2), (170, 165, 200), "center", spacing=2)
        # ---- barre du boss
        bo = g.boss
        if bo and not bo.dead and not g.boss_defeated:
            w = V.W * 0.34
            x0 = V.W / 2 - w / 2
            yb = V.PH - k * 10
            G.draw_text(self.canvas, "LE NECROMANCIEN", V.W / 2, yb - k * 6, int(k * 4.2), (255, 160, 200), "center", spacing=3)
            for i in range(BOSS_HITS):
                seg = pygame.Rect(int(x0 + i * w / BOSS_HITS + k), int(yb), int(w / BOSS_HITS - 2 * k), int(k * 3))
                on = i < g.boss_hp
                pygame.draw.rect(cv, (30, 10, 24), seg.inflate(k, k), border_radius=int(k * 2))
                pygame.draw.rect(cv, (220, 50, 110) if on else (60, 30, 50), seg, border_radius=int(k * 1.5))
                if on:
                    pygame.draw.rect(cv, (255, 150, 190), (seg.x + k, seg.y + k * 0.4, seg.w - 2 * k, k * 0.8), border_radius=int(k))

    def _hud_icon(self, kind, on):
        key = ("hudicon", kind, on)
        s = self.static.get(key)
        if s is None:
            k = self.V.k
            if kind == "coeur":
                spr = self.lib.item("coeur").surf
                s = pygame.transform.smoothscale(spr, (int(spr.get_width() * 0.75), int(spr.get_height() * 0.75)))
            else:
                spr = self.lib.wizard("stand", 0, 0, 0, False, captive=True).surf
                s = pygame.transform.smoothscale(spr, (int(spr.get_width() * 0.55), int(spr.get_height() * 0.55)))
            if not on:
                s = G.tinted(s, (70, 70, 96))
                s.set_alpha(170)
            self.static[key] = s
        return s

    # ------------------------------------------------------------------ écrans
    def _night_scene(self, kind="title"):
        """Paysage nocturne plein écran (titre, chapitre, victoire)."""
        key = ("scene", kind)
        s = self._screen_bg.get(key)
        if s is not None:
            return s
        V = self.V
        W, H = V.W, V.H
        k = V.k
        rng = G.rng_for("scene", kind)
        if kind == "over":
            s = G.vgradient(W, H, [(0, "#0a0206"), (0.6, "#2a0614"), (1, "#4a0a18")])
            MW.blobs(s, rng, 20, (0, H * 0.5, W, H), k * 20, k * 60, ("#5a0a20", "#3a0616"), 90, 8)
            MW.fog_band(s, H * 0.6, H * 0.4, "#ff3050", 40, "up")
        elif kind == "chapter":
            s = G.vgradient(W, H, [(0, "#04020c"), (0.5, "#1a0a30"), (1, "#3a1050")])
            MW.blobs(s, rng, 30, (0, 0, W, H), k * 16, k * 50, ("#5a1a8a", "#2a2a9a", "#9a2a7a"), 70, 10)
            MW.stars(s, rng, 200, H, colors=("#ffffff", "#e0c0ff", "#a0e0ff"), k=k * 0.5, big=0.1)
        else:
            s = G.vgradient(W, H, [(0, "#070a24"), (0.45, "#2a2152"), (0.75, "#7a4070"), (1, "#c86a6a")])
            MW.stars(s, rng, 220, H * 0.6, k=k * 0.5, big=0.1)
            MW.moon(s, W * 0.8, H * 0.2, k * 14, glow="#5a4a8a")
            seed = 1985
            MW.ridge(s, H * 0.72, H * 0.24, W * 0.35, "#3a2c5c", seed, rim="#f0a0b0")
            MW.fog_band(s, H * 0.55, H * 0.3, "#e8a0b0", 60)
            # château sur la colline
            bx, by = W * 0.18, H * 0.62
            col = C("#241a3a")
            for dx, w, h in ((0, 3, 34), (3, 12, 22), (15, 4, 40), (19, 10, 26), (29, 3, 30)):
                pygame.draw.rect(s, col, (bx + dx * k, by - h * k, w * k + 1, h * k + H))
                pygame.draw.polygon(s, col, [(bx + (dx - 0.6) * k, by - h * k), (bx + (dx + w + 0.6) * k, by - h * k), (bx + (dx + w / 2) * k, by - (h + w * 1.3) * k)])
            for (wx, wy) in ((6, 14), (9, 18), (16.5, 30), (23, 18), (17, 22)):
                pygame.draw.circle(s, C("#ffc860"), (bx + wx * k, by - wy * k), k * 0.8)
            MW.ridge(s, H * 0.86, H * 0.18, W * 0.22, "#21183a", seed + 5, rim="#c07090")
            MW.fog_band(s, H * 0.72, H * 0.3, "#e8a0b0", 50)
            MW.ridge(s, H * 1.0, H * 0.12, W * 0.16, "#140f24", seed + 9, rim="#804870")
        vig = self._vignette((W // 4, H // 4))
        s.blit(pygame.transform.smoothscale(vig, (W, H)), (0, 0), special_flags=pygame.BLEND_MULT)
        s = G.opt(s)
        self._screen_bg[key] = s
        return s

    def _title_text(self, text, size, top, bottom, glow):
        key = ("title", text, size)
        s = self.static.get(key)
        if s is None:
            f = G.font(size)
            base = f.render(text, True, (255, 255, 255))
            if not base.get_flags() & pygame.SRCALPHA:
                base = base.convert_alpha()
            w, h = base.get_size()
            grad = G.vgradient(w, h, [(0, C(top)), (0.55, mix(top, bottom, 0.5)), (1, C(bottom))]).convert_alpha()
            grad.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            pad = int(size * 0.4)
            s = G.surf(w + pad * 2, h + pad * 2, True)
            gl = G.surf(w + pad * 2, h + pad * 2, True)
            gl.blit(G.tinted(base, glow), (pad, pad))
            gl = G.blur(gl, max(2, int(size * 0.06)))
            s.blit(gl, (0, 0))
            s.blit(gl, (0, 0))
            sh = G.tinted(base, (10, 6, 20))
            s.blit(sh, (pad + size * 0.04, pad + size * 0.06))
            s.blit(grad, (pad, pad))
            s = G.opt(s)
            self.static[key] = s
        return s

    def _screen_particles(self, now, kind):
        V = self.V
        k = V.k
        dt = 0.0 if self.last_time is None else max(0.0, min(0.1, now - self.last_time))
        self.last_time = now
        if self.cur_room != ("screen", kind):
            self.cur_room = ("screen", kind)
            self.parts.clear()
            self.parts.rng.seed(G.h32("screen", kind))
            for _ in range(40):
                self._screen_spawn(kind, 0.1)
                self.parts.update(0.1, V.W, V.H, k)
        self._screen_spawn(kind, dt)
        self.parts.update(dt, V.W, V.H, k)

    def _screen_spawn(self, kind, dt):
        V = self.V
        k = V.k
        r = self.parts.rng
        self.spawn_acc += dt * (8 if kind != "over" else 12)
        while self.spawn_acc >= 1:
            self.spawn_acc -= 1
            if kind == "over":
                self.parts.add(r.uniform(0, V.W), V.H + 5, 0, -r.uniform(10, 30) * k, r.uniform(3, 6), k * r.uniform(0.6, 1.2), (255, 60, 80), "ember")
            else:
                self.parts.add(r.uniform(0, V.W), r.uniform(V.H * 0.3, V.H), 0, 0, r.uniform(4, 8), k * r.uniform(0.8, 1.5),
                               r.choice(((255, 220, 140), (200, 255, 140), (200, 160, 255))), "mote")

    def draw_title(self, tick, hiscore=0, time_min=TIME_LIMIT_MIN, mode_label="MODERNE"):
        self.t += 1
        V = self.V
        k = V.k
        W, H = V.W, V.H
        now = tick * TICK_S + self.alpha * TICK_S
        cv = self.canvas
        cv.blit(self._night_scene("title"), (0, 0))
        self._screen_particles(now, "title")
        self.parts.draw(cv)
        # sorcier qui vole avec traînée
        wx = ((now * 60 * k * 0.18) % (W + 40 * k)) - 20 * k
        wy = H * 0.36 + math.sin(now * 2.5) * k * 6
        spr = self.lib.wizard("fly", int(now * 16) % 8, 0.8, 0.3, False)
        for i in range(10):
            tx = wx - (i + 1) * k * 4
            ty = H * 0.36 + math.sin((now - (i + 1) * 0.05) * 2.5) * k * 6 + k * 8
            gl = G.radial(int(k * (3 - i * 0.2) + 2), mul(((150, 160, 255), (230, 140, 255), (255, 220, 140))[i % 3], 1 - i / 11), 1.6)
            cv.blit(gl, (tx - gl.get_width() / 2, ty - gl.get_height() / 2), special_flags=pygame.BLEND_ADD)
        cv.blit(spr.surf, (wx - spr.surf.get_width() / 2, wy - spr.oy * k))
        # titre
        tt = self._title_text("SORCERY", int(k * 34), "#fff2c0", "#ff8a40", (255, 120, 60))
        ty = H * 0.06 + math.sin(now * 1.5) * k
        cv.blit(tt, (W / 2 - tt.get_width() / 2, ty))
        shine = (now * 0.35) % 1.6
        if shine < 1.0:
            sx_ = W / 2 - tt.get_width() / 2 + tt.get_width() * shine
            gl = G.ellipse_light(k * 10, k * 26, (90, 70, 40), 1.4)
            cv.blit(gl, (sx_ - gl.get_width() / 2, ty + tt.get_height() / 2 - gl.get_height() / 2), special_flags=pygame.BLEND_ADD)
        G.draw_text(cv, "UNE RECREATION HOMMAGE  -  AMSTRAD CPC 1985", W / 2, ty + tt.get_height() * 0.86, int(k * 4.6),
                    (220, 210, 255), "center", spacing=3)
        # panneau des commandes
        pw, ph = W * 0.62, H * 0.42
        px, py = W / 2 - pw / 2, H * 0.48
        key = ("titlepanel", int(pw), int(ph))
        pan = self.static.get(key)
        if pan is None:
            pan = G.panel(pw, ph, k * 5, (30, 26, 56), (14, 12, 30), 210, (255, 255, 255), 40)
            self.static[key] = pan
        cv.blit(pan, (px, py))
        rows = [("FLECHES / ZQSD / WASD", "SE DEPLACER"), ("HAUT  /  BAS", "VOLER  /  PLONGER"),
                ("ESPACE", "PRENDRE / ECHANGER / POSER"), ("ESC", "PAUSE"), ("F11", "PLEIN ECRAN"),
                ("F4", "GRAPHISMES : %s" % mode_label)]
        size = int(k * 4.4)
        for i, (key_, desc) in enumerate(rows):
            yy = py + k * 6 + i * k * 7.4
            kw = G.text_width(key_, size) + k * 5
            kx = px + pw * 0.44 - kw
            pygame.draw.rect(cv, (60, 54, 100), (kx, yy - k * 1.2, kw, k * 6.4), border_radius=int(k * 1.6))
            pygame.draw.rect(cv, (110, 100, 170), (kx, yy - k * 1.2, kw, k * 6.4), max(1, int(k * 0.35)), border_radius=int(k * 1.6))
            G.draw_text(cv, key_, kx + kw / 2, yy, size, (255, 255, 255), "center", shadow=None)
            G.draw_text(cv, desc, px + pw * 0.44 + k * 4, yy, size, (255, 220, 140) if key_ == "F4" else (215, 210, 240))
        yy = py + k * 6 + len(rows) * k * 7.4 + k * 1
        G.draw_text(cv, "CH.1 : LIBEREZ LES 8 SORCIERS (%d MIN)   -   CH.2 : LES 8 COEURS SACRES ET LE NECROMANCIEN" % time_min,
                    W / 2, yy, int(k * 3.8), (140, 255, 190), "center")
        a = 0.55 + 0.45 * math.sin(now * 4)
        G.draw_text(cv, "APPUYEZ SUR ESPACE", W / 2, H * 0.915, int(k * 6), (255, 255, 255), "center", glow=(255, 160, 80), spacing=3, alpha=255 * a)
        G.draw_text(cv, "MEILLEUR SCORE  %06d" % hiscore, W / 2, H * 0.965, int(k * 3.8), (255, 140, 210), "center", spacing=2)

    def draw_chapter(self, g, tick):
        self.t += 1
        V = self.V
        k = V.k
        W, H = V.W, V.H
        now = tick * TICK_S + self.alpha * TICK_S
        cv = self.canvas
        cv.blit(self._night_scene("chapter"), (0, 0))
        self._screen_particles(now, "chapter")
        self.parts.draw(cv)
        tt = self._title_text("CHAPITRE %d" % (g.next_chapter or g.chapter), int(k * 22), "#ffe0ff", "#c060ff", (180, 80, 255))
        cv.blit(tt, (W / 2 - tt.get_width() / 2, H * 0.04))
        G.draw_text(cv, "LE MONDE DU NECROMANCIEN", W / 2, H * 0.04 + tt.get_height() * 0.85, int(k * 5), (255, 160, 230), "center", spacing=4)
        cx, cy = W / 2, H * 0.43
        self.glows = []
        self.lights = []
        self._vortex(cv, cx, cy, k * 26, k * 26, now)
        for x, y, r, col in self.glows:
            spr = G.radial(max(2, int(r)), col, 1.9)
            cv.blit(spr, (x - spr.get_width() / 2, y - spr.get_height() / 2), special_flags=pygame.BLEND_ADD)
        kk = (tick % 150) / 150.0
        a = tick * 0.12
        spr = self.lib.wizard("fly", int(now * 16) % 8, 1.0, 1.0, False)
        sc = max(0.05, 1 - kk)
        s = pygame.transform.rotozoom(spr.surf, -a * 40, sc)
        cv.blit(s, (cx + math.cos(a) * k * 22 * (1 - kk) - s.get_width() / 2, cy + math.sin(a) * k * 22 * (1 - kk) - s.get_height() / 2))
        pw, ph = W * 0.6, H * 0.3
        px, py = W / 2 - pw / 2, H * 0.62
        key = ("chpanel", int(pw), int(ph))
        pan = self.static.get(key)
        if pan is None:
            pan = G.panel(pw, ph, k * 5, (36, 20, 60), (16, 10, 30), 210, (255, 200, 255), 40)
            self.static[key] = pan
        cv.blit(pan, (px, py))
        lines = [("VOTRE SCEPTRE S'EST BRISE DANS LE VORTEX.", (255, 255, 255)),
                 ("TROUVEZ LES %d COEURS SACRES ET FRAPPEZ" % len(HEARTS), (255, 220, 140)),
                 ("LE NECROMANCIEN DE %d PENTACLES..." % BOSS_HITS, (255, 220, 140)),
                 ("MAIS IL N'EN EXISTE QUE DEUX !", (255, 140, 120))]
        for i, (l, c) in enumerate(lines):
            G.draw_text(cv, l, W / 2, py + k * 5 + i * k * 7, int(k * 4.8), c, "center")
        G.draw_text(cv, "BONUS TEMPS CH.1 : %d     SCORE : %06d     TEMPS LIMITE : %d MIN" % (g.chapter_bonus, g.score, g.time2_min),
                    W / 2, py + k * 5 + 4 * k * 7 + k * 2, int(k * 3.8), (160, 230, 255), "center")
        al = 0.55 + 0.45 * math.sin(now * 4)
        G.draw_text(cv, "ESPACE : CONTINUER", W / 2, H * 0.94, int(k * 5.2), (255, 255, 255), "center", glow=(200, 100, 255), spacing=3, alpha=255 * al)

    def draw_pause(self):
        V = self.V
        k = V.k
        cv = self.canvas
        dim = self.static.get("dim")
        if dim is None:
            dim = G.surf(V.W, V.H, True)
            dim.fill((6, 6, 14, 170))
            dim = G.opt(dim)
            self.static["dim"] = dim
        cv.blit(dim, (0, 0))
        pw, ph = k * 90, k * 40
        key = ("pausepanel", int(pw))
        pan = self.static.get(key)
        if pan is None:
            pan = G.panel(pw, ph, k * 5, (36, 32, 64), (16, 14, 32), 235, (255, 255, 255), 50)
            self.static[key] = pan
        x, y = V.W / 2 - pw / 2, V.PH / 2 - ph / 2
        cv.blit(pan, (x, y))
        G.draw_text(cv, "PAUSE", V.W / 2, y + k * 5, int(k * 11), (255, 230, 150), "center", glow=(255, 140, 60), spacing=4)
        G.draw_text(cv, "ESPACE : CONTINUER", V.W / 2, y + k * 21, int(k * 4.6), (255, 255, 255), "center")
        G.draw_text(cv, "ESC : ABANDONNER LA PARTIE", V.W / 2, y + k * 29, int(k * 4.6), (200, 190, 230), "center")

    def draw_gameover(self, g, tick):
        self.t += 1
        V = self.V
        k = V.k
        W, H = V.W, V.H
        now = tick * TICK_S + self.alpha * TICK_S
        cv = self.canvas
        cv.blit(self._night_scene("over"), (0, 0))
        self._screen_particles(now, "over")
        self.parts.draw(cv)
        spr = self.lib.necro(int(now * 6) % 8)
        s = pygame.transform.smoothscale(spr.surf, (int(spr.surf.get_width() * 1.3), int(spr.surf.get_height() * 1.3)))
        gl = G.radial(int(k * 50), (90, 10, 40), 1.6)
        cv.blit(gl, (W / 2 - gl.get_width() / 2, H * 0.2 - gl.get_height() / 2 + k * 20), special_flags=pygame.BLEND_ADD)
        cv.blit(s, (W / 2 - s.get_width() / 2, H * 0.03 + math.sin(now * 2) * k * 2))
        tt = self._title_text("LE NECROMANCIEN TRIOMPHE", int(k * 14), "#ffd0d8", "#ff2050", (255, 30, 70))
        cv.blit(tt, (W / 2 - tt.get_width() / 2, H * 0.5))
        y = H * 0.5 + tt.get_height() * 0.95
        G.draw_text(cv, g.lost_reason or "", W / 2, y, int(k * 5.4), (255, 255, 255), "center", spacing=2)
        if g.chapter == 2:
            line = "CHAPITRE 2  -  COEURS SACRES : %d / %d" % (len(g.hearts), len(HEARTS))
        else:
            line = "SORCIERS LIBERES : %d / %d" % (len(g.freed), len(CAPTIVES))
        G.draw_text(cv, line, W / 2, y + k * 10, int(k * 4.6), (255, 170, 200), "center")
        G.draw_text(cv, "SCORE  %06d" % g.score, W / 2, y + k * 19, int(k * 7), (255, 230, 150), "center", glow=(200, 80, 30))
        al = 0.55 + 0.45 * math.sin(now * 4)
        G.draw_text(cv, "ESPACE : RETOUR AU TITRE", W / 2, H * 0.93, int(k * 5), (255, 255, 255), "center", spacing=3, alpha=255 * al)

    def draw_victory(self, g, tick):
        self.t += 1
        V = self.V
        k = V.k
        W, H = V.W, V.H
        now = tick * TICK_S + self.alpha * TICK_S
        cv = self.canvas
        cv.blit(self._night_scene("title"), (0, 0))
        self._screen_particles(now, "victory")
        r = self.parts.rng
        if r.random() < 0.25:                         # feux d'artifice
            col = r.choice(((255, 200, 80), (120, 255, 170), (200, 140, 255), (255, 120, 180), (120, 200, 255)))
            self.parts.burst(r.uniform(W * 0.15, W * 0.85), r.uniform(H * 0.08, H * 0.35), col, 40, 90 * k, 1.4, k * 1.2, "spark")
        self.parts.draw(cv)
        tt = self._title_text("VICTOIRE !", int(k * 26), "#fff6c8", "#ffb030", (255, 170, 40))
        cv.blit(tt, (W / 2 - tt.get_width() / 2, H * 0.03))
        G.draw_text(cv, "LE NECROMANCIEN EST DETRUIT", W / 2, H * 0.03 + tt.get_height() * 0.86, int(k * 5.4), (255, 255, 255), "center", spacing=3)
        cx, cy = W / 2, H * 0.47
        gl = G.radial(int(k * 40), (60, 60, 120), 1.4)
        cv.blit(gl, (cx - gl.get_width() / 2, cy - gl.get_height() / 2), special_flags=pygame.BLEND_ADD)
        hero = self.lib.wizard("stand", int(now * 3) % 8, 0, 0, False)
        order = []
        for i, cid in enumerate(CAPTIVES):
            ang = now * 0.9 + i * math.tau / len(CAPTIVES)
            order.append((math.sin(ang), i, cid, ang))
        order.sort()
        drawn_hero = False
        for depth, i, cid, ang in order:
            if depth > 0 and not drawn_hero:
                cv.blit(hero.surf, (cx - hero.surf.get_width() / 2, cy - hero.oy * k - k * 8))
                drawn_hero = True
            if cid not in g.freed:
                continue
            x = cx + math.cos(ang) * k * 46
            y = cy + math.sin(ang) * k * 12
            spr = self.lib.wizard("fly" if i % 2 else "stand", int(now * 10 + i) % 8, 0.4, 0, math.sin(ang) > 0, captive=True,
                                  wave=(int(now * 4 + i) % 2 == 0))
            sc = 0.8 + 0.2 * depth
            s = pygame.transform.smoothscale(spr.surf, (int(spr.surf.get_width() * sc), int(spr.surf.get_height() * sc)))
            cv.blit(s, (x - s.get_width() / 2, y - spr.oy * k * sc - k * 8))
        if not drawn_hero:
            cv.blit(hero.surf, (cx - hero.surf.get_width() / 2, cy - hero.oy * k - k * 8))
        pw, ph = W * 0.5, H * 0.24
        px, py = W / 2 - pw / 2, H * 0.64
        key = ("vicpanel", int(pw))
        pan = self.static.get(key)
        if pan is None:
            pan = G.panel(pw, ph, k * 5, (30, 30, 60), (14, 14, 30), 210, (255, 230, 150), 50)
            self.static[key] = pan
        cv.blit(pan, (px, py))
        lines = [("LES SORCIERS SONT LIBRES !  (%d/%d)" % (len(g.freed), len(CAPTIVES)), (140, 255, 180)),
                 ("COEURS SACRES : %d/%d" % (len(g.hearts), len(HEARTS)), (255, 140, 210)),
                 ("BONUS TEMPS : %d" % g.time_bonus, (255, 230, 150))]
        for i, (l, c) in enumerate(lines):
            G.draw_text(cv, l, W / 2, py + k * 5 + i * k * 7, int(k * 4.8), c, "center")
        G.draw_text(cv, "SCORE FINAL  %06d" % g.score, W / 2, py + k * 27, int(k * 7.5), (255, 255, 255), "center", glow=(255, 170, 60))
        al = 0.55 + 0.45 * math.sin(now * 4)
        G.draw_text(cv, "ESPACE : RETOUR AU TITRE", W / 2, H * 0.94, int(k * 5), (255, 255, 255), "center", spacing=3, alpha=255 * al)

    # ------------------------------------------------------------------ composition
    def compose(self):
        return self.canvas

    def present(self, screen):
        sw, sh = screen.get_size()
        cw, ch = self.canvas.get_size()
        if (cw, ch) == (sw, sh):
            screen.blit(self.canvas, (0, 0))
        else:
            screen.fill((0, 0, 0))
            if cw <= sw and ch <= sh:
                screen.blit(self.canvas, ((sw - cw) // 2, (sh - ch) // 2))
            else:
                w, h = fit(sw, sh)
                screen.blit(pygame.transform.smoothscale(self.canvas, (w, h)), ((sw - w) // 2, (sh - h) // 2))
        self.ensure_size((sw, sh))

    def icon(self):
        spr = self.lib.wizard("stand", 0, 0, 0, False)
        return pygame.transform.smoothscale(spr.surf, (32, 32))
