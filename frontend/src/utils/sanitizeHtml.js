import DOMPurify from 'dompurify'

/**
 * Scrub HTML once more right before ``v-html``. The server already sanitises what it
 * stores; this is defence in depth should it ever let something through.
 *
 * @param {unknown} html
 * @returns {string} the scrubbed HTML, or ``''`` for empty input
 */
export function sanitizeHtml(html) {
  // No String(): DOMPurify reads any value itself, where String() throws on some objects.
  return html ? DOMPurify.sanitize(html) : ''
}
