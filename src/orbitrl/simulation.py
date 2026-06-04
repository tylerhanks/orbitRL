import esper
import pygame as pg

from orbitrl.core import (
    Circle,
    Layer2,
    MovementProcessor,
    PolarPosition,
    PolarToCartesianProcessor,
    Position,
)
from orbitrl.enemies import (
    CollisionProcessor,
    DeadEnemyProcessor,
    Enemy,
    EnemyDespawnProcessor,
    EnemySpawnProcessor,
)
from orbitrl.player import PlayerZoneProcessor, ScoreProcessor


def spawn_black_hole() -> None:
    black_hole = esper.create_entity()
    esper.add_component(black_hole, PolarPosition(r=0.0, theta=0.0))
    esper.add_component(black_hole, Position())
    esper.add_component(black_hole, Circle(radius=50.0, color=pg.Color("black")))
    esper.add_component(black_hole, Enemy())
    esper.add_component(black_hole, Layer2())


def setup_simulation_processors(rng=None) -> None:
    esper.add_processor(PolarToCartesianProcessor())
    esper.add_processor(MovementProcessor())
    esper.add_processor(CollisionProcessor())
    esper.add_processor(EnemySpawnProcessor(rng))
    esper.add_processor(EnemyDespawnProcessor())
    esper.add_processor(DeadEnemyProcessor())
    esper.add_processor(PlayerZoneProcessor())
    esper.add_processor(ScoreProcessor())
