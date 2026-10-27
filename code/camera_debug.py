# debug_thread.py
import time
import os
import csv
from datetime import datetime
import psutil
import threading

class GameDebugger:
    def __init__(self, camera_instance):
        """
        Inisialisasi debugger.
        Membutuhkan instance dari HandGestureCamera untuk mengambil data.
        """
        self.camera = camera_instance
        self.running = False
        self.log_file = None
        self.log_writer = None
        self.thread = None
        
        self.LOG_INTERVAL_SECONDS = 1.0
        self.LOG_FOLDER = "debug_logs"

    def _setup_logging(self):
        """Mempersiapkan folder log dan file CSV untuk sesi ini."""
        if not os.path.exists(self.LOG_FOLDER):
            os.makedirs(self.LOG_FOLDER)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(self.LOG_FOLDER, f"log_session_{timestamp}.csv")
        
        self.log_file = open(log_filename, 'w', newline='', encoding='utf-8')
        self.log_writer = csv.writer(self.log_file)
        
        header = [
            "Timestamp", "FPS", "Processing_Latency_ms", "Landmark_Status",
            "Prediction_Confidence", "Predicted_Gesture_ID", "CPU_Usage_%", "Memory_Usage_MB"
        ]
        self.log_writer.writerow(header)
        print(f"Debugger is logging to {log_filename}")

    def _get_system_stats(self):
        """Mengambil data penggunaan CPU dan Memori saat ini."""
        cpu_usage = psutil.cpu_percent(interval=None)
        memory_info = psutil.virtual_memory()
        memory_usage_mb = memory_info.used / (1024 * 1024)
        return cpu_usage, memory_usage_mb

    def _debug_loop(self):
        """Loop utama yang berjalan di thread terpisah untuk mencatat data."""
        frame_count = 0
        last_log_time = time.time()
        
        while self.running:
            # Kita tidak memanggil cam.process() di sini karena itu dipanggil oleh game loop utama.
            # Thread ini hanya bertugas membaca data dan mencatatnya.
            frame_count += 1
            
            current_time = time.time()
            elapsed_time = current_time - last_log_time

            if elapsed_time >= self.LOG_INTERVAL_SECONDS:
                # FPS di sini adalah FPS dari debug loop, bukan game.
                # Untuk FPS game yang akurat, idealnya dihitung di game loop.
                # Namun untuk tujuan debug, ini cukup representatif.
                fps = self.camera.get_game_fps() # Membutuhkan metode baru di camera class

                latency = self.camera.processing_latency_ms
                landmark_status = self.camera.landmark_status
                confidence = self.camera.last_prediction_confidence
                gesture_id = self.camera.last_predicted_label if self.camera.last_predicted_label is not None else "N/A"
                
                cpu, memory = self._get_system_stats()
                
                print(
                    f"\r[DEBUG] FPS: {fps:.2f} | Latency: {latency:.2f}ms | Confidence: {confidence:.2f} | CPU: {cpu:.1f}%",
                    end=""
                )

                log_row = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    f"{fps:.2f}", f"{latency:.2f}", landmark_status,
                    f"{confidence:.4f}", gesture_id, f"{cpu:.1f}", f"{memory:.1f}"
                ]
                self.log_writer.writerow(log_row)
                
                frame_count = 0
                last_log_time = current_time
            
            # Beri jeda kecil agar loop ini tidak memakan 100% CPU
            time.sleep(0.01)

    def start(self):
        """Memulai thread debugging."""
        if self.running:
            print("Debugger is already running.")
            return

        self._setup_logging()
        self.running = True
        # daemon=True berarti thread ini akan berhenti secara otomatis saat program utama ditutup
        self.thread = threading.Thread(target=self._debug_loop, daemon=True)
        self.thread.start()
        self.start_time_global = time.time()
        print("Debugging thread started.")

    def stop(self):
        """Menghentikan thread debugging dan menutup file log."""
        if not self.running:
            return
            
        self.running = False
        # Tidak perlu join() jika daemon=True, tapi ini memastikan cleanup terjadi.
        if self.log_file:
            self.log_file.close()
        print("\nDebugging thread stopped and log file closed.")

        if hasattr(self, "confirmed_prediction_times") and self.confirmed_prediction_times:
            total_time = sum(self.confirmed_prediction_times)
            avg_time = total_time / len(self.confirmed_prediction_times)
            print(f"\nTotal waktu menyelesaikan semua gesture: {total_time:.2f} ms (rata-rata {avg_time:.2f} ms/gesture)")

        if self.start_time_global is None:
            return
        self.end_time_global = time.time()
        total_duration_sec = self.end_time_global - self.start_time_global
        print(f"\nTotal waktu permainan: {total_duration_sec:.2f} detik ({total_duration_sec/60:.2f} menit)")

        self.camera.evaluate_level()
    