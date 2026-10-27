"""
stage1_report.py
================
Membuat lembar HTML terisi yang mengikuti susunan Lembar Pengumpul Data 1
(bagian I, II, III; bagian VI diisi setelah skrip ekspor).

Buka file di browser lalu Ctrl+P untuk mencetak atau menyimpan sebagai PDF.
Nama/inisial diambil dari kunci_identitas.csv (bila ada); No. RM dibiarkan kosong
untuk ditulis tangan. File HTML ini memuat nama: perlakukan seperti lembar kertas.

    python code\\stage1_report.py data\\stage1\\P01\\<session_id>
"""

import csv
import html
import json
import os
import sys

from stage1_form import EXCLUSION_CRITERIA, INCLUSION_CRITERIA

GESTURE_TITLES = {"palm": "Palm", "fist": "Fist", "grabbing": "Grabbing", "thumb_index": "Thumb_index"}
REPORT_NAME = "lembar_tahap1.html"


def _box(checked):
    return "&#9746;" if checked else "&#9744;"   # kotak bersilang / kotak kosong


def final_trials(trials, protocol):
    """
    Satu baris per (gestur, ulangan) sesuai urutan protokol: keputusan terakhir yang
    berlaku (accepted/skipped), serta jumlah percobaan ulang sebelumnya.
    """
    by_trial = {}
    for t in trials:
        by_trial.setdefault(t["trial_id"], []).append(t)
    rows = []
    for no, (gesture, rep) in enumerate(protocol, start=1):
        tid = f"{gesture}_r{rep}"
        attempts = by_trial.get(tid, [])
        final = next((a for a in reversed(attempts) if a["decision"] in ("accepted", "skipped")), None)
        rows.append({
            "no": no, "gesture": gesture, "rep": rep, "final": final,
            "n_redo": sum(1 for a in attempts if a["decision"] == "redo"),
            "n_attempts": len(attempts),
        })
    return rows


def render(meta, trials, identity=None):
    info = meta.get("participant_info", {})
    nama = (identity or {}).get("nama", "")
    crit = info.get("kriteria", {})
    proto = meta.get("protocol", {})
    order = proto.get("gestures_in_order", ["palm", "fist", "grabbing", "thumb_index"])
    reps = int(proto.get("repetitions_per_gesture", 5))
    protocol = [(g, r) for g in order for r in range(1, reps + 1)]
    rows = final_trials(trials, protocol)
    e = lambda x: html.escape(str(x if x is not None else ""))

    def yn(key, value):
        return f"{_box(value == 'ya')} Ya &nbsp; {_box(value == 'tidak')} Tidak"

    trial_rows = []
    for r in rows:
        f = r["final"]
        formed = f["gesture_formed"] if f else ""
        form = f["gesture_form"] if f else ""
        video = f["video_file"].replace("\\", "/").split("/")[-1] if f and f.get("video_file") else ""
        notes = []
        if f and f.get("note"):
            notes.append(e(f["note"]))
        if r["n_redo"]:
            notes.append(f"diulang {r['n_redo']}x")
        if f and f["decision"] == "accepted":
            notes.append(f"deteksi {float(f['detection_rate']) * 100:.0f}%, {float(f['effective_fps']):.0f} FPS")
        if not f:
            notes.append("belum direkam")
        trial_rows.append(
            f"<tr><td>{r['no']}</td><td>{GESTURE_TITLES[r['gesture']]}</td><td>{r['rep']}</td>"
            f"<td>{_box(formed == 'ya')} Ya {_box(formed == 'tidak')} Tidak</td>"
            f"<td>{_box(form == 'penuh')} Penuh {_box(form == 'sebagian')} Sebagian</td>"
            f"<td class='mono'>{e(video)}</td><td>{'; '.join(notes)}</td></tr>")

    inc_rows = "".join(f"<tr><td>{e(label)}</td><td>{yn(k, crit.get(k))}</td></tr>" for k, label in INCLUSION_CRITERIA)
    exc_rows = "".join(f"<tr><td>{e(label)}</td><td>{yn(k, crit.get(k))}</td></tr>" for k, label in EXCLUSION_CRITERIA)
    eligible = info.get("memenuhi_syarat") == "memenuhi"
    n_ok = sum(1 for r in rows if r["final"] and r["final"]["decision"] == "accepted")

    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8">
<title>Lembar Pengumpul Data 1 - {e(meta.get('participant'))}</title>
<style>
  body {{ font-family: "Segoe UI", Arial, sans-serif; font-size: 12px; color: #111; margin: 24px; }}
  h1 {{ font-size: 16px; margin: 0 0 2px; }} h2 {{ font-size: 13px; margin: 18px 0 6px; }}
  .sub {{ color: #444; margin-bottom: 12px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td, th {{ border: 1px solid #999; padding: 4px 6px; vertical-align: top; }}
  th {{ background: #eee; text-align: left; }}
  .blank {{ display: inline-block; min-width: 220px; border-bottom: 1px solid #000; height: 14px; }}
  .mono {{ font-family: Consolas, monospace; font-size: 11px; }}
  .note {{ color: #555; font-size: 11px; }}
  .sign td {{ border: none; padding-top: 40px; width: 50%; }}
  @media print {{ body {{ margin: 10mm; }} h2 {{ page-break-after: avoid; }} tr {{ page-break-inside: avoid; }} }}
</style></head><body>
<h1>LEMBAR PENGUMPUL DATA 1</h1>
<div class="sub">Data Gestur Tangan untuk Training-Validation-Testing Model GRU (Tahap 1)<br>
Sesi <span class="mono">{e(meta.get('session_id'))}</span> &middot; versi kode <span class="mono">{e(meta.get('git_commit'))}</span></div>

<h2>I. Identitas Partisipan</h2>
<table>
<tr><th style="width:28%">Kode partisipan</th><td>{e(info.get('participant'))}</td>
    <th style="width:22%">Tanggal pengambilan data</th><td>{e(info.get('tanggal'))}</td></tr>
<tr><th>Nama/inisial *</th><td>{e(nama) if nama else '<span class="blank"></span>'}</td><th>No. rekam medis *</th><td><span class="blank"></span></td></tr>
<tr><th>Usia</th><td>{e(info.get('usia'))} tahun</td><th>Jenis kelamin</th>
    <td>{_box(info.get('jenis_kelamin') == 'laki-laki')} Laki-laki &nbsp; {_box(info.get('jenis_kelamin') == 'perempuan')} Perempuan</td></tr>
<tr><th>Tangan dominan (sebelum sakit)</th>
    <td>{_box(info.get('tangan_dominan') == 'kanan')} Kanan &nbsp; {_box(info.get('tangan_dominan') == 'kiri')} Kiri</td>
    <th>Sisi paretik</th>
    <td>{_box(info.get('sisi_paretik') == 'kanan')} Kanan &nbsp; {_box(info.get('sisi_paretik') == 'kiri')} Kiri</td></tr>
</table>
<div class="note">* Ditulis tangan; hanya dicatat pada lembar ini untuk keperluan penghubung, tidak dimasukkan ke data olahan.</div>

<h2>II. Pemeriksaan Kelayakan</h2>
<table><tr><th>Kriteria inklusi</th><th style="width:20%">Jawaban</th></tr>{inc_rows}
<tr><th>Kriteria eksklusi (jawaban &ldquo;Ya&rdquo; = tidak dapat ikut serta)</th><th></th></tr>{exc_rows}
<tr><th>Kesimpulan kelayakan</th><td>{_box(eligible)} Memenuhi syarat, lanjut Tahap 1<br>{_box(not eligible)} Tidak memenuhi syarat</td></tr>
<tr><th>Informed consent ditandatangani</th><td>{_box(info.get('consent') == 'ya')} Ya {_box(info.get('consent') == 'tidak')} Tidak &nbsp; Tanggal: {e(info.get('consent_tanggal'))}</td></tr>
<tr><th>Diperiksa oleh (nama &amp; paraf dokter)</th><td>{e(info.get('diperiksa_oleh'))} &nbsp; <span class="blank" style="min-width:90px"></span></td></tr>
</table>

<h2>III. Perekaman Gestur (4 gestur &times; 5 pengulangan; setiap gestur ditahan &plusmn;2 detik)</h2>
<table><tr><th>No</th><th>Gestur</th><th>Ulangan ke-</th><th>Terbentuk &amp; ditahan &plusmn;2 detik</th>
<th>Bentuk gestur</th><th>Nama berkas video</th><th>Catatan</th></tr>
{''.join(trial_rows)}
</table>
<div class="note">Diterima {n_ok} dari {len(rows)} percobaan. Sesi berakhir: {e(meta.get('end_reason'))}.</div>

<h2>VI. Pasca-pemrosesan Data</h2>
<div class="note">Diisi otomatis oleh skrip ekspor (sampling 5 FPS dan pemeriksaan kualitas) pada tahap berikutnya.</div>

<table class="sign"><tr><td>Peneliti,<br><br><br>(Salsabila Ikasyah Ramadhani)</td>
<td>Dokter/tenaga rehabilitasi pendamping,<br><br><br>(______________________________)</td></tr></table>
</body></html>"""


PRINT_DIR = "lembar_cetak"


def write_report(session_dir, identity_root=None):
    """
    Tulis lembar_tahap1.html TANPA nama di folder sesi (aman dibagikan bersama
    data). Jika nama ada di kunci identitas, tulis juga lembar bernama untuk dicetak
    di <identity_root>/lembar_cetak/<session_id>.html (di luar folder sesi).
    Mengembalikan path lembar yang sebaiknya dicetak.
    """
    with open(os.path.join(session_dir, "session.json"), encoding="utf-8") as f:
        meta = json.load(f)
    with open(os.path.join(session_dir, "trials.csv"), newline="", encoding="utf-8") as f:
        trials = list(csv.DictReader(f))
    path = os.path.join(session_dir, REPORT_NAME)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(meta, trials, {}))
    if identity_root:
        from stage1_writer import load_identity
        identity = load_identity(identity_root, meta.get("session_id"))
        if identity.get("nama"):
            out_dir = os.path.join(identity_root, PRINT_DIR)
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, f"{meta.get('session_id')}.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(render(meta, trials, identity))
    return path

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    session_dir = sys.argv[1]
    root = os.path.dirname(os.path.dirname(os.path.abspath(session_dir)))
    print(write_report(session_dir, identity_root=root))
