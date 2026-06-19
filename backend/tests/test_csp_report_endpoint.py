"""Coverage for the CSP exhaustive whitelist + report endpoint.

Three contracts:

* The CSP header carries every third-party host the codebase relies on.
  Adding a new host to ``CSP_DIRECTIVES`` without updating this list
  will surface in code review here.
* ``/api/csp-violation-report`` accepts both the legacy
  ``application/csp-report`` shape and the modern
  ``application/reports+json`` Reporting API payload, returning 204.
* The same endpoint is rate-limited at 60/min/IP so a broken
  extension cannot flood the log pipeline.
"""
from __future__ import annotations

import logging

import pytest


_EXPECTED_DOMAINS = [
    # script-src
    ("script-src", "https://www.youtube.com"),
    # style-src
    ("style-src", "https://fonts.googleapis.com"),
    # font-src
    ("font-src", "https://fonts.gstatic.com"),
    # img-src — TMDB posters, Imgur uploads, YouTube thumbnails.
    ("img-src", "https://image.tmdb.org"),
    ("img-src", "https://i.imgur.com"),
    ("img-src", "https://img.youtube.com"),
    # frame-src — trailer player.
    ("frame-src", "https://www.youtube-nocookie.com"),
    ("frame-src", "https://player.vimeo.com"),
]


def _parse_csp_directives(csp: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for chunk in csp.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        name, _, sources = chunk.partition(" ")
        out[name] = sources.split()
    return out


@pytest.mark.asyncio
async def test_csp_header_contains_every_known_third_party_domain(client):
    r = await client.get("/api/health")
    csp = r.headers.get("Content-Security-Policy") or ""
    directives = _parse_csp_directives(csp)
    for directive, host in _EXPECTED_DOMAINS:
        assert host in directives.get(directive, []), (
            f"{host!r} missing from {directive!r} (CSP={csp})"
        )
    # object-src and report-uri are also part of the contract.
    assert directives.get("object-src") == ["'none'"]
    assert directives.get("report-uri") == ["/api/csp-violation-report"]


@pytest.mark.asyncio
async def test_report_endpoint_accepts_legacy_csp_report_payload(raw_client):
    """Legacy Chromium/Firefox/Safari shape — single ``csp-report`` key."""
    payload = {
        "csp-report": {
            "document-uri": "https://example/portal",
            "violated-directive": "img-src",
            "blocked-uri": "https://evil.example/x.png",
        }
    }
    r = await raw_client.post(
        "/api/csp-violation-report",
        headers={"Content-Type": "application/csp-report"},
        json=payload,
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_report_endpoint_accepts_reports_api_json_payload(raw_client):
    """Modern Reporting API — array of objects with ``type=csp-violation``."""
    payload = [
        {
            "type": "csp-violation",
            "url": "https://example/portal",
            "body": {
                "documentURL": "https://example/portal",
                "blockedURL": "https://evil.example/x.png",
                "effectiveDirective": "img-src",
            },
        }
    ]
    r = await raw_client.post(
        "/api/csp-violation-report",
        headers={"Content-Type": "application/reports+json"},
        json=payload,
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_report_endpoint_caps_at_sixty_per_minute(raw_client):
    """Slowapi 60/min/IP. A flood eventually hits 429 within 65
    requests."""
    seen = []
    payload = {"csp-report": {"violated-directive": "img-src"}}
    for _ in range(65):
        r = await raw_client.post(
            "/api/csp-violation-report",
            headers={"Content-Type": "application/csp-report"},
            json=payload,
        )
        seen.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in seen, f"expected 429 within 65 requests, saw {seen[:10]}..."


@pytest.mark.asyncio
async def test_report_endpoint_neutralises_crlf_in_logged_body(raw_client, caplog):
    """A non-JSON body carrying CR/LF must be logged on a single line so a
    hostile client cannot forge extra log entries (log injection)."""
    forged = "plain\r\n2099-01-01 00:00:00 [AUTH] admin login OK"
    with caplog.at_level(logging.INFO, logger="mediakeeper.csp"):
        r = await raw_client.post(
            "/api/csp-violation-report",
            headers={"Content-Type": "text/plain"},
            content=forged,
        )
    assert r.status_code == 204
    records = [rec for rec in caplog.records if "[CSP_VIOLATION]" in rec.getMessage()]
    assert records, "expected a CSP_VIOLATION log record"
    msg = records[-1].getMessage()
    assert "\n" not in msg and "\r" not in msg
    # The forged text survives only inline, never as a standalone log line.
    assert "admin login OK" in msg


@pytest.mark.asyncio
async def test_report_endpoint_caps_oversized_body_in_log(raw_client, caplog):
    """An oversized body is buffered up to a cap and the logged payload is
    truncated, so a hostile report cannot bloat the log pipeline."""
    from api.csp_report import _MAX_LOG_CHARS

    big = "A" * 50_000
    with caplog.at_level(logging.INFO, logger="mediakeeper.csp"):
        r = await raw_client.post(
            "/api/csp-violation-report",
            headers={"Content-Type": "text/plain"},
            content=big,
        )
    assert r.status_code == 204
    records = [rec for rec in caplog.records if "[CSP_VIOLATION]" in rec.getMessage()]
    assert records, "expected a CSP_VIOLATION log record"
    # The payload is the last positional arg of the lazy log call.
    assert len(records[-1].args[-1]) <= _MAX_LOG_CHARS
