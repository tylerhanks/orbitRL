import esper
import pygame as pg
import numpy as np
from dataclasses import dataclass as component, field

from orbitrl.config import CENTER_X, CENTER_Y, OUTER_RING_RADIUS, MIDDLE_RING_RADIUS, INNER_RING_RADIUS

@component
class Position:
    x: float = CENTER_X
    y: float = CENTER_Y

@component
class PolarPosition:
    r: float = 0.0
    theta: float = 0.0

@component
class PolarVelocity:
    r_dot: float = 0.0
    theta_dot: float = 0.0

@component
class Circle:
    radius: float = 10.0
    color: pg.Color = field(default_factory=lambda: pg.Color("black"))

@component
class Layer1:
    pass

@component
class Layer2:
    pass

@component
class Score:
    value: int = 0

@component
class GameplayPaused:
    pass

def gameplay_paused() -> bool:
    return bool(esper.get_component(GameplayPaused))

class MovementProcessor(esper.Processor):
    def process(self, dt):
        if gameplay_paused():
            return

        for ent, (polar_pos, polar_vel) in esper.get_components(PolarPosition, PolarVelocity):
            polar_pos.r += polar_vel.r_dot * dt
            polar_pos.theta += polar_vel.theta_dot * dt
            polar_pos.theta = polar_pos.theta % (2 * np.pi)  # wrap theta to [0, 2pi]

class PolarToCartesianProcessor(esper.Processor):
    def process(self, dt):
        if gameplay_paused():
            return

        for ent, (polar, pos) in esper.get_components(PolarPosition, Position):
            pos.x = polar.r * np.cos(polar.theta) + CENTER_X
            pos.y = polar.r * np.sin(polar.theta) + CENTER_Y

class RenderProcessor(esper.Processor):
    def __init__(self, screen: pg.Surface):
        super().__init__()
        self.screen = screen
        self.font = pg.font.SysFont(None, 36)
        self.background = pg.Surface(screen.get_size(), pg.SRCALPHA)
        self.score_value = None
        self.score_text = None
        self._white = pg.Color("white")

        pg.draw.circle(self.background, pg.Color(82, 55, 115), (int(CENTER_X), int(CENTER_Y)), OUTER_RING_RADIUS)
        pg.draw.circle(self.background, pg.Color(116, 78, 163, a=10), (int(CENTER_X), int(CENTER_Y)), MIDDLE_RING_RADIUS)
        pg.draw.circle(self.background, pg.Color(148, 100, 209, a=10), (int(CENTER_X), int(CENTER_Y)), INNER_RING_RADIUS)

    def process(self, dt):
        self.screen.blit(self.background, (0, 0))

        self.screen.lock()
        for ent, (layer1, pos, circle) in esper.get_components(Layer1, Position, Circle):
            pg.draw.circle(self.screen, circle.color, (int(pos.x), int(pos.y)), int(circle.radius))
        for ent, (layer2, pos, circle) in esper.get_components(Layer2, Position, Circle):
            pg.draw.circle(self.screen, circle.color, (int(pos.x), int(pos.y)), int(circle.radius))
        self.screen.unlock()

        for ent, (score) in esper.get_component(Score):
            if score.value != self.score_value:
                self.score_value = score.value
                self.score_text = self.font.render(f"Score: {score.value}", True, self._white)

            if self.score_text is not None:
                self.screen.blit(self.score_text, (10, 10))
