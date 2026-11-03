"""Restart-safe checkpoint: minimal per-ID state, atomic writes."""

from __future__ import annotations

import json
import os
import tempfile

from .exceptions import CheckpointError


class CheckpointStore:
    """Tracks {result_id: {status, source_sha256, attempt_count}}."""

    def __init__(self, path: str):
        self.path = path
        self.state: dict = {"version": 1, "items": {}}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict) or "items" not in data:
                raise ValueError("bad checkpoint shape")
            self.state = data
        except (OSError, ValueError, json.JSONDecodeError):
            backup = self.path + ".corrupt.bak"
            try:
                os.replace(self.path, backup)
            except OSError:
                pass
            self.state = {"version": 1, "items": {}}

    def is_completed(self, result_id: str, source_sha256: str) -> bool:
        item = self.state["items"].get(result_id)
        return bool(
            item
            and item.get("status") == "success"
            and item.get("source_sha256") == source_sha256
        )

    def save(self, result_id: str, status: str, source_sha256: str, attempts: int) -> None:
        self.state["items"][result_id] = {
            "status": status,
            "source_sha256": source_sha256,
            "attempt_count": attempts,
        }
        self._persist()

    def _persist(self) -> None:
        directory = os.path.dirname(self.path) or "."
        try:
            os.makedirs(directory, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.state, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        except OSError as exc:
            raise CheckpointError(f"Cannot persist checkpoint: {exc}") from exc
