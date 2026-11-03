"""JSON extraction with safe, minimal repair, then Pydantic validation."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from .exceptions import InvalidModelResponseError
from .schemas import GeneratedMetadata

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def _replace_booleans_outside_strings(text: str) -> str:
    """Convert unambiguous Python True/False/None tokens outside string
    literals. Anything inside quotes is left untouched."""
    out: list[str] = []
    i, n = 0, len(text)
    in_string = False
    quote = ""
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                in_string = False
            i += 1
            continue
        if ch in ("'", '"'):
            in_string = True
            quote = ch
            out.append(ch)
            i += 1
            continue
        rest = text[i:]
        for py, js in (("True", "true"), ("False", "false"), ("None", "null")):
            if rest.startswith(py):
                after = rest[len(py):len(py) + 1]
                before_ok = not out or not (out[-1].isalnum() or out[-1] == "_")
                after_ok = after == "" or not (after.isalnum() or after == "_")
                if before_ok and after_ok:
                    out.append(js)
                    i += len(py)
                    break
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _extract_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    quote = ""
    i = start
    while i < len(text):
        ch = text[i]
        if in_string:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                in_string = False
        elif ch in ('"', "'"):
            in_string = True
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    return None


def extract_json(raw: str) -> tuple[GeneratedMetadata, bool]:
    """Parse raw model output. Returns (metadata, repaired_flag)."""
    if not raw or not raw.strip():
        raise InvalidModelResponseError("Empty model response")
    repaired = False
    text = raw.strip()
    fence = _FENCE_RE.match(text)
    if fence:
        text = fence.group(1).strip()
        repaired = True
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        candidate = _extract_balanced_object(text)
        if candidate is None:
            raise InvalidModelResponseError("No JSON object found in response")
        text = candidate
        repaired = True
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            fixed = _TRAILING_COMMA_RE.sub(r"\1", text)
            fixed = _replace_booleans_outside_strings(fixed)
            if fixed != text:
                repaired = True
            try:
                obj = json.loads(fixed)
            except json.JSONDecodeError as exc:
                raise InvalidModelResponseError(f"Unparseable JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise InvalidModelResponseError("Top-level JSON must be an object")
    try:
        return GeneratedMetadata(**obj), repaired
    except ValidationError as exc:
        raise InvalidModelResponseError(f"Schema validation failed: {exc}") from exc
