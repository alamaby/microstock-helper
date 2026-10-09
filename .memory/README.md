# Project Memory Index

- **Format Version**: 1.0.0
- **Last Updated**: 2026-10-09 17:28:00 +07:00

## Current State
- `microstock-metadata-generator` mendukung input gambar dan video klip (8–10s, visual-only, backend `api`).
- Mendukung ekspor metadata video 4 platform stock: Adobe Stock, Dreamstime, Vecteezy, dan Pixabay via `scripts/csv_to_embed.py`.
- Terdapat modul profil platform terisolasi ([`platforms.py`](file:///C:/Side/Microstock/microstock-metadata-generator/src/microstock_metadata/platforms.py)) dan soft-gate kualitas video dengan deteksi vertikal HD.
- Flag model/property release dan status AI generated terintegrasi ke skema dan CSV output.
- Pipeline teruji penuh: 121 unit/integration test passed.

## Active Decisions
- Video input eksklusif untuk backend `api`; kombinasi video + `--backend local` fail-fast exit code 2.
- Menggunakan `ffmpeg`/`ffprobe` sistem dari PATH tanpa dependensi pip baru.
- Sampling video menggunakan 6 frame terdistribusi seragam `(i + 0.5) * duration / count`.
- 3 kolom CSV baru (`media_type`, `video_duration_sec`, `frame_count`) diikuti 3 kolom AI/release (`is_ai_generated`, `needs_model_release`, `needs_property_release`) diletakkan di akhir file untuk backward compatibility.
- Technical video check menggunakan mekanisme soft-gate (menandai `needs_review`, bukan menolak file secara fatal).

## Open Items / Blockers
- Konfirmasi open questions portal: verifikasi manual limit 4 portal, format nomor vs nama kategori Adobe, dan kategorisasi Vecteezy sebelum publish live batch.

## Recent Entries
- [2026-10-09 17:28:00 — Video 4-Platform Optimization Implementation](file:///C:/Side/Microstock/.memory/2026-10-09/172800-video-4platform-optimization.md)
- [2026-10-09 16:41:00 — Video Metadata Support Implementation](file:///C:/Side/Microstock/.memory/2026-10-09/164100-video-metadata-support.md)

