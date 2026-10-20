/**
 * Report form (FeedbackModal): location pre-filled from the admin page, the
 * resolution pre-fill, the payload it sends, a failed send, and the reset button.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { TOAST_TYPE } from '@/constants/toast'

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

const ADMIN_ZONE = 'Tableau de bord (admin général)'
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
const location = w => {
  const [page, tab] = selects(w)
  return { page: page.element.value, tab: tab?.element.value }
}
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

afterEach(() => {
  wrapper?.unmount()
  vi.unstubAllGlobals()
})

describe('FeedbackModal — location', () => {
  it('fills the page and the tab the admin is on', async () => {
    expect(location(await openModal())).toEqual({ page: 'stats', tab: 'users' })
  })

  it('leaves the location empty on a page outside the list', async () => {
    navigate('portal-home', undefined)
    expect(selects(await openModal())[0].element.value).toBe('')
  })

  it('keeps a started report, location included, when closed and reopened', async () => {
    const w = await openModal()
    await fillRequired(w)
    navigate('logs', 'config')
    await reopen(w)

    expect(titleInput(w).element.value).toBe('Sample title')
    expect(location(w)).toEqual({ page: 'stats', tab: 'users' })
  })

  it('shows no location fields on the portal', async () => {
    const w = await openModal({ showLocation: false, endpoint: '/api/portal/feedback' })
    expect(selects(w)).toHaveLength(1) // resolution only
  })
})

describe('FeedbackModal — resolution', () => {
  it('puts an unlisted screen size in the free field and sends it', async () => {
    vi.stubGlobal('screen', { width: 1366, height: 768 })
    h.apiPost.mockResolvedValueOnce({ ok: true })
    const w = await openModal()
    expect(w.findAll('input[type="text"]')[1].element.value).toBe('1366x768')

    await fillRequired(w)
    await send(w)
    expect(h.apiPost).toHaveBeenCalledWith(
      '/api/feedback',
      expect.objectContaining({ resolution: '1366x768' }),
    )
  })

  it('picks a listed screen size in the menu', async () => {
    vi.stubGlobal('screen', { width: 1920, height: 1080 })
    const w = await openModal()
    expect(selects(w).at(-1).element.value).toBe('1920x1080')
    expect(w.findAll('input[type="text"]')).toHaveLength(1) // no free field
  })
})

describe('FeedbackModal — sending', () => {
  it('posts the report with its location, then closes and clears the form', async () => {
    h.apiPost.mockResolvedValueOnce({ ok: true })
    const w = await openModal()
    await fillRequired(w)
    await send(w)

    expect(h.apiPost).toHaveBeenCalledWith('/api/feedback', {
      type: 'bug',
      title: 'Sample title',
      description: 'Sample description',
      reproduction: '',
      zone: ADMIN_ZONE,
      module: 'Statistiques',
      tab: 'stats.users',
      platform: 'both',
      resolution: '',
      tags: [],
      anonymous: false,
    })
    expect(h.showToast).toHaveBeenCalledWith('feedback.modal.sent', TOAST_TYPE.OK)
    expect(w.emitted('close')).toHaveLength(1)
    expect(titleInput(w).element.value).toBe('')
  })

  it('closes while still showing the sent report, so it fades out unchanged', async () => {
    h.apiPost.mockResolvedValueOnce({ ok: true })
    let atClose
    const w = await openModal({
      onClose: () =>
        (atClose = {
          title: titleInput(wrapper).element.value,
          sending: wrapper.find('button[type="submit"]').attributes('disabled') !== undefined,
        }),
    })
    await fillRequired(w)
    await send(w)
    expect(atClose).toEqual({ title: 'Sample title', sending: true })
  })

  it('sends portal reports to the portal endpoint without a location', async () => {
    h.apiPost.mockResolvedValueOnce({ ok: true })
    const w = await openModal({ showLocation: false, endpoint: '/api/portal/feedback' })
    await fillRequired(w)
    await send(w)

    expect(h.apiPost).toHaveBeenCalledWith(
      '/api/portal/feedback',
      expect.objectContaining({ zone: '', module: '', tab: '' }),
    )
  })

  it('keeps the typed report and stays open when the send fails', async () => {
    h.apiPost.mockRejectedValueOnce(new Error('send_failed'))
    const w = await openModal()
    await fillRequired(w)
    await send(w)

    expect(h.showToast).toHaveBeenCalledWith('error:send_failed', TOAST_TYPE.ERR)
    expect(w.emitted('close')).toBeUndefined()
    expect(titleInput(w).element.value).toBe('Sample title')
  })

  it('cannot be sent without a title and a description', async () => {
    const w = await openModal()
    expect(w.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    await fillRequired(w)
    expect(w.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })
})

describe('FeedbackModal — reset', () => {
  it('clears the fields and takes the location of the current page again', async () => {
    const w = await openModal()
    await fillRequired(w)
    navigate('logs', 'config')
    await w.find('.fbk-btn--reset').trigger('click')

    expect(titleInput(w).element.value).toBe('')
    expect(location(w)).toEqual({ page: 'logs', tab: 'config' })
  })
})
