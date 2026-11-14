"""Migration 070: ``user_profiles.onboarding_completed_at``, empty for every profile.

Bootstraps a fresh SQLite DB from the current metadata, drops the column the
metadata already holds, stamps it at 069, then runs the 070 upgrade, its
downgrade and the upgrade again.
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
REVISION = "070_profile_onboarding"
PREVIOUS = "069_profile_level_floor"


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    backend_str = str(BACKEND_ROOT)
    added = backend_str not in sys.path
    if added:
        sys.path.insert(0, backend_str)
    db_path = Path(workspace_tmp_path) / "alembic_070.sqlite"
    sync_url = f"sqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(sync_url, future=True)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("ALTER TABLE user_profiles DROP COLUMN onboarding_completed_at"))
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


def _columns(engine) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns("user_profiles")}


def test_upgrade_adds_an_empty_column_for_existing_profiles(alembic_db):
    cfg, engine = alembic_db
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO users (id, username, hashed_password, is_active, must_change_password) "
            "VALUES (1, 'alice', 'x', 1, 0)"
        ))
        conn.execute(sa.text(
            "INSERT INTO user_profiles (user_id, display_name) VALUES (1, 'Alice')"
        ))

    command.upgrade(cfg, REVISION)

    assert "onboarding_completed_at" in _columns(engine)
    with engine.connect() as conn:
        done = conn.execute(sa.text("SELECT onboarding_completed_at FROM user_profiles")).scalar_one()
    assert done is None  # the wizard opens once for existing accounts too


def test_downgrade_drops_the_column_and_upgrade_restores_it(alembic_db):
    cfg, engine = alembic_db
    command.upgrade(cfg, REVISION)
    command.downgrade(cfg, PREVIOUS)
    assert "onboarding_completed_at" not in _columns(engine)

    command.upgrade(cfg, REVISION)
    assert "onboarding_completed_at" in _columns(engine)
