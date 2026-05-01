/**
 * Trophy display logic for the profile page.
 *
 * Stacks tiered families (cinephile_1..5 → only show next active tier),
 * sorts by status + rarity, computes overlay categories, handles pinning.
 */
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { ICON_MAP, Trophy } from '@/utils/portal/iconMap'
import { TROPHY_STATUS } from '@/constants/achievements'

const CATEGORIES = [
  { id: 'all', label: 'All', icon: 'Trophy' },
  { id: 'watching', label: 'Watching', icon: 'Film' },
  { id: 'dedication', label: 'Dedication', icon: 'Flame' },
  { id: 'diversity', label: 'Diversity', icon: 'Globe' },
  { id: 'special', label: 'Special', icon: 'Zap' },
  { id: 'community', label: 'Community', icon: 'MessageCircle' },
  { id: 'ranking', label: 'Ranking', icon: 'Trophy' },
  { id: 'meta', label: 'Profile', icon: 'TrendingUp' },
  { id: 'mastery', label: 'Mastery', icon: 'Crown' },
  { id: 'secret', label: 'Secrets', icon: 'HelpCircle' },
]

export function useTrophyDisplay(trophies, profileData) {
  const { t, te } = useI18n()
  const { apiPost } = useApi()
  const { setPortalAuth, unreadNewsCount, ui } = usePortalAuth()

  const showAllTrophies = ref(false)
  const selectedCategory = ref('all')
  const selectedTrophy = ref(null)
  const unlockToast = ref(null)

  // Group standard trophies by family (name_key); show next un-unlocked tier or
  // the highest tier when all are unlocked. Secrets aren't stacked.
  const displayTrophies = computed(() => {
    const items = trophies.value?.items || []
    const secrets = items.filter(a => a.secret)
    const standards = items.filter(a => !a.secret)

    const groups = {}
    for (const ach of standards) {
      const key = ach.name_key
      if (!groups[key]) groups[key] = []
      groups[key].push(ach)
    }
    const stacked = []
    for (const achs of Object.values(groups)) {
      achs.sort((a, b) => a.tier - b.tier)
      const nextTier = achs.find(a => a.status !== TROPHY_STATUS.UNLOCKED)
      stacked.push(nextTier ? { ...nextTier } : { ...achs[achs.length - 1] })
    }

    const all = [...stacked, ...secrets]
    const statusOrder = (a) => {
      if (a.status === TROPHY_STATUS.UNLOCKED) return 0
      if (a.status === TROPHY_STATUS.PROGRESS) return 1
      if (a.status === TROPHY_STATUS.LOCKED) return 2
      return 3
    }
    all.sort((a, b) => {
      const sa = statusOrder(a), sb = statusOrder(b)
      if (sa !== sb) return sa - sb
      if (a.status === TROPHY_STATUS.UNLOCKED && b.status === TROPHY_STATUS.UNLOCKED) {
        return (a.rarity_pct ?? 100) - (b.rarity_pct ?? 100)
      }
      return (a.sort_order ?? 0) - (b.sort_order ?? 0)
    })
    return all
  })

  const displayTrophiesUnlocked = computed(
    () => displayTrophies.value.filter(a => a.status === TROPHY_STATUS.UNLOCKED).length,
  )

  // A trophy belongs to a category if its primary OR its secondary category
  // matches. Lets seasonal secrets show up both in "Secrets" and in their
  // thematic category (e.g. Christmas also appears in "Special").
  const trophyInCategory = (a, catId) => a.category === catId || a.secondary_category === catId

  const categoriesWithStats = computed(() => {
    const items = displayTrophies.value
    return CATEGORIES.map(cat => {
      const filtered = cat.id === 'all' ? items : items.filter(a => trophyInCategory(a, cat.id))
      return {
        ...cat,
        icon: ICON_MAP[cat.icon] || Trophy,
        total: filtered.length,
        unlocked: filtered.filter(a => a.status === TROPHY_STATUS.UNLOCKED).length,
      }
    })
  })

  const filteredTrophies = computed(() => {
    const items = displayTrophies.value
    if (selectedCategory.value === 'all') return items
    return items.filter(a => trophyInCategory(a, selectedCategory.value))
  })

  const globalProgressPct = computed(() => {
    const total = displayTrophies.value.length
    if (!total) return 0
    return Math.round(100 * displayTrophiesUnlocked.value / total)
  })

  function trophyDesc(ach) {
    const key = ach.description_key
    if (!key) return ''
    return te(key) ? t(key) : ''
  }

  function isPinned(achievementId) {
    return (profileData.value?.selected_badges || []).includes(achievementId)
  }

  async function togglePin(ach) {
    const pinned = isPinned(ach.id)
    const endpoint = pinned ? '/api/portal/achievements/unpin' : '/api/portal/achievements/pin'
    try {
      const res = await apiPost(endpoint, { achievement_id: ach.id })
      if (res?.ok === false) return
      // profileData is exposed as readonly() by usePortalAuth; rebuild a
    // fresh profile object and push it through setPortalAuth so reactivity
      // propagates (sidebar pinned row, leaderboard, etc.).
      const badges = profileData.value?.selected_badges || []
      const next = pinned
        ? badges.filter(b => b !== ach.id)
        : [...badges, ach.id]
      const nextProfile = { ...(profileData.value || {}), selected_badges: next }
    setPortalAuth(nextProfile, unreadNewsCount.value, ui.value)
    } catch (e) {
      console.error('[togglePin] failed', e)
    }
  }

  return {
    showAllTrophies, selectedCategory, selectedTrophy, unlockToast,
    displayTrophies, displayTrophiesUnlocked, categoriesWithStats, filteredTrophies,
    globalProgressPct, trophyDesc, isPinned, togglePin,
  }
}
