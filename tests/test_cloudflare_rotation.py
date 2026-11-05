"""Unit tests for Cloudflare Workers AI multi-account, key rotation, and quota circuit breaker."""

import io
import json
import urllib.error
import pytest
from PIL import Image

from microstock.metadata import api_inference as api
from microstock.metadata.exceptions import InferenceError


def _dummy_image():
    return Image.new("RGB", (64, 48), (1, 2, 3))


class DummyResponse:
    def __init__(self, data: bytes):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._data


def test_resolve_credentials_single(monkeypatch):
    monkeypatch.setattr(api, "ensure_dotenv_loaded", lambda: None)
    monkeypatch.delenv("MICROSTOCK_CF_ACCOUNTS", raising=False)
    monkeypatch.delenv("MICROSTOCK_CF_CREDENTIALS", raising=False)
    monkeypatch.setenv("TEST_ACC", "acc_alpha")
    monkeypatch.setenv("TEST_KEY", "tok_alpha")
    creds = api.resolve_api_credentials(key_env="TEST_KEY", account_env="TEST_ACC")
    assert creds == [("acc_alpha", "tok_alpha")]


def test_resolve_credentials_parallel_lists(monkeypatch):
    monkeypatch.setattr(api, "ensure_dotenv_loaded", lambda: None)
    monkeypatch.delenv("MICROSTOCK_CF_ACCOUNTS", raising=False)
    monkeypatch.delenv("MICROSTOCK_CF_CREDENTIALS", raising=False)
    monkeypatch.setenv("TEST_ACC", "acc_1, acc_2, acc_3")
    monkeypatch.setenv("TEST_KEY", "tok_1, tok_2, tok_3")
    creds = api.resolve_api_credentials(key_env="TEST_KEY", account_env="TEST_ACC")
    assert creds == [
        ("acc_1", "tok_1"),
        ("acc_2", "tok_2"),
        ("acc_3", "tok_3"),
    ]


def test_resolve_credentials_explicit_pairs(monkeypatch):
    monkeypatch.setenv("MICROSTOCK_CF_ACCOUNTS", "acc_x:tok_x, acc_y:tok_y")
    creds = api.resolve_api_credentials(key_env="ANY_KEY", account_env="ANY_ACC")
    assert creds == [
        ("acc_x", "tok_x"),
        ("acc_y", "tok_y"),
    ]


def test_key_pool_rotation_and_accounts():
    pool = api.KeyPool([("acc1", "tok1"), ("acc2", "tok2")])
    assert len(pool) == 2

    # Round robin
    p1, k1, a1 = pool.next()
    assert (p1, k1, a1) == (1, "tok1", "acc1")

    p2, k2, a2 = pool.next()
    assert (p2, k2, a2) == (2, "tok2", "acc2")

    p3, k3, a3 = pool.next()
    assert (p3, k3, a3) == (1, "tok1", "acc1")


def test_key_pool_quota_circuit_breaker():
    pool = api.KeyPool([("acc1", "tok1"), ("acc2", "tok2")])

    # Mark acc1 as quota exhausted
    pool.report_quota_exhausted("acc1")

    # Subsequent calls should strictly use acc2
    for _ in range(3):
        pos, key, acc = pool.next()
        assert acc == "acc2"
        assert key == "tok2"

    assert "QUOTA_EXHAUSTED" in pool.stats()

    # If acc2 also exhausted -> raises InferenceError
    pool.report_quota_exhausted("acc2")
    with pytest.raises(InferenceError, match="All API accounts exceeded their quota"):
        pool.next()


def test_generate_once_dynamic_url_rotation(monkeypatch):
    calls = []

    def _fake_urlopen(req, timeout=None):
        calls.append({
            "url": req.full_url,
            "auth": req.get_header("Authorization"),
        })
        resp_data = {"choices": [{"message": {"content": '{"title": "Test Title"}'}}]}
        return DummyResponse(json.dumps(resp_data).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    pool = api.KeyPool([("acc_001", "key_001"), ("acc_002", "key_002")])
    template_endpoint = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"

    # Request 1 -> acc_001
    text1 = api.generate_once(_dummy_image(), "prompt", template_endpoint, "@cf/model", pool)
    assert '{"title": "Test Title"}' in text1
    assert calls[0]["url"] == "https://api.cloudflare.com/client/v4/accounts/acc_001/ai/v1/chat/completions"
    assert calls[0]["auth"] == "Bearer key_001"

    # Request 2 -> acc_002
    text2 = api.generate_once(_dummy_image(), "prompt", template_endpoint, "@cf/model", pool)
    assert '{"title": "Test Title"}' in text2
    assert calls[1]["url"] == "https://api.cloudflare.com/client/v4/accounts/acc_002/ai/v1/chat/completions"
    assert calls[1]["auth"] == "Bearer key_002"


def test_generate_once_immediate_failover_on_quota_429(monkeypatch):
    calls = []

    def _fake_urlopen(req, timeout=None):
        calls.append(req.full_url)
        # acc_primary throws HTTP 429 daily quota
        if "acc_primary" in req.full_url:
            err_body = b'{"errors": [{"code": 10014, "message": "You have exceeded your daily quota"}]}'
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, io.BytesIO(err_body))

        resp_data = {"choices": [{"message": {"content": '{"title": "Success Backup"}'}}]}
        return DummyResponse(json.dumps(resp_data).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    monkeypatch.setattr(api.time, "sleep", lambda s: None)

    pool = api.KeyPool([("acc_primary", "tok_primary"), ("acc_backup", "tok_backup")])
    template_endpoint = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"

    # Should try acc_primary, get 429 quota exhausted, quarantine it, and immediately succeed on acc_backup
    text = api.generate_once(_dummy_image(), "prompt", template_endpoint, "@cf/model", pool)
    assert '{"title": "Success Backup"}' in text
    assert len(calls) == 2
    assert "acc_primary" in calls[0]
    assert "acc_backup" in calls[1]

    # In next generation call, acc_primary is quarantined, so it goes straight to acc_backup
    calls.clear()
    text2 = api.generate_once(_dummy_image(), "prompt", template_endpoint, "@cf/model", pool)
    assert '{"title": "Success Backup"}' in text2
    assert len(calls) == 1
    assert "acc_backup" in calls[0]
