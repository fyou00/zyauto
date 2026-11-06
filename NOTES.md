# NOTES: Prototype Upscaling Video (Topaz)

## Tujuan prototype
Buktikan alur: upload video -> worker proses Topaz -> download hasil. Localhost, tanpa login, tanpa CSS.

## Status
- [x] 1. Struktur proyek + config.py + db.py (tabel jobs)
- [x] 2. Halaman upload + validasi file + simpan job (queued)
- [x] 3. Daftar job dengan HTMX polling
- [ ] 4. Worker: ambil job, mode FAKE_TOPAZ, ubah status
- [ ] 5. Download hasil
- [ ] 6. Recovery: job 'processing' kembali 'queued' saat worker start; timeout job
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