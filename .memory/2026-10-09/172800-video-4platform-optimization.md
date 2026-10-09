# Video 4-Platform Optimization Implementation

- **Date**: 2026-10-09 17:28:00 +07:00
- **Task / Problem**: Mengimplementasikan optimasi metadata video multi-platform untuk 4 portal stock (Adobe Stock, Dreamstime, Vecteezy, Pixabay) sesuai [2026-10-09-video-4platform-optimization-plan.md](file:///C:/Side/Microstock/plans/2026-10-09-video-4platform-optimization-plan.md).
- **Plan Link**: [plans/2026-10-09-video-4platform-optimization-plan.md](file:///C:/Side/Microstock/plans/2026-10-09-video-4platform-optimization-plan.md)

## Berkas yang Diubah / Ditambah

- [`src/microstock_metadata/platforms.py`](file:///C:/Side/Microstock/microstock-metadata-generator/src/microstock_metadata/platforms.py) (Baru): Profil publikasi per platform (`PLATFORMS`) dan batasan kata/karakter.
- [`src/microstock_metadata/config.py`](file:///C:/Side/Microstock/microstock-metadata-generator/src/microstock_metadata/config.py): Tambah field `platform` pada `MetadataConfig` beserta validasinya.
- [`src/microstock_metadata/schemas.py`](file:///C:/Side/Microstock/microstock-metadata-generator/src/microstock_metadata/schemas.py): Tambah field `is_ai_generated`, `needs_model_release`, `needs_property_release` pada `ProcessingResult`.
- [`src/microstock_metadata/video_processing.py`](file:///C:/Side/Microstock/microstock-metadata-generator/src/microstock_metadata/video_processing.py): Parsing `codec_name`, `avg_frame_rate` (fps), `format_name` (container) di `probe_video` serta fungsi gate murni `assess_video`.
- [`src/microstock_metadata/cli.py`](file:///C:/Side/Microstock/microstock-metadata-generator/src/microstock_metadata/cli.py): Integrasi soft-gate video (dengan pengecualian vertikal HD 9:16), penggabungan `review_reasons`, propagasi field AI/release, serta pemotongan limit berbasis `resolve_limits`.
- [`src/microstock_metadata/normalization.py`](file:///C:/Side/Microstock/microstock-metadata-generator/src/microstock_metadata/normalization.py): Fungsi helper `resolve_limits`.
- [`src/microstock_metadata/prompts.py`](file:///C:/Side/Microstock/microstock-metadata-generator/src/microstock_metadata/prompts.py): Penambahan prompt `MICROSTOCK_VIDEO_V2` / `microstock-video-v2`.
- [`src/microstock_metadata/csv_embed.py`](file:///C:/Side/Microstock/microstock-metadata-generator/src/microstock_metadata/csv_embed.py): `cap_phrase_keywords`, `convert_video_rows`, `convert_video_file` untuk ekspor 4 platform video.
- [`scripts/csv_to_embed.py`](file:///C:/Side/Microstock/microstock-metadata-generator/scripts/csv_to_embed.py): Dukungan CLI flag multi-platform video (`--adobe-video-out`, `--vecteezy-out`, `--pixabay-out`, `--media-type`).
- [`src/microstock_metadata/exporters.py`](file:///C:/Side/Microstock/microstock-metadata-generator/src/microstock_metadata/exporters.py): Penambahan 3 kolom baru di ekor `CSV_COLUMNS` (`is_ai_generated`, `needs_model_release`, `needs_property_release`).
- [`README.md`](file:///C:/Side/Microstock/microstock-metadata-generator/README.md): Dokumentasi §9d Video untuk 4 platform.
- [`examples/sample_config.yaml`](file:///C:/Side/Microstock/microstock-metadata-generator/examples/sample_config.yaml): Pengaktifan opsi `platform: adobe`.
- [`examples/sample_video_output.json`](file:///C:/Side/Microstock/microstock-metadata-generator/examples/sample_video_output.json) (Baru): Contoh output video valid.
- Test suites:
  - [`tests/test_platforms.py`](file:///C:/Side/Microstock/microstock-metadata-generator/tests/test_platforms.py) (Baru)
  - [`tests/test_cli_video_gate.py`](file:///C:/Side/Microstock/microstock-metadata-generator/tests/test_cli_video_gate.py) (Baru)
  - [`tests/test_csv_embed_video.py`](file:///C:/Side/Microstock/microstock-metadata-generator/tests/test_csv_embed_video.py) (Baru)
  - [`tests/test_exporters.py`](file:///C:/Side/Microstock/microstock-metadata-generator/tests/test_exporters.py) (Diperbarui)
  - [`tests/test_normalization.py`](file:///C:/Side/Microstock/microstock-metadata-generator/tests/test_normalization.py) (Diperbarui)
  - [`tests/test_prompts.py`](file:///C:/Side/Microstock/microstock-metadata-generator/tests/test_prompts.py) (Diperbarui)
  - [`tests/test_video_processing.py`](file:///C:/Side/Microstock/microstock-metadata-generator/tests/test_video_processing.py) (Diperbarui)

## Keputusan Teknis & Bisnis

- Baseline tetap Adobe-strict (70 char title, 25-49 phrase keywords) sebagai default universal, varian platform lain diturunkan secara deterministik saat ekspor CSV.
- Pengecekan kualitas teknis video diterapkan sebagai **soft-gate** (`review_reasons`), tidak menolak (hard-fail) proses klip kecuali container korup / unreadable.
- Klip vertikal HD (720x1280 dan 1080x1920) dikecualikan secara khusus dari flag `below_hd_min`.
- Dreamstime mengecualikan kata stopwords dan memecah frasa menjadi single lowercase words.
- Kolom baru pada `metadata.csv` diletakkan di akhir untuk menjaga kompatibilitas pembaca CSV lama.

## Asumsi & Risiko

- Batasan numerik platform diambil dari pengetahuan cutoff dan kode lokal yang ada. Perubahan batas di portal di masa mendatang dapat disesuaikan cukup dengan mengedit [`src/microstock_metadata/platforms.py`](file:///C:/Side/Microstock/microstock-metadata-generator/src/microstock_metadata/platforms.py).
- Nomor kategori Adobe tetap menggunakan nama kategori standar (bukan kode integer angka) sesuai kesepakatan mitigasi plan.

## Blocker / Open Items

- Tidak ada blocker teknis aktif.
- 4 open questions (angka final portal, kategori Adobe nomor vs nama, default frames 6 vs 8, kategori Vecteezy map) diteruskan ke owner untuk keputusan sebelum rilis publikasi massal.

## Verifikasi yang Dilakukan

1. Pytest suite lengkap: 121 passed, 1 deselected in 20.51s.
2. CLI help verification: `python scripts/csv_to_embed.py --help` menampilkan semua opsi baru.
3. Doctor check: `run.bat doctor` status OK (semua tool terdeteksi termasuk ffmpeg/ffprobe, offline-ready).
4. Validasi file JSON contoh: `examples/sample_video_output.json` terbukti valid.

## Proposed Conventional Commit (1 baris)

```text
feat: add 4-platform video stock metadata export and quality gates
```
