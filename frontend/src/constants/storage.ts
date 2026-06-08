/**
 * Browser-storage keys for the auth/session flow, centralized so the same
 * literal is never recopied across LoginView, useAuth and apiClient (§6).
 */
export const STORAGE_KEYS = Object.freeze({
  /** sessionStorage — set on logout; shows the "logged out" banner on /login. */
  JUST_LOGGED_OUT: 'mk_just_logged_out',
  /** sessionStorage — set on 401/expiry; shows the "session expired" banner. */
  SESSION_EXPIRED: 'mk_session_expired',
  /** localStorage — username remembered for the "remember me" prefill. */
  SAVED_USERNAME: 'mediakeeper_saved_username',
} as const)

export type StorageKey = (typeof STORAGE_KEYS)[keyof typeof STORAGE_KEYS]
