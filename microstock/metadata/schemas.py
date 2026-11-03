"""Pydantic schemas for model output and processing results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GeneratedMetadata(BaseModel):
    title: str
    description: str
    category: str
    keywords: list[str]
    people_count: int = 0
    has_recognizable_people: bool = False
    contains_text: bool = False
    visible_text: list[str] = Field(default_factory=list)
    possible_trademark: bool = False
    editorial_risk: str = "low"
    review_notes: list[str] = Field(default_factory=list)


class ProcessingResult(BaseModel):
    id: str
    filename: str
    source_path: str
    relative_path: str
    source_size_bytes: int = 0
    source_modified_at: str = ""
    source_sha256: str = ""
    image_width: int = 0
    image_height: int = 0
    processed_width: int = 0
    processed_height: int = 0
    model_id: str = ""
    prompt_version: str = ""
    device: str = ""
    quantization: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0
    title: str = ""
    description: str = ""
    category: str = ""
    keywords: list[str] = Field(default_factory=list)
    keyword_count: int = 0
    people_count: int = 0
    has_recognizable_people: bool = False
    contains_text: bool = False
    visible_text: list[str] = Field(default_factory=list)
    possible_trademark: bool = False
    editorial_risk: str = "low"
    needs_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    status: Literal["success", "failed", "skipped"] = "success"
    backend: str = "api"  # api (OpenAI-compatible / Cloudflare)
    provider: str = ""  # api provider name that answered
    media_type: str = "image"
    video_duration_sec: float | None = None
    frame_count: int = 0
    is_ai_generated: bool = False
    needs_model_release: bool = False
    needs_property_release: bool = False
    attempt_count: int = 0
    raw_response: str | None = None
    error_type: str | None = None
    error_message: str | None = None
