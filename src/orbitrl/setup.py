import esper

from orbitrl.core import *
from orbitrl.player import *
from orbitrl.enemies import *

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
        for ent, player in esper.get_component(Player):
            if not player.alive:
                esper.clear_database()
                setup_entities()