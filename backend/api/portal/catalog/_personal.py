"""Personal endpoints: recommendations, history, my requests, profile."""
import logging
import traceback

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile
from core.database import get_db
from core.i18n import get_request_locale
from models.portal.profile import UserProfile
from models.user import User
from services.portal.adult_filter import drop_adult

logger = logging.getLogger("mediakeeper.portal.discover")
router = APIRouter()


@router.get("/recommended-for-me")
async def recommended_for_me(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    from services.portal.personal import get_recommendations_for_user
    user, profile = up
    try:
        return {"items": await get_recommendations_for_user(db, user, profile, locale=locale)}
    except Exception as e:
        logger.error("[RECO] recommended-for-me failed: %s", e)
        return {"items": []}


@router.get("/watch-history")
async def watch_history(
    page: int = Query(1, ge=1, le=500),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Paginated watch history for the current user."""
    from services.portal.profile_stats import get_watch_history_paginated
    user, profile = up
    try:
        return await get_watch_history_paginated(db, user, profile, page=page)
    except Exception as e:
        logger.error("[WATCH-HISTORY] error: %s", e)
        return {"items": [], "page": page, "has_more": False}


@router.get("/my-requests")
async def my_requests(
    page: int = Query(1, ge=1, le=500),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Paginated requests for the current user."""
    from services.portal.profile_stats import get_my_requests_paginated
    user, profile = up
    try:
        return await get_my_requests_paginated(db, user, page=page)
    except Exception as e:
        logger.error("[MY-REQUESTS] error: %s", e)
        return {"items": [], "page": page, "has_more": False}


@router.get("/profile-full")
async def profile_full(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_request_locale),
):
    """
    Aggregated profile page data: playback stats, genre radar, recent
    watches, user requests — all in one call. Metadata language follows
    the viewer's active locale (X-MK-Locale).
    """
    from services.portal.profile_stats import get_profile_full
    user, profile = up
    try:
        return await get_profile_full(db, user, profile, lang=lang)
    except Exception as e:
        logger.error("[PROFILE-FULL] failed for user=%s: %s\n%s", user.id, e, traceback.format_exc())
        return {
            "stats": {"total_plays": 0, "total_minutes": 0, "streak": 0,
                      "record_day": {"date": None, "count": 0},
                      "most_rewatched": None, "top_genres": []},
            "recent_watches": [],
            "my_requests": [],
        }


@router.get("/recommendations-full")
async def recommendations_full(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    """
    Premium recommendations page: reuses the proven home-page
    recommendation engine and enriches it with playback stats +
    genre IDs so the frontend can build the curated page.
    """
    from services.portal.personal import (
        _count_total_plays,
        _infer_genres_from_history_full,
        get_recommendations_for_user,
    )
    user, profile = up
    try:
        items = await get_recommendations_for_user(db, user, profile, locale=locale)
        logger.info("[RECO-FULL] user=%s got %s items from base engine", user.id, len(items))

        total_plays = await _count_total_plays(db, user, profile)
        inferred_primary, inferred_all = await _infer_genres_from_history_full(db, user, profile)

        total_weight = sum(inferred_all.values()) or 1
        genre_stats = [
            {"id": gid, "percentage": round(100 * w / total_weight)}
            for gid, w in inferred_all.most_common(6)
        ]

        if items:
            from services.portal.discover import _fetch_list_params
            from services.portal.personal import _get_indexed_tmdb_ids

            merged_genres = inferred_primary[:5]
            if not merged_genres and items:
                merged_genres = (items[0].get("genres") or [])[:3]

            if merged_genres:
                include_adult = not bool(profile.hide_adult)
                extra_params = {
                    # OR (``|``): ``,`` is AND and collapses to ~0 results past 2-3 genres.
                    "with_genres": "|".join(str(g) for g in merged_genres),
                    "sort_by": "popularity.desc",
                    "vote_count.gte": "200",
                }
                idx_m = await _get_indexed_tmdb_ids(db, "movie")
                idx_t = await _get_indexed_tmdb_ids(db, "tv")
                seen = {it.get("tmdb_id") or it.get("id") for it in items}

                for page in (2, 3):
                    for mt, idx in [("/discover/movie", idx_m), ("/discover/tv", idx_t)]:
                        extra = await _fetch_list_params(
                            db, mt, page, extra_params,
                            include_adult=include_adult, language=locale,
                        )
                        for it in extra:
                            tid = it.get("tmdb_id")
                            if tid and tid not in seen and tid not in idx:
                                items.append(it)
                                seen.add(tid)
                                if len(items) >= 60:
                                    break
                    if len(items) >= 60:
                        break

        hero = items[0] if items else None
        return {
            "hero": hero,
            "stats": {"total_plays": total_plays, "top_genres": genre_stats},
            "items": items,
            "genre_ids": inferred_primary[:5],
        }
    except Exception as e:
        logger.error("[RECO-FULL] failed for user=%s: %s\n%s", user.id, e, traceback.format_exc())
        return {"hero": None, "stats": {"total_plays": 0, "top_genres": []}, "items": [], "genre_ids": []}


@router.get("/because-you-watched")
async def because_you_watched(
    media_type: str | None = Query(None, pattern="^(movie|tv)$"),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    from services.portal.personal import get_because_you_watched
    user, profile = up
    try:
        result = await get_because_you_watched(db, user, profile, media_type_filter=media_type)
        result["items"] = drop_adult(result.get("items"), bool(profile.hide_adult))
        return result
    except Exception as e:
        logger.error("[RECO] because-you-watched failed: %s", e)
        return {"pivot": None, "items": []}


@router.get("/preferences-based")
async def preferences_based(
    page: int = Query(1, ge=1, le=50),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    """TMDB discover mixed by the user's ticked favorite genres."""
    from services.portal.preferences_based import get_preferences_based
    user, profile = up
    try:
        return await get_preferences_based(db, profile, page=page, locale=locale)
    except Exception as e:
        logger.error("[RECO] preferences-based failed: %s", e)
        return {"items": [], "page": page, "has_more": False}


@router.get("/recommended-full")
async def recommended_full_paginated(
    page: int = Query(1, ge=1, le=50),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    """Paginated view of the "Recommended for you" list — serves the
    dedicated category page opened from the profile carousel."""
    from services.portal.personal import get_recommendations_for_user
    from services.portal.discover import _fetch_list_params
    user, profile = up
    PAGE_SIZE = 40
    try:
        base = await get_recommendations_for_user(db, user, profile, locale=locale)
        if not base:
            return {"items": [], "page": page, "has_more": False}
        # Extend with popularity-ordered discover pages matching the
        # user's inferred top genres, de-duped and filtered to exclude
        # indexed TMDB ids already surfaced as "available" elsewhere.
        from services.portal.personal import _infer_genres_from_history_full
        inferred_primary, _ = await _infer_genres_from_history_full(db, user, profile)
        merged_genres = inferred_primary[:5]
        if not merged_genres:
            merged_genres = (base[0].get("genres") or [])[:3]
        include_adult = not bool(profile.hide_adult)
        seen = {it.get("tmdb_id") for it in base if it.get("tmdb_id")}
        pool = list(base)
        # Full browse page: we want the whole catalogue of matches so
        # the user can scroll through their personalised wall. Unlike
        # the home reco row we keep items that already live on Emby —
        # the card just switches to a "Playback" pill instead of "Request".
        if merged_genres:
            # OR semantics — TMDB treats ``,`` as AND (must contain ALL
            # genres), which yields zero results for users whose top
            # interests span more than 2-3 categories. ``|`` is the OR
            # operator and gives a much broader pool to paginate.
            extra_params = {
                "with_genres": "|".join(str(g) for g in merged_genres),
                "sort_by": "popularity.desc",
                "vote_count.gte": "100",
            }
            for tp in (2, 3, 4, 5, 6, 7, 8):
                for mt in ("/discover/movie", "/discover/tv"):
                    extra = await _fetch_list_params(
                        db, mt, tp, extra_params,
                        include_adult=include_adult, language=locale,
                    )
                    for it in extra:
                        tid = it.get("tmdb_id")
                        if tid and tid not in seen:
                            pool.append(it)
                            seen.add(tid)
                if len(pool) >= 300:
                    break
        start = (page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        return {"items": pool[start:end], "page": page, "has_more": len(pool) > end}
    except Exception as e:
        logger.error("[RECO] recommended-full failed: %s", e)
        return {"items": [], "page": page, "has_more": False}
