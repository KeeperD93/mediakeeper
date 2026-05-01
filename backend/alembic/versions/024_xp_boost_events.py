"""Add xp_boost_events table for Demandes XP campaigns."""
from alembic import op
import sqlalchemy as sa


revision = "024_xp_boost_events"
down_revision = "023_request_blacklist"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "xp_boost_events" in inspector.get_table_names():
        return

    op.create_table(
        "xp_boost_events",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("multiplier", sa.Float(), nullable=False, server_default=sa.text("2.0")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action_filter", sa.String(length=500), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "xp_boost_events" in inspector.get_table_names():
        op.drop_table("xp_boost_events")
