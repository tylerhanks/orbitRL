from dataclasses import dataclass as component

import esper
import pygame as pg
import pygame_gui as gui

from orbitrl.config import SCREEN_HEIGHT, SCREEN_WIDTH
from orbitrl.scenes import (
    FrameEvents,
    GAME_WORLD,
    HIGHSCORES_WORLD,
    MAIN_MENU_WORLD,
    WorldSwitchRequest,
    request_world_switch,
)


@component
class MainMenu:
    manager: gui.UIManager
    play_button: gui.elements.UIButton
    highscores_button: gui.elements.UIButton


@component
class HighscoresMenu:
    manager: gui.UIManager
    back_button: gui.elements.UIButton


class MainMenuProcessor(esper.Processor):
    def __init__(self, screen: pg.Surface):
        super().__init__()
        self.screen = screen

    def process(self, dt: float) -> None:
        for _ent, (menu, frame_events) in esper.get_components(MainMenu, FrameEvents):
            for event in frame_events.events:
                menu.manager.process_events(event)
                if event.type == gui.UI_BUTTON_PRESSED:
                    if event.ui_element == menu.play_button:
                        request_world_switch(GAME_WORLD)
                    elif event.ui_element == menu.highscores_button:
                        request_world_switch(HIGHSCORES_WORLD)

            menu.manager.update(dt)
            menu.manager.draw_ui(self.screen)


class HighscoresProcessor(esper.Processor):
    def __init__(self, screen: pg.Surface):
        super().__init__()
        self.screen = screen

    def process(self, dt: float) -> None:
        for _ent, (menu, frame_events) in esper.get_components(HighscoresMenu, FrameEvents):
            for event in frame_events.events:
                menu.manager.process_events(event)
                if event.type == gui.UI_BUTTON_PRESSED and event.ui_element == menu.back_button:
                    request_world_switch(MAIN_MENU_WORLD)

            menu.manager.update(dt)
            menu.manager.draw_ui(self.screen)


def setup_main_menu(screen: pg.Surface) -> None:
    manager = gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT))
    title_rect = pg.Rect((0, 120), (SCREEN_WIDTH, 64))
    play_rect = pg.Rect((SCREEN_WIDTH // 2 - 120, 250), (240, 56))
    highscores_rect = pg.Rect((SCREEN_WIDTH // 2 - 120, 326), (240, 56))

    gui.elements.UILabel(
        relative_rect=title_rect,
        text="orbitRL",
        manager=manager,
    )
    play_button = gui.elements.UIButton(
        relative_rect=play_rect,
        text="Play",
        manager=manager,
    )
    highscores_button = gui.elements.UIButton(
        relative_rect=highscores_rect,
        text="Highscores",
        manager=manager,
    )

    menu_entity = esper.create_entity()
    esper.add_component(
        menu_entity,
        MainMenu(
            manager=manager,
            play_button=play_button,
            highscores_button=highscores_button,
        ),
    )
    esper.add_component(menu_entity, FrameEvents())
    esper.add_component(menu_entity, WorldSwitchRequest())
    esper.add_processor(MainMenuProcessor(screen))


def setup_highscores_menu(screen: pg.Surface) -> None:
    manager = gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT))
    title_rect = pg.Rect((0, 150), (SCREEN_WIDTH, 52))
    message_rect = pg.Rect((SCREEN_WIDTH // 2 - 180, 230), (360, 48))
    back_rect = pg.Rect((SCREEN_WIDTH // 2 - 100, 326), (200, 52))

    gui.elements.UILabel(
        relative_rect=title_rect,
        text="Highscores",
        manager=manager,
    )
    gui.elements.UILabel(
        relative_rect=message_rect,
        text="Coming soon",
        manager=manager,
    )
    back_button = gui.elements.UIButton(
        relative_rect=back_rect,
        text="Back",
        manager=manager,
    )

    menu_entity = esper.create_entity()
    esper.add_component(
        menu_entity,
        HighscoresMenu(
            manager=manager,
            back_button=back_button,
        ),
    )
    esper.add_component(menu_entity, FrameEvents())
    esper.add_component(menu_entity, WorldSwitchRequest())
    esper.add_processor(HighscoresProcessor(screen))
