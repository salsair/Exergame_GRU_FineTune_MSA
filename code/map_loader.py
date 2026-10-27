import pygame
import pytmx

class TiledMap:
    def __init__(self, filename, scale=4):
        self.tmxdata = pytmx.load_pygame(filename, pixelalpha=True)

        # simpan scale
        self.SCALE = scale

        # ukuran tile setelah scaling
        self.tilewidth = self.tmxdata.tilewidth * self.SCALE
        self.tileheight = self.tmxdata.tileheight * self.SCALE

        # ukuran map setelah scaling
        self.width = self.tmxdata.width * self.tilewidth
        self.height = self.tmxdata.height * self.tileheight

        self.rect = pygame.Rect(0, 0, self.width, self.height)  # <-- safer

    def render(self, surface):
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = self.tmxdata.get_tile_image_by_gid(gid)
                    if tile:
                        
                        scaled_tile = pygame.transform.scale(
                            tile,
                            (self.tilewidth, self.tileheight)
                        )

                        surface.blit(
                            scaled_tile,
                            (x * self.tilewidth, y * self.tileheight)
                        )
            
    def get_size(self):
        return (self.width, self.height)
