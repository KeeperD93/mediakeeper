"""Unit tests for core.proxy — TRUSTED_PROXIES whitelist + middleware."""
from __future__ import annotations

import ipaddress

import pytest
from httpx import AsyncClient, ASGITransport
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from core.proxy import (
    ProxyHeadersMiddleware,
    is_request_from_trusted_proxy,
    is_request_secure,
    is_trusted_proxy_host,
    parse_trusted_proxies,
    trusted_forwarded_host,
)


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
    # 2 valid entries kept, the garbage is silently dropped.
    assert len(nets) == 2


def test_parse_trusted_proxies_empty_yields_empty_list():
    assert parse_trusted_proxies("") == []
    assert parse_trusted_proxies(None) == []


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
                "X-Forwarded-For": "1.2.3.4",
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
                "X-Forwarded-For": "1.2.3.4",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "mediakeeper.example.com",
            },
        )
    body = r.json()
    assert body["client"] == "1.2.3.4"
    assert body["scheme"] == "https"
    assert body["from_trusted_proxy"] is True
    assert body["secure"] is True
    assert body["fwd_host"] == "mediakeeper.example.com"


@pytest.mark.asyncio
async def test_xff_takes_leftmost_ip_in_chain():
    app = _build_app(trusted=parse_trusted_proxies("127.0.0.1"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/echo",
            headers={"X-Forwarded-For": "1.2.3.4, 10.0.0.5, 172.18.0.1"},
        )
    assert r.json()["client"] == "1.2.3.4"


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
