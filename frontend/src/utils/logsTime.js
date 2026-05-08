/**
 * Display-only conversion of UTC log timestamps to the browser's local
 * timezone. The backend stores and serves UTC; the frontend only formats
 * it at render time. Source of truth (raw lines, file metadata,
 * ``/api/logs/download`` blobs) is never mutated.
 *
 * Tests pin ``timeZone`` / ``locale`` via ``opts`` so assertions stay
 * deterministic across CI hosts; production calls pass nothing and let
 * Intl pick the user's locale and zone.
 */

// ``YYYY-MM-DD HH:mm:ss`` (or ``T``-separated, optional ``Z`` and
// fractional seconds) at the very start of a log line.
const TEXT_TS_RE = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z?(?=\s|$)/

// ``"ts": "2026-05-08T12:41:00.000Z"`` inside a JSON log entry. The
// surrounding capture groups preserve the key/quotes so the substitution
// only swaps the timestamp value.
const JSON_TS_RE = /("ts"\s*:\s*")(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z(")/

function _toDate(value) {
  if (value == null || value === '') return null
  const d = value instanceof Date ? value : new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

function _localStamp(date, timeZone) {
  // ``hourCycle: 'h23'`` keeps midnight as ``00`` rather than the ``24``
  // some Intl implementations emit with ``hour12: false``.
  const fmt = new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone,
    hourCycle: 'h23',
  })
  const out = {}
  for (const p of fmt.formatToParts(date)) out[p.type] = p.value
  return `${out.year}-${out.month}-${out.day} ${out.hour}:${out.minute}:${out.second}`
}

/**
 * Format a UTC ISO timestamp for display next to a log file. Accepts a
 * ``Date``, an ISO string (``2026-05-08T12:41:00Z``), or anything
 * ``new Date()`` understands. Returns an empty string for invalid input
 * so the caller can render a stable fallback.
 *
 * @param {string|Date|null|undefined} value
 * @param {{ locale?: string|string[], timeZone?: string }} [opts]
 * @returns {string}
 */
export function formatFileDate(value, opts = {}) {
  const d = _toDate(value)
  if (!d) return ''
  const fmt = new Intl.DateTimeFormat(opts.locale, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: opts.timeZone,
    hourCycle: 'h23',
  })
  return fmt.format(d)
}

/**
 * Replace recognised UTC timestamps inside a single log line with their
 * browser-local equivalents. Returns the line unchanged when no pattern
 * matches, so level/module markers downstream stay intact.
 *
 * Recognised patterns:
 * - text:  ``YYYY-MM-DD HH:mm:ss[.fff][Z] ...`` at the start of the line
 * - JSON:  ``"ts": "YYYY-MM-DDTHH:mm:ss[.fff]Z"`` anywhere inside the line
 *
 * Display-only: callers must keep their raw source available for
 * download, search-on-raw, or any backend round-trip.
 *
 * @param {string} line
 * @param {{ timeZone?: string }} [opts]
 * @returns {string}
 */
export function formatLogLine(line, opts = {}) {
  if (typeof line !== 'string' || !line) return line
  const tz = opts.timeZone

  const text = line.match(TEXT_TS_RE)
  if (text) {
    const d = new Date(`${text[1]}-${text[2]}-${text[3]}T${text[4]}:${text[5]}:${text[6]}Z`)
    if (!Number.isNaN(d.getTime())) {
      return _localStamp(d, tz) + line.slice(text[0].length)
    }
  }

  const json = line.match(JSON_TS_RE)
  if (json) {
    const d = new Date(`${json[2]}-${json[3]}-${json[4]}T${json[5]}:${json[6]}:${json[7]}Z`)
    if (!Number.isNaN(d.getTime())) {
      return line.replace(JSON_TS_RE, `$1${_localStamp(d, tz)}$8`)
    }
  }

  return line
}
