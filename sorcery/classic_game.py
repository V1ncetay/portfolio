"""Logique du mode « Classique CPC 1985 » (indépendante du rendu).

Une itération de `update()` = une trame du jeu original (37,5 Hz). Les règles, vitesses,
dégâts et barèmes sont ceux prouvés par l'analyse binaire (docs/ANALYSE_DSK.md) ; les
adresses Z80 correspondantes sont rappelées en commentaire. La carte est originale
(classic_world.py).
"""
import random

from config import (CL_CELL_W, CL_CELL_H, CL_COLS, CL_ROWS, CL_SPRITE_W, CL_SPRITE_H, CL_X_MAX,
                    CL_Y_MAX, CL_SPEED_X, CL_SPEED_UP, CL_SPEED_FALL, CL_ENERGY_MAX, CL_TIME_FRAMES,
                    CL_FRAME_HZ, CL_DMG_T1, CL_DMG_T2, CL_DMG_T3, CL_DMG_FIRE, CL_CAULDRON_GOOD,
                    CL_CAULDRON_BAD, CL_CONTACT_DY, CL_CONTACT_DX, CL_CAPTIVE_DY, CL_CAPTIVE_DX,
                    CL_CAULDRON_DX, CL_ENEMY_SPEED, CL_SCORE_ROOM, CL_SCORE_PICKUP, CL_SCORE_KILL,
                    CL_SCORE_SPELL, CL_SCORE_FREE, CL_PLAY_W, CL_PLAY_H)
import classic_world as W

ENEMY_DMG = {1: CL_DMG_T1, 2: CL_DMG_T2, 3: CL_DMG_T3}
TURN_FRAMES = 8                 # demi-tour animé des marcheurs / spectres
APPEAR_FRAMES = 24              # apparition du sorcier (état 1)
DYING_FRAMES = 60               # chute + agonie (états 3-4)
DROWN_FRAMES = 48               # noyade (états 5-6)
FREED_RISE = 2                  # sorcier libéré : 2 lignes par trame (&1A34)

LOST_ENERGY = "VOUS N'AVEZ PLUS D'ENERGIE"
LOST_DROWN = "VOUS VOUS ETES NOYE DANS LA RIVIERE"
LOST_TIME = "VOTRE CHANCE ET VOTRE TEMPS SONT EPUISES"


class NullAudio:
    def play(self, name):
        pass


class Body:
    """Corps 12x24 positionné au pixel Mode 0 (x) et à la ligne (y), coin haut-gauche."""
    w, h = CL_SPRITE_W, CL_SPRITE_H

    def __init__(self, x, y):
        self.x, self.y = int(x), int(y)


class Player(Body):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.facing = 1
        self.anim = 0
        self.landed = False
        self.moving = False
        self.hurt = 0

    def rect(self):
        return (self.x, self.y, self.w, self.h)

    def center(self):
        return self.x + self.w / 2, self.y + self.h / 2


class Enemy(Body):
    def __init__(self, etype, x, y):
        super().__init__(x, y)
        self.type = etype
        self.alive = True
        self.dying = 0            # explosion (type 4) en cours
        self.dir = -1
        self.turn = 0
        self.anim = 0

    def rect(self):
        return (self.x, self.y, self.w, self.h)


class ClassicGame:
    """Une partie en mode Classique. update(inp) = une trame à 37,5 Hz."""
    mode = "classic"
    chapter = 1

    def __init__(self, audio=None, seed=None, start=None, time_frames=CL_TIME_FRAMES):
        self.audio = audio or NullAudio()
        self.rng = random.Random(seed)
        # départ et chaudrons nocifs : même index (graine modulo 5, &06D6 / &073B)
        self.start_index = self.rng.randrange(len(W.STARTS)) if start is None else start
        self.poison = set(W.POISON[self.start_index])
        self.items = [dict(id=i, kind=k, room=r, x=x * CL_CELL_W, y=y * CL_CELL_H, taken=False)
                      for i, (r, k, x, y) in enumerate(W.item_instances())]
        self.carried = None                 # instance portée (dict) ou None
        self.open_barriers = set()
        self.freed = []                     # salles dont le captif est libéré (ordre)
        self.enemy_state = {}               # salle -> liste d'Enemy (état persistant, &13BA)
        self.visited = set()
        self.energy = CL_ENERGY_MAX
        self.dmg_acc = 0                    # fraction /256 (&1C56)
        self.time_total = time_frames
        self.time_left = time_frames
        self.score = 0
        self.state = "appear"
        self.timer = APPEAR_FRAMES
        self.lost_reason = ""
        self.tick = 0
        self.msg, self.msg_t, self.msg_color = "", 0, 5
        self.spells = []                    # [x, y, dx, dy]
        self.freed_anims = []               # [x, y, salle]
        self.contact = set()
        self.rooms_version = 0
        self.time_bonus = 0                 # aucun bonus de temps (§11)
        rid, cx, cy = W.STARTS[self.start_index]
        self.player = Player(cx * CL_CELL_W, cy * CL_CELL_H)
        self.enter_room(rid)
        self.say("LIBEREZ LES 8 SORCIERS CAPTIFS !", 1, 150)

    # ------------------------------------------------------------------ outils
    def say(self, text, color=5, ticks=110):
        self.msg, self.msg_color, self.msg_t = text, color, ticks

    def time_seconds(self):
        return max(0, int((self.time_left + CL_FRAME_HZ - 1) // CL_FRAME_HZ))

    @property
    def carried_kind(self):
        return self.carried["kind"] if self.carried else None

    def enter_room(self, rid):
        self.room_id = rid                  # l'état des ennemis est persistant (enemy_state)
        self.room = W.ROOMS[rid]
        if rid not in self.enemy_state:
            self.enemy_state[rid] = [Enemy(t, x * CL_CELL_W, y * CL_CELL_H) for t, x, y in self.room["enemies"]]
        self.enemies = self.enemy_state[rid]
        self.spells = []
        self.contact = set()
        self._rebuild()
        if rid not in self.visited:          # première visite : +500 (&0B6D)
            self.visited.add(rid)
            self.score += CL_SCORE_ROOM

    def _rebuild(self):
        self.grid = W.collision_grid(self.room_id, self.open_barriers)
        self.rooms_version += 1

    def cell(self, cx, cy):
        if cx < 0 or cy < 0 or cx >= CL_COLS or cy >= CL_ROWS:
            return W.SOLID
        return self.grid[cy][cx]

    def blocked(self, x, y, w=CL_SPRITE_W, h=CL_SPRITE_H):
        """Le rectangle touche-t-il une cellule bloquante (bit 7, &11E5) ou un bord d'écran ?"""
        if x < 0 or y < 0 or x + w > CL_PLAY_W or y + h > CL_PLAY_H:
            return True
        for cy in range(y // CL_CELL_H, (y + h - 1) // CL_CELL_H + 1):
            for cx in range(x // CL_CELL_W, (x + w - 1) // CL_CELL_W + 1):
                if self.grid[cy][cx] in W.BLOCKING:
                    return True
        return False

    def feet_cells(self, p=None):
        p = p or self.player
        cy = (p.y + p.h) // CL_CELL_H
        return [(cx, cy) for cx in range(p.x // CL_CELL_W, (p.x + p.w - 1) // CL_CELL_W + 1)]

    def damage(self, amount):
        """Accumulateur /256 : chaque retenue retire 1 point d'énergie (&1ACF)."""
        self.dmg_acc -= amount
        while self.dmg_acc < 0:
            self.dmg_acc += 256
            self.energy = max(0, self.energy - 1)
        if self.player.hurt <= 0:
            self.player.hurt = 8
            self.audio.play("hurt")

    def items_here(self):
        return [it for it in self.items if it["room"] == self.room_id]

    def barriers_here(self):
        return [b for b in W.BARRIERS if b[1] == self.room_id and b[0] not in self.open_barriers]

    # ------------------------------------------------------------------ mise à jour
    def update(self, inp):
        self.tick += 1
        if self.msg_t:
            self.msg_t -= 1
        for fa in self.freed_anims:
            fa[1] -= FREED_RISE
        self.freed_anims = [fa for fa in self.freed_anims if fa[1] > -CL_SPRITE_H]
        for e in self.enemies:
            if e.dying:
                e.dying -= 1
                e.anim += 1
        if self.state in ("lost", "won"):
            return
        # sablier : s'écoule hors pause (la pause ne fait pas appeler update)
        self.time_left -= 1
        if self.time_left <= 0:
            self.time_left = 0
            self._lose(LOST_TIME)
            return
        if self.state == "appear":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state == "dying":
            self.timer -= 1
            p = self.player
            if not self.blocked(p.x, p.y + CL_SPEED_FALL):
                p.y += CL_SPEED_FALL
            if self.timer <= 0:
                self.state = "lost"
            return
        if self.state == "drowning":
            self.timer -= 1
            if self.timer % 6 == 0 and self.player.y < CL_Y_MAX + 8:
                self.player.y += 1
            if self.timer <= 0:
                self.state = "lost"
            return
        self._update_play(inp)

    def _lose(self, reason):
        self.lost_reason = reason
        if reason == LOST_TIME:
            self.state = "lost"
        elif reason == LOST_DROWN:
            self.state, self.timer = "drowning", DROWN_FRAMES
        else:
            self.state, self.timer = "dying", DYING_FRAMES
        self.audio.play("gameover")

    def _move_player(self, inp):
        """Déplacement de l'état 2 (&0F2F) : 2 px / 2 lignes par trame, pas de « bas »."""
        p = self.player
        dx = (1 if inp.right else 0) - (1 if inp.left else 0)
        if dx:
            p.facing = dx
            nx = p.x + dx * CL_SPEED_X
            if 0 <= nx <= CL_X_MAX and not self.blocked(nx, p.y):
                p.x = nx
        dy = -CL_SPEED_UP if inp.up else CL_SPEED_FALL      # inp.down est ignoré
        ny = p.y + dy
        if 0 <= ny <= CL_Y_MAX and not self.blocked(p.x, ny):
            p.y = ny
        elif not dx:
            # aide d'alignement (absente de l'original) : un sorcier décalé de 2 px d'un
            # passage de 3 cellules (trappe, puits) y glisse au lieu d'y rester bloqué.
            for sx in (-CL_SPEED_X, CL_SPEED_X):
                if (0 <= ny <= CL_Y_MAX and 0 <= p.x + sx <= CL_X_MAX
                        and not self.blocked(p.x + sx, p.y) and not self.blocked(p.x + sx, ny)):
                    p.x += sx
                    p.y = ny
                    break
        p.landed = self.blocked(p.x, p.y + 1) or p.y >= CL_Y_MAX
        p.moving = bool(dx) or not p.landed
        p.anim += 1
        if p.hurt:
            p.hurt -= 1
        return dx

    def _update_play(self, inp):
        p = self.player
        dx = self._move_player(inp)
        if self._try_door(dx):
            return
        # noyade : posé sur des cellules toutes « eau » (&0FD1-&1003)
        if p.landed and p.y < CL_Y_MAX:
            feet = self.feet_cells()
            if all(self.cell(cx, cy) == W.WATER for cx, cy in feet):
                self._lose(LOST_DROWN)
                self.audio.play("drown")
                return
        # cases « feu » au niveau de la rangée basse du sorcier (&1048)
        low = (p.y + p.h - 1) // CL_CELL_H
        if any(self.cell(cx, low) == W.FIRE for cx in range(p.x // CL_CELL_W, (p.x + p.w - 1) // CL_CELL_W + 1)):
            self.damage(CL_DMG_FIRE)
        self._cauldron()
        self._barriers()
        self._captive()
        if inp.action:
            self._fire()
        self._enemies()
        self._spells()
        # victoire : 8 libérés, sorcier posé au sanctuaire (&1270)
        goal = self.room.get("goal")
        if goal and len(self.freed) == len(W.CAPTIVE_ROOMS):
            gx, gy = goal[0] * CL_CELL_W, goal[1] * CL_CELL_H
            if p.y == gy and abs(p.x - gx) <= 4:
                self.state = "won"
                self.audio.play("victory")
                return
        if self.energy <= 0:
            self._lose(LOST_ENERGY)

    # ------------------------------------------------------------------ portes
    def _try_door(self, dx):
        """On franchit une porte en poussant contre elle, au même Y et collé (&0F53)."""
        if not dx:
            self.contact.discard("door")
            return False
        p = self.player
        for slot, (cx, cy) in self.room["doors"].items():
            x, y = cx * CL_CELL_W, cy * CL_CELL_H
            if p.y != y:
                continue
            if slot[0] == "L" and dx < 0 and p.x == x + CL_SPRITE_W:
                pass
            elif slot[0] == "R" and dx > 0 and p.x + CL_SPRITE_W == x:
                pass
            else:
                continue
            dest, dslot, lock = W.DOOR_TO[(self.room_id, slot)]
            if lock and self.carried_kind != W.LOCK_ITEM[lock]:
                if "door" not in self.contact:
                    self.contact.add("door")
                    self.audio.play("denied")
                    self.say("PORTE SCELLEE : IL FAUT %s" % W.ITEMS[W.LOCK_ITEM[lock]]["art"], 3)
                return False
            self.enter_room(dest)
            ax, ay = W.arrival_cell(dest, dslot)
            p.x, p.y = ax * CL_CELL_W, ay * CL_CELL_H
            p.facing = 1 if dslot[0] == "L" else -1
            self.audio.play("door")
            return True
        return False

    # ------------------------------------------------------------------ chaudrons
    def _cauldron(self):
        c = self.room["cauldron"]
        if not c:
            return
        p = self.player
        cx, cy = c[0] * CL_CELL_W, c[1] * CL_CELL_H
        if p.y == cy - 16 and abs(p.x - cx) <= CL_CAULDRON_DX:
            if self.room_id in self.poison:                    # nocif (&14DD)
                self.energy = max(0, self.energy - CL_CAULDRON_BAD)
                if "cauldron" not in self.contact:
                    self.contact.add("cauldron")
                    self.audio.play("hurt")
                    self.say("CE CHAUDRON EST EMPOISONNE !", 3)
            elif self.energy < CL_ENERGY_MAX:                 # bienfaisant (&14A1)
                self.energy = min(CL_ENERGY_MAX, self.energy + CL_CAULDRON_GOOD)
                if self.tick % 8 == 0:
                    self.audio.play("cauldron")
        else:
            self.contact.discard("cauldron")

    # ------------------------------------------------------------------ barrières
    def barrier_touch(self, b, p=None):
        """Sorcier collé à la barrière : V au même niveau (±8 lignes), H au-dessus/dessous (±8 px)."""
        p = p or self.player
        bx, by = b[3] * CL_CELL_W, b[4] * CL_CELL_H
        if b[2] == "V":
            return abs(p.y - by) <= 8 and (p.x + CL_SPRITE_W == bx or p.x == bx + CL_SPRITE_W)
        return abs(p.x - bx) <= 8 and (p.y + CL_SPRITE_H == by or p.y == by + CL_SPRITE_H)

    def _barriers(self):
        for b in self.barriers_here():
            if not self.barrier_touch(b):
                self.contact.discard(("barrier", b[0]))
                continue
            if self.carried_kind == b[5]:
                self.open_barrier(b)
            elif ("barrier", b[0]) not in self.contact:
                self.contact.add(("barrier", b[0]))
                if b[0] in self.cage_ids():
                    self.say("CETTE CAGE S'OUVRE AVEC %s" % W.ITEMS[b[5]]["art"], 7)
                else:
                    self.say("IL FAUT %s POUR PASSER" % W.ITEMS[b[5]]["art"], 7)

    def cage_ids(self):
        return {W.cage_barrier(r)[0] for r in W.CAPTIVE_ROOMS}

    def open_barrier(self, b):
        """L'objet requis est consommé (ld (iy+5),0) ; la barrière disparaît pour la partie."""
        self.open_barriers.add(b[0])
        self.carried = None
        self._rebuild()
        self.audio.play("door")
        self.say("LA %s S'OUVRE" % ("GRILLE" if b[2] == "V" else "TRAPPE"), 8)

    # ------------------------------------------------------------------ captifs
    def _captive(self):
        c = self.room["captive"]
        if not c or self.room_id in self.freed:
            return
        p = self.player
        x, y = c[0] * CL_CELL_W, c[1] * CL_CELL_H
        if abs(p.y - y) <= CL_CAPTIVE_DY and abs(p.x - x) <= CL_CAPTIVE_DX:   # (&19E0)
            self.freed.append(self.room_id)
            self.score += CL_SCORE_FREE
            self.freed_anims.append([x, y, self.room_id])
            self.audio.play("free")
            n = len(self.freed)
            if n == len(W.CAPTIVE_ROOMS):
                self.say("LES 8 SONT LIBRES : RETOURNEZ AU SANCTUAIRE !", 1, 250)
            else:
                self.say("SORCIER LIBERE ! (%d/%d)" % (n, len(W.CAPTIVE_ROOMS)), 8, 150)

    # ------------------------------------------------------------------ bouton feu
    def in_contact(self, e, p=None):
        p = p or self.player
        return abs(e.y - p.y) <= CL_CONTACT_DY and abs(e.x - p.x) <= CL_CONTACT_DX

    def _fire(self):
        """Front montant de FEU : tuer à l'arme, sinon échanger, sinon lancer un sort."""
        p = self.player
        kind = self.carried_kind
        for e in self.enemies:
            if e.alive and not e.dying and self.in_contact(e) and kind == W.WEAPON[e.type]:
                self.kill(e, CL_SCORE_KILL)
                self.carried = None                      # l'arme est consommée
                return
        for it in self.items_here():
            if abs(it["y"] - p.y) <= CL_CONTACT_DY and abs(it["x"] - p.x) <= CL_CONTACT_DX:
                self.swap(it)
                return
        if kind in W.SPELLS:
            cx, cy = p.x + p.w // 2 - 1, p.y + p.h // 2 - 2
            for dy, dx in W.SPELLS[kind]:
                self.spells.append([cx, cy, dx, dy])
            self.carried = None                          # le sort est consommé
            self.audio.play("spell")
            return
        # sans objet à portée : rien (impossible de poser dans le vide)

    def swap(self, it):
        """Échange objet porté / objet posé (&17C5) ; premier ramassage : +250."""
        if self.carried:
            self.carried.update(room=self.room_id, x=it["x"], y=it["y"])
        it["room"] = None
        self.carried = it
        if not it["taken"]:
            it["taken"] = True
            self.score += CL_SCORE_PICKUP
        self.audio.play("pickup")
        self.say("VOUS PRENEZ %s" % W.ITEMS[it["kind"]]["art"], 5, 80)

    def kill(self, e, points):
        e.alive = False
        e.dying = 16
        e.anim = 0
        self.score += points
        self.audio.play("kill")

    # ------------------------------------------------------------------ ennemis
    def _enemies(self):
        p = self.player
        for e in self.enemies:
            if not e.alive:
                continue
            e.anim += 1
            sx, sy = CL_ENEMY_SPEED[e.type]
            if e.type == 1:                          # poursuite 2 axes, bloqué par les murs
                ddx = (p.x > e.x) - (p.x < e.x)
                ddy = (p.y > e.y) - (p.y < e.y)
                if ddx and not self.blocked(e.x + ddx * sx, e.y):
                    e.x += ddx * sx
                    e.dir = ddx
                if ddy and not self.blocked(e.x, e.y + ddy * sy):
                    e.y += ddy * sy
            else:                                    # marcheur (X) / spectre (X + Y, traverse)
                want = (p.x > e.x) - (p.x < e.x)
                if e.turn:
                    e.turn -= 1
                    if e.turn == 0:
                        e.dir = -e.dir
                elif want and want != e.dir:
                    e.turn = TURN_FRAMES
                elif want and abs(p.x - e.x) >= sx:
                    nx = e.x + e.dir * sx
                    if e.type == 3:
                        e.x = min(max(nx, 0), CL_X_MAX)
                    elif not self.blocked(nx, e.y):
                        e.x = nx
                if e.type == 3:
                    ddy = (p.y > e.y) - (p.y < e.y)
                    e.y = min(max(e.y + ddy * sy, 0), CL_Y_MAX)
            if self.in_contact(e):
                self.damage(ENEMY_DMG[e.type])

    def _spells(self):
        alive = []
        for s in self.spells:
            s[0] += s[2]
            s[1] += s[3]
            if not (0 <= s[0] < CL_PLAY_W and 0 <= s[1] < CL_PLAY_H):
                continue
            for e in self.enemies:
                if e.alive and not e.dying and e.x <= s[0] < e.x + e.w and e.y <= s[1] < e.y + e.h:
                    self.kill(e, CL_SCORE_SPELL)
            alive.append(s)
        self.spells = alive

    # ------------------------------------------------------------------ outils de test
    def place(self, rid, cx, cy):
        """Téléporte le sorcier (cellules) : utilisé par les tests et le rejeu du solveur."""
        if rid != self.room_id:
            self.enter_room(rid)
        self.player.x, self.player.y = cx * CL_CELL_W, cy * CL_CELL_H
        self.state = "play"
