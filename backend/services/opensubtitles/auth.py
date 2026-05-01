"""Configuration & authentification OpenSubtitles (API key, token JWT)."""
import time

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_external_client
from services.settings import get_settings_map
from ._constants import logger, OS_API_BASE, OS_USER_AGENT

# Cache token en memory
_token_cache = {"token": None, "expires": 0}


async def _get_os_config(db: AsyncSession) -> dict | None:
    """Fetch la config OpenSubtitles from les settings standards."""
    cfg = await get_settings_map(db, [
        "opensubtitles.api_key",
        "opensubtitles.username",
        "opensubtitles.password",
    ])
    api_key = cfg["opensubtitles.api_key"]
    if not api_key:
        return None
    return {
        "api_key": api_key,
        "username": cfg["opensubtitles.username"] or "",
        "password": cfg["opensubtitles.password"] or "",
    }


async def is_configured(db: AsyncSession) -> bool:
    """Check si OpenSubtitles est configured."""
    cfg = await get_settings_map(db, ["opensubtitles.api_key"])
    return bool(cfg["opensubtitles.api_key"])


async def _get_headers(db: AsyncSession) -> dict | None:
    """Return les headers with API key + token auth si available."""
    cfg = await _get_os_config(db)
    if not cfg:
        return None

    headers = {
        "Api-Key": cfg["api_key"],
        "User-Agent": OS_USER_AGENT,
        "Content-Type": "application/json",
    }

    if cfg.get("username") and cfg.get("password"):
        now = time.time()
        if _token_cache["token"] and now < _token_cache["expires"]:
            headers["Authorization"] = f"Bearer {_token_cache['token']}"
        else:
            token = await _login(cfg)
            if token:
                headers["Authorization"] = f"Bearer {token}"

    return headers


async def _login(cfg: dict) -> str | None:
    """Login OpenSubtitles → return le token JWT."""
    global _token_cache
    try:
        client = get_external_client()
        res = await client.post(
            f"{OS_API_BASE}/login",
            json={"username": cfg["username"], "password": cfg["password"]},
            headers={
                "Api-Key": cfg["api_key"],
                "User-Agent": OS_USER_AGENT,
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        if res.status_code == 200:
            data = res.json()
            token = data.get("token")
            if token:
                _token_cache = {"token": token, "expires": time.time() + 82800}
                logger.info("[opensubtitles] Login OK")
                return token
        else:
            logger.warning(f"[opensubtitles] Login failed: {res.status_code}")
    except Exception as e:
        logger.error(f"[opensubtitles] Login error: {e}")
    return None
