import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useConfirm } from '@/composables/useConfirm'
import { useStats } from '@/composables/useStats'
import { useStatsUI } from '@/composables/useStatsUI'

// Table state for the Activities tab: cursor pagination, client-side sort,
// row selection and bulk delete. Extracted from StatsActivityTab.vue to keep
// the view under the size budget; behaviour is unchanged.
export function useStatsActivityTable() {
  const { t } = useI18n()
  const { apiPost } = useApi()
  const mkConfirm = useConfirm()
  const { activity, loadingActivity, loadActivity, ticksToDuration } = useStats()
  const { activitySearchSeed } = useStatsUI()

  const activityCursorHistory = ref([])
  const activitySearch = ref('')
  const activitySortBy = ref('started_at')
  const activitySortOrder = ref('desc')
  const activityPerPage = ref(25)
  const activitySelected = ref(new Set())
  let actDb = null

  function fetchActivityData(cursor = '') {
    loadActivity({ cursor, limit: activityPerPage.value, search: activitySearch.value })
  }
  function changePerPage() {
    activityCursorHistory.value = []
    fetchActivityData('')
  }
  function activityNextPage() {
    const nc = activity.value.next_cursor
    if (nc) {
      activityCursorHistory.value.push('')
      fetchActivityData(nc)
    }
  }
  function activityPrevPage() {
    if (activityCursorHistory.value.length) {
      activityCursorHistory.value.pop()
      fetchActivityData('')
    }
  }
  function activityFirstPage() {
    activityCursorHistory.value = []
    fetchActivityData('')
  }
  function debouncedFetchActivity() {
    clearTimeout(actDb)
    actDb = setTimeout(() => {
      activityCursorHistory.value = []
      fetchActivityData('')
    }, 300)
  }

  function toggleActivitySort(c) {
    if (activitySortBy.value === c)
      activitySortOrder.value = activitySortOrder.value === 'desc' ? 'asc' : 'desc'
    else {
      activitySortBy.value = c
      activitySortOrder.value = 'desc'
    }
  }

  const sortedActivity = computed(() => {
    const it = [...(activity.value?.items || [])]
    if (activitySortBy.value === 'started_at' && activitySortOrder.value === 'desc') return it
    it.sort((a, b) => {
      let va = a[activitySortBy.value] || ''
      let vb = b[activitySortBy.value] || ''
      if (activitySortBy.value === 'duration') {
        va = a.duration_ticks || 0
        vb = b.duration_ticks || 0
      }
      if (typeof va === 'number') return activitySortOrder.value === 'desc' ? vb - va : va - vb
      return activitySortOrder.value === 'desc'
        ? String(vb).localeCompare(String(va))
        : String(va).localeCompare(String(vb))
    })
    return it
  })

  const activityAllChecked = computed(
    () =>
      sortedActivity.value.length > 0 &&
      sortedActivity.value.every(it => activitySelected.value.has(it.id)),
  )
  function toggleActivitySelect(id) {
    const s = new Set(activitySelected.value)
    if (s.has(id)) s.delete(id)
    else s.add(id)
    activitySelected.value = s
  }
  function toggleActivitySelectAll() {
    if (activityAllChecked.value) activitySelected.value = new Set()
    else activitySelected.value = new Set(sortedActivity.value.map(it => it.id))
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
      fetchActivityData('')
    } catch (e) {
      console.error('[useStatsActivityTable.bulkDeleteActivity] failed to bulk-delete', e)
    }
  }

  watch(activitySearchSeed, seed => {
    if (seed) {
      activitySearch.value = seed
      activityCursorHistory.value = []
      fetchActivityData('')
      activitySearchSeed.value = ''
    }
  })

  onMounted(() => {
    if (activitySearchSeed.value) {
      activitySearch.value = activitySearchSeed.value
      activitySearchSeed.value = ''
    }
    if (!activity.value.items.length || activitySearch.value) fetchActivityData('')
  })

  return {
    activity,
    loadingActivity,
    ticksToDuration,
    activityCursorHistory,
    activitySearch,
    activitySortBy,
    activitySortOrder,
    activityPerPage,
    activitySelected,
    sortedActivity,
    activityAllChecked,
    changePerPage,
    debouncedFetchActivity,
    activityFirstPage,
    activityPrevPage,
    activityNextPage,
    toggleActivitySort,
    toggleActivitySelect,
    toggleActivitySelectAll,
    bulkDeleteActivity,
  }
}
