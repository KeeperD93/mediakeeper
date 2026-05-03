"""Mode A vs Mode B handshake gate on the chat WebSocket.

These tests exercise ``_origin_is_allowed`` directly with synthetic
WebSocket-shaped objects so we don't have to spin up a real WS server.
The behaviour we pin:

* Operator allowlist (``FRONTEND_ORIGIN`` env CSV) keeps strict mode.
* Auto-derive fallback (``FRONTEND_ORIGIN`` empty) compares the
  browser-supplied Origin against the canonical origin computed from
  the WS scope. Mode A uses the ``Host`` header; Mode B uses
  ``X-Forwarded-Host`` only when the direct TCP client matches a
  network in ``TRUSTED_PROXIES``.
* The auto-derive WARN line is emitted once per process so logs do
  not get spammed by every handshake.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import api.portal.chat as chat_module


class _FakeWebSocket:
    """Minimal WebSocket double exposing the bits ``_origin_is_allowed``
    and ``websocket_canonical_origin`` care about — ``headers`` (a
    dict-like) and ``scope`` (an ASGI-style mapping)."""

    def __init__(self, *, host: str, scheme: str = "ws", client_host: str = "10.0.0.5",
                 forwarded_host: str | None = None, forwarded_proto: str | None = None):
        headers: dict[str, str] = {"host": host}
        if forwarded_host:
            headers["x-forwarded-host"] = forwarded_host
        if forwarded_proto:
            headers["x-forwarded-proto"] = forwarded_proto
        self.headers = headers
        self.scope = {
            "scheme": scheme,
            "client": (client_host, 51234),
            "server": (host, 80),
        }


@pytest.fixture(autouse=True)
def _reset_warning_flag():
    """Each test starts with a fresh "warning not yet emitted" state so
    the rate-limit assertion is independent."""
    chat_module._AUTO_DERIVE_WARNING_LOGGED = False
    yield
    chat_module._AUTO_DERIVE_WARNING_LOGGED = False


@pytest.fixture(autouse=True)
def _isolate_trusted_proxies(monkeypatch):
    """Each test scopes its own TRUSTED_PROXIES so Mode B cases are
    deterministic regardless of the surrounding env."""
    import core.csrf_helpers as helpers
    import core.proxy as proxy_mod
    monkeypatch.setattr(helpers, "TRUSTED_PROXIES", [])
    monkeypatch.setattr(proxy_mod, "TRUSTED_PROXIES", [])
    yield


def _set_trusted_proxies(monkeypatch, networks):
    import ipaddress
    import core.csrf_helpers as helpers
    import core.proxy as proxy_mod
    parsed = [ipaddress.ip_network(n, strict=False) for n in networks]
    monkeypatch.setattr(helpers, "TRUSTED_PROXIES", parsed)
    monkeypatch.setattr(proxy_mod, "TRUSTED_PROXIES", parsed)


def test_mode_a_same_origin_handshake_is_allowed(monkeypatch):
    """Direct LAN, no proxy. Browser Origin matches the Host header so
    the handshake is accepted under the auto-derive path."""
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    ws = _FakeWebSocket(host="mediakeeper.lan", scheme="ws")
    assert chat_module._origin_is_allowed("http://mediakeeper.lan", websocket=ws) is True


def test_mode_a_cross_origin_handshake_is_rejected(monkeypatch):
    """Same Mode A scope but with a foreign Origin header. Refused."""
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    ws = _FakeWebSocket(host="mediakeeper.lan", scheme="ws")
    assert chat_module._origin_is_allowed("https://evil.example", websocket=ws) is False


def test_mode_b_handshake_through_trusted_proxy_is_allowed(monkeypatch):
    """Reverse proxy in TRUSTED_PROXIES forwards X-Forwarded-Host. The
    canonical origin is derived from the forwarded value, not from the
    LAN-internal Host the proxy presents to MediaKeeper."""
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    _set_trusted_proxies(monkeypatch, ["192.0.2.0/24"])
    ws = _FakeWebSocket(
        host="internal.lan",
        scheme="ws",
        client_host="192.0.2.7",
        forwarded_host="public.example",
        forwarded_proto="https",
    )
    assert chat_module._origin_is_allowed("https://public.example", websocket=ws) is True


def test_mode_b_handshake_from_untrusted_source_is_rejected(monkeypatch):
    """A direct attacker that injects X-Forwarded-Host without sitting
    behind a trusted proxy must NOT see the forwarded value honoured —
    falls back to Host header which does not match."""
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    _set_trusted_proxies(monkeypatch, ["192.0.2.0/24"])
    ws = _FakeWebSocket(
        host="internal.lan",
        scheme="ws",
        client_host="203.0.113.9",       # not in TRUSTED_PROXIES
        forwarded_host="public.example",
        forwarded_proto="https",
    )
    # Origin claims to be public.example but Host says internal.lan, so
    # auto-derive resolves to internal.lan and the handshake is denied.
    assert chat_module._origin_is_allowed("https://public.example", websocket=ws) is False


def test_auto_derive_warning_logged_once(monkeypatch, caplog):
    """The hint line fires once per process to avoid log spam. Two
    successful auto-derive handshakes share the same WARN entry."""
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    ws = _FakeWebSocket(host="mediakeeper.lan", scheme="ws")
    with caplog.at_level("WARNING", logger="mediakeeper.portal.chat"):
        chat_module._origin_is_allowed("http://mediakeeper.lan", websocket=ws)
        chat_module._origin_is_allowed("http://mediakeeper.lan", websocket=ws)
    matching = [r for r in caplog.records if "FRONTEND_ORIGIN is not set" in r.message]
    assert len(matching) == 1, f"expected one WARN record, got {[r.message for r in matching]}"


def test_explicit_allowlist_keeps_strict_mode(monkeypatch, caplog):
    """When FRONTEND_ORIGIN is set, foreign origins are rejected even if
    they would have matched via Host fallback. The WARN line stays
    silent."""
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://public.example")
    ws = _FakeWebSocket(host="public.example", scheme="ws")
    with caplog.at_level("WARNING", logger="mediakeeper.portal.chat"):
        assert chat_module._origin_is_allowed("https://public.example", websocket=ws) is True
        assert chat_module._origin_is_allowed("https://evil.example", websocket=ws) is False
    auto_warns = [r for r in caplog.records if "FRONTEND_ORIGIN is not set" in r.message]
    assert auto_warns == []
