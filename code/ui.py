import pygame
import math
from settings import *
from camera import HandGestureCamera

class UI:
    def __init__(self, screen_surface):
        self.display_surface = screen_surface
        self.font = pygame.font.Font(None, 30)
        
        # Load item graphics
        self.item_graphics = {}
        for item in ITEM_TYPES:
            try:
                graphic_path = 'graphics/items/heart.png'
                self.item_graphics[item] = pygame.image.load(graphic_path).convert_alpha()
                self.item_graphics[item] = pygame.transform.scale(self.item_graphics[item], (50, 50))
            except Exception as e:
                print(f"Could not load graphic for {item}: {e}. Creating placeholder.")
                surf = pygame.Surface((32, 32))
                surf.fill('red')
                self.item_graphics[item] = surf

        # Camera display
        self.camera_object = None
        self.show_camera_feed = True
        
        # Dwell clock properties
        self.clock_radius = 25
        self.clock_bg_color = '#444444'
        self.clock_fg_color = '#00FF7F'  # SpringGreen
        self.clock_width = 6

        # Tombol Pause
        self.pause_button_rect = pygame.Rect(20, 90, 100, 40)
        self.is_paused = False

    # ===============================
    # ==== CAMERA & DWELL CLOCK ====
    # ===============================
    def set_camera(self, camera_instance):
        """Sets the camera instance to be used by the UI."""
        self.camera_object = camera_instance

    def toggle_camera_feed(self):
        """Toggles the visibility of the camera feed."""
        self.show_camera_feed = not self.show_camera_feed

    def display_camera_feed(self):
        """Displays the camera feed in the top-right corner."""
        if self.camera_object and self.show_camera_feed:
            try:
                cam_surface = self.camera_object.get_frame()
                if cam_surface:
                    cam_surface = pygame.transform.scale(cam_surface, (200, 160))
                    cam_rect = cam_surface.get_rect(topright=(self.display_surface.get_width() - 10, 10))
                    self.display_surface.blit(cam_surface, cam_rect)
                    pygame.draw.rect(self.display_surface, (255, 255, 255), cam_rect, 2)
                    return cam_rect
            except Exception as e:
                print(f"Error displaying camera feed: {e}")
        return None

    def display_dwell_clock(self, camera_rect):
        """Displays a circular progress bar under the camera feed."""
        if self.camera_object and camera_rect:
            progress = self.camera_object.get_dwell_progress()
            if progress > 0:
                clock_center = (camera_rect.centerx, camera_rect.bottom + self.clock_radius + 15)
                pygame.draw.circle(self.display_surface, self.clock_bg_color, clock_center, self.clock_radius, self.clock_width)
                if progress < 1.0:
                    start_angle = math.pi / 2
                    end_angle = start_angle - (progress * 2 * math.pi)
                    pygame.draw.arc(self.display_surface, self.clock_fg_color,
                                    (clock_center[0] - self.clock_radius, clock_center[1] - self.clock_radius,
                                     self.clock_radius * 2, self.clock_radius * 2),
                                    end_angle, start_angle, self.clock_width)
                else:
                    pygame.draw.circle(self.display_surface, self.clock_fg_color, clock_center, self.clock_radius, self.clock_width)

    # ==========================
    # ==== INVENTORY PANEL ====
    # ==========================
    def show_inventory(self, inventory, target):
        x, y = 20, 20
        for index, (item, amount) in enumerate(inventory.items()):
            item_image = self.item_graphics.get(item)
            if item_image:
                item_rect = item_image.get_rect(topleft=(x, y + index * 60))
                bg_rect = item_rect.inflate(20, 20)
                pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_rect, border_radius=5)
                self.display_surface.blit(item_image, item_rect)
                pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, bg_rect, 3, border_radius=5)
                
                display_text = f'{amount} / {target}'
                amount_text = self.font.render(display_text, False, TEXT_COLOR)
                amount_rect = amount_text.get_rect(midleft=(item_rect.right + 10, item_rect.centery))
                bg_text_rect = amount_rect.inflate(10, 10)
                pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_text_rect, border_radius=5)
                self.display_surface.blit(amount_text, amount_rect)
                pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, bg_text_rect, 3, border_radius=5)

        # --- Gambar tombol pause di posisi tetap ---
        self.draw_pause_button(90)

    # ==========================
    # ==== PAUSE BUTTON LOGIC ==
    # ==========================
    def draw_pause_button(self, y_offset=None):
        """Menampilkan tombol pause di pojok kiri atas."""
        rect = self.pause_button_rect.copy()
        if y_offset is not None:
            rect.y = y_offset
        pygame.draw.rect(self.display_surface, (0, 120, 200), rect, border_radius=8)
        text = self.font.render("Pause", True, (255, 255, 255))
        text_rect = text.get_rect(center=rect.center)
        self.display_surface.blit(text, text_rect)

    def handle_pause_click(self, pos):
        """True jika tombol pause diklik."""
        return self.pause_button_rect.collidepoint(pos)

    def handle_event(self, event, game_instance=None):
        """Handles click event for pause butƒ√ton and syncs with main game state."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            if self.pause_button_rect.collidepoint((mx, my)):
                if game_instance and game_instance.current_game_state == "PLAYING_LEVEL":
                    game_instance.last_game_surface_before_pause = self.display_surface.copy()
                    game_instance.current_game_state = "PAUSE_MENU"
                    print("[DEBUG] Pause button clicked — switched to PAUSE_MENU")

    # ==========================
    # ==== MAIN DISPLAY LOOP ===
    # ==========================
    def display(self, player, target):
        """Displays all UI elements."""
        if player and hasattr(player, 'inventory'):
            self.show_inventory(player.inventory, target)
        
        camera_rect = self.display_camera_feed()
        self.display_dwell_clock(camera_rect)
        self.draw_pause_button()
