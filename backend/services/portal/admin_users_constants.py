"""Constants for the premium admin "Users" page.

Centralised so that the API schema, the role preset application and
the front constants stay in sync. Keys mirror the columns added by
migration ``035_users_premium_management``.
"""

ROLE_VIEWER = "viewer"
ROLE_MODERATOR = "moderator"
ROLE_ADMIN = "admin"
ROLES = (ROLE_VIEWER, ROLE_MODERATOR, ROLE_ADMIN)

# Granular permission flag names — every entry maps to a column on
# ``UserProfile``. Adding one means: 1) new column in a migration,
# 2) new key here, 3) new entry in ``ROLE_PRESETS`` for each role.
PERMISSION_KEYS = (
    "can_chat",
    "can_portal",
    "can_problems",
    "can_lists",
    "can_earn_xp_offline",
)

# Default permission set applied when an admin switches a user's role.
# Individual flags can be overriden afterwards via the permissions tab.
ROLE_PRESETS: dict[str, dict[str, bool]] = {
    ROLE_VIEWER: {
        "can_chat": True,
        "can_portal": True,
        "can_problems": True,
        "can_lists": True,
        "can_earn_xp_offline": False,
    },
    ROLE_MODERATOR: {
        "can_chat": True,
        "can_portal": True,
        "can_problems": True,
        "can_lists": True,
        "can_earn_xp_offline": False,
    },
    ROLE_ADMIN: {
        "can_chat": True,
        "can_portal": True,
        "can_problems": True,
        "can_lists": True,
        "can_earn_xp_offline": True,
    },
}

# Source of an account: imported from Emby/Jellyfin or created locally
# in MediaKeeper for someone without a streaming account (a partner, a
# beta tester…).
SOURCE_EMBY = "emby"
SOURCE_LOCAL = "local"
SOURCES = (SOURCE_EMBY, SOURCE_LOCAL)

# Audit log actions — keep flat string constants so a free-text search
# in DB stays trivial. Anything mutating a user profile must record one.
ACTION_USER_CREATED = "user.created"
ACTION_USER_IMPORTED = "user.imported"
ACTION_USER_UPDATED_IDENTITY = "user.identity_updated"
ACTION_USER_ROLE_CHANGED = "user.role_changed"
ACTION_USER_PERMISSIONS_CHANGED = "user.permissions_changed"
ACTION_USER_ACCESS_WINDOW = "user.access_window_set"
ACTION_USER_ACCESS_EXTENDED = "user.access_extended"
ACTION_USER_ACCESS_EXPIRED = "user.access_expired"
ACTION_USER_ACTIVATED = "user.activated"
ACTION_USER_DEACTIVATED = "user.deactivated"
ACTION_USER_EMBY_ENABLED = "user.emby_enabled"
ACTION_USER_EMBY_DISABLED = "user.emby_disabled"
ACTION_USER_PASSWORD_RESET = "user.password_reset"
ACTION_USER_NOTES_UPDATED = "user.notes_updated"
ACTION_USER_TAGS_UPDATED = "user.tags_updated"
ACTION_USER_NOTIFICATION_SENT = "user.notification_sent"
ACTION_USER_RGPD_EXPORT = "user.rgpd_export"
ACTION_USER_SOFT_DELETED = "user.soft_deleted"
ACTION_USER_RESTORED = "user.restored"
ACTION_USER_BULK = "user.bulk_action"
ACTION_USER_FORCE_LOGOUT = "user.force_logout"
ACTION_USER_DELETION_REQUEST_CANCELLED = "user.deletion_request_cancelled"

# Bulk action ids used by the list view.
BULK_ACTIVATE = "activate"
BULK_DEACTIVATE = "deactivate"
BULK_DELETE = "delete"
BULK_SET_ROLE = "set_role"
BULK_SET_PERMISSIONS = "set_permissions"
BULK_EXPORT = "export"
BULK_ACTIONS = (
    BULK_ACTIVATE, BULK_DEACTIVATE, BULK_DELETE,
    BULK_SET_ROLE, BULK_SET_PERMISSIONS, BULK_EXPORT,
)

# Number of days before access_end_date that should surface a warning
# in the list ("expires soon" filter + visual badge on the row).
ACCESS_EXPIRY_WARNING_DAYS = 7

# A user that hasn't pinged the API for more than this is considered
# offline by the online indicator on the list.
ONLINE_WINDOW_SECONDS = 90
