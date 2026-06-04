import esper
import pygame as pg
from dataclasses import dataclass as component

from orbitrl.core import Score, PolarPosition, PolarVelocity, Position, Circle, Layer2, gameplay_paused
from orbitrl.config import INNER_RING_RADIUS, MIDDLE_RING_RADIUS, OUTER_RING_RADIUS

@component
class Player:
    alive: bool = True
    zone: int = 0

@component
class ScoreTracker:
    progress: float = 0.0

def spawn_player():
    player = esper.create_entity()
    esper.add_component(player, PolarPosition(r = 200.0, theta = 0.0))
    esper.add_component(player, PolarVelocity(r_dot = 0.0, theta_dot = -2.5))
    esper.add_component(player, Position())
    esper.add_component(player, Circle(radius=12.0, color=pg.Color("white")))
    esper.add_component(player, Player())
    esper.add_component(player, Layer2())
    esper.add_component(player, Score())
    esper.add_component(player, ScoreTracker())


class PlayerZoneProcessor(esper.Processor):
    def process(self, dt):
        if gameplay_paused():
            return

        for ent, (player, polar_pos, polar_vel) in esper.get_components(Player, PolarPosition, PolarVelocity):
            if not player.alive:
                continue
            if polar_pos.r < INNER_RING_RADIUS:
                polar_vel.theta_dot = -4.5
                player.zone = 4
            elif polar_pos.r < MIDDLE_RING_RADIUS:
                polar_vel.theta_dot = -3.0
                player.zone = 2
            elif polar_pos.r < OUTER_RING_RADIUS:
                polar_vel.theta_dot = -2.5
                player.zone = 1
            else:
                player.alive = False
                polar_vel.r_dot = 0.0
                polar_vel.theta_dot = 0.0

class InputProcessor(esper.Processor):
    def process(self, dt):
        if gameplay_paused():
            return

        keys = pg.key.get_pressed()
        for ent, (player, polar_vel) in esper.get_components(Player, PolarVelocity):
            if keys[pg.K_SPACE]:
                polar_vel.r_dot = 200.0
            else:
                polar_vel.r_dot = -100.0


class ScoreProcessor(esper.Processor):
    def process(self, dt):
        if gameplay_paused():
            return

        for ent, (score, tracker, player) in esper.get_components(Score, ScoreTracker, Player):
            if not player.alive:
                continue
            tracker.progress += player.zone * dt
            if tracker.progress >= 1.0:
                score.value += 1
                tracker.progress = 0.0
