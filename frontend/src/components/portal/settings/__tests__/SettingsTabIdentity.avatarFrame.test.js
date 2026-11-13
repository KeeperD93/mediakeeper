/**
 * Identity tab of the settings: its avatar preview wears the frame being chosen (or the
 * saved one) around the tier ring, as the rank card of the profile does.
 */
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

import SettingsTabIdentity from '../SettingsTabIdentity.vue'

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ locale: ref('fr'), t: key => key }),
}))

const preview = ({ chosen, saved = null } = {}) =>
  mount(SettingsTabIdentity, {
    props: {
      form: { display_name: 'Alice', bio: '', avatar_effect: chosen },
      profileData: { avatar_url: null, avatar_is_custom: false, avatar_effect: saved },
      usernameCheck: { suggestions: [] },
      uploadAvatar: vi.fn(),
      deleteCustomAvatar: vi.fn(),
      checkUsername: vi.fn(),
    },
  }).find('.pt-settings-avatar-preview')

describe('SettingsTabIdentity.vue, avatar preview', () => {
  it('draws the frame being chosen around the tier ring, with its room', () => {
    const zone = preview({ chosen: 'special', saved: 'meta' })
    const frame = zone.find('.pt-avf')
    expect(zone.classes()).toContain('gc-avatar-zone')
    expect(frame.classes()).toEqual(['pt-avf', 'pt-avf--fx', 'pt-avf--reserve'])
    expect(frame.find('.gc-avatar-fx--special').findAll('.gc-fx-rune')).toHaveLength(4)
    expect(frame.find('.gc-avatar-ring > .gc-avatar-inner > .gc-avatar-mk').exists()).toBe(true)
    expect(zone.find('.gc-avatar-fx--meta').exists()).toBe(false)
  })

  it('falls back on the saved frame', () => {
    const zone = preview({ chosen: undefined, saved: 'ranking' })
    expect(zone.find('.pt-avf-layer--top').classes()).toContain('gc-avatar-fx--ranking')
    expect(zone.findAll('.gc-fx-rstar')).toHaveLength(5)
  })

  it('draws no frame for one that is not unlockable, and keeps the bare ring', () => {
    const zone = preview({ chosen: 'sparkles' })
    expect(zone.find('.pt-avf-layer').exists()).toBe(false)
    expect(zone.find('.pt-avf').classes()).toEqual(['pt-avf'])
    expect(zone.find('.gc-avatar-ring .gc-avatar-mk').exists()).toBe(true)
  })
})
