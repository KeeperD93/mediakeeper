import { afterEach, describe, expect, it } from 'vitest'

import { applyLocaleEphemeral, getLocale } from '@/i18n'
import { localizedNumber } from '@/utils/localizedNumber'

// French groups digits with a narrow no-break space.
const FRENCH_12345 = '12 345'

describe('localizedNumber', () => {
  const initial = getLocale()

  afterEach(async () => {
    await applyLocaleEphemeral(initial)
  })

  it('groups the digits as French does in French', async () => {
    await applyLocaleEphemeral('fr')
    expect(localizedNumber(12345)).toBe(FRENCH_12345)
  })

  it('groups the digits as English does in English', async () => {
    await applyLocaleEphemeral('en')
    expect(localizedNumber(12345)).toBe('12,345')
  })

  it('passes its options on', async () => {
    await applyLocaleEphemeral('fr')
    expect(localizedNumber(0.5, { style: 'percent' })).toBe('50 %')
  })
})
