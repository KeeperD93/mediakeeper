"""Premium profile settings: display_name lock + first-login flag + custom avatar path.

Adds:
- ``display_name_must_set`` (bool, default true) — forces a username pick on
  first portal login. Set to false once the user picks a name.
- ``display_name_changed_at`` (datetime, nullable) — stamp of the latest
  username change. Used to enforce the 6-month rename cooldown.
- ``avatar_custom_path`` (str(500), nullable) — relative path under
  ``/data/avatars`` of an avatar uploaded through MediaKeeper. When set,
  takes precedence over the Emby-proxied ``avatar_url``.
- Functional unique index on ``LOWER(display_name)`` so usernames are
  case-insensitively unique across the portal.
"""
from alembic import op
import sqlalchemy as sa


revision = "031_profile_settings_premium"
down_revision = "030_list_item_metadata"
branch_labels = None
depends_on = None


_INDEX_NAME = "ix_user_profiles_display_name_lower"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("user_profiles")}

    if "display_name_must_set" not in cols:
        op.add_column(
            "user_profiles",
            sa.Column(
                "display_name_must_set",
                sa.Boolean(),
                server_default=sa.text("true"),
                nullable=False,
            ),
        )
    if "display_name_changed_at" not in cols:
        op.add_column(
            "user_profiles",
            sa.Column(
                "display_name_changed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
    if "avatar_custom_path" not in cols:
        op.add_column(
            "user_profiles",
            sa.Column("avatar_custom_path", sa.String(500), nullable=True),
        )

    # Functional unique index on LOWER(display_name).
    # Skip on SQLite (test env) — SQLite doesn't enforce functional unique
    # indexes the same way and the tests assert business logic, not DB
    # constraints. Postgres (prod) gets the real unique guard.
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("user_profiles")}
    if _INDEX_NAME not in existing_indexes and bind.dialect.name == "postgresql":
        op.create_index(
            _INDEX_NAME,
            "user_profiles",
            [sa.text("LOWER(display_name)")],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("user_profiles")}
    if _INDEX_NAME in existing_indexes:
        op.drop_index(_INDEX_NAME, table_name="user_profiles")

    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    if "avatar_custom_path" in cols:
        op.drop_column("user_profiles", "avatar_custom_path")
    if "display_name_changed_at" in cols:
        op.drop_column("user_profiles", "display_name_changed_at")
    if "display_name_must_set" in cols:
        op.drop_column("user_profiles", "display_name_must_set")
