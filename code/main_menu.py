import pygame, sys
import os
from button import Button
from settings import *
from tutorial_overlay import TutorialOverlay

class MainMenu:
    def __init__(self, screen, game):
        self.screen = screen
        self.game = game
        self.font = pygame.font.Font("graphics/font/joystix.ttf", 45) if os.path.exists("graphics/font/joystix.ttf") else pygame.font.Font(None, 45)
        self.tutorial = TutorialOverlay(self.screen, self.game)

        # Load background image (fallback to gradient if not found)
        try:
            self.background = pygame.image.load("graphics/tilemap/Background.png")
            self.background = pygame.transform.scale(self.background, (WIDTH, HEIGHT))
        except:
            # Create gradient background as fallback
            self.background = self.create_gradient_background()

    def create_gradient_background(self):
        """Create a gradient background if image not found"""
        surface = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            color_intensity = int(255 * (y / HEIGHT))
            color = (color_intensity // 4, color_intensity // 3, color_intensity // 2)
            pygame.draw.line(surface, color, (0, y), (WIDTH, y))
        return surface

    def get_font(self, size):
        if os.path.exists("graphics/font/joystix.ttf"):
            return pygame.font.Font("graphics/font/joystix.ttf", size)
        return pygame.font.Font(None, size)

    def show_main_menu(self):
        while True:
            self.screen.blit(self.background, (0, 0))
            mouse_pos = pygame.mouse.get_pos()

            # Judul dengan shadow
            title = self.get_font(80).render("MAIN MENU", True, TEXT_COLOR_SELECTED)
            title_rect = title.get_rect(center=(WIDTH // 2, 100))
            shadow = self.get_font(80).render("MAIN MENU", True, (50, 50, 50))
            self.screen.blit(shadow, (title_rect.x + 3, title_rect.y + 3))
            self.screen.blit(title, title_rect)

            # === Tombol utama ===
            play_button = Button((WIDTH // 2, 250), "PLAY", self.get_font(50), "white", "green")
            levels_button = Button((WIDTH // 2, 375), "LEVELS", self.get_font(50), "white", "dodgerblue")
            quit_button = Button((WIDTH // 2, 500), "QUIT", self.get_font(50), "white", "red")
            help_button = Button((WIDTH - 90, 50), "HELP", self.get_font(28), "white", "yellow")

            buttons = [play_button, levels_button, quit_button, help_button]

            for button in buttons:
                button.change_color(mouse_pos)
                button.draw(self.screen)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if play_button.check_click(mouse_pos):
                        return "PLAY"
                    if levels_button.check_click(mouse_pos):
                        return "LEVELS"
                    if help_button.check_click(mouse_pos):
                        self.tutorial.show_help_menu()
                        pygame.event.clear()
                    if quit_button.check_click(mouse_pos):
                        return "QUIT"

            pygame.display.update()


    def show_pause_menu(self, frozen_surface=None):
        while True:
            # Tampilkan tampilan game beku + overlay
            if frozen_surface:
                self.screen.blit(frozen_surface, (0, 0))
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.set_alpha(150)
                overlay.fill((0, 0, 0))
                self.screen.blit(overlay, (0, 0))
            else:
                self.screen.fill("gray")

            mouse_pos = pygame.mouse.get_pos()

            # Judul PAUSED
            pause_title = self.get_font(60).render("PAUSED", True, "white")
            pause_rect = pause_title.get_rect(center=(WIDTH // 2, 150))
            self.screen.blit(pause_title, pause_rect)

            # Tombol
            resume_button = Button((WIDTH // 2, 280), "RESUME", self.get_font(50), "white", "green")
            menu_button = Button((WIDTH // 2, 400), "MENU", self.get_font(50), "white", "orange")

            for button in [resume_button, menu_button]:
                button.change_color(mouse_pos)
                button.draw(self.screen)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return "RESUME"
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if resume_button.check_click(mouse_pos):
                        return "RESUME"
                    if menu_button.check_click(mouse_pos):
                        return "MENU"

            pygame.display.update()


    def show_levels_menu(self):
        scroll_y = 0  # posisi scroll
        scroll_speed = 50  # seberapa cepat scroll

        # Daftar level
        level_names = ["TRIAL"] + [f"LEVEL {i}" for i in range(1, 9)] + ["BACK"]

        while True:
            self.screen.fill("black")
            mouse_pos = pygame.mouse.get_pos()

            title = self.get_font(80).render("LEVELS", True, TEXT_COLOR_SELECTED)
            title_rect = title.get_rect(center=(WIDTH//2, 100 - scroll_y))
            self.screen.blit(title, title_rect)

            buttons = []
            start_y = 250  # posisi awal tombol
            gap = 100      # jarak antar tombol

            for i, name in enumerate(level_names):
                btn_y = start_y + i * gap - scroll_y
                if name == "TRIAL":
                    color = "green"
                elif name == "BACK":
                    color = "red"
                else:
                    color = "blue"

                button = Button((WIDTH//2, btn_y), name, self.get_font(50), "white", color)
                button.change_color(mouse_pos)
                button.draw(self.screen)
                buttons.append((name, button))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4:  # scroll up
                        scroll_y = max(0, scroll_y - scroll_speed)
                    elif event.button == 5:  # scroll down
                        scroll_y += scroll_speed
                    else:
                        for name, button in buttons:
                            if button.check_click(mouse_pos):
                                if name == "BACK":
                                    return "BACK"
                                return name.replace(" ", "_")  # TRIAL, LEVEL_1, LEVEL_2, ...
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        scroll_y = max(0, scroll_y - scroll_speed)
                    elif event.key == pygame.K_DOWN:
                        scroll_y += scroll_speed

            pygame.display.update()
