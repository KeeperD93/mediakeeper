/**
 * The portal applies its language while its layout is being set up, and the page
 * mounted right after sends its first requests at once: the switch cannot wait.
 */
import { describe, it, expect, afterEach } from 'vitest'
import { applyLocaleEphemeral, getLocale } from '@/i18n'
import { buildApiHeaders } from '@/composables/apiClient'

describe('applyLocaleEphemeral', () => {
  const initial = getLocale()

  afterEach(async () => {
    await applyLocaleEphemeral(initial)
  })

  it('has switched the language by the time the call returns', () => {
    const other = initial === 'fr' ? 'en' : 'fr'

    // Not awaited on purpose: this is what the layout does.
    applyLocaleEphemeral(other)

    expect(getLocale()).toBe(other)
    expect(document.documentElement.lang).toBe(other)
    expect(buildApiHeaders({ method: 'GET' }).get('X-MK-Locale')).toBe(other)
  })

  it('leaves the language alone when it is not supported', async () => {
    expect(await applyLocaleEphemeral('xx')).toBe(false)
    expect(getLocale()).toBe(initial)
  })
})
