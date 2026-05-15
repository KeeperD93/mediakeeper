/**
 * Generic value formatters shared across portal surfaces.
 * Kept dependency-free so they can be unit-tested in isolation.
 */

/**
 * Format a runtime expressed in minutes as a short human label.
 *
 *   formatRuntime(105) === '1h45'
 *   formatRuntime(90)  === '1h30'
 *   formatRuntime(45)  === '45min'
 *   formatRuntime(0)   === ''
 *
 * Returns an empty string for missing / non-positive values so callers
 * can simply render the result without a guard.
 */
export function formatRuntime(min) {
  if (!min || min < 1) return ''
  const n = Math.floor(Number(min))
  if (!Number.isFinite(n) || n < 1) return ''
  const h = Math.floor(n / 60)
  const m = n % 60
  if (h > 0) return m > 0 ? `${h}h${String(m).padStart(2, '0')}` : `${h}h`
  return `${m}min`
}

/**
 * Format an ISO date / `Date` instance using `Intl.DateTimeFormat`.
 * Returns an empty string for any unparsable input so callers can render
 * the result safely.
 */
export function formatDate(input, locale = 'fr') {
  if (!input) return ''
  const d = input instanceof Date ? input : new Date(input)
  if (Number.isNaN(d.getTime())) return ''
  try {
    return new Intl.DateTimeFormat(locale, {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }).format(d)
  } catch {
    return ''
  }
}
