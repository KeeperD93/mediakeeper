"""
    Trailer resolution service for the Portal.

Cascade order, used by ``resolve_trailer``:

  1. Emby ``LocalTrailers`` API   → MP4 streamed by the MediaKeeper backend
                                    (the Emby URL is never exposed to the client).
  2. TMDB ``videos`` filtered on the user's preferred language.
  3. TMDB ``videos`` filtered on English (``en``).
  4. TMDB ``videos`` filtered on the media's original language.
  5. TMDB ``videos`` — any language at all.
  6. ``None`` — no trailer found.

The function returns a small dict the frontend can render uniformly:

    {
        "source":   "emby" | "youtube" | "vimeo",
        "url":      str,        # backend proxy URL for emby, embed URL otherwise
        "key":      str | None, # video provider id (YouTube/Vimeo only)
        "language": str | None, # ISO 639-1 of the picked trailer
        "name":     str,
    }
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_external_client, get_internal_client
from services.settings import get_active_media_source
from services.tmdb import _get_tmdb_key, _tmdb_headers_sync, TMDB_BASE

logger = logging.getLogger("mediakeeper.portal.trailers")

# Emby item ids are alphanumeric GUIDs. Reject anything else before it
# reaches the upstream URL so a forged id cannot smuggle path/query
# characters into the proxied Emby request.
_TRAILER_ID_RE = re.compile(r"^[A-Za-z0-9]+$")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def resolve_trailer(
    db: AsyncSession,
    media_type: str,
    tmdb_id: int,
    user_language: str = "en",
    emby_item_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Run the trailer cascade and return the first hit, or ``None``.

    Parameters
    ----------
    db
        Active SQLAlchemy session (used to read settings + TMDB key).
    media_type
        ``"movie"`` or ``"tv"``.
    tmdb_id
        TMDB id of the media.
    user_language
        ISO 639-1 code of the user's preferred trailer language. Falls
        back to English when no match is found at this step.
    emby_item_id
        Optional Emby item id; when provided we try LocalTrailers first.
    """
    # 1) Local trailer hosted on Emby
    if emby_item_id:
        local = await _resolve_emby_local_trailer(db, emby_item_id)
        if local:
            return local

    # 2-5) TMDB cascade
    return await _resolve_tmdb_trailer(db, media_type, tmdb_id, user_language)


# ---------------------------------------------------------------------------
# Step 1 — Emby local trailers
# ---------------------------------------------------------------------------

async def _resolve_emby_local_trailer(
    db: AsyncSession, emby_item_id: str
) -> Optional[dict]:
    """
    Ask Emby whether the item has any local trailer files attached.
    Returns a proxy URL the frontend can stream through the backend
    (so the private Emby URL never leaks to the user agent).
    """
    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        return None
    internal_url = (source.get("url") or "").rstrip("/")
    api_key = source.get("api_key") or ""
    if not internal_url or not api_key:
        return None

    try:
        client = get_internal_client()
        res = await client.get(
            f"{internal_url}/Items/{emby_item_id}/LocalTrailers",
            headers={"X-Emby-Token": api_key},
        )
        if res.status_code != 200:
            return None
        trailers = res.json() or []
        if not trailers:
            return None
        # Pick the first trailer; Emby returns them in disk order.
        first = trailers[0]
        trailer_id = first.get("Id")
        if not trailer_id:
            return None
        return {
            "source": "emby",
            "url": f"/api/portal/trailers/emby/{trailer_id}",
            "key": None,
            "language": None,
            "name": first.get("Name", "Local trailer"),
        }
    except Exception as e:
        logger.warning(f"[TRAILERS] LocalTrailers lookup failed for {emby_item_id}: {e}")
        return None


async def stream_emby_trailer(
    db: AsyncSession, trailer_item_id: str
) -> Optional[dict]:
    """Build the upstream Emby stream URL for a local trailer.

    Returns ``{"url": ...}`` only when ``trailer_item_id`` is a
    syntactically valid Emby id AND the item is actually a ``Trailer``;
    ``None`` otherwise. The stream URL carries the admin API key, so
    without the type check any exposed Emby id (movie, episode) could be
    streamed in full through this proxy, bypassing per-user library
    permissions, parental control and the adult filter.
    """
    if not trailer_item_id or not _TRAILER_ID_RE.match(trailer_item_id):
        return None
    source = await get_active_media_source(db)
    if not source or source.get("source") not in ("emby", "jellyfin"):
        return None
    internal_url = (source.get("url") or "").rstrip("/")
    api_key = source.get("api_key") or ""
    if not internal_url or not api_key:
        return None
    client = get_internal_client()
    try:
        meta = await client.get(
            f"{internal_url}/Items",
            params={"Ids": trailer_item_id},
            headers={"X-Emby-Token": api_key},
        )
    except Exception as e:
        logger.warning("[TRAILERS] trailer lookup failed for %s: %s", trailer_item_id, e)
        return None
    if meta.status_code != 200:
        return None
    items = (meta.json() or {}).get("Items") or []
    if not items or items[0].get("Type") != "Trailer":
        return None
    return {
        "url": f"{internal_url}/Videos/{trailer_item_id}/stream?Static=true&api_key={api_key}",
    }


# ---------------------------------------------------------------------------
# Steps 2-5 — TMDB cascade
# ---------------------------------------------------------------------------

_VALID_TYPES = ("Trailer", "Teaser")

# Name-quality heuristics: TMDB occasionally ships several videos in the
# same ``iso_639_1`` bucket — a real publisher dub (``"Bande-annonce
# officielle"``) and a fan-uploaded subtitled version (``"VOSTFR"``)
# both tagged ``fr``. The static metadata flags (Trailer, official,
# published_at) don't always split them, so the picker also looks at the
# video's name to surface the studio-grade dub.
#
# The boost dictionary is keyed on ``iso_639_1``: a French title ranks
# ``"Bande annonce"`` ahead of ``"Trailer"`` whereas the English step
# does the opposite. ``official`` / ``officiel(le)`` lifts both.
_LANGUAGE_BOOST_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fr": (
        "bande-annonce", "bande annonce",
        "officiel", "officielle", "official",
        "version française", "version francaise",
    ),
    "en": ("trailer", "official"),
}
# Standalone ``VF`` / ``V.F.`` abbreviation (Version Française) — boosted
# at the fr step only. Word-boundary anchored so ``VFX`` (visual effects)
# doesn't accidentally lift a video into the studio bucket.
_LANGUAGE_BOOST_REGEX: dict[str, re.Pattern[str]] = {
    "fr": re.compile(r"\bv\.?f\.?\b", re.IGNORECASE),
}
_NAME_PENALTY_KEYWORDS = (
    "vost", "vostfr",
    "sous-titr", "subtitled", "subbed",
    "version originale", "original version",
)
# Matches the standalone ``VO`` / ``V.O.`` abbreviation (Version
# Originale) without colliding with "video", "voice over", etc. — both
# halves are word-boundary anchored so only the standalone token loses.
_VO_ABBREVIATION_RE = re.compile(r"\bv\.?o\.?\b", re.IGNORECASE)


def _name_score(name: str, language: Optional[str]) -> int:
    """Return ``+1`` for studio markers, ``-1`` for subtitled markers, else ``0``.

    ``language`` (``"fr"`` / ``"en"`` / ``None`` / any ISO 639-1 code)
    selects which boost list applies. Languages with no entry in the
    boost tables — Japanese, Spanish, German, … — only see the universal
    penalty list, so the scoring degrades to Trailer/official/date for
    them rather than producing surprising boosts. Extend the boost
    tables to add localisation.
    """
    n = (name or "").lower()
    if any(k in n for k in _NAME_PENALTY_KEYWORDS):
        return -1
    if _VO_ABBREVIATION_RE.search(n):
        return -1
    boost_words = _LANGUAGE_BOOST_KEYWORDS.get(language or "", ())
    if any(k in n for k in boost_words):
        return 1
    boost_re = _LANGUAGE_BOOST_REGEX.get(language or "")
    if boost_re and boost_re.search(n):
        return 1
    return 0


async def _resolve_tmdb_trailer(
    db: AsyncSession, media_type: str, tmdb_id: int, user_language: str
) -> Optional[dict]:
    api_key = await _get_tmdb_key(db)
    if not api_key:
        return None
    try:
        client = get_external_client()
        # Primary request covers user_language + English + language-agnostic
        # videos. TMDB filters ``videos`` server-side by
        # ``include_video_language``, so the film's original language is
        # only fetched when the first pass yields nothing usable (see below).
        res = await client.get(
            f"{TMDB_BASE}/{media_type}/{tmdb_id}",
            params={
                "language": user_language,
                "append_to_response": "videos",
                "include_video_language": f"{user_language},en,null",
            },
            headers=_tmdb_headers_sync(api_key),
        )
        if res.status_code != 200:
            return None
        data = res.json()
        videos = list((data.get("videos") or {}).get("results") or [])
        original_lang = data.get("original_language") or None

        # Cascade: user_language → en → original_language → null (any).
        # Original-language videos live outside the primary payload when
        # they differ from user_language/en, so we pull them lazily just
        # before step 3.
        def try_step(pool: list[dict], lang: Optional[str], seen: set) -> Optional[dict]:
            if lang in seen:
                return None
            seen.add(lang)
            return _pick_video(pool, lang)

        seen: set[Optional[str]] = set()
        for lang in (user_language, "en"):
            picked = try_step(videos, lang, seen)
            if picked:
                return picked

        if original_lang and original_lang not in (user_language, "en"):
            try:
                res_extra = await client.get(
                    f"{TMDB_BASE}/{media_type}/{tmdb_id}/videos",
                    params={"include_video_language": original_lang},
                    headers=_tmdb_headers_sync(api_key),
                )
                if res_extra.status_code == 200:
                    extra_videos = res_extra.json().get("results") or []
                    picked = try_step(extra_videos, original_lang, seen)
                    if picked:
                        return picked
            except Exception as exc:
                logger.debug(f"[TRAILERS] original-lang fallback failed: {exc}")
        elif original_lang:
            picked = try_step(videos, original_lang, seen)
            if picked:
                return picked

        # Final step: any language-agnostic video from the primary call.
        return try_step(videos, None, seen)
    except Exception as e:
        logger.warning(f"[TRAILERS] TMDB lookup failed for {media_type}/{tmdb_id}: {e}")
        return None


def _pick_video(videos: list[dict], language: Optional[str]) -> Optional[dict]:
    """
    Pick the best video matching ``language``.

    - ``language=None`` matches *any* video and is the final fallback step.
    - We only consider YouTube and Vimeo (the two TMDB-supported providers).
    - Ranking (most important first):
        1. ``Trailer`` before ``Teaser``;
        2. ``official=True`` before ``official=False`` — surfaces the
           publisher's own French dub over fan-uploaded VOSTFR teasers;
        3. name heuristic (``+1`` for "officielle" / "official", ``-1``
           for "VOST" / "sous-titré") — TMDB occasionally tags a fan
           subtitled cut with ``iso_639_1=fr`` alongside the real dub,
           and the name is the only thing that separates them;
        4. most recent ``published_at`` first — newer trailers usually
           ship with the full localised dub instead of an early subtitled
           promo cut.
    """
    candidates = []
    for v in videos:
        if v.get("site") not in ("YouTube", "Vimeo"):
            continue
        if v.get("type") not in _VALID_TYPES:
            continue
        if language is not None and (v.get("iso_639_1") or "") != language:
            continue
        candidates.append(v)

    if not candidates:
        return None

    # Python sort is stable: tie-break by published_at desc first, then
    # re-sort by primary criteria so equal Trailer/official/name rows
    # keep the newest-first order.
    candidates.sort(key=lambda v: v.get("published_at") or "", reverse=True)
    candidates.sort(key=lambda v: (
        0 if v.get("type") == "Trailer" else 1,
        0 if v.get("official") else 1,
        -_name_score(v.get("name", ""), language),
    ))
    best = candidates[0]
    site = best.get("site", "YouTube").lower()
    return {
        "source": site,  # "youtube" or "vimeo"
        "url": _embed_url(site, best["key"]),
        "key": best["key"],
        "language": best.get("iso_639_1") or None,
        "name": best.get("name", ""),
    }


def _embed_url(site: str, key: str) -> str:
    if site == "vimeo":
        return f"https://player.vimeo.com/video/{key}"
    # YouTube via the privacy-enhanced domain.
    return f"https://www.youtube-nocookie.com/embed/{key}"
