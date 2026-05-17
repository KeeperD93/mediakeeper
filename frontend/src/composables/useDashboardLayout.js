import { computed, ref } from 'vue'
import {
  Calendar,
  CalendarClock,
  CircleCheck,
  CirclePlay,
  ClipboardCheck,
  Clock,
  Copy,
  Database,
  Grid3x3,
  ShieldCheck,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-vue-next'
import { useApi } from './useApi'

/**
 * Dashboard layout: a single full-width grid.
 * 36 columns, rowHeight 10px.
 */

// Widget badge icons — Lucide components, rendered via <component :is="...">.
export const WIDGET_ICONS = {
  activity: Zap,
  statPlays: CirclePlay,
  statDuration: Clock,
  statDuplicates: Copy,
  statStorage: Database,
  heatmap: Grid3x3,
  topUsers: Users,
  linkWatchlist: ClipboardCheck,
  portalAction: CircleCheck,
  portalEngagement: TrendingUp,
  portalEvents: CalendarClock,
  upcoming: Calendar,
  healthScore: ShieldCheck,
}

export const WIDGET_REGISTRY = {
  activity: { label: 'Activity', defaultLayout: { x: 0, y: 0, w: 11, h: 30 }, minW: 6, minH: 12 },
  statPlays: { label: 'Total plays', defaultLayout: { x: 21, y: 0, w: 4, h: 5 }, minW: 3, minH: 4 },
  statDuration: {
    label: 'Total duration',
    defaultLayout: { x: 25, y: 0, w: 4, h: 5 },
    minW: 3,
    minH: 4,
  },
  statStorage: {
    label: 'Media storage',
    defaultLayout: { x: 29, y: 0, w: 4, h: 5 },
    minW: 3,
    minH: 4,
  },
  statDuplicates: {
    label: 'Duplicates',
    defaultLayout: { x: 33, y: 0, w: 3, h: 5 },
    minW: 3,
    minH: 4,
  },
  topUsers: {
    label: 'Top users',
    defaultLayout: { x: 11, y: 0, w: 10, h: 10 },
    minW: 6,
    minH: 9,
    maxH: 12,
  },
  heatmap: {
    label: 'Activity heatmap',
    defaultLayout: { x: 28, y: 20, w: 8, h: 10 },
    minW: 6,
    minH: 6,
  },
  upcoming: {
    label: 'Upcoming releases',
    defaultLayout: { x: 0, y: 30, w: 36, h: 15 },
    minW: 6,
    minH: 6,
  },
  portalAction: {
    label: 'Requests — action',
    defaultLayout: { x: 11, y: 10, w: 10, h: 8 },
    minW: 10,
    minH: 7,
  },
  portalEngagement: {
    label: 'Requests — activity',
    defaultLayout: { x: 11, y: 18, w: 10, h: 12 },
    minW: 10,
    minH: 7,
  },
  portalEvents: {
    label: 'Portal — upcoming events',
    defaultLayout: { x: 28, y: 5, w: 8, h: 15 },
    minW: 4,
    minH: 7,
  },
  linkWatchlist: {
    label: 'Tracking',
    defaultLayout: { x: 21, y: 9, w: 7, h: 4 },
    minW: 6,
    minH: 4,
  },
  healthScore: {
    label: 'Media health',
    defaultLayout: { x: 21, y: 5, w: 7, h: 4 },
    minW: 6,
    minH: 4,
  },
}

// Bump when WIDGET_REGISTRY.defaultLayout changes — forces user reset.
const LAYOUT_VERSION = 22

// Canonical widget IDs — single source of truth per Rules.md §6. Any
// new widget added to WIDGET_REGISTRY above must also appear here so
// consumers (MobileDashboardWidget dispatch, MOBILE_DEFAULT_ORDER…)
// reference the constant instead of duplicating string literals.
export const WIDGET_ID = Object.freeze({
  ACTIVITY: 'activity',
  STAT_PLAYS: 'statPlays',
  STAT_DURATION: 'statDuration',
  STAT_DUPLICATES: 'statDuplicates',
  STAT_STORAGE: 'statStorage',
  TOP_USERS: 'topUsers',
  HEATMAP: 'heatmap',
  UPCOMING: 'upcoming',
  PORTAL_ACTION: 'portalAction',
  PORTAL_ENGAGEMENT: 'portalEngagement',
  PORTAL_EVENTS: 'portalEvents',
  LINK_WATCHLIST: 'linkWatchlist',
  HEALTH_SCORE: 'healthScore',
})

// IDs of the four compact "stat" cards. They render in a fixed 2×2
// grid above the reorderable stack — reordering tiny stat tiles
// individually adds noise without value, and a uniform stack of mixed
// card sizes is harder to scan than the current top-strip baseline.
export const MOBILE_STAT_IDS = [
  WIDGET_ID.STAT_PLAYS,
  WIDGET_ID.STAT_DURATION,
  WIDGET_ID.STAT_DUPLICATES,
  WIDGET_ID.STAT_STORAGE,
]

// Mobile stack default ordering — the vertical sequence below the
// stats grid, before any user customisation. Mirrors the previously
// hardcoded markup of MobileDashboard.vue so an existing user who has
// never reordered keeps the exact same visual order.
export const MOBILE_DEFAULT_ORDER = [
  WIDGET_ID.HEALTH_SCORE,
  WIDGET_ID.PORTAL_ACTION,
  WIDGET_ID.PORTAL_ENGAGEMENT,
  WIDGET_ID.PORTAL_EVENTS,
  WIDGET_ID.ACTIVITY,
  WIDGET_ID.UPCOMING,
  WIDGET_ID.TOP_USERS,
  WIDGET_ID.HEATMAP,
  WIDGET_ID.LINK_WATCHLIST,
]

export function useDashboardLayout() {
  const { apiGet, apiPost } = useApi()

  const editing = ref(false)
  const hidden = ref([])
  const layout = ref([])
  const loaded = ref(false)
  // ``null`` = user has never customised the mobile order; the
  // ``effectiveMobileOrder`` computed below falls back to the baseline.
  // An array (even empty) means the user has explicitly set an order on
  // a phone, and we honour it.
  const mobileOrder = ref(null)
  let saveTimeout = null

  function buildLayout(savedPositions = {}, savedHidden = []) {
    const items = []
    for (const [id, def] of Object.entries(WIDGET_REGISTRY)) {
      if (savedHidden.includes(id)) continue
      const saved = savedPositions[id]
      items.push({
        i: id,
        x: saved?.x ?? def.defaultLayout.x,
        y: saved?.y ?? def.defaultLayout.y,
        w: saved?.w ?? def.defaultLayout.w,
        h: saved?.h ?? def.defaultLayout.h,
        minW: def.minW ?? 2,
        minH: def.minH ?? 2,
        ...(def.maxH != null && { maxH: def.maxH }),
      })
    }
    return items
  }

  async function loadLayout() {
    try {
      const data = await apiGet('/api/settings/dashboard')
      if (
        data &&
        data.positions &&
        Object.keys(data.positions).length > 0 &&
        data.v === LAYOUT_VERSION
      ) {
        hidden.value = data.hidden || []
        layout.value = buildLayout(data.positions, data.hidden || [])
      } else {
        layout.value = buildLayout()
        saveLayoutNow()
      }
      mobileOrder.value = Array.isArray(data?.mobile_order) ? data.mobile_order : null
    } catch {
      layout.value = buildLayout()
      mobileOrder.value = null
    }
    loaded.value = true
  }

  async function saveLayoutNow() {
    const positions = {}
    for (const item of layout.value) {
      positions[item.i] = { x: item.x, y: item.y, w: item.w, h: item.h }
    }
    try {
      await apiPost('/api/settings/dashboard', {
        hidden: hidden.value,
        positions,
        v: LAYOUT_VERSION,
        mobile_order: mobileOrder.value,
      })
    } catch (e) {
      console.warn('[useDashboardLayout.saveLayoutNow] failed to save layout', e)
    }
  }

  function saveLayout() {
    if (saveTimeout) clearTimeout(saveTimeout)
    saveTimeout = setTimeout(() => saveLayoutNow(), 800)
  }

  function toggleWidget(id) {
    const idx = hidden.value.indexOf(id)
    if (idx >= 0) {
      hidden.value.splice(idx, 1)
      const def = WIDGET_REGISTRY[id]
      if (def) {
        layout.value.push({
          i: id,
          x: def.defaultLayout.x,
          y: def.defaultLayout.y,
          w: def.defaultLayout.w,
          h: def.defaultLayout.h,
          minW: def.minW ?? 2,
          minH: def.minH ?? 2,
          ...(def.maxH != null && { maxH: def.maxH }),
        })
      }
    } else {
      hidden.value.push(id)
      layout.value = layout.value.filter(item => item.i !== id)
    }
    saveLayout()
  }

  function resetLayout() {
    hidden.value = []
    layout.value = buildLayout()
    saveLayout()
  }

  // Visible stack IDs in their effective mobile order — applies the
  // user's saved sequence when present, otherwise the baseline. The
  // four stat cards (MOBILE_STAT_IDS) are excluded from this list
  // because they live in a fixed 2×2 grid above the stack. Hidden
  // widgets are filtered out, and any widget added to the registry
  // after the user last reordered gets appended in registry order so
  // it doesn't silently disappear from the phone view.
  const effectiveMobileOrder = computed(() => {
    const base = mobileOrder.value ?? MOBILE_DEFAULT_ORDER
    const hide = new Set(hidden.value)
    const stats = new Set(MOBILE_STAT_IDS)
    const allIds = Object.keys(WIDGET_REGISTRY).filter(id => !stats.has(id))
    const seen = new Set()
    const out = []
    for (const id of base) {
      if (allIds.includes(id) && !hide.has(id) && !seen.has(id)) {
        out.push(id)
        seen.add(id)
      }
    }
    for (const id of allIds) {
      if (!hide.has(id) && !seen.has(id)) out.push(id)
    }
    return out
  })

  function setMobileOrder(newOrder) {
    mobileOrder.value = Array.isArray(newOrder) ? newOrder.slice() : null
    saveLayout()
  }

  function onLayoutUpdated(newLayout) {
    if (editing.value) {
      for (const item of newLayout) {
        const def = WIDGET_REGISTRY[item.i]
        if (def) {
          item.minW = def.minW ?? 2
          item.minH = def.minH ?? 2
          if (def.maxH != null) item.maxH = def.maxH
        }
      }
      layout.value = newLayout
      saveLayout()
    }
  }

  return {
    editing,
    hidden,
    layout,
    loaded,
    loadLayout,
    saveLayout,
    toggleWidget,
    resetLayout,
    onLayoutUpdated,
    mobileOrder,
    effectiveMobileOrder,
    setMobileOrder,
    WIDGET_REGISTRY,
    WIDGET_ICONS,
  }
}
