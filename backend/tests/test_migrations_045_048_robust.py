"""Robustness tests for migrations 045-048 (post batch_alter_table cleanup).

These migrations historically wrapped every ``ADD/DROP COLUMN`` in
``op.batch_alter_table``. On Postgres + asyncpg deployments the wrapper
silently no-op'd: alembic stamped ``alembic_version`` to the new
revision but the underlying ALTER never applied (observed in prod:
``mk_events.current_step`` missing while ``alembic_version=048``).

The migrations were rewritten to dispatch on dialect — native
``ADD/DROP COLUMN IF [NOT] EXISTS`` on Postgres, inspector-guarded
``add_column`` / ``drop_column`` on SQLite — with a post-condition that
raises ``RuntimeError`` when the inspector still reports the expected
column missing after the DDL.

This file asserts:
* Idempotence on SQLite (full chain 044→048 then downgrade→re-upgrade).
* Migration 048 post-condition canary: mock the inspector to keep
  reporting ``mk_events.current_step`` missing and verify ``upgrade()``
  raises with the expected message. Proves the safety net against the
  observed prod silent-fail.
* Migration 046 backfill regression guard: rows in ``available`` status
  with ``available_at IS NULL`` get ``available_at = updated_at`` after
  the upgrade.
"""
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from models.base import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]

_PRE_045_REV = "044_playback_pause_events"
_TARGET_REV = "048_mk_event_current_step"


def _make_alembic_config() -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return cfg


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    """Bootstrap a SQLite DB at post-048 metadata, stamped at 044."""
    backend_str = str(BACKEND_ROOT)
    added_path = backend_str not in sys.path
    if added_path:
        sys.path.insert(0, backend_str)

    db_path = Path(workspace_tmp_path) / "alembic_045_048.sqlite"
    if db_path.exists():
        db_path.unlink()

    sync_url = f"sqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(sync_url, future=True)
    Base.metadata.create_all(engine)

    monkeypatch.setenv("DATABASE_URL", sync_url)
    cfg = _make_alembic_config()
    command.stamp(cfg, _PRE_045_REV)

    try:
        yield cfg, engine
    finally:
        engine.dispose()
        if added_path:
            sys.path.remove(backend_str)


def _columns(engine, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def test_chain_045_to_048_idempotent_on_sqlite(alembic_db):
    """Run 045→048, downgrade to 044, re-run: schema stable, no exception."""
    cfg, engine = alembic_db

    command.upgrade(cfg, _TARGET_REV)

    assert {"start_at", "end_at"}.issubset(_columns(engine, "news"))
    assert "available_at" in _columns(engine, "media_requests")
    assert "current_step" in _columns(engine, "mk_events")
    assert "vote_count" not in _columns(engine, "media_requests")
    assert "request_votes" not in sa.inspect(engine).get_table_names()

    command.downgrade(cfg, _PRE_045_REV)
    command.upgrade(cfg, _TARGET_REV)

    assert {"start_at", "end_at"}.issubset(_columns(engine, "news"))
    assert "available_at" in _columns(engine, "media_requests")
    assert "current_step" in _columns(engine, "mk_events")


def test_046_backfills_available_at_from_updated_at(alembic_db):
    """Rows in status='available' with NULL available_at get updated_at."""
    cfg, engine = alembic_db
    command.upgrade(cfg, "045_news_scheduling_and_maintenance")

    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM media_requests"))
        conn.execute(
            sa.text(
                "INSERT INTO media_requests "
                "(user_id, tmdb_id, media_type, title, status, "
                "available_at, updated_at) "
                "VALUES "
                "(NULL, 1, 'movie', 'Backfilled', 'available', "
                "NULL, '2025-01-01 12:00:00'), "
                "(NULL, 2, 'movie', 'Untouched',  'pending', "
                "NULL, '2025-01-02 12:00:00')"
            )
        )

    command.upgrade(cfg, "046_request_available_at_and_cleanup_setting")

    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT title, status, available_at, updated_at "
                "FROM media_requests ORDER BY title"
            )
        ).fetchall()

    by_title = {r[0]: r for r in rows}
    backfilled = by_title["Backfilled"]
    untouched = by_title["Untouched"]
    assert backfilled[2] is not None
    assert backfilled[2] == backfilled[3]
    assert untouched[2] is None


def test_048_post_condition_raises_when_inspector_reports_missing(
    alembic_db, monkeypatch
):
    """Canary against the observed prod silent-fail.

    Mock ``sqlalchemy.inspect`` so ``get_columns("mk_events")`` always
    omits ``current_step``. The migration must then ``raise
    RuntimeError`` mentioning ``current_step`` and ``silently failed``.
    """
    cfg, engine = alembic_db
    command.upgrade(cfg, "047_remove_dead_vote_system")

    with engine.begin() as conn:
        try:
            conn.execute(
                sa.text("ALTER TABLE mk_events DROP COLUMN current_step")
            )
        except sa.exc.OperationalError:
            pass

    real_inspect = sa.inspect

    class _Filtered:
        def __init__(self, real):
            self._real = real

        def get_columns(self, table_name, *args, **kwargs):
            cols = self._real.get_columns(table_name, *args, **kwargs)
            if table_name == "mk_events":
                return [c for c in cols if c["name"] != "current_step"]
            return cols

        def __getattr__(self, name):
            return getattr(self._real, name)

    def fake_inspect(target, *args, **kwargs):
        result = real_inspect(target, *args, **kwargs)
        if hasattr(result, "get_columns"):
            return _Filtered(result)
        return result

    monkeypatch.setattr("sqlalchemy.inspect", fake_inspect)
    monkeypatch.setattr(sa, "inspect", fake_inspect)

    with pytest.raises(RuntimeError) as excinfo:
        command.upgrade(cfg, _TARGET_REV)

    msg = str(excinfo.value)
    assert "current_step" in msg
    assert "silently failed" in msg.lower()
