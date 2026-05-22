"""Unit tests for core.url_safety — persistence guard + SSRF helpers."""
from __future__ import annotations

import pytest

from core.url_safety import (
    UnsafeOutboundURL,
    is_allowed_image_url,
    is_discord_webhook_url,
    is_private_address,
    safe_url,
    validate_outbound_url,
)


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


def test_image_url_accepts_canonical_tmdb_url():
    assert is_allowed_image_url("https://image.tmdb.org/t/p/w500/abc.jpg")


def test_image_url_accepts_uppercase_host():
    assert is_allowed_image_url("https://Image.TMDB.org/t/p/w500/abc.jpg")


def test_image_url_rejects_http_scheme():
    assert not is_allowed_image_url("http://image.tmdb.org/x.jpg")


def test_image_url_rejects_userinfo_bypass():
    # The legacy ``startswith`` check accepted this — urlparse pins the
    # real hostname to ``evil.com`` so the strict equality fails closed.
    assert not is_allowed_image_url("https://image.tmdb.org@evil.com/x.jpg")
    assert not is_allowed_image_url(
        "https://image.tmdb.org:p@evil.com/x.jpg"
    )


def test_image_url_rejects_trailing_dot_subdomain():
    assert not is_allowed_image_url("https://image.tmdb.org.evil.com/x.jpg")


def test_image_url_rejects_subdomain_lookalike():
    assert not is_allowed_image_url("https://evil.image.tmdb.org/x.jpg")


def test_image_url_rejects_other_hosts():
    for url in (
        "https://example.com/x.jpg",
        "https://evil.com/image.tmdb.org/x.jpg",
        "https://127.0.0.1/x.jpg",
    ):
        assert not is_allowed_image_url(url)


def test_image_url_rejects_empty_and_non_string():
    assert not is_allowed_image_url("")
    assert not is_allowed_image_url(None)  # type: ignore[arg-type]
    assert not is_allowed_image_url(123)  # type: ignore[arg-type]


def test_discord_url_accepts_canonical():
    assert is_discord_webhook_url(
        "https://discord.com/api/webhooks/123456789012345678/token"
    )


def test_discord_url_accepts_legacy_discordapp_alias():
    assert is_discord_webhook_url(
        "https://discordapp.com/api/webhooks/1/token"
    )


def test_discord_url_rejects_userinfo_bypass():
    assert not is_discord_webhook_url(
        "https://discord.com@evil.com/api/webhooks/1/token"
    )


def test_discord_url_rejects_trailing_dot_subdomain():
    assert not is_discord_webhook_url(
        "https://discord.com.evil.com/api/webhooks/1/token"
    )


def test_discord_url_rejects_wrong_path_prefix():
    assert not is_discord_webhook_url("https://discord.com/api/users/123")
    assert not is_discord_webhook_url("https://discord.com/")


def test_discord_url_rejects_http_scheme():
    assert not is_discord_webhook_url(
        "http://discord.com/api/webhooks/1/token"
    )


def test_discord_url_rejects_empty_and_non_string():
    assert not is_discord_webhook_url("")
    assert not is_discord_webhook_url(None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        "127.255.255.254",
        "10.0.0.1",
        "10.255.255.255",
        "172.16.0.1",
        "172.31.255.254",
        "192.168.0.1",
        "192.168.255.254",
        "169.254.1.1",  # link-local
        "0.0.0.0",  # unspecified
        "224.0.0.1",  # multicast
        "::1",  # loopback v6
        "fe80::1",  # link-local v6
        "fd00::1",  # unique-local v6
        "::ffff:192.168.1.1",  # IPv4-mapped — must be unwrapped
        "::ffff:127.0.0.1",
    ],
)
def test_private_address_flags_lan_and_loopback(host):
    assert is_private_address(host), f"{host} should be private"


@pytest.mark.parametrize(
    "host",
    [
        "8.8.8.8",
        "1.1.1.1",
        "162.159.135.232",
        "2606:4700:4700::1111",  # Cloudflare DNS v6
        "example.com",  # not an IP literal at all
        "",
        "garbage",
    ],
)
def test_private_address_does_not_flag_public_or_non_ip(host):
    assert not is_private_address(host), f"{host} should not be private"


@pytest.mark.asyncio
async def test_validate_rejects_empty_url():
    with pytest.raises(UnsafeOutboundURL) as exc:
        await validate_outbound_url("")
    assert exc.value.reason == "empty_url"


@pytest.mark.asyncio
async def test_validate_rejects_http_scheme():
    with pytest.raises(UnsafeOutboundURL) as exc:
        await validate_outbound_url("http://example.com/")
    assert exc.value.reason == "scheme_not_allowed"


@pytest.mark.asyncio
async def test_validate_rejects_file_scheme():
    with pytest.raises(UnsafeOutboundURL) as exc:
        await validate_outbound_url("file:///etc/passwd")
    assert exc.value.reason == "scheme_not_allowed"


@pytest.mark.asyncio
async def test_validate_rejects_missing_host():
    with pytest.raises(UnsafeOutboundURL) as exc:
        await validate_outbound_url("https:///path")
    assert exc.value.reason == "missing_host"


@pytest.mark.asyncio
async def test_validate_rejects_private_ipv4_literal():
    with pytest.raises(UnsafeOutboundURL) as exc:
        await validate_outbound_url("https://192.168.1.10/")
    assert exc.value.reason == "private_ip_literal"


@pytest.mark.asyncio
async def test_validate_rejects_loopback_literal():
    with pytest.raises(UnsafeOutboundURL) as exc:
        await validate_outbound_url("https://127.0.0.1/")
    assert exc.value.reason == "private_ip_literal"


@pytest.mark.asyncio
async def test_validate_rejects_ipv6_loopback_literal():
    with pytest.raises(UnsafeOutboundURL) as exc:
        await validate_outbound_url("https://[::1]/")
    assert exc.value.reason == "private_ip_literal"


@pytest.mark.asyncio
async def test_validate_rejects_ipv4_mapped_ipv6_bypass():
    with pytest.raises(UnsafeOutboundURL) as exc:
        await validate_outbound_url("https://[::ffff:192.168.1.1]/")
    assert exc.value.reason == "private_ip_literal"


@pytest.mark.asyncio
async def test_validate_rejects_dns_failure(monkeypatch):
    async def _no_results(_host):
        return []

    monkeypatch.setattr("core.url_safety.resolve_host", _no_results)
    with pytest.raises(UnsafeOutboundURL) as exc:
        await validate_outbound_url("https://nx.example.invalid/")
    assert exc.value.reason == "dns_resolution_failed"


@pytest.mark.asyncio
async def test_validate_rejects_dns_resolving_to_private(monkeypatch):
    async def _private(_host):
        return ["192.168.1.50"]

    monkeypatch.setattr("core.url_safety.resolve_host", _private)
    with pytest.raises(UnsafeOutboundURL) as exc:
        await validate_outbound_url("https://malicious.example/")
    assert exc.value.reason == "dns_resolves_private"


@pytest.mark.asyncio
async def test_validate_rejects_when_any_record_is_private(monkeypatch):
    # Mixed answers — a single private record poisons the whole set.
    async def _mixed(_host):
        return ["8.8.8.8", "192.168.0.1"]

    monkeypatch.setattr("core.url_safety.resolve_host", _mixed)
    with pytest.raises(UnsafeOutboundURL) as exc:
        await validate_outbound_url("https://rebinder.example/")
    assert exc.value.reason == "dns_resolves_private"


@pytest.mark.asyncio
async def test_validate_accepts_public_dns(monkeypatch):
    async def _public(_host):
        return ["8.8.8.8", "2001:4860:4860::8888"]

    monkeypatch.setattr("core.url_safety.resolve_host", _public)
    addrs = await validate_outbound_url("https://example.test/")
    assert addrs == ["8.8.8.8", "2001:4860:4860::8888"]
