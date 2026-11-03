# Project Memory Index

- **Format Version**: 1.0.0
- **Last Updated**: 2026-11-03 08:55:00 +07:00

## Current State
- Mekanisme local AI model (Qwen2.5-VL via PyTorch / Transformers) telah sepenuhnya dihapus dari `microstock-metadata-generator`. Modul kini murni beroperasi menggunakan backend Vision API multi-tier (`local-gateway` OpenAI-compatible dengan failover otomatis ke `cloudflare` Workers AI).
- Dependensi dipangkas drastis (hanya memerlukan `pillow`, `pydantic>=2`, `pyyaml` tanpa PyTorch, torchvision, transformers, accelerate, atau bitsandbytes).
- Command `microstock-metadata doctor` dan script `scripts/verify_environment.py` telah diperbarui untuk memvalidasi Python, PIL, pydantic, yaml, ffmpeg, ffprobe, dan status konfigurasi API key tanpa ketergantungan model lokal.
- `Orchestrate-Stock.ps1` dan `Process-Batch.ps1` terkunci ke backend API.
- Seluruh 126 unit/integration tests lulus dengan mulus.
- Respon API dari proxy/gateway (seperti 9router/OpenCode) yang menambahkan trailer SSE (`data: [DONE]`) dapat ditangani dengan parsing toleran `raw_decode` tanpa error `Extra data`.
- Prioritas konfigurasi model menghormati hierarki: CLI flag `--api-model` > Environment variable `MICROSTOCK_API_MODEL` > YAML config.
- `microstock-metadata-generator` mendukung input gambar dan video klip (8–10s, visual-only, backend `api`).
- Mendukung ekspor metadata video 4 platform stock: Adobe Stock, Dreamstime, Vecteezy, dan Pixabay via `scripts/csv_to_embed.py`.
- `Orchestrate-Stock.ps1` mendukung parameter `-Platforms` (subset Adobe, Dreamstime, Vecteezy, Pixabay; default semua) untuk pembuatan atau pembuatan ulang selektif paket upload tanpa menyentuh platform lain.
- `Orchestrate-Stock.ps1` menoleransi kegagalan parsial generator metadata (`exit 1` dengan `OK > 0`), menandai status `PARTIAL`, mencatat file gagal ke `failed_05_metadata.txt` / `failed_03_metadata.txt`, dan melanjutkan embed untuk file yang berhasil.

## Active Decisions
- Mekanisme local model AI LLM dihapus sepenuhnya dari codebase; opsi `--backend local` ditolak dengan exit code 2 (Configuration Error).
- Parameter `--backend api` dipertahankan sebagai default dan untuk backward compatibility dengan seluruh script runner/orkestrator.
- Generator metadata API mendukung provider chain terurut: `local-gateway` (OpenCode/local proxy) dicoba terlebih dahulu; jika terkena HTTP 429 atau kegagalan transport, otomatis failover ke `cloudflare` Workers AI.
- `api_inference.py` memastikan `.env` dimuat sebelum evaluasi `model_env`/`account_env` agar override model dari `.env` segera aktif pada provider pertama.
- `Orchestrate-Stock.ps1` dan `Process-Batch.ps1` otomatis mendeteksi dan mengoper `--config config.yaml` ke generator metadata.
- Video input eksklusif untuk backend `api`.

## Open Items / Blockers
- Konfirmasi open questions portal: verifikasi manual limit 4 portal, format nomor vs nama kategori Adobe, dan kategorisasi Vecteezy sebelum publish live batch.
- Pengunggahan ke portal Pixabay memerlukan centang manual `AI-generated` dan pengisian tag melalui UI.

## Recent Entries
- [2026-11-03 08:55:00 — Remove Local AI Model Backend](file:///C:/Side/Microstock/.memory/2026-11-03/085500-remove-local-ai-model-backend.md)
- [2026-11-03 05:09:00 — Fix API Trailing SSE Extra Data & Cloudflare Vision Fallback](file:///C:/Side/Microstock/.memory/2026-11-03/050900-fix-api-response-trailing-sse-and-cf-vision.md)
- [2026-10-28 22:30:00 — Cloudflare Fallback & API Model Configuration](file:///C:/Side/Microstock/.memory/2026-10-28/223000-cloudflare-fallback-and-api-model-configuration.md)
- [2026-10-28 20:05:30 — Backup Scripts and Documentation to Google Drive](file:///C:/Side/Microstock/.memory/2026-10-28/200530-backup-scripts-docs-google-drive.md)
- [2026-10-11 22:18:00 — Orchestrator Platform Filter Implementation](file:///C:/Side/Microstock/.memory/2026-10-11/221800-orchestrator-platform-filter.md)
- [2026-10-11 09:12:00 — Metadata Partial-Failure Tolerance (Tahap 5 JPG & Tahap 3V)](file:///C:/Side/Microstock/.memory/2026-10-11/091200-metadata-partial-failure-tolerance.md)
- [2026-10-10 22:48:00 — Vecteezy + Pixabay Upload Directories Implementation](file:///C:/Side/Microstock/.memory/2026-10-10/224800-vecteezy-pixabay-upload-directories.md)
- [2026-10-09 17:28:00 — Video 4-Platform Optimization Implementation](file:///C:/Side/Microstock/.memory/2026-10-09/172800-video-4platform-optimization.md)
- [2026-10-09 16:41:00 — Video Metadata Support Implementation](file:///C:/Side/Microstock/.memory/2026-10-09/164100-video-metadata-support.md)
