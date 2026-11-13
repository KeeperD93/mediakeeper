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

/** i18n key of each refusal the profile save can send back for the name. */
export const NAME_REFUSAL_KEYS: Readonly<Record<string, string>> = Object.freeze({
  display_name_taken: 'portal.settings.identity.usernameTaken',
  display_name_reserved: 'portal.settings.identity.usernameReserved',
  display_name_too_short: 'portal.settings.identity.usernameTooShort',
  display_name_invalid: 'portal.settings.identity.usernameInvalid',
})
