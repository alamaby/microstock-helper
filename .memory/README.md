# Project Memory Index

- **Format Version**: 1.0.0
- **Last Updated**: 2026-10-11 09:12:00 +07:00

## Current State
- `microstock-metadata-generator` mendukung input gambar dan video klip (8–10s, visual-only, backend `api`).
- Mendukung ekspor metadata video 4 platform stock: Adobe Stock, Dreamstime, Vecteezy, dan Pixabay via `scripts/csv_to_embed.py`.
- `Orchestrate-Stock.ps1` mendukung 4 agensi microstock (Adobe Stock, Dreamstime, Vecteezy, Pixabay) untuk format JPG, SVG, dan EPS dengan direktori upload terpisah, sanitasi FTP Vecteezy, dan validasi kesiapan upload warn-only.
- `Orchestrate-Stock.ps1` menoleransi kegagalan parsial generator metadata (`exit 1` dengan `OK > 0`) di Tahap 5 JPG dan Tahap 3V Tier-3, menandai status `PARTIAL`, mencatat file gagal ke `failed_05_metadata.txt` / `failed_03_metadata.txt`, dan melanjutkan embed untuk file yang berhasil.
- Terdapat modul profil platform terisolasi ([`platforms.py`](file:///C:/Side/Microstock/microstock-metadata-generator/src/microstock_metadata/platforms.py)) dan soft-gate kualitas video dengan deteksi vertikal HD.
- Flag model/property release dan status AI generated terintegrasi ke skema dan CSV output.
- Pipeline teruji penuh: 121 unit/integration test passed dan verifikasi fixture PowerShell exit 0.

## Active Decisions
- `Orchestrate-Stock.ps1` menoleransi `exit 1` generator metadata jika baris sukses > 0; error fatal (`exit 2/3/4` atau `OK == 0`) tetap memicu `throw`.
- Daftar metadata gagal ditulis ke `failed_05_metadata.txt` (JPG) dan `failed_03_metadata.txt` (vektor), didahului dengan `Remove-Item -Force` untuk mencegah artefak basi.
- `Orchestrate-Stock.ps1` menghasilkan 4 direktori kind-pure: `for_vecteezy_photo`, `for_pixabay_photo`, `for_vecteezy_eps`, `for_pixabay_svg`.
- Kolom `License` CSV Vecteezy selalu literal `"free"` (non-exclusive).
- Paket Vecteezy disanitasi otomatis tanpa spasi/karakter khusus dan CSV paket ditulis ulang dengan Filename extensionless; file sumber dan agensi lain tidak diubah.
- Validasi portal pada `Test-UploadReadiness` bersifat warn-only dan menghasilkan laporan `validation_vecteezy_pixabay.txt`.
- Video input eksklusif untuk backend `api`; kombinasi video + `--backend local` fail-fast exit code 2.
- Menggunakan `ffmpeg`/`ffprobe` sistem dari PATH tanpa dependensi pip baru.
- Sampling video menggunakan 6 frame terdistribusi seragam `(i + 0.5) * duration / count`.
- 3 kolom CSV baru (`media_type`, `video_duration_sec`, `frame_count`) diikuti 3 kolom AI/release (`is_ai_generated`, `needs_model_release`, `needs_property_release`) diletakkan di akhir file untuk backward compatibility.
- Technical video check menggunakan mekanisme soft-gate (menandai `needs_review`, bukan menolak file secara fatal).

## Open Items / Blockers
- Konfirmasi open questions portal: verifikasi manual limit 4 portal, format nomor vs nama kategori Adobe, dan kategorisasi Vecteezy sebelum publish live batch.
- Pengunggahan ke portal Pixabay memerlukan centang manual `AI-generated` dan pengisian tag melalui UI.

## Recent Entries
- [2026-10-11 09:12:00 — Metadata Partial-Failure Tolerance (Tahap 5 JPG & Tahap 3V)](file:///C:/Side/Microstock/.memory/2026-10-11/091200-metadata-partial-failure-tolerance.md)
- [2026-10-10 22:48:00 — Vecteezy + Pixabay Upload Directories Implementation](file:///C:/Side/Microstock/.memory/2026-10-10/224800-vecteezy-pixabay-upload-directories.md)
- [2026-10-09 17:28:00 — Video 4-Platform Optimization Implementation](file:///C:/Side/Microstock/.memory/2026-10-09/172800-video-4platform-optimization.md)
- [2026-10-09 16:41:00 — Video Metadata Support Implementation](file:///C:/Side/Microstock/.memory/2026-10-09/164100-video-metadata-support.md)

