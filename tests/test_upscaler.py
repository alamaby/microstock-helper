"""Unit tests for upscaler module and unicode subprocess safety."""

import os
from unittest.mock import MagicMock, patch
from microstock.core.upscaler import get_default_models_dir, upscale_image


def test_get_default_models_dir(tmp_path):
    res_dir = tmp_path / "resources"
    bin_dir = res_dir / "bin"
    models_dir = res_dir / "models"
    bin_dir.mkdir(parents=True)
    models_dir.mkdir(parents=True)

    fake_bin = bin_dir / "upscayl-bin.exe"
    fake_bin.write_text("binary")

    detected = get_default_models_dir(str(fake_bin))
    assert os.path.abspath(detected) == os.path.abspath(str(models_dir))


def test_upscale_image_skip_existing(tmp_path):
    in_img = tmp_path / "in.jpg"
    in_img.write_bytes(b"dummy image data" * 100)

    out_img = tmp_path / "out.png"
    out_img.write_bytes(b"existing output" * 200)

    # Should skip execution since out_img exists and > 1024 bytes
    with patch("subprocess.run") as mock_sub:
        res = upscale_image(str(in_img), str(out_img), overwrite=False)
        assert res == str(out_img)
        mock_sub.assert_not_called()


def test_upscale_subprocess_encodes_utf8(tmp_path):
    in_img = tmp_path / "in.jpg"
    in_img.write_bytes(b"dummy image data")

    out_img = tmp_path / "out.png"

    def fake_subprocess_run(cmd, **kwargs):
        # Verify encoding and errors are explicitly passed
        assert kwargs.get("encoding") == "utf-8"
        assert kwargs.get("errors") == "replace"

        # Simulate creation of short_out in the temp dir
        out_idx = cmd.index("-o") + 1
        short_out_path = cmd[out_idx]
        with open(short_out_path, "wb") as fh:
            fh.write(b"upscaled fake data")

        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "Upscayl progress: \u2026 \u2588 100%"
        mock_res.stderr = ""
        return mock_res

    with patch("microstock.core.upscaler.resolve_binary", return_value="fake_upscayl.exe"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):
        res = upscale_image(str(in_img), str(out_img), overwrite=True)
        assert res == str(out_img)
        assert os.path.isfile(out_img)
