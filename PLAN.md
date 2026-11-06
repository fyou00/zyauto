# PLAN: Prototype Upscaling Video (Topaz, mode FAKE_TOPAZ)

Lingkungan: macOS (dev sekarang), Python 3.11+. Target akhir: Windows (belum diuji).
Lingkup: langkah 1–6 dari NOTES.md. Langkah 7 (Topaz asli) tidak termasuk.

## Keputusan (disetujui user)
- Worker berjalan terus (loop), mengambil satu job per waktu. Setelah selesai lanjut ke job berikutnya.
- Retry: kolom `attempts`. Maksimal 2 kali percobaan. Recovery saat start: `processing` dengan `attempts < 2` kembali ke `queued`; jika tidak, `failed`.
- Timeout job: 25 menit (`JOB_TIMEOUT_SEC = 25 * 60` di config.py).
- Mode FAKE: `app/fake_topaz.py` dijalankan sebagai subprocess. Lama delay dari `FAKE_TOPAZ_DELAY_SEC` di config.py, agar timeout bisa diuji.
- HTMX: versi terbaru (2.x), file lokal `app/static/htmx.min.js`.
- `requirements.txt` dibuat: fastapi, uvicorn, jinja2, python-multipart.
- Validasi upload: hanya ekstensi (mp4, mov, mkv), tanpa cek isi.
- Nama unduhan: `upscaled_<nama asli yang sudah disanitasi>.<ext>`. Nama di disk tetap UUID.

## Skema tabel `jobs` (revisi: tambah `attempts`)
```sql
CREATE TABLE IF NOT EXISTS jobs (
  id            TEXT PRIMARY KEY,
  original_name TEXT NOT NULL,
  ext           TEXT NOT NULL CHECK (ext IN ('mp4','mov','mkv')),
  input_path    TEXT NOT NULL,
  output_path   TEXT,
  size_bytes    INTEGER NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('queued','processing','done','failed')),
  attempts      INTEGER NOT NULL DEFAULT 0,
  error         TEXT,
  created_at    TEXT NOT NULL,
  started_at    TEXT,
  finished_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);
```

## Struktur folder
```
zyauto/
├── .clinerules, .gitignore, NOTES.md, PLAN.md, requirements.txt
├── app/
│   ├── __init__.py       — penanda package
│   ├── config.py         — semua path & setting (termasuk placeholder TOPAZ_*)
│   ├── db.py             — sqlite3: init_db, create/list/get/claim/update job, recovery
│   ├── main.py           — FastAPI dan semua route
│   ├── topaz.py          — run_upscale(): FAKE_TOPAZ → subprocess fake_topaz; tanpa FAKE → failed
│   ├── fake_topaz.py     — salin input ke output setelah delay (dipanggil sebagai subprocess)
│   ├── worker.py         — loop worker, recovery saat start, timeout
│   ├── templates/index.html, _jobs.html
│   └── static/htmx.min.js
└── data/                 — (gitignored) uploads/, outputs/, app.sqlite
```

## Route
| Method | Path | Fungsi |
|---|---|---|
| GET | `/` | Halaman form upload + wadah daftar job |
| POST | `/jobs` | Validasi ekstensi & ukuran (stream, 413 jika lebih), simpan UUID, insert `queued`, redirect 303 |
| GET | `/jobs` | Partial `_jobs.html`, di-poll HTMX tiap 3 detik |
| GET | `/jobs/{id}/download` | File hasil jika `done`; selain itu 404 |

## Langkah (satu langkah = satu commit)

**Langkah 1 — struktur, config, db**
- File: `app/__init__.py`, `app/config.py`, `app/db.py`, `requirements.txt`, update NOTES.md
- Commit: `feat: struktur proyek, config, dan skema tabel jobs`
- Tes: `init_db()` membuat tabel `jobs` dengan kolom `attempts`; `git status` tidak menampilkan `data/`.

**Langkah 2 — upload form + validasi + job queued**
- File: `app/main.py`, `app/templates/index.html`, `app/db.py`
- Commit: `feat: upload form dan validasi file`
- Tes: upload mp4 → 303 dan baris `queued`; `.txt` → 400; file > `MAX_UPLOAD_BYTES` → 413 tanpa sisa file di `data/uploads/`; nama di disk berupa UUID.

**Langkah 3 — daftar job + HTMX polling**
- File: `app/main.py` (GET `/jobs`), `app/templates/_jobs.html`, `app/static/htmx.min.js`, update `index.html`
- Commit: `feat: daftar job dengan polling htmx`
- Tes: ubah status via python, browser berubah tanpa reload; Network menunjukkan `GET /jobs` tiap 3 detik; `<b>` pada nama file tampil sebagai teks.

**Langkah 4 — worker + mode FAKE_TOPAZ**
- File: `app/worker.py`, `app/topaz.py`, `app/fake_topaz.py`, `app/db.py` (claim atomic)
- Commit: `feat: worker dengan mode FAKE_TOPAZ`
- Tes: `FAKE_TOPAZ=1 python -m app.worker` → `queued` → `processing` → `done`, file ada di `data/outputs/`; dua job diproses berurutan; tanpa FAKE → `failed` dengan error "Topaz belum dikonfigurasi".

**Langkah 5 — download hasil**
- File: `app/main.py` (route download), `_jobs.html` (link hanya saat `done`)
- Commit: `feat: link download hasil`
- Tes: `curl -o` hasil sama dengan output (`cmp`); job `queued` → 404; ID tidak ada → 404; header nama file = `upscaled_<nama>.<ext>`.

**Langkah 6 — recovery dan timeout**
- File: `app/worker.py`, `app/db.py`, `app/config.py` (`JOB_TIMEOUT_SEC`)
- Commit: `fix: reset job processing saat worker start dan timeout job`
- Tes:
  - Set `processing` manual dengan `attempts=1` → worker start → `queued` lalu `done`.
  - Set `processing` dengan `attempts=2` → `failed`.
  - Timeout: set `JOB_TIMEOUT_SEC` kecil dan `FAKE_TOPAZ_DELAY_SEC` lebih besar → `failed` dengan error timeout. Untuk tes 25 menit yang asli, cukup pastikan nilai di config.py.

## Di luar lingkup
Langkah 7 (Topaz asli), login, kuota, payment, After Effects, CSS.

## Verifikasi akhir
Alur end-to-end dengan `FAKE_TOPAZ=1`, lalu update NOTES.md (centang 1–6, commit terakhir, keputusan baru).
