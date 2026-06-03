# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**orbitRL** is a reinforcement learning game where players learn to play OrbitXL using ML. It's a PyGame-based arcade game where the player controls a white circle orbiting a black hole, dodging colored enemy circles that spawn and move toward the center. The game features three difficulty zones based on orbit radius, a scoring system, and a persistent leaderboard.

## Setup and Commands

### Build and Run

This project uses `uv` (Astral's fast Python package manager) for dependency management.

```bash
# Install dependencies and setup virtual environment
uv sync

# Run the game
uv run orbitrl

# Or use the entry point script
python -m orbitrl
```

### Dependencies

- **esper** (3.7): Entity Component System framework for game logic
- **pygame-ce** (2.5.7): Pygame Community Edition for graphics and input
- **pygame-gui** (0.6.14): GUI library for menus and dialogs
- **numpy** (2.4.4): Numerical operations, used for angle wrapping and math

### Python Version

Requires Python 3.12 or higher.

## High-Level Architecture

The game uses the **Entity Component System (ECS)** pattern via the `esper` library. This architecture decouples data (components) from behavior (processors/systems), making the codebase highly modular and extensible.

### Core Concepts

**Worlds**: The game has three separate ECS worlds managed by `esper`:
- `MAIN_MENU_WORLD`: Main menu interface
- `GAME_WORLD`: Active gameplay
- `HIGHSCORES_WORLD`: Leaderboard display

The app switches between worlds in response to user actions or game events.

**Components** (dataclasses in `/src/orbitrl/core.py`):
- `Position`: Cartesian coordinates (x, y)
- `PolarPosition`: Polar coordinates (r, theta) relative to screen center
- `PolarVelocity`: Polar velocity (r_dot, theta_dot)
- `Circle`: Radius and color for rendering
- `Score`: Current score value
- `Layer1`/`Layer2`: Render layers (enemies on Layer1, player on Layer2)
- `GameplayPaused`: Marks when gameplay is paused

**Processors** (systems that update entities):
- `MovementProcessor`: Updates polar position based on velocity
- `PolarToCartesianProcessor`: Converts polar to Cartesian coordinates
- `RenderProcessor`: Draws circles and background rings; displays score
- `CollisionProcessor`: Detects collisions and near-misses between player and enemies
- `InputProcessor`: Reads keyboard input and updates player radial velocity
- `PlayerZoneProcessor`: Assigns player to difficulty zones based on radius
- `ScoreProcessor`: Increments score based on time spent in zones
- `EnemySpawnProcessor`: Spawns enemies on a timer that accelerates over time
- `EnemyDespawnProcessor`: Removes enemies that have moved past the center
- `DeadEnemyProcessor`: Removes dead entities from the world
- `GameOverProcessor`: Handles game-over state and highscore entry dialog
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
1. Handle pygame events (quit, ESC to return to menu)
2. Clear screen background
3. Set frame events for the current ECS world
4. Process all entities and systems (`esper.process(dt)`)
5. Check for world switch requests (game started, highscores accessed)
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

### File Organization

- `/src/orbitrl/app.py`: Main entry point and world/world-setup management
- `/src/orbitrl/core.py`: ECS components and core processors (movement, rendering, collision)
- `/src/orbitrl/player.py`: Player entity spawning and player-specific processors
- `/src/orbitrl/enemies.py`: Enemy entity spawning and enemy-specific processors
- `/src/orbitrl/scenes.py`: World management and event routing between ECS worlds
- `/src/orbitrl/menu.py`: Menu UI setup and processors (main menu and leaderboard)
- `/src/orbitrl/highscores.py`: Highscore file I/O and validation
- `/src/orbitrl/config.py`: Game constants (screen dimensions, ring radii)
- `/src/orbitrl/setup.py`: Game world initialization (entities and processors)

### Key Design Patterns

**Component-as-Configuration**: ECS components are pure dataclasses; they hold state but no logic. This makes entity composition flexible.

**Processor Priority**: Processors have priority orders:
- Default priority: Standard updates (movement, collision, spawning)
- Priority 1: Rendering (drawn last, so UI overlays properly)
- Priority 2: Input (processed last to consume events)

**World Switching**: Uses a request/consume pattern via `WorldSwitchRequest` component to decouple world switching logic from event handling.

**Frame Events Distribution**: `FrameEvents` component carries pygame events into the ECS, allowing processors to respond to input without tight coupling to pygame.

## Development Notes

### Adding New Features

**New gameplay mechanic**: Add a processor to `/src/orbitrl/core.py` or create a new module. Register it in `setup_processors()` in `/src/orbitrl/setup.py`.

**New enemy type**: Modify `spawn_enemy()` in `/src/orbitrl/enemies.py` to add new enemy variants. Update `CollisionProcessor` if scoring for the type differs.

**New UI screen**: Create a world in `/src/orbitrl/scenes.py`, setup function, and processor in `/src/orbitrl/menu.py` (or a new module). Register the world constant and add switching logic in `/src/orbitrl/app.py`.

### Testing

No test framework is currently configured. Add pytest configuration to `pyproject.toml` if needed. Consider mocking the pygame and esper libraries for unit tests.

### Linting

No linter is currently configured. Add Ruff or Flake8 to `pyproject.toml` and `.vscode/settings.json` if desired.

### Difficulty Scaling

Difficulty increases automatically: every 10 enemy spawns, the spawn interval decreases by 0.5 seconds (min 0.5s). To adjust, modify the interval calculation in `EnemySpawnProcessor.process()` in `/src/orbitrl/enemies.py`.

