"""Solveur logique : BFS sur le graphe des salles + dépendances portes/objets/captifs.

Hypothèses (conformes au moteur) : portes non consommées et restant ouvertes,
objets de libération consommés (un par captif), un seul objet porté à la fois
(sans conséquence : on peut toujours revenir chercher un objet).
"""
from collections import deque

from world import ROOMS, OBJECTS, DOORS, CAPTIVES, START, FINAL_WEAPON, door_for_exit


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


def solve():
    """Retourne (gagnable, plan, salles_atteintes). plan = liste d'étapes."""
    opened, freed, used = set(), [], set()
    plan = []
    while True:
        rooms = reachable_rooms(opened)
        avail = {o for o, d in OBJECTS.items()
                 if d["room"] in rooms and d["kind"] != "potion" and o not in used}
        progress = False
        for did, d in DOORS.items():
            if did in opened:
                continue
            side = d["room"]
            other = ROOMS[side]["exits"][d["dir"]]
            if side not in rooms and other not in rooms:
                continue
            from_room = side if side in rooms else other
            if d.get("key") and d["key"] in avail:
                plan.append(("open", did, d["key"], from_room))
            elif d.get("need_freed") is not None and len(freed) >= d["need_freed"]:
                plan.append(("open", did, None, from_room))
            else:
                continue
            opened.add(did)
            progress = True
            break
        if progress:
            continue
        for cid, c in CAPTIVES.items():
            if cid in freed:
                continue
            if c["room"] in rooms and c["item"] in avail:
                plan.append(("free", cid, c["item"], c["room"]))
                freed.append(cid)
                used.add(c["item"])
                progress = True
                break
        if not progress:
            break
    rooms = reachable_rooms(opened)
    br = boss_room()
    win = (len(freed) == len(CAPTIVES) and br in rooms and OBJECTS[FINAL_WEAPON]["room"] in rooms)
    if win:
        plan.append(("boss", br, FINAL_WEAPON, br))
    return win, plan, rooms


def describe(plan):
    lines = []
    for i, (kind, what, item, room) in enumerate(plan, 1):
        if kind == "open":
            d = DOORS[what]
            if item:
                lines.append("%2d. Prendre %s (%s) -> ouvrir %s (%s)" % (
                    i, OBJECTS[item]["name"], OBJECTS[item]["room"], d["name"], room))
            else:
                lines.append("%2d. %s s'ouvre (%s) : 8 sorciers liberes" % (i, d["name"], room))
        elif kind == "free":
            lines.append("%2d. Prendre %s (%s) -> liberer %s (%s)" % (
                i, OBJECTS[item]["name"], OBJECTS[item]["room"], CAPTIVES[what]["name"], room))
        else:
            lines.append("%2d. Prendre %s (%s) -> detruire le Necromancien (%s)" % (
                i, OBJECTS[item]["name"], OBJECTS[item]["room"], room))
    return lines
