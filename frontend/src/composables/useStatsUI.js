import { ref, reactive, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { useI18n } from 'vue-i18n'
import { rootZoom } from '@/utils/zoom'

const activeTab = ref('general')
const preview = reactive({ show: false, x: 0, y: 0, img: '', name: '' })

const profileOpen = ref(false)
const profileName = ref('')
const profileTier = ref('bronze')
const profileAvatarUrl = ref(null)
const profileStyle = ref({})
const userProfile = ref(null)

const mergeModal = reactive({ open: false, source: null, targetId: null, allUsers: [], search: '' })
const activitySearchSeed = ref('')

const avatarColors = ['var(--accent-500)', '#8b5cf6', '#f59e0b', '#06b6d4', '#ec4899']

let refreshUsersList = null

export function useStatsUI() {
  const { apiGet, apiPost } = useApi()
  const { showToast } = useToast()
  const { t } = useI18n()

  function showPreview(e, item, imgKey) {
    preview.img = '/api/emby/image/' + item[imgKey]
    preview.name = item.name || ''
    // admin zoom: compute in unzoomed viewport space (clientX/innerWidth agree
    // there), then map to the zoomed shell the fixed preview lives in (utils/zoom).
    const z = rootZoom()
    let x = e.clientX + 16
    let y = e.clientY - 40
    if (x + 140 > window.innerWidth) x = e.clientX - 150
    if (y + 220 > window.innerHeight) y = e.clientY - 220
    preview.x = x / z
    preview.y = y / z
    preview.show = true
  }
  function hidePreview() {
    preview.show = false
  }

  async function fetchUserProfile(userId) {
    userProfile.value = null
    try {
      const res = await apiGet(
        `/api/stats/user_profile?user_id=${encodeURIComponent(String(userId))}&_t=${Date.now()}`,
      )
      userProfile.value = res || { _error: true }
    } catch {
      userProfile.value = { _error: true }
    }
  }

  async function openUserProfile(userId, name, event, opts = {}) {
    if (!userId) return
    profileName.value = name || '?'
    // Tier + avatar from the caller's row (e.g. StatsUsersTab list,
    // PlaybackCardRank items) so the popup header matches the rest
    // of the app — the stats profile detail endpoint itself returns
    // pure playback data with no identity fields.
    profileTier.value = opts.tier || 'bronze'
    profileAvatarUrl.value = opts.avatar_url || null
    const el = event?.target
    if (el) {
      const rect = el.getBoundingClientRect()
      const popW = 640,
        popH = 450
      // admin zoom: geometry is computed in unzoomed viewport space (rect,
      // innerWidth agree there); the final position is divided by the zoom so
      // the fixed popover lands under its trigger (utils/zoom).
      const z = rootZoom()
      const vw = window.innerWidth,
        vh = window.innerHeight
      const spaceBelow = vh - rect.bottom
      const above = spaceBelow < popH + 12 && rect.top > spaceBelow
      const top = above ? Math.max(8, rect.top - popH - 6) : rect.bottom + 6
      let left = rect.left
      if (left + popW > vw - 12) left = vw - popW - 12
      if (left < 12) left = 12
      profileStyle.value = { top: top / z + 'px', left: left / z + 'px' }
    }
    profileOpen.value = true
    await fetchUserProfile(userId)
  }

  async function openMergeModal(user) {
    mergeModal.source = user
    mergeModal.targetId = null
    mergeModal.search = ''
    mergeModal.open = true
    try {
      const d = await apiGet('/api/stats/users?per_page=500&show_hidden=true')
      mergeModal.allUsers = d?.users || []
    } catch {
      mergeModal.allUsers = []
    }
  }

  const mergeTargets = computed(() =>
    mergeModal.allUsers.filter(
      u =>
        u.user_id !== mergeModal.source?.user_id &&
        (!mergeModal.search || u.name.toLowerCase().includes(mergeModal.search.toLowerCase())),
    ),
  )

  async function handleMerge() {
    if (!mergeModal.targetId || !mergeModal.source) return
    const target = mergeModal.allUsers.find(u => u.user_id === mergeModal.targetId)
    await apiPost(`/api/stats/users/${encodeURIComponent(mergeModal.source.user_id)}/merge`, {
      target_user_id: mergeModal.targetId,
    })
    showToast(
      t('stats.userMerged', { source: mergeModal.source.name, target: target?.name || '?' }),
      TOAST_TYPE.OK,
    )
    mergeModal.open = false
    if (refreshUsersList) refreshUsersList()
  }

  function registerUsersRefresh(fn) {
    refreshUsersList = fn
  }

  function goToActivitySearch(name) {
    // Dismiss the hover-preview popup before navigating away. Without
    // this, the preview that opened on mouseenter stays pinned to its
    // last coordinates after the click switches tabs — the tab change
    // bypasses the mouseleave event that would normally hide it.
    hidePreview()
    activeTab.value = 'activity'
    activitySearchSeed.value = name
  }

  return {
    activeTab,
    preview,
    profileOpen,
    profileName,
    profileTier,
    profileAvatarUrl,
    profileStyle,
    userProfile,
    mergeModal,
    mergeTargets,
    activitySearchSeed,
    avatarColors,
    showPreview,
    hidePreview,
    openUserProfile,
    openMergeModal,
    handleMerge,
    registerUsersRefresh,
    goToActivitySearch,
  }
}
