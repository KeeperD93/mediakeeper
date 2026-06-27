"""get_profile_full re-resolves the profile carousels (recent watches,
next-to-finish, my requests) to the viewer locale."""
import pytest
from unittest.mock import AsyncMock, patch

from services.portal import profile_stats
from models.user import User
from models.portal.profile import UserProfile


async def _seed(db_session, username):
    user = User(username=username, hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    profile = UserProfile(
        user_id=user.id, display_name=username, role="viewer", account_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    return user, profile


def _trivial_stats():
    """AsyncMocks for the non-carousel aggregation coroutines so the test
    drives only the localized lists."""
    return dict(
        compute_totals=AsyncMock(return_value=(0, 0)),
        _compute_streak=AsyncMock(return_value=0),
        compute_record_day=AsyncMock(return_value={}),
        compute_most_rewatched=AsyncMock(return_value=(None, None, None)),
        compute_genre_stats=AsyncMock(return_value=[]),
        compute_day_stats=AsyncMock(return_value=None),
        compute_longest_session=AsyncMock(return_value=0),
        compute_media_type_ratio=AsyncMock(return_value={}),
        compute_hour_buckets=AsyncMock(return_value=[]),
        compute_record_month=AsyncMock(return_value={}),
        compute_ranking=AsyncMock(return_value={}),
    )


@pytest.mark.asyncio
async def test_profile_full_localizes_carousels(db_session):
    user, profile = await _seed(db_session, "loc_profile_en")
    recent = [{"title": "Le Roi", "tmdb_id": 1, "media_type": "movie"}]
    nxt = [{"title": "La Serie", "tmdb_id": 2, "media_type": "tv"}]
    reqs = [{"title": "Demande", "tmdb_id": 3, "media_type": "movie"}]

    async def fake_detail(media_type, tmdb_id, db, locale):
        return {"title": f"EN-{tmdb_id}"}

    with (
        patch.multiple(
            profile_stats,
            fetch_recent_watches=AsyncMock(return_value=recent),
            fetch_next_to_finish=AsyncMock(return_value=nxt),
            fetch_my_requests=AsyncMock(return_value=reqs),
            **_trivial_stats(),
        ),
        patch("services.portal.media_title_localize._get_tmdb_key", AsyncMock(return_value="k")),
        patch("services.portal.media_title_localize.get_media_detail",
              AsyncMock(side_effect=fake_detail)),
    ):
        out = await profile_stats.get_profile_full(db_session, user, profile, lang="en")

    assert out["recent_watches"][0]["title"] == "EN-1"
    assert out["next_to_finish"][0]["title"] == "EN-2"
    assert out["my_requests"][0]["title"] == "EN-3"


@pytest.mark.asyncio
async def test_profile_full_default_locale_serves_stored_titles(db_session):
    """Default locale → titles kept as-is, no TMDB re-resolution call."""
    user, profile = await _seed(db_session, "loc_profile_fr")
    recent = [{"title": "Le Roi", "tmdb_id": 1, "media_type": "movie"}]
    spy = AsyncMock(side_effect=AssertionError("no TMDB call for the default locale"))

    with (
        patch.multiple(
            profile_stats,
            fetch_recent_watches=AsyncMock(return_value=recent),
            fetch_next_to_finish=AsyncMock(return_value=[]),
            fetch_my_requests=AsyncMock(return_value=[]),
            **_trivial_stats(),
        ),
        patch("services.portal.media_title_localize._get_tmdb_key", AsyncMock(return_value="k")),
        patch("services.portal.media_title_localize.get_media_detail", spy),
    ):
        out = await profile_stats.get_profile_full(db_session, user, profile, lang="fr")

    assert out["recent_watches"][0]["title"] == "Le Roi"
