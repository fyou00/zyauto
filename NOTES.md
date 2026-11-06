# NOTES: Prototype Upscaling Video (Topaz)

## Tujuan prototype
Buktikan alur: upload video -> worker proses Topaz -> download hasil. Localhost, tanpa login, tanpa CSS.

## Status
- [x] 1. Struktur proyek + config.py + db.py (tabel jobs)
- [x] 2. Halaman upload + validasi file + simpan job (queued)
- [x] 3. Daftar job dengan HTMX polling
- [x] 4. Worker: ambil job, mode FAKE_TOPAZ, ubah status
- [x] 5. Download hasil
- [x] 6. Recovery: job 'processing' kembali 'queued' saat worker start; timeout job
- [ ] 7. Integrasi Topaz asli (isi TOPAZ_FFMPEG_PATH, TVAI_* env, TOPAZ_FILTER)

Commit terakhir: feat: daftar job dengan polling htmx

## Keputusan
- Stack: FastAPI + Jinja2 + HTMX, SQLite untuk jobs, tanpa Redis/Celery.
- Satu worker, satu job sekali jalan (hanya 1 GPU).
- Status job: queued -> processing -> done / failed.
- Format upload: mp4, mov, mkv. Batas ukuran di config.py (default 500 MB).
- Di luar prototype: login, kuota, payment, After Effects, CSS.

## Konteks
- PC: i5-4690, 16 GB DDR3, GTX 1070 Ti. Server dan worker satu mesin.
- Target nyata: video rata-rata 30 detik 1080p, proses Topaz sekitar 5-8 menit.

## Masalah terbuka
- Command dan filter Topaz belum diisi dari aplikasi Topaz (user yang isi).
- Dukungan GTX 1070 Ti di versi Topaz yang dipakai belum dites.
- Waktu proses After Effects belum diukur (belum masuk prototype).

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
