# Panduan Akuisisi Data Tahap 1

Alat ini merekam gestur tangan **paretik** untuk fine tuning GRU:
4 gestur × 5 pengulangan × 2 detik (proposal 3.3.2, Tabel 3.5–3.6).

## Sebelum pasien datang

```bat
cd /d "D:\!scros\kode\Exergame_GRU_FineTune_MSA"
venv\Scripts\activate
python code\collect_stage1.py --participant P99 --sisi kanan
```

Lakukan satu sesi uji coba dengan kode `P99` (tangan peneliti), lalu hapus folder `data\stage1\P99`.
Periksa di konsol bahwa resolusi kamera 1280×720; jika muncul `[PERINGATAN] Kamera memberi ...`, catat.

## Saat sesi pasien

```bat
python code\collect_stage1.py --participant P01 --sisi kiri
```

- `--participant`: kode anonim P01–P15 sesuai daftar Anda. **Jangan** memakai nama atau nomor rekam medis.
- `--sisi`: sisi tangan paretik pasien (`kiri` atau `kanan`).
- Kamera Logitech C922, jarak sekitar 50 cm dari tangan.

| Tombol | Fungsi |
| --- | --- |
| SPASI | Mulai rekam 2 detik, tekan saat gestur pasien sudah terbentuk |
| ENTER | Terima percobaan |
| R | Ulangi percobaan (data lama tetap disimpan, ditandai ditolak) |
| S | Lewati percobaan (mis. pasien tidak mampu) |
| Q / ESC dua kali | Keluar; data yang sudah ada tetap tersimpan |

Urutan gestur: palm → fist → grabbing → thumb_index, masing-masing 5 kali.
Jika deteksi di layar tinjau di bawah 80%, pertimbangkan menekan R.
Berhenti kapan saja bila pasien lelah atau tidak nyaman; tekan Q dua kali.

## Hasil

```
data\stage1\P01\P01_S1_<tanggal>_<jam>\
    session.json   metadata sesi
    frames.csv     landmark mentah semua frame (±60 frame per percobaan)
    trials.csv     daftar percobaan, termasuk yang diulang/dilewati
    videos\        satu video per percobaan
```

Folder `data\` berisi data pasien: **jangan** di-commit ke git atau dibagikan di luar tim penelitian.
Sampling 5 FPS, pemeriksaan kualitas, dan pembentukan 76 fitur dilakukan nanti oleh skrip ekspor.
