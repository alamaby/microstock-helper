# Fix Metadata Atomic Write Windows File Lock (WinError 5 Access is Denied)

- **Timestamp**: 2026-11-06 02:37:00 +07:00
- **Task/Problem**: Saat menjalankan proses generasi metadata pada batch besar (152 berkas di `wallpaper-01`), proses gagal di tahap flush output dengan pesan error: `Output error: Cannot write C:\Side\Microstock\wallpaper-01\_stock\metadata\metadata.json: [WinError 5] Access is denied: '...tmpnpe25c88.tmp' -> '...metadata.json'`.
- **Root Cause**: `_flush_outputs` dipanggil pada setiap item selesai diproses. Pada Windows, penggantian file berulang-ulang melalui `os.replace` (Windows API `MoveFileExW`) rentan bentrok sesaat dengan antivirus (Windows Defender), Windows Search Indexer, atau file watcher yang sedang membuka handle pembacaan untuk memindai berkas yang baru saja di-write. Tanpa retry backoff, `os.replace` langsung melempar `PermissionError: [WinError 5] Access is denied` atau `[WinError 32] Sharing violation`. Selain itu, berkas `.tmp` yang gagal replace tidak dibersihkan di blok `finally`.
- **Key Changes**:
  - `microstock/metadata/exporters.py` & `microstock-metadata-generator/src/microstock_metadata/exporters.py`:
    - Menambahkan fungsi `safe_replace(src, dst, max_retries=10, initial_delay=0.05)` dengan exponential retry backoff dan fallback unlinking untuk mengatasi lock transien Windows.
    - Memperbarui `_atomic_write_text` untuk menggunakan `safe_replace` dan menambahkan blok `finally` guna membersihkan berkas `.tmp` yatim jika terjadi kegagalan.
  - `microstock/metadata/checkpoint.py` & `microstock-metadata-generator/src/microstock_metadata/checkpoint.py`:
    - Menggunakan `safe_replace` pada `_persist()` untuk penyimpanan checkpoint dan membersihkan berkas `.tmp` di blok `finally`.
  - `microstock/metadata/cli.py` & `microstock-metadata-generator/src/microstock_metadata/cli.py`:
    - Menjadikan `_flush_outputs` di dalam iterasi per-item tidak mematikan loop jika terjadi kegagalan transien (mencatat warning log dan melanjutkan), lalu mengeksekusi flush final yang autoritatif setelah loop selesai.
  - `microstock/core/image_ops.py`, `upscaler.py`, `tracer.py`, `vector_ops.py`:
    - Mengintegrasikan `safe_replace` pada penyimpanan raster dan vektor final untuk mencegah `WinError 5` serupa.
  - `tests/test_image_ops.py` & `tests/test_cloudflare_rotation.py`:
    - Menambahkan unit test `test_safe_replace` dan `test_safe_replace_retry` dengan simulasi `PermissionError`.
    - Memperbaiki isolasi test environment variable Cloudflare rotation dari file `.env` lokal.
- **Verification**:
  - Seluruh 38 unit tests di `tests/` lulus 100%.
- **Proposed Commit**:
  `fix(metadata): add resilient safe_replace with retry backoff for windows file locks`
