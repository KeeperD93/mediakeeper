/**
 * Premium admin "Users" page — shared constants.
 * Mirrors backend services/portal/admin_users_constants.py.
 * Anything added here must also exist server-side.
 */

export const USER_ROLE = Object.freeze({
  VIEWER: 'viewer',
  MODERATOR: 'moderator',
  ADMIN: 'admin',
})

export const USER_ROLES = [USER_ROLE.VIEWER, USER_ROLE.MODERATOR, USER_ROLE.ADMIN]

export const USER_SOURCE = Object.freeze({
  EMBY: 'emby',
  LOCAL: 'local',
})

export const USER_SOURCES = [USER_SOURCE.EMBY, USER_SOURCE.LOCAL]

// Request-quota mode, exchanged with the backend (RequestQuota.mode).
export const QUOTA_MODE = Object.freeze({
  MANUAL: 'manual',
  AUTO: 'auto',
})

export const PERMISSION_KEYS = Object.freeze([
  'can_chat',
  'can_portal',
  'can_problems',
  'can_lists',
  'can_earn_xp_offline',
])

export const STATUS_FILTER = Object.freeze({
  ALL: '',
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  EXPIRED: 'expired',
  NEVER_LOGGED_IN: 'never_logged_in',
})

export const STATUS_FILTERS = [
  STATUS_FILTER.ALL,
  STATUS_FILTER.ACTIVE,
  STATUS_FILTER.INACTIVE,
  STATUS_FILTER.EXPIRED,
  STATUS_FILTER.NEVER_LOGGED_IN,
]

export const BULK_ACTION = Object.freeze({
  ACTIVATE: 'activate',
  DEACTIVATE: 'deactivate',
  DELETE: 'delete',
  SET_ROLE: 'set_role',
  SET_PERMISSIONS: 'set_permissions',
  SET_QUOTA: 'set_quota',
  EXPORT: 'export',
  // Frontend-only: the bulk-edit overlay fans this out into SET_PERMISSIONS
  // and/or SET_QUOTA at the page level; it never reaches the backend.
  BULK_EDIT: 'bulk_edit',
})

export const SORT_KEYS = Object.freeze([
  'display_name',
  'username',
  'level',
  'xp',
  'last_seen_at',
  'access_end_date',
  'created_at',
])

export const VIEW_MODE = Object.freeze({
  TABLE: 'table',
  CARDS: 'cards',
})

export const DRAWER_TAB = Object.freeze({
  IDENTITY: 'identity',
  ACCESS: 'access',
  QUOTA: 'quota',
  SECURITY: 'security',
  ACTIVITY: 'activity',
  TROPHIES: 'trophies',
  NOTES: 'notes',
  AUDIT: 'audit',
})

export const DRAWER_TABS = [
  DRAWER_TAB.IDENTITY,
  DRAWER_TAB.ACCESS,
  DRAWER_TAB.QUOTA,
  DRAWER_TAB.SECURITY,
  DRAWER_TAB.ACTIVITY,
  DRAWER_TAB.TROPHIES,
  DRAWER_TAB.NOTES,
  DRAWER_TAB.AUDIT,
]

export const EXPIRY_WARNING_DAYS = 7
export const EXTEND_PRESETS = [1, 3, 6, 12]
