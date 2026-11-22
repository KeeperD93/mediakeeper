"""Migration 073: each watched title keeps the time its user watched it alone."""
from datetime import datetime, timedelta

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy import select

from models.base import Base
from models.playback_stats import PlaybackCompletion
from services.stats_aggregator.users_admin import merge_user_stats
from tests._migration_073_helpers import (
    PAID,
    REVISION,
    RUNTIME,
    admin_deletes,
    backfilled,
    done_of,
    live_values,
    load_migration,
    migrate,
    watch,
)
from tests._migration_helpers import alembic_db_at
from tests._watch_measurement_helpers import STEP, T0, emby_session, poll

PREVIOUS = "072_display_name_keys"
CARRY = 10  # the carry frozen in the migration (``_MAX_CARRY_SECONDS``), not the collector's
# The table as it stands before 073 (the model already has the new column).
_COMPLETIONS_BEFORE = sa.table(
    "playback_completions",
    *(sa.column(name, sa.String) for name in ("user_id", "user_name", "item_id", "item_type", "item_name", "source")),
    *(sa.column(name, sa.Integer) for name in ("session_id", "runtime_seconds", "watched_seconds")),
    sa.column("completed_at", sa.DateTime(timezone=True)),
)


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    with alembic_db_at(PREVIOUS, workspace_tmp_path, monkeypatch) as (cfg, engine):
        # Built from the models: go through 073 and back for the real starting point.
        command.upgrade(cfg, REVISION)
        command.downgrade(cfg, PREVIOUS)
        yield cfg, engine


def _columns(engine) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns("playback_completions")}


def _sitting(
    conn, user: str, item: str, started: datetime, exclusive: int, watched: int | None = None,
    last_tick: datetime | None = None,
) -> int:
    return conn.execute(sa.insert(Base.metadata.tables["playback_sessions"]).values(
        session_key=f"{user}-{item}-{started.timestamp()}", user_id=user, user_name=user,
        item_id=item, item_name="Test Movie", item_type="Movie", started_at=started, last_tick_at=last_tick,
        watched_seconds=exclusive if watched is None else watched, exclusive_seconds=exclusive,
    )).inserted_primary_key[0]


def _completion(conn, session_id: int, user: str, item: str, at: datetime, watched: int, source: str = "live") -> None:
    conn.execute(sa.insert(_COMPLETIONS_BEFORE).values(
        session_id=session_id, user_id=user, user_name=user, item_id=item, item_type="Movie",
        item_name="Test Movie", runtime_seconds=RUNTIME, watched_seconds=watched, completed_at=at, source=source,
    ))


def _shares(engine) -> dict[tuple[str, str], list[int]]:
    with engine.connect() as conn:
        found = conn.execute(sa.text(
            "SELECT user_id, item_id, exclusive_seconds FROM playback_completions ORDER BY completed_at, id"
        )).all()
    shares: dict[tuple[str, str], list[int]] = {}
    for user, item, exclusive in found:
        shares.setdefault((user, item), []).append(exclusive)
    return shares


def test_upgrade_adds_the_column_and_backfills_each_watched_title(alembic_db):
    cfg, engine = alembic_db
    assert "exclusive_seconds" not in _columns(engine)
    with engine.begin() as conn:
        # Rebuilt history: the estimate is the exclusive time.
        old = _sitting(conn, "alice", "HISTORY-1", T0 - timedelta(days=90), 500)
        _completion(conn, old, "alice", "HISTORY-1", T0 - timedelta(days=90), 500, source="history")
        # One sitting, shared with a second screen: its own exclusive time only.
        one = _sitting(conn, "alice", "MOVIE-1", T0, 420, watched=600)
        _completion(conn, one, "alice", "MOVIE-1", T0 + timedelta(minutes=10), 600)
        # Two sittings add up; a third one, too old, does not.
        _sitting(conn, "bob", "MOVIE-2", T0 - timedelta(days=31), 300)
        _sitting(conn, "bob", "MOVIE-2", T0 - timedelta(days=1), 250)
        last = _sitting(conn, "bob", "MOVIE-2", T0, 300)
        _completion(conn, last, "bob", "MOVIE-2", T0 + timedelta(minutes=5), 550)
        # Watched twice: the second count starts after the first one.
        first = _sitting(conn, "carol", "MOVIE-3", T0, 600)
        _completion(conn, first, "carol", "MOVIE-3", T0 + timedelta(minutes=10), 600)
        again = _sitting(conn, "carol", "MOVIE-3", T0 + timedelta(days=2), 580)
        _completion(conn, again, "carol", "MOVIE-3", T0 + timedelta(days=2, minutes=10), 580)
        # Played again after the completion, never finished: not part of it.
        _sitting(conn, "carol", "MOVIE-3", T0 + timedelta(days=3), 100)
        # Two films at once on one account: the second one got no time of its own.
        both = [_sitting(conn, "dave", item, T0, seconds, watched=600) for item, seconds in (("M-A", 600), ("M-B", 0))]
        for session_id, item in zip(both, ("M-A", "M-B"), strict=True):
            _completion(conn, session_id, "dave", item, T0 + timedelta(minutes=10), 600)
        # Another user's sitting of the same title never counts.
        _sitting(conn, "erin", "MOVIE-1", T0, 600)
        # Watched alone with its end credits: the 90 s after the title counted are not part of it.
        credits = _sitting(conn, "frank", "MOVIE-4", T0, 600)
        _completion(conn, credits, "frank", "MOVIE-4", T0 + timedelta(minutes=9), 510)
        # Two titles at once for its first 120 s, then alone through the credits.
        mixed = _sitting(conn, "grace", "MOVIE-5", T0, 480, watched=600)
        _completion(conn, mixed, "grace", "MOVIE-5", T0 + timedelta(minutes=9), 510)
        # A sitting deleted since, last polled when its title counted: the row's own
        # time, less the most it can have watched since (a poll's carry).
        kept = _sitting(conn, "heidi", "MOVIE-6", T0, 300, last_tick=T0 + timedelta(minutes=5))
        _completion(conn, kept, "heidi", "MOVIE-6", T0 + timedelta(minutes=5), 600)

    command.upgrade(cfg, REVISION)

    assert _shares(engine) == {
        ("alice", "HISTORY-1"): [500],
        ("alice", "MOVIE-1"): [420],
        ("bob", "MOVIE-2"): [550],
        ("carol", "MOVIE-3"): [600, 580],
        ("dave", "M-A"): [600],
        ("dave", "M-B"): [0],
        ("frank", "MOVIE-4"): [510],
        ("grace", "MOVIE-5"): [390],
        ("heidi", "MOVIE-6"): [300 - CARRY],
    }


def test_upgrade_with_no_watched_title_and_downgrade(alembic_db):
    cfg, engine = alembic_db
    command.upgrade(cfg, REVISION)
    assert "exclusive_seconds" in _columns(engine)

    command.downgrade(cfg, PREVIOUS)
    assert "exclusive_seconds" not in _columns(engine)


async def test_the_backfill_finds_the_values_the_collector_fixed(db_session):
    db, end = db_session, RUNTIME // 5
    await watch(db, T0, 1, end, ("MOVIE-1", "S-1", end))  # alone, then its end credits
    await watch(db, T0 + timedelta(days=1), 1, end // 2, ("MOVIE-2", "S-2a", end // 2))
    await watch(db, T0 + timedelta(days=2), end // 2, end, ("MOVIE-2", "S-2b", end))
    await watch(db, T0 + timedelta(days=3), 1, end, ("MOVIE-1", "S-1b", end))  # watched again
    # Next to another title for 2 minutes (that one gets the time), then alone to the end.
    await watch(db, T0 + timedelta(days=5), 1, end, ("MOVIE-D", "S-D", 24), ("MOVIE-C", "S-C", end))
    live = await live_values(db)
    titles = dict((await db.execute(select(PlaybackCompletion.id, PlaybackCompletion.item_id))).all())
    assert sorted(titles.values()) == ["MOVIE-1", "MOVIE-1", "MOVIE-2", "MOVIE-C"]
    # Refused live by the 75 % rule; its end credits watched alone must not make it pass.
    assert next(v for i, v in live.items() if titles[i] == "MOVIE-C") < RUNTIME * 0.75

    migration = load_migration()
    await db.execute(sa.update(PlaybackCompletion).values(exclusive_seconds=0))  # as before 073
    await migrate(db, migration.upgrade)
    assert await live_values(db) == live

    await migrate(db, migration.downgrade)
    await migrate(db, migration.upgrade)
    assert await live_values(db) == live


async def _play(db, start: datetime, positions: list[int], session: str, user: str = "EMBY-1") -> None:
    """One poll of MOVIE-X per position, 5 s apart, then the player gone."""
    at = start
    for k, position in enumerate(positions):
        at = start + STEP * k
        await poll(db, at, emby_session(
            at=at, position_s=position, item="MOVIE-X", session=session, user=user, runtime_s=RUNTIME,
        ))
    await poll(db, at + STEP)


async def _shared_start(db) -> None:
    """MOVIE-X next to MOVIE-Y for 2 minutes (MOVIE-Y gets the time), left unfinished:
    the sitting the admin deletes."""
    await watch(db, T0, 1, 24, ("MOVIE-Y", "S-Y", 24), ("MOVIE-X", "S-Xa", 24))


async def test_a_deleted_sitting_takes_off_the_most_the_row_can_have_watched_since(db_session):
    db = db_session
    await _shared_start(db)
    await watch(db, T0 + timedelta(days=1), 24, RUNTIME // 5, ("MOVIE-X", "S-Xb", RUNTIME // 5))  # alone to the end
    live = await live_values(db)
    done = await done_of(db, "S-Xb")
    assert live[done] < PAID  # refused live
    await admin_deletes(db, "S-Xa")

    # Its 90 s of end credits come off, timed to its last poll, with a poll's carry.
    assert await backfilled(db) == {done: live[done] - CARRY}


async def test_a_rewind_in_the_end_credits_leaves_a_refused_title_refused(db_session):
    db = db_session
    await _shared_start(db)
    # Alone from 2 minutes to 9, then back to 5 minutes for one more: it stops before 85 %.
    await _play(db, T0 + timedelta(days=1), [120 + 5 * k for k in range(85)] + [300 + 5 * k for k in range(13)], "S-Xb")
    live = await live_values(db)
    done = await done_of(db, "S-Xb")
    assert live[done] < PAID
    await admin_deletes(db, "S-Xa")

    assert (await backfilled(db))[done] <= live[done]


async def test_an_earlier_completion_deleted_with_its_sitting_adds_nothing(db_session):
    db = db_session
    await watch(db, T0, 1, 100, ("MOVIE-X", "S-A1", 100))  # 500 s alone, left there
    await watch(db, T0 + timedelta(days=1), 100, 104, ("MOVIE-X", "S-A2", 104))  # 20 s more: it counts
    await watch(db, T0 + timedelta(days=5), 1, 24, ("MOVIE-Y", "S-Y", 24), ("MOVIE-X", "S-B1", 24))
    await watch(db, T0 + timedelta(days=6), 24, RUNTIME // 5, ("MOVIE-X", "S-B2", RUNTIME // 5))
    live = await live_values(db)
    second = await done_of(db, "S-B2")
    assert live[second] < PAID
    # The first count goes with its 20 s sitting: the 500 s one now falls in the 30 days.
    await admin_deletes(db, "S-A2")

    assert await backfilled(db) == {second: live[second]}


async def test_merged_statistics_take_the_cautious_share(db_session):
    db = db_session
    await _play(db, T0, [5 * k for k in range(1, 21)], "S-1a")  # 100 s, left there
    await _play(db, T0 + timedelta(days=1), [5 * k for k in range(1, 121)], "S-2", user="EMBY-2")
    await _play(db, T0 + timedelta(days=2), [100 + 5 * k for k in range(101)], "S-1b")  # 100 s to the end
    live = await live_values(db)
    done = await done_of(db, "S-1b")
    assert live[done] >= PAID
    # The other Emby user's count now sits between the two sittings: the first one is lost.
    await merge_user_stats(db, "EMBY-2", "EMBY-1")

    assert (await backfilled(db))[done] < PAID
