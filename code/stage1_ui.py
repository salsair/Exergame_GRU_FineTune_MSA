"""
stage1_ui.py
============
Tampilan aplikasi akuisisi Tahap 1 berbasis Pygame (teks anti-alias, rasio
gambar kamera terjaga, kartu contoh gestur di kanan atas).

Modul ini hanya menggambar dan membaca tombol. Logika rekam ada di
collect_stage1.py, penyimpanan di stage1_writer.py.
"""

import os

import pygame

WINDOW_SIZE = (1280, 720)

BG = (18, 20, 24)
PANEL = (0, 0, 0, 175)
WHITE = (245, 245, 245)
MUTED = (190, 196, 204)
GREEN = (72, 199, 116)
RED = (232, 76, 61)
AMBER = (245, 176, 65)
CARD_BORDER = (255, 255, 255)

KEY_MAP = {
    pygame.K_SPACE: "space",
    pygame.K_RETURN: "enter",
    pygame.K_KP_ENTER: "enter",
    pygame.K_r: "r",
    pygame.K_s: "s",
    pygame.K_q: "quit",
    pygame.K_ESCAPE: "quit",
}

DISPLAY_NAMES = {"palm": "Palm", "fist": "Fist", "grabbing": "Grabbing", "thumb_index": "Thumb Index"}


def _font(size, bold=False):
    for name in ("segoeui", "arial", "helvetica", "dejavusans"):
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size + 6)


class Stage1UI:
    def __init__(self, title, instructions, images_dir, size=WINDOW_SIZE):
        pygame.init()
        pygame.display.set_caption(title)
        # SCALED: jendela boleh diubah ukurannya tanpa meregangkan gambar.
        self.screen = pygame.display.set_mode(size, pygame.SCALED | pygame.RESIZABLE)
        self.size = size
        self.instructions = instructions
        self.f_title = _font(30, bold=True)
        self.f_body = _font(22)
        self.f_small = _font(18)
        self.f_big = _font(44, bold=True)
        self.card_size = 200
        self.images = {}
        for g in instructions:
            path = os.path.join(images_dir, f"{g}.png")
            if os.path.exists(path):
                img = pygame.image.load(path).convert()
                self.images[g] = pygame.transform.smoothscale(img, (self.card_size, self.card_size))
            else:
                print(f"[PERINGATAN] Gambar contoh tidak ditemukan: {path}")

    # ------------------------------------------------------------------
    def poll(self):
        """Kembalikan daftar tombol logis yang ditekan sejak panggilan sebelumnya."""
        keys = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                keys.append("quit")
            elif event.type == pygame.KEYDOWN:
                keys.append(KEY_MAP.get(event.key, "other"))
        return keys

    def close(self):
        pygame.quit()

    # ------------------------------------------------------------------
    def _panel(self, rect, alpha_color=PANEL, radius=0):
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, alpha_color, surf.get_rect(), border_radius=radius)
        self.screen.blit(surf, rect.topleft)

    def _text(self, text, font, color, pos, anchor="topleft"):
        surf = font.render(text, True, color)
        rect = surf.get_rect(**{anchor: pos})
        self.screen.blit(surf, rect)
        return rect

    def _camera(self, frame_rgb):
        h, w = frame_rgb.shape[:2]
        surf = pygame.image.frombuffer(frame_rgb.tobytes(), (w, h), "RGB")
        sw, sh = self.size
        scale = min(sw / w, sh / h)
        tw, th = int(w * scale), int(h * scale)
        if (tw, th) != (w, h):
            surf = pygame.transform.smoothscale(surf, (tw, th))
        self.screen.fill(BG)
        self.screen.blit(surf, ((sw - tw) // 2, (sh - th) // 2))

    def _card(self, gesture, top):
        sw, _ = self.size
        pad = 12
        x = sw - self.card_size - 24
        box = pygame.Rect(x - pad, top, self.card_size + 2 * pad, self.card_size + 2 * pad + 30)
        self._panel(box, (0, 0, 0, 190), radius=14)
        self._text("Contoh gestur", self.f_small, MUTED, (box.centerx, box.top + 8), "midtop")
        img_rect = pygame.Rect(x, box.top + 34, self.card_size, self.card_size)
        if gesture in self.images:
            self.screen.blit(self.images[gesture], img_rect.topleft)
        else:
            pygame.draw.rect(self.screen, (60, 60, 60), img_rect)
            self._text("gambar tidak ada", self.f_small, MUTED, img_rect.center, "center")
        pygame.draw.rect(self.screen, CARD_BORDER, img_rect, 2, border_radius=6)

    # ------------------------------------------------------------------
    def render(self, frame_rgb, view):
        """
        view: state ('SIAP'|'REKAM'|'TINJAU'), trial_idx, n_trials, gesture, rep, reps,
              detected, hold, remaining, summary, quit_pending, warn_threshold
        """
        sw, sh = self.size
        self._camera(frame_rgb)
        state, gesture = view["state"], view["gesture"]

        # --- bilah atas -------------------------------------------------
        top = pygame.Rect(0, 0, sw, 92)
        self._panel(top)
        self._text(f"{DISPLAY_NAMES[gesture]}  ·  ulangan {view['rep']} dari {view['reps']}",
                   self.f_title, WHITE, (24, 14))
        self._text(self.instructions[gesture], self.f_body, MUTED, (24, 54))
        self._text(f"Percobaan {view['trial_idx'] + 1} / {view['n_trials']}", self.f_body, WHITE,
                   (sw - 24, 18), "topright")

        # progres keseluruhan
        frac = view["trial_idx"] / max(1, view["n_trials"])
        pygame.draw.rect(self.screen, (70, 70, 70), (0, 92, sw, 4))
        pygame.draw.rect(self.screen, GREEN, (0, 92, int(sw * frac), 4))

        # --- kartu contoh gestur (kanan atas) ---------------------------
        self._card(gesture, top=112)

        # --- status deteksi (kiri bawah atas bilah bawah) ---------------
        det = view["detected"]
        pill = pygame.Rect(24, sh - 140, 250, 40)
        self._panel(pill, (0, 0, 0, 175), radius=20)
        pygame.draw.circle(self.screen, GREEN if det else RED, (pill.left + 22, pill.centery), 9)
        self._text("Tangan terdeteksi" if det else "Tangan tidak terdeteksi",
                   self.f_small, WHITE, (pill.left + 42, pill.centery), "midleft")

        # --- bilah bawah sesuai status ----------------------------------
        bottom = pygame.Rect(0, sh - 84, sw, 84)
        self._panel(bottom)
        if state == "SIAP":
            self._text("Tekan SPASI saat gestur sudah terbentuk", self.f_title, WHITE,
                       (24, bottom.centery), "midleft")
            self._text("Q / ESC: keluar", self.f_small, MUTED, (sw - 24, bottom.centery), "midright")
        elif state == "REKAM":
            pygame.draw.rect(self.screen, RED, (0, 0, sw, sh), 8)
            self._text("MEREKAM", self.f_title, RED, (24, bottom.top + 12))
            self._text(f"{view['remaining']:.1f} s", self.f_title, WHITE, (sw - 24, bottom.top + 12), "topright")
            bar = pygame.Rect(24, bottom.top + 56, sw - 48, 12)
            pygame.draw.rect(self.screen, (80, 80, 80), bar, border_radius=6)
            done = 1.0 - view["remaining"] / max(1e-6, view["hold"])
            pygame.draw.rect(self.screen, RED, (bar.left, bar.top, int(bar.width * done), bar.height),
                             border_radius=6)
        elif state == "TINJAU":
            s = view["summary"]
            ok = s["detection_rate"] >= view["warn_threshold"]
            color = GREEN if ok else AMBER
            self._text(f"{s['n_frames']} frame  ·  deteksi {s['detection_rate'] * 100:.0f}%  ·  "
                       f"{s['effective_fps']:.1f} FPS", self.f_title, color, (24, bottom.top + 8))
            self._text("ENTER terima    R ulangi    S lewati", self.f_body, WHITE, (24, bottom.top + 48))
            if not ok:
                self._text("Deteksi rendah, pertimbangkan ulangi (R)", self.f_body, AMBER,
                           (sw - 24, bottom.top + 48), "topright")

        # --- konfirmasi keluar ------------------------------------------
        if view.get("quit_pending"):
            self._panel(pygame.Rect(0, 0, sw, sh), (0, 0, 0, 150))
            box = pygame.Rect(0, 0, 640, 170)
            box.center = (sw // 2, sh // 2)
            self._panel(box, (30, 30, 34, 245), radius=16)
            self._text("Keluar dari sesi?", self.f_big, WHITE, (box.centerx, box.top + 28), "midtop")
            self._text("Tekan Q / ESC lagi untuk keluar, tombol lain untuk batal.",
                       self.f_body, MUTED, (box.centerx, box.top + 104), "midtop")

        pygame.display.flip()
