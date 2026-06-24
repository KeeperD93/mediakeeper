import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

const SEV_RANK = { critical: 3, warning: 2, info: 1, ok: 0 }

/**
 * Poster-detail loader for the health-check issue overlay: fetches the
 * per-item issue rows and shapes them into season groups (series) or a
 * flat issue list (movie). Extracted from HealthCheckIssueOverlay.vue so
 * the component stays a presentation layer.
 */
export function useHealthCheckPoster() {
  const { apiGet } = useApi()
  const detail = ref(null)

  async function load(item) {
    if (!item) {
      detail.value = null
      return
    }
    const kind = item.is_series ? 'series' : 'movie'
    const key = encodeURIComponent(item.is_series ? item.item_id || item.title : item.item_id)
    let rows = []
    try {
      const d = await apiGet(`/api/healthcheck/poster/${kind}/${key}`)
      rows = d?.items || []
    } catch {
      /* silent: poster detail fetch, overlay stays empty */
    }

    if (item.is_series) {
      const seasonMap = new Map()
      for (const ep of rows) {
        const num = ep.season_num || 1
        if (!seasonMap.has(num)) seasonMap.set(num, { num, open: false, episodes: [], allTags: [] })
        seasonMap.get(num).episodes.push(ep)
      }
      for (const s of seasonMap.values()) {
        const tagSet = new Map()
        for (const ep of s.episodes) {
          for (const iss of ep.issues || []) {
            if (
              !tagSet.has(iss.type) ||
              (SEV_RANK[iss.severity] || 0) > (SEV_RANK[tagSet.get(iss.type).severity] || 0)
            ) {
              tagSet.set(iss.type, iss)
            }
          }
        }
        s.allTags = [...tagSet.values()]
        s.episodes.sort((a, b) => (a.episode_num || 0) - (b.episode_num || 0))
      }
      const seasons = [...seasonMap.values()].sort((a, b) => a.num - b.num)
      detail.value = { ...item, seasons, episodes: rows }
    } else {
      const allIssues = rows.flatMap(r => r.issues || [])
      detail.value = { ...item, allIssues }
    }
  }

  return { detail, load }
}
