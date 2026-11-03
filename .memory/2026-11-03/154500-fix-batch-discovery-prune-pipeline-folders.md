# Fix Batch Discovery: Prune Pipeline & Output Folders, Auto-Detect Flat Root

- **Timestamp**: 2026-11-03 15:45:00 +07:00
- **Status**: Completed
- **Proposed Commit**: `fix(batch): prune pipeline output folders and auto-detect flat root in discovery`

## Task / Masalah
Saat pengguna menjalankan `python -m microstock batch "C:\Side\Microstock\Winter Microstock" --agencies adobe --overwrite`, terdeteksi 368 file alih-alih 68 file asli.

## Analisis Akar Masalah (Root Causes)
1. Di dalam folder `Winter Microstock`, terdapat folder kerja internal dan hasil output:
   - Root `Winter Microstock`: 68 file (file input asli)
   - `_stock\02_jpg_small`: 68 file
   - `_stock\03_upscaled`: 68 file
   - `_stock\04_final_jpg`: 68 file
   - `_stock\for_adobe`: 68 file
   - `for_adobe`: 28 file
   Total: 68 + 68 + 68 + 68 + 68 + 28 = 368 file.
2. Generator metadata dipanggil dengan `recursive=True` secara default.
3. Di script legacy `Process-Batch.ps1`, terdapat logika otomatis jika ada file di root batch folder (`$flat`), maka ditambahkan `--no-recursive`. Logika ini belum diimplementasikan di `microstock.pipeline.batch.run_batch`.
4. Fungsi `discover_inputs` di `discovery.py` belum mengecualikan folder pipeline/output (`_stock`, `output-api`, `for_adobe`, dll.) saat penjelajahan rekursif.

## Perubahan yang Dilakukan
1. `microstock/metadata/discovery.py` & `microstock-metadata-generator/src/microstock_metadata/discovery.py`:
   - Menambahkan filter direktori `dirs[:]` pada `os.walk()` untuk mengabaikan folder pipeline/output (`_stock`, `output-api`, `for_adobe`, `for_dreamstime`, `for_vecteezy`, `for_pixabay`, `output`).
2. `microstock/pipeline/batch.py`:
   - Menambahkan deteksi otomatis file gambar di root `batch_path`; jika ada, otomatis menambahkan flag `--no-recursive` saat memanggil `generate`.

## Verifikasi
- Pengujian `discover_inputs` pada `Winter Microstock`: Terdeteksi tepat 68 file (sebelumnya 368).
- Unit tests `tests/`: 25 passed (100%).
- Unit tests `microstock-metadata-generator/tests/`: 126 passed (100%).
