"""Add request_blacklist table (3-strike auto-block for rejected media)."""
from alembic import op
import sqlalchemy as sa

revision = "023_request_blacklist"
down_revision = "022_profile_avatar_effect"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "request_blacklist" not in inspector.get_table_names():
        op.create_table(
            "request_blacklist",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("tmdb_id", sa.Integer, nullable=False, index=True),
            sa.Column("media_type", sa.String(20), nullable=False),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("year", sa.Integer, nullable=True),
            sa.Column("poster_url", sa.String(500), nullable=True),
            sa.Column("requesters", sa.JSON, nullable=True),
            sa.Column("reject_count", sa.Integer, server_default="3", nullable=False),
            sa.Column("blocked_at", sa.DateTime(timezone=True)),
            sa.Column("blocked_by", sa.Integer,
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint("tmdb_id", "media_type", name="uq_blacklist_media"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "request_blacklist" in inspector.get_table_names():
        op.drop_table("request_blacklist")
