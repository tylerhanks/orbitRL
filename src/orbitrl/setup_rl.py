import esper
import pygame as pg

from orbitrl.ai import (
    DEFAULT_AGENT_COUNT,
    AIActionProcessor,
    RLEpisodeProcessor,
    RLHudProcessor,
    spawn_ai_agents,
)
from orbitrl.core import (
    Circle,
    Layer2,
    MovementProcessor,
    PolarPosition,
    PolarToCartesianProcessor,
    Position,
    RenderProcessor,
)
from orbitrl.enemies import (
    CollisionProcessor,
    DeadEnemyProcessor,
    Enemy,
    EnemyDespawnProcessor,
    EnemySpawnProcessor,
)
from orbitrl.player import PlayerZoneProcessor, ScoreProcessor


def setup_rl_entities():
    black_hole = esper.create_entity()
    esper.add_component(black_hole, PolarPosition(r=0.0, theta=0.0))
    esper.add_component(black_hole, Position())
    esper.add_component(black_hole, Circle(radius=50.0, color=pg.Color("black")))
    esper.add_component(black_hole, Enemy())
    esper.add_component(black_hole, Layer2())

    spawn_ai_agents(DEFAULT_AGENT_COUNT)


def setup_rl_processors(screen: pg.Surface):
    episode_processor = RLEpisodeProcessor(agent_count=DEFAULT_AGENT_COUNT)

    esper.add_processor(PolarToCartesianProcessor())
    esper.add_processor(MovementProcessor())
    esper.add_processor(CollisionProcessor())
    esper.add_processor(EnemySpawnProcessor())
    esper.add_processor(EnemyDespawnProcessor())
    esper.add_processor(DeadEnemyProcessor())
    esper.add_processor(PlayerZoneProcessor())
    esper.add_processor(ScoreProcessor())
    esper.add_processor(AIActionProcessor())
    esper.add_processor(episode_processor)
    esper.add_processor(RenderProcessor(screen, show_score=False), priority=1)
    esper.add_processor(RLHudProcessor(screen, episode_processor), priority=1)


def setup_rl(screen: pg.Surface):
    setup_rl_entities()
    setup_rl_processors(screen)
