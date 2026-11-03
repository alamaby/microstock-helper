"""Sequential file renumbering based on file creation/modification timestamps."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Tuple

MEDIA_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff",
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm",
    ".svg", ".eps",
)


def extract_3digit_number(filename: str) -> str | None:
    """Extract a 3-digit number from filename (e.g. 007 or __007-)."""
    # Prefer pattern ^NNN_ or ^NNN. or __NNN-
    match = re.search(r"(?:^|__|_|-)(\d{3})(?:_|-|\.|$)", filename)
    if match:
        return match.group(1)
    return None


def renumber_directory(
    directory: str,
    allowed_exts: Tuple[str, ...] = MEDIA_EXTENSIONS,
    dry_run: bool = False,
) -> List[Tuple[str, str]]:
    """Renumber media files in directory chronologically (001_..., 002_...).

    Files that already follow the 001_ prefix scheme are left untouched
    unless duplicate indices are detected.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Directory not found: {directory}")

    files = [
        f for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in allowed_exts
    ]

    if not files:
        return []

    # Check if files already properly numbered
    all_numbered = all(re.match(r"^\d{3}_", f.name) for f in files)
    if all_numbered:
        prefixes = [f.name[:3] for f in files]
        if len(prefixes) == len(set(prefixes)):
            # Perfectly numbered without duplicates
            return [(str(f), str(f)) for f in sorted(files, key=lambda x: x.name)]

    # Sort files by creation time, then modification time, then name
    def file_sort_key(p: Path) -> Tuple[float, float, str]:
        stat = p.stat()
        ctime = getattr(stat, "st_ctime", stat.st_mtime)
        return (ctime, stat.st_mtime, p.name.lower())

    sorted_files = sorted(files, key=file_sort_key)
    renamed: List[Tuple[str, str]] = []

    # Generate target names
    plan: List[Tuple[Path, Path]] = []
    for idx, old_path in enumerate(sorted_files, 1):
        num_str = f"{idx:03d}"
        clean_name = re.sub(r"^\d{3}_", "", old_path.name)
        new_name = f"{num_str}_{clean_name}"
        new_path = old_path.parent / new_name
        plan.append((old_path, new_path))
        renamed.append((str(old_path), str(new_path)))

    if dry_run:
        return renamed

    # Two-phase rename via .renametmp to prevent collisions
    temp_stage: List[Tuple[Path, Path]] = []
    for old_path, new_path in plan:
        if old_path == new_path:
            continue
        tmp_path = old_path.parent / f"{old_path.name}.{os.getpid()}.renametmp"
        old_path.rename(tmp_path)
        temp_stage.append((tmp_path, new_path))

    for tmp_path, new_path in temp_stage:
        if new_path.exists():
            new_path.unlink()
        tmp_path.rename(new_path)

    return renamed
