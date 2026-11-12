/**
 * Report window counters, read with the real texts: numbers in the app's language,
 * and the "too long" warning told to screen readers once, when it appears.
 */
import { afterEach, describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import i18n, { applyLocaleEphemeral, getLocale } from '@/i18n'

vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'portal-home', query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiPost: vi.fn() }),
  resolveApiError: code => code,
}))

import FeedbackModal from '@/components/feedback/FeedbackModal.vue'

const initial = getLocale()
let wrapper

async function openPortalForm(locale) {
  await applyLocaleEphemeral(locale)
  wrapper = mount(FeedbackModal, {
    props: { open: false, endpoint: '/api/portal/feedback', showLocation: false },
    global: { plugins: [i18n], mocks: { $t: (...args) => i18n.global.t(...args) } },
    attachTo: document.body,
  })
  await wrapper.setProps({ open: true })
  return wrapper
}

afterEach(async () => {
  wrapper?.unmount()
  await applyLocaleEphemeral(initial)
})

describe('FeedbackModal counters', () => {
  it.each([
    ['fr', '1\u202f500 / 1\u202f500 caractères'],
    ['en', '1,500 / 1,500 characters'],
  ])('writes the description counter in %s', async (locale, shown) => {
    const w = await openPortalForm(locale)
    const field = w.findAll('textarea')[0]
    await field.setValue('x'.repeat(1500))
    expect(w.find(`[id="${field.attributes('aria-describedby')}"]`).text()).toBe(shown)
  })

  it.each([
    ['fr', 'Signalement trop long : raccourcissez un champ.', '2\u202f414 / 1\u202f990 caractères'],
    ['en', 'Report too long: shorten a field.', '2,414 / 1,990 characters'],
  ])('announces the oversized report in %s', async (locale, warning, total) => {
    const w = await openPortalForm(locale)
    expect(w.find('[role="alert"]').exists()).toBe(false)

    await w.find('input[type="text"]').setValue('Sample title')
    const [description, reproduction] = w.findAll('textarea')
    await description.setValue('x'.repeat(1500))
    await reproduction.setValue('x'.repeat(500))

    // 194 + 208 for the block and its author, then 12 + 1500 + 500 typed: 2414.
    const over = w.find('.fbk-budget.over')
    expect(over.find('[role="alert"]').text()).toBe(warning)
    expect(over.text()).toBe(`${warning} ${total}`)
  })
})
