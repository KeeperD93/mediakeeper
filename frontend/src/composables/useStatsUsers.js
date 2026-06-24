import { ref, reactive, computed, onMounted, onDeactivated, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useStats } from '@/composables/useStats'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useStatsUI } from '@/composables/useStatsUI'
import { useConfirm } from '@/composables/useConfirm'

/**
 * Data, selection and bulk-action logic for the Statistics → Users tab.
 * Extracted from StatsUsersTab.vue so the component stays a thin
 * presentation layer. Owns the reactive list / sort / pagination state
 * plus the KeepAlive deactivation and debounce-cleanup wiring.
 */
export function useStatsUsers() {
  const { t } = useI18n()
  const { users, loadingUsers, loadUsers, ticksToDuration, timeAgo } = useStats()
  const { apiPost, apiDelete } = useApi()
  const { showToast } = useToast()
  const { openUserProfile, openMergeModal, registerUsersRefresh } = useStatsUI()
  const mkConfirm = useConfirm()

  const usersPage = ref(1)
  const usersPerPage = ref(30)
  const usersSearch = ref('')
  const usersSortBy = ref('last_seen')
  const usersSortOrder = ref('desc')
  const showHiddenUsers = ref(false)
  const showHistoricalOnly = ref(false)
  let usersDb = null

  // Selection state — reactive Set so .add() / .delete() / .clear()
  // automatically trigger re-renders (ref(new Set()) does not track method
  // calls, only reassignments).
  const selected = reactive(new Set())

  const selectedUsers = computed(() => users.value.users.filter(u => selected.has(u.user_id)))
  const visibleSelected = computed(() => selectedUsers.value.filter(u => !u.is_hidden))
  const hiddenSelected = computed(() => selectedUsers.value.filter(u => u.is_hidden))
  const allSelected = computed(
    () => users.value.users.length > 0 && selected.size === users.value.users.length,
  )
  const partiallySelected = computed(() => selected.size > 0 && !allSelected.value)

  function toggleSelect(userId) {
    if (selected.has(userId)) selected.delete(userId)
    else selected.add(userId)
  }

  function toggleSelectAll() {
    if (allSelected.value) {
      selected.clear()
    } else {
      users.value.users.forEach(u => selected.add(u.user_id))
    }
  }

  function clearSelection() {
    selected.clear()
  }

  // Clear the selection whenever the underlying user list changes —
  // page change, sort, search, or any visibility filter. Without this,
  // ids selected on page 1 would still appear in selected.size after
  // jumping to page 2, and bulk actions would silently no-op on the
  // ids that are no longer in users.value.users.
  watch(
    () => [
      usersPage.value,
      usersPerPage.value,
      usersSearch.value,
      usersSortBy.value,
      usersSortOrder.value,
      showHiddenUsers.value,
      showHistoricalOnly.value,
    ],
    () => selected.clear(),
  )

  // Run a bulk API action sequentially with per-item try/catch. Parallel
  // calls would race on the backend (CSRF / concurrent writes to the
  // same table) and only the first one would persist visibly, so each
  // mutation must commit before the next is fired. A try/catch around
  // every call keeps the loop alive on partial failure: we tally
  // succeeded / failed and report the right toast at the end.
  // clearSelection + fetchUsers run unconditionally so the UI always
  // reconciles with the server.
  async function runBulk(targets, callFor, successKey) {
    if (!targets.length) return
    let succeeded = 0
    let failed = 0
    for (const target of targets) {
      try {
        await callFor(target)
        succeeded += 1
      } catch (e) {
        failed += 1
        console.error('[StatsUsersTab.runBulk] item failed', e)
      }
    }
    if (failed === 0) {
      showToast(t(successKey, succeeded, { n: succeeded }), TOAST_TYPE.OK)
    } else {
      showToast(
        t('stats.bulkPartialFail', { succeeded, failed, total: targets.length }),
        TOAST_TYPE.ERR,
      )
    }
    clearSelection()
    fetchUsers()
  }

  async function bulkHide() {
    await runBulk(
      visibleSelected.value.slice(),
      u => apiPost(`/api/stats/users/${encodeURIComponent(u.user_id)}/hide`),
      'stats.bulkUsersHidden',
    )
  }

  async function bulkUnhide() {
    await runBulk(
      hiddenSelected.value.slice(),
      u => apiPost(`/api/stats/users/${encodeURIComponent(u.user_id)}/unhide`),
      'stats.bulkUsersUnhidden',
    )
  }

  function bulkMerge() {
    if (selected.size !== 1) return
    const u = selectedUsers.value[0]
    if (u) openMergeModal(u)
  }

  async function bulkDelete() {
    const targets = selectedUsers.value.slice()
    if (!targets.length) return
    const ok = await mkConfirm({
      title: t('common.confirmTitle.deleteUser'),
      message: t('stats.bulkDeleteConfirm', targets.length, { n: targets.length }),
      variant: 'danger',
      confirmLabel: t('common.delete'),
    })
    if (!ok) return
    await runBulk(
      targets,
      u => apiDelete(`/api/stats/users/${encodeURIComponent(u.user_id)}`),
      'stats.bulkUsersDeleted',
    )
  }

  function fetchUsers() {
    loadUsers({
      page: usersPage.value,
      per_page: usersPerPage.value,
      sort_by: usersSortBy.value,
      sort_order: usersSortOrder.value,
      search: usersSearch.value,
      show_hidden: showHiddenUsers.value,
      historical_only: showHistoricalOnly.value,
    })
  }

  function debouncedFetchUsers() {
    clearTimeout(usersDb)
    usersDb = setTimeout(() => {
      usersPage.value = 1
      fetchUsers()
    }, 300)
  }

  function toggleUserSort(c) {
    if (usersSortBy.value === c)
      usersSortOrder.value = usersSortOrder.value === 'desc' ? 'asc' : 'desc'
    else {
      usersSortBy.value = c
      usersSortOrder.value = 'desc'
    }
    usersPage.value = 1
    fetchUsers()
  }

  registerUsersRefresh(fetchUsers)
  onMounted(() => {
    if (!users.value.users.length) fetchUsers()
  })

  // The parent StatsView wraps tabs in <KeepAlive>, so this component is
  // cached rather than unmounted when the user navigates away (Activity
  // tab, another module, etc.). Without this hook the bulk-bar would
  // stay rendered on top of every other page since the selection state
  // survives the deactivation.
  onDeactivated(() => {
    selected.clear()
    // Cancel a pending search debounce so it can't fire a fetch on the
    // cached (deactivated) tab — see the timer in debouncedFetchUsers.
    clearTimeout(usersDb)
  })

  onUnmounted(() => {
    clearTimeout(usersDb)
  })

  return {
    users,
    loadingUsers,
    ticksToDuration,
    timeAgo,
    openUserProfile,
    usersPage,
    usersPerPage,
    usersSearch,
    usersSortBy,
    usersSortOrder,
    showHiddenUsers,
    showHistoricalOnly,
    selected,
    visibleSelected,
    hiddenSelected,
    allSelected,
    partiallySelected,
    toggleSelect,
    toggleSelectAll,
    fetchUsers,
    debouncedFetchUsers,
    toggleUserSort,
    bulkHide,
    bulkUnhide,
    bulkMerge,
    bulkDelete,
  }
}
