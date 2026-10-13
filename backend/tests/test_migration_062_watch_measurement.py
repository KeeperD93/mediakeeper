"""Migration 062: past sessions get their estimated watch time and watched titles.

Bootstraps a fresh SQLite DB from the current metadata, stamps it at 061,
seeds sessions recorded before the continuous measurement and runs the 062
upgrade.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from models.base import Base
from models.playback_stats import PlaybackCompletion, PlaybackSession

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TICKS_PER_MINUTE = 60 * 10_000_000
START = datetime(2026, 2, 1, 20, 30, tzinfo=timezone.utc)


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    backend_str = str(BACKEND_ROOT)
    added = backend_str not in sys.path
    if added:
        sys.path.insert(0, backend_str)
    db_path = Path(workspace_tmp_path) / "alembic_062.sqlite"
    if db_path.exists():
        db_path.unlink()
    sync_url = f"sqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(sync_url, future=True)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("DATABASE_URL", sync_url)
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.stamp(cfg, "061_feedback_reports")
    try:
        yield cfg, engine
    finally:
        engine.dispose()
        if added:
            sys.path.remove(backend_str)


def _row(key: str, *, item: str, item_type: str = "Movie", start: datetime = START,
         wall: timedelta, position_min: int, runtime_min: int) -> PlaybackSession:
    return PlaybackSession(
        session_key=key, user_id="EMBY-1", user_name="viewer", item_id=item,
        item_name="Sample title", item_type=item_type, started_at=start,
        last_seen_at=start + wall, ended_at=start + wall, is_active=False,
        position_ticks=position_min * TICKS_PER_MINUTE, duration_ticks=runtime_min * TICKS_PER_MINUTE,
    )


def _seed(engine) -> None:
    with Session(engine) as s:
        s.add_all([
            # Reopened over three days but only 30 minutes in: counts 30 minutes.
            _row("stretched", item="FILM-A", wall=timedelta(days=3), position_min=30, runtime_min=120),
            # Music keeps its time but never counts as watching.
            _row("song", item="SONG-1", item_type="Audio", wall=timedelta(minutes=4), position_min=4, runtime_min=4),
            # A film watched in two evenings: watched once, on the second evening.
            _row("part-1", item="FILM-B", wall=timedelta(minutes=60), position_min=60, runtime_min=100),
            _row("part-2", item="FILM-B", start=START + timedelta(days=1),
                 wall=timedelta(minutes=35), position_min=95, runtime_min=100),
            # Jumped to the end after a few minutes: not watched.
            _row("skipped", item="FILM-C", wall=timedelta(minutes=5), position_min=95, runtime_min=100),
        ])
        s.commit()


def test_backfill_stores_the_estimate_and_rebuilds_watched_titles(alembic_db):
    cfg, engine = alembic_db
    _seed(engine)
    command.upgrade(cfg, "062_continuous_watch_measurement")

    with Session(engine) as s:
        rows = {r.session_key: r for r in s.scalars(sa.select(PlaybackSession))}
        completions = s.scalars(sa.select(PlaybackCompletion)).all()

    assert all(r.emby_session_key == key for key, r in rows.items())
    assert all(r.measured is False for r in rows.values())

    stretched = rows["stretched"]
    assert stretched.watched_seconds == stretched.exclusive_seconds == 30 * 60
    assert stretched.watched_by_hour == {"2026-02-01T20": 1800}

    song = rows["song"]
    assert song.watched_seconds == 4 * 60 and song.exclusive_seconds == 0
    assert song.watched_by_hour is None

    (done,) = completions
    assert done.session_id == rows["part-2"].id and done.source == "history"
    assert done.item_id == "FILM-B" and done.watched_seconds == (60 + 35) * 60
    assert rows["part-2"].completed_at is not None
    assert rows["skipped"].completed_at is None


def test_backfill_is_a_noop_on_an_empty_database(alembic_db):
    cfg, engine = alembic_db
    command.upgrade(cfg, "062_continuous_watch_measurement")
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT COUNT(*) FROM playback_completions")).scalar() == 0
