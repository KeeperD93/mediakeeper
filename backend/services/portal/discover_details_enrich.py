"""Helpers that transform raw TMDB payloads into the enriched detail
payload consumed by the premium detail page.

Kept out of ``discover_details.py`` so that file can stay under the
300-line limit enforced by the project's coding rules.
"""
import logging

from services.portal.discover_lists import _IMG_BASE
from services.tmdb import _tmdb_headers_sync, TMDB_BASE

logger = logging.getLogger("mediakeeper.portal.discover")


# Crew jobs bundled into the premium detail "key crew" block. Ordered by
# importance so the UI can slice the first N without re-sorting.
KEY_CREW_JOBS = [
    "Director",
    "Screenplay", "Writer", "Story",
    "Original Music Composer", "Music", "Composer",
    "Director of Photography",
    "Editor",
    "Producer", "Executive Producer",
    "Production Design",
    "Costume Design",
]

# Video types we want to surface in the "Extras" tab.
ALLOWED_VIDEO_TYPES = {"Trailer", "Teaser", "Clip", "Featurette", "Behind the Scenes"}


def pick_certification(d: dict, media_type: str) -> str:
    """Pull a single age rating string out of TMDB's release_dates /
    content_ratings payload.

    Preference order: FR → US → first non-empty. Returns "" when no
    certification is found.
    """
    candidates: list[tuple[str, str]] = []
    if media_type == "movie":
        for entry in (d.get("release_dates", {}) or {}).get("results", []):
            region = entry.get("iso_3166_1", "")
            for rd in entry.get("release_dates", []) or []:
                cert = (rd.get("certification") or "").strip()
                if cert:
                    candidates.append((region, cert))
                    break
    else:
        for entry in (d.get("content_ratings", {}) or {}).get("results", []):
            region = entry.get("iso_3166_1", "")
            cert = (entry.get("rating") or "").strip()
            if cert:
                candidates.append((region, cert))
    for preferred in ("FR", "US"):
        for region, cert in candidates:
            if region == preferred:
                return cert
    return candidates[0][1] if candidates else ""


def pick_watch_providers(d: dict) -> dict:
    """Flatten TMDB /watch/providers into a compact FR-first dict.

    Returns ``{"flatrate": [...], "rent": [...], "buy": [...], "link": str}``
    where each list contains ``{name, logo}`` entries. Non-FR regions are
    used as a fallback when no FR data is available.
    """
    data = (d.get("watch/providers", {}) or {}).get("results", {})
    if not data:
        return {}
    region = data.get("FR") or next(iter(data.values()), {})
    if not region:
        return {}
    def _fmt(items):
        return [
            {
                "name": p.get("provider_name", ""),
                "logo": f"{_IMG_BASE}/w92{p['logo_path']}" if p.get("logo_path") else None,
            }
            for p in (items or [])
        ]
    return {
        "flatrate": _fmt(region.get("flatrate")),
        "rent": _fmt(region.get("rent")),
        "buy": _fmt(region.get("buy")),
        "link": region.get("link", ""),
    }


def extract_key_crew(crew: list[dict]) -> list[dict]:
    """Flatten the full crew into a "key crew" list, grouped by job and
    ordered by ``KEY_CREW_JOBS``. Deduplicates people holding two roles
    on the same production.
    """
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for job in KEY_CREW_JOBS:
        for c in crew:
            if c.get("job") != job:
                continue
            pair = (c.get("name", ""), job)
            if pair in seen:
                continue
            seen.add(pair)
            out.append({
                "id": c.get("id"),
                "name": c.get("name", ""),
                "job": job,
            })
    return out


def extract_videos(
    videos_payload: dict, language_priority: list[str] | None = None,
) -> list[dict]:
    """Filter and sort the TMDB ``videos.results`` list.

    ``language_priority`` is a list of ISO 639-1 codes, highest priority
    first (typically ``[user_lang, "en", original_lang]``). Videos whose
    ``iso_639_1`` matches an earlier entry rank ahead of later entries;
    language-agnostic uploads come last. Within the same language group,
    ``Trailer`` beats ``Teaser`` beats the rest so the first item is the
    best match for a trailer button. A YouTube thumbnail URL is added to
    each entry.
    """
    prio = [(lang or "").lower() for lang in (language_priority or []) if lang]
    type_order = ["Trailer", "Teaser", "Clip", "Featurette", "Behind the Scenes"]

    def rank(v: dict) -> tuple[int, int]:
        lang = (v.get("iso_639_1") or "").lower()
        lang_rank = prio.index(lang) if lang in prio else len(prio)
        vtype = v.get("type", "")
        type_rank = type_order.index(vtype) if vtype in type_order else len(type_order)
        return (lang_rank, type_rank)

    filtered = [
        v for v in (videos_payload or {}).get("results", [])
        if v.get("site") == "YouTube" and v.get("type") in ALLOWED_VIDEO_TYPES
    ]
    filtered.sort(key=rank)

    return [{
        "key": v["key"],
        "name": v.get("name", ""),
        "type": v.get("type", ""),
        "thumb": f"https://img.youtube.com/vi/{v['key']}/hqdefault.jpg",
    } for v in filtered]


def extract_reviews(reviews_payload: dict, limit: int = 3) -> list[dict]:
    """Keep up to ``limit`` meaningful reviews (≥ 40 chars) so the block
    isn't cluttered with one-word takes.
    """
    out: list[dict] = []
    for r in (reviews_payload or {}).get("results", [])[:10]:
        content = (r.get("content") or "").strip()
        if len(content) < 40:
            continue
        author = (
            r.get("author")
            or (r.get("author_details", {}) or {}).get("username")
            or "Anonymous"
        )
        rating = (r.get("author_details", {}) or {}).get("rating")
        out.append({
            "author": author,
            "date": (r.get("created_at") or "")[:10],
            "rating": rating,
            "content": content,
            "url": r.get("url", ""),
        })
        if len(out) >= limit:
            break
    return out


def extract_studios(companies: list[dict]) -> list[dict]:
    """Return production companies with absolute logo URLs."""
    return [
        {
            "id": s.get("id"),
            "name": s.get("name", ""),
            "logo": f"{_IMG_BASE}/w185{s['logo_path']}" if s.get("logo_path") else None,
        }
        for s in (companies or [])
    ]


async def merge_original_language_videos(
    client, media_type: str, tmdb_id: int, api_key: str,
    detail_payload: dict, primary_lang: str, original_lang: str,
) -> None:
    """Fetch and merge videos in the film's original language in-place.

    TMDB's ``include_video_language`` is a server-side filter, so an
    initial call asking for ``<user>,en,null`` excludes every video in
    the film's native language when that language differs. This helper
    makes the extra ``/{media_type}/{id}/videos`` call and appends new
    entries onto ``detail_payload["videos"]["results"]``, deduped by key.
    """
    if not original_lang or original_lang in (primary_lang, "en"):
        return
    try:
        res = await client.get(
            f"{TMDB_BASE}/{media_type}/{tmdb_id}/videos",
            params={"include_video_language": original_lang},
            headers=_tmdb_headers_sync(api_key),
        )
        if res.status_code != 200:
            return
        extra = res.json().get("results") or []
        payload = detail_payload.setdefault("videos", {})
        existing = payload.get("results") or []
        seen = {v.get("key") for v in existing if v.get("key")}
        payload["results"] = existing + [
            v for v in extra if v.get("key") and v.get("key") not in seen
        ]
    except Exception as exc:
        logger.debug("[DISCOVER] original-lang videos fetch failed: %s", exc)
