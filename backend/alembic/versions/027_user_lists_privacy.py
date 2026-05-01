"""Extend user_lists with 3-tier privacy + contributors/history tables.

- user_lists: drop is_public, add privacy/content_type/genres/copy_count/
  owner_muted/is_deleted/deleted_at/updated_at.
- user_list_items: add added_by_user_id.
- New tables: user_list_contributors, user_list_history.

DB wipe is scheduled at v1.0 so the migration freely drops the legacy
is_public column instead of keeping an alias.
"""
from alembic import op
import sqlalchemy as sa

revision = "027_user_lists_privacy"
down_revision = "026_request_retry_count"
branch_labels = None
depends_on = None


def _existing_cols(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {c["name"] for c in inspector.get_columns(table)}


def _existing_tables() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    lists_cols = _existing_cols("user_lists")

    # --- user_lists: new columns ---
    if "privacy" not in lists_cols:
        op.add_column(
            "user_lists",
            sa.Column("privacy", sa.String(20),
                      server_default="private", nullable=False),
        )
        op.create_index("ix_user_lists_privacy", "user_lists", ["privacy"])
    if "content_type" not in lists_cols:
        op.add_column(
            "user_lists",
            sa.Column("content_type", sa.String(20),
                      server_default="mixed", nullable=False),
        )
    if "genres" not in lists_cols:
        op.add_column("user_lists", sa.Column("genres", sa.JSON, nullable=True))
    if "copy_count" not in lists_cols:
        op.add_column(
            "user_lists",
            sa.Column("copy_count", sa.Integer,
                      server_default="0", nullable=False),
        )
    if "owner_muted" not in lists_cols:
        op.add_column(
            "user_lists",
            sa.Column("owner_muted", sa.Boolean,
                      server_default=sa.text("false"), nullable=False),
        )
    if "is_deleted" not in lists_cols:
        op.add_column(
            "user_lists",
            sa.Column("is_deleted", sa.Boolean,
                      server_default=sa.text("false"), nullable=False),
        )
        op.create_index("ix_user_lists_is_deleted",
                        "user_lists", ["is_deleted"])
    if "deleted_at" not in lists_cols:
        op.add_column(
            "user_lists",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "updated_at" not in lists_cols:
        op.add_column(
            "user_lists",
            sa.Column("updated_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # --- user_lists: drop legacy is_public ---
    if "is_public" in lists_cols:
        with op.batch_alter_table("user_lists") as batch:
            batch.drop_column("is_public")

    # --- user_list_items: added_by_user_id ---
    items_cols = _existing_cols("user_list_items")
    if "added_by_user_id" not in items_cols:
        op.add_column(
            "user_list_items",
            sa.Column(
                "added_by_user_id", sa.Integer,
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )

    tables = _existing_tables()

    # --- user_list_contributors ---
    if "user_list_contributors" not in tables:
        op.create_table(
            "user_list_contributors",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("list_id", sa.Integer,
                      sa.ForeignKey("user_lists.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("user_id", sa.Integer,
                      sa.ForeignKey("users.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("muted", sa.Boolean,
                      server_default=sa.text("false"), nullable=False),
            sa.Column("added_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
            sa.UniqueConstraint("list_id", "user_id", name="uq_list_contributor"),
        )

    # --- user_list_history ---
    if "user_list_history" not in tables:
        op.create_table(
            "user_list_history",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("list_id", sa.Integer,
                      sa.ForeignKey("user_lists.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("user_id", sa.Integer,
                      sa.ForeignKey("users.id", ondelete="SET NULL"),
                      nullable=True),
            sa.Column("action", sa.String(30), nullable=False, index=True),
            sa.Column("tmdb_id", sa.Integer, nullable=True),
            sa.Column("media_type", sa.String(20), nullable=True),
            sa.Column("title", sa.String(500), nullable=True),
            sa.Column("extra", sa.JSON, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), index=True),
        )


def downgrade() -> None:
    tables = _existing_tables()
    if "user_list_history" in tables:
        op.drop_table("user_list_history")
    if "user_list_contributors" in tables:
        op.drop_table("user_list_contributors")

    items_cols = _existing_cols("user_list_items")
    if "added_by_user_id" in items_cols:
        with op.batch_alter_table("user_list_items") as batch:
            batch.drop_column("added_by_user_id")

    lists_cols = _existing_cols("user_lists")
    with op.batch_alter_table("user_lists") as batch:
        if "updated_at" in lists_cols:
            batch.drop_column("updated_at")
        if "deleted_at" in lists_cols:
            batch.drop_column("deleted_at")
        if "is_deleted" in lists_cols:
            batch.drop_column("is_deleted")
        if "owner_muted" in lists_cols:
            batch.drop_column("owner_muted")
        if "copy_count" in lists_cols:
            batch.drop_column("copy_count")
        if "genres" in lists_cols:
            batch.drop_column("genres")
        if "content_type" in lists_cols:
            batch.drop_column("content_type")
        if "privacy" in lists_cols:
            batch.drop_column("privacy")
        if "is_public" not in lists_cols:
            batch.add_column(sa.Column(
                "is_public", sa.Boolean,
                server_default=sa.text("true"), nullable=False,
            ))
