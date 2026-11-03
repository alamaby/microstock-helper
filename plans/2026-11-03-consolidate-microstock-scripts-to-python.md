# Plan: Konsolidasi Seluruh Script Microstock ke Satu Aplikasi Python

Created: 2026-11-03 09:25:00 +07:00

## Objective
Mengonsolidasikan seluruh fungsi script PowerShell (baik script utilitas satuan seperti convert, upscale, trace, embed, renumber, maupun orkestrator batch dan end-to-end `Orchestrate-Stock.ps1`) serta modul `microstock-metadata-generator` ke dalam satu aplikasi/package Python terpadu (`microstock-helper` / `microstock`).

## Scope
1. Analisis arsitektur, pemetaan fungsi script PowerShell ke modul Python, serta perancangan struktur paket.
2. Penggabungan utilitas grafis raster (PNG/WEBP -> JPG) menggunakan pustaka murni Python (Pillow).
3. Wrapper subprocess berkinerja tinggi dan aman untuk CLI eksternal:
   - ExifTool (`exiftool.exe`) untuk triple-sync metadata JPG dan EPS XMP.
   - Upscayl CLI (`upscayl-bin.exe`) dengan penanganan sandbox path pendek (mengatasi limit `MAX_PATH` 260 karakter Windows).
   - vtracer CLI (`vtracer.exe`) untuk raster-to-SVG.
   - Inkscape CLI (`inkscape.com`) untuk SVG-to-EPS dan rendering raster preview.
4. Injeksi metadata SVG native XML murni Python (`xml.etree.ElementTree`).
5. Penomoran urut kronologis file (`001_...`) murni Python.
6. Penyatuan pipeline orkestrator (`Orchestrate-Stock.ps1` dan `Process-Batch.ps1`) ke dalam workflow Python:
   - Pipeline JPG & Vector (SVG/EPS).
   - Multi-platform packaging (Adobe Stock, Dreamstime, Vecteezy, Pixabay).
   - Mekanisme resume, sanitasi nama file, dan toleransi partial failure.
7. Antarmuka CLI tunggal (`microstock` / `python -m microstock`) dengan subcommands modular.
8. Penyediaan wrapper PowerShell tipis (opsional) untuk backward compatibility.

## Milestones
1. **Fase 1: Analisis & Desain Arsitektur**: Pemetaan lengkap, perancangan struktur folder, dan evaluasi trade-off (saat ini).
2. **Fase 2: Core Modules & Wrappers**: Implementasi fungsi konversi native, wrapper CLI pihak ketiga, penomoran, dan embedder.
3. **Fase 3: Integrasi Engine Metadata & Packaging**: Penyatuan modul generator metadata AI Vision API dan generator CSV 4 platform.
4. **Fase 4: Orchestrator Pipeline**: Implementasi pipeline end-to-end multi-tahap dengan preflight, resume checkpoints, dan reporting.
5. **Fase 5: Pengujian & Verifikasi Komparatif**: Verifikasi hasil output byte-level/metadata dengan hasil pipeline PowerShell sebelumnya.

## Tasks
- [x] Analisis seluruh fungsionalitas script eksisting (11 file PS1 + subproyek Python).
- [x] Implementasi preflight & binary resolver saat start aplikasi (otomatis cek ketersediaan CLI tools: exiftool, upscayl, vtracer, inkscape, ffmpeg, ffprobe, dan API keys).
- [x] Buat struktur paket Python terpadu `microstock/` di root workspace dan migrasikan modul dari `microstock-metadata-generator`.
- [x] Implementasi modul core: konversi raster (Pillow), renumber, upscaler wrapper, tracer wrapper, vector ops wrapper, dan metadata embedder (ExifTool + SVG XML).
- [x] Satukan pipeline orkestrator (`run` dan `batch`) dengan dukungan multi-platform packaging (Adobe, Dreamstime, Vecteezy, Pixabay), resume checkpoints, dan reporting.
- [x] Bangun CLI terpadu (`microstock`) dengan subcommands modular dan preflight check saat startup.
- [x] Update README.md lengkap dengan instruksi instalasi, arsitektur, dan panduan penggunaan CLI baru.
- [x] Verifikasi dan uji coba end-to-end dengan test suite dan sampel data.

## Risks & Mitigations
- **Risiko 1 (Batas MAX_PATH Windows)**: `upscayl-bin.exe` gagal membaca path > 260 karakter.
  - *Mitigasi*: Python menyalin file ke direktori sementara `%TEMP%` dengan nama pendek sebelum eksekusi CLI, lalu memindahkan hasilnya kembali (replikasi pola PowerShell).
- **Risiko 2 (Inkompatibilitas Path Binary Pihak Ketiga)**: Binary eksternal tidak berada di `PATH`.
  - *Mitigasi*: Buat resolver bertingkat: cek variabel lingkungan -> cek konfigurasi YAML -> cek `PATH` -> cek lokasi default Windows (`C:\Program Files\...`, `C:\Apps\...`).
- **Risiko 3 (Regresi Metadata ExifTool / SVG)**: Penulisan tag IPTC/XMP/EXIF tidak terbaca oleh agensi microstock.
  - *Mitigasi*: Gunakan 2-fase penulisan yang sama (reset -> write UTF-8) dan uji verifikasi baca-balik (*read-back verification*).
- **Risiko 4 (Ukuran Proyek & Perubahan Struktur Git)**: Sub-repository `microstock-metadata-generator` terpisah dari root repository.
  - *Mitigasi*: Integrasikan kode ke root repository sebagai satu paket terpadu sehingga seluruh repositori bersih dan tidak memiliki ketergantungan sub-repo yang membingungkan.

## Progress Log
- 2026-11-03 09:25:00 — Perumusan plan konsolidasi Python dan penyusunan analisis komprehensif.
- 2026-11-03 09:52:00 — Penambahan kebutuhan startup preflight CLI check dan pembaruan README.md.
- 2026-11-03 10:28:00 — Implementasi paket microstock terpadu, modul core, preflight check, subcommands CLI, test suite 25 tests passed 100%, dan penyesuaian README.md.

## Notes
- Pustaka Pillow mengeliminasi kebutuhan memanggil `ffmpeg.exe` untuk konversi raster sederhana (PNG/WEBP ke JPG), meningkatkan kecepatan konversi batch.
