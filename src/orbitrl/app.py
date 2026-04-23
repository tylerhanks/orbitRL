import pygame as pg
import numpy as np
import esper
from dataclasses import dataclass as component

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

CENTER_X = SCREEN_WIDTH / 2
CENTER_Y = SCREEN_HEIGHT / 2

@component
class Position:
    x: float = 0.0
    y: float = 0.0

@component
class PolarPosition:
    r: float = 0.0
    theta: float = 0.0

@component
class Circle:
    radius: float = 10.0
    color: str = "black"

class PolarToCartesianProcessor(esper.Processor):
    def process(self):
        for ent, (polar, pos) in esper.get_components(PolarPosition, Position):
            pos.x = polar.r * np.cos(polar.theta) + CENTER_X
            pos.y = polar.r * np.sin(polar.theta) + CENTER_Y

class DrawCirclesProcessor(esper.Processor):
    def __init__(self, screen: pg.Surface):
        super().__init__()
        self.screen = screen

    def process(self):
        for ent, (pos, circle) in esper.get_components(Position, Circle):
            pg.draw.circle(self.screen, circle.color, (int(pos.x), int(pos.y)), int(circle.radius))


def main() -> None:
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pg.time.Clock()
    running = True

    # spawn a circle entity
    black_hole = esper.create_entity()
    esper.add_component(black_hole, PolarPosition(r=0.0, theta=0.0))
    esper.add_component(black_hole, Position())
    esper.add_component(black_hole, Circle(radius=40.0, color="black"))

    polar_to_cartesian = PolarToCartesianProcessor()
    draw_circles = DrawCirclesProcessor(screen)
    esper.add_processor(polar_to_cartesian)
    esper.add_processor(draw_circles, priority=1)

    while running:
        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

        # fill the screen with a color to wipe away anything from last frame
        screen.fill("purple")

        # RENDER YOUR GAME HERE
        esper.process()

        # flip() the display to put your work on screen
        pg.display.flip()

        clock.tick(60)  # limits FPS to 60

    pg.quit()

