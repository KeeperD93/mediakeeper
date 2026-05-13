"""Drop the dead vote system on media requests.

The ``vote_count`` column on ``media_requests`` and the ``request_votes``
table have been clinically dead for a while: no producer writes to them
(the vote endpoint returned 410 ``votes_disabled``, the create path
seeded ``vote_count=0`` and never bumped it, no UI surface exposes
voting). This revision finishes the cleanup by removing the schema —
the serialiser, the route, the GDPR export, and the model class all
land in the same PR.

Idempotent upgrade: column / table drops are guarded with an inspector
check so a partial run (or a hand-patched DB) replays cleanly.
"""
from alembic import op
import sqlalchemy as sa


revision = "047_remove_dead_vote_system"
down_revision = "046_request_available_at_and_cleanup_setting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    request_cols = {c["name"] for c in inspector.get_columns("media_requests")}
    if "vote_count" in request_cols:
        with op.batch_alter_table("media_requests") as batch_op:
            batch_op.drop_column("vote_count")

    if "request_votes" in inspector.get_table_names():
        op.drop_table("request_votes")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    request_cols = {c["name"] for c in inspector.get_columns("media_requests")}
    if "vote_count" not in request_cols:
        with op.batch_alter_table("media_requests") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "vote_count",
                    sa.Integer,
                    server_default=sa.text("0"),
                    nullable=False,
                )
            )

    if "request_votes" not in inspector.get_table_names():
        op.create_table(
            "request_votes",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column(
                "request_id",
                sa.Integer,
                sa.ForeignKey("media_requests.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint("user_id", "request_id", name="uq_request_vote"),
        )
