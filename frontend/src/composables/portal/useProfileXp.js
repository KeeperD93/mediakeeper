/**
 * XP/level/time helpers for the profile page.
 *
 * Backend uses a quadratic XP curve: XP_for_level(n) = 50 * n * (n + 1).
 * e.g. level 1 = 100 XP, level 16 = 13 600 XP, level 50 = 127 500 XP (cap).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const DAY_LABELS = ['L', 'M', 'M', 'J', 'V', 'S', 'D']
const DAY_NAMES = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
const TITLE_TIER_MAP = {
  1: 'common',
  2: 'uncommon',
  3: 'rare',
  4: 'epic',
  5: 'legendary',
  6: 'mythic',
}

export function xpForLevel(n) {
  return 50 * n * (n + 1)
}

export function formatTime(minutes) {
  if (!minutes) return '0h'
  if (minutes < 60) return `${minutes}m`
  const h = Math.floor(minutes / 60)
  if (h < 24) return `${h}h`
  const d = Math.floor(h / 24)
  return `${d}j ${h % 24}h`
}

export function useProfileXp(profileData, stats) {
  const { t } = useI18n()

  const titleTierName = computed(() => TITLE_TIER_MAP[profileData.value?.title_tier] || 'common')

  const memberSince = computed(() => {
    const created = profileData.value?.created_at
    if (!created) return '—'
    const diff = Date.now() - new Date(created).getTime()
    return Math.max(1, Math.round(diff / (1000 * 60 * 60 * 24 * 30)))
  })

  const MAX_LEVEL = 50
  const MAX_XP = xpForLevel(MAX_LEVEL)

  const nextLevelXp = computed(() => {
    const level = profileData.value?.level || 1
    if (level >= MAX_LEVEL) return MAX_XP
    return xpForLevel(level + 1)
  })

  const xpPercent = computed(() => {
    const level = profileData.value?.level || 1
    if (level >= MAX_LEVEL) return 100
    const xp = profileData.value?.xp || 0
    const floor = xpForLevel(level)
    const ceiling = xpForLevel(level + 1)
    const span = Math.max(1, ceiling - floor)
    return Math.min(100, Math.max(0, Math.round(((xp - floor) / span) * 100)))
  })

  // Bar chart of plays per day of week (Monday → Sunday).
  const weekData = computed(() => {
    const ds = stats.value?.day_stats
    if (ds && Array.isArray(ds) && ds.length === 7) {
      const maxVal = Math.max(...ds.map(d => d.count || 0), 1)
      const topIdx = ds.reduce(
        (best, d, i) => ((d.count || 0) > (ds[best].count || 0) ? i : best),
        0,
      )
      return ds.map((d, i) => ({
        label: DAY_LABELS[i],
        pct: Math.round(((d.count || 0) / maxVal) * 100),
        top: i === topIdx,
      }))
    }
    return DAY_LABELS.map(label => ({ label, pct: 0, top: false }))
  })

  const topDay = computed(() => {
    const ds = stats.value?.day_stats
    if (ds && Array.isArray(ds) && ds.length === 7) {
      const topIdx = ds.reduce(
        (best, d, i) => ((d.count || 0) > (ds[best].count || 0) ? i : best),
        0,
      )
      if (ds[topIdx].count > 0) return DAY_NAMES[topIdx]
    }
    return '—'
  })

  // Fun comparison for total watch time — "= 12 movies", "= 3 days", etc.
  const funTimeComparison = computed(() => {
    const h = Math.floor((stats.value?.total_minutes || 0) / 60)
    if (h < 2) return ''
    if (h < 24) return t('portal.profile.funTime.movies', { count: Math.round(h / 2) })
    const d = Math.floor(h / 24)
    if (d < 7) return t('portal.profile.funTime.days', { count: d })
    if (d < 30) return t('portal.profile.funTime.weeks', { count: Math.round(d / 7) })
    return t('portal.profile.funTime.months', { count: Math.round(d / 30) })
  })

  return {
    titleTierName,
    memberSince,
    xpPercent,
    nextLevelXp,
    weekData,
    topDay,
    funTimeComparison,
    formatTime,
  }
}
