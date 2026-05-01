"""XP ledger table for tracking experience points with anti-abuse.

Revision ID: 019_xp_ledger
Revises: 018_healthcheck_series_id
"""
revision = "019_xp_ledger"
down_revision = "018_healthcheck_series_id"

from alembic import op
import sqlalchemy as sa


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "xp_ledger" in inspector.get_table_names():
        return

    op.create_table(
        "xp_ledger",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        # Action types: watch_movie, watch_episode, complete_series,
        # daily_login, request_created, request_approved,
        # event_created, event_joined, achievement_unlocked,
        # streak_7, streak_30
        sa.Column("action", sa.String(50), nullable=False),
        # Reference to prevent duplicates: item_id for watches,
        # request_id for requests, date string for daily actions
        sa.Column("reference", sa.String(200), nullable=False),
        sa.Column("xp", sa.Integer, nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        # Unique constraint: same user + action + reference = already granted
        sa.UniqueConstraint("user_id", "action", "reference", name="uq_xp_user_action_ref"),
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "xp_ledger" in inspector.get_table_names():
        op.drop_table("xp_ledger")
