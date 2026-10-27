import math

def distance(p1, p2):
    """Hitung jarak Euclidean antara dua titik (x, y, z)."""
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

def detect_grab(landmarks, threshold=0.25):
    """
    Deteksi gesture grabbing berdasarkan jarak thumb & index relatif terhadap panjang tangan.
    landmarks: daftar landmarks dari Mediapipe
    threshold: rasio jarak maksimal untuk dianggap grab
    """
    thumb = landmarks[4]
    index = landmarks[8]
    wrist = landmarks[0]
    middle_finger = landmarks[9]  # pakai sebagai skala panjang tangan

    norm = distance(wrist, middle_finger)
    d = distance(thumb, index) / norm
    return d < threshold

def detect_palm(landmarks, threshold=0.35):
    """
    Deteksi palm terbuka (tangan terbuka ke kamera)
    Bisa diukur jarak thumb & pinky relatif ke panjang tangan.
    """
    thumb = landmarks[4]
    pinky = landmarks[20]
    wrist = landmarks[0]
    middle_finger = landmarks[9]

    norm = distance(wrist, middle_finger)
    d = distance(thumb, pinky) / norm
    return d > threshold
