/**
 * URL scheme whitelist helpers for safely binding user/external content
 * to ``href`` / ``window.open`` / iframe ``src`` attributes.
 *
 * Vue does not auto-block dangerous schemes (``javascript:``, ``data:``,
 * ``vbscript:``, ``file:``, ``about:``) on attribute bindings, so we
 * normalise any external/user-controlled URL through one of these
 * helpers before rendering. They return ``null`` when the input is
 * unsafe, letting callers fall back to ``'#'`` and disable the link.
 */

const ALLOWED_HREF_SCHEMES = ['http:', 'https:', 'mailto:']
const ALLOWED_IFRAME_SCHEMES = ['https:']
const BLOCKED_SCHEMES = ['javascript:', 'data:', 'vbscript:', 'file:', 'about:']

// Strip whitespace that browsers tolerate inside URL attributes but that
// hides ``javascript:`` payloads (``\tjavascript:alert(1)`` or
// ``java\nscript:alert(1)``). \s covers \t \n \r \v \f and other
// Unicode whitespace.
const WHITESPACE_RE = /\s+/g

function _normalise(raw) {
  if (raw == null) return ''
  return String(raw).replace(WHITESPACE_RE, '')
}

function _scheme(value) {
  const m = value.match(/^([a-z][a-z0-9+.-]*):/i)
  return m ? m[1].toLowerCase() + ':' : null
}

/**
 * Validate a URL destined for an ``<a href>`` or ``window.open`` call.
 *
 * Accepts:
 * - ``http://`` / ``https://`` absolute URLs
 * - ``mailto:`` URIs
 * - relative paths (starting with ``/``, ``./``, ``../``, ``?`` or ``#``)
 *
 * Rejects ``javascript:``, ``data:``, ``vbscript:``, ``file:``, ``about:``
 * and any other custom scheme.
 *
 * @param {string|null|undefined} raw
 * @returns {string|null} normalised URL, or ``null`` when unsafe/empty
 */
export function safeHref(raw) {
  const value = _normalise(raw)
  if (!value) return null
  const scheme = _scheme(value)
  if (scheme == null) {
    // No scheme = relative URL. Accept only ``/path``, ``./path``,
    // ``../path``, ``?query``, ``#fragment``. Bare ``foo`` is rejected
    // even though it would resolve against the current origin —
    // requiring an explicit prefix avoids surprising callers.
    const first = value.charAt(0)
    if (first === '/' || first === '?' || first === '#') return value
    if (value.startsWith('./') || value.startsWith('../')) return value
    return null
  }
  if (BLOCKED_SCHEMES.includes(scheme)) return null
  if (ALLOWED_HREF_SCHEMES.includes(scheme)) return value
  return null
}

/**
 * Validate a URL destined for an ``<iframe src>`` attribute. Stricter
 * than {@link safeHref}: only absolute ``https://`` URLs are accepted.
 *
 * @param {string|null|undefined} raw
 * @returns {string|null} normalised URL, or ``null`` when unsafe/empty
 */
export function safeIframeSrc(raw) {
  const value = _normalise(raw)
  if (!value) return null
  const scheme = _scheme(value)
  if (scheme == null || BLOCKED_SCHEMES.includes(scheme)) return null
  if (ALLOWED_IFRAME_SCHEMES.includes(scheme)) return value
  return null
}
