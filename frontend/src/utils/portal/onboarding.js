/** Small pure helpers of the first-login wizard. */

const DAY_MS = 24 * 60 * 60 * 1000

const midnight = date => new Date(date.getFullYear(), date.getMonth(), date.getDate())

/** Calendar days from today to `iso` (0 today, 1 tomorrow), on this device's calendar. */
export function daysUntil(iso, now = new Date()) {
  return Math.round((midnight(new Date(iso)) - midnight(now)) / DAY_MS)
}

/** First character of a name, upper-cased (a whole emoji or accented letter). */
export function initialOf(name) {
  const [first = ''] = Array.from((name || '').trim())
  return first.toLocaleUpperCase()
}

/** Why a picked file cannot be a profile image ('type', 'size'), or null when it can. */
export function avatarFileProblem(file, { types, extensions, maxBytes }) {
  if (!types.includes(file.type) || !extensions.test(file.name)) return 'type'
  if (file.size > maxBytes) return 'size'
  return null
}
