/**
 * Feedback moderation page when a call fails: a clear message, a retry for
 * the list, and a slower load from another tab that changes nothing.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { TOAST_TYPE } from '@/constants/toast'

const h = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  showToast: vi.fn(),
}))

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))
vi.mock('@/i18n', () => ({ getLocale: () => 'en' }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ showToast: h.showToast }) }))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet: h.apiGet, apiPatch: h.apiPatch, apiPost: h.apiPost }),
  resolveApiError: (code, fallbackKey) => `error:${code}|${fallbackKey}`,
}))

import FeedbackModerationView from '@/views/FeedbackModerationView.vue'

const report = (over = {}) => ({
  id: 1,
  type: 'bug',
  title: 'Sample title',
  description: 'Sample description',
  reproduction: '',
  resolution: '',
  platform: 'both',
  tags: [],
  zone: '',
  module: '',
  tab: '',
  reporter_name: 'Sample user',
  anonymous: false,
  created_at: '2026-01-02T03:04:05Z',
  ...over,
})

let wrapper
// Each failure is logged: keep the expected ones out of the test output.
let consoleError

async function mountWith(items) {
  h.apiGet.mockResolvedValue({ items })
  wrapper = mount(FeedbackModerationView)
  await flushPromises()
  return wrapper
}

const cards = w => w.findAll('.fbm-card')
const button = (el, key) => el.findAll('button').find(b => b.text() === key)

beforeEach(() => {
  vi.clearAllMocks()
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
})
afterEach(() => {
  wrapper?.unmount()
  consoleError.mockRestore()
})

describe('FeedbackModerationView — errors', () => {
  it('offers a retry when the list fails to load, not an empty queue', async () => {
    h.apiGet.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const w = await mountWith([report()])

    expect(h.showToast).toHaveBeenCalledWith(
      'error:Failed to fetch|common.apiError.loadFailed',
      TOAST_TYPE.ERR,
    )
    expect(consoleError).toHaveBeenCalledWith('[useFeedbackModeration.load]', expect.any(TypeError))
    expect(w.find('.fbm-error').text()).toBe('feedback.moderation.loadError')
    expect(w.text()).not.toContain('feedback.moderation.empty')

    await button(w, 'feedback.moderation.retry').trigger('click')
    await flushPromises()
    expect(cards(w)).toHaveLength(1)
    expect(w.find('.fbm-error').exists()).toBe(false)
  })

  it('ignores a failure of the previous tab once another tab is loading', async () => {
    let failPending, answerRejected
    h.apiGet
      .mockReturnValueOnce(new Promise((_, reject) => (failPending = reject)))
      .mockReturnValueOnce(new Promise(resolve => (answerRejected = resolve)))
    wrapper = mount(FeedbackModerationView)
    await button(wrapper, 'feedback.moderation.tabRejected').trigger('click')

    failPending(new TypeError('Failed to fetch'))
    await flushPromises()
    expect(wrapper.find('.fbm-empty').text()).toBe('common.loading')

    answerRejected({ items: [report()] })
    await flushPromises()
    expect(cards(wrapper)).toHaveLength(1)
    expect(wrapper.find('.fbm-error').exists()).toBe(false)
    expect(h.showToast).not.toHaveBeenCalled()
  })

  it('drops the stale count when the reload after a save fails', async () => {
    h.apiPatch.mockResolvedValue({ ok: true })
    const w = await mountWith([report(), report({ id: 2 })])
    expect(w.find('.fbm-badge').text()).toBe('2')
    await button(cards(w)[0], 'feedback.moderation.edit').trigger('click')
    h.apiGet.mockRejectedValueOnce(new Error('http_500'))

    await w.find('form').trigger('submit')
    await flushPromises()

    expect(w.find('.fbm-error').exists()).toBe(true)
    expect(w.find('.fbm-badge').exists()).toBe(false)
  })

  it.each([
    ['validate', 'feedback.moderation.validate', 'common.apiError.submitFailed'],
    ['reject', 'feedback.moderation.reject', 'common.apiError.saveFailed'],
  ])('names a failed %s and keeps the report', async (action, label, fallbackKey) => {
    h.apiPost.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const w = await mountWith([report()])
    await button(cards(w)[0], label).trigger('click')
    await flushPromises()

    expect(h.showToast).toHaveBeenCalledWith(`error:Failed to fetch|${fallbackKey}`, TOAST_TYPE.ERR)
    expect(consoleError).toHaveBeenCalledWith(
      `[useFeedbackModeration.${action}]`,
      expect.any(TypeError),
    )
    expect(cards(w)).toHaveLength(1)
    expect(
      cards(w)[0]
        .findAll('.fbm-actions button')
        .some(b => b.element.disabled),
    ).toBe(false)
  })

  it('names a failed save and keeps the form open', async () => {
    h.apiPatch.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const w = await mountWith([report()])
    await button(cards(w)[0], 'feedback.moderation.edit').trigger('click')
    await w.find('form').trigger('submit')
    await flushPromises()

    expect(h.showToast).toHaveBeenCalledWith(
      'error:Failed to fetch|common.apiError.saveFailed',
      TOAST_TYPE.ERR,
    )
    expect(consoleError).toHaveBeenCalledWith('[useFeedbackModeration.save]', expect.any(TypeError))
    expect(w.find('form').exists()).toBe(true)
  })
})
