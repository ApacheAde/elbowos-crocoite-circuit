#!/usr/bin/env python3
"""Crocoite Circuit — neon light-cycle arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "CROCOITE CIRCUIT"
HANDLE = "x.com/ElbowOS"
BG = (8, 4, 14)
INK = (255, 236, 228)
CYAN = (56, 240, 220)
MAG = (255, 72, 168)
CRO = (255, 92, 36)
GOLD = (255, 210, 72)
VIO = (148, 86, 255)
GRID = (36, 18, 52)
COLS, ROWS = 18, 32
MARGIN_X, MARGIN_Y = 48, 220
CELL = (W - 2 * MARGIN_X) // COLS
OX = (W - COLS * CELL) // 2
OY = MARGIN_Y


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=5):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Bike:
    __slots__ = ("c", "r", "dx", "dy", "col", "trail", "alive", "name")

    def __init__(self, c, r, dx, dy, col, name):
        self.c, self.r, self.dx, self.dy = c, r, dx, dy
        self.col, self.name = col, name
        self.trail: list[tuple[int, int]] = [(c, r)]
        self.alive = True


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 62)
        self.font_md = pygame.font.Font(None, 44)
        self.font_sm = pygame.font.Font(None, 30)
        self.score = 0
        self.reset()

    def reset(self) -> None:
        self.t = 0.0
        self.flash = 0.0
        self.hurt = 0.0
        self.step_acc = 0.0
        self.step_iv = 0.085
        self.combo = 1
        self.sparks: list[Spark] = []
        self.gems: list[tuple[int, int]] = []
        self.you = Bike(3, ROWS // 2, 1, 0, CYAN, "YOU")
        self.foe = Bike(COLS - 4, ROWS // 2, -1, 0, MAG, "RIVAL")
        self.stars = [
            [random.uniform(0, W), random.uniform(0, H), random.uniform(0.6, 2.2)]
            for _ in range(80)
        ]
        self._seed_gems(7)

    def occupied(self) -> set[tuple[int, int]]:
        return set(self.you.trail) | set(self.foe.trail)

    def _seed_gems(self, n: int) -> None:
        occ = self.occupied()
        while len(self.gems) < n:
            p = (random.randrange(COLS), random.randrange(ROWS))
            if p not in occ and p not in self.gems:
                self.gems.append(p)

    def cell_xy(self, c: int, r: int) -> tuple[int, int]:
        return OX + c * CELL + CELL // 2, OY + r * CELL + CELL // 2

    def burst(self, x, y, col, n=16) -> None:
        for _ in range(n):
            a = random.random() * math.tau
            spd = random.uniform(60, 520)
            self.sparks.append(
                Spark(x, y, spd * math.cos(a), spd * math.sin(a),
                      random.uniform(0.18, 0.55), col, random.randint(3, 8))
            )

    def _looks_safe(self, b: Bike, dx: int, dy: int, occ: set) -> bool:
        nc, nr = b.c + dx, b.r + dy
        if not (0 <= nc < COLS and 0 <= nr < ROWS):
            return False
        return (nc, nr) not in occ

    def _steer(self, b: Bike, prefer: tuple[int, int] | None) -> None:
        occ = self.occupied()
        opts = [(b.dx, b.dy), (-b.dy, b.dx), (b.dy, -b.dx)]
        random.shuffle(opts[1:])
        if prefer is not None:
            gx, gy = prefer
            want = []
            if gx > b.c:
                want.append((1, 0))
            elif gx < b.c:
                want.append((-1, 0))
            if gy > b.r:
                want.append((0, 1))
            elif gy < b.r:
                want.append((0, -1))
            for w in want:
                if w != (-b.dx, -b.dy) and w not in opts:
                    opts.insert(0, w)
                elif w in opts:
                    opts.remove(w)
                    opts.insert(0, w)
        for dx, dy in opts:
            if (dx, dy) == (-b.dx, -b.dy):
                continue
            if self._looks_safe(b, dx, dy, occ):
                b.dx, b.dy = dx, dy
                return

    def autoplay(self) -> None:
        if self.gems:
            g = min(self.gems, key=lambda p: abs(p[0] - self.you.c) + abs(p[1] - self.you.r))
            self._steer(self.you, g)
        else:
            self._steer(self.you, None)
        threat = (self.you.c, self.you.r)
        self._steer(self.foe, threat if random.random() < 0.45 else None)

    def _advance(self, b: Bike) -> None:
        if not b.alive:
            return
        nc, nr = b.c + b.dx, b.r + b.dy
        occ = self.occupied()
        if not (0 <= nc < COLS and 0 <= nr < ROWS) or (nc, nr) in occ:
            b.alive = False
            x, y = self.cell_xy(b.c, b.r)
            self.burst(x, y, b.col, 28)
            self.hurt = 0.35
            return
        b.c, b.r = nc, nr
        b.trail.append((nc, nr))
        if len(b.trail) > 220:
            b.trail.pop(0)

    def update(self, dt: float) -> None:
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.hurt = max(0.0, self.hurt - dt)
        if self.record:
            self.autoplay()
        else:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                if self.you.dx == 0:
                    self.you.dx, self.you.dy = -1, 0
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                if self.you.dx == 0:
                    self.you.dx, self.you.dy = 1, 0
            elif keys[pygame.K_UP] or keys[pygame.K_w]:
                if self.you.dy == 0:
                    self.you.dx, self.you.dy = 0, -1
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                if self.you.dy == 0:
                    self.you.dx, self.you.dy = 0, 1
        self.step_acc += dt
        while self.step_acc >= self.step_iv:
            self.step_acc -= self.step_iv
            self._advance(self.you)
            self._advance(self.foe)
            if self.you.alive:
                self.score += 1 * self.combo
        if self.you.alive:
            hit = [g for g in self.gems if g == (self.you.c, self.you.r)]
            for g in hit:
                self.gems.remove(g)
                self.score += 40 * self.combo
                self.combo = min(9, self.combo + 1)
                self.flash = 0.12
                x, y = self.cell_xy(*g)
                self.burst(x, y, GOLD, 18)
            self._seed_gems(6)
        if not self.you.alive or not self.foe.alive:
            if not self.you.alive:
                self.combo = 1
            if self.hurt <= 0.02:
                keep = self.sparks[:]
                self.reset()
                self.sparks = keep
        sparks = []
        for sp in self.sparks:
            sp.life -= dt
            if sp.life <= 0:
                continue
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt
            sparks.append(sp)
        self.sparks = sparks
        for st in self.stars:
            st[1] += (12 + st[2] * 10) * dt
            if st[1] > H:
                st[1] = -4
                st[0] = random.uniform(0, W)

    def handle(self, ev) -> None:
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
            self.score = 0
            self.reset()

    def draw(self, s: pygame.Surface) -> None:
        s.fill(BG)
        pulse = 0.55 + 0.45 * math.sin(self.t * 2.4)
        for i in range(10):
            y = int(80 + i * 180 + math.sin(self.t * 0.7 + i) * 10)
            pygame.draw.line(s, (22, 8, 36), (0, y), (W, y), 2)
        for x, y, r in self.stars:
            pygame.draw.circle(s, (70, 30, 90), (int(x) % W, int(y) % H), int(r))
        board = pygame.Rect(OX - 10, OY - 10, COLS * CELL + 20, ROWS * CELL + 20)
        pygame.draw.rect(s, (18, 8, 28), board, border_radius=16)
        pygame.draw.rect(s, CRO, board, 4, border_radius=16)
        for c in range(COLS + 1):
            x = OX + c * CELL
            pygame.draw.line(s, GRID, (x, OY), (x, OY + ROWS * CELL), 1)
        for r in range(ROWS + 1):
            y = OY + r * CELL
            pygame.draw.line(s, GRID, (OX, y), (OX + COLS * CELL, y), 1)
        for bike in (self.foe, self.you):
            if len(bike.trail) < 2:
                continue
            pts = [self.cell_xy(c, r) for c, r in bike.trail]
            pygame.draw.lines(s, bike.col, False, pts, 10)
            glow = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.lines(glow, (*bike.col, 50), False, pts, 22)
            s.blit(glow, (0, 0))
        for gc, gr in self.gems:
            x, y = self.cell_xy(gc, gr)
            rad = 9 + int(3 * pulse)
            pygame.draw.circle(s, CRO, (x, y), rad)
            pygame.draw.circle(s, GOLD, (x, y), max(3, rad - 5))
        for bike in (self.you, self.foe):
            x, y = self.cell_xy(bike.c, bike.r)
            glow = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*bike.col, int(70 * pulse)), (x, y), 28)
            s.blit(glow, (0, 0))
            pygame.draw.circle(s, INK, (x, y), 14)
            pygame.draw.circle(s, bike.col, (x, y), 10)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life * 2)))
        if self.flash > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((255, 160, 40, int(50 * self.flash / 0.12)))
            s.blit(fl, (0, 0))
        if self.hurt > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((220, 20, 80, int(50 * self.hurt / 0.35)))
            s.blit(fl, (0, 0))
        title = self.font_lg.render(TITLE, True, CRO)
        s.blit(title, title.get_rect(center=(W // 2, 58)))
        handle = self.font_sm.render(HANDLE, True, CYAN)
        s.blit(handle, handle.get_rect(center=(W // 2, 108)))
        hud = self.font_md.render(f"SCORE  {self.score}    x{self.combo}", True, GOLD)
        s.blit(hud, hud.get_rect(center=(W // 2, 158)))
        hint = self.font_sm.render("ARROWS / WASD steer   R reset   x.com/ElbowOS", True, VIO)
        s.blit(hint, hint.get_rect(center=(W // 2, H - 48)))

    def play(self) -> None:
        screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                else:
                    self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/CROCOITE_CIRCUIT_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
