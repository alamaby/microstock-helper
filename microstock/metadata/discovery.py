"""File discovery: single image/video or directory, case-insensitive extensions."""

from __future__ import annotations

import os

from .constants import SUPPORTED_EXTENSIONS, SUPPORTED_VIDEO_EXTENSIONS
from .exceptions import ConfigurationError, UnsupportedImageError


def _normalize_extensions(
    extensions: list[str] | None, default_exts: tuple[str, ...]
) -> tuple[str, ...]:
    if not extensions:
        return default_exts
    cleaned = []
    for ext in extensions:
        ext = ext.strip().lower()
        if not ext.startswith("."):
            ext = "." + ext
        cleaned.append(ext)
    return tuple(cleaned)


def discover_inputs(
    input_path: str,
    recursive: bool = True,
    extensions: list[str] | None = None,
    limit: int | None = None,
    media_type: str = "auto",
) -> list[dict]:
    """Return sorted discovery records: {path, relative_path, filename, media}."""
    if media_type not in ("auto", "image", "video"):
        raise ConfigurationError(
            f"Invalid media_type: {media_type!r}. Must be 'auto', 'image', or 'video'."
        )

    if media_type == "image":
        default_exts = SUPPORTED_EXTENSIONS
    elif media_type == "video":
        default_exts = SUPPORTED_VIDEO_EXTENSIONS
    else:
        default_exts = SUPPORTED_EXTENSIONS + SUPPORTED_VIDEO_EXTENSIONS

    if extensions:
        normalized = _normalize_extensions(extensions, default_exts)
        if media_type == "image":
            allowed = tuple(e for e in normalized if e not in SUPPORTED_VIDEO_EXTENSIONS)
        elif media_type == "video":
            allowed = tuple(e for e in normalized if e in SUPPORTED_VIDEO_EXTENSIONS)
        else:
            allowed = normalized
    else:
        allowed = default_exts

    found: list[dict] = []
    if os.path.isfile(input_path):
        if os.path.splitext(input_path)[1].lower() not in allowed:
            raise UnsupportedImageError(f"Unsupported input extension: {input_path}")
        base = os.path.dirname(os.path.abspath(input_path))
        found.append(_record(input_path, base))
        return found
    if not os.path.isdir(input_path):
        raise ConfigurationError(f"Input path does not exist: {input_path}")
    base = os.path.abspath(input_path)
    if recursive:
        for root, dirs, files in os.walk(base):
            dirs[:] = [
                d for d in dirs
                if d.lower() not in (
                    "_stock", "output-api", "for_adobe", "for_dreamstime",
                    "for_vecteezy", "for_pixabay", "output"
                )
            ]
            for name in sorted(files):
                full = os.path.join(root, name)
                if os.path.splitext(name)[1].lower() in allowed:
                    found.append(_record(full, base))
    else:
        for name in sorted(os.listdir(base)):
            full = os.path.join(base, name)
            if os.path.isfile(full) and os.path.splitext(name)[1].lower() in allowed:
                found.append(_record(full, base))
    found.sort(key=lambda r: r["relative_path"].lower())
    if limit is not None:
        found = found[:limit]
    return found


def discover_images(
    input_path: str,
    recursive: bool = True,
    extensions: list[str] | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Return sorted discovery records: {path, relative_path, filename}."""
    return discover_inputs(
        input_path,
        recursive=recursive,
        extensions=extensions,
        limit=limit,
        media_type="image",
    )


def _record(path: str, base: str) -> dict:
    abs_path = os.path.abspath(path)
    ext = os.path.splitext(abs_path)[1].lower()
    media = "video" if ext in SUPPORTED_VIDEO_EXTENSIONS else "image"
    return {
        "path": abs_path,
        "relative_path": os.path.relpath(abs_path, base),
        "filename": os.path.basename(abs_path),
        "media": media,
    }
