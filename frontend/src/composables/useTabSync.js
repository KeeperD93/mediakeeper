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
 */
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export function useTabSync(tabIds, defaultTab) {
  const route = useRoute()
  const router = useRouter()

  const allowed = Array.isArray(tabIds) ? tabIds : []
  const initialFromQuery = allowed.includes(route.query.tab) ? route.query.tab : defaultTab
  const activeTab = ref(initialFromQuery)

  // URL → state
  watch(
    () => route.query.tab,
    q => {
      const next = allowed.includes(q) ? q : defaultTab
      if (next !== activeTab.value) activeTab.value = next
    },
  )

  // state → URL
  watch(activeTab, tab => {
    if (route.query.tab === tab) return
    router.replace({ query: { ...route.query, tab } })
  })

  return activeTab
}
