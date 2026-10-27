"""
stage1_writer.py
================
Penyimpanan data akuisisi Tahap 1 (gestur tangan paretik).

Struktur keluaran per sesi:
    data/stage1/<kode_partisipan>/<session_id>/
        session.json   metadata sesi (protokol, kamera, MediaPipe, versi kode)
        frames.csv     satu baris per frame yang direkam selama jendela trial
        trials.csv     satu baris per percobaan (attempt), termasuk yang ditolak
        videos/        satu video per percobaan (jika video diaktifkan)

Prinsip:
  - Semua frame mentah ~30 FPS disimpan. Sampling 5 FPS, pemeriksaan kualitas,
    dan pembentukan 76 fitur dilakukan oleh skrip ekspor, bukan di sini.
  - Percobaan yang diulang (redo) TIDAK dihapus; ditandai accepted=False.
  - File ditulis dan di-flush setiap frame/trial agar data aman bila program
    berhenti mendadak.
  - Tidak ada nama, nomor rekam medis, atau identitas lain selain kode partisipan.
"""

import csv
import json
import os
import re
from datetime import datetime

from gesture_pipeline import GESTURE_LABELS, LABEL_TO_INDEX, NUM_LANDMARKS

SCHEMA_VERSION = "stage1-v1"
PARTICIPANT_PATTERN = re.compile(r"^P\d{2}$")
HAND_STATUS_VALUES = ("paretik", "nonparetik")
HAND_SIDE_VALUES = ("kiri", "kanan")

LANDMARK_COLUMNS = [f"lm{i}_{axis}" for i in range(NUM_LANDMARKS) for axis in ("x", "y", "z")]

FRAME_COLUMNS = [
    "session_id", "participant", "hand_status", "hand_side",
    "trial_id", "attempt_id", "gesture", "gesture_index", "repetition", "attempt",
    "frame_in_trial", "t_trial_s", "t_session_s", "t_wall",
    "image_width", "image_height",
    "detected", "handedness_label", "handedness_score",
] + LANDMARK_COLUMNS

TRIAL_COLUMNS = [
    "session_id", "participant", "hand_status", "hand_side",
    "trial_id", "attempt_id", "gesture", "gesture_index", "repetition", "attempt",
    "t_start_session_s", "t_end_session_s", "duration_s",
    "n_frames", "n_detected", "detection_rate", "effective_fps",
    "accepted", "decision", "video_file", "note",
]


def validate_participant(code):
    if not PARTICIPANT_PATTERN.match(code or ""):
        raise ValueError(
            f"Kode partisipan '{code}' tidak valid. Gunakan format P01-P99. "
            "Jangan memakai nama atau nomor rekam medis."
        )
    return code


def build_protocol(repetitions=5, hold_seconds=2.0, order=None):
    """
    Daftar trial berurutan: [(gesture, repetition), ...].
    Default: urutan Tabel 3.5 proposal (palm, fist, grabbing, thumb_index),
    lima pengulangan per gestur, berurutan per gestur.
    """
    order = list(order or ("palm", "fist", "grabbing", "thumb_index"))
    for g in order:
        if g not in LABEL_TO_INDEX:
            raise ValueError(f"Gestur tidak dikenal: {g}")
    return [(g, r) for g in order for r in range(1, repetitions + 1)]


class Stage1SessionWriter:
    def __init__(self, root_dir, participant, hand_status, hand_side, metadata,
                 save_video=True, now=None):
        self.participant = validate_participant(participant)
        if hand_status not in HAND_STATUS_VALUES:
            raise ValueError(f"hand_status harus salah satu dari {HAND_STATUS_VALUES}")
        if hand_side not in HAND_SIDE_VALUES:
            raise ValueError(f"hand_side harus salah satu dari {HAND_SIDE_VALUES}")
        self.hand_status = hand_status
        self.hand_side = hand_side
        self.save_video = save_video

        now = now or datetime.now()
        self.session_id = f"{participant}_S1_{now.strftime('%Y%m%d_%H%M%S')}"
        self.session_dir = os.path.join(root_dir, participant, self.session_id)
        if os.path.exists(self.session_dir):
            raise FileExistsError(f"Folder sesi sudah ada: {self.session_dir}")
        os.makedirs(self.session_dir)
        self.video_dir = os.path.join(self.session_dir, "videos")
        if save_video:
            os.makedirs(self.video_dir)

        self.metadata = dict(metadata)
        self.metadata.update({
            "schema_version": SCHEMA_VERSION,
            "session_id": self.session_id,
            "participant": participant,
            "stage": 1,
            "hand_status": hand_status,
            "hand_side": hand_side,
            "gesture_labels": list(GESTURE_LABELS),
            "save_video": save_video,
            "started_at": now.isoformat(timespec="seconds"),
            "ended_at": None,
            "end_reason": None,
        })
        self._write_metadata()

        self._frames_f = open(os.path.join(self.session_dir, "frames.csv"), "w", newline="", encoding="utf-8")
        self._frames = csv.DictWriter(self._frames_f, fieldnames=FRAME_COLUMNS)
        self._frames.writeheader()
        self._trials_f = open(os.path.join(self.session_dir, "trials.csv"), "w", newline="", encoding="utf-8")
        self._trials = csv.DictWriter(self._trials_f, fieldnames=TRIAL_COLUMNS)
        self._trials.writeheader()

        self._attempt_counter = {}
        self._current = None
        self.closed = False

    # ------------------------------------------------------------------
    def _write_metadata(self):
        path = os.path.join(self.session_dir, "session.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    def _base(self):
        return {
            "session_id": self.session_id,
            "participant": self.participant,
            "hand_status": self.hand_status,
            "hand_side": self.hand_side,
        }

    # ------------------------------------------------------------------
    def start_attempt(self, gesture, repetition, t_session_s):
        if self._current is not None:
            raise RuntimeError("Masih ada percobaan yang belum ditutup")
        key = (gesture, repetition)
        attempt = self._attempt_counter.get(key, 0) + 1
        self._attempt_counter[key] = attempt
        trial_id = f"{gesture}_r{repetition}"
        attempt_id = f"{trial_id}_a{attempt}"
        video_file = os.path.join("videos", f"{attempt_id}.mp4") if self.save_video else ""
        self._current = {
            **self._base(),
            "trial_id": trial_id,
            "attempt_id": attempt_id,
            "gesture": gesture,
            "gesture_index": LABEL_TO_INDEX[gesture],
            "repetition": repetition,
            "attempt": attempt,
            "t_start_session_s": t_session_s,
            "n_frames": 0,
            "n_detected": 0,
            "video_file": video_file,
        }
        return self._current

    def video_path(self):
        if not self._current or not self.save_video:
            return None
        return os.path.join(self.session_dir, self._current["video_file"])

    def add_frame(self, t_trial_s, t_session_s, image_size, landmarks, handedness_label, handedness_score):
        cur = self._current
        if cur is None:
            raise RuntimeError("add_frame dipanggil di luar percobaan")
        row = {k: cur[k] for k in ("session_id", "participant", "hand_status", "hand_side", "trial_id",
                                   "attempt_id", "gesture", "gesture_index", "repetition", "attempt")}
        row.update({
            "frame_in_trial": cur["n_frames"],
            "t_trial_s": f"{t_trial_s:.6f}",
            "t_session_s": f"{t_session_s:.6f}",
            "t_wall": datetime.now().isoformat(timespec="milliseconds"),
            "image_width": image_size[0],
            "image_height": image_size[1],
            "detected": int(landmarks is not None),
            "handedness_label": handedness_label or "",
            "handedness_score": "" if handedness_score is None else f"{handedness_score:.4f}",
        })
        if landmarks is not None:
            flat = [float(v) for v in landmarks.reshape(-1)]
            row.update({col: f"{v:.7f}" for col, v in zip(LANDMARK_COLUMNS, flat)})
            cur["n_detected"] += 1
        else:
            row.update({col: "" for col in LANDMARK_COLUMNS})
        self._frames.writerow(row)
        cur["n_frames"] += 1

    def end_attempt(self, t_session_s):
        """Tutup jendela rekam; keputusan diterima/ditolak menyusul via decide()."""
        cur = self._current
        if cur is None:
            raise RuntimeError("Tidak ada percobaan aktif")
        cur["t_end_session_s"] = t_session_s
        cur["duration_s"] = t_session_s - cur["t_start_session_s"]
        self._frames_f.flush()
        return self.summary()

    def summary(self):
        cur = self._current
        n, d = cur["n_frames"], cur["n_detected"]
        dur = cur.get("duration_s") or 0.0
        return {
            "attempt_id": cur["attempt_id"],
            "n_frames": n,
            "n_detected": d,
            "detection_rate": (d / n) if n else 0.0,
            "effective_fps": (n / dur) if dur > 0 else 0.0,
            "duration_s": dur,
        }

    def decide(self, accepted, decision, note=""):
        """decision: 'accepted' | 'redo' | 'skipped' | 'aborted'."""
        cur = self._current
        if cur is None or "t_end_session_s" not in cur:
            raise RuntimeError("decide dipanggil sebelum end_attempt")
        s = self.summary()
        row = {k: cur.get(k, "") for k in TRIAL_COLUMNS}
        row.update({
            "t_start_session_s": f"{cur['t_start_session_s']:.6f}",
            "t_end_session_s": f"{cur['t_end_session_s']:.6f}",
            "duration_s": f"{s['duration_s']:.6f}",
            "detection_rate": f"{s['detection_rate']:.4f}",
            "effective_fps": f"{s['effective_fps']:.2f}",
            "accepted": int(bool(accepted)),
            "decision": decision,
            "note": note,
        })
        self._trials.writerow(row)
        self._trials_f.flush()
        self._current = None
        return row

    def close(self, end_reason):
        if self.closed:
            return
        if self._current is not None:
            if "t_end_session_s" not in self._current:
                self._current["t_end_session_s"] = self._current["t_start_session_s"]
                self._current["duration_s"] = 0.0
            self.decide(False, "aborted", note=f"sesi ditutup: {end_reason}")
        self._frames_f.close()
        self._trials_f.close()
        self.metadata["ended_at"] = datetime.now().isoformat(timespec="seconds")
        self.metadata["end_reason"] = end_reason
        self._write_metadata()
        self.closed = True
