"""Integration tests for Discord webhook delivery (signature + retry + log)."""
import json
import logging
from unittest.mock import AsyncMock, patch

import pytest

from core import webhooks
from services.discord.send import send_discord_webhook, send_discord_test


VALID_DISCORD_URL = "https://discord.com/api/webhooks/123456789012345678/secret"


class _FakeResponse:
    def __init__(self, status_code: int, headers: dict | None = None, text: str = ""):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text


@pytest.fixture(autouse=True)
def _isolate_signing_cache():
    webhooks.reset_signing_key_cache()
    yield
    webhooks.reset_signing_key_cache()


def _make_post_mock(responses):
    """Build a mock ``client.post`` that returns ``responses`` in order."""
    iterator = iter(responses)
    captured: list[dict] = []

    async def post(url, *, content, headers, timeout):
        captured.append({
            "url": url,
            "content": content,
            "headers": dict(headers),
            "timeout": timeout,
        })
        return next(iterator)

    return post, captured


@pytest.mark.asyncio
async def test_send_discord_webhook_attaches_signature_header(monkeypatch):
    post_mock, captured = _make_post_mock([_FakeResponse(204)])
    fake_client = AsyncMock()
    fake_client.post = post_mock

    with patch(
        "services.discord.send.get_external_client", return_value=fake_client
    ):
        ok = await send_discord_webhook(
            VALID_DISCORD_URL, {"content": "hello"}
        )

    assert ok is True
    assert len(captured) == 1
    sig = captured[0]["headers"][webhooks.SIGNATURE_HEADER_NAME]
    assert sig.startswith("sha256=") and len(sig.split("=", 1)[1]) == 64
    # Signature must be over the exact bytes we sent.
    assert webhooks.sign_webhook_payload(captured[0]["content"]) == sig


@pytest.mark.asyncio
async def test_send_discord_webhook_retries_once_on_429(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr("asyncio.sleep", fake_sleep)
    post_mock, captured = _make_post_mock(
        [_FakeResponse(429, {"Retry-After": "2"}), _FakeResponse(204)]
    )
    fake_client = AsyncMock()
    fake_client.post = post_mock

    with patch(
        "services.discord.send.get_external_client", return_value=fake_client
    ):
        ok = await send_discord_webhook(VALID_DISCORD_URL, {"content": "hi"})

    assert ok is True
    assert len(captured) == 2
    assert sleeps == [2.0]


@pytest.mark.asyncio
async def test_send_discord_webhook_logs_log_id_not_url_on_failure(monkeypatch, caplog):
    async def fake_sleep(_delay):
        return None

    monkeypatch.setattr("asyncio.sleep", fake_sleep)
    post_mock, _ = _make_post_mock(
        [_FakeResponse(429, {"Retry-After": "1"}), _FakeResponse(429, {"Retry-After": "1"})]
    )
    fake_client = AsyncMock()
    fake_client.post = post_mock

    with patch(
        "services.discord.send.get_external_client", return_value=fake_client
    ):
        with caplog.at_level(logging.WARNING, logger="mediakeeper.notifications.discord"):
            ok = await send_discord_webhook(VALID_DISCORD_URL, {"content": "x"})

    assert ok is False
    matching = [r for r in caplog.records if "rejected delivery" in r.message]
    assert matching, "expected a structured WARN log on final failure"
    rendered = "\n".join(r.getMessage() for r in matching)
    assert "discord:123456789012345678" in rendered
    assert "secret" not in rendered  # raw token must never reach the log
    assert VALID_DISCORD_URL not in rendered


@pytest.mark.asyncio
async def test_send_discord_webhook_swallows_exception_without_url_leak(
    monkeypatch, caplog
):
    class _Boom(Exception):
        def __str__(self):
            return f"connect error to {VALID_DISCORD_URL}"

    async def _raise(*_args, **_kwargs):
        raise _Boom("network gone")

    fake_client = AsyncMock()
    fake_client.post = _raise

    with patch(
        "services.discord.send.get_external_client", return_value=fake_client
    ):
        with caplog.at_level(logging.WARNING, logger="mediakeeper.notifications.discord"):
            ok = await send_discord_webhook(VALID_DISCORD_URL, {"content": "x"})

    assert ok is False
    rendered = "\n".join(r.getMessage() for r in caplog.records)
    # The exception's ``__str__`` includes the URL; the log must NOT.
    assert VALID_DISCORD_URL not in rendered
    assert "discord:123456789012345678" in rendered


@pytest.mark.asyncio
async def test_send_discord_webhook_returns_false_on_empty_url():
    ok = await send_discord_webhook("", {"content": "x"})
    assert ok is False


@pytest.mark.asyncio
async def test_send_discord_webhook_serialises_body_deterministically():
    """Signature and body must agree on bytes — separators=,: compact form."""
    captured = {}

    async def post(url, *, content, headers, timeout):
        captured["content"] = content
        captured["headers"] = dict(headers)
        return _FakeResponse(204)

    fake_client = AsyncMock()
    fake_client.post = post

    payload = {"content": "ok", "embeds": [{"title": "t"}]}
    with patch(
        "services.discord.send.get_external_client", return_value=fake_client
    ):
        await send_discord_webhook(VALID_DISCORD_URL, payload)

    expected = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    assert captured["content"] == expected


@pytest.mark.asyncio
async def test_send_discord_test_rejects_invalid_url():
    res = await send_discord_test("https://example.invalid/x", test_type="movie")
    assert res == {"error": "Invalid Discord webhook URL."}


@pytest.mark.asyncio
async def test_send_discord_test_signs_payload(monkeypatch):
    post_mock, captured = _make_post_mock([_FakeResponse(204)])
    fake_client = AsyncMock()
    fake_client.post = post_mock

    with patch(
        "services.discord.send.get_external_client", return_value=fake_client
    ):
        res = await send_discord_test(VALID_DISCORD_URL, test_type="movie")

    assert res == {"success": True}
    assert captured[0]["headers"][webhooks.SIGNATURE_HEADER_NAME].startswith(
        "sha256="
    )


@pytest.mark.asyncio
async def test_send_discord_test_resolves_instance_default_lang(monkeypatch):
    """With no per-call lang, the test message language follows the instance
    default (like real notifications), not the admin's UI locale or 'fr'."""
    post_mock, _ = _make_post_mock([_FakeResponse(204)])
    fake_client = AsyncMock()
    fake_client.post = post_mock
    captured_lang = {}

    def _fake_templates(lang):
        captured_lang["lang"] = lang
        return {"added_movie": "sample"}

    with patch("services.discord.send.get_external_client", return_value=fake_client), \
         patch("services.discord.send._resolve_system_lang", new=AsyncMock(return_value="en")), \
         patch("services.discord.send.get_default_templates", side_effect=_fake_templates):
        res = await send_discord_test(VALID_DISCORD_URL, wh_config={}, test_type="movie", db=object())

    assert res == {"success": True}
    assert captured_lang["lang"] == "en"
