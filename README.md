# Basketball Fun Game  v2.0

A physics-based basketball shooting game built with Python and Pygame.

---

## Requirements

| Dependency | Purpose          | Required |
|------------|------------------|----------|
| Python 3.9+ | Runtime         | Yes      |
| pygame 2.0+ | Graphics & input | Yes      |
| numpy       | Sound effects    | Optional |

---

## Installation & Running

```bash
pip install pygame
pip install numpy          # optional – enables sound effects
python basketball_game.py
```

---

## Controls

| Input | Action |
|-------|--------|
| Click on ball + drag away | Aim (slingshot) |
| Release mouse | Shoot |
| `F11` | Toggle fullscreen |
| `R` | Return to menu |
| `ESC` | Quit |

**Aiming:** Click on the ball and drag in the *opposite* direction of your target — like pulling back a slingshot. Drag distance = power.

---

## Game Flow

```
Menu  ──[pick difficulty]──►  Play  ──[15 shots]──►  Game Over
 ▲                                                        │
 └────────────────── Play Again ◄──────────────────────── ┘
```

---

## Difficulty Levels

Selected on the menu — not gradual escalation. The hoop starts moving and wind is active **before** your first shot.

| Level  | Hoop | Wind |
|--------|------|------|
| Easy   | Static | None |
| Medium | Slow vertical movement | Mild (±55 px/s) |
| Hard   | Fast vertical movement | Strong (±120 px/s) |

Wind re-randomises between each shot within the chosen range.

---

## Scoring

| Event | Points |
|-------|--------|
| Basket | +1 |
| Combo (3+ consecutive baskets) | +2 per basket |
| Miss | 0 (combo resets) |

---

## Stats

- **Score** — points this game  
- **Best Score** — saved to `best_score.json` and displayed on menu and HUD  
- **Shots** — out of 15  
- **Accuracy** — percentage of shots scored  

---

## Visuals (v2.0 enhancements)

| Feature | Detail |
|---------|--------|
| Ball | 3-D sphere shading (highlight + shadow side), leather pebble texture, curved seam arcs |
| Arena background | Night-arena gradient, three overhead spotlight cones, crowd silhouettes |
| Floor | Vertical hardwood planks with wood-grain lines and court markings |
| Rim | 3-D shading (highlight strip on top, shadow below), specular knob highlights |
| Net | Converging vertical strands + horizontal rows, shake animation on score |

---

## Physics

- **Gravity:** `vy += 850 × dt` each frame
- **Rim collision:** circle–circle with velocity reflection and 0.45 elasticity
- **Score detection:** ball centre crosses rim plane downward inside the scoring zone, checked via previous/current y-position to handle fast balls
- **Backboard:** flat-face reflection

---

## Persistent Best Score

Saved to `best_score.json` in the same folder as the script. Shown on the menu and HUD every session. A **"NEW BEST SCORE!"** banner appears on the game-over screen when you beat it.

---

## Fullscreen

Press `F11` at any time to toggle fullscreen. The game uses `pygame.SCALED` so the internal 960×620 canvas scales cleanly to any monitor resolution with letterboxing if needed. Current state is shown in the bottom-right corner of the menu.

---

## Project Structure

```
basketball_Fun_Game/
├── basketball_game.py   # All game code (single file)
├── best_score.json      # Created automatically on first game-over
└── README.md
```

### Code layout

| Class / Function | Responsibility |
|------------------|----------------|
| `Ball` | Physics, sphere rendering, trail |
| `Hoop` | Motion, rim/net rendering, collision |
| `Particle` | Score burst effects |
| `FloatingText` | Animated score labels |
| `SoundManager` | Procedural audio |
| `Game` | State machine, input, difficulty, loop |
| `_build_arena_bg()` | Precomputed arena gradient + spotlights |
| `_build_floor_surf()` | Precomputed wood-plank floor |
| `_build_ball_template()` | Precomputed sphere-shading surface |
| `draw_menu_screen()` | Title + difficulty buttons + instructions |
| `draw_hud()` | Score panel, wind bar, combo banner |
| `draw_game_over_screen()` | Results + best score + restart button |
| `load_best_score()` / `save_best_score()` | JSON persistence |

---

## Tips

- Aim for a **45–60° arc** — flat shots often clip the near rim
- On **Medium/Hard**, watch the wind indicator before each shot and aim into the wind
- On **Hard**, lead moving-hoop shots slightly ahead of the rim's travel direction
- Build **combos early** — once wind is strong, consistency drops
