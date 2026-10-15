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
