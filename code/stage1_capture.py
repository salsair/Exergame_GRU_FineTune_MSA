"""
stage1_capture.py
=================
Pembacaan kamera di thread terpisah agar perekaman mengikuti laju kamera
(~30 FPS), tidak tertahan oleh MediaPipe dan tampilan di thread utama.

- Thread membaca kamera terus-menerus dan menyimpan frame terbaru (untuk pratinjau).
- Saat merekam, SETIAP frame dari kamera disimpan bersama timestamp saat dibaca.
- Rekaman berhenti otomatis setelah `hold` detik berdasarkan timestamp frame.
- MediaPipe dijalankan pada frame rekaman SETELAH rekaman selesai (lihat
  collect_stage1.process_recording), sehingga laju rekaman tidak terganggu.
"""

import threading
import time


class CameraReader:
    def __init__(self, cap, clock=time.perf_counter):
        self.cap = cap
        self.clock = clock
        self._lock = threading.Lock()
        self._latest = None            # (t, frame)
        self._seq = 0
        self._recording = False
        self._rec_frames = []          # [(t, frame), ...]
        self._rec_start = None
        self._rec_hold = None
        self._rec_done = None
        self._running = False
        self._thread = None
        self.read_failures = 0

    # ------------------------------------------------------------------
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _loop(self):
        while self._running:
            ret, frame = self.cap.read()
            t = self.clock()
            if not ret:
                self.read_failures += 1
                time.sleep(0.01)
                continue
            self.read_failures = 0
            self._push(t, frame)

    def _push(self, t, frame):
        with self._lock:
            self._latest = (t, frame)
            self._seq += 1
            if self._recording:
                if t - self._rec_start < self._rec_hold:
                    self._rec_frames.append((t, frame))
                else:
                    self._recording = False
                    self._rec_done = (self._rec_start, t, self._rec_frames)
                    self._rec_frames = []

    # ------------------------------------------------------------------
    def latest(self):
        """(seq, t, frame) frame terbaru, atau None bila belum ada."""
        with self._lock:
            if self._latest is None:
                return None
            t, frame = self._latest
            return self._seq, t, frame

    def start_recording(self, hold_seconds):
        with self._lock:
            self._rec_frames = []
            self._rec_done = None
            self._rec_hold = hold_seconds
            self._rec_start = self.clock()
            self._recording = True
            return self._rec_start

    def recording_progress(self):
        """Detik yang sudah terekam (0 bila tidak merekam)."""
        with self._lock:
            if not self._recording:
                return 0.0
            return max(0.0, self.clock() - self._rec_start)

    def take_finished_recording(self):
        """(t_start, t_end, frames) bila rekaman sudah selesai, selain itu None."""
        with self._lock:
            done, self._rec_done = self._rec_done, None
            return done

    def cancel_recording(self):
        with self._lock:
            self._recording = False
            self._rec_frames = []
            self._rec_done = None


def measure_camera_fps(cap, seconds=3.0, clock=time.perf_counter):
    """Laju baca kamera murni (tanpa MediaPipe), untuk mode --cek-kamera."""
    n, t0 = 0, clock()
    while clock() - t0 < seconds:
        ret, _ = cap.read()
        if ret:
            n += 1
    dt = clock() - t0
    return n / dt if dt > 0 else 0.0
