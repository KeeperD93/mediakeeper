"""Add retry_count to media_requests (resubmission tracking)."""
from alembic import op
import sqlalchemy as sa

revision = "026_request_retry_count"
down_revision = "025_security_log"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("media_requests")}
    if "retry_count" not in cols:
        op.add_column(
            "media_requests",
            sa.Column(
                "retry_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("media_requests")}
    if "retry_count" in cols:
        op.drop_column("media_requests", "retry_count")
