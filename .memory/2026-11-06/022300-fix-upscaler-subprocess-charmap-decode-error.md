# Fix Upscaler and External Subprocess UnicodeDecodeError (cp1252 charmap)

- **Timestamp**: 2026-11-06 02:23:00 +07:00
- **Task/Problem**: Saat menjalankan `./run.bat run "C:\Side\Microstock\wallpaper-01" --target JPG --force`, proses di Tahap 4 (Upscale AI via Upscayl) gagal pada thread reader subprocess: `UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f in position 935: character maps to <undefined>`.
- **Root Cause**: Pemanggilan `subprocess.run(cmd, capture_output=True, text=True)` pada Windows default menggunakan encoding lokal sistem (`cp1252`). Ketika binary eksternal seperti `upscayl-bin.exe` mencetak output verbose berisi byte karakter non-ANSI (seperti byte `0x8f` yang undefined di Windows-1252), worker thread `_readerthread` di modul standar `subprocess.py` mengalami crash `UnicodeDecodeError` karena strict decoding charmap.
- **Key Changes**:
  - `microstock/core/upscaler.py`: Menambahkan parameter eksplisit `encoding="utf-8", errors="replace"` pada pemanggilan `subprocess.run(...)`.
  - `microstock/core/tracer.py`: Menambahkan parameter eksplisit `encoding="utf-8", errors="replace"` pada pemanggilan `vtracer`.
  - `microstock/core/vector_ops.py`: Menambahkan parameter eksplisit `encoding="utf-8", errors="replace"` pada kedua pemanggilan `inkscape` (konversi EPS dan render preview PNG).
  - `microstock/metadata/video_processing.py`: Menambahkan parameter eksplisit `encoding="utf-8", errors="replace"` pada pemanggilan `ffprobe` dan `ffmpeg`.
  - `run.bat`: Menambahkan `set "PYTHONUTF8=1"` dan `set "PYTHONIOENCODING=utf-8"` untuk mengaktifkan Python UTF-8 Mode (PEP 540) secara global di Windows.
  - `tests/test_upscaler.py`: Menambahkan unit test baru untuk memastikan `upscale_image` dan pemanggilan subprocess selalu memakai `encoding="utf-8"` dan `errors="replace"`.
- **Technical Decisions**:
  - Menggunakan kombinasi `encoding="utf-8"` dan `errors="replace"`: stdout/stderr dari tools eksternal didekode sebagai UTF-8, dan bila terdapat fragmen byte rusak/stray binary, karakter diganti dengan placeholder `\ufffd` tanpa melempar exception fatal.
  - Menambahkan UTF-8 Mode di `run.bat` sebagai layer pertahanan tambahan bagi stdout console printing pada Windows.
- **Assumptions/Risks**:
  - Binary `upscayl-bin.exe` tetap memerlukan waktu ~1-1.5 menit per berkas skala 5x; ini normal sesuai kapasitas hardware GPU mesin.
- **Verification**:
  - Menjalankan `pytest tests/test_upscaler.py` (3 passed).
  - Menjalankan `pytest tests/test_metadata_embed.py` (4 passed).
- **Proposed Commit**:
  `fix(upscaler): resolve cp1252 charmap unicodedecodeerror in subprocess calls`
