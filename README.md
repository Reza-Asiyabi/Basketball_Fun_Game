# Basketball Fun Game

A physics-based basketball shooting game built with Python and Pygame. Aim, shoot, score combos, and survive increasing difficulty across 15 shots.

---

## Screenshot

```
[ Start Screen ] --> [ Gameplay ] --> [ Game Over ]
     click            aim & shoot       play again
```

---

## Requirements

| Dependency | Purpose             | Required |
|------------|---------------------|----------|
| Python 3.9+ | Runtime            | Yes      |
| pygame     | Graphics & input    | Yes      |
| numpy      | Sound effects       | Optional |

---

## Installation & Running

**1. Clone or download the project**

```bash
git clone <repo-url>
cd basketball_Fun_Game
```

**2. Install dependencies**

```bash
pip install pygame
# Optional – enables sound effects:
pip install numpy
```

**3. Run the game**

```bash
python basketball_game.py
```

---

## Controls

| Input | Action |
|-------|--------|
| Click on ball | Begin aiming |
| Drag away from target | Set direction & power |
| Release mouse | Shoot |
| `R` | Restart at any time |
| `ESC` | Quit |

**Aiming mechanic (slingshot style):**
Click directly on the ball, then drag in the *opposite* direction of where you want to shoot — like pulling back a slingshot. The farther you drag, the more power is applied. A coloured arrow and power bar appear while aiming.

---

## Gameplay

### Objective
Score as many baskets as possible in **15 shots**.

### Scoring

| Situation | Points |
|-----------|--------|
| Ball through hoop | +1 |
| Combo (3+ consecutive baskets) | +2 per basket |
| Miss | 0 (combo resets) |

### Stats tracked
- **Score** — total points
- **Shots** — shots taken out of 15
- **Accuracy** — percentage of shots scored

---

## Difficulty Levels

Difficulty escalates automatically every **5 shots**:

| Level | Unlocks |
|-------|---------|
| 1 | Static hoop |
| 2 | Hoop moves vertically |
| 3 | Wind effect added |
| 4+ | Faster hoop + stronger wind |

Wind is shown as a directional bar in the HUD and `>>>` / `<<<` text in the centre of the screen. You must compensate for wind manually.

---

## Physics

- **Gravity**: `vy += 850 * dt` each frame (tuned for satisfying arcs)
- **Launch**: velocity is derived from drag distance (power) and angle
- **Rim collision**: circle–circle detection between ball and each rim knob; velocity is reflected along the collision normal and reduced by an elasticity factor (`0.45`) on each bounce
- **Score detection**: the ball centre must cross the rim plane **downward** while inside the scoring zone — checked using the ball's previous and current y-position to avoid missed detections at high speed

---

## Visual Features

- Ball trail with fade effect
- Rotating seam lines on the ball
- Net shake animation after scoring
- Particle burst on successful baskets
- Floating score text (`+1`, `COMBO x3!`)
- Animated aim arrow with colour-coded power indicator

---

## Sound Effects

Generated procedurally at startup (no audio files needed). Requires `numpy`.

| Sound | Trigger |
|-------|---------|
| Swish | Ball goes through hoop |
| Bounce | Ball hits the rim |
| Miss | Ball leaves the screen without scoring |

If `numpy` is not installed, the game runs silently with no other impact.

---

## Project Structure

```
basketball_Fun_Game/
├── basketball_game.py   # All game code (single file)
└── README.md
```

### Code organisation (within `basketball_game.py`)

| Class / Function | Responsibility |
|------------------|----------------|
| `Ball` | Position, velocity, physics step, trail, rendering |
| `Hoop` | Position, motion, rim/net rendering, collision detection |
| `Particle` | Score celebration burst particles |
| `FloatingText` | Animated `+1 / COMBO!` labels |
| `SoundManager` | Procedural audio generation and playback |
| `Game` | Main loop, state machine, input, difficulty scaling |
| `draw_court` | Background court rendering |
| `draw_hud` | Score panel, wind bar, combo banner |
| `draw_start_screen` | Title / instructions screen |
| `draw_game_over_screen` | Results screen with restart button |

---

## Game States

```
"start"  --[ click / any key ]-->  "play"
"play"   --[ 15 shots used ]-->    "gameover"
"gameover" --[ Play Again btn ]-->  "play"
```

---

## Tips

- Shoot at roughly a **45–60 degree arc** for the most reliable path to the hoop
- At **level 2**, lead your shot slightly — the hoop keeps moving
- At **level 3+**, check the wind bar before shooting and aim into the wind to compensate
- **Combos** of 3+ give double points — go for streaks early before wind makes accuracy harder
