from dataclasses import dataclass as component
from dataclasses import field

import esper
import numpy as np
import pygame as pg

from orbitrl.core import Circle, Layer1, Layer2, PolarPosition, PolarVelocity, Position, Score, gameplay_paused
from orbitrl.player import Player


@component
class Enemy:
    alive: bool = True


@component
class EnemyType:
    color: str


@component
class NearMissAwarded:
    awarded: set[int] = field(default_factory=set)


_COLOR_RED = pg.Color("red")
_COLOR_ORANGE = pg.Color("orange")
_COLOR_YELLOW = pg.Color("yellow")


class CollisionProcessor(esper.Processor):
    def process(self, dt):
        if gameplay_paused():
            return

        for ent1, (player, player_pos, player_circle, score, polar_vel) in esper.get_components(  # type: ignore[call-overload]
            Player, Position, Circle, Score, PolarVelocity
        ):
            if not player.alive:
                continue

            for ent2, (_enemy, enemy_pos, enemy_circle) in esper.get_components(Enemy, Position, Circle):
                dx = player_pos.x - enemy_pos.x
                dy = player_pos.y - enemy_pos.y
                distance_squared = dx * dx + dy * dy
                collision_radius = player_circle.radius + enemy_circle.radius
                near_miss_radius = collision_radius + 20.0

                if distance_squared < collision_radius * collision_radius:
                    player.alive = False
                    polar_vel.r_dot = 0.0
                    polar_vel.theta_dot = 0.0
                elif distance_squared < near_miss_radius * near_miss_radius:
                    awarded = esper.try_component(ent2, NearMissAwarded)
                    if awarded is not None and ent1 in awarded.awarded:
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

                    if awarded is None:
                        esper.add_component(ent2, NearMissAwarded({ent1}))
                    else:
                        awarded.awarded.add(ent1)


def spawn_enemy(rng=None):
    source = rng if rng is not None else np.random
    enemy_type = source.choice([1, 2, 3], p=[0.25, 0.50, 0.25])
    # enemy_type = 2  # for now just spawn standard orange enemies.
    if enemy_type == 1:
        enemy_color_name = "red"
        enemy_color = _COLOR_RED
        enemy_radius = 30.0
        enemy_speed = -50.0
    elif enemy_type == 2:
        enemy_color_name = "orange"
        enemy_color = _COLOR_ORANGE
        enemy_radius = 20.0
        enemy_speed = -80.0
    else:
        enemy_color_name = "yellow"
        enemy_color = _COLOR_YELLOW
        enemy_radius = 10.0
        enemy_speed = -160.0

    esper.create_entity(
        PolarPosition(r=400.0, theta=source.uniform(0, 2 * np.pi)),
        Position(),
        Enemy(),
        Layer2(),
        Circle(radius=enemy_radius, color=enemy_color),
        PolarVelocity(r_dot=enemy_speed, theta_dot=0.0),
        EnemyType(color=enemy_color_name),
    )


class EnemySpawnProcessor(esper.Processor):
    def __init__(self, rng=None):
        super().__init__()
        self.rng = rng
        self.spawn_timer = 0.0
        self.spawn_interval = 2.0
        self.num_spawns = 0

    def reset(self):
        self.spawn_timer = 0.0
        self.spawn_interval = 2.0
        self.num_spawns = 0

    def process(self, dt):
        if gameplay_paused():
            return

        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            spawn_enemy(self.rng)
            self.num_spawns += 1
            if self.num_spawns % 5 == 0:
                self.spawn_interval = max(0.1, self.spawn_interval - 0.5)


class EnemyDespawnProcessor(esper.Processor):
    def process(self, dt):
        if gameplay_paused():
            return

        for _ent, (enemy, polar_pos) in esper.get_components(Enemy, PolarPosition):
            if polar_pos.r < 0.0:
                enemy.alive = False


class DeadEnemyProcessor(esper.Processor):
    def process(self, dt):
        if gameplay_paused():
            return

        for ent, enemy in esper.get_component(Enemy):
            if not enemy.alive:
                esper.delete_entity(ent)
