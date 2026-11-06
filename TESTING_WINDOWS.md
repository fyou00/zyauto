# Tes Topaz asli di Windows (langkah 7)

Dokumen ini untuk tes Topaz asli di PC Windows, dari nol (clone git).
Tujuan: buktikan job video diproses lewat ffmpeg Topaz (`FAKE_TOPAZ=0`) dan hasilnya bisa diunduh.

## 0. Prasyarat

- Python 3.11 (cek: `py -3.11 --version`). Kalau belum ada, install dari python.org dan centang "Add to PATH" atau pakai `py` launcher.
- Git for Windows.
- Topaz Video AI sudah terpasang dan sudah pernah dijalankan minimal sekali (model sudah terunduh).
- Driver NVIDIA terbaru (encoder `h264_nvenc` dipakai di command).
- Satu video pendek untuk tes (5–10 detik, mp4/mov/mkv). Pakai yang pendek supaya cepat.

## 1. Clone repo

Buka PowerShell atau Terminal (Windows), pilih folder tujuan, lalu:

```powershell
git clone https://github.com/fyou00/zyauto.git
cd zyauto
git log --oneline -n 3
```

Pastikan commit teratas memuat `feat: integrasi Topaz asli (enhancement) dengan timeout proses pohon` atau commit yang lebih baru.

## 2. Virtual environment dan dependensi

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Kalau `activate` ditolak PowerShell (execution policy), jalankan sekali:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Lalu ulangi `.venv\Scripts\activate`.

## 3. Buat file `.env`

`.env` tidak ikut git. Buat dari contoh:

```powershell
copy .env.example .env
notepad .env
```

Isi dan ubah nilai berikut (contoh format saja, jangan dipakai mentah):

```
FAKE_TOPAZ=0
TOPAZ_FFMPEG_PATH=C:\Program Files\Topaz Labs LLC\Topaz Video AI\ffmpeg.exe
TVAI_MODEL_DIR=<isi sesuai command manual Anda>
TVAI_MODEL_DATA_DIR=<isi sesuai command manual Anda>
TOPAZ_FILTER=<string -filter_complex dari command manual Anda, utuh>
```

Catatan:
- `FAKE_TOPAZ=0` wajib untuk tes asli. `.env.example` default-nya `1`.
- Tulis path apa adanya, tanpa tanda kutip. Path dengan spasi tidak perlu dikutip.
- `TOPAZ_FILTER` dipakai persis seperti yang Anda tulis. Aplikasi tidak menebak apa pun.
- `FAKE_TOPAZ_DELAY_SEC` dan `TOPAZ_TIMEOUT_SEC` di `.env.example` tidak dibaca aplikasi. Timeout job tetap 25 menit (`JOB_TIMEOUT_SEC` di `app/config.py`).
- Env yang sudah diset di terminal menang atas isi `.env`. Kalau ada variabel lama di terminal, tutup terminal dulu.

## 4. Tes A: cek konfigurasi (tanpa video)

```powershell
python -c "from app import config as c; print('FFMPEG:', bool(c.TOPAZ_FFMPEG_PATH), '| FILTER:', bool(c.TOPAZ_FILTER), '| MODEL_DIR:', bool(c.TVAI_MODEL_DIR), '| MODEL_DATA_DIR:', bool(c.TVAI_MODEL_DATA_DIR))"
```

Harapan: keempatnya `True`. Kalau ada `False`, isi `.env` dulu.

Cek file ffmpeg-nya ada:

```powershell
Test-Path "C:\Program Files\Topaz Labs LLC\Topaz Video AI\ffmpeg.exe"
```

(Ganti path itu dengan nilai `TOPAZ_FFMPEG_PATH` Anda.) Harapan: `True`.

## 5. Tes B: jalankan web dan worker

Buka dua terminal. Keduanya: `cd zyauto` lalu `.venv\Scripts\activate`.

Terminal 1 (worker):

```powershell
python -m app.worker
```

Harapan log: `worker start`.

Terminal 2 (web):

```powershell
uvicorn app.main:app
```

Buka `http://127.0.0.1:8000` di browser.

## 6. Tes C: proses satu video asli

1. Di halaman upload, pilih video pendek, lalu kirim.
2. Tabel job menampilkan status `queued`, lalu `processing` (polling tiap 3 detik).
3. Lihat terminal worker. Kalau berhasil: `job <id> done`.
4. Klik **Download** di baris job. Nama file: `upscaled_<nama>.<ext>` (nama ini memang belum diganti, lihat NOTES.md).
5. Putar file hasilnya. Cek:
   - Durasi dan resolusi sesuai harapan filter Anda.
   - Video tidak rusak dan audio ada (audio di-copy dari input).

Opsional, cek metadata dengan ffprobe (ikut di folder `bin` Topaz kalau ada):

```powershell
& "C:\Program Files\Topaz Labs LLC\Topaz Video AI\ffprobe.exe" -hide_banner "<path file hasil>"
```

Hasil unduhan juga ada di `data\outputs\<id>.<ext>`.

## 7. Tes D: jalur gagal (env kosong)

Untuk memastikan job gagal dengan pesan jelas dan worker tidak mati:

1. Hentikan worker (Ctrl+C di terminal 1). Hentikan web juga kalau perlu.
2. Di terminal baru yang sudah diaktifkan venv, jalankan worker dengan env kosong:

```powershell
$env:FAKE_TOPAZ="0"; $env:TOPAZ_FFMPEG_PATH=""; $env:TOPAZ_FILTER=""; $env:TVAI_MODEL_DIR=""; $env:TVAI_MODEL_DATA_DIR=""; python -m app.worker
```

Catatan: env yang kosong di sini menang atas `.env`. Perintah ini tidak mengubah file `.env`.

3. Upload satu video lagi. Harapan: status `failed`, pesan `Topaz belum dikonfigurasi, kosong: ...`, dan worker tetap jalan (tidak keluar).
4. Setelah itu, hentikan worker dan jalankan lagi `python -m app.worker` biasa.

## 8. Kalau ada error

- `TOPAZ_FFMPEG_PATH tidak bisa dijalankan`: path salah, atau file tidak ada. Cek dengan `Test-Path`.
- `topaz gagal` di UI: penyebab asli ada di log terminal worker (stderr ffmpeg). Salin isinya.
- `Timeout setelah 1500 detik`: pesan ini tidak pernah muncul dengan timeout sekarang (25 menit). Kalau job gagal dengan timeout, catat waktu prosesnya.
- Job tertinggal `processing` setelah worker ditutup paksa: saat worker dijalankan lagi, job akan kembali ke `queued` (percobaan pertama) atau `failed` (percobaan kedua). Itu perilaku yang diharapkan.
- Error NVENC (misal "No NVENC capable devices found"): driver NVIDIA atau GPU tidak didukung versi Topaz ini. Catat di NOTES.md sebagai masalah terbuka.

## 9. Yang perlu dilaporkan balik

Kirimkan ke saya (salin teks, jangan screenshot kalau bisa):

1. Output tes A (True/False keempat variabel).
2. Isi log terminal worker untuk job tes C dan D.
3. Status akhir dan pesan error dari UI.
4. Apakah hasil video sesuai (durasi, resolusi, audio).
5. Versi Topaz Video AI dan versi driver NVIDIA.

Dengan data itu saya bisa menutup langkah 7 di NOTES.md.

## 10. Yang jangan dilakukan

- Jangan commit `.env` (sudah di `.gitignore`, tapi cek dengan `git status`).
- Jangan jalankan `git reset --hard` atau `git clean` di folder ini.
- Jangan ubah `TOPAZ_FILTER` atau command di `app/config.py` tanpa memberi tahu saya dulu.
