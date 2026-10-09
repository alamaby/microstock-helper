# Video Metadata Support — Implementation Plan

Created: 2026-10-09 09:00:00

## Objective

Menambah dukungan input video (klip 8–10 detik, visual-only, backend `api`) ke
`microstock-metadata-generator` dengan strategi frame sampling uniform
(6 frame via ffmpeg sistem), memakai ulang pipeline inference/validasi/export
yang ada tanpa mengubah perilaku image-only saat ini.

Keputusan yang sudah final (jangan dibuka ulang saat implementasi):
- D1: klip 8–10 detik, visual-only, tanpa audio/transkrip.
- D2: path video hanya backend `api`; kombinasi video + `--backend local` = fail-fast exit 2.
- D3: pakai ffmpeg + ffprobe sistem yang sudah di PATH (v9.0.2, Chocolatey), tanpa dependency pip baru.
- D4: sampling uniform 6 frame (bukan tengah-berat, bukan scene-detect).

## Scope

- In scope: `microstock-metadata-generator/` — discovery, config/CLI, prompt video,
  modul ekstraksi frame baru, multi-image payload API, field schema/exporter,
  cabang video di `cmd_generate`/`_process_one`, `doctor` cek ffmpeg, test, README + `sample_config.yaml`.
- Out of scope: native video tensor Qwen2.5-VL, audio/transkrip (whisper), scene detection,
  embed metadata ke file video (ExifTool video), uploader agensi, perubahan script PowerShell root
  (`Convert-*.ps1`, `Export-VectorPreview.ps1`, `Orchestrate-Stock.ps1`), perubahan model lokal.

## Requirement / Finding Traceability

| ID | Finding / Requirement | Ditangani langkah |
|----|----------------------|-------------------|
| F1 | `discovery.py` + `SUPPORTED_EXTENSIONS` hanya image; video ditolak | S1 |
| F2 | `normalize_image()` hanya 1 path image → 1 PIL | S4 (pakai ulang per frame, tanpa ubah F2) |
| F3 | `inference.py` lokal dan `api_inference.py` hanya 1 image | S5 (API saja; lokal tidak diubah) |
| F4 | Prompt `microstock-v1/v2/v3` berorientasi single image statis | S3 |
| F5 | `ProcessingResult`/CSV tidak punya field media video | S6 |
| F6 | `config.py`/`cli.py` tidak punya opsi video/media-type | S2, S7 |
| F7 | ffmpeg 9.0.2 + ffprobe ada di PATH; quirk image2 (`-frames:v 1 -update 1`, lihat `Export-VectorPreview.ps1:136-150`); pola Temp nama-pendek untuk MAX_PATH (lihat `Upscale.ps1`) | S4, S7 |
| F8 | Resume SHA-256, checkpoint-after-every-item, atomic writes, exit code 0/1/2/3/4, CSV UTF-8 BOM + formula guard harus dipertahankan | Semua langkah (ditegaskan per langkah) |
| F9 | Aturan validasi (title ≤70, description ≤200, keywords 25–49, kategori, editorial risk) tidak berubah untuk video | S3, S7 (tanpa ubah `validation.py`) |
| F10 | Test suite image-only harus tetap hijau; Doctor harus melaporkan kesiapan video | S7, S8 |

## Milestones

1. M1 — Discovery + config + prompt video (S1, S2, S3). Fondasi tanpa runtime baru.
2. M2 — Ekstraksi frame + multi-image API (S4, S5). Inti kapabilitas video.
3. M3 — Schema/exporter + wiring CLI + doctor (S6, S7). End-to-end path video.
4. M4 — Test + docs + verifikasi penuh (S8, S9).

## Tasks

- [x] S1 — Konstanta + discovery video
- [x] S2 — `VideoConfig`, validasi, mapping CLI
- [x] S3 — Prompt `microstock-video-v1`
- [x] S4 — Modul baru `video_processing.py` (ffprobe + ffmpeg, uniform 6 frame)
- [x] S5 — Multi-image payload di `api_inference.py`
- [x] S6 — Field schema + kolom CSV
- [x] S7 — Wiring `cli.py`: cabang video, guard local-backend, doctor ffmpeg
- [x] S8 — Test baru + update test lama
- [x] S9 — Docs + contoh config + verifikasi akhir

---

## Langkah Implementasi

### S1 — Konstanta + discovery video

- Tujuan langkah: file video ditemukan oleh discovery tanpa mengubah perilaku image-only.
- Finding/requirement: F1.
- Dependency: tidak ada (langkah pertama).
- File yang harus dibaca:
  - `src/microstock_metadata/constants.py` (seluruh file, 74 baris)
  - `src/microstock_metadata/discovery.py` (seluruh file, 64 baris)
  - `tests/test_discovery.py`, `tests/conftest.py` (pola fixture `img_dir`)
- File yang harus diubah:
  - `src/microstock_metadata/constants.py`
  - `src/microstock_metadata/discovery.py`
- Simbol terkait: `SUPPORTED_EXTENSIONS`, `discover_images`, `UnsupportedImageError`, `ConfigurationError`.
- Kondisi implementasi saat ini: `SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")`
  (`constants.py:20`); `discover_images(input_path, recursive, extensions, limit)` memfilter
  dengan ekstensi tersebut (`discovery.py:23-55`).
- Perubahan konkret:
  1. `constants.py`, setelah baris 20, tambah:
     `SUPPORTED_VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm")`
     dan `DEFAULT_VIDEO_FRAMES = 6`, `VIDEO_MAX_DURATION_SEC = 30`.
     Jangan ubah nilai `SUPPORTED_EXTENSIONS` yang ada.
  2. `discovery.py`:
     - import `SUPPORTED_VIDEO_EXTENSIONS`.
     - tambah `def discover_inputs(input_path, recursive=True, extensions=None, limit=None, media_type="auto")`
       dengan `media_type in ("auto", "image", "video")`; selain itu raise `ConfigurationError`.
       `media_type="image"` → perilaku identik `discover_images` saat ini.
       `media_type="video"` → hanya `SUPPORTED_VIDEO_EXTENSIONS`.
       `media_type="auto"` → gabungan keduanya.
     - tambah ke tiap record: `"media": "image"` atau `"media": "video"` (berdasarkan ekstensi).
     - pertahankan: sorting `relative_path.lower()`, semantik `limit`, error `UnsupportedImageError`
       untuk single-file tak didukung, `ConfigurationError` untuk path hilang.
     - `discover_images(...)` dipertahankan sebagai wrapper `discover_inputs(..., media_type="image")`
       agar seluruh pemanggil/test lama tidak berubah.
- Urutan perubahan di dalam file: konstanta dulu, lalu fungsi baru, lalu wrapper; tidak ada refactor fungsi lain.
- Behavior yang harus dipertahankan: hasil discovery image-only byte-identik (urutan, limit, error type).
- Error handling / edge case:
  - single file berekstensi video dengan `media_type="image"` → `UnsupportedImageError` (seperti `notes.txt` hari ini).
  - `media_type` invalid dari CLI/config → `ConfigurationError` → CLI exit 2.
  - perbandingan ekstensi case-insensitive (`.MP4` diterima), pola sama seperti image.
- Test: lihat S8 (test discovery video).
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_discovery.py -q`
- Hasil verifikasi yang diharapkan: semua test lama hijau + test video baru hijau.
- Completion criteria: `discover_inputs` ada dengan 3 mode; `discover_images` tetap ada dan tidak berubah perilakunya.
- File/area yang tidak boleh diubah: `image_processing.py`, `inference.py`, exporter, `validation.py`.

### S2 — `VideoConfig`, validasi, mapping CLI

- Tujuan langkah: opsi video masuk ke sistem config berlapis (defaults < YAML < CLI) dengan validasi keras.
- Finding/requirement: F6.
- Dependency: S1 (nama konstanta `DEFAULT_VIDEO_FRAMES`, `VIDEO_MAX_DURATION_SEC` dipakai sebagai default).
- File yang harus dibaca:
  - `src/microstock_metadata/config.py` (seluruh file, 197 baris)
  - `src/microstock_metadata/cli.py` bagian `build_parser` (baris 60-106) dan `_cli_to_config` (baris 109-143)
  - `tests/test_config.py`
- File yang harus diubah: `src/microstock_metadata/config.py` (saja; flag argparse CLI di S7).
- Simbol terkait: `AppConfig`, `ModelConfig`, `ApiConfig`, `build_config`, `validate_config`, `ConfigurationError`.
- Kondisi implementasi saat ini: tidak ada section `video`; `AppConfig` punya field
  `backend/limit/extensions/overwrite/verbose` plus section `model/api/image/metadata/processing/output`.
- Perubahan konkret:
  1. Tambah dataclass baru setelah `ImageConfig`:
     `VideoConfig` dengan field `frames: int = 6`, `max_duration_sec: int = 30`, `max_edge: int = 1024`.
  2. Tambah field `video: VideoConfig = field(default_factory=VideoConfig)` ke `AppConfig`.
  3. `build_config`: daftarkan section `"video"` di tuple `_apply_section` (setara `image`/`metadata`);
     tambah `"media_type"` ke daftar top-level keys (`backend/limit/extensions/...`) di dua tempat
     (loop YAML dan loop CLI).
  4. Tambah field `media_type: str = "auto"` ke `AppConfig`.
  5. `validate_config`, tambah 3 cek (pesan error persis):
     - `media_type not in ("auto","image","video")` → `ConfigurationError("Invalid media_type: ...")`
     - `not 1 <= video.frames <= 12` → `ConfigurationError("--frames must be between 1 and 12")`
     - `video.max_duration_sec < 5` → `ConfigurationError("--video-max-duration must be >= 5 seconds")`
     - `video.max_edge < 128` → `ConfigurationError("--video-max-edge must be >= 128")`
- Urutan perubahan: dataclass → field AppConfig → build_config → validate_config.
- Behavior yang harus dipertahankan: default image-only tidak berubah; `build_config({}, {})` tetap valid;
  precedence defaults < YAML < CLI tetap berlaku untuk section baru.
- Error handling / edge case: YAML section `video: "bukan-mapping"` → `ConfigurationError` via jalur yang sama
  seperti section lain; CLI mapping key unknown → `ConfigurationError("Unknown CLI config key: ...")`.
- Test: lihat S8 (test config video).
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_config.py -q`
- Hasil verifikasi yang diharapkan: test lama hijau + default baru `media_type=="auto"`, `video.frames==6`.
- Completion criteria: `build_config({"video": {"frames": 8}}, {})` menghasilkan `cfg.video.frames == 8`;
  nilai invalid ditolak dengan pesan di atas.
- File/area yang tidak boleh diubah: `cli.py` (di S7), aturan validasi metadata/image yang ada.

### S3 — Prompt `microstock-video-v1`

- Tujuan langkah: model menerima instruksi multi-frame temporal (aksi/gerakan), bukan deskripsi foto statis,
  dengan schema JSON yang sama persis agar parser/validasi lama bisa dipakai ulang.
- Finding/requirement: F4, F9.
- Dependency: tidak ada (independen dari S1/S2; dibutuhkan oleh S7).
- File yang harus dibaca: `src/microstock_metadata/prompts.py` (61 baris), `src/microstock_metadata/constants.py`
  (baris `PROMPT_VERSION`, `API_PROMPT_VERSION`), `tests/test_prompts.py`.
- File yang harus diubah: `src/microstock_metadata/prompts.py` (saja).
- Simbol terkait: `MICROSTOCK_V2`, `MICROSTOCK_V3`, `build_prompt`, `build_retry_prompt`, `RETRY_SUFFIX`.
- Kondisi implementasi saat ini: `build_prompt(version)` hanya kenal `microstock-v1/v3`, default `microstock-v2`;
  shape JSON tercantum di `prompts.py:20-21,41-42`.
- Perubahan konkret:
  1. Tambah konstanta `VIDEO_PROMPT_VERSION = "microstock-video-v1"`.
  2. Tambah `MICROSTOCK_VIDEO_V1` = salinan `MICROSTOCK_V2` dengan 3 edit: (a) kalimat pembuka
     "Analyze the image" → "Analyze the N frames in temporal order; they come from ONE video clip
     (8-10 seconds). Describe the visible ACTION/motion, not a static photo.";
     (b) tambah rule "Title must name the action (verb) plus subject and setting.";
     (c) tambah rule "Keywords: include 3-8 motion/action terms (e.g. walking, pouring, rotating)
     ordered with the rest most-important-first; all other keyword rules unchanged.";
     Shape JSON, daftar kategori, dan larangan nilai placeholder TIDAK diubah.
  3. `build_prompt`: tambah cabang `if version == "microstock-video-v1": return ("microstock-video-v1", MICROSTOCK_VIDEO_V1)`.
     `build_retry_prompt` otomatis ikut karena mendelegasikan ke `build_prompt`.
  4. Jangan ubah `PROMPT_VERSION`/`API_PROMPT_VERSION` default dan string V1/V2/V3 yang ada.
- Urutan perubahan: konstanta versi → teks prompt → cabang builder.
- Behavior yang harus dipertahankan: prompt image (`v1/v2/v3`) byte-identik; `build_prompt()` tanpa argumen tetap return v2.
- Error handling / edge case: versi tak dikenal tetap jatuh ke default v2 (perilaku lama); retry suffix tetap terappend.
- Test: lihat S8 (test prompt video).
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_prompts.py -q`
- Hasil verifikasi yang diharapkan: hijau; `build_prompt("microstock-video-v1")` return teks berisi "temporal order".
- Completion criteria: schema JSON di prompt video identik dengan V2 (bandingkan literal shape).
- File/area yang tidak boleh diubah: `constants.py` (default versi), `parsing.py`, `validation.py`, `normalization.py`.

### S4 — Modul baru `video_processing.py` (ffprobe + ffmpeg, uniform 6 frame)

- Tujuan langkah: mengubah 1 file video menjadi N frame PIL siap-inference, memakai ffmpeg sistem,
  tanpa dependency pip baru.
- Finding/requirement: F2, F7 (ffmpeg 9.0.2 + ffprobe di PATH; quirk `-frames:v 1 -update 1`;
  pola Temp nama-pendek untuk MAX_PATH seperti `Upscale.ps1`).
- Dependency: S1 (ekstensi video), S2 (nilai `frames/max_duration_sec/max_edge`).
- File yang harus dibaca:
  - `src/microstock_metadata/image_processing.py` (38 baris — pola `ImageReadError`, EXIF/RGB/resize)
  - `src/microstock_metadata/exceptions.py` (gunakan `ImageReadError` untuk semua kegagalan video agar
    pemanggil di `cli.py` tidak perlu cabang error baru)
  - `C:\Side\Microstock\Export-VectorPreview.ps1` baris 131-156 (pola flag ffmpeg 9 + log temp)
  - `src/microstock_metadata/cli.py` baris 168-173 (`_sha256_file`, dipakai untuk resume; modul ini tidak hash ulang)
- File yang harus diubah/dibuat: BUAT `src/microstock_metadata/video_processing.py`; tidak ada file lain di langkah ini.
- Simbol terkait: `normalize_image`, `ImageReadError`, `shutil`, `subprocess`, `tempfile`, `PIL.Image`.
- Kondisi implementasi saat ini: modul belum ada; frame extraction belum ada di mana pun di generator.
- Perubahan konkret (spesifikasi fungsi):
  1. `def probe_video(path: str) -> dict` — jalankan `ffprobe -v error -show_entries format=duration,size
     -show_entries stream=width,height,avg_frame_rate -of json <path>` via `subprocess.run`
     (timeout 30 dtk, tanpa `shell=True`). Return `{duration_sec: float|None, width, height, size_bytes}`.
     `FileNotFoundError` (binary hilang) → raise `ImageReadError("ffmpeg/ffprobe not found in PATH ...")`.
     Returncode != 0 atau JSON tak valid → `ImageReadError("Cannot probe video ...: <stderr 300 char>")`.
  2. `def extract_frames(path: str, count: int = 6, max_edge: int = 1024) -> list[PIL.Image]`:
     - panggil `probe_video`; jika `duration_sec` diketahui dan `> max_duration_sec` (diterima sebagai argumen,
       default 30) → raise `ImageReadError("Video too long ...")`. Durasi `None` = lanjut (jangan tolak).
     - hitung timestamp uniform: `t_i = duration*(i+0.5)/count` bila durasi diketahui; bila tidak,
       fallback `fps = count/10.0` dengan filter `fps=...,scale` — dokumentasikan fallback ini di docstring.
     - untuk tiap `i`: `ffmpeg -y -loglevel warning -ss <t> -i <path> -frames:v 1 -update 1 -q:v 2 <tmp_i.jpg>`
       (flag `-frames:v 1 -update 1` wajib karena quirk ffmpeg 9 image2).
       Simpan ke dir temp dengan nama pendek (`frame_00.jpg`, bukan path panjang) untuk hindari MAX_PATH.
     - buka tiap JPG dengan `PIL.Image.open + load`, terapkan EXIF transpose + konversi RGB + edge-resize
       (duplikasi 10 baris logika `normalize_image`, JANGAN import-mutasi fungsi itu karena ia buka path sendiri).
     - kembalikan list PIL yang sudah terbuka (caller yang close). Jika `count` frame gagal semua →
       `ImageReadError`; jika sebagian gagal → lanjut dengan yang berhasil selama >= 1, dan catat jumlahnya
       di return kedua: `-> tuple[list[Image], int]` = (frames, attempted).
     - bersihkan SEMUA file temp dalam `finally` (setara pola `.tmp` di `Export-VectorPreview.ps1`).
  3. Timeout per invocasi ffmpeg 60 dtk (`subprocess.TimeoutExpired` → `ImageReadError`).
     Jangan log full command dengan path user lebih dari basename (hindari kebocoran PII di log).
- Urutan implementasi di file: import → `probe_video` → `extract_frames` → helper `_ffmpeg()` kecil bila perlu.
- Behavior yang harus dipertahankan: tidak ada perilaku image yang tersentuh (file baru, fungsi baru).
- Error handling / edge case:
  - video korup/0-byte → `ImageReadError` (di CLI menjadi status failed, exit 1, batch lanjut).
  - video > `max_duration_sec` → `ImageReadError` dengan pesan memuat durasi aktual.
  - ffmpeg hilang di tengah → `ImageReadError` jelas, bukan traceback subprocess.
  - file temp selalu terhapus walau ekstraksi gagal di tengah.
- Test: lihat S8 (test video_processing dengan mock subprocess + 1 video sintetis kecil bila ffmpeg ada).
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_video_processing.py -q`
- Hasil verifikasi yang diharapkan: hijau tanpa ffmpeg asli (mock), plus 1 test integrasi yang skip bila ffmpeg absen.
- Completion criteria: `extract_frames` return 6 PIL RGB dengan longest-edge ≤ `max_edge` untuk klip uji;
  tidak ada file sisa di temp dir setelah return/raise.
- File/area yang tidak boleh diubah: semua file selain file baru ini.

### S5 — Multi-image payload di `api_inference.py`

- Tujuan langkah: backend `api` dapat mengirim N frame dalam 1 request chat-completions.
- Finding/requirement: F3 (sisi API saja).
- Dependency: S4 (list PIL sebagai input). Independen dari S3/S6.
- File yang harus dibaca:
  - `src/microstock_metadata/api_inference.py` baris 193-325 (`generate_with_fallback`, `image_to_data_uri`,
    `_post_json`, `generate_once`, `_payload`)
  - `tests/test_api_inference.py` (khusus `test_request_shape_and_auth`, `test_fallback_uses_first_healthy`)
- File yang harus diubah: `src/microstock_metadata/api_inference.py` (saja).
- Simbol terkait: `generate_once`, `generate_with_fallback`, `_payload`, `image_to_data_uri`.
- Kondisi implementasi saat ini: `_payload(model, prompt, pil_image, ...)` membangun 1 blok `image_url` +
  1 blok `text` (`api_inference.py:309-324`); `generate_once(pil_image, ...)` dan
  `generate_with_fallback(pil_image, ...)` terima 1 PIL.
- Perubahan konkret:
  1. `_payload(model_name, prompt_text, pil_images, max_tokens, temperature)`: parameter ketiga menjadi
     `pil_image | list`. Normalisasi di baris pertama: `frames = [pil_image] if single else list(pil_image)`;
     `if not frames: raise InferenceError("No frames to send")`.
     `content = [{"type":"image_url","image_url":{"url": image_to_data_uri(f)}} for f in frames]
     + [{"type":"text","text": prompt_text}]` (urutan: semua image dulu, teks terakhir — sama seperti single-image hari ini).
  2. `generate_once` dan `generate_with_fallback`: ganti nama parameter `pil_image` → `pil_images`
     (terima single PIL atau list; teruskan apa adanya ke `_payload`/rekursi). Isi logika retry/KeyPool/
     `_RetryableError`/`_AuthError` TIDAK diubah satu baris pun.
  3. `image_to_data_uri` tidak diubah.
- Urutan perubahan: `_payload` → `generate_once` → `generate_with_fallback`.
- Behavior yang harus dipertahankan: request single-image byte-identik (1 image_url + 1 text, urutan sama);
  semua test API lama harus hijau tanpa modifikasi.
- Error handling / edge case: list kosong → `InferenceError` (bukan `IndexError`);
  PIL tertutup/rusak saat encode → biarkan `OSError` membungkus jadi `InferenceError` via jalur `_post_json`? Tidak —
  encode terjadi di `_payload` sebelum POST: bungkus loop encode dengan try/except `Exception` →
  raise `InferenceError("Cannot encode frame ...")`. Maksimal 12 frame divalidasi di config (S2), bukan di sini.
- Test: lihat S8 (test payload multi-image).
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_api_inference.py -q`
- Hasil verifikasi yang diharapkan: 15 test lama hijau + test multi-image baru hijau.
- Completion criteria: `generate_once([img1, img2], ...)` menghasilkan body dengan 2 blok `image_url` + 1 `text`;
  `generate_once(img, ...)` tetap 1+1.
- File/area yang tidak boleh diubah: `inference.py` (jalur lokal), `model_loader.py`, `parsing.py`,
  logika retry/auth KeyPool.

### S6 — Field schema + kolom CSV

- Tujuan langkah: hasil video tercatat (media/durasi/jumlah frame) tanpa merusak pembaca output lama.
- Finding/requirement: F5, F8.
- Dependency: tidak ada (independen; dibutuhkan oleh S7).
- File yang harus dibaca:
  - `src/microstock_metadata/schemas.py` (63 baris)
  - `src/microstock_metadata/exporters.py` baris 75-140 (`CSV_COLUMNS`, `write_metadata_csv`)
  - `tests/test_exporters.py`
- File yang harus diubah:
  - `src/microstock_metadata/schemas.py`
  - `src/microstock_metadata/exporters.py`
- Simbol terkait: `ProcessingResult`, `CSV_COLUMNS`, `write_metadata_csv`, `write_metadata_json`.
- Kondisi implementasi saat ini: `ProcessingResult` tidak punya field media; `CSV_COLUMNS` berakhir di
  `duration_seconds, backend, provider` (`exporters.py:97-99`).
- Perubahan konkret:
  1. `schemas.py`, setelah field `provider` (baris 59), tambah dengan default (agar record lama tetap valid):
     `media_type: str = "image"`, `video_duration_sec: float | None = None`, `frame_count: int = 0`.
  2. `exporters.py`: tambah 3 nama ke AKHIR `CSV_COLUMNS` (jangan sisip di tengah agar indeks kolom lama stabil):
     `"media_type", "video_duration_sec", "frame_count"`. Tambah 3 sel terkait di `write_metadata_csv`
     dalam urutan sama (`_cell(r.media_type)`, `_cell(round(...) if not None else "")`, `_cell(r.frame_count)`).
     `write_metadata_json`/`write_failed_json`/`summarize` tidak diubah (json serialisasi otomatis via `model_dump`).
- Urutan perubahan: schema dulu, lalu kolom + baris writer.
- Behavior yang harus dipertahankan: CSV lama (tanpa 3 kolom) tetap bisa dibaca konsumen? Tidak — arah kompatibelnya:
  writer baru selalu tulis 3 kolom tambahan; record image mengisi `media_type=image`, durasi kosong, frame 0.
  BOM, quoting, formula guard, urutan kolom lama tidak berubah.
- Error handling / edge case: `video_duration_sec=None` → sel kosong (bukan "None"); `frame_count` selalu int.
- Test: lihat S8 (test exporter video).
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_exporters.py -q`
- Hasil verifikasi yang diharapkan: hijau; header CSV = header lama + 3 nama di akhir.
- Completion criteria: `ProcessingResult(...)` tanpa argumen baru tetap valid; CSV punya tepat 3 kolom tambahan di akhir.
- File/area yang tidak boleh diubah: `csv_embed.py` + `scripts/csv_to_embed.py` (konsumen CSV dibiarkan;
  kolom baru diabaikan oleh `csv.DictReader` karena akses by-name).

### S7 — Wiring `cli.py`: cabang video, guard local-backend, doctor ffmpeg

- Tujuan langkah: perintah `generate` end-to-end untuk video (api-only) + `doctor` melaporkan kesiapan video.
- Finding/requirement: F6, F7, F8, D2.
- Dependency: S1–S6 (semua). Ini langkah integrasi; kerjakan terakhir sebelum test.
- File yang harus dibaca:
  - `src/microstock_metadata/cli.py` seluruhnya (649 baris; fokus: `build_parser` 60-106,
    `_cli_to_config` 109-143, `cmd_generate` 176-281, `_process_one` 284-455, `cmd_doctor` 529-587)
  - `src/microstock_metadata/constants.py` (`VIDEO_PROMPT_VERSION` dari S3 — sebenarnya di `prompts.py`)
- File yang harus diubah: `src/microstock_metadata/cli.py` (saja).
- Simbol terkait: `build_parser`, `_cli_to_config`, `cmd_generate`, `_process_one`, `cmd_doctor`,
  `discover_inputs`, `extract_frames`, `probe_video`, `generate_with_fallback`, `EXIT_CONFIG_ERROR`.
- Kondisi implementasi saat ini: `cmd_generate` memanggil `discover_images` (baris 188),
  `_process_one` memanggil `normalize_image` (baris 326) lalu infer single PIL (baris 334-404).
- Perubahan konkret:
  1. `build_parser` → subparser `generate`, setelah `--extensions` tambah:
     `--media-type` (choices image/video/auto, default None),
     `--frames` (type int, default None), `--video-max-duration` (type int),
     `--video-max-edge` (type int). Mapping di `_cli_to_config`:
     `"media_type": "media_type"`, `"frames": "video.frames"`,
     `"video_max_duration": "video.max_duration_sec"`, `"video_max_edge": "video.max_edge"`.
  2. `cmd_generate`: ganti `discover_images(...)` → `discover_inputs(...,
     media_type=cfg.media_type ...)`. Setelah penentuan backend: jika ada item `media=="video"`
     dan `cfg.backend != "api"` → print `"Video input requires --backend api ..."` ke stderr,
     return `EXIT_CONFIG_ERROR` SEBELUM `load_model` (agar tidak load model sia-sia; cerminan pola dry-run).
     Untuk item video pilih `prompt_version = "microstock-video-v1"` (bukan `API_PROMPT_VERSION`);
     item image tetap seperti hari ini.
  3. `_process_one`: di titik `normalize_image` (baris 326), cabang:
     `if item.get("media") == "video" and use_api:` →
     `frames, attempted = extract_frames(item["path"], count=cfg.video.frames,
     max_edge=cfg.video.max_edge, max_duration_sec=cfg.video.max_duration_sec)`;
     loop inference memanggil `generate_with_fallback(frames, ...)` (bukan single `pil`);
     `pil.close()` di `finally` menjadi loop close semua frame; `result` diisi
     `media_type="video"`, `video_duration_sec=<dari probe>`, `frame_count=len(frames)`,
     `image_width/height` = dimensi video dari probe, `processed_width/height` = frame pertama.
     Jalur image tidak tersentuh. `store.save`, `_flush_outputs`, `cleanup_memory` tidak berubah.
  4. `cmd_doctor`: tambah 2 cek via `shutil.which`: `ffmpeg` dan `ffprobe`
     (`OK <path>` / `!! not in PATH (video input unavailable)`). Jangan ubah cek lain.
- Urutan perubahan: parser+mapping → `cmd_generate` (discovery+guard) → `_process_one` → `cmd_doctor`.
- Behavior yang harus dipertahankan: alur image byte-perilaku sama (prompt v2/v3, retry loop, resume skipped
  dengan `_load_prior_items`, checkpoint setiap item, exit code 0/1/2/3/4, log summary).
- Error handling / edge case:
  - video korup/terlalu panjang/ffmpeg hilang → `ImageReadError` dari S4 → `_failed(...)` →
    status failed, batch lanjut, exit 1 (bukan abort).
  - video + local backend → exit 2 dengan pesan satu baris (keputusan D2; bukan fallback diam-diam).
  - frame PIL selalu di-close (image dan video) termasuk jalur exception.
- Test: lihat S8 (test CLI video).
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_cli.py tests/test_integration.py -q`
  lalu `run.bat doctor` (cek baris ffmpeg/ffprobe).
- Hasil verifikasi yang diharapkan: test lama hijau; doctor menampilkan 2 baris baru.
- Completion criteria: `generate <clip.mp4> --backend api --dry-run` list file;
  generate mocked (S8) menghasilkan item `media_type=video, frame_count=6`.
- File/area yang tidak boleh diubah: `inference.py`, `model_loader.py`, `checkpoint.py`,
  `validation.py`, `normalization.py`, `parsing.py`, logika retry image.

### S8 — Test baru + update test lama

- Tujuan langkah: setiap finding punya verifikasi; suite tetap hijau tanpa binary/network asli.
- Finding/requirement: semua F1–F10 (verifikasi).
- Dependency: S1–S7 selesai.
- File yang harus dibaca: `tests/conftest.py`, `tests/test_*.py` yang relevan per sub-langkah.
- File yang harus diubah/dibuat:
  - BUAT `tests/test_video_processing.py`
  - UBAH `tests/test_discovery.py` (tambah, jangan ubah test lama), `tests/test_config.py`,
    `tests/test_prompts.py`, `tests/test_api_inference.py`, `tests/test_exporters.py`, `tests/test_cli.py`
- Perubahan konkret (spesifik, tanpa abstraksi):
  1. `test_video_processing.py` (baru):
     - `test_probe_parses_ffprobe_json`: mock `subprocess.run` return JSON
       `{"format": {"duration": "9.5"}, "streams": [{"width": 1280, "height": 720}]}` →
       assert `duration_sec == 9.5`, `width == 1280`.
     - `test_probe_failure_raises`: mock returncode 1 + stderr → `pytest.raises(ImageReadError)`.
     - `test_extract_uniform_timestamps`: mock `probe_video` (duration 9.0) + mock `subprocess.run`
       catat argumen `-ss` → assert 6 nilai `["0.75","2.25","3.75","5.25","6.75","8.25"]`
       (rumus `(i+0.5)*9/6`), dan PIL hasil di-close test (hindari leak).
     - `test_extract TOO LONG`: mock duration 60 + `max_duration_sec=30` → `ImageReadError` match "too long".
     - `test_missing_binary`: mock `FileNotFoundError` dari subprocess → `ImageReadError` match "not found in PATH".
  2. `test_discovery.py` (tambah 3 test, file lama utuh):
     - direktori berisi `a.jpg` + `b.mp4` (buat `b.mp4` sebagai file kosong — discovery hanya cek ekstensi):
       `discover_inputs(..., media_type="video")` → hanya `b.mp4` dengan `media=="video"`;
       `media_type="image"` → hanya `a.jpg`; `media_type="auto"` → keduanya.
     - `media_type="bogus"` → `ConfigurationError`.
  3. `test_config.py` (tambah 2 test): default `video.frames==6`, `media_type=="auto"`;
     `build_config({"video": {"frames": 99}}, {})` → `ConfigurationError`.
  4. `test_prompts.py` (tambah 1 test): `build_prompt("microstock-video-v1")` → versi sama,
     teks memuat "temporal order" dan shape JSON identik dengan V2 (assert substring
     `{"title": "string"` ada di keduanya).
  5. `test_api_inference.py` (tambah 1 test, tiru `test_request_shape_and_auth`):
     `generate_once([img1, img2], ...)` dengan `urlopen` mock → body content punya
     tepat 2 `image_url` (keduanya prefix `data:image/jpeg;base64,`) + 1 `text` di posisi terakhir.
  6. `test_exporters.py` (tambah 1 test): `_ok(media_type="video", video_duration_sec=9.5, frame_count=6)` →
     header = header lama + `["media_type","video_duration_sec","frame_count"]`; sel sesuai.
  7. `test_cli.py` (tambah 2 test, tiru `test_api_backend_skips_local_model` + `fake_stack`):
     - `test_video_api_mocked`: monkeypatch `cli.discover_inputs`? TIDAK — buat file `clip.mp4` kosong
       tidak bisa diprobe. Sebaliknya monkeypatch `microstock_metadata.cli.extract_frames`? Fungsi itu
       diimport di dalam `_process_one` — jadi monkeypatch atribut modul `video_processing.extract_frames`
       return `([Image.new("RGB",(64,48))]*6, 6)` dan `probe` implisit; monkeypatch
       `api_inference.generate_with_fallback` return `(VALID_MODEL_JSON, "p", "m")`;
       panggil `cli.main(["generate", <file.mp4>, --backend api, --min-keywords 3])` → exit 0,
       item `media_type=="video"`, `frame_count==6`, `prompt_version=="microstock-video-v1"`.
     - `test_video_local_backend_rejected`: `cli.main(["generate", <file.mp4>, --backend local])` → exit 2
       tanpa memanggil `load_model` (monkeypatch boom seperti `test_dry_run_loads_no_model`).
- Input test dan expected result: tercantum per test di atas (nilai literal, bukan "data valid").
- Command verifikasi: `.venv\Scripts\python -m pytest tests/ -q` (full suite; `test_real_model.py` sudah ter-mark
  dan tidak jalan by default — pertahankan begitu).
- Hasil verifikasi yang diharapkan: seluruh suite hijau; tidak ada test yang butuh network/GPU/ffmpeg asli
  kecuali 1 test integrasi opsional yang skip bila `shutil.which("ffmpeg")` None.
- Completion criteria: coverage per finding: F1 (test discovery), F3 (test payload), F4 (test prompt),
  F5 (test exporter), F6 (test config+CLI guard), F7 (test video_processing mock), F8 (suite lama hijau).
- File/area yang tidak boleh diubah: `tests/test_real_model.py`, `tests/test_integration.py` (kecuali bila perlu
  tambah 1 test video mocked — prefer `test_cli.py`), fixture `conftest.py` boleh DITAMBAH fixture baru
  tapi fixture lama (`img_dir`, `good_jpg`, `VALID_MODEL_JSON`) tidak boleh diubah.

### S9 — Docs + contoh config + verifikasi akhir

- Tujuan langkah: operator bisa memakai fitur tanpa membaca kode; contoh config tetap valid.
- Finding/requirement: dokumentasi perilaku baru (D1–D4, guard, kolom CSV baru).
- Dependency: S1–S8 selesai dan suite hijau.
- File yang harus dibaca: `README.md` (bagian 9a/10/11 sebagai pola), `examples/sample_config.yaml`.
- File yang harus diubah:
  - `README.md` (tambah subseksi `9c. Video input (API-only, uniform frames)` setelah 9b; jangan ubah 9a/9b selain referensi)
  - `examples/sample_config.yaml` (tambah block `video:` + komentar; tambah `media_type: auto` top-level)
- Perubahan konkret:
  1. `sample_config.yaml`: setelah block `image:`, tambah:
     `video: {frames: 6, max_duration_sec: 30, max_edge: 1024}` + 3 baris komentar
     (frames 1–12; guard durasi; butuh ffmpeg+ffprobe di PATH). Top-level tambah `media_type: auto`
     dengan komentar `# image | video | auto`.
  2. `README.md` seksi 9c berisi: prasyarat ffmpeg (`run.bat doctor`), contoh
     `run.bat generate .\clips --media-type video --backend api --frames 6`,
     tabel kolom CSV baru, perilaku guard (video+local → exit 2; video > max_duration → failed),
     dan catatan visual-only. Maksimal ~40 baris agar README tidak menggembung.
- Behavior yang harus dipertahankan: contoh config lama tetap load (`build_config` backward-compat);
  tidak ada perubahan perilaku runtime di langkah ini.
- Command verifikasi:
  1. `.venv\Scripts\python -m pytest tests/ -q` → hijau penuh.
  2. `run.bat doctor` → baris `ffmpeg`/`ffprobe` OK.
  3. `run.bat generate <satu-clip-mp4-asli-8-10dtk> --output-dir .\output-api --backend api --media-type video --dry-run` → `would process: <nama>`.
  4. (Bila kunci API tersedia) 1 file asli tanpa `--dry-run` → `metadata.csv` berisi `media_type=video`, `frame_count=6`.
- Hasil verifikasi yang diharapkan: (1) exit 0; (2) doctor OK; (3) dry-run exit 0; (4) CSV punya 3 kolom baru terisi.
- Completion criteria: README 9c ada; `sample_config.yaml` load tanpa `ConfigurationError`;
  suite hijau; dry-run video OK.
- File/area yang tidak boleh diubah: `.env`, `.env.example` (tanpa kunci baru), `LICENSE`, `requirements*.txt`
  (D3: tanpa dep baru — tegaskan; bila implementor tergoda tambah pip package, tolak),
  script PowerShell root, `dist/`, `output*/`.

## Risks

- R1 — ffmpeg hilang/rusak di mesin target → semua video gagal. Mitigasi: `doctor` + fail-fast jelas (S7);
  tidak ada fallback senyap ke frame tunggal.
- R2 — Biaya token ~6× per klip (6 frame). Mitigasi: `video.max_edge=1024` default + `frames` dibatasi 1–12 (S2).
- R3 — `avg_frame_rate`/`duration` aneh (VFR, "0/0") → timestamp NaN. Mitigasi: fallback fps + guard `None`
  di S4; uji dengan 1 klip VFR bila tersedia.
- R4 — Model API menolak N image sekaligus (batas provider). Mitigasi: `frames` kecil (6) + error provider
  mengalir ke jalur failed+retry yang sudah ada; tidak perlu kode khusus.
- R5 — Quirk ffmpeg 9 image2 tanpa `-frames:v 1 -update 1` → error pola sequence. Mitigasi: flag wajib di S4.
- R6 — MAX_PATH pada path klip panjang → ekstraksi gagal. Mitigasi: output frame selalu nama pendek di temp (S4).

## Progress Log

- 2026-10-09 09:00:00 — Plan dibuat dari analisis + keputusan D1–D4; belum ada implementasi.
- 2026-10-09 16:41:00 — S1–S9 selesai diimplementasikan dan diverifikasi: full suite 103 passed, doctor mendeteksi ffmpeg/ffprobe OK, dry-run video berhasil.

## Notes

- Keputusan eksplisit yang diambil di plan ini (agar model kecil tidak perlu desain ulang):
  N1: video+local → exit 2 (bukan multi-image lokal; alasan: VRAM 4 GB + scope atomik).
  N2: error video (korup/kepanjangan/ffmpeg hilang) → status failed per-item, batch lanjut (exit 1 bila ada gagal).
  N3: field baru di AKHIR CSV + default schema (alasan: kompatibilitas pembaca lama).
  N4: tanpa pip package baru (alasan: ffmpeg sistem sudah dijamin preflight workspace).
- Prompt video memakai schema JSON identik V2 sehingga `parsing.py`/`validation.py`/`normalization.py`
  dipakai ulang tanpa perubahan.
- Jika di tengah implementasi ditemukan bahwa provider API menolak >4 image: JANGAN ubah desain di tempat —
  catat sebagai blocker di plan ini (tambah entri Progress Log) dan turunkan default `frames` ke 4 via S2.

## Handoff Checklist (untuk model implementor)

- [x] Baca S1–S9 berurutan; jangan loncat (dependency: S7 butuh S1–S6; S8 butuh S7).
- [x] Sebelum ubah file apapun, baca file target lengkap (bukan cuplikan) sesuai daftar "File yang harus dibaca".
- [x] Patuhi "File/area yang tidak boleh diubah" di tiap langkah; bila terpaksa menyentuh, hentikan dan catat blocker.
- [x] Setiap langkah selesai → jalankan "Command verifikasi" langkah itu; lanjut hanya bila hasilnya sesuai ekspektasi.
- [x] Test baru harus tanpa network/GPU/ffmpeg-asli (mock `subprocess`/`urlopen`); 1 test integrasi boleh skip bila ffmpeg absen.
- [x] Setelah S9: full suite hijau + `run.bat doctor` + dry-run video 1 file asli.
- [x] Jangan: menambah pip dependency, mengubah aturan validasi/metadata, mengubah exit code,
      menyentuh `.env`/secrets, staging/commit file selain yang diminta pemberi tugas.
- [x] Serahkan kembali: daftar file diubah, hasil tiap command verifikasi (copy output), dan sisa blocker/open question (bila ada).
