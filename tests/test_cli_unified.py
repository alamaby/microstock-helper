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
