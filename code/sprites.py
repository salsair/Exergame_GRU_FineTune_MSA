import pygame
from settings import *
from random import choice

class Tile(pygame.sprite.Sprite):
    def __init__(self, pos, groups, sprite_type, surface=None):
        super().__init__(groups)
        self.sprite_type = sprite_type
        
        if surface:
            self.image = surface
        else:
            self.image = pygame.Surface((TILESIZE, TILESIZE))
            if sprite_type == 'invisible':
                # An invisible tile doesn't need to be drawn, but it still exists for collision.
                # A more efficient way would be to just use pygame.Rects for invisible walls.
                # For simplicity, we'll keep it as a transparent sprite.
                self.image.set_colorkey('black') # Make it transparent
                self.image.fill('black')
            else:
                self.image.fill((139, 69, 19)) # Generic color
        
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect # By default, hitbox is the same as the rect

    def update(self, **kwargs):
        # This method is added to ensure that Tile objects can safely receive
        # arguments from a group's update call without crashing.
        pass

# The rest of your sprites.py file (Player, Item) would be here.
# NOTE: The Player class in this file seems to be a different, simpler version
# than the one in level/player.py. Ensure you are using the correct Player class
# (from level/player.py) in your main game. The changes for the dwell time
# should be applied to the Player class you are actively using.

