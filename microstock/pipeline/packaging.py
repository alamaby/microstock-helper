"""Packaging, directory segregation, filename sanitization, and upload readiness verification."""

from __future__ import annotations

import csv
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def sanitize_vecteezy_filename(name: str) -> str:
    """Sanitize filename for Vecteezy FTP rules (no spaces or unusual symbols)."""
    stem = Path(name).stem
    ext = Path(name).suffix.lower()
    # Replace spaces and punctuation with underscores
    clean = re.sub(r"[^a-zA-Z0-9_\-]", "_", stem)
    clean = re.sub(r"_+", "_", clean).strip("_")
    return f"{clean}{ext}"


def package_agency_directory(
    agency: str,
    target_kind: str,  # 'JPG' | 'SVG' | 'EPS'
    out_base_dir: str,
    source_files: List[str],  # Final image or vector files
    preview_files: Optional[List[str]] = None,  # For vector mode (.jpg previews)
    csv_path: Optional[str] = None,
    overwrite: bool = True,
) -> Tuple[str, int]:
    """Package files into kind-pure agency upload folders.

    Returns (target_directory, file_count).
    """
    agency_lower = agency.lower()
    if target_kind.upper() == "JPG":
        if agency_lower == "vecteezy":
            folder_name = "for_vecteezy_photo"
        elif agency_lower == "pixabay":
            folder_name = "for_pixabay_photo"
        else:
            folder_name = f"for_{agency_lower}"
    else:
        vec_ext = target_kind.lower()
        if agency_lower == "vecteezy":
            folder_name = f"for_vecteezy_{vec_ext}"
        elif agency_lower == "pixabay":
            folder_name = f"for_pixabay_{vec_ext}"
        else:
            folder_name = f"for_{agency_lower}_{vec_ext}"

    target_dir = os.path.join(out_base_dir, folder_name)
    os.makedirs(target_dir, exist_ok=True)

    copied_count = 0
    is_vecteezy = agency_lower == "vecteezy"

    # Map of old_stem -> new_stem for CSV rewriting if vecteezy
    rename_map: Dict[str, str] = {}

    for src in source_files:
        src_path = Path(src)
        dest_name = sanitize_vecteezy_filename(src_path.name) if is_vecteezy else src_path.name
        rename_map[src_path.stem] = Path(dest_name).stem
        dest_file = os.path.join(target_dir, dest_name)
        if overwrite or not os.path.isfile(dest_file):
            shutil.copy2(src, dest_file)
            copied_count += 1

    if preview_files and target_kind.upper() in ("SVG", "EPS"):
        for prev in preview_files:
            prev_path = Path(prev)
            dest_name = (
                f"{rename_map.get(prev_path.stem, prev_path.stem)}.jpg"
                if is_vecteezy
                else prev_path.name
            )
            dest_file = os.path.join(target_dir, dest_name)
            if overwrite or not os.path.isfile(dest_file):
                shutil.copy2(prev, dest_file)

    # Copy and optionally rewrite CSV for the agency
    if csv_path and os.path.isfile(csv_path):
        dest_csv = os.path.join(target_dir, Path(csv_path).name)
        if is_vecteezy:
            _write_sanitized_vecteezy_csv(csv_path, dest_csv, rename_map)
        else:
            shutil.copy2(csv_path, dest_csv)

    return target_dir, copied_count


def _write_sanitized_vecteezy_csv(src_csv: str, dest_csv: str, rename_map: Dict[str, str]) -> None:
    """Rewrite Vecteezy CSV with extensionless sanitized filenames and license=free."""
    rows = []
    with open(src_csv, "r", encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        for row in reader:
            filename = row.get("Filename") or row.get("SourceFile") or ""
            stem = Path(filename).stem
            sanitized_stem = rename_map.get(stem, re.sub(r"[^a-zA-Z0-9_\-]", "_", stem))
            # Vecteezy requires Filename without extension
            if "Filename" in row:
                row["Filename"] = sanitized_stem
            elif "SourceFile" in row:
                row["SourceFile"] = sanitized_stem
            if "License" in row:
                row["License"] = "free"
            rows.append(row)

    with open(dest_csv, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def verify_upload_readiness(
    packaged_dir: str,
    platform: str,
) -> List[str]:
    """Check portal specific limits (warn-only check)."""
    warnings: List[str] = []
    p_lower = platform.lower()
    files = [f for f in os.listdir(packaged_dir) if os.path.isfile(os.path.join(packaged_dir, f))]
    csv_files = [f for f in files if f.endswith(".csv")]
    if not csv_files:
        warnings.append(f"No companion CSV found in {packaged_dir}")
        return warnings

    csv_path = os.path.join(packaged_dir, csv_files[0])
    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader, 1):
            title = row.get("Title") or ""
            keywords_str = row.get("Keywords") or ""
            kws = [k.strip() for k in keywords_str.split(",") if k.strip()]

            if p_lower == "adobe":
                if len(title) > 70:
                    warnings.append(f"Row {idx} ({row.get('Filename')}): Title {len(title)}ch > 70ch")
                if len(kws) > 49:
                    warnings.append(f"Row {idx}: {len(kws)} keywords > 49 max")
            elif p_lower == "dreamstime":
                if len(title) > 200:
                    warnings.append(f"Row {idx}: Title {len(title)}ch > 200ch")
                if len(kws) > 80:
                    warnings.append(f"Row {idx}: {len(kws)} keywords > 80 max single words")
            elif p_lower == "vecteezy":
                if len(title) > 70:
                    warnings.append(f"Row {idx}: Title {len(title)}ch > 70ch")
                if not (5 <= len(kws) <= 50):
                    warnings.append(f"Row {idx}: {len(kws)} keywords not between 5-50")
            elif p_lower == "pixabay":
                if len(title) > 100:
                    warnings.append(f"Row {idx}: Title {len(title)}ch > 100ch")
                if not (5 <= len(kws) <= 25):
                    warnings.append(f"Row {idx}: {len(kws)} keywords not between 5-25")

    return warnings
