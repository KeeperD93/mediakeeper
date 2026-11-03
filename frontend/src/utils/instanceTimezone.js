/**
 * The time zone list of the settings page. The server sends groups of zones that count
 * days alike, ``{ offset, zones }``, the offset in minutes east of UTC. A row is a line of
 * ``TIMEZONE_LINES``, or a group that has none.
 */
import { TIMEZONE_LINES } from '@/constants/timezones'

const PLACE = /^(Africa|America|Antarctica|Asia|Atlantic|Australia|Europe|Indian|Pacific)\//
const MAX_CITIES_OF_A_MINOR_ROW = 4

const readable = name => name.replaceAll('_', ' ')
const lastPart = zone => zone.split('/').pop()

/** Locale key of the name of a line of the list. */
export const lineKey = key => `settings.timezoneLine.${key}`

/** ``UTC+01:00``, ``UTC-05:00``, ``UTC+05:30``, from minutes east of UTC. */
export function formatOffset(minutes) {
  const absolute = Math.abs(minutes)
  const pad = value => String(value).padStart(2, '0')
  const hours = (absolute - (absolute % 60)) / 60
  return `UTC${minutes < 0 ? '-' : '+'}${pad(hours)}:${pad(absolute % 60)}`
}

const rowLabel = (offset, name) => `(${formatOffset(offset)}) ${name}`

function minorRow({ offset }, zones) {
  const places = zones.filter(zone => PLACE.test(zone)).map(zone => readable(lastPart(zone)))
  const cities = places.length ? places.slice(0, MAX_CITIES_OF_A_MINOR_ROW) : [readable(zones[0])]
  return {
    key: zones[0],
    offset,
    zones,
    isUtc: false,
    isMain: false,
    label: rowLabel(offset, cities.join(', ')),
  }
}

/**
 * Rows of the list, from the smallest offset to the largest, UTC first among equals:
 * ``(UTC+01:00) Bruxelles, Copenhague, Madrid, Paris``. ``lineName`` names a line of the list.
 * A zone that no longer counts days like the rest of its line leaves it. The other zones
 * of a group stay findable under its first line, or get a row when it has no line.
 */
export function buildRows(groups, { lineName, utcName, locale }) {
  const groupOf = new Map(groups.flatMap(group => group.zones.map(zone => [zone, group])))
  const placed = new Set()
  const firstRowOf = new Map()
  const rows = []
  for (const line of TIMEZONE_LINES) {
    const group = line.zones.map(zone => groupOf.get(zone)).find(Boolean)
    if (!group) continue
    const zones = line.zones.filter(zone => groupOf.get(zone) === group)
    const { offset } = group
    const row = {
      key: line.key,
      offset,
      zones,
      isUtc: false,
      isMain: true,
      label: rowLabel(offset, lineName(line.key)),
    }
    rows.push(row)
    zones.forEach(zone => placed.add(zone))
    if (!firstRowOf.has(group)) firstRowOf.set(group, row)
  }
  for (const group of groups) {
    const rest = group.zones.filter(zone => !placed.has(zone))
    const row = firstRowOf.get(group)
    if (group.zones.length === 1 && group.zones[0] === 'UTC') {
      rows.push({
        key: 'UTC',
        offset: 0,
        zones: ['UTC'],
        isUtc: true,
        isMain: true,
        label: `(UTC) ${utcName}`,
      })
    } else if (row) {
      row.zones = [...row.zones, ...rest]
    } else if (rest.length) {
      rows.push(minorRow(group, rest))
    }
  }
  return rows.sort(
    (a, b) =>
      a.offset - b.offset ||
      Number(b.isUtc) - Number(a.isUtc) ||
      a.label.localeCompare(b.label, locale),
  )
}

const searchable = text =>
  readable(text)
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()

/** Rows whose label or zones contain ``query``, ignoring case, accents and underscores. */
export function matchRows(rows, query) {
  const needle = searchable(query.trim())
  return rows.filter(row => searchable(`${row.label} ${row.zones.join(' ')}`).includes(needle))
}

/** The row holding the first of ``zones`` that has one. */
export function rowOfFirst(rows, zones) {
  for (const zone of zones) {
    const row = rows.find(candidate => candidate.zones.includes(zone))
    if (row) return row
  }
  return undefined
}

/** The zone a row saves: the admin's own when it holds it, else its first one. */
export const zoneToSave = (row, browser) => (row.zones.includes(browser) ? browser : row.zones[0])

export const browserZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone

/** Time at ``offset`` minutes from UTC: shifted, then read as UTC, to use the server's offset. */
export function clockAt(offset, locale, now) {
  const shifted = new Date(now.getTime() + offset * 60_000)
  return new Intl.DateTimeFormat(locale, { timeZone: 'UTC', timeStyle: 'short' }).format(shifted)
}
