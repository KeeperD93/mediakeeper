"""A profile never linked to a media-server user is local

``user_profiles.source`` came with migration 035, set to ``emby`` on every
profile already there, the backoffice admin's included. Only a profile holding
an Emby id is linked, as the leaderboard and the earning rule tell: the others
are relabelled ``local`` so the users list stops calling them Emby.
Irreversible: the relabelled profiles cannot be told apart afterwards, so
``downgrade`` is a no-op.

Revision ID: 068_unlinked_profiles_local
Revises: 067_drop_can_earn_xp_offline
Create Date: 2026-11-07
"""
from alembic import op

revision = "068_unlinked_profiles_local"
down_revision = "067_drop_can_earn_xp_offline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE user_profiles SET source = 'local' "
        "WHERE source = 'emby' AND emby_user_id IS NULL"
    )


def downgrade() -> None:
    # Irreversible: the relabelled profiles cannot be told apart.
    pass
