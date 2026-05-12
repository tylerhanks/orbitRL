import pygame as pg
import esper


from orbitrl.config import SCREEN_WIDTH, SCREEN_HEIGHT
from orbitrl.menu import setup_highscores_menu, setup_main_menu
from orbitrl.scenes import (
    GAME_WORLD,
    HIGHSCORES_WORLD,
    MAIN_MENU_WORLD,
    consume_world_switch_request,
    set_frame_events,
    switch_world,
)
from orbitrl.setup import setup_game


def setup_game_world(screen: pg.Surface) -> None:
    if GAME_WORLD in esper.list_worlds() and esper.current_world != GAME_WORLD:
        esper.delete_world(GAME_WORLD)

    switch_world(GAME_WORLD)
    esper.clear_database()
    setup_game(screen)


def setup_worlds(screen: pg.Surface) -> None:
    switch_world(MAIN_MENU_WORLD)
    esper.clear_database()
    setup_main_menu(screen)

    switch_world(HIGHSCORES_WORLD)
    esper.clear_database()
    setup_highscores_menu(screen)

    switch_world(MAIN_MENU_WORLD)


def main() -> None:
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pg.time.Clock()
    running = True
    dt = 0.0

    setup_worlds(screen)

    while running:
        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                running = False

        screen.fill(pg.Color(55, 30, 87, a=255))

        set_frame_events(events)
        esper.process(dt)

        target_world = consume_world_switch_request()
        if target_world == GAME_WORLD:
            setup_game_world(screen)
        elif target_world:
            switch_world(target_world)

        pg.display.flip()

        dt = clock.tick(60) / 1000.0  # limits FPS to 60

    pg.quit()
