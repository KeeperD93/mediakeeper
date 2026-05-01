"""Premium user management: source, granular permissions, access window, soft-delete, audit log.

Adds the columns needed by the refactored Portal admin "Users" page:

- ``source`` (str, default ``"emby"``) — distinguishes Emby-imported users
  from MediaKeeper-local accounts (manual creation flow).
- ``emby_user_id`` (str(64), nullable, indexed) — the Emby/Jellyfin user
  GUID, required to enable/disable the upstream account from the admin
  drawer.
- ``first_name`` / ``last_name`` / ``email`` (nullable) — admin-managed
  identity fields exposed on the Identity tab. Email is plain string,
  not unique, since two Emby users can share an external mailbox.
- ``access_start_date`` / ``access_end_date`` (datetime, nullable) — open
  access window for time-limited accounts (auto-deactivate at end_date).
- ``last_seen_at`` / ``last_login_at`` / ``last_login_ip`` /
  ``last_login_user_agent`` — populated by the auth layer, surfaced on
  the Security tab + online indicator on the list.
- ``admin_notes`` (text) and ``tags`` (json array) — admin-only metadata
  for triage (VIP, beta-tester, problematic…).
- ``can_chat`` / ``can_portal`` / ``can_problems`` / ``can_lists`` /
  ``can_earn_xp_offline`` — granular permissions overriding the role's
  preset. ``can_chat`` mirrors the legacy ``chat_enabled`` column at
  migration time so existing toggles keep working.
- ``deleted_at`` / ``deleted_by_user_id`` — soft-delete. The row stays
  in DB, queries filter ``deleted_at IS NULL`` to hide it from the list,
  and ownership of related data (requests, lists, tickets) is preserved.

Adds ``admin_audit_log`` table — every admin action that touches a user
profile is appended here (who, when, what, payload, IP).
"""
from alembic import op
import sqlalchemy as sa


revision = "035_users_premium_management"
down_revision = "034_chat_last_read"
branch_labels = None
depends_on = None


_NEW_PROFILE_COLUMNS: list[tuple[str, sa.Column]] = [
    ("source", sa.Column("source", sa.String(20), server_default="emby", nullable=False)),
    ("emby_user_id", sa.Column("emby_user_id", sa.String(64), nullable=True)),
    ("first_name", sa.Column("first_name", sa.String(100), nullable=True)),
    ("last_name", sa.Column("last_name", sa.String(100), nullable=True)),
    ("email", sa.Column("email", sa.String(255), nullable=True)),
    ("access_start_date", sa.Column("access_start_date", sa.DateTime(timezone=True), nullable=True)),
    ("access_end_date", sa.Column("access_end_date", sa.DateTime(timezone=True), nullable=True)),
    ("last_seen_at", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True)),
    ("last_login_at", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True)),
    ("last_login_ip", sa.Column("last_login_ip", sa.String(64), nullable=True)),
    ("last_login_user_agent", sa.Column("last_login_user_agent", sa.String(255), nullable=True)),
    ("admin_notes", sa.Column("admin_notes", sa.Text(), nullable=True)),
    ("tags", sa.Column("tags", sa.JSON(), nullable=True)),
    ("can_chat", sa.Column("can_chat", sa.Boolean(), server_default=sa.text("true"), nullable=False)),
    ("can_portal", sa.Column("can_portal", sa.Boolean(), server_default=sa.text("true"), nullable=False)),
    ("can_problems", sa.Column("can_problems", sa.Boolean(), server_default=sa.text("true"), nullable=False)),
    ("can_lists", sa.Column("can_lists", sa.Boolean(), server_default=sa.text("true"), nullable=False)),
    ("can_earn_xp_offline", sa.Column("can_earn_xp_offline", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
    ("deleted_at", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)),
    ("deleted_by_user_id", sa.Column("deleted_by_user_id", sa.Integer(), nullable=True)),
]

_NEW_PROFILE_INDEXES = [
    ("ix_user_profiles_emby_user_id", "emby_user_id"),
    ("ix_user_profiles_source", "source"),
    ("ix_user_profiles_deleted_at", "deleted_at"),
    ("ix_user_profiles_access_end_date", "access_end_date"),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    for name, column in _NEW_PROFILE_COLUMNS:
        if name not in cols:
            op.add_column("user_profiles", column)

    # Mirror chat_enabled into can_chat at migration time so existing toggles
    # keep working until the admin UI starts writing the new column directly.
    if "can_chat" not in cols and "chat_enabled" in cols:
        op.execute("UPDATE user_profiles SET can_chat = chat_enabled")

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("user_profiles")}
    for index_name, column in _NEW_PROFILE_INDEXES:
        if index_name not in existing_indexes:
            op.create_index(index_name, "user_profiles", [column])

    # admin_audit_log
    if "admin_audit_log" not in inspector.get_table_names():
        op.create_table(
            "admin_audit_log",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("admin_user_id", sa.Integer(), nullable=True),
            sa.Column("target_user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(64), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("ip", sa.String(64), nullable=True),
            sa.Column("user_agent", sa.String(255), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_admin_audit_log_admin_user_id", "admin_audit_log", ["admin_user_id"])
        op.create_index("ix_admin_audit_log_target_user_id", "admin_audit_log", ["target_user_id"])
        op.create_index("ix_admin_audit_log_created_at", "admin_audit_log", ["created_at"])
        op.create_index("ix_admin_audit_log_action", "admin_audit_log", ["action"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "admin_audit_log" in inspector.get_table_names():
        for index_name in (
            "ix_admin_audit_log_admin_user_id",
            "ix_admin_audit_log_target_user_id",
            "ix_admin_audit_log_created_at",
            "ix_admin_audit_log_action",
        ):
            try:
                op.drop_index(index_name, table_name="admin_audit_log")
            except Exception:
                pass
        op.drop_table("admin_audit_log")

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("user_profiles")}
    for index_name, _ in _NEW_PROFILE_INDEXES:
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="user_profiles")

    cols = {c["name"] for c in inspector.get_columns("user_profiles")}
    for name, _ in reversed(_NEW_PROFILE_COLUMNS):
        if name in cols:
            op.drop_column("user_profiles", name)
