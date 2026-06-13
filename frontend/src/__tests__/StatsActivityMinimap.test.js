import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import StatsActivityMinimap from '@/components/stats/StatsActivityMinimap.vue'

// Real vue-i18n (legacy:false, like the app) with the actual tooltip messages,
// so the test exercises real interpolation + pluralisation — this is what the
// previous 3-arg t(key, choice, named) call silently broke (the hour dropped).
const i18n = createI18n({
  legacy: false,
  locale: 'fr',
  messages: {
    fr: {
      stats: {
        last24h: 'Dernières 24 heures',
        plays_unit: 'lectures',
        directPlay: 'Direct',
        transcodeLabel: 'Transcode',
        otherStream: 'Autre',
        minimapHourTooltip: '{hour}h : {count} lecture | {hour}h : {count} lectures',
        minimapHourUsers: ' ({users})',
      },
    },
  },
})

function mountWith(items) {
  return mount(StatsActivityMinimap, { props: { items }, global: { plugins: [i18n] } })
}

// toISOString -> new Date(...).getHours() round-trips the local hour, so the
// item lands in the column for that local hour regardless of the test TZ.
function atHour(h) {
  return new Date(2026, 5, 13, h, 30).toISOString()
}

describe('StatsActivityMinimap — hourly tooltip', () => {
  it('interpolates the hour (regression: 3-arg call dropped {hour})', () => {
    const w = mountWith([{ started_at: atHour(14), play_method: 'DirectPlay', user: 'alice' }])
    const title = w.findAll('.minimap-hour-col')[14].attributes('title')
    expect(title).toBe('14h : 1 lecture (alice)')
  })

  it('pluralises and lists users from the named count', () => {
    const w = mountWith([
      { started_at: atHour(9), play_method: 'DirectPlay', user: 'a' },
      { started_at: atHour(9), play_method: 'Transcode', user: 'b' },
    ])
    const title = w.findAll('.minimap-hour-col')[9].attributes('title')
    expect(title).toBe('9h : 2 lectures (a, b)')
  })

  it('empty hours read singular-zero with the hour present', () => {
    const w = mountWith([])
    expect(w.findAll('.minimap-hour-col')[0].attributes('title')).toBe('0h : 0 lectures')
  })
})
