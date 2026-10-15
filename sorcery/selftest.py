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
                   OPPOSITE, DELTA, SOLID, WATER, EMPTY, FAKE, build_tiles, door_sides, opening_cells)
import solver  # noqa: E402

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
        rep.check(r["grid"] not in grid, "%s: position de grille dupliquée %s" % (rid, r["grid"]))
        grid[r["grid"]] = rid
    for rid, r in ROOMS.items():
        for d, nxt in r["exits"].items():
            if not rep.check(nxt in ROOMS, "%s: sortie %s -> salle inexistante %s" % (rid, d, nxt)):
                continue
            back = ROOMS[nxt]["exits"].get(OPPOSITE[d])
            rep.check(back == rid, "%s: sortie %s -> %s non réciproque (%s)" % (rid, d, nxt, back))
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
        rep.check(d.get("key") or d.get("need_freed"), "porte %s sans condition d'ouverture" % did)
    items = [c["item"] for c in CAPTIVES.values()]
    rep.check(len(items) == len(set(items)), "objets de libération non uniques")
    door_keys = {d.get("key") for d in DOORS.values()}
    for cid, c in CAPTIVES.items():
        rep.check(c["room"] in ROOMS, "captif %s dans salle inexistante" % cid)
        rep.check(c["item"] in OBJECTS, "captif %s : objet inexistant" % cid)
        rep.check(OBJECTS.get(c["item"], {}).get("kind") == "captif", "captif %s : objet pas de type captif" % cid)
        rep.check(c["item"] not in door_keys, "captif %s : objet aussi clé de porte" % cid)
    rep.check(FINAL_WEAPON in OBJECTS, "arme finale inexistante")
    rep.check(len(CAPTIVES) == 8, "il faut 8 captifs")
    rep.check(25 <= len(ROOMS) <= 47, "nombre de salles hors cible : %d" % len(ROOMS))
    rep.check(sum(1 for r in ROOMS.values() if r["boss"]) == 1, "il faut exactement une salle de boss")


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
    if rid == START["room"]:
        sx, sy = START["at"]
        starts["start"] = [(sx, sy)] if ok(sx, sy) else []
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
            it = game.items[oid]
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
        for e in r["enemies"]:
            kind, x, y = e[:3]
            rep.check(0 <= x < COLS and 0 <= y < ROWS and t[y][x] != SOLID or kind == "fish",
                      "%s: ennemi %s dans un mur" % (rid, kind))


# ------------------------------------------------------------------ simulation
def simulate_scripted(rep, frames=600, render=True):
    from game import Game, Input
    from render import Renderer
    g = Game()
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


def playthrough(rep, render=True):
    """Exécute le plan du solveur dans le vrai moteur (téléportation entre étapes)."""
    from game import Game, Input, ITEM_H
    from render import Renderer
    rend = Renderer() if render else None
    g = Game()
    win, plan, _ = solver.solve()
    idle = Input()

    def frames(n, inp=idle):
        for _ in range(n):
            g.energy = 100          # triche de test : on ne valide que la logique
            g.update(inp)
            if rend and g.tick % 25 == 0:
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
            d = DOORS[what]
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
        else:
            rep.check(fetch(item), "playthrough: impossible de prendre l'arme finale")
            goto(room, 40, 100)
            for _ in range(4000):
                b = g.boss
                if g.state != "play":
                    break
                if b and b.solid and not b.invuln:
                    g.player.x, g.player.y = b.x + 2, b.y + 2
                frames(1)
            frames(200)
    rep.check(g.state == "won", "playthrough: la partie n'est pas gagnée (état %s)" % g.state)
    rep.check(len(g.freed) == len(CAPTIVES), "playthrough: captifs libérés %d" % len(g.freed))
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
    rep.check(not a.ok or {"title", "over", "ingame"} <= set(a.tracks) | set(a.overrides),
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
    print("== Sorcery selftest ==")
    check_data(rep)
    print("[données] %d salles, %d objets, %d portes, %d captifs" % (len(ROOMS), len(OBJECTS), len(DOORS), len(CAPTIVES)))
    g = Game()
    check_rooms(rep, g)
    print("[salles] toutes chargées, accessibilité intra-salle vérifiée")
    win, plan, rooms = solver.solve()
    rep.check(win, "BFS : le jeu n'est pas gagnable")
    rep.check(len(rooms) == len(ROOMS), "BFS : salles jamais atteintes : %s" % sorted(set(ROOMS) - rooms))
    print("[BFS] gagnable=%s, %d étapes, %d/%d salles atteignables" % (win, len(plan), len(rooms), len(ROOMS)))
    check_mechanics(rep)
    check_game_over(rep)
    n, visited = simulate_scripted(rep, 600)
    print("[simulation] %d frames scriptées sans plantage, salles visitées : %s" % (n, ",".join(sorted(visited))))
    g = playthrough(rep)
    print("[partie complète] état=%s, libérés=%d, score=%d" % (g.state, len(g.freed), g.score))
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

    def shot(name, rid, x, y, carried=None, ticks=40, setup=None):
        g = Game()
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
    shot("09_necromancien.png", "N0", 70, 120, "sceptre", ticks=90)
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
    print("captures écrites dans", outdir)


if __name__ == "__main__":
    sys.exit(run())
