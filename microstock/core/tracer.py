"""vtracer CLI wrapper: raster image to SVG vector tracing."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from ..preflight import resolve_binary


def is_valid_svg(path: str) -> bool:
    """Check if file exists and contains valid SVG opening tag."""
    if not os.path.isfile(path) or os.path.getsize(path) < 10:
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            header = fh.read(1024)
            return "<svg" in header.lower()
    except Exception:
        return False


def trace_image_to_svg(
    input_path: str,
    output_path: str,
    binary_path: Optional[str] = None,
    overwrite: bool = False,
) -> str:
    """Trace a raster image (JPG/PNG) into SVG via vtracer CLI."""
    if not overwrite and is_valid_svg(output_path):
        return output_path

    bin_path = resolve_binary("vtracer", binary_path)
    if not bin_path:
        raise FileNotFoundError("vtracer binary not found. Run preflight check.")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    temp_out = f"{output_path}.tmp"

    cmd = [
        bin_path,
        "--input", input_path,
        "--output", temp_out,
        "--clustering", "color-cluster",
        "--hierarchical", "cutout",
        "--mode", "spline",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0 or not is_valid_svg(temp_out):
        err_msg = result.stderr.strip() or result.stdout.strip()
        if os.path.isfile(temp_out):
            os.remove(temp_out)
        raise RuntimeError(f"vtracer failed for {input_path} (exit code {result.returncode}): {err_msg}")

    if os.path.isfile(output_path):
        os.remove(output_path)
    os.rename(temp_out, output_path)

    return output_path


def batch_trace(
    input_dir: str,
    output_dir: str,
    binary_path: Optional[str] = None,
    overwrite: bool = False,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> List[Tuple[str, str]]:
    """Trace all small JPGs in input_dir into SVGs in output_dir."""
    in_path = Path(input_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    items = [
        f for f in sorted(in_path.iterdir())
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png")
    ]

    results: List[Tuple[str, str]] = []
    total = len(items)

    for idx, item in enumerate(items, 1):
        target = out_path / f"{item.stem}.svg"
        if progress_cb:
            progress_cb(idx, total, item.name)

        trace_image_to_svg(
            str(item),
            str(target),
            binary_path=binary_path,
            overwrite=overwrite,
        )
        results.append((str(item), str(target)))

    return results
