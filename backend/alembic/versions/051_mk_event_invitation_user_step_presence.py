"""Add ``user_step`` + ``last_seen_at`` on ``mk_event_invitations``.

Two related concerns folded into the same migration since they share
the same table and ship together with the cinema-room polish cycle:

* ``user_step`` (int, default 0) — per-user marathon progression so a
  latecomer can keep watching film 1/8 while the rest of the group is
  already on 3/8. ``MKEvent.current_step`` stays as the group-wide max
  used by the readiness gate. New invitations seed at 0; existing rows
  pick up the default via ``server_default="0"``.

* ``last_seen_at`` (timestamptz, null) — heartbeat stamp from the open
  cinema-room tab. ``None`` keeps the avatar hidden in the live UI but
  preserves ``seat_index`` so a viewer returning takes back the same
  seat.

Same DDL pattern as 048: native ``ADD/DROP COLUMN IF [NOT] EXISTS`` on
Postgres + inspector-guarded fallback on SQLite + a post-condition that
raises if any of the expected columns is still missing.
"""
from alembic import op
import sqlalchemy as sa


revision = "051_mk_event_invitation_user_step_presence"
down_revision = "050_scheduler_force_run"
branch_labels = None
depends_on = None


_NEW_COLUMNS = (
    ("user_step", 'INTEGER NOT NULL DEFAULT 0', sa.Column(
        "user_step",
        sa.Integer(),
        nullable=False,
        server_default="0",
    )),
    ("last_seen_at", 'TIMESTAMP WITH TIME ZONE', sa.Column(
        "last_seen_at",
        sa.DateTime(timezone=True),
        nullable=True,
    )),
)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    for name, pg_decl, sa_col in _NEW_COLUMNS:
        if dialect == "postgresql":
            op.execute(
                f'ALTER TABLE "mk_event_invitations" '
                f'ADD COLUMN IF NOT EXISTS "{name}" {pg_decl}'
            )
        else:
            inspector = sa.inspect(bind)
            cols = {c["name"] for c in inspector.get_columns("mk_event_invitations")}
            if name not in cols:
                op.add_column("mk_event_invitations", sa_col)

    cols_after = {
        c["name"] for c in sa.inspect(bind).get_columns("mk_event_invitations")
    }
    missing = [name for name, *_ in _NEW_COLUMNS if name not in cols_after]
    if missing:
        raise RuntimeError(
            "Migration 051 silently failed to add columns "
            f"{', '.join(missing)} on mk_event_invitations."
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    for name, *_ in _NEW_COLUMNS:
        if dialect == "postgresql":
            op.execute(
                f'ALTER TABLE "mk_event_invitations" '
                f'DROP COLUMN IF EXISTS "{name}"'
            )
        else:
            inspector = sa.inspect(bind)
            cols = {c["name"] for c in inspector.get_columns("mk_event_invitations")}
            if name in cols:
                op.drop_column("mk_event_invitations", name)
