### main.py
import pygame, sys
from settings import *
from main_menu import MainMenu
from code.level.sample_level import Level1

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('My Game')
        self.clock = pygame.time.Clock()
        self.state = "MENU"

        self.menu = MainMenu(self.screen)
        self.level = None

    def run(self):
        while True:
            if self.state == "MENU":
                result = self.menu.show_main_menu()
                if result == "PLAY":
                    self.level = Level1(self.screen)
                    self.state = "PLAY"
                elif result == "QUIT":
                    pygame.quit()
                    sys.exit()

            elif self.state == "PLAY":
                self.level.run()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        result = self.menu.show_pause_menu()
                        if result == "MENU":
                            self.state = "MENU"
                        elif result == "RESUME":
                            self.state = "PLAY"

            pygame.display.update()
            self.clock.tick(FPS)

if __name__ == '__main__':
    game = Game()
    game.run()


### settings.py
WIDTH = 1280
HEIGHT = 720
FPS = 60


### main_menu.py
import pygame, sys
from button import Button

class MainMenu:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font("assets/font.ttf", 45)

    def get_font(self, size):
        return pygame.font.Font("assets/font.ttf", size)

    def show_main_menu(self):
        while True:
            self.screen.fill("black")
            mouse_pos = pygame.mouse.get_pos()

            title = self.get_font(80).render("MAIN MENU", True, "white")
            self.screen.blit(title, title.get_rect(center=(640, 100)))

            play_button = Button((640, 250), "PLAY", self.get_font(50), "white", "green")
            quit_button = Button((640, 400), "QUIT", self.get_font(50), "white", "green")

            for button in [play_button, quit_button]:
                button.change_color(mouse_pos)
                button.draw(self.screen)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if play_button.check_click(mouse_pos):
                        return "PLAY"
                    if quit_button.check_click(mouse_pos):
                        return "QUIT"

            pygame.display.update()

    def show_pause_menu(self):
        while True:
            self.screen.fill("gray")
            mouse_pos = pygame.mouse.get_pos()

            resume_button = Button((640, 250), "RESUME", self.get_font(50), "white", "yellow")
            menu_button = Button((640, 400), "MENU", self.get_font(50), "white", "yellow")

            for button in [resume_button, menu_button]:
                button.change_color(mouse_pos)
                button.draw(self.screen)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if resume_button.check_click(mouse_pos):
                        return "RESUME"
                    if menu_button.check_click(mouse_pos):
                        return "MENU"

            pygame.display.update()


### button.py
import pygame

class Button:
    def __init__(self, pos, text, font, base_color, hover_color):
        self.text = text
        self.font = font
        self.base_color = base_color
        self.hover_color = hover_color
        self.text_surface = self.font.render(self.text, True, self.base_color)
        self.rect = self.text_surface.get_rect(center=pos)

    def draw(self, screen):
        screen.blit(self.text_surface, self.rect)

    def check_click(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

    def change_color(self, mouse_pos):
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.base_color
        self.text_surface = self.font.render(self.text, True, color)


### level/level_base.py
import pygame

class LevelBase:
    def __init__(self, screen):
        self.screen = screen

    def run(self):
        self.screen.fill("blue")
        font = pygame.font.Font(None, 50)
        text = font.render("Base Level", True, "white")
        self.screen.blit(text, (100, 100))


### level/level1.py
from level.level_base import LevelBase

class Level1(LevelBase):
    def run(self):
        self.screen.fill("green")
        font = pygame.font.Font(None, 50)
        text = font.render("Level 1", True, "white")
        self.screen.blit(text, (100, 100))
