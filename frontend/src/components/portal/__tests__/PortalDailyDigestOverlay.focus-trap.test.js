/**
 * Daily digest window and the keyboard: the focus starts on the close button, Tab and
 * Shift+Tab loop inside the window, and closing it gives the focus back to the page.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick, ref } from 'vue'

import PortalDailyDigestOverlay from '@/components/portal/PortalDailyDigestOverlay.vue'

const apiGet = vi.fn()

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ locale: ref('fr'), t: key => key }),
}))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet, apiPost: vi.fn().mockResolvedValue({}), apiPut: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: vi.fn() }) }))

const DIGEST = {
  date: '2026-11-13',
  empty: false,
  me: { display_name: 'Alice', avatar_url: null, avatar_effect: null, tier: 'gold' },
  level: {
    level: 12,
    xp: 340,
    xp_current_level: 300,
    xp_next_level: 500,
    xp_into_level: 40,
    percent: 68,
    maxed: false,
    title_key: 'regular',
    tier: 'gold',
    xp_yesterday: 0,
  },
  recent_adds: [],
  events: [],
  ranking: { position: 0, total: 0, movement: 0, top3: [] },
  quota: { used: 0, max_allowed: 0, unlimited: true, remaining: -1 },
  tickets_open: 0,
  streak: 0,
  next_achievement: null,
  expiry: null,
  news: [],
  for_you: [],
}

let wrapper
let opener

const press = (key, shiftKey = false) =>
  document.dispatchEvent(new KeyboardEvent('keydown', { key, shiftKey, bubbles: true }))

async function open() {
  apiGet.mockResolvedValue({ dismissed: false, compact: false, digest: DIGEST })
  wrapper = mount(PortalDailyDigestOverlay, { attachTo: document.body })
  await flushPromises()
  await nextTick()
}

describe('PortalDailyDigestOverlay.vue, focus trap', () => {
  beforeEach(() => {
    opener = document.createElement('button')
    opener.textContent = 'Open'
    document.body.append(opener)
    opener.focus()
  })
  afterEach(() => {
    wrapper?.unmount()
    opener.remove()
  })

  it('starts on the close button, inside a dialog named by its title', async () => {
    await open()
    const panel = wrapper.find('[role="dialog"]')
    expect(document.activeElement).toBe(wrapper.find('.dd-close').element)
    expect(panel.attributes('aria-modal')).toBe('true')
    const title = document.getElementById(panel.attributes('aria-labelledby'))
    expect(title.textContent).toBe('portal.dailyDigest.title')
  })

  it('loops from the last control back to the first with Tab', async () => {
    await open()
    wrapper.find('.dd-cta').element.focus()

    press('Tab')

    expect(document.activeElement).toBe(wrapper.find('.dd-switch').element)
  })

  it('loops from the first control to the last with Shift+Tab', async () => {
    await open()
    wrapper.find('.dd-switch').element.focus()

    press('Tab', true)

    expect(document.activeElement).toBe(wrapper.find('.dd-cta').element)
  })

  it('gives the focus back to what had it once the window closes', async () => {
    await open()
    expect(document.activeElement).not.toBe(opener)

    await wrapper.find('.dd-close').trigger('click')
    await nextTick()

    expect(document.activeElement).toBe(opener)
  })
})
