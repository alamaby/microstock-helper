"""Command-line interface: generate | doctor | download-model."""

from __future__ import annotations

import argparse
import gc
import hashlib
import os
import sys
import time
from datetime import datetime, timezone

from . import console_art
from .checkpoint import CheckpointStore
from .config import AppConfig, build_config, load_yaml
from .constants import (
    API_PROMPT_VERSION,
    DEFAULT_MODEL_ID,
    EXIT_CONFIG_ERROR,
    EXIT_ITEM_FAILURE,
    EXIT_MODEL_LOAD_ERROR,
    EXIT_OK,
    EXIT_OUTPUT_ERROR,
    PROMPT_VERSION,
)
from .discovery import discover_inputs
from .exceptions import (
    CheckpointError,
    ConfigurationError,
    ExportError,
    ImageReadError,
    InferenceError,
    InvalidModelResponseError,
    MetadataValidationError,
    MicrostockError,
    ModelLoadError,
    UnsupportedImageError,
)
from .exporters import (
    utcnow,
    write_failed_json,
    write_metadata_csv,
    write_metadata_json,
)
from .image_processing import normalize_image
from .logging_config import setup_logging
from .normalization import normalize_metadata


def cleanup_memory(device: str = "") -> None:
    gc.collect()
from .parsing import extract_json
from .prompts import VIDEO_PROMPT_VERSION, build_prompt
from .schemas import ProcessingResult
from .validation import decide_review, validate_required


def _none_default(parser: argparse.ArgumentParser, *args, **kwargs) -> None:
    kwargs.setdefault("default", None)
    parser.add_argument(*args, **kwargs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="microstock-metadata")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate metadata for an image or folder")
    gen.add_argument("input", help="Image file or directory")
    _none_default(gen, "--backend",
                  help="Inference path (default api; local backend removed)")
    _none_default(gen, "--api-endpoint", help="OpenAI-compatible base URL")
    _none_default(gen, "--api-model", help="API model name")
    _none_default(gen, "--api-timeout", type=int, help="API seconds (min 5)")
    _none_default(gen, "--output-dir", help="Output directory (default ./output)")
    _none_default(gen, "--model-id", help=argparse.SUPPRESS)
    _none_default(gen, "--device", help=argparse.SUPPRESS)
    _none_default(gen, "--quantization", help=argparse.SUPPRESS)
    gen.add_argument("--offline", action="store_true", default=None, help=argparse.SUPPRESS)
    gen.add_argument("--recursive", dest="recursive", action="store_true", default=None)
    gen.add_argument("--no-recursive", dest="recursive", action="store_false")
    gen.add_argument("--resume", dest="resume", action="store_true", default=None)
    gen.add_argument("--no-resume", dest="resume", action="store_false")
    gen.add_argument("--overwrite", action="store_true", default=None)
    _none_default(gen, "--max-keywords", type=int)
    _none_default(gen, "--min-keywords", type=int)
    _none_default(gen, "--max-new-tokens", type=int)
    _none_default(gen, "--max-image-edge", type=int)
    _none_default(gen, "--max-pixels", type=int)
    _none_default(gen, "--retry-count", type=int)
    gen.add_argument("--retry-invalid-json", dest="retry_invalid_json",
                     action="store_true", default=None)
    gen.add_argument("--no-retry-invalid-json", dest="retry_invalid_json",
                     action="store_false")
    _none_default(gen, "--temperature", type=float)
    gen.add_argument("--verbose", action="store_true", default=None)
    gen.add_argument("--dry-run", action="store_true", default=False)
    _none_default(gen, "--config", help="YAML config file")
    _none_default(gen, "--limit", type=int)
    _none_default(gen, "--extensions", help="Comma-separated extensions")
    _none_default(gen, "--media-type", choices=["image", "video", "auto"],
                  help="Input filter (image, video, or auto; default auto)")
    _none_default(gen, "--frames", type=int, help="Frames to extract from video (1-12)")
    _none_default(gen, "--video-max-duration", type=int,
                  help="Max video duration in seconds (min 5)")
    _none_default(gen, "--video-max-edge", type=int,
                  help="Max edge for extracted video frames")

    doc = sub.add_parser("doctor", help="Check environment and readiness")
    _none_default(doc, "--output-dir", help="Directory to test writability")

    return parser


def _cli_to_config(args: argparse.Namespace) -> dict:
    mapping = {
        "backend": "backend",
        "api_endpoint": "api.endpoint",
        "api_model": "api.model",
        "api_timeout": "api.timeout",
        "output_dir": "output.directory",
        "model_id": "model.id",
        "device": "model.device",
        "quantization": "model.quantization",
        "offline": "model.offline",
        "max_new_tokens": "model.max_new_tokens",
        "temperature": "model.temperature",
        "max_image_edge": "image.max_edge",
        "max_pixels": "image.max_pixels",
        "max_keywords": "metadata.max_keywords",
        "min_keywords": "metadata.min_keywords",
        "recursive": "processing.recursive",
        "resume": "processing.resume",
        "retry_count": "processing.retry_count",
        "retry_invalid_json": None,  # handled separately
        "limit": "limit",
        "extensions": "extensions",
        "media_type": "media_type",
        "frames": "video.frames",
        "video_max_duration": "video.max_duration_sec",
        "video_max_edge": "video.max_edge",
        "overwrite": "overwrite",
        "verbose": "verbose",
    }
    cli: dict = {}
    for attr, key in mapping.items():
        value = getattr(args, attr, None)
        if value is None or key is None:
            continue
        if attr == "extensions" and isinstance(value, str):
            value = [e.strip() for e in value.split(",") if e.strip()]
        cli[key] = value
    return cli


def _load_prior_items(json_path: str) -> dict:
    """Best-effort load of previous metadata.json items keyed by id.

    Lets resume-skipped rows keep their full metadata instead of
    degrading outputs to empty records.
    """
    import json as _json

    try:
        with open(json_path, "r", encoding="utf-8") as fh:
            data = _json.load(fh)
        items = data.get("items", [])
        return {i["id"]: i for i in items if isinstance(i, dict) and "id" in i}
    except (OSError, ValueError):
        return {}


def _result_id(abs_path: str, file_sha: str) -> str:
    norm = os.path.normcase(os.path.normpath(abs_path))
    return hashlib.sha256(f"{norm}|{file_sha}".encode("utf-8")).hexdigest()[:32]


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _close_images(imgs) -> None:
    if isinstance(imgs, (list, tuple)):
        for img in imgs:
            try:
                img.close()
            except Exception:
                pass
    elif imgs is not None:
        try:
            imgs.close()
        except Exception:
            pass


def _discover_default_config() -> str | None:
    pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    for candidate in [
        os.path.abspath("config.yaml"),
        os.path.join(pkg_root, "config.yaml"),
    ]:
        if os.path.isfile(candidate):
            return candidate
    return None


def cmd_generate(args: argparse.Namespace) -> int:
    config_path = args.config or _discover_default_config()
    yaml_data = load_yaml(config_path) if config_path else None
    try:
        cfg = build_config(yaml_data or {}, _cli_to_config(args))
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    logger = setup_logging(cfg.output.directory, cfg.verbose)
    retry_invalid = True if args.retry_invalid_json is None else args.retry_invalid_json

    try:
        discovered = discover_inputs(
            args.input,
            recursive=cfg.processing.recursive,
            extensions=cfg.extensions or None,
            limit=cfg.limit,
            media_type=cfg.media_type,
        )
    except (ConfigurationError, UnsupportedImageError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    logger.info("Discovered %d item(s) from %s", len(discovered), args.input)
    if args.dry_run:
        for item in discovered:
            print(f"would process: {item['relative_path']}")
        return EXIT_OK

    out = cfg.output
    try:
        store = CheckpointStore(os.path.join(out.directory, out.checkpoint_filename))
    except CheckpointError as exc:
        print(f"Checkpoint error: {exc}", file=sys.stderr)
        return EXIT_OUTPUT_ERROR

    prior_items = _load_prior_items(os.path.join(out.directory, out.json_filename))

    from .api_inference import build_providers

    if getattr(args, "api_model", None) is not None:
        cfg.api.cli_model = args.api_model

    try:
        providers = build_providers(cfg.api, cfg.api.timeout)
    except MicrostockError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    model, processor, device_used, quant_used = None, None, "api", "n/a"
    model_label = "+".join(p["model"] for p in providers)
    prompt_version = API_PROMPT_VERSION
    logger.info("API providers in order: %s",
                ", ".join(f"{p['name']}({p['model']})" for p in providers))
    console_art.print_banner(model_label, f"{device_used}({quant_used})",
                             False, cfg.backend)

    results: list[ProcessingResult] = []
    bar = console_art.ProgressBar(len(discovered))

    api_ctx = {"providers": providers, "timeout": cfg.api.timeout}
    for index, item in enumerate(discovered, 1):
        bar.show(index, item["filename"])
        progress = lambda label, _i=index, _b=bar: _b.show(_i, label)
        item_prompt_version = (
            VIDEO_PROMPT_VERSION if item.get("media") == "video" else prompt_version
        )
        result = _process_one(
            item, cfg, store, model, processor, device_used, quant_used,
            item_prompt_version, retry_invalid, logger, api_ctx, prior_items,
            progress,
        )
        results.append(result)
        try:
            _flush_outputs(results, cfg, prompt_version)
        except ExportError as exc:
            print(f"Output error: {exc}", file=sys.stderr)
            return EXIT_OUTPUT_ERROR
        cleanup_memory(device_used)
    gc.collect()

    bar.finish()
    from .exporters import summarize

    summary = summarize(results)
    logger.info(
        "Done: %d total, %d ok, %d failed, %d skipped, %d need review",
        summary["total"], summary["successful"], summary["failed"],
        summary["skipped"], summary["needs_review"],
    )
    console_art.print_summary(summary)
    for provider in api_ctx["providers"]:
        logger.info("API key usage %s: %s",
                    provider["name"], provider["pool"].stats())
    return EXIT_ITEM_FAILURE if summary["failed"] else EXIT_OK


def _process_one(item, cfg: AppConfig, store, model, processor,
                 device_used, quant_used, prompt_version, retry_invalid, logger,
                 api_ctx=None, prior_items=None, progress=None):
    ping = progress or (lambda label: None)
    started = time.monotonic()
    started_at = utcnow()
    base = {
        "filename": item["filename"],
        "source_path": item["path"],
        "relative_path": item["relative_path"],
        "model_id": cfg.model.id,
        "prompt_version": prompt_version,
        "device": device_used,
        "quantization": quant_used,
        "backend": "api",
        "provider": "",
        "media_type": item.get("media", "image"),
    }
    try:
        file_sha = _sha256_file(item["path"])
    except OSError as exc:
        return _failed(base, started, started_at, "ImageReadError", str(exc), store, 0,
                       source_sha="")
    rid = _result_id(item["path"], file_sha)
    stat = os.stat(item["path"])
    modified = datetime.fromtimestamp(stat.st_mtime, tz=datetime.now().astimezone().tzinfo).isoformat()

    if cfg.processing.resume and not cfg.overwrite and store.is_completed(rid, file_sha):
        logger.info("Skipped (resume): %s", item["relative_path"])
        prior = (prior_items or {}).get(rid)
        if prior:
            record = dict(prior)
            record["status"] = "skipped"
            try:
                return ProcessingResult(**record)
            except Exception:
                pass
        return ProcessingResult(id=rid, source_size_bytes=stat.st_size,
                                 source_modified_at=modified, source_sha256=file_sha,
                                 status="skipped", attempt_count=0, **base)

    is_video = item.get("media") == "video"
    pil = None
    video_gate_reasons: list[str] = []
    if is_video:
        from .video_processing import assess_video, extract_frames, probe_video

        try:
            probe = probe_video(item["path"])
            video_gate_reasons = assess_video(
                {**probe, "codec": probe.get("codec"), "fps": probe.get("fps"), "container": probe.get("container")}
            )
            w = probe.get("width")
            h = probe.get("height")
            if (w == 720 and h == 1280) or (w == 1080 and h == 1920):
                video_gate_reasons = [r for r in video_gate_reasons if r != "below_hd_min"]
            frames, _attempted = extract_frames(
                item["path"],
                count=cfg.video.frames,
                max_edge=cfg.video.max_edge,
                max_duration_sec=cfg.video.max_duration_sec,
            )
        except (ImageReadError, UnsupportedImageError) as exc:
            return _failed(base, started, started_at, type(exc).__name__, str(exc),
                           store, 0, source_sha=file_sha, size=stat.st_size,
                           modified=modified, rid=rid)

        pil = frames
        ow = probe.get("width") or 0
        oh = probe.get("height") or 0
        pw = frames[0].size[0] if frames else 0
        ph = frames[0].size[1] if frames else 0
        low_res = False
        video_dur = probe.get("duration_sec")
        frame_cnt = len(frames)
    else:
        try:
            pil, ow, oh, pw, ph = normalize_image(item["path"], cfg.image.max_edge)
        except (ImageReadError, UnsupportedImageError) as exc:
            return _failed(base, started, started_at, type(exc).__name__, str(exc),
                           store, 0, source_sha=file_sha, size=stat.st_size,
                           modified=modified, rid=rid)

        low_res = (ow * oh) < cfg.image.min_pixels
        video_dur = None
        frame_cnt = 0

    raw, repaired, attempts = "", False, 0
    try:
        from .api_inference import generate_with_fallback
        from .prompts import build_prompt as _bp
        from .prompts import build_retry_prompt as _brp

        max_attempts = cfg.processing.retry_count + 1
        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            attempts = attempt
            ping(f"api infer"
                 + (f" (retry {attempt})" if attempt > 1 else "")
                 + f" {item['filename']}")
            try:
                _v, first_text = _bp(prompt_version)
                _w, retry_text = _brp("previous response was not valid JSON",
                                      prompt_version)
                raw, prov_name, prov_model = generate_with_fallback(
                    pil, first_text if attempt == 1 else retry_text,
                    api_ctx["providers"],
                    max_tokens=cfg.api.max_tokens if hasattr(cfg.api, "max_tokens") else cfg.model.max_new_tokens,
                    temperature=cfg.api.temperature if hasattr(cfg.api, "temperature") else cfg.model.temperature,
                    timeout=api_ctx["timeout"],
                )
                base["model_id"] = prov_model
                base["provider"] = prov_name
                repaired = False
            except (InferenceError, InvalidModelResponseError) as exc:
                last_exc = exc
                if getattr(exc, "last_raw", ""):
                    raw = exc.last_raw  # type: ignore[attr-defined]
                if not retry_invalid:
                    break
                continue
            try:
                gen, repaired_flag = extract_json(raw)
                repaired = repaired or repaired_flag
                validate_required(
                    {"title": gen.title, "description": gen.description,
                     "keywords": gen.keywords}
                )
                last_exc = None
                break
            except (InvalidModelResponseError, MetadataValidationError) as exc:
                last_exc = exc
                if not retry_invalid:
                    break
                continue
        if last_exc is not None:
            raise last_exc
        ping(f"validate+save {item['filename']}")
    except MicrostockError as exc:
        _close_images(pil)
        cleanup_memory(device_used)
        return _failed(base, started, started_at, type(exc).__name__, str(exc),
                       store, attempts, source_sha=file_sha, size=stat.st_size,
                       modified=modified, rid=rid, raw=raw if cfg.processing.store_raw_response else None,
                       dims=(ow, oh, pw, ph))
    finally:
        _close_images(pil)

    from .normalization import resolve_limits as _resolve
    _tmax, _dmax, _kmax = _resolve(cfg.metadata.platform if hasattr(cfg.metadata, "platform") else "adobe", cfg.metadata.title_max_length, cfg.metadata.description_max_length, cfg.metadata.max_keywords)
    norm = normalize_metadata(
        gen,
        title_max=_tmax,
        description_max=_dmax,
        keyword_max_len=60,
        keyword_max_count=_kmax,
    )
    norm["review_reasons"] = list(norm.get("review_reasons", [])) + [
        r for r in video_gate_reasons if r not in norm.get("review_reasons", [])
    ]
    if len(norm["keywords"]) > cfg.metadata.max_keywords:
        pass  # already capped in normalize_keywords
    needs_review, reasons = decide_review(
        norm,
        min_keywords=cfg.metadata.min_keywords,
        repaired_json=repaired,
        retried=attempts > 1,
        low_resolution=low_res,
    )
    if len(norm["keywords"]) < cfg.metadata.min_keywords and not needs_review:
        needs_review = True  # decide_review already appends; belt and suspenders
    needs_review = needs_review or bool(video_gate_reasons)
    reasons = reasons + [r for r in video_gate_reasons if r not in reasons]
    duration = time.monotonic() - started
    result = ProcessingResult(
        id=rid, source_size_bytes=stat.st_size, source_modified_at=modified,
        source_sha256=file_sha, image_width=ow, image_height=oh,
        processed_width=pw, processed_height=ph,
        started_at=started_at, completed_at=utcnow(),
        duration_seconds=duration, title=norm["title"],
        description=norm["description"], category=norm["category"],
        keywords=norm["keywords"], keyword_count=len(norm["keywords"]),
        people_count=norm["people_count"],
        has_recognizable_people=norm["has_recognizable_people"],
        contains_text=norm["contains_text"], visible_text=norm["visible_text"],
        possible_trademark=norm["possible_trademark"],
        editorial_risk=norm["editorial_risk"], needs_review=needs_review,
        review_reasons=reasons, review_notes=norm["review_notes"],
        status="success", attempt_count=attempts,
        video_duration_sec=video_dur,
        frame_count=frame_cnt,
        is_ai_generated=(base.get("media_type") == "video"),
        needs_model_release=bool(norm.get("has_recognizable_people")),
        needs_property_release=bool(norm.get("possible_trademark")),
        raw_response=raw if cfg.processing.store_raw_response else None,
        **base,
    )
    try:
        store.save(rid, "success", file_sha, attempts)
    except CheckpointError as exc:
        logger.warning("Checkpoint save failed for %s: %s", item["filename"], exc)
    logger.info("OK %s kw=%d review=%s (%.1fs)", item["filename"],
                len(norm["keywords"]), needs_review, duration)
    cleanup_memory(device_used)
    return result


def _failed(base, started, started_at, error_type, message, store, attempts,
            source_sha="", size=0, modified="", rid="", raw=None, dims=(0, 0, 0, 0)):
    if not rid:
        rid = _result_id(base["source_path"], source_sha or base["source_path"])
    result = ProcessingResult(
        id=rid, source_size_bytes=size, source_modified_at=modified,
        source_sha256=source_sha, image_width=dims[0], image_height=dims[1],
        processed_width=dims[2], processed_height=dims[3],
        started_at=started_at, completed_at=utcnow(),
        duration_seconds=time.monotonic() - started, status="failed",
        attempt_count=attempts, raw_response=raw,
        error_type=error_type, error_message=message, **base,
    )
    try:
        store.save(rid, "failed", source_sha, attempts)
    except CheckpointError:
        pass
    return result


def _flush_outputs(results, cfg: AppConfig, prompt_version: str) -> None:
    from .exporters import write_failed_json, write_metadata_csv, write_metadata_json

    out = cfg.output
    configuration = {
        "backend": cfg.backend,
        "model": cfg.model.__dict__,
        "api": cfg.api.__dict__,
        "image": cfg.image.__dict__,
        "metadata": cfg.metadata.__dict__,
        "processing": cfg.processing.__dict__,
    }
    write_metadata_json(results, configuration, cfg.model.id, prompt_version,
                        os.path.join(out.directory, out.json_filename))
    write_metadata_csv(results, os.path.join(out.directory, out.csv_filename))
    write_failed_json(results, os.path.join(out.directory, out.failed_filename))


def _ram_info() -> str:
    try:
        import ctypes

        class MemStat(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        stat = MemStat()
        stat.dwLength = ctypes.sizeof(MemStat)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        total = stat.ullTotalPhys / (1024 ** 3)
        return f"{total:.1f} GB total"
    except Exception:
        pass
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return f"{kb / 1024 / 1024:.1f} GB total"
    except OSError:
        pass
    return "unknown"


def cmd_doctor(args: argparse.Namespace) -> int:
    import importlib.util
    import shutil

    out_dir = args.output_dir or "output"
    checks: list[tuple[str, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ("OK " if ok else "!! ") + detail))

    add("python", sys.version_info >= (3, 10), sys.version.split()[0])
    for pkg in ("PIL", "pydantic", "yaml"):
        spec = importlib.util.find_spec(pkg)
        detail = ""
        if spec is not None:
            try:
                mod = __import__(pkg)
                detail = getattr(mod, "__version__", getattr(mod, "VERSION", "installed"))
            except Exception:
                detail = "installed"
        add(pkg, spec is not None, str(detail) if detail else "MISSING")

    for tool in ("ffmpeg", "ffprobe"):
        tool_path = shutil.which(tool)
        add(tool, tool_path is not None, tool_path if tool_path else "not in PATH (video input unavailable)")

    from .api_inference import ensure_dotenv_loaded
    ensure_dotenv_loaded()
    api_key_set = bool(os.environ.get("MICROSTOCK_API_KEY", "").strip())
    add("api-key (local-gateway)", api_key_set, "configured" if api_key_set else "not set in env/.env")
    cf_token_set = bool(os.environ.get("MICROSTOCK_CF_API_TOKEN", "").strip())
    add("api-key (cloudflare)", cf_token_set, "configured" if cf_token_set else "not set in env/.env")

    try:
        os.makedirs(out_dir, exist_ok=True)
        probe = os.path.join(out_dir, ".writetest")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("ok")
        os.remove(probe)
        add("output-writable", True, os.path.abspath(out_dir))
    except OSError as exc:
        add("output-writable", False, str(exc))

    width = max(len(name) for name, _ in checks)
    print("microstock-metadata doctor")
    for name, status in checks:
        print(f"  {name.ljust(width)}  {status}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            return cmd_generate(args)
        if args.command == "doctor":
            return cmd_doctor(args)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except CheckpointError as exc:
        print(f"Checkpoint error: {exc}", file=sys.stderr)
        return EXIT_OUTPUT_ERROR
    except ExportError as exc:
        print(f"Output error: {exc}", file=sys.stderr)
        return EXIT_OUTPUT_ERROR
    parser.error("unknown command")
    return EXIT_CONFIG_ERROR
    parser.error("unknown command")
    return EXIT_CONFIG_ERROR


if __name__ == "__main__":
    sys.exit(main())
