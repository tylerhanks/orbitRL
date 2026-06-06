import random
from typing import Any, Protocol, cast

import neat
import pygame as pg
from neat.math_util import mean
from neat.reporting import ReporterSet

from orbitrl.environment import DEFAULT_AGENT_COUNT, OrbitSim, Policy, flatten

# Stable per-species colors: neat-python hands out monotonically increasing species ids and never
# reuses them, so a deterministic id->hue map lets a lineage keep its color across generations.
# The golden-ratio conjugate spreads successive ids around the hue wheel with maximal separation.
_GOLDEN_RATIO_CONJUGATE = 0.61803398875


def _species_color(species_id: int) -> pg.Color:
    c = pg.Color(0)
    c.hsva = ((species_id * _GOLDEN_RATIO_CONJUGATE % 1.0) * 360.0, 65.0, 95.0, 100.0)
    return c


def _dim(color: pg.Color) -> pg.Color:
    """A faded variant of a species color, for dead agents -- same hue, muted saturation/value."""
    h, s, v, _a = color.hsva
    d = pg.Color(0)
    d.hsva = (h, s * 0.4, v * 0.3, 100.0)
    return d


class NeatConfig(Protocol):
    """The subset of ``neat.Config``'s surface that NEATLab reads.

    neat-python sets the ``[NEAT]``-section parameters (pop_size, fitness_criterion, ...)
    via ``setattr`` from a parameter list (see ``neat/config.py``), so they are invisible
    to static analysis on ``neat.Config`` itself. Declaring them here lets us type the
    config precisely after a single ``cast``. The opaque ``*_type`` / ``*_config`` handles
    are passed straight back into neat's own (untyped) calls, so ``Any`` is honest there.
    """

    # Dynamically-set [NEAT]-section parameters.
    pop_size: int
    fitness_criterion: str
    fitness_threshold: float
    reset_on_extinction: bool
    no_fitness_termination: bool
    seed: int | None

    # Opaque component types/configs, forwarded into neat's own (untyped) calls.
    genome_type: Any
    genome_config: Any
    reproduction_type: Any
    reproduction_config: Any
    species_set_type: Any
    species_set_config: Any
    stagnation_type: Any
    stagnation_config: Any


class NEATLab:
    """Pygame adapter that renders an OrbitSim driven by NEAT-evolved policies.

    This is the watch-it-run demo: it owns the policies, the episode counter, and the
    HUD, and drives the Environment one tick per frame -- resetting on its own when an
    episode ends. A real trainer is the other adapter over the same Environment.
    """

    def __init__(self, surface: pg.Surface, config: neat.Config, n: int = DEFAULT_AGENT_COUNT, seed: int | None = None):
        # neat.Config sets its [NEAT]-section params dynamically; view it through the
        # NeatConfig protocol so those attributes are statically known from here on.
        cfg: NeatConfig = cast(NeatConfig, config)

        self.sim = OrbitSim(n, seed=seed, camp_timeout=True)
        self.obs = self.sim.reset()
        self.font = pg.font.SysFont(None, 28)
        self._white = pg.Color("white")

        # Handle random seed for reproducibility
        # Seed parameter takes precedence over config seed
        if seed is None:
            seed = cfg.seed

        if seed is not None:
            random.seed(seed)

        self.reporters = ReporterSet()
        self.config = cfg
        stagnation = cfg.stagnation_type(cfg.stagnation_config, self.reporters)
        self.reproduction = cfg.reproduction_type(cfg.reproduction_config, self.reporters, stagnation)
        if cfg.fitness_criterion == "max":
            self.fitness_criterion = max
        elif cfg.fitness_criterion == "min":
            self.fitness_criterion = min
        elif cfg.fitness_criterion == "mean":
            self.fitness_criterion = mean
        elif not cfg.no_fitness_termination:
            raise RuntimeError(f"Unexpected fitness_criterion: {cfg.fitness_criterion!r}")

        # Create a population from scratch, then partition into species.
        # The reproduction.create_new method will set up the innovation tracker
        self.population = self.reproduction.create_new(cfg.genome_type, cfg.genome_config, cfg.pop_size)
        self.species = cfg.species_set_type(cfg.species_set_config, self.reporters)
        self.generation = 0
        self.species.speciate(cfg, self.population, self.generation)

        self.best_genome: neat.DefaultGenome | None = None

        self.policies: list[Policy] = [self._neat_policy(genome, cfg) for genome in self.population.values()]

        # Per-agent full species color for the current generation, and whether each has been
        # dimmed (on death) since the last recolor.
        self._base_colors: list[pg.Color] = []
        self._dimmed: list[bool] = []
        self._recolor()

    def _recolor(self) -> None:
        """Repaint every agent to its species color and reset dim tracking for a fresh generation.

        Agent i maps positionally to the i-th genome in the population (the same enumeration used
        to assign fitness), so this stays in lockstep with the policies list.
        """
        genomes = list(self.population.values())
        self._base_colors = []
        self._dimmed = [False] * len(genomes)
        for i, genome in enumerate(genomes):
            color = _species_color(self.species.genome_to_species[genome.key])
            self._base_colors.append(color)
            self.sim.set_agent_color(i, color)

    def _neat_policy(self, genome: neat.DefaultGenome, config: NeatConfig) -> Policy:
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        return lambda obs: net.activate(flatten(obs, 5))[0] > 0.5

    def tick(self, surface: pg.Surface) -> None:
        actions = [
            policy(obs) if obs is not None else False for policy, obs in zip(self.policies, self.obs, strict=True)
        ]
        self.obs, _rewards, dones, all_done = self.sim.step(actions)

        # Fade agents that died this tick so the living species stand out.
        for i, done in enumerate(dones):
            if done and not self._dimmed[i]:
                self.sim.set_agent_color(i, _dim(self._base_colors[i]))
                self._dimmed[i] = True

        if all_done:
            print(f"[generation {self.generation}] scores: {self.sim.scores}")
            for i, genome in enumerate(self.population.values()):
                genome.fitness = self.sim.scores[i]

            best = None
            for g in self.population.values():
                if g.fitness is None:
                    raise RuntimeError(f"Fitness not assigned to genome {g.key}")

                # if best is None or self.config.is_better_fitness(g.fitness, best.fitness):
                if best is None or g.fitness > best.fitness:
                    best = g
            assert best is not None  # the population is non-empty, so the loop set best
            self.reporters.post_evaluate(self.config, self.population, self.species, best)

            # Track the best genome ever seen.
            # if self.best_genome is None or self.config.is_better_fitness(best.fitness, self.best_genome.fitness):
            if self.best_genome is None or best.fitness > self.best_genome.fitness:
                self.best_genome = best

            # if not self.config.no_fitness_termination:
            # End if the fitness threshold is reached.
            #    fv = self.fitness_criterion(g.fitness for g in self.population.values())
            #    if self.config.meets_threshold(fv, self.config.fitness_threshold):
            #        self.reporters.found_solution(self.config, self.generation, best)
            #        break

            # Create the next generation from the current generation.
            self.population = self.reproduction.reproduce(
                self.config, self.species, self.config.pop_size, self.generation
            )

            # Check for complete extinction.
            if not self.species.species:
                self.reporters.complete_extinction()

                # If requested by the user, create a completely new population,
                # otherwise raise an exception.
                if self.config.reset_on_extinction:
                    self.population = self.reproduction.create_new(
                        self.config.genome_type, self.config.genome_config, self.config.pop_size
                    )
                else:
                    raise neat.CompleteExtinctionException()

            # Divide the new population into species.
            self.species.speciate(self.config, self.population, self.generation)

            self.reporters.end_generation(self.config, self.population, self.species)

            self.generation += 1

            self.obs = self.sim.reset()
            self.policies = [self._neat_policy(genome, self.config) for genome in self.population.values()]
            self._recolor()

        self.sim.render(surface)
        self._draw_hud(surface)

    def _draw_hud(self, surface: pg.Surface) -> None:
        living_text = self.font.render(f"Living: {self.sim.living} / {self.sim.n}", True, self._white)
        episode_text = self.font.render(f"Generation: {self.generation}", True, self._white)
        surface.blit(living_text, (10, 10))
        surface.blit(episode_text, (10, 36))
