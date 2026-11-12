"""Every profile starts at level 1

A new profile is created at level 1, but a first XP grant under 100 XP used to
recompute its level to 0. The level is now never below 1: profiles left at 0 are
set to 1, which is what the level computed from their XP gives today. Level 1
grants no trophy and no title, so nothing else follows.
Irreversible: the profiles raised cannot be told apart afterwards, so
``downgrade`` is a no-op.

Revision ID: 069_profile_level_floor
Revises: 068_unlinked_profiles_local
Create Date: 2026-11-11
"""
from alembic import op

revision = "069_profile_level_floor"
down_revision = "068_unlinked_profiles_local"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE user_profiles SET level = 1 WHERE level < 1")


def downgrade() -> None:
    # Irreversible: the profiles raised cannot be told apart.
    pass
