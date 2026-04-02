"""
Basketball Fun Game  v2.1
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
# CONSTANTS
# ─────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 960, 620
FPS        = 60
GRAVITY    = 850.0
BALL_R     = 18
RIM_R      = 7
RIM_HALF   = 32
NET_H      = 42
MAX_SHOTS  = 15
MAX_DRAG   = 220.0
MIN_POWER  = 280.0
MAX_POWER  = 1200.0
ELASTICITY = 0.45

FLOOR_Y  = SCREEN_H - 80
BALL_X0  = 130
BALL_Y0  = FLOOR_Y - BALL_R - 1
HOOP_X0  = 740
HOOP_Y0  = 260
BOARD_X  = 840

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "best_score.json")

# ── Difficulty presets ───────────────────────────────
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
C_ORANGE  = (228, 100, 18)
C_DK_ORG  = (140,  42,  0)
C_SEAM    = ( 68,  14,  0)   # near-black seam lines on ball
C_RIM     = (200,  38,  8)
C_RIM_HI  = (248,  88, 48)
C_BOARD   = (192, 210, 230)
C_BOARD_E = (130, 148, 168)
C_NET     = (200, 200, 200)
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
# PRECOMPUTED SURFACES
# ─────────────────────────────────────────────────────

def _build_arena_bg() -> pygame.Surface:
    """
    Indoor NBA-style arena:
    - Deep gradient background (ceiling → court level)
    - Three overhead spotlight cones
    - Animated-style crowd silhouettes in tiered rows
    - Hanging championship banners
    - Scoreboard structure on the right wall
    """
    surf = pygame.Surface((SCREEN_W, FLOOR_Y))

    # ── Base gradient: near-black ceiling → deep navy at floor ──
    for y in range(FLOOR_Y):
        t = y / FLOOR_Y
        r = int(5  + 20 * t)
        g = int(6  + 16 * t)
        b = int(18 + 32 * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (SCREEN_W, y))

    # ── Overhead spotlight cones (3 lights) ──
    light = pygame.Surface((SCREEN_W, FLOOR_Y), pygame.SRCALPHA)
    for lx in (SCREEN_W // 5, SCREEN_W // 2, 4 * SCREEN_W // 5):
        for i in range(1, 45):
            t     = i / 45
            alpha = int(18 * (1 - t) ** 1.8)
            w     = int(20 + 200 * t)
            hc    = int(FLOOR_Y * t)
            pygame.draw.ellipse(light, (255, 248, 220, alpha),
                                pygame.Rect(lx - w // 2, 8, w, hc))
    surf.blit(light, (0, 0))

    # ── Ceiling structural elements ──
    pygame.draw.rect(surf, (4, 4, 14), pygame.Rect(0, 0, SCREEN_W, 12))
    for bx in range(0, SCREEN_W, 120):
        pygame.draw.rect(surf, (8, 8, 22), pygame.Rect(bx, 0, 6, 30))

    # ── Championship banners hanging from ceiling ──
    rng_b = random.Random(77)
    banner_colors = [
        (180, 20, 20), (20, 60, 180), (180, 150, 10),
        (20, 140, 40), (140, 20, 140), (180, 90, 10),
    ]
    for bx in range(60, SCREEN_W - 60, 115):
        col  = rng_b.choice(banner_colors)
        bw   = rng_b.randint(22, 32)
        bh   = rng_b.randint(38, 52)
        rect = pygame.Rect(bx - bw // 2, 0, bw, bh)
        pygame.draw.rect(surf, col, rect)
        pygame.draw.rect(surf, (255, 215, 0), rect, 1)
        # Year text stub (tiny yellow lines)
        for yi in range(3):
            pygame.draw.line(surf, (255, 215, 0),
                             (bx - bw//2 + 4, 10 + yi * 9),
                             (bx + bw//2 - 4, 10 + yi * 9), 1)

    # ── Tiered crowd rows (4 rows, back to front = small to large) ──
    rng = random.Random(99)
    skin_tones = [(210, 170, 130), (190, 150, 110), (160, 110, 75), (110, 68, 42)]
    jersey_cols = [
        (200, 25,  25), (25,  70, 200), (220, 190, 30),
        (240, 240, 240), (25, 160, 50), (170, 35, 210),
        (220, 110, 25), (30,  30,  30),
    ]
    for row_y, body_h, head_r, gap in (
        (20,  14,  4, 14),
        (52,  18,  5, 17),
        (96,  23,  6, 21),
        (152, 30,  8, 27),
    ):
        x = rng.randint(0, gap)
        while x < SCREEN_W:
            jcol  = rng.choice(jersey_cols)
            scol  = rng.choice(skin_tones)
            bw    = max(8, body_h - 2)
            # Body
            pygame.draw.rect(surf, jcol,
                             pygame.Rect(x - bw//2, row_y, bw, body_h))
            # Head
            pygame.draw.circle(surf, scol, (x, row_y - head_r + 1), head_r)
            # Raised arm (random chance)
            if rng.random() < 0.25:
                arm_x = x + rng.choice((-1, 1)) * (bw // 2 + 4)
                arm_y = row_y - head_r - 5
                pygame.draw.line(surf, jcol, (x, row_y + 2),
                                 (arm_x, arm_y), max(1, bw // 5))
            x += gap + rng.randint(-3, 5)

    # ── Scoreboard (right wall) ──
    sb_x, sb_y, sb_w, sb_h = 820, 165, 115, 65
    pygame.draw.rect(surf, (15, 15, 15),  pygame.Rect(sb_x, sb_y, sb_w, sb_h))
    pygame.draw.rect(surf, (60, 60, 60),  pygame.Rect(sb_x, sb_y, sb_w, sb_h), 2)
    # LED-style text stubs
    for row in range(3):
        pygame.draw.rect(surf, (180, 50, 0),
                         pygame.Rect(sb_x + 6, sb_y + 8 + row * 17, sb_w - 12, 10))

    return surf


def _build_floor_surf() -> pygame.Surface:
    """
    Hardwood floor: vertical plank strips with grain, court markings.
    Uses a fixed-seed RNG so the pattern is identical every run.
    """
    surf = pygame.Surface((SCREEN_W, 80))
    rng  = random.Random(42)

    plank_palette = [
        (175, 114, 48), (166, 108, 44), (182, 121, 52),
        (170, 111, 46), (178, 118, 50), (163, 106, 42),
        (176, 115, 48), (171, 111, 45),
    ]

    # Vertical plank strips
    x, pi = 0, 0
    while x < SCREEN_W:
        w   = rng.randint(26, 38)
        col = plank_palette[pi % len(plank_palette)]
        pygame.draw.rect(surf, col, pygame.Rect(x, 0, w, 80))

        # Wood-grain lines (lengthwise)
        gx = x + rng.randint(4, 10)
        while gx < x + w - 4:
            gc = (max(0, col[0] - rng.randint(8, 18)),
                  max(0, col[1] - rng.randint(6, 14)),
                  max(0, col[2] - rng.randint(4, 10)))
            pygame.draw.line(surf, gc, (gx, 0),
                             (gx + rng.randint(-6, 6), 80), 1)
            gx += rng.randint(5, 12)

        # Plank-edge shadow (right side darker line)
        ec = (max(0, col[0] - 22), max(0, col[1] - 17), max(0, col[2] - 12))
        pygame.draw.line(surf, ec, (x + w - 1, 0), (x + w - 1, 80), 1)
        x  += w
        pi += 1

    # ── Court markings ──
    mark  = (200, 138, 68)     # painted-line color
    mark2 = (185, 122, 54)     # slightly darker variant

    # Floor-wall boundary
    pygame.draw.line(surf, (128, 80, 28), (0, 0), (SCREEN_W, 0), 3)

    # Free-throw lane (key) box
    lane_l = BALL_X0 + 10
    lane_r = lane_l + 170
    pygame.draw.rect(surf, mark, pygame.Rect(lane_l, 0, 170, 80), 2)

    # Free-throw semicircle at top of key (visible as a partial ellipse at floor edge)
    pygame.draw.ellipse(surf, mark,
                        pygame.Rect(lane_l + 50, -28, 70, 56), 2)

    # Three-point line side extensions
    pygame.draw.line(surf, mark2, (lane_l - 40,  0), (lane_l - 40, 22), 2)
    pygame.draw.line(surf, mark2, (lane_r + 80,  0), (lane_r + 80, 22), 2)

    # Baseline
    pygame.draw.line(surf, mark2, (0, 78), (SCREEN_W, 78), 2)

    return surf


def _build_ball_template(radius: int) -> tuple[pygame.Surface, int]:
    """
    Pre-render a sphere-shaded basketball surface without seam lines.
    Uses layered semi-transparent circles to simulate diffuse + specular lighting.
    Returns (surface, centre_offset).
    """
    pad  = 8
    size = radius * 2 + pad * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2

    # ── Drop shadow (soft ellipse below the ball) ──
    sh = pygame.Surface((size + 10, 16), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 50),
                        pygame.Rect(0, 0, size + 10, 16))
    surf.blit(sh, (cx - size // 2 - 5, cy + radius - 4))

    # ── Base colour: warm dark orange (shadow side already in it) ──
    pygame.draw.circle(surf, (195, 78, 12), (cx, cy), radius)

    # ── Mid-tone layer: slightly lighter, offset top-left ──
    ml = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(ml, (228, 100, 18, 210),
                       (cx - radius // 6, cy - radius // 6),
                       int(radius * 0.88))
    surf.blit(ml, (0, 0))

    # ── Bright area: wide diffuse light from upper-left ──
    bl = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(bl, (248, 148, 52, 130),
                       (cx - radius // 4, cy - radius // 4),
                       int(radius * 0.65))
    surf.blit(bl, (0, 0))

    # ── Dark vignette rim: subtle darkening at edge for roundness ──
    vg = pygame.Surface((size, size), pygame.SRCALPHA)
    for ri in range(radius, radius - 5, -1):
        alpha = int(55 * (radius - ri + 1) / 5)
        pygame.draw.circle(vg, (0, 0, 0, alpha), (cx, cy), ri, 2)
    surf.blit(vg, (0, 0))

    # ── Specular highlight: small bright oval top-left ──
    spec = pygame.Surface((size, size), pygame.SRCALPHA)
    sr   = max(4, radius // 3)
    for ri in range(sr, 0, -1):
        t = 1 - ri / sr
        pygame.draw.circle(spec, (255, 250, 235, int(145 * t ** 1.4)),
                           (cx - radius // 3, cy - radius // 3), ri)
    surf.blit(spec, (0, 0))

    # ── Hard outer edge ──
    pygame.draw.circle(surf, (130, 38, 0), (cx, cy), radius, 2)

    return surf, cx


# ─────────────────────────────────────────────────────
# SOUND
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
    """Physics, sphere rendering with authentic seam lines, and motion trail."""

    TRAIL_LEN  = 26
    SEAM_STEPS = 30       # line-segment count per seam curve
    SEAM_AMP   = 0.32     # amplitude of the S-wave seam curves (normalised)

    def __init__(self, template: pygame.Surface, tmpl_off: int):
        self._tmpl     = template
        self._tmpl_off = tmpl_off
        self.reset()

    def reset(self):
        self.x         = float(BALL_X0)
        self.y         = float(BALL_Y0)
        self.vx        = 0.0
        self.vy        = 0.0
        self.in_flight = False
        self.spin      = 0.0        # degrees, cumulative rotation
        self.spin_rate = 0.0
        self.trail: list[tuple[float, float]] = []

    def shoot(self, angle_deg: float, speed: float, wind: float = 0.0):
        rad        = math.radians(angle_deg)
        self.vx    = speed * math.cos(rad) + wind
        self.vy    = -speed * math.sin(rad)
        self.in_flight = True
        self.spin_rate = speed * 0.042

    def update(self, dt: float):
        if not self.in_flight:
            return
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.TRAIL_LEN:
            self.trail.pop(0)
        self.vy   += GRAVITY * dt
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.spin += self.spin_rate

    @property
    def out_of_bounds(self) -> bool:
        return self.y > SCREEN_H + 60 or self.x < -80 or self.x > SCREEN_W + 80

    # ── Seam drawing ─────────────────────────────────

    def _seam_points(self, cx: int, cy: int, spin_rad: float,
                     seam_id: int) -> list[tuple[int, int]]:
        """
        Return screen-space points for one of the three basketball seam curves.

        Each seam is a great-circle arc expressed as an S-curve in normalised
        ball-local coordinates, then rotated by the current spin angle.

          Seam 0: S-wave going left → right   (horizontal seam)
          Seam 1: S-wave going top  → bottom, curving left
          Seam 2: S-wave going top  → bottom, curving right

        The S-wave formula:  deviation = SEAM_AMP * sin(π * t)  where t ∈ [-1, 1]
        This creates a smooth curve that passes through the "poles" at the ends.
        """
        r     = BALL_R - 2
        cos_s = math.cos(spin_rad)
        sin_s = math.sin(spin_rad)
        pts   = []

        for i in range(self.SEAM_STEPS + 1):
            t = -1.0 + i * (2.0 / self.SEAM_STEPS)      # t ∈ [-1 .. 1]
            dev = self.SEAM_AMP * math.sin(math.pi * t)  # S-wave deviation

            if seam_id == 0:        # horizontal: runs L→R, deviates in Y
                lx, ly = t, dev
            elif seam_id == 1:      # left-curving vertical: runs T→B, deviates left in X
                lx, ly = -dev, t
            else:                   # right-curving vertical: mirror of seam 1
                lx, ly = dev, t

            # Rotate by spin and scale to ball radius
            sx = int(cx + (lx * cos_s - ly * sin_s) * r)
            sy = int(cy + (lx * sin_s + ly * cos_s) * r)
            pts.append((sx, sy))

        return pts

    def draw(self, surf: pygame.Surface):
        cx, cy = int(self.x), int(self.y)

        # ── Motion trail ──
        n = len(self.trail)
        for i, (tx, ty) in enumerate(self.trail):
            ratio = (i + 1) / (n + 1)
            alpha = int(150 * ratio)
            r_tr  = max(2, int(BALL_R * 0.48 * ratio))
            ts    = pygame.Surface((r_tr * 2, r_tr * 2), pygame.SRCALPHA)
            pygame.draw.circle(ts, (228, 100, 18, alpha), (r_tr, r_tr), r_tr)
            surf.blit(ts, (int(tx) - r_tr, int(ty) - r_tr))

        # ── Sphere base (precomputed gradient + shading) ──
        off = self._tmpl_off
        surf.blit(self._tmpl, (cx - off, cy - off))

        # ── Basketball seam lines ──────────────────────────────────────────
        #
        # Three S-curved seams that rotate with the ball's spin.
        # Seam 0: wavy horizontal line (left-right)
        # Seam 1: left-curving vertical arc (top-bottom, bending left)
        # Seam 2: right-curving vertical arc (top-bottom, bending right)
        #
        # The curves are clipped to the ball's bounding rectangle so they
        # never visibly cross outside the ball circle.
        # ─────────────────────────────────────────────────────────────────
        spin_rad = math.radians(self.spin)

        old_clip = surf.get_clip()
        surf.set_clip(pygame.Rect(cx - BALL_R, cy - BALL_R,
                                  BALL_R * 2, BALL_R * 2))

        for seam_id in range(3):
            pts = self._seam_points(cx, cy, spin_rad, seam_id)
            if len(pts) >= 2:
                pygame.draw.lines(surf, C_SEAM, False, pts, 2)

        surf.set_clip(old_clip)

        # ── Outer edge (re-drawn on top to crisp up the silhouette) ──
        pygame.draw.circle(surf, (120, 34, 0), (cx, cy), BALL_R, 2)


# ─────────────────────────────────────────────────────
# HOOP
# ─────────────────────────────────────────────────────
class Hoop:
    """Backboard, rim (3-D shaded), net, and support pole."""

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

        # ── Support pole (floor to backboard) ──
        pole_x = bx + 4
        # Pole body
        pygame.draw.line(surf, (55, 55, 55),
                         (pole_x - 4, ry + 40), (pole_x - 4, FLOOR_Y), 10)
        pygame.draw.line(surf, (85, 85, 85),
                         (pole_x - 7, ry + 40), (pole_x - 7, FLOOR_Y), 2)
        # Pole base pad
        pygame.draw.rect(surf, (45, 45, 45),
                         pygame.Rect(pole_x - 16, FLOOR_Y - 6, 26, 6))

        # ── Backboard ──
        board = pygame.Rect(bx - 14, ry - 78, 16, 114)

        # Frosted-glass effect: fill with translucent layers
        glass = pygame.Surface((16, 114), pygame.SRCALPHA)
        glass.fill((195, 215, 235, 210))
        # Thin reflective streak
        pygame.draw.line(glass, (240, 252, 255, 120), (3, 4), (3, 110), 2)
        surf.blit(glass, (bx - 14, ry - 78))

        pygame.draw.rect(surf, C_BOARD_E, board, 2)
        # Orange target box
        pygame.draw.rect(surf, C_RIM,
                         pygame.Rect(bx - 12, ry - 40, 11, 34), 2)

        # ── Support arm (rim to backboard) ──
        pygame.draw.line(surf, (70, 70, 70),  (rx + 2, ry - 3), (bx - 14, ry - 3), 7)
        pygame.draw.line(surf, (100, 100, 100), (rx + 2, ry - 5), (bx - 14, ry - 5), 2)

        # ── Rim: 3-D shaded tube ──
        # Underside shadow
        pygame.draw.line(surf, (70, 10, 0),
                         (lx - RIM_R, ry + 5), (rx + RIM_R, ry + 5), 4)
        # Main rim bar
        pygame.draw.line(surf, C_RIM, (lx, ry), (rx, ry), RIM_R * 2)
        # Top highlight
        pygame.draw.line(surf, C_RIM_HI, (lx + 2, ry - 3), (rx - 2, ry - 3), 2)

        # Rim-end knobs
        for kx, ky in [self.left_rim, self.right_rim]:
            pygame.draw.circle(surf, (160, 28, 4),   (int(kx), int(ky)), RIM_R + 1)
            pygame.draw.circle(surf, C_RIM,           (int(kx), int(ky)), RIM_R)
            pygame.draw.circle(surf, C_RIM_HI,        (int(kx), int(ky) - 2), RIM_R // 2)

        # ── Net ──
        t_now = pygame.time.get_ticks() * 0.001
        shake = math.sin(t_now * 14) * self.net_shake * 5

        strands = 12
        for i in range(strands + 1):
            frac  = i / strands
            top_x = lx + frac * (rx - lx)
            bot_x = mid + (frac - 0.5) * 14 + shake * (frac - 0.5) * 1.2
            bot_y = ry + NET_H + self.net_shake * 7 * math.sin(frac * math.pi)
            pygame.draw.line(surf, C_NET,
                             (int(top_x), ry), (int(bot_x), int(bot_y)), 1)

        for row in range(1, 5):
            t     = row / 5
            y_row = ry + t * NET_H + self.net_shake * 5 * math.sin(t * math.pi + shake)
            xl    = lx + t * (mid - lx) + t * shake * 0.3
            xr    = rx + t * (mid - rx) - t * shake * 0.3
            pygame.draw.line(surf, C_NET,
                             (int(xl), int(y_row)), (int(xr), int(y_row)), 1)

    # ── Collision detection ──────────────────────────

    def check_score(self, ball: "Ball", prev_y: float) -> bool:
        if ball.vy <= 0:
            return False
        if not (prev_y < self.y <= ball.y):
            return False
        return abs(ball.x - self.x) <= RIM_HALF - BALL_R * 0.55

    def check_rim_collision(self, ball: "Ball") -> bool:
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
        a            = random.uniform(0, math.tau)
        sp           = random.uniform(90, 265)
        self.x, self.y = x, y
        self.vx, self.vy = sp * math.cos(a), sp * math.sin(a)
        self.color   = color
        self.life    = random.uniform(0.4, 0.85)
        self.max_l   = self.life
        self.r       = random.randint(3, 8)

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
        alpha    = int(255 * min(1.0, self.life / self.max_life * 2))
        rendered = self.font.render(self.text, True, self.color)
        rendered.set_alpha(alpha)
        surf.blit(rendered, (int(self.x) - rendered.get_width() // 2, int(self.y)))


# ─────────────────────────────────────────────────────
# HUD & SCREEN HELPERS
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
    bx, by = int(cx) - 32, int(cy) + 27
    pygame.draw.rect(surf, (30, 30, 30),   pygame.Rect(bx - 1,  by - 1, 66, 12))
    pygame.draw.rect(surf, (55, 55, 55),   pygame.Rect(bx,      by,     64, 10))
    fill_col = (int(50 + 200 * power), int(200 - 150 * power), 30)
    pygame.draw.rect(surf, fill_col,        pygame.Rect(bx,      by,     int(64 * power), 10))
    pygame.draw.rect(surf, C_WHITE,         pygame.Rect(bx - 1,  by - 1, 66, 12), 1)


def draw_hud(surf: pygame.Surface, score: int, shots: int, combo: int,
             difficulty: str, wind: float, best: int,
             font_lg: pygame.font.Font, font_sm: pygame.font.Font):
    # Panel background with subtle gradient
    panel = pygame.Surface((248, 158), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 0))
    for py in range(158):
        alpha = int(175 - py * 0.4)
        pygame.draw.line(panel, (8, 8, 20, alpha), (0, py), (248, py))
    pygame.draw.rect(panel, (80, 80, 120, 80), pygame.Rect(0, 0, 248, 158), 1)
    surf.blit(panel, (10, 10))

    acc      = (score * 100 // shots) if shots else 0
    diff_col = DIFFICULTIES[difficulty]["color"]
    diff_lbl = DIFFICULTIES[difficulty]["label"]
    rows = [
        (f"Score:      {score}",             font_lg, C_WHITE),
        (f"Shots:      {shots}/{MAX_SHOTS}", font_sm, (210, 210, 210)),
        (f"Accuracy:   {acc}%",              font_sm, (210, 210, 210)),
        (f"Best:       {best}",              font_sm, C_COMBO),
        (f"Difficulty: {diff_lbl}",          font_sm, diff_col),
    ]
    for i, (text, font, col) in enumerate(rows):
        surf.blit(font.render(text, True, col), (20, 16 + i * 27))

    # Wind indicator
    if abs(wind) > 1:
        wy = 173
        surf.blit(font_sm.render("Wind:", True, C_WIND_C), (20, wy))
        bw  = min(int(abs(wind) * 0.5), 90)
        bx2 = 72 if wind > 0 else 72 - bw
        pygame.draw.rect(surf, C_WIND_C, pygame.Rect(bx2, wy + 6, bw, 10))
        arr = ">>>" if wind > 0 else "<<<"
        ax2 = 72 + bw + 4 if wind > 0 else 72 - bw - 30
        surf.blit(font_sm.render(arr, True, C_WIND_C), (ax2, wy))

    # Combo banner
    if combo >= 2:
        ct = font_lg.render(f"COMBO  x{combo}!", True, C_COMBO)
        surf.blit(ct, (SCREEN_W // 2 - ct.get_width() // 2, 12))


def draw_menu_screen(surf: pygame.Surface, best_score: int,
                     font_title: pygame.font.Font,
                     font_md: pygame.font.Font,
                     font_sm: pygame.font.Font,
                     fullscreen: bool) -> dict:
    """Draw title + difficulty buttons. Returns button rect dict."""
    # Gradient background (dark arena feel)
    for y in range(SCREEN_H):
        t = y / SCREEN_H
        r = int(5  + 12 * t)
        g = int(6  + 10 * t)
        b = int(18 + 22 * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (SCREEN_W, y))

    # Subtle court glow at bottom
    glow = pygame.Surface((SCREEN_W, 200), pygame.SRCALPHA)
    for gy in range(200):
        alpha = int(28 * (1 - gy / 200))
        pygame.draw.line(glow, (175, 115, 48, alpha), (0, gy), (SCREEN_W, gy))
    surf.blit(glow, (0, SCREEN_H - 200))

    # Title with shadow
    shadow = font_title.render("BASKETBALL  FUN", True, (80, 30, 0))
    surf.blit(shadow, (SCREEN_W // 2 - shadow.get_width() // 2 + 3, 68))
    title = font_title.render("BASKETBALL  FUN", True, C_ORANGE)
    surf.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 65))

    sub = font_md.render("Physics Shooting Game", True, (170, 170, 170))
    surf.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 142))

    # Best score
    if best_score > 0:
        bs = font_md.render(f"Best Score:  {best_score}", True, C_COMBO)
        surf.blit(bs, (SCREEN_W // 2 - bs.get_width() // 2, 192))

    # Section label
    sd = font_md.render("SELECT  DIFFICULTY", True, C_WHITE)
    surf.blit(sd, (SCREEN_W // 2 - sd.get_width() // 2, 248))

    # Difficulty buttons
    btn_w, btn_h = 210, 88
    gap          = 30
    total_w      = btn_w * 3 + gap * 2
    start_x      = SCREEN_W // 2 - total_w // 2
    btn_y        = 296

    btns: dict = {}
    mx, my = pygame.mouse.get_pos()

    for i, key in enumerate(DIFF_ORDER):
        cfg   = DIFFICULTIES[key]
        bx    = start_x + i * (btn_w + gap)
        rect  = pygame.Rect(bx, btn_y, btn_w, btn_h)
        btns[key] = rect
        hover = rect.collidepoint(mx, my)
        base_c = cfg["color"]
        fill_c = tuple(min(255, c + 45) for c in base_c) if hover else base_c

        # Button shadow
        shadow_r = pygame.Rect(bx + 3, btn_y + 4, btn_w, btn_h)
        sh_surf = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        sh_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(sh_surf, (0, 0, 0, 80), pygame.Rect(0, 0, btn_w, btn_h),
                         border_radius=14)
        surf.blit(sh_surf, (bx + 3, btn_y + 4))

        pygame.draw.rect(surf, fill_c,  rect, border_radius=14)
        pygame.draw.rect(surf, C_WHITE, rect, 2, border_radius=14)

        lbl = font_md.render(cfg["label"], True, C_BLACK if hover else C_WHITE)
        surf.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                        rect.centery - lbl.get_height() // 2 - 8))

        desc = font_sm.render(cfg["desc"], True,
                              (40, 40, 40) if hover else (200, 200, 200))
        surf.blit(desc, (rect.centerx - desc.get_width() // 2,
                         rect.centery + 14))

    # Instructions
    lines = [
        ("HOW  TO  PLAY",                                    font_md, C_ORANGE),
        ("Click + drag FROM the ball to aim  (slingshot)",   font_sm, C_WHITE),
        ("Longer drag  =  more power  ·  Release to shoot",  font_sm, C_WHITE),
        ("3 consecutive baskets  =  COMBO  (+2 pts each)",   font_sm, C_COMBO),
        ("R = restart     ESC = quit     F11 = fullscreen",  font_sm, (150, 150, 150)),
    ]
    for i, (text, font, col) in enumerate(lines):
        t = font.render(text, True, col)
        surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 418 + i * 32))

    fs_text = "[ F11 ]  Fullscreen: ON" if fullscreen else "[ F11 ]  Fullscreen: OFF"
    fs_surf = font_sm.render(fs_text, True,
                             (100, 200, 100) if fullscreen else (140, 140, 140))
    surf.blit(fs_surf, (SCREEN_W - fs_surf.get_width() - 14, SCREEN_H - 26))

    return btns


def draw_game_over_screen(surf: pygame.Surface, score: int, shots: int,
                          best: int, new_best: bool,
                          font_title: pygame.font.Font,
                          font_md: pygame.font.Font,
                          font_sm: pygame.font.Font) -> pygame.Rect:
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 195))
    surf.blit(overlay, (0, 0))

    go = font_title.render("GAME  OVER", True, (218, 42, 42))
    surf.blit(go, (SCREEN_W // 2 - go.get_width() // 2, 100))

    if new_best:
        nb = font_md.render("NEW  BEST  SCORE!", True, C_COMBO)
        surf.blit(nb, (SCREEN_W // 2 - nb.get_width() // 2, 172))

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
        surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 220 + i * 52))

    btn = pygame.Rect(SCREEN_W // 2 - 125, 508, 250, 58)
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

    Key design decisions
    ────────────────────
    • Hoop movement and wind are active from game START (not after first shot).
    • Wind re-randomises between shots within the chosen difficulty range.
    • F11 toggles fullscreen via pygame.SCALED (internal res stays fixed).
    • Best score is persisted to best_score.json.
    """

    def __init__(self):
        pygame.init()
        self._fs_flags  = pygame.SCALED
        self.screen     = pygame.display.set_mode(
            (SCREEN_W, SCREEN_H), self._fs_flags)
        pygame.display.set_caption("Basketball Fun Game")
        self.clock      = pygame.time.Clock()
        self.fullscreen = False

        self.f_title = pygame.font.SysFont("Arial", 62, bold=True)
        self.f_lg    = pygame.font.SysFont("Arial", 26, bold=True)
        self.f_md    = pygame.font.SysFont("Arial", 36, bold=True)
        self.f_sm    = pygame.font.SysFont("Arial", 20)

        # Build precomputed surfaces AFTER pygame.init()
        self._arena_bg   = _build_arena_bg()
        self._floor_surf = _build_floor_surf()
        self._ball_tmpl, self._ball_tmpl_off = _build_ball_template(BALL_R)

        self.sounds     = SoundManager()
        self.best_score = load_best_score()
        self.state      = "menu"
        self.difficulty = "medium"

        self._diff_btns: dict   = {}
        self._restart_btn       = None

        self._init_game("medium")

    # ── Display ───────────────────────────────────────

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = (pygame.FULLSCREEN | pygame.SCALED
                 if self.fullscreen else self._fs_flags)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)

    # ── Game reset ────────────────────────────────────

    def _init_game(self, difficulty: str):
        self.difficulty    = difficulty
        self.ball          = Ball(self._ball_tmpl, self._ball_tmpl_off)
        self.hoop          = Hoop()
        self.score         = 0
        self.shots         = 0
        self.combo         = 0
        self.new_best      = False
        self.particles: list[Particle]     = []
        self.floats:    list[FloatingText] = []
        self.dragging      = False
        self.drag_start    = (0, 0)
        self.drag_cur      = (0, 0)
        self.waiting_reset = False
        self.reset_timer   = 0.0
        self.scored_shot   = False
        # Apply difficulty immediately so hoop moves and wind blows before shot 1
        self._apply_difficulty()

    def _apply_difficulty(self):
        cfg = DIFFICULTIES[self.difficulty]
        self.hoop.set_moving(cfg["hoop_speed"])
        self.wind = self._new_wind()

    def _new_wind(self) -> float:
        wm = DIFFICULTIES[self.difficulty]["wind_max"]
        return random.uniform(-wm, wm) if wm else 0.0

    # ── Input ─────────────────────────────────────────

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
        sx, sy = self.drag_start
        ex, ey = self.drag_cur
        dx, dy = sx - ex, sy - ey
        dist   = math.hypot(dx, dy)
        if dist < 12:
            return
        angle = math.degrees(math.atan2(-dy, dx))
        power = min(dist / MAX_DRAG, 1.0)
        speed = MIN_POWER + power * (MAX_POWER - MIN_POWER)
        self.ball.shoot(angle, speed, wind=self.wind)
        self.shots       += 1
        self.scored_shot  = False
        # Change wind for the NEXT shot after this one lands
        self.wind = self._new_wind()

    # ── Update ────────────────────────────────────────

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
        self.scored_shot    = True
        self.combo         += 1
        pts                 = 2 if self.combo >= 3 else 1
        self.score         += pts
        self.hoop.net_shake = 1.0
        self.sounds.play("swish")

        colours = [C_ORANGE, C_COMBO, C_WHITE, (255, 80, 80), (80, 200, 255)]
        for _ in range(40):
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
        if self.score > self.best_score:
            self.best_score = self.score
            self.new_best   = True
            save_best_score(self.best_score)
        self.state = "gameover"

    # ── Draw ──────────────────────────────────────────

    def draw(self):
        if self.state == "menu":
            self._diff_btns = draw_menu_screen(
                self.screen, self.best_score,
                self.f_title, self.f_md, self.f_sm,
                self.fullscreen)

        elif self.state in ("play", "gameover"):
            # Background arena + hardwood floor
            self.screen.blit(self._arena_bg,   (0, 0))
            self.screen.blit(self._floor_surf, (0, FLOOR_Y))

            self.hoop.draw(self.screen)

            for p in self.particles:
                p.draw(self.screen)

            self.ball.draw(self.screen)

            # Aim overlay
            if self.dragging and not self.ball.in_flight:
                sx, sy = self.drag_start
                ex, ey = self.drag_cur
                dist   = math.hypot(sx - ex, sy - ey)
                power  = min(dist / MAX_DRAG, 1.0)
                draw_aim_arrow(self.screen, (sx, sy), (ex, ey), power)
                draw_power_bar(self.screen, self.ball.x, self.ball.y, power)

            draw_hud(self.screen, self.score, self.shots, self.combo,
                     self.difficulty, self.wind, self.best_score,
                     self.f_lg, self.f_sm)

            for ft in self.floats:
                ft.draw(self.screen)

            left = MAX_SHOTS - self.shots
            rt   = self.f_sm.render(f"Shots remaining: {left}", True, C_WHITE)
            self.screen.blit(rt, (SCREEN_W - rt.get_width() - 14, SCREEN_H - 30))

            if not self.ball.in_flight and not self.waiting_reset and not self.dragging:
                hint = self.f_sm.render("Click + drag ball to shoot",
                                        True, (155, 155, 155))
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

    # ── Loop ──────────────────────────────────────────

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
