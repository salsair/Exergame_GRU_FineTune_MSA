"""
gesture_pipeline.py
===================
Satu-satunya sumber kebenaran untuk:
  - label kelas gestur dan urutan indeksnya,
  - konfigurasi kamera dan MediaPipe Hands,
  - pembentukan 76 fitur (63 koordinat ternormalisasi + 13 sudut).

Modul ini dipakai bersama oleh:
  - game (code/camera.py),
  - aplikasi akuisisi Tahap 1 (code/collect_stage1.py),
  - skrip ekspor dan fine tuning (menyusul).

ATURAN: jangan mengubah `engineer_features()` tanpa melatih ulang / mengevaluasi
ulang model. Fungsi ini disalin apa adanya dari `HandGestureCamera.engineer_features`
pada baseline Ulfa (2026) (tag git `baseline-ulfa-2026`) dan diuji identik oleh
tests/test_gesture_pipeline.py.

cv2 dan mediapipe diimpor di dalam fungsi agar modul ini dapat diuji tanpa kamera.
"""

import numpy as np

# ---------------------------------------------------------------------------
# Label kelas
# ---------------------------------------------------------------------------
# Urutan indeks = urutan keluaran softmax model GRU baseline.
# Diverifikasi 27 Oktober 2026 dengan model 311025_GRU_3.keras (uji langsung,
# tangan sehat peneliti): 0 palm, 1 fist, 2 thumb_index, 3 grabbing.
GESTURE_LABELS = ("palm", "fist", "thumb_index", "grabbing")
LABEL_TO_INDEX = {name: i for i, name in enumerate(GESTURE_LABELS)}

# Pemetaan kontrol sesuai Tabel 3.8 proposal (dipakai game, bukan akuisisi).
GESTURE_TO_DIRECTION = {
    "palm": "atas",
    "fist": "bawah",
    "grabbing": "kanan",
    "thumb_index": "kiri",
}

# ---------------------------------------------------------------------------
# Konfigurasi kamera dan MediaPipe
# ---------------------------------------------------------------------------
# Resolusi dikunci agar rasio aspek koordinat MediaPipe sama antara akuisisi
# data dan game (temuan T3). Nilai aktual yang diberikan driver kamera selalu
# dicatat di metadata sesi, karena driver boleh menolak permintaan ini.
CAMERA_CONFIG = {
    "width": 1280,
    "height": 720,
    "fps": 30,
}

# Sama dengan baseline camera.py agar distribusi landmark konsisten.
# min_detection_confidence=0.1 adalah nilai baseline (temuan S1, keputusan
# terbuka). Jika diubah, ubah di sini saja dan berlaku untuk akuisisi + game.
MEDIAPIPE_CONFIG = {
    "static_image_mode": False,
    "max_num_hands": 1,
    "min_detection_confidence": 0.1,
    "min_tracking_confidence": 0.5,  # default MediaPipe, ditulis eksplisit
}

NUM_LANDMARKS = 21
NUM_FEATURES = 76

# ---------------------------------------------------------------------------
# Definisi tulang dan sudut (identik dengan baseline)
# ---------------------------------------------------------------------------
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),         # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),         # Index finger
    (9, 10), (10, 11), (11, 12),            # Middle finger
    (13, 14), (14, 15), (15, 16),           # Ring finger
    (17, 18), (18, 19), (19, 20),           # Pinky finger
    (0, 9), (0, 13), (0, 17),               # Palm connections from wrist
    (5, 9), (9, 13), (13, 17),              # Palm connections across fingers
]

FLEXION_BONES = [
    ((0, 1), (1, 2)), ((1, 2), (2, 3)),
    ((0, 5), (5, 6)), ((5, 6), (6, 7)),
    ((0, 9), (9, 10)), ((9, 10), (10, 11)),
    ((0, 13), (13, 14)), ((13, 14), (14, 15)),
    ((0, 17), (17, 18)), ((17, 18), (18, 19)),
]

SPLAY_BONES = [((0, 5), (0, 9)), ((0, 9), (0, 13)), ((0, 13), (0, 17))]


def calculate_angle(v1, v2):
    """Sudut (radian) antara dua vektor. Identik dengan baseline."""
    if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
        return 0.0
    v1_u = v1 / np.linalg.norm(v1)
    v2_u = v2 / np.linalg.norm(v2)
    dot_product = np.clip(np.dot(v1_u, v2_u), -1.0, 1.0)
    return np.arccos(dot_product)


def engineer_features(landmarks_np):
    """
    21x3 landmark mentah (koordinat MediaPipe, ter-normalisasi citra) -> 76 fitur.

    Persamaan 2.1-2.3 proposal: relatif terhadap wrist, dibagi jarak Euclidean
    maksimum. Persamaan 2.4-2.5: 10 sudut ruas jari + 3 sudut antarkelompok jari.
    """
    landmarks_np = np.asarray(landmarks_np, dtype=float)
    if landmarks_np.shape != (NUM_LANDMARKS, 3):
        raise ValueError(f"landmarks harus berbentuk (21, 3), diterima {landmarks_np.shape}")

    wrist_landmark = landmarks_np[0]
    relative_landmarks = landmarks_np - wrist_landmark

    max_distance = np.max(np.linalg.norm(relative_landmarks, axis=1))
    normalized_landmarks = relative_landmarks / max_distance if max_distance > 0 else relative_landmarks

    bone_vectors = {(start, end): normalized_landmarks[end] - normalized_landmarks[start]
                    for start, end in HAND_CONNECTIONS}

    angles = []
    for bone1, bone2 in FLEXION_BONES:
        angles.append(calculate_angle(bone_vectors.get(bone1, np.zeros(3)), bone_vectors.get(bone2, np.zeros(3))))
    for bone1, bone2 in SPLAY_BONES:
        angles.append(calculate_angle(bone_vectors.get(bone1, np.zeros(3)), bone_vectors.get(bone2, np.zeros(3))))

    return np.concatenate([normalized_landmarks.flatten(), np.array(angles).flatten()])


# ---------------------------------------------------------------------------
# Kamera dan MediaPipe
# ---------------------------------------------------------------------------
def open_camera(index=0, config=CAMERA_CONFIG):
    """
    Buka kamera dan minta resolusi/FPS dari CAMERA_CONFIG.
    Mengembalikan (cap, actual) dengan actual = resolusi dan FPS yang benar-benar
    diberikan driver. Mengembalikan (None, None) jika kamera gagal dibuka.
    """
    import cv2

    # CAP_DSHOW di Windows mempercepat pembukaan kamera dan lebih patuh pada
    # permintaan resolusi; di sistem lain gunakan backend default.
    import sys
    backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        cap.release()
        return None, None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config["height"])
    cap.set(cv2.CAP_PROP_FPS, config["fps"])

    actual = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps_reported": float(cap.get(cv2.CAP_PROP_FPS)),
        "backend": cap.getBackendName() if hasattr(cap, "getBackendName") else str(backend),
    }
    return cap, actual


def create_hands(config=MEDIAPIPE_CONFIG):
    import mediapipe as mp
    return mp.solutions.hands.Hands(**config)


def extract_landmarks(result):
    """
    Hasil MediaPipe -> (landmarks 21x3 atau None, handedness_label, handedness_score).
    Hanya tangan pertama yang dipakai (max_num_hands=1).
    """
    if result is None or not result.multi_hand_landmarks:
        return None, None, None
    lms = result.multi_hand_landmarks[0].landmark
    arr = np.array([[lm.x, lm.y, lm.z] for lm in lms], dtype=float)
    label, score = None, None
    if getattr(result, "multi_handedness", None):
        cls = result.multi_handedness[0].classification[0]
        label, score = cls.label, float(cls.score)
    return arr, label, score
