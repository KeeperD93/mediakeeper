"""Migration 065: members' last sign-in filled in from their last visit."""
from datetime import datetime

import pytest
import sqlalchemy as sa
from alembic import command

from models.base import Base
from tests._migration_helpers import alembic_db_at

REVISION = "065_last_login_from_last_seen"
PREVIOUS = "064_security_cleared_and_automatic"
SEEN = datetime(2026, 3, 1, 12, 0)
SIGNED_IN = datetime(2026, 2, 1, 9, 30)


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    with alembic_db_at(PREVIOUS, workspace_tmp_path, monkeypatch) as db:
        yield db


def _add_profile(conn, name: str, *, seen: datetime | None, signed_in: datetime | None) -> None:
    tables = Base.metadata.tables
    user_id = conn.execute(sa.insert(tables["users"]).values(
        username=name, hashed_password="x", is_active=True, must_change_password=False,
    )).inserted_primary_key[0]
    conn.execute(sa.insert(tables["user_profiles"]).values(
        user_id=user_id, display_name=name, last_seen_at=seen, last_login_at=signed_in,
    ))


def _sign_ins(engine) -> dict[str, tuple]:
    profiles = Base.metadata.tables["user_profiles"]
    with engine.connect() as conn:
        rows = conn.execute(sa.select(
            profiles.c.display_name, profiles.c.last_login_at,
            profiles.c.last_login_ip, profiles.c.last_login_user_agent,
        )).all()
    return {name: tuple(rest) for name, *rest in rows}


def test_upgrade_copies_the_last_visit_only_where_no_sign_in_is_on_record(alembic_db):
    """Address and browser stay empty: a visit records neither."""
    cfg, engine = alembic_db
    with engine.begin() as conn:
        _add_profile(conn, "member-a", seen=SEEN, signed_in=None)
        _add_profile(conn, "member-b", seen=SEEN, signed_in=SIGNED_IN)
        _add_profile(conn, "member-c", seen=None, signed_in=None)

    command.upgrade(cfg, REVISION)

    assert _sign_ins(engine) == {
        "member-a": (SEEN, None, None),
        "member-b": (SIGNED_IN, None, None),
        "member-c": (None, None, None),
    }


def test_downgrade_keeps_the_copied_dates(alembic_db):
    cfg, engine = alembic_db
    with engine.begin() as conn:
        _add_profile(conn, "member-a", seen=SEEN, signed_in=None)
    command.upgrade(cfg, REVISION)

    command.downgrade(cfg, PREVIOUS)

    assert _sign_ins(engine) == {"member-a": (SEEN, None, None)}
