"""Batch runner: generate metadata -> convert CSV -> embed into images."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from ..core.metadata_embed import embed_jpg_file, find_matching_file, read_metadata_csv
from ..metadata.csv_embed import convert_to_all_platforms
from ..preflight import validate_dependencies
from .reporter import ConsoleReporter


def run_batch(
    batch_dir: str,
    agencies: List[str] = ["adobe", "dreamstime"],
    limit: Optional[int] = None,
    dry_run: bool = False,
    overwrite: bool = False,
    reporter: Optional[ConsoleReporter] = None,
) -> int:
    """Run 3-step batch process: generate metadata -> convert CSV -> embed."""
    rep = reporter or ConsoleReporter()
    batch_path = Path(batch_dir).resolve()
    if not batch_path.is_dir():
        rep.warn(f"Directory not found: {batch_dir}")
        return 2

    # Step 0: Preflight
    rep.stage(0, "PREFLIGHT")
    validate_dependencies(["exiftool"], require_api_key=True)
    rep.info("Preflight OK: ExifTool dan API keys tersedia.")

    # Step 1: Generate metadata
    rep.stage(1, "GENERATE METADATA")
    out_api = batch_path / "output-api"
    from ..metadata.cli import main as meta_main

    args = ["generate", str(batch_path), "--output-dir", str(out_api), "--backend", "api"]
    if limit and limit > 0:
        args.extend(["--limit", str(limit)])
    if overwrite:
        args.append("--overwrite")

    gen_code = meta_main(args)
    if gen_code not in (0, 1):
        rep.warn(f"Metadata generation failed (code {gen_code})")
        return gen_code

    master_csv = out_api / "metadata.csv"
    if not master_csv.is_file():
        rep.warn(f"Master metadata CSV not generated: {master_csv}")
        return 1

    # Step 2: Convert to platform CSVs
    rep.stage(2, "CONVERT TEMPLATE CSV")
    convert_to_all_platforms(str(master_csv), str(out_api))
    rep.info(f"4 template CSV dihasilkan di {out_api}")

    if dry_run:
        rep.info("Dry-run selesai (tahap embed dilewati).")
        return 0

    # Step 3: Embed metadata
    rep.stage(3, "EMBED METADATA")
    jpg_files = [
        str(f) for f in batch_path.iterdir()
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png")
    ]

    for agency in agencies:
        agency_lower = agency.lower()
        csv_file = out_api / f"metadata_{agency_lower}.csv"
        if not csv_file.is_file():
            rep.warn(f"CSV untuk agensi {agency} tidak ditemukan: {csv_file}")
            continue

        out_folder = batch_path / f"for_{agency_lower}"
        out_folder.mkdir(parents=True, exist_ok=True)
        rows = read_metadata_csv(str(csv_file))

        rep.info(f"Embedding {len(rows)} baris metadata untuk {agency} -> {out_folder}")
        for idx, row in enumerate(rows, 1):
            src_name = row.get("Filename") or row.get("SourceFile") or ""
            hit = find_matching_file(jpg_files, src_name, (".jpg", ".jpeg", ".png"))
            if not hit:
                rep.warn(f"File tidak cocok untuk {src_name}")
                continue

            dest_file = out_folder / Path(hit).name
            if not dest_file.exists() or overwrite:
                import shutil
                shutil.copy2(hit, dest_file)

            kws = [k.strip() for k in row.get("Keywords", "").split(",") if k.strip()]
            embed_jpg_file(
                str(dest_file),
                title=row.get("Title", ""),
                description=row.get("Description", ""),
                keywords=kws,
                copyright=row.get("Copyright", "alamaby"),
                creator=row.get("Creator", "alamaby"),
            )
            rep.progress(idx, len(rows), dest_file.name)
        rep.finish_progress()

    rep.info("Batch selesai sepenuhnya.")
    return 0
