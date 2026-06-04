import { getLocale } from '@/i18n'

/**
 * Locale-aware date/time formatting. Every call uses the app's active locale
 * (`getLocale`) instead of the browser default, so month/day names follow the
 * language chosen in MediaKeeper. Accepts a `Date` or any value `new Date()`
 * understands — callers keep their own Date construction (e.g. a date-only
 * string forced to local midnight) by passing the built `Date` in.
 */
const _date = value => (value instanceof Date ? value : new Date(value))

export const localizedDate = (value, options) =>
  _date(value).toLocaleDateString(getLocale(), options)

export const localizedTime = (value, options) =>
  _date(value).toLocaleTimeString(getLocale(), options)

export const localizedDateTime = (value, options) =>
  _date(value).toLocaleString(getLocale(), options)
