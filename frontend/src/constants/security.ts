/**
 * Sign-in security dashboard (Settings > Security), mirrored from the backend:
 * the scopes of `VALID_SCOPES` in `api/security.py`, the reasons written by
 * `services/security.py` and the tab, and the error codes the tab acts on.
 */

/** What a block or an attempt applies to. */
export const SECURITY_SCOPE = Object.freeze({
  ALL: 'all',
  ADMIN: 'admin',
  ADMIN_PASSWORD: 'admin_password',
  PORTAL: 'portal',
} as const)

export type SecurityScope = (typeof SECURITY_SCOPE)[keyof typeof SECURITY_SCOPE]

/** The scopes offered when blocking by hand, in the order the menu lists them. */
export const MANUAL_BLOCK_SCOPES: readonly SecurityScope[] = Object.freeze([
  SECURITY_SCOPE.ALL,
  SECURITY_SCOPE.ADMIN,
  SECURITY_SCOPE.PORTAL,
])

/** Reasons the server or the tab writes on a block; any other one was typed by an admin. */
export const BLOCK_REASON = Object.freeze({
  AUTO_IP_PREFIX: 'auto_block_bruteforce_ip:',
  AUTO_NAME_PREFIX: 'auto_block_bruteforce_username:',
  FROM_ATTEMPTS: 'manual_from_attempts',
} as const)

/** Stands in for a client whose address could not be read (`UNKNOWN_CLIENT_IP`). */
export const UNKNOWN_CLIENT_IP = 'unknown'

/** Longest values the server accepts for a manual block (`BlockRequest`). */
export const BLOCK_FIELD_MAX = Object.freeze({
  IP: 64,
  USERNAME: 100,
  REASON: 200,
} as const)

/** Error codes of the security API that the tab handles itself. */
export const SECURITY_ERROR = Object.freeze({
  BLOCK_NOT_FOUND: 'block_not_found',
} as const)

export type SecurityError = (typeof SECURITY_ERROR)[keyof typeof SECURITY_ERROR]
