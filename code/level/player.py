# Di player.py

import pygame
import os
from settings import * 

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, obstacle_sprites, camera_input=None, map_width=None, map_height=None):
        super().__init__(groups)
        try:
            self.image = pygame.image.load('graphics/player/down_idle/idle_down.png').convert_alpha()
        except pygame.error as e:
            print(f"Error loading player image: {e}. Creating placeholder.")
            self.image = pygame.Surface((TILESIZE, TILESIZE))
            self.image.fill((0, 0, 255)) # Blue placeholder
            
        self.rect = self.image.get_rect(center=pos) 
        self.hitbox = self.rect.inflate(0, -10) 
        self.hitbox.center = self.rect.center

        self.gesture_start_time = None
        self.gesture_hold_duration = 200  # ms, durasi minimum gesture
        self.current_gesture = None
        self.gesture_threshold = 0.25  # threshold grabbing, bisa kalibrasi

        # Tile-based Movement
        self.tile_size = TILESIZE
        self.move_cooldown_duration = 200  # Cooldown for keyboard movement
        self.last_move_time = 0

        self.obstacle_sprites = obstacle_sprites
        self.inventory = {'heart': 0}

        # Gesture Control Toggle
        self.control_with_gesture = True 
        self.g_key_was_pressed = False

        # Status
        self.status = 'down_idle'

        # Animation
        self.frame_index = 0
        self.animation_speed = 0.15
        self.moving_animation_until = 0

        # Animations dictionary
        self.animations = {
            'up': self.load_images('graphics/player/up'),
            'down': self.load_images('graphics/player/down'),
            'left': self.load_images('graphics/player/left'),
            'right': self.load_images('graphics/player/right'),
            'up_idle': [pygame.image.load('graphics/player/up_idle/idle_up.png').convert_alpha()],
            'down_idle': [pygame.image.load('graphics/player/down_idle/idle_down.png').convert_alpha()],
            'left_idle': [pygame.image.load('graphics/player/left_idle/idle_left.png').convert_alpha()],
            'right_idle': [pygame.image.load('graphics/player/right_idle/idle_right.png').convert_alpha()]
        }

        self.direction = pygame.math.Vector2()
        self.speed = 2
        self.target_pos = None
        self.moving = False

        self.map_width = map_width
        self.map_height = map_height

    def input(self):
        keys = pygame.key.get_pressed()
        if self.moving:  
            return  # jangan ambil input kalau sedang bergerak ke target

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.direction = pygame.math.Vector2(0, -1)
            self.status = 'up'
            self.start_tile_move()

        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.direction = pygame.math.Vector2(0, 1)
            self.status = 'down'
            self.start_tile_move()

        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.direction = pygame.math.Vector2(-1, 0)
            self.status = 'left'
            self.start_tile_move()

        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.direction = pygame.math.Vector2(1, 0)
            self.status = 'right'
            self.start_tile_move()

    def start_tile_move(self):
        self.moving = True
        self.target_pos = (
            self.rect.centerx + self.direction.x * self.tile_size,
            self.rect.centery + self.direction.y * self.tile_size
        )

    def smooth_move(self):
        if not self.moving:
            return

        move_x = self.direction.x * self.speed
        move_y = self.direction.y * self.speed

        distance_x = self.target_pos[0] - self.rect.centerx
        distance_y = self.target_pos[1] - self.rect.centery

        # Snap jika lewat target
        if abs(move_x) > abs(distance_x):
            move_x = distance_x
        if abs(move_y) > abs(distance_y):
            move_y = distance_y

        self.rect.centerx += move_x
        self.rect.centery += move_y

       # --- Batas map ---
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > self.map_width:
            self.rect.right = self.map_width
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > self.map_height:
            self.rect.bottom = self.map_height

        self.hitbox.center = self.rect.center

        # stop move kalau sudah sampai tile atau sudah mentok batas
        if (self.rect.center == self.target_pos or
            self.rect.left == 0 or
            self.rect.right == self.map_width or
            self.rect.top == 0 or
            self.rect.bottom == self.map_height):
            self.moving = False

    def get_status(self):
        # buang "_idle" dulu
        base = self.status.replace("_idle", "")

        # saat bergerak → animasi jalan
        if self.moving:
            new_status = base
        else:
            # idle mengarah ke arah terakhir
            new_status = base + "_idle"

        # reset frame saat berubah status
        if new_status != self.status:
            self.frame_index = 0

        self.status = new_status

    def execute_gesture_move(self, action_label):
        """
        Executes a move based on a confirmed gesture action.
        This bypasses the standard move cooldown, as the dwell time is the cooldown.
        """
        if not self.control_with_gesture:
            return

        move_dx_tile, move_dy_tile = 0, 0
        if action_label == 0: # Up
            move_dy_tile = -1; self.status = 'up'
        elif action_label == 1: # Down
            move_dy_tile = 1; self.status = 'down'
        elif action_label == 2: # Right
            move_dx_tile = 1; self.status = 'right'
        elif action_label == 3: # Left
            move_dx_tile = -1; self.status = 'left'

        if move_dx_tile != 0 or move_dy_tile != 0:
            self.move_tile(move_dx_tile, move_dy_tile)

    def move_tile(self, dx_tile, dy_tile):
        """Moves the player by a number of tiles, checking for collisions first."""
        target_center_x = self.rect.centerx + dx_tile * self.tile_size
        target_center_y = self.rect.centery + dy_tile * self.tile_size

        future_hitbox = self.hitbox.copy()
        future_hitbox.center = (target_center_x, target_center_y)

        if not self.check_obstacle_collision(future_hitbox):
            self.rect.center = (target_center_x, target_center_y)
            self.hitbox.center = self.rect.center
        else:
            # Optionally, revert status to idle if move failed
            pass

    def check_obstacle_collision(self, future_hitbox):
        for sprite in self.obstacle_sprites:
            if hasattr(sprite, 'hitbox') and sprite.hitbox.colliderect(future_hitbox):
                return True 
        return False

    def collect_item(self, item_name):
        self.inventory.setdefault(item_name, 0)
        self.inventory[item_name] += 1
        print(f"Player collected {item_name}. Inventory: {self.inventory}")

    def animate(self):
        animation = self.animations[self.status]

        # Loop frame index
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            self.frame_index = 0

        old_center = self.rect.center
        self.image = animation[int(self.frame_index)]
        self.rect = self.image.get_rect(center=old_center)

    def update(self, **kwargs):
        self.input()
        self.smooth_move()
        self.get_status()
        self.animate()

    def load_images(self, path):
        images = []
        for img_name in sorted(os.listdir(path)):
            if img_name.endswith('.png'):
                img = pygame.image.load(f"{path}/{img_name}").convert_alpha()
                images.append(img)
        return images
