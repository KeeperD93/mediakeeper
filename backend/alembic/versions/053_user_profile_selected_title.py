"""Add ``selected_title`` to ``user_profiles``.

The achievements system lets a player equip a unlocked title that is
displayed alongside their profile (badge wall, leaderboard, GDPR export,
portal /me payload). The ``selected_title`` column was added to the
``UserProfile`` model when the feature shipped, but no Alembic
migration was created to back it. Deployments bootstrapped via
``Base.metadata.create_all`` had the column from day one; deployments
that go through ``alembic upgrade head`` (the production path with
``MK_DB_SCHEMA_MODE=validate``) ended up with the table but **without**
the column. The result is a hard failure on first portal-login (500
Internal Server Error) and a crash loop on the ``expire_users``
scheduler task, since both flows ``SELECT ... user_profiles.selected_
title ...``.

Same DDL pattern as 048/052: native ``ADD COLUMN IF NOT EXISTS`` on
PostgreSQL, inspector-guarded ``add_column`` fallback on SQLite, and a
post-condition that raises if the column is still missing — so a silent
no-op in batch_alter_table can never recur for this fix.
"""
from alembic import op
import sqlalchemy as sa


revision = "053_user_profile_selected_title"
down_revision = "052_mk_events_max_participants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            'ALTER TABLE "user_profiles" '
            'ADD COLUMN IF NOT EXISTS "selected_title" '
            'VARCHAR(100)'
        )
    else:
        inspector = sa.inspect(bind)
        cols = {c["name"] for c in inspector.get_columns("user_profiles")}
        if "selected_title" not in cols:
            op.add_column(
                "user_profiles",
                sa.Column(
                    "selected_title",
                    sa.String(length=100),
                    nullable=True,
                ),
            )

    cols_after = {
        c["name"] for c in sa.inspect(bind).get_columns("user_profiles")
    }
    if "selected_title" not in cols_after:
        raise RuntimeError(
            "Migration 053 silently failed to add user_profiles.selected_title."
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            'ALTER TABLE "user_profiles" '
            'DROP COLUMN IF EXISTS "selected_title"'
        )
    else:
        inspector = sa.inspect(bind)
        cols = {c["name"] for c in inspector.get_columns("user_profiles")}
        if "selected_title" in cols:
            op.drop_column("user_profiles", "selected_title")
