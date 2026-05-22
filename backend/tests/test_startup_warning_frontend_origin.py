"""Unit tests for the FRONTEND_ORIGIN startup warning in proxy mode.

CSRF tolerates an empty ``FRONTEND_ORIGIN`` by auto-deriving the
expected Origin from a trusted ``X-Forwarded-Host``, but
CORSMiddleware does not — so a Mode B deployment that forgets to set
``FRONTEND_ORIGIN`` will silently break browser preflights from the
public hostname. Surface that misconfiguration once at boot rather than
let it manifest as a vague CORS error in the browser console.
"""
from __future__ import annotations

import logging

from core.app_startup import _warn_if_frontend_origin_missing_in_proxy_mode


def test_warning_emitted_when_proxy_mode_lacks_frontend_origin(caplog, monkeypatch):
    monkeypatch.delenv("MK_DEBUG", raising=False)
    monkeypatch.setenv("TRUSTED_PROXIES", "192.0.2.10")
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    with caplog.at_level(logging.WARNING, logger="mediakeeper"):
        _warn_if_frontend_origin_missing_in_proxy_mode()
    assert any(
        "FRONTEND_ORIGIN is unset" in r.message for r in caplog.records
    )


def test_warning_silenced_when_frontend_origin_set(caplog, monkeypatch):
    monkeypatch.delenv("MK_DEBUG", raising=False)
    monkeypatch.setenv("TRUSTED_PROXIES", "192.0.2.10")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://your-domain.example.com")
    with caplog.at_level(logging.WARNING, logger="mediakeeper"):
        _warn_if_frontend_origin_missing_in_proxy_mode()
    assert not [
        r for r in caplog.records if "FRONTEND_ORIGIN is unset" in r.message
    ]


def test_warning_silenced_in_direct_lan_mode(caplog, monkeypatch):
    monkeypatch.delenv("MK_DEBUG", raising=False)
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    with caplog.at_level(logging.WARNING, logger="mediakeeper"):
        _warn_if_frontend_origin_missing_in_proxy_mode()
    assert not [
        r for r in caplog.records if "FRONTEND_ORIGIN is unset" in r.message
    ]


def test_warning_silenced_in_debug_mode(caplog, monkeypatch):
    monkeypatch.setenv("MK_DEBUG", "true")
    monkeypatch.setenv("TRUSTED_PROXIES", "192.0.2.10")
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    with caplog.at_level(logging.WARNING, logger="mediakeeper"):
        _warn_if_frontend_origin_missing_in_proxy_mode()
    assert not [
        r for r in caplog.records if "FRONTEND_ORIGIN is unset" in r.message
    ]
