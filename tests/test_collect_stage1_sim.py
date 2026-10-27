"""
Simulasi end-to-end collect_stage1.main() dengan kamera, pembaca kamera, MediaPipe,
dan UI palsu. Memastikan alur formulir -> cek privasi -> SIAP -> REKAM -> PROSES ->
TINJAU (penuh/sebagian/ulang/lewati/catatan) dan penyimpanan berjalan.

Uji ini TIDAK membuktikan bahwa kamera, MediaPipe, Pygame, atau tkinter asli
berjalan; itu harus diuji di komputer peneliti.
"""
import csv
import json
import os
import shutil
import sys
import tempfile
import time
import types
import unittest

import numpy as np

CODE_DIR = os.path.join(os.path.dirname(__file__), "..", "code")
sys.path.insert(0, CODE_DIR)

FPS = 30.0
MODULES = ("cv2", "mediapipe", "collect_stage1", "gesture_pipeline", "stage1_writer",
           "stage1_report", "stage1_form", "stage1_capture")


class FakeClock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class FakeCap:
    def __init__(self, *a):
        self.props = {}

    def isOpened(self):
        return True

    def set(self, k, v):
        self.props[k] = v

    def get(self, k):
        return self.props.get(k, 0)

    def getBackendName(self):
        return "FAKE"

    def read(self):
        return True, np.zeros((720, 1280, 3), dtype=np.uint8)

    def release(self):
        pass


def install_fakes(detect_pattern=None):
    cv2 = types.ModuleType("cv2")
    cv2.__version__ = "fake"
    cv2.CAP_DSHOW, cv2.CAP_ANY = 700, 0
    cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS, cv2.CAP_PROP_FOURCC = 3, 4, 5, 6
    cv2.COLOR_BGR2RGB = 4
    cv2.written_video_frames = 0
    cv2.video_fps = []

    class VW:
        def __init__(self, path, fourcc, fps, size):
            cv2.video_fps.append(fps)

        def isOpened(self):
            return True

        def write(self, f):
            cv2.written_video_frames += 1

        def release(self):
            pass

    cv2.VideoCapture = FakeCap
    cv2.VideoWriter = VW
    cv2.VideoWriter_fourcc = lambda *a: 1196444237
    cv2.cvtColor = lambda img, code: img
    cv2.flip = lambda img, code: img

    mp = types.ModuleType("mediapipe")
    mp.__version__ = "fake"
    counter = {"n": 0}

    class LM:
        def __init__(self, x, y, z):
            self.x, self.y, self.z = x, y, z

    class Hands:
        def __init__(self, **kw):
            pass

        def process(self, img):
            counter["n"] += 1
            if detect_pattern and not detect_pattern(counter["n"]):
                return types.SimpleNamespace(multi_hand_landmarks=None, multi_handedness=None)
            rng = np.random.default_rng(counter["n"])
            hl = types.SimpleNamespace(landmark=[LM(*rng.uniform(0, 1, 3)) for _ in range(21)])
            cls = types.SimpleNamespace(label="Right", score=0.97)
            return types.SimpleNamespace(multi_hand_landmarks=[hl],
                                         multi_handedness=[types.SimpleNamespace(classification=[cls])])

        def close(self):
            pass

    mp.solutions = types.SimpleNamespace(
        hands=types.SimpleNamespace(Hands=Hands, HAND_CONNECTIONS=[]),
        drawing_utils=types.SimpleNamespace(draw_landmarks=lambda *a, **k: None))
    sys.modules["cv2"] = cv2
    sys.modules["mediapipe"] = mp
    return cv2, Hands


class FakeReader:
    """Pembaca kamera sinkron: tiap latest() = satu frame baru 1/30 s kemudian."""
    def __init__(self, clock):
        self.clock = clock
        self.seq = 0
        self.read_failures = 0
        self.recording = False
        self.frames, self.done, self.rec_start, self.hold = [], None, None, None
        self.stopped = False

    def latest(self):
        self.clock.t += 1.0 / FPS
        self.seq += 1
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        if self.recording:
            if self.clock.t - self.rec_start < self.hold:
                self.frames.append((self.clock.t, frame))
            else:
                self.recording = False
                self.done = (self.rec_start, self.clock.t, self.frames)
        return self.seq, self.clock.t, frame

    def start_recording(self, hold):
        self.frames, self.done, self.hold = [], None, hold
        self.rec_start = self.clock.t
        self.recording = True
        return self.rec_start

    def recording_progress(self):
        return self.clock.t - self.rec_start if self.recording else 0.0

    def take_finished_recording(self):
        d, self.done = self.done, None
        return d

    def cancel_recording(self):
        self.recording = False

    def stop(self):
        self.stopped = True


class FakeUI:
    def __init__(self, keys):
        self.keys = iter(keys)
        self.views, self.messages = [], []
        self.closed = False
        self.text_mode = False

    def poll(self):
        k = next(self.keys, "quit")
        return [] if k is None else list(k) if isinstance(k, tuple) else [k]

    def render(self, frame_rgb, view):
        self.views.append(dict(view))

    def set_text_mode(self, on):
        self.text_mode = on

    def show_message(self, title, lines, color=None):
        self.messages.append((title, lines))

    def close(self):
        self.closed = True


IDLE = None


def one_trial(decision_key, idle_after_space=70):
    return [IDLE] * 2 + ["space"] + [IDLE] * idle_after_space + [decision_key]


def form_info(code="P03", side="kiri"):
    return {"participant": code, "tanggal": "2026-11-03", "usia": "58", "jenis_kelamin": "laki-laki",
            "tangan_dominan": "kanan", "sisi_paretik": side,
            "kriteria": {"inklusi_stroke": "ya"}, "memenuhi_syarat": "memenuhi",
            "consent": "ya", "consent_tanggal": "2026-11-03", "diperiksa_oleh": "dr. Uji",
            "simpan_video": True, "camera": 0}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestCollectSimulation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._saved = {k: sys.modules.get(k) for k in MODULES}
        self._perf = time.perf_counter

    def tearDown(self):
        time.perf_counter = self._perf
        shutil.rmtree(self.tmp)
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v

    def run_app(self, keys, info=None, extra_args=(), detect_pattern=None, form_returns=True):
        clock = FakeClock()
        cv2, Hands = install_fakes(detect_pattern)
        for m in MODULES[2:]:
            sys.modules.pop(m, None)
        import collect_stage1
        collect_stage1.time.perf_counter = clock
        self.ui = FakeUI(keys)
        self.reader = FakeReader(clock)
        self.form_calls = []

        def form_fn(existing):
            self.form_calls.append(existing("P03"))
            return (info or form_info()) if form_returns else None

        rc = collect_stage1.main(["--out", self.tmp, *extra_args], ui_factory=lambda: self.ui,
                                 form_fn=form_fn, reader_factory=lambda cap: self.reader,
                                 hands_factory=lambda: Hands())
        return rc, cv2

    def session_dir(self, code="P03"):
        sessions = os.listdir(os.path.join(self.tmp, code))
        self.assertEqual(len(sessions), 1)
        return os.path.join(self.tmp, code, sessions[0])

    # ------------------------------------------------------------------
    def test_full_protocol_penuh_sebagian_redo_skip_note(self):
        keys = [IDLE, "c"]                                    # cek privasi
        keys += one_trial("r")                                # palm r1 a1 -> ulang
        keys += one_trial("enter")                            # palm r1 a2 -> penuh
        keys += one_trial("p")                                # palm r2 -> sebagian
        keys += one_trial("enter") * 2                        # palm r3, r4
        keys += [IDLE, "space"] + [IDLE] * 70 + ["n", ("char:j", "char:a", "char:r", "char:i"),
                                                   "backspace", "enter", "s"]   # palm r5 lewati + catatan "jar"
        keys += one_trial("enter") * 15
        rc, cv2 = self.run_app(keys)
        self.assertEqual(rc, 0)
        sdir = self.session_dir()

        trials = read_csv(os.path.join(sdir, "trials.csv"))
        self.assertEqual(len(trials), 21)
        self.assertEqual([t["decision"] for t in trials].count("redo"), 1)
        skipped = [t for t in trials if t["decision"] == "skipped"]
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["gesture_formed"], "tidak")
        self.assertEqual(skipped[0]["note"], "jar")
        accepted = [t for t in trials if t["accepted"] == "1"]
        self.assertEqual(len(accepted), 19)
        self.assertEqual(sum(t["gesture_form"] == "sebagian" for t in accepted), 1)
        self.assertTrue(all(t["gesture_formed"] == "ya" for t in accepted))

        # laju rekam mengikuti kamera (30 FPS), bukan laju tampilan
        for t in trials:
            self.assertIn(int(t["n_frames"]), (59, 60, 61))
            self.assertAlmostEqual(float(t["effective_fps"]), 30.0, delta=1.0)
        frames = read_csv(os.path.join(sdir, "frames.csv"))
        self.assertEqual(len(frames), sum(int(t["n_frames"]) for t in trials))
        self.assertEqual(cv2.written_video_frames, len(frames))
        self.assertTrue(all(abs(f - 30.0) < 1.0 for f in cv2.video_fps))

        with open(os.path.join(sdir, "session.json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta["end_reason"], "selesai")
        self.assertTrue(meta["privacy_check"]["confirmed"])
        self.assertEqual(meta["participant_info"]["tangan_dominan"], "kanan")
        self.assertEqual(meta["hand_side"], "kiri")
        self.assertEqual(meta["camera_requested"]["fourcc"], "MJPG")

        reg = read_csv(os.path.join(self.tmp, "participants.csv"))
        self.assertEqual(len(reg), 1)
        self.assertEqual(reg[0]["participant"], "P03")
        self.assertEqual(reg[0]["sisi_paretik"], "kiri")

        with open(os.path.join(sdir, "lembar_tahap1.html"), encoding="utf-8") as f:
            report = f.read()
        self.assertIn("LEMBAR PENGUMPUL DATA 1", report)
        self.assertIn("palm_r1_a2.mp4", report)
        self.assertIn("diulang 1x", report)
        self.assertIn("Diterima 19 dari 20", report)
        self.assertTrue(self.ui.closed and self.reader.stopped)
        self.assertEqual(self.form_calls, [[]])

    def test_space_ignored_before_privacy_check(self):
        keys = [IDLE, "space", "space", "c"] + one_trial("enter")
        self.run_app(keys)
        trials = read_csv(os.path.join(self.session_dir(), "trials.csv"))
        self.assertEqual(trials[0]["trial_id"], "palm_r1")
        self.assertEqual(trials[0]["decision"], "accepted")
        self.assertEqual(sum(t["accepted"] == "1" for t in trials), 1)

    def test_states_rendered(self):
        self.run_app([IDLE, "c"] + one_trial("enter") * 20)
        states = {v["state"] for v in self.ui.views}
        self.assertEqual(states, {"PRATINJAU", "SIAP", "REKAM", "PROSES", "TINJAU"})
        tinjau = [v for v in self.ui.views if v["state"] == "TINJAU"]
        self.assertTrue(all(v["video_name"] and v["video_name"].endswith(".mp4") for v in tinjau))

    def test_quit_while_recording_marks_abort(self):
        keys = [IDLE, "c"] + one_trial("enter") + [IDLE, "space"] + [IDLE] * 20 + ["quit", "quit"]
        self.run_app(keys)
        sdir = self.session_dir()
        trials = read_csv(os.path.join(sdir, "trials.csv"))
        self.assertEqual([t["decision"] for t in trials], ["accepted", "aborted"])
        with open(os.path.join(sdir, "session.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["end_reason"], "operator_keluar")
        self.assertTrue(os.path.exists(os.path.join(sdir, "lembar_tahap1.html")))

    def test_note_cancel_restores_previous(self):
        keys = [IDLE, "c", IDLE, "space"] + [IDLE] * 70 + ["n", ("char:x",), "cancel", "enter"]
        self.run_app(keys)
        t = read_csv(os.path.join(self.session_dir(), "trials.csv"))[0]
        self.assertEqual(t["note"], "")
        self.assertEqual(t["gesture_form"], "penuh")

    def test_detection_rate_is_recorded(self):
        self.run_app([IDLE, "c"] + one_trial("enter"), detect_pattern=lambda n: n % 2 == 0)
        t = read_csv(os.path.join(self.session_dir(), "trials.csv"))[0]
        self.assertGreater(float(t["detection_rate"]), 0.3)
        self.assertLess(float(t["detection_rate"]), 0.7)

    def test_form_cancel_saves_nothing(self):
        rc, _ = self.run_app([], form_returns=False)
        self.assertEqual(rc, 0)
        self.assertEqual(os.listdir(self.tmp), [])

    def test_uji_mode_uses_p99_without_form_or_registry(self):
        self.run_app([IDLE, "c"] + one_trial("enter"), extra_args=["--uji", "--sisi", "kanan"])
        self.assertEqual(self.form_calls, [])
        self.assertTrue(os.path.isdir(os.path.join(self.tmp, "P99")))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "participants.csv")))

    def test_no_video_option(self):
        info = form_info()
        info["simpan_video"] = False
        rc, cv2 = self.run_app([IDLE, "c"] + one_trial("enter"), info=info)
        self.assertEqual(cv2.written_video_frames, 0)
        self.assertFalse(os.path.exists(os.path.join(self.session_dir(), "videos")))


if __name__ == "__main__":
    unittest.main()
