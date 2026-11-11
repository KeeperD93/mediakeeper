/**
 * The total watch time of the profile writes its day unit in the page's language.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

const app = vi.hoisted(() => ({ t: null }))

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  // Run outside a component, the composable gets the app's own translations.
  useI18n: () => ({ t: (...args) => app.t(...args) }),
}))

import i18n, { applyLocaleEphemeral, getLocale } from '@/i18n'
import { useProfileXp } from '@/composables/portal/useProfileXp'

app.t = i18n.global.t

const THREE_DAYS_FOUR_HOURS = (3 * 24 + 4) * 60

async function formatTimeIn(locale) {
  await applyLocaleEphemeral(locale)
  return useProfileXp(ref({}), ref({})).formatTime
}

describe('useProfileXp — total watch time', () => {
  const initial = getLocale()

  afterEach(async () => {
    await applyLocaleEphemeral(initial)
  })

  it('writes the days with « j » in French', async () => {
    const formatTime = await formatTimeIn('fr')
    expect(formatTime(THREE_DAYS_FOUR_HOURS)).toBe('3j 4h')
  })

  it('writes the days with « d » in English', async () => {
    const formatTime = await formatTimeIn('en')
    expect(formatTime(THREE_DAYS_FOUR_HOURS)).toBe('3d 4h')
  })

  it('keeps hours and minutes as they were', async () => {
    const formatTime = await formatTimeIn('en')
    expect([0, 45, 5 * 60].map(formatTime)).toEqual(['0h', '45m', '5h'])
  })
})
