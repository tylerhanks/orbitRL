import esper
import numpy as np
from dataclasses import dataclass as component

from orbitrl.core import Position, Circle, PolarPosition, PolarVelocity, Layer1
from orbitrl.player import Player

@component
class Enemy:
    alive: bool = True

class CollisionProcessor(esper.Processor):
    def process(self, dt):
        for ent1, (player, player_pos, player_circle) in esper.get_components(Player, Position, Circle):
            for ent2, (enemy, enemy_pos, enemy_circle) in esper.get_components(Enemy, Position, Circle):
                dx = player_pos.x - enemy_pos.x
                dy = player_pos.y - enemy_pos.y
                distance = np.sqrt(dx * dx + dy * dy)
                if distance < player_circle.radius + enemy_circle.radius:
                    player.alive = False

def spawn_enemy():
    enemy = esper.create_entity()
    esper.add_component(enemy, PolarPosition(r=400.0, theta=np.random.uniform(0, 2 * np.pi)))
    esper.add_component(enemy, Position())
    esper.add_component(enemy, Enemy())
    esper.add_component(enemy, Layer1())

    enemy_type = np.random.choice([1,2,3])
    if enemy_type == 1:
        enemy_color = "red"
        enemy_radius = 30.0
        enemy_speed = -40.0
    elif enemy_type == 2:
        enemy_color = "orange"
        enemy_radius = 20.0
        enemy_speed = -70.0
    else:
        enemy_color = "yellow"
        enemy_radius = 10.0
        enemy_speed = -150.0
    esper.add_component(enemy, Circle(radius=enemy_radius, color=enemy_color))
    esper.add_component(enemy, PolarVelocity(r_dot=enemy_speed, theta_dot = 0.0))

class EnemySpawnProcessor(esper.Processor):
    def __init__(self):
        super().__init__()
        self.spawn_timer = 0.0
        self.spawn_interval = 4.0
        self.num_spawns = 0

    def process(self, dt):
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            spawn_enemy()
            self.num_spawns += 1
            if self.num_spawns % 10 == 0:
                self.spawn_interval = max(0.5, self.spawn_interval - 0.5)

class EnemyDespawnProcessor(esper.Processor):
    def process(self, dt):
        for ent, (enemy, polar_pos) in esper.get_components(Enemy, PolarPosition):
            if polar_pos.r < 0.0:
                enemy.alive = False

class DeadEnemyProcessor(esper.Processor):
    def process(self, dt):
        for ent, enemy in esper.get_component(Enemy):
            if not enemy.alive:
                esper.delete_entity(ent)