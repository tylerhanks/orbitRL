from dataclasses import dataclass as component

import esper
import pygame as pg
import pygame_gui as gui

from orbitrl.config import SCREEN_HEIGHT, SCREEN_WIDTH
from orbitrl.core import (
    Circle,
    GameplayPaused,
    Layer2,
    MovementProcessor,
    PolarPosition,
    PolarToCartesianProcessor,
    Position,
    RenderProcessor,
    Score,
)
from orbitrl.enemies import (
    CollisionProcessor,
    DeadEnemyProcessor,
    Enemy,
    EnemyDespawnProcessor,
    EnemySpawnProcessor,
)
from orbitrl.highscores import is_highscore, save_highscore
from orbitrl.player import InputProcessor, Player, PlayerZoneProcessor, ScoreProcessor, spawn_player
from orbitrl.scenes import FrameEvents, GAME_WORLD, request_world_switch


@component
class HighscorePrompt:
    manager: gui.UIManager
    score: int
    name_entry: gui.elements.UITextEntryLine
    save_button: gui.elements.UIButton

def setup_entities():
    # spawn the black hole
    black_hole = esper.create_entity()
    esper.add_component(black_hole, PolarPosition(r=0.0, theta=0.0))
    esper.add_component(black_hole, Position())
    esper.add_component(black_hole, Circle(radius=50.0, color="black"))
    esper.add_component(black_hole, Enemy())
    esper.add_component(black_hole, Layer2())

    spawn_player()

def setup_processors(screen):
    esper.add_processor(PolarToCartesianProcessor())
    esper.add_processor(MovementProcessor())
    esper.add_processor(CollisionProcessor())
    esper.add_processor(GameOverProcessor(screen))
    esper.add_processor(EnemySpawnProcessor())
    esper.add_processor(EnemyDespawnProcessor())
    esper.add_processor(DeadEnemyProcessor())
    esper.add_processor(PlayerZoneProcessor())
    esper.add_processor(ScoreProcessor())
    esper.add_processor(RenderProcessor(screen), priority=1)
    esper.add_processor(InputProcessor(), priority=2)


def setup_game(screen):
    setup_entities()
    setup_processors(screen)

class GameOverProcessor(esper.Processor):
    def __init__(self, screen):
        super().__init__()
        self.screen = screen

    def process(self, dt):
        if esper.get_component(HighscorePrompt):
            self.process_highscore_prompt(dt)
            return

        for ent, (player, score) in esper.get_components(Player, Score):
            if not player.alive:
                if is_highscore(score.value):
                    self.open_highscore_prompt(score.value)
                else:
                    self.restart_game()
                return

    def open_highscore_prompt(self, score: int):
        manager = gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT))
        panel_rect = pg.Rect((SCREEN_WIDTH // 2 - 180, SCREEN_HEIGHT // 2 - 130), (360, 260))
        title_rect = pg.Rect((SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 100), (300, 42))
        score_rect = pg.Rect((SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 56), (300, 32))
        entry_rect = pg.Rect((SCREEN_WIDTH // 2 - 130, SCREEN_HEIGHT // 2), (260, 42))
        button_rect = pg.Rect((SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2 + 64), (160, 46))

        gui.elements.UIPanel(relative_rect=panel_rect, manager=manager)
        gui.elements.UILabel(
            relative_rect=title_rect,
            text="New Highscore",
            manager=manager,
        )
        gui.elements.UILabel(
            relative_rect=score_rect,
            text=f"Score: {score}",
            manager=manager,
        )
        name_entry = gui.elements.UITextEntryLine(
            relative_rect=entry_rect,
            manager=manager,
        )
        name_entry.set_text("Player")
        name_entry.focus()
        save_button = gui.elements.UIButton(
            relative_rect=button_rect,
            text="Save",
            manager=manager,
        )

        prompt_entity = esper.create_entity()
        esper.add_component(
            prompt_entity,
            HighscorePrompt(
                manager=manager,
                score=score,
                name_entry=name_entry,
                save_button=save_button,
            ),
        )
        esper.add_component(prompt_entity, FrameEvents())
        esper.add_component(prompt_entity, GameplayPaused())

    def process_highscore_prompt(self, dt):
        for _ent, (prompt, frame_events) in esper.get_components(HighscorePrompt, FrameEvents):
            for event in frame_events.events:
                prompt.manager.process_events(event)
                if event.type == gui.UI_BUTTON_PRESSED and event.ui_element == prompt.save_button:
                    save_highscore(prompt.name_entry.get_text(), prompt.score)
                    self.restart_game()
                    return
                if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                    save_highscore(prompt.name_entry.get_text(), prompt.score)
                    self.restart_game()
                    return

            prompt.manager.update(dt)
            prompt.manager.draw_ui(self.screen)

    def restart_game(self):
        request_world_switch(GAME_WORLD)
