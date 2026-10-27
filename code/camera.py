# camera_debug.py
import cv2
import mediapipe as mp
import numpy as np
import time
from tensorflow.keras.models import load_model
import pygame
import math
from keras.initializers import Orthogonal
from keras.utils import custom_object_scope

# This code is used for capturing video from the camera and processing hand gestures using a pre-trained model.
# It uses OpenCV for video capture and Mediapipe for hand detection and landmark extraction.
# It also uses TensorFlow for loading the pre-trained model and making predictions.
# The camera feed is displayed in a Pygame window, and the detected hand landmarks are drawn on the video frame.

# ==============================================================================
# Constants
# ==============================================================================
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),         # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),         # Index finger
    (9, 10), (10, 11), (11, 12),            # Middle finger
    (13, 14), (14, 15), (15, 16),           # Ring finger
    (17, 18), (18, 19), (19, 20),           # Pinky finger
    (0, 9), (0, 13), (0, 17),               # Palm connections from wrist
    (5, 9), (9, 13), (13, 17)               # Palm connections across fingers
]

# Helper function to calculate angles
def calculate_angle(v1, v2):
    """Calculates the angle in radians between two vectors."""
    if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
        return 0.0
    v1_u = v1 / np.linalg.norm(v1)
    v2_u = v2 / np.linalg.norm(v2)
    dot_product = np.clip(np.dot(v1_u, v2_u), -1.0, 1.0)
    return np.arccos(dot_product)

class HandGestureCamera:
    def __init__(self):
        print("[DEBUG] Inisialisasi HandGestureCamera dimulai")

        # --- Coba buka kamera dari index 0–2 ---
        self.cap = None
        for i in range(3):
            cap_test = cv2.VideoCapture(i)
            if cap_test.isOpened():
                print(f"[DEBUG] Kamera berhasil dibuka di index {i}")
                self.cap = cap_test
                break
            else:
                print(f"[DEBUG] Kamera tidak tersedia di index {i}")

        if self.cap is None:
            print("Error: Tidak ada kamera yang bisa dibuka!")
            self.is_camera_available = False
            return
        else:
            self.is_camera_available = True

        # --- Inisialisasi MediaPipe ---
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.1
        )

        # --- Load model Keras ---
        self.model = None
        try:
            with custom_object_scope({'Orthogonal': Orthogonal}):
                self.model = load_model("model/GRU/311025_GRU_3.keras", compile=False, safe_mode=False)
            print("[DEBUG] Model berhasil diload")
        except Exception as e:
            print(f"Error loading Keras model: {e}. Gesture recognition akan dinonaktifkan.")
            self.model = None

        # --- Gesture mapping ---
        self.gesture_dict = {
            0: "Palm",
            1: "Fist",
            2: "Thumb Index",
            3: "Grabbing"
        }

        # --- Variabel evaluasi ---
        self.confidence_list = []
        self.log_writer = None

        # --- Drawing util ---
        self.mp_draw = mp.solutions.drawing_utils

        # --- Dwell Time ---
        self.DWELL_TIME_SECONDS = 2
        self.POST_ACTION_COOLDOWN = 0.5
        self._potential_label = None
        self._potential_label_start_time = 0
        self._action_to_consume = None
        self._is_in_cooldown = False
        self._cooldown_end_time = 0

        # --- Debug Info ---
        self.processing_latency_ms = 0
        self.last_prediction_confidence = 0.0
        self.landmark_status = "Not Detected"
        self.last_predicted_label = None
        
        # AKURASI
        self.current_frame = None
        self.game_fps = 0.0

        self.total_predictions = 0
        self.correct_predictions = 0
        self.model_accuracy = 0.0

        # === Ground truth untuk urutan latihan pasien ===
        self.expected_gestures = [0, 1, 2, 3]  # urutan gesture yang harus dilakukan pasien
        self.current_index = 0  # pointer ke gesture keberapa

        # === Variabel evaluasi ===
        self.correct_predictions = 0
        self.total_predictions = 0
        self.confirmed_prediction_times = []

        # after existing vars:
        self._last_confirmed_label = None   # label yang terakhir dikonfirmasi
        self._released = True               # apakah pasien 'melepaskan' pose sejak konfirmasi terakhir
        self._confirmed_prediction_times = []  # waktu prediksi tiap konfirmasi

        self.evaluation_log = []  # Simpan detail gesture

        self.confidence_buffer = []
        self.prediction_buffer = []
        self.MAX_BUFFER = 10                # jumlah frame untuk rata-rata confidence
        self.MIN_STABLE_FRAMES = 5          # berapa frame sama berturut-turut untuk valid

    def get_game_fps(self):
        return self.game_fps
    
    # ==================================================================
    # Frame Handling
    # ==================================================================
    def update_frame(self):
        """Ambil frame baru dari kamera (sekali per loop)."""
        if not self.is_camera_available:
            return False
        ret, frame = self.cap.read()
        if ret:
            self.current_frame = frame
            return True
        return False
    
    def engineer_features(self, landmarks_np):
        """
        Downgraded feature engineering to produce 76 features to match the old model.
        """
        wrist_landmark = landmarks_np[0]
        relative_landmarks = landmarks_np - wrist_landmark

        max_distance = np.max(np.linalg.norm(relative_landmarks, axis=1))
        normalized_landmarks = relative_landmarks / max_distance if max_distance > 0 else relative_landmarks

        bone_vectors = { (start, end): normalized_landmarks[end] - normalized_landmarks[start] for start, end in HAND_CONNECTIONS }
        
        angles = []
        flexion_bones = [((0,1),(1,2)), ((1,2),(2,3)), ((0,5),(5,6)), ((5,6),(6,7)), ((0,9),(9,10)), ((9,10),(10,11)), ((0,13),(13,14)), ((13,14),(14,15)), ((0,17),(17,18)), ((17,18),(18,19))]
        for bone1, bone2 in flexion_bones:
            angles.append(calculate_angle(bone_vectors.get(bone1, np.zeros(3)), bone_vectors.get(bone2, np.zeros(3))))
            
        splay_bones = [((0,5),(0,9)), ((0,9),(0,13)), ((0,13),(0,17))]
        for bone1, bone2 in splay_bones:
            angles.append(calculate_angle(bone_vectors.get(bone1, np.zeros(3)), bone_vectors.get(bone2, np.zeros(3))))

        return np.concatenate([normalized_landmarks.flatten(), np.array(angles).flatten()])

    def process(self):
        start_time = time.perf_counter()
        try:
            # --- CHECK COOLDOWN FIRST ---
            if getattr(self, "_is_in_cooldown", False):
                if time.time() < getattr(self, "_cooldown_end_time", 0):
                    # masih di cooldown: jangan proses prediksi konfirmasi baru
                    self.processing_latency_ms = (time.perf_counter() - start_time) * 1000
                    return
                else:
                    self._is_in_cooldown = False
                    # After cooldown finish, require release before new confirm
                    self._released = False

            # Ambil frame dari kamera
            ret, frame = self.cap.read()
            if not ret:
                self.processing_latency_ms = (time.perf_counter() - start_time) * 1000
                return
            self.current_frame = frame.copy()

            # Konversi ke RGB untuk diproses oleh model deteksi tangan
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.hands.process(image_rgb)

            current_prediction = None
            self.last_prediction_confidence = 0.0
            self.last_predicted_label = None
            self.last_prediction_time_ms = 0.0

            # Tidak ada tangan terdeteksi
            if result is None or not result.multi_hand_landmarks:
                self.landmark_status = "Not Detected"
            
            # Tangan terdeteksi → lakukan prediksi gesture
            else:
                self.landmark_status = f"Detected ({len(result.multi_hand_landmarks[0].landmark)} landmarks)"
                if self.model is not None:
                    # Ekstrak fitur dari landmark tangan
                    try:
                        landmarks_raw_np = np.array([[lm.x, lm.y, lm.z] for lm in result.multi_hand_landmarks[0].landmark])
                        features = self.engineer_features(landmarks_raw_np)
                        model_input = np.reshape(features, (1, 1, -1))

                        # Prediksi gesture menggunakan model
                        t_pred = time.perf_counter()
                        prediction = self.model.predict(model_input, verbose=0)
                        prediction_time_ms = (time.perf_counter() - t_pred) * 1000
                        self.last_prediction_time_ms = prediction_time_ms

                        # Ambil nilai confidence tertinggi dan label prediksi
                        self.last_prediction_confidence = float(np.max(prediction))
                        current_prediction = int(np.argmax(prediction))
                        self.last_predicted_label = current_prediction

                        # Abaikan prediksi dengan confidence terlalu rendah (<0.1)
                        if self.last_prediction_confidence < 0.1:
                            return

                    except Exception as e:
                        # Jika prediksi gagal → reset variabel
                        print(f"Error during gesture prediction: {e}")
                        current_prediction = None
                        self.last_prediction_confidence = 0.0
                        self.last_predicted_label = None

            # Jika tidak ada prediksi → reset potential gesture
            if current_prediction is None:
                self._potential_label = None
                self._potential_label_start_time = 0
                self.processing_latency_ms = (time.perf_counter() - start_time) * 1000
                # If currently holding previous confirmed label and detection lost, consider it released
                self._released = True
                return

            # Jika gesture sama dengan yang terakhir dikonfirmasi
            if self._last_confirmed_label is not None and current_prediction == self._last_confirmed_label:
                if self._is_in_cooldown:
                    # Masih dalam cooldown, tahan dulu
                    self.processing_latency_ms = (time.perf_counter() - start_time) * 1000
                    return
                else:
                    # Cooldown selesai → reset dwell agar bisa trigger lagi
                    if self._potential_label_start_time == 0:
                        self._potential_label = current_prediction
                        self._potential_label_start_time = time.time()
            
            # --- BUFFER CONFIDENCE DAN PREDIKSI ---
            self.confidence_buffer.append(self.last_prediction_confidence)
            self.prediction_buffer.append(current_prediction)

            # Batasi panjang buffer
            if len(self.confidence_buffer) > self.MAX_BUFFER:
                self.confidence_buffer.pop(0)
                self.prediction_buffer.pop(0)

            # Hitung rata-rata confidence
            avg_conf = np.mean(self.confidence_buffer)

            # Hitung stabilitas frame (berapa frame terakhir sama)
            stable_frames = 1
            for i in range(len(self.prediction_buffer) - 2, -1, -1):
                if self.prediction_buffer[i] == current_prediction:
                    stable_frames += 1
                else:
                    break

            # Simpan hasil ini supaya bisa dipakai di evaluasi
            self.avg_confidence_current = avg_conf
            self.stable_frames_current = stable_frames

            # --- DWELL TIME UNTUK KONFIRMASI GESTURE ---
            if current_prediction != self._potential_label:
                # new potential gesture (different from previous potential)
                self._potential_label = current_prediction
                self._potential_label_start_time = time.time()
            else:
                time_held = time.time() - self._potential_label_start_time
                if time_held >= self.DWELL_TIME_SECONDS:
                    # Confirm gesture once
                    # Determine dynamic mode: adaptive mode => true_label = current_prediction
                    true_label = current_prediction

                    # threshold per level
                    level_thresholds = {4:0.10, 5:0.30, 6:0.50, 7:0.70, 8:0.90}
                    current_level = getattr(self, "current_level", 6)
                    current_threshold = level_thresholds.get(current_level, 0.5)

                    is_valid = (
                        self.last_prediction_confidence >= current_threshold and 
                        self.stable_frames_current >= self.MIN_STABLE_FRAMES
                    )

                    # Update counters (evaluation)
                    self.total_predictions = getattr(self, "total_predictions", 0) + 1
                    if is_valid:
                        self.correct_predictions = getattr(self, "correct_predictions", 0) + 1

                    # --- Update counters for evaluation ---
                    self.total_confirmed_gestures = getattr(self, "total_confirmed_gestures", 0) + 1
                    if is_valid:
                        self.total_valid_gestures = getattr(self, "total_valid_gestures", 0) + 1

                    self.model_accuracy = (self.correct_predictions / self.total_predictions) * 100 if self.total_predictions>0 else 0.0

                    # record prediction time once
                    self._confirmed_prediction_times.append(self.last_prediction_time_ms)

                    # append confidence for evaluation
                    if hasattr(self, "confidence_list"):
                        self.confidence_list.append(self.last_prediction_confidence)

                    # Log evaluasi
                    if not hasattr(self, "evaluation_log"):
                        self.evaluation_log.append({
                            "gesture": self.gesture_dict.get(true_label, "-"),
                            "avg_conf": self.avg_confidence_current,
                            "stability": self.stable_frames_current,
                            "valid": is_valid
                        })

                    # mark last confirmed label and block re-confirm until release
                    self._last_confirmed_label = current_prediction
                    self._released = False
                    self._is_in_cooldown = True
                    self._cooldown_end_time = time.time() + self.POST_ACTION_COOLDOWN

                    # print summary for this confirmation
                    print("\n[GESTURE CONFIRMED]")
                    print(f"  Gesture Terdeteksi : {true_label} ({self.gesture_dict.get(true_label,'-')})")
                    print(f"  Confidence          : {self.last_prediction_confidence*100:.2f}%")
                    print(f"  Threshold Level {current_level}: {current_threshold*100:.0f}%")
                    print(f"  Status Gerakan      : {'✅ Valid' if is_valid else '❌ Lemah (tidak valid)'}")
                    print(f"  Waktu prediksi (ms) : {self.last_prediction_time_ms:.2f} ms")
                    print(f"  Rata-rata Confidence : {self.avg_confidence_current*100:.2f}%")
                    print(f"  Stabilitas Frame     : {self.stable_frames_current} frame")

                    if is_valid:
                        self._action_to_consume = true_label

                    # Reset potential so future different gestures start anew
                    self._potential_label = None
                    self._potential_label_start_time = 0

            # Setelah cooldown selesai, izinkan gesture yang sama diulang tanpa harus ubah pose
            if not self._is_in_cooldown and self._last_confirmed_label is not None:
                self._released = True

            self.processing_latency_ms = (time.perf_counter() - start_time) * 1000

        except Exception as e:
            print(f"Exception in process(): {e}")
            self.processing_latency_ms = (time.perf_counter() - start_time) * 1000
            return

    def consume_action(self):
        """
        Called by the game to get a confirmed action. Returns the label then resets.
        This ensures an action is only processed once.
        """
        action = self._action_to_consume
        if action is not None:
            self._action_to_consume = None
        return action

    def get_dwell_progress(self):
        """
        Returns the progress of the current dwell timer as a float (0.0 to 1.0).
        Used by the UI to draw the clock.
        """
        if self._potential_label is not None and self._potential_label_start_time > 0:
            time_held = time.time() - self._potential_label_start_time
            progress = min(time_held / self.DWELL_TIME_SECONDS, 1.0)
            return progress
        return 0.0

    def get_frame(self):
        """Returns a Pygame surface of the current camera view for display."""
        display_size = (200, 160)  # ukuran tampilan kamera 

        if not self.is_camera_available:
            placeholder = pygame.Surface(display_size)
            placeholder.fill((50, 50, 50))
            font = pygame.font.Font(None, 32)
            text = font.render("No Camera", True, (255, 255, 255))
            text_rect = text.get_rect(center=(display_size[0]//2, display_size[1]//2))
            placeholder.blit(text, text_rect)
            return placeholder

        ret, frame = self.cap.read()
        if not ret:
            placeholder = pygame.Surface(display_size)
            placeholder.fill((50, 50, 50))
            font = pygame.font.Font(None, 32)
            text = font.render("Frame Error", True, (255, 255, 255))
            text_rect = text.get_rect(center=(display_size[0]//2, display_size[1]//2))
            placeholder.blit(text, text_rect)
            return placeholder

        frame = cv2.flip(frame, 1)
        image_rgb_for_display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result_display = self.hands.process(image_rgb_for_display.copy())

        if result_display.multi_hand_landmarks:
            for hand_landmarks_display in result_display.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(frame, hand_landmarks_display, mp.solutions.hands.HAND_CONNECTIONS)

        frame_resized = cv2.resize(frame, display_size)
        frame_rgb_final = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        return pygame.surfarray.make_surface(frame_rgb_final.swapaxes(0, 1))

    def evaluate_level(self):
        """Hitung rata-rata confidence + waktu bermain + level."""

        if not hasattr(self, "total_confirmed_gestures") or self.total_confirmed_gestures == 0:
            print("\nBelum ada gesture yang terdeteksi.")
            return

        total_valid = getattr(self, "total_valid_gestures", 0)
        total_all = getattr(self, "total_confirmed_gestures", 0)

        avg_conf = (
            (sum(self.confidence_list) / len(self.confidence_list) * 100)
            if hasattr(self, "confidence_list") and self.confidence_list
            else 0.0
        )

        # === HITUNG WAKTU BERMAIN (DARI KAMERA AKTIF) ===
        if not hasattr(self, "session_start_time"):
            self.session_start_time = pygame.time.get_ticks()

        elapsed_seconds = (pygame.time.get_ticks() - self.session_start_time) / 1000
        minutes = int(elapsed_seconds // 60)
        seconds = int(elapsed_seconds % 60)
        time_str = f"{minutes:02d}:{seconds:02d}"

        # === AMBIL LEVEL ===
        level_name = getattr(self, "current_level", "UNKNOWN LEVEL")

        print(f"\n=== Evaluasi LEVEL {level_name} Selesai ===")
        print(f"Total Gesture Valid : {total_valid} dari {total_all}")
        print(f"Rata-rata Confidence: {avg_conf:.2f}%")
        print(f"Waktu Bermain      : {time_str}\n")

        self.last_evaluation = {
            "level": level_name,
            "total_valid": total_valid,
            "total_all": total_all,
            "avg_confidence": avg_conf,
            "play_time": time_str,
            "play_time_seconds": elapsed_seconds
        }

        return self.last_evaluation

    def release(self):
        if self.is_camera_available and self.cap.isOpened():
            self.cap.release()
        print("Camera released.")