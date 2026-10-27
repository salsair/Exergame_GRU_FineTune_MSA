import pygame, os

class TutorialOverlay:
    def __init__(self, screen, game, level_key=None):
        self.screen = screen
        self.game = game
        self.level_key = level_key
        self.margin = 20
        self.popup_w = 600
        self.popup_h = 520

        # Font mengikuti gaya sebelumnya
        self.font = pygame.font.Font(None, 22)
        self.title_font = pygame.font.Font(None, 32)

        # Load gesture images
        self.gestures = {
            "thumb_index": pygame.image.load("graphics/tutorials/kiri.png"),
            "grabbing": pygame.image.load("graphics/tutorials/kanan.png"),
            "palm": pygame.image.load("graphics/tutorials/atas.png"),
            "fist": pygame.image.load("graphics/tutorials/bawah.png")
        }

        # Instructions
        self.instructions = {
            "thumb_index": "Gerakan ke kiri - Buka jari-jari tangan seperti mau mencakar",
            "grabbing": "Gerakan ke kanan - Posisi tangan membentuk pistol mainan",
            "palm": "Gerakan ke atas - Buka telapak tangan lebar-lebar",
            "fist": "Gerakan ke bawah - Kepalkan tangan kuat-kuat"
        }

        # Informasi tambahan
        self.extra_info = [
            "Waktu permainan tiap level: 4 menit.",
            "Gambar cinta yang dikumpulkan per level: Level 3: 3 cinta, Level 4 = 3 cinta, Level 5 = 3 cinta, Level 6 = 4 cinta, Level 7 = 4 cinta, Level 8 = 4 cinta.",
            "Gerakan Level 1 adalah gerakan atas-bawah.",
            "Gerakan Level 2 adalah Gerakan kiri-kanan.",
            "Gerakan Level 3 sampai Level 8 adalah Gerakan atas-bawah dan kiri-kanan."
        ]

        self.scroll_offset = 0
        self.scroll_speed = 25

    def show_help_menu(self):
        sw, sh = self.screen.get_size()
        popup_rect = pygame.Rect((sw - self.popup_w)//2, (sh - self.popup_h)//2, self.popup_w, self.popup_h)
        clock = pygame.time.Clock()
        running = True

        if self.level_key == "LEVEL_1":
            gesture_labels = ["palm", "fist"]          # atas & bawah
        elif self.level_key == "LEVEL_2":
            gesture_labels = ["thumb_index", "grabbing"]  # kiri & kanan
        else:
            gesture_labels = list(self.gestures.keys())   # semua (LEVEL 3–8)

        content_rect = pygame.Rect(popup_rect.x + 20, popup_rect.y + 60, self.popup_w - 40, self.popup_h - 120)

        time_buttons = [
            ("3 Menit", 180),
            ("4 Menit", 240),
            ("5 Menit", 300),
            ("7 Menit", 420)
        ]

        btn_y = popup_rect.y + 120
        btn_x = popup_rect.x + 20

        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); raise SystemExit

                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    running = False

                if ev.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = pygame.mouse.get_pos()

                    # BACK BUTTON
                    back_btn = pygame.Rect(popup_rect.centerx - 70, popup_rect.bottom - 50, 140, 35)
                    if back_btn.collidepoint((mx, my)):
                        running = False
                        continue

                    # TIME BUTTONS
                    for i, (label, seconds) in enumerate(time_buttons):
                        btn = pygame.Rect(btn_x + i*140, btn_y, 120, 35)
                        if btn.collidepoint((mx, my)):
                            self.game.selected_duration = seconds
                            print(f"[INFO] Timer diset ke {seconds//60} menit")

                if ev.type == pygame.MOUSEWHEEL:
                    self.scroll_offset += -ev.y * self.scroll_speed
                    self.scroll_offset = max(min(self.scroll_offset, 2000), -2000)

            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))

            pygame.draw.rect(self.screen, (40, 40, 40), popup_rect, border_radius=12)
            pygame.draw.rect(self.screen, (100, 100, 100), popup_rect, 3, border_radius=12)

            title = self.title_font.render("Panduan Gerakan Tangan", True, (255, 255, 255))
            self.screen.blit(title, (popup_rect.x + 20, popup_rect.y + 15))

            # Surface content scroll
            content_surface = pygame.Surface((content_rect.w, 2000), pygame.SRCALPHA)
            y = 40

            btn_y = popup_rect.y + 50
            btn_x = popup_rect.x + 20

            for i, (label, seconds) in enumerate(time_buttons):
                btn = pygame.Rect(btn_x + i*140, btn_y, 120, 35)

                color = (0, 200, 0) if self.game.selected_duration == seconds else (0, 150, 200)

                pygame.draw.rect(self.screen, color, btn, border_radius=6)

                txt = self.font.render(label, True, (255,255,255))
                self.screen.blit(txt, txt.get_rect(center=btn.center))

            for label in gesture_labels:
                img = pygame.transform.smoothscale(self.gestures[label], (200, 100))
                content_surface.blit(img, (0, y))

                wrapped = self.wrap_text(self.instructions[label], self.font, 360)
                ty = y
                for line in wrapped:
                    t = self.font.render(line, True, (230, 230, 230))
                    content_surface.blit(t, (220, ty))
                    ty += 22
                y += 120

            # Extra info
            for text in self.extra_info:
                wrapped = self.wrap_text(text, self.font, content_rect.w - 10)
                for line in wrapped:
                    t = self.font.render(line, True, (230, 230, 230))
                    content_surface.blit(t, (0, y))
                    y += 22
                y += 10

            # Clip
            clipped = content_surface.subsurface(pygame.Rect(0, max(self.scroll_offset,0), content_rect.w, content_rect.h))
            self.screen.blit(clipped, (content_rect.x, content_rect.y))

            back_btn = pygame.Rect(popup_rect.centerx - 70, popup_rect.bottom - 50, 140, 35)
            pygame.draw.rect(self.screen, (0, 120, 200), back_btn, border_radius=6)
            back_text = self.font.render("Back to Menu", True, (255, 255, 255))
            self.screen.blit(back_text, back_text.get_rect(center=back_btn.center))

            pygame.display.flip()
            clock.tick(30)

    def wrap_text(self, text, font, max_width):
        words = text.split(' ')
        lines, current = [], ""
        for w in words:
            test = f"{current} {w}".strip()
            if font.size(test)[0] <= max_width:
                current = test
            else:
                lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines
