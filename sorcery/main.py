"""Sorcery - recréation pour Windows (Python + pygame).

    python main.py               jouer
    python main.py --selftest    tests headless (données, BFS, simulation)
    python main.py --screenshots génère des captures dans screenshots/
    python main.py --solution    affiche la solution calculée par le solveur
    python main.py --export-music F.wav  exporte le thème du titre en WAV
Options : --time MIN (durée), --fullscreen, --mute, --no-scanlines
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import pygame  # noqa: E402

from config import WINDOW_W, WINDOW_H, TICK_S, TIME_LIMIT_MIN  # noqa: E402
from game import Game, Input  # noqa: E402


class App:
    def __init__(self, fullscreen=False, mute=False, time_min=TIME_LIMIT_MIN, scanlines=True, headless=False):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        from render import Renderer
        from audio import Audio
        self.headless = headless
        flags = pygame.SCALED
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), flags)
        pygame.display.set_caption("Sorcery - recreation CPC")
        self.renderer = Renderer()
        self.renderer.scanlines = scanlines
        try:
            icon = pygame.transform.scale(self.renderer.spr["wiz0"], (32, 36))
            pygame.display.set_icon(icon)
        except Exception:
            pass
        self.audio = Audio(enabled=not mute)
        self.time_min = time_min
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
        self.game = Game(audio=self.audio, time_limit_min=self.time_min)
        self.audio.play("start")
        self.audio.play_music("ingame")
        self.scene = "play"
        self.scene_t = 0

    def to_title(self):
        if self.game:
            self.hiscore = max(self.hiscore, self.game.score)
        self.scene = "title"
        self.scene_t = 0
        self.audio.play_music("title")

    def step(self, inp, edges):
        """Un tick logique (50 Hz). edges = ensemble {'action', 'esc'}."""
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
            while acc >= TICK_S and self.running:
                edges, self.keys_edge = self.keys_edge, set()
                self.step(self.held_input(), edges)
                acc -= TICK_S
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
    ap.add_argument("--time", type=int, default=TIME_LIMIT_MIN, help="temps limite (minutes)")
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
    if args.solution:
        import solver
        win, plan, _ = solver.solve()
        print("Gagnable :", win)
        print("\n".join(solver.describe(plan)))
        return 0 if win else 1
    App(fullscreen=args.fullscreen, mute=args.mute, time_min=args.time,
        scanlines=not args.no_scanlines).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
