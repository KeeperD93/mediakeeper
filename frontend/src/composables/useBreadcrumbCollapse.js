import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'

/**
 * Collapse a breadcrumb's middle segments behind a "…" only when the full path
 * would overflow its container; otherwise every segment stays visible.
 * Re-measures on container resize and whenever the path changes.
 *
 * Bind `bcRef` to the scrollable breadcrumb element and drive the collapsed
 * rendering with `bcCollapsed`.
 *
 * @param {import('vue').Ref<string[]>} breadcrumbs - reactive path segments
 * @returns {{ bcRef: import('vue').Ref<HTMLElement|null>, bcCollapsed: import('vue').Ref<boolean> }}
 */
export function useBreadcrumbCollapse(breadcrumbs) {
  const bcRef = ref(null)
  const bcCollapsed = ref(false)

  // Render the full path first, then collapse only if it overflows. The reset
  // happens in a microtask (nextTick) so it never paints the intermediate state.
  function measure() {
    bcCollapsed.value = false
    nextTick(() => {
      const el = bcRef.value
      if (el) bcCollapsed.value = el.scrollWidth > el.clientWidth + 1
    })
  }

  let observer = null
  onMounted(() => {
    observer = new ResizeObserver(measure)
    if (bcRef.value) observer.observe(bcRef.value)
  })
  onUnmounted(() => observer?.disconnect())
  watch(breadcrumbs, measure)

  return { bcRef, bcCollapsed }
}
