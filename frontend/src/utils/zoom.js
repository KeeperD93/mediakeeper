/**
 * Effective CSS zoom applied to the document root.
 *
 * The admin shell renders ~10% smaller on desktop via `zoom` on <html>
 * (see styles/main.css). Pointer coordinates (clientX/clientY) and
 * window.innerWidth/Height are reported in the UNZOOMED viewport space, while
 * elements positioned inside the zoomed tree — and getBoundingClientRect —
 * live in zoomed (document) space. JS that mixes the two misplaces fixed
 * elements by the zoom factor, so divide viewport coordinates by this value
 * (or read clientWidth/Height instead of innerWidth/Height).
 *
 * Returns 1 when no zoom is applied (portal, mobile/tablet, or a browser
 * without `zoom` support), so callers can divide unconditionally.
 */
export function rootZoom() {
  const root = document.documentElement
  const z = root.currentCSSZoom
  if (typeof z === 'number' && z > 0) return z
  // Fallback for engines without Element.currentCSSZoom: derive the factor
  // from the viewport-vs-document width ratio. The admin shell has no root
  // scrollbar (its scroll is the inner .mk-app-content), so this stays exact,
  // and it reads 1 when the browser ignores `zoom` (document == viewport).
  const cw = root.clientWidth
  return cw > 0 ? window.innerWidth / cw : 1
}
