"""Remember when a member finished the first-login wizard

``user_profiles.onboarding_completed_at`` stays empty until the member finishes the
portal's first-login wizard. Existing profiles start empty too, on purpose: the
wizard opens once for every account when it ships, existing ones included.
Downgrade drops the column.

Revision ID: 070_profile_onboarding
Revises: 069_profile_level_floor
Create Date: 2026-11-13
"""
import sqlalchemy as sa
from alembic import op

revision = "070_profile_onboarding"
down_revision = "069_profile_level_floor"
branch_labels = None
depends_on = None

_TABLE = "user_profiles"
_COLUMN = "onboarding_completed_at"


def _columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(_TABLE)}


def upgrade() -> None:
    if _COLUMN not in _columns():
        op.add_column(_TABLE, sa.Column(_COLUMN, sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    if _COLUMN in _columns():
        op.drop_column(_TABLE, _COLUMN)
