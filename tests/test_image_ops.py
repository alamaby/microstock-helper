"""Unit tests for raster image operations."""

import os
from PIL import Image
from microstock.core.image_ops import (
    is_jpeg_bytes,
    is_png_bytes,
    convert_image_to_jpeg,
    batch_convert_to_jpg,
)


def test_magic_bytes_detection(tmp_path):
    # Test valid jpeg
    jpg_path = tmp_path / "test.jpg"
    img = Image.new("RGB", (50, 50), color="blue")
    img.save(str(jpg_path), format="JPEG")
    assert is_jpeg_bytes(str(jpg_path)) is True
    assert is_png_bytes(str(jpg_path)) is False

    # Test valid png
    png_path = tmp_path / "test.png"
    img_png = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))
    img_png.save(str(png_path), format="PNG")
    assert is_png_bytes(str(png_path)) is True
    assert is_jpeg_bytes(str(png_path)) is False

    # Nonexistent
    assert is_jpeg_bytes(str(tmp_path / "missing.jpg")) is False


def test_convert_image_to_jpeg_rgba_white_background(tmp_path):
    # Create RGBA with transparency
    src_png = tmp_path / "transparent.png"
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))  # fully transparent
    img.save(str(src_png), format="PNG")

    dest_jpg = tmp_path / "out.jpg"
    res = convert_image_to_jpeg(str(src_png), str(dest_jpg), quality=90)
    assert res == str(dest_jpg)
    assert os.path.exists(str(dest_jpg))
    assert is_jpeg_bytes(str(dest_jpg))

    # Read back and verify background turned white
    with Image.open(str(dest_jpg)) as out_img:
        assert out_img.mode == "RGB"
        pixel = out_img.getpixel((10, 10))
        # JPEG compression might slightly alter 255 to 254-255
        assert pixel[0] >= 250 and pixel[1] >= 250 and pixel[2] >= 250


def test_convert_image_downsample(tmp_path):
    src_png = tmp_path / "large.png"
    img = Image.new("RGB", (2000, 1000), color="green")
    img.save(str(src_png), format="PNG")

    dest_jpg = tmp_path / "downsampled.jpg"
    convert_image_to_jpeg(str(src_png), str(dest_jpg), max_edge=800)

    with Image.open(str(dest_jpg)) as out_img:
        assert max(out_img.size) == 800
        assert out_img.size == (800, 400)


def test_batch_convert_to_jpg(tmp_path):
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()

    # Create 2 pngs and 1 txt file
    Image.new("RGB", (50, 50), "red").save(str(src_dir / "img1.png"))
    Image.new("RGB", (50, 50), "green").save(str(src_dir / "img2.png"))
    (src_dir / "ignore.txt").write_text("hello")

    results = batch_convert_to_jpg(str(src_dir), str(dest_dir))
    assert len(results) == 2
    assert (dest_dir / "img1.jpg").exists()
    assert (dest_dir / "img2.jpg").exists()
    assert not (dest_dir / "ignore.jpg").exists()


def test_safe_replace(tmp_path):
    from microstock.core.image_ops import safe_replace

    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("new content")
    dst.write_text("old content")

    safe_replace(str(src), str(dst))
    assert dst.read_text() == "new content"
    assert not src.exists()


def test_safe_replace_retry(tmp_path, monkeypatch):
    from microstock.core.image_ops import safe_replace
    import os

    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("retried content")
    dst.write_text("original content")

    real_replace = os.replace
    attempts = [0]

    def mock_replace(s, d):
        attempts[0] += 1
        if attempts[0] < 3:
            raise PermissionError(5, "Access is denied (simulated lock)")
        return real_replace(s, d)

    monkeypatch.setattr(os, "replace", mock_replace)
    safe_replace(str(src), str(dst), max_retries=5, initial_delay=0.01)

    assert attempts[0] == 3
    assert dst.read_text() == "retried content"
