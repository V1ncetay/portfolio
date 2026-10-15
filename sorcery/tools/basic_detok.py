#!/usr/bin/env python3
"""Détokeniseur Locomotive BASIC 1.0/1.1 (Amstrad CPC). Code original, stdlib seulement.

Usage : python3 -I tools/basic_detok.py FICHIER.BAS   (fichier sans en-tête AMSDOS)
"""
import struct
import sys

KW = {
    0x80: "AFTER", 0x81: "AUTO", 0x82: "BORDER", 0x83: "CALL", 0x84: "CAT", 0x85: "CHAIN",
    0x86: "CLEAR", 0x87: "CLG", 0x88: "CLOSEIN", 0x89: "CLOSEOUT", 0x8A: "CLS", 0x8B: "CONT",
    0x8C: "DATA", 0x8D: "DEF", 0x8E: "DEFINT", 0x8F: "DEFREAL", 0x90: "DEFSTR", 0x91: "DEG",
    0x92: "DELETE", 0x93: "DIM", 0x94: "DRAW", 0x95: "DRAWR", 0x96: "EDIT", 0x97: "ELSE",
    0x98: "END", 0x99: "ENT", 0x9A: "ENV", 0x9B: "ERASE", 0x9C: "ERROR", 0x9D: "EVERY",
    0x9E: "FOR", 0x9F: "GOSUB", 0xA0: "GOTO", 0xA1: "IF", 0xA2: "INK", 0xA3: "INPUT",
    0xA4: "KEY", 0xA5: "LET", 0xA6: "LINE", 0xA7: "LIST", 0xA8: "LOAD", 0xA9: "LOCATE",
    0xAA: "MEMORY", 0xAB: "MERGE", 0xAC: "MID$", 0xAD: "MODE", 0xAE: "MOVE", 0xAF: "MOVER",
    0xB0: "NEXT", 0xB1: "NEW", 0xB2: "ON", 0xB3: "ON BREAK", 0xB4: "ON ERROR GOTO",
    0xB5: "ON SQ", 0xB6: "OPENIN", 0xB7: "OPENOUT", 0xB8: "ORIGIN", 0xB9: "OUT", 0xBA: "PAPER",
    0xBB: "PEN", 0xBC: "PLOT", 0xBD: "PLOTR", 0xBE: "POKE", 0xBF: "PRINT", 0xC0: "'",
    0xC1: "RAD", 0xC2: "RANDOMIZE", 0xC3: "READ", 0xC4: "RELEASE", 0xC5: "REM", 0xC6: "RENUM",
    0xC7: "RESTORE", 0xC8: "RESUME", 0xC9: "RETURN", 0xCA: "RUN", 0xCB: "SAVE", 0xCC: "SOUND",
    0xCD: "SPEED", 0xCE: "STOP", 0xCF: "SYMBOL", 0xD0: "TAG", 0xD1: "TAGOFF", 0xD2: "TROFF",
    0xD3: "TRON", 0xD4: "WAIT", 0xD5: "WEND", 0xD6: "WHILE", 0xD7: "WIDTH", 0xD8: "WINDOW",
    0xD9: "WRITE", 0xDA: "ZONE", 0xDB: "DI", 0xDC: "EI", 0xDD: "FILL", 0xDE: "GRAPHICS",
    0xDF: "MASK", 0xE0: "FRAME", 0xE1: "CURSOR", 0xE3: "ERL", 0xE4: "FN", 0xE5: "SPC",
    0xE6: "STEP", 0xE7: "SWAP", 0xEA: "TAB", 0xEB: "THEN", 0xEC: "TO", 0xED: "USING",
    0xEE: ">", 0xEF: "=", 0xF0: ">=", 0xF1: "<", 0xF2: "<>", 0xF3: "<=", 0xF4: "+", 0xF5: "-",
    0xF6: "*", 0xF7: "/", 0xF8: "^", 0xF9: "\\", 0xFA: "AND", 0xFB: "MOD", 0xFC: "OR",
    0xFD: "XOR", 0xFE: "NOT",
}
FN = {
    0x00: "ABS", 0x01: "ASC", 0x02: "ATN", 0x03: "CHR$", 0x04: "CINT", 0x05: "COS",
    0x06: "CREAL", 0x07: "EXP", 0x08: "FIX", 0x09: "FRE", 0x0A: "INKEY", 0x0B: "INP",
    0x0C: "INT", 0x0D: "JOY", 0x0E: "LEN", 0x0F: "LOG", 0x10: "LOG10", 0x11: "LOWER$",
    0x12: "PEEK", 0x13: "REMAIN", 0x14: "SGN", 0x15: "SIN", 0x16: "SPACE$", 0x17: "SQ",
    0x18: "SQR", 0x19: "STR$", 0x1A: "TAN", 0x1B: "UNT", 0x1C: "UPPER$", 0x1D: "VAL",
    0x40: "EOF", 0x41: "ERR", 0x42: "HIMEM", 0x43: "INKEY$", 0x44: "PI", 0x45: "RND",
    0x46: "TIME", 0x47: "XPOS", 0x48: "YPOS", 0x49: "DERR",
    0x71: "BIN$", 0x72: "DEC$", 0x73: "HEX$", 0x74: "INSTR", 0x75: "LEFT$", 0x76: "MAX",
    0x77: "MIN", 0x78: "POS", 0x79: "RIGHT$", 0x7A: "ROUND", 0x7B: "STRING$", 0x7C: "TEST",
    0x7D: "TESTR", 0x7E: "COPYCHR$", 0x7F: "VPOS",
}


def real5(b):
    m = b[0] | (b[1] << 8) | (b[2] << 16) | ((b[3] & 0x7F) << 24)
    e = b[4]
    if e == 0:
        return 0.0
    v = (1 + m / 2.0 ** 31) * 2.0 ** (e - 129)
    return -v if b[3] & 0x80 else v


def detok_line(t):
    out = []
    i = 0
    quote = rem = False
    while i < len(t):
        c = t[i]
        if c == 0:
            break
        if quote or rem:
            if c == 0x22:
                quote = False
            out.append(chr(c) if 32 <= c < 127 else "{%02X}" % c)
            i += 1
            continue
        if c == 0x22:
            quote = True
            out.append('"')
            i += 1
        elif c == 0x01:
            out.append(":")
            i += 1
        elif 0x02 <= c <= 0x0D:          # variables : offset 2 octets puis nom (bit 7 = fin)
            i += 3
            name = ""
            while i < len(t):
                name += chr(t[i] & 0x7F)
                if t[i] & 0x80:
                    i += 1
                    break
                i += 1
            out.append(name + {2: "%", 3: "$", 4: "!"}.get(c, ""))
        elif 0x0E <= c <= 0x17:
            out.append(str(c - 0x0E))
            i += 1
        elif c == 0x18:
            out.append(str(t[i + 1]))
            i += 2
        elif c in (0x19,):
            out.append(str(t[i + 1]))
            i += 2
        elif c in (0x1A, 0x1E):
            out.append(str(struct.unpack_from("<H", t, i + 1)[0]))
            i += 3
        elif c == 0x1B:
            out.append("&X" + bin(struct.unpack_from("<H", t, i + 1)[0])[2:])
            i += 3
        elif c == 0x1C:
            out.append("&" + "%X" % struct.unpack_from("<H", t, i + 1)[0])
            i += 3
        elif c == 0x1D:                  # pointeur de ligne (après RUN)
            out.append("<ptr %04X>" % struct.unpack_from("<H", t, i + 1)[0])
            i += 3
        elif c == 0x1F:
            out.append(("%.9g" % real5(t[i + 1:i + 6])))
            i += 6
        elif c == 0xFF:
            out.append(FN.get(t[i + 1], "{FF%02X}" % t[i + 1]))
            i += 2
        elif c >= 0x80:
            kw = KW.get(c, "{%02X}" % c)
            out.append(kw if c >= 0xEE else " " + kw + " ")
            if c in (0xC5, 0xC0):
                rem = True
            i += 1
        else:
            out.append(chr(c))
            i += 1
    return "".join(out).replace("  ", " ")


def detok(data):
    i = 0
    lines = []
    while i + 4 <= len(data):
        ln = struct.unpack_from("<H", data, i)[0]
        if ln == 0:
            break
        num = struct.unpack_from("<H", data, i + 2)[0]
        lines.append("%d %s" % (num, detok_line(data[i + 4:i + ln]).strip()))
        i += ln
    return lines


if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        print("\n".join(detok(f.read())))
