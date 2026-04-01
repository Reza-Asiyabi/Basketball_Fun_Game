"""
Basketball Fun Game
===================
A physics-based basketball shooting game built with Pygame.

Requirements:
    pip install pygame

Run:
    python basketball_game.py

Controls:
    - Click and drag FROM the ball to aim (slingshot style)
    - Longer drag = more power
    - Release mouse to shoot
    - R = restart   ESC = quit
"""

import pygame
import sys
import math
import random

# ─────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────
SCREEN_W    = 960
SCREEN_H    = 620
FPS         = 60
GRAVITY     = 850.0      # pixels / s²  (tuned for fun arc)
BALL_RADIUS = 18
RIM_RADIUS  = 7          # visual thickness of rim knobs
RIM_HALF    = 32         # half-width of rim opening in pixels
NET_H       = 40         # net height below rim
MAX_SHOTS   = 15         # shots per game
MAX_DRAG    = 220.0      # drag distance (px) that maps to max power
MIN_POWER   = 280.0      # minimum launch speed  (px/s)
MAX_POWER   = 1200.0     # maximum launch speed  (px/s)
ELASTICITY  = 0.45       # energy kept after rim bounce
LEVEL_EVERY = 5          # shots between difficulty increases

# Ball starting position (sits on the floor)
BALL_ORIGIN_X = 130
BALL_ORIGIN_Y = SCREEN_H - 80 - BALL_RADIUS - 2

# Hoop base position
HOOP_BASE_X   = 700
HOOP_BASE_Y   = 260
BACKBOARD_X   = 830      # right-side backboard x

# Colors
C_BG        = (28,  56,  28)
C_FLOOR     = (175, 118, 55)
C_FLOOR_LN  = (155,  95, 35)
C_WHITE     = (255, 255, 255)
C_BLACK     = (  0,   0,   0)
C_ORANGE    = (230, 115, 25)
C_DK_ORANGE = (170,  65,  0)
C_RIM       = (205,  45,  10)
C_BOARD     = (205, 215, 225)
C_BOARD_LN  = (145, 155, 165)
C_NET       = (215, 215, 215)
C_COMBO     = (255, 215,   0)
C_WIND_COL  = ( 90, 170, 255)


# ─────────────────────────────────────────────────────
# SOUND  (procedural – no .wav files needed)
# ─────────────────────────────────────────────────────
class SoundManager:
    """Generate and play simple sound effects using numpy + pygame.mixer."""

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
            pass  # silently run without audio

    @staticmethod
    def _make_swish(sr, np):
        t = np.linspace(0, 0.4, int(sr * 0.4))
        env = np.sin(np.pi * t / 0.4) ** 2
        noise = np.random.uniform(-1, 1, len(t))
        data = (env * noise * 20000).astype(np.int16)
        stereo = np.column_stack([data, data])
        return pygame.sndarray.make_sound(stereo)

    @staticmethod
    def _make_bounce(sr, np):
        t = np.linspace(0, 0.25, int(sr * 0.25))
        env = np.exp(-14 * t)
        freq = 90 - 50 * t / 0.25
        wave = np.sin(2 * np.pi * freq * t)
        data = (env * wave * 22000).astype(np.int16)
        stereo = np.column_stack([data, data])
        return pygame.sndarray.make_sound(stereo)

    @staticmethod
    def _make_miss(sr, np):
        t = np.linspace(0, 0.18, int(sr * 0.18))
        env = np.exp(-10 * t)
        wave = np.sin(2 * np.pi * 180 * t)
        data = (env * wave * 14000).astype(np.int16)
        stereo = np.column_stack([data, data])
        return pygame.sndarray.make_sound(stereo)

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
    """Handles position, velocity, physics, rendering and trail."""

    TRAIL_LEN = 22

    def __init__(self):
        self.reset()

    def reset(self):
        self.x         = float(BALL_ORIGIN_X)
        self.y         = float(BALL_ORIGIN_Y)
        self.vx        = 0.0
        self.vy        = 0.0
        self.in_flight = False
        self.spin      = 0.0   # degrees, for visual seam rotation
        self.spin_rate = 0.0
        self.trail: list[tuple[float, float]] = []

    def shoot(self, angle_deg: float, speed: float, wind: float = 0.0):
        """Launch at angle (degrees, 0=right, 90=up) at given speed (px/s)."""
        rad = math.radians(angle_deg)
        self.vx = speed * math.cos(rad) + wind
        self.vy = -speed * math.sin(rad)   # screen y is inverted
        self.in_flight = True
        self.spin_rate = speed * 0.045

    def update(self, dt: float):
        if not self.in_flight:
            return
        # Append trail point
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.TRAIL_LEN:
            self.trail.pop(0)

        # Projectile motion
        self.vy  += GRAVITY * dt
        self.x   += self.vx * dt
        self.y   += self.vy * dt
        self.spin += self.spin_rate

    @property
    def out_of_bounds(self) -> bool:
        return (self.y > SCREEN_H + 60 or
                self.x < -80 or
                self.x > SCREEN_W + 80)

    def draw(self, surf: pygame.Surface):
        # ── Trail ──
        n = len(self.trail)
        for i, (tx, ty) in enumerate(self.trail):
            ratio = (i + 1) / (n + 1)
            alpha = int(180 * ratio)
            r = max(2, int(BALL_RADIUS * 0.55 * ratio))
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (230, 115, 25, alpha), (r, r), r)
            surf.blit(s, (int(tx) - r, int(ty) - r))

        # ── Ball body ──
        cx, cy = int(self.x), int(self.y)
        pygame.draw.circle(surf, C_ORANGE, (cx, cy), BALL_RADIUS)

        # ── Seam lines (rotate with spin) ──
        for offset in (0, 90, 180, 270):
            a = math.radians(self.spin + offset)
            # curved seam approximated with a line
            x1 = cx + int(BALL_RADIUS * 0.85 * math.cos(a))
            y1 = cy + int(BALL_RADIUS * 0.85 * math.sin(a))
            x2 = cx - int(BALL_RADIUS * 0.85 * math.cos(a))
            y2 = cy - int(BALL_RADIUS * 0.85 * math.sin(a))
            pygame.draw.line(surf, C_DK_ORANGE, (x1, y1), (x2, y2), 2)

        pygame.draw.circle(surf, C_DK_ORANGE, (cx, cy), BALL_RADIUS, 2)


# ─────────────────────────────────────────────────────
# HOOP
# ─────────────────────────────────────────────────────
class Hoop:
    """Basketball hoop with backboard, rim, and net. Supports vertical motion."""

    def __init__(self):
        self.x          = float(HOOP_BASE_X)
        self.y          = float(HOOP_BASE_Y)
        self.move_speed = 0.0
        self.move_dir   = 1.0
        self.net_shake  = 0.0   # > 0 triggers net animation after score

    # ── Rim edge positions ──
    @property
    def left_rim_pos(self) -> tuple[float, float]:
        return (self.x - RIM_HALF, self.y)

    @property
    def right_rim_pos(self) -> tuple[float, float]:
        return (self.x + RIM_HALF, self.y)

    def set_moving(self, speed: float):
        self.move_speed = speed

    def update(self, dt: float):
        # Vertical oscillation
        if self.move_speed > 0:
            self.y += self.move_speed * self.move_dir * dt
            if self.y < 180 or self.y > 380:
                self.move_dir *= -1

        # Decay net shake animation
        if self.net_shake > 0:
            self.net_shake = max(0.0, self.net_shake - dt * 5)

    def draw(self, surf: pygame.Surface):
        bx  = BACKBOARD_X
        ry  = int(self.y)
        lx  = int(self.x - RIM_HALF)
        rx  = int(self.x + RIM_HALF)
        mid = int(self.x)

        # ── Support pole from backboard to rim ──
        pygame.draw.line(surf, (70, 70, 70), (bx - 8, ry - 18), (bx + 28, ry - 18), 6)

        # ── Backboard ──
        board = pygame.Rect(bx - 14, ry - 75, 16, 110)
        pygame.draw.rect(surf, C_BOARD, board)
        pygame.draw.rect(surf, C_BOARD_LN, board, 2)
        # target box on backboard
        pygame.draw.rect(surf, C_RIM, pygame.Rect(bx - 12, ry - 38, 12, 32), 2)

        # ── Rim ──
        pygame.draw.line(surf, C_RIM, (lx, ry), (rx, ry), RIM_RADIUS * 2)
        pygame.draw.circle(surf, C_RIM, (lx, ry), RIM_RADIUS)
        pygame.draw.circle(surf, C_RIM, (rx, ry), RIM_RADIUS)

        # ── Net ──
        t_now  = pygame.time.get_ticks() * 0.001
        shake  = math.sin(t_now * 12) * self.net_shake * 5

        # Vertical strands of the net (fan from rim edges to bottom centre)
        strands = 10
        for i in range(strands + 1):
            frac  = i / strands
            top_x = lx + frac * (rx - lx)
            top_y = ry
            bot_x = mid + (frac - 0.5) * 12 + shake * (frac - 0.5)
            bot_y = ry + NET_H + self.net_shake * 6 * math.sin(frac * math.pi)
            pygame.draw.line(surf, C_NET,
                             (int(top_x), int(top_y)),
                             (int(bot_x), int(bot_y)), 1)

        # Horizontal rows
        for row in range(1, 5):
            t = row / 5
            y_row = ry + t * NET_H + self.net_shake * 5 * math.sin(t * math.pi + shake)
            xl = lx + t * (mid - lx) + (t * shake * 0.3)
            xr = rx + t * (mid - rx) - (t * shake * 0.3)
            pygame.draw.line(surf, C_NET,
                             (int(xl), int(y_row)), (int(xr), int(y_row)), 1)

    # ─── Collision helpers ───────────────────────────

    def check_score(self, ball: Ball, prev_y: float) -> bool:
        """
        Detect clean basket: ball centre crosses rim plane downward while inside
        the scoring zone (not overlapping either rim knob).
        prev_y is the ball y-position on the previous physics frame.
        """
        if ball.vy <= 0:
            return False   # must be falling
        rim_y = self.y
        # Did the ball centre cross rim_y this frame?
        if not (prev_y < rim_y <= ball.y):
            return False
        # Horizontal scoring zone: generous (allows slight rim grazes)
        score_half = RIM_HALF - BALL_RADIUS * 0.6
        return abs(ball.x - self.x) <= score_half

    def check_rim_collision(self, ball: Ball) -> bool:
        """
        Bounce ball off the left/right rim knobs using circle-circle collision.
        Returns True if a collision occurred.
        """
        bounced = False
        for (kx, ky) in [self.left_rim_pos, self.right_rim_pos]:
            dx = ball.x - kx
            dy = ball.y - ky
            dist = math.hypot(dx, dy)
            min_dist = BALL_RADIUS + RIM_RADIUS
            if dist < min_dist and dist > 0:
                # Push ball outside rim knob
                nx, ny = dx / dist, dy / dist
                overlap = min_dist - dist
                ball.x += nx * overlap
                ball.y += ny * overlap
                # Reflect velocity along the collision normal
                dot = ball.vx * nx + ball.vy * ny
                ball.vx = (ball.vx - 2 * dot * nx) * ELASTICITY
                ball.vy = (ball.vy - 2 * dot * ny) * ELASTICITY
                bounced = True
        return bounced

    def check_backboard_collision(self, ball: Ball) -> bool:
        """Bounce ball off the front face of the backboard."""
        board_face = BACKBOARD_X - 14   # left (front) face of the backboard
        board_top  = self.y - 75
        board_bot  = self.y + 35
        if (ball.vx > 0
                and ball.x + BALL_RADIUS >= board_face
                and ball.x < board_face + 20        # prevent tunnelling
                and board_top <= ball.y <= board_bot):
            ball.x  = board_face - BALL_RADIUS
            ball.vx = -abs(ball.vx) * ELASTICITY
            return True
        return False


# ─────────────────────────────────────────────────────
# PARTICLE SYSTEM
# ─────────────────────────────────────────────────────
class Particle:
    """A single firework-style particle for score celebrations."""

    def __init__(self, x: float, y: float, color: tuple):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(90, 260)
        self.x     = x
        self.y     = y
        self.vx    = speed * math.cos(angle)
        self.vy    = speed * math.sin(angle)
        self.color = color
        self.life  = random.uniform(0.45, 0.9)
        self.max_l = self.life
        self.r     = random.randint(3, 8)

    def update(self, dt: float):
        self.x   += self.vx * dt
        self.y   += self.vy * dt
        self.vy  += 350 * dt   # particles fall
        self.vx  *= 0.98       # slight air drag
        self.life -= dt

    def draw(self, surf: pygame.Surface):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / self.max_l))
        s = pygame.Surface((self.r * 2, self.r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], alpha), (self.r, self.r), self.r)
        surf.blit(s, (int(self.x) - self.r, int(self.y) - self.r))


# ─────────────────────────────────────────────────────
# FLOATING SCORE TEXT
# ─────────────────────────────────────────────────────
class FloatingText:
    """Animated score text that rises and fades."""

    def __init__(self, text: str, x: float, y: float,
                 color: tuple, size: int = 34, duration: float = 1.1):
        self.text     = text
        self.x        = x
        self.y        = y
        self.color    = color
        self.life     = duration
        self.max_life = duration
        self.vy       = -90.0
        self.font     = pygame.font.SysFont("Arial", size, bold=True)

    def update(self, dt: float):
        self.y    += self.vy * dt
        self.life -= dt

    def draw(self, surf: pygame.Surface):
        if self.life <= 0:
            return
        alpha = int(255 * min(1.0, (self.life / self.max_life) * 2))
        rendered = self.font.render(self.text, True, self.color)
        rendered.set_alpha(alpha)
        surf.blit(rendered, (int(self.x) - rendered.get_width() // 2, int(self.y)))


# ─────────────────────────────────────────────────────
# RENDERER  (drawing helpers)
# ─────────────────────────────────────────────────────
def draw_court(surf: pygame.Surface):
    """Render the basketball court background."""
    surf.fill(C_BG)
    # Hardwood floor strip
    pygame.draw.rect(surf, C_FLOOR,
                     pygame.Rect(0, SCREEN_H - 80, SCREEN_W, 80))
    pygame.draw.line(surf, C_FLOOR_LN,
                     (0, SCREEN_H - 80), (SCREEN_W, SCREEN_H - 80), 3)

    # Three-point arc – centred at the basket/hoop side, opening toward the shooter
    pygame.draw.arc(surf, C_FLOOR_LN,
                    pygame.Rect(HOOP_BASE_X - 200, SCREEN_H - 310, 400, 380),
                    math.radians(15), math.radians(165), 2)

    # Free-throw lane – box on the hoop side (from baseline toward shooter)
    lane_left  = HOOP_BASE_X - 170   # free-throw line
    lane_right = BACKBOARD_X         # baseline
    lane_floor = SCREEN_H - 80
    lane_top   = SCREEN_H - 200
    pygame.draw.line(surf, C_FLOOR_LN, (lane_left, lane_floor), (lane_right, lane_floor), 3)
    pygame.draw.line(surf, C_FLOOR_LN, (lane_left, lane_floor), (lane_left, lane_top), 2)
    pygame.draw.line(surf, C_FLOOR_LN, (lane_right, lane_floor), (lane_right, lane_top), 2)
    pygame.draw.line(surf, C_FLOOR_LN, (lane_left, lane_top), (lane_right, lane_top), 2)


def draw_aim_arrow(surf: pygame.Surface, origin: tuple, drag: tuple, power: float):
    """
    Visualise aim direction and power.
    origin  = ball position (click start)
    drag    = current drag end position
    power   = 0.0 – 1.0 power ratio
    """
    ox, oy = origin
    dx, dy = drag
    if math.hypot(dx - ox, dy - oy) < 8:
        return
    # Arrow direction is OPPOSITE of drag (slingshot)
    ax = int(ox + (ox - dx) * 0.5)
    ay = int(oy + (oy - dy) * 0.5)

    green = int(200 - 150 * power)
    red   = int(50  + 200 * power)
    color = (red, green, 30)

    pygame.draw.line(surf, color, (ox, oy), (ax, ay), 3)
    # Arrowhead
    angle = math.atan2(ay - oy, ax - ox)
    for side in (0.45, -0.45):
        hx = ax - 16 * math.cos(angle + side)
        hy = ay - 16 * math.sin(angle + side)
        pygame.draw.line(surf, color, (ax, ay), (int(hx), int(hy)), 3)


def draw_power_bar(surf: pygame.Surface, cx: float, cy: float, power: float):
    """Small power bar drawn below the ball during aim."""
    bx = int(cx) - 30
    by = int(cy) + 26
    pygame.draw.rect(surf, (50, 50, 50), pygame.Rect(bx, by, 60, 8))
    fill = int(60 * power)
    col = (int(50 + 200 * power), int(200 - 150 * power), 30)
    pygame.draw.rect(surf, col, pygame.Rect(bx, by, fill, 8))
    pygame.draw.rect(surf, C_WHITE, pygame.Rect(bx, by, 60, 8), 1)


def draw_hud(surf, score, shots, combo, level, wind, font_lg, font_sm):
    """Draw the heads-up display: score, accuracy, combo, wind."""
    panel = pygame.Surface((230, 140), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 155))
    surf.blit(panel, (10, 10))

    acc = (score * 100 // shots) if shots > 0 else 0
    rows = [
        (f"Score:    {score}",    font_lg, C_WHITE),
        (f"Shots:    {shots}/{MAX_SHOTS}", font_sm, C_WHITE),
        (f"Accuracy: {acc}%",     font_sm, C_WHITE),
        (f"Level:    {level}",    font_sm,
         (255, 100, 100) if level >= 3 else C_WHITE),
    ]
    for i, (text, font, col) in enumerate(rows):
        surf.blit(font.render(text, True, col), (18, 14 + i * 30))

    # Wind bar
    if abs(wind) > 1:
        wy = 158
        surf.blit(font_sm.render("Wind:", True, C_WIND_COL), (18, wy))
        bar_w = min(int(abs(wind) * 0.55), 80)
        bx = 70 if wind > 0 else 70 - bar_w
        pygame.draw.rect(surf, C_WIND_COL, pygame.Rect(bx, wy + 6, bar_w, 10))
        arrow = ">>>" if wind > 0 else "<<<"
        ax = 70 + bar_w + 4 if wind > 0 else 70 - bar_w - 30
        surf.blit(font_sm.render(arrow, True, C_WIND_COL), (ax, wy))

    # Combo banner (centred, above everything)
    if combo >= 2:
        label = f"COMBO  x{combo}!"
        ct = font_lg.render(label, True, C_COMBO)
        surf.blit(ct, (SCREEN_W // 2 - ct.get_width() // 2, 12))


def draw_start_screen(surf, font_title, font_md, font_sm):
    surf.fill((14, 28, 14))

    title = font_title.render("BASKETBALL FUN", True, C_ORANGE)
    surf.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 110))

    sub = font_md.render("Physics Shooting Game", True, (200, 200, 200))
    surf.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 185))

    # Draw a little hoop icon
    pygame.draw.line(surf, C_RIM,
                     (SCREEN_W // 2 - 36, 245), (SCREEN_W // 2 + 36, 245), 8)
    pygame.draw.circle(surf, C_ORANGE, (SCREEN_W // 2 - 70, 280), 20)

    lines = [
        ("HOW TO PLAY",            font_md, C_ORANGE),
        ("",                        font_sm, C_WHITE),
        ("Click + drag FROM the ball to aim", font_sm, C_WHITE),
        ("Pull back  =  more power",          font_sm, C_WHITE),
        ("Release to shoot!",                 font_sm, C_WHITE),
        ("",                                  font_sm, C_WHITE),
        ("Score combos for  +2  bonus points!", font_sm, (255, 215, 0)),
        ("Hoop moves and wind starts at level 2+", font_sm, C_WIND_COL),
        ("",                                  font_sm, C_WHITE),
        ("R = restart    ESC = quit",          font_sm, (180, 180, 180)),
    ]
    for i, (text, font, col) in enumerate(lines):
        t = font.render(text, True, col)
        surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 280 + i * 30))

    # Pulsing start prompt
    alpha = int(140 + 115 * math.sin(pygame.time.get_ticks() * 0.004))
    st = font_md.render("CLICK  TO  START", True, C_ORANGE)
    st.set_alpha(alpha)
    surf.blit(st, (SCREEN_W // 2 - st.get_width() // 2, 590))


def draw_game_over_screen(surf, score, shots, font_title, font_md, font_sm) -> pygame.Rect:
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 185))
    surf.blit(overlay, (0, 0))

    go = font_title.render("GAME  OVER", True, (220, 45, 45))
    surf.blit(go, (SCREEN_W // 2 - go.get_width() // 2, 130))

    acc = (score * 100 // shots) if shots > 0 else 0
    rating = "PERFECT!" if acc == 100 else "GREAT!" if acc >= 70 else "GOOD!" if acc >= 50 else "KEEP PRACTISING!"
    rat_col = C_COMBO if acc >= 70 else C_WHITE

    stats = [
        (f"Final Score:  {score}",  font_md, C_WHITE),
        (f"Shots Taken:  {shots}",  font_md, C_WHITE),
        (f"Accuracy:     {acc}%",   font_md, C_WHITE),
        (f"{rating}",               font_md, rat_col),
    ]
    for i, (text, font, col) in enumerate(stats):
        t = font.render(text, True, col)
        surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 240 + i * 55))

    btn = pygame.Rect(SCREEN_W // 2 - 115, 490, 230, 58)
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
    Top-level game controller.
    States: "start" → "play" → "gameover" → (restart) → "play"
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Basketball Fun Game")
        self.clock  = pygame.time.Clock()

        # Fonts (created once and reused)
        self.f_title = pygame.font.SysFont("Arial", 62, bold=True)
        self.f_lg    = pygame.font.SysFont("Arial", 26, bold=True)
        self.f_md    = pygame.font.SysFont("Arial", 36, bold=True)
        self.f_sm    = pygame.font.SysFont("Arial", 20)

        self.sounds  = SoundManager()
        self.state   = "start"
        self._restart_btn: pygame.Rect | None = None

        self._init_game()

    # ─── Game initialisation ─────────────────────────

    def _init_game(self):
        """Reset all game state (called at start and on restart)."""
        self.ball      = Ball()
        self.hoop      = Hoop()
        self.score     = 0
        self.shots     = 0
        self.combo     = 0
        self.level     = 1
        self.wind      = 0.0

        self.particles: list[Particle]     = []
        self.floats:    list[FloatingText] = []

        # Drag-to-aim state
        self.dragging    = False
        self.drag_start  = (0, 0)
        self.drag_cur    = (0, 0)

        # Ball-reset countdown (after a shot ends)
        self.waiting_reset = False
        self.reset_timer   = 0.0

        # Prevent double-scoring on the same shot
        self.scored_shot   = False

    # ─── Difficulty scaling ──────────────────────────

    def _update_difficulty(self):
        """Called after each shot to potentially increase difficulty."""
        self.level = self.shots // LEVEL_EVERY + 1

        # Level 2+: hoop moves vertically
        if self.level >= 2:
            speed = min(50.0 + (self.level - 2) * 30, 200.0)
            self.hoop.set_moving(speed)
        else:
            self.hoop.set_moving(0)

        # Level 3+: wind effect
        if self.level >= 3:
            max_w = min(25 + (self.level - 3) * 20, 110)
            self.wind = random.uniform(-max_w, max_w)
        else:
            self.wind = 0.0

    # ─── Input handling ──────────────────────────────

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    self._init_game()
                    if self.state != "start":
                        self.state = "play"

            # ── Start screen ──
            if self.state == "start":
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    self.state = "play"

            # ── Play screen ──
            elif self.state == "play":
                self._handle_play_input(event)

            # ── Game-over screen ──
            elif self.state == "gameover":
                if (event.type == pygame.MOUSEBUTTONDOWN and
                        self._restart_btn and
                        self._restart_btn.collidepoint(event.pos)):
                    self._init_game()
                    self.state = "play"

    def _handle_play_input(self, event: pygame.event.Event):
        """Process mouse events for the slingshot aim mechanic."""
        bx, by = int(self.ball.x), int(self.ball.y)

        if (event.type == pygame.MOUSEBUTTONDOWN and
                not self.ball.in_flight and
                not self.waiting_reset):
            mx, my = event.pos
            # Click must start on/near ball
            if math.hypot(mx - bx, my - by) <= BALL_RADIUS + 22:
                self.dragging   = True
                self.drag_start = event.pos
                self.drag_cur   = event.pos

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.drag_cur = event.pos

        elif event.type == pygame.MOUSEBUTTONUP and self.dragging:
            self.dragging = False
            self._fire_shot()

    def _fire_shot(self):
        """Convert drag vector to launch angle and speed, then shoot ball."""
        if self.shots >= MAX_SHOTS:
            return

        sx, sy = self.drag_start
        ex, ey = self.drag_cur
        # Drag BACK from ball → shot direction is reversed
        dx = sx - ex
        dy = sy - ey   # in screen coords (positive y = down)
        dist = math.hypot(dx, dy)

        if dist < 12:
            return   # ignore tiny flicks

        # Compute angle: atan2(-dy, dx) converts screen-y to math-y
        angle = math.degrees(math.atan2(-dy, dx))
        power = min(dist / MAX_DRAG, 1.0)
        speed = MIN_POWER + power * (MAX_POWER - MIN_POWER)

        self.ball.shoot(angle, speed, wind=self.wind)
        self.shots       += 1
        self.scored_shot  = False
        self._update_difficulty()

    # ─── Physics & game logic update ─────────────────

    def update(self, dt: float):
        if self.state != "play":
            return

        # Always update hoop (even while ball is at rest)
        self.hoop.update(dt)

        # ── Ball physics ──
        if self.ball.in_flight:
            prev_y = self.ball.y
            self.ball.update(dt)

            # Score detection (only once per shot)
            if not self.scored_shot and self.hoop.check_score(self.ball, prev_y):
                self._on_score()

            # Rim collision (bounce off knobs)
            if self.hoop.check_rim_collision(self.ball):
                self.sounds.play("bounce")

            # Backboard collision
            if self.hoop.check_backboard_collision(self.ball):
                self.sounds.play("bounce")

            # Ball left the screen
            if self.ball.out_of_bounds:
                if not self.scored_shot:
                    self.combo = 0
                    self.sounds.play("miss")
                self.ball.in_flight  = False
                self.waiting_reset   = True
                self.reset_timer     = 1.2

        # ── Reset countdown ──
        if self.waiting_reset:
            self.reset_timer -= dt
            if self.reset_timer <= 0:
                self.waiting_reset = False
                self.ball.reset()
                if self.shots >= MAX_SHOTS:
                    self.state = "gameover"

        # ── Update visual effects ──
        for p in self.particles[:]:
            p.update(dt)
            if p.life <= 0:
                self.particles.remove(p)

        for ft in self.floats[:]:
            ft.update(dt)
            if ft.life <= 0:
                self.floats.remove(ft)

    def _on_score(self):
        """Handle a successful basket."""
        self.scored_shot = True
        self.combo      += 1

        # Combos of 3+ are worth +2 pts
        pts = 2 if self.combo >= 3 else 1
        self.score      += pts

        self.hoop.net_shake = 1.0
        self.sounds.play("swish")

        # Particle burst at hoop
        colours = [C_ORANGE, C_COMBO, C_WHITE, (255, 80, 80)]
        for _ in range(35):
            self.particles.append(
                Particle(self.hoop.x, self.hoop.y,
                         random.choice(colours))
            )

        # Floating score label
        label = (f"+{pts}  COMBO  x{self.combo}!"
                 if self.combo >= 3 else f"+{pts}")
        self.floats.append(
            FloatingText(label,
                         self.hoop.x, self.hoop.y - 50,
                         C_COMBO if self.combo >= 3 else C_WHITE,
                         size=38 if self.combo >= 3 else 34)
        )

        # Gently kill horizontal speed so ball drops through net
        self.ball.vx *= 0.25
        self.ball.vy  = max(self.ball.vy, 60)   # ensure downward

        # Start reset timer (ball exits screen naturally)
        self.waiting_reset = True
        self.reset_timer   = 1.8

    # ─── Rendering ───────────────────────────────────

    def draw(self):
        if self.state == "start":
            draw_start_screen(self.screen, self.f_title, self.f_md, self.f_sm)

        elif self.state in ("play", "gameover"):
            draw_court(self.screen)
            self.hoop.draw(self.screen)

            # Particles drawn behind ball
            for p in self.particles:
                p.draw(self.screen)

            self.ball.draw(self.screen)

            # Aim visualisation
            if self.dragging and not self.ball.in_flight:
                sx, sy = self.drag_start
                ex, ey = self.drag_cur
                dist   = math.hypot(sx - ex, sy - ey)
                power  = min(dist / MAX_DRAG, 1.0)
                draw_aim_arrow(self.screen, (sx, sy), (ex, ey), power)
                draw_power_bar(self.screen, self.ball.x, self.ball.y, power)

            # HUD
            draw_hud(self.screen, self.score, self.shots,
                     self.combo, self.level, self.wind,
                     self.f_lg, self.f_sm)

            # Floating texts
            for ft in self.floats:
                ft.draw(self.screen)

            # Shots remaining (bottom-right)
            left = MAX_SHOTS - self.shots
            rt = self.f_sm.render(f"Shots remaining: {left}", True, C_WHITE)
            self.screen.blit(rt, (SCREEN_W - rt.get_width() - 16, SCREEN_H - 32))

            # Hint text when ball is ready and not dragging
            if not self.ball.in_flight and not self.waiting_reset and not self.dragging:
                hint = self.f_sm.render("Click + drag ball to shoot", True, (170, 170, 170))
                self.screen.blit(hint,
                                 (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 32))

            # Wind notification (only on new level)
            if abs(self.wind) > 5:
                wdir = "WIND >>>" if self.wind > 0 else "<<< WIND"
                wt = self.f_sm.render(wdir, True, C_WIND_COL)
                self.screen.blit(wt, (SCREEN_W // 2 - wt.get_width() // 2, 45))

            if self.state == "gameover":
                self._restart_btn = draw_game_over_screen(
                    self.screen, self.score, self.shots,
                    self.f_title, self.f_md, self.f_sm
                )

        pygame.display.flip()

    # ─── Main loop ───────────────────────────────────

    def run(self):
        while True:
            # Cap dt to avoid tunnelling on frame spikes
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(dt)
            self.draw()


# ─────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    game = Game()
    game.run()
