# Project Memory Index

- **Format Version**: 1.0.0
- **Last Updated**: 2026-11-06 02:23:00 +07:00

## Current State
- Seluruh fungsionalitas otomasi microstock (utilitas raster, renumbering, upscaler, tracer vektor, vector render/convert, embedder ExifTool/SVG XML, dan orkestrator pipeline multi-platform) telah dikonsolidasikan ke dalam satu paket aplikasi Python terpadu (`microstock-helper` / `microstock`).
- Seluruh pemanggilan binary eksternal (`upscayl`, `vtracer`, `inkscape`, `ffmpeg`/`ffprobe`, `exiftool`) via subprocess telah diproteksi dengan `encoding="utf-8", errors="replace"` serta global UTF-8 Mode (`PYTHONUTF8=1`) di `run.bat` guna mencegah crash `UnicodeDecodeError` / `cp1252 charmap` pada Windows.
- Dokumentasi `README.md` telah diperbarui sepenuhnya ke dalam Bahasa Inggris standar dengan diagram alur dan panduan multi-account Cloudflare yang komprehensif.
- CLI terpadu dilengkapi startup preflight dependency check yang otomatis memverifikasi keberadaan `exiftool`, `upscayl`, `vtracer`, `inkscape`, `ffmpeg`, `ffprobe`, dan status API token sebelum tugas pipeline dijalankan.
- Generator metadata Vision API Cloudflare Workers AI mendukung konfigurasi multi-account dan multi-key dengan rotasi round-robin, substitusi URL dinamis per request (`{account_id}`), serta karantina instan (circuit breaker) saat akun terkena kuota harian habis (HTTP 429).
- Konversi gambar raster (PNG/WebP/TIF/BMP ke JPEG) dioperasikan secara native via Pillow dengan penanganan alpha compositing ke latar putih standar microstock.
- Mekanisme local AI model (Qwen2.5-VL via PyTorch) telah dihapus dari codebase; kini murni beroperasi menggunakan backend Vision API multi-tier (`cloudflare` Workers AI dengan fallback ke `local-gateway` OpenAI-compatible).
- Modul discovery metadata otomatis mengecualikan folder pipeline internal (`_stock`, `output-api`, `for_*`) dan `batch` otomatis mendeteksi struktur flat root (`--no-recursive`).
- Seluruh script PowerShell legacy (`Orchestrate-Stock.ps1`, `Process-Batch.ps1`, `Embed-JpgMetadata.ps1`, dll.) tetap dipertahankan untuk backward compatibility.
- Seluruh unit tests (33 tests di `tests/` dan 21 tests di `microstock-metadata-generator/tests/test_api_inference.py`) lulus 100%.

## Active Decisions
- Dokumentasi publik `README.md` menggunakan Bahasa Inggris standar industri microstock.
- Konsolidasi satu pintu: CLI terpadu `microstock` menyediakan subcommand: `run`, `batch`, `convert`, `renumber`, `upscale`, `trace`, `vector-preview`, `convert-eps`, `embed-jpg`, `embed-vector`, `doctor`, dan `generate`.
- Multi-Account & Key Rotation Cloudflare: Mendukung format pasangan eksplisit `MICROSTOCK_CF_ACCOUNTS=acc1:tok1,acc2:tok2` dan format paralel `MICROSTOCK_CF_ACCOUNT_ID=acc1,acc2` + `MICROSTOCK_CF_API_TOKEN=tok1,tok2`.
- Quota Circuit Breaker: HTTP 429 / kuota harian Cloudflare langsung mengkarantina akun tersebut untuk sesi batch berjalan, merotasi request ke akun berikutnya tanpa sleep delay.
- Startup preflight check wajib memvalidasi tool CLI eksternal sebelum menjalankan operasi pipeline untuk mencegah kegagalan di tengah jalan.
- Batas `MAX_PATH` 260 karakter Upscayl diatasi dengan sandboxing direktori `%TEMP%`.
- Mekanisme local model AI LLM dihapus sepenuhnya dari codebase; opsi `--backend local` ditolak dengan exit code 2 (Configuration Error).
- Generator metadata API mendukung provider chain terurut: `cloudflare` dicoba terlebih dahulu; jika terkena HTTP 429 atau kegagalan transport dan seluruh akun cadangan habis, otomatis failover ke `local-gateway`.

## Open Items / Blockers
- Batch `Winter Microstock` di Adobe Stock: 28 file sukses terunggah, 39 file tertahan upload limit (menunggu kuota/slot review terbuka), dan 1 file (`022`) mengalami upload error (perlu re-upload mandiri).
- Metadata `021`, `022`, dan `023` pada batch `Winter Microstock` tercatat "Flowers blooming..." dan perlu disesuaikan sebelum submit kurasi.
- Konfirmasi open questions portal: verifikasi manual limit 4 portal, format nomor vs nama kategori Adobe, dan kategorisasi Vecteezy sebelum publish live batch.
- Pengunggahan ke portal Pixabay memerlukan centang manual `AI-generated` dan pengisian tag melalui UI.

## Recent Entries
- [2026-11-06 02:23:00 — Fix Upscaler and External Subprocess UnicodeDecodeError (cp1252 charmap)](file:///C:/Side/Microstock/.memory/2026-11-06/022300-fix-upscaler-subprocess-charmap-decode-error.md)
- [2026-11-04 14:08:00 — Translate README to English & Document Multi-Account Capabilities](file:///C:/Side/Microstock/.memory/2026-11-04/140800-translate-readme-to-english.md)
- [2026-11-03 23:05:00 — Implement Cloudflare Workers AI Multi-Account and Key Rotation](file:///C:/Side/Microstock/.memory/2026-11-03/230500-cloudflare-multi-account-rotation.md)
- [2026-11-03 15:45:00 — Fix Batch Discovery: Prune Pipeline & Output Folders, Auto-Detect Flat Root](file:///C:/Side/Microstock/.memory/2026-11-03/154500-fix-batch-discovery-prune-pipeline-folders.md)
- [2026-11-03 15:10:00 — Diagnosis: 9Router Stripping Image Payload on Cloudflare Vision Model](file:///C:/Side/Microstock/.memory/2026-11-03/151000-diagnose-9router-image-stripping-cloudflare-vision.md)
- [2026-11-03 13:30:00 — Winter Microstock Adobe Stock Upload Status & Limit Tracking](file:///C:/Side/Microstock/.memory/2026-11-03/133000-winter-microstock-adobe-upload-tracking.md)
- [2026-11-03 10:30:00 — Consolidate Microstock Scripts to Unified Python Application](file:///C:/Side/Microstock/.memory/2026-11-03/103000-consolidate-microstock-scripts-to-python.md)
- [2026-11-03 08:55:00 — Remove Local AI Model Backend](file:///C:/Side/Microstock/.memory/2026-11-03/085500-remove-local-ai-model-backend.md)
- [2026-11-03 05:09:00 — Fix API Trailing SSE Extra Data & Cloudflare Vision Fallback](file:///C:/Side/Microstock/.memory/2026-11-03/050900-fix-api-response-trailing-sse-and-cf-vision.md)
- [2026-10-28 22:30:00 — Cloudflare Fallback & API Model Configuration](file:///C:/Side/Microstock/.memory/2026-10-28/223000-cloudflare-fallback-and-api-model-configuration.md)
- [2026-10-28 20:05:30 — Backup Scripts and Documentation to Google Drive](file:///C:/Side/Microstock/.memory/2026-10-28/200530-backup-scripts-docs-google-drive.md)
- [2026-10-11 22:18:00 — Orchestrator Platform Filter Implementation](file:///C:/Side/Microstock/.memory/2026-10-11/221800-orchestrator-platform-filter.md)
- [2026-10-11 09:12:00 — Metadata Partial-Failure Tolerance (Tahap 5 JPG & Tahap 3V)](file:///C:/Side/Microstock/.memory/2026-10-11/091200-metadata-partial-failure-tolerance.md)
- [2026-10-10 22:48:00 — Vecteezy + Pixabay Upload Directories Implementation](file:///C:/Side/Microstock/.memory/2026-10-10/224800-vecteezy-pixabay-upload-directories.md)
- [2026-10-09 17:28:00 — Video 4-Platform Optimization Implementation](file:///C:/Side/Microstock/.memory/2026-10-09/172800-video-4platform-optimization.md)
- [2026-10-09 16:41:00 — Video Metadata Support Implementation](file:///C:/Side/Microstock/.memory/2026-10-09/164100-video-metadata-support.md)
