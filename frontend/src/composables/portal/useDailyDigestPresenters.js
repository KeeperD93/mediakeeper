import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Crown, Flame, Send, MessageCircle } from 'lucide-vue-next'

/**
 * Pure presentation helpers for the Daily Digest overlay.
 *
 * Pulled out of the component so the .vue file stays under the 300L cap
 * and the layout logic stays readable. All inputs are reactive refs so
 * the returned computeds stay in sync with the source of truth.
 *
 * @param {import('vue').Ref} digest — the digest payload ref
 * @param {import('vue').Ref} profile — the Portal profile ref
 */
export function useDailyDigestPresenters(digest, profile) {
  const { t, locale } = useI18n()

  const formattedDate = computed(() => {
    try {
      return new Date().toLocaleDateString(locale.value, {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
      })
    } catch {
      return ''
    }
  })

  const greeting = computed(() => {
    const name = profile?.value?.display_name || ''
    const hour = new Date().getHours()
    const slot = hour < 6 ? 'night' : hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening'
    return name
      ? t(`portal.dailyDigest.greeting.${slot}WithName`, { name })
      : t(`portal.dailyDigest.greeting.${slot}`)
  })

  const statCards = computed(() => {
    const d = digest.value
    if (!d || d.empty) return []
    const out = []
    const r = d.ranking
    if (r?.position) {
      out.push({
        key: 'rank',
        icon: Crown,
        cls: 'ddd-stat--rank',
        label: t('portal.dailyDigest.pills.rank'),
        value: `#${r.position}`,
        caption: t('portal.dailyDigest.pills.rankOf', { total: r.total }),
        delta: r.movement ? (r.movement > 0 ? `↑${r.movement}` : `↓${Math.abs(r.movement)}`) : '',
        deltaClass:
          r.movement > 0 ? 'ddd-stat-delta--up' : r.movement < 0 ? 'ddd-stat-delta--down' : '',
      })
    }
    if (d.streak > 0) {
      out.push({
        key: 'streak',
        icon: Flame,
        cls: 'ddd-stat--streak',
        label: t('portal.dailyDigest.pills.streak'),
        value: d.streak,
        caption: t('portal.dailyDigest.pills.streakDays', { n: d.streak }),
      })
    }
    const q = d.quota
    if (q && !q.unlimited && q.max_allowed > 0) {
      out.push({
        key: 'quota',
        icon: Send,
        cls: 'ddd-stat--quota',
        label: t('portal.dailyDigest.pills.quota'),
        value: q.remaining,
        caption: t('portal.dailyDigest.pills.quotaOf', { total: q.max_allowed }),
      })
    }
    if (d.tickets_open > 0) {
      out.push({
        key: 'tickets',
        icon: MessageCircle,
        cls: 'ddd-stat--tickets',
        label: t('portal.dailyDigest.pills.tickets'),
        value: d.tickets_open,
        caption: t('portal.dailyDigest.pills.ticketsCaption'),
      })
    }
    return out
  })

  const achPercent = computed(() => {
    const n = digest.value?.next_achievement
    if (!n || !n.threshold) return 0
    return Math.min(100, Math.max(0, Math.round((n.progress / n.threshold) * 100)))
  })

  function movementLabel(m) {
    if (m > 0) return `↑${m}`
    if (m < 0) return `↓${Math.abs(m)}`
    return '—'
  }

  function movementClass(m) {
    if (m > 0) return 'ddd-top3-move--up'
    if (m < 0) return 'ddd-top3-move--down'
    return 'ddd-top3-move--flat'
  }

  function formatEventDay(iso) {
    try {
      return new Date(iso).toLocaleDateString(locale.value, { day: '2-digit' })
    } catch {
      return ''
    }
  }
  function formatEventMonth(iso) {
    try {
      return new Date(iso).toLocaleDateString(locale.value, { month: 'short' })
    } catch {
      return ''
    }
  }
  function formatEventTime(iso) {
    try {
      return new Date(iso).toLocaleTimeString(locale.value, { hour: '2-digit', minute: '2-digit' })
    } catch {
      return ''
    }
  }

  return {
    formattedDate,
    greeting,
    statCards,
    achPercent,
    movementLabel,
    movementClass,
    formatEventDay,
    formatEventMonth,
    formatEventTime,
  }
}
