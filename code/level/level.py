import pygame, sys
from settings import *
from tile import Tile
from level.player import Player
from level.support import *
from random import choice
from ui import UI
from button import Button
from map_loader import TiledMap
import pytmx
from camera_game import Camera

class Item(pygame.sprite.Sprite):
    def __init__(self, pos, groups, item_type, surface=None):
        super().__init__(groups)
        self.sprite_type = 'item'
        self.item_type = item_type
        if surface:
            self.image = surface
        else:
            self.image = pygame.Surface((TILESIZE, TILESIZE))
            self.image.fill('red' if self.item_type == 'heart' else 'grey')
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.inflate(0, 0)


class Level:
    def __init__(self, camera_instance, screen_surface, font_renderer, map_file, hearts_to_collect=2, level_key=None):
        print("Loading TMX map:", map_file)

        self.level_key = level_key

        # --- Surface & UI ---
        self.screen_surface = screen_surface   # <--- simpan surface utama
        self.font_renderer = font_renderer
        self.game_camera = camera_instance
        self.hearts_to_collect = hearts_to_collect
        self.game_paused = False

        # --- Level state ---
        self.level_complete = False         
        self.proceed_to_next_level = False  
        self.manual_gesture_input_mode = False

        # --- Sprite groups ---
        self.visible_sprites = YSortCameraGroup(self.screen_surface, None)
        self.obstacle_sprites = pygame.sprite.Group()
        self.item_sprites = pygame.sprite.Group()

        # --- Player --- 
        screen_width, screen_height = self.screen_surface.get_size()
        center_x, center_y = screen_width // 2, screen_height // 2

        # --- UI ---
        self.ui = None

        self.level_duration = 4 * 60        # 4 menit dalam detik
        self.start_time = pygame.time.get_ticks()
        self.time_up = False

        # --- Load map TMX ---
        if map_file:
            from map_loader import TiledMap
            print("DEBUG Loading TMX from:", map_file)
            self.map = TiledMap(map_file)

            # --- Pastikan map surface minimal sebesar layar ---
            map_w = max(self.map.width, self.screen_surface.get_width())
            map_h = max(self.map.height, self.screen_surface.get_height())
            self.map_surface = pygame.Surface((map_w, map_h))
            self.map_surface.fill((0, 0, 0))  # background jika tile tidak menutupi
            self.map.render(self.map_surface)
            self.map_rect = self.map_surface.get_rect(topleft=(0,0))

            # --- Kamera ---
            self.camera = Camera(
                self.map.width,
                self.map.height,
                self.screen_surface.get_width(),
                self.screen_surface.get_height()
            )
            self.visible_sprites.camera = self.camera

            # === Gesture panel ===
            self.gesture_images = {
                "kiri": pygame.image.load("graphics/tutorials/kiri.png"),
                "kanan": pygame.image.load("graphics/tutorials/kanan.png"),
                "atas": pygame.image.load("graphics/tutorials/atas.png"),
                "bawah": pygame.image.load("graphics/tutorials/bawah.png")
            }

            # Resize kalau mau sedikit lebih kecil
            for key in self.gesture_images:
                self.gesture_images[key] = pygame.transform.smoothscale(self.gesture_images[key], (200, 100))

            # --- Spawn objects dari TMX ---
            tile_w, tile_h = self.map.tmxdata.tilewidth, self.map.tmxdata.tileheight

            # Default spawn → pakai tengah map (pixel, bukan tile)
            default_spawn = (
                (self.map.tmxdata.width * tile_w) // 2,
                (self.map.tmxdata.height * tile_h) // 2
            )

            player_spawn = None
            for obj in self.map.tmxdata.objects:
                
                ox = obj.x * self.map.SCALE
                oy = obj.y * self.map.SCALE

                if obj.name == "Player":
                    player_spawn = (obj.x, obj.y)

                elif obj.name == "heart":
                    image = pygame.image.load("graphics/items/heart.png").convert_alpha()
                    image = pygame.transform.scale(image, (64, 64))  # ubah ke ukuran tile
                    Item((ox, oy), [self.visible_sprites, self.item_sprites], "heart", image)

                elif obj.name in ["obs", "0", "01", "02", "03", "04", "05", "06", "07", "08",
                                "09", "10", "11", "12", "14", "15", "17", "18",
                                "grass_1", "grass_2", "grass_3", "health"]:

                    # Ambil tile image dari gid (gambar dari tileset)
                    tile_img = self.map.tmxdata.get_tile_image_by_gid(obj.gid)

                    if tile_img:
                        tile_img = tile_img.convert_alpha()
                        tile_img.set_colorkey((0,0,0))

                        # scale dengan nearest-neighbor (pixel perfect)
                        scaled = pygame.transform.scale(
                            tile_img,
                            (self.map.tmxdata.tilewidth * self.map.SCALE,
                            self.map.tmxdata.tileheight * self.map.SCALE)
                        )

                        Tile(
                            (ox, oy),
                            [self.visible_sprites, self.obstacle_sprites],
                            obj.name,
                            scaled
                        )

            # --- Buat player hanya sekali (di luar loop) ---
            spawn_pos = player_spawn if player_spawn else default_spawn
            spawn_pos = (spawn_pos[0] * self.map.SCALE, spawn_pos[1] * self.map.SCALE)

            self.player = Player(
                pos=spawn_pos,
                groups=[self.visible_sprites],
                obstacle_sprites=self.obstacle_sprites,
                camera_input=self.game_camera,
                map_width=self.map.width,
                map_height=self.map.height
            )

            # --- Paksa kamera langsung fokus ke player ---
            if hasattr(self, "camera") and self.camera:
                self.camera.update(self.player)
        
        print("DEBUG: Player gesture control =", self.player.control_with_gesture)

    def toggle_pause(self):
        pass

    def set_ui(self, ui_instance):
        self.ui = ui_instance
        if self.game_camera:
            self.ui.set_camera(self.game_camera)

    def run(self):
        if self.level_complete:
            action = self.show_level_complete_screen()
            return action if action else "RUNNING"

        if not self.game_paused:
            gesture_action = None
            if self.game_camera and self.player and self.player.control_with_gesture and not self.manual_gesture_input_mode:
                self.game_camera.process()
                gesture_action = self.game_camera.consume_action()

            if gesture_action is not None:
                self.player.execute_gesture_move(gesture_action)

            # --- Bersihkan layar dulu agar sprite lama hilang ---
            self.screen_surface.fill("black")

            self.visible_sprites.update()
            self.player_item_collection_logic()
            remaining_time = self.update_timer()
        
            # --- gambar map + sprite ---
            self.visible_sprites.custom_draw(
                self.player,
                map_surface=getattr(self, "map_surface", None),
                map_rect=getattr(self, "map", None).rect if hasattr(self, "map") else None
            )

        if hasattr(self, 'ui') and self.player:
            self.ui.display(self.player, self.hearts_to_collect)
            self.draw_gesture_panel() 

            minutes = remaining_time // 60
            seconds = remaining_time % 60
            timer_text = self.font_renderer.render(f"{minutes:02d}:{seconds:02d}", True, (255,255,255))
            self.screen_surface.blit(timer_text, (25, 140))   # 140 = di bawah tombol pause

            pygame.display.update()
            
    
    def draw_gesture_panel(self):
        margin = 20
        screen_w, screen_h = self.screen_surface.get_size()

        img_w, img_h = 200, 100
        gap_x, gap_y = 2, 2

        # === FILTER GESTURE SESUAI LEVEL ===
        if self.level_key == "LEVEL_1":
            gestures = ["atas", "bawah"]
        elif self.level_key == "LEVEL_2":
            gestures = ["kiri", "kanan"]
        else:
            gestures = ["kanan", "atas", "kiri", "bawah"]

        # Layout otomatis
        if len(gestures) == 2:
            layout = [gestures]        # 1 baris
            rows, cols = 1, 2
        else:
            layout = [
                gestures[:2],
                gestures[2:]
            ]
            rows, cols = 2, 2

        panel_w = (img_w * cols) + gap_x * (cols + 1)
        panel_h = (img_h * rows) + gap_y * (rows + 1)

        panel_rect = pygame.Rect(
            screen_w - panel_w - margin,
            screen_h - panel_h - margin,
            panel_w,
            panel_h
        )

        overlay = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen_surface.blit(overlay, panel_rect.topleft)

        y = panel_rect.y + gap_y
        for row in layout:
            x = panel_rect.x + gap_x
            for key in row:
                img = self.gesture_images[key]
                self.screen_surface.blit(img, (x, y))
                x += img_w + gap_x
            y += img_h + gap_y

    def player_item_collection_logic(self):
        if self.player and not self.level_complete:
            collided_items = pygame.sprite.spritecollide(self.player, self.item_sprites, True)
            for item_sprite in collided_items:
                self.player.collect_item(item_sprite.item_type)

                # Cek apakah jumlah heart sudah cukup
                if self.player.inventory.get('heart', 0) >= self.hearts_to_collect:
                    self.level_complete = True
                    print(f"{getattr(self, 'level_name', 'Level')} Objective Achieved!")

                    # --- panggil evaluasi dari kamera ---
                    if self.game_camera:
                        eval_result = self.game_camera.evaluate_level()

                        # Simpan hasilnya agar bisa diakses di game / UI
                        self.gesture_valid_count = eval_result.get("total_valid", 0)
                        self.gesture_total_count = eval_result.get("total_all", 0)
                        self.avg_confidence = eval_result.get("avg_confidence", 0.0)
                        self.play_time = eval_result.get("play_time", "00:00")

                        print(f"\n=== Evaluasi Level Selesai ===")
                        print(f".level Total Gesture Valid : {self.gesture_valid_count} dari {self.gesture_total_count}")
                        print(f"Rata-rata Confidence: {self.avg_confidence:.2f}%\n")
                        print(f"Waktu Bermain       : {self.play_time}\n")

    def update_timer(self):
        elapsed = (pygame.time.get_ticks() - self.start_time) / 1000
        remaining = int(self.level_duration - elapsed)
        
        if remaining <= 0 and not self.time_up:
            self.time_up = True
            self.level_complete = True

            if self.game_camera:
                eval_result = self.game_camera.evaluate_level()
                self.gesture_valid_count = eval_result.get("total_valid", 0)
                self.gesture_total_count = eval_result.get("total_all", 0)
                self.avg_confidence = eval_result.get("avg_confidence", 0.0)
                self.play_time = eval_result.get("play_time", "00:00")

                print(f"\n=== Evaluasi Level Selesai ===")
                print(f"Total Gesture Valid : {self.gesture_valid_count} dari {self.gesture_total_count}")
                print(f"Rata-rata Confidence: {self.avg_confidence:.2f}%\n")
                print(f"Waktu Bermain       : {self.play_time}\n")

        return max(0, remaining)

class Collision(pygame.sprite.Sprite):
    def __init__(self, pos, size, groups):
        super().__init__(groups)
        self.image = pygame.Surface(size, pygame.SRCALPHA)  # invisible
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.copy()

class YSortCameraGroup(pygame.sprite.Group):
    def __init__(self, screen_surface, camera_instance):
        super().__init__()
        self.screen_surface = screen_surface
        self.half_width = self.screen_surface.get_width() // 2
        self.half_height = self.screen_surface.get_height() // 2
        self.camera = camera_instance
        self.offset = pygame.math.Vector2()

        try:
            self.floor_surf = pygame.image.load("graphics/tilemap/Background.png").convert()
        except pygame.error:
            self.floor_surf = pygame.Surface(self.screen_surface.get_size())
            self.floor_surf.fill((30,30,30))
        self.floor_rect = self.floor_surf.get_rect(topleft=(0,0))

    def custom_draw(self, player, map_surface=None, map_rect=None):
        # Update kamera mengikuti player
        if self.camera:
            self.camera.update(player)

        # Gambar background
        floor_offset = pygame.math.Vector2(self.floor_rect.topleft) - self.camera.offset
        self.screen_surface.blit(self.floor_surf, floor_offset)

        # Gambar map (hanya sekali blit)
        if map_surface and map_rect:
            map_offset = pygame.math.Vector2(map_rect.topleft) - self.camera.offset
            self.screen_surface.blit(map_surface, map_offset)

        # Gambar semua sprite sesuai urutan Y
        for sprite in sorted(self.sprites(), key=lambda spr: spr.rect.centery):
            offset_pos = pygame.math.Vector2(sprite.rect.topleft) - self.camera.offset
            self.screen_surface.blit(sprite.image, offset_pos)

    def update(self, **kwargs):
        for sprite in self.sprites():
            sprite.update(**kwargs)
