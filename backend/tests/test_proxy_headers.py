"""Tests for core.proxy — TRUSTED_PROXIES whitelist, middleware and the client IP."""
from __future__ import annotations

import ipaddress

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from core.proxy import (
    ProxyHeadersMiddleware,
    get_client_ip,
    is_request_from_trusted_proxy,
    is_request_secure,
    is_trusted_proxy_host,
    normalize_ip,
    parse_trusted_proxies,
    trusted_forwarded_host,
)
from models.security import SecurityAttempt
from services.security import FAIL_BLOCK_THRESHOLD, is_blocked, record_failure


def _build_app(trusted: list):
    async def echo(request):
        return JSONResponse({
            "client": request.client.host if request.client else None,
            "scheme": request.url.scheme,
            "from_trusted_proxy": is_request_from_trusted_proxy(request),
            "secure": is_request_secure(request),
            "fwd_host": trusted_forwarded_host(request),
        })

    app = Starlette(routes=[Route("/echo", echo)])
    app.add_middleware(ProxyHeadersMiddleware, networks=trusted)
    return app


def test_parse_trusted_proxies_handles_csv_with_cidr_and_ip():
    nets = parse_trusted_proxies("127.0.0.1, 172.18.0.0/16,  10.0.0.0/8")
    assert len(nets) == 3
    assert ipaddress.ip_address("172.18.5.5") in nets[1]
    assert ipaddress.ip_address("10.255.0.1") in nets[2]


def test_parse_trusted_proxies_drops_invalid_entries():
    nets = parse_trusted_proxies("127.0.0.1, not-an-ip, 10.0.0.0/8")
    # 2 valid entries kept; the garbage is dropped with a warning.
    assert len(nets) == 2


def test_parse_trusted_proxies_empty_yields_empty_list():
    assert parse_trusted_proxies("") == []
    assert parse_trusted_proxies(None) == []


def test_parse_trusted_proxies_warns_on_overly_broad_cidr(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="mediakeeper"):
        nets = parse_trusted_proxies("0.0.0.0/0, 10.0.0.0/8, 198.51.100.10/32")

    # All three are still accepted — the warning is advisory, not a reject.
    assert len(nets) == 3
    warnings = " ".join(r.message for r in caplog.records if r.levelno == logging.WARNING)
    assert "very broad" in warnings
    # A tight /32 host must never be flagged.
    assert "198.51.100.10/32" not in warnings


def test_is_trusted_proxy_host_matches_cidr():
    nets = parse_trusted_proxies("172.18.0.0/16")
    assert is_trusted_proxy_host("172.18.5.5", nets) is True
    assert is_trusted_proxy_host("10.0.0.1", nets) is False
    assert is_trusted_proxy_host(None, nets) is False
    assert is_trusted_proxy_host("not-an-ip", nets) is False


@pytest.mark.asyncio
async def test_xff_ignored_when_trusted_proxies_empty():
    app = _build_app(trusted=[])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/echo",
            headers={
                "X-Forwarded-For": "198.51.100.4",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "evil.example",
            },
        )
    body = r.json()
    assert body["client"] == "127.0.0.1"  # original ASGI client preserved
    assert body["scheme"] == "http"
    assert body["from_trusted_proxy"] is False
    assert body["secure"] is False
    assert body["fwd_host"] is None  # ignored even if header is present


@pytest.mark.asyncio
async def test_xff_honoured_when_proxy_in_whitelist():
    app = _build_app(trusted=parse_trusted_proxies("127.0.0.1"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/echo",
            headers={
                "X-Forwarded-For": "198.51.100.4",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "mediakeeper.example.com",
            },
        )
    body = r.json()
    assert body["client"] == "198.51.100.4"
    assert body["scheme"] == "https"
    assert body["from_trusted_proxy"] is True
    assert body["secure"] is True
    assert body["fwd_host"] == "mediakeeper.example.com"


@pytest.mark.parametrize("raw, expected", [
    ("203.0.113.7", "203.0.113.7"),
    (" 203.0.113.7 ", "203.0.113.7"),
    ("203.0.113.7:51234", "203.0.113.7"),
    ("[2001:db8::1]:443", "2001:db8::1"),
    ("2001:DB8:0:0:0:0:0:1", "2001:db8::1"),
    ("fe80::1%eth0", "fe80::1"),
    pytest.param("fe80::1%" + "x" * 200, "fe80::1", id="long-zone-id"),
    ("::ffff:203.0.113.7", "203.0.113.7"),
    ("unknown", None),
    ("1.2.3.4.5", None),
    pytest.param("x" * 200, None, id="long-garbage"),
    ("", None),
    (None, None),
])
def test_normalize_ip(raw, expected):
    assert normalize_ip(raw) == expected


@pytest.mark.parametrize("xff, trusted, expected", [
    # The client writes what it wants on the left; the proxy appends the real peer.
    ("198.51.100.66, 203.0.113.7", "127.0.0.1", "203.0.113.7"),
    ("198.51.100.4, 10.0.0.5, 172.18.0.1", "127.0.0.1", "172.18.0.1"),
    # Inner hops that are trusted proxies themselves are skipped, once normalized.
    ("198.51.100.66, 203.0.113.7, 172.18.0.5", "127.0.0.1, 172.18.0.0/16", "203.0.113.7"),
    ("203.0.113.7, ::ffff:172.18.0.5", "127.0.0.1, 172.18.0.0/16", "203.0.113.7"),
    # Ports, zone ids and empty entries are tolerated.
    ("203.0.113.7:51234", "127.0.0.1", "203.0.113.7"),
    pytest.param("fe80::1%" + "x" * 200, "127.0.0.1", "fe80::1", id="long-zone-id"),
    ("203.0.113.7, ", "127.0.0.1", "203.0.113.7"),
])
@pytest.mark.asyncio
async def test_xff_takes_the_rightmost_hop_that_is_not_a_trusted_proxy(xff, trusted, expected):
    app = _build_app(trusted=parse_trusted_proxies(trusted))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/echo", headers={"X-Forwarded-For": xff})
    assert r.json()["client"] == expected


@pytest.mark.parametrize("xff, trusted, expected", [
    # Every hop is a trusted proxy: the leftmost one is kept.
    ("10.0.0.7, 10.0.0.9", "127.0.0.1, 10.0.0.0/8", "10.0.0.7"),
    # A hop that is not an IP ends the walk on the last good address, a proxy's.
    pytest.param("x" * 200, "127.0.0.1", "127.0.0.1", id="long-garbage"),
    ("203.0.113.7, unknown", "127.0.0.1", "127.0.0.1"),
    ("unknown, 172.18.0.5", "127.0.0.1, 172.18.0.0/16", "172.18.0.5"),
])
@pytest.mark.asyncio
async def test_xff_falls_back_to_a_trusted_address_without_a_client_hop(xff, trusted, expected):
    app = _build_app(trusted=parse_trusted_proxies(trusted))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/echo", headers={"X-Forwarded-For": xff})
    assert r.json()["client"] == expected


@pytest.mark.asyncio
async def test_xff_header_lines_are_read_in_order():
    app = _build_app(trusted=parse_trusted_proxies("127.0.0.1, 172.18.0.0/16"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/echo",
            headers=[
                ("X-Forwarded-For", "198.51.100.66"),
                ("X-Forwarded-For", "203.0.113.7"),
                ("X-Forwarded-For", "172.18.0.5"),
            ],
        )
    assert r.json()["client"] == "203.0.113.7"


def test_get_client_ip_normalizes_what_the_server_put_in_scope():
    def ip_of(host):
        return get_client_ip(Request({"type": "http", "client": (host, 0), "headers": []}))

    assert ip_of("::ffff:203.0.113.7") == "203.0.113.7"
    assert ip_of("x" * 200) is None


@pytest.mark.asyncio
async def test_a_forged_forwarded_value_cannot_switch_off_the_lockout(db_session):
    """Each failure is stored under the real, bounded client IP (SQLite does
    not enforce VARCHAR(64), so the stored value is checked explicitly)."""
    async def attempt(request):
        await record_failure(db_session, get_client_ip(request) or "unknown", "victim", "admin")
        return JSONResponse({})

    app = Starlette(routes=[Route("/attempt", attempt, methods=["POST"])])
    app.add_middleware(ProxyHeadersMiddleware, networks=parse_trusted_proxies("127.0.0.1"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for i in range(FAIL_BLOCK_THRESHOLD):
            forged = f"{'x' * 100}{i}, fe80::1%{'y' * 100}"
            await ac.post("/attempt", headers={"X-Forwarded-For": forged})

    ips = (await db_session.execute(select(SecurityAttempt.ip))).scalars().all()
    assert ips == ["fe80::1"] * FAIL_BLOCK_THRESHOLD
    # No username given: only the IP block can match.
    assert await is_blocked(db_session, "fe80::1", None, "admin")


@pytest.mark.asyncio
async def test_xff_proto_invalid_value_is_ignored():
    app = _build_app(trusted=parse_trusted_proxies("127.0.0.1"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/echo", headers={"X-Forwarded-Proto": "ftp"})
    assert r.json()["scheme"] == "http"


@pytest.mark.asyncio
async def test_no_xff_keeps_original_request():
    app = _build_app(trusted=parse_trusted_proxies("127.0.0.1"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/echo")
    body = r.json()
    assert body["client"] == "127.0.0.1"
    assert body["scheme"] == "http"
    assert body["from_trusted_proxy"] is True
