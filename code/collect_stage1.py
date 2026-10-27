"""
collect_stage1.py
=================
Aplikasi akuisisi data Tahap 1: gestur tangan paretik untuk fine tuning GRU.

Protokol (proposal 3.3.2, Tabel 3.5 dan 3.6):
  4 gestur x 5 pengulangan x pose efektif 2 detik, kamera 30 FPS.
  Operator menekan SPASI saat gestur pasien sudah terbentuk; 2 detik direkam
  otomatis. Setelah itu operator menerima (ENTER), mengulang (R), atau
  melewati (S) percobaan tersebut.

Jalankan dari folder akar proyek:
    python code\\collect_stage1.py --participant P01 --sisi kanan

Tombol:
    SPASI   mulai rekam 2 detik (saat status SIAP)
    ENTER   terima percobaan (saat status TINJAU)
    R       ulangi percobaan (data percobaan lama tetap disimpan, ditandai ditolak)
    S       lewati percobaan (mis. pasien tidak mampu); dicatat sebagai skipped
    Q / ESC keluar (tekan dua kali untuk konfirmasi); data yang sudah ada tetap tersimpan

Data pasien disimpan di data/stage1/. Folder ini JANGAN di-commit ke git.
"""

import argparse
import os
import platform
import subprocess
import sys
import time

import cv2
import numpy as np

from gesture_pipeline import (CAMERA_CONFIG, MEDIAPIPE_CONFIG, create_hands,
                              extract_landmarks, open_camera)
from stage1_writer import Stage1SessionWriter, build_protocol, validate_participant

APP_VERSION = "collect_stage1 0.2"

INSTRUCTIONS = {  # Tabel 3.5 proposal
    "palm": "Buka telapak tangan, jari direntangkan sesuai kemampuan",
    "fist": "Tekuk seluruh jari hingga membentuk kepalan",
    "grabbing": "Lengkungkan jari-jari seperti mencengkeram",
    "thumb_index": "Rentangkan ibu jari dan telunjuk membentuk huruf L",
}

LOW_DETECTION_WARNING = 0.80   # peringatan saja; keputusan tetap di tangan operator
WINDOW_TITLE = "Akuisisi Tahap 1"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMAGES_DIR = os.path.join(PROJECT_ROOT, "graphics", "stage1")


def parse_args():
    p = argparse.ArgumentParser(description="Akuisisi data gestur Tahap 1")
    p.add_argument("--participant", required=True, help="Kode anonim, format P01-P99")
    p.add_argument("--sisi", required=True, choices=["kiri", "kanan"], help="Sisi tangan paretik yang direkam")
    p.add_argument("--status", default="paretik", choices=["paretik", "nonparetik"],
                   help="Tahap 1 sesuai proposal: paretik")
    p.add_argument("--camera", type=int, default=0, help="Indeks kamera (default 0)")
    p.add_argument("--reps", type=int, default=5, help="Pengulangan per gestur (default 5)")
    p.add_argument("--hold", type=float, default=2.0, help="Durasi rekam per percobaan, detik (default 2)")
    p.add_argument("--out", default=os.path.join("data", "stage1"), help="Folder keluaran")
    p.add_argument("--no-video", action="store_true", help="Jangan simpan video")
    p.add_argument("--no-mirror", action="store_true", help="Tampilan tidak dicerminkan")
    return p.parse_args()


def git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=3)
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=3)
        if out.returncode == 0:
            return out.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")
    except Exception:
        pass
    return None


def library_versions():
    import mediapipe as mp
    return {"python": platform.python_version(), "opencv": cv2.__version__,
            "mediapipe": getattr(mp, "__version__", "unknown"), "numpy": np.__version__}


def make_ui():
    from stage1_ui import Stage1UI
    return Stage1UI(WINDOW_TITLE, INSTRUCTIONS, IMAGES_DIR)


def main(ui_factory=make_ui):
    args = parse_args()
    try:
        validate_participant(args.participant)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return 2

    protocol = build_protocol(repetitions=args.reps, hold_seconds=args.hold)

    cap, cam_actual = open_camera(args.camera)
    if cap is None:
        print(f"[ERROR] Kamera indeks {args.camera} tidak bisa dibuka.")
        return 1
    if (cam_actual["width"], cam_actual["height"]) != (CAMERA_CONFIG["width"], CAMERA_CONFIG["height"]):
        print(f"[PERINGATAN] Kamera memberi {cam_actual['width']}x{cam_actual['height']}, "
              f"diminta {CAMERA_CONFIG['width']}x{CAMERA_CONFIG['height']}. Nilai aktual dicatat di session.json.")

    import mediapipe as mp
    hands = create_hands()
    drawer = mp.solutions.drawing_utils

    metadata = {
        "app_version": APP_VERSION,
        "git_commit": git_commit(),
        "libraries": library_versions(),
        "protocol": {
            "gestures_in_order": [g for g, _ in protocol[::args.reps]],
            "repetitions_per_gesture": args.reps,
            "hold_seconds": args.hold,
            "trigger": "operator_spacebar",
            "n_trials": len(protocol),
        },
        "camera_index": args.camera,
        "camera_requested": CAMERA_CONFIG,
        "camera_actual": cam_actual,
        "mediapipe_config": MEDIAPIPE_CONFIG,
        "landmarks_source": "frame asli tanpa flip (sama dengan baseline camera.py)",
        "display_mirrored": not args.no_mirror,
        "low_detection_warning": LOW_DETECTION_WARNING,
    }
    writer = Stage1SessionWriter(args.out, args.participant, args.status, args.sisi, metadata,
                                 save_video=not args.no_video)
    print(f"[INFO] Sesi {writer.session_id} -> {writer.session_dir}")

    ui = None
    t0 = time.perf_counter()
    trial_idx, state = 0, "SIAP"
    rec_start, video = None, None
    summary, quit_pending = None, False
    end_reason = "selesai"
    consecutive_read_failures = 0

    try:
        ui = ui_factory()
        while trial_idx < len(protocol):
            gesture, rep = protocol[trial_idx]
            ret, frame = cap.read()
            t_now = time.perf_counter() - t0
            if not ret:
                consecutive_read_failures += 1
                if consecutive_read_failures > 60:
                    print("[ERROR] Kamera berhenti memberi frame.")
                    end_reason = "kamera_gagal"
                    break
                if "quit" in ui.poll():
                    end_reason = "operator_keluar"
                    break
                continue
            consecutive_read_failures = 0

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)
            landmarks, hand_label, hand_score = extract_landmarks(result)

            remaining = args.hold
            if state == "REKAM":
                writer.add_frame(t_now - rec_start, t_now, (frame.shape[1], frame.shape[0]),
                                 landmarks, hand_label, hand_score)
                if video is not None:
                    video.write(frame)
                remaining = max(0.0, args.hold - (t_now - rec_start))
                if t_now - rec_start >= args.hold:
                    summary = writer.end_attempt(t_now)
                    if video is not None:
                        video.release()
                        video = None
                    state = "TINJAU"

            # --- tampilan -------------------------------------------------
            display = frame.copy()
            if result is not None and result.multi_hand_landmarks:
                drawer.draw_landmarks(display, result.multi_hand_landmarks[0], mp.solutions.hands.HAND_CONNECTIONS)
            if not args.no_mirror:
                display = cv2.flip(display, 1)
            ui.render(cv2.cvtColor(display, cv2.COLOR_BGR2RGB), {
                "state": state, "trial_idx": trial_idx, "n_trials": len(protocol),
                "gesture": gesture, "rep": rep, "reps": args.reps,
                "detected": landmarks is not None, "hold": args.hold, "remaining": remaining,
                "summary": summary, "quit_pending": quit_pending,
                "warn_threshold": LOW_DETECTION_WARNING,
            })

            # --- tombol ---------------------------------------------------
            stop = False
            for key in ui.poll():
                if quit_pending:
                    quit_pending = False
                    if key == "quit":
                        end_reason, stop = "operator_keluar", True
                        break
                    continue
                if key == "quit":
                    quit_pending = True
                elif state == "SIAP" and key == "space":
                    writer.start_attempt(gesture, rep, t_now)
                    path = writer.video_path()
                    if path:
                        fps = cam_actual["fps_reported"] or CAMERA_CONFIG["fps"]
                        video = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps,
                                                (frame.shape[1], frame.shape[0]))
                        if not video.isOpened():
                            print("[PERINGATAN] Video tidak bisa ditulis; landmark tetap disimpan.")
                            video = None
                    rec_start, state = t_now, "REKAM"
                    break
                elif state == "TINJAU" and key == "enter":
                    writer.decide(True, "accepted")
                    trial_idx, state, summary = trial_idx + 1, "SIAP", None
                    break
                elif state == "TINJAU" and key == "r":
                    writer.decide(False, "redo")
                    state, summary = "SIAP", None
                    break
                elif state == "TINJAU" and key == "s":
                    writer.decide(False, "skipped", note="dilewati operator")
                    trial_idx, state, summary = trial_idx + 1, "SIAP", None
                    break
            if stop:
                break
    except KeyboardInterrupt:
        end_reason = "keyboard_interrupt"
    finally:
        if video is not None:
            video.release()
        writer.close(end_reason)
        hands.close()
        cap.release()
        if ui is not None:
            ui.close()

    print(f"[INFO] Sesi ditutup ({end_reason}). Data: {writer.session_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
