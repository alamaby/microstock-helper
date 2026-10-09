# Video 4-Platform Optimization Implementation Plan (Adobe / Dreamstime / Vecteezy / Pixabay)

Created: 2026-10-09 12:00:00

## Objective

Extend `microstock-metadata-generator` so one video run produces portal-ready metadata for Adobe Stock, Dreamstime, Vecteezy, and Pixabay for AI-generated clips, without breaking existing image flow, resume/checkpoint behavior, or CSV/JSON contracts.

Non-goal: this plan does NOT implement changes. It is a step-by-step handoff for a smaller model to execute deterministically.

## Scope

- In scope: `microstock-metadata-generator/src/microstock_metadata/` modules (`platforms` baru, `schemas.py`, `video_processing.py`, `cli.py`, `normalization.py`, `prompts.py`, `csv_embed.py`, `exporters.py`, `config.py`), `scripts/csv_to_embed.py`, `examples/sample_config.yaml`, `README.md` §9d, `tests/`.
- Out of scope: model weights, `.venv/`, `output/`, `output-api/`, PowerShell scripts at workspace root (`Embed-JpgMetadata.ps1`, `Orchestrate-Stock.ps1`, etc.), git history, any live portal upload automation.

## Milestones

1. Baseline green (S0) — prove current tests pass before touching code.
2. Data + schema foundation (S1–S2) — platform profiles + AI/release fields.
3. Video tech gate (S3–S4) — ffprobe extension + soft-gate wiring.
4. Metadata quality (S5–S6) — platform-aware truncation + video prompt v2.
5. Export (S7–S8) — 4-platform video CSVs + new columns backward-compatible.
6. Docs + full verification (S9–S10).

## Tasks

- [x] S0 Baseline verification (no code change)
- [x] S1 Add per-platform profiles module + config plumbing
- [x] S2 Add AI/release fields to schemas
- [x] S3 Extend ffprobe parsing + video gate helper
- [x] S4 Wire gate into CLI video path (soft-gate)
- [x] S5 Platform-aware normalization
- [x] S6 Add microstock-video-v2 prompt
- [x] S7 Four-platform video exporter + CLI flags
- [x] S8 Export new columns (backward compatible)
- [x] S9 Docs + sample config + examples
- [x] S10 Full verification + handoff

## Risks

- Live portal docs were unreachable during analysis (websearch empty 4/4; webfetch 403 helpx.adobe.com/dreamstime/pixabay, 404 Vecteezy guesses). All numeric limits below are knowledge-cutoff + local-code evidence and MUST be treated as defaults, not gospel. Mitigation: constants isolated in one new module (S1) so portal correction = 1-file edit.
- Adobe CSV spec wants category NUMBERS but code uses NAMES (`csv_embed.py` comment lines 28-31). Mitigation: S7 keeps names + adds number column left blank, never invents numbers.
- Over-strict video gate could reject valid vertical 9:16 clips. Mitigation: S4 implements soft-gate (`needs_review`, never hard-fail except unreadable container).

## Progress Log

- 2026-10-09 12:00:00 — Plan created from analysis + traceability; no implementation done.
- 2026-10-09 17:12:00 — S0 Baseline verification PASSED: pytest 103 passed, 1 deselected in 17.31s; run.bat doctor OK (ffmpeg/ffprobe found and OK, offline-ready yes).
- 2026-10-09 17:13:50 — S1 Added platforms.py, config.py platform field + validation, sample_config.yaml comment. Verified tests/test_platforms.py & tests/test_config.py (11 passed).
- 2026-10-09 17:14:38 — S2 Added is_ai_generated, needs_model_release, needs_property_release to ProcessingResult schema. Verified tests/test_exporters.py (5 passed).
- 2026-10-09 17:16:19 — S3 Extended probe_video with codec, fps, container; added assess_video. Verified tests/test_video_processing.py (7 passed).
- 2026-10-09 17:18:31 — S4 Wired video gate into CLI video path with vertical HD exemption, merged review_reasons, populated AI/release fields. Verified tests/test_cli_video_gate.py & tests/test_cli.py (13 passed).
- 2026-10-09 17:19:34 — S5 Added resolve_limits in normalization.py, wired into cli.py. Verified tests/test_normalization.py & tests/test_config.py (19 passed).
- 2026-10-09 17:20:25 — S6 Added MICROSTOCK_VIDEO_V2 and VIDEO_PROMPT_V2 in prompts.py. Verified tests/test_prompts.py (7 passed).
- 2026-10-09 17:22:48 — S7 Added convert_video_rows, convert_video_file, updated scripts/csv_to_embed.py with 4 platforms. Verified tests/test_csv_embed.py & tests/test_csv_embed_video.py (7 passed), --help verified.
- 2026-10-09 17:24:06 — S8 Appended is_ai_generated, needs_model_release, needs_property_release to CSV_COLUMNS and write_metadata_csv. Verified tests/test_exporters.py (6 passed).
- 2026-10-09 17:25:17 — S9 Added README section 9d, updated sample_config.yaml, added sample_video_output.json. Verified JSON validity.
- 2026-10-09 17:26:25 — S10 Full verification PASSED: full pytest suite 121 passed, 1 deselected in 20.51s; csv_to_embed.py --help verified; run.bat doctor OK (offline-ready yes).

## Notes

- Traceability: F1 Adobe strict (70/25-49/phrase) / F2 Dreamstime single-word ≤70 / F3 Vecteezy phrase tags / F4 Pixabay minimal tags / F5 single global profile / F6 no tech gate / F7 no AI-release fields / F8 exporter only 2-platform JPG / F9 video prompt lacks camera-vs-subject split / F10 Adobe category names-vs-numbers debt.
- Design decisions already fixed (do not re-decide): baseline = Adobe-strict then derive variants; video gate = soft-gate; new schema fields default safe (`is_ai_generated=True` for video rows only); new CSV columns appended at end.
- Open questions / blockers: see §Open Questions at end. Do NOT silently choose.

---

## STEP S0 — Baseline verification (no code change)

- Tujuan: buktikan repo hijau sebelum menyentuh kode; kunci command verifikasi.
- Finding/requirement: prerequisite semua langkah; memastikan failure sesudahnya = regresi baru.
- Dependency: tidak ada.
- File yang harus dibaca:
  - `microstock-metadata-generator/pyproject.toml` (lines 25-30 pytest config)
  - `microstock-metadata-generator/run.bat` (venv runner)
  - `microstock-metadata-generator/tests/conftest.py`
- File yang harus diubah: TIDAK ADA.
- Simbol terkait: n/a.
- Kondisi saat ini: suite `pytest` dengan `addopts = "-m 'not real_model'"`, `testpaths = ["tests"]`.
- Perubahan konkret: TIDAK ADA perubahan kode.
- Urutan perubahan: n/a.
- Behavior dipertahankan: semua.
- Error handling/edge: jika `.venv\Scripts\python.exe` hilang → STOP, catat blocker, jangan `pip install` sendiri.
- Test tambah/update: TIDAK ADA.
- Input/expected: n/a.
- Command verifikasi (jalankan dari `microstock-metadata-generator/`):
  1. `.venv\Scripts\python -m pytest -q`
  2. `run.bat doctor`
- Hasil yang diharapkan:
  1. `passed` semua, `0 failed`, tidak ada `real_model` yang jalan.
  2. `doctor` mencetak tabel OK, `ffmpeg/ffprobe` boleh `!! not in PATH` (dicatat, bukan gagal).
- Completion criteria: kedua command selesai, output disalin ke Progress Log plan.
- Jangan ubah: file apa pun, `.venv/`, `output/`.

---

## STEP S1 — Per-platform profiles module + config plumbing

- Tujuan: isolasi semua angka batas portal di satu modul agar koreksi portal = 1-file edit.
- Finding: F1, F2, F3, F4, F5, F10.
- Dependency: S0.
- File yang harus dibaca:
  - `src/microstock_metadata/constants.py` (lines 14-18 limits, 25-46 CATEGORIES)
  - `src/microstock_metadata/config.py` (lines 46-52 MetadataConfig, 86-100 AppConfig, 123-158 build_config)
  - `src/microstock_metadata/csv_embed.py` (lines 17-53 STOPWORDS, maps)
  - `examples/sample_config.yaml` (lines 46-51)
- File yang harus diubah:
  1. BUAT `src/microstock_metadata/platforms.py` (baru)
  2. EDIT `src/microstock_metadata/config.py` (tambah field saja)
  3. EDIT `examples/sample_config.yaml` (tambah blok komentar saja)
- Simbol terkait: `constants.TITLE_MAX_LENGTH`, `constants.DESCRIPTION_MAX_LENGTH`, `constants.KEYWORD_MIN_TARGET`, `constants.KEYWORD_MAX_DEFAULT`, `config.MetadataConfig`, `config.AppConfig`, `csv_embed.STOPWORDS`, `csv_embed.ADOBE_CATEGORY_MAP`.
- Kondisi saat ini: satu global `title_max=70, desc_max=200, min=25, max=49`; tidak ada konsep platform; `ADOBE_CATEGORY_MAP` nama-bukan-nomor.
- Perubahan konkret:
  1. Buat `platforms.py` dengan isi persis:
     ```python
     """Per-platform publishing profiles. Defaults from knowledge cutoff + local evidence; verify in portals before tightening."""
     PLATFORMS = {
       "adobe": {"title_max": 70, "description_max": 200, "kw_min": 25, "kw_max": 49, "kw_style": "phrase", "category_system": "adobe_portal_names"},
       "dreamstime": {"title_max": 200, "description_max": 200, "kw_min": 10, "kw_max": 70, "kw_style": "single", "category_system": "dreamstime_web"},
       "vecteezy": {"title_max": 70, "description_max": 200, "kw_min": 5, "kw_max": 50, "kw_style": "phrase", "category_system": "vecteezy_web"},
       "pixabay": {"title_max": 100, "description_max": 200, "kw_min": 5, "kw_max": 25, "kw_style": "phrase", "category_system": "none"},
     }
     VECTEEZY_CATEGORY_MAP = {}  # kosong disengaja; diisi S7 dari peta manual, jangan tebak
     PIXABAY_MAX_TAGS = 25
     ```
  2. `config.py`: di `MetadataConfig` tambah SATU field `platform: str = "adobe"`; di `validate_config()` tambah cek `if cfg.metadata.platform not in ("adobe","dreamstime","vecteezy","pixabay","all"): raise ConfigurationError("--platform must be one of ...")`. Di `build_config()` tidak perlu mapping baru karena `_apply_section(target...)` sudah generik untuk section `metadata`. Di `cli.py` JANGAN tambah flag di langkah ini (ditunda S7) agar diff atomik.
  3. `sample_config.yaml`: tambah di bawah blok `metadata:` komentar `# platform: adobe  # adobe|dreamstime|vecteezy|pixabay|all (S7 memakai all)`.
- Urutan perubahan dalam file: `platforms.py` dulu → `config.py` field → `config.py` validasi → yaml komentar.
- Behavior dipertahankan: default `platform="adobe"` = perilaku existing (70/200/25-49); `build_config({}, {})` tetap lolos test existing.
- Error handling/edge: platform string case-sensitive; input `"Adobe"` → `ConfigurationError` (jangan lower-case diam-diam); `providers`/`metadata` lain tak tersentuh.
- Test tambah/update:
  - TAMBAH `tests/test_platforms.py`:
    - `test_adobe_is_strictest_title`: `assert PLATFORMS["adobe"]["title_max"] == 70`
    - `test_dreamstime_single_style`: `assert PLATFORMS["dreamstime"]["kw_style"] == "single" and PLATFORMS["dreamstime"]["kw_max"] == 70`
    - `test_pixabay_cap_25`: `assert PLATFORMS["pixabay"]["kw_max"] == 25`
    - `test_invalid_platform_rejected`: `with pytest.raises(ConfigurationError): build_config({"metadata": {"platform": "Adobe"}}, {})` dan `build_config({"metadata": {"platform": "tiktok"}}, {})` raise; `build_config({"metadata": {"platform": "pixabay"}}, {}).metadata.platform == "pixabay"`.
- Input/expected: `build_config({}, {})` → `metadata.platform == "adobe"`, `title_max_length == 70` (tidak berubah).
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_platforms.py tests/test_config.py -q`
- Hasil diharapkan: `5 passed` (4 baru + existing config tetap hijau; jumlah existing boleh lebih, yang penting 0 failed).
- Completion criteria: file baru ada, default tak berubah, test baru hijau.
- Jangan ubah: `constants.py` angka existing, `csv_embed.py` logic, `cli.py`, `prompts.py`, `schemas.py`.

---

## STEP S2 — AI/release fields di schema

- Tujuan: bedakan klip AI vs kamera + tandai kebutuhan release agar portal tidak reject diam-diam.
- Finding: F7 (tidak ada `is_ai_generated`/`needs_*_release`).
- Dependency: S0 (independen dari S1, boleh paralel, tapi verifikasi sesudah S1).
- File yang harus dibaca:
  - `src/microstock_metadata/schemas.py` (lines 24-66 ProcessingResult)
  - `src/microstock_metadata/exporters.py` (lines 75-103 CSV_COLUMNS)
  - `tests/test_exporters.py` (helper `_ok`)
- File yang harus diubah: `src/microstock_metadata/schemas.py` SAJA (export kolom ditunda S8).
- Simbol terkait: `schemas.ProcessingResult`, fields `has_recognizable_people`, `possible_trademark`, `media_type`.
- Kondisi saat ini: `ProcessingResult` tidak punya field AI/release; `cli.py:_process_one` mengisi `media_type` tapi tidak menurunkan release flags.
- Perubahan konkret — tambah TIGA field di `ProcessingResult` SETELAH `frame_count` (agar diff di ekor, tidak geser posisi existing):
  ```python
  is_ai_generated: bool = False
  needs_model_release: bool = False
  needs_property_release: bool = False
  ```
  Default `False` agar semua fixture existing tetap valid (Pydantic tidak komplain).
- Urutan: tambah 3 baris setelah `frame_count: int = 0`, sebelum `attempt_count`.
- Behavior dipertahankan: semua konstruksi `ProcessingResult(**base)` existing tetap lolos; JSON existing tanpa 3 key tetap parse (default).
- Error handling/edge: JANGAN set `is_ai_generated=True` di sini (wiring di S4); JANGAN ubah `GeneratedMetadata` (model output tetap murni visual).
- Test tambah/update:
  - TAMBAH ke `tests/test_exporters.py` fungsi baru `test_schema_ai_release_defaults`: `r = _ok(); assert r.is_ai_generated is False and r.needs_model_release is False`; `r2 = _ok(is_ai_generated=True, needs_model_release=True); assert r2.needs_model_release is True`. UPDATE file yang sama saja, jangan buat file baru.
- Input/expected: `_ok()` tanpa argumen baru → 3 field False; dengan argumen → tersimpan + ikut `model_dump()`.
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_exporters.py -q`
- Hasil diharapkan: semua test existing + 1 baru passed.
- Completion criteria: schema punya 3 field, tidak ada test existing rusak.
- Jangan ubah: `exporters.py` (S8), `cli.py` (S4), `normalization.py` (S5).

---

## STEP S3 — Extend ffprobe parsing + video gate helper

- Tujuan: dapatkan codec/fps/container + satu fungsi pure penilai kelayakan portal.
- Finding: F6 (hanya cek durasi atas; tanpa resolusi/codec/fps/min-durasi).
- Dependency: S0.
- File yang harus dibaca:
  - `src/microstock_metadata/video_processing.py` (lines 18-101 probe_video, 104-128 extract_frames guard)
  - `src/microstock_metadata/constants.py` (lines 21-23 ext + durasi)
  - `tests/test_video_processing.py` (mock pola `subprocess.run`)
- File yang harus diubah: `src/microstock_metadata/video_processing.py` SAJA.
- Simbol terkait: `video_processing.probe_video`, `video_processing.extract_frames`, `exceptions.ImageReadError`.
- Kondisi saat ini: `probe_video` query `format=duration,size` + `stream=width,height,avg_frame_rate` tapi MENGABAIKAN `avg_frame_rate`/`codec_name`/`format_name`; `extract_frames` raise bila `duration > max_duration_sec`.
- Perubahan konkret:
  1. Ubah `cmd` ffprobe: tambah `"codec_name"` ke `-show_entries stream=` dan `"format_name"` ke `-show_entries format=`. Tepatnya ganti `"format=duration,size"` → `"format=duration,size,format_name"` dan `"stream=width,height,avg_frame_rate"` → `"stream=width,height,avg_frame_rate,codec_name"`.
  2. Parse tambahan setelah blok width/height existing:
     ```python
     codec = None; fps = None; container = fmt.get("format_name")
     for s in streams:
         if "codec_name" in s: codec = s.get("codec_name"); break
     for s in streams:
         rate = s.get("avg_frame_rate")
         if isinstance(rate, str) and "/" in rate:
             try:
                 num, den = rate.split("/", 1); fps = float(num) / float(den) if float(den) else None
             except (ValueError, ZeroDivisionError): fps = None
             break
     ```
     Kembalikan dict existing DITAMBAH `codec`, `fps`, `container` (jangan hapus key lama).
  3. Tambah fungsi pure BARU di ekor modul:
     ```python
     VIDEO_MIN_WIDTH = 1280
     VIDEO_MIN_HEIGHT = 720
     VIDEO_MIN_DURATION_SEC = 5.0
     VIDEO_ALLOWED_CODECS = ("h264", "hevc", "prores", "mjpeg", "png")
     def assess_video(info: dict) -> list[str]:
         """Return list of soft-gate reason codes; empty = pass. Pure, no I/O."""
         reasons = []
         w, h = info.get("width"), info.get("height")
         if isinstance(w, int) and isinstance(h, int) and (w < 1280 or h < 720):
             reasons.append("below_hd_min")
         dur = info.get("duration_sec")
         if isinstance(dur, (int, float)) and dur < 5.0:
             reasons.append("too_short")
         codec = (info.get("codec") or "")
         if isinstance(codec, str) and codec and codec.lower() not in VIDEO_ALLOWED_CODECS:
             reasons.append("uncommon_codec")
         fps = info.get("fps")
         if isinstance(fps, (int, float)) and (fps < 20 or fps > 70):
             reasons.append("unusual_fps")
         return reasons
     ```
     Catatan: `mjpeg/png` dimasukkan agar frame-extract test dummy tidak kena flag saat unit test (hanya untuk assess, bukan klaim portal terima).
- Urutan dalam file: edit cmd → edit return dict → tambah konstanta + `assess_video` di ekor.
- Behavior dipertahankan: `probe_video` return lama tetap ada (`duration_sec/width/height/size_bytes`); `extract_frames` guard durasi-atas TIDAK diubah di langkah ini.
- Error handling/edge: `avg_frame_rate="0/0"` → fps None (jangan ZeroDivision); `format_name` bisa `"mov,mp4,m4a"` → simpan mentah apa adanya; stream tanpa codec → codec None → tidak flag.
- Test tambah/update — TAMBAH ke `tests/test_video_processing.py`:
  - `test_probe_parses_codec_fps_container`: mock payload `{"format": {"duration": "9.5", "size": "1", "format_name": "mov,mp4"}, "streams": [{"width":1280,"height":720,"avg_frame_rate":"30/1","codec_name":"h264"}]}` → `info["codec"]=="h264"`, `abs(info["fps"]-30.0)<0.01`, `"mp4" in info["container"]`.
  - `test_assess_video_flags`: `assess_video({"width":640,"height":480,"duration_sec":3.0,"codec":"vp9","fps":15})` mengandung `below_hd_min`, `too_short`, `uncommon_codec`, `unusual_fps`; `assess_video({"width":1920,"height":1080,"duration_sec":9.0,"codec":"h264","fps":30.0}) == []`; `assess_video({"width":None,"height":None,"duration_sec":None,"codec":None,"fps":None}) == []` (unknown = pass, jangan false-positive).
- Input/expected: seperti di atas, eksplisit.
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_video_processing.py -q`
- Hasil diharapkan: 5 existing + 2 baru passed.
- Completion criteria: `probe_video` kembalikan 7 key, `assess_video` pure lolos 3 kasus.
- Jangan ubah: `cli.py`, `constants.py`, `config.py`, logika `extract_frames`.

---

## STEP S4 — Wire soft-gate ke CLI video path

- Tujuan: flag teknis jadi `review_reasons` + isi field AI/release; TIDAK hard-fail agar klip vertikal valid tidak terbuang.
- Finding: F6, F7.
- Dependency: S2 + S3 (wajib sesudah keduanya).
- File yang harus dibaca:
  - `src/microstock_metadata/cli.py` (lines 359-395 blok video probe/extract, 469-515 normalize + ProcessingResult)
  - `src/microstock_metadata/validation.py` (lines 22-41 decide_review)
  - `src/microstock_metadata/normalization.py` (lines 108-170 return review_reasons)
- File yang harus diubah: `src/microstock_metadata/cli.py` SAJA.
- Simbol terkait: `cli._process_one`, `video_processing.probe_video`, `video_processing.extract_frames`, `video_processing.assess_video`, `normalization.normalize_metadata`, `validation.decide_review`, `schemas.ProcessingResult(is_ai_generated, needs_model_release, needs_property_release)`.
- Kondisi saat ini: blok `is_video and use_api` (lines 361-384) set `video_dur/frame_cnt`, `low_res=False` hardcoded; `norm = normalize_metadata(...)` (469) lalu `decide_review(...)` (478); `ProcessingResult(...)` (488) tanpa 3 field baru.
- Perubahan konkret (3 edit berurutan di `_process_one`):
  1. Setelah `probe = probe_video(...)` dan SEBELUM `extract_frames`, sisipkan: `from .video_processing import assess_video` sejajar import existing, lalu `video_gate_reasons = assess_video({**probe, "codec": probe.get("codec"), "fps": probe.get("fps"), "container": probe.get("container")})`. Jika `probe` lama tanpa key baru (misal di-test) → `.get` = None → `assess_video` return [] (aman).
  2. Setelah `norm = normalize_metadata(...)`, sisipkan: `norm["review_reasons"] = list(norm.get("review_reasons", [])) + [r for r in video_gate_reasons if r not in norm.get("review_reasons", [])]` — JANGAN timpa, hanya append dedupe.
  3. Di konstruktor `ProcessingResult(...)`: tambah `is_ai_generated=(base.get("media_type") == "video"), needs_model_release=bool(norm.get("has_recognizable_people")), needs_property_release=bool(norm.get("possible_trademark")),` dan tambah `review_reasons` hasil gabungan: karena `needs_review/reasons` dihitung SEBELUM edit ini oleh `decide_review`, panggil ulang TIDAK boleh; sebagai gantinya: `needs_review = needs_review or bool(video_gate_reasons)` dan `reasons = reasons + [r for r in video_gate_reasons if r not in reasons]`, lalu teruskan `needs_review=needs_review, review_reasons=reasons` ke konstruktor. Jika variabel `needs_review/reasons` sudah dipakai, edit di tempat, jangan buat nama baru.
- Urutan: import assess → hitung gate → gabung reasons → set 3 field + needs_review.
- Behavior dipertahankan: hard-fail HANYA untuk `extract_frames` raise (terlalu panjang/corrupt) seperti sekarang; gate baru TIDAK raise; resume/checkpoint (`store.is_completed`, `_failed`) tak tersentuh; image path (`else` branch) tidak kena gate.
- Error handling/edge: `probe.get("duration_sec")` None → gate [] ; klip 720x1280 vertikal (w=720,h=1280) → `w<1280` TRUE tapi itu false-positive vertikal → TAMBAH pengecualian di S4: bila `(w==720 and h==1280) atau (w==1080 and h==1920)` maka hapus `below_hd_min` dari list sebelum gabung. Ini satu-satunya logika khusus vertikal yang diizinkan.
- Test tambah/update:
  - TAMBAH `tests/test_cli_video_gate.py` (baru) dengan 2 test memakai mock `probe_video`/`extract_frames` + API stub seperti pola existing `test_cli.py` (baca `test_cli.py` dulu untuk fixture):
    - `test_vertical_hd_not_flagged_below_hd`: probe `{"width":720,"height":1280,"duration_sec":9.0,"codec":"h264","fps":30.0}` → result `needs_review` boleh True karena alasan lain tapi `"below_hd_min" not in result.review_reasons`, `is_ai_generated is True`.
    - `test_small_clip_flagged_not_failed`: probe `{"width":640,"height":480,"duration_sec":9.0,"codec":"h264","fps":30.0}` → `status=="success"`, `"below_hd_min" in review_reasons`, `needs_review is True`.
  - Jika fixture `test_cli.py` sulit dipakai ulang, mock langsung `_process_one` dengan `cfg` minimal (ikuti `build_config` default) — JANGAN ubah `test_cli.py` existing.
- Input/expected: seperti di atas.
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_cli_video_gate.py tests/test_cli.py -q`
- Hasil diharapkan: test baru 2 passed + existing CLI hijau.
- Completion criteria: klip kecil → success+flag; vertikal HD → tanpa below_hd_min; corrupt → tetap failed via jalur lama.
- Jangan ubah: `video_processing.py`, `schemas.py`, `validation.py`, `exporters.py`, discovery.

---

## STEP S5 — Platform-aware normalization

- Tujuan: Title/desc dipotong per platform tanpa mengubah default Adobe.
- Finding: F1, F2, F3, F4, F5.
- Dependency: S1.
- File yang harus dibaca:
  - `src/microstock_metadata/normalization.py` (lines 22-39 title/desc, 108-170 normalize_metadata signature)
  - `src/microstock_metadata/platforms.py` (hasil S1)
  - `src/microstock_metadata/cli.py` (lines 469-475 pemanggilan normalize)
  - `tests/test_normalization.py` (helper `_gen`)
- File yang harus diubah:
  1. `src/microstock_metadata/normalization.py`
  2. `src/microstock_metadata/cli.py` (1 baris: teruskan platform)
- Simbol terkait: `normalization.normalize_title`, `normalize_description`, `normalize_metadata`, `platforms.PLATFORMS`, `config.MetadataConfig.platform`.
- Kondisi saat ini: `normalize_metadata(gen, title_max, description_max, keyword_max_len, keyword_max_count)` terima angka mentah dari `cfg.metadata.title_max_length/description_max_length`.
- Perubahan konkret:
  1. `normalization.py`: tambah fungsi BARU sebelum `normalize_metadata`:
     ```python
     def resolve_limits(platform: str, title_max: int, description_max: int, keyword_max_count: int) -> tuple[int, int, int]:
         """Platform override with global fallback. Unknown platform returns globals unchanged."""
         try:
             from .platforms import PLATFORMS
         except ImportError:
             return title_max, description_max, keyword_max_count
         prof = PLATFORMS.get((platform or "adobe").lower())
         if not prof:
             return title_max, description_max, keyword_max_count
         return prof["title_max"], prof["description_max"], min(keyword_max_count, prof["kw_max"])
     ```
     Note: `min()` agar CLI `--max-keywords 20` yang lebih ketat tetap dihormati; jangan pernah naikkan di atas CLI.
  2. `cli.py` line ~469: ganti pemanggilan menjadi:
     ```python
     from .normalization import resolve_limits as _resolve
     _tmax, _dmax, _kmax = _resolve(cfg.metadata.platform if hasattr(cfg.metadata, "platform") else "adobe", cfg.metadata.title_max_length, cfg.metadata.description_max_length, cfg.metadata.max_keywords)
     norm = normalize_metadata(gen, title_max=_tmax, description_max=_dmax, keyword_max_len=60, keyword_max_count=_kmax)
     ```
     `keyword_max_len=60` TETAP (jangan ubah).
- Urutan: tambah `resolve_limits` → edit pemanggilan CLI.
- Behavior dipertahankan: `platform="adobe"` → limit identik existing; `normalize_metadata` signature TETAP (tidak tambah argumen) agar test existing lolos.
- Error handling/edge: platform unknown/None → fallback global; `keyword_max_count` CLI lebih kecil dari profil → pakai CLI.
- Test tambah/update — TAMBAH ke `tests/test_normalization.py`:
  - `test_resolve_limits_pixabay_caps_keywords`: `resolve_limits("pixabay", 70, 200, 49) == (100, 200, 25)`
  - `test_resolve_limits_respects_tighter_cli`: `resolve_limits("dreamstime", 70, 200, 20) == (200, 200, 20)`
  - `test_resolve_limits_unknown_falls_back`: `resolve_limits("nope", 70, 200, 49) == (70, 200, 49)`
- Input/expected: eksplisit di atas.
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_normalization.py tests/test_config.py -q`
- Hasil diharapkan: 9 existing + 3 baru passed.
- Completion criteria: pixabay potong keyword 25, dreamstime title 200, unknown aman.
- Jangan ubah: `constants.py`, `schemas.py`, `prompts.py`, `exporters.py`, `csv_embed.py`.

---

## STEP S6 — Prompt microstock-video-v2

- Tujuan: bedakan camera-move vs subject-action + larang klaim lokasi; versi lama tetap tersedia.
- Finding: F9.
- Dependency: S0 (independen; boleh dikerjakan paralel S1–S5).
- File yang harus dibaca:
  - `src/microstock_metadata/prompts.py` (lines 49-87)
  - `src/microstock_metadata/cli.py` (lines 280-285 pemilihan VIDEO_PROMPT_VERSION)
  - `tests/test_prompts.py`
- File yang harus diubah: `src/microstock_metadata/prompts.py` SAJA (JANGAN ubah `cli.py` default di langkah ini agar rollout eksplisit).
- Simbol terkait: `prompts.VIDEO_PROMPT_VERSION`, `MICROSTOCK_VIDEO_V1`, `build_prompt`, `build_retry_prompt`.
- Kondisi saat ini: `VIDEO_PROMPT_VERSION = "microstock-video-v1"`; `build_prompt` kenal `microstock-v1/v3/video-v1`, else → v2.
- Perubahan konkret:
  1. Tambah konstanta BARU setelah `MICROSTOCK_VIDEO_V1` (jangan edit V1):
     ```python
     MICROSTOCK_VIDEO_V2 = MICROSTOCK_VIDEO_V1 + "\nRules append: Separate CAMERA move (static, pan, tilt, dolly, drone, handheld) from SUBJECT action in the description as two clauses. Never describe a single frame as a photo. Never claim a specific city, place, or person identity."
     VIDEO_PROMPT_V2 = "microstock-video-v2"
     ```
  2. Di `build_prompt`, tambah cabang SEBELUM `return "microstock-v2"...`:
     ```python
     if version == "microstock-video-v2":
         return "microstock-video-v2", MICROSTOCK_VIDEO_V2
     ```
  3. `VIDEO_PROMPT_VERSION` TETAP `"microstock-video-v1"` (jangan flip default di sini).
- Urutan: tambah V2 string → tambah konstanta nama → tambah cabang build.
- Behavior dipertahankan: `build_prompt()` default tetap v2 image; `build_prompt("microstock-video-v1")` byte-identik; retry suffix tak berubah.
- Error handling/edge: versi tak dikenal → tetap v2 (existing fallback); tidak ada migrasi checkpoint.
- Test tambah/update — TAMBAH ke `tests/test_prompts.py`:
  - `test_video_v2_appends_camera_rule`: `v, t = build_prompt("microstock-video-v2"); assert v == "microstock-video-v2" and "CAMERA move" in t and "temporal order" in t`
  - `test_video_v1_unchanged`: `v1, t1 = build_prompt("microstock-video-v1"); assert "CAMERA move" not in t1`
- Input/expected: seperti di atas.
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_prompts.py -q`
- Hasil diharapkan: 5 existing + 2 baru passed.
- Completion criteria: V2 tersedia opt-in, V1 tak berubah.
- Jangan ubah: `cli.py` default version, `constants.py`, V1 string.

---

## STEP S7 — Four-platform video exporter + CLI flags

- Tujuan: satu `metadata.csv` → 4 CSV portal siap upload untuk video.
- Finding: F1, F2, F3, F4, F8, F10.
- Dependency: S1 + S5 (butuh profil + gaya keyword).
- File yang harus dibaca:
  - `src/microstock_metadata/csv_embed.py` (full, 114 lines)
  - `scripts/csv_to_embed.py` (full, 33 lines)
  - `src/microstock_metadata/platforms.py` (hasil S1)
  - `tests/test_csv_embed.py`
- File yang harus diubah:
  1. `src/microstock_metadata/csv_embed.py`
  2. `scripts/csv_to_embed.py`
- Simbol terkait: `csv_embed.convert_rows`, `convert_file`, `split_single_words`, `adobe_category`, `ADOBE_CATEGORY_MAP`, `EMBED_COLUMNS`, `ADOBE_COLUMNS`, `platforms.PLATFORMS`.
- Kondisi saat ini: `convert_rows` kembalikan `(adobe, dream, counts)`; `convert_file(input, adobe_path, dream_path)` tulis 2 file; kolom Adobe `Filename,Title,Description,Keywords,Category,Releases,Copyright,Creator`.
- Perubahan konkret:
  1. `csv_embed.py`, TAMBAH setelah `DREAMSTIME_MAX_WORDS`:
     ```python
     VECTEEZY_MAX_TAGS = 50
     PIXABAY_MAX_TAGS = 25
     VIDEO_ADOBE_COLUMNS = ["Filename", "Title", "Description", "Keywords", "Category", "Releases", "Copyright", "Creator", "IsAIGenerated"]
     ```
     TAMBAH fungsi baru (jangan ubah existing):
     ```python
     def cap_phrase_keywords(keywords_cell: str, cap: int) -> str:
         """Keep original phrase order, cut to cap phrases."""
         phrases = [p.strip() for p in (keywords_cell or "").split(",") if p.strip()]
         return ", ".join(phrases[:cap])
     def convert_video_rows(rows, copyright_, creator):
         """Return dict platform -> rows for video. Skips failed/empty like convert_rows."""
         out = {"adobe": [], "dreamstime": [], "vecteezy": [], "pixabay": []}
         skipped = 0
         for row in rows:
             if row.get("status") not in ("success", "skipped"): skipped += 1; continue
             if (row.get("media_type") or "") not in ("", "video", "image"): skipped += 1; continue
             title = (row.get("title") or "").strip()
             keywords = (row.get("keywords") or "").strip()
             if not title or not keywords: skipped += 1; continue
             fname = (row.get("filename") or "").strip()
             base = {"Title": title[:70] if False else title, "Description": (row.get("description") or "").strip(), "Copyright": copyright_, "Creator": creator}
             # Adobe-video: phrase, cap 49, category via adobe_category, Releases "", IsAIGenerated "yes" bila media video
             # Dreamstime: single words cap 70 via split_single_words
             # Vecteezy: phrase cap 50
             # Pixabay: phrase cap 25
             ...
         return out, {"converted": ..., "skipped": skipped}
     ```
     Implementasi sel target (tulis persis, jangan improvisasi kolom):
     - `adobe`: `{Filename: fname, Title: title[:70], Description: desc[:200], Keywords: cap_phrase(title=keywords,49), Category: adobe_category(category), Releases: "", Copyright, Creator, IsAIGenerated: "yes" if media_type=="video" else ""}`
     - `dreamstime`: `{SourceFile: fname, Title: title[:200], Description: desc or title, Keywords: ", ".join(split_single_words(keywords)[:70]), Copyright, Creator}`
     - `vecteezy`: `{Filename: fname, Title: title[:70], Description: desc[:200], Keywords: cap_phrase(keywords,50), Copyright, Creator}`
     - `pixabay`: `{Filename: fname, Title: title[:100], Description: desc[:200], Keywords: cap_phrase(keywords,25), Copyright, Creator}`
     `Title` Adobe/Vecteezy dipotong 70 char dengan `title[:70].rstrip()`; Dreamstime 200; Pixabay 100. `Description` kosong di Dreamstime → fallback ke title (jangan biarkan kosong).
  2. `scripts/csv_to_embed.py`: TAMBAH argumen `--dreamstime-out` TETAP wajib (backward compat), tambah `--vecteezy-out default None`, `--pixabay-out default None`, `--adobe-video-out default None`, `--media-type default "image" choices image|video`. Logika: bila `media-type==video` → panggil `convert_video_rows`, tulis file yang path-nya diberikan (yang None dilewati); cetak `converted/skipped + per-platform counts`. Bila `image` → perilaku lama persis (panggil `convert_file`). JANGAN ubah signature `convert_file`.
- Urutan: konstanta → `cap_phrase_keywords` → `convert_video_rows` → CLI flags → branching image/video.
- Behavior dipertahankan: `convert_rows`/`convert_file` dan pemanggilan image existing byte-identik outputnya; header 2 file lama tak berubah.
- Error handling/edge: baris `status=failed` atau title/keywords kosong → skipped+count; `media_type` kosong (CSV lama tanpa kolom) → diperlakukan sebagai image-able (ikut convert); keyword sel `""` → skip bukan crash; file input tidak ada → `Conversion failed` exit 1 seperti sekarang.
- Test tambah/update — TAMBAH `tests/test_csv_embed_video.py` (baru):
  - helper `_vrow(media="video", keywords=...)` dengan `filename/title/description/keywords/status/category/media_type`.
  - `test_video_four_platforms`: 1 baris video 60 frasa → `adobe` 49 frasa + `IsAIGenerated=="yes"` + Title ≤70; `dreamstime` kata tunggal ≤70 + Title ≤200; `vecteezy` ≤50 frasa; `pixabay` ≤25 frasa.
  - `test_video_skips_failed_and_empty`: rows failed + empty → `skipped==2`, converted 0.
  - `test_image_path_unchanged`: `convert_rows` existing tetap 49-tidak-capped-untuk-image (gunakan `_row` pola existing).
- Input/expected: contoh keyword `", ".join(f"clip phrase {i}" for i in range(60))` → adobe `len(...split(","))==49`, pixabay `==25`.
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_csv_embed.py tests/test_csv_embed_video.py -q` + manual `--help` (` .venv\Scripts\python scripts/csv_to_embed.py --help` harus tampilkan 4 flag baru).
- Hasil diharapkan: semua passed; help tampilkan flags.
- Completion criteria: 4 CSV terdefinisi, image path tak berubah, Adobe numbers-debt TIDAK diutak-atik (kolom Category tetap nama).
- Jangan ubah: `exporters.py`, `constants.py`, `ADOBE_CATEGORY_MAP` isi, `convert_file` signature.

---

## STEP S8 — Export new columns (backward compatible)

- Tujuan: `metadata.csv/json` bawa 3 field baru tanpa geser kolom lama.
- Finding: F7.
- Dependency: S2 + S4.
- File yang harus dibaca:
  - `src/microstock_metadata/exporters.py` (lines 75-145)
  - `tests/test_exporters.py`
- File yang harus diubah: `src/microstock_metadata/exporters.py` SAJA.
- Simbol terkait: `exporters.CSV_COLUMNS`, `write_metadata_csv`, `write_metadata_json`, `_cell`.
- Kondisi saat ini: `CSV_COLUMNS` berakhir `..., "media_type", "video_duration_sec", "frame_count"`; `_cell` guard formula; JSON dump `model_dump()` otomatis ikut field baru.
- Perubahan konkret: append TIGA nama di EKOR `CSV_COLUMNS`: `"is_ai_generated", "needs_model_release", "needs_property_release"`. Di `write_metadata_csv` tambah TIGA `_cell(...)` SEJAJAR di ekor `writer.writerow([...])`: `_cell(r.is_ai_generated), _cell(r.needs_model_release), _cell(r.needs_property_release)`. JANGAN sisip di tengah. JSON tidak perlu edit (otomatis).
- Urutan: columns → writer row.
- Behavior dipertahankan: 27 kolom lama urutan+isi identik; BOM + quoting + formula guard tak tersentuh; `write_metadata_json` tak diubah.
- Error handling/edge: baris lama (tanpa attr, misal unpickle manual) → gunakan `getattr(r, "is_ai_generated", False)` agar tidak AttributeError bila test pihak ketiga bangun objek parsial. Implementasi: `_cell(getattr(r, "is_ai_generated", False))` dst.
- Test tambah/update — TAMBAH ke `tests/test_exporters.py`:
  - `test_csv_new_columns_appended`: tulis `_ok()` → header 3 terakhir `== ["is_ai_generated","needs_model_release","needs_property_release"]`, nilai `"false"`; tulis `_ok(is_ai_generated=True, ...)` → `"true"`.
- Input/expected: eksplisit di atas.
- Command verifikasi: `.venv\Scripts\python -m pytest tests/test_exporters.py -q`
- Hasil diharapkan: passed termasuk 2 test video existing.
- Completion criteria: kolom baru di ekor, file lama tetap dibaca Excel/Sheets.
- Jangan ubah: `schemas.py`, urutan kolom lama, `write_metadata_json`, `write_failed_json`.

---

## STEP S9 — Docs + sample config + examples

- Tujuan: dokumentasikan alur video 4-platform agar model kecil/executor tak perlu tanya ulang.
- Finding: semua (traceability user-facing).
- Dependency: S1–S8 (tulis sesudah API stabil).
- File yang harus dibaca: `README.md` (lines 158-180 §9c), `examples/sample_config.yaml`, `examples/sample_output.json`.
- File yang harus diubah:
  1. `README.md` (tambah §9d SAJA, jangan edit §9c)
  2. `examples/sample_config.yaml` (ganti komentar S1 jadi blok nyata + contoh providers tak tersentuh)
  3. TAMBAH `examples/sample_video_output.json` (baru, 1 item video)
- Simbol terkait: n/a (docs).
- Kondisi saat ini: §9c dokumentasikan video API-only 6 frames; tidak ada matriks platform.
- Perubahan konkret:
  1. `README.md`: sisipkan setelah §9c blok `## 9d. Video untuk 4 platform (API-only)` berisi: tabel batas (Adobe 70/49 phrase, Dreamstime 200/70 single, Vecteezy 70/50 phrase, Pixabay 100/25 phrase), command generate (`run.bat generate .\clips --backend api --media-type video --frames 6`), command convert video (`python scripts/csv_to_embed.py --input out/metadata.csv --media-type video --adobe-video-out ... --dreamstime-out ... --vecteezy-out ... --pixabay-out ...`), catatan AI-checkbox + releases di portal, catatan verifikasi portal (angka default, bukan final).
  2. `sample_config.yaml`: di blok `metadata:` tambah baris nyata `platform: adobe` + komentar `# adobe|dreamstime|vecteezy|pixabay|all`.
  3. `sample_video_output.json`: salin struktur `sample_output.json` 1 item, set `media_type: video, video_duration_sec: 9.5, frame_count: 6, is_ai_generated: true, prompt_version: microstock-video-v1`.
- Behavior dipertahankan: tidak ada kode; §9c byte-identik.
- Error handling/edge: contoh JSON harus valid JSON (koma benar); command docs pakai path Windows `.\` konsisten README.
- Test: TIDAK ADA test kode; verifikasi = ` .venv\Scripts\python -c "import json; json.load(open('examples/sample_video_output.json'))"` sukses + `git diff --stat` hanya 3 file docs.
- Command verifikasi: command python di atas + eyeball README render.
- Completion criteria: §9d ada, config contoh punya platform, JSON contoh valid.
- Jangan ubah: kode `src/`, `scripts/`, test, `SPEC.md`, PowerShell root.

---

## STEP S10 — Full verification + handoff

- Tujuan: kunci tidak ada regresi sebelum serah terima.
- Dependency: S0–S9 semua.
- File dibaca: output `pytest`, `run.bat doctor`.
- File diubah: TIDAK ADA (kecuali update Progress Log plan ini).
- Perubahan: TIDAK ADA.
- Command verifikasi (dari `microstock-metadata-generator/`):
  1. `.venv\Scripts\python -m pytest -q`
  2. `.venv\Scripts\python scripts/csv_to_embed.py --help`
  3. `run.bat doctor`
- Hasil diharapkan:
  1. `passed`, 0 failed, `real_model` ter-skip otomatis.
  2. Help tampilkan `--vecteezy-out --pixabay-out --adobe-video-out --media-type`.
  3. Doctor OK (ffmpeg baris boleh `!!` bila tidak install — catat).
- Completion criteria: 3 command hijau (dengan catatan ffmpeg), plan Tasks dicentang, handoff checklist di bawah diisi.
- Jangan ubah: apa pun selain plan.

---

## Open Questions (blocker, jangan pilih diam-diam)

1. **Angka final portal.** Opsi: (a) pakai default plan ini; (b) verifikasi manual di 4 portal lalu patch `platforms.py`. Risiko (a): reject/trim di portal. Rekomendasi: (b) sebelum rilis; S1 membuat patch = 1 file.
2. **Nomor kategori Adobe.** Opsi: (a) tetap nama (Sensei fallback); (b) petakan nomor dari dialog upload-CSV portal. Risiko (b): nomor salah = kolom invalid. Rekomendasi: (a) untuk sekarang; catat di README §9d.
3. **Default `frames` 6 vs 8 dan flip V1→V2.** Opsi: (a) tetap 6+V1 default; (b) naikkan + flip. Risiko (b): biaya/latensi API naik. Rekomendasi: (a); V2 opt-in via `--config`/`prompt_version` di follow-up.
4. **Kategori Vecteezy/Dreamstime.** `VECTEEZY_CATEGORY_MAP` dikosongkan disengaja. Opsi: isi manual dari portal vs kosong. Rekomendasi: kosong sampai ada sumber portal terverifikasi.

## Handoff Checklist (diisi executor)

- [x] S0 output pytest + doctor disalin ke Progress Log
- [x] S1–S8 tiap test baru hijau, tidak ada test existing diubah kecuali penambahan fungsi
- [x] `git status --short` hanya sentuh file yang diizinkan tiap langkah
- [x] `git diff` tiap langkah direview: tidak ada secret/key, tidak ada path absolut pribadi
- [x] README §9d + sample JSON valid
- [x] Open questions di atas diteruskan ke owner, bukan diputuskan executor

## Files Must-Not-Touch (global)

- `.venv/`, `output/`, `output-api/`, model cache HF, `*.bak`, `checkpoint.json` hasil run
- Workspace-root PowerShell (`Embed-*.ps1`, `Orchestrate-Stock.ps1`, `Process-Batch.ps1`, `Upscale.ps1`, `Trace-Svg.ps1`)
- `.env` (hanya `.env.example` boleh dibaca), git history/rebase, `SPEC.md` normatif
