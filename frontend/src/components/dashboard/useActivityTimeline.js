import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { parseActivityLog, parseActivityAlert } from './activityLog.js'

export function useActivityTimeline(props) {
  const { t } = useI18n()
  const { apiGet } = useApi()

  const activeTab = ref('all')
  const rootRef = ref(null)
  const popoverRef = ref(null)

  const lecturesTabSeen = ref(false)
  const alertesTabSeen = ref(false)

  const sessionsCount = computed(() => props.sessions.length)
  const unreadAlerts = computed(
    () => props.alerts.filter(a => !props.seenAlertIds.has(String(a.id || a.date))).length,
  )

  watch(sessionsCount, (n, o) => {
    if (n > o) lecturesTabSeen.value = false
  })
  watch(unreadAlerts, (n, o) => {
    if (n > o) alertesTabSeen.value = false
  })

  function switchTab(id) {
    activeTab.value = id
    if (id === 'lectures') lecturesTabSeen.value = true
    if (id === 'alertes') alertesTabSeen.value = true
  }

  const popover = reactive({
    visible: false,
    loading: false,
    error: '',
    data: null,
    style: {},
    _currentKey: '',
  })
  const tmdbCache = ref({})

  async function togglePopover(item, event) {
    if (popover.visible && popover._currentKey === item.rawMediaName) {
      closePopover()
      return
    }
    const el = event.target
    const rect = el.getBoundingClientRect()
    /* Position the popover in viewport coordinates so the ``position:
     * fixed`` rule lets it escape the parent widget's ``overflow:
     * hidden`` and render at its full size (otherwise the TMDB card
     * gets clipped at the widget border). Clamp horizontally to keep
     * the 340 px card inside the viewport on narrow screens. */
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - 340 - 8))
    const top = rect.bottom + 8
    popover.style = { left: left + 'px', top: top + 'px' }
    popover.visible = true
    popover.loading = true
    popover.error = ''
    popover.data = null
    popover._currentKey = item.rawMediaName
    const rawMedia = item.rawMediaName || item.media || ''
    if (!rawMedia) {
      popover.error = t('dashboard.nameNotFound')
      popover.loading = false
      return
    }
    const cacheKey = rawMedia.toLowerCase().trim()
    if (tmdbCache.value[cacheKey]) {
      popover.data = tmdbCache.value[cacheKey]
      popover.loading = false
      return
    }
    try {
      const results = await apiGet(`/api/watchlist/search?q=${encodeURIComponent(rawMedia)}`)
      if (!results || results.error || !Array.isArray(results) || results.length === 0) {
        popover.error = t('dashboard.noTmdbResult')
        popover.loading = false
        return
      }
      const best = results[0]
      const detail = await apiGet(`/api/watchlist/tmdb/${best.media_type}/${best.tmdb_id}`)
      if (!detail || detail.error) {
        popover.error = detail?.error || t('dashboard.tmdbError')
        popover.loading = false
        return
      }
      tmdbCache.value[cacheKey] = detail
      popover.data = detail
    } catch {
      popover.error = t('dashboard.tmdbUnavailable')
    }
    popover.loading = false
  }

  function closePopover() {
    popover.visible = false
    popover.data = null
    popover.error = ''
    popover._currentKey = ''
  }

  function onDocClick(e) {
    if (popover.visible && popoverRef.value && !popoverRef.value.contains(e.target)) closePopover()
    if (rootRef.value && rootRef.value.closest('.cinema-dash')?.contains(e.target)) {
      lecturesTabSeen.value = true
      alertesTabSeen.value = true
    }
  }
  function onKeydown(e) {
    if (e.key === 'Escape') closePopover()
  }

  onMounted(() => {
    document.addEventListener('click', onDocClick)
    document.addEventListener('keydown', onKeydown)
  })
  onUnmounted(() => {
    document.removeEventListener('click', onDocClick)
    document.removeEventListener('keydown', onKeydown)
  })

  function buildEmbyUrl(session) {
    if (!props.embyBaseUrl || !session.item_id) return ''
    return `${props.embyBaseUrl}/web/index.html#!/item?id=${session.item_id}`
  }

  const allItems = computed(() => {
    const items = []
    for (const s of props.sessions) {
      const mediaName = s.series ? `${s.series} ${s.episode || ''}`.trim() : s.media || ''
      const rawMediaName = s.series || s.media || ''
      items.push({
        type: 'playing',
        user: s.user,
        action: t('dashboard.watching'),
        media: mediaName,
        rawMediaName,
        device: s.client || s.device || '',
        ago: t('dashboard.justNow'),
        tag: s.is_playing ? t('dashboard.playing') : t('dashboard.paused'),
        tagClass: s.is_playing ? 'tag-green' : 'tag-yellow',
        ts: Date.now(),
        key: 'session-' + (s.session_id || s.user + s.media),
      })
    }
    for (const a of props.alerts) {
      items.push({
        type: 'alert',
        user: '',
        action: parseActivityAlert(a, t),
        media: '',
        rawMediaName: '',
        device: '',
        ago: timeAgo(a.date),
        tag: null,
        tagClass: '',
        ts: new Date(a.date).getTime(),
        key: 'alert-' + (a.id || a.date),
      })
    }
    for (const log of props.logs) {
      const p = parseActivityLog(log, t)
      items.push({
        type: 'log',
        user: p.user,
        action: p.action,
        media: p.media,
        rawMediaName: p.rawMediaName,
        device: p.device,
        ago: timeAgo(log.date),
        tag: null,
        tagClass: '',
        ts: new Date(log.date).getTime(),
        key: 'log-' + log.date + p.media,
      })
    }
    items.sort((a, b) => b.ts - a.ts)
    return items
  })

  const filteredItems = computed(() => {
    let list = allItems.value
    if (activeTab.value === 'lectures')
      list = list.filter(i => i.type === 'playing' || i.type === 'log')
    else if (activeTab.value === 'alertes') list = list.filter(i => i.type === 'alert')
    return activeTab.value === 'all' ? list.slice(0, 20) : list.slice(0, 40)
  })

  const tabs = computed(() => [
    { id: 'all', label: t('dashboard.tabAll'), count: 0 },
    { id: 'lectures', label: t('dashboard.tabPlayback'), count: sessionsCount.value },
    { id: 'alertes', label: t('dashboard.tabAlerts'), count: unreadAlerts.value },
  ])

  function dotClass(item) {
    if (item.type === 'playing') return 'dot-active'
    if (item.type === 'alert') return 'dot-error'
    return 'dot-past'
  }

  function timeAgo(dateStr) {
    if (!dateStr) return ''
    const diff = Date.now() - new Date(dateStr).getTime()
    const min = Math.floor(diff / 60000)
    if (min < 1) return t('dashboard.justNow')
    if (min < 60) return t('dashboard.minutesAgo', { min })
    const h = Math.floor(min / 60)
    if (h < 24) return t('dashboard.hoursAgo', { h })
    return t('dashboard.daysAgo', { d: Math.floor(h / 24) })
  }

  return {
    activeTab,
    rootRef,
    popoverRef,
    lecturesTabSeen,
    alertesTabSeen,
    sessionsCount,
    unreadAlerts,
    tabs,
    filteredItems,
    popover,
    switchTab,
    togglePopover,
    closePopover,
    buildEmbyUrl,
    dotClass,
  }
}
