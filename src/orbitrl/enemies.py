import esper
import numpy as np
from dataclasses import dataclass as component

from orbitrl.core import Position, Circle, PolarPosition, PolarVelocity, Layer1
from orbitrl.player import Player

@component
class Enemy:
    pass

class CollisionProcessor(esper.Processor):
    def process(self, dt):
        for ent1, (player, player_pos, player_circle) in esper.get_components(Player, Position, Circle):
            for ent2, (enemy, enemy_pos, enemy_circle) in esper.get_components(Enemy, Position, Circle):
                dx = player_pos.x - enemy_pos.x
                dy = player_pos.y - enemy_pos.y
                distance = np.sqrt(dx * dx + dy * dy)
                if distance < player_circle.radius + enemy_circle.radius:
                    player.alive = False

class EnemySpawnProcessor(esper.Processor):
    def __init__(self):
        super().__init__()
        self.spawn_timer = 0.0

    def process(self, dt):
        self.spawn_timer += dt
        if self.spawn_timer >= 4.0:
            self.spawn_timer = 0.0
            enemy = esper.create_entity()
            esper.add_component(enemy, PolarPosition(r=400.0, theta=np.random.uniform(0, 2 * np.pi)))
            esper.add_component(enemy, Position())
            esper.add_component(enemy, Circle(radius=15.0, color="red"))
            esper.add_component(enemy, Enemy())
            esper.add_component(enemy, PolarVelocity(r_dot=-40.0, theta_dot = 0.0))
            esper.add_component(enemy, Layer1())

class EnemyDespawnProcessor(esper.Processor):
    def process(self, dt):
        for ent, (enemy, polar_pos) in esper.get_components(Enemy, PolarPosition):
            if polar_pos.r < 0.0:
                esper.delete_entity(ent)