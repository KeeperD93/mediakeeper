"""Helpers URL Emby : public URL, server_id, deep-link builder."""


def get_emby_public_url(source: dict | None) -> str:
    """
    Returns the URL to use when generating user-facing links to Emby
    (e.g. the "Watch on Emby" button). Prefers the configured public/HTTPS
    URL when available, otherwise falls back to the internal URL.
    The internal URL is what the backend itself uses to talk to Emby
    (scan, API calls, trailer proxying), so it's never appropriate for
    end-user browsers when the server lives on a private LAN.
    """
    if not source:
        return ""
    public = (source.get("public_url") or "").strip().rstrip("/")
    if public:
        return public
    return (source.get("url") or "").strip().rstrip("/")


# Cache Emby server Id: keyed by internal URL so swapping servers invalidates it.
_emby_server_id_cache: dict[str, str] = {}


async def get_emby_server_id(source: dict | None) -> str:
    """
    Fetch + cache the Emby server's `Id` so it can be appended to
    every user-facing deep link. Returns "" if Emby is unreachable
    or not configured — callers should fall back to a link without
    the serverId in that case.
    """
    if not source:
        return ""
    internal_url = (source.get("url") or "").strip().rstrip("/")
    api_key = (source.get("api_key") or "").strip()
    if not internal_url or not api_key:
        return ""
    cached = _emby_server_id_cache.get(internal_url)
    if cached:
        return cached
    try:
        from core.http_client import get_internal_client
        client = get_internal_client()
        res = await client.get(
            f"{internal_url}/System/Info",
            headers={"X-Emby-Token": api_key},
            timeout=5.0,
        )
        if res.status_code == 200:
            sid = (res.json() or {}).get("Id") or ""
            if sid:
                _emby_server_id_cache[internal_url] = sid
                return sid
    except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
        pass
    return ""


def build_emby_deep_link(public_url: str, item_id: str | None, server_id: str = "") -> str:
    """
    Build a user-facing Emby Web deep link.

    Emby 4.9+ requires the `serverId` query param to render the item
    detail page; without it the SPA loads but the route resolves to
    nothing and the user sees a blank page. The legacy `#!/item?id=`
    hash route is still the canonical entry point as of 4.10.
    """
    if not public_url or not item_id:
        return ""
    base = f"{public_url}/web/index.html#!/item?id={item_id}"
    if server_id:
        base += f"&serverId={server_id}"
    return base
