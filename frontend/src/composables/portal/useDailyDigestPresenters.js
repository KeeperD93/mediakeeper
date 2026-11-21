import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Calendar, Check, CircleCheck, Crown, Flame, MessageCircle, Send } from 'lucide-vue-next'
import { FOR_YOU_KIND } from '@/constants/dailyDigest'
import { MEDIA_TYPE } from '@/constants/media'
import { PORTAL_TAB } from '@/constants/portal'
import { localizedDate, localizedTime } from '@/utils/datetime'
import { localizedNumber } from '@/utils/localizedNumber'
import { capitalize, relativeTime } from '@/utils/portal/dailyDigest'
import { timeAgoForNotification } from '@/utils/portal/notificationLabel'

const percentOf = (part, whole) =>
  whole ? Math.min(100, Math.max(0, Math.round((part / whole) * 100))) : 0

/**
 * What both views of the daily digest write from its payload: the greeting, the
 * figures of the day, the level, the next trophy, the expiry warning, the « For you »
 * rows and the events. All computeds follow the digest ref.
 *
 * @param {import('vue').Ref} digest — the digest payload
 */
export function useDailyDigestPresenters(digest) {
  const { t } = useI18n()
  const k = key => `portal.dailyDigest.${key}`

  // The digest's day is the instance's: read at local midnight, not the browser's today.
  const day = computed(() => {
    const iso = digest.value?.date
    return iso ? new Date(`${iso}T00:00:00`) : new Date()
  })
  const formattedDate = computed(() =>
    capitalize(localizedDate(day.value, { weekday: 'long', day: 'numeric', month: 'long' })),
  )

  const greeting = computed(() => {
    const name = digest.value?.me?.display_name || ''
    const hour = new Date().getHours()
    const slot = hour < 6 ? 'night' : hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening'
    return name ? t(k(`greeting.${slot}WithName`), { name }) : t(k(`greeting.${slot}`))
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
        label: t(k('pills.rank')),
        value: `#${r.position}`,
        caption: t(k('pills.rankOf'), { total: r.total }),
        compactCaption: t(k('pills.rankCompact'), { total: r.total }),
        delta: r.movement ? `${r.movement > 0 ? '↑' : '↓'}${Math.abs(r.movement)}` : '',
        deltaDown: r.movement < 0,
      })
    }
    // Streak and tickets always show, 0 included: a missing card left a hole in the row.
    out.push({
      key: 'streak',
      icon: Flame,
      label: t(k('pills.streak')),
      value: d.streak,
      caption: t(k('pills.streakDays'), d.streak),
      compactCaption: t(k('pills.streakCompact'), d.streak),
    })
    const q = d.quota
    if (q && !q.unlimited && q.max_allowed > 0) {
      out.push({
        key: 'quota',
        icon: Send,
        label: t(k('pills.quota')),
        value: q.remaining,
        compactValue: `${q.remaining}/${q.max_allowed}`,
        caption: t(k('pills.quotaOf'), { total: q.max_allowed }),
        compactCaption: t(k('pills.quota')),
      })
    }
    out.push({
      key: 'tickets',
      icon: MessageCircle,
      label: t(k('pills.tickets')),
      value: d.tickets_open,
      caption: t(k(d.tickets_open > 0 ? 'pills.ticketsCaption' : 'pills.ticketsCaptionNone')),
      compactCaption: t(k('pills.ticketsCompact'), d.tickets_open),
    })
    return out
  })

  const level = computed(() => {
    const l = digest.value?.level
    if (!l) return null
    const percent = l.maxed ? 100 : percentOf(l.percent || 0, 100)
    const xp = localizedNumber(Math.max(0, l.xp_next_level - l.xp))
    const next = { xp, level: l.level + 1 }
    return {
      level: l.level,
      percent,
      title: t(`portal.profile.titles.${l.title_key || 'spectator'}`),
      ringLabel: l.maxed
        ? t(k('level.ringLabelMaxed'), { level: l.level })
        : t(k('level.ringLabel'), { level: l.level, percent }),
      xpYesterday:
        l.xp_yesterday > 0 ? t(k('level.xpYesterday'), { n: localizedNumber(l.xp_yesterday) }) : '',
      progress: l.maxed
        ? `${localizedNumber(l.xp)} XP`
        : `${localizedNumber(l.xp_into_level)} / ${localizedNumber(l.xp_next_level - l.xp_current_level)} XP`,
      toNext: l.maxed ? t(k('level.maxed')) : t(k('level.toNext'), next),
      toNextShort: l.maxed ? t(k('level.maxed')) : t(k('level.toNextShort'), next),
    }
  })

  const achievement = computed(() => {
    const n = digest.value?.next_achievement
    if (!n) return null
    return {
      name: t(n.name_key),
      description: n.description_key ? t(n.description_key) : '',
      percent: percentOf(n.progress, n.threshold),
      count: `${localizedNumber(n.progress)} / ${localizedNumber(n.threshold)}`,
      remaining: t(k('achievement.remaining'), { count: n.remaining }),
      remainingShort: t(k('achievement.remainingShort'), { count: n.remaining }),
    }
  })

  const expiry = computed(() => {
    const e = digest.value?.expiry
    if (!e) return null
    const date = localizedDate(e.ends_at, { day: 'numeric', month: 'long', year: 'numeric' })
    const when = t(k('expiry.when'), { n: e.days_left }, e.days_left)
    return {
      title: t(k('expiry.title'), { date, when }),
      hint: t(k('expiry.hint')),
      lead: t(k('expiry.lead'), { date }),
      whenShort: t(k('expiry.whenCompact'), { when }),
      hintShort: t(k('expiry.hintCompact')),
    }
  })

  function forYouRow(item, index) {
    const title = item.title || ''
    const base = {
      key: `${item.kind}-${index}`,
      kind: item.kind,
      ago: timeAgoForNotification(item.at, t),
    }
    if (item.kind === FOR_YOU_KIND.REQUEST_AVAILABLE) {
      return {
        ...base,
        tone: 'available',
        icon: CircleCheck,
        compactIcon: Check,
        text: t(k('forYou.available'), { title }),
        textShort: t(k('forYou.available'), { title }),
        sub: t(k('forYou.availableSince'), { when: relativeTime(item.at) }),
        link: t(k('forYou.see')),
        to: item.tmdb_id
          ? {
              name: 'portal-media-detail',
              params: { type: item.media_type || MEDIA_TYPE.MOVIE, id: item.tmdb_id },
            }
          : null,
      }
    }
    if (item.kind === FOR_YOU_KIND.REQUEST_APPROVED) {
      return {
        ...base,
        tone: 'approved',
        icon: Send,
        compactIcon: Send,
        text: t(k('forYou.approved'), { title }),
        textShort: t(k('forYou.approvedShort'), { title }),
        sub: t(k('forYou.approvedHint')),
        link: '',
        to: null,
      }
    }
    return {
      ...base,
      tone: 'ticket',
      icon: MessageCircle,
      compactIcon: MessageCircle,
      text: t(k('forYou.ticketReply'), { title }),
      textShort: t(k('forYou.ticketReplyShort'), { title }),
      sub: capitalize(relativeTime(item.at)),
      link: t(k('forYou.read')),
      to: item.ticket_id
        ? { name: PORTAL_TAB.TICKET_DETAIL, params: { id: item.ticket_id } }
        : null,
    }
  }

  const forYou = computed(() => (digest.value?.for_you || []).map(forYouRow))

  const events = computed(() =>
    (digest.value?.events || []).map(ev => {
      const at = new Date(ev.scheduled_at)
      const dayNumber = localizedDate(at, { day: 'numeric' })
      const month = localizedDate(at, { month: 'short' })
      const time = localizedTime(at, { hour: '2-digit', minute: '2-digit' })
      return {
        id: ev.id,
        title: ev.title,
        kind: t(k(`events.${ev.kind}`)),
        day: dayNumber,
        month,
        time,
        when: t(k('events.when'), {
          date: localizedDate(at, { day: 'numeric', month: 'short' }),
          time,
        }),
        icon: Calendar,
        to: { name: 'portal-rooms', params: { id: ev.id } },
      }
    }),
  )

  return {
    formattedDate,
    greeting,
    statCards,
    level,
    achievement,
    expiry,
    forYou,
    events,
  }
}
