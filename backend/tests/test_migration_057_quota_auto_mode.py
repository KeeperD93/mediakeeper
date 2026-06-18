"""Round-trip tests for migration 057 (request_quotas auto-mode bounds).

Migration 057 adds ``auto_min`` / ``auto_max`` / ``last_recomputed_at`` to
``request_quotas`` and renames the legacy ``mode`` vocabulary
(``fixed`` -> ``manual``, ``proportional`` -> ``auto``). The unit/atomicity
quota tests build the schema via ``Base.metadata.create_all`` and never drive
this migration, so the column guards, the data-rename UPDATEs and the SQLite
``batch_alter_table`` downgrade would otherwise ship untested.

Asserts (mirrors the 053 pattern):
* Upgrade adds the three columns and renames the two legacy mode values.
* Downgrade drops the columns and reverts the rename.
* upgrade -> downgrade -> re-upgrade leaves the schema + data stable.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from models.base import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]

_PRE_REV = "056_user_preferences_table_columns"
_TARGET_REV = "057_request_quota_auto_mode"
_TABLE = "request_quotas"
_NEW_COLS = ("auto_min", "auto_max", "last_recomputed_at")


def _make_alembic_config() -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return cfg


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    """Bootstrap a SQLite DB at post-057 metadata, stamped at 056."""
    backend_str = str(BACKEND_ROOT)
    added_path = backend_str not in sys.path
    if added_path:
        sys.path.insert(0, backend_str)

    db_path = Path(workspace_tmp_path) / "alembic_057.sqlite"
    if db_path.exists():
        db_path.unlink()

    sync_url = f"sqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(sync_url, future=True)
    Base.metadata.create_all(engine)

    monkeypatch.setenv("DATABASE_URL", sync_url)
    cfg = _make_alembic_config()
    command.stamp(cfg, _PRE_REV)

    try:
        yield cfg, engine
    finally:
        engine.dispose()
        if added_path:
            sys.path.remove(backend_str)


def _columns(engine, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def _seed_pre_057(engine) -> None:
    """Drop the 057 columns and seed two rows with the legacy mode vocabulary."""
    with engine.begin() as conn:
        for col in reversed(_NEW_COLS):
            conn.exec_driver_sql(f"ALTER TABLE {_TABLE} DROP COLUMN {col}")
        conn.exec_driver_sql(
            f"INSERT INTO {_TABLE} (user_id, month, mode) VALUES (1, '2026-06', 'fixed')"
        )
        conn.exec_driver_sql(
            f"INSERT INTO {_TABLE} (user_id, month, mode) VALUES (2, '2026-06', 'proportional')"
        )


def _modes_by_user(engine) -> dict[int, str]:
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(f"SELECT user_id, mode FROM {_TABLE}").fetchall()
    return {row[0]: row[1] for row in rows}


def _auto_bounds_by_user(engine) -> dict[int, tuple[int, int]]:
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(
            f"SELECT user_id, auto_min, auto_max FROM {_TABLE}"
        ).fetchall()
    return {row[0]: (row[1], row[2]) for row in rows}


def test_upgrade_adds_columns_and_renames_modes(alembic_db):
    cfg, engine = alembic_db
    _seed_pre_057(engine)
    for col in _NEW_COLS:
        assert col not in _columns(engine, _TABLE), f"Precondition: {col} must be absent"

    command.upgrade(cfg, _TARGET_REV)

    cols = _columns(engine, _TABLE)
    for col in _NEW_COLS:
        assert col in cols, f"Migration 057 did not add {col}"
    assert _modes_by_user(engine) == {1: "manual", 2: "auto"}


def test_idempotent_upgrade_downgrade_upgrade(alembic_db):
    cfg, engine = alembic_db
    _seed_pre_057(engine)

    command.upgrade(cfg, _TARGET_REV)
    assert all(c in _columns(engine, _TABLE) for c in _NEW_COLS)
    assert _modes_by_user(engine) == {1: "manual", 2: "auto"}

    command.downgrade(cfg, _PRE_REV)
    cols = _columns(engine, _TABLE)
    assert all(c not in cols for c in _NEW_COLS)
    assert _modes_by_user(engine) == {1: "fixed", 2: "proportional"}  # rename reverted

    command.upgrade(cfg, _TARGET_REV)
    assert all(c in _columns(engine, _TABLE) for c in _NEW_COLS)
    assert _modes_by_user(engine) == {1: "manual", 2: "auto"}


def test_upgrade_backfills_auto_band_server_default(alembic_db):
    """auto_min/auto_max land with the 2/15 server_default, so pre-057 rows are
    backfilled with a valid band (and later inserts inherit it)."""
    cfg, engine = alembic_db
    _seed_pre_057(engine)

    command.upgrade(cfg, _TARGET_REV)

    assert _auto_bounds_by_user(engine) == {1: (2, 15), 2: (2, 15)}
