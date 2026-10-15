"""Tests headless : intégrité des données, accessibilité, BFS de victoire, simulation.

Lancer : python main.py --selftest   (ou python selftest.py)
"""
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from config import COLS, ROWS, TILE, PLAY_H  # noqa: E402
from world import (ROOMS, OBJECTS, DOORS, CAPTIVES, ENEMY_TYPES, ZONES, START, FINAL_WEAPON,  # noqa: E402
                   OPPOSITE, DELTA, SOLID, WATER, EMPTY, FAKE, HEARTS, CRAFTS, CHAPTER_START,
                   BOSS_HITS, BOSS_WEAPON_KIND, build_tiles, door_sides, opening_cells, room_chapter)
import solver  # noqa: E402
import selftest_classic  # noqa: E402  (tests du mode Classique CPC 1985)

FOOT_W, FOOT_H = 2, 3          # empreinte (en tuiles) conservative du sorcier 6x16 px


class Report:
    def __init__(self):
        self.errors = []
        self.passed = 0

    def check(self, cond, msg):
        if cond:
            self.passed += 1
        else:
            self.errors.append(msg)
        return cond


# ------------------------------------------------------------------ données
def check_data(rep):
    grid = {}
    for rid, r in ROOMS.items():
        rep.check(r["zone"] in ZONES, "%s: zone inconnue" % rid)
        key = (room_chapter(rid), r["grid"])         # une grille par chapitre
        rep.check(key not in grid, "%s: position de grille dupliquée %s" % (rid, key))
        grid[key] = rid
    for rid, r in ROOMS.items():
        for d, nxt in r["exits"].items():
            if not rep.check(nxt in ROOMS, "%s: sortie %s -> salle inexistante %s" % (rid, d, nxt)):
                continue
            back = ROOMS[nxt]["exits"].get(OPPOSITE[d])
            rep.check(back == rid, "%s: sortie %s -> %s non réciproque (%s)" % (rid, d, nxt, back))
            rep.check(room_chapter(nxt) == room_chapter(rid), "%s: sortie %s vers un autre chapitre" % (rid, d))
            dx, dy = DELTA[d]
            gx, gy = r["grid"]
            rep.check(ROOMS[nxt]["grid"] == (gx + dx, gy + dy),
                      "%s: sortie %s incohérente avec la grille" % (rid, d))
        for e in r["enemies"]:
            rep.check(e[0] in ENEMY_TYPES, "%s: type d'ennemi inconnu %s" % (rid, e[0]))
        for c in r["cauldrons"]:
            rep.check(c[2] in ("plein", "maudit"), "%s: chaudron invalide" % rid)
    rep.check(START["room"] in ROOMS, "salle de départ inexistante")
    for t, et in ENEMY_TYPES.items():
        for k in et["killed_by"]:
            rep.check(k in OBJECTS, "ennemi %s tué par objet inexistant %s" % (t, k))
    for oid, o in OBJECTS.items():
        rep.check(o["room"] in ROOMS, "objet %s dans salle inexistante" % oid)
    for did, d in DOORS.items():
        rep.check(d["room"] in ROOMS and d["dir"] in ROOMS[d["room"]]["exits"],
                  "porte %s sur une sortie inexistante" % did)
        rep.check(d.get("key") is None or d["key"] in OBJECTS, "porte %s : clé inexistante" % did)
        rep.check(d.get("key") or d.get("need_freed") or d.get("need_hearts"),
                  "porte %s sans condition d'ouverture" % did)
        sides = door_sides(did)
        rep.check(room_chapter(sides[0][0]) == room_chapter(sides[1][0]), "porte %s entre deux chapitres" % did)
        if d.get("key") in OBJECTS:
            rep.check(room_chapter(OBJECTS[d["key"]]["room"]) == room_chapter(d["room"]),
                      "porte %s : clé dans l'autre chapitre" % did)
    items = [c["item"] for c in CAPTIVES.values()]
    rep.check(len(items) == len(set(items)), "objets de libération non uniques")
    door_keys = {d.get("key") for d in DOORS.values()}
    for cid, c in CAPTIVES.items():
        rep.check(c["room"] in ROOMS, "captif %s dans salle inexistante" % cid)
        rep.check(c["item"] in OBJECTS, "captif %s : objet inexistant" % cid)
        rep.check(OBJECTS.get(c["item"], {}).get("kind") == "captif", "captif %s : objet pas de type captif" % cid)
        rep.check(c["item"] not in door_keys, "captif %s : objet aussi clé de porte" % cid)
    rep.check(FINAL_WEAPON in OBJECTS, "relique du vortex inexistante")
    rep.check(len(CAPTIVES) == 8, "il faut 8 captifs")
    ch1 = [rid for rid in ROOMS if room_chapter(rid) == 1]
    ch2 = [rid for rid in ROOMS if room_chapter(rid) == 2]
    rep.check(25 <= len(ch1) <= 47, "Ch.1 : nombre de salles hors cible : %d" % len(ch1))
    rep.check(len(ch2) == 28, "Ch.2 : il faut 28 salles (%d)" % len(ch2))
    rep.check(len(ch1) + len(ch2) == len(ROOMS), "salle sans chapitre")
    bosses = [rid for rid, r in ROOMS.items() if r["boss"]]
    rep.check(len(bosses) == 1 and room_chapter(bosses[0]) == 2, "il faut une salle de boss, au Ch.2")
    for rid, r in ROOMS.items():
        g = r.get("gate")
        if g:
            rep.check(room_chapter(rid) == 1 and g["to"] in CHAPTER_START and g["key"] in OBJECTS,
                      "%s: vortex invalide" % rid)
    rep.check(sum(1 for r in ROOMS.values() if r.get("gate")) == 1, "il faut exactement un vortex")
    for n, st in CHAPTER_START.items():
        rep.check(st["room"] in ROOMS and room_chapter(st["room"]) == n, "départ du chapitre %d invalide" % n)
    for cid, c in CAPTIVES.items():
        rep.check(room_chapter(c["room"]) == 1, "captif %s hors du Ch.1" % cid)
    # cœurs
    rep.check(len(HEARTS) == 8, "il faut 8 cœurs sacrés (%d)" % len(HEARTS))
    for oid in HEARTS:
        rep.check(room_chapter(OBJECTS[oid]["room"]) == 2, "cœur %s hors du Ch.2" % oid)
    rep.check(any(d.get("need_hearts") == len(HEARTS) for d in DOORS.values()), "aucun sceau à %d cœurs" % len(HEARTS))
    # 3 exemplaires : 2 dans le monde + 1 fabriqué
    pents = [o for o, d in OBJECTS.items() if d["kind"] == BOSS_WEAPON_KIND]
    made = [o for o in pents if OBJECTS[o].get("crafted")]
    rep.check(BOSS_HITS == 3 and len(pents) == 3 and len(made) == 1,
              "il faut 3 pentacles dont 1 fabriqué (%d / %d)" % (len(pents), len(made)))
    for cid, c in CRAFTS.items():
        rep.check(c["room"] in ROOMS, "station %s dans une salle inexistante" % cid)
        rep.check(all(n in OBJECTS and not OBJECTS[n].get("crafted") for n in c["needs"]),
                  "station %s : ingrédient invalide" % cid)
        rep.check(OBJECTS.get(c["makes"], {}).get("crafted") == cid, "station %s : produit invalide" % cid)
        rep.check(OBJECTS[c["makes"]]["room"] == c["room"], "station %s : produit hors de la salle" % cid)
    for oid, o in OBJECTS.items():
        rep.check(o["kind"] in ("arme", "cle", "indice", "captif", "relique", "potion", "coeur",
                                "ingredient", "pentacle"), "objet %s : type inconnu" % oid)


# ------------------------------------------------------------------ accessibilité intra-salle
def flood(rid):
    """Positions d'empreinte (tx, ty) atteignables en vol, portes ouvertes, faux murs franchissables."""
    t = build_tiles(rid)

    def free(cx, cy):
        if cx < 0 or cy < 0 or cx >= COLS or cy >= ROWS:
            return False
        return t[cy][cx] in (EMPTY, FAKE)

    def ok(x, y):
        return all(free(x + i, y + j) for i in range(FOOT_W) for j in range(FOOT_H))

    starts = {}
    for d in ROOMS[rid]["exits"]:
        cells = opening_cells(d)
        cand = []
        for cx, cy in cells:
            for x in range(cx - FOOT_W + 1, cx + 1):
                for y in range(cy - FOOT_H + 1, cy + 1):
                    if ok(x, y):
                        cand.append((x, y))
        starts[d] = cand
    for n, st in CHAPTER_START.items():
        if rid == st["room"]:
            sx, sy = st["at"]
            starts["start%d" % n] = [(sx, sy)] if ok(sx, sy) else []
    seen = set()
    first = None
    comps = {}
    for key, cand in starts.items():
        if not cand:
            comps[key] = None
            continue
        if cand[0] in seen:
            comps[key] = comps.get(("pos", cand[0]))
            continue
        # BFS
        comp = set([cand[0]])
        q = [cand[0]]
        while q:
            x, y = q.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if n not in comp and ok(*n):
                    comp.add(n)
                    q.append(n)
        seen |= comp
        for p in comp:
            comps[("pos", p)] = id(comp)
        comps[key] = id(comp)
        if first is None:
            first = comp
        comps[("set", id(comp))] = comp
    return t, starts, comps


def touchable(comp, rect_tiles):
    x0, y0, x1, y1 = rect_tiles
    for (x, y) in comp:
        if x <= x1 and x + FOOT_W - 1 >= x0 and y <= y1 and y + FOOT_H - 1 >= y0:
            return True
    return False


def check_rooms(rep, game):
    from game import ITEM_W, ITEM_H, CAGE_W, CAGE_H
    for rid, r in ROOMS.items():
        t, starts, comps = flood(rid)
        keys = [k for k in starts]
        ids = set()
        for k in keys:
            rep.check(comps.get(k) is not None, "%s: entrée %s bloquée" % (rid, k))
            if comps.get(k) is not None:
                ids.add(comps[k])
        rep.check(len(ids) <= 1, "%s: sorties non reliées entre elles (%d zones)" % (rid, len(ids)))
        if not ids:
            continue
        comp = comps[("set", ids.pop())]
        # objets (position initiale posée)
        for oid, o in OBJECTS.items():
            if o["room"] != rid:
                continue
            tx, ty = o["at"]
            rep.check(t[ty][tx] in (EMPTY, FAKE), "%s: objet %s placé dans un mur" % (rid, oid))
            it = game.items[oid] or game._spawn_item(oid)      # objet fabriqué : position finale
            rt = (int(it["x"] // TILE), int(it["y"] // TILE),
                  int((it["x"] + ITEM_W - 1) // TILE), int((it["y"] + ITEM_H - 1) // TILE))
            rep.check(touchable(comp, rt), "%s: objet %s inaccessible" % (rid, oid))
        for cid, c in CAPTIVES.items():
            if c["room"] != rid:
                continue
            x, y = c["at"]
            rep.check(all(t[y + j][x + i] in (EMPTY,) for i in range(2) for j in range(3)),
                      "%s: cage de %s dans un mur" % (rid, cid))
            rep.check(any(t[y + 3][x + i] in (SOLID, WATER) for i in range(2)),
                      "%s: cage de %s ne repose sur rien" % (rid, cid))
            rep.check(touchable(comp, (x, y, x + 1, y + 2)), "%s: captif %s inaccessible" % (rid, cid))
        for c in r["cauldrons"]:
            x, y = c[0], c[1]
            rep.check(all(t[y + j][x + i] == EMPTY for i in range(2) for j in range(2)),
                      "%s: chaudron dans un mur" % rid)
            rep.check(any(t[y + 2][x + i] in (SOLID, WATER) for i in range(2)), "%s: chaudron en l'air" % rid)
            rep.check(touchable(comp, (x, y, x + 1, y + 1)), "%s: chaudron inaccessible" % rid)
        for cid, c in CRAFTS.items():
            if c["room"] != rid:
                continue
            x, y = c["at"]
            rep.check(all(t[y + j][x + i] == EMPTY for i in range(2) for j in range(2)),
                      "%s: station %s dans un mur" % (rid, cid))
            rep.check(any(t[y + 2][x + i] == SOLID for i in range(2)), "%s: station %s en l'air" % (rid, cid))
            rep.check(touchable(comp, (x, y, x + 1, y + 1)), "%s: station %s inaccessible" % (rid, cid))
        g = r.get("gate")
        if g:
            (x, y), (w, h) = g["at"], g["size"]
            rep.check(all(t[y + j][x + i] == EMPTY for i in range(w) for j in range(h)), "%s: vortex dans un mur" % rid)
            rep.check(touchable(comp, (x, y, x + w - 1, y + h - 1)), "%s: vortex inaccessible" % rid)
        for e in r["enemies"]:
            kind, x, y = e[:3]
            rep.check(0 <= x < COLS and 0 <= y < ROWS and t[y][x] != SOLID or ENEMY_TYPES[kind]["move"] == "jump",
                      "%s: ennemi %s dans un mur" % (rid, kind))
            if ENEMY_TYPES[kind]["move"] == "jump":
                rep.check(r["water"] and t[ROWS - 2][x] == WATER, "%s: %s hors du liquide" % (rid, kind))


# ------------------------------------------------------------------ simulation
def simulate_scripted(rep, frames=600, render=True, chapter=1):
    from game import Game, Input
    from render import Renderer
    g = Game(chapter=chapter)
    r = Renderer() if render else None
    script = [(80, dict(right=True)), (40, dict(up=True)), (60, dict(left=True, up=True)),
              (1, dict(action=True)), (50, dict(right=True)), (30, dict(down=True)),
              (60, dict(left=True)), (1, dict(action=True)), (90, dict(right=True, up=True)),
              (80, dict(right=True)), (60, dict()), (48, dict(left=True, down=True))]
    n = 0
    rooms = set()
    while n < frames:
        for dur, keys in script:
            for _ in range(dur):
                g.update(Input(**keys))
                rooms.add(g.room_id)
                if r and n % 5 == 0:
                    r.draw_game(g)
                    r.compose()
                n += 1
                if n >= frames:
                    break
            if n >= frames:
                break
    rep.check(g.state in ("play", "dying", "lost"), "état inattendu après simulation : %s" % g.state)
    rep.check(0 <= g.energy <= 100, "énergie hors bornes")
    p = g.player
    rep.check(not g.room.rect_blocked(p.x, p.y, p.w, p.h), "le joueur est coincé dans un mur")
    return n, rooms


def simulate_enemies(rep, ticks=400):
    """Toutes les salles : ennemis mis à jour + rendu, sans plantage ni fuite hors écran."""
    from game import Game, Input
    from render import Renderer
    from config import PLAY_W
    r = Renderer()
    g = Game()
    kinds = set()
    for rid in ROOMS:
        g.enter_room(rid)
        g.grace = 0
        g.player.x, g.player.y = 76.0, 60.0
        for t in range(ticks):
            for e in g.enemies:
                e.update(g.room, g.player)
            if t % 50 == 0:
                r.draw_game(g)
        for e in g.enemies:
            kinds.add(e.kind)
            rep.check(-2 <= e.x <= PLAY_W + 2 and -20 <= e.y <= PLAY_H + 20,
                      "%s: ennemi %s sorti de l'écran (%.0f,%.0f)" % (rid, e.kind, e.x, e.y))
    rep.check(set(ENEMY_TYPES) <= kinds, "types d'ennemis jamais placés : %s" % (set(ENEMY_TYPES) - kinds))
    return kinds


def playthrough(rep, render=True):
    """Exécute le plan du solveur dans le vrai moteur, du Ch.1 à la victoire au Ch.2
    (téléportation entre étapes ; le transport d'objets, les dépôts et les coups sont réels)."""
    from game import Game, Input, ITEM_H, ITEM_W
    from render import Renderer
    rend = Renderer() if render else None
    g = Game()
    win, plan, _ = solver.solve()
    idle = Input()
    log = dict(chapters=[], hp=[])

    def frames(n, inp=idle):
        for _ in range(n):
            g.energy = 100          # triche de test : on ne valide que la logique
            g.update(inp)
            if rend and g.tick % 25 == 0:
                if g.state == "chapter":
                    rend.draw_chapter(g, g.tick)
                else:
                    rend.draw_game(g)

    def goto(rid, x, y):
        g.enter_room(rid)
        g.grace = 1000
        g.player.x, g.player.y = float(x), float(y)

    def fetch(oid):
        if g.carried == oid:
            return True
        it = g.items[oid]
        if it is None:
            return False
        goto(it["room"], it["x"], it["y"] + ITEM_H - 16)
        g.update(Input(action=True))
        return g.carried == oid

    for kind, what, item, room in plan:
        if kind == "open":
            if item:
                rep.check(fetch(item), "playthrough: impossible de prendre %s" % item)
            side = [s for s in door_sides(what) if s[0] == room][0]
            cells = opening_cells(side[1])
            cx, cy = cells[len(cells) // 2]
            x = min(max(cx * TILE, TILE), (COLS - 1) * TILE - 6)
            y = min(max(cy * TILE - 8, TILE), PLAY_H - TILE - 16)
            goto(room, x, y)
            frames(3)
            rep.check(what in g.doors_open, "playthrough: porte %s pas ouverte" % what)
        elif kind == "free":
            rep.check(fetch(item), "playthrough: impossible de prendre %s" % item)
            c = CAPTIVES[what]
            goto(c["room"], c["at"][0] * TILE + 4, c["at"][1] * TILE + 4)
            frames(2)
            rep.check(what in g.freed, "playthrough: %s pas libéré" % what)
        elif kind == "heart":
            it = g.items[what]
            rep.check(it is not None, "playthrough: cœur %s absent" % what)
            if it:
                goto(it["room"], it["x"], it["y"] + ITEM_H - 16)
                frames(2)
            rep.check(what in g.hearts, "playthrough: cœur %s pas ramassé" % what)
        elif kind == "craft":
            c = CRAFTS[what]
            for n in item:
                rep.check(fetch(n), "playthrough: impossible de prendre l'ingrédient %s" % n)
                goto(c["room"], c["at"][0] * TILE + 4, c["at"][1] * TILE - 10)
                frames(2)
                rep.check(n in g.craft_in[what], "playthrough: %s pas déposé au %s" % (n, c["name"]))
            rep.check(c["makes"] in g.crafted and g.items[c["makes"]] is not None,
                      "playthrough: %s pas fabriqué" % c["makes"])
        elif kind == "gate":
            rep.check(fetch(item), "playthrough: impossible de prendre %s" % item)
            gate = ROOMS[room]["gate"]
            goto(room, gate["at"][0] * TILE + 12, gate["at"][1] * TILE + 8)
            frames(2)
            rep.check(g.state == "chapter", "playthrough: le vortex ne mène pas au chapitre suivant")
            log["chapters"].append((g.state, g.chapter_bonus))
            frames(60)
            g.update(Input(action=True))          # Espace : passe l'écran de transition
            rep.check(g.state == "play" and g.chapter == gate["to"], "playthrough: Ch.%d non démarré" % gate["to"])
            rep.check(g.energy == 100 and g.time_left == g.time_total, "playthrough: Ch.2 sans énergie/temps neufs")
            log["chapters"].append((g.room_id, g.score))
        else:
            # On dépose d'abord les 3 pentacles dans le sanctuaire (un seul porté à la fois),
            # puis on les reprend un par un pour frapper : chaque coup en consomme un.
            for oid in item:
                rep.check(fetch(oid), "playthrough: impossible de prendre %s" % oid)
                goto(room, 20 + 8 * item.index(oid), 120)
                frames(1)
                g.update(Input(action=True))
                rep.check(g.carried is None and g.items[oid]["room"] == room, "playthrough: %s pas posé" % oid)
            frames(5)
            for oid in item:
                it = g.items[oid]
                g.player.x, g.player.y = it["x"], it["y"] + ITEM_H - 16
                g.update(Input(action=True))
                rep.check(g.carried == oid, "playthrough: %s pas repris dans le sanctuaire" % oid)
                hp = g.boss_hp
                for _ in range(1500):
                    b = g.boss
                    if g.state != "play" or g.boss_hp < hp:
                        break
                    if b and b.solid and not b.invuln:
                        g.player.x, g.player.y = b.x + 2, b.y + 2
                    frames(1)
                rep.check(g.items[oid] is None and g.carried is None, "playthrough: %s pas consommé" % oid)
                log["hp"].append(g.boss_hp)
                g.player.x, g.player.y = 76.0, 120.0
            frames(200)
    rep.check(g.state == "won", "playthrough: la partie n'est pas gagnée (état %s)" % g.state)
    rep.check(len(g.freed) == len(CAPTIVES), "playthrough: captifs libérés %d" % len(g.freed))
    rep.check(len(g.hearts) == len(HEARTS), "playthrough: cœurs %d" % len(g.hearts))
    rep.check(log["hp"] == list(range(BOSS_HITS - 1, -1, -1)), "playthrough: PV du boss %s" % log["hp"])
    g.log = log
    return g


def check_game_over(rep):
    from game import Game, Input
    g = Game(time_limit_min=0)
    g.time_left = 10
    for _ in range(20):
        g.update(Input())
    rep.check(g.state == "lost" and "TEMPS" in g.lost_reason, "fin par temps non détectée")
    g = Game()
    g.energy = 0.1
    g.water_test = True
    g._hurt(1)
    for _ in range(100):
        g.update(Input())
    rep.check(g.state == "lost" and "ENERGIE" in g.lost_reason, "fin par énergie non détectée")
    g = Game(chapter=2)
    g.time_left = 10
    for _ in range(20):
        g.update(Input())
    rep.check(g.state == "lost" and "TEMPS" in g.lost_reason, "Ch.2 : fin par temps non détectée")


def check_mechanics(rep):
    """Tests ciblés : prise/échange/pose, porte refusée, chaudron, passage de salle."""
    from game import Game, Input
    g = Game()
    # vol vers la gauche jusqu'à la salle L1
    for _ in range(200):
        g.update(Input(left=True))
        if g.room_id != "L2":
            break
    rep.check(g.room_id == "L1", "transition ouest L2->L1 échouée (%s)" % g.room_id)
    g = Game()
    g.enter_room("L4")
    it = g.items["epee"]
    g.player.x, g.player.y = it["x"], it["y"] - 6
    g.update(Input(action=True))
    rep.check(g.carried == "epee", "ramassage échoué")
    g.player.x -= 30
    for _ in range(40):
        g.update(Input())
    g.update(Input(action=True))
    rep.check(g.carried is None and g.items["epee"] is not None, "pose échouée")
    # échange
    g.player.x, g.player.y = g.items["epee"]["x"], g.items["epee"]["y"] - 6
    g.carried = "hache"
    g.items["hache"] = None
    g.update(Input(action=True))
    rep.check(g.carried == "epee" and g.items["hache"]["room"] == "L4", "échange échoué")
    # chaudron
    g = Game()
    g.energy = 50
    c = ROOMS["L2"]["cauldrons"][0]
    g.player.x, g.player.y = c[0] * TILE + 4, c[1] * TILE - 16
    for _ in range(50):
        g.update(Input())
    rep.check(g.energy > 60, "le chaudron ne recharge pas (%.1f)" % g.energy)
    # porte fermée sans clé
    g = Game()
    g.enter_room("L3")
    g.player.x, g.player.y = 19 * TILE - 8, 15 * TILE
    for _ in range(30):
        g.update(Input(right=True))
    rep.check(g.room_id == "L3" and "porte_bois" not in g.doors_open, "la porte de bois s'ouvre sans hache")
    # tuer un ennemi avec la bonne arme
    g = Game()
    g.enter_room("L1")
    g.grace = 0
    g.carried = "epee"
    e = g.enemies[0]
    g.player.x, g.player.y = e.x, e.y - 4
    g.update(Input())
    rep.check(not e.alive and g.score >= 100, "l'épée ne tue pas le crâne")


def check_chapter2(rep):
    """Mécanique du Ch.2 : vortex, transition, cœurs, sceau, creuset, boss à 3 pentacles."""
    from game import Game, Input
    from config import ENERGY_MAX
    # vortex : refusé sans le Sceptre, refusé avec une autre relique, accepté avec lui
    g = Game()
    gate = ROOMS["N0"]["gate"]
    gx, gy = gate["at"][0] * TILE + 12, gate["at"][1] * TILE + 8
    for carried in (None, "orbe"):
        g.enter_room("N0")
        g.carried = carried
        g.player.x, g.player.y = gx, gy
        g.update(Input())
        rep.check(g.state == "play", "le vortex accepte %s" % carried)
    g.enter_room("N0")
    g.contact = {}
    g.carried, g.items["sceptre"] = "sceptre", None
    g.score, g.energy, g.time_left = 1000, 20, g.time_total - 50 * 60
    g.player.x, g.player.y = gx, gy
    g.update(Input())
    rep.check(g.state == "chapter" and g.carried is None, "le Sceptre n'ouvre pas le vortex")
    rep.check(g.chapter_bonus > 0 and g.score == 1000 + g.chapter_bonus, "bonus de temps du Ch.1 absent")
    for _ in range(600):
        g.update(Input())
        if g.state != "chapter":
            break
    rep.check(g.state == "play" and g.chapter == 2 and g.room_id == CHAPTER_START[2]["room"],
              "la transition ne démarre pas le Ch.2 (%s, %s)" % (g.state, g.room_id))
    rep.check(g.energy == ENERGY_MAX and g.time_left > g.time_total - 50 and g.score >= 1000,
              "Ch.2 : énergie/temps/score mal initialisés")
    # --chapter 2
    g = Game(chapter=2)
    rep.check(g.chapter == 2 and g.room_id == CHAPTER_START[2]["room"] and len(g.freed) == len(CAPTIVES),
              "--chapter 2 : départ invalide")
    # cœur au contact, sceau refusé avant 8
    h = HEARTS[0]
    it = g.items[h]
    g.enter_room(it["room"])
    g.player.x, g.player.y = it["x"], it["y"] - 6
    g.update(Input())
    rep.check(g.hearts == [h] and g.items[h] is None and g.carried is None, "cœur non ramassé au contact")
    sceau = [d for d, v in DOORS.items() if v.get("need_hearts")][0]
    side = door_sides(sceau)[0]
    g.enter_room(side[0])
    cx, cy = opening_cells(side[1])[1]
    g.player.x, g.player.y = cx * TILE, cy * TILE + 10
    for _ in range(20):
        g.update(Input(up=True))
    rep.check(sceau not in g.doors_open and g.room_id == side[0], "le sceau s'ouvre avec 1 cœur")
    for oid in HEARTS[1:]:
        g.items[oid] = None
        g.hearts.append(oid)
    for _ in range(20):
        g.update(Input(up=True))
    rep.check(sceau in g.doors_open, "le sceau ne s'ouvre pas avec 8 cœurs")
    # creuset : rejet d'un mauvais objet, un seul ingrédient ne suffit pas
    cid, c = list(CRAFTS.items())[0]
    g = Game(chapter=2)
    g.enter_room(c["room"])
    g.grace = 1000
    pos = (c["at"][0] * TILE + 4, c["at"][1] * TILE - 10)
    g.carried, g.items["faux"] = "faux", None
    g.player.x, g.player.y = pos
    g.update(Input())
    rep.check(g.carried == "faux" and not g.craft_in[cid], "le creuset accepte un mauvais objet")
    g.carried, g.items[c["needs"][0]] = c["needs"][0], None
    g.update(Input())
    rep.check(g.carried is None and g.craft_in[cid] == [c["needs"][0]] and c["makes"] not in g.crafted,
              "dépôt du 1er ingrédient invalide")
    g.player.y -= 40
    g.update(Input())
    g.carried, g.items[c["needs"][1]] = c["needs"][1], None
    g.player.x, g.player.y = pos
    g.update(Input())
    rep.check(c["makes"] in g.crafted and g.items[c["makes"]] is not None, "le creuset ne forge rien")
    # boss : objet quelconque sans effet ; pentacle consommé ; PV conservés en sortant
    g = Game(chapter=2)
    br = solver.boss_room()
    g.enter_room(br)
    g.grace = 0
    b = g.boss
    for _ in range(200):
        if b.solid:
            break
        g.update(Input())
    g.carried, g.items["faux"] = "faux", None
    g.player.x, g.player.y = b.x + 2, b.y + 2
    g.update(Input())
    rep.check(b.hp == BOSS_HITS and g.carried == "faux", "le boss est blessé par un objet quelconque")
    pent = [o for o, d in OBJECTS.items() if d["kind"] == BOSS_WEAPON_KIND][0]
    g.carried, g.items[pent] = pent, None
    b.invuln = 0
    g.player.x, g.player.y = b.x + 2, b.y + 2
    g.update(Input())
    rep.check(g.boss_hp == BOSS_HITS - 1 and g.carried is None, "un pentacle ne blesse pas / n'est pas consommé")
    g.enter_room(ROOMS[br]["exits"]["S"])
    g.enter_room(br)
    rep.check(g.boss.hp == BOSS_HITS - 1, "le Nécromancien regagne ses PV en sortant")
    # salle de lave : plus douloureuse que l'eau
    g = Game(chapter=2)
    lava = [rid for rid, r in ROOMS.items() if r["lava"]][0]
    g.enter_room(lava)
    g.grace = 1000
    g.enemies = []
    g.player.x, g.player.y = 7.0 * TILE, (ROWS - 2) * TILE - 16.0
    e0 = g.energy
    for _ in range(10):
        g.update(Input())
    rep.check(g.energy < e0 - 5, "la lave ne fait pas mal (%s)" % lava)


def check_music(rep):
    import music
    from audio import Audio
    for e in music.check_scores():
        rep.check(False, "musique : " + e)
    n = 0
    for key, (text, chords) in music.SCORES.items():
        bars = music.parse_bars(text)
        n += len(bars)
        rep.check(all(sum(d for _, d in b) == music.BAR_EIGHTHS for b in bars), "musique : %s pas en 3/8" % key)
    title = music.build_title()
    st = music.stats(title)
    rep.check(25.0 <= st["duration"] <= 45.0, "musique : durée du titre %.1f s" % st["duration"])
    rep.check(st["peak"] < 1.0, "musique : saturation (crête %.2f)" % st["peak"])
    rep.check(st["rms"] > 0.02, "musique : thème silencieux")
    a = Audio()
    rep.check(not a.ok or {"title", "over", "ingame", "ingame2"} <= set(a.tracks) | set(a.overrides),
              "musique : pistes manquantes")
    a.play_music("title")
    on = a.toggle_music()
    rep.check(not on and not a.music_on, "musique : F3 ne coupe pas")
    a.toggle_music()
    rep.check(not a.ok or a.music_on, "musique : F3 ne relance pas")
    a.music_stop()
    muted = Audio(enabled=False)
    muted.play_music("title")
    rep.check(not muted.music_on, "musique : --mute ne coupe pas")
    print("[audio] mixer=%s, %d effets, %d mesures de partition, titre %.1f s (crête %.2f)"
          % (a.ok, len(a.sounds), n, st["duration"], st["peak"]))


def run():
    t0 = time.time()
    import pygame
    pygame.init()
    pygame.display.set_mode((960, 600))
    from game import Game
    rep = Report()
    print("== Sorcery selftest : mode Classique CPC 1985 ==")
    selftest_classic.run(rep)
    print("== Sorcery selftest : mode Sorcery+ (--plus) ==")
    check_data(rep)
    print("[données] %d salles (Ch.1 %d + Ch.2 %d), %d objets, %d portes, %d captifs, %d cœurs" % (
        len(ROOMS), sum(room_chapter(r) == 1 for r in ROOMS), sum(room_chapter(r) == 2 for r in ROOMS),
        len(OBJECTS), len(DOORS), len(CAPTIVES), len(HEARTS)))
    g = Game()
    check_rooms(rep, g)
    print("[salles] toutes chargées, accessibilité intra-salle vérifiée")
    win, plan, rooms = solver.solve()
    rep.check(win, "BFS : le jeu n'est pas gagnable")
    rep.check(len(rooms) == len(ROOMS), "BFS : salles jamais atteintes : %s" % sorted(set(ROOMS) - rooms))
    kinds = [st[0] for st in plan]
    for oid, o in OBJECTS.items():
        rep.check(o["room"] in rooms, "BFS : objet %s inatteignable" % oid)
    rep.check(sorted(st[1] for st in plan if st[0] == "heart") == sorted(HEARTS), "BFS : cœurs non tous ramassés")
    rep.check(sorted(st[1] for st in plan if st[0] == "craft") == sorted(CRAFTS), "BFS : fabrication non résolue")
    rep.check(kinds.count("gate") == 1 and kinds[-1] == "boss", "BFS : ordre des chapitres invalide")
    gi = kinds.index("gate") if "gate" in kinds else 0
    rep.check(all(k in ("open", "free") for k in kinds[:gi]) and "free" not in kinds[gi:],
              "BFS : le Ch.1 n'est pas terminé avant le vortex")
    print("[BFS] gagnable=%s, %d étapes (Ch.1 %d, Ch.2 %d), %d/%d salles atteignables" % (
        win, len(plan), gi + 1, len(plan) - gi - 1, len(rooms), len(ROOMS)))
    check_mechanics(rep)
    check_chapter2(rep)
    check_game_over(rep)
    print("[mécanique] Ch.1 et Ch.2 (vortex, transition, cœurs, sceau, creuset, boss 3 pentacles, lave)")
    n, visited = simulate_scripted(rep, 600)
    print("[simulation] %d frames scriptées sans plantage, salles visitées : %s" % (n, ",".join(sorted(visited))))
    n, visited = simulate_scripted(rep, 600, chapter=2)
    print("[simulation Ch.2] %d frames scriptées, salles visitées : %s" % (n, ",".join(sorted(visited))))
    kinds = simulate_enemies(rep)
    print("[ennemis] %d salles x 400 ticks, types : %s" % (len(ROOMS), ",".join(sorted(kinds))))
    g = playthrough(rep)
    print("[partie complète] état=%s, libérés=%d, cœurs=%d, PV boss %s, score=%d" % (
        g.state, len(g.freed), len(g.hearts), g.log["hp"], g.score))
    check_music(rep)
    print("%d vérifications OK, %d erreurs (%.1fs)" % (rep.passed, len(rep.errors), time.time() - t0))
    for e in rep.errors:
        print("  ERREUR:", e)
    return 1 if rep.errors else 0


# ------------------------------------------------------------------ captures
def screenshots(outdir):
    import pygame
    pygame.init()
    pygame.display.set_mode((960, 600))
    from game import Game, Input
    from render import Renderer
    os.makedirs(outdir, exist_ok=True)
    selftest_classic.screenshots(outdir)
    r = Renderer()

    def save(name):
        pygame.image.save(r.compose(), os.path.join(outdir, name))

    r.draw_title(120, 12500)
    save("01_titre.png")
    g = Game()
    for _ in range(60):
        g.update(Input(right=True, up=True))
    r.draw_game(g)
    save("02_tour_depart.png")

    def shot(name, rid, x, y, carried=None, ticks=40, setup=None, chapter=1):
        g = Game(chapter=chapter)
        g.enter_room(rid)
        g.player.x, g.player.y = x, y
        if carried:
            g.carried = carried
            g.items[carried] = None
        if setup:
            setup(g)
        for _ in range(ticks):
            g.update(Input(up=True) if _ % 3 == 0 else Input())
        r.draw_game(g)
        save(name)
        return g

    shot("03_bois.png", "B5", 60, 90, "amulette")
    shot("04_riviere.png", "R2", 30, 50, "harpe")
    shot("05_chateau.png", "C1", 90, 40, "hache")
    shot("06_catacombes_sombres.png", "K2", 60, 50)
    shot("07_palais.png", "P2", 30, 80, "couronne")
    shot("08_stonehenge.png", "S1", 60, 40, "sceptre")
    shot("09_vortex.png", "N0", 30, 70, "sceptre", ticks=60,
         setup=lambda g: (setattr(g, "freed", list(CAPTIVES)), g.doors_open.add("portail")))
    g = Game()
    g.state, g.lost_reason, g.score = "lost", "LE TEMPS EST ECOULE", 4300
    g.freed = list(CAPTIVES)[:5]
    r.draw_gameover(g, 30)
    save("10_game_over.png")
    g = Game()
    g.freed = list(CAPTIVES)
    g.time_bonus, g.score = 8450, 18750
    r.draw_victory(g, 30)
    save("11_victoire.png")
    # ---- Chapitre 2
    g = Game()
    g.freed = list(CAPTIVES)
    g.score, g.chapter_bonus, g.next_chapter, g.state = 23950, 9870, 2, "chapter"
    r.draw_chapter(g, 70)
    save("12_chapitre2.png")

    def hearts(n):
        def f(g):
            for oid in HEARTS[:n]:
                g.items[oid] = None
                g.hearts.append(oid)
        return f
    shot("13_foret_maudite.png", "F3", 100, 60, "faux", chapter=2, setup=hearts(1))
    shot("14_chapelle.png", "A5", 60, 60, "eau_benite", chapter=2, setup=hearts(3))

    def forge(g):
        hearts(5)(g)
        g.craft_in["creuset"].append("cloche")
        g.items["cloche"] = None
    shot("15_forge_lave.png", "V5", 60, 100, "eclat", chapter=2, setup=forge)
    shot("16_crypte.png", "X7", 50, 50, "cierge", chapter=2, setup=hearts(6))

    def lair(g):
        hearts(8)(g)
        g.doors_open.add("sceau")
        g.boss_hp = 2
        for oid in ("pentacle_1", "pentacle_2"):
            g.items[oid] = None
        g.items["pentacle_3"] = dict(room="N1", x=40.0, y=86.0, vy=0.0)
    shot("17_sanctuaire.png", "N1", 120, 120, "pentacle_2", ticks=90, chapter=2, setup=lair)
    print("captures écrites dans", outdir)


if __name__ == "__main__":
    sys.exit(run())
