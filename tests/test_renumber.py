"""Unit tests for sequential file renumbering."""

import time
from microstock.core.renumber import extract_3digit_number, renumber_directory


def test_extract_3digit_number():
    assert extract_3digit_number("001_photo.jpg") == "001"
    assert extract_3digit_number("batch__042-test.png") == "042"
    assert extract_3digit_number("item-123.jpg") == "123"
    assert extract_3digit_number("photo.jpg") is None
    assert extract_3digit_number("2026-10-03-something.jpg") is None  # 4 digits date shouldn't match as 3-digit alone if followed by digits


def test_renumber_directory_basic(tmp_path):
    f1 = tmp_path / "zebra.jpg"
    f2 = tmp_path / "apple.jpg"
    f1.write_text("1")
    time.sleep(0.01)
    f2.write_text("2")

    # In dry run, files are not renamed
    plan = renumber_directory(str(tmp_path), dry_run=True)
    assert len(plan) == 2
    assert f1.exists()
    assert f2.exists()

    # Actual renumber
    res = renumber_directory(str(tmp_path), dry_run=False)
    assert len(res) == 2
    names = sorted([f.name for f in tmp_path.iterdir()])
    assert names[0].startswith("001_")
    assert names[1].startswith("002_")


def test_renumber_already_numbered(tmp_path):
    (tmp_path / "001_one.jpg").write_text("1")
    (tmp_path / "002_two.jpg").write_text("2")

    # Should detect no-op
    res = renumber_directory(str(tmp_path))
    assert len(res) == 2
    assert (tmp_path / "001_one.jpg").exists()
    assert (tmp_path / "002_two.jpg").exists()
