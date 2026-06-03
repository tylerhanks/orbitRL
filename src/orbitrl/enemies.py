import esper
import numpy as np
import pygame as pg
from dataclasses import dataclass as component

from orbitrl.core import Position, Circle, PolarPosition, PolarVelocity, Layer1, Score, gameplay_paused
from orbitrl.player import Player

@component
class Enemy:
    alive: bool = True

@component
class EnemyType:
    color: str

@component
class NearMissAwarded:
    pass

_COLOR_RED = pg.Color("red")
_COLOR_ORANGE = pg.Color("orange")
_COLOR_YELLOW = pg.Color("yellow")

class CollisionProcessor(esper.Processor):
    def process(self, dt):
        if gameplay_paused():
            return

        for ent1, (player, player_pos, player_circle, score) in esper.get_components(Player, Position, Circle, Score):
            if not player.alive:
                continue

            for ent2, (enemy, enemy_pos, enemy_circle) in esper.get_components(Enemy, Position, Circle):
                dx = player_pos.x - enemy_pos.x
                dy = player_pos.y - enemy_pos.y
                distance_squared = dx * dx + dy * dy
                collision_radius = player_circle.radius + enemy_circle.radius
                near_miss_radius = collision_radius + 20.0

                if distance_squared < collision_radius * collision_radius:
                    player.alive = False
                elif distance_squared < near_miss_radius * near_miss_radius:
                    if esper.has_component(ent2, NearMissAwarded):
                        continue

                    enemy_type = esper.try_component(ent2, EnemyType)
                    if enemy_type is None:
                        continue

                    if enemy_type.color == "red":
                        score.value += 5
                    elif enemy_type.color == "orange":
                        score.value += 10
                    elif enemy_type.color == "yellow":
                        score.value += 20
                    esper.add_component(ent2, NearMissAwarded())

def spawn_enemy():
    enemy_type = np.random.choice([1, 2, 3])
    if enemy_type == 1:
        enemy_color_name = "red"
        enemy_color = _COLOR_RED
        enemy_radius = 30.0
        enemy_speed = -40.0
    elif enemy_type == 2:
        enemy_color_name = "orange"
        enemy_color = _COLOR_ORANGE
        enemy_radius = 20.0
        enemy_speed = -70.0
    else:
        enemy_color_name = "yellow"
        enemy_color = _COLOR_YELLOW
        enemy_radius = 10.0
        enemy_speed = -150.0

    esper.create_entity(
        PolarPosition(r=400.0, theta=np.random.uniform(0, 2 * np.pi)),
        Position(),
        Enemy(),
        Layer1(),
        Circle(radius=enemy_radius, color=enemy_color),
        PolarVelocity(r_dot=enemy_speed, theta_dot=0.0),
        EnemyType(color=enemy_color_name),
    )

class EnemySpawnProcessor(esper.Processor):
    def __init__(self):
        super().__init__()
        self.spawn_timer = 0.0
        self.spawn_interval = 4.0
        self.num_spawns = 0

    def process(self, dt):
        if gameplay_paused():
            return

        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            spawn_enemy()
            self.num_spawns += 1
            if self.num_spawns % 10 == 0:
                self.spawn_interval = max(0.5, self.spawn_interval - 0.5)

class EnemyDespawnProcessor(esper.Processor):
    def process(self, dt):
        if gameplay_paused():
            return

        for ent, (enemy, polar_pos) in esper.get_components(Enemy, PolarPosition):
            if polar_pos.r < 0.0:
                enemy.alive = False

class DeadEnemyProcessor(esper.Processor):
    def process(self, dt):
        if gameplay_paused():
            return

        for ent, enemy in esper.get_component(Enemy):
            if not enemy.alive:
                esper.delete_entity(ent)
