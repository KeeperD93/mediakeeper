import { ref, watch } from 'vue'

const FALLBACK_TAB = 'identity'

export function tabFromHash(hash, tabIds) {
  const id = String(hash || '').replace(/^#/, '')
  return tabIds.includes(id) ? id : FALLBACK_TAB
}

export function useSettingsTabHash(route, router, visibleTabIds) {
  const activeTab = ref(tabFromHash(route.hash, visibleTabIds.value))

  function writeHash(target) {
    if (route.hash === target) return
    router.replace({ path: route.path, query: route.query, hash: target })
  }

  // URL → state: any hash change normalises to a visible tab.
  // `immediate: true` also rewrites a stale/invalid hash on first mount.
  watch(
    () => route.hash,
    next => {
      const resolved = tabFromHash(next, visibleTabIds.value)
      if (resolved !== activeTab.value) {
        activeTab.value = resolved
        return
      }
      writeHash(`#${resolved}`)
    },
    { immediate: true },
  )

  // State → URL: tab clicks and programmatic switches (e.g. username
  // errors forcing back to Identity) must keep the URL in sync without
  // pushing a new history entry.
  watch(activeTab, next => writeHash(`#${next}`))

  // The privacy tab only exists when GDPR mode is enabled. If it gets
  // hidden mid-session, drop back to identity so the body does not
  // render an empty card.
  watch(visibleTabIds, ids => {
    if (!ids.includes(activeTab.value)) {
      activeTab.value = ids[0] || FALLBACK_TAB
    }
  })

  return { activeTab }
}
