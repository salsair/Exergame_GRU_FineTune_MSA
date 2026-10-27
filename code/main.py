import pygame, sys
from settings import *
from main_menu import MainMenu
from level.level import Level
from camera import HandGestureCamera
# from ui import UI # UI dikelola di dalam Level
import threading  # --- PERUBAHAN UNTUK DEBUGGING ---
from camera_debug import GameDebugger  # --- PERUBAHAN UNTUK DEBUGGING ---
from ui import UI
from button import Button

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Heart Collector') # Ganti judul game jika mau
        self.clock = pygame.time.Clock()
        
        self.current_game_state = "MENU" # Menggunakan nama state yang lebih deskriptif
        self.active_level_instance = None # Untuk menyimpan instance level yang sedang berjalan

        self.camera = HandGestureCamera()
        self.main_menu = MainMenu(self.screen, self) # MainMenu juga akan berfungsi sebagai font

        # --- PERUBAHAN UNTUK DEBUGGING ---
        # Buat instance debugger dan berikan akses ke instance kamera
        self.debugger = GameDebugger(self.camera)
        # --------------------------------

        self.selected_duration = 240  # default 4 menit

        self.ui = UI(self.screen)

        pygame.mixer.init()
        pygame.mixer.music.load("audio/main.ogg")
        pygame.mixer.music.set_volume(0.5)   # 0.0 – 1.0
        pygame.mixer.music.play(-1)          # -1 = loop terus

        self.camera.session_start_time = pygame.time.get_ticks()

        # Placeholder untuk Level
        self.level_definitions = {
            "LEVEL_1": lambda cam, screen_surface, font: Level(
                cam, screen_surface, font,
                map_file="map/coba2.tmx",
                hearts_to_collect=2
            ),
            "LEVEL_2": lambda cam, screen_surface, font: Level(
                cam, screen_surface, font,
                map_file="map/lv2.tmx",
                hearts_to_collect=2
            ),
            "LEVEL_3": lambda cam, screen_surface, font: Level(
                cam, screen_surface, font,
                map_file="map/lv3.tmx",
                hearts_to_collect=3
            ),
            "LEVEL_4": lambda cam, screen_surface, font: Level(
                cam, screen_surface, font,
                map_file="map/lv4.tmx",
                hearts_to_collect=3
            ),
            "LEVEL_5": lambda cam, screen_surface, font: Level(
                cam, screen_surface, font,
                map_file="map/lv5.tmx",
                hearts_to_collect=3
            ),
            "LEVEL_6": lambda cam, screen_surface, font: Level(
                cam, screen_surface, font,
                map_file="map/lv6.tmx",
                hearts_to_collect=4
            ),
            "LEVEL_7": lambda cam, screen_surface, font: Level(
                cam, screen_surface, font,
                map_file="map/lv7.tmx",
                hearts_to_collect=4
            ),
            "LEVEL_8": lambda cam, screen_surface, font: Level(
                cam, screen_surface, font,
                map_file="map/lv8.tmx",
                hearts_to_collect=4
            ),
            "TRIAL": lambda cam, screen_surface, font: Level(
                cam, screen_surface, font,
                map_file="map/trial.tmx",
                hearts_to_collect=1
            ),
        }

        self.current_level_key = None

    def start_level(self, level_key):
        print(f"[DEBUG] Memulai level: {level_key}")

        # Simpan level yang aktif
        self.current_level_key = level_key

        # --- Atur current_level kamera ---
        if "LEVEL_" in level_key:
            try:
                level_number = int(level_key.split("_")[1])
                self.camera.current_level = level_number
                print(f"[INFO] Kamera diatur ke level {level_number}")
            except Exception as e:
                print(f"[WARN] Tidak bisa baca nomor level dari '{level_key}': {e}")
                self.camera.current_level = 6
        else:
            self.camera.current_level = 6

        # Ambil factory level
        level_factory = self.level_definitions.get(level_key)

        if level_factory:
            try:
                # Buat instance level
                self.active_level_instance = level_factory(
                    self.camera, self.screen, self.main_menu.font
                )

                # Set durasi level dari pilihan menu
                self.active_level_instance.level_duration = self.selected_duration
                self.active_level_instance.start_time = pygame.time.get_ticks()

                print(f"[INFO] Durasi level: {self.selected_duration//60} menit")

                # === INI YANG PENTING ===
                self.active_level_instance.level_key = level_key

                # Set UI
                self.active_level_instance.set_ui(self.ui)

                # Masuk gameplay
                self.current_game_state = "PLAYING_LEVEL"

                print(f"[INFO] Level '{level_key}' dimulai dengan kamera level {self.camera.current_level}")

            except Exception as e:
                print(f"[ERROR] Gagal memulai level '{level_key}': {e}")
        else:
            print(f"[ERROR] Level '{level_key}' tidak ditemukan di level_definitions!")

    def run(self):
        # --- PERUBAHAN UNTUK DEBUGGING ---
        # Jalankan debugger di thread terpisah
        self.debugger.start()
        # --------------------------------
        
        while True:
            # --- PERUBAHAN UNTUK DEBUGGING ---
            # Berikan data FPS game ke instance kamera agar debugger bisa membacanya
            # Ini lebih akurat daripada menghitung FPS di dalam thread debug itu sendiri
            current_fps = self.clock.get_fps()
            self.camera.game_fps = current_fps # Anda perlu menambahkan atribut ini di camera_debug.py

            # Event handling umum
            for event in pygame.event.get():  # Get all events
                if event.type == pygame.QUIT:
                    if self.camera:
                        self.camera.release()
                    pygame.quit()
                    sys.exit()

                # === Tangani tombol ESC (pause lewat keyboard) ===
                if self.current_game_state == "PLAYING_LEVEL" and event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.active_level_instance:
                            # Simpan layar saat ini sebelum masuk ke menu pause
                            self.last_game_surface_before_pause = self.screen.copy()
                            self.current_game_state = "PAUSE_MENU"

                # === Tangani klik tombol pause di UI ===
                if self.ui:
                    self.ui.handle_event(event, self)

            # State machine utama
            if self.current_game_state == "MENU":
                menu_action = self.main_menu.show_main_menu()
                if menu_action == "PLAY": 
                    self.start_level("LEVEL_1")
                elif menu_action == "LEVELS":
                    self.current_game_state = "LEVEL_SELECT_MENU"
                elif menu_action == "QUIT":
                    if self.camera: self.camera.release()
                    pygame.quit()
                    sys.exit()

            elif self.current_game_state == "LEVEL_SELECT_MENU":
                level_choice = self.main_menu.show_levels_menu()
                if level_choice == "BACK":
                    self.current_game_state = "MENU"
                elif level_choice == "TRIAL": 
                    self.start_level("TRIAL")
                elif level_choice == "LEVEL_1":
                    self.start_level("LEVEL_1")
                elif level_choice == "LEVEL_2": 
                    self.start_level("LEVEL_2")
                elif level_choice == "LEVEL_3": 
                    self.start_level("LEVEL_3")
                elif level_choice == "LEVEL_4": 
                    self.start_level("LEVEL_4")
                elif level_choice == "LEVEL_5": 
                    self.start_level("LEVEL_5")
                elif level_choice == "LEVEL_6": 
                    self.start_level("LEVEL_6")
                elif level_choice == "LEVEL_7": 
                    self.start_level("LEVEL_7")
                elif level_choice == "LEVEL_8": 
                    self.start_level("LEVEL_8")

            elif self.current_game_state == "PLAYING_LEVEL":
                self.screen.fill("black") 
                if self.active_level_instance:
                    level_status = self.active_level_instance.run()

                    self.ui.display(self.active_level_instance.player, getattr(self.active_level_instance, "hearts_to_collect", 0))

                    if getattr(self.active_level_instance, "level_complete", False):
                        total_valid = getattr(self.active_level_instance, "gesture_valid_count", 0)
                        total_gesture = getattr(self.active_level_instance, "gesture_total_count", 0)
                        avg_conf = getattr(self.active_level_instance, "avg_confidence", 0.0)
                        play_time = getattr(self.active_level_instance, "play_time", "00:00")

                        # BARU reset
                        self.active_level_instance = None
                        self.current_game_state = "MENU"

                        self.show_evaluation_screen(total_valid, total_gesture, avg_conf, play_time)

                    if level_status == "LEVEL_COMPLETE_PROCEED":
                        print(f"{self.current_level_key} complete. Proceeding...")
                        if self.current_level_key == "LEVEL_1":
                            self.start_level("LEVEL_2")
                        elif self.current_level_key == "LEVEL_2":
                            self.start_level("LEVEL_3")
                        elif self.current_level_key == "LEVEL_3":
                            self.start_level("LEVEL_4")
                        elif self.current_level_key == "LEVEL_4":
                            self.start_level("LEVEL_5")
                        elif self.current_level_key == "LEVEL_5":
                            self.start_level("LEVEL_6")
                        elif self.current_level_key == "LEVEL_6":
                            self.start_level("LEVEL_7")
                        elif self.current_level_key == "LEVEL_7":
                            self.start_level("LEVEL_8")
                        elif self.current_level_key == "LEVEL_8":
                            print("Level 8 complete! Congratulations!")
                            self.active_level_instance = None
                            self.current_game_state = "MENU"
                        else:
                            print(f"No next level defined after {self.current_level_key}. Returning to menu.")
                            self.active_level_instance = None
                            self.current_game_state = "MENU"
                    
                    elif level_status == "RETURN_TO_MENU":
                        self.active_level_instance = None
                        self.current_game_state = "MENU"
                    
                    elif level_status == "PAUSED": 
                        # Simpan layar saat ini jika status PAUSED dikembalikan oleh level
                        # (Meskipun lebih umum K_ESCAPE ditangani di loop utama Game)
                        if not hasattr(self, 'last_game_surface_before_pause'):
                             self.last_game_surface_before_pause = self.screen.copy()
                        self.current_game_state = "PAUSE_MENU"

                else:
                    print("Error: No active level instance while in PLAYING_LEVEL state.")
                    self.current_game_state = "MENU"
            
            elif self.current_game_state == "PAUSE_MENU":
                pause_action = self.main_menu.show_pause_menu(getattr(self, 'last_game_surface_before_pause', None))
                if pause_action == "RESUME":
                    self.current_game_state = "PLAYING_LEVEL"
                elif pause_action == "MENU":
                    self.active_level_instance = None 
                    self.current_game_state = "MENU"
                
                if hasattr(self, 'last_game_surface_before_pause'):
                    del self.last_game_surface_before_pause
                
                if self.ui.is_paused:
                    overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 150))
                    self.screen.blit(overlay, (0, 0))

                    font = pygame.font.Font(None, 60)
                    text = font.render("Game Paused", True, (255, 255, 255))
                    text_rect = text.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2))
                    self.screen.blit(text, text_rect)

                    pygame.display.update()
                    self.clock.tick(FPS)
                    continue  # lewati update game kalau paused

            pygame.display.update()
            self.clock.tick(FPS)

    def show_evaluation_screen(self, total_valid, total_gesture, avg_confidence, play_time):

        font_title = pygame.font.Font(None, 60)
        font_text = pygame.font.Font(None, 40)
        font_button = pygame.font.Font(None, 36)

        WHITE = (255, 255, 255)
        BLACK = (0, 0, 0)
        GREY = (40, 40, 40)
        BLUE = (0, 120, 255)

        popup_width, popup_height = 600, 360
        popup_rect = pygame.Rect(
            (self.screen.get_width() - popup_width) // 2,
            (self.screen.get_height() - popup_height) // 2,
            popup_width,
            popup_height
        )

        # Posisi tombol
        button_width, button_height = 250, 60
        button_rect = pygame.Rect(
            popup_rect.centerx - button_width // 2,
            popup_rect.bottom - button_height - 15,
            button_width,
            button_height
        )

        # BUAT TOMBOL SEKALI SAJA
        back_button = Button(button_rect.center, "BACK TO MENU", font_button, "white", "blue")

        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if back_button.check_click(event.pos):
                        print("[DEBUG] Back to Menu diklik")
                        self.current_game_state = "MENU"
                        self.active_level_instance = None
                        return

            self.screen.fill(BLACK)

            pygame.draw.rect(self.screen, GREY, popup_rect, border_radius=20)
            pygame.draw.rect(self.screen, WHITE, popup_rect, 3, border_radius=20)

            # Teks
            title_text = font_title.render("Evaluasi Level Selesai", True, WHITE)
            valid_text = font_text.render(f"Gesture Valid: {total_valid} dari {total_gesture}", True, WHITE)
            conf_text = font_text.render(f"Rata-rata Confidence: {avg_confidence:.2f}%", True, WHITE)
            time_text = font_text.render(f"Waktu Bermain: {play_time}", True, WHITE)

            self.screen.blit(title_text, (popup_rect.centerx - title_text.get_width() // 2, popup_rect.top + 40))
            self.screen.blit(valid_text, (popup_rect.centerx - valid_text.get_width() // 2, popup_rect.top + 120))
            self.screen.blit(conf_text, (popup_rect.centerx - conf_text.get_width() // 2, popup_rect.top + 170))
            self.screen.blit(time_text, (popup_rect.centerx - time_text.get_width() // 2, popup_rect.top + 210))

            # Tombol (UPDATE ONLY)
            back_button.change_color(pygame.mouse.get_pos())
            back_button.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(30)

if __name__ == '__main__':
    game = Game()
    try:
        game.run()
    finally:
        # --- PERUBAHAN UNTUK DEBUGGING ---
        # Pastikan debugger dan kamera dihentikan dengan benar saat program keluar
        print("\nExiting game...")
        if hasattr(game, 'debugger'):
            game.debugger.stop()
        if hasattr(game, 'camera'):
            game.camera.release()
        pygame.quit()
        sys.exit()