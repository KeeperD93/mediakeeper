"""Make user_profiles.language nullable — NULL inherits the instance default.

The portal language becomes a per-user OVERRIDE of an instance-wide default
(settings key ``portal.default_language``). A NULL value means "inherit". Rows
created before this feature all carry the old ``server_default`` ``'fr'``,
indistinguishable from a real choice, so they are converted to NULL: the
instance default then applies to everyone who has not explicitly picked a
language. New rows are born NULL (``server_default`` dropped).

Same DDL dispatch as 053: native ``ALTER COLUMN`` on PostgreSQL,
inspector-guarded ``batch_alter_table`` on SQLite, and a post-condition that
raises if the column is still NOT NULL — so a silent ``batch_alter_table``
no-op on asyncpg can never recur for this change.
"""
from alembic import op
import sqlalchemy as sa


revision = "055_user_profile_language_nullable"
down_revision = "054_tmdb_runtime_cache"
branch_labels = None
depends_on = None


def _language_nullable(bind) -> bool:
    col = {c["name"]: c for c in sa.inspect(bind).get_columns("user_profiles")}.get("language")
    return bool(col and col.get("nullable"))


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE user_profiles ALTER COLUMN language DROP NOT NULL")
        op.execute("ALTER TABLE user_profiles ALTER COLUMN language DROP DEFAULT")
    elif not _language_nullable(bind):
        with op.batch_alter_table("user_profiles") as batch:
            batch.alter_column(
                "language",
                existing_type=sa.String(length=10),
                nullable=True,
                server_default=None,
            )
    # Pre-feature 'fr' is the old default, not a real choice -> NULL so the
    # instance default applies until the user explicitly picks a language.
    op.execute("UPDATE user_profiles SET language = NULL WHERE language = 'fr'")
    if not _language_nullable(bind):
        raise RuntimeError(
            "Migration 055 silently failed to make user_profiles.language nullable."
        )


def downgrade() -> None:
    op.execute("UPDATE user_profiles SET language = 'fr' WHERE language IS NULL")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE user_profiles ALTER COLUMN language SET DEFAULT 'fr'")
        op.execute("ALTER TABLE user_profiles ALTER COLUMN language SET NOT NULL")
    else:
        with op.batch_alter_table("user_profiles") as batch:
            batch.alter_column(
                "language",
                existing_type=sa.String(length=10),
                nullable=False,
                server_default="fr",
            )
