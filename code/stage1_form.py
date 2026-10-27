"""
stage1_form.py
==============
Formulir Lembar Pengumpul Data 1, bagian I (Identitas) dan II (Kelayakan).

Nama/inisial dan No. rekam medis TIDAK ditanyakan: sesuai catatan Lembar 1
("hanya dicatat pada lembar ini untuk keperluan penghubung; tidak dimasukkan
ke data olahan") dan formulir etik, keduanya hanya ditulis tangan di lembar.

Logika (validasi, kelayakan) dipisahkan dari tampilan tkinter agar bisa diuji.
"""

import re
from datetime import date

PARTICIPANT_PATTERN = re.compile(r"^P\d{2}$")

INCLUSION_CRITERIA = [  # Tabel 3.3 proposal / Lembar 1 bagian II
    ("inklusi_stroke", "Terdiagnosis stroke dengan gangguan motorik ekstremitas atas"),
    ("inklusi_mmt", "MMT grade 3 pada sisi paretik"),
    ("inklusi_mas", "MAS ≤2 pada sisi paretik"),
    ("inklusi_komunikasi", "Mampu berkomunikasi dan mengikuti instruksi sederhana"),
    ("inklusi_mampu", "Mampu mengikuti rangkaian pengambilan data dan pengujian sistem"),
    ("inklusi_bersedia", "Bersedia menjadi partisipan dan menandatangani informed consent"),
]
EXCLUSION_CRITERIA = [  # Tabel 3.4 proposal / Lembar 1 bagian II
    ("eksklusi_kognitif", "Gangguan kognitif atau komunikasi berat sehingga tidak dapat mengikuti instruksi"),
    ("eksklusi_penglihatan", "Gangguan penglihatan yang menghambat interaksi dengan sistem"),
    ("eksklusi_medis", "Kondisi medis/keluhan yang tidak memungkinkan mengikuti penelitian "
                       "(termasuk tanda vital tidak stabil)"),
]

FIELD_LABELS = {
    "participant": "Kode partisipan",
    "tanggal": "Tanggal pengambilan data",
    "usia": "Usia",
    "jenis_kelamin": "Jenis kelamin",
    "tangan_dominan": "Tangan dominan (sebelum sakit)",
    "sisi_paretik": "Sisi paretik",
    "consent": "Informed consent ditandatangani",
    "consent_tanggal": "Tanggal informed consent",
    "diperiksa_oleh": "Diperiksa oleh (dokter)",
}


def evaluate_eligibility(answers):
    """
    answers: dict kunci kriteria -> 'ya' | 'tidak' | None.
    Mengembalikan (status, alasan) dengan status 'memenuhi' | 'tidak_memenuhi' | 'belum_lengkap'.
    Memenuhi = semua inklusi 'ya' dan semua eksklusi 'tidak' (Lembar 1: eksklusi "Ya" = tidak dapat ikut).
    """
    missing = [k for k, _ in INCLUSION_CRITERIA + EXCLUSION_CRITERIA if answers.get(k) not in ("ya", "tidak")]
    if missing:
        return "belum_lengkap", f"{len(missing)} kriteria belum dijawab"
    failed_inc = [label for k, label in INCLUSION_CRITERIA if answers[k] != "ya"]
    hit_exc = [label for k, label in EXCLUSION_CRITERIA if answers[k] == "ya"]
    if failed_inc or hit_exc:
        reasons = [f"inklusi tidak terpenuhi: {x}" for x in failed_inc] + [f"eksklusi: {x}" for x in hit_exc]
        return "tidak_memenuhi", "; ".join(reasons)
    return "memenuhi", ""


def _parse_date(text):
    try:
        return date.fromisoformat(text.strip())
    except (ValueError, AttributeError):
        return None


def validate_form(values, today=None):
    """
    values: dict dari formulir (semua string). Mengembalikan (info, errors).
    info berisi nilai yang sudah dinormalisasi; errors = daftar pesan.
    Sesi hanya boleh dimulai bila errors kosong.
    """
    today = today or date.today()
    errors, info = [], {}

    code = (values.get("participant") or "").strip().upper()
    if not PARTICIPANT_PATTERN.match(code):
        errors.append("Kode partisipan harus berformat P01-P99 (bukan nama atau No. RM).")
    info["participant"] = code

    d = _parse_date(values.get("tanggal", ""))
    if d is None:
        errors.append("Tanggal pengambilan data harus berformat YYYY-MM-DD.")
    elif d > today:
        errors.append("Tanggal pengambilan data tidak boleh di masa depan.")
    info["tanggal"] = d.isoformat() if d else ""

    usia_txt = (values.get("usia") or "").strip()
    # Hanya pemeriksaan salah ketik; proposal tidak menetapkan kriteria usia.
    if not usia_txt.isdigit() or not (1 <= int(usia_txt) <= 120):
        errors.append("Usia harus berupa angka tahun (1-120).")
    info["usia"] = usia_txt

    for key, allowed in (("jenis_kelamin", ("laki-laki", "perempuan")),
                         ("tangan_dominan", ("kanan", "kiri")),
                         ("sisi_paretik", ("kanan", "kiri"))):
        v = values.get(key) or ""
        if v not in allowed:
            errors.append(f"{FIELD_LABELS[key]} belum dipilih.")
        info[key] = v

    answers = {k: values.get(k) for k, _ in INCLUSION_CRITERIA + EXCLUSION_CRITERIA}
    status, reason = evaluate_eligibility(answers)
    info["kriteria"] = answers
    info["memenuhi_syarat"] = status
    if status == "belum_lengkap":
        errors.append(f"Pemeriksaan kelayakan: {reason}.")
    elif status == "tidak_memenuhi":
        errors.append(f"Partisipan tidak memenuhi syarat ({reason}). Perekaman tidak boleh dimulai.")

    consent = values.get("consent") or ""
    info["consent"] = consent
    if consent != "ya":
        errors.append("Informed consent harus sudah ditandatangani sebelum perekaman.")
    cd = _parse_date(values.get("consent_tanggal", ""))
    info["consent_tanggal"] = cd.isoformat() if cd else ""
    if consent == "ya":
        if cd is None:
            errors.append("Tanggal informed consent harus berformat YYYY-MM-DD.")
        elif d is not None and cd > d:
            errors.append("Tanggal informed consent tidak boleh setelah tanggal pengambilan data.")

    pemeriksa = (values.get("diperiksa_oleh") or "").strip()
    if not pemeriksa:
        errors.append("Nama dokter pemeriksa kelayakan harus diisi.")
    info["diperiksa_oleh"] = pemeriksa

    info["simpan_video"] = bool(values.get("simpan_video", True))
    cam = str(values.get("camera", "0")).strip()
    if not cam.isdigit():
        errors.append("Indeks kamera harus angka (biasanya 0 atau 1).")
    info["camera"] = int(cam) if cam.isdigit() else 0
    return info, errors


# ---------------------------------------------------------------------------
# Tampilan tkinter
# ---------------------------------------------------------------------------
def ask_participant_info(existing_sessions_fn=None, today=None):
    """
    Tampilkan formulir. Mengembalikan dict info (lihat validate_form) atau None bila dibatalkan.
    existing_sessions_fn(code) -> daftar sesi lama untuk peringatan duplikasi.
    """
    import tkinter as tk
    from tkinter import messagebox, ttk

    today = today or date.today()
    root = tk.Tk()
    root.title("Lembar Pengumpul Data 1 - Tahap 1")
    root.geometry("860x760")
    root.minsize(760, 600)
    style = ttk.Style(root)
    try:
        style.theme_use("vista" if "vista" in style.theme_names() else "clam")
    except tk.TclError:
        pass
    style.configure("Head.TLabel", font=("Segoe UI", 13, "bold"))
    style.configure("Note.TLabel", foreground="#666666", font=("Segoe UI", 9))
    style.configure("Err.TLabel", foreground="#b00020", font=("Segoe UI", 9))
    style.configure("Ok.TLabel", foreground="#1b7f3b", font=("Segoe UI", 10, "bold"))
    style.configure("Bad.TLabel", foreground="#b00020", font=("Segoe UI", 10, "bold"))

    # --- area gulir -------------------------------------------------------
    outer = ttk.Frame(root)
    outer.pack(fill="both", expand=True)
    canvas = tk.Canvas(outer, highlightthickness=0)
    sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    body = ttk.Frame(canvas, padding=16)
    body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    win = canvas.create_window((0, 0), window=body, anchor="nw")
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

    v = {
        "participant": tk.StringVar(), "tanggal": tk.StringVar(value=today.isoformat()),
        "usia": tk.StringVar(), "jenis_kelamin": tk.StringVar(), "tangan_dominan": tk.StringVar(),
        "sisi_paretik": tk.StringVar(), "consent": tk.StringVar(),
        "consent_tanggal": tk.StringVar(value=today.isoformat()), "diperiksa_oleh": tk.StringVar(),
        "camera": tk.StringVar(value="0"), "simpan_video": tk.BooleanVar(value=True),
    }
    for k, _ in INCLUSION_CRITERIA + EXCLUSION_CRITERIA:
        v[k] = tk.StringVar()

    def radio_row(parent, var, options, row, col):
        f = ttk.Frame(parent)
        f.grid(row=row, column=col, sticky="w", pady=3)
        for value, label in options:
            ttk.Radiobutton(f, text=label, value=value, variable=var).pack(side="left", padx=(0, 14))
        return f

    # --- I. Identitas -----------------------------------------------------
    ttk.Label(body, text="I. Identitas Partisipan", style="Head.TLabel").grid(row=0, column=0, columnspan=2,
                                                                          sticky="w", pady=(0, 6))
    sec1 = ttk.Frame(body)
    sec1.grid(row=1, column=0, columnspan=2, sticky="ew")
    sec1.columnconfigure(1, weight=1)
    r = 0
    ttk.Label(sec1, text="Kode partisipan").grid(row=r, column=0, sticky="w", padx=(0, 12), pady=3)
    codes = [f"P{i:02d}" for i in range(1, 16)] + ["P99"]
    cb = ttk.Combobox(sec1, textvariable=v["participant"], values=codes, width=8)
    cb.grid(row=r, column=1, sticky="w", pady=3)
    r += 1
    ttk.Label(sec1, text="P01-P15 untuk pasien, P99 untuk uji coba peneliti.", style="Note.TLabel").grid(
        row=r, column=1, sticky="w")
    r += 1
    ttk.Label(sec1, text="Tanggal pengambilan data").grid(row=r, column=0, sticky="w", padx=(0, 12), pady=3)
    ttk.Entry(sec1, textvariable=v["tanggal"], width=14).grid(row=r, column=1, sticky="w", pady=3)
    r += 1
    ttk.Label(sec1, text="Usia (tahun)").grid(row=r, column=0, sticky="w", padx=(0, 12), pady=3)
    ttk.Entry(sec1, textvariable=v["usia"], width=6).grid(row=r, column=1, sticky="w", pady=3)
    r += 1
    ttk.Label(sec1, text="Jenis kelamin").grid(row=r, column=0, sticky="w", padx=(0, 12))
    radio_row(sec1, v["jenis_kelamin"], [("laki-laki", "Laki-laki"), ("perempuan", "Perempuan")], r, 1)
    r += 1
    ttk.Label(sec1, text="Tangan dominan (sebelum sakit)").grid(row=r, column=0, sticky="w", padx=(0, 12))
    radio_row(sec1, v["tangan_dominan"], [("kanan", "Kanan"), ("kiri", "Kiri")], r, 1)
    r += 1
    ttk.Label(sec1, text="Sisi paretik (yang direkam)").grid(row=r, column=0, sticky="w", padx=(0, 12))
    radio_row(sec1, v["sisi_paretik"], [("kanan", "Kanan"), ("kiri", "Kiri")], r, 1)
    r += 1
    ttk.Label(sec1, text="Nama/inisial dan No. rekam medis ditulis tangan di lembar kertas saja; "
                         "tidak disimpan di aplikasi.", style="Note.TLabel").grid(
        row=r, column=0, columnspan=2, sticky="w", pady=(4, 0))

    # --- II. Kelayakan ----------------------------------------------------
    ttk.Separator(body).grid(row=2, column=0, columnspan=2, sticky="ew", pady=12)
    ttk.Label(body, text="II. Pemeriksaan Kelayakan", style="Head.TLabel").grid(row=3, column=0, columnspan=2,
                                                                             sticky="w", pady=(0, 6))
    sec2 = ttk.Frame(body)
    sec2.grid(row=4, column=0, columnspan=2, sticky="ew")
    sec2.columnconfigure(0, weight=1)
    r = 0
    ttk.Label(sec2, text="Kriteria inklusi", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="w")
    r += 1
    for k, label in INCLUSION_CRITERIA:
        ttk.Label(sec2, text=label, wraplength=520).grid(row=r, column=0, sticky="w", pady=2)
        radio_row(sec2, v[k], [("ya", "Ya"), ("tidak", "Tidak")], r, 1)
        r += 1
    ttk.Label(sec2, text='Kriteria eksklusi (jawaban "Ya" = tidak dapat ikut serta)',
              font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="w", pady=(8, 0))
    r += 1
    for k, label in EXCLUSION_CRITERIA:
        ttk.Label(sec2, text=label, wraplength=520).grid(row=r, column=0, sticky="w", pady=2)
        radio_row(sec2, v[k], [("ya", "Ya"), ("tidak", "Tidak")], r, 1)
        r += 1
    elig_label = ttk.Label(sec2, text="")
    elig_label.grid(row=r, column=0, columnspan=2, sticky="w", pady=(8, 4))
    r += 1

    sec3 = ttk.Frame(body)
    sec3.grid(row=5, column=0, columnspan=2, sticky="ew")
    ttk.Label(sec3, text="Informed consent ditandatangani").grid(row=0, column=0, sticky="w", padx=(0, 12))
    radio_row(sec3, v["consent"], [("ya", "Ya"), ("tidak", "Tidak")], 0, 1)
    ttk.Label(sec3, text="Tanggal consent").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=3)
    ttk.Entry(sec3, textvariable=v["consent_tanggal"], width=14).grid(row=1, column=1, sticky="w", pady=3)
    ttk.Label(sec3, text="Diperiksa oleh (nama dokter)").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=3)
    ttk.Entry(sec3, textvariable=v["diperiksa_oleh"], width=40).grid(row=2, column=1, sticky="w", pady=3)

    # --- Pengaturan -------------------------------------------------------
    ttk.Separator(body).grid(row=6, column=0, columnspan=2, sticky="ew", pady=12)
    sec4 = ttk.Frame(body)
    sec4.grid(row=7, column=0, columnspan=2, sticky="ew")
    ttk.Label(sec4, text="Indeks kamera").grid(row=0, column=0, sticky="w", padx=(0, 12))
    ttk.Entry(sec4, textvariable=v["camera"], width=4).grid(row=0, column=1, sticky="w")
    ttk.Checkbutton(sec4, text="Simpan video per percobaan (hanya area tangan)",
                    variable=v["simpan_video"]).grid(row=0, column=2, sticky="w", padx=(24, 0))

    err_label = ttk.Label(body, text="", style="Err.TLabel", wraplength=780, justify="left")
    err_label.grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 0))

    result = {"info": None}

    def collect():
        return {k: var.get() for k, var in v.items()}

    def refresh(*_):
        answers = {k: v[k].get() or None for k, _ in INCLUSION_CRITERIA + EXCLUSION_CRITERIA}
        status, reason = evaluate_eligibility(answers)
        if status == "memenuhi":
            elig_label.configure(text="Kesimpulan: Memenuhi syarat, lanjut Tahap 1", style="Ok.TLabel")
        elif status == "tidak_memenuhi":
            elig_label.configure(text=f"Kesimpulan: Tidak memenuhi syarat ({reason})", style="Bad.TLabel")
        else:
            elig_label.configure(text=f"Kesimpulan: belum lengkap ({reason})", style="Note.TLabel")

    for k, _ in INCLUSION_CRITERIA + EXCLUSION_CRITERIA:
        v[k].trace_add("write", refresh)
    refresh()

    def on_start():
        info, errors = validate_form(collect(), today=today)
        if errors:
            err_label.configure(text="\n".join(f"• {e}" for e in errors))
            return
        if existing_sessions_fn:
            old = existing_sessions_fn(info["participant"])
            if old and not messagebox.askyesno(
                    "Kode sudah dipakai",
                    f"{info['participant']} sudah memiliki {len(old)} sesi:\n" + "\n".join(old[-3:]) +
                    "\n\nLanjutkan sebagai sesi BARU untuk partisipan yang sama?"):
                return
        result["info"] = info
        root.destroy()

    def on_cancel():
        root.destroy()

    btns = ttk.Frame(root, padding=(16, 8))
    btns.pack(fill="x")
    ttk.Button(btns, text="Batal", command=on_cancel).pack(side="right")
    ttk.Button(btns, text="Mulai perekaman", command=on_start).pack(side="right", padx=8)
    root.protocol("WM_DELETE_WINDOW", on_cancel)
    cb.focus_set()
    root.mainloop()
    return result["info"]
