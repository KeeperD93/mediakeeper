/** First-login wizard of the portal: what it shows, in which order, and its limits. */

/** The whole tour (once per account), or the name alone after an admin reset it. */
export const WIZARD_MODE = Object.freeze({
  FULL: 'full',
  RESET: 'reset',
} as const)

export type WizardMode = (typeof WIZARD_MODE)[keyof typeof WIZARD_MODE]

export const WIZARD_STEP = Object.freeze({
  WELCOME: 'welcome',
  NAME: 'name',
  LANGUAGE: 'language',
  VISIBILITY: 'visibility',
  FEATURES: 'features',
  HELP: 'help',
  EXPIRY: 'expiry',
  NOTIFICATIONS: 'notifications',
  GENRES: 'genres',
  AVATAR: 'avatar',
  DONE: 'done',
} as const)

export type WizardStep = (typeof WIZARD_STEP)[keyof typeof WIZARD_STEP]

/** The tour in order; the first and the last steps are not counted in the progress. */
export const FULL_TOUR: readonly WizardStep[] = Object.freeze([
  WIZARD_STEP.WELCOME,
  WIZARD_STEP.NAME,
  WIZARD_STEP.LANGUAGE,
  WIZARD_STEP.VISIBILITY,
  WIZARD_STEP.FEATURES,
  WIZARD_STEP.HELP,
  WIZARD_STEP.EXPIRY,
  WIZARD_STEP.NOTIFICATIONS,
  WIZARD_STEP.GENRES,
  WIZARD_STEP.AVATAR,
  WIZARD_STEP.DONE,
])

/**
 * Who the name step talks to: no name chosen yet, a chosen name an admin reset, a name
 * to keep or change, a locked name.
 */
export const WIZARD_ACCOUNT = Object.freeze({
  NEW: 'new',
  RESET: 'reset',
  EXISTING: 'existing',
  LOCKED: 'locked',
} as const)

export type WizardAccount = (typeof WIZARD_ACCOUNT)[keyof typeof WIZARD_ACCOUNT]

/** The image step: keep the current picture, or send one at the end. */
export const AVATAR_CHOICE = Object.freeze({
  KEEP: 'keep',
  OWN: 'own',
} as const)

/** Same limits as the server's avatar upload. */
export const AVATAR_TYPES: readonly string[] = Object.freeze([
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
])
export const AVATAR_EXTENSIONS = /\.(jpe?g|png|webp|gif)$/i
export const AVATAR_MAX_BYTES = 5 * 1024 * 1024

/** Most genres the server takes in one save. */
export const MAX_FAVORITE_GENRES = 30

/** Pause in typing before the server judges a name, and free names shown at most. */
export const NAME_CHECK_DEBOUNCE_MS = 350
export const NAME_SUGGESTIONS_SHOWN = 3
/** The live check could not get an answer (network, rate limit). */
export const NAME_CHECK_FAILED = 'error'

/** What the browser allows for notifications on this page. */
export const NOTIFY_STATE = Object.freeze({
  INSECURE: 'insecure',
  UNSUPPORTED: 'unsupported',
  DEFAULT: 'default',
  GRANTED: 'granted',
  DENIED: 'denied',
} as const)

export type NotifyState = (typeof NOTIFY_STATE)[keyof typeof NOTIFY_STATE]
