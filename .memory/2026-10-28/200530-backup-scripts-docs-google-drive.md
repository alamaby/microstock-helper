# Backup Scripts and Documentation to Google Drive

- **Timestamp**: 2026-10-28 20:05:30 +07:00
- **Status**: Completed
- **Proposed Commit**: `chore: backup microstock scripts and documentation to Google Drive tools directory`

## Task / Masalah
Menyalin seluruh script otomatisasi dan dokumen panduan penggunaan microstock dari repositori lokal ke direktori Google Drive `G:\My Drive\microstock\` dengan struktur folder baru yang rapi dan terorganisir.

## Berkas yang Disalin / Struktur Destinasi
Direktori tujuan: `G:\My Drive\microstock\tools\`
1. **PowerShell Pipeline Scripts (Root `tools/`)**:
   - `Orchestrate-Stock.ps1`
   - `Process-Batch.ps1`
   - `Rename-Numbered.ps1`
   - `Upscale.ps1`
   - `Convert-PngToJpg.ps1`
   - `Convert-WebpToJpg.ps1`
   - `Convert-SvgToEps.ps1`
   - `Trace-Svg.ps1`
   - `Export-VectorPreview.ps1`
   - `Embed-JpgMetadata.ps1`
   - `Embed-VectorMetadata.ps1`
2. **Dokumentasi & Panduan**:
   - `README.md` (Panduan lengkap script batch)
   - `AGENTS.md` (Spesifikasi & panduan CLI external tools)
   - `PANDUAN MICROSTOCK VERSI 1.pdf` (Panduan dasar microstock)
   - `docs/` (Koleksi dokumen rapi: `PANDUAN_SCRIPT.md`, `PANDUAN_CLI_TOOLS.md`, `PANDUAN MICROSTOCK VERSI 1.pdf`, dan `project-docs/`)
3. **Generator Metadata Package (`microstock-metadata-generator/`)**:
   - Source code (`src/`), utility scripts (`scripts/`), unit tests (`tests/`)
   - Batch runner & installer (`setup.bat`, `run.bat`)
   - Requirements & metadata konfigurasi (`pyproject.toml`, `requirements.txt`, `requirements-gpu.txt`, `.env.example`, `SPEC.md`, `README.md`)

## Keputusan Teknis & Higienitas
- **Preservasi Relatif Path**: Script `.ps1` dan folder `microstock-metadata-generator` diletakkan berdampingan di root folder `tools` agar pemanggilan dependensi `$PSScriptRoot` pada `Orchestrate-Stock.ps1` dan `Process-Batch.ps1` tetap berfungsi secara valid.
- **Safety & Secret Guard**: Berkas `.env` aktif yang berisi token API sengaja tidak disalin ke Google Drive untuk menghindari kebocoran kredensial ke cloud storage; template `.env.example` disediakan sebagai gantinya.
- **Clean Artifacts**: Direktori virtual environment (`.venv`), cache python (`__pycache__`), cache test (`.pytest_cache`), dan folder output sementara dibersihkan dari salinan tujuan.

## Verifikasi
- Struktur dan eksistensi berkas diverifikasi via PowerShell `Get-ChildItem`.
- Seluruh 11 script `.ps1` telah terkonfirmasi utuh.
- Verifikasi `Test-Path` memastikan file rahasia `.env` tidak ada di folder tujuan Google Drive.
