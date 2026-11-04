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
    """Round-robin pool of API keys and optional account IDs.

    - next() rotates across healthy credentials.
    - report_bad(key, account_id=None) quarantines a rejected key (401/403).
    - report_quota_exhausted(account_id, key=None) quarantines an exhausted account (429/quota).
    """

    def __init__(self, keys: list[str] | list[tuple[str | None, str]]):
        import threading
        from collections import Counter

        seen: list[tuple[str | None, str]] = []
        has_accounts = False
        for item in keys or []:
            if isinstance(item, tuple):
                acc, key = item
                acc = (acc or "").strip() or None
                key = (key or "").strip().strip("\"'")
                if acc:
                    has_accounts = True
                if key and (acc, key) not in seen:
                    seen.append((acc, key))
            else:
                key = (item or "").strip().strip("\"'")
                if key and (None, key) not in seen:
                    seen.append((None, key))
        if not seen:
            raise InferenceError(
                f"API key missing: set {DEFAULT_KEY_ENV} in the environment "
                "or in a .env file (comma-separated for several keys). "
                "See .env.example for the shape."
            )
        self._items = seen
        self._keys = [k for _, k in seen]
        self._has_accounts = has_accounts
        self._bad: set[str] = set()
        self._exhausted_accounts: set[str] = set()
        self._idx = 0
        self._lock = threading.Lock()
        self._uses: Counter = Counter()

    def __len__(self) -> int:
        return len(self._items)

    def next(self) -> tuple[int, str] | tuple[int, str, str | None]:
        with self._lock:
            healthy = [
                (acc, k) for acc, k in self._items
                if k not in self._bad and (acc is None or acc not in self._exhausted_accounts)
            ]
            if not healthy:
                if self._exhausted_accounts:
                    raise InferenceError("All API accounts exceeded their quota or were rejected.")
                raise InferenceError("All API keys were rejected by the provider.")
            pick_acc, pick_key = healthy[self._idx % len(healthy)]
            self._idx += 1
            self._uses[(pick_acc, pick_key)] += 1
            pos = self._items.index((pick_acc, pick_key)) + 1
            if self._has_accounts:
                return pos, pick_key, pick_acc
            return pos, pick_key

    def report_bad(self, key: str, account_id: str | None = None) -> None:
        with self._lock:
            self._bad.add(key)

    def report_quota_exhausted(self, account_id: str | None = None, key: str | None = None) -> None:
        with self._lock:
            if account_id:
                self._exhausted_accounts.add(account_id)
            elif key:
                self._bad.add(key)

    def stats(self) -> str:
        parts = []
        for pos, (acc, key) in enumerate(self._items, 1):
            if key in self._bad:
                mark = "REJECTED"
            elif acc and acc in self._exhausted_accounts:
                mark = "QUOTA_EXHAUSTED"
            else:
                mark = f"x{self._uses.get((acc, key), 0)}"
            acc_label = f"[{acc[:6]}..]" if acc else ""
            parts.append(f"#{pos}{acc_label}{mark}")
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


def resolve_api_credentials(
    key_env: str = DEFAULT_KEY_ENV,
    account_env: str = "",
    accounts_env: str = "",
) -> list[tuple[str | None, str]]:
    """Resolve credentials as list of (account_id, api_token) pairs.

    Resolution order:
    1. accounts_env (or MICROSTOCK_CF_ACCOUNTS / MICROSTOCK_CF_CREDENTIALS):
       Formatted as comma-separated pairs: 'acc1:tok1,acc2:tok2'
    2. Parallel environment variables:
       account_env: 'acc1,acc2'
       key_env: 'tok1,tok2'
    3. Single account with comma-separated keys:
       account_env: 'acc1'
       key_env: 'tok1,tok2' -> [('acc1', 'tok1'), ('acc1', 'tok2')]
    4. Key-only (for providers without accounts, e.g. local gateway):
       key_env: 'tok1,tok2' -> [(None, 'tok1'), (None, 'tok2')]
    """
    ensure_dotenv_loaded()

    # 1. Check explicit combined accounts_env or global multi-account env
    comb_candidates = [accounts_env] if accounts_env else ["MICROSTOCK_CF_ACCOUNTS", "MICROSTOCK_CF_CREDENTIALS"]
    for env_name in comb_candidates:
        if env_name and os.environ.get(env_name, "").strip():
            raw_comb = os.environ[env_name].strip()
            pairs: list[tuple[str | None, str]] = []
            for item in raw_comb.split(","):
                item = item.strip().strip("\"'")
                if not item:
                    continue
                if ":" in item:
                    acc, tok = item.split(":", 1)
                    pairs.append((acc.strip(), tok.strip()))
                else:
                    pairs.append((None, item.strip()))
            if pairs:
                return pairs

    # 2. Check parallel / separate account_env and key_env
    acc_raw = os.environ.get(account_env, "").strip() if account_env else ""
    key_raw = os.environ.get(key_env, "").strip()
    if not key_raw:
        ensure_dotenv_loaded()
        key_raw = os.environ.get(key_env, "").strip()

    accounts = [a.strip().strip("\"'") for a in acc_raw.split(",") if a.strip().strip("\"'")]
    keys = [k.strip().strip("\"'") for k in key_raw.split(",") if k.strip().strip("\"'")]

    if not keys:
        raise InferenceError(
            f"API key missing: set {key_env} in the environment or in a .env "
            "file (comma-separated for several keys). "
            "See .env.example for the shape."
        )

    if not accounts:
        return [(None, k) for k in keys]

    if len(accounts) == 1:
        return [(accounts[0], k) for k in keys]

    if len(accounts) == len(keys):
        return list(zip(accounts, keys))

    if len(keys) == 1:
        return [(acc, keys[0]) for acc in accounts]

    raise InferenceError(
        f"Mismatched account/key count in {account_env} ({len(accounts)}) "
        f"and {key_env} ({len(keys)}). Provide equal counts or use 'acc1:tok1,acc2:tok2' format."
    )


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
            account_env = str(entry.get("account_env") or "")
            accounts_env = str(entry.get("accounts_env") or "")

            if not endpoint or not model:
                raise InferenceError(f"provider '{name}': endpoint/model required.")

            credentials = resolve_api_credentials(key_env, account_env, accounts_env)
            if "{account_id}" in endpoint:
                accounts = [acc for acc, _ in credentials if acc]
                if not accounts:
                    log.warning("API provider '%s' skipped: %s not set.",
                                name, account_env or "account_env")
                    continue
                unique_accounts = list(dict.fromkeys(accounts))
                if len(unique_accounts) == 1:
                    endpoint = endpoint.replace("{account_id}", unique_accounts[0])

            pool = KeyPool(credentials)
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
        if exc.code == 429 or (exc.code == 400 and any(w in detail.lower() for w in ("quota", "exceeded", "daily", "neuron"))):
            if any(w in detail.lower() for w in ("quota", "exceeded", "daily", "neuron")):
                raise _QuotaExceededError(f"API daily quota exceeded (HTTP {exc.code}): {detail}") from exc
            raise _RetryableError(f"HTTP {exc.code}: {detail}") from exc
        if exc.code in (500, 502, 503, 504):
            raise _RetryableError(f"HTTP {exc.code}: {detail}") from exc
        raise InferenceError(f"API error HTTP {exc.code}: {detail}") from exc
    except TimeoutError as exc:
        raise _RetryableError(f"API timeout: {exc}") from exc
    except OSError as exc:
        raise InferenceError(f"Cannot reach API endpoint {url}: {exc}") from exc


class _RetryableError(InferenceError):
    """Transient transport failure worth one more attempt."""


class _QuotaExceededError(InferenceError):
    """Account quota exhausted (HTTP 429 or daily neurons limit exceeded)."""


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
    the next key on 401/403 or quota exhausted (429). Only key indexes are ever logged.
    """
    import logging

    log = logging.getLogger("microstock")
    last: Exception | None = None
    max_attempts = max(transport_retries + 1, len(key_pool))
    for attempt in range(max_attempts):
        next_item = key_pool.next()
        if len(next_item) >= 3:
            key_no, key, account_id = next_item[0], next_item[1], next_item[2]
        else:
            key_no, key, account_id = next_item[0], next_item[1], None

        req_endpoint = endpoint
        if "{account_id}" in req_endpoint and account_id:
            req_endpoint = req_endpoint.replace("{account_id}", account_id)

        log.debug("API attempt %d with key #%d/%d (account %s)",
                  attempt + 1, key_no, len(key_pool), account_id or "default")
        try:
            data = _post_json(req_endpoint, _payload(model_name, prompt_text, pil_images,
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
            key_pool.report_bad(key, account_id)
            log.warning("API key #%d rejected, failing over: %s", key_no, exc)
            last = exc
            continue
        except _QuotaExceededError as exc:
            key_pool.report_quota_exhausted(account_id, key)
            log.warning("API quota exceeded on account %s (key #%d), rotating: %s",
                        account_id or "default", key_no, exc)
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
