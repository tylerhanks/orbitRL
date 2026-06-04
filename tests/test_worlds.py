import esper

from orbitrl.core import Score
from orbitrl.player import Player
from orbitrl.scenes import GAME_WORLD, switch_world
from orbitrl.setup import setup_game

# Priority order esper runs in the game world: priority 2 (Input), priority 1 (Render),
# then the priority-0 group in registration order -- the simulation spine contiguous,
# with GameOver registered after it (candidate-4 regression guard).
EXPECTED_GAME_PROCESSORS = [
    "InputProcessor",
    "RenderProcessor",
    "PolarToCartesianProcessor",
    "MovementProcessor",
    "CollisionProcessor",
    "EnemySpawnProcessor",
    "EnemyDespawnProcessor",
    "DeadEnemyProcessor",
    "PlayerZoneProcessor",
    "ScoreProcessor",
    "GameOverProcessor",
]


def test_game_world_steps_on_the_spine(screen):
    switch_world(GAME_WORLD)
    setup_game(screen)

    for _ in range(120):
        esper.process(1.0 / 60.0)

    assert esper.get_component(Player), "expected a Player entity"
    assert esper.get_component(Score), "expected a Score entity"


def test_game_world_processor_order(screen):
    switch_world(GAME_WORLD)
    setup_game(screen)

    order = [type(p).__name__ for p in esper._processors]
    assert order == EXPECTED_GAME_PROCESSORS
