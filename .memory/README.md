# Project Memory Index

- **Format Version**: 1.0.0
- **Last Updated**: 2026-10-09 16:41:00 +07:00

## Current State
- `microstock-metadata-generator` mendukung input gambar dan video klip (8–10s, visual-only, backend `api`).
- Ekstraksi frame video dilakukan seragam (uniform 6 frame) via `ffmpeg` & `ffprobe` sistem.
- Model backend: `local` (Qwen2.5-VL-3B-Instruct) dan `api` (OpenAI-compatible multi-provider failover).
- Pipeline teruji penuh: 103 unit/integration test passed.

## Active Decisions
- Video input eksklusif untuk backend `api`; kombinasi video + `--backend local` fail-fast exit code 2.
- Menggunakan `ffmpeg`/`ffprobe` sistem dari PATH tanpa dependensi pip baru.
- Sampling video menggunakan 6 frame terdistribusi seragam `(i + 0.5) * duration / count`.
- 3 kolom CSV baru (`media_type`, `video_duration_sec`, `frame_count`) diletakkan di akhir file untuk stabilitas kompatibilitas.

## Open Items / Blockers
- Tidak ada blocker aktif saat ini.

## Recent Entries
- [2026-10-09 16:41:00 — Video Metadata Support Implementation](file:///C:/Side/Microstock/.memory/2026-10-09/164100-video-metadata-support.md)
