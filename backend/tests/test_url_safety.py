"""Unit tests for core.url_safety.safe_url — URL scheme whitelist helper."""
from __future__ import annotations

import pytest

from core.url_safety import safe_url


# ─────────────────────────── scheme acceptance ───────────────────────────


def test_safe_url_accepts_https():
    assert safe_url("https://example.com/path?q=1") == "https://example.com/path?q=1"


def test_safe_url_accepts_https_with_port():
    assert safe_url("https://example.com:8443/x") == "https://example.com:8443/x"


def test_safe_url_default_rejects_http():
    # Default scheme set is https only — http must be opted-in explicitly.
    assert safe_url("http://example.com") is None


def test_safe_url_accepts_http_when_explicitly_allowed():
    assert safe_url("http://example.com", schemes=("http", "https")) == "http://example.com"


# ─────────────────────────── scheme rejection ───────────────────────────


def test_safe_url_blocks_javascript_scheme():
    assert safe_url("javascript:alert(1)") is None


def test_safe_url_blocks_javascript_scheme_uppercase():
    assert safe_url("JavaScript:alert(1)") is None


def test_safe_url_blocks_javascript_scheme_with_leading_whitespace():
    assert safe_url("  javascript:alert(1)") is None
    assert safe_url("\tjavascript:alert(1)") is None
    assert safe_url("\njavascript:alert(1)") is None


def test_safe_url_blocks_javascript_scheme_with_embedded_whitespace():
    assert safe_url("java\nscript:alert(1)") is None
    assert safe_url("java\tscript:alert(1)") is None


def test_safe_url_blocks_data_uri():
    assert safe_url("data:text/html,<script>alert(1)</script>") is None


def test_safe_url_blocks_vbscript_scheme():
    assert safe_url("vbscript:msgbox(1)") is None


def test_safe_url_blocks_file_scheme():
    assert safe_url("file:///etc/passwd") is None


def test_safe_url_blocks_about_scheme():
    assert safe_url("about:blank") is None


def test_safe_url_blocks_blocked_scheme_even_when_listed():
    # Defence in depth: if a caller mistakenly includes a blocked scheme
    # in ``schemes``, the BLOCKED_SCHEMES set still wins.
    assert safe_url("javascript:alert(1)", schemes=("javascript", "https")) is None


# ─────────────────────────── input handling ───────────────────────────


def test_safe_url_rejects_empty_inputs():
    assert safe_url("") is None
    assert safe_url("   ") is None
    assert safe_url(None) is None


def test_safe_url_rejects_non_string_inputs():
    assert safe_url(123) is None  # type: ignore[arg-type]
    assert safe_url({"url": "x"}) is None  # type: ignore[arg-type]


def test_safe_url_rejects_relative_paths():
    # Backend persistence boundary requires absolute URLs (the helper
    # is not used for in-app paths; routing layer handles those).
    assert safe_url("/api/foo") is None
    assert safe_url("./foo") is None


def test_safe_url_rejects_url_without_host():
    assert safe_url("https:///path") is None


# ─────────────────────────── host whitelist ───────────────────────────


def test_safe_url_accepts_host_in_whitelist():
    assert safe_url(
        "https://image.tmdb.org/t/p/w500/poster.jpg",
        allowed_hosts=("image.tmdb.org", "i.imgur.com"),
    ) == "https://image.tmdb.org/t/p/w500/poster.jpg"


def test_safe_url_accepts_imgur_host():
    assert safe_url(
        "https://i.imgur.com/abc123.png",
        allowed_hosts=("image.tmdb.org", "i.imgur.com"),
    ) == "https://i.imgur.com/abc123.png"


def test_safe_url_rejects_host_outside_whitelist():
    assert safe_url(
        "https://evil.example.com/poster.jpg",
        allowed_hosts=("image.tmdb.org", "i.imgur.com"),
    ) is None


def test_safe_url_host_whitelist_is_case_insensitive():
    assert safe_url(
        "https://Image.TMDB.org/path",
        allowed_hosts=("image.tmdb.org",),
    ) == "https://Image.TMDB.org/path"


def test_safe_url_no_whitelist_accepts_any_host():
    assert safe_url("https://example.com") == "https://example.com"
    assert safe_url("https://other.example") == "https://other.example"


# ─────────────────────────── parser robustness ───────────────────────────


def test_safe_url_handles_garbage_strings():
    # ``urlparse`` is permissive; we still need to land in a sensible
    # rejection rather than a value error.
    for garbage in [
        ":",
        "://no-scheme",
        "https:",
        "https//missing-colon",
        "%%%%%",
    ]:
        assert safe_url(garbage) is None
