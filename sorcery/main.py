"""Sorcery - recréation pour Windows (Python + pygame).

    python main.py               jouer (mode « Classique CPC 1985 », par défaut)
    python main.py --plus        jouer au mode Sorcery+ (flip-screen, Chapitre 2)
    python main.py --selftest    tests headless des deux modes (données, BFS, simulation)
    python main.py --screenshots génère des captures dans screenshots/ (classic_*.png + Sorcery+)
    python main.py --solution    affiche la solution du solveur (classique : les 5 départs)
    python main.py --export-music F.wav  exporte le thème du titre en WAV
Options : --time MIN (durée : Ch.1 de Sorcery+, ou sablier du mode classique), --time2 MIN
(Ch.2), --chapter 2 (Sorcery+ au Chapitre 2), --start N (classique : départ 0-4),
--fullscreen, --mute, --no-scanlines
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import pygame  # noqa: E402

from config import (WINDOW_W, WINDOW_H, TICK_S, TIME_LIMIT_MIN, TIME_LIMIT_CH2_MIN,  # noqa: E402
                    CL_FRAME_S, CL_FRAME_HZ, CL_TIME_FRAMES)
from game import Game, Input  # noqa: E402
from classic_game import ClassicGame  # noqa: E402
from classic_render import ClassicRenderer  # noqa: E402
from render import Renderer  # noqa: E402
from audio import Audio  # noqa: E402


class App:
    """mode = "classic" (CPC 1985, 37,5 Hz, par défaut) ou "plus" (Sorcery+, 50 Hz)."""

    def __init__(self, fullscreen=False, mute=False, time_min=None, scanlines=True, headless=False,
                 chapter=1, time2_min=TIME_LIMIT_CH2_MIN, mode="classic", start=None):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.headless = headless
        self.mode = mode
        self.start = start
        flags = 0 if headless else pygame.SCALED
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), flags)
        if mode == "classic":
            pygame.display.set_caption("Sorcery - mode classique CPC 1985")
            self.renderer = ClassicRenderer()
            self.tick_s = CL_FRAME_S
        else:
            pygame.display.set_caption("Sorcery+ - recreation CPC")
            self.renderer = Renderer()
            self.tick_s = TICK_S
            if time_min is None:
                time_min = TIME_LIMIT_MIN
        self.renderer.scanlines = scanlines
        try:
            icon = pygame.transform.scale(self.renderer.spr["wiz0"], (32, 36))
            pygame.display.set_icon(icon)
        except Exception:
            pass
        self.audio = Audio(enabled=not mute)
        self.time_min = time_min
        self.time2_min = time2_min
        self.chapter = chapter
        self.track = None
        self.scene = "title"
        self.scene_t = 0
        self.game = None
        self.hiscore = 0
        self.running = True
        self.keys_edge = set()
        self.joy = None
        try:
            pygame.joystick.init()
            if pygame.joystick.get_count():
                self.joy = pygame.joystick.Joystick(0)
        except Exception:
            self.joy = None
        if fullscreen:
            self.toggle_fullscreen()
        self.audio.play_music("title")

    # ------------------------------------------------------------------ entrées
    def toggle_fullscreen(self):
        try:
            pygame.display.toggle_fullscreen()
        except Exception:
            pass

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN:
                alt = ev.mod & pygame.KMOD_ALT
                if ev.key == pygame.K_F11 or (ev.key == pygame.K_RETURN and alt):
                    self.toggle_fullscreen()
                elif ev.key == pygame.K_F2:
                    self.renderer.scanlines = not self.renderer.scanlines
                elif ev.key == pygame.K_F3:
                    self.audio.toggle_music()
                elif ev.key == pygame.K_ESCAPE:
                    self.keys_edge.add("esc")
                elif ev.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_LCTRL, pygame.K_RCTRL):
                    self.keys_edge.add("action")
            elif ev.type == pygame.JOYBUTTONDOWN:
                if ev.button in (6, 7, 9):
                    self.keys_edge.add("esc")
                else:
                    self.keys_edge.add("action")
            elif ev.type == pygame.JOYDEVICEADDED and self.joy is None:
                try:
                    self.joy = pygame.joystick.Joystick(ev.device_index)
                except Exception:
                    pass

    def held_input(self):
        k = pygame.key.get_pressed()
        inp = Input(
            left=k[pygame.K_LEFT] or k[pygame.K_a] or k[pygame.K_q],
            right=k[pygame.K_RIGHT] or k[pygame.K_d],
            up=k[pygame.K_UP] or k[pygame.K_w] or k[pygame.K_z],
            down=k[pygame.K_DOWN] or k[pygame.K_s],
        )
        if self.joy is not None:
            try:
                ax = self.joy.get_axis(0) if self.joy.get_numaxes() > 0 else 0
                ay = self.joy.get_axis(1) if self.joy.get_numaxes() > 1 else 0
                hx, hy = self.joy.get_hat(0) if self.joy.get_numhats() else (0, 0)
                inp.left |= ax < -0.5 or hx < 0
                inp.right |= ax > 0.5 or hx > 0
                inp.up |= ay < -0.5 or hy > 0
                inp.down |= ay > 0.5 or hy < 0
            except Exception:
                pass
        return inp

    # ------------------------------------------------------------------ scènes
    def new_game(self):
        if self.mode == "classic":
            frames = CL_TIME_FRAMES if self.time_min is None else int(self.time_min * 60 * CL_FRAME_HZ)
            self.game = ClassicGame(audio=self.audio, start=self.start, time_frames=frames)
        else:
            self.game = Game(audio=self.audio, time_limit_min=self.time_min, chapter=self.chapter,
                             time2_min=self.time2_min)
        self.audio.play("start")
        self.track = None
        self.sync_music()
        self.scene = "play"
        self.scene_t = 0

    def sync_music(self):
        """Piste de jeu selon le chapitre ; silence pendant l'écran de transition."""
        g = self.game
        want = None if g.state == "chapter" else ("ingame2" if g.chapter == 2 else "ingame")
        if want == self.track:
            return
        self.track = want
        if want:
            self.audio.play_music(want)
        else:
            self.audio.music_stop()

    def to_title(self):
        if self.game:
            self.hiscore = max(self.hiscore, self.game.score)
        self.scene = "title"
        self.scene_t = 0
        self.audio.play_music("title")

    def step(self, inp, edges):
        """Un tick logique (37,5 Hz en classique, 50 Hz en Sorcery+). edges = {'action', 'esc'}."""
        self.scene_t += 1
        if self.scene == "title":
            if "action" in edges:
                self.new_game()
            elif "esc" in edges:
                self.running = False
        elif self.scene == "play":
            if "esc" in edges:
                self.scene = "pause"
                return
            inp.action = "action" in edges
            self.game.update(inp)
            if self.game.state in ("play", "chapter", "appear"):
                self.sync_music()
            if self.game.state == "lost":
                self.scene, self.scene_t = "over", 0
                self.audio.play_music("over", loops=0)
                self.hiscore = max(self.hiscore, self.game.score)
            elif self.game.state == "won":
                self.scene, self.scene_t = "victory", 0
                self.audio.music_stop()
                self.hiscore = max(self.hiscore, self.game.score)
        elif self.scene == "pause":
            if "action" in edges:
                self.scene = "play"
            elif "esc" in edges:
                self.to_title()
        elif self.scene in ("over", "victory"):
            if self.scene_t > 50 and edges & {"action", "esc"}:
                self.to_title()

    def draw(self):
        r = self.renderer
        if self.scene == "title":
            r.draw_title(self.scene_t, self.hiscore, self.time_min)
        elif self.scene in ("play", "pause"):
            if self.game.state == "chapter":
                r.draw_chapter(self.game, self.game.tick)
            else:
                r.draw_game(self.game)
            if self.scene == "pause":
                r.draw_pause()
        elif self.scene == "over":
            r.draw_gameover(self.game, self.scene_t)
        elif self.scene == "victory":
            r.draw_victory(self.game, self.scene_t)

    def run(self):
        clock = pygame.time.Clock()
        acc = 0.0
        while self.running:
            acc += min(clock.tick(120) / 1000.0, 0.1)
            self.handle_events()
            while acc >= self.tick_s and self.running:
                edges, self.keys_edge = self.keys_edge, set()
                self.step(self.held_input(), edges)
                acc -= self.tick_s
            self.draw()
            self.renderer.present(self.screen)
            pygame.display.flip()
        pygame.quit()


def main(argv=None):
    if sys.stdout is None:            # exe --windowed : pas de console
        sys.stdout = sys.stderr = open(os.devnull, "w")
    ap = argparse.ArgumentParser(description="Sorcery - recreation CPC")
    ap.add_argument("--selftest", action="store_true", help="tests headless")
    ap.add_argument("--screenshots", nargs="?", const=os.path.join(HERE, "screenshots"), help="captures PNG")
    ap.add_argument("--solution", action="store_true", help="affiche la solution")
    ap.add_argument("--plus", action="store_true", help="mode Sorcery+ (flip-screen, Chapitre 2)")
    ap.add_argument("--time", type=float, default=None,
                    help="temps limite en minutes (Sorcery+ Ch.1 : 30 ; classique : 15:22 du binaire)")
    ap.add_argument("--time2", type=int, default=TIME_LIMIT_CH2_MIN, help="temps limite du Ch.2 (minutes)")
    ap.add_argument("--chapter", type=int, choices=(1, 2), default=1, help="chapitre de départ (Sorcery+)")
    ap.add_argument("--start", type=int, choices=range(5), default=None, help="classique : départ 0-4")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--mute", action="store_true")
    ap.add_argument("--no-scanlines", action="store_true")
    ap.add_argument("--export-music", metavar="WAV", help="exporte le thème du titre en WAV")
    args = ap.parse_args(argv)
    if args.export_music:
        import music
        samples = music.build_title()
        music.write_wav(args.export_music, samples)
        st = music.stats(samples)
        print("%s : %.1f s, crête %.2f, RMS %.3f" % (args.export_music, st["duration"], st["peak"], st["rms"]))
        return 0
    if args.selftest or args.screenshots:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import selftest
        code = 0
        if args.selftest:
            code = selftest.run()
        if args.screenshots:
            selftest.screenshots(args.screenshots)
        return code
    plus = args.plus or args.chapter == 2
    if args.solution:
        import solver
        if plus:
            win, plan, _ = solver.solve()
            print("Gagnable :", win)
            print("\n".join(solver.describe(plan)))
            return 0 if win else 1
        ok = True
        for st in ([args.start] if args.start is not None else range(5)):
            win, plan, frames, _ = solver.solve_classic(st)
            ok &= win
            print("== Depart %d (salle %d) : gagnable=%s" % (st, solver.CW.STARTS[st][0], win))
            print("\n".join(solver.describe_classic(plan, frames)))
        return 0 if ok else 1
    App(fullscreen=args.fullscreen, mute=args.mute, time_min=args.time,
        scanlines=not args.no_scanlines, chapter=args.chapter, time2_min=args.time2,
        mode="plus" if plus else "classic", start=args.start).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
