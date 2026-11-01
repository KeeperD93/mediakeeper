/**
 * The scheduler's short durations, through the real locale files: a wrong key
 * or placeholder, or a unit left in one language, would only show on screen.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import fr from '@/locales/fr.json'
import en from '@/locales/en.json'
import { useParamsScheduler } from '@/composables/useParamsScheduler'
import SchedulerTaskRowMenu from '@/components/settings/SchedulerTaskRowMenu.vue'

vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet: vi.fn(), apiFetch: vi.fn() }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))

const i18nIn = locale =>
  createI18n({ legacy: false, locale, missingWarn: false, messages: { fr, en } })

function formatterIn(i18n) {
  let formatter
  mount(
    {
      setup() {
        formatter = useParamsScheduler().formatSeconds
        return () => null
      },
    },
    { global: { plugins: [i18n] } },
  )
  return formatter
}

describe('formatSeconds', () => {
  it.each([
    [90, '90s'],
    [60, '1min'],
    [5400, '90min'],
    [3600, '1h'],
    [7200, '2h'],
    [86400, '1j'],
    [172800, '2j'],
  ])('gives %i seconds in French', (seconds, expected) => {
    expect(formatterIn(i18nIn('fr'))(seconds)).toBe(expected)
  })

  it.each([
    [90, '90s'],
    [60, '1min'],
    [3600, '1h'],
    [86400, '1d'],
    [172800, '2d'],
  ])('gives %i seconds in English', (seconds, expected) => {
    expect(formatterIn(i18nIn('en'))(seconds)).toBe(expected)
  })

  it.each([
    ['fr', 'Remettre à 1j'],
    ['en', 'Reset to 1d'],
  ])('reaches the Default button tooltip in %s', (locale, expected) => {
    const i18n = i18nIn(locale)
    const wrapper = mount(SchedulerTaskRowMenu, {
      props: {
        task: { description: 'Test task', default_sec: 86400 },
        formatSeconds: formatterIn(i18n),
      },
      global: { plugins: [i18n], mocks: { $t: i18n.global.t } },
    })

    expect(wrapper.find('.strm-action-btn').attributes('title')).toBe(expected)
    wrapper.unmount()
  })
})
