"""Tests for preflight validation and binary discovery."""

import pytest
from microstock.preflight import PreflightError, resolve_binary, validate_dependencies, get_tool_map


def test_resolve_binary_known_path(monkeypatch):
    monkeypatch.setenv("MICROSTOCK_TESTTOOL_PATH", "C:/does/not/exist.exe")
    assert resolve_binary("testtool") is None


def test_resolve_binary_env_override(tmp_path, monkeypatch):
    dummy_exe = tmp_path / "dummy.exe"
    dummy_exe.write_text("dummy")
    monkeypatch.setenv("MICROSTOCK_CUSTOM_PATH", str(dummy_exe))
    assert resolve_binary("custom") == str(dummy_exe)


def test_validate_dependencies_missing():
    with pytest.raises(PreflightError, match="Missing required external CLI tools"):
        validate_dependencies(["nonexistent_tool_12345"])


def test_validate_dependencies_success():
    # exiftool and ffmpeg are present on this machine
    res = validate_dependencies(["exiftool", "ffmpeg"])
    assert "exiftool" in res and "ffmpeg" in res


def test_get_tool_map():
    tool_map = get_tool_map()
    assert "exiftool" in tool_map
    assert "upscayl" in tool_map
    assert "vtracer" in tool_map
    assert "inkscape" in tool_map
    assert "ffmpeg" in tool_map
    assert "ffprobe" in tool_map
