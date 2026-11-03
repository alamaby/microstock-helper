"""Validation: required fields and the needs_review decision (§16)."""

from __future__ import annotations

from .exceptions import MetadataValidationError

# Schema-echo artifacts: the model sometimes returns type names instead
# of content (e.g. {"title": "string"}). Treat as missing -> retry path.
_PLACEHOLDERS = {"string", "title", "description", "text", "n/a", "none", "null", ""}


def validate_required(normalized: dict) -> None:
    """Raise if required fields are missing (caller retries inference)."""
    if str(normalized.get("title", "")).strip().lower() in _PLACEHOLDERS:
        raise MetadataValidationError("Title is missing or a placeholder")
    if str(normalized.get("description", "")).strip().lower() in _PLACEHOLDERS:
        raise MetadataValidationError("Description is missing or a placeholder")
    if not isinstance(normalized.get("keywords"), list):
        raise MetadataValidationError("Keywords must be a list")


def decide_review(
    normalized: dict,
    min_keywords: int,
    repaired_json: bool,
    retried: bool,
    low_resolution: bool,
) -> tuple[bool, list[str]]:
    reasons = list(normalized.get("review_reasons", []))
    if len(normalized.get("keywords", [])) < min_keywords:
        reasons.append("insufficient_keywords")
    if repaired_json and "repaired_json" not in reasons:
        reasons.append("repaired_json")
    if retried and "retried_inference" not in reasons:
        reasons.append("retried_inference")
    if low_resolution and "low_resolution_source" not in reasons:
        reasons.append("low_resolution_source")
    # Dedupe while preserving order.
    seen: set[str] = set()
    ordered = [r for r in reasons if not (r in seen or seen.add(r))]
    return bool(ordered), ordered
