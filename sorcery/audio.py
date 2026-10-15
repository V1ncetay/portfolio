"""Sons et musique synthétisés en Python pur (ondes carrées façon AY-3-8912).

Aucun fichier audio fourni : les tampons 16 bits sont générés avec le module array
puis passés à pygame.mixer.Sound(buffer=...). Le thème du titre et de la défaite
(Dukas, domaine public) est arrangé dans music.py ; la boucle de jeu ci-dessous est
une mélodie originale. Remplacement facultatif par des fichiers de l'utilisateur :
music/title.(ogg|wav|mp3), music/ingame.(...), music/ingame2.(...) (Chapitre 2),
music/gameover.(...) à côté de main.py
ou de l'exécutable.
"""
import array
import os
import random
import sys

import music

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
    fx["heart"] = _tones([(midi(n), 0.05) for n in (76, 81, 84, 88, 93)] + [(midi(88), 0.15)], 0.22, 0.25, 0.4)
    craft = _tones([(midi(n), 0.08) for n in (60, 67, 72, 79, 84)] + [(midi(91), 0.4)], 0.22, 0.375, 0.5)
    _noise(craft, 0, 0.25, 0.12, 1.0, 5, seed=11)
    fx["craft"] = craft
    return fx


# Boucle de jeu (discrète) : mélodie originale en la mineur, 8 mesures de 8 croches (0 = silence).
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


def build_tune(transpose=0, step=STEP, dark=False):
    """Boucle de jeu. dark=True : variante du Chapitre 2 (plus grave, plus lente, mélodie au
    rapport cyclique fin, basse en octaves descendantes et arpèges renversés)."""
    total = len(TUNE_MELODY) * step
    buf = _blank(total)
    st = int(step * RATE)
    for i, n in enumerate(TUNE_MELODY):
        if n:
            _square(buf, i * st, midi(n + transpose), step * 0.95, 0.20, 0.375 if dark else 0.5, 0.5)
    for bar, root in enumerate(TUNE_BASS):
        for q in range(4):
            if dark:
                note = root + transpose - 12 + (0 if q % 2 else 12)
            else:
                note = root + (12 if q % 2 else 0)
            _square(buf, (bar * 8 + q * 2) * st, midi(note), step * 1.9, 0.17, 0.5, 0.3)
    half = st // 2
    for bar, chord in enumerate(TUNE_CHORDS):
        for k in range(16):
            note = (chord[::-1] if dark else chord)[k % 3] + 12 + transpose
            _square(buf, bar * 8 * st + k * half, midi(note), step / 2, 0.07, 0.25, 0.6)
    return buf


def build_tune2():
    """Chapitre 2 : variation de la boucle de jeu, une tierce mineure plus bas."""
    return build_tune(transpose=-3, step=0.17, dark=True)


def to_bytes(samples, channels=1):
    out = array.array("h")
    for s in samples:
        v = int(max(-1.0, min(1.0, s)) * 28000)
        out.append(v)
        if channels == 2:
            out.append(v)
    return out.tobytes()


MUSIC_EXTS = (".ogg", ".wav", ".mp3")
TRACK_VOLUME = {"title": 1.0, "over": 1.0, "ingame": 0.35, "ingame2": 0.35}
OVERRIDE_NAMES = {"title": "title", "ingame": "ingame", "ingame2": "ingame2", "over": "gameover"}


def music_dirs():
    """Dossiers « music/ » où chercher les fichiers de remplacement."""
    dirs = []
    if getattr(sys, "frozen", False):
        dirs.append(os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "music"))
    dirs.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "music"))
    return dirs


def find_override(track):
    base = OVERRIDE_NAMES.get(track, track)
    for d in music_dirs():
        for ext in MUSIC_EXTS:
            p = os.path.join(d, base + ext)
            if os.path.isfile(p):
                return p
    return None


class Audio:
    """Effets + musique par scène. play_music(piste) choisit la piste de la scène ;
    toggle_music() (F3) coupe/rétablit la musique sans oublier la piste courante."""

    def __init__(self, enabled=True):
        self.ok = False
        self.sounds = {}
        self.tracks = {}
        self.overrides = {}
        self.music_enabled = True
        self.current = None          # (piste, boucles) de la scène courante
        self.music_on = False
        if not enabled:
            return
        try:
            import pygame
            self.pg = pygame
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
            for name, builder in (("title", music.build_title), ("over", music.build_over),
                                  ("ingame", build_tune), ("ingame2", build_tune2)):
                path = find_override(name)
                if path:
                    self.overrides[name] = path
                else:
                    self.tracks[name] = pygame.mixer.Sound(buffer=to_bytes(builder(), channels))
            self.music = self.tracks.get("title")
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

    def play_music(self, track, loops=-1):
        """Musique de la scène (title, ingame, over). Relance si la piste change."""
        if self.current == (track, loops) and self.music_on:
            return
        self._halt()
        self.current = (track, loops)
        if self.music_enabled:
            self._start()

    def _start(self):
        if not self.ok or self.current is None:
            return
        track, loops = self.current
        vol = TRACK_VOLUME.get(track, 1.0)
        try:
            if track in self.overrides:
                self.pg.mixer.music.load(self.overrides[track])
                self.pg.mixer.music.set_volume(vol)
                self.pg.mixer.music.play(loops)
            elif track in self.tracks:
                self.music_channel.set_volume(vol)
                self.music_channel.play(self.tracks[track], loops=loops)
            else:
                return
            self.music_on = True
        except Exception:
            self.music_on = False

    def _halt(self):
        if self.ok and self.music_on:
            try:
                self.music_channel.stop()
                self.pg.mixer.music.stop()
            except Exception:
                pass
        self.music_on = False

    def music_stop(self):
        """Plus de musique pour la scène courante (ex. victoire)."""
        self._halt()
        self.current = None

    def music_start(self):
        """Compatibilité : musique du titre."""
        self.play_music("title")

    def toggle_music(self):
        self.music_enabled = not self.music_enabled
        if self.music_enabled:
            self._start()
        else:
            self._halt()
        return self.music_enabled
