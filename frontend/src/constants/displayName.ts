/**
 * Verdicts on a display name, as the live check (`reason`) and a refused save
 * (`display_name_<reason>`) send them — mirrors backend `constants/display_name.py`.
 */
export const DISPLAY_NAME_REASON = Object.freeze({
  INVALID: 'invalid',
  TOO_SHORT: 'too_short',
  GENERATED: 'generated',
  PREVIOUS: 'previous',
  RESERVED: 'reserved',
  LOCKED: 'locked',
  TAKEN: 'taken',
  CURRENT: 'current',
  FREE: 'free',
} as const)

export type DisplayNameReason = (typeof DISPLAY_NAME_REASON)[keyof typeof DISPLAY_NAME_REASON]

const IDENTITY = 'portal.settings.identity'

/** What a name field shows for each verdict: the flag's tone and its text. */
export const DISPLAY_NAME_FLAGS: Readonly<
  Record<DisplayNameReason, { tone: 'ok' | 'warn' | 'err'; key: string }>
> = Object.freeze({
  [DISPLAY_NAME_REASON.CURRENT]: { tone: 'warn', key: `${IDENTITY}.usernameCurrent` },
  [DISPLAY_NAME_REASON.FREE]: { tone: 'ok', key: `${IDENTITY}.usernameAvailable` },
  [DISPLAY_NAME_REASON.TAKEN]: { tone: 'err', key: `${IDENTITY}.usernameTaken` },
  [DISPLAY_NAME_REASON.RESERVED]: { tone: 'err', key: `${IDENTITY}.usernameReserved` },
  [DISPLAY_NAME_REASON.TOO_SHORT]: { tone: 'err', key: `${IDENTITY}.usernameTooShort` },
  [DISPLAY_NAME_REASON.INVALID]: { tone: 'err', key: `${IDENTITY}.usernameInvalid` },
  [DISPLAY_NAME_REASON.LOCKED]: { tone: 'err', key: `${IDENTITY}.usernameLockedShort` },
  [DISPLAY_NAME_REASON.GENERATED]: { tone: 'err', key: `${IDENTITY}.usernameGenerated` },
  [DISPLAY_NAME_REASON.PREVIOUS]: { tone: 'err', key: `${IDENTITY}.usernamePrevious` },
})

const REFUSAL_PREFIX = 'display_name_'

/** Verdict carried by a save refused for its name (`display_name_<reason>`), or null. */
export function refusedNameReason(error: unknown): DisplayNameReason | null {
  if (typeof error !== 'string' || !error.startsWith(REFUSAL_PREFIX)) return null
  const reason = error.slice(REFUSAL_PREFIX.length) as DisplayNameReason
  // Own keys only: `in` would also accept inherited ones (`display_name_constructor`).
  return Object.hasOwn(DISPLAY_NAME_FLAGS, reason) ? reason : null
}
