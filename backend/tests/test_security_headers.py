"""Smoke tests for the SecurityHeadersMiddleware shipped headers."""
from __future__ import annotations

import os

import pytest


@pytest.mark.asyncio
async def test_health_endpoint_carries_security_headers(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    headers = r.headers

    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in headers["Permissions-Policy"]
    assert "geolocation=()" in headers["Permissions-Policy"]


@pytest.mark.asyncio
async def test_csp_directive_present_in_enforce_mode(client, monkeypatch):
    # Default enforce mode shipped: header name is Content-Security-Policy.
    r = await client.get("/api/health")
    csp = r.headers.get("Content-Security-Policy") or r.headers.get(
        "Content-Security-Policy-Report-Only"
    )
    assert csp is not None
    assert "default-src 'self'" in csp
    # vue-i18n compiles message templates at runtime via new Function() —
    # 'unsafe-eval' must stay until messages are pre-compiled at build time.
    assert "script-src 'self' 'unsafe-eval'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "https://image.tmdb.org" in csp
    assert "https://fonts.googleapis.com" in csp


@pytest.mark.asyncio
async def test_csp_includes_frame_src_youtube_and_vimeo(client):
    """Trailer iframes embed YouTube and Vimeo players. Without an
    explicit ``frame-src`` whitelist they'd fall back to ``default-src
    'self'`` and be blocked under enforce mode."""
    r = await client.get("/api/health")
    csp = r.headers.get("Content-Security-Policy") or ""
    assert "frame-src" in csp
    assert "https://www.youtube-nocookie.com" in csp
    assert "https://player.vimeo.com" in csp


@pytest.mark.asyncio
async def test_csp_allows_youtube_iframe_api_loader_only_in_script_src(client):
    """The IFrame API script ships from ``youtube.com``; the embedded
    iframe still targets ``youtube-nocookie.com``. ``script-src`` and
    ``frame-src`` must reflect that split — no trailing ``youtube.com``
    on ``frame-src`` and no missing loader origin on ``script-src``."""
    r = await client.get("/api/health")
    csp = r.headers.get("Content-Security-Policy") or ""

    # Walk each directive so we can assert per-directive sources without
    # accidentally matching the youtube.com prefix on youtube-nocookie.com.
    directives = {}
    for chunk in csp.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        name, _, sources = chunk.partition(" ")
        directives[name] = sources.split()

    assert "https://www.youtube.com" in directives["script-src"]
    assert "https://www.youtube-nocookie.com" in directives["frame-src"]
    assert "https://www.youtube.com" not in directives["frame-src"]


@pytest.mark.asyncio
async def test_csp_object_src_none(client):
    """``object-src 'none'`` blocks legacy ``<object>`` / ``<embed>``
    plugin loaders MediaKeeper never uses."""
    r = await client.get("/api/health")
    csp = r.headers.get("Content-Security-Policy") or ""
    assert "object-src 'none'" in csp


@pytest.mark.asyncio
async def test_hsts_absent_on_plain_http_request(client):
    # The test transport speaks plain HTTP; HSTS must NOT be emitted.
    r = await client.get("/api/health")
    assert "Strict-Transport-Security" not in r.headers


@pytest.mark.asyncio
async def test_security_headers_present_on_login_endpoint(client):
    r = await client.post("/api/auth/login", json={"username": "x", "password": "y"})
    # We don't care if login succeeds — we care that the headers ride along
    # on the error response too (defence-in-depth on every response).
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
