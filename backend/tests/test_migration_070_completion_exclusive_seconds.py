"""Migration 070: each watched title keeps the time its user watched it alone."""
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from alembic import command

from models.base import Base
from tests._migration_helpers import alembic_db_at

REVISION = "070_completion_exclusive_seconds"
PREVIOUS = "069_profile_level_floor"
T0 = datetime(2026, 3, 7, 20, 0, tzinfo=UTC)
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

    command.upgrade(cfg, REVISION)

    assert _shares(engine) == {
        ("alice", "HISTORY-1"): [500],
        ("alice", "MOVIE-1"): [420],
        ("bob", "MOVIE-2"): [550],
        ("carol", "MOVIE-3"): [600, 580],
        ("dave", "M-A"): [600],
        ("dave", "M-B"): [0],
    }


def test_upgrade_with_no_watched_title_and_downgrade(alembic_db):
    cfg, engine = alembic_db
    command.upgrade(cfg, REVISION)
    assert "exclusive_seconds" in _columns(engine)

    command.downgrade(cfg, PREVIOUS)
    assert "exclusive_seconds" not in _columns(engine)
