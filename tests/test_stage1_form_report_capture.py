"""
Uji logika formulir (tanpa tkinter), pembuat lembar HTML, dan CameraReader.
"""
import os
import sys
import threading
import unittest
from datetime import date

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
from stage1_capture import CameraReader  # noqa: E402
from stage1_form import (EXCLUSION_CRITERIA, INCLUSION_CRITERIA,  # noqa: E402
                         evaluate_eligibility, validate_form)
from stage1_report import final_trials, render  # noqa: E402

TODAY = date(2026, 11, 3)


def valid_values(**over):
    v = {"participant": "p04", "tanggal": "2026-11-03", "usia": "61", "jenis_kelamin": "perempuan",
         "tangan_dominan": "kanan", "sisi_paretik": "kiri", "consent": "ya",
         "consent_tanggal": "2026-11-02", "diperiksa_oleh": "dr. A", "camera": "0", "simpan_video": True}
    v.update({k: "ya" for k, _ in INCLUSION_CRITERIA})
    v.update({k: "tidak" for k, _ in EXCLUSION_CRITERIA})
    v.update(over)
    return v


class TestForm(unittest.TestCase):
    def test_valid_form(self):
        info, errors = validate_form(valid_values(), today=TODAY)
        self.assertEqual(errors, [])
        self.assertEqual(info["participant"], "P04")            # dinormalisasi ke huruf besar
        self.assertEqual(info["memenuhi_syarat"], "memenuhi")
        self.assertEqual(info["sisi_paretik"], "kiri")
        self.assertNotIn("nama", info)
        self.assertNotIn("no_rm", info)

    def test_name_rejected_as_code(self):
        _, errors = validate_form(valid_values(participant="Budi"), today=TODAY)
        self.assertTrue(any("P01-P99" in e for e in errors))

    def test_exclusion_yes_blocks(self):
        _, errors = validate_form(valid_values(eksklusi_medis="ya"), today=TODAY)
        self.assertTrue(any("tidak memenuhi syarat" in e for e in errors))

    def test_inclusion_no_blocks(self):
        status, reason = evaluate_eligibility({**{k: "ya" for k, _ in INCLUSION_CRITERIA},
                                               "inklusi_mmt": "tidak",
                                               **{k: "tidak" for k, _ in EXCLUSION_CRITERIA}})
        self.assertEqual(status, "tidak_memenuhi")
        self.assertIn("MMT", reason)

    def test_incomplete_criteria(self):
        _, errors = validate_form(valid_values(inklusi_mas=""), today=TODAY)
        self.assertTrue(any("belum dijawab" in e for e in errors))

    def test_consent_required_and_dated(self):
        _, errors = validate_form(valid_values(consent="tidak"), today=TODAY)
        self.assertTrue(any("consent" in e for e in errors))
        _, errors = validate_form(valid_values(consent_tanggal="2026-11-05"), today=TODAY)
        self.assertTrue(any("setelah tanggal pengambilan" in e for e in errors))

    def test_radio_fields_required(self):
        for field in ("jenis_kelamin", "tangan_dominan", "sisi_paretik"):
            _, errors = validate_form(valid_values(**{field: ""}), today=TODAY)
            self.assertTrue(errors, field)

    def test_future_date_and_bad_age(self):
        _, errors = validate_form(valid_values(tanggal="2026-12-01"), today=TODAY)
        self.assertTrue(any("masa depan" in e for e in errors))
        _, errors = validate_form(valid_values(usia="enam puluh"), today=TODAY)
        self.assertTrue(any("Usia" in e for e in errors))

    def test_no_age_criterion_invented(self):
        _, errors = validate_form(valid_values(usia="17"), today=TODAY)
        self.assertEqual(errors, [])


class TestReport(unittest.TestCase):
    def trial(self, tid, decision, form="", note="", video=""):
        g, r = tid.rsplit("_r", 1)
        return {"trial_id": tid, "decision": decision, "gesture_formed": {"accepted": "ya", "skipped": "tidak"}.get(decision, ""),
                "gesture_form": form, "note": note, "video_file": video,
                "detection_rate": "0.95", "effective_fps": "29.8"}

    def test_final_trials_and_render(self):
        protocol = [(g, r) for g in ("palm", "fist", "grabbing", "thumb_index") for r in range(1, 6)]
        trials = [self.trial("palm_r1", "redo", video="videos\\palm_r1_a1.mp4"),
                  self.trial("palm_r1", "accepted", "penuh", video="videos\\palm_r1_a2.mp4"),
                  self.trial("palm_r2", "accepted", "sebagian", note="jari <manis> kaku"),
                  self.trial("palm_r3", "skipped", note="lelah")]
        rows = final_trials(trials, protocol)
        self.assertEqual(len(rows), 20)
        self.assertEqual(rows[0]["final"]["gesture_form"], "penuh")
        self.assertEqual(rows[0]["n_redo"], 1)
        self.assertEqual(rows[2]["final"]["decision"], "skipped")
        self.assertIsNone(rows[3]["final"])

        meta = {"session_id": "P04_S1_x", "participant": "P04", "git_commit": "abc1234",
                "participant_info": {"participant": "P04", "sisi_paretik": "kiri", "consent": "ya",
                                     "memenuhi_syarat": "memenuhi", "kriteria": {"inklusi_mmt": "ya"}},
                "protocol": {"gestures_in_order": ["palm", "fist", "grabbing", "thumb_index"],
                             "repetitions_per_gesture": 5},
                "privacy_check": {"confirmed": True, "confirmed_at": "2026-11-03T09:00:00"},
                "end_reason": "operator_keluar"}
        out = render(meta, trials)
        self.assertIn("palm_r1_a2.mp4", out)
        self.assertIn("jari &lt;manis&gt; kaku", out)           # teks catatan di-escape
        self.assertIn("belum direkam", out)
        self.assertIn("Diterima 2 dari 20", out)
        self.assertIn("No. rekam medis", out)                     # baris kosong untuk ditulis tangan


class FakeCap:
    def __init__(self, n_frames):
        self.n, self.i = n_frames, 0

    def read(self):
        if self.i >= self.n:
            return False, None
        self.i += 1
        return True, np.full((2, 2, 3), self.i, dtype=np.uint8)


class TestCameraReader(unittest.TestCase):
    def test_recording_window_by_timestamp(self):
        t = {"now": 0.0}
        reader = CameraReader(FakeCap(0), clock=lambda: t["now"])
        start = reader.start_recording(2.0)
        self.assertEqual(start, 0.0)
        for i in range(1, 70):                       # 30 FPS selama 2,3 s
            t["now"] = i / 30.0
            reader._push(t["now"], np.zeros((2, 2, 3)))
        done = reader.take_finished_recording()
        self.assertIsNotNone(done)
        t_start, t_end, frames = done
        self.assertEqual(len(frames), 59)            # frame 1/30 ... 59/30 (< 2,0 s)
        self.assertGreaterEqual(t_end - t_start, 2.0)
        self.assertIsNone(reader.take_finished_recording())
        self.assertEqual(reader.latest()[0], 69)

    def test_cancel(self):
        reader = CameraReader(FakeCap(0), clock=lambda: 0.0)
        reader.start_recording(2.0)
        reader.cancel_recording()
        reader._push(5.0, np.zeros((2, 2, 3)))
        self.assertIsNone(reader.take_finished_recording())

    def test_thread_reads_until_stopped(self):
        cap = FakeCap(50)
        reader = CameraReader(cap)
        reader.start()
        deadline = threading.Event()
        for _ in range(200):
            if cap.i >= 50:
                break
            deadline.wait(0.01)
        reader.stop()
        self.assertEqual(cap.i, 50)
        self.assertEqual(int(reader.latest()[2][0, 0, 0]), 50)


if __name__ == "__main__":
    unittest.main()
