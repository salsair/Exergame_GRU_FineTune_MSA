import os
import pygame
from csv import reader
from settings import *

def import_csv_layout(path):
    """Import CSV layout for map creation"""
    terrain_map = []
    if os.path.exists(path):
        with open(path) as level_map:
            layout = reader(level_map, delimiter=',')
            for row in layout:
                terrain_map.append(list(row))
    else:
        # Create default layout if file doesn't exist
        terrain_map = [['-1' for _ in range(20)] for _ in range(15)]
        # Add some boundaries
        for i in range(20):
            terrain_map[0][i] = '0'  # Top boundary
            terrain_map[14][i] = '0'  # Bottom boundary
        for i in range(15):
            terrain_map[i][0] = '0'  # Left boundary
            terrain_map[i][19] = '0'  # Right boundary
    return terrain_map

def import_folder(path):
    """Import all images from a folder"""
    surface_list = []
    if os.path.exists(path):
        for _, __, img_files in os.walk(path):
            for image in img_files:
                full_path = path + '/' + image
                image_surf = pygame.image.load(full_path).convert_alpha()
                surface_list.append(image_surf)
    else:
        # Create default surfaces if folder doesn't exist
        default_surf = pygame.Surface((TILESIZE, TILESIZE))
        default_surf.fill((100, 200, 100))  # Green color
        surface_list.append(default_surf)
    return surface_list