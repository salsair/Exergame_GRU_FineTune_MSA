"""
collect_stage1.py
=================
Aplikasi akuisisi data Tahap 1: gestur tangan paretik untuk fine tuning GRU.

Alur:
  1. Formulir Lembar Pengumpul Data 1 (identitas tanpa nama/No. RM, kelayakan, consent).
  2. Cek privasi: pastikan wajah tidak masuk frame (tombol C).
  3. 4 gestur x 5 pengulangan x 2 detik. SPASI mulai rekam; kamera direkam di
     thread terpisah (~30 FPS), MediaPipe memproses frame setelah rekaman selesai.
  4. Tinjau tiap percobaan: ENTER bentuk penuh, P sebagian, R ulangi, S lewati, N catatan.
  5. Di akhir: lembar_tahap1.html terisi (cetak dari browser) + data mentah.

Jalankan dari folder akar proyek:
    python code\\collect_stage1.py                 (pasien: lewat formulir)
    python code\\collect_stage1.py --uji           (uji coba peneliti, kode P99, tanpa formulir)
    python code\\collect_stage1.py --cek-kamera    (ukur FPS kamera saja)

Data pasien disimpan di data/stage1/. Folder ini JANGAN di-commit ke git.
"""

import argparse
import os
import platform
import subprocess
import sys
import time
from datetime import date, datetime

import cv2
import numpy as np

from gesture_pipeline import (CAMERA_CONFIG, MEDIAPIPE_CONFIG, create_hands,
                              extract_landmarks, open_camera)
from stage1_writer import (Stage1SessionWriter, append_participant_registry,
                           build_protocol, existing_sessions)

APP_VERSION = "collect_stage1 0.3"

INSTRUCTIONS = {  # Tabel 3.5 proposal / Lembar 1
    "palm": "Buka telapak tangan, jari direntangkan sesuai kemampuan",
    "fist": "Tekuk seluruh jari hingga membentuk kepalan",
    "grabbing": "Lengkungkan jari-jari seperti mencengkeram",
    "thumb_index": "Rentangkan ibu jari dan telunjuk membentuk huruf L",
}

LOW_DETECTION_WARNING = 0.80   # peringatan saja; keputusan tetap di tangan operator
MAX_NOTE_LENGTH = 120
WINDOW_TITLE = "Akuisisi Tahap 1"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMAGES_DIR = os.path.join(PROJECT_ROOT, "graphics", "stage1")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Akuisisi data gestur Tahap 1")
    p.add_argument("--uji", action="store_true", help="Uji coba peneliti (kode P99) tanpa formulir")
    p.add_argument("--sisi", default="kanan", choices=["kiri", "kanan"], help="Sisi tangan untuk --uji")
    p.add_argument("--cek-kamera", action="store_true", help="Ukur FPS kamera selama 3 detik lalu keluar")
    p.add_argument("--camera", type=int, default=0, help="Indeks kamera untuk --uji / --cek-kamera")
    p.add_argument("--reps", type=int, default=5, help="Pengulangan per gestur (default 5)")
    p.add_argument("--hold", type=float, default=2.0, help="Durasi rekam per percobaan, detik (default 2)")
    p.add_argument("--out", default=os.path.join("data", "stage1"), help="Folder keluaran")
    p.add_argument("--no-mirror", action="store_true", help="Tampilan tidak dicerminkan")
    return p.parse_args(argv)


def git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=3)
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True, timeout=3)
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


def make_form(existing_fn):
    from stage1_form import ask_participant_info
    return ask_participant_info(existing_sessions_fn=existing_fn)


def make_reader(cap):
    from stage1_capture import CameraReader
    reader = CameraReader(cap)
    reader.start()
    return reader


def uji_info(args):
    today = date.today().isoformat()
    return {
        "participant": "P99", "tanggal": today, "usia": "", "jenis_kelamin": "", "tangan_dominan": "",
        "sisi_paretik": args.sisi, "kriteria": {}, "memenuhi_syarat": "uji_coba_peneliti",
        "consent": "", "consent_tanggal": "", "diperiksa_oleh": "", "simpan_video": True,
        "camera": args.camera,
    }


def process_recording(writer, recording, t0, hands, video_path):
    """
    Jalankan MediaPipe pada setiap frame rekaman (urut waktu), tulis frames.csv dan video.
    recording: (t_start, t_end, [(t, frame), ...]) dari CameraReader.
    """
    t_start, t_end, frames = recording
    video = None
    if video_path and frames:
        if len(frames) > 1:
            span = frames[-1][0] - frames[0][0]
            fps = (len(frames) - 1) / span if span > 0 else CAMERA_CONFIG["fps"]
        else:
            fps = CAMERA_CONFIG["fps"]
        h, w = frames[0][1].shape[:2]
        video = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        if not video.isOpened():
            print("[PERINGATAN] Video tidak bisa ditulis; landmark tetap disimpan.")
            video = None
    for t, frame in frames:
        result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        landmarks, label, score = extract_landmarks(result)
        writer.add_frame(t - t_start, t - t0, (frame.shape[1], frame.shape[0]), landmarks, label, score)
        if video is not None:
            video.write(frame)
    if video is not None:
        video.release()
    return writer.end_attempt(t_end - t0)


def check_camera(args):
    from stage1_capture import measure_camera_fps
    cap, actual = open_camera(args.camera)
    if cap is None:
        print(f"[ERROR] Kamera indeks {args.camera} tidak bisa dibuka.")
        return 1
    print(f"[INFO] Kamera {args.camera}: {actual}")
    fps = measure_camera_fps(cap, 3.0)
    cap.release()
    print(f"[INFO] Laju baca kamera tanpa MediaPipe: {fps:.1f} FPS (target {CAMERA_CONFIG['fps']})")
    if fps < 0.9 * CAMERA_CONFIG["fps"]:
        print("[PERINGATAN] Kamera di bawah target. Coba indeks kamera lain, pencahayaan lebih terang "
              "(webcam menurunkan FPS di ruangan gelap), atau port USB lain.")
    return 0


def main(argv=None, ui_factory=make_ui, form_fn=make_form, reader_factory=make_reader,
         hands_factory=create_hands):
    args = parse_args(argv)
    if args.cek_kamera:
        return check_camera(args)

    info = uji_info(args) if args.uji else form_fn(lambda code: existing_sessions(args.out, code))
    if info is None:
        print("[INFO] Formulir dibatalkan; tidak ada data yang disimpan.")
        return 0

    protocol = build_protocol(repetitions=args.reps, hold_seconds=args.hold)
    cap, cam_actual = open_camera(info["camera"])
    if cap is None:
        print(f"[ERROR] Kamera indeks {info['camera']} tidak bisa dibuka.")
        return 1
    if (cam_actual["width"], cam_actual["height"]) != (CAMERA_CONFIG["width"], CAMERA_CONFIG["height"]):
        print(f"[PERINGATAN] Kamera memberi {cam_actual['width']}x{cam_actual['height']}, "
              f"diminta {CAMERA_CONFIG['width']}x{CAMERA_CONFIG['height']}.")

    import mediapipe as mp
    drawer = mp.solutions.drawing_utils
    hand_connections = mp.solutions.hands.HAND_CONNECTIONS
    hands_live = hands_factory()

    participant_info = {k: v for k, v in info.items() if k not in ("camera", "simpan_video")}
    metadata = {
        "app_version": APP_VERSION,
        "git_commit": git_commit(),
        "libraries": library_versions(),
        "participant_info": participant_info,
        "protocol": {
            "gestures_in_order": [g for g, _ in protocol[::args.reps]],
            "repetitions_per_gesture": args.reps,
            "hold_seconds": args.hold,
            "trigger": "operator_spacebar",
            "n_trials": len(protocol),
            "capture": "thread kamera terpisah; MediaPipe dijalankan pada frame rekaman setelah 2 detik selesai",
        },
        "camera_index": info["camera"],
        "camera_requested": CAMERA_CONFIG,
        "camera_actual": cam_actual,
        "mediapipe_config": MEDIAPIPE_CONFIG,
        "landmarks_source": "frame asli tanpa flip (sama dengan baseline camera.py)",
        "display_mirrored": not args.no_mirror,
        "low_detection_warning": LOW_DETECTION_WARNING,
        "privacy_check": {"confirmed": False, "confirmed_at": None},
    }
    writer = Stage1SessionWriter(args.out, info["participant"], "paretik", info["sisi_paretik"], metadata,
                                 save_video=info["simpan_video"])
    if not args.uji:
        append_participant_registry(args.out, writer.session_id, participant_info)
    print(f"[INFO] Sesi {writer.session_id} -> {writer.session_dir}")

    ui, reader = None, None
    t0 = time.perf_counter()
    trial_idx, state = 0, "PRATINJAU"
    summary, note, note_editing, quit_pending = None, "", False, False
    last_seq, preview_rgb, detected = -1, None, False
    end_reason = "selesai"

    def view(**extra):
        gesture, rep = protocol[min(trial_idx, len(protocol) - 1)]
        v = {
            "state": state, "trial_idx": trial_idx, "n_trials": len(protocol), "gesture": gesture,
            "rep": rep, "reps": args.reps, "detected": detected, "hold": args.hold,
            "remaining": args.hold, "summary": summary, "quit_pending": quit_pending,
            "warn_threshold": LOW_DETECTION_WARNING, "participant": info["participant"],
            "side": info["sisi_paretik"], "video_name": os.path.basename(writer.video_path() or "") or None,
            "note": note, "note_editing": note_editing,
        }
        v.update(extra)
        return v

    def decide(accepted, decision, form=""):
        nonlocal trial_idx, state, summary, note
        writer.decide(accepted, decision, note=note, gesture_form=form)
        if decision in ("accepted", "skipped"):
            trial_idx += 1
        state, summary, note = "SIAP", None, ""

    try:
        ui = ui_factory()
        reader = reader_factory(cap)
        while trial_idx < len(protocol):
            if reader.read_failures > 60:
                print("[ERROR] Kamera berhenti memberi frame.")
                end_reason = "kamera_gagal"
                break

            # --- pratinjau langsung (laju sesuai kemampuan MediaPipe) ------
            latest = reader.latest()
            if latest is not None and latest[0] != last_seq:
                last_seq, _, frame = latest
                result = hands_live.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                detected = bool(result is not None and result.multi_hand_landmarks)
                display = frame.copy()
                if detected:
                    drawer.draw_landmarks(display, result.multi_hand_landmarks[0], hand_connections)
                if not args.no_mirror:
                    display = cv2.flip(display, 1)
                preview_rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
            elif latest is None:
                time.sleep(0.005)

            # --- rekaman selesai? -----------------------------------------
            extra = {}
            if state == "REKAM":
                extra["remaining"] = max(0.0, args.hold - reader.recording_progress())
                recording = reader.take_finished_recording()
                if recording is not None:
                    state = "PROSES"
                    ui.render(preview_rgb, view(n_processing=len(recording[2])))
                    hands_rec = hands_factory()
                    try:
                        summary = process_recording(writer, recording, t0, hands_rec, writer.video_path())
                    finally:
                        hands_rec.close()
                    state = "TINJAU"
            ui.render(preview_rgb, view(**extra))

            # --- tombol ---------------------------------------------------
            stop = False
            for key in ui.poll():
                if note_editing:
                    if key == "enter" or key == "cancel":
                        if key == "cancel":
                            note = note_backup
                        note_editing = False
                        ui.set_text_mode(False)
                    elif key == "backspace":
                        note = note[:-1]
                    elif key.startswith("char:") and len(note) < MAX_NOTE_LENGTH:
                        note += key[5:]
                    continue
                if quit_pending:
                    quit_pending = False
                    if key == "quit":
                        end_reason, stop = "operator_keluar", True
                        break
                    continue
                if key == "quit":
                    quit_pending = True
                elif state == "PRATINJAU" and key == "c":
                    writer.set_metadata(privacy_check={
                        "confirmed": True, "confirmed_at": datetime.now().isoformat(timespec="seconds")})
                    state = "SIAP"
                elif state == "SIAP" and key == "space":
                    gesture, rep = protocol[trial_idx]
                    t_rec = reader.start_recording(args.hold)
                    writer.start_attempt(gesture, rep, t_rec - t0)
                    state = "REKAM"
                    break
                elif state == "TINJAU" and key == "enter":
                    decide(True, "accepted", "penuh")
                    break
                elif state == "TINJAU" and key == "p":
                    decide(True, "accepted", "sebagian")
                    break
                elif state == "TINJAU" and key == "r":
                    decide(False, "redo")
                    break
                elif state == "TINJAU" and key == "s":
                    decide(False, "skipped")
                    break
                elif state == "TINJAU" and key == "n":
                    note_backup, note_editing = note, True
                    ui.set_text_mode(True)
                    break
            if stop:
                break
    except KeyboardInterrupt:
        end_reason = "keyboard_interrupt"
    finally:
        if reader is not None:
            reader.cancel_recording()
            reader.stop()
        writer.close(end_reason)
        hands_live.close()
        cap.release()
        report = None
        try:
            from stage1_report import write_report
            report = write_report(writer.session_dir)
        except Exception as e:  # laporan tidak boleh menggagalkan penyimpanan data
            print(f"[PERINGATAN] Lembar HTML gagal dibuat: {e}")
        if ui is not None:
            n_ok = trial_idx
            ui.show_message("Sesi selesai" if end_reason == "selesai" else "Sesi dihentikan",
                            [f"{info['participant']}: {n_ok} dari {len(protocol)} percobaan tercatat.",
                             "Lembar terisi: lembar_tahap1.html di folder sesi."])
            time.sleep(0 if argv is not None else 2.0)
            ui.close()

    print(f"[INFO] Sesi ditutup ({end_reason}). Data: {writer.session_dir}")
    if report:
        print(f"[INFO] Lembar terisi: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
