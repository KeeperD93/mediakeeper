"""Statistics title cards: most watched = time actually spent, popular = distinct
viewers past the watch threshold (most recently watched first on a tie), and the
period buttons apply to every card, Top watchers included."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from models.playback_stats import PlaybackSession
from services.stats import add_exclusion
from services.stats_aggregator.playback import get_playback_stats

TICK = 10_000_000  # 1 second in Emby ticks
NOW = datetime.now(timezone.utc)


def _play(key, *, user, item_id, name, started, kind="Movie", series=None, pct=0.95,
          runtime_s=3600, watched_s=None, exclusive_s=None):
    runtime = runtime_s * TICK
    watched = int(runtime_s * pct) if watched_s is None else watched_s
    return PlaybackSession(
        session_key=key, user_id=user, user_name=user, item_id=item_id, item_name=name,
        item_type=kind, series_name=series, duration_ticks=runtime,
        position_ticks=int(runtime * pct), started_at=started, last_seen_at=started,
        ended_at=started + timedelta(seconds=watched), is_active=False,
        watched_seconds=watched, exclusive_seconds=watched if exclusive_s is None else exclusive_s,
    )


def _names(rows):
    return [r["name"] for r in rows]


@pytest.mark.asyncio
async def test_series_most_watched_by_time_popular_by_viewers(db_session):
    """A binge by one viewer leads the time list, a series several people
    watched leads the popular list: the two cards differ."""
    day = NOW - timedelta(days=1)
    db_session.add_all([
        _play(f"binge-{i}", user="viewer-a", item_id=f"b{i}", name=f"Binge episode {i}",
              kind="Episode", series="Binge series", started=day + timedelta(hours=i), runtime_s=3000)
        for i in range(12)
    ])
    db_session.add_all([
        _play(f"shared-{u}", user=u, item_id="s1", name="Shared episode", kind="Episode",
              series="Shared series", started=day, runtime_s=3000)
        for u in ("viewer-a", "viewer-b", "viewer-c")
    ])
    await db_session.commit()

    stats = await get_playback_stats(db_session, days=0)

    assert _names(stats["top_series"]) == ["Binge series", "Shared series"]
    assert stats["top_series"][0]["ticks"] == 12 * int(3000 * 0.95) * TICK
    assert _names(stats["popular_series"]) == ["Shared series", "Binge series"]
    assert stats["popular_series"][0]["users"] == 3


@pytest.mark.asyncio
async def test_movie_time_counts_rewatches_and_unfinished_sittings(db_session):
    day = NOW - timedelta(days=2)
    db_session.add_all([
        # Seen once by two people.
        _play("a1", user="viewer-a", item_id="m-a", name="Movie A", started=day, watched_s=3600),
        _play("a2", user="viewer-b", item_id="m-a", name="Movie A", started=day, watched_s=3600),
        # One person: two full viewings and a third stopped halfway.
        _play("b1", user="viewer-c", item_id="m-b", name="Movie B", started=day, watched_s=3600),
        _play("b2", user="viewer-c", item_id="m-b", name="Movie B", started=day, watched_s=3600),
        _play("b3", user="viewer-c", item_id="m-b", name="Movie B", started=day, pct=0.5, watched_s=1800),
    ])
    await db_session.commit()

    stats = await get_playback_stats(db_session, days=0)

    top = {m["name"]: m["ticks"] for m in stats["top_movies"]}
    assert top == {"Movie B": 9000 * TICK, "Movie A": 7200 * TICK}
    assert _names(stats["top_movies"]) == ["Movie B", "Movie A"]
    popular = {m["name"]: m["users"] for m in stats["popular_movies"]}
    assert popular == {"Movie A": 2, "Movie B": 1}
    assert _names(stats["popular_movies"]) == ["Movie A", "Movie B"]


@pytest.mark.asyncio
async def test_popular_tie_goes_to_the_most_recently_watched_then_the_name(db_session):
    db_session.add_all([
        _play("old", user="viewer-a", item_id="m-1", name="Alpha", started=NOW - timedelta(days=3)),
        _play("new", user="viewer-a", item_id="m-2", name="Zulu", started=NOW - timedelta(days=1)),
        _play("same-1", user="viewer-b", item_id="m-3", name="Charlie", started=NOW - timedelta(days=5)),
        _play("same-2", user="viewer-b", item_id="m-4", name="Bravo", started=NOW - timedelta(days=5)),
    ])
    await db_session.commit()

    stats = await get_playback_stats(db_session, days=0)

    assert _names(stats["popular_movies"]) == ["Zulu", "Alpha", "Bravo", "Charlie"]


@pytest.mark.asyncio
async def test_untimed_and_sampled_titles_stay_out_of_their_lists(db_session):
    day = NOW - timedelta(days=1)
    db_session.add_all([
        # Seen to the end but no measured time (older estimate at 0): no time.
        _play("untimed", user="viewer-a", item_id="m-u", name="Untimed", started=day, watched_s=0),
        # Sampled for a few minutes: some time, but nobody watched it.
        _play("sample", user="viewer-b", item_id="m-s", name="Sampled", started=day, pct=0.1),
    ])
    await db_session.commit()

    stats = await get_playback_stats(db_session, days=0)

    assert _names(stats["top_movies"]) == ["Sampled"]
    assert _names(stats["popular_movies"]) == ["Untimed"]


@pytest.mark.asyncio
async def test_period_and_exclusions_apply_to_every_card(db_session):
    db_session.add_all([
        _play("recent", user="viewer-a", item_id="m-r", name="Recent movie", started=NOW - timedelta(days=2)),
        _play("old", user="viewer-b", item_id="m-o", name="Old movie", started=NOW - timedelta(days=40),
              exclusive_s=99_000),
        _play("hidden", user="viewer-a", item_id="m-h", name="Hidden movie", started=NOW - timedelta(days=2)),
        _play("ep", user="viewer-a", item_id="e-1", name="Old episode", kind="Episode",
              series="Old series", started=NOW - timedelta(days=40)),
        # Music only: playback time, but no watch time.
        _play("song", user="listener", item_id="a-1", name="Song", kind="Audio",
              started=NOW - timedelta(days=2), exclusive_s=0),
    ])
    await db_session.commit()
    await add_exclusion(db_session, "exact", "Hidden movie")

    recent = await get_playback_stats(db_session, days=30)
    for card in ("top_movies", "popular_movies"):
        assert _names(recent[card]) == ["Recent movie"]
    assert recent["top_series"] == [] and recent["popular_series"] == []
    # Top watchers follows the period too: the 40-day-old viewer is gone, and
    # the listener, without any watch time, never counts.
    assert [u["user_id"] for u in recent["top_users_hours"]] == ["viewer-a"]
    # The hidden movie's time does not count either.
    assert recent["top_users_hours"][0]["ticks"] == 3420 * TICK

    everything = await get_playback_stats(db_session, days=0)
    assert set(_names(everything["top_movies"])) == {"Recent movie", "Old movie"}
    assert _names(everything["top_series"]) == ["Old series"]
    assert [u["user_id"] for u in everything["top_users_hours"]] == ["viewer-b", "viewer-a"]
