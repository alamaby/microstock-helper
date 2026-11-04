# Implement Cloudflare Workers AI Multi-Account and Key Rotation

- **Timestamp**: 2026-11-03 23:05:00 +07:00
- **Task/Problem**: Menambahkan dukungan akun cadangan dan API token cadangan (multi-account & multi-key) pada Cloudflare Workers AI dengan auto-rotation round-robin, dynamic endpoint URL substitution per `{account_id}`, serta quota circuit breaker (karantina instan akun saat terkena HTTP 429 atau kuota harian habis).
- **Changed Files**:
  - `microstock/metadata/api_inference.py`
  - `microstock-metadata-generator/src/microstock_metadata/api_inference.py`
  - `config.yaml`
  - `microstock-metadata-generator/config.yaml`
  - `.env.example`
  - `microstock-metadata-generator/.env.example`
  - `tests/test_cloudflare_rotation.py`
  - `plans/2026-11-03-cloudflare-multi-account-rotation.md`
  - `.memory/README.md`
  - `.memory/2026-11-03/230500-cloudflare-multi-account-rotation.md`

## Technical & Business Decisions
1. **Multi-Format Credential Resolution (`resolve_api_credentials`)**:
   - Mendukung format pasangan eksplisit via `MICROSTOCK_CF_ACCOUNTS=acc1:token1,acc2:token2` (atau `MICROSTOCK_CF_CREDENTIALS`).
   - Mendukung format list paralel via `MICROSTOCK_CF_ACCOUNT_ID=acc1,acc2` + `MICROSTOCK_CF_API_TOKEN=tok1,tok2`.
   - Tetap 100% backward-compatible dengan format single account/single key lama maupun single account multi-token.
2. **Account-Aware `KeyPool`**:
   - Mampu menyimpan tuple `(account_id, api_token)` atau string tunggal `(None, api_token)`.
   - Jika initialized dengan account IDs, `next()` mengembalikan `(pos, key, account_id)`. Jika tanpa account IDs, mengembalikan `(pos, key)` untuk backward compatibility penuh.
   - Menyediakan `report_quota_exhausted(account_id)` untuk mengkarantina seluruh kredensial dari akun tersebut selama batch run.
3. **Dynamic URL Construction**:
   - Pada endpoint yang mengandung `{account_id}`, URL di-format secara dinamis di `generate_once` sesuai `account_id` yang aktif pada request tersebut.
4. **Quota Circuit Breaker (`_QuotaExceededError`)**:
   - HTTP 429 atau pesan "exceeded your daily quota" / "quota" memicu `_QuotaExceededError`.
   - Akun langsung dikarantina dan request berikutnya langsung dioper ke akun cadangan tanpa sleep delay transport retry yang membuang waktu.
5. **Adaptive Max Attempts**:
   - Loop retry di `generate_once` menggunakan `max(transport_retries + 1, len(key_pool))`, menjamin seluruh akun cadangan dicoba sebelum melempar error ke level fallback provider berikutnya.

## Assumptions & Risks
- **Asumsi**: Akun Cloudflare cadangan dibuat secara sah dengan token yang memiliki izin `Workers AI: Read/Write`.
- **Risiko**: Jika seluruh akun Cloudflare cadangan telah habis kuota hariannya, sistem otomatis failover ke provider berikutnya di rantai konfigurasi (misal `local-gateway`).

## Verification
- 7 unit tests baru di `tests/test_cloudflare_rotation.py` lulus 100% (resolusi kredensial single, paralel, eksplisit, round-robin, circuit breaker karantina 429, dynamic URL substitution, dan failover instan).
- Seluruh 33 unit tests di `tests/` lulus 100%.
- Seluruh 21 unit tests di `microstock-metadata-generator/tests/test_api_inference.py` lulus 100%.

## Proposed Conventional Commit
`feat(api): add cloudflare multi-account key rotation and quota circuit breaker`
