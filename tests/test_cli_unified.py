"""Unit tests for the unified CLI interface."""

import pytest
from microstock.cli import build_parser, main
from PIL import Image


def test_cli_parser_help():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])


def test_cli_doctor(capsys):
    ret = main(["doctor"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "MICROSTOCK SYSTEM DIAGNOSTIC (DOCTOR)" in captured.out
    assert "External CLI Tools" in captured.out


def test_cli_convert(tmp_path, capsys):
    src = tmp_path / "src"
    out = tmp_path / "out"
    src.mkdir()
    img = Image.new("RGB", (20, 20), color="red")
    img.save(str(src / "test.png"))

    ret = main(["convert", str(src), "--out", str(out)])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Successfully converted 1 files" in captured.out
    assert (out / "test.jpg").exists()


def test_cli_renumber(tmp_path, capsys):
    (tmp_path / "b.jpg").write_text("b")
    (tmp_path / "a.jpg").write_text("a")

    ret = main(["renumber", str(tmp_path), "--dry-run"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Would rename 2 files" in captured.out


def test_cli_preflight_abort(monkeypatch, capsys, tmp_path):
    from microstock import cli
    from microstock.preflight import PreflightError

    dummy_dir = tmp_path / "batch"
    dummy_dir.mkdir()

    def mock_validate(tools, require_api_key=False):
        raise PreflightError("Missing required external CLI tools: exiftool")

    monkeypatch.setattr(cli, "validate_dependencies", mock_validate)

    ret = main(["run", str(dummy_dir), "--target", "JPG"])
    assert ret == 2
    captured = capsys.readouterr()
    assert "Preflight dependency check failed" in captured.err


def test_cli_embed_jpg(tmp_path, capsys, monkeypatch):
    from microstock import cli

    # Mock validate_dependencies so it doesn't require actual exiftool binary in unit test
    monkeypatch.setattr(cli, "validate_dependencies", lambda tools: None)

    # Mock embed_jpg_file
    embedded = []
    def mock_embed(dest, title, desc, kws, copyr, creator):
        embedded.append((dest, title))
        return True

    from microstock.core import metadata_embed
    monkeypatch.setattr(metadata_embed, "embed_jpg_file", mock_embed)

    images_dir = tmp_path / "images"
    out_dir = tmp_path / "out"
    images_dir.mkdir()
    (images_dir / "001.jpg").write_text("data")

    csv_file = tmp_path / "meta.csv"
    csv_file.write_text("Filename,Title,Description,Keywords\n001.jpg,Sample Title,Sample Desc,kw1\n", encoding="utf-8")

    ret = main(["embed-jpg", "--csv", str(csv_file), "--images", str(images_dir), "--out", str(out_dir)])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Embedded metadata into 1 image files" in captured.out
    assert len(embedded) == 1
    assert (out_dir / "001.jpg").exists()

