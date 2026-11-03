"""Configuration: code defaults, optional YAML override, CLI overrides YAML."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml

from .constants import (
    DEFAULT_MODEL_ID,
    DEFAULT_VIDEO_FRAMES,
    DESCRIPTION_MAX_LENGTH,
    KEYWORD_MAX_DEFAULT,
    KEYWORD_MIN_TARGET,
    TITLE_MAX_LENGTH,
    VIDEO_MAX_DURATION_SEC,
)
from .exceptions import ConfigurationError


@dataclass
class ModelConfig:
    id: str = DEFAULT_MODEL_ID
    max_new_tokens: int = 768
    temperature: float = 0.0


@dataclass
class ImageConfig:
    max_edge: int = 1536
    min_pixels: int = 200704
    max_pixels: int = 602112


@dataclass
class VideoConfig:
    frames: int = DEFAULT_VIDEO_FRAMES
    max_duration_sec: int = VIDEO_MAX_DURATION_SEC
    max_edge: int = 1024


@dataclass
class MetadataConfig:
    language: str = "en"
    platform: str = "adobe"
    min_keywords: int = KEYWORD_MIN_TARGET
    max_keywords: int = KEYWORD_MAX_DEFAULT
    title_max_length: int = TITLE_MAX_LENGTH
    description_max_length: int = DESCRIPTION_MAX_LENGTH


@dataclass
class ProcessingConfig:
    recursive: bool = True
    resume: bool = True
    retry_count: int = 2
    store_raw_response: bool = True


@dataclass
class OutputConfig:
    directory: str = "output"
    json_filename: str = "metadata.json"
    csv_filename: str = "metadata.csv"
    failed_filename: str = "failed_items.json"
    checkpoint_filename: str = "checkpoint.json"
    log_filename: str = "processing.log"


@dataclass
class ApiConfig:
    endpoint: str = "http://127.0.0.1:20128/v1"
    model: str = "oc/mimo-v2.6-flash-free"
    key_env: str = "MICROSTOCK_API_KEY"
    timeout: int = 120
    max_tokens: int = 768
    temperature: float = 0.0
    # Ordered provider chain (failover in list order). Empty -> single
    # provider built from the flat endpoint/model/key_env above.
    # Each entry: {name, endpoint, model, key_env, account_env?}.
    # "{account_id}" in endpoint is replaced from account_env.
    providers: list = field(default_factory=list)


@dataclass
class AppConfig:
    backend: str = "api"  # api only (OpenAI-compatible & Cloudflare)
    media_type: str = "auto"
    model: ModelConfig = field(default_factory=ModelConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    image: ImageConfig = field(default_factory=ImageConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    metadata: MetadataConfig = field(default_factory=MetadataConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    limit: int | None = None
    extensions: list[str] = field(default_factory=list)
    overwrite: bool = False
    verbose: bool = False


def load_yaml(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Config file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError(f"Config file must contain a mapping: {path}")
    return data


def _apply_section(obj: object, data: dict, prefix: str) -> None:
    for key, value in data.items():
        if not hasattr(obj, key):
            raise ConfigurationError(f"Unknown config key: {prefix}.{key}")
        setattr(obj, key, value)


def build_config(yaml_data: dict | None, cli: dict) -> AppConfig:
    """Precedence: code defaults < YAML < explicit CLI values."""
    cfg = AppConfig()
    if yaml_data:
        for section, target in (
            ("model", cfg.model),
            ("api", cfg.api),
            ("image", cfg.image),
            ("video", cfg.video),
            ("metadata", cfg.metadata),
            ("processing", cfg.processing),
            ("output", cfg.output),
        ):
            section_data = yaml_data.get(section, {})
            if section_data is None:
                continue
            if not isinstance(section_data, dict):
                raise ConfigurationError(f"Config section must be a mapping: {section}")
            _apply_section(target, section_data, section)
        for key in ("backend", "media_type", "limit", "extensions", "overwrite", "verbose"):
            if key in yaml_data:
                setattr(cfg, key, yaml_data[key])
    for key, value in cli.items():
        if value is None:
            continue
        if key in ("backend", "media_type", "limit", "extensions", "overwrite", "verbose"):
            setattr(cfg, key, value)
        elif "." in key:
            section, field_name = key.split(".", 1)
            target = getattr(cfg, section, None)
            if target is None or not hasattr(target, field_name):
                raise ConfigurationError(f"Unknown config key: {key}")
            setattr(target, field_name, value)
        else:
            raise ConfigurationError(f"Unknown CLI config key: {key}")
    return validate_config(cfg)


def validate_config(cfg: AppConfig) -> AppConfig:
    if cfg.media_type not in ("auto", "image", "video"):
        raise ConfigurationError(f"Invalid media_type: {cfg.media_type}")
    if not 1 <= cfg.video.frames <= 12:
        raise ConfigurationError("--frames must be between 1 and 12")
    if cfg.video.max_duration_sec < 5:
        raise ConfigurationError("--video-max-duration must be >= 5 seconds")
    if cfg.video.max_edge < 128:
        raise ConfigurationError("--video-max-edge must be >= 128")
    if cfg.backend != "api":
        raise ConfigurationError(
            f"Invalid backend: '{cfg.backend}'. Local model backend has been removed. "
            "Supported backend is 'api' (OpenAI-compatible & Cloudflare)."
        )
    if cfg.api.timeout < 5:
        raise ConfigurationError("--api-timeout must be >= 5 seconds")
    if not isinstance(cfg.api.providers, list):
        raise ConfigurationError("api.providers must be a list")
    for entry in cfg.api.providers:
        if not isinstance(entry, dict):
            raise ConfigurationError("api.providers entries must be mappings")
        for field in ("name", "endpoint", "model", "key_env"):
            if field not in entry:
                raise ConfigurationError(
                    f"api.providers entry missing '{field}': {entry}")
    if cfg.metadata.platform not in ("adobe", "dreamstime", "vecteezy", "pixabay", "all"):
        raise ConfigurationError(
            f"--platform must be one of: adobe, dreamstime, vecteezy, pixabay, all (got: {cfg.metadata.platform})"
        )
    if not 5 <= cfg.metadata.max_keywords <= 80:
        raise ConfigurationError("--max-keywords must be between 5 and 80")
    if cfg.metadata.min_keywords < 1:
        raise ConfigurationError("--min-keywords must be >= 1")
    if cfg.metadata.min_keywords > cfg.metadata.max_keywords:
        raise ConfigurationError("--min-keywords cannot exceed --max-keywords")
    if cfg.model.max_new_tokens < 64:
        raise ConfigurationError("--max-new-tokens must be >= 64")
    if cfg.model.temperature < 0.0:
        raise ConfigurationError("--temperature cannot be negative")
    if cfg.model.temperature > 0.0:
        # Deterministic generation is the default; sampling is allowed explicitly.
        pass
    if cfg.image.max_edge < 128:
        raise ConfigurationError("--max-image-edge must be >= 128")
    if cfg.processing.retry_count < 0:
        raise ConfigurationError("--retry-count cannot be negative")
    if cfg.limit is not None and cfg.limit < 1:
        raise ConfigurationError("--limit must be >= 1")
    out = os.path.abspath(cfg.output.directory)
    try:
        os.makedirs(out, exist_ok=True)
    except OSError as exc:
        raise ConfigurationError(f"Output directory is not writable: {out}: {exc}") from exc
    cfg.output.directory = out
    return cfg
