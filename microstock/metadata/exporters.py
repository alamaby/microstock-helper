"""Exporters: metadata.json, metadata.csv (UTF-8 BOM), failed_items.json."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from datetime import datetime, timezone

from .constants import SCHEMA_VERSION
from .exceptions import ExportError
from .schemas import ProcessingResult


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_text(path: str, text: str, encoding: str = "utf-8") -> None:
    directory = os.path.dirname(path) or "."
    try:
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        with os.fdopen(fd, "w", encoding=encoding, newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError as exc:
        raise ExportError(f"Cannot write {path}: {exc}") from exc


def summarize(results: list[ProcessingResult]) -> dict:
    return {
        "total": len(results),
        "successful": sum(1 for r in results if r.status == "success"),
        "failed": sum(1 for r in results if r.status == "failed"),
        "skipped": sum(1 for r in results if r.status == "skipped"),
        "needs_review": sum(1 for r in results if r.needs_review),
    }


def write_metadata_json(
    results: list[ProcessingResult],
    configuration: dict,
    model_id: str,
    prompt_version: str,
    path: str,
) -> None:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utcnow(),
        "model_id": model_id,
        "prompt_version": prompt_version,
        "configuration": configuration,
        "summary": summarize(results),
        "items": [r.model_dump() for r in results],
    }
    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def _cell(value: object) -> str:
    """Stringify + mitigate spreadsheet formula injection."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    if text[:1] in ("=", "+", "-", "@"):
        return "'" + text
    return text


CSV_COLUMNS = [
    "filename",
    "relative_path",
    "title",
    "description",
    "category",
    "keywords",
    "keyword_count",
    "people_count",
    "has_recognizable_people",
    "contains_text",
    "visible_text",
    "possible_trademark",
    "editorial_risk",
    "needs_review",
    "review_reasons",
    "review_notes",
    "status",
    "error_message",
    "source_sha256",
    "model_id",
    "prompt_version",
    "duration_seconds",
    "backend",
    "provider",
    "media_type",
    "video_duration_sec",
    "frame_count",
    "is_ai_generated",
    "needs_model_release",
    "needs_property_release",
]


def write_metadata_csv(results: list[ProcessingResult], path: str) -> None:
    import io

    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for r in results:
        writer.writerow(
            [
                _cell(r.filename),
                _cell(r.relative_path),
                _cell(r.title),
                _cell(r.description),
                _cell(r.category),
                _cell(", ".join(r.keywords)),
                _cell(r.keyword_count),
                _cell(r.people_count),
                _cell(r.has_recognizable_people),
                _cell(r.contains_text),
                _cell(" | ".join(r.visible_text)),
                _cell(r.possible_trademark),
                _cell(r.editorial_risk),
                _cell(r.needs_review),
                _cell(" | ".join(r.review_reasons)),
                _cell(" | ".join(r.review_notes)),
                _cell(r.status),
                _cell(r.error_message),
                _cell(r.source_sha256),
                _cell(r.model_id),
                _cell(r.prompt_version),
                _cell(round(r.duration_seconds, 2)),
                _cell(r.backend),
                _cell(r.provider),
                _cell(r.media_type),
                _cell(round(r.video_duration_sec, 2) if r.video_duration_sec is not None else ""),
                _cell(r.frame_count),
                _cell(getattr(r, "is_ai_generated", False)),
                _cell(getattr(r, "needs_model_release", False)),
                _cell(getattr(r, "needs_property_release", False)),
            ]
        )
    # UTF-8 with BOM for spreadsheet compatibility.
    _atomic_write_text(path, buf.getvalue(), encoding="utf-8-sig")


def write_failed_json(results: list[ProcessingResult], path: str) -> None:
    failed = [r for r in results if r.status == "failed"]
    payload = [
        {
            "filename": r.filename,
            "source_path": r.source_path,
            "attempt_count": r.attempt_count,
            "raw_response": r.raw_response,
            "error_type": r.error_type,
            "error_message": r.error_message,
        }
        for r in failed
    ]
    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))
