"""Unit tests for packaging and agency segregation."""

import csv
from pathlib import Path
from microstock.pipeline.packaging import (
    sanitize_vecteezy_filename,
    package_agency_directory,
    verify_upload_readiness,
)


def test_sanitize_vecteezy_filename():
    assert sanitize_vecteezy_filename("001_beautiful photo!.jpg") == "001_beautiful_photo.jpg"
    assert sanitize_vecteezy_filename("hello (world) [final].eps") == "hello_world_final.eps"
    assert sanitize_vecteezy_filename("clean_file.png") == "clean_file.png"


def test_package_agency_directory_adobe(tmp_path):
    out_base = tmp_path / "output"
    src_img = tmp_path / "001_apple.jpg"
    src_img.write_text("fake jpeg")

    csv_file = tmp_path / "adobe.csv"
    csv_file.write_text("SourceFile,Title,Keywords\n001_apple.jpg,Apple,fruit\n")

    target_dir, count = package_agency_directory(
        agency="adobe",
        target_kind="JPG",
        out_base_dir=str(out_base),
        source_files=[str(src_img)],
        csv_path=str(csv_file),
    )

    assert count == 1
    assert Path(target_dir).name == "for_adobe"
    assert (Path(target_dir) / "001_apple.jpg").exists()
    assert (Path(target_dir) / "adobe.csv").exists()


def test_package_agency_directory_vecteezy(tmp_path):
    out_base = tmp_path / "output"
    src_img = tmp_path / "001 special! photo.jpg"
    src_img.write_text("fake jpeg")

    csv_file = tmp_path / "vecteezy.csv"
    csv_file.write_text("Filename,Title,Keywords,License\n001 special! photo.jpg,Photo,test,free\n")

    target_dir, count = package_agency_directory(
        agency="vecteezy",
        target_kind="JPG",
        out_base_dir=str(out_base),
        source_files=[str(src_img)],
        csv_path=str(csv_file),
    )

    assert count == 1
    assert Path(target_dir).name == "for_vecteezy_photo"
    sanitized_file = Path(target_dir) / "001_special_photo.jpg"
    assert sanitized_file.exists()

    # Check rewritten CSV filename field
    with open(Path(target_dir) / "vecteezy.csv", "r", encoding="utf-8") as fh:
        reader = list(csv.DictReader(fh))
        assert reader[0]["Filename"] == "001_special_photo"  # Vecteezy extensionless


def test_verify_upload_readiness(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()

    # Create companion CSV with long title for Adobe
    csv_file = pkg_dir / "adobe.csv"
    long_title = "A" * 75
    csv_file.write_text(f"Filename,Title,Keywords\n001.jpg,{long_title},apple,fruit\n")

    warns = verify_upload_readiness(str(pkg_dir), "adobe")
    assert any("Title 75ch > 70ch" in w for w in warns)
