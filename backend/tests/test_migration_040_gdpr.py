"""Round-trip tests for Alembic migration 040 (GDPR groundwork).

The full pre-040 migration chain contains SQLite-incompatible
``op.alter_column`` calls that pre-date this migration. To stay focused on
040 itself we bootstrap a fresh on-disk SQLite database from the
current SQLAlchemy metadata (post-040 shape), stamp it at revision
039, and then exercise the 040 upgrade / downgrade pair against it.

The model definitions already reflect the post-040 chat-message FK
shape, so 040's idempotent upgrade is a near no-op for the FK alters
themselves but must still INSERT the five ``gdpr.*`` settings rows.
The downgrade then reverts to the pre-040 state and is verified.
"""
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from models.base import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _make_alembic_config() -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return cfg


@pytest.fixture
def alembic_db(workspace_tmp_path, monkeypatch):
    """Bootstrap a SQLite DB at post-040 schema, stamp it at 039.

    Yields ``(cfg, engine)`` so the test can run upgrade / downgrade
    and inspect the resulting schema. ``DATABASE_URL`` is set on the
    monkeypatched env so ``alembic/env.py`` resolves it back to this
    same SQLite file.
    """
    backend_str = str(BACKEND_ROOT)
    added_path = backend_str not in sys.path
    if added_path:
        sys.path.insert(0, backend_str)

    db_path = Path(workspace_tmp_path) / "alembic_040.sqlite"
    if db_path.exists():
        db_path.unlink()

    sync_url = f"sqlite:///{db_path.as_posix()}"
    engine = sa.create_engine(sync_url, future=True)
    Base.metadata.create_all(engine)
    # create_all reflects the current metadata, but this fixture stamps at 039
    # and exercises only 040's transitions. SQLite refuses to DROP COLUMN while
    # an index references it, so strip the index a later migration (059) puts on
    # users.pending_deletion_at — in the real chain 059's downgrade removes it
    # before 040's downgrade drops the column.
    with engine.begin() as conn:
        conn.execute(sa.text("DROP INDEX IF EXISTS ix_users_pending_deletion_at"))

    monkeypatch.setenv("DATABASE_URL", sync_url)
    cfg = _make_alembic_config()

    # Pretend the chain finished at 039 — only the 040 transitions
    # exercised here actually run alembic code.
    command.stamp(cfg, "039_users_tokens_invalidated_at")

    try:
        yield cfg, engine
    finally:
        engine.dispose()
        if added_path:
            sys.path.remove(backend_str)


def _gdpr_setting_keys(engine) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT key FROM settings WHERE key LIKE 'gdpr.%' ORDER BY key"
            )
        ).fetchall()
    return [k for (k,) in rows]


def test_upgrade_inserts_five_gdpr_settings(alembic_db):
    cfg, engine = alembic_db
    assert _gdpr_setting_keys(engine) == [], "pre-condition: no gdpr settings"

    command.upgrade(cfg, "040_gdpr_pending_deletion")

    keys = _gdpr_setting_keys(engine)
    assert keys == [
        "gdpr.account_purge_delay_days",
        "gdpr.dpo_contact",
        "gdpr.enabled",
        "gdpr.privacy_text_en",
        "gdpr.privacy_text_fr",
    ]
    with engine.connect() as conn:
        values = dict(
            conn.execute(
                sa.text("SELECT key, value FROM settings WHERE key LIKE 'gdpr.%'")
            ).fetchall()
        )
    assert values["gdpr.enabled"] == "false"
    assert values["gdpr.account_purge_delay_days"] == "30"
    assert values["gdpr.dpo_contact"] == ""
    assert "Politique de confidentialité" in values["gdpr.privacy_text_fr"]
    assert "Privacy policy" in values["gdpr.privacy_text_en"]


def test_upgrade_is_idempotent_on_settings(alembic_db):
    """Running the upgrade twice must not duplicate the gdpr.* rows."""
    cfg, engine = alembic_db
    command.upgrade(cfg, "040_gdpr_pending_deletion")
    command.downgrade(cfg, "039_users_tokens_invalidated_at")
    command.upgrade(cfg, "040_gdpr_pending_deletion")
    assert len(_gdpr_setting_keys(engine)) == 5


def test_downgrade_removes_gdpr_settings(alembic_db):
    cfg, engine = alembic_db
    command.upgrade(cfg, "040_gdpr_pending_deletion")
    assert len(_gdpr_setting_keys(engine)) == 5

    command.downgrade(cfg, "039_users_tokens_invalidated_at")

    assert _gdpr_setting_keys(engine) == []


def test_upgrade_chat_fk_is_set_null(alembic_db):
    """After upgrade, the chat_messages.user_id FK must be SET NULL."""
    cfg, engine = alembic_db
    command.upgrade(cfg, "040_gdpr_pending_deletion")

    inspector = sa.inspect(engine)
    fks = inspector.get_foreign_keys("chat_messages")
    user_fk = next(
        (fk for fk in fks if "user_id" in fk["constrained_columns"]),
        None,
    )
    assert user_fk is not None
    ondelete = (user_fk.get("options") or {}).get("ondelete", "").upper()
    assert ondelete == "SET NULL"

    cols = {c["name"]: c for c in inspector.get_columns("chat_messages")}
    assert cols["user_id"]["nullable"] is True


def _user_fk_ondelete(inspector, table: str, column: str) -> str:
    fks = inspector.get_foreign_keys(table)
    target = next(
        (fk for fk in fks if column in fk["constrained_columns"]),
        None,
    )
    assert target is not None, f"missing FK on {table}.{column}"
    return (target.get("options") or {}).get("ondelete", "").upper()


def test_upgrade_seen_alerts_fk_is_cascade(alembic_db):
    """Migration 040 also re-installs seen_alerts.user_id with
    ``ON DELETE CASCADE``. Without it, hard-deleting a ``users`` row
    raises an integrity error."""
    cfg, engine = alembic_db
    command.upgrade(cfg, "040_gdpr_pending_deletion")

    inspector = sa.inspect(engine)
    assert _user_fk_ondelete(inspector, "seen_alerts", "user_id") == "CASCADE"


def test_upgrade_xp_ledger_fk_is_cascade(alembic_db):
    """Migration 040 also re-installs xp_ledger.user_id with
    ``ON DELETE CASCADE``. The ledger is account-bound: a purged user
    must not leave orphan grants behind."""
    cfg, engine = alembic_db
    command.upgrade(cfg, "040_gdpr_pending_deletion")

    inspector = sa.inspect(engine)
    assert _user_fk_ondelete(inspector, "xp_ledger", "user_id") == "CASCADE"


# ─────────────────────────── migration 041 ─────────────────────────


_FK_041_TARGETS: tuple[tuple[str, str], ...] = (
    ("news",              "author_id"),
    ("mk_event_messages", "user_id"),
    ("watch_parties",     "host_user_id"),
    ("chat_reports",      "reporter_id"),
    ("ticket_replies",    "user_id"),
    ("tickets",           "user_id"),
    ("media_requests",    "user_id"),
    ("mk_events",         "creator_user_id"),
)


def test_upgrade_041_sets_consumer_fks_to_set_null(alembic_db):
    """Migration 041 flips eight consumer-side FKs to SET NULL so the
    rows survive a GDPR purge anonymised. End-state behaviour is also
    covered via Base.metadata in the consumer-side FK regression tests;
    this asserts the migration code itself produces the expected FK
    options on top of a stamped 040."""
    cfg, engine = alembic_db
    command.upgrade(cfg, "041_fk_consumer_set_null")

    inspector = sa.inspect(engine)
    for table, column in _FK_041_TARGETS:
        ondelete = _user_fk_ondelete(inspector, table, column)
        assert ondelete == "SET NULL", (
            f"{table}.{column}: expected SET NULL, got {ondelete!r}"
        )
        cols = {c["name"]: c for c in inspector.get_columns(table)}
        assert cols[column]["nullable"] is True, (
            f"{table}.{column}: SET NULL requires the column to be nullable"
        )


def test_downgrade_041_restores_cascade(alembic_db):
    """The 041 downgrade re-installs CASCADE + NOT NULL on the eight
    targets, matching the pre-041 contract."""
    cfg, engine = alembic_db
    command.upgrade(cfg, "041_fk_consumer_set_null")
    command.downgrade(cfg, "040_gdpr_pending_deletion")

    inspector = sa.inspect(engine)
    for table, column in _FK_041_TARGETS:
        ondelete = _user_fk_ondelete(inspector, table, column)
        assert ondelete == "CASCADE", (
            f"{table}.{column}: expected CASCADE after downgrade, "
            f"got {ondelete!r}"
        )
        cols = {c["name"]: c for c in inspector.get_columns(table)}
        assert cols[column]["nullable"] is False, (
            f"{table}.{column}: CASCADE expected NOT NULL after downgrade"
        )
