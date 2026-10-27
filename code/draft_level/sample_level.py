import pygame
from level.level_base import LevelBase
from sprites import *
from ui import UI
from utils import import_csv_layout, import_folder
from settings import *
from random import choice
import sys
import os

# Add camera import with error handling
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from camera import HandGestureCamera
    CAMERA_AVAILABLE = True
except ImportError:
    print("Camera module not available. Gesture recognition disabled.")
    CAMERA_AVAILABLE = False

class Level1(LevelBase):
    def __init__(self, screen):
        super().__init__(screen)
        self.screen = screen
        
        # Sprite groups
        self.visible_sprites = CameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()
        self.item_sprites = pygame.sprite.Group()
        
        # UI
        self.ui = UI()
        
        # Camera for gesture recognition
        self.camera = None
        if CAMERA_AVAILABLE:
            try:
                self.camera = HandGestureCamera()
                self.show_camera = True
            except Exception as e:
                print(f"Failed to initialize camera: {e}")
                self.camera = None
                self.show_camera = False
        else:
            self.show_camera = False
        
        # Create map and player
        self.create_map()

    def create_map(self):
        layouts = {
            'boundary': import_csv_layout('map/map_FloorBlocks.csv'),
            'grass': import_csv_layout('map/map_Grass.csv'),
            'object': import_csv_layout('map/map_Objects.csv'),
            'entities': import_csv_layout('map/map_Entities.csv'),
        }
        
        graphics = {
            'grass': import_folder('graphics/Grass'),
            'objects': import_folder('graphics/objects')
        }
        
        for style, layout in layouts.items():
            for row_index, row in enumerate(layout):
                for col_index, col in enumerate(row):
                    if col != '-1':
                        x = col_index * TILESIZE
                        y = row_index * TILESIZE
                        
                        if style == 'boundary':
                            Tile((x, y), [self.obstacle_sprites], 'invisible')
                        
                        elif style == 'grass':
                            random_grass_image = choice(graphics['grass'])
                            Tile((x, y), 
                                [self.visible_sprites], 
                                'grass', 
                                random_grass_image)
                        
                        elif style == 'object':
                            if int(col) < len(graphics['objects']):
                                surf = graphics['objects'][int(col)]
                            else:
                                surf = graphics['objects'][0]
                            Tile((x, y), [self.visible_sprites, self.obstacle_sprites], 'object', surf)
                        
                        elif style == 'entities':
                            if col == '394':  # Player spawn
                                self.player = Player(
                                    (x, y),
                                    [self.visible_sprites],
                                    self.obstacle_sprites
                                )
        
        # Create some items to collect
        self.create_items()

    def create_items(self):
        """Create collectible items on the map"""
        item_positions = [
            (300, 200, 'coin'),
            (500, 400, 'key'),
            (700, 300, 'potion'),
            (400, 500, 'coin'),
            (600, 200, 'potion')
        ]
        
        for x, y, item_type in item_positions:
            Item((x, y), [self.visible_sprites, self.item_sprites], item_type)

    def check_item_collision(self):
        """Check for item pickup collisions"""
        for item in self.item_sprites:
            if self.player.rect.colliderect(item.rect):
                self.player.add_item(item.item_type)
                item.kill()

    def handle_gesture_input(self):
        """Handle gesture recognition input"""
        if self.camera:
            try:
                self.camera.process()
            except Exception as e:
                print(f"Camera processing error: {e}")

    def run(self):
        # Handle gesture recognition
        if self.camera and self.show_camera:
            self.handle_gesture_input()
        
        # Update sprites
        self.visible_sprites.update()
        self.item_sprites.update()
        
        # Check item collisions
        self.check_item_collision()
        
        # Draw everything
        self.visible_sprites.custom_draw(self.player)
        
        # Draw UI
        self.ui.show_inventory(self.player.inventory)
        
        # Draw camera feed if available
        if self.camera and self.show_camera:
            try:
                camera_surface = self.camera.get_frame()
                if camera_surface:
                    # Position camera feed in top-right corner
                    camera_rect = camera_surface.get_rect()
                    camera_rect.topright = (WIDTH - 10, 10)
                    self.screen.blit(camera_surface, camera_rect)
                    
                    # Draw camera border
                    pygame.draw.rect(self.screen, (255, 255, 255), camera_rect, 2)
            except Exception as e:
                print(f"Camera display error: {e}")
        
        # Toggle camera with C key
        keys = pygame.key.get_pressed()
        if keys[pygame.K_c]:
            self.show_camera = not self.show_camera

class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.half_width = self.display_surface.get_size()[0] // 2
        self.half_height = self.display_surface.get_size()[1] // 2
        self.offset = pygame.math.Vector2()

    def custom_draw(self, player):
        # Getting the offset
        self.offset.x = player.rect.centerx - self.half_width
        self.offset.y = player.rect.centery - self.half_height

        # Drawing sprites
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.centery):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)