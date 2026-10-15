"""Sons et musique synthétisés en Python pur (ondes carrées façon AY-3-8912).

Aucun fichier audio : les tampons 16 bits sont générés avec le module array
puis passés à pygame.mixer.Sound(buffer=...). Mélodie originale (pas celle du jeu).
"""
import array
import math
import random

RATE = 22050


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def _square(buf, start, freq, dur, vol, duty=0.5, decay=0.0, slide=0.0):
    n = int(dur * RATE)
    if freq <= 0 or n <= 0:
        return
    phase = 0.0
    for i in range(n):
        f = freq + slide * i / n
        phase += f / RATE
        if phase >= 1.0:
            phase -= int(phase)
        env = 1.0 - decay * i / n
        if i > n - 60:
            env *= (n - i) / 60.0
        idx = start + i
        if idx < len(buf):
            buf[idx] += vol * env if phase < duty else -vol * env


def _noise(buf, start, dur, vol, decay=1.0, step=2, seed=7):
    rng = random.Random(seed)
    n = int(dur * RATE)
    v = 0.0
    for i in range(n):
        if i % step == 0:
            v = rng.uniform(-1, 1)
        idx = start + i
        if idx < len(buf):
            buf[idx] += vol * v * (1.0 - decay * i / n)


def _blank(seconds):
    return [0.0] * int(seconds * RATE)


def _tones(seq, vol=0.3, duty=0.5, decay=0.4):
    """seq = [(freq|midi négatif?, durée, slide)] ; freq en Hz."""
    total = sum(s[1] for s in seq)
    buf = _blank(total + 0.02)
    pos = 0
    for item in seq:
        f, d = item[0], item[1]
        slide = item[2] if len(item) > 2 else 0.0
        _square(buf, pos, f, d, vol, duty, decay, slide)
        pos += int(d * RATE)
    return buf


def build_effects():
    fx = {}
    fx["pickup"] = _tones([(midi(72), 0.05), (midi(76), 0.05), (midi(84), 0.08)], 0.25)
    fx["drop"] = _tones([(500, 0.12, -280)], 0.25)
    door = _tones([(110, 0.35, -60)], 0.25, 0.3, 0.6)
    _noise(door, 0, 0.3, 0.12, 1.0, 6)
    fx["door"] = door
    hurt = _blank(0.08)
    _noise(hurt, 0, 0.08, 0.3, 1.0, 3, seed=3)
    fx["hurt"] = hurt
    kill = _tones([(900, 0.18, -800)], 0.22)
    _noise(kill, 0, 0.18, 0.18, 1.0, 2, seed=5)
    fx["kill"] = kill
    fx["free"] = _tones([(midi(n), 0.07) for n in (60, 64, 67, 72, 76, 79)] + [(midi(84), 0.3)], 0.25, 0.5, 0.5)
    fx["cauldron"] = _tones([(320, 0.03), (450, 0.03), (380, 0.04)], 0.15)
    fx["potion"] = _tones([(midi(n), 0.04) for n in (72, 76, 79, 84, 88)], 0.22)
    fx["denied"] = _tones([(150, 0.08), (0, 0.04), (120, 0.12)], 0.25)
    fx["portal"] = _tones([(200 + 40 * (i % 2), 0.05, 300) for i in range(12)], 0.2, 0.3)
    bh = _tones([(300, 0.3, -250)], 0.3, 0.25)
    _noise(bh, 0, 0.3, 0.25, 1.0, 4, seed=9)
    fx["boss_hit"] = bh
    fx["fireball"] = _tones([(1000, 0.12, -700)], 0.12, 0.25)
    fx["victory"] = _tones([(midi(n), d) for n, d in ((67, .12), (72, .12), (76, .12), (79, .24),
                                                      (76, .12), (79, .5))], 0.25, 0.5, 0.3)
    fx["gameover"] = _tones([(midi(n), d) for n, d in ((69, .25), (68, .25), (67, .25), (66, .25), (57, .8))],
                            0.25, 0.5, 0.3)
    fx["start"] = _tones([(midi(n), 0.06) for n in (57, 60, 64, 69, 72, 76, 81)], 0.22)
    return fx


# Mélodie originale en la mineur, 8 mesures de 8 croches (0 = silence).
TUNE_MELODY = [
    69, 72, 76, 72, 81, 79, 76, 72,
    77, 76, 72, 69, 72, 76, 77, 79,
    76, 0, 72, 76, 79, 0, 76, 72,
    74, 71, 67, 71, 74, 79, 78, 79,
    81, 79, 76, 72, 76, 79, 81, 84,
    84, 81, 77, 72, 77, 81, 79, 77,
    74, 77, 81, 77, 74, 72, 71, 72,
    71, 68, 64, 68, 71, 74, 76, 0,
]
TUNE_BASS = [45, 41, 48, 43, 45, 41, 38, 40]
TUNE_CHORDS = [(57, 60, 64), (53, 57, 60), (55, 60, 64), (55, 59, 62),
               (57, 60, 64), (53, 57, 60), (50, 53, 57), (52, 56, 59)]
STEP = 0.15


def build_tune():
    total = len(TUNE_MELODY) * STEP
    buf = _blank(total)
    st = int(STEP * RATE)
    for i, n in enumerate(TUNE_MELODY):
        if n:
            _square(buf, i * st, midi(n), STEP * 0.95, 0.20, 0.5, 0.5)
    for bar, root in enumerate(TUNE_BASS):
        for q in range(4):
            note = root + (12 if q % 2 else 0)
            _square(buf, (bar * 8 + q * 2) * st, midi(note), STEP * 1.9, 0.17, 0.5, 0.3)
    half = st // 2
    for bar, chord in enumerate(TUNE_CHORDS):
        for k in range(16):
            note = chord[k % 3] + 12
            _square(buf, bar * 8 * st + k * half, midi(note), STEP / 2, 0.07, 0.25, 0.6)
    return buf


def to_bytes(samples, channels=1):
    out = array.array("h")
    for s in samples:
        v = int(max(-1.0, min(1.0, s)) * 28000)
        out.append(v)
        if channels == 2:
            out.append(v)
    return out.tobytes()


class Audio:
    def __init__(self, enabled=True):
        self.ok = False
        self.sounds = {}
        self.music = None
        self.music_on = False
        if not enabled:
            return
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(RATE, -16, 1, 512)
            freq, size, channels = pygame.mixer.get_init()
            if freq != RATE or abs(size) != 16:
                pygame.mixer.quit()
                pygame.mixer.init(RATE, -16, channels, 512)
                freq, size, channels = pygame.mixer.get_init()
            self.channels = channels
            for name, samples in build_effects().items():
                self.sounds[name] = pygame.mixer.Sound(buffer=to_bytes(samples, channels))
            self.music = pygame.mixer.Sound(buffer=to_bytes(build_tune(), channels))
            pygame.mixer.set_reserved(1)
            self.music_channel = pygame.mixer.Channel(0)
            self.ok = True
        except Exception:
            self.ok = False

    def play(self, name):
        if self.ok and name in self.sounds:
            try:
                self.sounds[name].play()
            except Exception:
                pass

    def music_start(self):
        if self.ok and not self.music_on:
            self.music_channel.play(self.music, loops=-1)
            self.music_on = True

    def music_stop(self):
        if self.ok and self.music_on:
            self.music_channel.stop()
            self.music_on = False
