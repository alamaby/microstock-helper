# Task: Remove Local AI Model Backend from microstock-metadata-generator

- **Date / Time**: 2026-11-03 08:55:00 +07:00
- **Scope**: `microstock-metadata-generator/` & `Process-Batch.ps1`

## Problem & Context
Inference model lokal (Qwen2.5-VL via PyTorch / Hugging Face Transformers) pada mesin lokal dinilai terlalu lambat (~3–14 menit/gambar) dan membebani dependensi lingkungan (torch, torchvision, transformers, accelerate, bitsandbytes, dsb.). Sistem telah memiliki backend API vision multi-tier yang sangat cepat dan stabil (OpenAI-compatible local gateway dengan failover otomatis ke Cloudflare Workers AI). Seluruh mekanisme model lokal dihapus agar sistem lebih ramping, cepat, dan terfokus pada API backend.

## Key Changes
1. **Dihapus (File Berlebih)**:
   - `src/microstock_metadata/model_loader.py`: Pemuatan model lokal PyTorch, bitsandbytes 4-bit, CUDA/CPU device selector.
   - `src/microstock_metadata/inference.py`: Eksekusi inferensi lokal Hugging Face Transformers.
   - `scripts/download_model.py`: Script download snapshot Hugging Face Hub.
   - `tests/test_real_model.py`: Test model lokal Hugging Face.
   - `requirements-gpu.txt`: Dependensi CUDA/bitsandbytes.
2. **CLI & Engine (`cli.py`, `console_art.py`, `constants.py`, `schemas.py`)**:
   - `cleanup_memory()` disederhanakan murni menjadi pemanggilan `gc.collect()`.
   - Command `download-model` dihapus dari CLI parser.
   - Opsi `--backend` dikunci hanya menerima `api` (input `local` memicu validasi error yang jelas).
   - Flag model lokal (`--model-id`, `--device`, `--quantization`, `--offline`) disupres/didepresiasi.
   - Command `doctor` diperbarui untuk mengecek dependensi dasar (Python, PIL, pydantic, yaml, ffmpeg, ffprobe) dan mendeteksi kesiapan API keys (`MICROSTOCK_API_KEY` & `MICROSTOCK_CF_API_TOKEN`) tanpa ketergantungan PyTorch/CUDA/cache.
   - Pipeline pemrosesan `cmd_generate` dan `_process_one` dipusatkan ke `api_inference.build_providers` dan `generate_with_fallback`.
3. **Konfigurasi (`config.py`, `config.yaml`, `examples/sample_config.yaml`, `.env.example`)**:
   - Default backend adalah `api`. Jika `backend != "api"`, `validate_config` melempar `ConfigurationError`.
   - Bagian `model:` lokal (Qwen, device, quantization, offline) dihapus dari konfigurasi.
   - Bagian 3 (Local inference & cache) dihapus dari `.env.example`.
4. **Dependensi & Setup (`pyproject.toml`, `requirements.txt`, `setup.bat`, `scripts/verify_environment.py`)**:
   - `requirements.txt` dan `pyproject.toml` dirampingkan menjadi hanya `pillow`, `pydantic>=2`, dan `pyyaml`.
   - `setup.bat` disederhanakan tanpa cabang GPU/CUDA PyTorch.
   - `verify_environment.py` disesuaikan untuk memverifikasi dependensi API.
5. **Skrip Orkestrasi (`Process-Batch.ps1`)**:
   - Parameter `-Backend` disesuaikan hanya menerima `api`.
6. **Tests (`tests/`)**:
   - `test_cli.py`, `test_config.py`, dan `test_integration.py` dimutakhirkan untuk menguji inferensi API dan penolakan backend `local`.
   - Seluruh 126 test unit/integration passed 100%.

## Technical & Business Decisions
- Parameter `--backend api` dipertahankan untuk backward compatibility penuh dengan skrip PowerShell yang sudah ada (`Orchestrate-Stock.ps1`, `Process-Batch.ps1`).
- Argumen `--backend local` menghasilkan error konfigurasi (exit code 2) yang ramah pengguna.
- Modul `doctor` memberikan status visual kesiapan token API gateway lokal dan fallback Cloudflare.

## Risks & Assumptions
- Generator metadata memerlukan setidaknya satu API provider aktif yang terkonfigurasi (local-gateway atau Cloudflare Workers AI) melalui berkas `.env` atau environment variable.

## Verification
- Menjalankan `microstock-metadata doctor`:
  ```
  python OK, PIL OK, pydantic OK, yaml OK, ffmpeg OK, ffprobe OK, api-key OK, output-writable OK
  ```
- Menjalankan `verify_environment.py`: `RESULT: READY`
- Menjalankan test suite pytest: 126 passed dalam 4.60 detik.

## Proposed Conventional Commit
`refactor(metadata-generator): remove local ai model and enforce api backend`
