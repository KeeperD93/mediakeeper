"""Add ``max_participants`` to ``mk_events`` for per-event capacity.

The cinema room used to reserve a fixed 50-seat pool for every event.
We now expose two admin-tunable bounds (``portal.events.max_participants_
min`` / ``_max``, stored in the generic ``settings`` table — no schema
needed) and let the event creator pick a value in the [min, max] range
by steps of 5. Backfill: existing rows get ``10`` so older events keep
working without an admin touching anything.

Same DDL pattern as 048: native ``ADD COLUMN IF NOT EXISTS`` on
PostgreSQL + inspector-guarded fallback on SQLite + a post-condition
that raises if the column is still missing.
"""
from alembic import op
import sqlalchemy as sa


revision = "052_mk_events_max_participants"
down_revision = "051_mk_event_invitation_user_step_presence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            'ALTER TABLE "mk_events" '
            'ADD COLUMN IF NOT EXISTS "max_participants" '
            'INTEGER NOT NULL DEFAULT 10'
        )
    else:
        inspector = sa.inspect(bind)
        cols = {c["name"] for c in inspector.get_columns("mk_events")}
        if "max_participants" not in cols:
            op.add_column(
                "mk_events",
                sa.Column(
                    "max_participants",
                    sa.Integer(),
                    nullable=False,
                    server_default="10",
                ),
            )

    cols_after = {
        c["name"] for c in sa.inspect(bind).get_columns("mk_events")
    }
    if "max_participants" not in cols_after:
        raise RuntimeError(
            "Migration 052 silently failed to add mk_events.max_participants."
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            'ALTER TABLE "mk_events" '
            'DROP COLUMN IF EXISTS "max_participants"'
        )
    else:
        inspector = sa.inspect(bind)
        cols = {c["name"] for c in inspector.get_columns("mk_events")}
        if "max_participants" in cols:
            op.drop_column("mk_events", "max_participants")
