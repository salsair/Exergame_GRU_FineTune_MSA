"""
Uji bahwa gesture_pipeline.engineer_features identik dengan fungsi baseline
HandGestureCamera.engineer_features (tag baseline-ulfa-2026).

Jalankan dari folder akar proyek:
    python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
import gesture_pipeline as gp  # noqa: E402

# --- Salinan verbatim dari baseline code/camera.py (jangan diubah) ----------
BASELINE_HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (9, 10), (10, 11), (11, 12),
    (13, 14), (14, 15), (15, 16),
    (17, 18), (18, 19), (19, 20),
    (0, 9), (0, 13), (0, 17),
    (5, 9), (9, 13), (13, 17)
]


def baseline_calculate_angle(v1, v2):
    if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
        return 0.0
    v1_u = v1 / np.linalg.norm(v1)
    v2_u = v2 / np.linalg.norm(v2)
    dot_product = np.clip(np.dot(v1_u, v2_u), -1.0, 1.0)
    return np.arccos(dot_product)


def baseline_engineer_features(landmarks_np):
    wrist_landmark = landmarks_np[0]
    relative_landmarks = landmarks_np - wrist_landmark
    max_distance = np.max(np.linalg.norm(relative_landmarks, axis=1))
    normalized_landmarks = relative_landmarks / max_distance if max_distance > 0 else relative_landmarks
    bone_vectors = {(start, end): normalized_landmarks[end] - normalized_landmarks[start] for start, end in BASELINE_HAND_CONNECTIONS}
    angles = []
    flexion_bones = [((0,1),(1,2)), ((1,2),(2,3)), ((0,5),(5,6)), ((5,6),(6,7)), ((0,9),(9,10)), ((9,10),(10,11)), ((0,13),(13,14)), ((13,14),(14,15)), ((0,17),(17,18)), ((17,18),(18,19))]
    for bone1, bone2 in flexion_bones:
        angles.append(baseline_calculate_angle(bone_vectors.get(bone1, np.zeros(3)), bone_vectors.get(bone2, np.zeros(3))))
    splay_bones = [((0,5),(0,9)), ((0,9),(0,13)), ((0,13),(0,17))]
    for bone1, bone2 in splay_bones:
        angles.append(baseline_calculate_angle(bone_vectors.get(bone1, np.zeros(3)), bone_vectors.get(bone2, np.zeros(3))))
    return np.concatenate([normalized_landmarks.flatten(), np.array(angles).flatten()])
# ---------------------------------------------------------------------------


class TestFeaturesIdenticalToBaseline(unittest.TestCase):
    def test_random_hands_bit_identical(self):
        rng = np.random.default_rng(2026)
        for _ in range(2000):
            lm = rng.uniform(0.0, 1.0, (21, 3))
            lm[:, 2] = rng.normal(0, 0.05, 21)
            np.testing.assert_array_equal(gp.engineer_features(lm), baseline_engineer_features(lm))

    def test_degenerate_inputs(self):
        same = np.full((21, 3), 0.5)                     # semua titik berimpit
        np.testing.assert_array_equal(gp.engineer_features(same), baseline_engineer_features(same))
        lm = np.random.default_rng(1).uniform(0, 1, (21, 3))
        lm[1] = lm[0]                                    # satu tulang panjang nol
        np.testing.assert_array_equal(gp.engineer_features(lm), baseline_engineer_features(lm))

    def test_shape_and_count(self):
        f = gp.engineer_features(np.random.default_rng(3).uniform(0, 1, (21, 3)))
        self.assertEqual(f.shape, (gp.NUM_FEATURES,))
        self.assertEqual(len(gp.FLEXION_BONES) + len(gp.SPLAY_BONES), 13)

    def test_rejects_wrong_shape(self):
        with self.assertRaises(ValueError):
            gp.engineer_features(np.zeros((20, 3)))

    def test_label_order_matches_verified_model(self):
        self.assertEqual(gp.GESTURE_LABELS, ("palm", "fist", "thumb_index", "grabbing"))

    def test_direction_map_matches_proposal_table_3_8(self):
        self.assertEqual(gp.GESTURE_TO_DIRECTION,
                         {"palm": "atas", "fist": "bawah", "grabbing": "kanan", "thumb_index": "kiri"})


if __name__ == "__main__":
    unittest.main()
