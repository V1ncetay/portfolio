"""Solveur logique : BFS sur le graphe des salles + dépendances portes/objets/captifs/cœurs,
pour les deux chapitres.

Hypothèses (conformes au moteur) : portes non consommées et restant ouvertes, objets de
libération consommés (un par captif), ingrédients consommés par la station de fabrication
qui fait alors apparaître l'objet fabriqué, Sceptre consommé par le vortex (passage au
Chapitre 2, sans retour), un pentacle consommé par coup porté au Nécromancien. Un seul objet
porté à la fois : sans conséquence, on peut toujours revenir chercher un objet (les objets
posés restent dans leur salle et les cœurs se ramassent au contact).
"""
from collections import deque

from world import (ROOMS, OBJECTS, DOORS, CAPTIVES, START, HEARTS, CRAFTS, CHAPTER_START,
                   BOSS_HITS, BOSS_WEAPON_KIND, door_for_exit)


def reachable_rooms(opened, start=None):
    start = start or START["room"]
    seen = {start}
    q = deque([start])
    while q:
        rid = q.popleft()
        for direction, nxt in ROOMS[rid]["exits"].items():
            did = door_for_exit(rid, direction)
            if did and did not in opened:
                continue
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return seen


def boss_room():
    for rid, r in ROOMS.items():
        if r["boss"]:
            return rid
    return None


def _available(rooms, used, crafted):
    """Objets portables présents dans les salles atteintes (hors potions et cœurs)."""
    out = set()
    for o, d in OBJECTS.items():
        if d["kind"] in ("potion", "coeur") or o in used:
            continue
        if d.get("crafted") and o not in crafted:
            continue
        if d["room"] in rooms:
            out.add(o)
    return out


def solve():
    """Retourne (gagnable, plan, salles_atteintes_tous_chapitres).

    plan = liste d'étapes (type, quoi, objet(s), salle) :
      open / free / heart / craft / gate / boss.
    """
    opened, freed, used, hearts, crafted = set(), [], set(), [], set()
    plan = []
    chapter, start = 1, START["room"]
    seen = set()
    while True:
        rooms = reachable_rooms(opened, start)
        seen |= rooms
        avail = _available(rooms, used, crafted)
        step = None
        for did, d in DOORS.items():
            if did in opened:
                continue
            side = d["room"]
            other = ROOMS[side]["exits"][d["dir"]]
            if side not in rooms and other not in rooms:
                continue
            from_room = side if side in rooms else other
            if d.get("key") and d["key"] in avail:
                step = ("open", did, d["key"], from_room)
            elif d.get("need_freed") is not None and len(freed) >= d["need_freed"]:
                step = ("open", did, None, from_room)
            elif d.get("need_hearts") is not None and len(hearts) >= d["need_hearts"]:
                step = ("open", did, None, from_room)
            if step:
                opened.add(did)
                break
        if not step:
            for cid, c in CAPTIVES.items():
                if cid not in freed and c["room"] in rooms and c["item"] in avail:
                    step = ("free", cid, c["item"], c["room"])
                    freed.append(cid)
                    used.add(c["item"])
                    break
        if not step:
            for oid in HEARTS:
                if oid not in hearts and OBJECTS[oid]["room"] in rooms:
                    step = ("heart", oid, None, OBJECTS[oid]["room"])
                    hearts.append(oid)
                    break
        if not step:
            for cid, c in CRAFTS.items():
                if (c["makes"] not in crafted and c["room"] in rooms
                        and all(n in avail for n in c["needs"])):
                    step = ("craft", cid, tuple(c["needs"]), c["room"])
                    used |= set(c["needs"])
                    crafted.add(c["makes"])
                    break
        if not step:
            # le vortex n'est tenté qu'une fois tout le reste du chapitre épuisé
            for rid in sorted(rooms):
                gate = ROOMS[rid].get("gate")
                if gate and gate["key"] in avail:
                    step = ("gate", rid, gate["key"], rid)
                    used.add(gate["key"])
                    chapter = gate["to"]
                    start = CHAPTER_START[chapter]["room"]
                    break
        if not step:
            break
        plan.append(step)
    rooms = reachable_rooms(opened, start)
    avail = _available(rooms, used, crafted)
    br = boss_room()
    weapons = sorted(o for o in avail if OBJECTS[o]["kind"] == BOSS_WEAPON_KIND)
    win = (len(freed) == len(CAPTIVES) and len(hearts) == len(HEARTS) and br in rooms
           and len(weapons) >= BOSS_HITS)
    if win:
        plan.append(("boss", br, tuple(weapons[:BOSS_HITS]), br))
    return win, plan, seen


def _name(oid):
    return "%s (%s)" % (OBJECTS[oid]["name"], OBJECTS[oid]["room"])


def describe(plan):
    lines = []
    for i, (kind, what, item, room) in enumerate(plan, 1):
        if kind == "open":
            d = DOORS[what]
            if item:
                lines.append("%2d. Prendre %s -> ouvrir %s (%s)" % (i, _name(item), d["name"], room))
            elif d.get("need_hearts") is not None:
                lines.append("%2d. %s cede (%s) : %d coeurs reunis" % (i, d["name"], room, d["need_hearts"]))
            else:
                lines.append("%2d. %s s'ouvre (%s) : 8 sorciers liberes" % (i, d["name"], room))
        elif kind == "free":
            lines.append("%2d. Prendre %s -> liberer %s (%s)" % (i, _name(item), CAPTIVES[what]["name"], room))
        elif kind == "heart":
            lines.append("%2d. Ramasser un COEUR SACRE (%s)" % (i, room))
        elif kind == "craft":
            c = CRAFTS[what]
            lines.append("%2d. Deposer %s au %s (%s) -> %s forge" % (
                i, " puis ".join(_name(n) for n in item), c["name"], room, OBJECTS[c["makes"]]["name"]))
        elif kind == "gate":
            lines.append("%2d. Porter %s dans le VORTEX (%s) -> CHAPITRE 2" % (i, _name(item), room))
        else:
            lines.append("%2d. Frapper le Necromancien (%s) avec %d pentacles : %s" % (
                i, room, len(item), ", ".join(_name(o) for o in item)))
    return lines


# ===========================================================================
# Mode « Classique CPC 1985 » : preuve de terminabilité depuis chacun des 5 départs.
#
# Modèle (conforme à classic_game.py) :
# - déplacement sur la grille de cellules : position alignée (cx, cy) du sorcier 3x3 ; un pas
#   horizontal de 4 px coûte 2 trames, un pas vertical (ou diagonal) de 8 lignes 4 trames ;
#   le passage exige que l'union des deux empreintes soit libre ; se poser sur de l'eau
#   (toutes les cellules sous les pieds) est interdit (noyade) ;
# - portes : on les franchit depuis la case collée à la porte ; un sens verrouillé exige de
#   PORTER l'objet-clé (blason / fleur de lys), qui n'est pas consommé ;
# - un seul objet porté ; on ne peut que l'échanger contre un objet posé (jamais poser dans
#   le vide) : l'objet lâché prend la place de l'objet ramassé ;
# - barrière : la toucher en portant l'objet requis l'ouvre et consomme l'objet ;
# - captif : le toucher (cage ouverte) le libère ; victoire = 8 libérés puis autel du sanctuaire.
# Recherche : à chaque étape, Dijkstra multi-sources sur le graphe (salle, point d'intérêt)
# pour chaque type d'objet (« aller prendre un objet de type K puis aller au but »), avec au
# besoin un détour par un objet-clé de porte ; on applique l'action la moins coûteuse. Un plan
# trouvé est une preuve constructive ; son coût (trames) est comparé au sablier.
# ===========================================================================
import heapq

import classic_world as CW
from config import CL_TIME_FRAMES, CL_FRAME_HZ

INF = float("inf")
DOOR_COST = 2          # pousser contre la porte + reprise après changement de salle
ACT_COST = 1           # appui sur FEU / contact


def _valid_grid(grid):
    """Positions alignées (cx, cy) valides pour l'empreinte 3x3 du sorcier."""
    rows, cols = len(grid), len(grid[0])
    free = [[grid[y][x] not in CW.BLOCKING for x in range(cols)] for y in range(rows)]

    def block_free(x0, y0, x1, y1):
        if x0 < 0 or y0 < 0 or x1 >= cols or y1 >= rows:
            return False
        return all(free[y][x] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1))

    valid = set()
    for cy in range(rows - 2):
        for cx in range(cols - 2):
            if not block_free(cx, cy, cx + 2, cy + 2):
                continue
            if cy + 3 < rows and all(grid[cy + 3][cx + i] == CW.WATER for i in range(3)):
                continue                      # posé sur l'eau : noyade
            valid.add((cx, cy))
    return valid, block_free


class ClassicRoomGraph:
    """Points d'intérêt d'une salle + distances entre eux selon les barrières ouvertes."""

    def __init__(self, rid):
        self.rid = rid
        room = CW.ROOMS[rid]
        pts, self.kind = [], []
        self.door_pt, self.slot_pt, self.bar_pts = {}, {}, {}
        self.captive_pt = self.goal_pt = None
        self.start_pt = {}
        for slot in sorted(room["doors"]):
            self.door_pt[slot] = len(pts)
            pts.append([CW.arrival_cell(rid, slot)])
        for i, (kind, x, y) in enumerate(room["items"]):
            self.slot_pt[(rid, i)] = len(pts)
            pts.append([(x + dx, y + dy) for dy in (0, -1, 1, -2, 2) for dx in (0, -1, 1, -2, 2)])
        for b in CW.BARRIERS:
            if b[1] != rid:
                continue
            bid, _, d, x, y, _ = b
            self.bar_pts[bid] = []
            if d == "V":
                sides = [[(x - 3, y + k) for k in (0, -1, 1)], [(x + 3, y + k) for k in (0, -1, 1)]]
            else:
                sides = [[(x + k, y - 3) for k in (0, -1, 1, -2, 2)], [(x + k, y + 3) for k in (0, -1, 1, -2, 2)]]
            for s in sides:
                self.bar_pts[bid].append(len(pts))
                pts.append(s)
        if room["captive"]:
            x, y = room["captive"]
            self.captive_pt = len(pts)
            pts.append([(x + dx, y + dy) for dy in (0, -1, 1, -2, 2) for dx in (0, -1, 1, -2, 2)])
        if room["goal"]:
            x, y = room["goal"]
            self.goal_pt = len(pts)
            pts.append([(x, y), (x - 1, y), (x + 1, y)])
        for si, (srid, x, y) in enumerate(CW.STARTS):
            if srid == rid:
                self.start_pt[si] = len(pts)
                pts.append([(x, y)])
        self.cands = pts
        self._cache = {}

    def config(self, open_barriers):
        key = frozenset(b for b in open_barriers if b in self.bar_pts)
        m = self._cache.get(key)
        if m is None:
            m = self._cache[key] = self._matrix(key)
        return m

    def _matrix(self, opened):
        grid = CW.collision_grid(self.rid, opened)
        valid, block_free = _valid_grid(grid)
        reps = []
        for cand in self.cands:
            rep = next((c for c in cand if c in valid), None)
            reps.append(rep)
        n = len(reps)
        mat = [[INF] * n for _ in range(n)]
        for i, src in enumerate(reps):
            if src is None:
                continue
            dist = self._dijkstra(src, valid, block_free)
            for j, dst in enumerate(reps):
                if dst is not None and dst in dist:
                    mat[i][j] = dist[dst]
        return dict(reps=reps, mat=mat)

    @staticmethod
    def _dijkstra(src, valid, block_free):
        dist = {src: 0}
        pq = [(0, src)]
        while pq:
            d, (x, y) = heapq.heappop(pq)
            if d > dist[(x, y)]:
                continue
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if not dx and not dy:
                        continue
                    n = (x + dx, y + dy)
                    if n not in valid:
                        continue
                    if not block_free(min(x, n[0]), min(y, n[1]), max(x, n[0]) + 2, max(y, n[1]) + 2):
                        continue
                    nd = d + (4 if dy else 2)
                    if nd < dist.get(n, INF):
                        dist[n] = nd
                        heapq.heappush(pq, (nd, n))
        return dist


class ClassicSolver:
    def __init__(self, start):
        self.start = start
        self.rooms = {rid: ClassicRoomGraph(rid) for rid in CW.ROOMS}
        inst = CW.item_instances()
        self.inst_kind = [k for (_r, k, _x, _y) in inst]
        self.slot_of_inst = {}
        self.slots = {}                        # (salle, i) -> instance posée (ou None)
        per_room = {}
        for idx, (rid, kind, x, y) in enumerate(inst):
            i = per_room.get(rid, 0)
            per_room[rid] = i + 1
            self.slots[(rid, i)] = idx
        self.open = set()
        self.freed = []
        self.carried = None
        rid = CW.STARTS[start][0]
        self.cur = (rid, self.rooms[rid].start_pt[start])
        self.t = 0
        self.plan = []

    # --------------------------------------------------------------- graphe global
    def position(self, node):
        """Position alignée (cellules) représentant un point du plan, barrières actuelles."""
        rid, i = node
        return self.rooms[rid].config(self.open)["reps"][i]

    def kind(self, inst):
        return None if inst is None else self.inst_kind[inst]

    def dijkstra(self, sources, carried_kind):
        """sources : {(salle, point): (coût, origine)} -> {(salle, point): (coût, origine)}."""
        best = dict(sources)
        pq = [(c, node, o) for node, (c, o) in sources.items()]
        heapq.heapify(pq)
        while pq:
            d, node, origin = heapq.heappop(pq)
            if d > best[node][0]:
                continue
            rid, i = node
            g = self.rooms[rid]
            m = g.config(self.open)["mat"]
            for j, c in enumerate(m[i]):
                if c < INF and j != i:
                    nd = d + c
                    if nd < best.get((rid, j), (INF,))[0]:
                        best[(rid, j)] = (nd, origin)
                        heapq.heappush(pq, (nd, (rid, j), origin))
            for slot, p in g.door_pt.items():
                if p != i:
                    continue
                dest, dslot, lock = CW.DOOR_TO[(rid, slot)]
                if lock and carried_kind != CW.LOCK_ITEM[lock]:
                    continue
                nn = (dest, self.rooms[dest].door_pt[dslot])
                nd = d + DOOR_COST
                if nd < best.get(nn, (INF,))[0]:
                    best[nn] = (nd, origin)
                    heapq.heappush(pq, (nd, nn, origin))
        return best

    def _pick_sources(self, dist, kind):
        """Points où l'on peut ramasser un objet de type `kind` (coût d'arrivée + échange)."""
        src = {}
        for key, inst in self.slots.items():
            if inst is None or self.inst_kind[inst] != kind:
                continue
            node = (key[0], self.rooms[key[0]].slot_pt[key])
            if node in dist and dist[node][1] and dist[node][1][1] == key:
                continue                     # emplacement déjà vidé par le ramassage précédent
            if node in dist:
                c = dist[node][0] + ACT_COST
                if c < src.get(node, (INF,))[0]:
                    src[node] = (c, (dist[node][1], key))
        return src

    def _targets(self):
        """Buts possibles : (coût_noeuds, type requis, action)."""
        out = []
        for rid in CW.CAPTIVE_ROOMS:
            if rid in self.freed:
                continue
            cage = CW.cage_barrier(rid)
            if cage[0] in self.open:
                out.append(([(rid, self.rooms[rid].captive_pt)], None, ("free", rid)))
        for b in CW.BARRIERS:
            if b[0] in self.open:
                continue
            g = self.rooms[b[1]]
            out.append(([(b[1], p) for p in g.bar_pts[b[0]]], b[5], ("open", b[0])))
        if len(self.freed) == len(CW.CAPTIVE_ROOMS):
            out = [([(CW.SANCTUARY, self.rooms[CW.SANCTUARY].goal_pt)], None, ("goal", CW.SANCTUARY))]
        return out

    def candidates(self):
        """Actions possibles, de la moins coûteuse à la plus coûteuse (une par but et chaîne)."""
        ck = self.kind(self.carried)
        d0 = self.dijkstra({self.cur: (0, ())}, ck)
        # chaînes de ramassages : () rien à prendre, (K,), (L, K) avec L = clé de porte
        chains = {(): d0}
        kinds = sorted(set(self.inst_kind))
        locks = sorted(set(CW.LOCK_ITEM.values()))
        for k in kinds:
            src = self._pick_sources(d0, k)
            if src:
                chains[(k,)] = self.dijkstra(src, k)
        for lk in locks:
            dl = chains.get((lk,))
            if not dl:
                continue
            for k in kinds:
                src = self._pick_sources(dl, k)
                if src:
                    chains[(lk, k)] = self.dijkstra(src, k)
        out = []
        for nodes, need, action in self._targets():
            for chain, dist in chains.items():
                last = chain[-1] if chain else ck
                if need is not None and last != need:
                    continue
                if need is None and chain and chain[-1] not in locks:
                    continue
                best = None
                for n in nodes:
                    if n in dist and (best is None or dist[n][0] < best[0]):
                        best = (dist[n][0], n, chain, dist[n][1], action)
                if best:
                    out.append(best)
        out.sort(key=lambda c: c[0])
        return out

    def apply(self, cand):
        cost, node, chain, origin, action = cand
        picks = []
        o = origin
        while o:
            o, key = o
            picks.append(key)
        picks.reverse()
        for key in picks:
            inst = self.slots[key]
            self.slots[key] = self.carried          # l'objet porté prend sa place
            self.carried = inst
            self.plan.append(("take", key[0], self.inst_kind[inst], key))
        self.t += cost + ACT_COST
        self.cur = node
        kind, what = action
        if kind == "open":
            self.open.add(what)
            self.plan.append(("open", what, self.kind(self.carried), node))
            self.carried = None
        elif kind == "free":
            self.freed.append(what)
            self.plan.append(("free", what, None, node))
        else:
            self.plan.append(("goal", what, None, node))
            return True
        return False

    def _snapshot(self):
        return (dict(self.slots), set(self.open), list(self.freed), self.carried, self.cur, self.t, len(self.plan))

    def _restore(self, snap):
        self.slots, self.open, self.freed, self.carried, self.cur, self.t, n = snap
        self.slots, self.open, self.freed = dict(self.slots), set(self.open), list(self.freed)
        del self.plan[n:]

    def _key(self):
        kinds = tuple(sorted((k, self.kind(v)) for k, v in self.slots.items()))
        return (frozenset(self.open), frozenset(self.freed), self.kind(self.carried), self.cur, kinds)

    def solve(self, branch=3, budget=4000):
        """Recherche en profondeur : l'action la moins chère d'abord, retour arrière si
        l'on se retrouve bloqué (ex. objet-clé de porte abandonné du mauvais côté)."""
        seen = set()
        self.expanded = 0

        def dfs():
            key = self._key()
            if key in seen or self.expanded >= budget:
                return False
            seen.add(key)
            self.expanded += 1
            for cand in self.candidates()[:branch]:
                snap = self._snapshot()
                if self.apply(cand) or dfs():
                    return True
                self._restore(snap)
            return False

        return dfs()


def solve_classic(start):
    """Retourne (gagnable, plan, trames estimées, solveur)."""
    s = ClassicSolver(start)
    win = s.solve()
    return win, s.plan, s.t, s


def describe_classic(plan, frames=None):
    lines = []
    for i, step in enumerate(plan, 1):
        kind, what, item = step[:3]
        if kind == "take":
            lines.append("%2d. Prendre %s (salle %d)" % (i, CW.ITEMS[item]["name"], what))
        elif kind == "open":
            b = CW.BARRIER_BY_ID[what]
            lines.append("%2d. Ouvrir la %s de la salle %d avec %s" % (
                i, "grille" if b[2] == "V" else "trappe", b[1], CW.ITEMS[item]["name"]))
        elif kind == "free":
            lines.append("%2d. Liberer le sorcier de la salle %d (%s)" % (i, what, CW.ROOMS[what]["place"]))
        else:
            lines.append("%2d. Rejoindre l'autel du sanctuaire (salle %d)" % (i, what))
    if frames is not None:
        lines.append("Temps estime : %.0f s sur %.1f s" % (frames / CL_FRAME_HZ, CL_TIME_FRAMES / CL_FRAME_HZ))
    return lines
