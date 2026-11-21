"""Migration 072: the name comparison columns, the names sorted out with the app's
rules, and the unique key.

Bootstraps a fresh SQLite DB from the current metadata, drops what 072 adds,
stamps it at 071, seeds profiles, then runs the 072 upgrade, its downgrade and
the upgrade again.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from models.base import Base
from services.portal._pseudo_words import generate_pseudo

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REVISION = "072_display_name_keys"
PREVIOUS = "071_help_seed_rewrite"
KEY_INDEX = "uq_user_profiles_display_name_key"
SKELETON_INDEX = "ix_user_profiles_display_name_skeleton"


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    backend_str = str(BACKEND_ROOT)
    added = backend_str not in sys.path
    if added:
        sys.path.insert(0, backend_str)
    db_path = Path(workspace_tmp_path) / "alembic_072.sqlite"
    sync_url = f"sqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(sync_url, future=True)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        for index in (KEY_INDEX, SKELETON_INDEX):
            conn.execute(sa.text(f"DROP INDEX {index}"))
        for column in ("display_name_key", "display_name_skeleton"):
            conn.execute(sa.text(f"ALTER TABLE user_profiles DROP COLUMN {column}"))
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


def _add(conn, user_id: int, name: str, *, must_set=False, role="viewer", changed_at="2026-10-01"):
    conn.execute(sa.text(
        "INSERT INTO users (id, username, hashed_password, is_active, must_change_password) "
        "VALUES (:id, :login, 'x', 1, 0)"
    ), {"id": user_id, "login": f"login{user_id}"})
    conn.execute(sa.text(
        "INSERT INTO user_profiles (user_id, display_name, display_name_must_set, role, "
        "display_name_changed_at) VALUES (:id, :name, :must_set, :role, :changed_at)"
    ), {"id": user_id, "name": name, "must_set": must_set, "role": role, "changed_at": changed_at})


def _profiles(engine) -> dict[int, tuple]:
    with engine.connect() as conn:
        rows = conn.execute(sa.text(
            "SELECT user_id, display_name, display_name_must_set, display_name_key, "
            "display_name_skeleton FROM user_profiles"
        )).all()
    return {r[0]: (r[1], bool(r[2]), r[3], r[4]) for r in rows}


def test_upgrade_sorts_out_the_names_with_the_app_rules(alembic_db):
    cfg, engine = alembic_db
    with engine.begin() as conn:
        _add(conn, 1, "Alice", changed_at="2026-09-01")
        _add(conn, 2, "alice", changed_at="2026-10-01")  # same key, chosen later
        _add(conn, 3, "Zo" + chr(0xE9), changed_at="2026-10-02")
        _add(conn, 4, "Zoe", changed_at="2026-10-03")  # same skeleton, chosen later
        _add(conn, 5, "Max", changed_at=None)  # unknown date counts as earliest
        _add(conn, 6, "max", changed_at="2026-01-01")
        _add(conn, 7, "Admin Bob")  # reserved
        _add(conn, 8, "Renard-Bleu-42")  # shaped like a provisional pseudo
        _add(conn, 9, "admin", role="admin", changed_at=None)
        _add(conn, 10, "login10", must_set=True, changed_at=None)  # never chose: sign-in name
        _add(conn, 11, "Reset", must_set=True)  # reset by an admin: name kept

    command.upgrade(cfg, REVISION)

    rows = _profiles(engine)
    assert rows[1] == ("Alice", False, "alice", "aiice")
    assert rows[2][1:3] == (True, None)
    assert rows[3][1] is False and rows[4][1:3] == (True, None)
    assert rows[5][1:3] == (False, "max") and rows[6][1:3] == (True, None)
    assert rows[7][1:3] == (True, None)
    assert rows[8][1:3] == (True, None)
    assert rows[9] == ("admin", False, None, None)
    assert rows[10] == (generate_pseudo(10, "fr"), True, None, None)
    assert rows[11] == ("Reset", True, None, None)


def test_the_unique_key_refuses_a_second_member_with_the_same_key(alembic_db):
    cfg, engine = alembic_db
    with engine.begin() as conn:
        _add(conn, 1, "Alice")
    command.upgrade(cfg, REVISION)

    with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
        _add(conn, 2, "Bob")
        conn.execute(sa.text("UPDATE user_profiles SET display_name_key = 'alice' WHERE user_id = 2"))


def test_downgrade_drops_the_columns_and_upgrade_restores_them(alembic_db):
    cfg, engine = alembic_db
    with engine.begin() as conn:
        _add(conn, 1, "Alice")
    command.upgrade(cfg, REVISION)
    command.downgrade(cfg, PREVIOUS)

    columns = {c["name"] for c in sa.inspect(engine).get_columns("user_profiles")}
    indexes = {i["name"] for i in sa.inspect(engine).get_indexes("user_profiles")}
    assert not {"display_name_key", "display_name_skeleton"} & columns
    assert not {KEY_INDEX, SKELETON_INDEX} & indexes

    command.upgrade(cfg, REVISION)
    assert _profiles(engine)[1] == ("Alice", False, "alice", "aiice")


def test_upgrade_on_an_empty_table_creates_the_indexes(alembic_db):
    cfg, engine = alembic_db
    command.upgrade(cfg, REVISION)
    indexes = {i["name"] for i in sa.inspect(engine).get_indexes("user_profiles")}
    assert {KEY_INDEX, SKELETON_INDEX} <= indexes
