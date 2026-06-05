import esper
import neat
import pygame as pg

from orbitrl.config import SCREEN_HEIGHT, SCREEN_WIDTH
from orbitrl.menu import setup_highscores_menu, setup_main_menu
from orbitrl.neat import NEATLab
from orbitrl.rl_lab import RLLab
from orbitrl.scenes import (
    GAME_WORLD,
    HIGHSCORES_WORLD,
    MAIN_MENU_WORLD,
    RL_WORLD,
    consume_world_switch_request,
    set_frame_events,
    switch_world,
)
from orbitrl.setup import setup_game


def setup_game_world(screen: pg.Surface) -> None:
    if GAME_WORLD in esper.list_worlds():
        if esper.current_world == GAME_WORLD:
            switch_world(MAIN_MENU_WORLD)
        esper.delete_world(GAME_WORLD)

    switch_world(GAME_WORLD)
    setup_game(screen)


def setup_highscores_world(screen: pg.Surface) -> None:
    if HIGHSCORES_WORLD in esper.list_worlds():
        if esper.current_world == HIGHSCORES_WORLD:
            switch_world(MAIN_MENU_WORLD)
        esper.delete_world(HIGHSCORES_WORLD)

    switch_world(HIGHSCORES_WORLD)
    setup_highscores_menu(screen)


def setup_worlds(screen: pg.Surface) -> None:
    switch_world(MAIN_MENU_WORLD)
    esper.clear_database()
    setup_main_menu(screen)

    setup_highscores_world(screen)

    switch_world(MAIN_MENU_WORLD)


def main() -> None:
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pg.time.Clock()
    running = True
    dt = 0.0

    config = neat.Config(
        neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet, neat.DefaultStagnation, "config-orbitrl"
    )

    setup_worlds(screen)

    # The RL Lab scene is driven by an OrbitSim (rl_lab), not by the generic esper.process
    # path the menu/game/highscores worlds use -- esper is a global singleton and the sim
    # manages its own world, so it cannot be stepped through that path.
    # rl_lab: RLLab | None = None
    neat_lab: NEATLab | None = None

    while running:
        events = pg.event.get()
        return_to_menu = False
        for event in events:
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                return_to_menu = esper.current_world != MAIN_MENU_WORLD

        screen.fill(pg.Color(55, 30, 87, a=255))

        if return_to_menu:
            neat_lab = None
            switch_world(MAIN_MENU_WORLD)

        # if rl_lab is not None:
        #    rl_lab.tick(screen)
        if neat_lab is not None:
            neat_lab.tick(screen)
        else:
            set_frame_events(events)
            esper.process(dt)

            target_world = consume_world_switch_request()
            if target_world == GAME_WORLD:
                setup_game_world(screen)
            elif target_world == HIGHSCORES_WORLD:
                setup_highscores_world(screen)
            elif target_world == RL_WORLD:
                # rl_lab = RLLab(screen)
                neat_lab = NEATLab(screen, config, n=200)
            elif target_world:
                switch_world(target_world)

        pg.display.flip()

        dt = clock.tick(60) / 1000.0  # limits FPS to 60

    pg.quit()
