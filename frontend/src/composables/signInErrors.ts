import i18n from '@/i18n'
import { SIGN_IN_ERROR } from '@/constants/auth'
import { resolveScopedError } from './useApi'

const WAIT_MESSAGES: Record<string, string> = {
  [SIGN_IN_ERROR.BLOCKED]: 'login.errors.blockedWait',
  [SIGN_IN_ERROR.RATE_LIMITED]: 'login.errors.rateLimitedWait',
}

const SECONDS_PER_MINUTE = 60
const SECONDS_PER_HOUR = 3600

export interface SignInFailure {
  message: string
  retryAfter?: number | null
}

/**
 * The sign-in page's text for a failed sign-in: the wait when the server gave
 * one, rounded up to the minute past 60 s. Past an hour it no longer helps to
 * count, and the text without a wait tells the person who to contact instead.
 */
export function signInErrorMessage({ message, retryAfter }: SignInFailure): string {
  const t = i18n.global.t as unknown as (key: string, named?: Record<string, unknown>) => string
  const waitMessage = WAIT_MESSAGES[message]
  if (waitMessage && retryAfter && retryAfter < SECONDS_PER_HOUR) {
    const wait =
      retryAfter < SECONDS_PER_MINUTE
        ? t('common.duration.sec', { n: retryAfter })
        : t('common.duration.min', { n: Math.ceil(retryAfter / SECONDS_PER_MINUTE) })
    return t(waitMessage, { wait })
  }
  return resolveScopedError('login.errors', message)
}
