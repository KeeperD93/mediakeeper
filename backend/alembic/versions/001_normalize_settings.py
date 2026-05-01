"""create user_preferences, watchlist_scans, notification_channels and migrate data from settings

Revision ID: 001_normalize_settings
Revises: 000_baseline_core
Create Date: 2026-03-19
"""
from typing import Sequence, Union
from alembic import context, op
import sqlalchemy as sa

revision: str = "001_normalize_settings"
down_revision: Union[str, None] = "000_baseline_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- 1. Create the new tables ----
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("preferences", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("dashboard_layout", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"])

    op.create_table(
        "watchlist_scans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scan_key", sa.String(200), unique=True, nullable=False),
        sa.Column("data", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_watchlist_scans_scan_key", "watchlist_scans", ["scan_key"])

    op.create_table(
        "notification_channels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("channel_key", sa.String(200), unique=True, nullable=False),
        sa.Column("data", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notification_channels_channel_key", "notification_channels", ["channel_key"])

    # ---- 2. Migrate data from settings ----
    if context.is_offline_mode():
        op.execute("-- Offline SQL mode: legacy settings row migration is online-only.")
        return

    conn = op.get_bind()

    # -- user_preferences : user.{id}.preferences + user.{id}.dashboard.layout --
    rows = conn.execute(
        sa.text("SELECT key, value FROM settings WHERE key LIKE 'user.%.preferences' OR key LIKE 'user.%.dashboard.layout'")
    ).fetchall()

    user_prefs = {}  # user_id -> {"preferences": ..., "dashboard_layout": ...}
    for key, value in rows:
        parts = key.split(".")
        # user.{id}.preferences  OR  user.{id}.dashboard.layout
        try:
            uid = int(parts[1])
        except (IndexError, ValueError):
            continue
        if uid not in user_prefs:
            user_prefs[uid] = {"preferences": "{}", "dashboard_layout": "{}"}
        if key.endswith(".preferences"):
            user_prefs[uid]["preferences"] = value or "{}"
        elif key.endswith(".dashboard.layout"):
            user_prefs[uid]["dashboard_layout"] = value or "{}"

    for uid, data in user_prefs.items():
        # Check that the user exists
        user_exists = conn.execute(sa.text("SELECT id FROM users WHERE id = :uid"), {"uid": uid}).fetchone()
        if user_exists:
            conn.execute(
                sa.text(
                    "INSERT INTO user_preferences (user_id, preferences, dashboard_layout) "
                    "VALUES (:uid, :prefs, :layout)"
                ),
                {"uid": uid, "prefs": data["preferences"], "layout": data["dashboard_layout"]},
            )

    # -- watchlist_scans : watchlist.* --
    wl_rows = conn.execute(
        sa.text("SELECT key, value FROM settings WHERE key LIKE 'watchlist.%'")
    ).fetchall()
    for key, value in wl_rows:
        # watchlist.scan_results -> scan_key = "scan_results"
        # watchlist.tracked -> "tracked"
        # watchlist.calendar.2026-03 -> "calendar.2026-03"
        scan_key = key.replace("watchlist.", "", 1)
        conn.execute(
            sa.text("INSERT INTO watchlist_scans (scan_key, data) VALUES (:sk, :d)"),
            {"sk": scan_key, "d": value or "{}"},
        )

    # -- notification_channels : notifications.discord, notifications.imgur, notifications.queue --
    notif_keys = ["notifications.discord", "notifications.imgur", "notifications.queue"]
    for nk in notif_keys:
        row = conn.execute(
            sa.text("SELECT value FROM settings WHERE key = :k"), {"k": nk}
        ).fetchone()
        if row:
            channel_key = nk.replace("notifications.", "", 1)
            conn.execute(
                sa.text("INSERT INTO notification_channels (channel_key, data) VALUES (:ck, :d)"),
                {"ck": channel_key, "d": row[0] or "{}"},
            )

    # ---- 3. Delete migrated keys from settings ----
    conn.execute(sa.text("DELETE FROM settings WHERE key LIKE 'user.%.preferences'"))
    conn.execute(sa.text("DELETE FROM settings WHERE key LIKE 'user.%.dashboard.layout'"))
    conn.execute(sa.text("DELETE FROM settings WHERE key LIKE 'watchlist.%'"))
    conn.execute(sa.text("DELETE FROM settings WHERE key IN ('notifications.discord', 'notifications.imgur', 'notifications.queue')"))


def downgrade() -> None:
    # Note: data is NOT restored into settings during downgrade.
    # A DB backup before migration is recommended.
    op.drop_index("ix_notification_channels_channel_key", table_name="notification_channels")
    op.drop_table("notification_channels")
    op.drop_index("ix_watchlist_scans_scan_key", table_name="watchlist_scans")
    op.drop_table("watchlist_scans")
    op.drop_index("ix_user_preferences_user_id", table_name="user_preferences")
    op.drop_table("user_preferences")
