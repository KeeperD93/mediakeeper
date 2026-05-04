"""Unit tests for the outbound-webhook helpers in :mod:`core.webhooks`."""
import hashlib
import hmac

import pytest

from core import webhooks


@pytest.fixture(autouse=True)
def _isolate_signing_cache():
    """Each test gets a fresh derived key — no leakage across cases."""
    webhooks.reset_signing_key_cache()
    yield
    webhooks.reset_signing_key_cache()


# --- sign_webhook_payload ---------------------------------------------------

def test_signature_is_sha256_prefixed_hex():
    sig = webhooks.sign_webhook_payload(b"{}")
    assert sig.startswith("sha256=")
    digest_hex = sig.split("=", 1)[1]
    assert len(digest_hex) == 64
    int(digest_hex, 16)  # must be valid hex


def test_signature_is_deterministic_for_same_body():
    body = b'{"hello":"world"}'
    assert webhooks.sign_webhook_payload(body) == webhooks.sign_webhook_payload(body)


def test_signature_differs_for_different_body():
    a = webhooks.sign_webhook_payload(b'{"a":1}')
    b = webhooks.sign_webhook_payload(b'{"a":2}')
    assert a != b


def test_signature_uses_derived_key_not_master(monkeypatch):
    """Header digest must not be a raw HMAC of the Fernet key over the body."""
    fake_master = b"a" * 44
    monkeypatch.setattr(webhooks, "_master_key_bytes", lambda: fake_master)
    webhooks._signing_key.cache_clear()

    body = b'{"x":1}'
    raw = hmac.new(fake_master, body, hashlib.sha256).hexdigest()
    derived = webhooks.sign_webhook_payload(body).split("=", 1)[1]
    assert derived != raw  # the helper applies a domain-separation step


# --- webhook_log_id ---------------------------------------------------------

def test_log_id_extracts_discord_numeric_id():
    url = "https://discord.com/api/webhooks/123456789012345678/secrettoken"
    assert webhooks.webhook_log_id(url) == "discord:123456789012345678"


def test_log_id_hashes_external_url_without_leaking_token():
    url = "https://example.invalid/webhooks/abcdef/SECRET-TOKEN"
    log_id = webhooks.webhook_log_id(url)
    assert log_id.startswith("external:")
    assert "SECRET-TOKEN" not in log_id
    assert len(log_id.split(":", 1)[1]) == 8  # 8 hex chars


def test_log_id_handles_empty_url():
    assert webhooks.webhook_log_id("") == "external:unset"


def test_log_id_does_not_emit_token_for_discord_url():
    url = "https://discord.com/api/webhooks/42/super-secret-token-value"
    log_id = webhooks.webhook_log_id(url)
    assert "super-secret-token-value" not in log_id


# --- parse_retry_after_header ----------------------------------------------

def test_retry_after_parses_seconds():
    assert webhooks.parse_retry_after_header("2") == 2.0


def test_retry_after_caps_at_five_seconds():
    assert webhooks.parse_retry_after_header("60") == webhooks.RETRY_AFTER_CAP_SECONDS


def test_retry_after_handles_floats():
    assert webhooks.parse_retry_after_header("0.5") == 0.5


def test_retry_after_clamps_negative_to_zero():
    assert webhooks.parse_retry_after_header("-3") == 0.0


def test_retry_after_falls_back_when_missing():
    assert webhooks.parse_retry_after_header(None) == webhooks.RETRY_AFTER_DEFAULT_SECONDS
    assert webhooks.parse_retry_after_header("") == webhooks.RETRY_AFTER_DEFAULT_SECONDS


def test_retry_after_falls_back_when_unparseable():
    assert webhooks.parse_retry_after_header("Tue, 03 Jun 2026 04:00:00 GMT") == (
        webhooks.RETRY_AFTER_DEFAULT_SECONDS
    )


# --- post_signed_with_retry ------------------------------------------------

class _FakeResponse:
    def __init__(self, status_code: int, headers: dict | None = None):
        self.status_code = status_code
        self.headers = headers or {}


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def post(self, url, *, content, headers, timeout):
        self.calls.append({
            "url": url,
            "content": content,
            "headers": dict(headers),
            "timeout": timeout,
        })
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_post_signed_with_retry_no_429_no_retry(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", _async_noop_sleep)
    client = _FakeClient([_FakeResponse(204)])
    res = await webhooks.post_signed_with_retry(
        client, "https://discord.com/api/webhooks/1/x", {"content": "ok"},
        timeout=10.0,
    )
    assert res.status_code == 204
    assert len(client.calls) == 1
    assert client.calls[0]["headers"][webhooks.SIGNATURE_HEADER_NAME].startswith(
        "sha256="
    )
    assert client.calls[0]["headers"]["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_post_signed_with_retry_replays_once_on_429(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr("asyncio.sleep", fake_sleep)
    client = _FakeClient(
        [_FakeResponse(429, {"Retry-After": "2"}), _FakeResponse(204)]
    )
    res = await webhooks.post_signed_with_retry(
        client, "https://discord.com/api/webhooks/1/x", {"content": "ok"},
        timeout=10.0,
    )
    assert res.status_code == 204
    assert len(client.calls) == 2
    assert sleeps == [2.0]


@pytest.mark.asyncio
async def test_post_signed_with_retry_does_not_loop_after_second_429(monkeypatch):
    async def fake_sleep(_delay):
        return None

    monkeypatch.setattr("asyncio.sleep", fake_sleep)
    client = _FakeClient(
        [_FakeResponse(429, {"Retry-After": "1"}), _FakeResponse(429, {"Retry-After": "1"})]
    )
    res = await webhooks.post_signed_with_retry(
        client, "https://discord.com/api/webhooks/1/x", {"content": "ok"},
        timeout=10.0,
    )
    assert res.status_code == 429
    assert len(client.calls) == 2  # first + one retry only


@pytest.mark.asyncio
async def test_post_signed_with_retry_caps_retry_after(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr("asyncio.sleep", fake_sleep)
    client = _FakeClient(
        [_FakeResponse(429, {"Retry-After": "120"}), _FakeResponse(204)]
    )
    await webhooks.post_signed_with_retry(
        client, "https://discord.com/api/webhooks/1/x", {"content": "ok"},
        timeout=10.0,
    )
    assert sleeps == [webhooks.RETRY_AFTER_CAP_SECONDS]


async def _async_noop_sleep(_delay):
    return None
