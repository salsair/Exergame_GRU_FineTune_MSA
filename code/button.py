import pygame

class Button:
    def __init__(self, pos, text, font, base_color, hover_color, bg_color=(50, 50, 50)):
        """
        pos: tuple (x, y) posisi tengah tombol
        text: isi teks tombol
        font: objek font pygame
        base_color: warna teks normal
        hover_color: warna teks saat hover
        bg_color: warna dasar background tombol (opsional)
        """
        self.text_input = text
        self.font = font
        self.base_color = base_color
        self.hover_color = hover_color
        self.bg_color = bg_color
        self.is_hovered = False

        # Render teks
        self.text_surface = self.font.render(self.text_input, True, self.base_color)
        self.rect = self.text_surface.get_rect(center=pos)

        # Background tombol (lebih besar sedikit)
        self.bg_rect = self.rect.inflate(60, 30)  # padding background

    def draw(self, screen):
        """Gambar tombol (background + teks)"""
        # Warna background berubah sedikit saat hover
        if self.is_hovered:
            bg_color = tuple(min(255, c + 40) for c in self.bg_color)  # lebih terang saat hover
        else:
            bg_color = self.bg_color

        # Gambar background & border
        pygame.draw.rect(screen, bg_color, self.bg_rect, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), self.bg_rect, 2, border_radius=10)

        # Gambar teks
        screen.blit(self.text_surface, self.rect)

    def change_color(self, mouse_pos):
        """Ubah warna teks dan status hover berdasarkan posisi mouse"""
        self.is_hovered = self.bg_rect.collidepoint(mouse_pos)
        color = self.hover_color if self.is_hovered else self.base_color
        self.text_surface = self.font.render(self.text_input, True, color)

    def check_click(self, mouse_pos):
        """True jika tombol diklik"""
        return self.bg_rect.collidepoint(mouse_pos)
