/**
 * Effective CSS zoom applied to the document root.
 *
 * The admin shell renders ~10% smaller on desktop via `zoom` on <html>
 * (see styles/main.css). `zoom` does not change DOM measurements: clientX/Y,
 * innerWidth/Height and getBoundingClientRect all report in the same zoomed
 * viewport space (they agree). It only changes paint — a `left`/`top` set on
 * an element inside the zoomed subtree is taken in that element's own
 * coordinates and then multiplied by the zoom when painted. So an element
 * positioned from those measurements lands `zoom`× too close to the origin:
 * divide the final position by this factor to compensate (and likewise scale
 * an offset/delta that is consumed in the unzoomed content space).
 *
 * Returns 1 when no zoom is applied (portal, mobile/tablet, or a browser
 * without `zoom` support), so callers can divide unconditionally.
 */
export function rootZoom() {
  const root = document.documentElement
  const z = root.currentCSSZoom
  if (typeof z === 'number' && z > 0) return z
  // Fallback for engines without Element.currentCSSZoom: derive the factor
  // from the viewport-vs-document width ratio. Exact because the admin shell
  // never becomes a root scroll container (overflow-x:clip on .mk-app-shell +
  // body scrollbar-gutter:stable reserving the vertical gutter; scroll lives on
  // inner .mk-app-content), and it reads 1 when the browser ignores `zoom`.
  const cw = root.clientWidth
  return cw > 0 ? window.innerWidth / cw : 1
}
