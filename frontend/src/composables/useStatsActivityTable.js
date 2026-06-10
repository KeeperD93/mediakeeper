import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useConfirm } from '@/composables/useConfirm'
import { useStats } from '@/composables/useStats'
import { useStatsUI } from '@/composables/useStatsUI'

// Table state for the Activities tab. Two display modes share this composable:
//  - GROUPED (sort = date desc, the default): consecutive same-(user, item)
//    sessions merge into expandable parent rows; cursor paging.
//  - FLAT (any other sort): individual rows sorted server-side across all
//    pages (#327); offset paging.
// Selection works on real session ids, so a grouped parent selects/deletes all
// of its children at once.
export function useStatsActivityTable() {
  const { t } = useI18n()
  const { apiPost } = useApi()
  const mkConfirm = useConfirm()
  const {
    activity,
    loadingActivity,
    loadActivity,
    ticksToDuration,
    activityUsers,
    loadActivityUsers,
  } = useStats()
  const { activitySearchSeed } = useStatsUI()

  const activitySearch = ref('')
  const activitySortBy = ref('started_at')
  const activitySortOrder = ref('desc')
  const activityPerPage = ref(25)
  const activitySelected = ref(new Set()) // selected session ids (leaf rows)
  const excludedUserIds = ref(new Set()) // ephemeral display filter, reset on reload
  const expandedRows = ref(new Set()) // expanded grouped-parent ids
  const groupedCursors = ref(['']) // cursor used to reach each grouped page
  const groupedPage = ref(0)
  const flatPage = ref(1)
  let actDb = null

  const isGrouped = computed(
    () => activitySortBy.value === 'started_at' && activitySortOrder.value === 'desc',
  )
  const activityItems = computed(() => activity.value?.items || [])

  function fetchActivity() {
    expandedRows.value = new Set()
    const common = {
      search: activitySearch.value,
      excludeUsers: [...excludedUserIds.value].join(','),
      sortBy: activitySortBy.value,
      sortOrder: activitySortOrder.value,
    }
    if (isGrouped.value)
      loadActivity({
        ...common,
        cursor: groupedCursors.value[groupedPage.value] || '',
        limit: activityPerPage.value,
      })
    else loadActivity({ ...common, page: flatPage.value, perPage: activityPerPage.value })
  }

  function resetPaging() {
    groupedCursors.value = ['']
    groupedPage.value = 0
    flatPage.value = 1
  }
  function reload() {
    resetPaging()
    fetchActivity()
  }

  function toggleUserFilter(id) {
    const s = new Set(excludedUserIds.value)
    if (s.has(id)) s.delete(id)
    else s.add(id)
    excludedUserIds.value = s
    reload()
  }
  function setAllUsersFilter(included) {
    excludedUserIds.value = included ? new Set() : new Set(activityUsers.value.map(u => u.id))
    reload()
  }
  function changePerPage() {
    reload()
  }
  function debouncedFetchActivity() {
    clearTimeout(actDb)
    actDb = setTimeout(reload, 300)
  }

  // --- Pagination (mode-aware) ---
  const flatHasMore = computed(
    () => flatPage.value * activityPerPage.value < (activity.value.total || 0),
  )
  const canPrev = computed(() => (isGrouped.value ? groupedPage.value > 0 : flatPage.value > 1))
  const canNext = computed(() => (isGrouped.value ? !!activity.value.has_more : flatHasMore.value))
  const pageNumber = computed(() => (isGrouped.value ? groupedPage.value + 1 : flatPage.value))
  const flatRangeStart = computed(() => (flatPage.value - 1) * activityPerPage.value + 1)
  const flatRangeEnd = computed(
    () => (flatPage.value - 1) * activityPerPage.value + activityItems.value.length,
  )

  function activityNextPage() {
    if (isGrouped.value) {
      if (!activity.value.has_more || !activity.value.next_cursor) return
      if (groupedCursors.value.length === groupedPage.value + 1)
        groupedCursors.value.push(activity.value.next_cursor)
      groupedPage.value += 1
    } else {
      if (!flatHasMore.value) return
      flatPage.value += 1
    }
    fetchActivity()
  }
  function activityPrevPage() {
    if (isGrouped.value) {
      if (groupedPage.value === 0) return
      groupedPage.value -= 1
    } else {
      if (flatPage.value <= 1) return
      flatPage.value -= 1
    }
    fetchActivity()
  }
  function activityFirstPage() {
    reload()
  }

  function toggleActivitySort(c) {
    if (activitySortBy.value === c)
      activitySortOrder.value = activitySortOrder.value === 'desc' ? 'asc' : 'desc'
    else {
      activitySortBy.value = c
      activitySortOrder.value = 'desc'
    }
    reload()
  }

  // --- Expand / collapse ---
  function isExpanded(id) {
    return expandedRows.value.has(id)
  }
  function toggleExpand(id) {
    const s = new Set(expandedRows.value)
    if (s.has(id)) s.delete(id)
    else s.add(id)
    expandedRows.value = s
  }

  // --- Selection (group-aware) ---
  function rowIds(it) {
    return it.sessions ? it.sessions.map(s => s.id) : [it.id]
  }
  function rowSelectState(it) {
    const ids = rowIds(it)
    const n = ids.filter(id => activitySelected.value.has(id)).length
    return n === 0 ? 'none' : n === ids.length ? 'all' : 'some'
  }
  function toggleActivitySelect(it) {
    const ids = rowIds(it)
    const s = new Set(activitySelected.value)
    if (rowSelectState(it) === 'all') ids.forEach(id => s.delete(id))
    else ids.forEach(id => s.add(id))
    activitySelected.value = s
  }
  function toggleSessionSelect(id) {
    const s = new Set(activitySelected.value)
    if (s.has(id)) s.delete(id)
    else s.add(id)
    activitySelected.value = s
  }
  const allLeafIds = computed(() => activityItems.value.flatMap(rowIds))
  const activityAllChecked = computed(
    () =>
      allLeafIds.value.length > 0 && allLeafIds.value.every(id => activitySelected.value.has(id)),
  )
  const activitySomeChecked = computed(
    () => !activityAllChecked.value && allLeafIds.value.some(id => activitySelected.value.has(id)),
  )
  function toggleActivitySelectAll() {
    activitySelected.value = activityAllChecked.value ? new Set() : new Set(allLeafIds.value)
  }

  async function bulkDeleteActivity() {
    const ids = [...activitySelected.value]
    if (!ids.length) return
    const ok = await mkConfirm({
      title: t('common.confirmTitle.delete'),
      message: t('stats.confirmBulkDeleteActivity', { count: ids.length }),
      variant: 'danger',
      confirmLabel: t('common.delete'),
    })
    if (!ok) return
    try {
      await apiPost('/api/stats/activity/bulk-delete', { ids })
      activitySelected.value = new Set()
      reload()
    } catch (e) {
      console.error('[useStatsActivityTable.bulkDeleteActivity] failed to bulk-delete', e)
    }
  }

  watch(activitySearchSeed, seed => {
    if (seed) {
      activitySearch.value = seed
      reload()
      activitySearchSeed.value = ''
    }
  })

  onMounted(() => {
    if (activitySearchSeed.value) {
      activitySearch.value = activitySearchSeed.value
      activitySearchSeed.value = ''
    }
    if (!activityItems.value.length || activitySearch.value) fetchActivity()
    if (!activityUsers.value.length) loadActivityUsers()
  })

  return {
    activity,
    loadingActivity,
    ticksToDuration,
    activitySearch,
    activitySortBy,
    activitySortOrder,
    activityPerPage,
    activitySelected,
    activityUsers,
    excludedUserIds,
    activityItems,
    isGrouped,
    activityAllChecked,
    activitySomeChecked,
    canPrev,
    canNext,
    pageNumber,
    flatRangeStart,
    flatRangeEnd,
    changePerPage,
    debouncedFetchActivity,
    activityFirstPage,
    activityPrevPage,
    activityNextPage,
    toggleActivitySort,
    isExpanded,
    toggleExpand,
    rowSelectState,
    toggleActivitySelect,
    toggleSessionSelect,
    toggleActivitySelectAll,
    bulkDeleteActivity,
    toggleUserFilter,
    setAllUsersFilter,
  }
}
