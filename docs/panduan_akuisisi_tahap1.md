# Panduan Akuisisi Data Tahap 1

Alat ini merekam gestur tangan **paretik** untuk fine tuning GRU:
4 gestur × 5 pengulangan × 2 detik (proposal 3.3.2, Tabel 3.5–3.6; Lembar Pengumpul Data 1).

Sisi yang direkam selalu sisi **paretik** pasien sesuai pemeriksaan dokter (bisa kiri atau kanan).

## Sebelum hari pengambilan data

```bat
cd /d "D:\!scros\kode\Exergame_GRU_FineTune_MSA"
venv\Scripts\activate
git status
python code\collect_stage1.py --cek-kamera
python code\collect_stage1.py --uji --sisi kanan
```

1. `git status` harus bersih (semua perubahan sudah di-commit) agar setiap sesi tercatat dengan versi kode yang tepat.
2. `--cek-kamera` harus menunjukkan laju mendekati 30 FPS. Jika jauh di bawah: coba `--camera 1` (kamera eksternal), ruangan lebih terang, atau port USB lain.
3. Uji coba lengkap dengan tangan peneliti (kode P99), lalu hapus: `rmdir /s /q data\stage1\P99`.

## Saat sesi pasien

```bat
python code\collect_stage1.py
```

1. **Formulir (Lembar 1 bagian I–II).** Isi kode partisipan (P01–P15), tanggal, usia, jenis kelamin,
   tangan dominan sebelum sakit, sisi paretik, kriteria inklusi/eksklusi, informed consent, dan nama dokter pemeriksa.
   Tombol **Mulai perekaman** hanya berhasil bila pasien memenuhi syarat dan consent sudah ditandatangani.
   **Nama/inisial dan No. RM hanya ditulis tangan di lembar kertas**, tidak dimasukkan ke aplikasi.
2. **Cek privasi.** Atur kamera (±50 cm dari tangan) sehingga hanya tangan yang terlihat. Tekan **C**.
3. **Perekaman.** Urutan: palm → fist → grabbing → thumb_index, masing-masing 5 kali.

| Tombol | Fungsi |
| --- | --- |
| C | Konfirmasi cek privasi (sekali di awal) |
| SPASI | Mulai rekam 2 detik, tekan saat gestur pasien sudah terbentuk |
| ENTER | Terima, bentuk gestur **penuh** |
| P | Terima, bentuk gestur **sebagian** |
| R | Ulangi percobaan (data lama tetap disimpan, ditandai ditolak) |
| S | Lewati: gestur **tidak terbentuk** / pasien tidak mampu |
| N | Tulis catatan untuk percobaan ini (ENTER simpan, ESC batal) |
| Q / ESC dua kali | Keluar; data yang sudah ada tetap tersimpan |

Jika deteksi di layar tinjau di bawah 80%, pertimbangkan R. Hentikan kapan saja bila pasien lelah (Q dua kali).

## Hasil

```
data\stage1\participants.csv              satu baris per sesi (kode, usia, JK, dominan, sisi, kelayakan)
data\stage1\P01\P01_S1_<tanggal>_<jam>\
    lembar_tahap1.html   Lembar 1 terisi: buka di browser, Ctrl+P untuk cetak/PDF
    session.json         metadata sesi (kamera, MediaPipe, versi kode, cek privasi)
    frames.csv           landmark mentah semua frame (±60 per percobaan)
    trials.csv           daftar percobaan, termasuk yang diulang/dilewati
    videos\              satu video per percobaan
```

Folder `data\` berisi data pasien: **jangan** di-commit ke git atau dibagikan di luar tim penelitian.
Simpan maksimal 1 tahun setelah penelitian selesai, sesuai formulir etik.
Bagian VI lembar (sampling 5 FPS, data dibuang, record valid) diisi oleh skrip ekspor.
