# Plan: Activate Cloudflare Fallback & API Model Config

Created: 2026-10-28 22:12:00

## Objective
Mengaktifkan fallback provider Cloudflare dan sinkronisasi model API (`MICROSTOCK_API_MODEL`) pada `Orchestrate-Stock.ps1` dan `microstock-metadata-generator` saat terjadi error kuota/rate-limit pada local gateway / OpenCode (HTTP 429).

## Scope
- Pembuatan file konfigurasi operasional `config.yaml` pada `microstock-metadata-generator`.
- Perbaikan bug urutan pemuatan `.env` dan `model_env` pada `src/microstock_metadata/api_inference.py`.
- Auto-discovery file `config.yaml` default pada `src/microstock_metadata/cli.py`.
- Integrasi parameter `--config` pada `Orchestrate-Stock.ps1` (Tahap 5 JPG dan Tahap 3V Vektor).
- Verifikasi unit test tanpa regresi.
- Pembaruan dokumentasi Project Memory (`.memory/`).

## Milestones
1. Milestone 1: Konfigurasi & Perbaikan Core Generator (Python)
2. Milestone 2: Integrasi Orchestrator (PowerShell)
3. Milestone 3: Verifikasi Pengujian & Dokumentasi Memory

## Tasks
- [x] Task 1: Buat `microstock-metadata-generator/config.yaml` berbasis `sample_config.yaml` dengan chain `local-gateway` -> `cloudflare`.
- [x] Task 2: Perbaiki `api_inference.py` agar me-load `.env` sebelum evaluasi `model_env`/`account_env`, perbaiki relative path root `.env`, dan tambahkan `model_env` pada default flat provider.
- [x] Task 3: Tambahkan fallback auto-discovery `config.yaml` pada `cli.py` jika `--config` tidak diisi.
- [x] Task 4: Perbarui `Orchestrate-Stock.ps1` untuk menyertakan argumen `--config` jika `config.yaml` tersedia, serta tambahkan info provider chain di preflight log.
- [x] Task 5: Jalankan pytest pada `microstock-metadata-generator` untuk memastikan seluruh test tetap lulus (0 regression).
- [x] Task 6: Tulis entri Project Memory baru di `.memory/2026-10-28/` dan perbarui `.memory/README.md`.

## Risks
- **Cloudflare Rate Limit / Billing**: Model Cloudflare Workers AI `@cf/google/gemma-4-26b-a4b-it` memiliki kuota harian. Jika token/account tidak valid atau kuota habis, fallback akan tetap gagal.
  - *Mitigasi*: Exception ditangkap dengan jelas dan dilaporkan di logging/failed items.
- **Breaking existing CLI usage**: Penambahan auto-discovery `config.yaml` tidak boleh merusak pemanggilan manual yang mengandalkan default flags.
  - *Mitigasi*: Explicit CLI flag tetap memiliki prioritas tertinggi (`CLI overrides YAML`).

## Progress Log
- 2026-10-28 22:12:00 — Plan dirumuskan dan diinisialisasi.
- 2026-10-28 22:28:00 — Task 1 sampai 5 selesai: config.yaml dibuat, api_inference & cli diperbaiki, Orchestrate-Stock.ps1 & Process-Batch.ps1 diperbarui, verifikasi 115 test pytest 100% passed.
- 2026-10-29 08:50:00 — .env.example diperbarui di microstock-metadata-generator/ dan root workspace dengan struktur terorganisir dan placeholder aman.

## Notes
- Mengikuti aturan Conventional Commits (1 baris, tanpa co-authored trailer).
- Mematuhi Env Guard (tidak mencetak secret/key ke log atau chat).
