"""Entités : carte de collision, sorcier, ennemis, Nécromancien, projectiles."""
import math

from config import (TILE, COLS, ROWS, PLAY_W, PLAY_H, SPEED_X, SPEED_UP, SPEED_FALL,
                    SPEED_DOWN)
from world import SOLID, WATER, ENEMY_TYPES

EPS = 1e-4


def overlap(a, b):
    return (a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and
            a[1] < b[1] + b[3] and b[1] < a[1] + a[3])


def grow(r, d):
    return (r[0] - d, r[1] - d, r[2] + 2 * d, r[3] + 2 * d)


class RoomMap:
    """Grille de collision d'une salle + cellules de portes fermées."""

    def __init__(self, rid, tiles, closed_cells=None):
        self.rid = rid
        self.tiles = tiles
        self.closed = dict(closed_cells or {})   # (cx, cy) -> door id

    def kind(self, cx, cy):
        if cx < 0 or cy < 0 or cx >= COLS or cy >= ROWS:
            return 0
        return self.tiles[cy][cx]

    def blocked_cell(self, cx, cy):
        if (cx, cy) in self.closed:
            return True
        k = self.kind(cx, cy)
        return k == SOLID or k == WATER

    def cells(self, x, y, w, h):
        x0 = int(math.floor(x / TILE))
        x1 = int(math.floor((x + w - EPS) / TILE))
        y0 = int(math.floor(y / TILE))
        y1 = int(math.floor((y + h - EPS) / TILE))
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                yield cx, cy

    def rect_blocked(self, x, y, w, h):
        return any(self.blocked_cell(cx, cy) for cx, cy in self.cells(x, y, w, h))

    def rect_touches_kind(self, x, y, w, h, kind):
        return any(self.kind(cx, cy) == kind for cx, cy in self.cells(x, y, w, h))


def move_axis(body, room, dx, dy):
    """Déplacement avec collision, par pas d'au plus 1 px. Retourne (bloqué_x, bloqué_y)."""
    hit_x = hit_y = False
    for axis, d in ((0, dx), (1, dy)):
        remaining = abs(d)
        sign = 1 if d > 0 else -1
        while remaining > EPS:
            step = sign * min(1.0, remaining)
            nx = body.x + (step if axis == 0 else 0)
            ny = body.y + (step if axis == 1 else 0)
            if room.rect_blocked(nx, ny, body.w, body.h):
                # colle au bord du pixel entier
                if axis == 0:
                    snap = math.floor(body.x) if sign < 0 else math.ceil(body.x)
                    if snap != body.x and not room.rect_blocked(snap, body.y, body.w, body.h):
                        body.x = float(snap)
                    hit_x = True
                else:
                    snap = math.floor(body.y) if sign < 0 else math.ceil(body.y)
                    if snap != body.y and not room.rect_blocked(body.x, snap, body.w, body.h):
                        body.y = float(snap)
                    hit_y = True
                break
            body.x, body.y = nx, ny
            remaining -= abs(step)
    return hit_x, hit_y


class Player:
    w, h = 6, 16

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.facing = 1
        self.anim = 0
        self.landed = False
        self.hurt = 0
        self.moving = False

    def rect(self):
        return (self.x, self.y, self.w, self.h)

    def center(self):
        return self.x + self.w / 2, self.y + self.h / 2

    def update(self, inp, room):
        dx = (1 if inp.right else 0) - (1 if inp.left else 0)
        if dx:
            self.facing = dx
        if inp.up:
            dy = -SPEED_UP
        elif inp.down:
            dy = SPEED_DOWN
        else:
            dy = SPEED_FALL
        move_axis(self, room, dx * SPEED_X, dy)
        self.landed = room.rect_blocked(self.x, self.y + 1, self.w, self.h)
        self.moving = bool(dx) or not self.landed
        self.anim += 1
        if self.hurt:
            self.hurt -= 1


class Enemy:
    def __init__(self, kind, tx, ty, param, rng, room):
        t = ENEMY_TYPES[kind]
        self.kind = kind
        self.type = t
        self.w, self.h = t["w"], t["h"]
        self.speed = t["speed"]
        self.rng = rng
        self.alive = True
        self.t = rng.randrange(0, 100)
        self.x = float(tx * TILE)
        self.y = float(ty * TILE)
        self.vx = self.speed * (1 if rng.random() < 0.5 else -1)
        self.vy = 0.0
        self.base_y = self.y
        self.visible = True
        move = t["move"]
        if move == "yoyo":
            self.range = (param or 8) * TILE
            self.anchor = self.y
            # remonte jusqu'à la première tuile solide pour accrocher le fil
            cy = int(self.y // TILE) - 1
            while cy > 0 and not room.blocked_cell(int((self.x + 4) // TILE), cy):
                cy -= 1
            self.thread_top = (cy + 1) * TILE
            self.vy = self.speed
        elif move in ("patrol", "stalk"):
            self.y = float((ty + 1) * TILE - self.h)
            while not room.rect_blocked(self.x, self.y + 1, self.w, self.h) and self.y < PLAY_H:
                self.y += 1
        elif move == "orbit":
            # feu follet : tourne autour de son point d'apparition, rayon variable
            self.cx, self.cy = self.x, self.y
            self.radius = (param or 3) * TILE
            self.angle = rng.uniform(0, 2 * math.pi)
            self.dir = 1 if rng.random() < 0.5 else -1
            self._orbit_pos()
        elif move == "swoop":
            # gargouille : perchée, plonge vers le joueur puis remonte à son perchoir
            self.perch = (self.x, self.y)
            self.state = "perch"
            self.cool = rng.randrange(20, 60)
        elif move == "jump":
            self.water_y = (ROWS - 2) * TILE
            self.y = float(self.water_y + 2)
            self.visible = False
            self.wait = rng.randrange(40, 120)
        elif move == "erratic":
            self._new_dir()

    def rect(self):
        return (self.x, self.y, self.w, self.h)

    def _orbit_pos(self):
        r = self.radius * (0.75 + 0.25 * math.sin(self.t * 0.05))
        self.x = self.cx + math.cos(self.angle) * r
        self.y = self.cy + math.sin(self.angle) * r * 0.8
        self.x = min(max(self.x, TILE), PLAY_W - TILE - self.w)
        self.y = min(max(self.y, TILE), PLAY_H - TILE - self.h)

    def _new_dir(self):
        a = self.rng.uniform(0, 2 * math.pi)
        self.vx = math.cos(a) * self.speed
        self.vy = math.sin(a) * self.speed * 0.7
        self.turn = self.rng.randrange(25, 70)

    def update(self, room, player):
        self.t += 1
        move = self.type["move"]
        if move == "sine":
            nx = self.x + self.vx
            if nx < TILE or nx + self.w > PLAY_W - TILE or room.rect_blocked(nx, self.y, self.w, self.h):
                self.vx = -self.vx
            else:
                self.x = nx
            ny = self.base_y + 6 * math.sin(self.t * 0.08)
            if not room.rect_blocked(self.x, ny, self.w, self.h):
                self.y = ny
        elif move == "chase":
            px, py = player.center()
            cx, cy = self.x + self.w / 2, self.y + self.h / 2
            d = math.hypot(px - cx, py - cy) or 1
            self.x += (px - cx) / d * self.speed
            self.y += (py - cy) / d * self.speed + 0.3 * math.sin(self.t * 0.1)
            self.x = min(max(self.x, 2), PLAY_W - self.w - 2)
            self.y = min(max(self.y, 2), PLAY_H - self.h - 2)
            if abs(px - cx) > 1:
                self.vx = 1 if px > cx else -1
        elif move == "erratic":
            self.turn -= 1
            if self.turn <= 0:
                self._new_dir()
            nx, ny = self.x + self.vx, self.y + self.vy
            if nx < TILE or nx + self.w > PLAY_W - TILE or room.rect_blocked(nx, self.y, self.w, self.h):
                self.vx = -self.vx
            else:
                self.x = nx
            if ny < TILE or ny + self.h > PLAY_H - TILE or room.rect_blocked(self.x, ny, self.w, self.h):
                self.vy = -self.vy
            else:
                self.y = ny
        elif move == "yoyo":
            self.y += self.vy
            if self.y >= self.anchor + self.range or room.rect_blocked(self.x, self.y + 1, self.w, self.h):
                self.vy = -self.speed
            elif self.y <= self.anchor:
                self.y = self.anchor
                self.vy = self.speed
        elif move == "patrol":
            nx = self.x + self.vx
            ahead = nx + (self.w if self.vx > 0 else 0)
            ground = room.blocked_cell(int(ahead // TILE), int((self.y + self.h + 1) // TILE))
            if room.rect_blocked(nx, self.y, self.w, self.h) or not ground or nx < 1 or nx + self.w > PLAY_W - 1:
                self.vx = -self.vx
            else:
                self.x = nx
        elif move == "stalk":
            # goule : marche vers le joueur s'il est à peu près à sa hauteur, sinon erre
            px, py = player.center()
            if abs(py - (self.y + self.h / 2)) < 36 and abs(px - (self.x + self.w / 2)) > 2:
                want = 1 if px > self.x + self.w / 2 else -1
                self.vx = want * self.speed * 1.5
            elif abs(self.vx) > self.speed:
                self.vx = self.speed * (1 if self.vx > 0 else -1)
            nx = self.x + self.vx
            ahead = nx + (self.w if self.vx > 0 else 0)
            ground = room.blocked_cell(int(ahead // TILE), int((self.y + self.h + 1) // TILE))
            if room.rect_blocked(nx, self.y, self.w, self.h) or not ground or nx < 1 or nx + self.w > PLAY_W - 1:
                self.vx = -self.vx
            else:
                self.x = nx
        elif move == "orbit":
            self.angle += self.speed * self.dir
            self._orbit_pos()
        elif move == "swoop":
            px, py = player.center()
            cx, cy = self.x + self.w / 2, self.y + self.h / 2
            if self.state == "perch":
                self.cool -= 1
                if self.cool <= 0 and abs(px - cx) < 40 and py > cy - 8:
                    d = math.hypot(px - cx, py - cy) or 1
                    self.vx = (px - cx) / d * self.speed
                    self.vy = (py - cy) / d * self.speed
                    self.state = "dive"
                    self.dive_t = 70
            elif self.state == "dive":
                self.dive_t -= 1
                nx, ny = self.x + self.vx, self.y + self.vy
                if (self.dive_t <= 0 or room.rect_blocked(nx, ny, self.w, self.h) or
                        nx < TILE or nx + self.w > PLAY_W - TILE or ny + self.h > PLAY_H - TILE):
                    self.state = "back"
                else:
                    self.x, self.y = nx, ny
            else:  # back : retour au perchoir (vol fantôme, sans collision)
                hx, hy = self.perch
                d = math.hypot(hx - self.x, hy - self.y)
                if d < 1.0:
                    self.x, self.y = hx, hy
                    self.state = "perch"
                    self.cool = self.rng.randrange(50, 110)
                else:
                    self.vx = (hx - self.x) / d * 0.6
                    self.x += self.vx
                    self.y += (hy - self.y) / d * 0.6
        elif move == "jump":
            if not self.visible:
                self.wait -= 1
                if self.wait <= 0:
                    self.visible = True
                    self.vy = -self.speed
                    self.y = float(self.water_y)
            else:
                self.vy += 0.08
                self.y += self.vy
                if self.y > self.water_y + 2 and self.vy > 0:
                    self.visible = False
                    self.wait = self.rng.randrange(60, 150)

    @property
    def active(self):
        return self.alive and self.visible


class Fireball:
    w, h = 4, 4

    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.alive = True
        self.t = 0

    def rect(self):
        return (self.x, self.y, self.w, self.h)

    def update(self, room):
        self.t += 1
        self.x += self.vx
        self.y += self.vy
        if (self.x < 0 or self.y < 0 or self.x > PLAY_W or self.y > PLAY_H or
                room.rect_blocked(self.x, self.y, self.w, self.h)):
            self.alive = False


class Necromancer:
    """Boss : se téléporte entre des ancres, tire des boules de feu."""
    w, h = 20, 40
    FADE = 20
    STAY = 170
    SHOOT = 55

    def __init__(self, anchors, hp, rng):
        self.anchors = [(ax * TILE, ay * TILE) for ax, ay in anchors]
        self.hp = hp
        self.rng = rng
        self.idx = 0
        self.x, self.y = self.anchors[0]
        self.base_y = self.y
        self.phase = "appear"       # appear -> stay -> vanish -> appear ... / dying
        self.timer = self.FADE
        self.invuln = 0
        self.t = 0
        self.dead = False

    def rect(self):
        return (self.x, self.y, self.w, self.h)

    @property
    def solid(self):
        """Peut être touché / blesser (visible)."""
        return self.phase == "stay"

    def teleport(self):
        choices = [i for i in range(len(self.anchors)) if i != self.idx]
        self.idx = self.rng.choice(choices)
        self.phase = "vanish"
        self.timer = self.FADE

    def update(self, player, fireballs):
        self.t += 1
        if self.invuln:
            self.invuln -= 1
        if self.phase == "dying":
            self.timer -= 1
            if self.timer <= 0:
                self.dead = True
            return
        self.timer -= 1
        if self.phase == "appear":
            if self.timer <= 0:
                self.phase, self.timer = "stay", self.STAY
        elif self.phase == "vanish":
            if self.timer <= 0:
                self.x, self.y = self.anchors[self.idx]
                self.base_y = self.y
                self.phase, self.timer = "appear", self.FADE
        elif self.phase == "stay":
            self.y = self.base_y + 3 * math.sin(self.t * 0.07)
            if self.t % self.SHOOT == 0:
                px, py = player.center()
                cx, cy = self.x + self.w / 2, self.y + 12
                d = math.hypot(px - cx, py - cy) or 1
                fireballs.append(Fireball(cx - 2, cy - 2, (px - cx) / d * 1.2, (py - cy) / d * 1.2))
            if self.timer <= 0:
                self.teleport()

    def hit(self):
        self.hp -= 1
        self.invuln = 60
        if self.hp <= 0:
            self.phase = "dying"
            self.timer = 120
        else:
            self.teleport()
