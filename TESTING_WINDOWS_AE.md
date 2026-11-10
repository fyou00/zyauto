# Tes AE, HandBrake, dan topaz_cc di Windows

Dokumen ini untuk menguji layanan `topaz_cc` (Topaz -> AE -> HandBrake) di PC Windows.
Tujuan: buktikan job `topaz_cc` selesai penuh dari upload sampai file hasil bisa diunduh.

## 0. Prasyarat

- Topaz Video AI terpasang dan berfungsi. `ffprobe.exe` harus ada di folder yang sama dengan `ffmpeg.exe` Topaz (dipakai untuk membaca durasi dan orientasi).
- After Effects terpasang dan sudah pernah dibuka sekali (lisensi aktif).
- HandBrake terpasang, dan `HandBrakeCLI.exe` ada (biasanya di `C:\Program Files\HandBrake\HandBrakeCLI.exe`).
- Driver NVIDIA terbaru (encoder NVENC).
- Video tes 5-10 detik (mp4/mov/mkv). Jangan pakai video di bawah 2 detik: durasi render AE tidak bisa diuji dengan benar.

## 1. Kode terbaru

```powershell
git pull
git log --oneline -n 3
```

Commit teratas minimal memuat `feat: input AE lewat AE_WORK_DIR, durasi ffprobe, template per orientasi`.

## 2. Siapkan file .aep

File `.aep` tidak ada di repo (folder `presets/` di `.gitignore`). Untuk tes pertama cukup satu preset.

1. Buka After Effects, buat atau buka project template CC Anda.
2. Di dalam comp, ganti footage yang akan di-CC menjadi file dengan nama **`input`** (contoh `input.mp4`), dan letakkan file itu di folder kerja AE (`AE_WORK_DIR`, default `<repo>\data\ae_work`). Worker akan mengisi/menimpa file itu setiap job, jadi `.aep` tidak perlu diubah.
3. Simpan sebagai `soft_fresh.aep` di folder presets (default `<repo>\presets`, atau folder yang Anda isi di `AE_PRESET_DIR`).
4. Catat **nama comp** dan **nama output module QuickTime** persis seperti di AE.
5. Video portrait: simpan salinan dengan nama `soft_fresh_portrait.aep` di folder yang sama. Tanpa file itu, job portrait akan gagal (disengaja, supaya hasil salah tidak lolos diam-diam).

Nama folder presets dan folder kerja AE:

| Setting | Default kalau kosong | Isi di .env kalau mau di luar repo |
|---|---|---|
| `AE_PRESET_DIR` | `<repo>\presets` | misal `D:\zyauto_assets\aep` |
| `AE_WORK_DIR` | `<repo>\data\ae_work` | misal `D:\zyauto_assets\work` |

## 3. Siapkan preset HandBrake (NVENC)

1. Buka aplikasi HandBrake, atur encoder video ke salah satu NVENC (`H.264 (NVIDIA NVENC)` atau `H.265 (NVIDIA NVENC)`).
2. Simpan sebagai preset baru (beri nama, catat persis).
3. Export preset ke file `.json` (Presets -> Export). Simpan misal di `<repo>\presets\handbrake_cc.json`.
4. Worker menolak preset non-NVENC sebelum encoding dijalankan, dan pesannya menyebut "bukan NVENC".

## 4. Isi .env

```powershell
copy .env.example .env
notepad .env
```

Contoh isi (ganti semua nilai dengan milik Anda, jangan disalin mentah):

```
FAKE_TOPAZ=0
TOPAZ_FFMPEG_PATH=C:\Program Files\Topaz Labs LLC\Topaz Video AI\ffmpeg.exe
TVAI_MODEL_DIR=<isi sesuai command manual Anda>
TVAI_MODEL_DATA_DIR=<isi sesuai command manual Anda>
TOPAZ_FILTER=<string -filter_complex dari command manual Anda>

FAKE_AE=
FAKE_HANDBRAKE=
AE_AERENDER_PATH=C:\Program Files\Adobe\Adobe After Effects 2024\Support Files\aerender.exe
AE_COMP_NAME=<nama comp>
AE_OM_TEMPLATE=<nama output module QuickTime>
AE_PRESET_DIR=
AE_WORK_DIR=

HANDBRAKE_CLI_PATH=C:\Program Files\HandBrake\HandBrakeCLI.exe
HANDBRAKE_PRESET_FILE=presets\handbrake_cc.json
HANDBRAKE_PRESET_NAME=<nama preset di file json>

SHOW_RENDER_TIME=1
```

Catatan:
- `FAKE_AE` dan `FAKE_HANDBRAKE` **kosong = mode asli**. Jangan diisi `1` kecuali sedang tes mode fake.
- `HANDBRAKE_PRESET_FILE` sebaiknya path **absolut**. Kalau relatif (contoh `presets\handbrake_cc.json`), dihitung dari folder tempat worker dijalankan, bukan dari folder repo. Jalankan worker selalu dari folder repo.
- `SHOW_RENDER_TIME=1` menampilkan kolom waktu render. Kosongkan saat produksi.

## 5. Cek konfigurasi (tanpa video)

```powershell
python -c "from app import config as c; print('AE_AERENDER:', bool(c.AE_AERENDER_PATH)); print('COMP:', bool(c.AE_COMP_NAME)); print('OM:', bool(c.AE_OM_TEMPLATE)); print('HB_CLI:', bool(c.HANDBRAKE_CLI_PATH)); print('HB_FILE:', bool(c.HANDBRAKE_PRESET_FILE)); print('HB_NAME:', bool(c.HANDBRAKE_PRESET_NAME)); print('PRESET_DIR:', c.AE_PRESET_DIR); print('WORK_DIR:', c.AE_WORK_DIR)"
```

Harapan: semua `True`, dan dua path terakhir menunjuk folder yang Anda maksud.

Cek file fisiknya:

```powershell
Test-Path .\presets\soft_fresh.aep
Test-Path .\presets\handbrake_cc.json
Test-Path "<folder ffmpeg Topaz>\ffprobe.exe"
```

Harapan: `True` semua.

## 6. Cek opsi aerender versi Anda

Kode memakai opsi `-project -comp -OMtemplate -output -s -e`. Pastikan versi AE Anda mendukungnya:

```powershell
& "<AE_AERENDER_PATH>" -help
```

Kalau ada nama opsi yang berbeda di output itu, **jangan** diubah sendiri di kode. Catat dan laporkan.

## 7. Render manual (sebelum lewat worker)

Isi dulu folder kerja AE dengan satu file bernama `input.mp4` (video apa saja), lalu:

```powershell
& "<AE_AERENDER_PATH>" -project ".\presets\soft_fresh.aep" -comp "<nama comp>" -OMtemplate "<nama OM>" -output ".\data\manual_test.mov" -s 0 -e 4
```

Harapan: `data\manual_test.mov` terbentuk. Kalau langkah ini gagal, worker juga akan gagal.

## 8. Urutan tes (jangan dilompati)

Buka dua terminal, keduanya sudah `activate` venv dan `cd` ke folder repo.

- Terminal 1: `python -m app.worker`
- Terminal 2: `uvicorn app.main:app`
- Browser: `http://127.0.0.1:8000`

| Tes | Env | Preset CC | Yang dibuktikan | Harapan |
|---|---|---|---|---|
| A | `FAKE_AE=1`, `FAKE_HANDBRAKE=1` | `soft_fresh` | Topaz asli + alur tahap | `done`. File hasil = hasil Topaz (belum ada CC) |
| B | `FAKE_AE=1`, HandBrake asli | `soft_fresh` | NVENC + preset HandBrake | `done`. File hasil mp4 dengan ukuran berbeda dari input |
| C | AE asli, HandBrake asli | `soft_fresh` | AE render + CC tampak | `done`. Durasi dan orientasi sama seperti input |
| D | seperti C | `soft_fresh` | penanganan gagal | sengaja salah (lihat bagian 9), job `failed`, worker tetap hidup |

Untuk tes A dan B, set env di terminal 1 saja:

```powershell
$env:FAKE_AE="1"; $env:FAKE_HANDBRAKE="1"; python -m app.worker
```

Env di terminal menang atas isi `.env`. Tutup terminal setelah tes supaya tidak tercampur.

Untuk setiap job, cek log worker. Urutan yang benar untuk `topaz_cc`:

```
job <id> processing
job <id> orientasi landscape
job <id> stage topaz start
job <id> stage topaz end
job <id> stage ae start
job <id> stage ae end
job <id> stage encoding start
job <id> stage encoding end
job <id> done
```

## 9. Tes gagal yang perlu dicoba

| Yang dirusak | Pesan yang diharapkan |
|---|---|
| `AE_AERENDER_PATH` diisi path salah | `AE tidak bisa dijalankan` |
| File `.aep` dihapus / nama salah | `AE: file preset tidak ditemukan: <nama>.aep` |
| Video portrait, `_portrait.aep` tidak ada | `AE: template portrait tidak ditemukan: <nama>_portrait.aep` |
| `HANDBRAKE_CLI_PATH` dikosongkan | `HandBrake belum dikonfigurasi, kosong: ...` |
| Preset HandBrake non-NVENC | `HandBrake: preset bukan NVENC, tahap encoding belum siap` |
| Nama preset salah | `HandBrake: preset tidak ditemukan di file preset` |
| aerender sukses tapi hasil .mov kosong / tanpa frame | `AE: output tidak valid (...)` (job `failed`, bukan `done`) |

Di semua kasus: status job `failed`, worker tetap jalan, dan tidak ada proses `aerender.exe` / `HandBrakeCLI.exe` yang tertinggal di Task Manager.

Tes tambahan yang penting: hentikan worker dengan Ctrl+C **saat** `stage ae start` sudah muncul. Jalankan worker lagi. Harapan: log recovery menyebut job dikembalikan ke `queued`, dan job itu diproses ulang dari awal. Cek juga tidak ada `aerender.exe` yatim.

### Perbaikan: Ctrl+C saat tahap AE
Dulu Ctrl+C pada worker saat `stage ae` berjalan meninggalkan proses anak (aerender) yang masih hidup, sementara job tertinggal `processing`. Sekarang worker memasang handler sinyal: SIGINT (Ctrl+C), SIGTERM, dan SIGBREAK (Ctrl+Break di Windows) akan membunuh pohon proses tahap yang sedang berjalan. Job tetap tertinggal `processing` dan dikembalikan ke `queued` saat worker start berikutnya.


## 10. Yang perlu dilaporkan balik

1. Output cek konfigurasi (bagian 5) dan hasil `Test-Path`.
2. Output `aerender -help` (bagian 6) dan hasil render manual (bagian 7).
3. Isi log terminal worker untuk tes A sampai D (salin teks, bukan screenshot).
4. Durasi input vs durasi output, dan orientasi hasil.
5. Apakah CC benar-benar terlihat di hasil, dan audio masih ada.
6. Versi After Effects, versi HandBrake, versi driver NVIDIA.

Dengan data itu, langkah tes AE di `PLAN.md` dan masalah terbuka di `NOTES.md` bisa ditutup.

## 11. Yang jangan dilakukan

- Jangan commit file `.aep`, video hasil, atau `.env`.
- Jangan mengubah `.aep` dari worker: worker hanya menyalin file ke `AE_WORK_DIR`.
- Jangan mengganti nama `input` di dalam `.aep` tanpa mengubah `AE_INPUT_STEM` di `app/config.py`.
- Jangan jalankan `git reset --hard` atau `git clean` di folder ini.

