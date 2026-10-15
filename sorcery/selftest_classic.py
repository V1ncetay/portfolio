"""Tests headless du mode « Classique CPC 1985 » (appelés par selftest.run()).

Vérifie : constantes = valeurs de docs/ANALYSE_DSK.md, 40 salles, graphe de portes, verrous,
solvabilité par le solveur depuis les 5 départs dans le temps du sablier (et rejeu du plan
dans le vrai moteur), noyade, chaudrons, armes dédiées, sorts, pause, simulation par salle.
"""
import random

import config as C
import classic_world as W
import classic_sprites as CS
import solver
from classic_game import ClassicGame, LOST_DROWN, LOST_TIME, LOST_ENERGY

CW_, CH_ = C.CL_CELL_W, C.CL_CELL_H


class Inp:
    def __init__(self, left=False, right=False, up=False, down=False, action=False):
        self.left, self.right, self.up, self.down, self.action = left, right, up, down, action


def check_constants(rep):
    """Chaque constante doit valoir ce que prouve le binaire (§7, §8, §10, §11, §12)."""
    expect = dict(
        CL_FRAME_HZ=37.5, CL_CELL_W=4, CL_CELL_H=8, CL_COLS=40, CL_ROWS=18, CL_PLAY_W=160,
        CL_PLAY_H=144, CL_HUD_Y=144, CL_ROOMS=40, CL_CAPTIVES=8, CL_SPRITE_W=12, CL_SPRITE_H=24,
        CL_X_MAX=148, CL_Y_MAX=120, CL_SPEED_X=2, CL_SPEED_UP=2, CL_SPEED_FALL=2, CL_ENERGY_MAX=99,
        CL_DMG_T1=75, CL_DMG_T2=60, CL_DMG_T3=50, CL_DMG_FIRE=50, CL_CAULDRON_GOOD=1,
        CL_CAULDRON_BAD=2, CL_CONTACT_DY=18, CL_CONTACT_DX=9, CL_CAPTIVE_DY=22, CL_CAPTIVE_DX=10,
        CL_CAULDRON_DX=4, CL_SPELL_DY=4, CL_SPELL_DX=2, CL_SCORE_ROOM=500, CL_SCORE_PICKUP=250,
        CL_SCORE_KILL=1000, CL_SCORE_SPELL=500, CL_SCORE_FREE=2000, CL_SCORE_TIME_PER_S=0,
        CL_HUD_BG=(0, 0, 128))
    for k, v in expect.items():
        rep.check(getattr(C, k, None) == v, "constante %s = %r (binaire : %r)" % (k, getattr(C, k, None), v))
    rep.check(abs(C.CL_TIME_S - 921.6) < 1e-9 and C.CL_TIME_VBL == 640 * 72, "sablier != 921,6 s (640 x 72 VBL)")
    rep.check(C.CL_TIME_FRAMES == 34560, "sablier : %d trames à 37,5 Hz" % C.CL_TIME_FRAMES)
    rep.check(C.CL_ENEMY_SPEED == {1: (1, 1), 2: (1, 0), 3: (2, 1)}, "vitesses d'ennemis")
    rep.check(C.CL_PALETTE[1] == (255, 255, 0) and C.CL_PALETTE[12] == (255, 255, 128) and len(C.CL_PALETTE) == 16,
              "palette de jeu")
    rep.check(W.WEAPON == {1: "boulet", 2: "epee", 3: "hache"} and W.LOCK_ITEM == {1: "blason", 2: "lys"},
              "armes / objets-clés")
    rep.check(len(W.SPELLS["etoile"]) == 8 and len(W.SPELLS["sac"]) == 4, "sorts : 8 et 4 projectiles")
    rep.check(all(abs(dy) in (0, 4) and abs(dx) in (0, 2) for v in W.SPELLS.values() for dy, dx in v),
              "projectiles : 4 lignes / 2 px par trame")
    rep.check(len(W.ITEMS) == 17, "17 types d'objets")


def check_world(rep):
    rooms = W.ROOMS
    rep.check(sorted(rooms) == list(range(40)), "il faut exactement 40 salles numérotées 0..39")
    rep.check(len(W.CAPTIVE_ROOMS) == 8, "8 captifs (%d)" % len(W.CAPTIVE_ROOMS))
    rep.check(len(W.CAULDRON_ROOMS) == 9, "9 chaudrons (%d)" % len(W.CAULDRON_ROOMS))
    rep.check(len(W.STARTS) == 5 and len(W.POISON) == 5, "5 départs et 5 paires de chaudrons nocifs")
    for pair in W.POISON:
        rep.check(len(set(pair)) == 2 and all(r in W.CAULDRON_ROOMS for r in pair), "paire nocive %s" % (pair,))
    rep.check(len(set(map(frozenset, W.POISON))) == 5, "paires nocives non distinctes")
    used = {}
    for a, sa, b, sb, lock in W.LINKS:
        for r, s in ((a, sa), (b, sb)):
            rep.check(s in rooms[r]["doors"], "lien vers une porte inexistante %d.%s" % (r, s))
            used[(r, s)] = used.get((r, s), 0) + 1
        rep.check(lock in (None, 1, 2), "verrou invalide")
    for r, d in rooms.items():
        for s in d["doors"]:
            rep.check(used.get((r, s)) == 1, "porte %d.%s utilisée %s fois" % (r, s, used.get((r, s))))
        rep.check(sum(1 for s in d["doors"] if s[0] == "L") <= 2 and sum(1 for s in d["doors"] if s[0] == "R") <= 2,
                  "salle %d : plus de 2 portes d'un côté" % r)
        rep.check(len(d["items"]) <= 2 and len(d["enemies"]) <= 2, "salle %d : > 2 objets ou ennemis" % r)
        rep.check(all(t in (1, 2, 3) for t, _x, _y in d["enemies"]), "salle %d : type d'ennemi" % r)
    locks = [l for *_x, l in W.LINKS if l]
    rep.check(locks.count(1) == 4 and locks.count(2) == 4, "8 sens verrouillés : 4 blason + 4 lys (%s)" % locks)
    rep.check(len(rooms[W.SANCTUARY]["doors"]) == 1 and rooms[W.SANCTUARY]["goal"], "sanctuaire : 1 porte + autel")
    # graphe connexe (non orienté) et fortement connexe sans emprunter aucun sens verrouillé
    adj, free = {r: set() for r in rooms}, {r: set() for r in rooms}
    for (r, s), (d, ds, lock) in W.DOOR_TO.items():
        adj[r].add(d)
        if not lock:
            free[r].add(d)

    def reach(g, src):
        seen, st = {src}, [src]
        while st:
            for n in g[st.pop()]:
                if n not in seen:
                    seen.add(n)
                    st.append(n)
        return seen
    rep.check(len(reach(adj, 0)) == 40, "graphe des portes non connexe")
    rep.check(all(len(reach(free, r)) == 40 for r in rooms),
              "graphe des sens libres non fortement connexe (un verrou isolerait une zone)")
    # cages : une barrière par captif, objets de cage uniques ; 17 types posés dans le monde
    cage_items = [W.cage_barrier(r)[5] for r in W.CAPTIVE_ROOMS]
    rep.check(len(set(cage_items)) == 8, "objets de cage non uniques : %s" % cage_items)
    kinds = {k for _r, k, _x, _y in W.item_instances()}
    rep.check(kinds == set(W.ITEMS), "types jamais posés : %s" % (set(W.ITEMS) - kinds))
    for b in W.BARRIERS:
        rep.check(b[5] in kinds, "barrière %s : objet %s absent du monde" % (b[0], b[5]))
    # géométrie : portes, objets, captifs, chaudrons, départs, ennemis dans des cases libres
    for r, d in rooms.items():
        t = W.build_tiles(r)
        blocks = W.solid_blocks(r)

        def free3(x, y, extra=()):
            return all(0 <= x + i < 40 and 0 <= y + j < 18 and t[y + j][x + i] not in W.BLOCKING
                       and (x + i, y + j) not in extra for i in range(3) for j in range(3))
        for s, (x, y) in d["doors"].items():
            rep.check(free3(x, y), "salle %d : porte %s dans un mur" % (r, s))
            ax, ay = W.arrival_cell(r, s)
            rep.check(free3(ax, ay, blocks), "salle %d : arrivée de la porte %s bloquée" % (r, s))
            rep.check(ay + 3 == 18 or t[ay + 3][ax] in W.BLOCKING or t[ay + 3][ax + 2] in W.BLOCKING,
                      "salle %d : porte %s ne repose sur rien" % (r, s))
        for k, x, y in d["items"]:
            rep.check(free3(x, y, blocks), "salle %d : objet %s dans un mur" % (r, k))
        if d["captive"]:
            rep.check(free3(*d["captive"], blocks), "salle %d : captif dans un mur" % r)
        if d["cauldron"]:
            x, y = d["cauldron"]
            rep.check(free3(x, y), "salle %d : chaudron dans un mur" % r)
        for _t, x, y in d["enemies"]:
            rep.check(0 <= x <= 37 and 0 <= y <= 15, "salle %d : ennemi hors écran" % r)
    for rid, x, y in W.STARTS:
        t = W.build_tiles(rid)
        rep.check(all(t[y + j][x + i] not in W.BLOCKING for i in range(3) for j in range(3)), "départ %d bloqué" % rid)
    # sprites 12 x 24
    for name in ("WIZ_STAND", "DOOR", "GRILLE", "TRAPPE", "CAULDRON"):
        a = getattr(CS, name)
        rep.check(len(a) == 24 and {len(r) for r in a} == {12}, "sprite %s pas en 12x24" % name)
    for name in ("WIZ_WALK", "WIZ_FLY", "CAPTIVE", "CHASER", "WALKER", "SPECTRE"):
        for a in getattr(CS, name):
            rep.check(len(a) == 24 and {len(r) for r in a} == {12}, "sprite %s pas en 12x24" % name)


def check_solver(rep):
    """Preuve de terminabilité depuis les 5 départs, dans le temps du sablier."""
    results = []
    for st in range(len(W.STARTS)):
        win, plan, frames, s = solver.solve_classic(st)
        rep.check(win, "départ %d : partie non terminable" % st)
        rep.check(frames < C.CL_TIME_FRAMES, "départ %d : %d trames > sablier" % (st, frames))
        rep.check(len(s.freed) == 8 and plan and plan[-1][0] == "goal", "départ %d : plan incomplet" % st)
        # chaque porte verrouillée a son objet-clé atteignable (état final du plan)
        for (r, slot), (d, ds, lock) in W.DOOR_TO.items():
            if not lock:
                continue
            kind = W.LOCK_ITEM[lock]
            d0 = s.dijkstra({s.cur: (0, ())}, None)
            dl = s.dijkstra(s._pick_sources(d0, kind), kind)
            node = (r, s.rooms[r].door_pt[slot])
            rep.check(node in dl, "départ %d : verrou %d.%s -> %d sans %s atteignable" % (st, r, slot, d, kind))
        results.append((st, win, len(plan), frames, s.expanded))
        replay(rep, st, plan)
    return results


def replay(rep, start, plan):
    """Rejoue le plan du solveur dans le vrai moteur (téléportation entre étapes ; ramassages,
    échanges, ouvertures de barrières, libérations et victoire sont réels)."""
    g = ClassicGame(start=start)
    for step in plan:
        kind, what, item, info = step
        g.energy = C.CL_ENERGY_MAX
        if kind == "take":
            rid, i = info
            x, y = W.ROOMS[rid]["items"][i][1:]
            g.place(rid, x, y)
            for e in g.enemies:
                e.alive = False
            before = g.carried
            g.update(Inp(action=True))
            ok = g.carried is not None and g.carried["kind"] == item and g.carried is not before
            rep.check(ok, "rejeu %d : ramassage de %s en salle %d" % (start, item, rid))
        elif kind == "open":
            b = W.BARRIER_BY_ID[what]
            _bid, rid, d, bx, by, need = b
            g.place(rid, bx, by)
            grid = g.grid
            cands = ([((bx - 3, by), False), ((bx + 3, by), False)] if d == "V"
                     else [((bx, by - 3), False), ((bx, by + 3), True)])
            for (cx, cy), up in cands:
                if all(0 <= cx + i < 40 and 0 <= cy + j < 18 and grid[cy + j][cx + i] not in W.BLOCKING
                       for i in range(3) for j in range(3)):
                    break
            g.place(rid, cx, cy)
            for e in g.enemies:
                e.alive = False
            rep.check(g.carried_kind == need, "rejeu %d : %s n'est pas porté" % (start, need))
            g.update(Inp(up=up))
            rep.check(what in g.open_barriers and g.carried is None,
                      "rejeu %d : barrière %s pas ouverte / objet non consommé" % (start, what))
        elif kind == "free":
            g.place(what, *W.ROOMS[what]["captive"])
            g.update(Inp())
            rep.check(what in g.freed, "rejeu %d : captif %d pas libéré" % (start, what))
        else:
            gx, gy = W.ROOMS[what]["goal"]
            g.place(what, gx, gy)
            score = g.score
            g.update(Inp())
            rep.check(g.state == "won", "rejeu %d : pas de victoire au sanctuaire (%s)" % (start, g.state))
            rep.check(g.score == score, "rejeu %d : bonus de fin inattendu" % start)
    rep.check(len(g.freed) == 8, "rejeu %d : %d libérés" % (start, len(g.freed)))
    return g


def _game(rid, cx, cy, start=0, clear=True):
    g = ClassicGame(start=start)
    g.place(rid, cx, cy)
    if clear:
        for e in g.enemies:
            e.alive = False
    return g


def check_mechanics(rep):
    # aucune commande « bas » : chute à vitesse constante identique
    a, b = _game(0, 32, 0), _game(0, 32, 0)
    for _ in range(5):
        a.update(Inp(down=True))
        b.update(Inp())
    rep.check(a.player.y == b.player.y == 10, "« bas » a un effet ou chute != 2 lignes/trame")
    g = _game(0, 30, 2)
    y0 = g.player.y
    g.update(Inp(up=True))
    rep.check(g.player.y == y0 - 2, "montée != 2 lignes/trame")
    x0 = g.player.x
    g.update(Inp(right=True, up=True))
    rep.check(g.player.x == x0 + 2, "horizontal != 2 px/trame")
    # bords d'écran = murs (aucun flip-screen)
    g = _game(0, 3, 1)
    for _ in range(30):
        g.update(Inp(left=True, up=True))
    rep.check(g.room_id == 0 and g.player.x == 0 and g.player.y == 0, "le bord gauche/haut n'est pas un mur")
    # porte libre : pousser contre elle mène à la salle reliée, collé à la porte d'arrivée
    ax, ay = W.arrival_cell(0, "R1")
    g = _game(0, ax, ay)
    g.update(Inp(right=True))
    dest, dslot, _ = W.DOOR_TO[(0, "R1")]
    rep.check(g.room_id == dest and (g.player.x, g.player.y) == tuple(v * k for v, k in zip(
        W.arrival_cell(dest, dslot), (CW_, CH_))), "passage de porte 0.R1 incorrect")
    # même Y exigé
    g = _game(0, ax, ay - 1)
    g.update(Inp(right=True, up=True))
    rep.check(g.room_id == 0, "porte franchie sans être au même Y")
    # verrou : refus sans l'objet, passage avec (non consommé), retour libre
    locked = [(k, v) for k, v in W.DOOR_TO.items() if v[2]]
    for (r, slot), (d, ds, lock) in locked:
        ax, ay = W.arrival_cell(r, slot)
        push = Inp(left=slot[0] == "L", right=slot[0] == "R")
        g = _game(r, ax, ay)
        g.update(push)
        rep.check(g.room_id == r, "verrou %d.%s franchi sans objet" % (r, slot))
        g = _game(r, ax, ay)
        it = next(i for i in g.items if i["kind"] == W.LOCK_ITEM[lock])
        it["room"], g.carried = None, it
        g.update(push)
        rep.check(g.room_id == d and g.carried is it, "verrou %d.%s : refus avec l'objet ou objet consommé" % (r, slot))
        bx, by = W.arrival_cell(d, ds)
        g = _game(d, bx, by)
        g.update(Inp(left=ds[0] == "L", right=ds[0] == "R"))
        rep.check(g.room_id == r, "retour %d.%s -> %d bloqué (le verrou ne vaut que dans un sens)" % (d, ds, r))
    # noyade immédiate en se posant sur l'eau
    g = _game(36, 8, 8)
    for _ in range(40):
        g.update(Inp())
    rep.check(g.state in ("drowning", "lost") and g.lost_reason == LOST_DROWN, "pas de noyade sur l'eau (%s)" % g.state)
    e0 = g.energy
    for _ in range(80):
        g.update(Inp())
    rep.check(g.state == "lost" and g.energy == e0, "noyade : fin de partie / énergie modifiée")
    # survoler l'eau sans s'y poser ne tue pas
    g = _game(36, 8, 8)
    for i in range(60):
        g.update(Inp(up=i % 2 == 0))
    rep.check(g.state == "play", "survol de l'eau mortel")
    # case de feu : 50/256 par trame
    g = _game(8, 18, 14)
    for _ in range(256):
        g.update(Inp())
    rep.check(g.energy == 99 - 50, "feu : %d d'énergie après 256 trames (attendu 49)" % g.energy)
    # contact ennemi : 75 / 60 / 50 par trame, /256
    for t, dmg in ((1, 75), (2, 60), (3, 50)):
        rid = next(r for r, d in W.ROOMS.items() if any(e[0] == t for e in d["enemies"]))
        g = _game(rid, 18, 0, clear=False)
        for e in g.enemies:
            e.alive = e.type == t
        e = next(e for e in g.enemies if e.alive)
        n = 0
        for _ in range(128):
            e.x, e.y = g.player.x + 8, g.player.y + 17
            g.update(Inp(up=True))
            n += 1
        # accumulateur /256 parti de 0 : la 1re trame retire déjà 1 point
        rep.check(g.energy == 99 + (-n * dmg) // 256, "T%d : énergie %d après %d trames de contact" % (t, g.energy, n))
    # chaudrons : les 2 nocifs dépendent du départ
    for st in range(5):
        for rid in W.CAULDRON_ROOMS:
            cx, cy = W.ROOMS[rid]["cauldron"]
            g = _game(rid, cx, cy - 2, start=st)
            g.energy = 50
            for _ in range(10):
                g.update(Inp())
            want = 30 if rid in W.POISON[st] else 60
            rep.check(g.energy == want, "départ %d chaudron %d : énergie %d (attendu %d)" % (st, rid, g.energy, want))
    # armes dédiées : seule la bonne arme tue, et elle est consommée
    for t in (1, 2, 3):
        rid = next(r for r, d in W.ROOMS.items() if any(e[0] == t for e in d["enemies"]))
        for weapon in ("boulet", "epee", "hache", "cle"):
            g = _game(rid, 18, 2, clear=False)
            for it in g.items_here():
                it["room"] = -1                       # aucun objet à portée d'échange
            e = next(e for e in g.enemies if e.type == t)
            for o in g.enemies:
                o.alive = o is e
            inst = next(i for i in g.items if i["kind"] == weapon)
            inst["room"], g.carried = None, inst
            e.x, e.y = g.player.x + 4, g.player.y
            score = g.score
            g.update(Inp(action=True, up=True))
            right = weapon == W.WEAPON[t]
            rep.check((not e.alive) == right, "T%d %s par %s" % (t, "survit" if right else "tué", weapon))
            rep.check((g.carried is None) == right, "T%d : arme %s consommée à tort / pas consommée" % (t, weapon))
            rep.check(g.score - score == (C.CL_SCORE_KILL if right else 0), "T%d : score de mise à mort" % t)
    # sorts : l'étoile filante tue tous les types (+500)
    g = _game(13, 18, 8, clear=False)
    for it in g.items_here():
        it["room"] = -1
    inst = next(i for i in g.items if i["kind"] == "etoile")
    inst["room"], g.carried = None, inst
    px, py = g.player.x, g.player.y
    g.enemies[:] = []
    from classic_game import Enemy
    for t, (ex, ey) in zip((1, 2, 3), ((px + 50, py), (px - 50, py), (px, py + 60))):
        g.enemies.append(Enemy(t, max(0, ex), min(120, ey)))
    for en in g.enemies:
        en.turn = 999                              # immobiles
    score = g.score
    g.update(Inp(action=True, up=True))
    rep.check(g.carried is None and len(g.spells) == 8, "étoile filante : pas 8 projectiles / non consommée")
    for _ in range(40):
        for en in g.enemies:
            en.x, en.y = (en.x, en.y)
        g.update(Inp(up=True))
    rep.check(sum(not en.alive for en in g.enemies) >= 2 and g.score - score >= 2 * C.CL_SCORE_SPELL,
              "les sorts ne tuent pas")
    # bouton feu : pas de pose dans le vide ; échange avec un objet à portée ; +250 une fois
    g = _game(0, 30, 2)
    inst = next(i for i in g.items if i["kind"] == "fiole")
    inst["room"], inst["taken"], g.carried = None, True, inst
    g.update(Inp(action=True, up=True))
    rep.check(g.carried is inst, "objet posé dans le vide")
    it = next(i for i in g.items_here() if i["kind"] == "cle")
    g.place(0, it["x"] // CW_, it["y"] // CH_)
    for e in g.enemies:
        e.alive = False
    s0 = g.score
    g.update(Inp(action=True))
    rep.check(g.carried is it and inst["room"] == 0 and (inst["x"], inst["y"]) == (it["x"], it["y"]),
              "échange incorrect")
    rep.check(g.score - s0 == C.CL_SCORE_PICKUP, "premier ramassage != +250")
    g.update(Inp(action=True))
    g.update(Inp(action=True))
    rep.check(g.score - s0 == C.CL_SCORE_PICKUP, "ramassage compté deux fois")
    # barrière : mauvais objet sans effet, bon objet consommé
    b = W.BARRIER_BY_ID["24.0"]
    g = _game(24, b[3] - 3, b[4])
    wrong = next(i for i in g.items if i["kind"] == "fiole")
    wrong["room"], g.carried = None, wrong
    g.update(Inp())
    rep.check(b[0] not in g.open_barriers and g.carried is wrong, "barrière ouverte par un mauvais objet")
    good = next(i for i in g.items if i["kind"] == b[5])
    good["room"], g.carried = None, good
    g.update(Inp())
    rep.check(b[0] in g.open_barriers and g.carried is None and not g.blocked(b[3] * CW_, b[4] * CH_),
              "barrière non ouverte / objet non consommé / cases non libérées")
    # première visite +500, une seule fois
    g = _game(0, 30, 2)
    s0 = g.score
    g.enter_room(1)
    g.enter_room(0)
    g.enter_room(1)
    rep.check(g.score - s0 == C.CL_SCORE_ROOM, "points de première visite")
    # victoire refusée tant que les 8 ne sont pas libres
    gx, gy = W.ROOMS[W.SANCTUARY]["goal"]
    g = _game(W.SANCTUARY, gx, gy)
    g.update(Inp())
    rep.check(g.state == "play", "victoire sans les 8 sorciers")
    g.freed = list(W.CAPTIVE_ROOMS)
    g.update(Inp())
    rep.check(g.state == "won" and g.time_bonus == 0, "victoire au sanctuaire")
    # sablier vide / énergie nulle
    g = ClassicGame(start=0, time_frames=30)
    for _ in range(40):
        g.update(Inp())
    rep.check(g.state == "lost" and g.lost_reason == LOST_TIME, "fin par sablier vide")
    g = _game(0, 30, 2)
    g.energy = 0
    for _ in range(80):
        g.update(Inp())
    rep.check(g.state == "lost" and g.lost_reason == LOST_ENERGY, "fin par énergie nulle")
    # 5 départs tirés au sort
    seen = {ClassicGame(seed=s).start_index for s in range(60)}
    rep.check(seen == set(range(5)), "les 5 départs ne sont pas tous tirés (%s)" % seen)


def check_pause(rep):
    """La pause (scène de l'App) gèle le sablier."""
    import sys
    App = getattr(sys.modules.get("__main__"), "App", None)
    if App is None:                      # lancé hors de main.py (python selftest.py)
        from main import App
    app = App(mute=True, headless=True, mode="classic", start=0)
    app.new_game()
    for _ in range(5):
        app.step(Inp(), set())
    t0 = app.game.time_left
    app.step(Inp(), {"esc"})
    rep.check(app.scene == "pause", "ESC ne met pas en pause")
    for _ in range(200):
        app.step(Inp(), set())
        app.draw()
    rep.check(app.game.time_left == t0, "le sablier s'écoule pendant la pause")
    app.step(Inp(), {"action"})
    app.step(Inp(), set())
    rep.check(app.scene == "play" and app.game.time_left == t0 - 1, "reprise après pause")
    rep.check(abs(app.tick_s - 1 / 37.5) < 1e-12, "cadence du mode classique != 37,5 Hz")


def _path(grid, src, dst):
    """Chemin (positions alignées) du modèle du solveur, avec prédécesseurs."""
    import heapq
    valid, block_free = solver._valid_grid(grid)
    if src not in valid or dst not in valid:
        return None
    dist, prev, pq = {src: 0}, {}, [(0, src)]
    while pq:
        d, (x, y) = heapq.heappop(pq)
        if (x, y) == dst:
            break
        if d > dist[(x, y)]:
            continue
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if (dx or dy) and n in valid and block_free(min(x, n[0]), min(y, n[1]),
                                                           max(x, n[0]) + 2, max(y, n[1]) + 2):
                    nd = d + (4 if dy else 2)
                    if nd < dist.get(n, 1e9):
                        dist[n], prev[n] = nd, (x, y)
                        heapq.heappush(pq, (nd, n))
    if dst not in dist:
        return None
    out = [dst]
    while out[-1] != src:
        out.append(prev[out[-1]])
    return out[::-1], dist[dst]


def check_paths(rep):
    """Les chemins du solveur sont jouables au joystick dans le vrai moteur : on suit chaque
    chemin (gauche / droite / haut seulement, chute sinon) entre portes, objets et captif."""
    n_paths = frames_total = cost_total = 0
    for rid, room in sorted(W.ROOMS.items()):
        opened = {b[0] for b in W.BARRIERS if b[1] == rid}
        grid = W.collision_grid(rid, opened)
        pts = [W.arrival_cell(rid, s) for s in sorted(room["doors"])]
        pts += [(x, y) for _k, x, y in room["items"]]
        if room["captive"]:
            pts.append(tuple(room["captive"]))
        src = pts[0]
        for dst in pts[1:]:
            res = _path(grid, src, dst)
            if not rep.check(res is not None, "salle %d : %s inaccessible depuis %s" % (rid, dst, src)):
                continue
            path, cost = res
            g = _game(rid, *src)
            g.open_barriers |= opened
            g._rebuild()
            g.items = []                      # pas d'échange ni de captif pendant le parcours
            frames = 0
            ok = True
            # cases de poussée des portes : y arriver en poussant vers la porte la franchit
            spots = {(W.arrival_cell(rid, s_), s_[0]) for s_ in room["doors"]}
            for i, (cx, cy) in enumerate(path[1:]):
                tx, ty = cx * CW_, cy * CH_
                last = i == len(path) - 2
                for k in range(40):
                    p = g.player
                    if (p.x, p.y) == (tx, ty):
                        break
                    up = p.y > ty or (p.y == ty and not p.landed and k % 2 == 0)
                    left, right = p.x > tx, p.x < tx
                    for (sx, sy), side in spots:
                        nx = p.x + (2 if right else -2 if left else 0)
                        toward = (side == "L" and left) or (side == "R" and right)
                        if toward and nx == sx * CW_ and abs(p.y - sy * CH_) <= 2 and not last:
                            left = right = False      # d'abord le vertical, pour ne pas sortir
                    g.update(Inp(left=left, right=right, up=up))
                    g.energy, g.state = 99, "play"
                    frames += 1
                    if g.room_id != rid:
                        break
                else:
                    ok = False
                if g.room_id != rid:
                    ok = last and (cx, cy) in {sp for sp, _s in spots}   # porte franchie = arrivée
                    break
                if not ok:
                    break
            rep.check(ok, "salle %d : chemin %s -> %s non jouable (bloqué en %d,%d)" % (
                rid, src, dst, g.player.x, g.player.y))
            n_paths += 1
            frames_total += frames
            cost_total += cost
    return n_paths, frames_total, cost_total


def simulate_rooms(rep, frames=400, render=True):
    """Chaque salle : plusieurs centaines de trames d'entrées pseudo-aléatoires, sans exception."""
    from classic_render import ClassicRenderer
    r = ClassicRenderer() if render else None
    rng = random.Random(1985)
    total = 0
    for rid in sorted(W.ROOMS):
        slot = sorted(W.ROOMS[rid]["doors"])[0]
        g = _game(rid, *W.arrival_cell(rid, slot), clear=False)
        hold = Inp()
        for n in range(frames):
            if n % 12 == 0:
                hold = Inp(left=rng.random() < 0.4, right=rng.random() < 0.4, up=rng.random() < 0.5)
            hold.action = rng.random() < 0.03
            g.update(hold)
            total += 1
            if g.state in ("lost", "dying", "drowning"):
                g.state, g.energy = "play", 99
                g.place(rid, *W.arrival_cell(rid, slot))
            p = g.player
            if g.blocked(p.x, p.y):
                rep.check(False, "salle %d : sorcier dans un mur en (%d,%d)" % (rid, p.x, p.y))
                break
            if r and n % 40 == 0:
                r.draw_game(g)
                r.compose()
            for e in g.enemies:
                if not (0 <= e.x <= C.CL_X_MAX and 0 <= e.y <= C.CL_Y_MAX):
                    rep.check(False, "salle %d : ennemi hors écran" % rid)
    return total


def run(rep):
    check_constants(rep)
    check_world(rep)
    print("[classique] constantes = binaire, %d salles, %d liens de porte (%d verrouillés), %d barrières, "
          "%d objets, 9 chaudrons, 8 captifs" % (len(W.ROOMS), len(W.LINKS), sum(1 for l in W.LINKS if l[4]),
                                                 len(W.BARRIERS), len(W.item_instances())))
    solver_results = check_solver(rep)
    for st, win, n, frames, exp in solver_results:
        print("[classique BFS] départ %d (salle %2d) : gagnable=%s, %d étapes, %.0f s estimées / %.1f s, "
              "rejeu moteur OK" % (st, W.STARTS[st][0], win, n, frames / C.CL_FRAME_HZ, C.CL_TIME_S))
    check_mechanics(rep)
    check_pause(rep)
    print("[classique mécanique] pas de « bas », murs, portes/verrous, noyade, feu, chaudrons, armes, sorts, "
          "échange, barrières, score, pause")
    n_paths, fr, cost = check_paths(rep)
    print("[classique chemins] %d chemins du solveur rejoués au joystick : %d trames réelles pour %d estimées"
          % (n_paths, fr, cost))
    n = simulate_rooms(rep)
    print("[classique simulation] %d salles x 400 trames (%d trames) sans exception" % (len(W.ROOMS), n))
    return solver_results


def screenshots(outdir):
    """Captures du mode classique : screenshots/classic_*.png."""
    import os
    import pygame
    from classic_render import ClassicRenderer
    r = ClassicRenderer()

    def save(name):
        pygame.image.save(r.compose(), os.path.join(outdir, "classic_" + name))

    r.draw_title(120, 12500)
    save("01_titre.png")

    def shot(name, rid, cx, cy, carried=None, ticks=30, setup=None, inputs=None, start=0, keep=False):
        g = ClassicGame(start=start, seed=7)
        g.place(rid, cx, cy)
        if carried:
            inst = next(i for i in g.items if i["kind"] == carried and i["room"] != rid)
            inst["room"], g.carried = None, inst
        if setup:
            setup(g)
        for k in range(ticks):
            g.update(inputs(k) if inputs else Inp(up=k % 3 == 0))
            if not keep and g.state != "play":
                g.state = "play"
        r.draw_game(g)
        save(name)
        return g

    g = ClassicGame(start=0, seed=7)
    for k in range(70):
        g.update(Inp(right=k > 30, up=k % 4 != 0))
    r.draw_game(g)
    save("02_village_depart.png")
    shot("03_foret_cage.png", 7, 26, 14, "grimoire", ticks=20, inputs=lambda k: Inp())
    shot("04_cascade.png", 17, 6, 8, "fiole", ticks=24)
    shot("05_fosse_ardente.png", 23, 14, 6, "baguette", ticks=10)
    shot("06_salle_du_trone.png", 28, 4, 3, "couronne", ticks=10)
    shot("07_chapelle_chateau.png", 13, 13, 2, "lyre", ticks=4)

    def opened(*bids):
        def f(g):
            g.open_barriers |= set(bids)
            g._rebuild()
        return f
    shot("08_cachot_trappe.png", 33, 17, 7, None, ticks=4, inputs=lambda k: Inp())
    shot("09_cercle_de_pierres.png", 38, 9, 2, "lune", ticks=20, inputs=lambda k: Inp(up=k % 3 == 0, left=k < 10))

    def all_freed(g):
        g.freed = list(W.CAPTIVE_ROOMS)
    shot("10_sanctuaire.png", W.SANCTUARY, 12, 2, ticks=20, setup=all_freed)

    def spell(g):
        g.enemies[0].x, g.enemies[0].y = 110, 20
        g.update(Inp(action=True, up=True))
    g = shot("11_sort_etoile.png", 22, 18, 3, "etoile", ticks=6, setup=spell)
    g = shot("12_marais.png", 36, 4, 9, "cle", ticks=6)
    r.draw_game(g)
    r.draw_pause()
    save("13_pause.png")
    g = ClassicGame(start=0, seed=7)
    g.place(36, 8, 8)
    for _ in range(140):
        g.update(Inp())
    g.score = 23750
    g.freed = list(W.CAPTIVE_ROOMS)[:5]
    r.draw_gameover(g, 30)
    save("14_game_over_noyade.png")
    g = ClassicGame(start=0, seed=7)
    g.freed = list(W.CAPTIVE_ROOMS)
    g.visited = set(W.ROOMS)
    g.score, g.time_left = 61250, 9000
    g.state = "won"
    r.draw_victory(g, 30)
    save("15_victoire.png")
