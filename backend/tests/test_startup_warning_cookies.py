"""Unit tests for the production-mode Secure-cookie startup warning."""
from __future__ import annotations

import logging

import pytest

from core.app_startup import _warn_if_secure_cookies_unavailable


def test_warning_emitted_when_production_lacks_tls_signal(caplog, monkeypatch):
    monkeypatch.delenv("MK_DEBUG", raising=False)
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    with caplog.at_level(logging.WARNING, logger="mediakeeper"):
        _warn_if_secure_cookies_unavailable()
    messages = [r.message for r in caplog.records]
    assert any("COOKIE_SECURE is unset" in msg for msg in messages)


def test_warning_silenced_when_cookie_secure_is_set(caplog, monkeypatch):
    monkeypatch.delenv("MK_DEBUG", raising=False)
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    with caplog.at_level(logging.WARNING, logger="mediakeeper"):
        _warn_if_secure_cookies_unavailable()
    assert not [r for r in caplog.records if "COOKIE_SECURE is unset" in r.message]


def test_warning_silenced_when_trusted_proxies_set(caplog, monkeypatch):
    monkeypatch.delenv("MK_DEBUG", raising=False)
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.setenv("TRUSTED_PROXIES", "127.0.0.1")
    with caplog.at_level(logging.WARNING, logger="mediakeeper"):
        _warn_if_secure_cookies_unavailable()
    assert not [r for r in caplog.records if "COOKIE_SECURE is unset" in r.message]


def test_warning_silenced_in_debug_mode(caplog, monkeypatch):
    monkeypatch.setenv("MK_DEBUG", "true")
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    with caplog.at_level(logging.WARNING, logger="mediakeeper"):
        _warn_if_secure_cookies_unavailable()
    assert not [r for r in caplog.records if "COOKIE_SECURE is unset" in r.message]


def test_warning_silenced_when_cookie_secure_explicitly_false(caplog, monkeypatch):
    """An operator running HTTP-only on a trusted LAN can set
    COOKIE_SECURE=false to acknowledge the trade-off and silence
    the boot warning — the warning message now points at this
    escape hatch explicitly."""
    monkeypatch.delenv("MK_DEBUG", raising=False)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    with caplog.at_level(logging.WARNING, logger="mediakeeper"):
        _warn_if_secure_cookies_unavailable()
    assert not [r for r in caplog.records if "COOKIE_SECURE is unset" in r.message]


def test_warning_text_mentions_the_escape_hatch(caplog, monkeypatch):
    """Regression guard: the message must keep telling the operator
    they can set COOKIE_SECURE=false to silence the warning on a
    deliberate HTTP-only LAN deployment, otherwise the docs and the
    runtime hint drift apart."""
    monkeypatch.delenv("MK_DEBUG", raising=False)
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    with caplog.at_level(logging.WARNING, logger="mediakeeper"):
        _warn_if_secure_cookies_unavailable()
    full_text = " ".join(r.message for r in caplog.records)
    assert "COOKIE_SECURE=false" in full_text
    assert "trusted LAN" in full_text
