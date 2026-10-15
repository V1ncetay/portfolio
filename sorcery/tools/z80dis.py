#!/usr/bin/env python3
"""Désassembleur Z80 minimal (code original, stdlib seulement).

Décodage algorithmique par champs x/y/z/p/q de l'opcode, préfixes CB, ED, DD, FD, DDCB, FDCB.
Syntaxe Zilog, nombres en hexadécimal « &XXXX » (convention Amstrad).

Usage en ligne de commande :
    python3 -I tools/z80dis.py FICHIER ORIGINE DEBUT [FIN|+N] [--labels]
      FICHIER : binaire brut chargé à l'adresse ORIGINE ; DEBUT/FIN en hexadécimal.
API :
    from z80dis import disasm_one, disasm_range
    disasm_one(mem, addr) -> (taille, texte, cibles)   # mem : bytes/bytearray indexé par adresse
"""
import sys

R = ["b", "c", "d", "e", "h", "l", "(hl)", "a"]
RP = ["bc", "de", "hl", "sp"]
RP2 = ["bc", "de", "hl", "af"]
CC = ["nz", "z", "nc", "c", "po", "pe", "p", "m"]
ALU = ["add a,", "adc a,", "sub ", "sbc a,", "and ", "xor ", "or ", "cp "]
ROT = ["rlc", "rrc", "rl", "rr", "sla", "sra", "sll", "srl"]
IM = ["0", "0", "1", "2", "0", "0", "1", "2"]
BLI = {(4, 0): "ldi", (4, 1): "cpi", (4, 2): "ini", (4, 3): "outi",
       (5, 0): "ldd", (5, 1): "cpd", (5, 2): "ind", (5, 3): "outd",
       (6, 0): "ldir", (6, 1): "cpir", (6, 2): "inir", (6, 3): "otir",
       (7, 0): "lddr", (7, 1): "cpdr", (7, 2): "indr", (7, 3): "otdr"}


def h8(v):
    return "&%02X" % (v & 0xFF)


def h16(v):
    return "&%04X" % (v & 0xFFFF)


def disasm_one(mem, a):
    """Retourne (taille, texte, cibles) ; cibles = adresses de saut/appel."""
    def b(i):
        return mem[(a + i) & 0xFFFF]

    def w(i):
        return b(i) | (b(i + 1) << 8)

    def sd(v):
        return v - 256 if v > 127 else v

    pre = None
    i = 0
    op = b(0)
    if op in (0xDD, 0xFD):
        pre = "ix" if op == 0xDD else "iy"
        i = 1
        op = b(1)
        if op in (0xDD, 0xFD, 0xED):
            return 1, "db " + h8(b(0)) + " ; préfixe orphelin", []
    if op == 0xED:
        return _ed(b, w, i)
    if op == 0xCB:
        if pre:
            d = sd(b(i + 1))
            o2 = b(i + 2)
            x, y, z = o2 >> 6, (o2 >> 3) & 7, o2 & 7
            m = "(%s%+d)" % (pre, d)
            if x == 0:
                t = "%s %s" % (ROT[y], m)
            elif x == 1:
                t = "bit %d,%s" % (y, m)
            elif x == 2:
                t = "res %d,%s" % (y, m)
            else:
                t = "set %d,%s" % (y, m)
            if x != 1 and z != 6:
                t += " ; ->" + R[z]
            return i + 3, t, []
        o2 = b(1)
        x, y, z = o2 >> 6, (o2 >> 3) & 7, o2 & 7
        if x == 0:
            return 2, "%s %s" % (ROT[y], R[z]), []
        return 2, "%s %d,%s" % (["", "bit", "res", "set"][x], y, R[z]), []

    x, y, z = op >> 6, (op >> 3) & 7, op & 7
    p, q = y >> 1, y & 1
    n = i + 1           # index de l'octet suivant l'opcode

    def reg(r, allow_idx=True):
        """Registre 8 bits, en tenant compte de IX/IY. Retourne (texte, octets d'offset)."""
        if pre and allow_idx:
            if r == 6:
                return "(%s%+d)" % (pre, sd(b(n))), 1
            if r == 4:
                return pre + "h", 0
            if r == 5:
                return pre + "l", 0
        return R[r], 0

    def rp(k, tbl=RP):
        if pre and tbl[k] == "hl":
            return pre
        return tbl[k]

    if x == 0:
        if z == 0:
            if y == 0:
                return n, "nop", []
            if y == 1:
                return n, "ex af,af'", []
            tgt = (a + n + 1 + sd(b(n))) & 0xFFFF
            if y == 2:
                return n + 1, "djnz " + h16(tgt), [tgt]
            if y == 3:
                return n + 1, "jr " + h16(tgt), [tgt]
            return n + 1, "jr %s,%s" % (CC[y - 4], h16(tgt)), [tgt]
        if z == 1:
            if q == 0:
                return n + 2, "ld %s,%s" % (rp(p), h16(w(n))), []
            return n, "add %s,%s" % (rp(2), rp(p)), []
        if z == 2:
            tbl = [("ld (bc),a", 0), ("ld a,(bc)", 0), ("ld (de),a", 0), ("ld a,(de)", 0),
                   ("ld (%s),%s" % (h16(w(n)), rp(2)), 2), ("ld %s,(%s)" % (rp(2), h16(w(n))), 2),
                   ("ld (%s),a" % h16(w(n)), 2), ("ld a,(%s)" % h16(w(n)), 2)]
            t, k = tbl[y]
            return n + k, t, []
        if z == 3:
            return n, ("inc " if q == 0 else "dec ") + rp(p), []
        if z in (4, 5):
            r, k = reg(y)
            return n + k, ("inc " if z == 4 else "dec ") + r, []
        if z == 6:
            r, k = reg(y)
            return n + k + 1, "ld %s,%s" % (r, h8(b(n + k))), []
        return n, ["rlca", "rrca", "rla", "rra", "daa", "cpl", "scf", "ccf"][y], []
    if x == 1:
        if y == 6 and z == 6:
            return n, "halt", []
        # ld r,r' : si l'un est (ix+d), l'autre n'est pas remplacé par ixh/ixl
        if pre and (y == 6 or z == 6):
            if y == 6:
                d, _ = reg(6)
                return n + 1, "ld %s,%s" % (d, R[z]), []
            s, _ = reg(6)
            return n + 1, "ld %s,%s" % (R[y], s), []
        d, _ = reg(y)
        s, _ = reg(z)
        return n, "ld %s,%s" % (d, s), []
    if x == 2:
        r, k = reg(z)
        return n + k, ALU[y] + r, []
    # x == 3
    if z == 0:
        return n, "ret " + CC[y], []
    if z == 1:
        if q == 0:
            return n, "pop " + rp(p, RP2), []
        t = ["ret", "exx", "jp (%s)" % rp(2), "ld sp,%s" % rp(2)][p]
        return n, t, []
    if z == 2:
        return n + 2, "jp %s,%s" % (CC[y], h16(w(n))), [w(n)]
    if z == 3:
        if y == 0:
            return n + 2, "jp " + h16(w(n)), [w(n)]
        if y == 2:
            return n + 1, "out (%s),a" % h8(b(n)), []
        if y == 3:
            return n + 1, "in a,(%s)" % h8(b(n)), []
        return n, ["", "", "", "", "ex (sp),%s" % rp(2), "ex de,hl", "di", "ei"][y], []
    if z == 4:
        return n + 2, "call %s,%s" % (CC[y], h16(w(n))), [w(n)]
    if z == 5:
        if q == 0:
            return n, "push " + rp(p, RP2), []
        if p == 0:
            return n + 2, "call " + h16(w(n)), [w(n)]
    if z == 6:
        return n + 1, ALU[y] + h8(b(n)), []
    return n, "rst " + h8(y * 8), [y * 8]


def _ed(b, w, i):
    op = b(i + 1)
    n = i + 2
    x, y, z = op >> 6, (op >> 3) & 7, op & 7
    p, q = y >> 1, y & 1
    if x == 1:
        if z == 0:
            return n, ("in %s,(c)" % R[y]) if y != 6 else "in (c)", []
        if z == 1:
            return n, ("out (c),%s" % R[y]) if y != 6 else "out (c),0", []
        if z == 2:
            return n, ("sbc" if q == 0 else "adc") + " hl," + RP[p], []
        if z == 3:
            if q == 0:
                return n + 2, "ld (%s),%s" % (h16(w(n)), RP[p]), []
            return n + 2, "ld %s,(%s)" % (RP[p], h16(w(n))), []
        if z == 4:
            return n, "neg", []
        if z == 5:
            return n, "reti" if y == 1 else "retn", []
        if z == 6:
            return n, "im " + IM[y], []
        return n, ["ld i,a", "ld r,a", "ld a,i", "ld a,r", "rrd", "rld", "nop*", "nop*"][y], []
    if x == 2 and (y, z) in BLI:
        return n, BLI[(y, z)], []
    return n, "db &ED,%s ; ED invalide" % h8(op), []


def disasm_range(mem, start, end):
    a = start
    out = []
    while a < end:
        size, txt, tg = disasm_one(mem, a)
        raw = " ".join("%02X" % mem[(a + k) & 0xFFFF] for k in range(size))
        out.append((a, raw, txt, tg))
        a += size
    return out


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    data = open(argv[1], "rb").read()
    org = int(argv[2], 16)
    mem = bytearray(65536)
    mem[org:org + len(data)] = data
    start = int(argv[3], 16)
    if len(argv) > 4 and not argv[4].startswith("--"):
        end = start + int(argv[4][1:], 16) if argv[4].startswith("+") else int(argv[4], 16)
    else:
        end = start + 0x40
    for a, raw, txt, _ in disasm_range(mem, start, end):
        print("%04X  %-14s %s" % (a, raw, txt))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
