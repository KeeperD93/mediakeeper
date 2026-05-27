/* Runtime resolver for the Design Tokens catalogue.
 *
 * Each swatch in the catalogue ships with ``data-token="--name"``. This
 * script substitutes the placeholder text by the computed value at
 * runtime so the catalogue stays accurate even when --accent-* is
 * overridden by useTheme or any other source.
 *
 * Loaded globally by preview.ts so every story benefits from it. Uses a
 * MutationObserver because Storybook re-renders each story without a
 * full reload, and Vue mounts the template after the JS in the page has
 * already finished executing.
 */

function resolveAllTokens() {
  const root = getComputedStyle(document.documentElement)
  document.querySelectorAll('[data-token]:not([data-resolved])').forEach(el => {
    const name = el.dataset.token
    const val = root.getPropertyValue(name).trim()
    el.textContent = val || '(unset)'
    el.setAttribute('data-resolved', 'true')
  })
}

if (typeof window !== 'undefined') {
  /* Watch the whole document so swatches added by a new story are
   * resolved as soon as Vue inserts them in the DOM. */
  const observer = new MutationObserver(() => resolveAllTokens())
  observer.observe(document.body, { childList: true, subtree: true })
  /* Initial pass for swatches present at first paint. */
  resolveAllTokens()
}
