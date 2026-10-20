"""Migration 063: ``media_requests.archived_at`` + the missing available dates.

Bootstraps a fresh SQLite DB from the current metadata, stamps it at 062,
seeds requests marked available with and without a date, then runs the 063
upgrade, its downgrade and the upgrade again.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from models.base import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REVISION = "063_request_archiving"
PREVIOUS = "062_continuous_watch_measurement"
UPDATED = datetime(2026, 3, 1, 12, 0)
STAMPED = datetime(2026, 2, 1, 12, 0)


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    backend_str = str(BACKEND_ROOT)
    added = backend_str not in sys.path
    if added:
        sys.path.insert(0, backend_str)
    db_path = Path(workspace_tmp_path) / "alembic_063.sqlite"
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


def test_upgrade_dates_requests_marked_available_by_hand(alembic_db):
    cfg, engine = alembic_db
    table = Base.metadata.tables["media_requests"]
    with engine.begin() as conn:
        # Same keys in every row: an executemany only inserts the first row's columns.
        conn.execute(sa.insert(table), [
            {"tmdb_id": 1, "media_type": "movie", "title": "By hand", "status": "available",
             "available_at": None, "updated_at": UPDATED},
            {"tmdb_id": 2, "media_type": "movie", "title": "Stamped", "status": "available",
             "available_at": STAMPED, "updated_at": UPDATED},
            {"tmdb_id": 3, "media_type": "movie", "title": "Pending", "status": "pending",
             "available_at": None, "updated_at": UPDATED},
        ])

    command.upgrade(cfg, REVISION)

    with engine.connect() as conn:
        dates = dict(conn.execute(sa.select(table.c.tmdb_id, table.c.available_at)).all())
    assert dates[1].replace(tzinfo=None) == UPDATED  # from its last update
    assert dates[2].replace(tzinfo=None) == STAMPED  # an existing date is kept
    assert dates[3] is None


def test_downgrade_drops_archived_at_and_upgrade_restores_it(alembic_db):
    cfg, engine = alembic_db

    def columns() -> set[str]:
        return {c["name"] for c in sa.inspect(engine).get_columns("media_requests")}

    command.upgrade(cfg, REVISION)
    command.downgrade(cfg, PREVIOUS)
    assert "archived_at" not in columns()

    command.upgrade(cfg, REVISION)
    assert "archived_at" in columns()
    indexes = {i["name"] for i in sa.inspect(engine).get_indexes("media_requests")}
    assert "ix_media_requests_archived_at" in indexes
