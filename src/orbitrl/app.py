import pygame as pg
import esper

from orbitrl.config import SCREEN_WIDTH, SCREEN_HEIGHT
from orbitrl.setup import setup_game

def main() -> None:
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pg.time.Clock()
    running = True
    dt = 0.0

    setup_game(screen)

    while running:
        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

        # fill the screen with a color to wipe away anything from last frame
        screen.fill(pg.Color(55, 30, 87, a=255))

        # RENDER YOUR GAME HERE
        esper.process(dt)

        # flip() the display to put your work on screen
        pg.display.flip()

        dt = clock.tick(60) / 1000.0  # limits FPS to 60

    pg.quit()

