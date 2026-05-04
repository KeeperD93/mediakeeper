"""Switch consumer-side FKs to ``users.id`` from CASCADE to SET NULL.

Eight tables hold content with audit / community / moderation value
that should outlive the GDPR purge of its author. Switching the FK to
``ON DELETE SET NULL`` (and flipping the column to ``nullable=True``)
preserves the row while severing the personal link.

Tables touched:
* ``news.author_id``
* ``mk_event_messages.user_id``
* ``watch_parties.host_user_id``
* ``chat_reports.reporter_id``
* ``ticket_replies.user_id``
* ``tickets.user_id``
* ``media_requests.user_id``
* ``mk_events.creator_user_id``

Constraint names are looked up dynamically so the migration is robust
across Postgres-auto-named FKs and SQLite (where batch_alter_table
recreates the table). The downgrade backfills any ``NULL`` left behind
with the synthetic ``-1`` placeholder before re-installing the NOT NULL
column, mirroring migration 040's chat_messages downgrade.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "041_fk_consumer_set_null"
down_revision: Union[str, None] = "040_gdpr_pending_deletion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column, fk_name)
_FK_TARGETS: tuple[tuple[str, str, str], ...] = (
    ("news",              "author_id",       "news_author_id_fkey"),
    ("mk_event_messages", "user_id",         "mk_event_messages_user_id_fkey"),
    ("watch_parties",     "host_user_id",    "watch_parties_host_user_id_fkey"),
    ("chat_reports",      "reporter_id",     "chat_reports_reporter_id_fkey"),
    ("ticket_replies",    "user_id",         "ticket_replies_user_id_fkey"),
    ("tickets",           "user_id",         "tickets_user_id_fkey"),
    ("media_requests",    "user_id",         "media_requests_user_id_fkey"),
    ("mk_events",         "creator_user_id", "mk_events_creator_user_id_fkey"),
)


def _existing_fk_name(inspector, table: str, column: str) -> str | None:
    """Return the actual FK constraint name covering ``column`` on
    ``table``, or ``None`` when the inspector doesn't surface one
    (SQLite often reports ``None`` for FKs created without an explicit
    name)."""
    for fk in inspector.get_foreign_keys(table):
        if column in fk.get("constrained_columns", []):
            return fk.get("name")
    return None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for table, column, target_fk_name in _FK_TARGETS:
        if table not in existing_tables:
            continue
        current_name = _existing_fk_name(inspector, table, column)
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                column, existing_type=sa.Integer(), nullable=True
            )
            if current_name:
                batch_op.drop_constraint(current_name, type_="foreignkey")
            batch_op.create_foreign_key(
                target_fk_name,
                "users",
                [column],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for table, column, target_fk_name in _FK_TARGETS:
        if table not in existing_tables:
            continue
        # Backfill any ``NULL`` left by a purge so NOT NULL can be
        # re-imposed. ``-1`` is intentionally invalid as a user id so
        # surviving rows remain obviously synthetic. Pre-1.0 only —
        # production data is wiped at v1.0.
        synthetic = sa.table(table, sa.column(column, sa.Integer))
        bind.execute(
            sa.update(synthetic)
            .where(synthetic.c[column].is_(None))
            .values({column: -1})
        )
        current_name = _existing_fk_name(inspector, table, column)
        with op.batch_alter_table(table) as batch_op:
            if current_name:
                batch_op.drop_constraint(current_name, type_="foreignkey")
            batch_op.create_foreign_key(
                target_fk_name,
                "users",
                [column],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.alter_column(
                column, existing_type=sa.Integer(), nullable=False
            )
