"""dedupe user achievements and add unique index

Revision ID: 021_user_ach_unique_idx
Revises: 020_runtime_schema_cleanup
Create Date: 2026-04-13
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "021_user_ach_unique_idx"
down_revision: Union[str, None] = "020_runtime_schema_cleanup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if context.is_offline_mode():
        op.execute("-- Offline SQL mode: duplicate cleanup is online-only.")
        op.execute(sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_user_achievements_user_achievement "
            "ON user_achievements (user_id, achievement_id)"
        ))
        return

    conn = op.get_bind()
    rows = list(conn.execute(sa.text(
        "SELECT id, user_id, achievement_id, progress, unlocked "
        "FROM user_achievements"
    )).mappings())

    rows.sort(key=lambda row: (
        row["user_id"],
        row["achievement_id"],
        -(1 if row["unlocked"] else 0),
        -(row["progress"] or 0),
        -(row["id"] or 0),
    ))

    seen = set()
    duplicates = []
    for row in rows:
        key = (row["user_id"], row["achievement_id"])
        if key in seen:
            duplicates.append(row["id"])
            continue
        seen.add(key)

    for duplicate_id in duplicates:
        conn.execute(
            sa.text("DELETE FROM user_achievements WHERE id = :id"),
            {"id": duplicate_id},
        )

    op.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_user_achievements_user_achievement "
        "ON user_achievements (user_id, achievement_id)"
    ))


def downgrade() -> None:
    op.execute(sa.text(
        "DROP INDEX IF EXISTS uq_user_achievements_user_achievement"
    ))
