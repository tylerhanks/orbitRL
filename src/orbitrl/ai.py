import random
from collections.abc import Callable
from dataclasses import dataclass as component

import esper
import numpy as np
import pygame as pg

from orbitrl.core import (
    Circle,
    Layer2,
    PolarPosition,
    PolarVelocity,
    Position,
    Score,
    gameplay_paused,
)
from orbitrl.enemies import Enemy, EnemySpawnProcessor
from orbitrl.player import Player, ScoreTracker

Observation = None
Policy = Callable[[Observation], bool]

DEFAULT_AGENT_COUNT = 5

AGENT_PALETTE: list[pg.Color] = [
    pg.Color("cyan"),
    pg.Color("magenta"),
    pg.Color("green"),
    pg.Color("white"),
    pg.Color("pink"),
]


def _random_policy_factory(_index: int) -> Policy:
    return lambda _obs: random.random() < 0.3


@component
class AIAgent:
    policy: Policy | None = None


def spawn_ai_agents(
    n: int,
    policy_factory: Callable[[int], Policy] | None = None,
) -> None:
    factory = policy_factory if policy_factory is not None else _random_policy_factory
    for i in range(n):
        theta = (2.0 * np.pi * i) / n if n > 0 else 0.0
        color = AGENT_PALETTE[i % len(AGENT_PALETTE)]
        esper.create_entity(
            PolarPosition(r=200.0, theta=theta),
            PolarVelocity(r_dot=0.0, theta_dot=-2.5),
            Position(),
            Circle(radius=12.0, color=color),
            Player(),
            AIAgent(policy=factory(i)),
            Layer2(),
            Score(),
            ScoreTracker(),
        )


class AIActionProcessor(esper.Processor):
    def process(self, dt):
        if gameplay_paused():
            return

        for _ent, (agent, player, polar_vel) in esper.get_components(AIAgent, Player, PolarVelocity):
            if not player.alive or agent.policy is None:
                continue
            if agent.policy(None):
                polar_vel.r_dot = 200.0
            else:
                polar_vel.r_dot = -100.0


class RLEpisodeProcessor(esper.Processor):
    def __init__(self, agent_count: int = DEFAULT_AGENT_COUNT):
        super().__init__()
        self.agent_count = agent_count
        self.episode_count = 1
        self.living_count = agent_count

    def process(self, dt):
        if gameplay_paused():
            return

        living = 0
        scores: list[int] = []
        for _ent, (_agent, player, score) in esper.get_components(AIAgent, Player, Score):
            scores.append(score.value)
            if player.alive:
                living += 1

        self.living_count = living

        if scores and living == 0:
            print(f"[episode {self.episode_count}] scores: {scores}")
            self.episode_count += 1
            reset_rl_world(agent_count=self.agent_count)
            self.living_count = self.agent_count


def reset_rl_world(
    agent_count: int = DEFAULT_AGENT_COUNT,
    policy_factory: Callable[[int], Policy] | None = None,
) -> None:
    for ent, (_enemy, _vel) in list(esper.get_components(Enemy, PolarVelocity)):
        esper.delete_entity(ent, immediate=True)

    for ent, _agent in list(esper.get_component(AIAgent)):
        esper.delete_entity(ent, immediate=True)

    spawner = esper.get_processor(EnemySpawnProcessor)
    if isinstance(spawner, EnemySpawnProcessor):
        spawner.reset()

    spawn_ai_agents(agent_count, policy_factory)


class RLHudProcessor(esper.Processor):
    def __init__(self, screen: pg.Surface, episode_processor: RLEpisodeProcessor):
        super().__init__()
        self.screen = screen
        self.episode_processor = episode_processor
        self.font = pg.font.SysFont(None, 28)
        self._white = pg.Color("white")
        self._cached_living: int | None = None
        self._cached_episode: int | None = None
        self._living_text: pg.Surface | None = None
        self._episode_text: pg.Surface | None = None

    def process(self, dt):
        living = self.episode_processor.living_count
        total = self.episode_processor.agent_count
        episode = self.episode_processor.episode_count

        if living != self._cached_living:
            self._cached_living = living
            self._living_text = self.font.render(f"Living: {living} / {total}", True, self._white)
        if episode != self._cached_episode:
            self._cached_episode = episode
            self._episode_text = self.font.render(f"Episode: {episode}", True, self._white)

        if self._living_text is not None:
            self.screen.blit(self._living_text, (10, 10))
        if self._episode_text is not None:
            self.screen.blit(self._episode_text, (10, 36))
