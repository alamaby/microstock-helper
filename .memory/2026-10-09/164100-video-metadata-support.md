# Video Metadata Support Implementation

- **Tanggal/Waktu**: 2026-10-09 16:41:00 +07:00
- **Plan**: [plans/2026-10-09-video-metadata-support-implementation-plan.md](file:///C:/Side/Microstock/plans/2026-10-09-video-metadata-support-implementation-plan.md)

## Task / Masalah
Menambah dukungan input video (klip 8–10 detik, visual-only, backend `api`) ke `microstock-metadata-generator` dengan strategi uniform frame sampling (6 frame via ffmpeg sistem), memakai ulang pipeline inference/validasi/export tanpa mengubah perilaku image-only.

## Berkas yang Diubah / Dibuat
- `src/microstock_metadata/constants.py`: Tambah `SUPPORTED_VIDEO_EXTENSIONS`, `DEFAULT_VIDEO_FRAMES`, `VIDEO_MAX_DURATION_SEC`.
- `src/microstock_metadata/discovery.py`: Tambah `discover_inputs()` dengan filter `media_type` (`auto`/`image`/`video`) dan bungkus `discover_images()`.
- `src/microstock_metadata/config.py`: Dataclass `VideoConfig`, konfigurasi top-level `media_type`, validasi `--frames`, `--video-max-duration`, `--video-max-edge`.
- `src/microstock_metadata/prompts.py`: Prompt `microstock-video-v1` dengan instruksi urutan temporal dan aksi.
- `src/microstock_metadata/video_processing.py` *(baru)*: Ekstraksi metadata video via `ffprobe` dan uniform frame sampling via `ffmpeg`.
- `src/microstock_metadata/api_inference.py`: Multi-image payload support di `_payload`, `generate_once`, dan `generate_with_fallback`.
- `src/microstock_metadata/schemas.py`: Field `media_type`, `video_duration_sec`, `frame_count` di `ProcessingResult`.
- `src/microstock_metadata/exporters.py`: Penambahan 3 kolom metadata video di akhir `CSV_COLUMNS` dan `write_metadata_csv`.
- `src/microstock_metadata/cli.py`: Flag CLI video, fail-fast guard backend lokal untuk video, pemilihan prompt video, dan pengecekan `ffmpeg`/`ffprobe` di `cmd_doctor`.
- `examples/sample_config.yaml`: Dokumentasi blok konfigurasi `video:` dan `media_type: auto`.
- `README.md`: Subseksi `9c. Video input (API-only, uniform frames)`.
- `pyproject.toml`: Konfigurasi `addopts = "-m 'not real_model'"` untuk default testing.
- `tests/test_video_processing.py` *(baru)*: Unit test ekstraksi dan probing video mocked.
- `tests/test_discovery.py`: Test video extension & media_type discovery.
- `tests/test_config.py`: Test konfigurasi dan validasi video.
- `tests/test_prompts.py`: Test template prompt `microstock-video-v1`.
- `tests/test_api_inference.py`: Test payload multi-image API.
- `tests/test_exporters.py`: Test kolom CSV video.
- `tests/test_cli.py`: Test CLI API mocked untuk video, guard local backend, dan doctor ffmpeg.

## Keputusan Teknis & Bisnis
- **D1/D2**: Input video hanya didukung pada backend `api`. Percobaan menggunakan video dengan `--backend local` langsung ditolak dengan exit code 2 (mencegah OOM pada VRAM laptop 4GB).
- **D3**: Memakai `ffmpeg` dan `ffprobe` dari sistem yang sudah terpasang di PATH (v9.0.2), tanpa dependensi pip baru.
- **D4**: Menggunakan sampling uniform 6 frame temporal `(i + 0.5) * duration / count`.
- **N3**: Kolom CSV baru ditambahkan di akhir file agar kompatibel dengan pembaca CSV lama.

## Verifikasi yang Dilakukan
- Full test suite pytest: 103 passed, 1 deselected dalam 22s.
- `run.bat doctor`: Berhasil mendeteksi `ffmpeg` dan `ffprobe` OK.
- Uji coba generate synthetic 8s video clip:
  - `--media-type video --backend api --dry-run` berhasil menampilkan list file dengan exit code 0.
  - `--backend local` berhasil ditolak dengan pesan error dan exit code 2.

## Proposed Conventional Commit
```text
feat(generator): add video input support via ffmpeg uniform frame sampling and api backend
```
