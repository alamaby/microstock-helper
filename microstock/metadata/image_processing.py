"""Image preprocessing: EXIF orientation, RGB, longest-edge resize.

The Pillow stage only normalizes orientation/mode/size. The Qwen2.5-VL
processor's own smart resize (min/max_pixels) governs the final visual
token budget; processed_width/height below record the Pillow output size.
"""

from __future__ import annotations

from PIL import Image, ImageOps

from .exceptions import ImageReadError


def normalize_image(path: str, max_edge: int) -> tuple[Image.Image, int, int, int, int]:
    """Return (rgb_image, orig_w, orig_h, proc_w, proc_h). Caller must close."""
    try:
        img = Image.open(path)
        img.load()
    except Exception as exc:
        raise ImageReadError(f"Cannot open image {path}: {exc}") from exc
    try:
        img = ImageOps.exif_transpose(img)
        orig_w, orig_h = img.size
        if img.mode != "RGB":
            img = img.convert("RGB")
        longest = max(orig_w, orig_h)
        if longest > max_edge:
            scale = max_edge / longest
            new_size = (max(1, int(orig_w * scale)), max(1, int(orig_h * scale)))
            img = img.resize(new_size, Image.LANCZOS)
        return img, orig_w, orig_h, img.size[0], img.size[1]
    except Exception as exc:
        try:
            img.close()
        except Exception:
            pass
        raise ImageReadError(f"Cannot normalize image {path}: {exc}") from exc
