"""Logique de jeu (indépendante du rendu) : une partie de Sorcery."""
import random
import zlib

from config import (TILE, PLAY_W, PLAY_H, ENERGY_MAX, TICK_HZ, TIME_LIMIT_MIN, TIME_LIMIT_CH2_MIN,
                    CHAPTER_SCREEN_TICKS, SCORE_KILL, SCORE_FREE, SCORE_BOSS, SCORE_TIME_PER_S,
                    SCORE_HEART, SCORE_CRAFT)
from world import (ROOMS, OBJECTS, DOORS, CAPTIVES, START, BOSS_HITS, BOSS_WEAPON_KIND, WATER,
                   HEARTS, CRAFTS, CHAPTER_START, build_tiles, door_sides, doors_in_room,
                   opening_cells, gate_rect)
from entities import RoomMap, Player, Enemy, Necromancer, overlap, grow

ITEM_W, ITEM_H = 7, 10
CAGE_W, CAGE_H = 16, 24
CAULDRON_W, CAULDRON_H = 16, 12


class Input:
    __slots__ = ("left", "right", "up", "down", "action")

    def __init__(self, left=False, right=False, up=False, down=False, action=False):
        self.left, self.right, self.up, self.down, self.action = left, right, up, down, action


class NullAudio:
    def play(self, name):
        pass


class Game:
    """État complet d'une partie. update(inp) = un tick de 1/50 s."""

    def __init__(self, audio=None, time_limit_min=TIME_LIMIT_MIN, seed=1985, chapter=1,
                 time2_min=TIME_LIMIT_CH2_MIN):
        self.audio = audio or NullAudio()
        self.seed = seed
        self.rng = random.Random(seed)
        self.tiles = {rid: build_tiles(rid) for rid in ROOMS}
        self.doors_open = set()
        self.items = {}
        for oid, o in OBJECTS.items():
            # un objet fabriqué n'existe pas tant qu'il n'a pas été forgé
            self.items[oid] = None if o.get("crafted") else self._spawn_item(oid)
        self.carried = None
        self.freed = []
        self.hearts = []                       # cœurs sacrés ramassés (Ch.2)
        self.craft_in = {cid: [] for cid in CRAFTS}   # ingrédients déposés par station
        self.crafted = set()
        self.boss_hp = BOSS_HITS               # persiste entre deux entrées dans le sanctuaire
        self.chapter = 1
        self.next_chapter = None
        self.chapter_bonus = 0
        self.time2_min = time2_min
        self.energy = ENERGY_MAX
        self.time_total = time_limit_min * 60 * TICK_HZ
        self.time_left = self.time_total
        self.score = 0
        self.state = "play"          # play / dying / boss_dying / lost / won
        self.lost_reason = ""
        self.timer = 0
        self.tick = 0
        self.msg = ""
        self.msg_t = 0
        self.msg_color = 15
        self.particles = []
        self.freed_anims = []
        self.boss = None
        self.boss_defeated = False
        self.time_bonus = 0
        self.fireballs = []
        self.contact = {}
        self.visited = set()
        self.rooms_version = 0
        if chapter == 2:                       # --chapter 2 : Ch.1 considéré comme terminé
            self.freed = list(CAPTIVES)
            self.items["sceptre"] = None
            self.start_chapter(2)
        else:
            sx, sy = START["at"]
            self.player = Player(sx * TILE, sy * TILE)
            self.enter_room(START["room"])
            self.say("LIBEREZ LES 8 SORCIERS CAPTIFS !", 11, 200)

    def start_chapter(self, n):
        """Début d'un chapitre : énergie pleine, nouveau compte à rebours, score conservé."""
        self.chapter = n
        self.next_chapter = None
        self.state = "play"
        self.energy = ENERGY_MAX
        self.time_total = self.time2_min * 60 * TICK_HZ
        self.time_left = self.time_total
        self.carried = None
        self.particles, self.freed_anims, self.fireballs = [], [], []
        st = CHAPTER_START[n]
        sx, sy = st["at"]
        self.player = Player(sx * TILE, sy * TILE)
        self.enter_room(st["room"])
        self.say("CHAPITRE %d : TROUVEZ LES %d COEURS SACRES !" % (n, len(HEARTS)), 11, 250)

    def _spawn_item(self, oid):
        o = OBJECTS[oid]
        tx, ty = o["at"]
        it = dict(room=o["room"], x=float(tx * TILE), y=float(ty * TILE + TILE - ITEM_H), vy=0.0)
        self._settle(it)
        return it

    # ------------------------------------------------------------------ helpers
    def say(self, text, color=15, ticks=150):
        self.msg, self.msg_color, self.msg_t = text, color, ticks

    def time_seconds(self):
        return max(0, (self.time_left + TICK_HZ - 1) // TICK_HZ)

    def _room_map(self, rid):
        tiles = self.tiles[rid]
        closed = {}
        for did, direction in doors_in_room(rid):
            if did not in self.doors_open:
                for cell in opening_cells(direction):
                    closed[cell] = did
        return RoomMap(rid, tiles, closed)

    def _settle(self, it):
        room = self._room_map(it["room"]) if not hasattr(self, "room") or self.room.rid != it["room"] else self.room
        while not room.rect_blocked(it["x"], it["y"] + 1, ITEM_W, ITEM_H) and it["y"] + ITEM_H < PLAY_H:
            it["y"] += 1

    def enter_room(self, rid):
        self.room_id = rid
        self.room = self._room_map(rid)
        self.visited.add(rid)
        data = ROOMS[rid]
        # graine stable (hash() de str est salé par processus : captures non reproductibles)
        rrng = random.Random(zlib.crc32(("%d:%s:%d" % (self.seed, rid, self.tick)).encode()))
        self.enemies = []
        for e in data["enemies"]:
            kind, tx, ty = e[:3]
            param = e[3] if len(e) > 3 else None
            self.enemies.append(Enemy(kind, tx, ty, param, rrng, self.room))
        self.fireballs = []
        self.boss = None
        if data["boss"] and not self.boss_defeated:
            self.boss = Necromancer(data["boss"]["anchors"], self.boss_hp, rrng)
        self.grace = 30
        self.contact = {}
        self.rooms_version += 1

    def items_here(self):
        return [(oid, it) for oid, it in self.items.items() if it is not None and it["room"] == self.room_id]

    @staticmethod
    def item_rect(it):
        return (it["x"], it["y"], ITEM_W, ITEM_H)

    @staticmethod
    def cage_rect(c):
        return (c["at"][0] * TILE, c["at"][1] * TILE, CAGE_W, CAGE_H)

    @staticmethod
    def craft_rect(c):
        return (c["at"][0] * TILE, c["at"][1] * TILE + 2 * TILE - CAULDRON_H, CAULDRON_W, CAULDRON_H)

    @staticmethod
    def cauldron_rect(c):
        return (c[0] * TILE, c[1] * TILE + 2 * TILE - CAULDRON_H, CAULDRON_W, CAULDRON_H)

    def spark(self, x, y, color, n=12, speed=1.2, life=30):
        for _ in range(n):
            self.particles.append([x, y, self.rng.uniform(-speed, speed), self.rng.uniform(-speed, speed * 0.6),
                                   life + self.rng.randrange(0, 15), color])

    # ------------------------------------------------------------------ actions
    def open_door(self, did):
        if did in self.doors_open:
            return
        self.doors_open.add(did)
        self.room = self._room_map(self.room_id)
        self.rooms_version += 1
        self.audio.play("portal" if DOORS[did].get("style") in ("portail", "sceau") else "door")
        self.say(DOORS[did]["name"] + " OUVERTE !", 7)
        for room, direction in door_sides(did):
            if room == self.room_id:
                cx, cy = opening_cells(direction)[1]
                self.spark(cx * TILE + 4, cy * TILE + 4, 11, 20)

    def free_captive(self, cid):
        c = CAPTIVES[cid]
        self.freed.append(cid)
        self.items[self.carried] = None        # objet de libération consommé
        self.carried = None
        self.score += SCORE_FREE
        r = self.cage_rect(c)
        self.freed_anims.append([r[0] + 4, r[1] + 4, 0, cid])
        self.spark(r[0] + 8, r[1] + 12, 7, 30, 1.6, 40)
        self.audio.play("free")
        n = len(self.freed)
        if n == len(CAPTIVES):
            for did, d in DOORS.items():
                if d.get("need_freed") is not None and n >= d["need_freed"]:
                    self.open_door(did)
            self.say("TOUS LIBRES ! LE PORTAIL DE STONEHENGE S'OUVRE", 11, 300)
        else:
            self.say("%s EST LIBRE !  (%d/%d)" % (c["name"], n, len(CAPTIVES)), 7, 180)

    def collect_heart(self, oid):
        it = self.items[oid]
        self.items[oid] = None
        self.hearts.append(oid)
        self.energy = min(ENERGY_MAX, self.energy + OBJECTS[oid].get("energy", 15))
        self.score += SCORE_HEART
        self.audio.play("heart")
        self.spark(it["x"] + 3, it["y"] + 3, 13, 24, 1.4, 35)
        n = len(self.hearts)
        if n == len(HEARTS):
            for did, d in DOORS.items():
                if d.get("need_hearts") is not None and n >= d["need_hearts"]:
                    self.open_door(did)
            self.say("LES %d COEURS ! LE SCEAU DU SANCTUAIRE SE BRISE" % n, 11, 300)
        else:
            self.say("COEUR SACRE !  (%d/%d)" % (n, len(HEARTS)), 13, 160)

    def _touch_craft(self, cid, c):
        """Dépose l'ingrédient porté dans la station ; forge l'objet quand tout y est."""
        if c["makes"] in self.crafted:
            return
        inside = self.craft_in[cid]
        if self.carried in c["needs"] and self.carried not in inside:
            oid = self.carried
            inside.append(oid)
            self.items[oid] = None
            self.carried = None
            r = self.craft_rect(c)
            self.spark(r[0] + 8, r[1] + 2, 12, 16, 1.0)
            if len(inside) == len(c["needs"]):
                self.crafted.add(c["makes"])
                self.items[c["makes"]] = self._spawn_item(c["makes"])
                self.score += SCORE_CRAFT
                self.audio.play("craft")
                self.spark(r[0] + 8, r[1] - 4, 15, 40, 1.8, 45)
                self.say("LE %s FORGE UN NOUVEAU %s !" % (c["name"], OBJECTS[c["makes"]]["name"]), 11, 250)
            else:
                self.audio.play("cauldron")
                self.say("%s FOND DANS LE %s (%d/%d)" % (OBJECTS[oid]["name"], c["name"],
                                                         len(inside), len(c["needs"])), 12, 200)
            self.contact[("craft", cid)] = True
        elif ("craft", cid) not in self.contact:
            self.contact[("craft", cid)] = True
            if self.carried:
                self.audio.play("denied")
                self.say("LE %s REJETTE : %s" % (c["name"], OBJECTS[self.carried]["name"]), 4)
            else:
                self.say("LE %s ATTEND L'ARGENT ET LA LUNE..." % c["name"], 12)

    def do_action(self):
        p = self.player
        pr = grow(p.rect(), 2)
        best, bestd = None, 1e9
        pcx, pcy = p.center()
        for oid, it in self.items_here():
            if OBJECTS[oid]["kind"] in ("potion", "coeur"):
                continue
            if overlap(pr, self.item_rect(it)):
                d = abs(it["x"] + ITEM_W / 2 - pcx) + abs(it["y"] + ITEM_H / 2 - pcy)
                if d < bestd:
                    best, bestd = oid, d
        if best is not None:
            it = self.items[best]
            if self.carried:
                self.items[self.carried] = dict(room=self.room_id, x=it["x"], y=it["y"], vy=0.0)
                self._settle(self.items[self.carried])
            self.items[best] = None
            self.carried = best
            self.audio.play("pickup")
            o = OBJECTS[best]
            if o.get("text"):
                self.say(o["text"], 11, 400)
            else:
                self.say("VOUS PRENEZ : " + o["name"], 15, 100)
        elif self.carried:
            oid = self.carried
            x = min(max(p.x + p.w / 2 - ITEM_W / 2, 0), PLAY_W - ITEM_W)
            it = dict(room=self.room_id, x=float(int(x)), y=float(int(p.y + p.h - ITEM_H)), vy=0.0)
            if self.room.rect_blocked(it["x"], it["y"], ITEM_W, ITEM_H):
                it["x"], it["y"] = float(int(p.x)), float(int(p.y))
            self.items[oid] = it
            self._settle(it)
            self.carried = None
            self.audio.play("drop")
            self.say("VOUS POSEZ : " + OBJECTS[oid]["name"], 14, 80)

    # ------------------------------------------------------------------ update
    def update(self, inp):
        self.tick += 1
        if self.msg_t:
            self.msg_t -= 1
        self._update_particles()
        if self.state == "play":
            self._update_play(inp)
        elif self.state == "chapter":            # écran de transition « CHAPITRE 2 »
            self.timer -= 1
            if self.timer <= 0 or (inp.action and self.timer < CHAPTER_SCREEN_TICKS - 50):
                self.start_chapter(self.next_chapter)
        elif self.state == "dying":
            self.timer -= 1
            self.player.y = min(self.player.y + 0.5, PLAY_H - self.player.h - TILE)
            if self.timer <= 0:
                self.state = "lost"
        elif self.state == "boss_dying":
            self.timer -= 1
            if self.boss:
                self.boss.update(self.player, [])
                if self.tick % 4 == 0:
                    b = self.boss
                    self.spark(b.x + self.rng.uniform(0, b.w), b.y + self.rng.uniform(0, b.h),
                               self.rng.choice((4, 11, 13, 15)), 6, 1.5, 25)
            if self.timer <= 0:
                self.state = "won"
                self.time_bonus = self.final_bonus()
                self.score += self.time_bonus

    def _update_particles(self):
        for pt in self.particles:
            pt[0] += pt[2]
            pt[1] += pt[3]
            pt[3] += 0.03
            pt[4] -= 1
        self.particles = [pt for pt in self.particles if pt[4] > 0]
        for fa in self.freed_anims:
            fa[1] -= 0.8
            fa[2] += 1
        self.freed_anims = [fa for fa in self.freed_anims if fa[2] < 120]

    def _hurt(self, amount):
        self.energy -= amount
        if self.player.hurt <= 0:
            self.player.hurt = 12
            self.audio.play("hurt")

    def _update_play(self, inp):
        p = self.player
        self.time_left -= 1
        p.update(inp, self.room)
        self._check_transition()
        pr = p.rect()

        # objets qui tombent (posés en l'air)
        for oid, it in self.items_here():
            if not self.room.rect_blocked(it["x"], it["y"] + 1, ITEM_W, ITEM_H) and it["y"] + ITEM_H < PLAY_H:
                it["y"] += 1

        # potions : consommées au contact
        for oid, it in self.items_here():
            o = OBJECTS[oid]
            if o["kind"] == "potion" and overlap(pr, self.item_rect(it)):
                self.items[oid] = None
                self.energy = min(ENERGY_MAX, self.energy + o.get("energy", 40))
                self.audio.play("potion")
                self.say("UN COEUR MAGIQUE : ENERGIE +", 13)
                self.spark(it["x"] + 3, it["y"] + 3, 13, 15)
            elif o["kind"] == "coeur" and overlap(pr, self.item_rect(it)):
                self.collect_heart(oid)

        if inp.action:
            self.do_action()

        near = grow(pr, 2)
        # portes
        for did, direction in doors_in_room(self.room_id):
            if did in self.doors_open:
                continue
            d = DOORS[did]
            touching = any(overlap(near, (cx * TILE, cy * TILE, TILE, TILE)) for cx, cy in opening_cells(direction))
            if not touching:
                self.contact.pop(("door", did), None)
                continue
            if d.get("key") and self.carried == d["key"]:
                self.open_door(did)
            elif d.get("need_freed") is not None and len(self.freed) >= d["need_freed"]:
                self.open_door(did)
            elif d.get("need_hearts") is not None and len(self.hearts) >= d["need_hearts"]:
                self.open_door(did)
            elif ("door", did) not in self.contact:
                self.contact[("door", did)] = True
                self.audio.play("denied")
                if d.get("need_freed") is not None:
                    self.say("LIBEREZ D'ABORD LES %d SORCIERS !" % d["need_freed"], 4)
                elif d.get("need_hearts") is not None:
                    self.say("LE SCEAU EXIGE %d COEURS SACRES (%d/%d)" % (
                        d["need_hearts"], len(self.hearts), d["need_hearts"]), 4)
                else:
                    self.say(d["name"] + " : FERMEE", 4)

        # captifs
        for cid, c in CAPTIVES.items():
            if c["room"] != self.room_id or cid in self.freed:
                continue
            if overlap(pr, self.cage_rect(c)):
                if self.carried == c["item"]:
                    self.free_captive(cid)
                elif ("cage", cid) not in self.contact:
                    self.contact[("cage", cid)] = True
                    if self.carried:
                        self.audio.play("denied")
                        self.say("%s : CE N'EST PAS LE BON OBJET..." % c["name"], 12)
                    else:
                        self.say("%s : AIDE-MOI, SORCIER !" % c["name"], 12)
            else:
                self.contact.pop(("cage", cid), None)

        # stations de fabrication (creuset)
        for cid, c in CRAFTS.items():
            if c["room"] != self.room_id:
                continue
            if overlap(near, self.craft_rect(c)):
                self._touch_craft(cid, c)
            else:
                self.contact.pop(("craft", cid), None)

        # vortex (fin du chapitre)
        gate = ROOMS[self.room_id].get("gate")
        if gate:
            if overlap(pr, gate_rect(gate)):
                if self.carried == gate["key"]:
                    self.items[self.carried] = None     # le Sceptre se brise dans le vortex
                    self.carried = None
                    self.chapter_bonus = self.time_seconds() * SCORE_TIME_PER_S
                    self.score += self.chapter_bonus
                    self.next_chapter = gate["to"]
                    self.state = "chapter"
                    self.timer = CHAPTER_SCREEN_TICKS
                    self.audio.play("portal")
                    return
                if ("gate", 0) not in self.contact:
                    self.contact[("gate", 0)] = True
                    self.audio.play("denied")
                    if self.carried and OBJECTS[self.carried]["kind"] == "relique":
                        self.say("CETTE RELIQUE EST SANS EFFET !", 4)
                    else:
                        self.say("LE VORTEX EXIGE LA VRAIE RELIQUE", 4)
            else:
                self.contact.pop(("gate", 0), None)

        # chaudrons
        for c in ROOMS[self.room_id]["cauldrons"]:
            if overlap(near, self.cauldron_rect(c)):
                if c[2] == "plein":
                    if self.energy < ENERGY_MAX:
                        self.energy = min(ENERGY_MAX, self.energy + 0.5)
                        if self.tick % 16 == 0:
                            self.audio.play("cauldron")
                    if ("cauldron", c) not in self.contact:
                        self.contact[("cauldron", c)] = True
                        self.say("LE CHAUDRON VOUS REVIGORE", 7, 100)
                else:
                    self._hurt(0.4)
                    if ("cauldron", c) not in self.contact:
                        self.contact[("cauldron", c)] = True
                        self.say("CHAUDRON MAUDIT !", 4, 100)
            else:
                self.contact.pop(("cauldron", c), None)

        # eau
        if self.room.rect_touches_kind(p.x, p.y + 1, p.w, p.h, WATER):
            self._hurt(0.7 if ROOMS[self.room_id]["lava"] else 0.4)

        # ennemis
        if self.grace:
            self.grace -= 1
        for e in self.enemies:
            if not e.alive:
                continue
            if not self.grace:
                e.update(self.room, p)
            if e.active and overlap(pr, e.rect()):
                if self.carried and self.carried in e.type["killed_by"]:
                    e.alive = False
                    self.score += SCORE_KILL
                    self.audio.play("kill")
                    self.spark(e.x + e.w / 2, e.y + e.h / 2, 15, 16)
                elif not self.grace:
                    self._hurt(e.type["drain"])

        # boss
        b = self.boss
        if b and not self.boss_defeated:
            b.update(p, self.fireballs)
            weapon = self.carried and OBJECTS[self.carried]["kind"] == BOSS_WEAPON_KIND
            if b.solid and overlap(pr, b.rect()):
                if weapon and not b.invuln:
                    b.hit()
                    self.boss_hp = b.hp
                    self.items[self.carried] = None      # le pentacle se brise sur lui
                    self.carried = None
                    self.audio.play("boss_hit")
                    self.spark(b.x + b.w / 2, b.y + b.h / 2, 13, 25, 1.8)
                    if b.hp <= 0:
                        self.boss_defeated = True
                        self.score += SCORE_BOSS
                        self.state = "boss_dying"
                        self.timer = 150
                        self.fireballs = []
                        self.say("LE NECROMANCIEN EST DETRUIT !", 11, 300)
                        self.audio.play("victory")
                        return
                    self.say("LE PENTACLE SE BRISE : IL FAIBLIT ! (%d)" % b.hp, 11)
                elif not b.invuln:
                    if self.carried and ("boss", 0) not in self.contact:
                        self.contact[("boss", 0)] = True
                        self.say("SEUL UN PENTACLE PEUT LE BLESSER !", 4)
                    self._hurt(0.5)
            else:
                self.contact.pop(("boss", 0), None)
            for fb in self.fireballs:
                fb.update(self.room)
                if fb.alive and overlap(pr, fb.rect()):
                    fb.alive = False
                    self._hurt(6)
            self.fireballs = [fb for fb in self.fireballs if fb.alive]
            if b.t % b.SHOOT == 1 and b.solid:
                self.audio.play("fireball")

        # fin de partie
        if self.energy <= 0:
            self.energy = 0
            self.state = "dying"
            self.timer = 75
            self.lost_reason = "VOTRE ENERGIE EST EPUISEE"
            self.audio.play("gameover")
        elif self.time_left <= 0:
            self.time_left = 0
            self.state = "lost"
            self.lost_reason = "LE TEMPS EST ECOULE"
            self.audio.play("gameover")

    def _check_transition(self):
        p = self.player
        cx, cy = p.center()
        exits = ROOMS[self.room_id]["exits"]
        direction = None
        if cx < 0:
            direction, p.x = "W", p.x + PLAY_W
        elif cx >= PLAY_W:
            direction, p.x = "E", p.x - PLAY_W
        elif cy < 0:
            direction, p.y = "N", p.y + PLAY_H
        elif cy >= PLAY_H:
            direction, p.y = "S", p.y - PLAY_H
        if direction is None:
            return
        target = exits.get(direction)
        if target is None:          # ne devrait pas arriver (murs) : on annule
            p.x = min(max(p.x, TILE), PLAY_W - TILE - p.w)
            p.y = min(max(p.y, TILE), PLAY_H - TILE - p.h)
            return
        self.enter_room(target)
        # sécurité : ne jamais apparaître dans un mur
        if self.room.rect_blocked(p.x, p.y, p.w, p.h):
            for dy in range(0, 40):
                for sy in (-dy, dy):
                    if not self.room.rect_blocked(p.x, p.y + sy, p.w, p.h):
                        p.y += sy
                        return

    def final_bonus(self):
        return self.time_seconds() * SCORE_TIME_PER_S
