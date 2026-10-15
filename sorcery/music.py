"""Musique : arrangement original 3 voix (façon AY-3-8912) du thème du balai de
« L'apprenti sorcier » de Paul Dukas (1897, domaine public ; Dukas est mort en 1935).

Seule la mélodie de Dukas est reprise, transcrite de mémoire depuis la partition
(thème des bassons, 3/8, Vif, fa mineur). L'harmonisation, la basse, les arpèges,
la percussion et l'enchaînement sont un arrangement propre à ce projet : rien n'est
repris de l'arrangement de la version CPC (Virgin, 1985).

La partition est stockée en texte pour pouvoir la corriger à l'oreille :
- une mesure par segment séparé par « | » ; une mesure de 3/8 = 3 croches ;
- note = nom anglais + altération (b ou #) + octave (C4 = do central), ex. « Ab4 » ;
- « r » = silence ; durée en croches après « : » (défaut 1), ex. « Ab4:3 » = noire pointée ;
- une harmonie (accord) par mesure, qui sert à la basse (voix 2) et aux arpèges (voix 3).
"""
import math
import random
import re

RATE = 22050
AY_CLOCK = 1_000_000          # horloge de l'AY du CPC (1 MHz)
FRAME = RATE // 50            # l'AY était piloté à 50 Hz : enveloppes par trame
BAR_EIGHTHS = 3               # 3/8

# ------------------------------------------------------------------ partition
# Thème A (16 mesures) : exposé du thème aux bassons. La mesure 1 est l'anacrouse.
THEME_A = """
r r C4      | F4 G4 Ab4   | G4 F4 E4    | F4 C4 r     |
Ab4 Bb4 C5  | Bb4 Ab4 G4  | Ab4:3       | r r C4      |
F4 G4 Ab4   | Bb4 C5 Db5  | C5 Bb4 Ab4  | G4 E4 C4    |
F4 E4 F4    | G4 Ab4 Bb4  | C5 G4 E4    | F4:2 r
"""
CHORDS_A = "Fm Fm C7 Fm  Db C7 Fm C7  Fm Bbm Fm C7  Fm C7 C7 Fm"

# Montée (16 mesures) : le motif monte par marches (les balais se multiplient),
# pédale de dominante, puis cadence qui ramène à l'anacrouse du début.
THEME_B = """
F4 G4 Ab4   | G4 F4 E4    | G4 A4 Bb4   | A4 G4 F#4   |
A4 B4 C5    | B4 A4 G#4   | Bb4 C5 D5   | C5 Bb4 A4   |
C5 Db5 C5   | E5 F5 G5    | Ab5 G5 F5   | E5 C5 G4    |
Ab4 Bb4 C5  | Db5 C5 Bb4  | C5 G4 E4    | F4 C4 r
"""
CHORDS_B = "Fm C7 Gm D7  Am E7 Bb F7  C7 C7 Fm C7  Db Bbm C7 Fm"

# Fin pour l'écran de défaite (cadence lente, jouée une fois).
CODA = """
Db4 C4 Bb3  | Ab3 G3 E3   | F3:3        | F3:3
"""
CHORDS_CODA = "Bbm C7 Fm Fm"

SCORES = {"A": (THEME_A, CHORDS_A), "B": (THEME_B, CHORDS_B), "CODA": (CODA, CHORDS_CODA)}

# Morceaux : (partition, mesures [début, fin), transposition, intensité 0..2)
TITLE_FORM = [("A", 0, 16, 0, 0), ("A", 0, 16, 12, 1), ("B", 0, 16, 0, 2)]
TITLE_TEMPO = 92              # noire pointée par minute
OVER_FORM = [("A", 0, 8, -12, 0), ("CODA", 0, 4, 0, 0)]
OVER_TEMPO = 60
OVER_LEAD_S = 1.0             # laisse finir l'effet « gameover »

_NOTE_RE = re.compile(r"^([A-G])([b#]?)(-?\d)$")
_SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_CHORD_RE = re.compile(r"^([A-G][b#]?)(m|7|m7|dim)?$")
_CHORD_IV = {None: (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10), "m7": (0, 3, 7, 10), "dim": (0, 3, 6)}


def note_to_midi(name):
    """« Ab4 » -> 68. Lève ValueError si le nom est invalide."""
    m = _NOTE_RE.match(name)
    if not m:
        raise ValueError("note invalide : %r" % name)
    letter, acc, octave = m.groups()
    return 12 * (int(octave) + 1) + _SEMI[letter] + {"": 0, "b": -1, "#": 1}[acc]


def chord_tones(name):
    """« C7 » -> (racine MIDI octave 2, intervalles)."""
    m = _CHORD_RE.match(name)
    if not m:
        raise ValueError("accord invalide : %r" % name)
    root = note_to_midi(m.group(1) + "2")
    if root < note_to_midi("E2"):        # basse entre E2 et D#3
        root += 12
    return root, _CHORD_IV[m.group(2)]


def parse_bars(text):
    """Texte -> liste de mesures ; mesure = liste de (midi|None, croches)."""
    bars = []
    for seg in text.split("|"):
        toks = seg.split()
        if not toks:
            continue
        bar = []
        for tok in toks:
            name, _, dur = tok.partition(":")
            d = int(dur) if dur else 1
            bar.append((None if name == "r" else note_to_midi(name), d))
        bars.append(bar)
    return bars


def check_scores():
    """Liste d'erreurs (vide si tout est cohérent) : notes, durées par mesure, accords."""
    errs = []
    for key, (text, chords) in SCORES.items():
        try:
            bars = parse_bars(text)
        except ValueError as e:
            errs.append("%s : %s" % (key, e))
            continue
        for i, bar in enumerate(bars):
            tot = sum(d for _, d in bar)
            if tot != BAR_EIGHTHS:
                errs.append("%s mesure %d : %d croches au lieu de %d" % (key, i + 1, tot, BAR_EIGHTHS))
        names = chords.split()
        if len(names) != len(bars):
            errs.append("%s : %d accords pour %d mesures" % (key, len(names), len(bars)))
        for c in names:
            try:
                chord_tones(c)
            except ValueError as e:
                errs.append("%s : %s" % (key, e))
    for form in (TITLE_FORM, OVER_FORM):
        for key, a, b, _, _ in form:
            if key not in SCORES or not 0 <= a < b <= len(parse_bars(SCORES[key][0])):
                errs.append("forme : section invalide %s[%d:%d]" % (key, a, b))
    return errs


_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def midi_name(n):
    return "%s%d" % (_NAMES[n % 12], n // 12 - 1)


def melody_listing(key="A", count=8):
    bars = parse_bars(SCORES[key][0])[:count]
    out = []
    for bar in bars:
        out.append(" ".join(("r" if n is None else midi_name(n)) + (":%d" % d if d != 1 else "") for n, d in bar))
    return " | ".join(out)


# ------------------------------------------------------------------ synthèse AY
# Table de volume logarithmique de l'AY (16 niveaux, ~3 dB par pas).
AY_VOL = [0.0] + [2 ** ((v - 15) / 2.0) for v in range(1, 16)]


def ay_freq(f):
    """Quantifie la fréquence sur la période entière d'un canal tonal de l'AY."""
    period = max(1, round(AY_CLOCK / (16.0 * f)))
    return AY_CLOCK / (16.0 * period)


def _env_levels(nframes, peak, shape):
    """Enveloppe logicielle par trame (niveaux 0..15), comme un driver CPC."""
    out = []
    for k in range(nframes):
        if shape == "pluck":            # basse staccato : chute rapide
            v = peak - 3 * k
        elif shape == "lead":           # mélodie : attaque, petite chute, tenue
            v = peak - min(k, 2) - k // 6
        elif shape == "soft":           # arpège / contre-chant
            v = peak - k // 2
        else:                           # "long" : tenue avec lente décroissance
            v = peak - k // 10
        out.append(max(0, min(15, v)))
    return out


def ay_tone(buf, start, freq, dur, peak, shape="lead", duty=0.5, gate=0.9):
    """Ajoute une note carrée au tampon (start en échantillons, dur en secondes)."""
    n = int(dur * gate * RATE)
    if n <= 0 or freq <= 0:
        return
    f = ay_freq(freq)
    inc = f / RATE
    levels = _env_levels(n // FRAME + 1, peak, shape)
    phase = 0.0
    end = min(len(buf), start + n)
    i = start
    while i < end:
        k = (i - start) // FRAME
        a = AY_VOL[levels[k]]
        stop = min(end, start + (k + 1) * FRAME)
        if a:
            for j in range(i, stop):
                buf[j] += a if phase < duty else -a
                phase += inc
                if phase >= 1.0:
                    phase -= 1.0
        else:
            phase = (phase + inc * (stop - i)) % 1.0
        i = stop


def ay_noise(buf, start, dur, peak, period=2, seed=1):
    """Percussion au générateur de bruit (décroissance d'une trame à l'autre)."""
    rng = random.Random(seed)
    n = int(dur * RATE)
    v = 0.0
    for i in range(min(n, len(buf) - start)):
        if i % period == 0:
            v = 1.0 if rng.random() < 0.5 else -1.0
        lvl = max(0, peak - 4 * (i // FRAME))
        buf[start + i] += AY_VOL[lvl] * v


MIX = {"lead": 0.30, "bass": 0.26, "arp": 0.10, "noise": 0.07}


def render(form, tempo, lead_s=0.0, tail_s=0.0):
    """Rend une forme (liste de sections) en échantillons flottants mono."""
    eighth = 60.0 / tempo / 3.0
    nbars = sum(b - a for _, a, b, _, _ in form)
    total = lead_s + nbars * BAR_EIGHTHS * eighth + tail_s
    lead_b, bass_b, arp_b, noise_b = ([0.0] * int(total * RATE + 1) for _ in range(4))
    t = lead_s
    rng = random.Random(1897)
    for key, a, b, tr, level in form:
        text, chords = SCORES[key]
        bars = parse_bars(text)[a:b]
        names = chords.split()[a:b]
        for bar, cname in zip(bars, names):
            pos = t
            # Voix 1 : mélodie (rapport cyclique plus fin quand ça monte en intensité)
            for n, d in bar:
                if n is not None:
                    ay_tone(lead_b, int(pos * RATE), 440.0 * 2 ** ((n + tr - 69) / 12.0), d * eighth,
                            15 - (level == 0), "long" if d >= 2 else "lead",
                            0.5 if level < 2 else 0.375, 0.92 if d == 1 else 0.97)
                pos += d * eighth
            root, iv = chord_tones(cname)
            if tempo < 80:
                root -= 12
            fifth = root + 7
            # Voix 2 : basse staccato, fondamentale / quinte (pizz.)
            ay_tone(bass_b, int(t * RATE), _hz(root), eighth, 15, "pluck", 0.5, 0.8)
            if level >= 1 or tempo < 80:
                ay_tone(bass_b, int((t + 2 * eighth) * RATE), _hz(fifth if level < 2 else root + 12),
                        eighth, 13, "pluck", 0.5, 0.7)
            # Voix 3 : contre-chant (croches) puis arpège rapide en doubles croches
            chord = [root + 12 + i for i in iv[:3]]
            if level == 0:
                if tempo < 80:
                    ay_tone(arp_b, int(t * RATE), _hz(chord[1]), 3 * eighth, 10, "long", 0.5, 0.95)
                else:
                    for k, n in enumerate((chord[0], chord[2], chord[1])):
                        if k:
                            ay_tone(arp_b, int((t + k * eighth) * RATE), _hz(n + 12), eighth, 10, "soft", 0.25, 0.6)
            else:
                seq = chord + [chord[1]] + chord[:2] if level == 1 else chord[::-1] + chord
                for k, n in enumerate(seq):
                    ay_tone(arp_b, int((t + k * eighth / 2) * RATE), _hz(n + 12 * level), eighth / 2,
                            11, "soft", 0.25, 0.85)
            # Percussion (bruit) : sur le temps en mesure 2, plus charleston en montée
            if level >= 1:
                ay_noise(noise_b, int(t * RATE), 0.09, 14, 3, rng.randrange(1 << 16))
            if level >= 2:
                for k in (1, 2):
                    ay_noise(noise_b, int((t + k * eighth) * RATE), 0.04, 11, 1, rng.randrange(1 << 16))
            t += BAR_EIGHTHS * eighth
    return [MIX["lead"] * a + MIX["bass"] * b + MIX["arp"] * c + MIX["noise"] * d
            for a, b, c, d in zip(lead_b, bass_b, arp_b, noise_b)]


def _hz(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def build_title():
    """Thème du titre (~31 s, en boucle)."""
    return render(TITLE_FORM, TITLE_TEMPO)


def build_over():
    """Variante lente et sombre + cadence finale, pour l'écran de défaite (une fois)."""
    return render(OVER_FORM, OVER_TEMPO, OVER_LEAD_S, 0.6)


def write_wav(path, samples):
    import array
    import wave
    data = array.array("h", (int(max(-1.0, min(1.0, s)) * 28000) for s in samples))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())


def stats(samples):
    peak = max(abs(s) for s in samples) if samples else 0.0
    rms = math.sqrt(sum(s * s for s in samples) / max(1, len(samples)))
    return {"duration": len(samples) / RATE, "peak": peak, "rms": rms}
