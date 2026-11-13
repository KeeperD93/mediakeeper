import { DIGEST_RELEASE_TEASER_SIZE, NEWS_TYPE, RELEASE_CATEGORY } from '@/constants/dailyDigest'
import { getLocale } from '@/i18n'
import { localizedDate } from '@/utils/datetime'
import { localizedNumber } from '@/utils/localizedNumber'

const NEWS_TYPES = Object.values(NEWS_TYPE)
const RELEASE_CATEGORIES = Object.values(RELEASE_CATEGORY)
const NEWS_BADGE_TONE = { [NEWS_TYPE.MAINTENANCE]: 'warn', [NEWS_TYPE.EVENT]: 'event' }

/** Paragraphs of a news text: split on blank lines, or on line breaks when it has none. */
export function newsParagraphs(content) {
  const text = (content || '').trim()
  if (!text) return []
  const separator = /\n\s*\n/.test(text) ? /\n\s*\n/ : /\n/
  return text
    .split(separator)
    .map(part => part.trim())
    .filter(Boolean)
}

/** A news item as the digest draws it: type badge, short date and paragraphs. */
export function newsView(item) {
  const type = NEWS_TYPES.includes(item.type) ? item.type : NEWS_TYPE.OTHER
  const tone = NEWS_BADGE_TONE[type]
  return {
    id: item.id,
    title: item.title,
    imageUrl: item.image_url || null,
    pinned: !!item.pinned,
    isNew: !!item.is_new,
    typeKey: `portal.news.types.${type}`,
    badgeClass: tone ? `dd-badge--${tone}` : '',
    date: item.created_at ? localizedDate(item.created_at, { day: 'numeric', month: 'short' }) : '',
    paragraphs: newsParagraphs(item.content),
  }
}

/** A section of a version: its label (the changelog's own word when unknown) and tone. */
function releaseGroup([name, items]) {
  const key = RELEASE_CATEGORIES.includes(name) ? name.toLowerCase() : null
  return {
    name,
    labelKey: key ? `changelog.cat.${key}` : null,
    toneClass: key ? `dd-release-cat--${key}` : '',
    count: localizedNumber(items.length),
    items,
  }
}

/**
 * The new Portal version as the digest draws it: number, short date, its sections,
 * and the first changes the closed card shows before « +N other changes ».
 */
export function releaseView(release) {
  const groups = Object.entries(release.categories || {})
    .filter(([, items]) => items.length)
    .map(releaseGroup)
  const changes = groups.flatMap(group => group.items.map(text => ({ ...group, text })))
  const rest = Math.max(0, changes.length - DIGEST_RELEASE_TEASER_SIZE)
  return {
    version: release.version,
    isNew: !!release.is_new,
    date: release.date
      ? localizedDate(new Date(`${release.date}T00:00:00`), { day: 'numeric', month: 'short' })
      : '',
    groups,
    total: changes.length,
    totalLabel: localizedNumber(changes.length),
    teaser: changes.slice(0, DIGEST_RELEASE_TEASER_SIZE),
    rest,
    restLabel: localizedNumber(rest),
  }
}

/** First letter in capitals, for a date or a delay that opens a line. */
export function capitalize(text) {
  return text ? text.charAt(0).toLocaleUpperCase(getLocale()) + text.slice(1) : ''
}

/** How long ago a moment was, in words: « il y a 2 heures », « hier ». */
export function relativeTime(iso, now = Date.now()) {
  const seconds = Math.trunc((new Date(iso).getTime() - now) / 1000)
  const format = new Intl.RelativeTimeFormat(getLocale(), { numeric: 'auto' })
  const elapsed = Math.abs(seconds)
  if (elapsed < 60) return format.format(seconds, 'second')
  if (elapsed < 3600) return format.format(Math.trunc(seconds / 60), 'minute')
  if (elapsed < 86400) return format.format(Math.trunc(seconds / 3600), 'hour')
  return format.format(Math.trunc(seconds / 86400), 'day')
}

/** A rank's move since last month, as the ranking draws it: « ↑2 », « ↓1 », « — ». */
export function rankMove(movement) {
  if (movement > 0) return { text: `↑${movement}`, tone: 'up', n: movement }
  if (movement < 0) return { text: `↓${-movement}`, tone: 'down', n: -movement }
  return { text: '—', tone: 'flat', n: 0 }
}

const METALS = ['gold', 'silver', 'bronze']

function rankingRow(entry, t) {
  const move = rankMove(entry.movement)
  const title = t(`portal.profile.titles.${entry.title_key || 'spectator'}`)
  const trophies = entry.trophies_won || 0
  return {
    entry,
    move,
    moveTitle:
      move.tone === 'flat'
        ? t('portal.leaderboard.move.month.stable')
        : t(`portal.leaderboard.move.month.${move.tone}`, { n: move.n }),
    levelShort: t('portal.dailyDigest.top3.levelShort', { level: entry.level, title }),
    levelLong: t('portal.leaderboard.hero.levelTitle', { level: entry.level, title }),
    xp: `${localizedNumber(entry.period_xp || 0)} XP`,
    trophies: t('portal.leaderboard.trophiesWon', { n: trophies }, trophies),
    to: entry.user_id ? { name: 'portal-user-profile', params: { id: entry.user_id } } : undefined,
  }
}

/**
 * The month's ranking of the digest, as both views draw it: the first three with
 * their place and metal, then the viewer when the server added them further down.
 */
export function rankingRows(entries, t) {
  const leaders = entries
    .slice(0, 3)
    .map((entry, index) => ({ ...rankingRow(entry, t), place: index + 1, metal: METALS[index] }))
  const viewer = entries.slice(3).find(entry => entry.is_current_user)
  return { leaders, me: viewer ? rankingRow(viewer, t) : null }
}
