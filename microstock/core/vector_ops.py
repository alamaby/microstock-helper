"""Inkscape CLI wrapper: SVG to EPS conversion and raster preview generation."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, List, Optional, Tuple
from PIL import Image

from ..preflight import resolve_binary


def is_valid_eps(path: str) -> bool:
    """Check if file exists and starts with PostScript header '%!'."""
    if not os.path.isfile(path) or os.path.getsize(path) < 4:
        return False
    try:
        with open(path, "rb") as fh:
            magic = fh.read(4)
            return len(magic) == 4 and magic[:2] == b"%!"
    except Exception:
        return False


def convert_svg_to_eps(
    svg_path: str,
    eps_path: str,
    binary_path: Optional[str] = None,
    overwrite: bool = False,
) -> str:
    """Convert an SVG file to PostScript EPS via Inkscape CLI."""
    if not overwrite and is_valid_eps(eps_path):
        return eps_path

    bin_path = resolve_binary("inkscape", binary_path)
    if not bin_path:
        raise FileNotFoundError("Inkscape binary not found. Run preflight check.")

    os.makedirs(os.path.dirname(os.path.abspath(eps_path)), exist_ok=True)
    temp_eps = f"{eps_path}.tmp"

    cmd = [
        bin_path,
        svg_path,
        "--export-type=eps",
        f"--export-filename={temp_eps}",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0 or not is_valid_eps(temp_eps):
        err_msg = result.stderr.strip() or result.stdout.strip()
        if os.path.isfile(temp_eps):
            os.remove(temp_eps)
        raise RuntimeError(f"Inkscape EPS conversion failed for {svg_path}: {err_msg}")

    from .image_ops import safe_replace
    safe_replace(temp_eps, eps_path)

    return eps_path


def render_svg_preview(
    svg_path: str,
    jpg_path: str,
    width: int = 6000,
    quality: int = 95,
    binary_path: Optional[str] = None,
    overwrite: bool = False,
) -> str:
    """Render high-resolution preview JPG from SVG via Inkscape and Pillow."""
    from .image_ops import is_jpeg_bytes

    if not overwrite and os.path.isfile(jpg_path) and is_jpeg_bytes(jpg_path):
        return jpg_path

    bin_path = resolve_binary("inkscape", binary_path)
    if not bin_path:
        raise FileNotFoundError("Inkscape binary not found. Run preflight check.")

    os.makedirs(os.path.dirname(os.path.abspath(jpg_path)), exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ms_ink_") as tmp_dir:
        temp_png = os.path.join(tmp_dir, "render.png")
        cmd = [
            bin_path,
            svg_path,
            "--export-type=png",
            f"--export-width={width}",
            f"--export-filename={temp_png}",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0 or not os.path.isfile(temp_png):
            err_msg = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"Inkscape preview render failed for {svg_path}: {err_msg}")

        # Convert rendered PNG to clean JPEG
        with Image.open(temp_png) as img:
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                rgba = img.convert("RGBA")
                bg = Image.new("RGB", rgba.size, (255, 255, 255))
                bg.paste(rgba, mask=rgba.split()[3])
                rgb = bg
            elif img.mode != "RGB":
                rgb = img.convert("RGB")
            else:
                rgb = img.copy()

            temp_jpg = f"{jpg_path}.tmp"
            rgb.save(temp_jpg, format="JPEG", quality=quality, subsampling=0)
            if os.path.isfile(jpg_path):
                os.remove(jpg_path)
            os.rename(temp_jpg, jpg_path)

    return jpg_path


def batch_convert_eps(
    svg_dir: str,
    eps_dir: str,
    binary_path: Optional[str] = None,
    overwrite: bool = False,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> List[Tuple[str, str]]:
    """Convert all SVGs in svg_dir into EPS in eps_dir."""
    in_path = Path(svg_dir)
    out_path = Path(eps_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    items = [f for f in sorted(in_path.iterdir()) if f.is_file() and f.suffix.lower() == ".svg"]
    results: List[Tuple[str, str]] = []
    total = len(items)

    for idx, item in enumerate(items, 1):
        target = out_path / f"{item.stem}.eps"
        if progress_cb:
            progress_cb(idx, total, item.name)

        convert_svg_to_eps(str(item), str(target), binary_path=binary_path, overwrite=overwrite)
        results.append((str(item), str(target)))

    return results


def batch_render_previews(
    svg_dir: str,
    jpg_dir: str,
    width: int = 6000,
    quality: int = 95,
    binary_path: Optional[str] = None,
    overwrite: bool = False,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> List[Tuple[str, str]]:
    """Render preview JPGs for all SVGs in svg_dir."""
    in_path = Path(svg_dir)
    out_path = Path(jpg_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    items = [f for f in sorted(in_path.iterdir()) if f.is_file() and f.suffix.lower() == ".svg"]
    results: List[Tuple[str, str]] = []
    total = len(items)

    for idx, item in enumerate(items, 1):
        target = out_path / f"{item.stem}.jpg"
        if progress_cb:
            progress_cb(idx, total, item.name)

        render_svg_preview(
            str(item),
            str(target),
            width=width,
            quality=quality,
            binary_path=binary_path,
            overwrite=overwrite,
        )
        results.append((str(item), str(target)))

    return results
