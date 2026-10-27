import pygame
import math
from sprites import *
from ui import UI
from settings import TILESIZE, WIDTH, HITBOX_OFFSET  # Make sure to import HITBOX_OFFSET
from random import choice
import sys, os

# Import functions from support.py
def import_csv_layout(path):
    terrain_map = []
    with open(path) as level_map:
        from csv import reader
        layout = reader(level_map, delimiter=',')
        for row in layout:
            terrain_map.append(list(row))
        return terrain_map

def import_folder(path):
    surface_list = []
    from os import walk
    for _, __, img_files in walk(path):
        for image in img_files:
            full_path = path + '/' + image
            image_surf = pygame.image.load(full_path).convert_alpha()
            surface_list.append(image_surf)
    return surface_list

# Camera setup
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from camera import HandGestureCamera
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

# Tile class (matching your tile.py)
class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, groups, sprite_type, surface=None):
        super().__init__(groups)
        self.sprite_type = sprite_type
        
        # Create default surface if none provided
        if surface is None:
            surface = pygame.Surface((TILESIZE, TILESIZE))
            if sprite_type == 'invisible':
                surface.set_alpha(0)  # Make invisible tiles transparent
            else:
                surface.fill((100, 100, 100))  # Gray color for debugging
        
        self.image = surface
        
        # Position handling (matching your tile.py)
        if sprite_type == 'object':
            self.rect = self.image.get_rect(topleft=(pos[0], pos[1] - TILESIZE))
        else:
            self.rect = self.image.get_rect(topleft=pos)
        
        # Create hitbox with offset
        y_offset = HITBOX_OFFSET.get(sprite_type, 0) if 'HITBOX_OFFSET' in globals() else 0
        self.hitbox = self.rect.inflate(0, y_offset)

class ItemCollectionLevelBase:
    def __init__(self, screen, map_path='map/map_Entities.csv'):
        self.screen = screen
        self.visible_sprites = CameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()
        self.item_sprites = pygame.sprite.Group()
        self.ui = UI()
        self.camera = None
        self.player = None  # Initialize player as None

        if CAMERA_AVAILABLE:
            try:
                self.camera = HandGestureCamera()
                self.show_camera = True
            except Exception:
                self.camera = None
                self.show_camera = False
        else:
            self.show_camera = False

        self.map_path = map_path
        self.create_map()

    def create_map(self):
        # Load layouts with detailed error reporting
        layouts = {}
        
        # Try to load each CSV file individually with detailed feedback
        csv_files = {
            'boundary': 'map/map_FloorBlocks.csv',
            'grass': 'map/map_Grass.csv', 
            'object': 'map/map_Objects.csv',
            'entities': self.map_path
        }
        
        for layout_name, file_path in csv_files.items():
            try:
                layout_data = import_csv_layout(file_path)
                layouts[layout_name] = layout_data
                print(f"✓ Successfully loaded {layout_name} from {file_path} - {len(layout_data)} rows")
                
                # Debug: Show first few entries for entities
                if layout_name == 'entities' and layout_data:
                    print(f"  First row of entities: {layout_data[0][:10] if len(layout_data[0]) > 10 else layout_data[0]}")
                    
            except FileNotFoundError:
                print(f"✗ File not found: {file_path}")
                layouts[layout_name] = [[]]  # Empty layout
            except Exception as e:
                print(f"✗ Error loading {layout_name} from {file_path}: {e}")
                layouts[layout_name] = [[]]  # Empty layout
        
        # Check if we have any valid layouts
        total_data = sum(len(layout) for layout in layouts.values())
        if total_data == 0:
            print("WARNING: No map data found, creating minimal fallback")
            # Create proper 2D layout arrays (rows and columns)
            layouts = {
                'boundary': [
                    ['395', '-1', '-1'],
                    ['-1', '-1', '-1'],
                    ['-1', '-1', '-1']
                ],
                'grass': [
                    ['8', '9', '10'],
                    ['8', '9', '10'], 
                    ['8', '9', '10']
                ],
                'object': [
                    ['2', '3', '4'],
                    ['5', '6', '7'],
                    ['8', '9', '10']
                ],
                'entities': [
                    ['394', '390', '391'],  # Player and hearts
                    ['-1', '392', '-1'],
                    ['-1', '-1', '-1']
                ]
            }

        # Load graphics with fallbacks
        try:
            graphics = {
                'grass': import_folder('graphics/Grass'),
                'objects': import_folder('graphics/objects'),
            }
            
            # Load heart image with better fallback
            try:
                heart_image = pygame.image.load('graphics/items/Heart.png').convert_alpha()
                # Scale heart to full tile size
                heart_image = pygame.transform.scale(heart_image, (TILESIZE, TILESIZE))
                graphics['heart'] = heart_image
                print("Heart image loaded and scaled to full tile size")
            except Exception as e:
                print(f"Error loading heart image: {e}")
                # Create a more visible fallback heart image at full tile size
                heart_surf = pygame.Surface((TILESIZE, TILESIZE))
                heart_surf.fill((255, 0, 0))  # Red color
                # Add a simple heart shape using pygame.draw
                center_x, center_y = TILESIZE//2, TILESIZE//2
                pygame.draw.circle(heart_surf, (255, 100, 100), (center_x - TILESIZE//6, center_y - TILESIZE//6), TILESIZE//6)
                pygame.draw.circle(heart_surf, (255, 100, 100), (center_x + TILESIZE//6, center_y - TILESIZE//6), TILESIZE//6)
                pygame.draw.polygon(heart_surf, (255, 100, 100), [
                    (center_x - TILESIZE//3, center_y - TILESIZE//12),
                    (center_x, center_y + TILESIZE//3),
                    (center_x + TILESIZE//3, center_y - TILESIZE//12)
                ])
                graphics['heart'] = heart_surf
                
            print(f"Loaded {len(graphics['grass'])} grass images")
            print(f"Loaded {len(graphics['objects'])} object images")
            
        except Exception as e:
            print(f"Error loading graphics: {e}")
            # Create fallback graphics
            graphics = {
                'grass': [pygame.Surface((TILESIZE, TILESIZE))],
                'objects': [pygame.Surface((TILESIZE, TILESIZE))],
                'heart': pygame.Surface((TILESIZE, TILESIZE))  # Full tile size
            }
            graphics['grass'][0].fill((0, 128, 0))  # Green
            graphics['objects'][0].fill((139, 69, 19))  # Brown
            graphics['heart'].fill((255, 0, 0))  # Red

        # Process map data with detailed debugging
        player_found = False
        hearts_found = 0
        
        for style, layout in layouts.items():
            print(f"\nProcessing {style} layout with {len(layout)} rows")
            
            for row_index, row in enumerate(layout):
                for col_index, col in enumerate(row):
                    if col != '-1' and col != '' and col.strip() != '':  # Also check for empty strings and whitespace
                        x = col_index * TILESIZE
                        y = row_index * TILESIZE
                        
                        if style == 'boundary':
                            Tile((x, y), [self.obstacle_sprites], 'invisible')
                            
                        elif style == 'grass':
                            if graphics['grass']:  # Check if grass images exist
                                random_grass_image = choice(graphics['grass'])
                                Tile((x, y), [self.visible_sprites], 'grass', random_grass_image)
                            
                        elif style == 'object':
                            if graphics['objects']:  # Check if object images exist
                                try:
                                    col_int = int(col)
                                    if col_int < len(graphics['objects']):
                                        surf = graphics['objects'][col_int]
                                    else:
                                        surf = graphics['objects'][0]  # Use first object as fallback
                                    Tile((x, y), [self.visible_sprites, self.obstacle_sprites], 'object', surf)
                                except ValueError:
                                    print(f"Invalid object ID in {style}: '{col}' at ({col_index}, {row_index})")
                                    continue
                            
                        elif style == 'entities':
                            try:
                                col_int = int(col)
                                if col_int == 394:  # Player spawn point
                                    self.player = Player((x, y), [self.visible_sprites], self.obstacle_sprites)
                                    player_found = True
                                    print(f"✓ Player created at tile ({col_index}, {row_index}) = world pos ({x}, {y})")
                                elif col_int in [390, 391, 392]:  # Heart spawn points
                                    Heart((x, y), [self.visible_sprites, self.item_sprites], graphics['heart'])
                                    hearts_found += 1
                                    print(f"✓ Heart created at tile ({col_index}, {row_index}) = world pos ({x}, {y})")
                                else:
                                    # Debug: Show other entity IDs found
                                    if col_int not in [-1, 0]:  # Don't spam for empty tiles
                                        print(f"  Found entity ID {col_int} at ({col_index}, {row_index})")
                            except ValueError:
                                print(f"Invalid entity ID in {style}: '{col}' at ({col_index}, {row_index})")
                                continue

        # Report what we found
        print(f"\n=== MAP LOADING SUMMARY ===")
        print(f"Player found in CSV: {player_found}")
        print(f"Hearts found in CSV: {hearts_found}")
        print(f"Total visible sprites: {len(self.visible_sprites)}")
        print(f"Total obstacle sprites: {len(self.obstacle_sprites)}")
        
        # Fallback: Create player at default position if not found in map
        if self.player is None:
            print("WARNING: Player spawn point (394) not found in entities CSV!")
            print("This could mean:")
            print("- The entities CSV file doesn't contain '394'")
            print("- The CSV file path is wrong")
            print("- The CSV file is corrupted or empty")
            self.player = Player((100, 100), [self.visible_sprites], self.obstacle_sprites)
            print("Player created at fallback position (100, 100)")

        # Create fallback hearts only if none were found in CSV
        if len(self.item_sprites) == 0:
            print("No hearts found in entities CSV, creating fallback hearts")
            heart_positions = [(300, 200), (500, 400), (700, 300)]
            for pos in heart_positions:
                Heart(pos, [self.visible_sprites, self.item_sprites], graphics['heart'])
                print(f"Fallback heart created at position {pos}")

        print(f"Final map stats - Items: {len(self.item_sprites)}, Player exists: {self.player is not None}")
        print("===========================")

    def check_item_collision(self):
        # Add safety check for player existence
        if self.player is None:
            return
            
        for heart in self.item_sprites:
            if self.player.rect.colliderect(heart.rect):
                self.collect_heart()
                heart.kill()
                print(f"Heart collected! Remaining hearts: {len(self.item_sprites)}")
                
    def collect_heart(self):
        """Handle what happens when a heart is collected"""
        print("Heart collected!")
        # Add your collection logic here:
        # - Restore health
        # - Play sound effect
        # - Update score
        # - Show visual feedback
        # Example: self.player.health += 1

    def handle_gesture_input(self):
        if self.camera:
            try:
                self.camera.process()
            except Exception:
                pass

    def run(self):
        # Add safety check for player existence
        if self.player is None:
            print("Critical Error: Player not initialized properly")
            # Try to create emergency player
            try:
                self.player = Player((100, 100), [self.visible_sprites], self.obstacle_sprites)
                print("Emergency player created")
            except Exception as e:
                print(f"Failed to create emergency player: {e}")
                return
            
        if self.camera and self.show_camera:
            self.handle_gesture_input()
            
        self.visible_sprites.update()
        self.item_sprites.update()
        self.check_item_collision()
        self.visible_sprites.custom_draw(self.player)
        self.ui.show_inventory(self.player.inventory)
        
        if self.camera and self.show_camera:
            try:
                cam_surface = self.camera.get_frame()
                if cam_surface:
                    rect = cam_surface.get_rect(topright=(WIDTH - 10, 10))
                    self.screen.blit(cam_surface, rect)
                    pygame.draw.rect(self.screen, (255, 255, 255), rect, 2)
            except Exception:
                pass
                
        if pygame.key.get_pressed()[pygame.K_c]:
            self.show_camera = not self.show_camera

class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.half_w = self.display_surface.get_width() // 2
        self.half_h = self.display_surface.get_height() // 2
        self.offset = pygame.math.Vector2()

        # Disable floor background to see CSV map tiles
        # Comment out or remove this section if you want to see your CSV-based map
        try:
            # self.floor_surf = pygame.image.load('graphics/tilemap/ground.png').convert()
            # self.floor_rect = self.floor_surf.get_rect(topleft=(0, 0))
            # print("Floor background loaded")
            self.floor_surf = None
            print("Floor background disabled to show CSV map")
        except Exception as e:
            print(f"Floor background not found: {e}")
            self.floor_surf = None

    def custom_draw(self, player):
        self.offset.x = player.rect.centerx - self.half_w
        self.offset.y = player.rect.centery - self.half_h
        
        # Draw floor background if available
        if self.floor_surf:
            floor_offset_pos = self.floor_rect.topleft - self.offset
            self.display_surface.blit(self.floor_surf, floor_offset_pos)
        
        # Draw sprites sorted by y position
        for sprite in sorted(self.sprites(), key=lambda s: s.rect.centery):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)

class Heart(pygame.sprite.Sprite):
    def __init__(self, pos, groups, image):
        super().__init__(groups)
        self.image = image
        self.rect = self.image.get_rect(topleft=pos)
        # Make hitbox slightly smaller for better collection feel, but still reasonable for full tile
        self.hitbox = self.rect.inflate(-5, -5)  
        self.sprite_type = 'heart'  # Add sprite type for identification
        
        # Add floating animation variables
        self.float_offset = 0
        self.float_speed = 0.05
        self.original_y = pos[1]
        
    def update(self):
        # Add floating animation
        self.float_offset += self.float_speed
        float_y = self.original_y + math.sin(self.float_offset) * 5  # Float up and down by 5 pixels
        self.rect.y = int(float_y)
        self.hitbox.y = int(float_y) - 5  # Adjust hitbox position too