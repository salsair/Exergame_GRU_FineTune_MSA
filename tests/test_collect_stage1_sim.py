"""
Simulasi end-to-end collect_stage1.main() dengan kamera, OpenCV, dan MediaPipe palsu.
Tujuan: memastikan alur SIAP -> REKAM -> TINJAU -> (terima/ulang/lewati) dan
penyimpanan berjalan untuk 20 percobaan, tanpa perangkat keras.

Uji ini TIDAK membuktikan bahwa kamera atau MediaPipe asli berjalan; itu harus
diuji di komputer peneliti.
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


class FakeClock:
    def __init__(self):
        self.t = 100.0

    def perf_counter(self):
        return self.t


def install_fakes(keys, clock, detect_pattern=None):
    """Pasang modul cv2 dan mediapipe palsu di sys.modules."""
    cv2 = types.ModuleType("cv2")
    cv2.__version__ = "fake"
    cv2.CAP_DSHOW, cv2.CAP_ANY = 700, 0
    cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS = 3, 4, 5
    cv2.COLOR_BGR2RGB, cv2.FONT_HERSHEY_SIMPLEX, cv2.LINE_AA, cv2.WINDOW_NORMAL = 4, 0, 16, 0
    cv2.written_video_frames = 0
    cv2.opened_videos = []

    class Cap:
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
            clock.t += 1.0 / FPS
            return True, np.zeros((720, 1280, 3), dtype=np.uint8)

        def release(self):
            pass

    class VW:
        def __init__(self, path, *a):
            cv2.opened_videos.append(path)

        def isOpened(self):
            return True

        def write(self, f):
            cv2.written_video_frames += 1

        def release(self):
            pass

    key_iter = iter(keys)
    cv2.VideoCapture = Cap
    cv2.VideoWriter = VW
    cv2.VideoWriter_fourcc = lambda *a: 0
    cv2.cvtColor = lambda img, code: img
    cv2.flip = lambda img, code: img
    cv2.putText = cv2.rectangle = lambda *a, **k: None
    cv2.namedWindow = cv2.imshow = cv2.destroyAllWindows = lambda *a, **k: None
    cv2.waitKey = lambda ms: next(key_iter, ord("q"))

    mp = types.ModuleType("mediapipe")
    mp.__version__ = "fake"
    counter = {"n": 0}

    class LM:
        def __init__(self, x, y, z):
            self.x, self.y, self.z = x, y, z

    class Hands:
        def __init__(self, **kw):
            self.kw = kw

        def process(self, img):
            counter["n"] += 1
            detected = detect_pattern(counter["n"]) if detect_pattern else True
            if not detected:
                return types.SimpleNamespace(multi_hand_landmarks=None, multi_handedness=None)
            rng = np.random.default_rng(counter["n"])
            lms = [LM(*rng.uniform(0, 1, 3)) for _ in range(21)]
            hl = types.SimpleNamespace(landmark=lms)
            cls = types.SimpleNamespace(label="Right", score=0.97)
            return types.SimpleNamespace(multi_hand_landmarks=[hl],
                                         multi_handedness=[types.SimpleNamespace(classification=[cls])])

        def close(self):
            pass

    mp.solutions = types.SimpleNamespace(
        hands=types.SimpleNamespace(Hands=Hands, HAND_CONNECTIONS=[]),
        drawing_utils=types.SimpleNamespace(draw_landmarks=lambda *a, **k: None),
    )
    sys.modules["cv2"] = cv2
    sys.modules["mediapipe"] = mp
    return cv2


IDLE = 255
SPACE, ENTER = ord(" "), 13


def one_trial(decision_key, idle_after_space=70):
    # SIAP: beberapa frame idle, SPASI, ~2,3 s idle (rekam 2 s), lalu keputusan
    return [IDLE] * 3 + [SPACE] + [IDLE] * idle_after_space + [decision_key]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestCollectSimulation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._saved = {k: sys.modules.get(k) for k in ("cv2", "mediapipe", "collect_stage1", "gesture_pipeline")}
        self._perf_counter = time.perf_counter

    def tearDown(self):
        time.perf_counter = self._perf_counter
        shutil.rmtree(self.tmp)
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v

    def run_app(self, keys, extra_args=(), detect_pattern=None):
        clock = FakeClock()
        cv2 = install_fakes(keys, clock, detect_pattern)
        for m in ("collect_stage1", "gesture_pipeline", "stage1_writer"):
            sys.modules.pop(m, None)
        import collect_stage1
        collect_stage1.time.perf_counter = clock.perf_counter
        sys.argv = ["collect_stage1.py", "--participant", "P03", "--sisi", "kiri",
                    "--out", self.tmp, *extra_args]
        rc = collect_stage1.main()
        sessions = os.listdir(os.path.join(self.tmp, "P03"))
        self.assertEqual(len(sessions), 1)
        return rc, os.path.join(self.tmp, "P03", sessions[0]), cv2

    def test_full_protocol_with_one_redo_and_one_skip(self):
        keys = one_trial(ord("r"))                     # palm r1 percobaan 1 -> ulang
        keys += one_trial(ENTER)                       # palm r1 percobaan 2 -> terima
        keys += one_trial(ENTER) * 3                   # palm r2..r4
        keys += one_trial(ord("s"))                    # palm r5 -> lewati
        keys += one_trial(ENTER) * 15                  # fist, grabbing, thumb_index
        rc, sdir, cv2 = self.run_app(keys)
        self.assertEqual(rc, 0)

        trials = read_csv(os.path.join(sdir, "trials.csv"))
        self.assertEqual(len(trials), 21)
        self.assertEqual(sum(t["accepted"] == "1" for t in trials), 19)
        self.assertEqual([t["decision"] for t in trials].count("redo"), 1)
        self.assertEqual([t["decision"] for t in trials].count("skipped"), 1)
        accepted = [t for t in trials if t["accepted"] == "1"]
        self.assertEqual({t["gesture"] for t in accepted}, {"palm", "fist", "grabbing", "thumb_index"})

        for t in trials:
            self.assertGreaterEqual(float(t["duration_s"]), 2.0)
            self.assertLess(float(t["duration_s"]), 2.0 + 2.0 / FPS)
            self.assertIn(int(t["n_frames"]), (60, 61))

        frames = read_csv(os.path.join(sdir, "frames.csv"))
        self.assertEqual(len(frames), sum(int(t["n_frames"]) for t in trials))
        self.assertEqual({f["hand_side"] for f in frames}, {"kiri"})
        self.assertEqual(cv2.written_video_frames, len(frames))
        self.assertEqual(len(cv2.opened_videos), 21)

        with open(os.path.join(sdir, "session.json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta["end_reason"], "selesai")
        self.assertEqual(meta["protocol"]["gestures_in_order"], ["palm", "fist", "grabbing", "thumb_index"])
        self.assertEqual(meta["camera_requested"], {"width": 1280, "height": 720, "fps": 30})
        self.assertEqual(meta["mediapipe_config"]["min_detection_confidence"], 0.1)

    def test_quit_midway_keeps_data_and_marks_abort(self):
        keys = one_trial(ENTER) * 2
        keys += [IDLE, SPACE] + [IDLE] * 20 + [ord("q"), ord("q")]   # keluar saat merekam
        rc, sdir, _ = self.run_app(keys)
        trials = read_csv(os.path.join(sdir, "trials.csv"))
        self.assertEqual([t["decision"] for t in trials], ["accepted", "accepted", "aborted"])
        with open(os.path.join(sdir, "session.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["end_reason"], "operator_keluar")

    def test_single_q_is_cancelled_by_other_key(self):
        keys = [IDLE, ord("q"), ord("x")] + one_trial(ENTER)   # q lalu batal
        rc, sdir, _ = self.run_app(keys)
        trials = read_csv(os.path.join(sdir, "trials.csv"))
        self.assertEqual(trials[0]["decision"], "accepted")

    def test_detection_rate_is_recorded(self):
        keys = one_trial(ENTER)
        rc, sdir, _ = self.run_app(keys, detect_pattern=lambda n: n % 2 == 0)
        t = read_csv(os.path.join(sdir, "trials.csv"))[0]
        self.assertAlmostEqual(float(t["detection_rate"]), 0.5, delta=0.02)

    def test_no_video_flag(self):
        rc, sdir, cv2 = self.run_app(one_trial(ENTER), extra_args=["--no-video"])
        self.assertEqual(cv2.written_video_frames, 0)
        self.assertFalse(os.path.exists(os.path.join(sdir, "videos")))

    def test_invalid_participant_rejected_before_camera(self):
        clock = FakeClock()
        install_fakes([], clock)
        for m in ("collect_stage1", "gesture_pipeline", "stage1_writer"):
            sys.modules.pop(m, None)
        import collect_stage1
        sys.argv = ["collect_stage1.py", "--participant", "Budi", "--sisi", "kiri", "--out", self.tmp]
        self.assertEqual(collect_stage1.main(), 2)
        self.assertEqual(os.listdir(self.tmp), [])


if __name__ == "__main__":
    unittest.main()
