"""Full media details, person filmography, and collection retrieval from TMDB."""
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_external_client
from services.portal.discover_details_enrich import (
    extract_key_crew,
    extract_reviews,
    extract_studios,
    extract_videos,
    merge_original_language_videos,
    pick_certification,
    pick_watch_providers,
)
from services.portal.adult_filter import has_adult_keyword
from services.portal.discover_lists import _IMG_BASE, _normalize
from services.portal.runtime_cache import resolve_runtimes
from services.tmdb import _get_tmdb_key, _tmdb_headers_sync, tmdb_language, TMDB_BASE

from ._constants import LANGUAGE, logger


async def get_full_details(
    db: AsyncSession, media_type: str, tmdb_id: int, language: str | None = None,
) -> dict | None:
    """
    Full media details: cast, crew, budget, runtime, etc.
    ``language`` is an ISO 639-1 code (e.g. "fr"); mapped to a TMDB
    ``xx-YY`` code via ``tmdb_language()`` (e.g. "en" -> "en-US"), the
    same canonical helper the rest of the per-viewer i18n path uses.
    """
    api_key = await _get_tmdb_key(db)
    lang = tmdb_language(language)
    try:
        client = get_external_client()
        ratings_field = "release_dates" if media_type == "movie" else "content_ratings"
        primary_lang = lang.split("-")[0]
        video_langs = ",".join(dict.fromkeys([primary_lang, "en", "null"]))
        res = await client.get(
            f"{TMDB_BASE}/{media_type}/{tmdb_id}",
            params={
                "language": lang,
                "include_video_language": video_langs,
                "append_to_response": (
                    "credits,videos,recommendations,"
                    "keywords,reviews,external_ids,watch/providers,"
                    f"{ratings_field}"
                ),
            },
            headers=_tmdb_headers_sync(api_key),
        )
        if res.status_code != 200:
            return None
        d = res.json()

        if not (d.get("overview") or "").strip() and primary_lang != "en":
            try:
                res_en = await client.get(
                    f"{TMDB_BASE}/{media_type}/{tmdb_id}",
                    params={"language": "en-US"},
                    headers=_tmdb_headers_sync(api_key),
                )
                if res_en.status_code == 200:
                    en_overview = (res_en.json().get("overview") or "").strip()
                    if en_overview:
                        d["overview"] = en_overview
            except Exception as exc:
                logger.debug("[DISCOVER] overview en-US fallback failed: %s", exc)

        title = d.get("title") or d.get("name", "")
        date_key = "release_date" if media_type == "movie" else "first_air_date"
        year = d.get(date_key, "")[:4] if d.get(date_key) else ""

        crew = d.get("credits", {}).get("crew", [])
        directors = [
            {"id": c.get("id"), "name": c["name"],
             "photo": f"{_IMG_BASE}/w185{c['profile_path']}" if c.get("profile_path") else None}
            for c in crew if c.get("job") == "Director"
        ]
        key_crew = extract_key_crew(crew)

        cast_raw = d.get("credits", {}).get("cast", [])[:20]
        cast = [{
            "id": c.get("id"),
            "name": c["name"],
            "character": c.get("character", ""),
            "photo": f"{_IMG_BASE}/w185{c['profile_path']}" if c.get("profile_path") else None,
        } for c in cast_raw]

        original_lang = d.get("original_language") or ""
        await merge_original_language_videos(
            client, media_type, tmdb_id, api_key, d, primary_lang, original_lang,
        )
        video_priority = [primary_lang, "en"]
        if original_lang and original_lang not in video_priority:
            video_priority.append(original_lang)
        videos = extract_videos(d.get("videos", {}), language_priority=video_priority)
        recs = [_normalize(r) for r in d.get("recommendations", {}).get("results", [])[:20]]
        await resolve_runtimes(recs)

        kw_payload = d.get("keywords", {}) or {}
        raw_kw = kw_payload.get("keywords") or kw_payload.get("results") or []
        keywords = [k.get("name", "") for k in raw_kw if k.get("name")]
        is_adult = has_adult_keyword(
            {k.get("id") for k in raw_kw if isinstance(k.get("id"), int)}
        )

        reviews = extract_reviews(d.get("reviews", {}))
        studios = extract_studios(d.get("production_companies", []))
        # Expose ISO codes (3166-1 alpha-2) so the frontend can localise the
        # label via ``Intl.DisplayNames``. TMDB only translates a subset of
        # country names — most stay English regardless of the ``language``
        # query parameter.
        country_codes = [
            (c.get("iso_3166_1") or "").upper()
            for c in d.get("production_countries") or []
            if c.get("iso_3166_1")
        ]

        external = d.get("external_ids", {}) or {}

        result = {
            "id": d.get("id"),
            "tmdb_id": d.get("id"),
            "title": title,
            "original_title": d.get("original_title") or d.get("original_name", ""),
            "year": year,
            "overview": d.get("overview", ""),
            "poster": f"{_IMG_BASE}/w500{d['poster_path']}" if d.get("poster_path") else "",
            "backdrop": f"{_IMG_BASE}/w1280{d['backdrop_path']}" if d.get("backdrop_path") else "",
            "vote": round(d.get("vote_average", 0), 1),
            "vote_count": d.get("vote_count", 0),
            "popularity": round(d.get("popularity", 0), 1),
            "genres": [g.get("name", "") for g in d.get("genres", [])],
            "media_type": media_type,
            "is_adult": is_adult,
            "directors": directors,
            "key_crew": key_crew,
            "cast": cast,
            "videos": videos,
            "recommendations": recs,
            "tagline": d.get("tagline", ""),
            "keywords": keywords,
            "reviews": reviews,
            "watch_providers": pick_watch_providers(d),
            "studios": studios,
            "country_codes": country_codes,
            "original_language": d.get("original_language", ""),
            "homepage": d.get("homepage", ""),
            "imdb_id": external.get("imdb_id", ""),
            "certification": pick_certification(d, media_type),
        }

        collection = d.get("belongs_to_collection")
        if collection:
            result["collection"] = {
                "id": collection.get("id"),
                "name": collection.get("name", ""),
                "poster": f"{_IMG_BASE}/w300{collection['poster_path']}" if collection.get("poster_path") else None,
                "backdrop": f"{_IMG_BASE}/w780{collection['backdrop_path']}" if collection.get("backdrop_path") else None,
            }

        if media_type == "movie":
            result["runtime"] = d.get("runtime", 0)
            result["budget"] = d.get("budget", 0)
            result["revenue"] = d.get("revenue", 0)
            result["release_date"] = d.get("release_date", "")
            result["status"] = d.get("status", "")
        else:
            result["seasons_count"] = d.get("number_of_seasons", 0)
            result["episodes_count"] = d.get("number_of_episodes", 0)
            result["status"] = d.get("status", "")
            result["networks"] = [n.get("name", "") for n in d.get("networks", [])]
            result["created_by"] = [c.get("name", "") for c in d.get("created_by", [])]

        return result
    except Exception as e:
        logger.error(
            "[DISCOVER] Error get_full_details(%s/%s): %s", media_type, tmdb_id, e,
        )
        return None


async def get_person_filmography(
    db: AsyncSession, person_id: int,
    role: str = "all", media_filter: str = "all",
    *, language: str | None = None,
) -> dict:
    """Return a person's full filmography (as director or as cast).

    ``role`` = "director" | "acting" | "all"
    ``media_filter`` = "movie" | "tv" | "all"
    """
    api_key = await _get_tmdb_key(db)
    try:
        client = get_external_client()
        res_info = await client.get(
            f"{TMDB_BASE}/person/{person_id}",
            params={"language": language or LANGUAGE},
            headers=_tmdb_headers_sync(api_key),
        )
        res_credits = await client.get(
            f"{TMDB_BASE}/person/{person_id}/combined_credits",
            params={"language": language or LANGUAGE},
            headers=_tmdb_headers_sync(api_key),
        )
        info = res_info.json() if res_info.status_code == 200 else {}
        creds = res_credits.json() if res_credits.status_code == 200 else {}

        items = []
        if role in ("all", "acting"):
            items += creds.get("cast", [])
        if role in ("all", "director"):
            items += [c for c in creds.get("crew", []) if c.get("job") == "Director"]

        if media_filter in ("movie", "tv"):
            items = [i for i in items if i.get("media_type") == media_filter]

        seen: dict = {}
        for it in items:
            key = (it.get("id"), it.get("media_type"))
            if key not in seen or (it.get("popularity") or 0) > (seen[key].get("popularity") or 0):
                seen[key] = it
        items = sorted(seen.values(), key=lambda x: x.get("popularity", 0), reverse=True)
        normalized = [_normalize(i) for i in items]
        await resolve_runtimes(normalized)

        return {
            "person": {
                "id": info.get("id"),
                "name": info.get("name", ""),
                "photo": f"{_IMG_BASE}/w300{info['profile_path']}" if info.get("profile_path") else None,
                "biography": info.get("biography", ""),
                "known_for": info.get("known_for_department", ""),
            },
            "items": normalized,
        }
    except Exception as e:
        logger.error("[DISCOVER] person filmography error: %s", e)
        return {"person": None, "items": []}


async def get_collection(
    db: AsyncSession, collection_id: int, *, language: str | None = None,
) -> dict:
    """Return the parts of a TMDB collection (franchise)."""
    api_key = await _get_tmdb_key(db)
    try:
        client = get_external_client()
        res = await client.get(
            f"{TMDB_BASE}/collection/{collection_id}",
            params={"language": language or LANGUAGE},
            headers=_tmdb_headers_sync(api_key),
        )
        if res.status_code != 200:
            return {"collection": None, "items": []}
        d = res.json()
        items = sorted(d.get("parts", []), key=lambda x: x.get("release_date") or "")
        parts = [_normalize(i) for i in items]
        await resolve_runtimes(parts)
        return {
            "collection": {
                "id": d.get("id"),
                "name": d.get("name", ""),
                "overview": d.get("overview", ""),
                "poster": f"{_IMG_BASE}/w500{d['poster_path']}" if d.get("poster_path") else None,
                "backdrop": f"{_IMG_BASE}/w1280{d['backdrop_path']}" if d.get("backdrop_path") else None,
            },
            "items": parts,
        }
    except Exception as e:
        logger.error("[DISCOVER] collection error: %s", e)
        return {"collection": None, "items": []}
