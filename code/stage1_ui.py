"""
stage1_ui.py
============
Tampilan aplikasi akuisisi Tahap 1 berbasis Pygame (teks anti-alias, rasio
gambar kamera terjaga, kartu contoh gestur di kanan atas).

Status layar:
  SIAP       tunggu SPASI
  REKAM      merekam 2 detik
  PROSES     MediaPipe memproses frame rekaman
  TINJAU     ENTER penuh / P sebagian / R ulang / S lewati / N catatan

Modul ini hanya menggambar dan membaca tombol. Logika ada di collect_stage1.py.
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
BLUE = (88, 166, 255)

KEY_MAP = {
    pygame.K_SPACE: "space",
    pygame.K_RETURN: "enter",
    pygame.K_KP_ENTER: "enter",
    pygame.K_p: "p",
    pygame.K_r: "r",
    pygame.K_s: "s",
    pygame.K_n: "n",
    pygame.K_c: "c",
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
        self.text_mode = False
        self.images = {}
        for g in instructions:
            path = os.path.join(images_dir, f"{g}.png")
            if os.path.exists(path):
                img = pygame.image.load(path).convert()
                self.images[g] = pygame.transform.smoothscale(img, (self.card_size, self.card_size))
            else:
                print(f"[PERINGATAN] Gambar contoh tidak ditemukan: {path}")

    # ------------------------------------------------------------------
    def set_text_mode(self, on):
        self.text_mode = on
        if on:
            pygame.key.start_text_input()
        else:
            pygame.key.stop_text_input()

    def poll(self):
        """
        Tombol logis sejak panggilan sebelumnya. Dalam mode teks: 'char:<c>',
        'backspace', 'enter', 'cancel'.
        """
        keys = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                keys.append("quit")
            elif self.text_mode and event.type == pygame.TEXTINPUT:
                keys.extend(f"char:{c}" for c in event.text)
            elif event.type == pygame.KEYDOWN:
                if self.text_mode:
                    if event.key == pygame.K_BACKSPACE:
                        keys.append("backspace")
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        keys.append("enter")
                    elif event.key == pygame.K_ESCAPE:
                        keys.append("cancel")
                else:
                    keys.append(KEY_MAP.get(event.key, "other"))
        return keys

    def close(self):
        pygame.quit()

    # ------------------------------------------------------------------
    def _panel(self, rect, color=PANEL, radius=0):
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, color, surf.get_rect(), border_radius=radius)
        self.screen.blit(surf, rect.topleft)

    def _text(self, text, font, color, pos, anchor="topleft"):
        surf = font.render(text, True, color)
        rect = surf.get_rect(**{anchor: pos})
        self.screen.blit(surf, rect)
        return rect

    def _camera(self, frame_rgb):
        self.screen.fill(BG)
        if frame_rgb is None:
            return
        h, w = frame_rgb.shape[:2]
        surf = pygame.image.frombuffer(frame_rgb.tobytes(), (w, h), "RGB")
        sw, sh = self.size
        scale = min(sw / w, sh / h)
        tw, th = int(w * scale), int(h * scale)
        if (tw, th) != (w, h):
            surf = pygame.transform.smoothscale(surf, (tw, th))
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
        pygame.draw.rect(self.screen, WHITE, img_rect, 2, border_radius=6)

    def _dialog(self, title, lines, color=WHITE, dim=True):
        sw, sh = self.size
        if dim:
            self._panel(pygame.Rect(0, 0, sw, sh), (0, 0, 0, 150))
        box = pygame.Rect(0, 0, 760, 120 + 36 * len(lines))
        box.center = (sw // 2, sh // 2)
        self._panel(box, (30, 30, 34, 245), radius=16)
        self._text(title, self.f_big, color, (box.centerx, box.top + 24), "midtop")
        for i, line in enumerate(lines):
            self._text(line, self.f_body, MUTED, (box.centerx, box.top + 96 + 36 * i), "midtop")

    # ------------------------------------------------------------------
    def render(self, frame_rgb, view):
        """
        view: state, trial_idx, n_trials, gesture, rep, reps, detected, hold, remaining,
              summary, quit_pending, warn_threshold, participant, side, video_name,
              note, note_editing, n_processing
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
                   (sw - 24, 14), "topright")
        self._text(f"{view['participant']} · paretik {view['side']}", self.f_small, BLUE,
                   (sw - 24, 52), "topright")
        frac = view["trial_idx"] / max(1, view["n_trials"])
        pygame.draw.rect(self.screen, (70, 70, 70), (0, 92, sw, 4))
        pygame.draw.rect(self.screen, GREEN, (0, 92, int(sw * frac), 4))

        self._card(gesture, top=112)

        det = view["detected"]
        pill = pygame.Rect(24, sh - 140, 250, 40)
        self._panel(pill, (0, 0, 0, 175), radius=20)
        pygame.draw.circle(self.screen, GREEN if det else RED, (pill.left + 22, pill.centery), 9)
        self._text("Tangan terdeteksi" if det else "Tangan tidak terdeteksi",
                   self.f_small, WHITE, (pill.left + 42, pill.centery), "midleft")

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
        elif state == "PROSES":
            self._text(f"Memproses {view.get('n_processing', 0)} frame...", self.f_title, AMBER,
                       (24, bottom.centery), "midleft")
        elif state == "TINJAU":
            s = view["summary"]
            ok = s["detection_rate"] >= view["warn_threshold"]
            color = GREEN if ok else AMBER
            self._text(f"{s['n_frames']} frame  ·  deteksi {s['detection_rate'] * 100:.0f}%  ·  "
                       f"{s['effective_fps']:.1f} FPS", self.f_title, color, (24, bottom.top + 8))
            self._text("ENTER bentuk penuh   P sebagian   R ulangi   S lewati (tidak terbentuk)   N catatan",
                       self.f_small, WHITE, (24, bottom.top + 52))
            info = pygame.Rect(24, sh - 196, 760, 48)
            self._panel(info, (0, 0, 0, 175), radius=10)
            self._text(f"Video: {view.get('video_name') or '(tidak disimpan)'}", self.f_small, MUTED,
                       (info.left + 14, info.top + 4))
            note = view.get("note") or ""
            self._text(f"Catatan: {note}" + ("_" if view.get("note_editing") else ""),
                       self.f_small, AMBER if view.get("note_editing") else MUTED, (info.left + 14, info.top + 24))
            if not ok:
                self._text("Deteksi rendah, pertimbangkan ulangi (R)", self.f_body, AMBER,
                           (sw - 24, sh - 172), "midright")
            if view.get("note_editing"):
                self._text("Ketik catatan, ENTER simpan, ESC batal", self.f_small, AMBER,
                           (info.right + 16, info.centery), "midleft")

        self._quit_overlay(view)
        pygame.display.flip()

    def _quit_overlay(self, view):
        if view.get("quit_pending"):
            self._dialog("Keluar dari sesi?", ["Tekan Q / ESC lagi untuk keluar, tombol lain untuk batal.",
                                               "Data yang sudah direkam tetap tersimpan."])

    def show_message(self, title, lines, color=WHITE):
        self.screen.fill(BG)
        self._dialog(title, lines, color, dim=False)
        pygame.display.flip()
