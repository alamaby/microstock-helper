"""Native raster image conversions using Pillow."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image


def is_jpeg_bytes(path: str) -> bool:
    """Check if file starts with JPEG magic bytes FF D8."""
    try:
        with open(path, "rb") as fh:
            magic = fh.read(2)
            return len(magic) == 2 and magic[0] == 0xFF and magic[1] == 0xD8
    except Exception:
        return False


def is_png_bytes(path: str) -> bool:
    """Check if file starts with PNG magic bytes 89 50 4E 47."""
    try:
        with open(path, "rb") as fh:
            magic = fh.read(4)
            return len(magic) == 4 and magic == b"\x89PNG"
    except Exception:
        return False


def convert_image_to_jpeg(
    src_path: str,
    dest_path: str,
    quality: int = 95,
    max_edge: Optional[int] = None,
    overwrite: bool = True,
) -> str:
    """Convert any supported raster image to a high-quality JPEG.

    Transparencies (RGBA/LA/Palette) are composited onto a solid white background.
    """
    if not overwrite and os.path.isfile(dest_path) and is_jpeg_bytes(dest_path):
        return dest_path

    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)

    with Image.open(src_path) as img:
        # Normalize orientation if EXIF orientation is present
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            # Stock photo standard: composite alpha onto clean white background
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[3])
            rgb = bg
        elif img.mode != "RGB":
            rgb = img.convert("RGB")
        else:
            rgb = img.copy()

        if max_edge and max(rgb.size) > max_edge:
            ratio = max_edge / float(max(rgb.size))
            new_size = (int(rgb.size[0] * ratio), int(rgb.size[1] * ratio))
            rgb = rgb.resize(new_size, Image.Resampling.LANCZOS)

        temp_dest = f"{dest_path}.tmp"
        rgb.save(temp_dest, format="JPEG", quality=quality, subsampling=0)
        if os.path.isfile(dest_path):
            os.remove(dest_path)
        os.rename(temp_dest, dest_path)

    return dest_path


def batch_convert_to_jpg(
    src_dir: str,
    dest_dir: str,
    quality: int = 95,
    max_edge: Optional[int] = None,
    allowed_exts: Tuple[str, ...] = (".png", ".webp", ".tif", ".tiff", ".bmp", ".jpg", ".jpeg"),
    overwrite: bool = False,
) -> List[Tuple[str, str]]:
    """Convert all images in src_dir into dest_dir as .jpg files."""
    converted: List[Tuple[str, str]] = []
    src_path = Path(src_dir)
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    for item in sorted(src_path.iterdir()):
        if not item.is_file():
            continue
        if item.suffix.lower() not in allowed_exts:
            continue

        out_file = dest_path / f"{item.stem}.jpg"
        convert_image_to_jpeg(
            str(item),
            str(out_file),
            quality=quality,
            max_edge=max_edge,
            overwrite=overwrite,
        )
        converted.append((str(item), str(out_file)))

    return converted
