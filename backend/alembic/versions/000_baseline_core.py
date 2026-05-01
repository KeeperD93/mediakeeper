"""baseline core tables used before the first normalized settings migration

Revision ID: 000_baseline_core
Revises: None
Create Date: 2026-04-29
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "000_baseline_core"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set[str]:
    if context.is_offline_mode():
        return set()
    bind = op.get_bind()
    return set(sa.inspect(bind).get_table_names())


def _indexes(table_name: str) -> set[str]:
    if context.is_offline_mode():
        return set()
    bind = op.get_bind()
    return {idx["name"] for idx in sa.inspect(bind).get_indexes(table_name)}


def _create_index_once(name: str, table_name: str, columns: list[str], *, unique: bool = False) -> None:
    if context.is_offline_mode() or name not in _indexes(table_name):
        op.create_index(name, table_name, columns, unique=unique)


def upgrade() -> None:
    tables = _tables()

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(50), nullable=False),
            sa.Column("hashed_password", sa.String(255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("must_change_password", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    _create_index_once("ix_users_id", "users", ["id"])
    _create_index_once("ix_users_username", "users", ["username"], unique=True)

    if "settings" not in tables:
        op.create_table(
            "settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("key", sa.String(100), nullable=False),
            sa.Column("value", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    _create_index_once("ix_settings_id", "settings", ["id"])
    _create_index_once("ix_settings_key", "settings", ["key"], unique=True)

    if "seen_alerts" not in tables:
        op.create_table(
            "seen_alerts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("alert_id", sa.String(255), nullable=False),
            sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        )
    _create_index_once("ix_seen_alerts_id", "seen_alerts", ["id"])
    _create_index_once("ix_seen_alerts_user_id", "seen_alerts", ["user_id"])

    if "library_cache" not in tables:
        op.create_table(
            "library_cache",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("lib_id", sa.String(100), nullable=False),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("collection_type", sa.String(50), nullable=True),
            sa.Column("total_items", sa.Integer(), nullable=True),
            sa.Column("count_movies", sa.Integer(), nullable=True),
            sa.Column("count_series", sa.Integer(), nullable=True),
            sa.Column("count_seasons", sa.Integer(), nullable=True),
            sa.Column("count_episodes", sa.Integer(), nullable=True),
            sa.Column("size_bytes", sa.BigInteger(), nullable=True),
            sa.Column("runtime_ticks", sa.BigInteger(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    _create_index_once("ix_library_cache_id", "library_cache", ["id"])
    _create_index_once("ix_library_cache_lib_id", "library_cache", ["lib_id"], unique=True)

    if "playback_sessions" not in tables:
        op.create_table(
            "playback_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("session_key", sa.String(200), nullable=False),
            sa.Column("user_id", sa.String(100), nullable=False),
            sa.Column("user_name", sa.String(200), nullable=False),
            sa.Column("item_id", sa.String(100), nullable=False),
            sa.Column("item_name", sa.String(500), nullable=False),
            sa.Column("item_type", sa.String(50), nullable=False),
            sa.Column("series_name", sa.String(500), nullable=True),
            sa.Column("season_number", sa.Integer(), nullable=True),
            sa.Column("episode_number", sa.Integer(), nullable=True),
            sa.Column("library_name", sa.String(200), nullable=True),
            sa.Column("client_name", sa.String(200), nullable=True),
            sa.Column("device_name", sa.String(200), nullable=True),
            sa.Column("ip_address", sa.String(100), nullable=True),
            sa.Column("play_method", sa.String(50), nullable=True),
            sa.Column("container", sa.String(50), nullable=True),
            sa.Column("video_codec", sa.String(50), nullable=True),
            sa.Column("audio_codec", sa.String(50), nullable=True),
            sa.Column("resolution", sa.String(20), nullable=True),
            sa.Column("bitrate", sa.Integer(), nullable=True),
            sa.Column("duration_ticks", sa.BigInteger(), nullable=True),
            sa.Column("position_ticks", sa.BigInteger(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
        )
    _create_index_once("ix_playback_sessions_id", "playback_sessions", ["id"])
    _create_index_once("ix_playback_sessions_session_key", "playback_sessions", ["session_key"], unique=True)
    _create_index_once("ix_playback_sessions_user_id", "playback_sessions", ["user_id"])
    _create_index_once("ix_playback_sessions_item_id", "playback_sessions", ["item_id"])
    _create_index_once("ix_playback_started", "playback_sessions", ["started_at"])
    _create_index_once("ix_playback_user_started", "playback_sessions", ["user_id", "started_at"])
    _create_index_once("ix_playback_item_started", "playback_sessions", ["item_type", "started_at"])
    _create_index_once("ix_playback_library", "playback_sessions", ["library_name", "started_at"])


def downgrade() -> None:
    for name, table in (
        ("ix_playback_library", "playback_sessions"),
        ("ix_playback_item_started", "playback_sessions"),
        ("ix_playback_user_started", "playback_sessions"),
        ("ix_playback_started", "playback_sessions"),
        ("ix_playback_sessions_item_id", "playback_sessions"),
        ("ix_playback_sessions_user_id", "playback_sessions"),
        ("ix_playback_sessions_session_key", "playback_sessions"),
        ("ix_playback_sessions_id", "playback_sessions"),
        ("ix_library_cache_lib_id", "library_cache"),
        ("ix_library_cache_id", "library_cache"),
        ("ix_seen_alerts_user_id", "seen_alerts"),
        ("ix_seen_alerts_id", "seen_alerts"),
        ("ix_settings_key", "settings"),
        ("ix_settings_id", "settings"),
        ("ix_users_username", "users"),
        ("ix_users_id", "users"),
    ):
        if context.is_offline_mode() or (table in _tables() and name in _indexes(table)):
            op.drop_index(name, table_name=table)

    for table in ("playback_sessions", "library_cache", "seen_alerts", "settings", "users"):
        if context.is_offline_mode() or table in _tables():
            op.drop_table(table)
