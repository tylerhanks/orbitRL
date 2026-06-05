from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

import esper
import numpy as np
import pygame as pg

from orbitrl.core import (
    Circle,
    Layer2,
    PolarPosition,
    PolarVelocity,
    Position,
    RenderProcessor,
    Score,
)
from orbitrl.enemies import Enemy, EnemySpawnProcessor, EnemyType
from orbitrl.player import Player, ScoreTracker
from orbitrl.scenes import RL_WORLD
from orbitrl.simulation import setup_simulation_processors, spawn_black_hole

# esper's always-present startup World, used as a scratch context when we need to
# step off our own world to delete and rebuild it.
_DEFAULT_WORLD = "default"

DEFAULT_AGENT_COUNT = 5

AGENT_PALETTE: list[pg.Color] = [
    pg.Color("cyan"),
    pg.Color("magenta"),
    pg.Color("green"),
    pg.Color("white"),
    pg.Color("pink"),
]

# Control semantics, mirroring InputProcessor: hold = push outward, release = fall inward.
HOLD_R_DOT = 200.0
RELEASE_R_DOT = -100.0

# Anti-camping timeout (opt-in via OrbitSim(camp_timeout=True)). The action space is binary
# (hold/release), so a "stationary" agent is really bang-bang oscillating in a tight radial
# band -- we detect it as a small max-min spread of r over a sliding window. A real dodger
# sweeps across zones and never trips this. Tune these after watching a few generations.
CAMP_WINDOW_TICKS = 300  # ~5 s at dt = 1/60
CAMP_BAND = 20.0  # max-min of r (units) below this over a full window = camping
CAMP_PENALTY = 50  # score subtracted at camping-death


@dataclass
class EnemyObs:
    r: float
    theta: float
    radius: float
    speed: float


@dataclass
class Observation:
    r: float
    theta: float
    r_dot: float
    zone: int
    alive: bool
    enemies: list[EnemyObs] = field(default_factory=list)


Policy = Callable[[Observation], bool]


class OrbitSim:
    """Headless, steppable Environment over the simulation spine for one episode of N agents.

    esper is a global singleton, so OrbitSim manages a *named* esper world. Each world
    carries its own component cache, so the only thing OrbitSim must guarantee is that its
    world is the active one before it touches esper -- it does not need to clear the cache
    (esper invalidates it on every mutation). _enter() switches only when some other code
    has changed the active world, so the common single-sim hot loop pays just a compare.

    Do not drive an OrbitSim from inside another world's esper.process (no nested stepping).
    Concurrent instances (e.g. a vectorized trainer) must each get a distinct `world` name;
    two sims sharing a name alias the same esper world.
    """

    def __init__(
        self,
        n_agents: int = DEFAULT_AGENT_COUNT,
        *,
        dt: float = 1.0 / 60.0,
        seed: int | None = None,
        world: str = RL_WORLD,
        camp_timeout: bool = False,
    ) -> None:
        self.n = n_agents
        self.dt = dt
        self.world = world
        self.camp_timeout = camp_timeout
        self.rng = np.random.default_rng(seed)
        self._agents: list[int] = []
        self._camp_windows: list[deque[float]] = []
        self._prev_scores: list[int] = [0] * n_agents
        self._renderer: RenderProcessor | None = None
        self._build()

    # -- lifecycle ---------------------------------------------------------

    def _enter(self) -> None:
        if esper.current_world != self.world:
            esper.switch_world(self.world)

    def _build(self) -> None:
        # Start from a clean world: delete any prior generation's world (entities AND
        # processors), then re-create it empty.
        if self.world in esper.list_worlds():
            if esper.current_world == self.world:
                esper.switch_world(_DEFAULT_WORLD)  # can't delete the active world
            esper.delete_world(self.world)

        esper.switch_world(self.world)
        spawn_black_hole()
        self._spawn_agents()
        setup_simulation_processors(rng=self.rng)

    def _spawn_agents(self) -> None:
        self._agents = []
        for i in range(self.n):
            theta = (2.0 * np.pi * i) / self.n if self.n > 0 else 0.0
            color = AGENT_PALETTE[i % len(AGENT_PALETTE)]
            ent = esper.create_entity(
                PolarPosition(r=200.0, theta=theta),
                PolarVelocity(r_dot=0.0, theta_dot=-2.5),
                Position(),
                Circle(radius=12.0, color=color),
                Player(),
                Layer2(),
                Score(),
                ScoreTracker(),
            )
            self._agents.append(ent)
        self._camp_windows = [deque(maxlen=CAMP_WINDOW_TICKS) for _ in self._agents]
        self._prev_scores = [0] * self.n

    def reset(self, seed: int | None = None) -> list[Observation | None]:
        self._enter()

        if seed is not None:
            self.rng = np.random.default_rng(seed)

        # Delete enemies (Enemy + PolarVelocity) and the current agents; the black hole
        # has no PolarVelocity so it survives, as do the registered processors.
        for ent, (_enemy, _vel) in list(esper.get_components(Enemy, PolarVelocity)):
            esper.delete_entity(ent, immediate=True)
        for ent in list(self._agents):
            esper.delete_entity(ent, immediate=True)

        spawner = esper.get_processor(EnemySpawnProcessor)
        if isinstance(spawner, EnemySpawnProcessor):
            spawner.reset()
            spawner.rng = self.rng

        self._spawn_agents()
        return self._observe()

    # -- stepping ----------------------------------------------------------

    def step(self, actions: list[bool]) -> tuple[list[Observation | None], list[float], list[bool], bool]:
        self._enter()

        self._apply(actions)
        esper.process(self.dt)
        if self.camp_timeout:
            self._check_camping()

        obs = self._observe()
        scores = self._scores()
        rewards = [float(scores[i] - self._prev_scores[i]) for i in range(self.n)]
        dones = [not esper.component_for_entity(ent, Player).alive for ent in self._agents]
        self._prev_scores = scores
        all_done = all(dones)
        return obs, rewards, dones, all_done

    def _apply(self, actions: list[bool]) -> None:
        for action, ent in zip(actions, self._agents, strict=True):
            player = esper.component_for_entity(ent, Player)
            if not player.alive:
                continue
            polar_vel = esper.component_for_entity(ent, PolarVelocity)
            polar_vel.r_dot = HOLD_R_DOT if action else RELEASE_R_DOT

    def _check_camping(self) -> None:
        # Kill any living agent whose radius has stayed inside CAMP_BAND for a full window,
        # mirroring collision/ring death (alive=False, velocity zeroed) plus a score penalty.
        for ent, window in zip(self._agents, self._camp_windows, strict=True):
            player = esper.component_for_entity(ent, Player)
            if not player.alive:
                continue
            window.append(esper.component_for_entity(ent, PolarPosition).r)
            if len(window) == window.maxlen and (max(window) - min(window)) < CAMP_BAND:
                player.alive = False
                pv = esper.component_for_entity(ent, PolarVelocity)
                pv.r_dot = 0.0
                pv.theta_dot = 0.0
                esper.component_for_entity(ent, Score).value -= CAMP_PENALTY

    # -- observation -------------------------------------------------------

    def _observe(self) -> list[Observation | None]:
        enemies = self._enemy_obs()
        obs: list[Observation | None] = []
        for ent in self._agents:
            player = esper.component_for_entity(ent, Player)
            if not player.alive:
                obs.append(None)
                continue
            pp = esper.component_for_entity(ent, PolarPosition)
            pv = esper.component_for_entity(ent, PolarVelocity)
            obs.append(
                Observation(
                    r=pp.r,
                    theta=pp.theta,
                    r_dot=pv.r_dot,
                    zone=player.zone,
                    alive=True,
                    enemies=enemies,
                )
            )
        return obs

    def _enemy_obs(self) -> list[EnemyObs]:
        # The black hole carries Enemy but no EnemyType, so it is excluded.
        result: list[EnemyObs] = []
        for _ent, (_enemy, _etype, pp, pv, circle) in esper.get_components(  # type: ignore[call-overload]
            Enemy, EnemyType, PolarPosition, PolarVelocity, Circle
        ):
            result.append(EnemyObs(r=pp.r, theta=pp.theta, radius=circle.radius, speed=pv.r_dot))
        return result

    def _scores(self) -> list[int]:
        return [esper.component_for_entity(ent, Score).value for ent in self._agents]

    # -- inspection / rendering -------------------------------------------

    @property
    def scores(self) -> list[int]:
        self._enter()
        return self._scores()

    @property
    def living(self) -> int:
        self._enter()
        return sum(1 for ent in self._agents if esper.component_for_entity(ent, Player).alive)

    def render(self, surface: pg.Surface) -> None:
        self._enter()
        if self._renderer is None:
            self._renderer = RenderProcessor(surface, show_score=False)
        self._renderer.process(0.0)


def flatten(obs: Observation | None, k: int) -> np.ndarray:
    """Convenience: own state + the k nearest enemies as a fixed-size float32 vector.

    The Environment never calls this -- featurization is a trainer concern. Dead agents
    (obs is None) flatten to zeros.
    """
    width = 5 + 4 * k
    if obs is None:
        return np.zeros(width, dtype=np.float32)

    own = np.array([obs.r, obs.theta, obs.r_dot, float(obs.zone), float(obs.alive)], dtype=np.float32)

    def distance(e: EnemyObs) -> float:
        # dr = abs(e.r - obs.r)
        # How far the player must travel before its theta reaches the enemy's theta.
        # theta_dot is always negative, so the player moves toward decreasing theta.
        # ahead ∈ [0, 2π): near-zero = just ahead, near-2π = just behind.
        ahead = (obs.theta - e.theta) % (2.0 * np.pi)
        # Enemies behind (ahead > π) are penalized with a +2π offset so any forward
        # enemy is always ranked closer than any behind enemy in the angular component.
        angular_dist = ahead if ahead <= np.pi else ahead + 2.0 * np.pi
        # return float(dr + angular_dist)
        return angular_dist

    nearest = sorted(obs.enemies, key=distance)[:k]
    enemy_feats = np.zeros(4 * k, dtype=np.float32)
    for i, e in enumerate(nearest):
        ahead = (obs.theta - e.theta) % (2.0 * np.pi)
        angular_dist = ahead if ahead <= np.pi else ahead + 2.0 * np.pi
        dr = abs(e.r - obs.r)
        enemy_feats[4 * i : 4 * i + 4] = (angular_dist, dr, e.radius, e.speed)
    return np.concatenate([own, enemy_feats])
