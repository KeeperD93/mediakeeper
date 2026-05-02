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
