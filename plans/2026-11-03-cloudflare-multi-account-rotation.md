# Implementasi Multi-Account & Key Backup Cloudflare Workers AI dengan Auto-Rotation

Created: 2026-11-03 22:52:00 +07:00

## Objective
Menambahkan dukungan akun dan API token cadangan (multi-account & multi-key) pada backend inference Cloudflare Workers AI, dilengkapi mekanisme rotasi otomatis (round-robin), substitusi URL dinamis per `{account_id}`, serta karantina instan (circuit breaker) untuk akun yang terkena limit kuota harian (HTTP 429 / Quota Exceeded) atau kegagalan otentikasi (HTTP 401/403).

## Scope
- Mendukung format kredensial multi-account via environment variables:
  - `MICROSTOCK_CF_ACCOUNTS=acc1:token1,acc2:token2` (format pasangan eksplisit), ATAU
  - `MICROSTOCK_CF_ACCOUNT_ID=acc1,acc2` + `MICROSTOCK_CF_API_TOKEN=tok1,tok2` (format paralel).
  - Tetap backward-compatible dengan format tunggal lama.
- Kelas `CredentialPool` (pengembangan dari `KeyPool`) yang mengelola pasangan `(account_id, api_token)`.
- Substitusi dinamis `{account_id}` pada URL endpoint Cloudflare di setiap request `generate_once`.
- Deteksi HTTP 429 dan error "daily quota exceeded", dengan penandaan `report_quota_exhausted(account_id)` tanpa sleep delay berlebih sehingga langsung rotasi ke akun berikutnya.
- Sinkronisasi kedua implementasi: `microstock/metadata/api_inference.py` dan `microstock-metadata-generator/src/microstock_metadata/api_inference.py`.
- Pembaruan dokumentasi `.env.example`.
- Penulisan unit tests komprehensif untuk memverifikasi rotasi, error handling, dan backward compatibility.

## Milestones
1. Refactor `api_inference.py` untuk mendukung `CredentialPool` berpasangan dan rotasi dinamis per request.
2. Implementasikan klasifikasi error khusus `_QuotaExceededError` dan karantina akun.
3. Sinkronisasikan kode ke `microstock-metadata-generator/src/microstock_metadata/api_inference.py`.
4. Perbarui `.env.example`.
5. Buat unit tests pengujian rotasi multi-account dan jalankan verifikasi test suite.
6. Catat riwayat di `.memory/` dan update `.memory/README.md`.

## Tasks
- [x] Buat dukungan credential pairs dan resolver format multi-account di `microstock/metadata/api_inference.py`.
- [x] Update `generate_once` & `_post_json` untuk dynamic endpoint formatting dan penanganan kuota 429 (`_QuotaExceededError`).
- [x] Sinkronkan ke `microstock-metadata-generator/src/microstock_metadata/api_inference.py`.
- [x] Perbarui `.env.example` dan `config.yaml` dengan dokumentasi format multi-account.
- [x] Tulis unit test di `tests/test_cloudflare_rotation.py`.
- [x] Jalankan test suite `pytest tests/` untuk memastikan seluruh test lulus 100% (33 tests pass).
- [ ] Buat catatan memori `.memory/2026-11-03/230000-cloudflare-multi-account-rotation.md` dan update `.memory/README.md`.

## Risks
- Format kredensial Cloudflare tidak valid (misal karakter ilegal atau pasangan tidak seimbang).
- Perilaku non-Cloudflare provider (seperti `local-gateway` yang tidak memiliki `account_id`) harus tetap 100% kompatibel tanpa regresi.

## Progress Log
- 2026-11-03 22:52:00 — Plan dirumuskan dan file plan diinisialisasi.
- 2026-11-03 23:02:00 — Implementasi multi-account, key rotation, dynamic endpoint substitution, dan quota circuit breaker selesai. 7 unit tests baru dan 26 unit tests eksisting lulus 100%.

## Notes
- Backward compatibility wajib dijaga untuk single key/account lama.
