"""API backend: OpenAI-compatible chat-completions inference (v3).

User-approved deviation from the local-only spec: some machines are too
slow for local VL inference. The default endpoint points at a LOCAL
gateway (127.0.0.1); images still never go to a public cloud unless the
operator configures such an endpoint.

Auth: bearer key read from the environment (never hardcoded, never logged).
A minimal `.env` file loader is included so no third-party dependency
(python-dotenv) is needed.
"""

from __future__ import annotations

import base64
import io
import json
import os
import time
import urllib.error
import urllib.request

from .exceptions import InferenceError

DEFAULT_ENDPOINT = "http://127.0.0.1:20128/v1"
DEFAULT_MODEL = "oc/mimo-v2.6-flash-free"
DEFAULT_KEY_ENV = "MICROSTOCK_API_KEY"


class KeyPool:
    """Round-robin pool of API keys (comma-separated in one env var).

    - next() rotates across healthy keys; logs use 1-based indexes only.
    - report_bad() quarantines a rejected key (401/403); failover is
      automatic on the next attempt. All-bad -> InferenceError.
    """

    def __init__(self, keys: list[str]):
        import threading
        from collections import Counter

        seen: list[str] = []
        for key in keys or []:
            key = (key or "").strip().strip("\"'")
            if key and key not in seen:
                seen.append(key)
        if not seen:
            raise InferenceError(
                f"API key missing: set {DEFAULT_KEY_ENV} in the environment "
                "or in a .env file (comma-separated for several keys). "
                "See .env.example for the shape."
            )
        self._keys = seen
        self._bad: set[str] = set()
        self._idx = 0
        self._lock = threading.Lock()
        self._uses: Counter = Counter()

    def __len__(self) -> int:
        return len(self._keys)

    def next(self) -> tuple[int, str]:
        with self._lock:
            healthy = [k for k in self._keys if k not in self._bad]
            if not healthy:
                raise InferenceError("All API keys were rejected by the provider.")
            pick = healthy[self._idx % len(healthy)]
            self._idx += 1
            self._uses[pick] += 1
            return self._keys.index(pick) + 1, pick

    def report_bad(self, key: str) -> None:
        with self._lock:
            self._bad.add(key)

    def stats(self) -> str:
        parts = []
        for pos, key in enumerate(self._keys, 1):
            mark = "REJECTED" if key in self._bad else f"x{self._uses.get(key, 0)}"
            parts.append(f"#{pos}{mark}")
        return " ".join(parts)


def load_dotenv(path: str) -> dict:
    """Minimal .env parser: KEY=VALUE lines, ignores blanks/#comments."""
    loaded: dict = {}
    try:
        # utf-8-sig tolerates a BOM left by Windows editors like Notepad.
        with open(path, "r", encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip().strip("\"'")
                if key and key not in os.environ:
                    os.environ[key] = value
                    loaded[key] = "set"
    except FileNotFoundError:
        pass
    return loaded


def ensure_dotenv_loaded() -> None:
    """Load .env from cwd, package root, or parent workspace root if not already set."""
    file_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(".env"),
        os.path.abspath(os.path.join(file_dir, "..", ".env")),
        os.path.abspath(os.path.join(file_dir, "..", "..", ".env")),
        os.path.abspath(os.path.join(file_dir, "..", "..", "microstock-metadata-generator", ".env")),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            load_dotenv(candidate)


def resolve_api_keys(key_env: str = DEFAULT_KEY_ENV) -> list[str]:
    """Search order: process env, ./.env, project-root/.env, workspace-root/.env.

    Value may hold several comma-separated keys for round-robin.
    Returns the raw list (KeyPool dedupes); raises if none found.
    """
    raw = os.environ.get(key_env, "")
    if not raw:
        ensure_dotenv_loaded()
        raw = os.environ.get(key_env, "")
        if not raw:
            raise InferenceError(
                f"API key missing: set {key_env} in the environment or in a .env "
                "file (comma-separated for several keys). "
                "See .env.example for the shape."
            )
    return [k.strip() for k in raw.split(",") if k.strip()]


def resolve_api_key(key_env: str = DEFAULT_KEY_ENV) -> str:
    """Backward-compatible single-key resolver (first healthy key)."""
    keys = [k for k in resolve_api_keys(key_env) if k]
    if not keys:
        raise InferenceError(f"API key missing: {key_env} is empty.")
    return keys[0]


def build_providers(api_cfg, timeout: int) -> list:
    """Build the ordered live-provider chain from config.

    Entries without usable keys (or with an unresolvable {account_id})
    are skipped with a warning. Flat endpoint/model/key_env act as the
    single default provider when `providers` is empty.
    Each live entry: {name, endpoint, model, pool}.
    """
    import logging

    log = logging.getLogger("microstock")
    ensure_dotenv_loaded()

    raw_entries = list(getattr(api_cfg, "providers", None) or [])
    if not raw_entries:
        cli_model = getattr(api_cfg, "cli_model", None)
        env_model = os.environ.get("MICROSTOCK_API_MODEL", "").strip()
        if cli_model:
            chosen_model = cli_model
        elif env_model and api_cfg.model == DEFAULT_MODEL:
            chosen_model = env_model
        else:
            chosen_model = api_cfg.model
        raw_entries = [{
            "name": "default",
            "endpoint": api_cfg.endpoint,
            "model": chosen_model,
            "key_env": api_cfg.key_env,
        }]
    live = []
    for idx, entry in enumerate(raw_entries):
        if not isinstance(entry, dict):
            raise InferenceError("api.providers entries must be mappings.")
        name = str(entry.get("name") or "provider")
        try:
            endpoint = str(entry.get("endpoint") or "")
            model = str(entry.get("model") or "")
            # CLI flag has top priority on primary provider (CLI > ENV > YAML).
            cli_model = getattr(api_cfg, "cli_model", None)
            if idx == 0 and cli_model:
                model = cli_model
            else:
                # model_env lets an env var override the YAML model (empty = keep YAML).
                model_env = str(entry.get("model_env") or "")
                if model_env and os.environ.get(model_env, "").strip():
                    model = os.environ[model_env].strip()
            key_env = str(entry.get("key_env") or DEFAULT_KEY_ENV)
            if not endpoint or not model:
                raise InferenceError(f"provider '{name}': endpoint/model required.")
            if "{account_id}" in endpoint:
                account_env = str(entry.get("account_env") or "")
                account_id = os.environ.get(account_env, "") if account_env else ""
                if not account_id:
                    log.warning("API provider '%s' skipped: %s not set.",
                                name, account_env or "account_env")
                    continue
                endpoint = endpoint.replace("{account_id}", account_id)
            pool = KeyPool(resolve_api_keys(key_env))
        except InferenceError as exc:
            log.warning("API provider '%s' skipped: %s", name, exc)
            continue
        live.append({"name": name, "endpoint": endpoint,
                     "model": model, "pool": pool})
    if not live:
        raise InferenceError(
            "No usable API provider: configure keys (see .env.example) "
            "for at least one entry in api.providers."
        )
    return live


def generate_with_fallback(pil_images, prompt_text: str, providers: list,
                           max_tokens: int = 768, temperature: float = 0.0,
                           timeout: int = 120) -> tuple[str, str, str]:
    """Walk providers in config order; return (text, provider, model)."""
    import logging

    log = logging.getLogger("microstock")
    last: Exception | None = None
    for provider in providers:
        try:
            text = generate_once(
                pil_images, prompt_text, provider["endpoint"], provider["model"],
                provider["pool"], max_tokens=max_tokens, temperature=temperature,
                timeout=timeout,
            )
            if provider is not providers[0]:
                log.info("API fallback answered: %s (%s)",
                         provider["name"], provider["model"])
            return text, provider["name"], provider["model"]
        except InferenceError as exc:
            log.warning("API provider '%s' failed, trying next: %s",
                        provider["name"], exc)
            last = exc
    assert last is not None
    raise last


def image_to_data_uri(pil_image) -> str:
    buf = io.BytesIO()
    image = pil_image.convert("RGB") if pil_image.mode != "RGB" else pil_image
    image.save(buf, format="JPEG", quality=85)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return "data:image/jpeg;base64," + encoded


def _parse_response_json(text: str) -> dict:
    text = text.strip()
    if not text:
        raise ValueError("Empty response body from API")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some gateways/proxies (e.g. 9router/OpenCode) append SSE tokens
        # like 'data: [DONE]' or trailing whitespace to non-streaming responses.
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(text.lstrip())
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

        # Handle SSE format if the proxy streamed response chunks
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk != "[DONE]":
                    try:
                        obj = json.loads(chunk)
                        if isinstance(obj, dict) and "choices" in obj:
                            return obj
                    except json.JSONDecodeError:
                        continue
        raise


def _post_json(url: str, payload: dict, api_key: str, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/chat/completions",
        data=data,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return _parse_response_json(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")[:300]
        except Exception:
            detail = ""
        if exc.code in (401, 403):
            raise _AuthError(
                f"API rejected the key (HTTP {exc.code}). "
                "Failing over to the next key. " + detail
            ) from exc
        if exc.code in (429, 500, 502, 503, 504):
            raise _RetryableError(f"HTTP {exc.code}: {detail}") from exc
        raise InferenceError(f"API error HTTP {exc.code}: {detail}") from exc
    except TimeoutError as exc:
        raise _RetryableError(f"API timeout: {exc}") from exc
    except OSError as exc:
        raise InferenceError(f"Cannot reach API endpoint {url}: {exc}") from exc


class _RetryableError(InferenceError):
    """Transient transport failure worth one more attempt."""


class _AuthError(InferenceError):
    """Key rejected (401/403): quarantine it and fail over, never log it."""


def generate_once(
    pil_images,
    prompt_text: str,
    endpoint: str,
    model_name: str,
    key_pool,
    max_tokens: int = 768,
    temperature: float = 0.0,
    timeout: int = 120,
    transport_retries: int = 2,
) -> str:
    """One generation call (content retries are handled by the caller).

    key_pool: KeyPool — round-robin per attempt, automatic failover to
    the next key on 401/403. Only key indexes are ever logged.
    """
    import logging

    log = logging.getLogger("microstock")
    last: Exception | None = None
    for attempt in range(transport_retries + 1):
        key_no, key = key_pool.next()
        log.debug("API attempt %d with key #%d/%d",
                  attempt + 1, key_no, len(key_pool))
        try:
            data = _post_json(endpoint, _payload(model_name, prompt_text, pil_images,
                              max_tokens, temperature), key, timeout)
            choice = data["choices"][0]
            msg = choice.get("message") or {}
            content = msg.get("content")
            if content is None:
                content = msg.get("reasoning_content") or choice.get("text") or ""
            if isinstance(content, dict):
                if "text" in content and isinstance(content["text"], str):
                    content = content["text"]
                else:
                    content = json.dumps(content)
            elif isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        parts.append(str(part["text"]))
                    elif isinstance(part, str):
                        parts.append(part)
                    else:
                        parts.append(json.dumps(part))
                content = "".join(parts)
            elif not isinstance(content, str):
                content = str(content)
            return content.strip()
        except _AuthError as exc:
            key_pool.report_bad(key)
            log.warning("API key #%d rejected, failing over: %s", key_no, exc)
            last = exc
            continue
        except _RetryableError as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            raise InferenceError(f"Unexpected API response shape: {exc}") from exc
    assert last is not None
    raise last


def _payload(model_name: str, prompt_text: str, pil_images,
             max_tokens: int, temperature: float) -> dict:
    if isinstance(pil_images, (list, tuple)):
        frames = list(pil_images)
    else:
        frames = [pil_images]
    if not frames:
        raise InferenceError("No frames to send")

    content = []
    for f in frames:
        try:
            uri = image_to_data_uri(f)
        except Exception as exc:
            raise InferenceError(f"Cannot encode frame: {exc}") from exc
        content.append({"type": "image_url", "image_url": {"url": uri}})

    content.append({"type": "text", "text": prompt_text})

    return {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": content,
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
