import numpy as np
import pygame as pg

from orbitrl.environment import DEFAULT_AGENT_COUNT, OrbitSim, Policy


class RLLab:
    """Pygame adapter that renders an OrbitSim driven by default random policies.

    This is the watch-it-run demo: it owns the policies, the episode counter, and the
    HUD, and drives the Environment one tick per frame -- resetting on its own when an
    episode ends. A real trainer is the other adapter over the same Environment.
    """

    def __init__(self, surface: pg.Surface, n: int = DEFAULT_AGENT_COUNT, seed: int | None = None):
        self.sim = OrbitSim(n, seed=seed)
        self._rng = np.random.default_rng()  # policy randomness (demo only)
        self.policies: list[Policy] = [self._random_policy() for _ in range(n)]
        self.obs = self.sim.reset()
        self.episode = 1
        self.font = pg.font.SysFont(None, 28)
        self._white = pg.Color("white")

    def _random_policy(self) -> Policy:
        rng = self._rng
        return lambda _obs: rng.random() < 0.3

    def tick(self, surface: pg.Surface) -> None:
        actions = [
            policy(obs) if obs is not None else False
            for policy, obs in zip(self.policies, self.obs, strict=True)
        ]
        self.obs, _rewards, _dones, all_done = self.sim.step(actions)

        if all_done:
            print(f"[episode {self.episode}] scores: {self.sim.scores}")
            self.episode += 1
            self.obs = self.sim.reset()

        self.sim.render(surface)
        self._draw_hud(surface)

    def _draw_hud(self, surface: pg.Surface) -> None:
        living_text = self.font.render(f"Living: {self.sim.living} / {self.sim.n}", True, self._white)
        episode_text = self.font.render(f"Episode: {self.episode}", True, self._white)
        surface.blit(living_text, (10, 10))
        surface.blit(episode_text, (10, 36))
