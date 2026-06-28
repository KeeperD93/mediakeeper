"""Localized TMDB season/episode detail (name + overview).

The catalog ``get_season_episodes`` / ``get_tv_seasons`` helpers return names
only; surfaces that also need the per-season/episode *overview* in the viewer's
language (e.g. Discord season/episode notifications) use these. English-cascade
on a blank overview like ``get_media_detail`` so it never renders empty (#288).
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_external_client
from services.tmdb import _get_tmdb_key, _tmdb_headers_sync, tmdb_language, TMDB_BASE

logger = logging.getLogger("mediakeeper.tmdb")


async def _fetch_localized(url_path: str, db: AsyncSession | None, locale: str | None) -> dict:
    """Return ``{"name", "overview"}`` for a TMDB sub-resource in ``locale``.

    Falls back to the English overview when the localized one is blank, and to
    an empty dict on any failure so callers keep their source values.
    """
    api_key = await _get_tmdb_key(db)
    if not api_key:
        return {}
    lang = tmdb_language(locale)
    try:
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}{url_path}",
            params={"language": lang},
            headers=_tmdb_headers_sync(api_key),
        )
        if res.status_code != 200:
            return {}
        d = res.json()
        overview = (d.get("overview") or "").strip()
        if not overview and not lang.startswith("en"):
            try:
                res_en = await client.get(
                    f"{TMDB_BASE}{url_path}",
                    params={"language": "en-US"},
                    headers=_tmdb_headers_sync(api_key),
                )
                if res_en.status_code == 200:
                    overview = (res_en.json().get("overview") or "").strip()
            except Exception:
                logger.debug("[tmdb] %s en overview fallback failed", url_path, exc_info=True)
        return {"name": d.get("name") or "", "overview": overview}
    except Exception:
        logger.exception("[tmdb] localized detail %s failed", url_path)
        return {}


async def get_season_detail(
    tmdb_id: int, season: int, db: AsyncSession | None = None, locale: str | None = None,
) -> dict:
    """Localized ``{name, overview}`` for a TV season ("" / "" on failure)."""
    return await _fetch_localized(f"/tv/{tmdb_id}/season/{season}", db, locale)


async def get_episode_detail(
    tmdb_id: int, season: int, episode: int,
    db: AsyncSession | None = None, locale: str | None = None,
) -> dict:
    """Localized ``{name, overview}`` for a TV episode ("" / "" on failure)."""
    return await _fetch_localized(
        f"/tv/{tmdb_id}/season/{season}/episode/{episode}", db, locale,
    )
