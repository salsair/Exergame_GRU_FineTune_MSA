"""
Uji Stage1SessionWriter dengan data sintetis (tanpa kamera, tanpa data pasien).
"""
import csv
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
from stage1_writer import (FRAME_COLUMNS, Stage1SessionWriter,  # noqa: E402
                           build_protocol, validate_participant)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestWriter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def make(self, **kw):
        return Stage1SessionWriter(self.tmp, "P01", "paretik", "kanan", {"note": "uji"},
                                   save_video=kw.get("save_video", False),
                                   now=kw.get("now", datetime(2026, 11, 2, 9, 0, 0)))

    def record(self, w, gesture, rep, t0, n=60, fps=30.0, miss_every=0):
        w.start_attempt(gesture, rep, t0)
        rng = np.random.default_rng(rep)
        for i in range(n):
            lm = None if (miss_every and i % miss_every == 0) else rng.uniform(0, 1, (21, 3))
            w.add_frame(i / fps, t0 + i / fps, (1280, 720), lm,
                        None if lm is None else "Right", None if lm is None else 0.98)
        return w.end_attempt(t0 + n / fps)

    def test_protocol_default(self):
        p = build_protocol()
        self.assertEqual(len(p), 20)
        self.assertEqual(p[0], ("palm", 1))
        self.assertEqual(p[5], ("fist", 1))
        self.assertEqual([g for g, _ in p[::5]], ["palm", "fist", "grabbing", "thumb_index"])

    def test_participant_validation(self):
        for bad in ("Budi", "p01", "P1", "P001", "", None):
            with self.assertRaises(ValueError):
                validate_participant(bad)
        self.assertEqual(validate_participant("P15"), "P15")

    def test_full_session_with_redo_and_skip(self):
        w = self.make()
        s = self.record(w, "palm", 1, 1.0, miss_every=5)       # 20% frame tanpa deteksi
        self.assertAlmostEqual(s["detection_rate"], 0.8)
        self.assertAlmostEqual(s["effective_fps"], 30.0)
        w.decide(False, "redo")
        self.record(w, "palm", 1, 5.0)
        w.decide(True, "accepted", gesture_form="penuh")
        self.record(w, "fist", 1, 9.0, n=10)
        w.decide(False, "skipped", note="tidak mampu")
        w.close("selesai")

        trials = read_csv(os.path.join(w.session_dir, "trials.csv"))
        self.assertEqual([t["attempt_id"] for t in trials], ["palm_r1_a1", "palm_r1_a2", "fist_r1_a1"])
        self.assertEqual([t["accepted"] for t in trials], ["0", "1", "0"])
        self.assertEqual([t["decision"] for t in trials], ["redo", "accepted", "skipped"])
        self.assertEqual([t["gesture_formed"] for t in trials], ["", "ya", "tidak"])
        self.assertEqual([t["gesture_form"] for t in trials], ["", "penuh", ""])

        frames = read_csv(os.path.join(w.session_dir, "frames.csv"))
        self.assertEqual(len(frames), 60 + 60 + 10)
        self.assertEqual(list(frames[0].keys()), FRAME_COLUMNS)
        self.assertEqual(frames[0]["detected"], "0")              # frame 0 = tanpa deteksi
        self.assertEqual(frames[0]["lm0_x"], "")
        self.assertEqual(frames[1]["detected"], "1")
        self.assertNotEqual(frames[1]["lm20_z"], "")
        self.assertEqual(frames[1]["gesture_index"], "0")
        self.assertEqual({f["participant"] for f in frames}, {"P01"})

        with open(os.path.join(w.session_dir, "session.json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta["end_reason"], "selesai")
        self.assertEqual(meta["gesture_labels"], ["palm", "fist", "thumb_index", "grabbing"])
        self.assertEqual(meta["hand_side"], "kanan")
        self.assertIsNotNone(meta["ended_at"])

    def test_close_mid_attempt_marks_aborted(self):
        w = self.make()
        w.start_attempt("grabbing", 2, 3.0)
        w.add_frame(0.0, 3.0, (1280, 720), np.zeros((21, 3)), "Left", 0.9)
        w.close("operator_keluar")
        trials = read_csv(os.path.join(w.session_dir, "trials.csv"))
        self.assertEqual(len(trials), 1)
        self.assertEqual(trials[0]["decision"], "aborted")
        self.assertEqual(trials[0]["accepted"], "0")
        self.assertEqual(len(read_csv(os.path.join(w.session_dir, "frames.csv"))), 1)

    def test_landmark_roundtrip_precision(self):
        w = self.make()
        w.start_attempt("palm", 1, 0.0)
        lm = np.random.default_rng(7).uniform(0, 1, (21, 3))
        w.add_frame(0.0, 0.0, (1280, 720), lm, "Right", 0.99)
        w.end_attempt(0.1); w.decide(True, "accepted", gesture_form="penuh"); w.close("selesai")
        row = read_csv(os.path.join(w.session_dir, "frames.csv"))[0]
        back = np.array([float(row[f"lm{i}_{a}"]) for i in range(21) for a in "xyz"]).reshape(21, 3)
        self.assertLess(np.abs(back - lm).max(), 1e-7)

    def test_accept_requires_gesture_form(self):
        w = self.make()
        self.record(w, "palm", 1, 0.0, n=5)
        with self.assertRaises(ValueError):
            w.decide(True, "accepted")
        with self.assertRaises(ValueError):
            w.decide(False, "tidak_dikenal")
        w.decide(True, "accepted", gesture_form="sebagian")
        w.close("selesai")

    def test_participant_registry_appends(self):
        from stage1_writer import append_participant_registry, existing_sessions
        info = {"participant": "P01", "usia": "60", "sisi_paretik": "kiri", "nama": "JANGAN DISIMPAN"}
        path = append_participant_registry(self.tmp, "P01_S1_a", info)
        append_participant_registry(self.tmp, "P01_S1_b", info)
        rows = read_csv(path)
        self.assertEqual([r["session_id"] for r in rows], ["P01_S1_a", "P01_S1_b"])
        self.assertNotIn("nama", rows[0])
        w = self.make()
        self.assertEqual(existing_sessions(self.tmp, "P01"), [w.session_id])
        self.assertEqual(existing_sessions(self.tmp, "P02"), [])
        w.close("selesai")

    def test_set_metadata_persists(self):
        w = self.make()
        w.set_metadata(privacy_check={"confirmed": True})
        with open(os.path.join(w.session_dir, "session.json"), encoding="utf-8") as f:
            self.assertTrue(json.load(f)["privacy_check"]["confirmed"])
        w.close("selesai")

    def test_refuses_to_overwrite_session(self):
        w = self.make()
        with self.assertRaises(FileExistsError):
            self.make()
        w.close("selesai")

    def test_video_folder_only_when_enabled(self):
        w = self.make(save_video=True)
        w.start_attempt("palm", 1, 0.0)
        self.assertTrue(w.video_path().endswith(os.path.join("videos", "palm_r1_a1.mp4")))
        self.assertTrue(os.path.isdir(os.path.join(w.session_dir, "videos")))
        w.close("selesai")


if __name__ == "__main__":
    unittest.main()
