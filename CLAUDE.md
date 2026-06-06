# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**orbitRL** is a reinforcement learning game where players learn to play OrbitXL using ML. It's a PyGame-based arcade game where the player controls a white circle orbiting a black hole, dodging colored enemy circles that spawn and move toward the center. The game features three difficulty zones based on orbit radius, a scoring system, a persistent leaderboard, and an **RL Lab** mode that runs the same environment with N AI-controlled agents instead of a human player.

## Setup and Commands

### Build and Run

This project uses `uv` (Astral's fast Python package manager) for dependency management.

```bash
# Install dependencies (including dev tools) and setup virtual environment
uv sync

# Run the game
uv run orbitrl

# Or use the entry point script
python -m orbitrl

# Lint (Ruff). Run this after edits — config lives in pyproject.toml.
uv run ruff check src/orbitrl

# Auto-fix the safe subset (import sorting, pyupgrade rewrites, etc.)
uv run ruff check src/orbitrl --fix
```

### Dependencies

- **esper** (3.7): Entity Component System framework for game logic
- **pygame-ce** (2.5.7): Pygame Community Edition for graphics and input
- **pygame-gui** (0.6.14): GUI library for menus and dialogs
- **numpy** (2.4.4): Numerical operations, used for angle wrapping and math

Dev dependencies (under `[dependency-groups] dev` in `pyproject.toml`):

- **ruff** (0.15+): Linter and import sorter, configured with `select = ["E", "F", "I", "UP", "B"]` and `line-length = 120`
- **pytest** (8.3+): Test runner; suite lives in `tests/`

### Python Version

Requires Python 3.12 or higher.

## High-Level Architecture

The game uses the **Entity Component System (ECS)** pattern via the `esper` library. This architecture decouples data (components) from behavior (processors/systems), making the codebase highly modular and extensible.

### Core Concepts

**Worlds**: The game has four separate ECS worlds managed by `esper`:
- `MAIN_MENU_WORLD`: Main menu interface (three buttons: Play, Highscores, RL Lab)
- `GAME_WORLD`: Active human-controlled gameplay
- `HIGHSCORES_WORLD`: Leaderboard display
- `RL_WORLD`: Multi-agent RL sandbox — same physics/enemies as `GAME_WORLD` but no human player, no `GameOverProcessor`/`InputProcessor`, and no highscore popup

The app switches between worlds in response to user actions or game events.

**Components**:
- Core (`/src/orbitrl/core.py`): `Position` (x, y), `PolarPosition` (r, theta), `PolarVelocity` (r_dot, theta_dot), `Circle` (radius, color), `Score` (value), `Layer1`/`Layer2` (render layers — enemies on 1, player/agents/black hole on 2), `GameplayPaused` (marker)
- Player (`/src/orbitrl/player.py`): `Player` (alive, zone), `ScoreTracker` (progress) — per-entity score accumulator; required for multi-agent correctness
- Enemies (`/src/orbitrl/enemies.py`): `Enemy` (alive), `EnemyType` (color name for scoring), `NearMissAwarded` (`set[int]` of crediting entity ids — per-(agent, enemy) so each agent independently earns near-miss bonuses)

**Processors** (systems that update entities):
- `MovementProcessor`: Updates polar position based on velocity
- `PolarToCartesianProcessor`: Converts polar to Cartesian coordinates
- `RenderProcessor`: Draws circles and background rings; HUD score blit is gated on `show_score` flag (default `True`; RL world passes `False`)
- `CollisionProcessor`: Detects collisions and near-misses between any `Player` entity and enemies; iterates all `Player` entities so naturally handles N agents. Zeros `PolarVelocity` on collision death
- `InputProcessor`: Reads keyboard input and updates player radial velocity (game world only — not registered in RL world)
- `PlayerZoneProcessor`: Assigns alive players to difficulty zones based on radius; on outer-ring exit, zeros `PolarVelocity` and marks dead. Skips dead players so their frozen velocity persists across frames
- `ScoreProcessor`: Increments per-entity score based on time spent in zones, using each entity's own `ScoreTracker.progress`
- `EnemySpawnProcessor`: Spawns enemies on a timer that accelerates over time; has a `reset()` method for episode boundaries
- `EnemyDespawnProcessor`: Removes enemies that have moved past the center
- `DeadEnemyProcessor`: Removes dead entities from the world
- `GameOverProcessor`: Handles game-over state and highscore entry dialog (game world only — not registered in RL world)
- `MainMenuProcessor`/`HighscoresProcessor`: Handle menu UI events

### Coordinate System

- **Center**: (400, 300) on an 800x600 screen
- **Zones**: Three concentric rings defined by radii:
  - Inner (r < 120): Zone 4, fastest angular velocity (-4.5 rad/s)
  - Middle (120 ≤ r < 200): Zone 2, medium angular velocity (-3.0 rad/s)
  - Outer (200 ≤ r < 270): Zone 1, slow angular velocity (-2.5 rad/s)
  - Beyond outer: Game over
- **Enemies**: Three types with different colors, sizes, and inward speeds (negative r_dot):
  - Red (radius 30, speed -40): Worth 5 points on near-miss
  - Orange (radius 20, speed -70): Worth 10 points
  - Yellow (radius 10, speed -150): Worth 20 points (fastest)

### Game Loop

The main game loop in `/src/orbitrl/app.py`:
1. Handle pygame events (quit, ESC to return to menu — works from any non-menu world)
2. Clear screen background
3. If `rl_lab` is set: call `rl_lab.tick(screen)` (bypasses the esper world path entirely)
4. Otherwise: set frame events for the current ECS world, then `esper.process(dt)`
5. Check for world switch requests; dispatch to `setup_game_world` / `setup_highscores_world` for worlds that need rebuilding, or `switch_world` for simple swaps. RL Lab request creates an `RLLab` instance instead of switching worlds.
6. Render to screen and flip display
7. Limit to 60 FPS

### Gameplay Mechanics

**Player Mechanics**:
- Controls radial velocity with spacebar (200 units/s outward when held, -100 units/s inward when released)
- Automatically rotates around black hole based on current zone
- Dies when moving beyond outer ring or colliding with enemy

**Enemy Mechanics**:
- Spawn every 4 seconds (decreasing to 0.5s minimum as difficulty increases)
- Move radially inward at constant velocity
- Despawn when crossing center (r < 0)
- Reward points on near-miss (within radius + 20 units)

**Scoring**:
- Time-based: 1 point per second spent in current zone, multiplied by zone difficulty (zone 1 = 1 point/sec, zone 2 = 2 points/sec, zone 4 = 4 points/sec)
- Bonus: Enemy near-misses reward 5/10/20 points based on enemy type

**Highscores**:
- Persisted in `/highscores.json` (top 10 only)
- Saved via `save_highscore(name, score)` in `/src/orbitrl/highscores.py`
- Checked against via `is_highscore(score)` to determine if new score qualifies

**RL Lab Mechanics**:
- `OrbitSim` (`/src/orbitrl/environment.py`) is the headless environment. It owns a named esper world, N agent entities (carrying only `Player` — no `AIAgent` component), and the simulation processors. Exposes `reset() → list[Observation | None]` and `step(actions) → (obs, rewards, dones, all_done)`.
- `RLLab` (`/src/orbitrl/rl_lab.py`) is a thin pygame adapter over `OrbitSim` for the watch-it-run demo. It holds random policies, an episode counter, and a HUD; calls `sim.step()` and `sim.reset()` on each tick; prints `[episode K] scores: [...]` when an episode ends.
- Agents are spawned at `r=200`, evenly spaced in `theta`, colored from `AGENT_PALETTE`. Default `n = DEFAULT_AGENT_COUNT = 5`.
- Death is decoupled from reset: `CollisionProcessor`/`PlayerZoneProcessor` set `Player.alive = False` and zero `PolarVelocity`. Dead agents stay frozen in the world; their observations are `None`, rewards are `0`. `OrbitSim.reset()` deletes enemies and agent entities, calls `EnemySpawnProcessor.reset()`, and re-spawns a fresh generation. Processors stay registered across resets.

### File Organization

- `/src/orbitrl/app.py`: Main entry point and world/world-setup management; tracks `rl_lab: RLLab | None`
- `/src/orbitrl/core.py`: Shared ECS components and core processors (movement, rendering, polar→cartesian)
- `/src/orbitrl/player.py`: `Player` + `ScoreTracker` components, `spawn_player`, and player-aware processors (`InputProcessor`, `PlayerZoneProcessor`, `ScoreProcessor`) — all generalized to operate on any entity carrying `Player`
- `/src/orbitrl/enemies.py`: Enemy components and processors (spawn, despawn, collision, dead-entity cleanup)
- `/src/orbitrl/simulation.py`: Shared simulation spine — `spawn_black_hole()` and `setup_simulation_processors(rng=None)` (the 8 headless processors shared by the game world and `OrbitSim`)
- `/src/orbitrl/environment.py`: `OrbitSim` headless gym-style environment; `Observation`, `EnemyObs`, `flatten`
- `/src/orbitrl/rl_lab.py`: `RLLab` — pygame adapter that renders `OrbitSim` with random policies for the demo
- `/src/orbitrl/scenes.py`: World constants (`MAIN_MENU_WORLD`, `GAME_WORLD`, `HIGHSCORES_WORLD`, `RL_WORLD`) and event routing helpers
- `/src/orbitrl/menu.py`: Menu UI setup and processors (main menu and leaderboard); main menu has Play/Highscores/RL Lab buttons
- `/src/orbitrl/highscores.py`: Highscore file I/O and validation
- `/src/orbitrl/config.py`: Game constants (screen dimensions, ring radii)
- `/src/orbitrl/setup.py`: Game world initialization (entities and processors)

### Key Design Patterns

**Component-as-Configuration**: ECS components are pure dataclasses; they hold state but no logic. This makes entity composition flexible.

**Processor Priority**: Higher priority runs first (esper sorts descending). Game world: priority 2 = `InputProcessor`, priority 1 = `RenderProcessor`, priority 0 = everything else in registration order. `OrbitSim` worlds have no priority overrides — all 8 spine processors run at priority 0 in registration order.

**Simulation spine / OrbitSim split**: The 8 headless processors (`PolarToCartesian → Movement → Collision → EnemySpawn → EnemyDespawn → DeadEnemy → PlayerZone → Score`) live in `simulation.py` and are shared by the game world (`setup.py`) and `OrbitSim` (`environment.py`). The game world adds `InputProcessor` (priority 2), `RenderProcessor` (priority 1), and `GameOverProcessor` (priority 0). `OrbitSim` adds none — its `render()` method constructs a `RenderProcessor` lazily on first call so headless trainers pay no display cost.

**Death/reset decoupling (OrbitSim)**: Per-agent death sets `Player.alive = False` and zeros `PolarVelocity`. Dead agents stay frozen in the world with masked observations (`None`) and zero rewards. `OrbitSim.reset()` deletes enemies + agent entities in-place (processors stay registered), calls `EnemySpawnProcessor.reset()`, and re-spawns a fresh generation. Trainers read `sim.scores` immediately after an episode ends to collect per-agent fitness before reset.

**World Switching**: Uses a request/consume pattern via `WorldSwitchRequest` component to decouple world switching logic from event handling.

**Frame Events Distribution**: `FrameEvents` component carries pygame events into the ECS, allowing processors to respond to input without tight coupling to pygame.

### esper Conventions and Gotchas

Notes about the `esper` library specifically — verify against `.venv/lib/python3.14/site-packages/esper/__init__.py` when in doubt:

- **Processor priority**: higher value runs **first** (esper sorts descending). Default priority is 0; ties are broken by insertion order (stable sort). In this codebase, priority 2 = `InputProcessor`, priority 1 = `RenderProcessor`, priority 0 = everything else.
- **`get_components` type stubs are only declared for arity 2–4.** A 5+ component call works at runtime (the underlying impl is `*component_types`) but Pylance flags it with "No overloads match". Suppress with `# type: ignore[call-overload]` or restructure to fetch the extra component inside the loop via `component_for_entity` / `try_component`.
- **`get_processor(ProcessorType)` returns `Processor | None`** — the base class, not the subclass you passed in. To call subclass-specific methods, narrow with `isinstance(p, ProcessorType)`, not just `if p is not None`.
- **`delete_entity` defaults to deferred deletion.** Pass `immediate=True` when you need the entity gone before the next `esper.process` (e.g. inside a reset function). Do *not* call `immediate=True` while iterating that entity's component query — materialize the iterator with `list(...)` first, as `OrbitSim.reset` does.
- **Multi-world API**: `switch_world(name)` activates a world (auto-creates if missing); `list_worlds()` returns existing names; `delete_world(name)` removes one. Components, entities, and processors are per-world. `clear_cache()` is called automatically on every mutation (`create_entity`, `delete_entity`, `add_component`) — calling it manually after a world switch is unnecessary and defeats the query cache in hot loops. `scenes.switch_world` calls it, which is cargo-cult; don't copy that pattern.
- **Querying patterns**: prefer `get_components(A, B, ...)` for joined iteration; use `try_component(ent, T)` for optional access (returns `None` if absent); use `has_component` only for marker checks where you don't need the value. Avoid `component_for_entity` for components that may not exist — it raises `KeyError`.
- **Markers are components too**: empty dataclass components (`Layer1`, `GameplayPaused`, `NearMissAwarded` before the multi-agent fix) participate in joins normally. Add them when you want a query to filter on presence; remove them when the condition no longer holds.
- **`esper.process(dt)` is the world step.** It runs every registered processor's `process(dt)` in priority order. Processors should be idempotent w.r.t. components they don't own and should early-return on `gameplay_paused()` if they're gameplay logic (see existing processors for the pattern).

## Development Notes

### Adding New Features

**New gameplay mechanic**: Add a processor to `/src/orbitrl/core.py` or create a new module. If it belongs in the shared simulation spine (i.e. it's headless and needed in both the game world and `OrbitSim`), add it to `setup_simulation_processors()` in `/src/orbitrl/simulation.py`. Otherwise register it only in `setup.py` (game world) or directly in `OrbitSim._build` (RL only).

**New enemy type**: Modify `spawn_enemy()` in `/src/orbitrl/enemies.py` to add new enemy variants. Update `CollisionProcessor` if scoring for the type differs.

**New UI screen**: Create a world in `/src/orbitrl/scenes.py`, setup function, and processor in `/src/orbitrl/menu.py` (or a new module). Register the world constant and add switching logic in `/src/orbitrl/app.py`.

**New RL algorithm**: Construct an `OrbitSim(n, seed=...)` and drive it with a standard `reset()`/`step(actions)` loop. `step()` returns `(obs, rewards, dones, all_done)`; `obs[i]` is `None` for dead agents. Read `sim.scores` after `all_done` to get per-agent cumulative fitness before calling `reset()`. `flatten(obs, k)` converts an `Observation` to a fixed-length `float32` numpy vector (5 + 4k features). For parallelism, each concurrent sim needs a distinct `world=` name. `Observation` carries `r, theta, r_dot, zone, alive, enemies` — add new fields there when a policy needs additional world state.

### Testing

Tests use **pytest** (dev dependency, `[tool.pytest.ini_options] testpaths = ["tests"]`). Run with:

```bash
uv run pytest          # full suite
uv run pytest -q tests/test_environment.py   # OrbitSim only (runs without a display)
```

Conventions in `tests/`:

- **Headless**: `tests/conftest.py` sets `SDL_VIDEODRIVER=dummy` / `SDL_AUDIODRIVER=dummy` at import (before pygame loads), so the suite runs without a window. Tests use **real** pygame/esper, not mocks.
- **esper isolation**: an autouse `clean_esper` fixture resets the global singleton between tests (switch to `"default"`, delete other worlds, `clear_database`). Pass explicit `world=` names to `OrbitSim`; concurrent sims sharing a name alias the same world.
- **`screen` fixture**: a session-scoped dummy-driver display surface for tests that render or build GUI (`test_rl_lab.py`, `test_worlds.py`). Pure `OrbitSim` tests don't request it and never touch a display.
- **Assertion style**: structural invariants (determinism via two same-seed sims, dead-agent masking, `reward == score delta`, `reset` restoring `living == N`) plus one **trajectory fingerprint** canary in `test_environment.py` (`FINGERPRINT`) that catches silent dynamics drift — re-bless that constant only when you intentionally change the simulation's physics/scoring.
- `test_worlds.py::test_game_world_processor_order` pins the game world's processor order (spine contiguous, `GameOver` last) as a regression guard for the simulation-spine extraction.

### Linting

Ruff is configured as a dev dependency. Settings live in `pyproject.toml`:

- `line-length = 120`
- `select = ["E", "F", "I", "UP", "B"]` — pycodestyle errors, pyflakes, isort, pyupgrade, bugbear

Run `uv run ruff check src/orbitrl` after edits; use `--fix` to auto-apply the safe subset (import sorting, `typing.Callable` → `collections.abc.Callable`, etc.).

**Conventions enforced by Ruff that matter here:**

- **Unused loop control variables must be `_`-prefixed.** B007 flags `for ent, ... in get_components(...)` when `ent` isn't used in the body; rename to `_ent`. Same for unused destructured marker components (e.g. `_layer1`, `_enemy`). The codebase uses this convention consistently — match it for new code.
- **Imports must be sorted** (stdlib → third-party → local), so don't hand-organize import blocks; let `--fix` do it.
- **`from collections.abc import Callable`**, not `from typing import Callable` (UP035).

**Known noise to ignore:**

- Pylance (the VS Code Python extension) flags `_`-prefixed unused vars too, even though Ruff considers them intentional. Either ignore the squiggles or silence them in user settings: `"python.analysis.diagnosticSeverityOverrides": { "reportUnusedVariable": "none" }`.
- `enemies.py:33` carries a `# type: ignore[call-overload]` because esper's `get_components` only declares overloads for arity 2–4 — see the "esper Conventions" section.

### Difficulty Scaling

Difficulty increases automatically: every 10 enemy spawns, the spawn interval decreases by 0.5 seconds (min 0.5s). To adjust, modify the interval calculation in `EnemySpawnProcessor.process()` in `/src/orbitrl/enemies.py`.

## Agent skills

### Issue tracker

Issues live in GitHub Issues at `github.com/tylerhanks/orbitRL`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary — `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo — one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

