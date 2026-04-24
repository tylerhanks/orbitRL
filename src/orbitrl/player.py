import esper
import pygame as pg
from dataclasses import dataclass as component

from orbitrl.core import Score, PolarPosition, PolarVelocity
from orbitrl.config import INNER_RING_RADIUS, MIDDLE_RING_RADIUS, OUTER_RING_RADIUS


@component
class Player:
    alive: bool = True
    zone: int = 0


class PlayerZoneProcessor(esper.Processor):
    def process(self, dt):
        for ent, (player, polar_pos, polar_vel) in esper.get_components(Player, PolarPosition, PolarVelocity):
            if polar_pos.r < INNER_RING_RADIUS:
                polar_vel.theta_dot = -4.7
                player.zone = 4
            elif polar_pos.r < MIDDLE_RING_RADIUS:
                polar_vel.theta_dot = -3.3
                player.zone = 2
            elif polar_pos.r < OUTER_RING_RADIUS:
                polar_vel.theta_dot = -2.0
                player.zone = 1
            else:
                player.alive = False

class InputProcessor(esper.Processor):
    def process(self, dt):
        keys = pg.key.get_pressed()
        for ent, (player, polar_vel) in esper.get_components(Player, PolarVelocity):
            if keys[pg.K_SPACE]:
                polar_vel.r_dot = 200.0
            else:
                polar_vel.r_dot = -100.0


class ScoreProcessor(esper.Processor):
    def __init__(self):
        super().__init__()
        self.score_tracker = 0.0

    def process(self, dt):
        for ent, (score, player) in esper.get_components(Score, Player):
            self.score_tracker += player.zone * dt
            if self.score_tracker >= 1.0:
                score.value += 1
                self.score_tracker = 0.0


class GameOverProcessor(esper.Processor):
    def process(self, dt):
        for ent, player in esper.get_component(Player):
            if not player.alive:
                print("Game Over!")
                pg.quit()
                exit()