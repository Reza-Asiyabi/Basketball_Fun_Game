"""
Basketball Fun Game  v2.0
=========================
A physics-based basketball shooting game built with Pygame.

Requirements:
    pip install pygame            (required)
    pip install numpy             (optional – enables sound effects)

Run:
    python basketball_game.py

Controls:
    Click + drag FROM the ball to aim (slingshot style)
    Release to shoot  |  F11 = toggle fullscreen  |  R = restart  |  ESC = quit
"""

import pygame
import sys
import math
import random
import json
import os

# ─────────────────────────────────────────────────────
# CONSTANTS  (all positions are in the 960×620 canvas;
#             pygame.SCALED handles fullscreen scaling)
# ─────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 960, 620
FPS        = 60
GRAVITY    = 850.0          # px/s²
BALL_R     = 18             # ball radius in px
RIM_R      = 7              # rim-knob radius
RIM_HALF   = 32             # half the rim opening width
NET_H      = 42
MAX_SHOTS  = 15
MAX_DRAG   = 220.0          # drag px → max power
MIN_POWER  = 280.0          # px/s
MAX_POWER  = 1200.0         # px/s
ELASTICITY = 0.45           # energy fraction kept after rim bounce

FLOOR_Y  = SCREEN_H - 80   # y coordinate of the floor surface
BALL_X0  = 130
BALL_Y0  = FLOOR_Y - BALL_R - 1
HOOP_X0  = 740              # rim centre x
HOOP_Y0  = 260              # rim centre y (default)
BOARD_X  = 840              # backboard face x

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "best_score.json")

# ── Difficulty presets – applied from game start, not mid-game ──────────
DIFFICULTIES = {
    "easy": {
        "label":      "EASY",
        "color":      (50, 200, 70),
        "hoop_speed": 0,
        "wind_max":   0,
        "desc":       "Static hoop  ·  No wind",
    },
    "medium": {
        "label":      "MEDIUM",
        "color":      (230, 185, 25),
        "hoop_speed": 85,
        "wind_max":   55,
        "desc":       "Moving hoop  ·  Mild wind",
    },
    "hard": {
        "label":      "HARD",
        "color":      (220, 45, 45),
        "hoop_speed": 180,
        "wind_max":   120,
        "desc":       "Fast hoop  ·  Strong wind",
    },
}
DIFF_ORDER = ["easy", "medium", "hard"]

# ── Colors ───────────────────────────────────────────
C_WHITE   = (255, 255, 255)
C_BLACK   = (  0,   0,   0)
C_ORANGE  = (225, 108, 18)
C_DK_ORG  = (150,  48,  0)
C_RIM     = (198,  38,  8)
C_RIM_HI  = (245,  85, 45)
C_BOARD   = (195, 210, 228)
C_BOARD_E = (135, 150, 168)
C_NET     = (205, 205, 205)
C_COMBO   = (255, 215,   0)
C_WIND_C  = ( 85, 168, 255)


# ─────────────────────────────────────────────────────
# PERSISTENT BEST SCORE
# ─────────────────────────────────────────────────────
def load_best_score() -> int:
    try:
        with open(SAVE_FILE) as f:
            return int(json.load(f).get("best", 0))
    except Exception:
        return 0


def save_best_score(score: int):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump({"best": score}, f)
    except Exception:
        pass


# ─────────────────────────────────────────────────────
# PRECOMPUTED SURFACES  (called after pygame.init())
# ─────────────────────────────────────────────────────
def _build_arena_bg() -> pygame.Surface:
    """Dark indoor-arena gradient with three overhead spotlight cones."""
    surf = pygame.Surface((SCREEN_W, FLOOR_Y))

    # Vertical gradient: near-black ceiling → deep navy toward court
    for y in range(FLOOR_Y):
        t = y / FLOOR_Y
        pygame.draw.line(surf,
                         (int(6 + 18 * t), int(8 + 14 * t), int(22 + 28 * t)),
                         (0, y), (SCREEN_W, y))

    # Overhead light cones (three spotlights)
    light = pygame.Surface((SCREEN_W, FLOOR_Y), pygame.SRCALPHA)
    for lx in (SCREEN_W // 5, SCREEN_W // 2, 4 * SCREEN_W // 5):
        for i in range(1, 38):
            t     = i / 38
            alpha = int(22 * (1 - t) ** 2)
            w     = int(30 + 180 * t)
            h_c   = int(FLOOR_Y * t)
            pygame.draw.ellipse(light, (255, 245, 215, alpha),
                                pygame.Rect(lx - w // 2, 10, w, h_c))
    surf.blit(light, (0, 0))

    # Crowd-silhouette rows near ceiling
    rng = random.Random(99)
    for row_y, scale in ((18, 0.9), (48, 1.15), (88, 1.35), (138, 1.6)):
        for bx in range(0, SCREEN_W, rng.randint(10, 18)):
            bw  = rng.randint(7, int(14 * scale))
            bh  = rng.randint(10, int(20 * scale))
            col = rng.choice(((35, 15, 75), (75, 15, 15),
                               (15, 50, 15), (60, 50, 10)))
            pygame.draw.ellipse(surf, col, pygame.Rect(bx, row_y, bw, bh))
            # head
            pygame.draw.circle(surf, (185, 145, 110),
                                (bx + bw // 2, row_y - rng.randint(3, 7)),
                                rng.randint(3, int(5 * scale)))
    return surf


def _build_floor_surf() -> pygame.Surface:
    """Hardwood floor with vertical planks, grain and court markings."""
    surf = pygame.Surface((SCREEN_W, 80))
    rng  = random.Random(42)

    plank_palette = [
        (172, 112, 46), (164, 107, 43), (179, 119, 50),
        (168, 110, 45), (176, 116, 49), (161, 104, 41),
        (174, 113, 47), (169, 110, 44),
    ]

    # Vertical plank strips (left-right oriented boards)
    x = 0
    pi = 0
    while x < SCREEN_W:
        w   = rng.randint(26, 38)
        col = plank_palette[pi % len(plank_palette)]
        pygame.draw.rect(surf, col, pygame.Rect(x, 0, w, 80))

        # Lengthwise grain lines
        gx = x + rng.randint(4, 10)
        while gx < x + w - 4:
            gc = (max(0, col[0] - rng.randint(8, 18)),
                  max(0, col[1] - rng.randint(6, 14)),
                  max(0, col[2] - rng.randint(4, 10)))
            pygame.draw.line(surf, gc, (gx, 0), (gx + rng.randint(-6, 6), 80), 1)
            gx += rng.randint(5, 12)

        # Plank-edge shadow (right side)
        ec = (max(0, col[0] - 22), max(0, col[1] - 17), max(0, col[2] - 12))
        pygame.draw.line(surf, ec, (x + w - 1, 0), (x + w - 1, 80), 1)

        x  += w
        pi += 1

    # Top edge (floor-wall boundary line)
    pygame.draw.line(surf, (140, 88, 32), (0, 0), (SCREEN_W, 0), 3)

    # Court markings (painted-on lines – subtle lighter tone)
    mark = (195, 132, 62)
    # Free-throw lane box
    lane_x = BALL_X0 + 10
    pygame.draw.rect(surf, mark, pygame.Rect(lane_x, 0, 175, 80), 2)
    # Three-point arc (appears as short vertical marks at floor edge)
    pygame.draw.line(surf, mark, (lane_x + 195, 0), (lane_x + 195, 12), 2)

    return surf


def _build_ball_template(radius: int) -> tuple[pygame.Surface, int]:
    """
    Pre-render a sphere-shaded ball surface (no seams).
    Returns (surface, centre_offset) where centre_offset is the pixel
    offset from surface top-left to the ball centre.
    """
    pad  = 6          # extra space for drop-shadow
    size = radius * 2 + pad * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2

    # Drop shadow (soft ellipse below-right)
    sh = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 55),
                        pygame.Rect(cx - radius + 5, cy + radius - 5,
                                    radius * 2 - 2, 10))
    surf.blit(sh, (0, 0))

    # Base sphere (main orange)
    pygame.draw.circle(surf, C_ORANGE, (cx, cy), radius)

    # Dark shading on the shadow side (bottom-right)
    dark = pygame.Surface((size, size), pygame.SRCALPHA)
    off  = radius // 4
    for r in range(radius - 1, 0, -3):
        t     = 1 - r / radius
        alpha = int(70 * t * t)
        pygame.draw.circle(dark, (55, 15, 0, alpha),
                           (cx + off, cy + off), r)
    surf.blit(dark, (0, 0))

    # Specular highlight (top-left, warm white)
    hl = pygame.Surface((size, size), pygame.SRCALPHA)
    hc = radius // 3
    for r in range(hc, 0, -1):
        alpha = int(100 * (1 - r / hc) ** 1.5)
        pygame.draw.circle(hl, (255, 235, 190, alpha),
                           (cx - radius // 3, cy - radius // 3), r)
    surf.blit(hl, (0, 0))

    # Outer edge (slight darkening at rim for depth)
    pygame.draw.circle(surf, C_DK_ORG, (cx, cy), radius, 2)

    return surf, cx


# ─────────────────────────────────────────────────────
# SOUND  (procedural – no .wav files needed)
# ─────────────────────────────────────────────────────
class SoundManager:
    def __init__(self):
        self.enabled = False
        try:
            pygame.mixer.init(44100, -16, 2, 512)
            import numpy as np
            sr = 44100
            self.swish  = self._make_swish(sr, np)
            self.bounce = self._make_bounce(sr, np)
            self.miss   = self._make_miss(sr, np)
            self.enabled = True
        except Exception:
            pass

    @staticmethod
    def _make_swish(sr, np):
        t    = np.linspace(0, 0.4, int(sr * 0.4))
        env  = np.sin(np.pi * t / 0.4) ** 2
        data = (env * np.random.uniform(-1, 1, len(t)) * 20000).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack([data, data]))

    @staticmethod
    def _make_bounce(sr, np):
        t    = np.linspace(0, 0.25, int(sr * 0.25))
        env  = np.exp(-14 * t)
        wave = np.sin(2 * np.pi * (90 - 50 * t / 0.25) * t)
        data = (env * wave * 22000).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack([data, data]))

    @staticmethod
    def _make_miss(sr, np):
        t    = np.linspace(0, 0.18, int(sr * 0.18))
        data = (np.exp(-10 * t) * np.sin(2 * np.pi * 180 * t) * 14000).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack([data, data]))

    def play(self, name: str):
        if not self.enabled:
            return
        try:
            getattr(self, name).play()
        except Exception:
            pass


# ─────────────────────────────────────────────────────
# BALL
# ─────────────────────────────────────────────────────
class Ball:
    """Physics, rendering (textured sphere), and trail."""

    TRAIL_LEN = 24
    # Precomputed pebble offsets for leather texture (fixed seed)
    _rng = random.Random(7)
    _PEBBLES = [
        (_rng.uniform(-BALL_R * 0.82, BALL_R * 0.82),
         _rng.uniform(-BALL_R * 0.82, BALL_R * 0.82))
        for _ in range(22)
        if math.hypot(_rng.uniform(-BALL_R * 0.82, BALL_R * 0.82),
                      _rng.uniform(-BALL_R * 0.82, BALL_R * 0.82)) < BALL_R * 0.78
    ]

    def __init__(self, template: pygame.Surface, tmpl_off: int):
        self._tmpl     = template
        self._tmpl_off = tmpl_off   # pixel distance from surface edge to ball centre
        self.reset()

    def reset(self):
        self.x         = float(BALL_X0)
        self.y         = float(BALL_Y0)
        self.vx        = 0.0
        self.vy        = 0.0
        self.in_flight = False
        self.spin      = 0.0        # degrees, drives seam + pebble rotation
        self.spin_rate = 0.0
        self.trail: list[tuple[float, float]] = []

    def shoot(self, angle_deg: float, speed: float, wind: float = 0.0):
        rad        = math.radians(angle_deg)
        self.vx    = speed * math.cos(rad) + wind
        self.vy    = -speed * math.sin(rad)   # screen y inverted
        self.in_flight = True
        self.spin_rate = speed * 0.045

    def update(self, dt: float):
        if not self.in_flight:
            return
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.TRAIL_LEN:
            self.trail.pop(0)
        # Projectile motion
        self.vy   += GRAVITY * dt
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.spin += self.spin_rate

    @property
    def out_of_bounds(self) -> bool:
        return self.y > SCREEN_H + 60 or self.x < -80 or self.x > SCREEN_W + 80

    def draw(self, surf: pygame.Surface):
        # ── Trail (fading orange ghost circles) ──
        n = len(self.trail)
        for i, (tx, ty) in enumerate(self.trail):
            ratio = (i + 1) / (n + 1)
            alpha = int(160 * ratio)
            r     = max(2, int(BALL_R * 0.5 * ratio))
            s     = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (225, 108, 18, alpha), (r, r), r)
            surf.blit(s, (int(tx) - r, int(ty) - r))

        cx, cy = int(self.x), int(self.y)

        # ── Sphere base (precomputed shading) ──
        off = self._tmpl_off
        surf.blit(self._tmpl, (cx - off, cy - off))

        # ── Leather pebbles (tiny dots, co-rotate with spin) ──
        sr  = math.radians(self.spin)
        cos_s, sin_s = math.cos(sr), math.sin(sr)
        for (px, py) in self._PEBBLES:
            # Rotate pebble position by spin angle
            rx = px * cos_s - py * sin_s
            ry = px * sin_s + py * cos_s
            # Only draw if roughly on the "front" hemisphere (positive z proxy)
            if rx * rx + ry * ry < (BALL_R * 0.85) ** 2:
                pygame.draw.circle(surf, C_DK_ORG,
                                   (cx + int(rx), cy + int(ry)), 1)

        # ── Curved seam arcs (two perpendicular half-circles) ──
        seam_rect = pygame.Rect(cx - BALL_R + 3, cy - BALL_R + 3,
                                (BALL_R - 3) * 2, (BALL_R - 3) * 2)
        a0 = math.radians(self.spin)
        pygame.draw.arc(surf, C_DK_ORG, seam_rect, a0,           a0 + math.pi,       2)
        pygame.draw.arc(surf, C_DK_ORG, seam_rect, a0 + math.pi * 0.5,
                        a0 + math.pi * 1.5, 2)


# ─────────────────────────────────────────────────────
# HOOP
# ─────────────────────────────────────────────────────
class Hoop:
    """Backboard, rim (3-D shaded), net. Supports vertical motion."""

    def __init__(self):
        self.x          = float(HOOP_X0)
        self.y          = float(HOOP_Y0)
        self.move_speed = 0.0
        self.move_dir   = 1.0
        self.net_shake  = 0.0

    @property
    def left_rim(self) -> tuple[float, float]:
        return (self.x - RIM_HALF, self.y)

    @property
    def right_rim(self) -> tuple[float, float]:
        return (self.x + RIM_HALF, self.y)

    def set_moving(self, speed: float):
        self.move_speed = speed

    def update(self, dt: float):
        if self.move_speed > 0:
            self.y += self.move_speed * self.move_dir * dt
            if self.y < 175 or self.y > 385:
                self.move_dir *= -1
        self.net_shake = max(0.0, self.net_shake - dt * 5)

    def draw(self, surf: pygame.Surface):
        bx  = BOARD_X
        ry  = int(self.y)
        lx  = int(self.x - RIM_HALF)
        rx  = int(self.x + RIM_HALF)
        mid = int(self.x)

        # ── Support arm ──
        pygame.draw.line(surf, (70, 70, 70), (rx + 2, ry - 3), (bx - 12, ry - 3), 6)
        pygame.draw.line(surf, (95, 95, 95), (rx + 2, ry - 5), (bx - 12, ry - 5), 2)

        # ── Backboard body ──
        board = pygame.Rect(bx - 14, ry - 78, 16, 112)
        pygame.draw.rect(surf, C_BOARD, board)
        # Slight inner bevel (lighter left edge, darker right edge)
        pygame.draw.line(surf, (225, 235, 245), (bx - 13, ry - 77), (bx - 13, ry + 33), 2)
        pygame.draw.rect(surf, C_BOARD_E, board, 2)
        # Target rectangle on board
        pygame.draw.rect(surf, C_RIM, pygame.Rect(bx - 12, ry - 40, 11, 34), 2)

        # ── Rim (3-D shaded tube) ──
        # Shadow line under rim
        pygame.draw.line(surf, (80, 15, 0),
                         (lx - RIM_R, ry + 4), (rx + RIM_R, ry + 4), 4)
        # Main rim bar
        pygame.draw.line(surf, C_RIM, (lx, ry), (rx, ry), RIM_R * 2)
        # Highlight line on top of rim
        pygame.draw.line(surf, C_RIM_HI, (lx, ry - 3), (rx, ry - 3), 2)
        # Rim-end knobs
        for kx, ky in [self.left_rim, self.right_rim]:
            pygame.draw.circle(surf, C_RIM,    (int(kx), int(ky)), RIM_R)
            pygame.draw.circle(surf, C_RIM_HI, (int(kx), int(ky) - 2), RIM_R // 2)

        # ── Net ──
        t_now = pygame.time.get_ticks() * 0.001
        shake = math.sin(t_now * 14) * self.net_shake * 5

        # Vertical strands fanning from rim to a narrowed bottom
        strands = 12
        for i in range(strands + 1):
            frac  = i / strands
            top_x = lx + frac * (rx - lx)
            bot_x = (mid + (frac - 0.5) * 14
                     + shake * (frac - 0.5) * 1.2)
            bot_y = ry + NET_H + self.net_shake * 7 * math.sin(frac * math.pi)
            pygame.draw.line(surf, C_NET,
                             (int(top_x), ry), (int(bot_x), int(bot_y)), 1)

        # Horizontal rows (4 rows, converging)
        for row in range(1, 5):
            t      = row / 5
            y_row  = (ry + t * NET_H
                      + self.net_shake * 5 * math.sin(t * math.pi + shake))
            xl = lx + t * (mid - lx) + t * shake * 0.3
            xr = rx + t * (mid - rx) - t * shake * 0.3
            pygame.draw.line(surf, C_NET,
                             (int(xl), int(y_row)), (int(xr), int(y_row)), 1)

    # ── Collision detection ──────────────────────────

    def check_score(self, ball: "Ball", prev_y: float) -> bool:
        """Ball centre crossed rim plane downward inside the scoring zone."""
        if ball.vy <= 0:
            return False
        if not (prev_y < self.y <= ball.y):
            return False
        return abs(ball.x - self.x) <= RIM_HALF - BALL_R * 0.55

    def check_rim_collision(self, ball: "Ball") -> bool:
        """Circle-circle bounce off left/right rim knobs."""
        bounced = False
        for (kx, ky) in [self.left_rim, self.right_rim]:
            dx, dy   = ball.x - kx, ball.y - ky
            dist     = math.hypot(dx, dy)
            min_dist = BALL_R + RIM_R
            if 0 < dist < min_dist:
                nx, ny   = dx / dist, dy / dist
                ball.x  += nx * (min_dist - dist)
                ball.y  += ny * (min_dist - dist)
                dot      = ball.vx * nx + ball.vy * ny
                ball.vx  = (ball.vx - 2 * dot * nx) * ELASTICITY
                ball.vy  = (ball.vy - 2 * dot * ny) * ELASTICITY
                bounced  = True
        return bounced

    def check_backboard_collision(self, ball: "Ball") -> bool:
        """Simple flat-face bounce off the front of the backboard."""
        face = BOARD_X - 14
        if (ball.vx > 0
                and ball.x + BALL_R >= face
                and ball.x < face + 20
                and self.y - 78 <= ball.y <= self.y + 34):
            ball.x  = face - BALL_R
            ball.vx = -abs(ball.vx) * ELASTICITY
            return True
        return False


# ─────────────────────────────────────────────────────
# PARTICLES & FLOATING TEXT
# ─────────────────────────────────────────────────────
class Particle:
    def __init__(self, x: float, y: float, color: tuple):
        a       = random.uniform(0, math.tau)
        sp      = random.uniform(90, 265)
        self.x, self.y = x, y
        self.vx, self.vy = sp * math.cos(a), sp * math.sin(a)
        self.color = color
        self.life  = random.uniform(0.4, 0.85)
        self.max_l = self.life
        self.r     = random.randint(3, 8)

    def update(self, dt: float):
        self.x   += self.vx * dt
        self.y   += self.vy * dt
        self.vy  += 350 * dt
        self.vx  *= 0.98
        self.life -= dt

    def draw(self, surf: pygame.Surface):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / self.max_l))
        s = pygame.Surface((self.r * 2, self.r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], alpha), (self.r, self.r), self.r)
        surf.blit(s, (int(self.x) - self.r, int(self.y) - self.r))


class FloatingText:
    def __init__(self, text: str, x: float, y: float,
                 color: tuple, size: int = 34, duration: float = 1.1):
        self.text     = text
        self.x, self.y = x, y
        self.color    = color
        self.life     = duration
        self.max_life = duration
        self.vy       = -88.0
        self.font     = pygame.font.SysFont("Arial", size, bold=True)

    def update(self, dt: float):
        self.y    += self.vy * dt
        self.life -= dt

    def draw(self, surf: pygame.Surface):
        if self.life <= 0:
            return
        alpha   = int(255 * min(1.0, self.life / self.max_life * 2))
        rendered = self.font.render(self.text, True, self.color)
        rendered.set_alpha(alpha)
        surf.blit(rendered, (int(self.x) - rendered.get_width() // 2, int(self.y)))


# ─────────────────────────────────────────────────────
# HUD & SCREEN DRAWING HELPERS
# ─────────────────────────────────────────────────────
def draw_aim_arrow(surf: pygame.Surface,
                   origin: tuple, drag: tuple, power: float):
    ox, oy = origin
    dx, dy = drag
    if math.hypot(dx - ox, dy - oy) < 8:
        return
    ax  = int(ox + (ox - dx) * 0.5)
    ay  = int(oy + (oy - dy) * 0.5)
    col = (int(50 + 200 * power), int(200 - 150 * power), 30)
    pygame.draw.line(surf, col, (ox, oy), (ax, ay), 3)
    ang = math.atan2(ay - oy, ax - ox)
    for side in (0.45, -0.45):
        pygame.draw.line(surf, col, (ax, ay),
                         (int(ax - 16 * math.cos(ang + side)),
                          int(ay - 16 * math.sin(ang + side))), 3)


def draw_power_bar(surf: pygame.Surface, cx: float, cy: float, power: float):
    bx, by = int(cx) - 30, int(cy) + 26
    pygame.draw.rect(surf, (45, 45, 45),  pygame.Rect(bx,      by, 60,           8))
    pygame.draw.rect(surf,
                     (int(50 + 200 * power), int(200 - 150 * power), 30),
                     pygame.Rect(bx, by, int(60 * power), 8))
    pygame.draw.rect(surf, C_WHITE,       pygame.Rect(bx,      by, 60,           8), 1)


def draw_hud(surf: pygame.Surface, score: int, shots: int, combo: int,
             difficulty: str, wind: float, best: int,
             font_lg: pygame.font.Font, font_sm: pygame.font.Font):
    panel = pygame.Surface((240, 150), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 160))
    surf.blit(panel, (10, 10))

    acc      = (score * 100 // shots) if shots else 0
    diff_col = DIFFICULTIES[difficulty]["color"]
    diff_lbl = DIFFICULTIES[difficulty]["label"]
    rows = [
        (f"Score:     {score}",             font_lg, C_WHITE),
        (f"Shots:     {shots}/{MAX_SHOTS}", font_sm, C_WHITE),
        (f"Accuracy:  {acc}%",              font_sm, C_WHITE),
        (f"Best:      {best}",              font_sm, C_COMBO),
        (f"Difficulty: {diff_lbl}",         font_sm, diff_col),
    ]
    for i, (text, font, col) in enumerate(rows):
        surf.blit(font.render(text, True, col), (18, 14 + i * 26))

    # Wind bar
    if abs(wind) > 1:
        wy = 168
        surf.blit(font_sm.render("Wind:", True, C_WIND_C), (18, wy))
        bw = min(int(abs(wind) * 0.5), 90)
        bx = 70 if wind > 0 else 70 - bw
        pygame.draw.rect(surf, C_WIND_C, pygame.Rect(bx, wy + 6, bw, 10))
        arr = ">>>" if wind > 0 else "<<<"
        ax  = 70 + bw + 4 if wind > 0 else 70 - bw - 30
        surf.blit(font_sm.render(arr, True, C_WIND_C), (ax, wy))

    # Combo banner
    if combo >= 2:
        ct = font_lg.render(f"COMBO  x{combo}!", True, C_COMBO)
        surf.blit(ct, (SCREEN_W // 2 - ct.get_width() // 2, 12))


def draw_menu_screen(surf: pygame.Surface, best_score: int,
                     font_title: pygame.font.Font,
                     font_md: pygame.font.Font,
                     font_sm: pygame.font.Font,
                     fullscreen: bool) -> dict[str, pygame.Rect]:
    """Draw title + difficulty buttons. Returns {'easy':Rect, 'medium':Rect, 'hard':Rect}."""
    surf.fill((10, 18, 10))

    # Title
    title = font_title.render("BASKETBALL  FUN", True, C_ORANGE)
    surf.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 65))

    sub = font_md.render("Physics Shooting Game", True, (185, 185, 185))
    surf.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 142))

    # Best score
    bs = font_md.render(f"Best Score:  {best_score}", True, C_COMBO)
    surf.blit(bs, (SCREEN_W // 2 - bs.get_width() // 2, 192))

    # "Select difficulty" label
    sd = font_md.render("SELECT  DIFFICULTY", True, C_WHITE)
    surf.blit(sd, (SCREEN_W // 2 - sd.get_width() // 2, 262))

    # Difficulty buttons (3 side-by-side)
    btn_w, btn_h = 210, 90
    gap          = 28
    total_w      = btn_w * 3 + gap * 2
    start_x      = SCREEN_W // 2 - total_w // 2
    btn_y        = 310

    btns: dict[str, pygame.Rect] = {}
    mx, my = pygame.mouse.get_pos()

    for i, key in enumerate(DIFF_ORDER):
        cfg  = DIFFICULTIES[key]
        bx   = start_x + i * (btn_w + gap)
        rect = pygame.Rect(bx, btn_y, btn_w, btn_h)
        btns[key] = rect

        hover  = rect.collidepoint(mx, my)
        base_c = cfg["color"]
        fill_c = tuple(min(255, c + 40) for c in base_c) if hover else base_c

        pygame.draw.rect(surf, fill_c,  rect, border_radius=14)
        pygame.draw.rect(surf, C_WHITE, rect, 2, border_radius=14)

        lbl = font_md.render(cfg["label"], True, C_BLACK if hover else C_WHITE)
        surf.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                        rect.centery - lbl.get_height() // 2 - 8))

        desc = font_sm.render(cfg["desc"], True, C_BLACK if hover else (200, 200, 200))
        surf.blit(desc, (rect.centerx - desc.get_width() // 2,
                         rect.centery + 14))

    # Instructions
    lines = [
        ("HOW  TO  PLAY", font_md, C_ORANGE),
        ("Click + drag FROM the ball to aim  (slingshot)", font_sm, C_WHITE),
        ("Longer drag  =  more power  ·  Release to shoot", font_sm, C_WHITE),
        ("3 consecutive baskets  =  COMBO  (+2 pts each)", font_sm, C_COMBO),
        ("R = restart     ESC = quit     F11 = fullscreen", font_sm, (160, 160, 160)),
    ]
    for i, (text, font, col) in enumerate(lines):
        t = font.render(text, True, col)
        surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 430 + i * 32))

    # Fullscreen status badge
    fs_text = "[ F11 ]  Fullscreen: ON" if fullscreen else "[ F11 ]  Fullscreen: OFF"
    fs_surf = font_sm.render(fs_text, True, (120, 200, 120) if fullscreen else (160, 160, 160))
    surf.blit(fs_surf, (SCREEN_W - fs_surf.get_width() - 14, SCREEN_H - 28))

    return btns


def draw_game_over_screen(surf: pygame.Surface, score: int, shots: int,
                          best: int, new_best: bool,
                          font_title: pygame.font.Font,
                          font_md: pygame.font.Font,
                          font_sm: pygame.font.Font) -> pygame.Rect:
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    surf.blit(overlay, (0, 0))

    go = font_title.render("GAME  OVER", True, (218, 42, 42))
    surf.blit(go, (SCREEN_W // 2 - go.get_width() // 2, 105))

    if new_best:
        nb = font_md.render("NEW  BEST  SCORE!", True, C_COMBO)
        surf.blit(nb, (SCREEN_W // 2 - nb.get_width() // 2, 178))

    acc    = (score * 100 // shots) if shots else 0
    rating = ("PERFECT!" if acc == 100 else
              "GREAT!"   if acc >= 70  else
              "GOOD!"    if acc >= 50  else "KEEP  PRACTISING!")

    stats = [
        (f"Final Score:  {score}",  font_md, C_WHITE),
        (f"Best Score:   {best}",   font_md, C_COMBO),
        (f"Shots Taken:  {shots}",  font_md, C_WHITE),
        (f"Accuracy:     {acc}%",   font_md, C_WHITE),
        (rating,                    font_md, C_COMBO if acc >= 70 else C_WHITE),
    ]
    for i, (text, font, col) in enumerate(stats):
        t = font.render(text, True, col)
        surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 225 + i * 52))

    btn = pygame.Rect(SCREEN_W // 2 - 125, 510, 250, 58)
    pygame.draw.rect(surf, C_ORANGE, btn, border_radius=12)
    pygame.draw.rect(surf, C_WHITE,  btn, 2, border_radius=12)
    bt = font_md.render("PLAY  AGAIN", True, C_BLACK)
    surf.blit(bt, (btn.centerx - bt.get_width() // 2,
                   btn.centery - bt.get_height() // 2))
    return btn


# ─────────────────────────────────────────────────────
# MAIN GAME CLASS
# ─────────────────────────────────────────────────────
class Game:
    """
    State machine:  "menu"  →  "play"  →  "gameover"  →  "menu"

    Fixes vs v1
    ───────────
    • Hoop movement and wind are SET when the game starts (not after the
      first shot).  Wind re-randomises between shots, still within the
      chosen difficulty range.
    • Difficulty is chosen upfront on the menu – no gradual escalation.
    • Best score is loaded from disk and saved on game-over.
    • F11 toggles true fullscreen via pygame.SCALED (internal res fixed).
    """

    def __init__(self):
        pygame.init()
        # Use SCALED so the 960×620 canvas fills any monitor in fullscreen
        self._fs_flags = pygame.SCALED
        self.screen     = pygame.display.set_mode(
            (SCREEN_W, SCREEN_H), self._fs_flags)
        pygame.display.set_caption("Basketball Fun Game")
        self.clock      = pygame.time.Clock()
        self.fullscreen = False

        # Fonts
        self.f_title = pygame.font.SysFont("Arial", 62, bold=True)
        self.f_lg    = pygame.font.SysFont("Arial", 26, bold=True)
        self.f_md    = pygame.font.SysFont("Arial", 36, bold=True)
        self.f_sm    = pygame.font.SysFont("Arial", 20)

        # Precomputed surfaces (requires pygame.init to be done first)
        self._arena_bg    = _build_arena_bg()
        self._floor_surf  = _build_floor_surf()
        self._ball_tmpl, self._ball_tmpl_off = _build_ball_template(BALL_R)

        self.sounds = SoundManager()

        self.best_score = load_best_score()
        self.state      = "menu"
        self.difficulty = "medium"          # default selection
        self._diff_btns: dict[str, pygame.Rect] = {}
        self._restart_btn: pygame.Rect | None   = None

        self._init_game("medium")

    # ─── Display ──────────────────────────────────────

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = pygame.FULLSCREEN | pygame.SCALED if self.fullscreen else self._fs_flags
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)

    # ─── Game initialisation ──────────────────────────

    def _init_game(self, difficulty: str):
        """
        Reset all game state and immediately apply difficulty settings so
        the hoop is ALREADY moving and wind is ALREADY set before the
        first shot – not triggered by it.
        """
        self.difficulty  = difficulty
        self.ball        = Ball(self._ball_tmpl, self._ball_tmpl_off)
        self.hoop        = Hoop()
        self.score       = 0
        self.shots       = 0
        self.combo       = 0
        self.new_best    = False

        self.particles:  list[Particle]     = []
        self.floats:     list[FloatingText] = []

        self.dragging    = False
        self.drag_start  = (0, 0)
        self.drag_cur    = (0, 0)

        self.waiting_reset = False
        self.reset_timer   = 0.0
        self.scored_shot   = False

        # Apply difficulty IMMEDIATELY – hoop moves and wind blows from the start
        self._apply_difficulty()

    def _apply_difficulty(self):
        """Set hoop speed and wind from the current difficulty preset."""
        cfg = DIFFICULTIES[self.difficulty]
        self.hoop.set_moving(cfg["hoop_speed"])
        self.wind = self._new_wind()

    def _new_wind(self) -> float:
        """Return a new random wind within the current difficulty range."""
        wm = DIFFICULTIES[self.difficulty]["wind_max"]
        if wm == 0:
            return 0.0
        return random.uniform(-wm, wm)

    # ─── Input ────────────────────────────────────────

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._quit()
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                if event.key == pygame.K_r and self.state != "menu":
                    self.state = "menu"

            if self.state == "menu":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    for key, rect in self._diff_btns.items():
                        if rect.collidepoint(event.pos):
                            self._init_game(key)
                            self.state = "play"

            elif self.state == "play":
                self._handle_play_input(event)

            elif self.state == "gameover":
                if (event.type == pygame.MOUSEBUTTONDOWN and
                        self._restart_btn and
                        self._restart_btn.collidepoint(event.pos)):
                    self.state = "menu"

    def _handle_play_input(self, event: pygame.event.Event):
        bx, by = int(self.ball.x), int(self.ball.y)

        if (event.type == pygame.MOUSEBUTTONDOWN
                and not self.ball.in_flight
                and not self.waiting_reset):
            if math.hypot(event.pos[0] - bx, event.pos[1] - by) <= BALL_R + 22:
                self.dragging   = True
                self.drag_start = event.pos
                self.drag_cur   = event.pos

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.drag_cur = event.pos

        elif event.type == pygame.MOUSEBUTTONUP and self.dragging:
            self.dragging = False
            self._fire_shot()

    def _fire_shot(self):
        if self.shots >= MAX_SHOTS:
            return
        sx, sy  = self.drag_start
        ex, ey  = self.drag_cur
        dx, dy  = sx - ex, sy - ey
        dist    = math.hypot(dx, dy)
        if dist < 12:
            return

        # atan2(-dy, dx): convert screen-y to maths-y
        angle = math.degrees(math.atan2(-dy, dx))
        power = min(dist / MAX_DRAG, 1.0)
        speed = MIN_POWER + power * (MAX_POWER - MIN_POWER)

        self.ball.shoot(angle, speed, wind=self.wind)
        self.shots      += 1
        self.scored_shot = False

        # Change wind for the NEXT shot (current shot already in the air)
        self.wind = self._new_wind()

    # ─── Update ───────────────────────────────────────

    def update(self, dt: float):
        if self.state != "play":
            return

        self.hoop.update(dt)

        if self.ball.in_flight:
            prev_y = self.ball.y
            self.ball.update(dt)

            if not self.scored_shot and self.hoop.check_score(self.ball, prev_y):
                self._on_score()

            if self.hoop.check_rim_collision(self.ball):
                self.sounds.play("bounce")

            if self.hoop.check_backboard_collision(self.ball):
                self.sounds.play("bounce")

            if self.ball.out_of_bounds:
                if not self.scored_shot:
                    self.combo = 0
                    self.sounds.play("miss")
                self.ball.in_flight = False
                self.waiting_reset  = True
                self.reset_timer    = 1.2

        if self.waiting_reset:
            self.reset_timer -= dt
            if self.reset_timer <= 0:
                self.waiting_reset = False
                self.ball.reset()
                if self.shots >= MAX_SHOTS:
                    self._end_game()

        for lst in (self.particles, self.floats):
            for obj in lst[:]:
                obj.update(dt)
                if obj.life <= 0:
                    lst.remove(obj)

    def _on_score(self):
        self.scored_shot = True
        self.combo      += 1
        pts              = 2 if self.combo >= 3 else 1
        self.score      += pts
        self.hoop.net_shake = 1.0
        self.sounds.play("swish")

        colours = [C_ORANGE, C_COMBO, C_WHITE, (255, 80, 80), (80, 200, 255)]
        for _ in range(38):
            self.particles.append(
                Particle(self.hoop.x, self.hoop.y, random.choice(colours)))

        label = (f"+{pts}  COMBO  x{self.combo}!" if self.combo >= 3 else f"+{pts}")
        self.floats.append(
            FloatingText(label, self.hoop.x, self.hoop.y - 55,
                         C_COMBO if self.combo >= 3 else C_WHITE,
                         size=40 if self.combo >= 3 else 34))

        self.ball.vx *= 0.25
        self.ball.vy  = max(self.ball.vy, 60)
        self.waiting_reset = True
        self.reset_timer   = 1.8

    def _end_game(self):
        """Called when all shots are used. Save best score and switch state."""
        if self.score > self.best_score:
            self.best_score = self.score
            self.new_best   = True
            save_best_score(self.best_score)
        self.state = "gameover"

    # ─── Draw ─────────────────────────────────────────

    def draw(self):
        if self.state == "menu":
            self._diff_btns = draw_menu_screen(
                self.screen, self.best_score,
                self.f_title, self.f_md, self.f_sm,
                self.fullscreen)

        elif self.state in ("play", "gameover"):
            # ── Background + floor ──
            self.screen.blit(self._arena_bg, (0, 0))
            self.screen.blit(self._floor_surf, (0, FLOOR_Y))

            # ── Court markings on floor ──
            # Three-point arc visible on floor
            pygame.draw.arc(self.screen, (155, 96, 38),
                            pygame.Rect(BALL_X0 - 85, FLOOR_Y - 310, 430, 390),
                            math.radians(12), math.radians(168), 2)

            self.hoop.draw(self.screen)

            for p in self.particles:
                p.draw(self.screen)

            self.ball.draw(self.screen)

            # ── Aim overlay ──
            if self.dragging and not self.ball.in_flight:
                sx, sy = self.drag_start
                ex, ey = self.drag_cur
                dist   = math.hypot(sx - ex, sy - ey)
                power  = min(dist / MAX_DRAG, 1.0)
                draw_aim_arrow(self.screen, (sx, sy), (ex, ey), power)
                draw_power_bar(self.screen, self.ball.x, self.ball.y, power)

            # ── HUD ──
            draw_hud(self.screen, self.score, self.shots, self.combo,
                     self.difficulty, self.wind, self.best_score,
                     self.f_lg, self.f_sm)

            for ft in self.floats:
                ft.draw(self.screen)

            # Shots remaining
            left = MAX_SHOTS - self.shots
            rt   = self.f_sm.render(f"Shots remaining: {left}", True, C_WHITE)
            self.screen.blit(rt, (SCREEN_W - rt.get_width() - 14, SCREEN_H - 30))

            # Hint / wind direction banner
            if not self.ball.in_flight and not self.waiting_reset and not self.dragging:
                hint = self.f_sm.render("Click + drag ball to shoot", True, (160, 160, 160))
                self.screen.blit(hint,
                                 (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 30))

            if abs(self.wind) > 5:
                wt = self.f_sm.render(
                    "WIND  >>>" if self.wind > 0 else "<<<  WIND",
                    True, C_WIND_C)
                self.screen.blit(wt, (SCREEN_W // 2 - wt.get_width() // 2, 46))

            if self.state == "gameover":
                self._restart_btn = draw_game_over_screen(
                    self.screen, self.score, self.shots,
                    self.best_score, self.new_best,
                    self.f_title, self.f_md, self.f_sm)

        pygame.display.flip()

    # ─── Loop ─────────────────────────────────────────

    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(dt)
            self.draw()

    @staticmethod
    def _quit():
        pygame.quit()
        sys.exit()


# ─────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    Game().run()
