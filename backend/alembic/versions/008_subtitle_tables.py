"""create subtitle_downloads and subtitle_profiles tables

Revision ID: 008_subtitle_tables
Revises: 007_healthcheck
Create Date: 2026-04-05
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "008_subtitle_tables"
down_revision: Union[str, None] = "007_healthcheck"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Download history ---
    op.create_table(
        "subtitle_downloads",
        sa.Column("id",                 sa.Integer,                        primary_key=True, index=True),
        sa.Column("emby_item_id",       sa.String(64),    nullable=False),
        sa.Column("media_name",         sa.String(500),   nullable=False),
        sa.Column("media_type",         sa.String(20),    nullable=True),
        sa.Column("series_name",        sa.String(300),   nullable=True),
        sa.Column("season",             sa.Integer,       nullable=True),
        sa.Column("episode",            sa.Integer,       nullable=True),
        sa.Column("os_file_id",         sa.Integer,       nullable=False),
        sa.Column("os_subtitle_id",     sa.String(50),    nullable=True),
        sa.Column("file_name",          sa.String(500),   nullable=True),
        sa.Column("language",           sa.String(10),    nullable=False),
        sa.Column("destination",        sa.String(1000),  nullable=False),
        sa.Column("file_size",          sa.Integer,       nullable=True),
        sa.Column("quality_score",      sa.Float,         nullable=True),
        sa.Column("hash_match",         sa.Boolean,       server_default=sa.text("false")),
        sa.Column("hearing_impaired",   sa.Boolean,       server_default=sa.text("false")),
        sa.Column("foreign_parts_only", sa.Boolean,       server_default=sa.text("false")),
        sa.Column("from_trusted",       sa.Boolean,       server_default=sa.text("false")),
        sa.Column("ai_translated",      sa.Boolean,       server_default=sa.text("false")),
        sa.Column("source",             sa.String(50),    server_default="opensubtitles"),
        sa.Column("downloaded_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_subdl_emby_item", "subtitle_downloads", ["emby_item_id"])
    op.create_index("ix_subdl_language",  "subtitle_downloads", ["language"])
    op.create_index("ix_subdl_date",      "subtitle_downloads", ["downloaded_at"])

    # --- Subtitle profiles ---
    op.create_table(
        "subtitle_profiles",
        sa.Column("id",                sa.Integer,                        primary_key=True, index=True),
        sa.Column("name",              sa.String(100),   nullable=False),
        sa.Column("is_default",        sa.Boolean,       server_default=sa.text("false")),
        sa.Column("languages",         sa.Text,          nullable=False),
        sa.Column("include_hi",        sa.Boolean,       server_default=sa.text("false")),
        sa.Column("include_forced",    sa.Boolean,       server_default=sa.text("true")),
        sa.Column("exclude_ai",        sa.Boolean,       server_default=sa.text("true")),
        sa.Column("exclude_machine",   sa.Boolean,       server_default=sa.text("true")),
        sa.Column("prefer_trusted",    sa.Boolean,       server_default=sa.text("true")),
        sa.Column("prefer_hash_match", sa.Boolean,       server_default=sa.text("true")),
        sa.Column("auto_download",     sa.Boolean,       server_default=sa.text("false")),
        sa.Column("min_score",         sa.Float,         server_default=sa.text("3.0")),
        sa.Column("created_at",        sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",        sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed a default profile
    op.execute(
        sa.text(
            "INSERT INTO subtitle_profiles (name, is_default, languages) "
            "VALUES ('Par défaut', true, '[\"fre\",\"eng\"]')"
        )
    )


def downgrade() -> None:
    op.drop_table("subtitle_profiles")
    op.drop_table("subtitle_downloads")
