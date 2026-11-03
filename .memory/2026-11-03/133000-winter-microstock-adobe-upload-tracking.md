# Winter Microstock Adobe Stock Upload Status & Limit Tracking

- **Timestamp**: 2026-11-03 13:30:00 +07:00
- **Status**: Completed
- **Proposed Commit**: `docs: track adobe stock upload status and limit threshold for winter microstock batch`

## Task / Masalah
Mendokumentasikan hasil pengunggahan batch `Winter Microstock` (folder `_stock/for_adobe`) ke portal Adobe Stock yang menghasilkan pesan limitasi kuota dan kesalahan unggah pada beberapa berkas.

## Fakta Terverifikasi
Total berkas pada folder `Winter Microstock/_stock/for_adobe` berjumlah 68 berkas JPEG (5120x5120 px):
1. **Sukses Terunggah (28 berkas)**:
   - `001` s/d `021` (21 berkas)
   - `023` s/d `028` (6 berkas)
   - `030` (1 berkas)
2. **Tertahan Kuota Upload Limit (39 berkas)**:
   - `029`
   - `031` s/d `068` (38 berkas)
3. **Gagal karena Kesalahan Unggah Teknis (1 berkas)**:
   - `022_Winter_transport_paper_cut_illus…_378c9be6.jpg` (ukuran 1,503 KB, 5120x5120, format JPEG standar valid diverifikasi via Pillow dan ExifTool).

## Berkas yang Dibuat / Diubah
- [`Winter Microstock/UPLOAD_STATUS.md`](file:///C:/Side/Microstock/Winter%20Microstock/UPLOAD_STATUS.md): Dokumen pelacak status upload per-file lengkap dengan klasifikasi status dan panduan tindakan lanjutan.

## Keputusan Teknis & Bisnis
1. **Pemisahan Kategori Gagal**: Memisahkan secara tegas berkas yang gagal akibat batas kuota portal (39 berkas) vs kegagalan koneksi/server transient pada berkas tunggal (berkas `022`).
2. **Strategi Re-upload**:
   - Berkas `022` dijadwalkan untuk dicoba unggah ulang tersendiri (single file upload retry).
   - 39 berkas lainnya dijadwalkan diunggah saat slot kuota upload Adobe Stock terbuka kembali.
3. **Temuan Audit Metadata**:
   - Berkas `021`, `022`, dan `023` di dalam file metadata CSV memiliki judul dan kata kunci "Flowers blooming in a garden" (tidak sesuai tema stiker musim dingin). Judul untuk berkas `021` dan `023` yang sudah sukses terunggah perlu direvisi langsung di halaman antrean Adobe Stock sebelum di-submit, dan metadata `022` perlu disesuaikan sebelum diunggah ulang.

## Asumsi & Risiko
- Slot kuota upload Adobe Stock akan kembali terbuka setelah berkas yang sedang dalam tahap *in review* disetujui/ditolak oleh kurator Adobe, atau setelah jendela waktu kuota berkala di-reset.
- Risiko penolakan (*rejection*) metadata tidak relevan pada berkas `021` dan `023` jika kurasi dilakukan sebelum penyesuaian judul "Flowers blooming...".

## Blocker / Open Items
- [ ] Menunggu pembukaan slot kuota upload Adobe Stock untuk 39 berkas (`029`, `031`–`068`).
- [ ] Mengunggah ulang berkas `022`.
- [ ] Menyesuaikan metadata judul/deskripsi berkas `021`, `022`, dan `023` agar sesuai dengan tema winter stickers.

## Verifikasi
- Validasi daftar 68 berkas di direktori `for_adobe` terhadap input laporan kegagalan: 28 sukses + 39 limit + 1 error = 68 berkas (100% cocok dan terverifikasi).
- Pengujian integritas berkas `022` via Pillow (`img.verify()`) dan pembacaan header ExifTool berhasil tanpa korupsi berkas.
