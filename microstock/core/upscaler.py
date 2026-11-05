"""Upscayl CLI wrapper with MAX_PATH 260 character workaround."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from ..preflight import resolve_binary


def get_default_models_dir(binary_path: str) -> str:
    """Infer models directory from Upscayl binary installation location."""
    bin_dir = os.path.dirname(binary_path)
    # Binary is typically inside resources/bin
    res_dir = os.path.dirname(bin_dir)
    models_dir = os.path.join(res_dir, "models")
    if os.path.isdir(models_dir):
        return models_dir
    return bin_dir


def upscale_image(
    input_path: str,
    output_path: str,
    binary_path: Optional[str] = None,
    scale: int = 5,
    model_name: str = "upscayl-standard-4x",
    models_dir: Optional[str] = None,
    gpu: str = "auto",
    overwrite: bool = False,
) -> str:
    """Upscale an image using Upscayl CLI.

    Bypasses Windows MAX_PATH (260 character) limitation by running via
    short temporary paths in the system temp directory.
    """
    if not overwrite and os.path.isfile(output_path) and os.path.getsize(output_path) > 1024:
        return output_path

    bin_path = resolve_binary("upscayl", binary_path)
    if not bin_path:
        raise FileNotFoundError("Upscayl binary not found. Run preflight check.")

    m_dir = models_dir or get_default_models_dir(bin_path)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Use short temporary directory to avoid Windows MAX_PATH failure
    with tempfile.TemporaryDirectory(prefix="ms_ups_") as temp_dir:
        in_ext = Path(input_path).suffix or ".png"
        short_in = os.path.join(temp_dir, f"u_in{in_ext}")
        short_out = os.path.join(temp_dir, "u_out.png")

        shutil.copy2(input_path, short_in)

        # Scale model is 4 for upscayl-standard-4x; output scale can be 2, 3, 4, 5
        cmd = [
            bin_path,
            "-i", short_in,
            "-o", short_out,
            "-m", m_dir,
            "-n", model_name,
            "-z", "4",
            "-s", str(scale),
            "-f", "png",
            "-v",
        ]
        if gpu and gpu != "auto":
            cmd.extend(["-g", str(gpu)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0 or not os.path.isfile(short_out):
            err_msg = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"Upscayl failed (exit code {result.returncode}): {err_msg}")

        # Atomic copy back to destination
        from .image_ops import safe_replace
        tmp_final = f"{output_path}.tmp"
        shutil.copy2(short_out, tmp_final)
        safe_replace(tmp_final, output_path)

    return output_path


def batch_upscale(
    input_dir: str,
    output_dir: str,
    binary_path: Optional[str] = None,
    scale: int = 5,
    overwrite: bool = False,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> List[Tuple[str, str]]:
    """Upscale all raster images in input_dir into output_dir."""
    in_path = Path(input_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    items = [
        f for f in sorted(in_path.iterdir())
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
    ]

    results: List[Tuple[str, str]] = []
    total = len(items)

    for idx, item in enumerate(items, 1):
        target = out_path / f"{item.stem}.png"
        if progress_cb:
            progress_cb(idx, total, item.name)

        upscale_image(
            str(item),
            str(target),
            binary_path=binary_path,
            scale=scale,
            overwrite=overwrite,
        )
        results.append((str(item), str(target)))

    return results
