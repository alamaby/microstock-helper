"""Unified command-line interface for microstock tools and pipelines."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from typing import List, Optional

from .preflight import PreflightError, get_tool_map, validate_dependencies


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="microstock",
        description="Unified Microstock Automation CLI (Processing, Vectorization, Metadata, & Orchestration)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # 1. run (Orchestrate full pipeline)
    run_parser = sub.add_parser("run", help="Run full end-to-end stock pipeline (JPG/SVG/EPS)")
    run_parser.add_argument("source_dir", help="Directory containing source media files")
    run_parser.add_argument("--target", choices=["JPG", "SVG", "EPS"], default="JPG",
                            help="Processing pipeline target (default: JPG)")
    run_parser.add_argument("--platforms", default="Adobe,Dreamstime,Vecteezy,Pixabay",
                            help="Comma-separated target platforms (default: Adobe,Dreamstime,Vecteezy,Pixabay)")
    run_parser.add_argument("--scale", type=int, default=5, choices=[2, 3, 4, 5],
                            help="Upscale factor for JPG pipeline (default: 5)")
    run_parser.add_argument("--preview-width", type=int, default=6000,
                            help="Width for vector JPG preview render (default: 6000)")
    run_parser.add_argument("--copyright", default="alamaby", help="Copyright notice string")
    run_parser.add_argument("--creator", default="alamaby", help="Creator/Artist string")
    run_parser.add_argument("--force", action="store_true", help="Force rebuild upstream stages")

    # 2. batch (Process-Batch: Generate -> Convert CSV -> Embed)
    batch_parser = sub.add_parser("batch", help="Run 3-step batch: generate metadata -> convert CSV -> embed")
    batch_parser.add_argument("batch_dir", help="Directory containing media files")
    batch_parser.add_argument("--agencies", choices=["both", "adobe", "dreamstime"], default="both",
                              help="Agencies to embed for (default: both)")
    batch_parser.add_argument("--limit", type=int, default=None, help="Limit number of items to process")
    batch_parser.add_argument("--dry-run", action="store_true", help="Test without writing final files")
    batch_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")

    # 3. convert (Raster conversions via Pillow)
    conv_parser = sub.add_parser("convert", help="Convert images (PNG/WEBP/BMP) to JPG via Pillow")
    conv_parser.add_argument("src_dir", help="Source directory containing images")
    conv_parser.add_argument("--out", required=True, help="Destination directory for JPGs")
    conv_parser.add_argument("--quality", type=int, default=95, help="JPEG quality 1-100 (default: 95)")
    conv_parser.add_argument("--max-edge", type=int, default=None, help="Max edge size for downsampling")
    conv_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")

    # 4. renumber (Chronological file renumbering)
    renum_parser = sub.add_parser("renumber", help="Renumber media files chronologically (001_...)")
    renum_parser.add_argument("directory", help="Directory containing files to rename")
    renum_parser.add_argument("--dry-run", action="store_true", help="Print plan without renaming")

    # 5. upscale (Upscayl CLI)
    ups_parser = sub.add_parser("upscale", help="Upscale raster images using Upscayl CLI")
    ups_parser.add_argument("input_dir", help="Directory containing images to upscale")
    ups_parser.add_argument("--out", required=True, help="Destination directory for upscaled images")
    ups_parser.add_argument("--scale", type=int, default=5, choices=[2, 3, 4, 5], help="Upscale scale")
    ups_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing upscaled images")

    # 6. trace (vtracer CLI)
    trace_parser = sub.add_parser("trace", help="Trace raster images to SVG vectors using vtracer CLI")
    trace_parser.add_argument("input_dir", help="Directory containing JPG images")
    trace_parser.add_argument("--out", required=True, help="Destination directory for SVGs")
    trace_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing SVGs")

    # 7. vector-preview (Inkscape render)
    prev_parser = sub.add_parser("vector-preview", help="Render SVG vectors to high-res JPG previews")
    prev_parser.add_argument("svg_dir", help="Directory containing SVG files")
    prev_parser.add_argument("--out", required=True, help="Destination directory for preview JPGs")
    prev_parser.add_argument("--width", type=int, default=6000, help="Preview width in pixels")
    prev_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing previews")

    # 8. convert-eps (Inkscape SVG -> EPS)
    eps_parser = sub.add_parser("convert-eps", help="Convert SVG vectors to PostScript EPS via Inkscape")
    eps_parser.add_argument("svg_dir", help="Directory containing SVG files")
    eps_parser.add_argument("--out", required=True, help="Destination directory for EPS files")
    eps_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing EPS files")

    # 9. embed-jpg (ExifTool triple sync)
    embed_jpg_p = sub.add_parser("embed-jpg", help="Embed CSV metadata into JPG/PNG files via ExifTool")
    embed_jpg_p.add_argument("--csv", required=True, help="Path to metadata CSV file")
    embed_jpg_p.add_argument("--images", required=True, help="Directory containing image files")
    embed_jpg_p.add_argument("--out", default=None, help="Output directory (modifies in-place if omitted)")
    embed_jpg_p.add_argument("--copyright", default="alamaby", help="Copyright string")
    embed_jpg_p.add_argument("--creator", default="alamaby", help="Creator string")

    # 10. embed-vector (Vector package embed)
    embed_vec_p = sub.add_parser("embed-vector", help="Embed metadata into vector packages (SVG/EPS + preview JPG)")
    embed_vec_p.add_argument("--csv", required=True, help="Path to metadata CSV file")
    embed_vec_p.add_argument("--jpg-dir", required=True, help="Directory containing preview JPGs")
    embed_vec_p.add_argument("--vec-dir", required=True, help="Directory containing SVG or EPS files")
    embed_vec_p.add_argument("--out", required=True, help="Output directory for packaged files")
    embed_vec_p.add_argument("--vec-kind", choices=["auto", "svg", "eps"], default="auto", help="Vector format")
    embed_vec_p.add_argument("--copyright", default="alamaby", help="Copyright string")
    embed_vec_p.add_argument("--creator", default="alamaby", help="Creator string")

    # 11. doctor (Health check)
    sub.add_parser("doctor", help="Check system readiness, CLI dependencies, and API keys")

    # 12. generate (Pass through to metadata generator)
    gen_parser = sub.add_parser("generate", help="Generate AI metadata for images/videos")
    gen_parser.add_argument("input", help="Image/video file or directory")
    gen_parser.add_argument("--output-dir", required=True, help="Directory to save metadata")
    gen_parser.add_argument("--backend", default="api", choices=["api"], help="Backend inference path")
    gen_parser.add_argument("--limit", type=int, default=None, help="Limit number of items")
    gen_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing items")

    return parser


def cmd_doctor() -> int:
    """Run full diagnostic check of all required external CLI tools and environment."""
    import importlib.util
    from .metadata.api_inference import ensure_dotenv_loaded
    import os

    ensure_dotenv_loaded()
    print("=" * 60)
    print("  MICROSTOCK SYSTEM DIAGNOSTIC (DOCTOR)")
    print("=" * 60)

    # 1. Python environment
    print(f"  Python                   : OK {sys.version.split()[0]} (>= 3.10)")
    for pkg in ("PIL", "pydantic", "yaml"):
        present = importlib.util.find_spec(pkg) is not None
        status = "OK" if present else "MISSING"
        print(f"  Package {pkg:<17}: {status}")

    # 2. External CLI Tools
    tools = get_tool_map()
    print("\n  [External CLI Tools]")
    for tool_name, resolved_path in tools.items():
        if resolved_path and os.path.isfile(resolved_path):
            print(f"  {tool_name:<25}: OK  {resolved_path}")
        else:
            print(f"  {tool_name:<25}: !! MISSING")

    # 3. API Keys
    print("\n  [API Key Configuration]")
    primary_key = os.environ.get("MICROSTOCK_API_KEY", "").strip()
    cf_token = os.environ.get("MICROSTOCK_CF_API_TOKEN", "").strip()
    cf_acc = os.environ.get("MICROSTOCK_CF_ACCOUNT_ID", "").strip()

    print(f"  Local Gateway (Primary)  : {'OK configured' if primary_key else '!! NOT SET (MICROSTOCK_API_KEY)'}")
    print(f"  Cloudflare AI (Fallback) : {'OK configured' if (cf_token and cf_acc) else '!! INCOMPLETE (MICROSTOCK_CF_API_TOKEN / ACCOUNT_ID)'}")
    print("=" * 60)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        # Preflight startup check based on active command
        if args.command == "run":
            req_tools = ["exiftool"]
            if args.target.upper() == "JPG":
                req_tools.append("upscayl")
            else:
                req_tools.extend(["vtracer", "inkscape"])
            validate_dependencies(req_tools, require_api_key=True)

            from .pipeline.orchestrator import orchestrate_directory
            platform_list = [p.strip() for p in args.platforms.split(",") if p.strip()]
            return orchestrate_directory(
                source_dir=args.source_dir,
                target=args.target,
                platforms=platform_list,
                scale=args.scale,
                preview_width=args.preview_width,
                copyright=args.copyright,
                creator=args.creator,
                force=args.force,
            )

        elif args.command == "batch":
            validate_dependencies(["exiftool"], require_api_key=True)
            from .pipeline.batch import run_batch
            agencies = ["adobe", "dreamstime"] if args.agencies == "both" else [args.agencies]
            return run_batch(
                batch_dir=args.batch_dir,
                agencies=agencies,
                limit=args.limit,
                dry_run=args.dry_run,
                overwrite=args.overwrite,
            )

        elif args.command == "convert":
            from .core.image_ops import batch_convert_to_jpg
            converted = batch_convert_to_jpg(
                args.src_dir,
                args.out,
                quality=args.quality,
                max_edge=args.max_edge,
                overwrite=args.overwrite,
            )
            print(f"Successfully converted {len(converted)} files to JPEG in {args.out}")
            return 0

        elif args.command == "renumber":
            from .core.renumber import renumber_directory
            renamed = renumber_directory(args.directory, dry_run=args.dry_run)
            action = "Would rename" if args.dry_run else "Renamed"
            print(f"{action} {len(renamed)} files in {args.directory}")
            return 0

        elif args.command == "upscale":
            validate_dependencies(["upscayl"])
            from .core.upscaler import batch_upscale
            upscaled = batch_upscale(
                args.input_dir,
                args.out,
                scale=args.scale,
                overwrite=args.overwrite,
            )
            print(f"Successfully upscaled {len(upscaled)} files to {args.out}")
            return 0

        elif args.command == "trace":
            validate_dependencies(["vtracer"])
            from .core.tracer import batch_trace
            traced = batch_trace(
                args.input_dir,
                args.out,
                overwrite=args.overwrite,
            )
            print(f"Successfully traced {len(traced)} SVGs to {args.out}")
            return 0

        elif args.command == "vector-preview":
            validate_dependencies(["inkscape"])
            from .core.vector_ops import batch_render_previews
            rendered = batch_render_previews(
                args.svg_dir,
                args.out,
                width=args.width,
                overwrite=args.overwrite,
            )
            print(f"Successfully rendered {len(rendered)} preview JPGs to {args.out}")
            return 0

        elif args.command == "convert-eps":
            validate_dependencies(["inkscape"])
            from .core.vector_ops import batch_convert_eps
            converted = batch_convert_eps(
                args.svg_dir,
                args.out,
                overwrite=args.overwrite,
            )
            print(f"Successfully converted {len(converted)} EPS files to {args.out}")
            return 0

        elif args.command == "embed-jpg":
            validate_dependencies(["exiftool"])
            from .core.metadata_embed import embed_jpg_file, find_matching_file, read_metadata_csv
            import shutil

            rows = read_metadata_csv(args.csv)
            images = [os.path.join(args.images, f) for f in os.listdir(args.images)]
            out_dir = args.out or args.images
            os.makedirs(out_dir, exist_ok=True)

            count = 0
            for row in rows:
                name = row.get("Filename") or row.get("SourceFile") or ""
                hit = find_matching_file(images, name, (".jpg", ".jpeg", ".png"))
                if not hit:
                    continue
                dest = os.path.join(out_dir, os.path.basename(hit))
                if out_dir != args.images:
                    shutil.copy2(hit, dest)
                kws = [k.strip() for k in row.get("Keywords", "").split(",") if k.strip()]
                if embed_jpg_file(dest, row.get("Title", ""), row.get("Description", ""), kws, args.copyright, args.creator):
                    count += 1
            print(f"Embedded metadata into {count} image files in {out_dir}")
            return 0

        elif args.command == "embed-vector":
            validate_dependencies(["exiftool"])
            from .core.metadata_embed import embed_eps_file, embed_jpg_file, embed_svg_file, find_matching_file, read_metadata_csv
            import shutil

            rows = read_metadata_csv(args.csv)
            jpgs = [os.path.join(args.jpg_dir, f) for f in os.listdir(args.jpg_dir)]
            vecs = [os.path.join(args.vec_dir, f) for f in os.listdir(args.vec_dir)]
            os.makedirs(args.out, exist_ok=True)

            count = 0
            for row in rows:
                name = row.get("Filename") or row.get("SourceFile") or ""
                hit_jpg = find_matching_file(jpgs, name, (".jpg", ".jpeg"))
                hit_vec = find_matching_file(vecs, name, (".svg", ".eps"))
                if not (hit_jpg and hit_vec):
                    continue
                dest_jpg = os.path.join(args.out, os.path.basename(hit_jpg))
                dest_vec = os.path.join(args.out, os.path.basename(hit_vec))
                shutil.copy2(hit_jpg, dest_jpg)
                shutil.copy2(hit_vec, dest_vec)

                kws = [k.strip() for k in row.get("Keywords", "").split(",") if k.strip()]
                embed_jpg_file(dest_jpg, row.get("Title", ""), row.get("Description", ""), kws, args.copyright, args.creator)
                if dest_vec.lower().endswith(".eps"):
                    embed_eps_file(dest_vec, row.get("Title", ""), row.get("Description", ""), kws, args.copyright, args.creator)
                else:
                    embed_svg_file(dest_vec, row.get("Title", ""), row.get("Description", ""), kws, args.copyright, args.creator)
                count += 1
            print(f"Packaged and embedded {count} vector pairs to {args.out}")
            return 0

        elif args.command == "doctor":
            return cmd_doctor()

        elif args.command == "generate":
            from .metadata.cli import main as meta_main
            raw_args = ["generate", args.input, "--output-dir", args.output_dir, "--backend", args.backend]
            if args.limit:
                raw_args.extend(["--limit", str(args.limit)])
            if args.overwrite:
                raw_args.append("--overwrite")
            return meta_main(raw_args)

    except PreflightError as exc:
        print(f"\n[STARTUP ERROR] Preflight dependency check failed:\n{exc}\n", file=sys.stderr)
        print("Tip: Jalankan 'microstock doctor' untuk memeriksa instalasi seluruh tool.", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"\n[ERROR] Command failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
