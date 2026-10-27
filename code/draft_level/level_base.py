import pygame

class LevelBase:
    def __init__(self, screen):
        self.screen = screen

    def run(self):
        self.screen.fill("blue")
        font = pygame.font.Font(None, 50)
        text = font.render("Base Level", True, "white")
        self.screen.blit(text, (100, 100))