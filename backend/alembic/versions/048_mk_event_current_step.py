"""Add ``current_step`` to ``mk_events`` for server-authoritative marathon flow.

The cinema room marathon now tracks the active film index on the server
so the "next film" button can be gated on every participant having
crossed the 85% threshold (see ``services/portal/mk_events_marathon``).

DDL pattern: native ``ADD/DROP COLUMN IF [NOT] EXISTS`` on Postgres
(``op.batch_alter_table`` was a silent no-op on asyncpg in some
deployments — alembic_version stamped to 048, ALTER never applied,
``mk_events.current_step`` missing in prod). SQLite falls back to the
inspector-guarded ``add_column`` / ``drop_column`` pair. A
post-condition raises if the expected column is still missing.
"""
from alembic import op
import sqlalchemy as sa


revision = "048_mk_event_current_step"
down_revision = "047_remove_dead_vote_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            'ALTER TABLE "mk_events" '
            'ADD COLUMN IF NOT EXISTS "current_step" INTEGER NOT NULL DEFAULT 0'
        )
    else:
        inspector = sa.inspect(bind)
        cols = {c["name"] for c in inspector.get_columns("mk_events")}
        if "current_step" not in cols:
            op.add_column(
                "mk_events",
                sa.Column(
                    "current_step",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                ),
            )

    cols_after = {
        c["name"] for c in sa.inspect(bind).get_columns("mk_events")
    }
    if "current_step" not in cols_after:
        raise RuntimeError(
            "Migration 048 silently failed to add mk_events.current_step. "
            "Underlying DDL did not apply."
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            'ALTER TABLE "mk_events" DROP COLUMN IF EXISTS "current_step"'
        )
    else:
        inspector = sa.inspect(bind)
        cols = {c["name"] for c in inspector.get_columns("mk_events")}
        if "current_step" in cols:
            op.drop_column("mk_events", "current_step")
