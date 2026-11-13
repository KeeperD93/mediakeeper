/**
 * Daily digest window: when it opens by itself, the « Compact view » switch the account
 * keeps, every way out closing it for the day, and the news it marks as read.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick, ref } from 'vue'

import PortalDailyDigestOverlay from '@/components/portal/PortalDailyDigestOverlay.vue'
import DigestCompact from '@/components/portal/daily-digest/DigestCompact.vue'
import DigestFull from '@/components/portal/daily-digest/DigestFull.vue'

const apiGet = vi.fn()
const apiPost = vi.fn()
const apiPut = vi.fn()
const showToast = vi.fn()

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ locale: ref('fr'), t: key => key }),
}))
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet, apiPost, apiPut }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast }) }))

const DISMISS = '/api/portal/daily-digest/dismiss'

const news = (id, extra = {}) => ({
  id,
  title: `Test news ${id}`,
  content: 'One short paragraph.',
  image_url: null,
  type: 'announcement',
  pinned: false,
  created_at: '2026-11-12T10:00:00Z',
  is_new: false,
  ...extra,
})

const digest = (extra = {}) => ({
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
  ...extra,
})

let wrapper

async function open(payload, props = {}) {
  apiGet.mockResolvedValue({ dismissed: false, compact: false, ...payload })
  wrapper = mount(PortalDailyDigestOverlay, { props })
  await flushPromises()
  return wrapper
}

const postedUrls = () => apiPost.mock.calls.map(([url]) => url)

describe('PortalDailyDigestOverlay.vue', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset().mockResolvedValue({})
    apiPut.mockReset().mockResolvedValue({ compact: true })
    showToast.mockReset()
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        disconnect() {}
      },
    )
  })

  afterEach(() => {
    wrapper?.unmount()
    vi.unstubAllGlobals()
  })

  it('opens by itself in the view the account keeps', async () => {
    await open({ digest: digest() })
    expect(wrapper.findComponent(DigestFull).exists()).toBe(true)
    wrapper.unmount()

    await open({ compact: true, digest: digest() })
    expect(wrapper.findComponent(DigestCompact).exists()).toBe(true)
    expect(wrapper.find('.dd-switch').attributes('aria-checked')).toBe('true')
  })

  it('stays closed on a day it was closed, or with nothing to show', async () => {
    await open({ dismissed: true, digest: digest() })
    expect(wrapper.find('.dd-panel').exists()).toBe(false)
    wrapper.unmount()

    await open({ digest: digest({ empty: true }) })
    expect(wrapper.find('.dd-panel').exists()).toBe(false)
  })

  it('opens on demand from the avatar menu, even after being closed today', async () => {
    await open({ dismissed: true, digest: digest() }, { auto: false })
    expect(apiGet).not.toHaveBeenCalled()

    await wrapper.setProps({ open: true })
    await flushPromises()

    expect(apiGet).toHaveBeenCalledWith('/api/portal/daily-digest?force=true')
    expect(wrapper.findComponent(DigestFull).exists()).toBe(true)
  })

  it('switches the view at once and saves it for the account', async () => {
    await open({ digest: digest() })

    await wrapper.find('.dd-switch').trigger('click')

    expect(wrapper.findComponent(DigestCompact).exists()).toBe(true)
    expect(wrapper.find('.dd-switch').attributes('aria-checked')).toBe('true')
    expect(apiPut).toHaveBeenCalledWith('/api/portal/daily-digest/view', { compact: true })
  })

  it('puts the view back, with a message, when it cannot be saved', async () => {
    apiPut.mockRejectedValue(new Error('http_500'))
    await open({ digest: digest() })

    await wrapper.find('.dd-switch').trigger('click')
    await flushPromises()

    expect(wrapper.findComponent(DigestFull).exists()).toBe(true)
    expect(showToast).toHaveBeenCalledWith('portal.dailyDigest.viewError', 'err')
  })

  it.each([
    ['the button at the bottom', w => w.find('.dd-cta').trigger('click')],
    ['Escape', () => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))],
  ])('closes for the day with %s', async (_, close) => {
    await open({ digest: digest() })

    await close(wrapper)
    await flushPromises()

    expect(postedUrls()).toContain(DISMISS)
    expect(wrapper.emitted('close')).toHaveLength(1)
    expect(wrapper.find('.dd-panel').exists()).toBe(false)
  })

  it('closes for the day when a link inside is followed', async () => {
    const event = {
      id: 3,
      title: 'Test party',
      kind: 'public',
      scheduled_at: '2026-11-20T20:00:00Z',
    }
    await open({ digest: digest({ events: [event] }) })

    await wrapper.find('.dd-ev').trigger('click')

    expect(postedUrls()).toContain(DISMISS)
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('marks read on close a news item it showed whole', async () => {
    await open({ digest: digest({ news: [news(7, { is_new: true })] }) })
    expect(postedUrls()).not.toContain('/api/portal/news/read/7?dismissed=true')

    await wrapper.find('.dd-cta').trigger('click')

    expect(postedUrls()).toContain('/api/portal/news/read/7?dismissed=true')
  })

  it('drops the « New » mark as soon as a news item is opened, and reads it once', async () => {
    await open({ digest: digest({ news: [news(7), news(8, { is_new: true })] }) })
    expect(wrapper.find('.dd-new-mini').exists()).toBe(true)

    await wrapper.find('.dd-more-row').trigger('click')
    await nextTick()

    expect(wrapper.find('.dd-new-mini').exists()).toBe(false)
    expect(postedUrls()).toEqual(['/api/portal/news/read/8?dismissed=true'])

    await wrapper.find('.dd-cta').trigger('click')
    expect(postedUrls().filter(url => url.includes('/news/read/'))).toHaveLength(1)
  })

  it('reads nothing on close that was already read', async () => {
    await open({ digest: digest({ news: [news(7)] }) })

    await wrapper.find('.dd-cta').trigger('click')

    expect(postedUrls()).toEqual([DISMISS])
  })
})
