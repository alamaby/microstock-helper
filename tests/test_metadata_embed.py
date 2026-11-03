"""Unit tests for metadata embedding and matching logic."""

import xml.etree.ElementTree as ET
from microstock.core.metadata_embed import (
    find_matching_file,
    read_metadata_csv,
    embed_svg_file,
    embed_jpg_file,
)
from PIL import Image


def test_find_matching_file():
    files = [
        "C:/media/001_photo.jpg",
        "C:/media/002_vector.eps",
        "C:/media/002_vector.jpg",
        "C:/media/batch__042-flower.png",
    ]

    # Exact filename match
    assert find_matching_file(files, "001_photo.jpg") == "C:/media/001_photo.jpg"

    # Stem match with different extension requested
    assert find_matching_file(files, "002_vector.eps", allowed_exts=(".jpg",)) == "C:/media/002_vector.jpg"

    # 3-digit number match fallback
    assert find_matching_file(files, "target__042_something.jpg") == "C:/media/batch__042-flower.png"

    # Not found
    assert find_matching_file(files, "999_none.jpg") is None


def test_read_metadata_csv(tmp_path):
    csv_file = tmp_path / "metadata.csv"
    csv_file.write_text(
        "SourceFile,Title,Description,Keywords,Copyright,Creator\n"
        "001.jpg,Test Title,Test Description,\"kw1, kw2\",(C) 2026,alamaby\n",
        encoding="utf-8",
    )

    rows = read_metadata_csv(str(csv_file))
    assert len(rows) == 1
    assert rows[0]["SourceFile"] == "001.jpg"
    assert rows[0]["Title"] == "Test Title"
    assert rows[0]["Keywords"] == "kw1, kw2"


def test_embed_svg_file(tmp_path):
    svg_file = tmp_path / "test.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100"/></svg>',
        encoding="utf-8",
    )

    ok = embed_svg_file(
        str(svg_file),
        title="Vector Rose",
        description="Beautiful vector rose illustration",
        keywords=["rose", "flower", "vector"],
        copyright="(C) 2026 alamaby",
        creator="alamaby",
    )
    assert ok is True

    # Parse and verify elements
    tree = ET.parse(str(svg_file))
    root = tree.getroot()
    assert "svg" in root.tag.lower()

    # Find title
    titles = [c for c in root if c.tag.endswith("title")]
    assert len(titles) == 1
    assert titles[0].text == "Vector Rose"

    # Find metadata
    metas = [c for c in root if c.tag.endswith("metadata")]
    assert len(metas) == 1


def test_embed_jpg_file_exiftool(tmp_path):
    # Test real ExifTool embedding since ExifTool is installed
    jpg_path = tmp_path / "sample.jpg"
    img = Image.new("RGB", (100, 100), color="yellow")
    img.save(str(jpg_path), format="JPEG")

    ok = embed_jpg_file(
        str(jpg_path),
        title="Yellow Box",
        description="A plain yellow box for testing",
        keywords=["yellow", "box", "minimalist"],
        copyright="alamaby",
        creator="alamaby",
    )
    assert ok is True
