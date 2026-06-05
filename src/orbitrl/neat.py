import random
from itertools import count

import neat
import numpy as np
import pygame as pg
from neat.math_util import mean
from neat.reporting import ReporterSet
from pygame import surface

from orbitrl.environment import DEFAULT_AGENT_COUNT, OrbitSim, Policy, flatten


class NEATLab:
    """Pygame adapter that renders an OrbitSim driven by NEAT-evolved policies.

    This is the watch-it-run demo: it owns the policies, the episode counter, and the
    HUD, and drives the Environment one tick per frame -- resetting on its own when an
    episode ends. A real trainer is the other adapter over the same Environment.
    """

    def __init__(self, surface: pg.Surface, config: neat.Config, n: int = DEFAULT_AGENT_COUNT, seed: int | None = None):
        self.sim = OrbitSim(n, seed=seed)
        self.obs = self.sim.reset()
        self.nn_inputs = [flatten(self.obs[i], 5) for i in range(n)]
        self.font = pg.font.SysFont(None, 28)
        self._white = pg.Color("white")

        # Handle random seed for reproducibility
        # Seed parameter takes precedence over config seed
        if seed is None and hasattr(config, "seed"):
            seed = config.seed

        if seed is not None:
            random.seed(seed)

        self.reporters = ReporterSet()
        self.config = config
        stagnation = config.stagnation_type(config.stagnation_config, self.reporters)
        self.reproduction = config.reproduction_type(config.reproduction_config, self.reporters, stagnation)
        if config.fitness_criterion == "max":
            self.fitness_criterion = max
        elif config.fitness_criterion == "min":
            self.fitness_criterion = min
        elif config.fitness_criterion == "mean":
            self.fitness_criterion = mean
        elif not config.no_fitness_termination:
            raise RuntimeError(f"Unexpected fitness_criterion: {config.fitness_criterion!r}")

        # Create a population from scratch, then partition into species.
        # The reproduction.create_new method will set up the innovation tracker
        self.population = self.reproduction.create_new(config.genome_type, config.genome_config, config.pop_size)
        self.species = config.species_set_type(config.species_set_config, self.reporters)
        self.generation = 0
        self.species.speciate(config, self.population, self.generation)

        self.best_genome = None

        self.policies: list[Policy] = [self._neat_policy(genome, config) for genome in self.population.values()]

    def _neat_policy(self, genome: neat.DefaultGenome, config: neat.Config) -> Policy:
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        return lambda obs: net.activate(flatten(obs, 3))[0] > 0.5

    def tick(self, surface: pg.Surface) -> None:
        actions = [
            policy(obs) if obs is not None else False for policy, obs in zip(self.policies, self.obs, strict=True)
        ]
        self.obs, rewards, dones, all_done = self.sim.step(actions)

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

        self.sim.render(surface)
        self._draw_hud(surface)

    def _draw_hud(self, surface: pg.Surface) -> None:
        living_text = self.font.render(f"Living: {self.sim.living} / {self.sim.n}", True, self._white)
        episode_text = self.font.render(f"Generation: {self.generation}", True, self._white)
        surface.blit(living_text, (10, 10))
        surface.blit(episode_text, (10, 36))
