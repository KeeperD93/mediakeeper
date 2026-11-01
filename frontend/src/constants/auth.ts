/**
 * User role, read from `profile.role`. Used by admin-gate guards across
 * the portal layer (PortalLayout, PortalHome, PortalMediaDetail…).
 */
export const USER_ROLE = Object.freeze({
  ADMIN: 'admin',
  USER: 'user',
} as const)

export type UserRole = (typeof USER_ROLE)[keyof typeof USER_ROLE]

/** Sign-in refusals that come with a wait (same codes as `constants/security.py`). */
export const SIGN_IN_ERROR = Object.freeze({
  BLOCKED: 'login_blocked',
  RATE_LIMITED: 'login_rate_limited',
} as const)

export type SignInError = (typeof SIGN_IN_ERROR)[keyof typeof SIGN_IN_ERROR]

/** Shortest new password the server accepts (`ChangePasswordRequest` in `api/auth/_schemas.py`). */
export const PASSWORD_MIN_LENGTH = 12
