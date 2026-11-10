# NOTES:  Prototype Video Enhancement (Topaz, mode FAKE_TOPAZ)

## Tujuan prototype
Tujuannya untuk enchancement video dengan resolusi asli (original). Buktikan alur: upload video -> worker proses Topaz -> download hasil. Localhost, tanpa login, tanpa CSS.

## Status
- [x] 1. Struktur proyek + config.py + db.py (tabel jobs)
- [x] 2. Halaman upload + validasi file + simpan job (queued)
- [x] 3. Daftar job dengan HTMX polling
- [x] 4. Worker: ambil job, mode FAKE_TOPAZ, ubah status
- [x] 5. Download hasil
- [x] 6. Recovery: job 'processing' kembali 'queued' saat worker start; timeout job
- [x] 7. Integrasi Topaz asli (enhancement, tanpa upscaling). Kode selesai; tes Topaz asli di Windows: PENDING (user)

Commit terakhir: feat: worker pipeline bertahap topaz -> ae -> encoding dengan FAKE_AE dan HandBrake

## Layanan AE (rencana lengkap di PLAN.md, bagian "Layanan AE")
- [x] 2. DB: kolom service, cc_preset, stage, intermediate_path + migrasi
- [x] 3. UI: radio layanan, dropdown preset CC, kolom Layanan dan Tahap
- [x] 4. Worker bertahap topaz -> ae -> encode, FAKE_AE, tes aturan antrian
- [x] Kolom waktu render sementara untuk testing, dikontrol `SHOW_RENDER_TIME`
- [ ] 1, 5, 6, 7: placeholder kosong di PLAN.md (tes AE asli di Windows)

## Keputusan
- Stack: FastAPI + Jinja2 + HTMX, SQLite untuk jobs, tanpa Redis/Celery.
- Satu worker, satu job sekali jalan (hanya 1 GPU).
- Status job: queued -> processing -> done / failed.
- Format upload: mp4, mov, mkv. Batas ukuran di config.py (default 500 MB).
- Di luar prototype: login, kuota, payment, CSS. (After Effects sekarang masuk lewat bagian "Layanan AE"; .clinerules sudah diperbarui sesuai keputusan user.)
- Encoding akhir topaz_cc: AE render ke .mov (QuickTime), lalu HandBrakeCLI encode ke .mp4 dengan preset NVENC dari presets/. Bukan ffmpeg. topaz_only tidak di-encode ulang.
- Preset CC: id stabil + label UI + path .aep, di config.py. Dropdown hanya tampilan; server tetap memvalidasi id.
- Path .aep: `AE_PRESET_DIR` dari .env (kosong -> `BASE_DIR / "presets"`), `aep_path = AE_PRESET_DIR / "<file>.aep"` (pathlib, tanpa hardcode mesin). `presets/` di .gitignore; file .aep tidak di-commit, hanya daftar preset di config.py.
- `_run_aerender`: cek config dulu, lalu cek file .aep. Jika file tidak ada -> job failed "AE: file preset tidak ditemukan: <nama file>" (nama saja, tanpa path lokal), bukan crash. `-project` akan diisi `str(aep_path)`. FAKE_AE tidak membaca aep_path sama sekali.
- Langkah 3: radio layanan wajib (atribut `required`, tanpa default terpilih). Dropdown preset diisi HTMX lewat GET /ui/cc-presets?service=... (tanpa JS inline). Daftar preset berasal dari config.CC_PRESETS, template hanya loop.
- Validasi server di `validate_service()`: service kosong/tidak dikenal -> 400 "Pilih layanan (topaz_only atau topaz_cc)"; topaz_cc tanpa preset -> 400 "Pilih preset CC untuk layanan topaz_cc"; id preset tidak ada di config -> 400 "Preset tidak dikenal"; topaz_only mengabaikan cc_preset (disimpan NULL). Validasi dijalankan SEBELUM file disimpan, supaya tidak ada file yatim di data/uploads.
- Kolom tabel: Layanan dan Tahap (stage ditampilkan "-" jika NULL). CC_PRESETS tidak lagi dibaca dari .env.
- Layanan: topaz_only dan topaz_cc. Satu order = satu job. Worker memproses satu job penuh (termasuk seluruh tahap AE) sebelum job berikutnya; AE gagal -> job failed, job berikutnya lanjut.
- Skema (langkah 2): kolom baru service (default 'topaz_only', CHECK), cc_preset, stage (CHECK topaz|ae|encoding atau NULL), intermediate_path. Migrasi lewat ALTER TABLE ADD COLUMN di init_db(), dilewati jika kolom sudah ada; baris lama terbaca sebagai topaz_only.
- Daftar preset CC dibaca dari CC_PRESETS di .env (dipisah koma), default kosong. Nama preset belum diputuskan user, tidak diisi tebakan.
- Kolom waktu render hanya untuk testing: `SHOW_RENDER_TIME=1` menampilkan durasi total `started_at -> finished_at`; default mati, sehingga tidak dirender ke user saat deploy. Job processing menampilkan waktu berjalan; queued menampilkan `-`.
- Tidak ada kolom DB baru untuk waktu render. Durasi diformat sebagai `5m 12s` (atau `1h 2m 5s`) di route `/jobs`. Requeue worker tetap membuat durasi hanya mencerminkan percobaan terakhir.

- Tanpa pilihan layanan: ditolak (400), tidak ada default di server. Berlaku saat UI/route dikerjakan di langkah 3.
- File perantara disimpan di data/intermediates (INTERMEDIATE_DIR), dihapus saat job selesai atau gagal (langkah 4).
- Langkah 4 selesai (tes Mac, FAKE). Urutan tahap di log berstempel waktu: topaz -> ae -> encoding -> done. Job 2 baru processing setelah job 1 done/failed (`tests_queue.py`, skenario A dan B lulus).
- Keputusan: tahap AE asli SENGAJA berhenti dengan pesan "AE asli belum siap" sampai cara input hasil Topaz masuk ke comp diputuskan. Tanpa itu aerender bisa merender footage bawaan template dan hasilnya salah diam-diam.
- Keputusan: jalur FAKE Topaz/AE/HandBrake juga lewat `proc.run_real` (timeout membunuh seluruh pohon proses). Ditemukan saat tes: `subprocess.run(timeout=)` tidak membunuh anak proses.
- Keputusan: topaz_cc keluar sebagai `<job_id>.mp4` (dari HandBrake). topaz_only tetap ext asli. Nama unduhan mengikuti ext file.
- Keputusan: `FAKE_AE_FAIL=1` (di fake_ae.py) dipakai khusus tes antrian skenario B.
- Keputusan: `FAKE_AE` dan `FAKE_HANDBRAKE` WAJIB ada saat dev di Mac (aturan .clinerules). Di Windows dikosongkan.
- Tes tambahan (`/tmp/test_langkah4_extra.py`, tidak ikut commit): config HandBrake kosong -> pesan jelas; preset non-NVENC ditolak; preset NVENC lolos dan argumen CLI benar; timeout AE membunuh proses anak; topaz_only tidak melewati AE/encoding. 8/8 lulus.
- Belum dites: AE asli (aerender) dan HandBrakeCLI asli di Windows. Input hasil Topaz ke comp (BELUM DIPUTUSKAN).

## Hasil tes (Mac, FAKE)
Semua tes memakai DB dan folder sementara di /tmp. DB asli tidak disentuh.

### Antrian worker (tests_queue.py)
- Skenario A (order 1 topaz_cc, order 2 topaz_only, sukses): LULUS.
  - Job 2 baru processing setelah job 1 done. Log job 1 berurutan: topaz -> ae -> encoding -> done.
  - Tidak ada file perantara tersisa. Output kedua job identik dengan input.
- Skenario B (AE job 1 gagal, FAKE_AE_FAIL=1): LULUS.
  - Job 1 failed dan tahap encoding tidak dimulai. Job 2 tetap jalan sampai done.
  - Tidak ada file perantara tersisa.

### Validasi form dan route HTTP (langkah 3)
- Tanpa service, service tidak dikenal, topaz_cc tanpa preset, preset palsu, file txt: 400 dengan pesan sesuai.
- topaz_only dan topaz_cc valid: 303. Tidak ada file yatim di data/uploads.
- Fragmen /ui/cc-presets: topaz_only dan tanpa service kosong. topaz_cc menampilkan dropdown, label ter-escape.
- Halaman utama tanpa radio terpilih dan tanpa tag style.

### Encoding HandBrake (langkah 4, tes tambahan 8/8 lulus)
- Config kosong: pesan menyebut HANDBRAKE_CLI_PATH, HANDBRAKE_PRESET_FILE, HANDBRAKE_PRESET_NAME.
- Preset non-NVENC ditolak.
- Preset NVENC lolos, argumen CLI benar, tahap encoding sukses.
- topaz_only tidak melewati AE atau encoding.

### Timeout proses (proc.run_real)
- Timeout tahap AE melapor AE: timeout setelah N detik, dan proses anak ikut mati.
- Bug ditemukan saat tes: subprocess.run(timeout=) tidak membunuh anak. Sekarang jalur FAKE juga lewat run_real.

### Waktu render (flag SHOW_RENDER_TIME)
- Unit `format_duration`: 0s, 59s, 1m 1s, 5m 12s, 1h 2m 5s, queued "-", started_at kosong, finished_at kosong, selesai lebih awal -> 0s, timestamp rusak. LULUS.
- HTTP flag tidak diset dan `SHOW_RENDER_TIME=0`: header dan nilai durasi tidak ada di HTML (6 kolom). LULUS.
- HTTP `SHOW_RENDER_TIME=1`: header muncul, job done `5m 12s`, job queued `-` (7 kolom). LULUS.
- End-to-end FAKE: topaz_cc 11 detik (Topaz 5 + AE 3 + HandBrake 3), topaz_only 5 detik. LULUS.
- Regresi `tests_queue.py` skenario A/B: LULUS.
- Total 19/19 cek unit+HTTP lulus.

### Path preset .aep (AE_PRESET_DIR)
- Fallback tanpa env: `AE_PRESET_DIR` = `<repo>/presets`, semua aep_path di folder itu. LULUS.
- `AE_PRESET_DIR` dari env: aep_path = `<AE_PRESET_DIR>/<file>.aep`. LULUS.
- Mode asli, file .aep tidak ada: `AE: file preset tidak ditemukan: soft_fresh.aep`, tanpa traceback. LULUS.
- Mode asli, config kosong: `AE belum dikonfigurasi, kosong: AE_AERENDER_PATH, AE_COMP_NAME, AE_OM_TEMPLATE`. LULUS.
- FAKE_AE=1 dengan AE_PRESET_DIR tidak ada: tetap sukses (tidak membaca .aep). LULUS.
- `presets/` ada di .gitignore. LULUS.
- Regresi: `tests_queue.py` A/B, tes HTTP 5 preset, tes waktu render 19/19. LULUS.

Belum dites: AE asli (aerender), HandBrakeCLI asli, NVENC di Windows.

## Konteks
- PC: i5-4690, 16 GB DDR3, GTX 1070 Ti. Server dan worker satu mesin.
- Target nyata: video rata-rata 30 detik 1080p, proses Topaz sekitar 5-8 menit.

## Masalah terbuka
- Waktu proses After Effects belum diukur.
- `CC_PRESETS` di app/config.py berisi 5 preset UJI untuk FAKE_AE (soft_fresh, dream_glow, blue_beats, warm_pop, punchy_contrast). Dua terakhir dipilih bebas atas izin user. Nama final dan file .aep (presets/*.aep, belum ada) menunggu user. FAKE_AE tidak membaca aep_path.
- Preset HandBrake (presets/*.json, nama preset, encoder NVENC) belum ada. Dibutuhkan untuk tes asli di Windows (langkah 4).
- Toggle dropdown preset: selesai (HTMX murni, GET /ui/cc-presets), tidak ada pertanyaan terbuka.

- AE_AERENDER_PATH dan AE_PROJECT_PATH di .env belum diisi (langkah 4, tes asli di Windows).
- Tes asli HandBrakeCLI dan NVENC belum dilakukan (menunggu Windows).

## Catatan sesi
(agent menambah ringkasan singkat di sini setelah tiap tugas)
- Langkah 1 selesai. Python 3.11.18 di /usr/local/bin/python3.11, venv di .venv. Tabel jobs punya kolom attempts. Rencana lengkap di PLAN.md.
- Tes: init_db membuat tabel jobs + index, init_db idempoten, data/ dan .venv/ ter-ignore.
- Langkah 2 selesai. Upload mp4 -> 303 + baris queued; txt -> 400; >500 MB -> 413 tanpa sisa file; nama disk UUID.
- Keputusan: original_name disimpan apa adanya (Path().name, hanya untuk tampilan, di-escape Jinja). Sanitasi nama untuk unduhan dilakukan di langkah 5.
- Langkah 3 selesai. HTMX 2.0.11 lokal di app/static/htmx.min.js (dari jsDelivr, bukan CDN saat runtime). GET /jobs di-poll tiap 3 detik (POLL_INTERVAL_SEC). Nama job di-escape Jinja.
- Tes: /static/htmx.min.js 200; status diubah manual muncul di GET /jobs; tabel kosong menampilkan "Belum ada job."
- Langkah 4 selesai. Worker satu proses, claim atomic (BEGIN IMMEDIATE), ambil job queued tertua. Tes: FAKE dua job berurutan -> done + cmp sama; tanpa FAKE -> failed "Topaz belum dikonfigurasi"; input hilang -> failed dengan pesan singkat (stderr hanya ke log worker, bukan ke DB/UI); worker tetap hidup.
- Keputusan: error tak terduga di worker ditangkap sebagai failed (pesan "error tak terduga: <tipe>"), supaya worker tidak mati dan job tidak tertinggal di processing.- Langkah 5 selesai. GET /jobs/{id}/download: 404 jika job tidak ada/belum done/file hilang. Nama unduhan upscaled_<stem>.<ext>, stem disanitasi (karakter aneh -> _, tanpa path). Link Download di tabel hanya untuk status done dengan output_path.
- Tes: cmp hasil j1 (mp4) dan j2 (mov) sama dengan upload; queued -> 404; ID tidak ada -> 404; jumlah link Download = jumlah job done; sanitasi nama uji: "Liburan Bali (1).mp4" -> Liburan_Bali_1, "../../etc/passwd.mov" -> passwd.
- Perubahan di luar daftar PLAN: tambah db.get_job(). Temuan: job done tanpa output_path bisa muncul (data manual); link sekarang hanya tampil jika output_path ada.
- Langkah 6 selesai. Worker start: job processing dikembalikan ke queued jika attempts < MAX_ATTEMPTS (2), selain itu failed ("gagal setelah percobaan maksimal (worker terhenti)"). Timeout: subprocess.run(timeout=JOB_TIMEOUT_SEC) -> failed "Timeout setelah N detik".
- Tes: processing attempts=1 -> queued -> done; attempts=2 -> failed; timeout (JOB_TIMEOUT_SEC=2, delay 10) -> failed dengan pesan timeout; py_compile ok. Nilai 25 menit tetap di config.py.
- Langkah 7 (kode) selesai. config.py membaca .env sendiri (loader kecil dari stdlib, tanpa python-dotenv). TOPAZ_FFMPEG_PATH, TOPAZ_FILTER, TVAI_MODEL_DIR, TVAI_MODEL_DATA_DIR dibaca dari env; TOPAZ_FILTER tidak punya default.
- Command Topaz: list argumen, urutan sesuai command manual yang sudah jalan. Disimpan sebagai TOPAZ_ENCODE_ARGS (sebelum -filter_complex) dan TOPAZ_ENCODE_ARGS_TAIL (sesudahnya), karena -filter_complex ada di tengah. TVAI_* dikirim sebagai env subprocess.
- Timeout Topaz: Windows pakai taskkill /F /T; macOS/Linux pakai start_new_session + killpg. Jalur FAKE tidak berubah.
- Tes (salinan repo di /tmp, DB asli tidak tersentuh): FAKE_TOPAZ=1 worker -> done, output identik input. FAKE_TOPAZ=0 dengan env kosong -> failed "Topaz belum dikonfigurasi, kosong: ..." dan worker tetap hidup. Argumen yang dikirim cocok dengan urutan spesifikasi (dicek lewat skrip stub). Timeout 2 detik -> failed, anak ffmpeg (sleep) ikut mati.
- Belum dites: Topaz asli di Windows (user). Setelah itu langkah 7 ditandai [x] dan commit lagi.
- Perubahan di luar lingkup: tidak ada. Kata "upscaling" di .clinerules dan NOTES.md sudah diganti. Yang masih ada dan sengaja tidak diubah: judul halaman "Upscaling Video" (index.html), nama unduhan "upscaled_<stem>" (main.py), PLAN.md, dan docstring awal yang sudah diubah di topaz.py.
- Catatan: FAKE_TOPAZ_DELAY_SEC di config.py tetap hardcode 5 (.env.example memuat nilainya, tapi tidak dibaca). Tidak diubah karena di luar lingkup.
