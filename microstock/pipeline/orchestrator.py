"""Full microstock orchestrator: end-to-end pipeline for JPG, SVG, and EPS workflows."""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

from ..core.image_ops import batch_convert_to_jpg, convert_image_to_jpeg
from ..core.metadata_embed import embed_eps_file, embed_jpg_file, embed_svg_file, find_matching_file, read_metadata_csv
from ..core.renumber import renumber_directory
from ..core.tracer import batch_trace
from ..core.upscaler import batch_upscale
from ..core.vector_ops import batch_convert_eps, batch_render_previews
from ..metadata.csv_embed import convert_to_all_platforms
from ..preflight import validate_dependencies
from .packaging import package_agency_directory, verify_upload_readiness
from .reporter import ConsoleReporter


def orchestrate_directory(
    source_dir: str,
    target: str = "JPG",  # JPG | SVG | EPS
    platforms: Optional[List[str]] = None,
    scale: int = 5,
    preview_width: int = 6000,
    copyright: str = "alamaby",
    creator: str = "alamaby",
    force: bool = False,
    reporter: Optional[ConsoleReporter] = None,
) -> int:
    """Execute end-to-end processing pipeline for a batch folder."""
    rep = reporter or ConsoleReporter()
    start_time = time.time()
    stages_log: List[Dict[str, str]] = []
    target = target.upper()
    platforms = [p.capitalize() for p in (platforms or ["Adobe", "Dreamstime", "Vecteezy", "Pixabay"])]

    src_path = Path(source_dir).resolve()
    if not src_path.is_dir():
        rep.warn(f"Source directory not found: {source_dir}")
        return 2

    # Stage 0: Preflight
    rep.stage(0, "Preflight Dependencies")
    required = ["exiftool"]
    if target == "JPG":
        required.append("upscayl")
    else:
        required.extend(["vtracer", "inkscape"])

    try:
        tools = validate_dependencies(required, require_api_key=True)
        rep.info(f"Semua alat terverifikasi: {', '.join(tools.keys())}")
        stages_log.append({"no": "0", "tahap": "Preflight", "status": "OK", "detail": f"Target={target}"})
    except Exception as exc:
        rep.warn(f"Preflight gagal: {exc}")
        stages_log.append({"no": "0", "tahap": "Preflight", "status": "FAIL", "detail": str(exc)})
        return 2

    # Internal directory layout
    stock_dir = src_path / "_stock"
    jpg_small_dir = stock_dir / "02_jpg_small"
    upscaled_dir = stock_dir / "03_upscaled"
    final_jpg_dir = stock_dir / "04_final_jpg"
    svg_dir = stock_dir / "05_svg"
    preview_jpg_dir = stock_dir / "06_preview_jpg"
    eps_dir = stock_dir / "07_eps"
    meta_dir = stock_dir / "metadata"

    stock_dir.mkdir(parents=True, exist_ok=True)
    jpg_small_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: Rename chronologically
    rep.stage(1, "Penomoran Urut (001_...)")
    try:
        renamed = renumber_directory(str(src_path), dry_run=False)
        rep.info(f"Memproses {len(renamed)} berkas dengan skema penomoran urut.")
        stages_log.append({"no": "1", "tahap": "Rename", "status": "OK", "detail": f"{len(renamed)} berkas"})
    except Exception as exc:
        rep.warn(f"Tahap rename gagal: {exc}")
        stages_log.append({"no": "1", "tahap": "Rename", "status": "FAIL", "detail": str(exc)})
        return 1

    # Stage 2: Convert non-JPG to small JPGs for downsample / inference
    rep.stage(2, "Downsample ke JPG Kecil")
    try:
        batch_convert_to_jpg(
            str(src_path),
            str(jpg_small_dir),
            quality=90,
            max_edge=1536,
            overwrite=force,
        )
        small_jpgs = [str(f) for f in jpg_small_dir.iterdir() if f.suffix.lower() == ".jpg"]
        rep.info(f"{len(small_jpgs)} file JPG kecil siap di {jpg_small_dir}")
        stages_log.append({"no": "2", "tahap": "Convert Small", "status": "OK", "detail": f"{len(small_jpgs)} items"})
    except Exception as exc:
        rep.warn(f"Tahap downsample gagal: {exc}")
        stages_log.append({"no": "2", "tahap": "Convert Small", "status": "FAIL", "detail": str(exc)})
        return 1

    # Stage 3: Metadata generation via Vision API
    rep.stage(3, "Inference Metadata AI")
    master_csv = meta_dir / "metadata.csv"
    from ..metadata.cli import main as meta_main

    args = ["generate", str(jpg_small_dir), "--output-dir", str(meta_dir), "--backend", "api"]
    if force:
        args.append("--overwrite")

    code = meta_main(args)
    if code not in (0, 1) or not master_csv.is_file():
        rep.warn("Generasi metadata AI gagal.")
        stages_log.append({"no": "3", "tahap": "Metadata AI", "status": "FAIL", "detail": f"Code={code}"})
        return 1

    convert_to_all_platforms(str(master_csv), str(meta_dir))
    stages_log.append({"no": "3", "tahap": "Metadata AI", "status": "OK", "detail": "4 template CSV siap"})

    # Stage 4: Processing based on target (Upscale vs Trace/Vector)
    final_files: List[str] = []
    preview_files: List[str] = []

    if target == "JPG":
        rep.stage(4, f"Upscale AI ({scale}x via Upscayl)")
        upscaled_dir.mkdir(parents=True, exist_ok=True)
        final_jpg_dir.mkdir(parents=True, exist_ok=True)

        batch_upscale(
            str(jpg_small_dir),
            str(upscaled_dir),
            scale=scale,
            overwrite=force,
            progress_cb=rep.progress,
        )
        rep.finish_progress()

        # Convert upscaled PNGs into final JPGs
        rep.info("Mengonversi PNG hasil upscale ke JPG final kualitas maksimum...")
        batch_convert_to_jpg(
            str(upscaled_dir),
            str(final_jpg_dir),
            quality=95,
            overwrite=force,
        )
        final_files = [str(f) for f in final_jpg_dir.iterdir() if f.suffix.lower() == ".jpg"]
        stages_log.append({"no": "4", "tahap": "Upscale JPG", "status": "OK", "detail": f"{len(final_files)} final JPG"})

    else:  # SVG or EPS
        rep.stage(4, "Tracing Vektor & Render Preview")
        svg_dir.mkdir(parents=True, exist_ok=True)
        preview_jpg_dir.mkdir(parents=True, exist_ok=True)

        batch_trace(
            str(jpg_small_dir),
            str(svg_dir),
            overwrite=force,
            progress_cb=rep.progress,
        )
        rep.finish_progress()

        batch_render_previews(
            str(svg_dir),
            str(preview_jpg_dir),
            width=preview_width,
            overwrite=force,
            progress_cb=rep.progress,
        )
        rep.finish_progress()
        preview_files = [str(f) for f in preview_jpg_dir.iterdir() if f.suffix.lower() == ".jpg"]

        if target == "EPS":
            eps_dir.mkdir(parents=True, exist_ok=True)
            batch_convert_eps(
                str(svg_dir),
                str(eps_dir),
                overwrite=force,
                progress_cb=rep.progress,
            )
            rep.finish_progress()
            final_files = [str(f) for f in eps_dir.iterdir() if f.suffix.lower() == ".eps"]
            stages_log.append({"no": "4", "tahap": "Trace+EPS", "status": "OK", "detail": f"{len(final_files)} EPS"})
        else:
            final_files = [str(f) for f in svg_dir.iterdir() if f.suffix.lower() == ".svg"]
            stages_log.append({"no": "4", "tahap": "Trace SVG", "status": "OK", "detail": f"{len(final_files)} SVG"})

    # Stage 5 & 6: Packaging & Embedding Metadata for Selected Platforms
    rep.stage(5, f"Embedding Metadata & Packaging Agensi ({', '.join(platforms)})")
    for platform in platforms:
        p_lower = platform.lower()
        if p_lower == "vecteezy" and target == "SVG":
            rep.warn("Vecteezy tidak mendukung format vektor SVG (butuh EPS). Platform dilewati.")
            continue

        csv_file = meta_dir / f"metadata_{p_lower}.csv"
        if not csv_file.is_file():
            rep.warn(f"CSV untuk {platform} tidak ditemukan.")
            continue

        target_dir, count = package_agency_directory(
            agency=platform,
            target_kind=target,
            out_base_dir=str(src_path),
            source_files=final_files,
            preview_files=preview_files if target != "JPG" else None,
            csv_path=str(csv_file),
            overwrite=True,
        )

        # Embed metadata to copied files in agency directory
        rep.info(f"Embedding metadata ke folder {platform} ({count} berkas)...")
        rows = read_metadata_csv(str(csv_file))
        pkg_files = [os.path.join(target_dir, f) for f in os.listdir(target_dir)]

        for row in rows:
            name = row.get("Filename") or row.get("SourceFile") or ""
            title = row.get("Title", "")
            desc = row.get("Description", "")
            kws = [k.strip() for k in row.get("Keywords", "").split(",") if k.strip()]

            if target == "JPG":
                hit = find_matching_file(pkg_files, name, (".jpg", ".jpeg"))
                if hit:
                    embed_jpg_file(hit, title, desc, kws, copyright, creator)
            elif target == "SVG":
                hit_svg = find_matching_file(pkg_files, name, (".svg",))
                if hit_svg:
                    embed_svg_file(hit_svg, title, desc, kws, copyright, creator)
                hit_jpg = find_matching_file(pkg_files, name, (".jpg", ".jpeg"))
                if hit_jpg:
                    embed_jpg_file(hit_jpg, title, desc, kws, copyright, creator)
            elif target == "EPS":
                hit_eps = find_matching_file(pkg_files, name, (".eps",))
                if hit_eps:
                    embed_eps_file(hit_eps, title, desc, kws, copyright, creator)
                hit_jpg = find_matching_file(pkg_files, name, (".jpg", ".jpeg"))
                if hit_jpg:
                    embed_jpg_file(hit_jpg, title, desc, kws, copyright, creator)

        # Upload readiness verification
        warns = verify_upload_readiness(target_dir, platform)
        if warns:
            rep.warn(f"Verifikasi {platform}: {len(warns)} catatan review.")

    stages_log.append({"no": "5", "tahap": "Embed & Package", "status": "OK", "detail": f"{len(platforms)} platform"})

    # Stage 7: Summary Report
    elapsed = time.time() - start_time
    rep.print_summary(stages_log, elapsed)
    return 0
