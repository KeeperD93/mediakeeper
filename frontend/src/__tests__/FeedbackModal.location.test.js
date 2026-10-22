/**
 * Report form (FeedbackModal): the affected page follows the admin page unless
 * a report is in progress (text typed or page/tab picked by hand), and the
 * "current page" shortcut.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const h = vi.hoisted(() => ({ apiPost: vi.fn(), showToast: vi.fn(), push: vi.fn() }))
const routeName = ref('stats')
const routeTab = ref('users')

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
vi.mock('vue-router', () => ({
  useRoute: () => ({
    get name() {
      return routeName.value
    },
    get query() {
      return routeTab.value === undefined ? {} : { tab: routeTab.value }
    },
  }),
  useRouter: () => ({ push: h.push }),
}))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: h.showToast }) }))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiPost: h.apiPost }),
  resolveApiError: code => `error:${code}`,
}))

import FeedbackModal from '@/components/feedback/FeedbackModal.vue'

let wrapper

async function openModal(props = {}) {
  wrapper = mount(FeedbackModal, { props: { open: false, ...props }, attachTo: document.body })
  // The pre-fill watch is not immediate: it runs on the closed → open change.
  await wrapper.setProps({ open: true })
  return wrapper
}

async function reopen(w) {
  await w.setProps({ open: false })
  await w.setProps({ open: true })
}

function navigate(name, tab) {
  routeName.value = name
  routeTab.value = tab
}

const selects = w => w.findAll('select')
const formLocation = w => {
  const [page, tab] = selects(w)
  return { page: page.element.value, tab: tab?.element.value }
}
const shortcut = w => w.find('.fbk-here')
const titleInput = w => w.find('input[type="text"]')

async function fillRequired(w) {
  await titleInput(w).setValue('Sample title')
  await w.find('textarea').setValue('Sample description')
}

async function send(w) {
  await w.find('form').trigger('submit')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  navigate('stats', 'users')
})

afterEach(() => wrapper?.unmount())

describe('FeedbackModal — location', () => {
  it('fills the page and the tab the admin is on', async () => {
    expect(formLocation(await openModal())).toEqual({ page: 'stats', tab: 'users' })
  })

  it('takes the tab the page shows when the address names none', async () => {
    navigate('stats', undefined)
    expect(formLocation(await openModal())).toEqual({ page: 'stats', tab: 'general' })
  })

  it('leaves the location empty on a page outside the list', async () => {
    navigate('portal-home', undefined)
    expect(selects(await openModal())[0].element.value).toBe('')
  })

  it('follows the current page on reopening when no report was started', async () => {
    const w = await openModal()
    navigate('logs', 'config')
    await reopen(w)
    expect(formLocation(w)).toEqual({ page: 'logs', tab: 'config' })
  })

  it('takes the current page after a report was sent', async () => {
    h.apiPost.mockResolvedValueOnce({ ok: true })
    navigate('stats', 'general')
    const w = await openModal()
    await fillRequired(w)
    await send(w)
    navigate('stats', 'users')
    await reopen(w)
    expect(formLocation(w)).toEqual({ page: 'stats', tab: 'users' })
  })

  it('keeps a started report, location included, when closed and reopened', async () => {
    const w = await openModal()
    await fillRequired(w)
    navigate('logs', 'config')
    await reopen(w)

    expect(titleInput(w).element.value).toBe('Sample title')
    expect(formLocation(w)).toEqual({ page: 'stats', tab: 'users' })
  })

  it.each([
    ['title', w => titleInput(w)],
    ['description', w => w.findAll('textarea')[0]],
    ['reproduction', w => w.findAll('textarea')[1]],
  ])('keeps the location when only the %s is typed', async (_, field) => {
    const w = await openModal()
    await field(w).setValue('Sample text')
    navigate('logs', 'config')
    await reopen(w)
    expect(formLocation(w)).toEqual({ page: 'stats', tab: 'users' })
  })

  it('follows the current page when the title holds only spaces', async () => {
    const w = await openModal()
    await titleInput(w).setValue('   ')
    navigate('logs', 'config')
    await reopen(w)
    expect(formLocation(w)).toEqual({ page: 'logs', tab: 'config' })
  })

  it('keeps a page picked by hand when closed and reopened', async () => {
    const w = await openModal()
    await selects(w)[0].setValue('logs')
    navigate('health', undefined)
    await reopen(w)
    expect(formLocation(w)).toEqual({ page: 'logs', tab: '' })
  })

  it('keeps a tab picked by hand when closed and reopened', async () => {
    const w = await openModal()
    await selects(w)[1].setValue('tools')
    navigate('logs', 'config')
    await reopen(w)
    expect(formLocation(w)).toEqual({ page: 'stats', tab: 'tools' })
  })

  it('releases a page picked by hand once the report is sent', async () => {
    h.apiPost.mockResolvedValueOnce({ ok: true })
    const w = await openModal()
    await selects(w)[0].setValue('logs')
    await fillRequired(w)
    await send(w)
    navigate('health', 'config')
    await reopen(w)
    expect(formLocation(w)).toEqual({ page: 'health', tab: 'config' })
  })

  it('releases a page picked by hand on reset', async () => {
    const w = await openModal()
    await selects(w)[0].setValue('logs')
    await w.find('.fbk-btn--reset').trigger('click')
    navigate('health', 'config')
    await reopen(w)
    expect(formLocation(w)).toEqual({ page: 'health', tab: 'config' })
  })

  it('clears the tab when another page is picked', async () => {
    navigate('logs', 'config')
    const w = await openModal()
    await selects(w)[0].setValue('settings') // Settings also has a "config" tab
    expect(formLocation(w)).toEqual({ page: 'settings', tab: '' })
  })

  it('shows no location fields on the portal', async () => {
    const w = await openModal({ showLocation: false, endpoint: '/api/portal/feedback' })
    expect(selects(w)).toHaveLength(1) // resolution only
  })
})

describe('FeedbackModal — "current page" shortcut', () => {
  async function draftOnStatsThenLogs() {
    const w = await openModal()
    await fillRequired(w)
    navigate('logs', 'config')
    await reopen(w)
    return w
  }

  it('is hidden while the form shows the current page', async () => {
    expect(shortcut(await openModal()).exists()).toBe(false)
  })

  it('fills in the current page and keeps the typed text', async () => {
    const w = await draftOnStatsThenLogs()
    await shortcut(w).trigger('click')
    expect(formLocation(w)).toEqual({ page: 'logs', tab: 'config' })
    expect(shortcut(w).exists()).toBe(false)
    expect(titleInput(w).element.value).toBe('Sample title')
  })

  it('moves keyboard focus to the page menu it filled', async () => {
    const w = await draftOnStatsThenLogs()
    shortcut(w).element.focus()
    await shortcut(w).trigger('click')
    expect(document.activeElement).toBe(selects(w)[0].element)
  })

  it('leaves focus alone after a tap, which would open the menu on iOS', async () => {
    const w = await draftOnStatsThenLogs()
    await shortcut(w).trigger('click')
    expect(document.activeElement).not.toBe(selects(w)[0].element)
  })

  it('is offered when only the tab differs', async () => {
    navigate('stats', 'general')
    const w = await openModal()
    await fillRequired(w)
    navigate('stats', 'charts')
    await reopen(w)
    await shortcut(w).trigger('click')
    expect(formLocation(w)).toEqual({ page: 'stats', tab: 'charts' })
  })

  it('appears when the page changes while the window stays open, without moving the form', async () => {
    const w = await openModal()
    navigate('logs', 'config')
    await flushPromises()
    expect(shortcut(w).exists()).toBe(true)
    expect(formLocation(w)).toEqual({ page: 'stats', tab: 'users' })
  })

  it('releases a page picked by hand', async () => {
    const w = await openModal()
    await selects(w)[0].setValue('logs')
    navigate('health', 'config')
    await flushPromises()
    await shortcut(w).trigger('click')
    navigate('stats', 'charts')
    await reopen(w)
    expect(formLocation(w)).toEqual({ page: 'stats', tab: 'charts' })
  })

  it('is not offered on a page outside the list', async () => {
    const w = await openModal()
    await fillRequired(w)
    navigate('portal-home', undefined)
    await reopen(w)
    expect(shortcut(w).exists()).toBe(false)
  })

  it('is never offered on the portal', async () => {
    const w = await openModal({ showLocation: false, endpoint: '/api/portal/feedback' })
    await fillRequired(w)
    navigate('logs', 'config')
    await reopen(w)
    expect(shortcut(w).exists()).toBe(false)
  })
})
