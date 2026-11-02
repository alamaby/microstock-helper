# Fix API Trailing SSE Extra Data & Cloudflare Vision Model Fallback

- **Timestamp**: 2026-11-03 05:09:00 +07:00
- **Status**: Completed
- **Proposed Commit**: `fix: handle api response trailing sse data and enforce cli model precedence`

## Task / Masalah
Saat menjalankan generator metadata `microstock_metadata`, muncul dua error beruntun:
1. `API provider 'local-gateway' failed, trying next: Unexpected API response shape: Extra data: line 1 column 991 (char 990)`.
2. `API provider 'cloudflare' failed, trying next: API error HTTP 400: {"errors":[{"message":"AiError: AiError: Unable to add image when there are no user-supplied nor system-supplied messages..."}]}`.

## Analisis Akar Masalah (Root Causes)

1. **Error Provider `local-gateway` (Extra data: line 1 column X)**:
   - Gateway lokal (9router pada port 20128) yang mengeksekusi model `combo-3` mengembalikan response HTTP 200 dengan payload JSON lengkap, namun menyertakan trailer token SSE `data: [DONE]\n\n` di akhir body response.
   - Pemanggilan `json.loads(resp.read().decode("utf-8"))` standar melempar `JSONDecodeError: Extra data` karena adanya byte tambahan setelah objek JSON selesai ditutup (`}`).
   - Error ini tertangkap sebagai `ValueError` dan membungkus exception menjadi `Unexpected API response shape`, menyebabkan sistem menganggap provider gagal dan memicu fallback.

2. **Error Provider `cloudflare` (AiError 3030: Unable to add image)**:
   - Pada file `.env`, variabel `MICROSTOCK_CF_MODEL` diatur ke `@cf/meta/llama-3.2-11b-vision-instruct`.
   - Endpoint OpenAI-compatible Workers AI (`/ai/v1/chat/completions`) milik Cloudflare saat ini memiliki bug/limitasi internal pada model `@cf/meta/llama-3.2-11b-vision-instruct` saat memproses payload multimodal `image_url` standar, melempar HTTP 400 kode 3030.
   - Sebaliknya, model default Cloudflare yang dikonfigurasikan di `config.yaml` (`@cf/google/gemma-4-26b-a4b-it`) terverifikasi 100% didukung dan sukses membaca gambar melalui endpoint chat completions Cloudflare.

3. **CLI Model Precedence Bug**:
   - Jika argumen `--api-model` diberikan via CLI saat variabel `MICROSTOCK_API_MODEL` ada di environment, provider chain sebelumnya mengutamakan `model_env`. Seharusnya hierarki prioritas adalah CLI > ENV > YAML.

4. **Error Respon Objek Dict/List (`AttributeError: 'dict' object has no attribute 'strip'`)**:
   - Beberapa model/proxy mengembalikan `message["content"]` berupa objek `dict` (JSON ter-parse atau content block) alih-alih `str`.
   - Kode sebelumnya memanggil `.strip()` langsung pada `content` tanpa mengecek tipe data, memicu `AttributeError`. Karena `AttributeError` belum ditangkap pada tuple exception `generate_once`, error ini lolos dan menghentikan eksekusi generator (crash pada item 19).
   - Diperbaiki dengan mengekstrak teks, men-dump `json.dumps(content)` bila berupa `dict`, menggabungkan teks bila berupa `list`, dan menambahkan `AttributeError` pada tuple penanganan exception `InferenceError`.

## Berkas yang Diubah
1. `microstock-metadata-generator/src/microstock_metadata/api_inference.py`:
   - Menambahkan fungsi helper `_parse_response_json(text)` yang menggunakan `json.JSONDecoder().raw_decode()` untuk mem-parse objek JSON utama dan mentolerir trailer SSE (`data: [DONE]`), trailing whitespace, maupun format chunk SSE.
   - Memperbarui `_post_json()` untuk memakai `_parse_response_json()`.
   - Memperbarui `build_providers()` untuk menghormati prioritas flag CLI `cli_model` pada provider primer di atas `model_env`.
   - Menangani `content` bertipe `dict` atau `list` pada `generate_once()` dan menangkap `AttributeError`.
2. `microstock-metadata-generator/src/microstock_metadata/cli.py`:
   - Menyimpan `args.api_model` ke `cfg.api.cli_model` pada `cmd_generate()` jika dispesifikasikan eksplisit via CLI.
3. `microstock-metadata-generator/tests/test_api_inference.py`:
   - Menambahkan unit test `test_parse_response_json_with_trailing_sse` untuk response ber-trailer `data: [DONE]`.
   - Menambahkan unit test `test_cli_model_precedence` untuk memastikan CLI meng-override `model_env`.
   - Menambahkan unit test `test_generate_once_with_dict_content` dan `test_generate_once_with_list_content`.

## Keputusan Teknis & Rekomendasi
- Parser JSON toleran terhadap trailer token tanpa mengubah struktur payload request OpenAI standard.
- Konfigurasi `.env` untuk fallback Cloudflare (`MICROSTOCK_CF_MODEL`) disarankan menggunakan model default `@cf/google/gemma-4-26b-a4b-it` yang stabil di endpoint `/chat/completions`.

## Verifikasi
- Pengujian unit `pytest microstock-metadata-generator`: 126 passed (100% pass) tanpa regresi.
- Pengujian live `local-gateway` dengan model `combo-3`: Berhasil mem-parse response dan menghasilkan metadata tanpa error `Extra data`.
- Pengujian live Cloudflare Workers AI dengan model `@cf/google/gemma-4-26b-a4b-it`: Berhasil menganalisis gambar dan mengembalikan hasil akurat.
