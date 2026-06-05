# orbitRL

A reinforcement learning sandbox built around OrbitXL — a PyGame arcade game where a white circle orbits a black hole while dodging colored enemy circles that spiral inward.

The game ships with an **RL Lab** mode that replaces the human player with N AI-controlled agents. Each episode runs until all agents are dead, then resets automatically. You can inject any policy by passing a `policy_factory` callable — the default is a random stub.

## Setup

Requires Python 3.12+ and [`uv`](https://github.com/astral-sh/uv).

```bash
# Install dependencies and create virtual environment
uv sync

# Run the game
uv run orbitrl
```

## How to Play

- **Spacebar** — hold to thrust outward, release to fall inward
- Survive by staying within the three concentric orbit zones
- Score points by surviving longer in inner (harder) zones and by narrowly dodging enemies
- Colliding with an enemy or drifting beyond the outer ring ends the game

## RL Lab

The RL Lab runs the same physics and enemy logic with N agents instead of a human. Access it from the main menu via the **RL Lab** button.

The core interface is `OrbitSim` in `src/orbitrl/environment.py` — a headless, gym-style environment you can drive from a training loop:

```python
from orbitrl.environment import OrbitSim

sim = OrbitSim(n=5, seed=42)
obs = sim.reset()

while True:
    actions = [policy(o) for policy, o in zip(policies, obs)]
    obs, rewards, dones, info = sim.step(actions)
    if all(dones):
        obs = sim.reset()
```

Each agent's cumulative score is returned as its reward signal. `RLLab` in `src/orbitrl/rl_lab.py` is a thin PyGame adapter over `OrbitSim` that renders the demo with random policies.

## Project Layout

```text
src/orbitrl/
├── app.py           # main loop and world switching
├── core.py          # shared ECS components and processors (movement, rendering)
├── player.py        # player component, spawner, and player-aware processors
├── enemies.py       # enemy components and processors
├── simulation.py    # shared simulation spine (processors + black hole spawn)
├── environment.py   # OrbitSim: headless gym-style RL environment
├── rl_lab.py        # PyGame adapter that renders OrbitSim with random policies
├── setup.py         # game world initialization
├── scenes.py        # world constants and event routing
├── menu.py          # main menu and leaderboard UI
├── highscores.py    # persistent leaderboard (top 10, JSON)
└── config.py        # screen dimensions and zone radii constants
```

## Running Tests

```bash
uv run pytest          # full suite (headless, no display required)
uv run pytest -q tests/test_environment.py   # OrbitSim environment tests only
```

## Linting

```bash
uv run ruff check src/orbitrl        # check
uv run ruff check src/orbitrl --fix  # auto-fix safe subset
```
