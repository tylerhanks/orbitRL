import os

# Run pygame headless. Must be set before pygame is imported anywhere.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import esper  # noqa: E402
import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from orbitrl.config import SCREEN_HEIGHT, SCREEN_WIDTH  # noqa: E402

_DEFAULT_WORLD = "default"


@pytest.fixture(autouse=True)
def clean_esper():
    """Reset esper's global singleton between tests.

    esper keeps worlds, entities, and processors in module-level state, so without
    this every test would inherit the previous one's worlds.
    """
    yield
    esper.switch_world(_DEFAULT_WORLD)
    for world in esper.list_worlds():
        if world != _DEFAULT_WORLD:
            esper.delete_world(world)
    esper.clear_database()


@pytest.fixture(scope="session")
def screen():
    """A real (dummy-driver) display surface for tests that render or build GUI."""
    pg.init()
    surface = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    yield surface
    pg.quit()
