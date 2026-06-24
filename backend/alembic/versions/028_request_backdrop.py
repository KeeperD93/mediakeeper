"""Add backdrop_url to media_requests — powers the row
backdrop in the admin requests view. Populated on create from the TMDB
payload; missing values are backfilled live the first time the admin
list loads (see ``services.portal.requests.list_requests``)."""
from alembic import op
import sqlalchemy as sa

revision = "028_request_backdrop"
down_revision = "027_user_lists_privacy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("media_requests")}
    if "backdrop_url" not in cols:
        op.add_column(
            "media_requests",
            sa.Column("backdrop_url", sa.String(500), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("media_requests")}
    if "backdrop_url" in cols:
        with op.batch_alter_table("media_requests") as batch:
            batch.drop_column("backdrop_url")
