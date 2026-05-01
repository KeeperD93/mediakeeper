"""
Shared HTTP client (httpx).
- A single connection pool for the whole application.
- SSL configurable via VERIFY_SSL in .env.
- Must be initialized on startup and closed on shutdown (lifespan).
"""
import os
import httpx

VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() not in ("false", "0", "no")

# Clients initialized in the app lifespan
_internal_client: httpx.AsyncClient | None = None
_external_client: httpx.AsyncClient | None = None


async def init_clients():
    """Initialize the httpx clients (call in the lifespan startup)."""
    global _internal_client, _external_client
    # Internal client (NAS, Emby, local tools) — SSL configurable
    _internal_client = httpx.AsyncClient(
        verify=VERIFY_SSL,
        timeout=httpx.Timeout(15.0, connect=5.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    # External client (TMDB, OpenSubtitles, etc.) — SSL always on, redirects followed
    _external_client = httpx.AsyncClient(
        verify=True,
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
