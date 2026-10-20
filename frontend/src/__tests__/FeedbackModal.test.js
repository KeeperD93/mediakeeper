/**
 * Report form (FeedbackModal): menus, resolution pre-fill, the payload it
 * sends, a failed send, and the reset button. The affected page and its
 * shortcut are in FeedbackModal.location.test.js.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { FEEDBACK_MAX } from '@/constants/feedback'
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
  resolveApiError: (code, fallbackKey) => `error:${code}|${fallbackKey}`,
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

function navigate(name, tab) {
  routeName.value = name
  routeTab.value = tab
}

const selects = w => w.findAll('select')
const formLocation = w => {
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

describe('FeedbackModal — menus', () => {
  it('give every menu the shared arrow', async () => {
    const menus = selects(await openModal())
    expect(menus).toHaveLength(3) // page, tab, resolution
    for (const menu of menus) expect(menu.classes()).toContain('mk-select-chevron')
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
  // A failed send logs its error: keep the expected ones out of the test output.
  let consoleError
  beforeEach(() => {
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
  })
  afterEach(() => consoleError.mockRestore())

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

  it('sends the chosen type, platform, tags and anonymity', async () => {
    h.apiPost.mockResolvedValueOnce({ ok: true })
    const w = await openModal()
    await w.findAll('.fbk-seg-btn')[1].trigger('click') // suggestion
    const [platformChips, tagChips] = w.findAll('.fbk-chips')
    await platformChips.findAll('.fbk-chip')[0].trigger('click') // desktop
    const tags = tagChips.findAll('.fbk-chip')
    await tags[0].trigger('click')
    await tags[1].trigger('click')
    await tags[1].trigger('click') // second tag off again
    await w.find('input[type="checkbox"]').setValue(true)
    await fillRequired(w)
    await send(w)

    expect(h.apiPost).toHaveBeenCalledWith(
      '/api/feedback',
      expect.objectContaining({
        type: 'suggestion',
        platform: 'desktop',
        tags: ['urgent'],
        anonymous: true,
      }),
    )
  })

  it('counts the report against the Discord budget and blocks an oversized one', async () => {
    const w = await openModal()
    const budget = () => w.find('.fbk-budget')
    // Fixed block (170) + zone and module of Statistiques + the tab label (t() returns
    // keys in these tests, so "stats.users"); no resolution under jsdom.
    expect(budget().text()).toContain('"used":224')
    await w.findAll('.fbk-chips')[1].find('.fbk-chip').trigger('click')
    expect(budget().text()).toContain('"used":230')

    await titleInput(w).setValue('Sample title')
    await w.findAll('textarea')[0].setValue('x'.repeat(FEEDBACK_MAX.description))
    await w.findAll('textarea')[1].setValue('x'.repeat(FEEDBACK_MAX.reproduction))
    expect(budget().classes()).toContain('over')
    expect(w.find('button[type="submit"]').attributes('disabled')).toBeDefined()
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

    expect(h.showToast).toHaveBeenCalledWith(
      'error:send_failed|common.apiError.submitFailed',
      TOAST_TYPE.ERR,
    )
    expect(w.emitted('close')).toBeUndefined()
    expect(titleInput(w).element.value).toBe('Sample title')
  })

  it('names a failed send that got no answer and logs it', async () => {
    h.apiPost.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const w = await openModal()
    await fillRequired(w)
    await send(w)

    expect(h.showToast).toHaveBeenCalledWith(
      'error:Failed to fetch|common.apiError.submitFailed',
      TOAST_TYPE.ERR,
    )
    expect(consoleError).toHaveBeenCalledWith('[useFeedbackForm.submit]', expect.any(TypeError))
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
    expect(formLocation(w)).toEqual({ page: 'logs', tab: 'config' })
  })
})
