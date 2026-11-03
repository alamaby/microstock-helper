"""Metadata normalization: limits, dedupe, category and risk fallbacks."""

from __future__ import annotations

import re

from .constants import CATEGORIES, CATEGORY_ALIASES
from .schemas import GeneratedMetadata

_TRAILING_PUNCT_RE = re.compile(r"[.!?;:,]+$")
_NUMBER_PREFIX_RE = re.compile(r"^\s*(?:\d+[.)\]}:-]|[-*\u2022])\s+")
_WHITESPACE_RE = re.compile(r"\s+")
_LOCATION_CLAIM_RE = re.compile(
    r"\b(?:in|at|near|from|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})"
)


def _clean_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value or "").strip()


def normalize_title(title: str, max_length: int) -> tuple[str, bool]:
    text = _clean_text(title).replace("\n", " ")
    text = _TRAILING_PUNCT_RE.sub("", text).strip()
    truncated = False
    if len(text) > max_length:
        text = text[:max_length].rstrip()
        truncated = True
    return text, truncated


def normalize_description(description: str, max_length: int) -> tuple[str, bool]:
    text = _clean_text(description).replace("\n", " ")
    text = re.sub(r"[*_`#]", "", text)
    truncated = False
    if len(text) > max_length:
        text = text[:max_length].rstrip()
        truncated = True
    return text, truncated


def normalize_keyword(raw: str, max_length: int) -> str:
    text = _clean_text(raw).lower()
    text = _NUMBER_PREFIX_RE.sub("", text)
    text = text.lstrip("#").strip()
    text = re.sub(r"[.,;:!?]+$", "", text).strip()
    if len(text) > max_length:
        text = text[:max_length].rstrip()
    return text


def normalize_keywords(
    keywords: list[str], max_length: int, max_count: int
) -> tuple[list[str], bool]:
    """Lowercase, dedupe (case-insensitive), preserve relevance order."""
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in keywords or []:
        text = normalize_keyword(str(raw), max_length)
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    truncated = False
    if len(cleaned) > max_count:
        cleaned = cleaned[:max_count]
        truncated = True
    return cleaned, truncated


def normalize_category(category: str) -> tuple[str, bool]:
    text = _clean_text(category)
    lowered = text.lower()
    for valid in CATEGORIES:
        if valid.lower() == lowered:
            return valid, False
    if lowered in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[lowered], False
    return "Other", True


def normalize_editorial_risk(value: str) -> tuple[str, bool]:
    text = _clean_text(str(value)).lower()
    if text in ("low", "medium", "high"):
        return text, False
    return "medium", True


def normalize_people_count(value: object) -> tuple[int, bool]:
    try:
        count = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0, True
    if isinstance(value, bool) or count < 0:
        return 0, True
    return count, False


def normalize_visible_text(items: list[str]) -> list[str]:
    return [_clean_text(str(v)) for v in (items or []) if _clean_text(str(v))]


def detect_location_claim(title: str, description: str) -> bool:
    combined = f"{title} {description}"
    return _LOCATION_CLAIM_RE.search(combined) is not None


def resolve_limits(platform: str, title_max: int, description_max: int, keyword_max_count: int) -> tuple[int, int, int]:
    """Platform override with global fallback. Unknown platform returns globals unchanged."""
    try:
        from .platforms import PLATFORMS
    except ImportError:
        return title_max, description_max, keyword_max_count
    prof = PLATFORMS.get((platform or "adobe").lower())
    if not prof:
        return title_max, description_max, keyword_max_count
    return prof["title_max"], prof["description_max"], min(keyword_max_count, prof["kw_max"])


def normalize_metadata(
    gen: GeneratedMetadata,
    title_max: int,
    description_max: int,
    keyword_max_len: int,
    keyword_max_count: int,
) -> dict:
    """Return normalized fields plus a list of review reasons found so far."""
    reasons: list[str] = []
    title, title_trunc = normalize_title(gen.title, title_max)
    if title_trunc:
        reasons.append("title_truncated")
    description, desc_trunc = normalize_description(gen.description, description_max)
    if desc_trunc:
        reasons.append("description_truncated")
    keywords, _kw_trunc = normalize_keywords(gen.keywords, keyword_max_len, keyword_max_count)
    # Truncation to max_count is recorded by the caller (needs config context).
    category, invalid_cat = normalize_category(gen.category)
    if invalid_cat:
        reasons.append("invalid_category")
    risk, risk_fixed = normalize_editorial_risk(gen.editorial_risk)
    if risk_fixed:
        reasons.append("editorial_risk_unknown")
    people_count, people_fixed = normalize_people_count(gen.people_count)
    if people_fixed:
        reasons.append("people_count_invalid")
    visible_text = normalize_visible_text(gen.visible_text)
    contains_text = bool(gen.contains_text)
    if contains_text and not visible_text:
        reasons.append("visible_text_missing")
    if not contains_text and visible_text:
        reasons.append("visible_text_unexpected")
    has_people = bool(gen.has_recognizable_people)
    trademark = bool(gen.possible_trademark)
    if has_people:
        reasons.append("recognizable_people")
    if contains_text:
        reasons.append("visible_text")
    if trademark:
        reasons.append("possible_trademark")
    if risk == "medium":
        reasons.append("editorial_risk_medium")
    elif risk == "high":
        reasons.append("editorial_risk_high")
    if gen.review_notes:
        reasons.append("model_review_note")
    if detect_location_claim(title, description):
        reasons.append("location_claim")
    return {
        "title": title,
        "description": description,
        "category": category,
        "keywords": keywords,
        "keywords_truncated": _kw_trunc,
        "people_count": people_count,
        "has_recognizable_people": has_people,
        "contains_text": contains_text,
        "visible_text": visible_text,
        "possible_trademark": trademark,
        "editorial_risk": risk,
        "review_notes": [_clean_text(str(n)) for n in (gen.review_notes or []) if _clean_text(str(n))],
        "review_reasons": reasons,
    }
