"""Migration 064: ``security_attempts.cleared_at`` + ``security_blocks.automatic``.

Bootstraps a fresh SQLite DB from the current metadata, stamps it at 063,
seeds blocks of every kind, then runs the 064 upgrade, its downgrade and the
upgrade again.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from models.base import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REVISION = "064_security_cleared_and_automatic"
PREVIOUS = "063_request_archiving"
UNTIL = datetime(2026, 3, 1, 12, 0) + timedelta(minutes=10)


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    backend_str = str(BACKEND_ROOT)
    added = backend_str not in sys.path
    if added:
        sys.path.insert(0, backend_str)
    db_path = Path(workspace_tmp_path) / "alembic_064.sqlite"
    sync_url = f"sqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(sync_url, future=True)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("DATABASE_URL", sync_url)
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.stamp(cfg, PREVIOUS)
    try:
        yield cfg, engine
    finally:
        engine.dispose()
        if added:
            sys.path.remove(backend_str)


def test_upgrade_marks_only_the_automatic_blocks(alembic_db):
    cfg, engine = alembic_db
    table = Base.metadata.tables["security_blocks"]
    with engine.begin() as conn:
        # Same keys in every row: an executemany only inserts the first row's columns.
        conn.execute(sa.insert(table), [
            {"ip": "198.51.100.31", "username": None, "scope": "portal", "permanent": 0,
             "blocked_until": UNTIL, "reason": "auto_block_bruteforce_ip:portal", "created_by": None},
            {"ip": None, "username": "member-a", "scope": "admin", "permanent": 0,
             "blocked_until": UNTIL, "reason": "auto_block_bruteforce_username:admin", "created_by": None},
            # A manual block whose admin was deleted: no creator left, its own reason.
            {"ip": None, "username": "member-b", "scope": "portal", "permanent": 0,
             "blocked_until": UNTIL, "reason": "seen on the router", "created_by": None},
            {"ip": "198.51.100.32", "username": None, "scope": "all", "permanent": 1,
             "blocked_until": None, "reason": "manual_from_attempts", "created_by": None},
            # Look-alike reason: '_' must not act as a wildcard.
            {"ip": "198.51.100.33", "username": None, "scope": "portal", "permanent": 0,
             "blocked_until": UNTIL, "reason": "autoXblockXbruteforceXip:portal", "created_by": None},
        ])

    command.upgrade(cfg, REVISION)

    with engine.connect() as conn:
        marks = dict(conn.execute(sa.select(table.c.reason, table.c.automatic)).all())
    assert marks == {
        "auto_block_bruteforce_ip:portal": 1,
        "auto_block_bruteforce_username:admin": 1,
        "seen on the router": 0,
        "manual_from_attempts": 0,
        "autoXblockXbruteforceXip:portal": 0,
    }


def test_downgrade_drops_both_columns_and_upgrade_restores_them(alembic_db):
    cfg, engine = alembic_db

    def columns(name: str) -> set[str]:
        return {c["name"] for c in sa.inspect(engine).get_columns(name)}

    command.upgrade(cfg, REVISION)
    command.downgrade(cfg, PREVIOUS)
    assert "cleared_at" not in columns("security_attempts")
    assert "automatic" not in columns("security_blocks")

    # A failure recorded by the older code still counts after the upgrade.
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO security_attempts (ip, username, scope, success, created_at) "
            "VALUES ('198.51.100.34', 'member-c', 'portal', 0, CURRENT_TIMESTAMP)"
        ))
    command.upgrade(cfg, REVISION)
    assert "cleared_at" in columns("security_attempts")
    assert "automatic" in columns("security_blocks")
    with engine.connect() as conn:
        cleared = conn.execute(sa.text("SELECT cleared_at FROM security_attempts")).scalar_one()
    assert cleared is None
