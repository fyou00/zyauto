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
- [ ] 7. Integrasi Topaz asli (enhancement, tanpa upscaling). Kode selesai; tes Topaz asli di Windows: PENDING (user)

Commit terakhir: feat: kolom service, cc_preset, stage, intermediate_path dan migrasi db

## Layanan AE (rencana lengkap di PLAN.md, bagian "Layanan AE")
- [x] 2. DB: kolom service, cc_preset, stage, intermediate_path + migrasi
- [ ] 3. UI: radio layanan, dropdown preset CC, kolom Layanan dan Tahap
- [ ] 4. Worker bertahap topaz -> ae -> encode, FAKE_AE, tes aturan antrian

## Keputusan
- Stack: FastAPI + Jinja2 + HTMX, SQLite untuk jobs, tanpa Redis/Celery.
- Satu worker, satu job sekali jalan (hanya 1 GPU).
- Status job: queued -> processing -> done / failed.
- Format upload: mp4, mov, mkv. Batas ukuran di config.py (default 500 MB).
- Di luar prototype: login, kuota, payment, CSS. (After Effects sekarang masuk lewat bagian "Layanan AE"; .clinerules sudah diperbarui sesuai keputusan user.)
- Encoding akhir topaz_cc: AE render ke .mov (QuickTime), lalu HandBrakeCLI encode ke .mp4 dengan preset NVENC dari presets/. Bukan ffmpeg. topaz_only tidak di-encode ulang.
- Preset CC: id stabil + label UI + path .aep, di config.py. Dropdown hanya tampilan; server tetap memvalidasi id.
- Layanan: topaz_only dan topaz_cc. Satu order = satu job. Worker memproses satu job penuh (termasuk seluruh tahap AE) sebelum job berikutnya; AE gagal -> job failed, job berikutnya lanjut.
- Skema (langkah 2): kolom baru service (default 'topaz_only', CHECK), cc_preset, stage (CHECK topaz|ae|encoding atau NULL), intermediate_path. Migrasi lewat ALTER TABLE ADD COLUMN di init_db(), dilewati jika kolom sudah ada; baris lama terbaca sebagai topaz_only.
- Daftar preset CC dibaca dari CC_PRESETS di .env (dipisah koma), default kosong. Nama preset belum diputuskan user, tidak diisi tebakan.
- Tanpa pilihan layanan: ditolak (400), tidak ada default di server. Berlaku saat UI/route dikerjakan di langkah 3.
- File perantara disimpan di data/intermediates (INTERMEDIATE_DIR), dihapus saat job selesai atau gagal (langkah 4).

## Konteks
- PC: i5-4690, 16 GB DDR3, GTX 1070 Ti. Server dan worker satu mesin.
- Target nyata: video rata-rata 30 detik 1080p, proses Topaz sekitar 5-8 menit.

## Masalah terbuka
- Nilai TOPAZ_FILTER dan TVAI_* di .env belum diisi user (kode siap, tes asli menunggu Windows).
- Dukungan GTX 1070 Ti di versi Topaz yang dipakai belum dites.
- Waktu proses After Effects belum diukur.
- Daftar preset CC awal (id, label, file .aep) belum diisi user. Struktur sudah diputuskan, lihat PLAN.md bagian "Revisi keputusan".
- Preset HandBrake (presets/*.json, nama preset, encoder NVENC) belum ada. Dibutuhkan untuk tes asli di Windows (langkah 4).
- Toggle dropdown preset: rencana HTMX murni (route fragment), menunggu konfirmasi (langkah 3).
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
