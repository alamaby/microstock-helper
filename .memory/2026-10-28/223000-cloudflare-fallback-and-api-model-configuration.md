# Cloudflare Fallback & API Model Configuration

- **Timestamp**: 2026-10-28 22:30:00 +07:00
- **Status**: Completed
- **Proposed Commit**: `feat: enable cloudflare fallback provider and env model overrides in orchestrator`
- **Plan Reference**: [plans/2026-10-28-activate-cloudflare-fallback-and-api-model-config.md](file:///C:/Side/Microstock/plans/2026-10-28-activate-cloudflare-fallback-and-api-model-config.md)

## Task / Masalah
Mengaktifkan rantai fallback provider API (Gateway lokal OpenCode -> Cloudflare Workers AI) dan sinkronisasi model API via variabel environment `MICROSTOCK_API_MODEL` pada generator metadata ketika `Orchestrate-Stock.ps1` dijalankan dan menghadapi HTTP 429 (rate-limit / kuota habis pada gateway lokal).

## Berkas yang Diubah / Dibuat
1. `microstock-metadata-generator/config.yaml` (dibuat baru):
   - Mendaftarkan rantai provider `api.providers`: `local-gateway` (model `oc/mimo-v2.6-flash-free`, override `MICROSTOCK_API_MODEL`) disusul `cloudflare` (`@cf/google/gemma-4-26b-a4b-it`, override `MICROSTOCK_CF_MODEL`).
   - Backend disetel `local` pada konfigurasi file agar tidak merusak pengujian unit CLI lokal (flag `--backend api` di-passing eksplisit oleh orchestrator).
2. `microstock-metadata-generator/src/microstock_metadata/api_inference.py`:
   - Menambahkan `ensure_dotenv_loaded()` yang dipanggil sebelum evaluasi `raw_entries` pada `build_providers()`, memastikan variabel `model_env` dan `account_env` terbaca dari `.env`.
   - Memperbaiki path lookup root `.env` dari generator directory (`../../.env`).
   - Memberikan fallback override `MICROSTOCK_API_MODEL` jika flat provider menggunakan default model.
3. `microstock-metadata-generator/src/microstock_metadata/cli.py`:
   - Menambahkan auto-discovery file `config.yaml` default jika argumen `--config` tidak diberikan secara eksplisit.
4. `Orchestrate-Stock.ps1`:
   - Menambahkan pengecekan status Cloudflare di tahap Preflight (menampilkan status apakah fallback Cloudflare terkonfigurasi).
   - Menyertakan argumen `--config` di Tahap 5 (JPG) dan Tahap 3 (Vektor) jika file `config.yaml` tersedia.
5. `Process-Batch.ps1`:
   - Menyertakan argumen `--config` pada pemanggilan `run.bat generate` jika `config.yaml` tersedia.

## Keputusan Teknis
- **Priority Precedence**: Tetap mempertahankan prinsip `CLI flags > YAML config > code defaults`. Argumen eksplisit seperti `--backend api` atau `--limit` selalu mengesampingkan nilai di file YAML.
- **Failover Transparan**: `generate_with_fallback()` mencoba provider pertama (`local-gateway`). Jika terkena error kuota (HTTP 429) atau kegagalan koneksi, fungsi otomatis berpindah ke provider kedua (`cloudflare`).
- **Safety / Env Guard**: Kredensial rahasia Cloudflare (`MICROSTOCK_CF_ACCOUNT_ID` dan `MICROSTOCK_CF_API_TOKEN`) tetap berada di berkas `.env` dan tidak pernah dicatat (log) atau di-hardcode ke file konfigurasi repository.

## Verifikasi
- Pengujian unit generator: 115 unit test pytest lulus (100% pass) tanpa regresi.
- Verifikasi programmatic `build_providers()`: Berhasil memuat 2 provider (`local-gateway` dan `cloudflare`) dengan parameter model yang ter-override dari `.env`.
- Verifikasi Preflight `Orchestrate-Stock.ps1`: Berhasil mendeteksi konfigurasi Cloudflare dan menampilkan `[i] Provider API: Gateway lokal + Fallback Cloudflare Workers AI terkonfigurasi.`
