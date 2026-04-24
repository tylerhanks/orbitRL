import esper

from orbitrl.core import *
from orbitrl.player import *
from orbitrl.enemies import *

def setup_game(screen):
    # spawn the black hole
    black_hole = esper.create_entity()
    esper.add_component(black_hole, PolarPosition(r=0.0, theta=0.0))
    esper.add_component(black_hole, Position())
    esper.add_component(black_hole, Circle(radius=50.0, color="black"))
    esper.add_component(black_hole, Enemy())
    esper.add_component(black_hole, Layer2())

    # spawn the player
    player = esper.create_entity()
    esper.add_component(player, PolarPosition(r = 200.0, theta = 0.0))
    esper.add_component(player, PolarVelocity(r_dot = 0.0, theta_dot = -2.5))
    esper.add_component(player, Position())
    esper.add_component(player, Circle(radius=10.0, color="white"))
    esper.add_component(player, Player())
    esper.add_component(player, Layer2())
    esper.add_component(player, Score())

    polar_to_cartesian = PolarToCartesianProcessor()
    movement = MovementProcessor()
    render = RenderProcessor(screen)
    input = InputProcessor()
    game_over = GameOverProcessor()
    collision = CollisionProcessor()
    enemy_spawn = EnemySpawnProcessor()
    enemy_despawn = EnemyDespawnProcessor()
    player_zone = PlayerZoneProcessor()
    score = ScoreProcessor()
    esper.add_processor(polar_to_cartesian)
    esper.add_processor(movement)
    esper.add_processor(collision)
    esper.add_processor(game_over)
    esper.add_processor(enemy_spawn)
    esper.add_processor(enemy_despawn)
    esper.add_processor(player_zone)
    esper.add_processor(score)
    esper.add_processor(render, priority=1)
    esper.add_processor(input, priority=2)