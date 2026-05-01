"""Mirror the Emby ``IsDisabled`` flag onto ``user_profiles`` so the admin
list can show "actif côté MK / désactivé côté Emby" without an extra Emby
round-trip per row.

The column is nullable because we don't know the upstream state until the
admin runs the "Synchroniser les ID Emby" pass (or until the user logs in
again, where ``emby_auth.py`` could backfill in a future iteration).
"""
from alembic import op
import sqlalchemy as sa


revision = "036_user_profile_emby_disabled"
down_revision = "035_users_premium_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    if "emby_is_disabled" not in cols:
        op.add_column(
            "user_profiles",
            sa.Column("emby_is_disabled", sa.Boolean(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    if "emby_is_disabled" in cols:
        op.drop_column("user_profiles", "emby_is_disabled")
