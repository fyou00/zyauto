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

---

# PLAN (bagian baru): Layanan AE, langkah 2-4

Status: rencana disetujui, kode BELUM dikerjakan.

## Layanan
- `topaz_only`: upload -> validasi -> Topaz -> done.
- `topaz_cc`: upload -> validasi -> Topaz -> AE (aerender + preset CC) -> encode akhir -> done.
- Satu order = satu job. Worker memproses SATU job dari awal sampai akhir (semua tahap) sebelum claim job berikutnya. Job berikutnya, termasuk topaz_only, menunggu job sebelumnya done/failed.
- Tahap AE gagal -> job failed (refund kuota nanti, belum sekarang), job berikutnya lanjut.
- FAKE_AE=1 untuk Mac: tahap AE cuma menyalin file setelah FAKE_AE_DELAY_SEC.

## Keputusan yang BELUM DIPUTUSKAN (tanya user, jangan menebak)
1. Nama dan daftar preset CC awal untuk `CC_PRESETS` di config.py (nama bebas atau nama file .aep/.ffx?).
2. Tanpa pilihan layanan: default rencana = tolak 400 "Pilih layanan (topaz_only atau topaz_cc)". Menunggu konfirmasi.
3. Toggle dropdown preset: default rencana = HTMX murni (route fragment kecil), tanpa JS inline. Menunggu konfirmasi.
4. Encode akhir setelah AE: apakah perlu ffmpeg lagi, atau output AE langsung final? Menentukan apakah stage `encoding` punya kerja nyata.
5. Catatan konflik dokumen: `.clinerules` masih melarang After Effects dan NOTES.md belum punya bagian "Layanan AE". Keduanya perlu diperbarui saat langkah 2 dimulai (izin user dulu).

## Langkah 2 - DB: kolom baru + migrasi
- `app/db.py`: tambah kolom `service` (TEXT NOT NULL DEFAULT 'topaz_only', CHECK topaz_only|topaz_cc), `cc_preset` (TEXT NULL), `stage` (TEXT NULL: topaz|ae|encoding), `intermediate_path` (TEXT NULL). Migrasi: daftar `ALTER TABLE jobs ADD COLUMN` di `init_db()`, dilewati jika kolom sudah ada (cek `PRAGMA table_info`). Tambah `set_stage()`, `set_intermediate_path()`; `create_job()` terima `service` dan `cc_preset`. Status tetap queued -> processing -> done/failed.
- `app/config.py`: tambah `CC_PRESETS`, `FAKE_AE_DELAY_SEC`, `INTERMEDIATE_DIR`, placeholder `AE_*` (path aerender, project) dibaca dari .env, tanpa nilai tebakan.
- `app/main.py`: pemanggilan `create_job()` menyesuaikan signature baru (service default sementara).
- Commit: `feat: kolom service, cc_preset, stage, intermediate_path dan migrasi db`
- Tes Mac: salin DB lama ke /tmp, `init_db()` dua kali -> kolom ada, tidak error (idempoten); baris lama terbaca dengan service='topaz_only'; CHECK menolak service tidak valid.
- Tes Windows (nanti): jalankan di DB Windows yang sudah berisi job; semua baris lama tetap terbaca.

## Langkah 3 - UI (HTMX, tanpa CSS)
- `app/templates/index.html`: radio layanan (tanpa default terpilih), area `#preset-area` yang diisi via HTMX hanya untuk topaz_cc.
- `app/templates/_preset.html` (baru): fragment dropdown preset, daftar dari `config.CC_PRESETS` (bukan hardcode di template).
- `app/templates/_jobs.html`: tambah kolom Layanan dan Tahap (stage, "-" jika null).
- `app/main.py`: route fragment preset; POST /jobs menerima `service` dan `cc_preset`. Validasi: service kosong/tidak dikenal -> 400; topaz_cc tanpa preset -> 400; preset tidak ada di `CC_PRESETS` -> 400; topaz_only mengabaikan preset. Jinja autoescape tetap aktif.
- Commit: `feat: form pilih layanan, dropdown preset CC, kolom layanan dan tahap`
- Tes Mac: curl POST untuk tiap kasus validasi (tanpa service, topaz_cc tanpa preset, preset palsu, topaz_only, topaz_cc valid) + cek baris DB; GET /jobs menampilkan kolom baru; tidak ada `<style>` atau file css.
- Tes Windows (nanti): dropdown menampilkan preset sesuai config di mesin itu.

## Langkah 4 - Worker bertahap
- `app/ae.py` (baru): `AEError`, `run_ae(input, output, preset, timeout)`, mode FAKE_AE=1 menjalankan `app/fake_ae.py`; mode asli memanggil aerender (list argumen, sys.executable untuk skrip Python), kosong konfigurasi -> `AEError("AE belum dikonfigurasi, kosong: ...")`.
- `app/fake_ae.py` (baru): salin file setelah delay.
- `app/topaz.py`: `_start`/`_kill_tree` dipakai bersama oleh topaz dan ae (kill pohon proses yang sudah ada), perilaku Topaz tidak berubah. Pilih cara paling kecil: impor dari topaz.py atau file util baru.
- `app/worker.py`: `process_job()` jadi pipeline: set_stage('topaz') -> Topaz; jika topaz_cc: simpan intermediate_path, set_stage('ae') -> AE, set_stage('encoding') -> encode/simpan (isi tergantung keputusan 4); mark_done; stage dikosongkan. Hapus file perantara saat selesai ATAU gagal. Log berstempel waktu per tahap. Timeout per tahap lewat kill pohon proses.
- `app/db.py`: `mark_done`/`mark_failed` mengosongkan stage.
- `tests_queue.py` (baru, skrip Python biasa, bukan pytest karena pytest tidak ada di requirements): lihat test case di bawah.
- Commit: `feat: worker pipeline bertahap topaz -> ae -> done dengan FAKE_AE`
- Tes Mac: `FAKE_TOPAZ=1 FAKE_AE=1 python -m app.worker`; job topaz_cc selesai, stage berganti, intermediate terhapus; tahap AE dibuat gagal (output tidak ada / timeout kecil) -> job failed, intermediate terhapus, worker hidup.
- Tes Windows (nanti): aerender asli, preset CC asli, kill pohon proses saat timeout AE (cek tidak ada aerender/ffmpeg yatim di Task Manager).

## Test case aturan antrian (FAKE mode)
- Order 1 = topaz_cc, order 2 = topaz_only, keduanya queued sebelum worker jalan. FAKE_TOPAZ_DELAY_SEC=3, FAKE_AE_DELAY_SEC=3, DB sementara di /tmp (DB asli tidak disentuh).
- Log worker berstempel waktu: `job <id> processing`, `stage topaz start/end`, `stage ae start/end`, `done/failed`.
- Bukti: `started_at` job 2 >= `finished_at` job 1 (sudah mencakup akhir tahap AE job 1). Skrip membaca log dan DB lalu assert.
- Kasus tambahan: AE job 1 dipaksa gagal -> job 1 failed, job 2 tetap jalan dan done setelah job 1 selesai.
- Hasil log disalin ke catatan sesi NOTES.md.

## Urutan dan commit
- Langkah 2 -> 3 -> 4, satu commit per langkah, hanya setelah tes lulus.
- Tidak ada git push, reset, rebase, atau clean.
- NOTES.md diperbarui di akhir tiap langkah.

## Revisi keputusan (disetujui user, menggantikan butir terkait di atas)
- Preset CC dipisah jadi tiga bagian di config.py. `CC_PRESETS` berisi list dict: `id` (stabil, pola huruf kecil/angka/underscore, mis. soft_fresh), `label` (teks di UI, mis. "CC Soft Fresh"), `aep_path` (Path ke template .aep, satu .aep per preset untuk MVP). Nama di UI bisa diganti tanpa mengubah file.
- Isi awal `CC_PRESETS` kosong. Nama preset dan file .aep belum diberikan user, tidak ada tebakan.
- Validasi server tetap wajib: `cc_preset` harus berupa id yang ada di config. Dropdown hanya tampilan.
- Alur topaz_cc: Topaz -> AE render ke QuickTime (.mov) -> HandBrakeCLI encode ke .mp4 -> done. Tahap encoding memakai HandBrakeCLI, bukan ffmpeg.
- Setting encode: file preset HandBrake (.json) hasil export aplikasi HandBrake, disimpan di `presets/`. Worker memakai `--preset-import-file <file>` dan `-Z "<nama preset>"`. Preset wajib memakai encoder NVENC. Jika tidak, tahap encoding dianggap belum siap (job failed dengan pesan jelas).
- Config baru (.env): HANDBRAKE_CLI_PATH, HANDBRAKE_PRESET_FILE, HANDBRAKE_PRESET_NAME. Jika kosong dan FAKE_AE=0, job failed dengan pesan "HandBrake belum dikonfigurasi, kosong: ..." (tanpa path lokal di pesan).
- topaz_only tidak di-encode ulang. Hasil Topaz langsung jadi file download.
- Timeout tahap HandBrake memakai kill_process_tree yang sama dengan tahap lain.
- Mode fake: FAKE_HANDBRAKE=1 untuk tes di Mac, menyalin file dengan delay FAKE_HANDBRAKE_DELAY_SEC (baru di config.py).
- FAKE_AE=1 wajib saat dev di Mac (aturan baru di .clinerules).
- HandBrakeCLI adalah binary eksternal, bukan library Python. Tidak masuk requirements.txt.
- Dampak ke langkah: langkah 3 hanya menyesuaikan dropdown ke id dan label. Langkah 4 menambah `app/handbrake.py` (pola sama dengan topaz.py dan ae.py) dan `app/fake_handbrake.py`. Tahap `encoding` di DB berarti HandBrake.

## Langkah 1 - (placeholder, kosong)
Belum diisi. Akan ditulis setelah keputusan user. Tes: Windows langsung (AE asli).

## Langkah 5 - (placeholder, kosong)
Belum diisi. Akan ditulis setelah keputusan user. Tes: Windows langsung (AE asli).

## Langkah 6 - (placeholder, kosong)
Belum diisi. Akan ditulis setelah keputusan user. Tes: Windows langsung (AE asli).

## Langkah 7 - (placeholder, kosong)
Belum diisi. Akan ditulis setelah keputusan user. Tes: Windows langsung (AE asli).

## Tes AE asli di Windows (diperbarui)
Status: BELUM bisa dijalankan. Menunggu keputusan "cara input hasil Topaz masuk ke comp" dan implementasi `_run_aerender` di app/ae.py (saat ini sengaja berhenti dengan pesan "AE asli belum siap").

### Prasyarat
- After Effects terpasang, sudah pernah dibuka sekali (lisensi aktif). Catat versi AE.
- Project template `.aep` berisi satu comp dengan layer footage pengganti. Nama comp dicatat persis.
- Template output module QuickTime dibuat di AE (menu Output Module Templates). Nama template dicatat persis.

### Langkah tes (urutan wajib)
1. Baca opsi yang didukung versi AE ini: `& "C:\Program Files\Adobe\Adobe After Effects <versi>\Support Files\aerender.exe" -help`. Opsi yang dipakai di kode harus sesuai output ini (tidak dari ingatan atau dokumentasi lama).
2. Render manual dari PowerShell dengan opsi dari langkah 1 (project, comp, output .mov, output module). Harapan: file .mov terbentuk. Catat durasi dan ukuran file.
3. Isi `.env`: `FAKE_AE=0`, `AE_AERENDER_PATH`, `AE_COMP_NAME`, `AE_OM_TEMPLATE`. Lalu cek dengan `python -c` seperti di TESTING_WINDOWS.md (bagian A).
4. Tes gagal dulu: `AE_AERENDER_PATH` diisi path salah. Harapan: job `topaz_cc` failed dengan pesan "AE tidak bisa dijalankan", worker tetap hidup.
5. Tes sukses: upload `topaz_cc` dengan video pendek. Harapan di log worker: `stage ae start`, `stage ae end`, lalu `stage encoding start/end` (HandBrake), `done`. Simpan log lengkap.
6. Tes timeout AE: turunkan batas waktu sementara (satu kali, lalu kembalikan). Harapan: job failed dengan pesan timeout, dan tidak ada `aerender.exe` yang masih berjalan di Task Manager.
7. Catat waktu tahap AE dari log untuk mengisi masalah terbuka "waktu proses AE belum diukur".

### Path file .aep
- Keputusan (disetujui user): `AE_PRESET_DIR` dari `.env`; kosong -> `BASE_DIR / "presets"`.
- `aep_path` per preset = `AE_PRESET_DIR / "<nama_file>.aep"` (pathlib).
- `presets/` ada di `.gitignore` (berlaku untuk fallback). File .aep tidak di-commit; yang di-commit hanya daftar preset di config.py.
- `_run_aerender`: `-project` diisi dari `aep_path`. Jika file tidak ada -> job failed dengan pesan jelas, bukan crash.
- `FAKE_AE=1` tidak membaca file .aep sama sekali.
- Status: aturan path dan alur input diimplementasikan dan dites di Mac (path 10/10, input AE 23/23 dengan ffprobe + aerender palsu).
- Input ke comp (Opsi A, disetujui user): worker menyalin hasil Topaz ke `AE_WORK_DIR/input<ext>` sebelum aerender; .aep tidak diubah (template wajib punya footage placeholder bernama `input`). `AE_WORK_DIR` dibuat otomatis dan input lama dihapus dulu.
- `-s 0 -e <durasi>`: durasi dibaca ffprobe (folder yang sama dengan `TOPAZ_FFMPEG_PATH`); nilai = durasi bulat - 1, minimal 0.
- Orientasi: ffprobe memilih `<preset>.aep` (landscape) atau `<preset>_portrait.aep` (portrait). Orientasi tidak terbaca -> landscape (hanya peringatan di log). Portrait tanpa file -> job failed.
