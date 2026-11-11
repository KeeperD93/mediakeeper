import { describe, it, expect, vi, afterEach } from 'vitest'
import { ref } from 'vue'

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: k => k }),
}))

import { applyLocaleEphemeral, getLocale } from '@/i18n'
import { useProfileXp, xpForLevel } from '@/composables/portal/useProfileXp'

// Monday → Sunday, as the server sends them; Sunday is the busiest day.
const busySunday = () => ref({ day_stats: [1, 0, 0, 0, 0, 0, 5].map(count => ({ count })) })

const labels = weekData => weekData.value.map(day => day.label)

describe('useProfileXp — days of the week', () => {
  const initial = getLocale()

  afterEach(async () => {
    await applyLocaleEphemeral(initial)
  })

  it('writes the days in French on a French profile, Monday first', async () => {
    await applyLocaleEphemeral('fr')
    const { weekData, topDay } = useProfileXp(ref({}), busySunday())

    expect(labels(weekData)).toEqual(['L', 'M', 'M', 'J', 'V', 'S', 'D'])
    expect(weekData.value.filter(day => day.top)).toEqual([weekData.value[6]])
    expect(topDay.value).toBe('Dimanche')
  })

  it('writes the days in English on an English profile, Monday first', async () => {
    await applyLocaleEphemeral('en')
    const { weekData, topDay } = useProfileXp(ref({}), busySunday())

    expect(labels(weekData)).toEqual(['M', 'T', 'W', 'T', 'F', 'S', 'S'])
    expect(topDay.value).toBe('Sunday')
  })

  it('follows a change of language', async () => {
    await applyLocaleEphemeral('fr')
    const { weekData, topDay } = useProfileXp(ref({}), busySunday())
    expect(topDay.value).toBe('Dimanche')

    await applyLocaleEphemeral('en')
    expect(topDay.value).toBe('Sunday')
    expect(labels(weekData)[0]).toBe('M')
  })

  it('keeps the seven labels without any play', async () => {
    await applyLocaleEphemeral('en')
    const { weekData, topDay } = useProfileXp(ref({}), ref({ day_stats: null }))

    expect(labels(weekData)).toEqual(['M', 'T', 'W', 'T', 'F', 'S', 'S'])
    expect(weekData.value.every(day => day.pct === 0 && !day.top)).toBe(true)
    expect(topDay.value).toBe('—')
  })
})

describe('xpForLevel', () => {
  // Same table as the server test of xp_for_level.
  it.each([
    [1, 100],
    [16, 13_600],
    [50, 127_500],
  ])('level %i takes %i XP, as on the server', (level, xp) => {
    expect(xpForLevel(level)).toBe(xp)
  })
})
