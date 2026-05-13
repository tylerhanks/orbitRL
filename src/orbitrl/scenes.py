from dataclasses import dataclass, field

import esper
import pygame as pg


MAIN_MENU_WORLD = "main_menu"
GAME_WORLD = "game"
HIGHSCORES_WORLD = "highscores"


@dataclass
class FrameEvents:
    events: list[pg.event.Event] = field(default_factory=list)


@dataclass
class WorldSwitchRequest:
    target_world: str | None = None


def switch_world(target_world: str) -> None:
    esper.switch_world(target_world)
    esper.clear_cache()


def set_frame_events(events: list[pg.event.Event]) -> None:
    existing_frame_events = esper.get_component(FrameEvents)
    for _ent, frame_events in existing_frame_events:
        frame_events.events = events

    if existing_frame_events:
        return

    event_entity = esper.create_entity()
    esper.add_component(event_entity, FrameEvents(events))


def request_world_switch(target_world: str) -> None:
    for _ent, request in esper.get_component(WorldSwitchRequest):
        request.target_world = target_world
        return

    for ent, _frame_events in esper.get_component(FrameEvents):
        esper.add_component(ent, WorldSwitchRequest(target_world))
        return

    request_entity = esper.create_entity()
    esper.add_component(request_entity, WorldSwitchRequest(target_world))


def consume_world_switch_request() -> str | None:
    for _ent, request in esper.get_component(WorldSwitchRequest):
        target_world = request.target_world
        request.target_world = None
        return target_world

    return None
