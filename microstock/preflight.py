"""Preflight validation and external binary discovery."""

from __future__ import annotations

import os
import shutil
import sys
from typing import Dict, List, Optional, Tuple

DEFAULT_WINDOWS_PATHS: Dict[str, List[str]] = {
    "exiftool": [
        r"C:\Apps\exiftool\exiftool.exe",
        r"C:\Program Files\exiftool\exiftool.exe",
        r"C:\Program Files (x86)\exiftool\exiftool.exe",
    ],
    "upscayl": [
        r"C:\Program Files\Upscayl\resources\bin\upscayl-bin.exe",
        r"C:\Program Files (x86)\Upscayl\resources\bin\upscayl-bin.exe",
        r"C:\Apps\Upscayl\resources\bin\upscayl-bin.exe",
    ],
    "vtracer": [
        r"C:\Apps\vtracer.exe",
        r"C:\Program Files\vtracer\vtracer.exe",
        r"C:\Program Files (x86)\vtracer\vtracer.exe",
    ],
    "inkscape": [
        r"C:\Program Files\Inkscape\bin\inkscape.com",
        r"C:\Program Files\Inkscape\inkscape.com",
        r"C:\Program Files (x86)\Inkscape\bin\inkscape.com",
    ],
    "ffmpeg": [
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ],
    "ffprobe": [
        r"C:\ProgramData\chocolatey\bin\ffprobe.exe",
        r"C:\ffmpeg\bin\ffprobe.exe",
    ],
}


class PreflightError(Exception):
    """Raised when one or more required external dependencies are missing."""


def resolve_binary(tool_name: str, explicit_path: Optional[str] = None) -> Optional[str]:
    """Resolve executable path for a given tool.

    Priority:
    1. Explicit path passed directly or from configuration
    2. Environment variable MICROSTOCK_<TOOL>_PATH
    3. System PATH (shutil.which)
    4. Known Windows installation directories
    """
    if explicit_path:
        path = os.path.abspath(os.path.expanduser(explicit_path))
        if os.path.isfile(path):
            return path

    env_var = f"MICROSTOCK_{tool_name.upper()}_PATH"
    if env_var in os.environ and os.environ[env_var].strip():
        env_path = os.path.abspath(os.path.expanduser(os.environ[env_var].strip()))
        if os.path.isfile(env_path):
            return env_path

    in_path = shutil.which(tool_name)
    if in_path:
        return os.path.abspath(in_path)

    if sys.platform == "win32":
        for ext in (".exe", ".com", ".bat", ".cmd"):
            in_path = shutil.which(f"{tool_name}{ext}")
            if in_path:
                return os.path.abspath(in_path)

        for candidate in DEFAULT_WINDOWS_PATHS.get(tool_name.lower(), []):
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)

    return None


def get_tool_map(explicit_paths: Optional[Dict[str, str]] = None) -> Dict[str, Optional[str]]:
    """Return dictionary of resolved paths for all recognized tools."""
    explicit_paths = explicit_paths or {}
    tools = ["exiftool", "upscayl", "vtracer", "inkscape", "ffmpeg", "ffprobe"]
    return {tool: resolve_binary(tool, explicit_paths.get(tool)) for tool in tools}


def validate_dependencies(
    required_tools: List[str],
    explicit_paths: Optional[Dict[str, str]] = None,
    require_api_key: bool = False,
) -> Dict[str, str]:
    """Validate that all required tools exist.

    Returns dict of tool -> resolved path. Raises PreflightError on failure.
    """
    resolved: Dict[str, str] = {}
    missing: List[str] = []
    tool_map = get_tool_map(explicit_paths)

    for tool in required_tools:
        path = tool_map.get(tool.lower())
        if path and os.path.isfile(path):
            resolved[tool.lower()] = path
        else:
            missing.append(tool)

    api_missing = False
    if require_api_key:
        from .metadata.api_inference import ensure_dotenv_loaded

        ensure_dotenv_loaded()
        primary_key = os.environ.get("MICROSTOCK_API_KEY", "").strip()
        cf_token = os.environ.get("MICROSTOCK_CF_API_TOKEN", "").strip()
        if not (primary_key or cf_token):
            api_missing = True

    if missing or api_missing:
        reasons = []
        if missing:
            reasons.append(f"Missing required external CLI tools: {', '.join(missing)}")
        if api_missing:
            reasons.append(
                "Missing API keys: Set MICROSTOCK_API_KEY or MICROSTOCK_CF_API_TOKEN in .env"
            )
        msg = "\n".join(reasons)
        raise PreflightError(msg)

    return resolved
