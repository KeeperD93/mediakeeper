/**
 * Identity tab of the settings: the flag next to the username says the verdict of the
 * live check, refusals included (too short, invalid characters), and nothing otherwise.
 */
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

import SettingsTabIdentity from '../SettingsTabIdentity.vue'

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ locale: ref('fr'), t: key => key }),
}))

const flagFor = usernameCheck =>
  mount(SettingsTabIdentity, {
    props: {
      form: { display_name: 'Alice', bio: '' },
      profileData: { avatar_url: null, avatar_is_custom: false },
      usernameState: { lock_days: 180 },
      usernameCheck: { suggestions: [], ...usernameCheck },
      uploadAvatar: vi.fn(),
      deleteCustomAvatar: vi.fn(),
      checkUsername: vi.fn(),
    },
  }).find('.pt-settings-uname-flag')

describe('SettingsTabIdentity.vue, username flag', () => {
  it.each([
    ['current', 'warn', 'usernameCurrent'],
    ['free', 'ok', 'usernameAvailable'],
    ['taken', 'err', 'usernameTaken'],
    ['reserved', 'err', 'usernameReserved'],
    ['too_short', 'err', 'usernameTooShort'],
    ['invalid', 'err', 'usernameInvalid'],
    ['locked', 'err', 'usernameLockedShort'],
  ])('says « %s » with its tone', (reason, tone, key) => {
    const flag = flagFor({ reason })
    expect(flag.classes()).toContain(`pt-settings-uname-flag--${tone}`)
    expect(flag.text()).toBe(`portal.settings.identity.${key}`)
  })

  it('says it is checking while the check runs', () => {
    expect(flagFor({ reason: 'free', pending: true }).text()).toBe(
      'portal.settings.forceUsername.checking',
    )
  })

  it('shows nothing for no verdict or a failed check', () => {
    expect(flagFor({ reason: null }).exists()).toBe(false)
    expect(flagFor({ reason: 'error' }).exists()).toBe(false)
  })
})
