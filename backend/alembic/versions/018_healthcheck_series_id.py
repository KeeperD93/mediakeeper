"""Add series_id column to healthcheck_results."""
from alembic import op
import sqlalchemy as sa

revision = "018_healthcheck_series_id"
down_revision = "017_profile_hide_adult"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("healthcheck_results")}
    if "series_id" not in cols:
        op.add_column(
            "healthcheck_results",
            sa.Column("series_id", sa.String(length=100), nullable=True),
        )
        op.create_index("ix_hc_series_id", "healthcheck_results", ["series_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("healthcheck_results")}
    if "series_id" in cols:
        op.drop_index("ix_hc_series_id", "healthcheck_results")
        op.drop_column("healthcheck_results", "series_id")
