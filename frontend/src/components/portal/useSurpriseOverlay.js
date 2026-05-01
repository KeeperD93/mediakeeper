import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useApi } from '@/composables/useApi'
import { useTrailer } from '@/composables/portal/useTrailer'
import { useSurpriseRoll } from '@/composables/portal/useSurpriseRoll'

// "animation" was removed as a separate kind. Animated movies are now
// part of the "movie" pool (the backend filter is broadened accordingly),
// so users get a single "Films" tab covering all flavours.
export const KINDS = [
  { key: 'movie',       label: 'portal.surprise.kinds.movie' },
  { key: 'tv',          label: 'portal.surprise.kinds.tv' },
  { key: 'manga',       label: 'portal.surprise.kinds.manga' },
  { key: 'documentary', label: 'portal.surprise.kinds.documentary' },
]

export function useSurpriseOverlay(emit) {
  const { apiGet } = useApi()
  const { trailer, resolve: resolveTrailer, clear: clearTrailer } = useTrailer()

  const kind = ref('movie')
  const pool = ref([])
  const loading = ref(false)
  const winner = ref(null)
  const revealed = ref(false)
  const lightboxOpen = ref(false)
  const gridWrapRef = ref(null)
  const cellSize = ref(70)
  const gap = ref(6)
  const colCount = ref(10)

  // Pick the largest 2:3 cell size that fits the wrap, restricting cols
  // to divisors of the pool size so every row is full (no trailing gaps).
  function recalcCellSize() {
    const el = gridWrapRef.value
    const n = pool.value.length
    if (!el || !n) return
    const W = el.clientWidth
    const H = el.clientHeight
    if (W <= 0 || H <= 0) return
    const g = Math.max(4, Math.min(10, Math.floor(Math.min(W, H) / 90)))
    gap.value = g
    let bestW = 32
    let bestCols = 1
    for (let cols = 1; cols <= n; cols++) {
      if (n % cols !== 0) continue
      const rows = n / cols
      const w = Math.floor(Math.min(
        (W - (cols - 1) * g) / cols,
        (H - (rows - 1) * g) / rows / 1.5,
        140,
      ))
      if (w > bestW) { bestW = w; bestCols = cols }
    }
    cellSize.value = Math.max(32, bestW)
    colCount.value = bestCols
  }

  let resizeObs = null
  watch(() => pool.value.length, () => nextTick(recalcCellSize))
  watch(revealed, (v) => { if (!v) nextTick(recalcCellSize) })

  const {
    rolling, activeIdx, soundOn, toggleSound, startRoll, resetRoll,
  } = useSurpriseRoll({
    getPool: () => pool.value,
    onReveal: (idx) => reveal(idx),
  })

  async function loadPool() {
    loading.value = true
    try {
      const res = await apiGet(`/api/portal/library/surprise?kind=${kind.value}&limit=50`)
      pool.value = res?.items || []
    } finally {
      loading.value = false
    }
  }

  function selectKind(k) {
    if (rolling.value) return
    kind.value = k
    revealed.value = false
    winner.value = null
    resetRoll()
    clearTrailer()
    loadPool()
  }

  function launchRoll() {
    revealed.value = false
    winner.value = null
    startRoll()
  }

  function reveal(idx) {
    winner.value = pool.value[idx] || null
    revealed.value = true
    // Pre-load the trailer so the button is instant when clicked.
    if (winner.value) {
      const id = winner.value.tmdb_id || winner.value.id
      const type = winner.value.media_type || 'movie'
      resolveTrailer(type, id, winner.value.emby_item_id || null)
    }
  }

  function retry() {
    revealed.value = false
    winner.value = null
    clearTrailer()
    setTimeout(() => startRoll(), 250)
  }

  function openTrailer() {
    if (trailer.value) lightboxOpen.value = true
  }

  function formatRuntime(min) {
    if (!min) return ''
    const h = Math.floor(min / 60)
    const m = min % 60
    return h > 0 ? `${h}h${m > 0 ? String(m).padStart(2, '0') : ''}` : `${m}min`
  }

  function close() {
    resetRoll()
    clearTrailer()
    emit('close')
  }

  function onKey(e) {
    if (e.key === 'Escape') close()
  }

  onMounted(() => {
    loadPool()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    nextTick(() => {
      recalcCellSize()
      if (gridWrapRef.value) {
        resizeObs = new ResizeObserver(recalcCellSize)
        resizeObs.observe(gridWrapRef.value)
      }
    })
  })

  onBeforeUnmount(() => {
    document.removeEventListener('keydown', onKey)
    document.body.style.overflow = ''
    resizeObs?.disconnect()
  })

  return {
    KINDS,
    kind, pool, loading, winner, revealed, lightboxOpen,
    gridWrapRef, cellSize, gap, colCount,
    rolling, activeIdx, soundOn, trailer,
    toggleSound, selectKind, launchRoll, retry, openTrailer,
    formatRuntime, close,
  }
}
