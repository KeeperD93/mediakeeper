"""Add hide_adult column to user_profiles."""
from alembic import op
import sqlalchemy as sa

revision = "017_profile_hide_adult"
down_revision = "016_mk_events"
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent: only add the column if it doesn't already exist, so the
    # migration can be re-run safely after a partial failure.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    if "hide_adult" not in cols:
        op.add_column(
            "user_profiles",
            sa.Column("hide_adult", sa.Boolean(), server_default="true", nullable=False),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    if "hide_adult" in cols:
        op.drop_column("user_profiles", "hide_adult")
