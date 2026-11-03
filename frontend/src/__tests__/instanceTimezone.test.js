import { describe, it, expect } from 'vitest'
import { TIMEZONE_LINES } from '@/constants/timezones'
import en from '@/locales/en.json'
import fr from '@/locales/fr.json'
import {
  buildRows,
  clockAt,
  formatOffset,
  lineKey,
  matchRows,
  rowOfFirst,
  zoneToSave,
} from '@/utils/instanceTimezone'

const GROUPS = [
  { offset: -300, zones: ['America/Bogota', 'America/Lima'] },
  { offset: -300, zones: ['America/New_York', 'America/Toronto', 'US/Eastern'] },
  { offset: 0, zones: ['Africa/Monrovia', 'Etc/UTC'] },
  { offset: 0, zones: ['UTC'] },
  {
    offset: 60,
    zones: ['Europe/Berlin', 'Europe/Madrid', 'Europe/Paris', 'Europe/Tirane', 'Europe/Warsaw'],
  },
  { offset: 345, zones: ['Asia/Kathmandu', 'Asia/Katmandu'] },
  { offset: 660, zones: ['Pacific/Norfolk'] },
  { offset: -720, zones: ['Etc/GMT+12'] },
]
const NAMES = { Eastern: 'Eastern Time', Sarajevo: 'Sarajevo, Varsovie' }
const rowsOf = groups =>
  buildRows(groups, {
    lineName: key => NAMES[key] ?? key,
    utcName: 'Universal time',
    locale: 'fr',
  })
const rows = () => rowsOf(GROUPS)
const row = zone => rowOfFirst(rows(), [zone])

describe('lines of the list', () => {
  it('have a name in both languages, and no name is left over', () => {
    for (const { key } of TIMEZONE_LINES) {
      const name = lineKey(key).split('.').pop()
      expect(fr.settings.timezoneLine[name], key).toBeTruthy()
      expect(en.settings.timezoneLine[name], key).toBeTruthy()
    }
    expect(Object.keys(fr.settings.timezoneLine)).toHaveLength(TIMEZONE_LINES.length)
  })

  it('hold real zones, once each, under distinct keys', () => {
    const zones = TIMEZONE_LINES.flatMap(line => line.zones)
    expect(new Set(zones).size).toBe(zones.length)
    expect(new Set(TIMEZONE_LINES.map(line => line.key)).size).toBe(TIMEZONE_LINES.length)
    for (const zone of zones) {
      expect(() => new Intl.DateTimeFormat('en', { timeZone: zone }), zone).not.toThrow()
    }
  })
})

describe('formatOffset', () => {
  it.each([
    [0, 'UTC+00:00'],
    [60, 'UTC+01:00'],
    [-300, 'UTC-05:00'],
    [330, 'UTC+05:30'],
    [345, 'UTC+05:45'],
    [-210, 'UTC-03:30'],
    [780, 'UTC+13:00'],
    [-720, 'UTC-12:00'],
  ])('%i minutes reads %s', (minutes, expected) => {
    expect(formatOffset(minutes)).toBe(expected)
  })
})

describe('buildRows', () => {
  it('goes from the negative offsets to the positive ones, UTC first among equals', () => {
    expect(rows().map(({ label }) => label)).toEqual([
      '(UTC-12:00) Etc/GMT+12',
      '(UTC-05:00) Bogota',
      '(UTC-05:00) Eastern Time',
      '(UTC) Universal time',
      '(UTC+00:00) Monrovia',
      '(UTC+01:00) Amsterdam',
      '(UTC+01:00) Brussels',
      '(UTC+01:00) Sarajevo, Varsovie',
      '(UTC+05:45) Kathmandu',
      '(UTC+11:00) Norfolk',
    ])
  })

  it('splits a group across its lines', () => {
    expect(row('Europe/Paris').label).toBe('(UTC+01:00) Brussels')
    expect(row('Europe/Madrid').label).toBe('(UTC+01:00) Brussels')
    expect(row('Europe/Berlin').label).toBe('(UTC+01:00) Amsterdam')
    expect(row('Europe/Warsaw').label).toBe('(UTC+01:00) Sarajevo, Varsovie')
  })

  it('keeps the zones on no line findable under the first line of their group', () => {
    expect(row('Europe/Tirane').label).toBe('(UTC+01:00) Amsterdam')
    expect(row('US/Eastern').label).toBe('(UTC-05:00) Eastern Time')
    expect(row('Etc/UTC').label).toBe('(UTC+00:00) Monrovia')
    expect(row('Asia/Katmandu').label).toBe('(UTC+05:45) Kathmandu')
  })

  it('takes a zone out of its line once it counts days differently', () => {
    const [madrid, paris] = rowsOf([
      { offset: 60, zones: ['Europe/Madrid'] },
      { offset: 120, zones: ['Europe/Paris'] },
    ])
    expect(madrid.label).toBe('(UTC+01:00) Brussels')
    expect(paris.label).toBe('(UTC+02:00) Paris')
    expect(paris.isMain).toBe(false)
  })

  it('limits a row of a group without a line to a few names', () => {
    const zones = [
      'Pacific/Enderbury',
      'Pacific/Fakaofo',
      'Pacific/Kanton',
      'Pacific/Tongatapu',
      'Pacific/Wake',
    ]
    expect(rowsOf([{ offset: 780, zones }])[0].label).toBe(
      '(UTC+13:00) Enderbury, Fakaofo, Kanton, Tongatapu',
    )
  })

  it('marks as main the lines of the list and UTC, not the other rows', () => {
    const others = rows().filter(({ isMain }) => !isMain)
    expect(others.map(({ key }) => key)).toEqual(['Etc/GMT+12', 'Pacific/Norfolk'])
    expect(rows().find(({ isUtc }) => isUtc).isMain).toBe(true)
  })
})

describe('matchRows', () => {
  const found = query => matchRows(rows(), query).map(({ key }) => key)

  it.each([
    ['brussels', ['Brussels']],
    ['BRUSSELS', ['Brussels']],
    ['  brussels  ', ['Brussels']],
    ['paris', ['Brussels']],
    ['varsovie', ['Sarajevo']],
    ['warsaw', ['Sarajevo']],
    ['new york', ['Eastern']],
    ['new_york', ['Eastern']],
    ['tirane', ['Amsterdam']],
    ['katmandu', ['Kathmandu']],
    ['norfolk', ['Pacific/Norfolk']],
    ['+01:00', ['Amsterdam', 'Brussels', 'Sarajevo']],
    ['atlantis', []],
  ])('finds %s', (query, expected) => {
    expect(found(query)).toEqual(expected)
  })

  it('ignores accents', () => {
    const list = buildRows([{ offset: -180, zones: ['America/Sao_Paulo'] }], {
      lineName: () => 'Brasília',
      utcName: '',
      locale: 'fr',
    })
    expect(matchRows(list, 'brasilia')).toHaveLength(1)
    expect(matchRows(list, 'são')).toHaveLength(1)
  })
})

describe('rowOfFirst', () => {
  it('takes the first zone that has a row', () => {
    expect(rowOfFirst(rows(), ['Mars/Olympus', 'Europe/Paris', 'UTC']).key).toBe('Brussels')
  })

  it('finds nothing when no zone has a row', () => {
    expect(rowOfFirst(rows(), ['Mars/Olympus', null])).toBeUndefined()
  })
})

describe('zoneToSave', () => {
  it('keeps the zone of the admin when the row holds it', () => {
    expect(zoneToSave(row('Europe/Paris'), 'Europe/Paris')).toBe('Europe/Paris')
    expect(zoneToSave(row('Europe/Tirane'), 'Europe/Tirane')).toBe('Europe/Tirane')
  })

  it('otherwise takes the first zone of the row', () => {
    expect(zoneToSave(row('Europe/Paris'), 'Asia/Tokyo')).toBe('Europe/Madrid')
    expect(zoneToSave(row('US/Eastern'), 'Asia/Tokyo')).toBe('America/New_York')
    expect(zoneToSave(row('Pacific/Norfolk'), 'Asia/Tokyo')).toBe('Pacific/Norfolk')
  })

  it('saves UTC as UTC', () => {
    expect(zoneToSave(row('UTC'), 'Asia/Tokyo')).toBe('UTC')
  })
})

describe('clockAt', () => {
  const NOW = new Date('2026-07-15T22:30:00Z')

  it('reads the clock at the offset, across midnight', () => {
    expect(clockAt(120, 'fr', NOW)).toBe('00:30')
    expect(clockAt(540, 'fr', NOW)).toBe('07:30')
    expect(clockAt(-300, 'fr', NOW)).toBe('17:30')
    expect(clockAt(0, 'fr', NOW)).toBe('22:30')
  })
})
