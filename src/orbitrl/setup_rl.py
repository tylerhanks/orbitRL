import esper
import pygame as pg

from orbitrl.ai import (
    DEFAULT_AGENT_COUNT,
    AIActionProcessor,
    RLEpisodeProcessor,
    RLHudProcessor,
    spawn_ai_agents,
)
from orbitrl.core import RenderProcessor
from orbitrl.simulation import setup_simulation_processors, spawn_black_hole


def setup_rl_entities():
    spawn_black_hole()
    spawn_ai_agents(DEFAULT_AGENT_COUNT)


def setup_rl_processors(screen: pg.Surface):
    episode_processor = RLEpisodeProcessor(agent_count=DEFAULT_AGENT_COUNT)

    setup_simulation_processors()
    esper.add_processor(AIActionProcessor())
    esper.add_processor(episode_processor)
    esper.add_processor(RenderProcessor(screen, show_score=False), priority=1)
    esper.add_processor(RLHudProcessor(screen, episode_processor), priority=1)


def setup_rl(screen: pg.Surface):
    setup_rl_entities()
    setup_rl_processors(screen)
