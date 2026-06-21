"""Activity-history row serialization (progress + session-duration data)
and the ephemeral exclude-users display filter."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from models.playback_stats import PlaybackSession
from services.stats_aggregator.activity import (
    _activity_row_to_dict,
    get_activity_grouped,
    get_activity_history,
    get_activity_users,
)


def _ticks(minutes: float) -> int:
    return int(minutes * 60 * 1e7)  # Emby uses 100ns ticks (1e7 per second)


def _row(**kw) -> PlaybackSession:
    base = dict(
        id=1, session_key="k", user_id="u1", user_name="Alice",
        item_id="m1", item_name="Film", item_type="Movie",
    )
    base.update(kw)
    return PlaybackSession(**base)


def test_activity_row_exposes_position_and_runtime():
    d = _activity_row_to_dict(_row(duration_ticks=_ticks(114), position_ticks=_ticks(89)))
    assert d["runtime_ticks"] == _ticks(114)  # total media length
    assert d["position_ticks"] == _ticks(89)  # how far the session reached


def test_session_ticks_is_the_active_span():
    start = datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc)
    d = _activity_row_to_dict(_row(
        duration_ticks=_ticks(62.5), position_ticks=_ticks(55),
        started_at=start, last_seen_at=start + timedelta(minutes=25),
    ))
    # The session lasted 25 min even though it reached the 55-min mark (resume).
    assert d["session_ticks"] == _ticks(25)


def test_session_ticks_capped_at_runtime_for_never_closed_sessions():
    start = datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc)
    d = _activity_row_to_dict(_row(
        duration_ticks=_ticks(60), position_ticks=_ticks(60),
        started_at=start, last_seen_at=start + timedelta(days=2),  # ghost session
    ))
    assert d["session_ticks"] == _ticks(60)  # capped at the media runtime


def test_runtime_and_session_default_to_zero_when_unknown():
    d = _activity_row_to_dict(_row(duration_ticks=None, position_ticks=_ticks(5)))
    assert d["runtime_ticks"] == 0
    assert d["session_ticks"] == 0  # no timestamps -> no span


@pytest.mark.asyncio
async def test_get_activity_history_excludes_users(db_session):
    db_session.add_all([
        _row(id=1, session_key="s1", user_id="A", user_name="Admin"),
        _row(id=2, session_key="s2", user_id="A", user_name="Admin"),
        _row(id=3, session_key="s3", user_id="B", user_name="Bob"),
    ])
    await db_session.commit()

    full = await get_activity_history(db_session)
    assert full["total"] == 3

    filtered = await get_activity_history(db_session, exclude_users="A")
    assert filtered["total"] == 1
    assert [it["user_id"] for it in filtered["items"]] == ["B"]


@pytest.mark.asyncio
async def test_get_activity_history_ignores_empty_exclude(db_session):
    db_session.add(_row(id=1, session_key="s1", user_id="A", user_name="Admin"))
    await db_session.commit()
    res = await get_activity_history(db_session, exclude_users="")
    assert res["total"] == 1


@pytest.mark.asyncio
async def test_search_matches_like_wildcards_literally(db_session):
    # #341: the search box must treat % and _ as literal characters, not SQL
    # LIKE wildcards. autoescape emits an ESCAPE clause so this holds on SQLite
    # too (Postgres defaults to backslash; SQLite has no default escape).
    db_session.add_all([
        _row(id=1, session_key="w1", item_name="50% off"),
        _row(id=2, session_key="w2", item_name="5000 off"),   # '%' wildcard would catch this
        _row(id=3, session_key="w3", item_name="john_doe"),
        _row(id=4, session_key="w4", item_name="johnXdoe"),    # '_' wildcard would catch this
    ])
    await db_session.commit()

    percent = await get_activity_history(db_session, search="50% off")
    assert [it["title"] for it in percent["items"]] == ["50% off"]

    underscore = await get_activity_history(db_session, search="john_doe")
    assert [it["title"] for it in underscore["items"]] == ["john_doe"]


@pytest.mark.asyncio
async def test_get_activity_users_returns_distinct(db_session):
    db_session.add_all([
        _row(id=1, session_key="s1", user_id="A", user_name="Admin"),
        _row(id=2, session_key="s2", user_id="A", user_name="Admin"),
        _row(id=3, session_key="s3", user_id="B", user_name="Bob"),
    ])
    await db_session.commit()
    users = await get_activity_users(db_session)
    assert {u["id"] for u in users} == {"A", "B"}
    assert {u["name"] for u in users} == {"Admin", "Bob"}


@pytest.mark.asyncio
async def test_grouped_merges_consecutive_same_content(db_session):
    db_session.add_all([
        _row(id=5, session_key="g5", user_id="A", item_id="f1"),
        _row(id=4, session_key="g4", user_id="A", item_id="f1"),
        _row(id=3, session_key="g3", user_id="B", item_id="f2"),
        _row(id=2, session_key="g2", user_id="A", item_id="f1"),
        _row(id=1, session_key="g1", user_id="A", item_id="f1"),
    ])
    await db_session.commit()
    res = await get_activity_grouped(db_session, limit=25)
    assert res["total"] == 5
    # [5,4] / [3] / [2,1] — the interleaved user B splits the A/f1 run
    assert [it["session_count"] for it in res["items"]] == [2, 1, 2]
    assert res["items"][0]["user_id"] == "A"
    assert len(res["items"][0]["sessions"]) == 2
    assert res["has_more"] is False


@pytest.mark.asyncio
async def test_grouped_pagination_does_not_split_groups(db_session):
    db_session.add_all([
        _row(id=5, session_key="g5", user_id="A", item_id="f1"),
        _row(id=4, session_key="g4", user_id="A", item_id="f1"),
        _row(id=3, session_key="g3", user_id="B", item_id="f2"),
        _row(id=2, session_key="g2", user_id="A", item_id="f1"),
        _row(id=1, session_key="g1", user_id="A", item_id="f1"),
    ])
    await db_session.commit()
    p1 = await get_activity_grouped(db_session, limit=2)
    assert [it["session_count"] for it in p1["items"]] == [2, 1]
    assert p1["has_more"] is True and p1["next_cursor"]
    p2 = await get_activity_grouped(db_session, limit=2, cursor=p1["next_cursor"])
    assert [it["session_count"] for it in p2["items"]] == [2]  # [2,1] intact, not split
    assert p2["has_more"] is False


@pytest.mark.asyncio
async def test_grouped_respects_user_filter(db_session):
    db_session.add_all([
        _row(id=2, session_key="g2", user_id="A", item_id="f1"),
        _row(id=1, session_key="g1", user_id="B", item_id="f2"),
    ])
    await db_session.commit()
    res = await get_activity_grouped(db_session, exclude_users="A")
    assert [it["user_id"] for it in res["items"]] == ["B"]


@pytest.mark.asyncio
async def test_flat_sort_by_user_orders_the_whole_set(db_session):
    # #327: sorting must apply server-side across all pages, not per-page.
    db_session.add_all([
        _row(id=1, session_key="s1", user_id="C", user_name="Charlie"),
        _row(id=2, session_key="s2", user_id="A", user_name="Alice"),
        _row(id=3, session_key="s3", user_id="B", user_name="Bob"),
    ])
    await db_session.commit()
    asc = await get_activity_history(db_session, sort_by="user", sort_order="asc")
    assert [it["user"] for it in asc["items"]] == ["Alice", "Bob", "Charlie"]
    desc = await get_activity_history(db_session, sort_by="user", sort_order="desc")
    assert [it["user"] for it in desc["items"]] == ["Charlie", "Bob", "Alice"]


@pytest.mark.asyncio
async def test_flat_sort_by_title_coalesces_series_name(db_session):
    db_session.add_all([
        _row(id=1, session_key="s1", item_id="m1", item_name="Zodiac"),
        _row(id=2, session_key="s2", item_id="e1", item_name="Pilot", series_name="Andor"),
    ])
    await db_session.commit()
    asc = await get_activity_history(db_session, sort_by="title", sort_order="asc")
    # Sort key = coalesce(series_name, item_name): "Andor" < "Zodiac".
    assert [it["title"] for it in asc["items"]] == ["Andor - Pilot", "Zodiac"]


@pytest.mark.asyncio
async def test_activity_route_groups_by_default_and_flattens_on_sort(authed_client, db_session):
    db_session.add_all([
        _row(id=2, session_key="r2", user_id="A", user_name="Alice", item_id="f1"),
        _row(id=1, session_key="r1", user_id="A", user_name="Alice", item_id="f1"),
    ])
    await db_session.commit()

    grouped = (await authed_client.get("/api/stats/activity")).json()
    assert grouped["items"][0]["session_count"] == 2  # consecutive runs merged
    assert "next_cursor" in grouped

    flat = (await authed_client.get("/api/stats/activity?sort_by=user&sort_order=asc")).json()
    assert "session_count" not in flat["items"][0]  # flat rows stay individual
    assert flat["page"] == 1
    assert len(flat["items"]) == 2


@pytest.mark.asyncio
async def test_grouped_single_run_filling_scan_cap_keeps_paging(db_session, monkeypatch):
    # A single (user, item) run larger than the scan window must keep paging
    # (advance the cursor through it) instead of stalling with has_more=False.
    import services.stats_aggregator.activity as act
    monkeypatch.setattr(act, "_GROUP_SCAN_CAP", 3)
    db_session.add_all([
        _row(id=i, session_key=f"c{i}", user_id="A", item_id="f1") for i in range(1, 6)
    ])
    await db_session.commit()
    res = await get_activity_grouped(db_session, limit=25)
    assert res["has_more"] is True
    assert res["next_cursor"]
