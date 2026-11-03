"""Video processing: ffprobe metadata extraction and uniform frame sampling via ffmpeg."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import tempfile
from typing import Any

from PIL import Image, ImageOps

from .exceptions import ImageReadError


def probe_video(path: str) -> dict[str, Any]:
    """Probe video format and stream properties using ffprobe CLI.

    Returns dict with keys:
        - duration_sec: float | None
        - width: int | None
        - height: int | None
        - size_bytes: int | None
        - codec: str | None
        - fps: float | None
        - container: str | None
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,size,format_name",
        "-show_entries",
        "stream=width,height,avg_frame_rate,codec_name",
        "-of",
        "json",
        path,
    ]
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
    except FileNotFoundError as exc:
        raise ImageReadError(
            "ffmpeg/ffprobe not found in PATH; video processing requires ffmpeg and ffprobe."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ImageReadError(
            f"ffprobe timed out probing video {os.path.basename(path)}"
        ) from exc
    except Exception as exc:
        raise ImageReadError(f"Cannot probe video {os.path.basename(path)}: {exc}") from exc

    if res.returncode != 0:
        err_msg = (res.stderr or "").strip()[:300]
        raise ImageReadError(f"Cannot probe video {os.path.basename(path)}: {err_msg}")

    try:
        data = json.loads(res.stdout)
    except Exception as exc:
        raise ImageReadError(
            f"Cannot probe video {os.path.basename(path)}: invalid json ({exc})"
        ) from exc

    fmt = data.get("format", {})
    streams = data.get("streams", [])

    duration_sec: float | None = None
    duration_val = fmt.get("duration")
    if duration_val is not None:
        try:
            duration_sec = float(duration_val)
        except (ValueError, TypeError):
            duration_sec = None

    size_bytes: int | None = None
    size_val = fmt.get("size")
    if size_val is not None:
        try:
            size_bytes = int(size_val)
        except (ValueError, TypeError):
            size_bytes = None

    width: int | None = None
    height: int | None = None
    for s in streams:
        if "width" in s and "height" in s:
            width = s.get("width")
            height = s.get("height")
            break

    codec = None
    fps = None
    container = fmt.get("format_name")
    for s in streams:
        if "codec_name" in s:
            codec = s.get("codec_name")
            break
    for s in streams:
        rate = s.get("avg_frame_rate")
        if isinstance(rate, str) and "/" in rate:
            try:
                num, den = rate.split("/", 1)
                fps = float(num) / float(den) if float(den) else None
            except (ValueError, ZeroDivisionError):
                fps = None
            break

    return {
        "duration_sec": duration_sec,
        "width": width,
        "height": height,
        "size_bytes": size_bytes,
        "codec": codec,
        "fps": fps,
        "container": container,
    }


def extract_frames(
    path: str,
    count: int = 6,
    max_edge: int = 1024,
    max_duration_sec: int = 30,
) -> tuple[list[Image.Image], int]:
    """Extract uniform temporal frames from video using ffmpeg.

    Timestamps are computed uniformly as t_i = duration * (i + 0.5) / count.
    If duration is unknown (None), fallback assumes a nominal 10.0s clip
    with timestamps (10.0 * (i + 0.5) / count).

    Returns (frames, attempted) where caller is responsible for closing frames.
    """
    probe = probe_video(path)
    duration = probe.get("duration_sec")
    if duration is not None and duration > max_duration_sec:
        raise ImageReadError(
            f"Video too long ({duration:.1f}s > {max_duration_sec}s): {os.path.basename(path)}"
        )

    effective_duration = duration if (duration is not None and duration > 0) else 10.0
    timestamps = [
        f"{(effective_duration * (i + 0.5) / count):.2f}" for i in range(count)
    ]

    temp_dir = tempfile.mkdtemp(prefix="microstock_vid_")
    frames: list[Image.Image] = []
    attempted = 0
    try:
        for idx, ts in enumerate(timestamps):
            attempted += 1
            frame_filename = f"f_{idx:02d}.jpg"
            out_frame_path = os.path.join(temp_dir, frame_filename)
            cmd = [
                "ffmpeg",
                "-y",
                "-loglevel",
                "warning",
                "-ss",
                ts,
                "-i",
                path,
                "-frames:v",
                "1",
                "-update",
                "1",
                "-q:v",
                "2",
                out_frame_path,
            ]
            try:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60,
                )
            except FileNotFoundError as exc:
                raise ImageReadError(
                    "ffmpeg/ffprobe not found in PATH; video processing requires ffmpeg."
                ) from exc
            except subprocess.TimeoutExpired as exc:
                raise ImageReadError(
                    f"ffmpeg timed out extracting frame {idx} from {os.path.basename(path)}"
                ) from exc

            if res.returncode != 0 or not os.path.isfile(out_frame_path):
                continue

            try:
                with open(out_frame_path, "rb") as fh:
                    raw_bytes = fh.read()
                buf = io.BytesIO(raw_bytes)
                with Image.open(buf) as raw_img:
                    raw_img.load()
                    transposed = ImageOps.exif_transpose(raw_img)
                    if transposed.mode != "RGB":
                        transposed = transposed.convert("RGB")
                    orig_w, orig_h = transposed.size
                    longest = max(orig_w, orig_h)
                    if longest > max_edge:
                        scale = max_edge / longest
                        new_size = (
                            max(1, int(orig_w * scale)),
                            max(1, int(orig_h * scale)),
                        )
                        proc_img = transposed.resize(new_size, Image.LANCZOS)
                    else:
                        proc_img = transposed.copy()
                    frames.append(proc_img)
            except Exception:
                continue

        if not frames:
            raise ImageReadError(
                f"Failed to extract any frames from {os.path.basename(path)}"
            )

        return frames, attempted
    except Exception:
        for f in frames:
            try:
                f.close()
            except Exception:
                pass
        raise
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


VIDEO_MIN_WIDTH = 1280
VIDEO_MIN_HEIGHT = 720
VIDEO_MIN_DURATION_SEC = 5.0
VIDEO_ALLOWED_CODECS = ("h264", "hevc", "prores", "mjpeg", "png")


def assess_video(info: dict) -> list[str]:
    """Return list of soft-gate reason codes; empty = pass. Pure, no I/O."""
    reasons = []
    w, h = info.get("width"), info.get("height")
    if isinstance(w, int) and isinstance(h, int) and (w < VIDEO_MIN_WIDTH or h < VIDEO_MIN_HEIGHT):
        reasons.append("below_hd_min")
    dur = info.get("duration_sec")
    if isinstance(dur, (int, float)) and dur < VIDEO_MIN_DURATION_SEC:
        reasons.append("too_short")
    codec = info.get("codec") or ""
    if isinstance(codec, str) and codec and codec.lower() not in VIDEO_ALLOWED_CODECS:
        reasons.append("uncommon_codec")
    fps = info.get("fps")
    if isinstance(fps, (int, float)) and (fps < 20 or fps > 70):
        reasons.append("unusual_fps")
    return reasons

