"""Counting rules for Top 20, Top genre and the 85% watch threshold.

Covers:
  - Bug #7  — Top 20: a series watched as N episodes by a single user
              must contribute 1, not N (count distinct viewers).
  - Bug #12 — Sub-85% sessions never qualify (movies and episodes).
  - Bug #16 — Top genre: a series binged by one user counts +1 per
              genre, not +N where N is the number of episodes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from api.portal.top20 import get_top20
from models.playback_stats import PlaybackSession
from models.portal.profile import UserProfile
from models.user import User
from services.portal.profile_stats_viewing import compute_genre_stats

TICK = 10_000_000  # 1 second in Emby ticks
RUNTIME_HOUR = 3600 * TICK


async def _make_profile(
    db_session, *, username: str, emby_user_id: str = "EMBY-1",
) -> tuple[User, UserProfile]:
    user = User(
        username=username,
        hashed_password="x",
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
        account_active=True,
        emby_user_id=emby_user_id,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile


def _movie(
    *,
    session_key: str,
    user_id: str,
    user_name: str,
    item_id: str,
    item_name: str,
    started_at: datetime,
    watched_pct: float = 0.95,
    runtime_ticks: int = RUNTIME_HOUR,
    genres: str | None = None,
) -> PlaybackSession:
    return PlaybackSession(
        session_key=session_key,
        user_id=user_id,
        user_name=user_name,
        item_id=item_id,
        item_name=item_name,
        item_type="Movie",
        duration_ticks=runtime_ticks,
        position_ticks=int(runtime_ticks * watched_pct),
        started_at=started_at,
        last_seen_at=started_at,
        ended_at=started_at + timedelta(seconds=int(runtime_ticks // TICK)),
        is_active=False,
        genres=genres,
    )


def _episode(
    *,
    session_key: str,
    user_id: str,
    user_name: str,
    item_id: str,
    item_name: str,
    series_name: str,
    started_at: datetime,
    watched_pct: float = 0.95,
    runtime_ticks: int = RUNTIME_HOUR,
    genres: str | None = None,
) -> PlaybackSession:
    return PlaybackSession(
        session_key=session_key,
        user_id=user_id,
        user_name=user_name,
        item_id=item_id,
        item_name=item_name,
        item_type="Episode",
        series_name=series_name,
        duration_ticks=runtime_ticks,
        position_ticks=int(runtime_ticks * watched_pct),
        started_at=started_at,
        last_seen_at=started_at,
        ended_at=started_at + timedelta(seconds=int(runtime_ticks // TICK)),
        is_active=False,
        genres=genres,
    )


@pytest.fixture
def now_in_month():
    """A timestamp guaranteed to land inside the current month so the
    ``started_at >= month_start`` filter accepts every fixture row."""
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=12, minute=0, second=0, microsecond=0) + timedelta(hours=1)


# ---------------------------------------------------------------------------
# Bug #7 — distinct counting in Top 20
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_top20_counts_series_once_per_user_month(db_session, now_in_month):
    user, profile = await _make_profile(db_session, username="alice")
    base = now_in_month
    db_session.add_all([
        _episode(
            session_key=f"S1-EP{i}",
            user_id="EMBY-1",
            user_name="alice",
            item_id=f"EP-{i}",
            item_name=f"Episode {i}",
            series_name="Show A",
            started_at=base + timedelta(minutes=i),
        )
        for i in range(3)
    ])
    db_session.add(_movie(
        session_key="MOV-B",
        user_id="EMBY-1",
        user_name="alice",
        item_id="MOVIE-B",
        item_name="Film B",
        started_at=base + timedelta(hours=2),
    ))
    await db_session.commit()

    with patch(
        "api.portal.top20.get_active_media_source",
        new=AsyncMock(return_value=None),
    ), patch(
        "api.portal.top20.get_emby_public_url", return_value=""
    ), patch(
        "api.portal.top20.get_emby_server_id",
        new=AsyncMock(return_value=""),
    ), patch(
        "api.portal.top20.build_emby_deep_link", return_value=""
    ):
        result = await get_top20(up=(user, profile), db=db_session)

    counts = {(it["title"], it["media_type"]): it["play_count"] for it in result["items"]}
    assert counts == {("Show A", "tv"): 1, ("Film B", "movie"): 1}


# ---------------------------------------------------------------------------
# Bug #12 — sub-85% sessions are dropped (movies + episodes)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_top20_skips_movie_under_85pct(db_session, now_in_month):
    user, profile = await _make_profile(db_session, username="bob", emby_user_id="EMBY-2")
    base = now_in_month
    db_session.add(_movie(
        session_key="MOV-LOW",
        user_id="EMBY-2",
        user_name="bob",
        item_id="MOVIE-LOW",
        item_name="Sampled Film",
        started_at=base,
        watched_pct=0.80,
    ))
    db_session.add(_movie(
        session_key="MOV-HIGH",
        user_id="EMBY-2",
        user_name="bob",
        item_id="MOVIE-HIGH",
        item_name="Finished Film",
        started_at=base + timedelta(minutes=10),
        watched_pct=0.90,
    ))
    await db_session.commit()

    with patch(
        "api.portal.top20.get_active_media_source",
        new=AsyncMock(return_value=None),
    ), patch(
        "api.portal.top20.get_emby_public_url", return_value=""
    ), patch(
        "api.portal.top20.get_emby_server_id",
        new=AsyncMock(return_value=""),
    ), patch(
        "api.portal.top20.build_emby_deep_link", return_value=""
    ):
        result = await get_top20(up=(user, profile), db=db_session)

    titles = [it["title"] for it in result["items"]]
    assert titles == ["Finished Film"]


@pytest.mark.asyncio
async def test_top20_skips_episode_under_85pct(db_session, now_in_month):
    user, profile = await _make_profile(db_session, username="carol", emby_user_id="EMBY-3")
    base = now_in_month
    # Two episodes well above threshold + one well below.
    db_session.add_all([
        _episode(
            session_key="C-EP-1",
            user_id="EMBY-3",
            user_name="carol",
            item_id="EP-1",
            item_name="E1",
            series_name="Show C",
            started_at=base,
            watched_pct=0.95,
        ),
        _episode(
            session_key="C-EP-2",
            user_id="EMBY-3",
            user_name="carol",
            item_id="EP-2",
            item_name="E2",
            series_name="Show C",
            started_at=base + timedelta(minutes=30),
            watched_pct=0.90,
        ),
        _episode(
            session_key="C-EP-3",
            user_id="EMBY-3",
            user_name="carol",
            item_id="EP-3",
            item_name="E3",
            series_name="Show C",
            started_at=base + timedelta(hours=1),
            watched_pct=0.50,
        ),
    ])
    await db_session.commit()

    with patch(
        "api.portal.top20.get_active_media_source",
        new=AsyncMock(return_value=None),
    ), patch(
        "api.portal.top20.get_emby_public_url", return_value=""
    ), patch(
        "api.portal.top20.get_emby_server_id",
        new=AsyncMock(return_value=""),
    ), patch(
        "api.portal.top20.build_emby_deep_link", return_value=""
    ):
        result = await get_top20(up=(user, profile), db=db_session)

    counts = {(it["title"], it["media_type"]): it["play_count"] for it in result["items"]}
    assert counts == {("Show C", "tv"): 1}


# ---------------------------------------------------------------------------
# Bug #16 — genres credited once per (user × media), not per session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_top_genre_counts_series_once(db_session, now_in_month):
    user, profile = await _make_profile(db_session, username="dora", emby_user_id="EMBY-4")
    base = now_in_month
    # Series with two genres watched as 10 episodes — must credit each
    # genre +1, not +10.
    db_session.add_all([
        _episode(
            session_key=f"D-EP-{i}",
            user_id="EMBY-4",
            user_name="dora",
            item_id=f"EP-D-{i}",
            item_name=f"E{i}",
            series_name="Show D",
            started_at=base + timedelta(minutes=i * 5),
            genres="Comedy,Drama",
        )
        for i in range(10)
    ])
    # One movie tagged Comedy — adds +1 to Comedy only.
    db_session.add(_movie(
        session_key="D-MOV",
        user_id="EMBY-4",
        user_name="dora",
        item_id="MOVIE-D",
        item_name="Funny Film",
        started_at=base + timedelta(hours=3),
        genres="Comedy",
    ))
    await db_session.commit()

    stats = await compute_genre_stats(db_session, user, profile)

    by_id = {row["id"]: row["count"] for row in stats}
    # Comedy = 35 (1 series + 1 movie), Drama = 18 (1 series only).
    assert by_id == {35: 2, 18: 1}
