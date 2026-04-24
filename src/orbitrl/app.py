import pygame as pg
import numpy as np
import esper
from dataclasses import dataclass as component

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

CENTER_X = SCREEN_WIDTH / 2
CENTER_Y = SCREEN_HEIGHT / 2

INNER_RING_RADIUS = 120
MIDDLE_RING_RADIUS = 200
OUTER_RING_RADIUS = 270

@component
class Position:
    x: float = CENTER_X
    y: float = CENTER_Y

@component
class PolarPosition:
    r: float = 0.0
    theta: float = 0.0

@component
class PolarVelocity:
    r_dot: float = 0.0
    theta_dot: float = 0.0

@component
class Circle:
    radius: float = 10.0
    color: str = "black"

@component
class Player:
    alive: bool = True
    zone: int = 0

@component
class Enemy:
    pass

@component
class Layer1:
    pass

@component
class Layer2:
    pass

@component
class Score:
    value: int = 0

class ScoreProcessor(esper.Processor):
    def __init__(self):
        super().__init__()
        self.score_tracker = 0.0

    def process(self, dt):
        for ent, (score, player) in esper.get_components(Score, Player):
            self.score_tracker += player.zone * dt
            if self.score_tracker >= 1.0:
                score.value += 1
                self.score_tracker = 0.0

class GameOverProcessor(esper.Processor):
    def process(self, dt):
        for ent, player in esper.get_component(Player):
            if not player.alive:
                print("Game Over!")
                pg.quit()
                exit()

class CollisionProcessor(esper.Processor):
    def process(self, dt):
        for ent1, (player, player_pos, player_circle) in esper.get_components(Player, Position, Circle):
            for ent2, (enemy, enemy_pos, enemy_circle) in esper.get_components(Enemy, Position, Circle):
                dx = player_pos.x - enemy_pos.x
                dy = player_pos.y - enemy_pos.y
                distance = np.sqrt(dx * dx + dy * dy)
                if distance < player_circle.radius + enemy_circle.radius:
                    player.alive = False


class PlayerZoneProcessor(esper.Processor):
    def process(self, dt):
        for ent, (player, polar_pos, polar_vel) in esper.get_components(Player, PolarPosition, PolarVelocity):
            if polar_pos.r < INNER_RING_RADIUS:
                polar_vel.theta_dot = -4.7
                player.zone = 4
            elif polar_pos.r < MIDDLE_RING_RADIUS:
                polar_vel.theta_dot = -3.3
                player.zone = 2
            elif polar_pos.r < OUTER_RING_RADIUS:
                polar_vel.theta_dot = -2.0
                player.zone = 1
            else:
                player.alive = False

class InputProcessor(esper.Processor):
    def process(self, dt):
        keys = pg.key.get_pressed()
        for ent, (player, polar_vel) in esper.get_components(Player, PolarVelocity):
            if keys[pg.K_SPACE]:
                polar_vel.r_dot = 200.0
            else:
                polar_vel.r_dot = -100.0


class MovementProcessor(esper.Processor):
    def process(self, dt):
        for ent, (polar_pos, polar_vel) in esper.get_components(PolarPosition, PolarVelocity):
            polar_pos.r += polar_vel.r_dot * dt
            polar_pos.theta += polar_vel.theta_dot * dt
            polar_pos.theta = polar_pos.theta % (2 * np.pi)  # wrap theta to [0, 2pi]

class PolarToCartesianProcessor(esper.Processor):
    def process(self, dt):
        for ent, (polar, pos) in esper.get_components(PolarPosition, Position):
            pos.x = polar.r * np.cos(polar.theta) + CENTER_X
            pos.y = polar.r * np.sin(polar.theta) + CENTER_Y

class RenderProcessor(esper.Processor):
    def __init__(self, screen: pg.Surface):
        super().__init__()
        self.screen = screen
        self.font = pg.font.SysFont(None, 36)

    def process(self, dt):
        self.screen.lock()
        pg.draw.circle(self.screen, pg.Color(82, 55, 115), (int(CENTER_X), int(CENTER_Y)), OUTER_RING_RADIUS)
        pg.draw.circle(self.screen, pg.Color(116, 78, 163, a=10), (int(CENTER_X), int(CENTER_Y)), MIDDLE_RING_RADIUS)
        pg.draw.circle(self.screen, pg.Color(148, 100, 209, a=10), (int(CENTER_X), int(CENTER_Y)), INNER_RING_RADIUS)
        for ent, (layer1, pos, circle) in esper.get_components(Layer1, Position, Circle):
            pg.draw.circle(self.screen, circle.color, (int(pos.x), int(pos.y)), int(circle.radius))
        for ent, (layer2, pos, circle) in esper.get_components(Layer2, Position, Circle):
            pg.draw.circle(self.screen, circle.color, (int(pos.x), int(pos.y)), int(circle.radius))
        self.screen.unlock()
        for ent, (score) in esper.get_component(Score):
            score_text = self.font.render(f"Score: {score.value}", True, pg.Color("white"))
            self.screen.blit(score_text, (10, 10))



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


def main() -> None:
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pg.time.Clock()
    running = True
    dt = 0.0

    # spawn the black hole
    black_hole = esper.create_entity()
    esper.add_component(black_hole, PolarPosition(r=0.0, theta=0.0))
    esper.add_component(black_hole, Position())
    esper.add_component(black_hole, Circle(radius=50.0, color="black"))
    esper.add_component(black_hole, Enemy())
    esper.add_component(black_hole, Layer2())

    # spawn the player
    player = esper.create_entity()
    esper.add_component(player, PolarPosition(r = 200.0, theta = 0.0))
    esper.add_component(player, PolarVelocity(r_dot = 0.0, theta_dot = -2.5))
    esper.add_component(player, Position())
    esper.add_component(player, Circle(radius=10.0, color="white"))
    esper.add_component(player, Player())
    esper.add_component(player, Layer2())
    esper.add_component(player, Score())

    polar_to_cartesian = PolarToCartesianProcessor()
    movement = MovementProcessor()
    render = RenderProcessor(screen)
    input = InputProcessor()
    game_over = GameOverProcessor()
    collision = CollisionProcessor()
    enemy_spawn = EnemySpawnProcessor()
    enemy_despawn = EnemyDespawnProcessor()
    player_zone = PlayerZoneProcessor()
    score = ScoreProcessor()
    esper.add_processor(polar_to_cartesian)
    esper.add_processor(movement)
    esper.add_processor(collision)
    esper.add_processor(game_over)
    esper.add_processor(enemy_spawn)
    esper.add_processor(enemy_despawn)
    esper.add_processor(player_zone)
    esper.add_processor(score)
    esper.add_processor(render, priority=1)
    esper.add_processor(input, priority=2)

    while running:
        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

        # fill the screen with a color to wipe away anything from last frame
        screen.fill(pg.Color(55, 30, 87, a=255))

        # RENDER YOUR GAME HERE
        esper.process(dt)

        # flip() the display to put your work on screen
        pg.display.flip()

        dt = clock.tick(60) / 1000.0  # limits FPS to 60

    pg.quit()

