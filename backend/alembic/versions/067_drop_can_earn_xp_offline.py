"""Every account earns XP and trophies until it is deactivated

``user_profiles.can_earn_xp_offline`` let an admin allow an account not yet
activated to earn from its Emby plays. Earning now stops only when the account
is deactivated, expires or is deleted (``users.is_active``), so the column goes.
Downgrade adds it back, false for every profile: the old choices are gone.

Revision ID: 067_drop_can_earn_xp_offline
Revises: 066_last_login_from_sign_ins
Create Date: 2026-11-06
"""
import sqlalchemy as sa
from alembic import op

revision = "067_drop_can_earn_xp_offline"
down_revision = "066_last_login_from_sign_ins"
branch_labels = None
depends_on = None

_TABLE = "user_profiles"
_COLUMN = "can_earn_xp_offline"


def _has_column() -> bool:
    return _COLUMN in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(_TABLE)}


def upgrade() -> None:
    # Offline, the inspector reports an empty schema: the drop is rendered anyway.
    if op.get_context().as_sql or _has_column():
        op.drop_column(_TABLE, _COLUMN)


def downgrade() -> None:
    if not _has_column():
        op.add_column(
            _TABLE,
            sa.Column(_COLUMN, sa.Boolean(), server_default=sa.text("false"), nullable=False),
        )
