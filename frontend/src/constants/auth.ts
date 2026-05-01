/**
 * User role, read from `profile.role`. Used by admin-gate guards across
 * the portal layer (PortalLayout, PortalHome, PortalMediaDetail…).
 */
export const USER_ROLE = Object.freeze({
  ADMIN: 'admin',
  USER: 'user',
} as const)

export type UserRole = (typeof USER_ROLE)[keyof typeof USER_ROLE]
