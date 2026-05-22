"""
Shared HTTP client (httpx).
- A single connection pool for the whole application.
- SSL configurable via VERIFY_SSL in .env.
- The external client routes through a DNS-pinned transport
  (:mod:`core.safe_http`) so server-side notifiers can never be
  redirected to private addresses via DNS rebinding (SSRF).
- Must be initialized on startup and closed on shutdown (lifespan).
"""
import os
import httpx

from core.safe_http import make_safe_external_transport

VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() not in ("false", "0", "no")

# Clients initialized in the app lifespan
_internal_client: httpx.AsyncClient | None = None
_external_client: httpx.AsyncClient | None = None


async def init_clients():
    """Initialize the httpx clients (call in the lifespan startup)."""
    global _internal_client, _external_client
    # Internal client (NAS, Emby, local tools) — SSL configurable.
    # Stays on the default backend because internal calls MUST be
    # able to reach private LAN addresses (RFC 1918: 10/8, 172.16/12,
    # 192.168/16 — plus IPv6 link-local fe80::/10 if applicable).
    _internal_client = httpx.AsyncClient(
        verify=VERIFY_SSL,
        timeout=httpx.Timeout(15.0, connect=5.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    # External client (TMDB, OpenSubtitles, Discord webhooks, etc.) —
    # SSL always on, redirects followed, DNS-pinned + private-IP-blocked
    # at the transport layer.
    _external_client = httpx.AsyncClient(
        transport=make_safe_external_transport(verify=True),
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=True,
    )


async def close_clients():
    """Close the httpx clients (call in the lifespan shutdown)."""
    global _internal_client, _external_client
    if _internal_client:
        await _internal_client.aclose()
        _internal_client = None
    if _external_client:
        await _external_client.aclose()
        _external_client = None


def get_internal_client() -> httpx.AsyncClient:
    """Client for local network calls (NAS, Emby, tools)."""
    if _internal_client is None:
        raise RuntimeError("HTTP client not initialized. Check the lifespan.")
    return _internal_client


def get_external_client() -> httpx.AsyncClient:
    """Client for external calls (TMDB, etc.)."""
    if _external_client is None:
        raise RuntimeError("HTTP client not initialized. Check the lifespan.")
    return _external_client
