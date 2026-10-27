import pygame

class Camera:
    """
    Kamera untuk viewport peta (scrolling). 
    offset adalah Vector2(x, y) yang menunjukkan posisi kiri-atas kamera di world coords.
    update(target) menerima object dengan .rect (mis. player) dan meng-update offset.
    """
    def __init__(self, width, height, screen_width, screen_height):
        self.width = width
        self.height = height
        self.screen_width = screen_width
        self.screen_height = screen_height

        # offset world coordinates (kiri-atas kamera)
        self.offset = pygame.math.Vector2(0, 0)

        # camera rect (optional, kalau perlu)
        self.camera_rect = pygame.Rect(0, 0, width, height)

    def apply(self, entity):
        """Return rect yang sudah disesuaikan dengan camera offset."""
        return entity.rect.move(-self.offset.x, -self.offset.y)

    def apply_rect(self, rect):
        return rect.move(-self.offset.x, -self.offset.y)

    def update(self, target):
        """
        Ikuti target (biasanya player). 
        target harus punya attribute .rect.centerx / .rect.centery.
        """
        # center kamera di target
        self.offset.x = target.rect.centerx - self.screen_width // 2
        self.offset.y = target.rect.centery - self.screen_height // 2

        # clamp agar kamera tidak keluar dari bounds map
        max_x = max(0, self.width - self.screen_width)
        max_y = max(0, self.height - self.screen_height)

        # pastikan offset berada di range [0, max_x] dan [0, max_y]
        if self.offset.x < 0:
            self.offset.x = 0
        elif self.offset.x > max_x:
            self.offset.x = max_x

        if self.offset.y < 0:
            self.offset.y = 0
        elif self.offset.y > max_y:
            self.offset.y = max_y

        # sinkronkan camera_rect (opsional)
        self.camera_rect.topleft = (int(self.offset.x), int(self.offset.y))
