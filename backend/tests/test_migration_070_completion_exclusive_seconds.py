"""Migration 070: each watched title keeps the time its user watched it alone."""
import importlib.util
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select

from models.base import Base
from models.playback_stats import PlaybackCompletion, PlaybackSession
from tests._migration_helpers import BACKEND_ROOT, alembic_db_at
from tests._watch_measurement_helpers import STEP, emby_session, poll

REVISION = "070_completion_exclusive_seconds"
PREVIOUS = "069_profile_level_floor"
T0 = datetime(2026, 3, 7, 20, 0, tzinfo=UTC)
RUNTIME = 600
# The table as it stands before 070 (the model already has the new column).
_COMPLETIONS_BEFORE = sa.table(
    "playback_completions",
    *(sa.column(name, sa.String) for name in ("user_id", "user_name", "item_id", "item_type", "item_name", "source")),
    *(sa.column(name, sa.Integer) for name in ("session_id", "runtime_seconds", "watched_seconds")),
    sa.column("completed_at", sa.DateTime(timezone=True)),
)


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    with alembic_db_at(PREVIOUS, workspace_tmp_path, monkeypatch) as (cfg, engine):
        # Built from the models: go through 070 and back for the real starting point.
        command.upgrade(cfg, REVISION)
        command.downgrade(cfg, PREVIOUS)
        yield cfg, engine


def _columns(engine) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns("playback_completions")}


def _sitting(conn, user: str, item: str, started: datetime, exclusive: int, watched: int | None = None) -> int:
    return conn.execute(sa.insert(Base.metadata.tables["playback_sessions"]).values(
        session_key=f"{user}-{item}-{started.timestamp()}", user_id=user, user_name=user,
        item_id=item, item_name="Test Movie", item_type="Movie", started_at=started,
        watched_seconds=exclusive if watched is None else watched, exclusive_seconds=exclusive,
    )).inserted_primary_key[0]


def _completion(conn, session_id: int, user: str, item: str, at: datetime, watched: int, source: str = "live") -> None:
    conn.execute(sa.insert(_COMPLETIONS_BEFORE).values(
        session_id=session_id, user_id=user, user_name=user, item_id=item, item_type="Movie",
        item_name="Test Movie", runtime_seconds=600, watched_seconds=watched, completed_at=at, source=source,
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
        # A sitting deleted since, position unknown: the row's own exclusive time.
        kept = _sitting(conn, "heidi", "MOVIE-6", T0, 300)
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
        ("heidi", "MOVIE-6"): [300],
    }


def test_upgrade_with_no_watched_title_and_downgrade(alembic_db):
    cfg, engine = alembic_db
    command.upgrade(cfg, REVISION)
    assert "exclusive_seconds" in _columns(engine)

    command.downgrade(cfg, PREVIOUS)
    assert "exclusive_seconds" not in _columns(engine)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "migration_070_under_test", BACKEND_ROOT / "alembic" / "versions" / f"{REVISION}.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _migrate(db, step) -> None:
    def run(sync_conn):
        with Operations.context(MigrationContext.configure(sync_conn)):
            step()

    await (await db.connection()).run_sync(run)
    await db.commit()


async def _watch(db, start: datetime, first: int, last: int, *titles: tuple[str, str, int]) -> None:
    """Polls ``first`` to ``last``, 5 s apart; each ``(item, session, last poll)`` plays 5 s a poll."""
    at = start
    for i in range(first, last + 1):
        at = start + STEP * i
        await poll(db, at, *[
            emby_session(at=at, position_s=5 * i, item=item, session=session, runtime_s=RUNTIME)
            for item, session, until in titles if i <= until
        ])
    await poll(db, at + STEP)  # every player gone: the rows close


async def _live_values(db) -> dict[int, int]:
    found = await db.execute(select(PlaybackCompletion.id, PlaybackCompletion.exclusive_seconds))
    return dict(found.all())


async def test_the_backfill_finds_the_values_the_collector_fixed(db_session):
    db, end = db_session, RUNTIME // 5
    await _watch(db, T0, 1, end, ("MOVIE-1", "S-1", end))  # alone, then its end credits
    await _watch(db, T0 + timedelta(days=1), 1, end // 2, ("MOVIE-2", "S-2a", end // 2))
    await _watch(db, T0 + timedelta(days=2), end // 2, end, ("MOVIE-2", "S-2b", end))
    await _watch(db, T0 + timedelta(days=3), 1, end, ("MOVIE-1", "S-1b", end))  # watched again
    # Next to another title for 2 minutes (that one gets the time), then alone to the end.
    await _watch(db, T0 + timedelta(days=5), 1, end, ("MOVIE-D", "S-D", 24), ("MOVIE-C", "S-C", end))
    live = await _live_values(db)
    titles = dict((await db.execute(select(PlaybackCompletion.id, PlaybackCompletion.item_id))).all())
    assert sorted(titles.values()) == ["MOVIE-1", "MOVIE-1", "MOVIE-2", "MOVIE-C"]
    # Refused live by the 75 % rule; its end credits watched alone must not make it pass.
    assert next(v for i, v in live.items() if titles[i] == "MOVIE-C") < RUNTIME * 0.75

    migration = _load_migration()
    await db.execute(sa.update(PlaybackCompletion).values(exclusive_seconds=0))  # as before 070
    await _migrate(db, migration.upgrade)
    assert await _live_values(db) == live

    await _migrate(db, migration.downgrade)
    await _migrate(db, migration.upgrade)
    assert await _live_values(db) == live


async def test_a_sitting_deleted_since_leaves_the_end_credits_out(db_session):
    db, end = db_session, RUNTIME // 5
    # Next to another title for 2 minutes (that one gets the time), left unfinished.
    await _watch(db, T0, 1, 24, ("MOVIE-Y", "S-Y", 24), ("MOVIE-X", "S-Xa", 24))
    # Resumed alone the next day at 2 minutes, watched through its end credits.
    await _watch(db, T0 + timedelta(days=1), 24, end, ("MOVIE-X", "S-Xb", end))
    live = await _live_values(db)
    done = await db.scalar(select(PlaybackCompletion.id).where(PlaybackCompletion.item_id == "MOVIE-X"))
    assert live[done] < RUNTIME * 0.75  # refused live by the 75 % rule
    # The admin deletes the shared sitting (Statistics > Activity) before 070 runs.
    await db.delete(await db.scalar(
        select(PlaybackSession).where(PlaybackSession.item_id == "MOVIE-X").order_by(PlaybackSession.started_at)
    ))
    await db.commit()

    await db.execute(sa.update(PlaybackCompletion).values(exclusive_seconds=0))  # as before 070
    await _migrate(db, _load_migration().upgrade)
    assert await _live_values(db) == live
