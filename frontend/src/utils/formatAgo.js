/**
 * Format a timestamp as a relative "X ago" string (just-now / Xmin / Xh / Xd).
 *
 * Accepts either ISO strings or Unix timestamps and auto-detects the scale:
 *   - numbers < 1e12 are treated as Unix seconds (Python `time.time()`)
 *   - numbers >= 1e12 are treated as Unix ms
 *   - strings are parsed via `new Date(...)`
 *
 * Returns an empty string for missing / unparsable input so callers can
 * render the result transparently without a falsy guard.
 *
 * The translator `t` is injected explicitly so this utility stays dep-free
 * and trivially unit-testable. Callers pass their composable's `t` from
 * `useI18n()`.
 *
 * The `compact` style (default) stops at days, which is the right grain for
 * "last scan / last detection" labels. Admin lists where entries can be
 * months old pass `style: 'verbose'` to roll days up into months (30-364d)
 * and years (>=365d) instead of showing a large day count.
 *
 * Note: the current pattern `${m}min` / `${h}h` is a known i18n debt
 * (should use proper i18n pluralisation). Preserved as-is here to keep
 * behaviour identical across consumers; tracked for a dedicated
 * i18n-time-formatting refactor.
 *
 * @param {string|number|null|undefined} input  ISO string, Unix seconds, or Unix ms
 * @param {(key: string) => string} t           vue-i18n translator function
 * @param {{ style?: 'compact' | 'verbose' }} [opts]  'verbose' adds month/year buckets
 * @returns {string}
 */
export function formatAgo(input, t, { style = 'compact' } = {}) {
  if (!input) return ''
  const ms =
    typeof input === 'number' ? (input < 1e12 ? input * 1000 : input) : new Date(input).getTime()
  if (Number.isNaN(ms) || ms <= 0) return ''
  const diff = Date.now() - ms
  if (diff < 0) return ''
  const m = Math.floor(diff / 60000)
  if (m < 1) return t('healthCheck.justNow')
  if (m < 60) return `${m}min`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h`
  const d = Math.floor(h / 24)
  if (style !== 'verbose' || d < 30) return `${d}${t('stats.daysShort')}`
  if (d < 365) return `${Math.floor(d / 30)}${t('stats.monthsShort')}`
  return `${Math.floor(d / 365)}${t('stats.yearsShort')}`
}
