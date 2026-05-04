import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useSubtitles } from '@/composables/useSubtitles'
import { useSubLibraryItem } from '@/composables/useSubLibraryItem'

function computePageSize() {
  const w = window.innerWidth - 80
  const h = window.innerHeight - 120
  const cols = Math.max(1, Math.floor((w + 12) / (155 + 12)))
  const rows = Math.max(4, Math.ceil(h / 230) + 2)
  return Math.max(60, cols * rows)
}

export function useSubLibrary(emit) {
  const { apiGet, apiPost } = useApi()
  const { defaultLanguagesParam, loadSeriesMatrix, loadAvailableCounts } = useSubtitles()

  const PAGE_SIZE = ref(computePageSize())
  const libraryItems = ref([])
  const libraryTotal = ref(0)
  const libLoading = ref(false)
  const libSearch = ref('')
  const libType = ref('Movie,Episode')
  const libLibrary = ref('')
  const libStatus = ref('')
  const viewMode = ref('grid')
  const currentPage = ref(1)

  const expandedId = ref(null)
  const itemSubs = ref(null)
  const itemAudio = ref([])
  const itemFilePath = ref('')
  const itemResults = ref([])
  const itemSearching = ref(false)
  const downloading = ref(null)
  const lastDownloadResult = ref(null)

  const matrixData = ref(null)
  const matrixLoading = ref(false)
  const compareFiles = ref([])
  const showComparator = ref(false)
  const selectMode = ref(false)
  const selectedItems = ref([])
  const batchRunning = ref(false)
  const seriesOverlay = ref(null)
  const itemOverlay = ref(null)

  let _debounceTimer = null
  let _countTimer = null
  let _resizeTimer = null

  const displayItems = computed(() => {
    const items = libraryItems.value
    const groups = new Map()
    const result = []
    for (const item of items) {
      if (item.type === 'Episode' && item.series_name) {
        const key = item.series_name
        if (!groups.has(key)) {
          const hasMissing = !Object.values(item.subtitle_status).every(v => v)
          const group = {
            _isGroup: true,
            _groupKey: 'group_' + key,
            _episodes: [item],
            item_id: item.item_id,
            poster_id: item.poster_id,
            name: item.series_name,
            series_name: null,
            type: 'Series',
            year: item.year,
            subtitle_status: { ...item.subtitle_status },
            imdb_id: item.series_imdb_id || item.imdb_id,
            tmdb_id: item.tmdb_id,
            file_path: item.file_path,
            existing_count: item.existing_count,
            _episodeCount: 1,
            _hasMissing: hasMissing,
          }
          groups.set(key, group)
          result.push(group)
        } else {
          const group = groups.get(key)
          group._episodes.push(item)
          group._episodeCount++
          for (const [lang, has] of Object.entries(item.subtitle_status)) {
            if (!has) group._hasMissing = true
            if (!has && group.subtitle_status[lang]) group.subtitle_status[lang] = false
          }
        }
      } else {
        result.push(item)
      }
    }
    return result
  })

  const missingCount = computed(
    () => libraryItems.value.filter(i => !Object.values(i.subtitle_status).every(v => v)).length,
  )
  watch(missingCount, v => emit && emit('update-missing', v))

  const totalPages = computed(() => Math.max(1, Math.ceil(libraryTotal.value / PAGE_SIZE.value)))
  const visiblePages = computed(() => {
    const total = totalPages.value
    const cur = currentPage.value
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
    const pages = [1]
    if (cur > 3) pages.push('...')
    for (let i = Math.max(2, cur - 1); i <= Math.min(total - 1, cur + 1); i++) pages.push(i)
    if (cur < total - 2) pages.push('...')
    pages.push(total)
    return pages
  })

  function goToPage(page) {
    if (page < 1 || page > totalPages.value) return
    currentPage.value = page
    expandedId.value = null
    loadPage()
  }

  async function loadPage() {
    libLoading.value = true
    try {
      const params = new URLSearchParams({
        start: String((currentPage.value - 1) * PAGE_SIZE.value),
        limit: String(PAGE_SIZE.value),
        type: libType.value,
        languages: defaultLanguagesParam.value,
      })
      if (libSearch.value.trim()) params.set('search', libSearch.value.trim())
      if (libLibrary.value) params.set('library', libLibrary.value)
      if (libStatus.value) params.set('status', libStatus.value)
      const d = await apiGet(`/api/subtitles/library?${params}`)
      if (d && d.items) {
        libraryItems.value = d.items
        libraryTotal.value = d.total
        scheduleCountLoad()
      }
    } catch {
      /* silent: library page fetch */
    }
    libLoading.value = false
  }

  function resetLibrary() {
    currentPage.value = 1
    expandedId.value = null
    loadPage()
  }
  function debounceLibrary() {
    clearTimeout(_debounceTimer)
    _debounceTimer = setTimeout(resetLibrary, 400)
  }

  const itemActions = useSubLibraryItem({
    expandedId,
    itemSubs,
    itemAudio,
    itemFilePath,
    itemResults,
    itemSearching,
    downloading,
    lastDownloadResult,
  })

  function onItemClick(item) {
    if (selectMode.value) {
      toggleItemSelect(item)
      return
    }
    if (item._isGroup) {
      expandedId.value = null
      seriesOverlay.value = {
        seriesName: item.name,
        posterId: item.poster_id,
        episodes: item._episodes,
      }
    } else {
      itemOverlay.value = item
    }
  }
  function onOverlayEpisodeSelect() {}

  function toggleSelectMode() {
    selectMode.value = !selectMode.value
    if (!selectMode.value) selectedItems.value = []
  }
  function toggleItemSelect(item) {
    if (item._isGroup) {
      for (const ep of item._episodes || []) toggleItemSelect(ep)
      return
    }
    const idx = selectedItems.value.findIndex(s => s.emby_item_id === item.item_id)
    if (idx >= 0) {
      selectedItems.value.splice(idx, 1)
      return
    }
    selectedItems.value.push({
      emby_item_id: item.item_id,
      file_path: item.file_path,
      media_name: item.series_name ? `${item.series_name} — ${item.name}` : item.name,
      type: item.type,
      imdb_id: item.imdb_id || '',
      tmdb_id: item.tmdb_id || '',
      series_name: item.series_name || '',
      season: item.season || 0,
      episode: item.episode || 0,
      series_imdb_id: item.series_imdb_id || '',
    })
  }
  async function startBatch() {
    if (!selectedItems.value.length) return
    batchRunning.value = true
    try {
      await apiPost('/api/subtitles/batch-download', { items: selectedItems.value })
    } catch (e) {
      console.error('[useSubLibrary.startBatch] failed to start batch download', e)
    }
  }
  async function cancelBatch() {
    try {
      await apiPost('/api/subtitles/batch-cancel')
    } catch (e) {
      console.warn('[useSubLibrary.cancelBatch] failed to cancel batch', e)
    }
    batchRunning.value = false
  }

  function openComparator(selection) {
    compareFiles.value = selection
    showComparator.value = true
  }

  async function showMatrix(item) {
    matrixLoading.value = true
    matrixData.value = {
      series_name: item.series_name || item.name,
      seasons: {},
      languages: [],
      total_episodes: 0,
      coverage: {},
    }
    matrixData.value = await loadSeriesMatrix(item.poster_id || item.item_id)
    matrixLoading.value = false
  }
  function onMatrixEpisodeClick(itemId) {
    matrixData.value = null
    viewMode.value = 'list'
    const item = libraryItems.value.find(i => i.item_id === itemId)
    if (item) itemActions.toggleExpand(item)
  }

  function scheduleCountLoad() {
    clearTimeout(_countTimer)
    _countTimer = setTimeout(() => {
      const items = libraryItems.value
        .slice(0, 50)
        .map(i => ({
          imdb_id: i.imdb_id || '',
          tmdb_id: i.tmdb_id || '',
          type: i.type,
        }))
        .filter(i => i.imdb_id || i.tmdb_id)
      if (items.length) {
        for (let i = 0; i < items.length; i += 10) loadAvailableCounts(items.slice(i, i + 10))
      }
    }, 500)
  }

  function onResize() {
    clearTimeout(_resizeTimer)
    _resizeTimer = setTimeout(() => {
      const newSize = computePageSize()
      if (newSize !== PAGE_SIZE.value) {
        PAGE_SIZE.value = newSize
        loadPage()
      }
    }, 300)
  }

  onMounted(() => {
    loadPage()
    window.addEventListener('resize', onResize)
  })
  onUnmounted(() => {
    clearTimeout(_debounceTimer)
    clearTimeout(_countTimer)
    clearTimeout(_resizeTimer)
    window.removeEventListener('resize', onResize)
  })

  return {
    PAGE_SIZE,
    libraryItems,
    libraryTotal,
    libLoading,
    libSearch,
    libType,
    libLibrary,
    libStatus,
    viewMode,
    currentPage,
    expandedId,
    itemSubs,
    itemAudio,
    itemResults,
    itemSearching,
    downloading,
    lastDownloadResult,
    matrixData,
    matrixLoading,
    compareFiles,
    showComparator,
    selectMode,
    selectedItems,
    batchRunning,
    seriesOverlay,
    itemOverlay,
    displayItems,
    totalPages,
    visiblePages,
    goToPage,
    loadPage,
    resetLibrary,
    debounceLibrary,
    onItemClick,
    onOverlayEpisodeSelect,
    toggleSelectMode,
    toggleItemSelect,
    startBatch,
    cancelBatch,
    openComparator,
    showMatrix,
    onMatrixEpisodeClick,
    ...itemActions,
  }
}
