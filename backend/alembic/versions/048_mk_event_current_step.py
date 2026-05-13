"""Add ``current_step`` to ``mk_events`` for server-authoritative marathon flow.

The cinema room marathon now tracks the active film index on the server
so the "next film" button can be gated on every participant having
crossed the 85% threshold (see ``services/portal/mk_events_marathon``).

Idempotent upgrade: the column is added only if it is missing so a
partial run replays cleanly. ``server_default='0'`` retro-fits all the
rows that pre-date this migration.
"""
from alembic import op
import sqlalchemy as sa


revision = "048_mk_event_current_step"
down_revision = "047_remove_dead_vote_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("mk_events")}
    if "current_step" not in cols:
        with op.batch_alter_table("mk_events") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "current_step",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("mk_events")}
    if "current_step" in cols:
        with op.batch_alter_table("mk_events") as batch_op:
            batch_op.drop_column("current_step")
