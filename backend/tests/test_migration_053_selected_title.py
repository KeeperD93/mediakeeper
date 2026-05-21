"""Robustness tests for migration 053 (user_profiles.selected_title backfill).

The achievements feature shipped with ``selected_title`` on the
``UserProfile`` model but no Alembic migration to back it. Production
deployments using ``MK_DB_SCHEMA_MODE=validate`` ended up with the
table but without the column, breaking ``/api/auth/portal-login`` and
the ``expire_users`` scheduler with a hard ``UndefinedColumnError`` —
see migration 053 docstring for the full story.

This file asserts:
* The migration is idempotent on SQLite (upgrade → downgrade →
  re-upgrade leaves the schema stable).
* The post-condition raises if the column is still missing after the
  DDL, mirroring the 048 canary pattern.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from models.base import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]

_PRE_053_REV = "052_mk_events_max_participants"
_TARGET_REV = "053_user_profile_selected_title"
_TABLE = "user_profiles"
_COLUMN = "selected_title"


def _make_alembic_config() -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return cfg


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    """Bootstrap a SQLite DB at post-053 metadata, stamped at 052."""
    backend_str = str(BACKEND_ROOT)
    added_path = backend_str not in sys.path
    if added_path:
        sys.path.insert(0, backend_str)

    db_path = Path(workspace_tmp_path) / "alembic_053.sqlite"
    if db_path.exists():
        db_path.unlink()

    sync_url = f"sqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(sync_url, future=True)
    Base.metadata.create_all(engine)

    monkeypatch.setenv("DATABASE_URL", sync_url)
    cfg = _make_alembic_config()
    command.stamp(cfg, _PRE_053_REV)

    try:
        yield cfg, engine
    finally:
        engine.dispose()
        if added_path:
            sys.path.remove(backend_str)


def _columns(engine, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def test_upgrade_adds_selected_title(alembic_db):
    cfg, engine = alembic_db

    with engine.begin() as conn:
        conn.exec_driver_sql(f'ALTER TABLE {_TABLE} DROP COLUMN {_COLUMN}')

    assert _COLUMN not in _columns(engine, _TABLE), (
        "Precondition: column must be absent before upgrade"
    )

    command.upgrade(cfg, _TARGET_REV)

    assert _COLUMN in _columns(engine, _TABLE), (
        f"Migration 053 did not add {_TABLE}.{_COLUMN}"
    )


def test_idempotent_upgrade_downgrade_upgrade(alembic_db):
    cfg, engine = alembic_db

    with engine.begin() as conn:
        conn.exec_driver_sql(f'ALTER TABLE {_TABLE} DROP COLUMN {_COLUMN}')

    command.upgrade(cfg, _TARGET_REV)
    assert _COLUMN in _columns(engine, _TABLE)

    command.downgrade(cfg, _PRE_053_REV)
    assert _COLUMN not in _columns(engine, _TABLE)

    command.upgrade(cfg, _TARGET_REV)
    assert _COLUMN in _columns(engine, _TABLE)


def test_post_condition_raises_on_silent_failure(alembic_db):
    """Mock the inspector to keep reporting the column missing after DDL.

    Proves the safety net against the historical batch_alter_table silent
    no-op observed in 045-048.
    """
    cfg, engine = alembic_db

    with engine.begin() as conn:
        conn.exec_driver_sql(f'ALTER TABLE {_TABLE} DROP COLUMN {_COLUMN}')

    class _FakeInspector:
        def get_columns(self, table):
            return [{"name": "id"}]

    with patch("sqlalchemy.inspect", return_value=_FakeInspector()):
        with pytest.raises(RuntimeError, match="Migration 053 silently failed"):
            command.upgrade(cfg, _TARGET_REV)
