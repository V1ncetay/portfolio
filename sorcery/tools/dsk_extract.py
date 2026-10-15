#!/usr/bin/env python3
"""Extracteur d'image disquette Amstrad CPC (.dsk standard « MV - CPC » et EDSK).

Code original, bibliothèque standard uniquement.

Usage :
    python3 -I tools/dsk_extract.py IMAGE.dsk REPERTOIRE_SORTIE [--json]

- parse l'en-tête Disk-Info et chaque Track-Info (C, H, R, N, ST1, ST2, taille) ;
- signale les secteurs hors format (ID non C1..C9 / 41..49, N != 2, erreurs FDC, tailles atypiques) ;
- lit le catalogue AMSDOS (piste 0 du format DATA, ou piste 2 du format SYSTEM/VENDOR),
  regroupe les extents, reconstitue chaque fichier à partir des blocs de 1 Ko ;
- décode l'en-tête AMSDOS de 128 octets (type, chargement, exécution, longueur, checksum vérifié) ;
- écrit chaque fichier (sans en-tête) + un fichier .hdr et un index catalogue.json dans la sortie.

Les données extraites d'un jeu commercial ne doivent pas être versionnées : choisir un
répertoire de sortie hors du dépôt.
"""
import json
import os
import struct
import sys

TYPES = {0: "BASIC", 1: "BASIC protégé", 2: "binaire", 3: "binaire protégé",
         4: "image écran", 6: "ASCII", 0x16: "ASCII (16)"}


class Dsk:
    def __init__(self, data):
        self.data = data
        sig = data[:34]
        self.extended = sig.startswith(b"EXTENDED CPC DSK")
        if not (self.extended or sig.startswith(b"MV - CPC")):
            raise ValueError("signature DSK inconnue: %r" % sig[:16])
        self.creator = data[0x22:0x30].rstrip(b"\0").decode("latin-1")
        self.ntracks = data[0x30]
        self.nsides = data[0x31]
        self.tracks = {}       # (piste, face) -> dict
        off = 0x100
        for t in range(self.ntracks):
            for s in range(self.nsides):
                if self.extended:
                    tsize = data[0x34 + t * self.nsides + s] * 256
                else:
                    tsize = struct.unpack_from("<H", data, 0x32)[0]
                if tsize == 0:
                    continue
                self.tracks[(t, s)] = self._parse_track(off, tsize, t, s)
                off += tsize

    def _parse_track(self, off, tsize, t, s):
        d = self.data
        if not d[off:off + 12].startswith(b"Track-Info"):
            return {"error": "Track-Info absent", "offset": off, "sectors": []}
        info = {"offset": off, "size": tsize, "track": d[off + 0x10], "side": d[off + 0x11],
                "N": d[off + 0x14], "nsect": d[off + 0x15], "gap3": d[off + 0x16],
                "filler": d[off + 0x17], "sectors": []}
        p = off + 0x100
        for i in range(info["nsect"]):
            c, h, r, n, st1, st2, alen = struct.unpack_from("<BBBBBBH", d, off + 0x18 + 8 * i)
            length = alen if self.extended else (128 << info["N"])
            info["sectors"].append({"C": c, "H": h, "R": r, "N": n, "ST1": st1, "ST2": st2,
                                    "len": length, "pos": p})
            p += length
        return info

    def sector(self, track, rid, side=0):
        for sec in self.tracks[(track, side)]["sectors"]:
            if sec["R"] == rid:
                return self.data[sec["pos"]:sec["pos"] + sec["len"]]
        raise KeyError((track, side, rid))


def detect_format(dsk):
    ids = {s["R"] for s in dsk.tracks[(0, 0)]["sectors"]}
    if 0xC1 in ids:
        return "DATA", 0xC1, 0          # piste de début du répertoire
    if 0x41 in ids:
        return "SYSTEM", 0x41, 2
    if 0x01 in ids:
        return "IBM", 0x01, 1
    raise ValueError("format inconnu")


def anomalies(dsk, first_id):
    out = []
    expected = set(range(first_id, first_id + 9))
    for (t, s), tr in sorted(dsk.tracks.items()):
        if "error" in tr:
            out.append("piste %d face %d: %s" % (t, s, tr["error"]))
            continue
        ids = [x["R"] for x in tr["sectors"]]
        if tr["track"] != t:
            out.append("piste %d: numéro de piste déclaré %d" % (t, tr["track"]))
        if set(ids) != expected or len(ids) != 9:
            out.append("piste %d: IDs %s" % (t, " ".join("%02X" % i for i in ids)))
        for x in tr["sectors"]:
            if x["C"] != t or x["N"] != 2 or x["ST1"] or x["ST2"] or x["H"] != s:
                out.append("piste %d secteur %02X: C=%d H=%d N=%d ST1=%02X ST2=%02X"
                           % (t, x["R"], x["C"], x["H"], x["N"], x["ST1"], x["ST2"]))
    return out


def logical_sectors(dsk, first_id, first_track):
    """Secteurs logiques 512 o dans l'ordre AMSDOS (à partir de la piste du répertoire)."""
    for t in range(first_track, dsk.ntracks):
        for r in range(first_id, first_id + 9):
            yield dsk.sector(t, r)


def read_catalogue(dsk, first_id, first_track):
    secs = list(logical_sectors(dsk, first_id, first_track))
    raw = b"".join(secs[:4])           # 64 entrées de 32 octets
    entries = []
    for i in range(64):
        e = raw[i * 32:(i + 1) * 32]
        user = e[0]
        if user == 0xE5:
            continue
        name = bytes(b & 0x7F for b in e[1:9]).decode("latin-1")
        ext = bytes(b & 0x7F for b in e[9:12]).decode("latin-1")
        flags = {"RO": bool(e[9] & 0x80), "SYS": bool(e[10] & 0x80)}
        entries.append({"index": i, "user": user, "name": name, "ext": ext, "flags": flags,
                        "extent": e[12], "s1": e[13], "s2": e[14], "rc": e[15],
                        "blocks": [b for b in e[16:32] if b]})
    return entries, secs


def amsdos_header(h):
    if len(h) < 128:
        return None
    calc = sum(h[:67]) & 0xFFFF
    stored = struct.unpack_from("<H", h, 67)[0]
    if calc != stored or calc == 0:
        return None
    return {"user": h[0], "name": h[1:9].decode("latin-1"), "ext": h[9:12].decode("latin-1"),
            "type": h[0x12], "type_txt": TYPES.get(h[0x12], "?"),
            "load": struct.unpack_from("<H", h, 0x15)[0],
            "length_field": struct.unpack_from("<H", h, 0x18)[0],
            "exec": struct.unpack_from("<H", h, 0x1A)[0],
            "length": h[0x40] | (h[0x41] << 8) | (h[0x42] << 16),
            "checksum": stored, "checksum_ok": True}


def rebuild(entries, secs):
    files = {}
    for e in entries:
        key = (e["user"], e["name"], e["ext"])
        files.setdefault(key, []).append(e)
    out = []
    for key, exts in files.items():
        exts.sort(key=lambda x: x["extent"] + 32 * x["s2"])
        data = bytearray()
        blocks = []
        for x in exts:
            nrec = x["rc"]
            chunk = bytearray()
            for b in x["blocks"]:
                blocks.append(b)
                chunk += secs[2 * b] + secs[2 * b + 1]
            data += chunk[:nrec * 128]
        out.append({"user": key[0], "name": key[1].strip(), "ext": key[2].strip(),
                    "extents": [x["extent"] for x in exts], "blocks": blocks,
                    "records": sum(x["rc"] for x in exts), "flags": exts[0]["flags"],
                    "raw": bytes(data)})
    return out


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    path, outdir = argv[1], argv[2]
    with open(path, "rb") as f:
        dsk = Dsk(f.read())
    os.makedirs(outdir, exist_ok=True)
    fmt, first_id, first_track = detect_format(dsk)
    print("Image : %s" % os.path.basename(path))
    print("  %s, créateur %r, %d pistes, %d face(s), format %s"
          % ("EDSK" if dsk.extended else "DSK standard", dsk.creator, dsk.ntracks,
             dsk.nsides, fmt))
    an = anomalies(dsk, first_id)
    print("Secteurs hors format : %s" % (len(an) or "aucun"))
    for a in an:
        print("  " + a)
    entries, secs = read_catalogue(dsk, first_id, first_track)
    used = set()
    index = {"image": os.path.basename(path), "format": fmt, "anomalies": an, "files": []}
    print("Catalogue (%d entrées) :" % len(entries))
    for fobj in rebuild(entries, secs):
        raw = fobj["raw"]
        hdr = amsdos_header(raw[:128])
        body = raw[128:] if hdr else raw
        if hdr:
            body = body[:hdr["length"]]
        used.update(fobj["blocks"])
        fname = "%s.%s" % (fobj["name"], fobj["ext"]) if fobj["ext"] else fobj["name"]
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in fname)
        with open(os.path.join(outdir, safe), "wb") as f:
            f.write(body)
        if hdr:
            with open(os.path.join(outdir, safe + ".hdr"), "wb") as f:
                f.write(raw[:128])
        rec = {k: v for k, v in fobj.items() if k != "raw"}
        rec["file"] = safe
        rec["size_on_disk"] = len(raw)
        rec["header"] = hdr
        index["files"].append(rec)
        if hdr:
            desc = "%s, charge &%04X, exec &%04X, long. %d (&%04X), checksum &%04X OK" % (
                hdr["type_txt"], hdr["load"], hdr["exec"], hdr["length"], hdr["length"],
                hdr["checksum"])
        else:
            desc = "pas d'en-tête AMSDOS (ASCII ou brut), %d octets" % len(raw)
        print("  U%d %-8s.%-3s ext %s blocs %s %s\n      -> %s" % (
            fobj["user"], fobj["name"], fobj["ext"], fobj["extents"],
            ",".join("%02X" % b for b in fobj["blocks"]),
            "[%s]" % ",".join(k for k, v in fobj["flags"].items() if v) if any(
                fobj["flags"].values()) else "", desc))
    total_blocks = (len(secs)) // 2
    free = [b for b in range(2, total_blocks) if b not in used]
    # blocs libres contenant des données (fichiers effacés / données cachées)
    nonempty = [b for b in free if any(x not in (0xE5, 0) for x in secs[2 * b] + secs[2 * b + 1])]
    index["blocks_total"] = total_blocks
    index["blocks_free_nonempty"] = nonempty
    print("Blocs : %d au total, %d utilisés, %d libres dont %d non vides %s" % (
        total_blocks, len(used), len(free), len(nonempty),
        ",".join("%02X" % b for b in nonempty)))
    with open(os.path.join(outdir, "catalogue.json"), "w") as f:
        json.dump(index, f, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
