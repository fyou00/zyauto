Fase 1: Pastikan inti beres
Tes Topaz asli di PC Windows (langkah 7): isi path ffmpeg Topaz dan filter, tes 1 klip 30 detik 1080p, catat waktu proses nyata.
Pisahkan config per mesin (Mac untuk dev, Windows untuk produksi).
Validasi file pakai ffprobe: batasi durasi (misal maks 60 detik), resolusi, codec, ukuran. Tolak file rusak sebelum masuk antrian.
Tampilkan progress dan error di UI (persen dari output ffmpeg, pesan gagal yang jelas).
Cancel job dan retry otomatis untuk gagal ringan.
Fase 2: Tambah After Effects
Tes aerender manual dulu: template .aep + preset .ffx lu, 1 video.
Ukur waktunya (ini yang belum masuk hitungan kapasitas).
Tambah ke worker sebagai tahap kedua: upscaling lalu color grading.
Perbarui status job: validating → queued → upscaling → color grading → encoding → done/failed.
Opsi hemat: kalau preset murni warna, coba LUT .cube + ffmpeg sebagai pengganti AE.
Fase 3: Akun dan kuota
Login/register (hash password pakai argon2 atau bcrypt, jangan simpan polos).
Kuota pakai tabel ledger: reserve saat upload, commit kalau sukses, refund otomatis kalau gagal.
Tampilkan sisa kuota dan riwayat job per user.
Pindah dari SQLite ke PostgreSQL (dibutuhkan kalau web dan worker beda mesin, atau banyak user bersamaan).
Fase 4: Pembayaran
Pilih gateway: Midtrans / Xendit / Tripay (QRIS, VA, e-wallet).
Alur: pilih paket → bayar → webhook + cek signature → kuota bertambah.
Mulai dari mode sandbox. Jangan percaya klien untuk konfirmasi bayar.
Halaman riwayat pembelian, dan kebijakan refund yang jelas.
Fase 5: UI
Baru sekarang tambah CSS (prototype tadi sengaja tanpa CSS).
Halaman: landing, login, dashboard (kuota + upload), daftar job, beli paket.
Responsif untuk HP (kebanyakan user kemungkinan upload dari HP).
Estimasi antrian (“posisi 3, sekitar 25 menit”).
Preview gratis (5-10 detik pertama atau watermark) supaya user yakin sebelum bayar.
Pakai Figma MCP kalau mau desain dulu, seperti tes landing page tadi.
Fase 6: Hosting
Server web + DB bisa di VPS murah, atau PC lu sendiri.
Worker tetap di PC Windows lu (butuh GPU). Worker menarik job lewat API dari server (bukan akses DB langsung), jadi PC tidak perlu dibuka ke internet.
Kalau semua di PC rumah: pakai Cloudflare Tunnel (aman, tanpa buka port, cocok kalau ISP pakai CGNAT).
Domain + HTTPS, reverse proxy (Caddy/Nginx), jalankan sebagai service (auto-start saat PC nyala).
Storage upload besar: chunk/resumable upload, atau Cloudflare R2.
Fase 7: Keamanan dan keandalan
Rate limit upload, batas ukuran, cek tipe file sebenarnya (bukan cuma ekstensi).
Link download pakai signed URL yang kedaluwarsa.
Auto-hapus file input/output setelah 24-72 jam, dan pause antrian kalau disk hampir penuh.
Jangan pernah jalankan nama file user di shell. Pakai UUID.
Backup database berkala.
Monitor suhu GPU, sisa disk, dan log error. Notifikasi kalau worker mati.
Listrik: UPS kalau PC jadi server 24/7.
Fase 8: Operasional
Dashboard admin: antrian, pendapatan, user, error, tombol refund manual.
Notifikasi selesai (email atau WhatsApp).
Halaman ToS, kebijakan privasi, refund, dan hak cipta video.
Kontak support (WhatsApp).
Yang jangan dilewat: legal dan lisensi
Cek EULA Topaz dan Adobe sebelum menjual jasa. Lisensi personal bisa melarang pemakaian komersial untuk pihak lain. Ini bisa menghentikan seluruh bisnisnya, jadi cek sebelum menghabiskan waktu di fase 4-8.
Peluncuran
Beta tertutup dulu (5-10 teman), harga murah atau gratis, untuk lihat waktu proses dan masalah nyata.
Baru buka umum, dengan batas antrian supaya PC tidak kewalahan.
Saran urutan kerja
Topaz asli + validasi + progress (fase 1)
AE (fase 2)
Cek lisensi
Login + kuota (fase 3)
Hosting sederhana + beta tertutup (fase 6)
Payment + UI polish (fase 4-5)
Keamanan dan admin (fase 7-8)

Alasannya: hosting dan beta sebelum payment, supaya lu dapat umpan balik nyata sebelum investasi di bagian yang paling ribet.

Mau gw buatkan versi checklist ini jadi update NOTES.md (langkah 8 dst) supaya Cline bisa mengerjakannya per langkah?