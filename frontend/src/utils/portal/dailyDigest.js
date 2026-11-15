import {
  DIGEST_RELEASE_TEASER_SIZE,
  DIGEST_ROW_KIND,
  DIGEST_ROW_RANK,
  NEWS_TYPE,
  RELEASE_CATEGORY,
} from '@/constants/dailyDigest'
import { getLocale } from '@/i18n'
import { localizedDate, localizedDateTime } from '@/utils/datetime'
import { localizedNumber } from '@/utils/localizedNumber'

const NEWS_TYPES = Object.values(NEWS_TYPE)
const RELEASE_CATEGORIES = Object.values(RELEASE_CATEGORY)
const NEWS_BADGE_TONE = { [NEWS_TYPE.MAINTENANCE]: 'warn', [NEWS_TYPE.EVENT]: 'event' }
// Types without a rank of their own go with the announcements.
const NEWS_RANK = {
  [NEWS_TYPE.MAINTENANCE]: DIGEST_ROW_RANK.MAINTENANCE,
  [NEWS_TYPE.EVENT]: DIGEST_ROW_RANK.EVENT,
}

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
    type,
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

/** Time left before `iso` in its largest whole unit: days, hours, then minutes (one at least). */
export function timeLeft(iso, now = Date.now()) {
  const seconds = Math.max(60, Math.trunc((new Date(iso).getTime() - now) / 1000))
  if (seconds >= 86400) return { unit: 'days', n: Math.trunc(seconds / 86400) }
  if (seconds >= 3600) return { unit: 'hours', n: Math.trunc(seconds / 3600) }
  return { unit: 'minutes', n: Math.trunc(seconds / 60) }
}

/**
 * A running XP boost as the digest draws it: « Reduced XP » under ×1, its multiplier and
 * its end in the viewer's language, the time left, its text and the actions it is
 * limited to (none: every action counts).
 */
export function boostView(boost, now = Date.now()) {
  const left = timeLeft(boost.ends_at, now)
  // The end on the server's clock, the same for every viewer: its wall time read as UTC.
  const end = new Date(`${boost.ends_local}Z`)
  return {
    key: `${DIGEST_ROW_KIND.BOOST}-${boost.id}`,
    name: boost.name,
    reduced: boost.multiplier < 1,
    multiplier: localizedNumber(boost.multiplier),
    until: localizedDate(end, { day: 'numeric', month: 'short', timeZone: 'UTC' }),
    ends: localizedDateTime(end, {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
    }),
    leftKey: `portal.dailyDigest.boost.left.${left.unit}`,
    left: left.n,
    leftLabel: localizedNumber(left.n),
    paragraphs: newsParagraphs(boost.description),
    actions: boost.actions.map(action => ({
      key: `portal.dailyDigest.boost.actions.${action}`,
      action,
    })),
  }
}

function newsRow(item) {
  const view = newsView(item)
  const rank = view.pinned
    ? DIGEST_ROW_RANK.PINNED
    : (NEWS_RANK[view.type] ?? DIGEST_ROW_RANK.ANNOUNCEMENT)
  return { kind: DIGEST_ROW_KIND.NEWS, key: view.id, rank, view }
}

function boostRow(boost) {
  const view = boostView(boost)
  return { kind: DIGEST_ROW_KIND.BOOST, key: view.key, rank: DIGEST_ROW_RANK.BOOST, view }
}

/**
 * The news block as both views lay it out: the first news item in the list's order
 * gets the card, the other rows follow `DIGEST_ROW_RANK` and keep the server's order
 * (newest news, first boost to end) within a rank. Drawn only when there is at least
 * one news item.
 */
export function newsLayout(news, release, boosts = []) {
  const rows = news.map(newsRow)
  if (release) {
    rows.push({
      kind: DIGEST_ROW_KIND.RELEASE,
      key: DIGEST_ROW_KIND.RELEASE,
      rank: DIGEST_ROW_RANK.RELEASE,
      view: releaseView(release),
    })
  }
  rows.push(...boosts.map(boostRow))
  rows.sort((a, b) => a.rank - b.rank)
  const [main] = rows.splice(
    rows.findIndex(row => row.kind === DIGEST_ROW_KIND.NEWS),
    1,
  )
  return { main: main.view, rows }
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
