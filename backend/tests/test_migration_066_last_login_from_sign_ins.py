"""Migration 066: the last sign-in taken from the attempts log where it holds one."""
from datetime import datetime

import pytest
import sqlalchemy as sa
from alembic import command

from models.base import Base
from tests._migration_helpers import alembic_db_at

REVISION = "066_last_login_from_sign_ins"
PREVIOUS = "065_last_login_from_last_seen"
CREATED = datetime(2026, 1, 1, 8, 0)
EARLIER = datetime(2026, 2, 10, 9, 0)
LATEST = datetime(2026, 2, 20, 8, 0)
STAMPED = datetime(2026, 2, 1, 7, 0)
VISIT = datetime(2026, 3, 1, 12, 0)
AFTER_VISIT = datetime(2026, 3, 2, 12, 0)
ADDRESS = "198.51.100.40"
BROWSER = "TestBrowser/1.2.3"


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    with alembic_db_at(PREVIOUS, workspace_tmp_path, monkeypatch) as db:
        yield db


def _add_profile(conn, name: str, *, signed_in=VISIT, ip: str | None = None, created: datetime = CREATED) -> None:
    tables = Base.metadata.tables
    user_id = conn.execute(sa.insert(tables["users"]).values(
        username=name, hashed_password="x", is_active=True, must_change_password=False,
    )).inserted_primary_key[0]
    conn.execute(sa.insert(tables["user_profiles"]).values(
        user_id=user_id, display_name=name, last_login_at=signed_in, last_login_ip=ip, created_at=created,
    ))


def _log(conn, name: str, at: datetime, *, scope: str = "portal", success: int = 1,
         ip: str = ADDRESS, agent: str | None = BROWSER) -> None:
    conn.execute(sa.insert(Base.metadata.tables["security_attempts"]).values(
        username=name, created_at=at, scope=scope, success=success, ip=ip, user_agent=agent,
    ))


def _sign_ins(engine) -> dict[str, tuple]:
    profiles = Base.metadata.tables["user_profiles"]
    with engine.connect() as conn:
        rows = conn.execute(sa.select(
            profiles.c.display_name, profiles.c.last_login_at,
            profiles.c.last_login_ip, profiles.c.last_login_user_agent,
        )).all()
    return {name: tuple(rest) for name, *rest in rows}


def test_upgrade_gives_each_unstamped_profile_its_latest_sign_in(alembic_db):
    cfg, engine = alembic_db
    with engine.begin() as conn:
        # The latest sign-in wins over an earlier one, a later failure and a
        # later password change.
        _add_profile(conn, "member-a")
        _log(conn, "member-a", EARLIER, ip="198.51.100.41", agent="TestBrowser/0.0.1")
        _log(conn, "member-a", LATEST)
        _log(conn, "member-a", AFTER_VISIT, success=0, ip="198.51.100.42")
        _log(conn, "member-a", AFTER_VISIT, scope="admin_password", ip="198.51.100.43")
        # Names are logged in lower case; a sign-in on the admin page counts.
        _add_profile(conn, "Member-B")
        _log(conn, "member-b", LATEST, scope="admin")
        # Signed in without ever being seen: 065 had nothing to copy.
        _add_profile(conn, "member-c", signed_in=None)
        _log(conn, "member-c", LATEST)
        # The log keeps more of the browser than the profile can hold.
        _add_profile(conn, "member-d")
        _log(conn, "member-d", LATEST, agent="B" * 300)
        # A logged sign-in may have no browser.
        _add_profile(conn, "member-e")
        _log(conn, "member-e", LATEST, agent=None)

    command.upgrade(cfg, REVISION)

    assert _sign_ins(engine) == {
        "member-a": (LATEST, ADDRESS, BROWSER),
        "Member-B": (LATEST, ADDRESS, BROWSER),
        "member-c": (LATEST, ADDRESS, BROWSER),
        "member-d": (LATEST, ADDRESS, "B" * 255),
        "member-e": (LATEST, ADDRESS, None),
    }


def test_upgrade_leaves_every_other_profile_alone(alembic_db):
    cfg, engine = alembic_db
    with engine.begin() as conn:
        # Really stamped: it has its address, whatever the log holds.
        _add_profile(conn, "member-f", signed_in=STAMPED, ip="198.51.100.44")
        _log(conn, "member-f", LATEST)
        # Nothing in the log: the copied visit stays.
        _add_profile(conn, "member-g")
        # Only refused tries and a password change.
        _add_profile(conn, "member-h")
        _log(conn, "member-h", LATEST, success=0)
        _log(conn, "member-h", LATEST, scope="admin_password")
        # Never seen, nothing logged: still never signed in.
        _add_profile(conn, "member-i", signed_in=None)
        # A former account of that name signed in before this profile existed.
        _add_profile(conn, "member-j", signed_in=None, created=AFTER_VISIT)
        _log(conn, "member-j", LATEST)

    command.upgrade(cfg, REVISION)

    assert _sign_ins(engine) == {
        "member-f": (STAMPED, "198.51.100.44", None),
        "member-g": (VISIT, None, None),
        "member-h": (VISIT, None, None),
        "member-i": (None, None, None),
        "member-j": (None, None, None),
    }


def test_downgrade_keeps_the_sign_ins(alembic_db):
    cfg, engine = alembic_db
    with engine.begin() as conn:
        _add_profile(conn, "member-a")
        _log(conn, "member-a", LATEST)
    command.upgrade(cfg, REVISION)

    command.downgrade(cfg, PREVIOUS)

    assert _sign_ins(engine) == {"member-a": (LATEST, ADDRESS, BROWSER)}
