"""Backfill migration 060: silent imported users get a generated pseudo.

Bootstraps a fresh SQLite DB from the current metadata, stamps it at 059,
seeds a mix of accounts and runs the 060 upgrade. Only silent non-admin
profiles must be rewritten to their ``generate_pseudo`` value — the admin
and users who already picked a pseudo stay untouched.
"""
import sys
from pathlib import Path

import sqlalchemy as sa
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from models.base import Base
from models.portal.profile import UserProfile
from models.user import User
from services.portal._pseudo_words import generate_pseudo

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    backend_str = str(BACKEND_ROOT)
    added = backend_str not in sys.path
    if added:
        sys.path.insert(0, backend_str)

    db_path = Path(workspace_tmp_path) / "alembic_060.sqlite"
    if db_path.exists():
        db_path.unlink()

    sync_url = f"sqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(sync_url, future=True)
    Base.metadata.create_all(engine)

    monkeypatch.setenv("DATABASE_URL", sync_url)
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.stamp(cfg, "059_index_pending_deletion_at")

    try:
        yield cfg, engine
    finally:
        engine.dispose()
        if added:
            sys.path.remove(backend_str)


def _seed(engine) -> tuple[int, int, int]:
    """Insert a silent viewer, the admin and a viewer with a chosen pseudo."""
    with Session(engine) as s:
        silent = User(username="emby_login_silent", hashed_password="x", is_active=True)
        admin = User(username="root_admin", hashed_password="x", is_active=True)
        chosen = User(username="emby_login_chosen", hashed_password="x", is_active=True)
        s.add_all([silent, admin, chosen])
        s.flush()
        s.add_all([
            UserProfile(user_id=silent.id, display_name="emby_login_silent",
                        role="viewer", account_active=False, display_name_must_set=True),
            UserProfile(user_id=admin.id, display_name="root_admin",
                        role="admin", account_active=True, display_name_must_set=True),
            UserProfile(user_id=chosen.id, display_name="ChosenName",
                        role="viewer", account_active=True, display_name_must_set=False),
        ])
        s.commit()
        return silent.id, admin.id, chosen.id


def test_backfill_rewrites_only_silent_non_admin(alembic_db):
    cfg, engine = alembic_db
    silent_id, admin_id, chosen_id = _seed(engine)

    command.upgrade(cfg, "060_backfill_anonymous_pseudonyms")

    with engine.connect() as conn:
        names = dict(conn.execute(sa.text(
            "SELECT user_id, display_name FROM user_profiles"
        )).fetchall())

    assert names[silent_id] == generate_pseudo(silent_id, "fr")
    assert names[silent_id] != "emby_login_silent"  # the Emby login is gone
    assert names[admin_id] == "root_admin"          # admin untouched
    assert names[chosen_id] == "ChosenName"         # chosen pseudo untouched


def test_backfill_is_a_noop_on_an_empty_database(alembic_db):
    cfg, engine = alembic_db
    command.upgrade(cfg, "060_backfill_anonymous_pseudonyms")
    with engine.connect() as conn:
        count = conn.execute(sa.text("SELECT COUNT(*) FROM user_profiles")).scalar()
    assert count == 0
