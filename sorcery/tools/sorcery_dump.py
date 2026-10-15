#!/usr/bin/env python3
"""Décodeur des tables de Sorcery (CPC, disquette) à partir des fichiers extraits par dsk_extract.py.

Code original, stdlib seulement. N'embarque aucune donnée du jeu : tout est relu dans les
fichiers fournis (à garder hors du dépôt).

Usage :
    python3 -I tools/sorcery_dump.py REPERTOIRE_DSK_OUT [--mem FICHIER] [--map N]

- reconstitue la mémoire telle que le jeu la voit après son propre `LDDR` de relocalisation
  (SORCERY2.BIN en &05CF, SORCERY1.BIN chargé en &27C6 puis déplacé de &7FF octets vers le haut) ;
- --mem écrit cette image 64 Ko (pour z80dis.py) ;
- imprime : départs aléatoires, salles (lieu, ennemis, portes, chaudrons, barrières, captif),
  objets posés, palettes ;
- --map N : classe de collision de chaque cellule de la salle N (40x18).
Adresses : voir docs/ANALYSE_DSK.md.
"""
import os
import sys

ROOMS, REC = 40, 48
A_ROOMREC, A_OBJ, A_MAP = 0x5B80, 0x5A40, 0x3240
A_LOCNAMES, A_TOKENS = 0x1E3A, 0x1E0D
A_OBJIDS, A_OBJNAMES, N_OBJIDS = 0x1CF5, 0x1F1B, 0x13
A_START, A_SWAP = 0x1D80, 0x1C3C
HW2FW = [13, 13, 19, 25, 1, 7, 10, 16, 7, 25, 24, 26, 6, 8, 15, 17,
         1, 19, 18, 20, 0, 2, 9, 11, 4, 22, 21, 23, 3, 5, 12, 14]


def build_memory(d):
    m = bytearray(0x10000)
    s2 = open(os.path.join(d, "SORCERY2.BIN"), "rb").read()
    s1 = open(os.path.join(d, "SORCERY1.BIN"), "rb").read()
    m[0x05CF:0x05CF + len(s2)] = s2
    m[0x27C6:0x27C6 + len(s1)] = s1
    # reproduit « ld bc,&7B3A / ld de,&AAFE / ld hl,&A2FF / lddr » (&05CF)
    for k in range(0x7B3A):
        m[0xAAFE - k] = m[0xA2FF - k]
    return m


def nth_string(m, start, n):
    """Émule &1B38 : saute n chaînes (bit 7 = fin) à partir de start puis lit la suivante."""
    hl = start
    for _ in range(n):
        while not m[hl] & 0x80:
            hl += 1
        hl += 1
    out = ""
    while True:
        c = m[hl]
        hl += 1
        ch = c & 0x7F
        if ch < 0x20:                       # jeton : chaîne n° ch+1 après &1E0D
            out += nth_string(m, A_TOKENS, ch + 1)
        else:
            out += chr(ch)
        if c & 0x80:
            return out


def object_names(m):
    names = {}
    for i in range(N_OBJIDS - 1):
        names[m[A_OBJIDS + i]] = nth_string(m, A_OBJNAMES, i + 1).rstrip(".")
    return names


def room_maps(m):
    p = A_MAP
    lists = []
    while len(lists) < ROOMS + 2:
        cells = []
        while True:
            a = m[p]
            p += 1
            if a == 0xFF:
                break
            if a == 0:
                cells += [0] * m[p]
                p += 1
            else:
                cells.append(a)
        lists.append(cells)
    return lists[1:]                        # &0E4E saute (salle+1) terminateurs


def cell_class(t):
    """Classe affectée par &0EB4 (attributs de collision)."""
    if t == 0 or t >= 0xDF:
        return "."                          # vide
    if t < 0x20:
        return "~"                          # &81 : eau (solide, noyade si posé dessus)
    if t < 0x48:
        return "a"                          # &01 : animation décorative traversable
    if t < 0x70:
        return "f"                          # &02 : nocif (feu)
    return "#"                              # &80 : solide


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    m = build_memory(argv[1])
    if "--mem" in argv:
        with open(argv[argv.index("--mem") + 1], "wb") as f:
            f.write(m)
    names = object_names(m)
    on = lambda v: names.get(v, "?%02X" % v) if v else "-"
    locks = {1: on(0x3B), 2: on(0x2B)}       # &1BAF / &1BB7
    print("Objets (id -> nom) :", ", ".join("%02X=%s" % kv for kv in sorted(names.items())))
    print("Départs aléatoires (salle, Y, X) et salles dont le chaudron devient nocif :")
    for i in range(5):
        r, y, x = m[A_START + 3 * i:A_START + 3 * i + 3]
        sw = [v for v in m[A_SWAP + 4 * i:A_SWAP + 4 * i + 4] if v != 0xFF]
        print("  %d : salle %d Y%d X%d ; chaudrons nocifs : %s" % (i, r, y, x, sw))
    print("Salles :")
    for r in range(ROOMS):
        rec = m[A_ROOMREC + REC * r:A_ROOMREC + REC * (r + 1)]
        parts = ["%2d %s" % (r, nth_string(m, A_LOCNAMES, rec[0] + 1).strip())]
        for k, b in enumerate((2, 10)):
            if rec[b] & 0x0F:
                parts.append("E%d type%d Y%d X%d spr&%02X" % (k + 1, rec[b] & 15, rec[b + 1],
                                                              rec[b + 2], rec[b + 3]))
        for b, side in ((18, "G1"), (22, "G2"), (26, "D1"), (30, "D2")):
            y, x, dst, lock = rec[b:b + 4]
            if y != 0xFF:
                parts.append("%s(Y%d,X%d)->%d%s%s%s" % (
                    side, y, x, dst & 0x3F, "D" if dst & 0x80 else "G", "2" if dst & 0x40 else "1",
                    " [%s]" % locks.get(lock, lock) if lock else ""))
        if rec[34] != 0xFF:
            parts.append("chaudron Y%d X%d" % (rec[34], rec[35]))
        if rec[37] != 0xFF:
            parts.append("chaudron nocif Y%d X%d dmg%d" % (rec[37], rec[38], rec[39]))
        if rec[40] != 0xFF:
            parts.append("barrière&43 Y%d X%d <- %s" % (rec[40], rec[41], on(rec[42])))
        if rec[43] != 0xFF:
            parts.append("barrière&42 Y%d X%d <- %s" % (rec[43], rec[44], on(rec[45])))
        if rec[46] != 0xFF:
            parts.append("CAPTIF Y%d X%d" % (rec[46], rec[47]))
        ob = m[A_OBJ + 8 * r:A_OBJ + 8 * r + 8]
        for k in (0, 4):
            if ob[k + 2]:
                parts.append("objet %s Y%d X%d" % (on(ob[k + 2]), ob[k], ob[k + 1]))
        print("; ".join(parts))
    for base, label in ((0x1CB2, "jeu"), (0x1CC3, "titre"), (0x1CD4, "démarrage")):
        print("Palette %s (&%04X) : %s" % (label, base, " ".join(
            "%d" % HW2FW[m[base + i] & 0x1F] for i in range(17))))
    if "--map" in argv:
        n = int(argv[argv.index("--map") + 1])
        cells = room_maps(m)[n]
        for y in range(18):
            print("".join(cell_class(t) for t in cells[y * 40:(y + 1) * 40]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
