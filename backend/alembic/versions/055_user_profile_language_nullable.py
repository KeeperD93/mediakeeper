"""Make user_profiles.language nullable — NULL inherits the instance default.

The portal language becomes a per-user OVERRIDE of an instance-wide default
(settings key ``portal.default_language``). A NULL value means "inherit". Rows
created before this feature all carry the old ``server_default`` ``'fr'``,
indistinguishable from a real choice, so they are converted to NULL: the
instance default then applies to everyone who has not explicitly picked a
language. New rows are born NULL (``server_default`` dropped).

Idempotent: the column alter is skipped when ``language`` is already nullable
(deployments bootstrapped via ``Base.metadata.create_all`` already have it).
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
    if not _language_nullable(bind):
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


def downgrade() -> None:
    op.execute("UPDATE user_profiles SET language = 'fr' WHERE language IS NULL")
    with op.batch_alter_table("user_profiles") as batch:
        batch.alter_column(
            "language",
            existing_type=sa.String(length=10),
            nullable=False,
            server_default="fr",
        )
