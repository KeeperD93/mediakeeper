/**
 * Two-way sync between an active-tab ref and the URL `?tab=` query.
 *
 * Each module page used to render a TabStrip whose internal state lived
 * in a local ref. Tabs now live in the sidebar instead, and the URL
 * `?tab=<id>` is the single source of truth: clicking a sub-link in the
 * sidebar pushes the query, and the view picks it up here.
 *
 * Behaviour:
 *  - On mount/route change, if `route.query.tab` is one of the allowed
 *    `tabIds`, the active ref is set to it; otherwise it falls back to
 *    `defaultTab`.
 *  - When the active ref is mutated from inside the view (e.g. a button
 *    that programmatically jumps to another tab), we mirror that back
 *    into the URL via `router.replace`.
 *  - Same-value writes are skipped to avoid feedback loops and noisy
 *    history entries.
 *  - URL-driven updates flip an internal flag so the state→URL watcher
 *    doesn't re-emit a `router.replace` for the same value (this avoids
 *    a race where consecutive sub-link clicks could be eaten by an
 *    overlapping navigation).
 */
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export function useTabSync(tabIds, defaultTab) {
  const route = useRoute()
  const router = useRouter()

  const allowed = Array.isArray(tabIds) ? tabIds : []
  const resolve = q => (allowed.includes(q) ? q : defaultTab)
  const activeTab = ref(resolve(route.query.tab))

  // Capture the parent path at setup so the state→URL watcher cannot
  // mirror a stale activeTab back onto a route the view has already left
  // (the writer would otherwise race against the next view's own sync).
  const parentPath = route.path

  // Suppress the state→URL watcher while we're applying a URL-driven
  // update. Without this, navigating between sub-links can produce a
  // brief inconsistency where the state→URL watcher reads a stale
  // `route.query.tab` and re-issues `router.replace` with the previous
  // value, snapping the view back to the previous tab.
  let applyingFromUrl = false

  watch(
    () => route.query.tab,
    q => {
      const next = resolve(q)
      if (next === activeTab.value) return
      applyingFromUrl = true
      activeTab.value = next
    },
    { flush: 'sync' },
  )

  watch(
    activeTab,
    tab => {
      if (applyingFromUrl) {
        applyingFromUrl = false
        return
      }
      if (route.path !== parentPath) return
      if (route.query.tab === tab) return
      router.replace({ path: parentPath, query: { ...route.query, tab } })
    },
    { flush: 'sync' },
  )

  return activeTab
}
