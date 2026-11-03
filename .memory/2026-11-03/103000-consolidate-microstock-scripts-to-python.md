# Consolidate Microstock Scripts and Workflows to Unified Python Application

- **Timestamp**: 2026-11-03 10:30:00 +07:00
- **Task/Problem**: Seluruh fungsionalitas script otomasi microstock (PowerShell utilitas satuan, batch orkestrator, end-to-end `Orchestrate-Stock.ps1`, dan modul generator metadata) dikonsolidasikan ke dalam satu paket aplikasi Python terpadu (`microstock-helper` / `microstock`) dengan startup preflight check untuk seluruh CLI dependencies eksternal.
- **Changed Files**:
  - `microstock/__init__.py`
  - `microstock/__main__.py`
  - `microstock/preflight.py`
  - `microstock/core/image_ops.py`
  - `microstock/core/renumber.py`
  - `microstock/core/upscaler.py`
  - `microstock/core/tracer.py`
  - `microstock/core/vector_ops.py`
  - `microstock/core/metadata_embed.py`
  - `microstock/metadata/`
  - `microstock/pipeline/packaging.py`
  - `microstock/pipeline/reporter.py`
  - `microstock/pipeline/batch.py`
  - `microstock/pipeline/orchestrator.py`
  - `microstock/cli.py`
  - `pyproject.toml`
  - `requirements.txt`
  - `setup.bat`
  - `run.bat`
  - `README.md`
  - `tests/test_preflight.py`
  - `tests/test_image_ops.py`
  - `tests/test_renumber.py`
  - `tests/test_metadata_embed.py`
  - `tests/test_packaging.py`
  - `tests/test_cli_unified.py`
  - `plans/2026-11-03-consolidate-microstock-scripts-to-python.md`
  - `.memory/README.md`
  - `.memory/2026-11-03/103000-consolidate-microstock-scripts-to-python.md`

## Technical & Business Decisions
1. **Startup Preflight Dependency Validation**:
   - Seluruh tool eksternal (`exiftool`, `upscayl`, `vtracer`, `inkscape`, `ffmpeg`, `ffprobe`) dicek otomatis saat startup via resolver bertingkat: Explicit Arg/Config -> Environment Variables (`MICROSTOCK_<TOOL>_PATH`) -> System `PATH` (`shutil.which`) -> Standard Windows Installation Paths.
   - Command `doctor` (`run.bat doctor`) disediakan untuk diagnosis menyeluruh kesiapan sistem.
2. **Pillow Native Raster Processing**:
   - Menghilangkan overhead subprocess `ffmpeg` untuk konversi raster sederhana (PNG, WebP, TIF, BMP ke JPG).
   - Transparansi (alpha) secara otomatis di-composite ke background solid putih standar microstock.
3. **MAX_PATH 260 Character Bypass**:
   - Mengatasi limit `upscayl-bin.exe` dengan memproses file via nama pendek di `%TEMP%` (`u_in.png`) lalu disalin kembali secara atomis.
4. **ExifTool 2-Phase Triple Sync**:
   - Mempertahankan penulisan metadata 2 fase (reset -> write UTF-8) untuk mencegah penggandaan list tag pada IPTC, XMP, dan EXIF.
5. **Unified Multi-Agency Packaging**:
   - Memisahkan folder agensi `for_adobe`, `for_dreamstime`, `for_vecteezy_*`, dan `for_pixabay_*` dengan sanitasi penamaan file FTP Vecteezy otomatis.
6. **Backward Compatibility**:
   - Script PowerShell legacy tetap dipertahankan sebagai opsi alternatif tanpa merusak alur kerja lama.

## Assumptions & Risks
- **Asumsi**: Pengguna menjalankan aplikasi di sistem operasi Windows dengan tool-tool eksternal di lokasi standar atau terdaftar di PATH / environment variables.
- **Risiko**: Ekspektasi portal microstock terhadap format metadata (misal format nomor vs nama kategori Adobe Stock) memerlukan verifikasi saat pengunggahan live.

## Verification
- Diagnosis startup: `run.bat doctor` berhasil mendeteksi ke-6 binary eksternal dan status API keys.
- Unit testing: 25 tests baru di `tests/` lulus 100% (preflight, image ops, renumbering, SVG XML embedding, ExifTool JPG embed, packaging, dan unified CLI).
- Regresi metadata generator: 126 tests di `microstock-metadata-generator/tests` lulus 100%.

## Proposed Conventional Commit
`feat(cli): consolidate all scripts and orchestrators into unified python app`
