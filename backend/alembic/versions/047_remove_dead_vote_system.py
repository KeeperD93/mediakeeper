"""Drop the dead vote system on media requests.

The ``vote_count`` column on ``media_requests`` and the ``request_votes``
table have been clinically dead for a while: no producer writes to them
(the vote endpoint returned 410 ``votes_disabled``, the create path
seeded ``vote_count=0`` and never bumped it, no UI surface exposes
voting). This revision finishes the cleanup by removing the schema —
the serialiser, the route, the GDPR export, and the model class all
land in the same PR.

DDL pattern: native ``DROP COLUMN / TABLE IF EXISTS`` on Postgres
(``op.batch_alter_table`` was a silent no-op on asyncpg in some
deployments). SQLite falls back to the inspector-guarded
``drop_column`` / ``drop_table`` pair. A post-condition raises if the
expected drops did not happen.
"""
from alembic import op
import sqlalchemy as sa


revision = "047_remove_dead_vote_system"
down_revision = "046_request_available_at_and_cleanup_setting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            'ALTER TABLE "media_requests" DROP COLUMN IF EXISTS "vote_count"'
        )
        op.execute('DROP TABLE IF EXISTS "request_votes"')
    else:
        inspector = sa.inspect(bind)
        request_cols = {c["name"] for c in inspector.get_columns("media_requests")}
        if "vote_count" in request_cols:
            op.drop_column("media_requests", "vote_count")
        if "request_votes" in inspector.get_table_names():
            op.drop_table("request_votes")

    inspector_after = sa.inspect(bind)
    cols_after = {
        c["name"] for c in inspector_after.get_columns("media_requests")
    }
    tables_after = set(inspector_after.get_table_names())
    leftovers = []
    if "vote_count" in cols_after:
        leftovers.append("media_requests.vote_count")
    if "request_votes" in tables_after:
        leftovers.append("request_votes")
    if leftovers:
        raise RuntimeError(
            f"Migration 047 ran but dead vote artefacts remain: {leftovers}. "
            "Underlying DDL did not apply."
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    request_cols = {c["name"] for c in inspector.get_columns("media_requests")}
    if "vote_count" not in request_cols:
        op.add_column(
            "media_requests",
            sa.Column(
                "vote_count",
                sa.Integer,
                server_default=sa.text("0"),
                nullable=False,
            ),
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
