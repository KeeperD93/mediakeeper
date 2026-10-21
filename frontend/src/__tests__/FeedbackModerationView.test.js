/**
 * Feedback moderation page: the list per tab, the validate / reject actions
 * and the inline edit form. Failures are in FeedbackModerationView.errors.test.js.
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
// One translated key, to tell a known tag from an unknown one; others echo.
const MESSAGES = { 'feedback.tags.urgent': 'Urgent' }

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (k, p) => MESSAGES[k] ?? (p ? `${k}:${p.name}` : k) }),
}))
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
  reproduction: 'Sample steps',
  resolution: '1920x1080',
  platform: 'both',
  tags: ['urgent', 'sample_tag'],
  zone: 'Sample zone',
  module: 'Sample module',
  tab: 'Sample tab',
  reporter_name: 'Sample user',
  anonymous: false,
  created_at: '2026-01-02T03:04:05Z',
  ...over,
})

let wrapper

async function mountWith(items) {
  h.apiGet.mockResolvedValue({ items })
  wrapper = mount(FeedbackModerationView)
  await flushPromises()
  return wrapper
}

const cards = w => w.findAll('.fbm-card')
const button = (el, key) => el.findAll('button').find(b => b.text() === key)
const chip = (el, key) => el.findAll('.fbm-chip').find(b => b.text() === key)
// The box under a field's label (the i18n mock echoes the key).
const field = (el, key) =>
  el
    .findAll('label')
    .find(l => l.find('span').text() === key)
    .find('input, textarea')

beforeEach(() => vi.clearAllMocks())
afterEach(() => wrapper?.unmount())

describe('FeedbackModerationView — list', () => {
  it('loads the pending reports and shows each one', async () => {
    const w = await mountWith([report(), report({ id: 2, title: 'Other title' })])

    expect(h.apiGet).toHaveBeenCalledWith('/api/feedback/reports?status=pending')
    expect(cards(w)).toHaveLength(2)
    const card = cards(w)[0]
    expect(card.find('.fbm-title').text()).toBe('Sample title')
    expect(card.find('.fbm-type').classes()).toContain('fbm-type--bug')
    expect(card.find('.fbm-meta').text()).toBe(
      'feedback.moderation.by:Sample user · feedback.moderation.platformBoth · 1920x1080',
    )
    expect(card.find('.fbm-loc').text()).toBe('Sample zone · Sample module · Sample tab')
    expect(card.find('.fbm-repro').text()).toContain('Sample steps')
    expect(card.find('time').attributes('datetime')).toBe('2026-01-02T03:04:05Z')
    // A known tag is translated, an unknown one shows as sent.
    expect(card.findAll('.fbm-tag').map(t => t.text())).toEqual(['Urgent', 'sample_tag'])
    expect(w.find('.fbm-badge').text()).toBe('2')
  })

  it('names neither the reporter of an anonymous report nor an empty location', async () => {
    const w = await mountWith([report({ anonymous: true, zone: '', module: '', tab: '' })])

    expect(w.find('.fbm-meta').text()).toMatch(/^feedback\.moderation\.anonymous · /)
    expect(w.find('.fbm-loc').exists()).toBe(false)
  })

  it('leaves out empty steps and a missing platform', async () => {
    const w = await mountWith([report({ reproduction: null, platform: null, resolution: null })])

    expect(w.find('.fbm-meta').text()).toBe('feedback.moderation.by:Sample user')
    expect(w.find('.fbm-repro').exists()).toBe(false)
  })

  it('shows the empty message of each tab', async () => {
    const w = await mountWith([])
    expect(w.find('.fbm-empty').text()).toBe('feedback.moderation.empty')

    await button(w, 'feedback.moderation.tabRejected').trigger('click')
    await flushPromises()
    expect(w.find('.fbm-empty').text()).toBe('feedback.moderation.emptyRejected')
  })

  it('lists rejected reports without moderation buttons', async () => {
    const w = await mountWith([report()])
    await button(w, 'feedback.moderation.tabRejected').trigger('click')
    await flushPromises()

    expect(h.apiGet).toHaveBeenLastCalledWith('/api/feedback/reports?status=rejected')
    expect(cards(w)).toHaveLength(1)
    expect(w.find('.fbm-actions').exists()).toBe(false)
    expect(w.find('.fbm-badge').exists()).toBe(false)
  })

  it('keeps the tab on screen when the previous tab answers late', async () => {
    let answerPending
    h.apiGet
      .mockReturnValueOnce(new Promise(resolve => (answerPending = resolve)))
      .mockResolvedValueOnce({ items: [] })
    wrapper = mount(FeedbackModerationView)
    await button(wrapper, 'feedback.moderation.tabRejected').trigger('click')
    await flushPromises()

    answerPending({ items: [report()] })
    await flushPromises()
    expect(cards(wrapper)).toHaveLength(0)
    expect(wrapper.find('.fbm-empty').text()).toBe('feedback.moderation.emptyRejected')
  })
})

describe('FeedbackModerationView — actions', () => {
  it.each([
    ['validate', 'feedback.moderation.validate', 'feedback.moderation.validated'],
    ['reject', 'feedback.moderation.reject', 'feedback.moderation.rejected'],
  ])('%s takes the report off the list and confirms', async (action, label, toastKey) => {
    h.apiPost.mockResolvedValue({ ok: true })
    const w = await mountWith([report(), report({ id: 2 })])

    await button(cards(w)[0], label).trigger('click')
    await flushPromises()

    expect(h.apiPost).toHaveBeenCalledWith(`/api/feedback/reports/1/${action}`)
    expect(cards(w)).toHaveLength(1)
    expect(h.showToast).toHaveBeenCalledWith(toastKey, TOAST_TYPE.OK)
  })

  it('locks only the report whose action is running', async () => {
    let finish
    h.apiPost.mockReturnValue(new Promise(resolve => (finish = resolve)))
    const w = await mountWith([report(), report({ id: 2 })])

    await button(cards(w)[0], 'feedback.moderation.validate').trigger('click')
    const disabled = card => card.findAll('.fbm-actions button').map(b => b.element.disabled)
    expect(disabled(cards(w)[0])).toEqual([true, true, true])
    expect(disabled(cards(w)[1])).toEqual([false, false, false])

    finish({ ok: true })
    await flushPromises()
  })
})

describe('FeedbackModerationView — edit', () => {
  async function openEdit(over) {
    const w = await mountWith([report(over), report({ id: 2 })])
    await button(cards(w)[0], 'feedback.moderation.edit').trigger('click')
    return w
  }

  it("opens the form in place of the report, filled with the report's values", async () => {
    const w = await openEdit()
    const card = cards(w)[0]

    expect(card.find('form').exists()).toBe(true)
    expect(card.find('.fbm-desc').exists()).toBe(false)
    expect(cards(w)[1].find('form').exists()).toBe(false)
    expect(field(card, 'feedback.modal.titleField').element.value).toBe('Sample title')
    expect(field(card, 'feedback.modal.descField').element.value).toBe('Sample description')
    expect(field(card, 'feedback.modal.reproField').element.value).toBe('Sample steps')
    expect(field(card, 'feedback.modal.resolution').element.value).toBe('1920x1080')
    expect(chip(card, 'feedback.modal.type_bug').attributes('aria-pressed')).toBe('true')
    // "both" fills the two platform chips.
    expect(chip(card, 'feedback.modal.platform_desktop').attributes('aria-pressed')).toBe('true')
    expect(chip(card, 'feedback.modal.platform_mobile').attributes('aria-pressed')).toBe('true')
    expect(chip(card, 'feedback.tags.crash').attributes('aria-pressed')).toBe('false')
  })

  it('cannot save without a title', async () => {
    const w = await openEdit()
    await field(w, 'feedback.modal.titleField').setValue('   ')

    expect(w.find('form button[type="submit"]').element.disabled).toBe(true)
  })

  it('saves the trimmed draft, then reloads the list', async () => {
    h.apiPatch.mockResolvedValue({ ok: true })
    const w = await openEdit()
    const card = cards(w)[0]
    await chip(card, 'feedback.modal.type_suggestion').trigger('click')
    await field(card, 'feedback.modal.titleField').setValue('  New title  ')
    await field(card, 'feedback.modal.descField').setValue('  New description  ')
    await field(card, 'feedback.modal.reproField').setValue('  New steps  ')
    await field(card, 'feedback.modal.resolution').setValue('  1280x720  ')
    await chip(card, 'feedback.modal.platform_mobile').trigger('click')
    await chip(card, 'feedback.tags.crash').trigger('click')
    h.apiGet.mockClear()

    await card.find('form').trigger('submit')
    await flushPromises()

    expect(h.apiPatch).toHaveBeenCalledWith('/api/feedback/reports/1', {
      type: 'suggestion',
      title: 'New title',
      description: 'New description',
      reproduction: 'New steps',
      resolution: '1280x720',
      platform: 'desktop',
      tags: ['urgent', 'sample_tag', 'crash'],
    })
    expect(h.showToast).toHaveBeenCalledWith('feedback.moderation.saved', TOAST_TYPE.OK)
    expect(h.apiGet).toHaveBeenCalledWith('/api/feedback/reports?status=pending')
    expect(w.find('form').exists()).toBe(false)
  })

  it.each([
    ['both chips on', 'both', []],
    ['both chips off', 'mobile', ['feedback.modal.platform_mobile']],
  ])('saves "both" with %s', async (_, platform, clicks) => {
    h.apiPatch.mockResolvedValue({ ok: true })
    const w = await openEdit({ platform })
    const card = cards(w)[0]
    for (const label of clicks) await chip(card, label).trigger('click')

    await card.find('form').trigger('submit')
    await flushPromises()

    expect(h.apiPatch.mock.calls[0][1].platform).toBe('both')
  })

  it.each([
    ['desktop', 'true', 'false'],
    ['mobile', 'false', 'true'],
  ])('keeps a %s-only report on its platform', async (platform, desktopOn, mobileOn) => {
    h.apiPatch.mockResolvedValue({ ok: true })
    const w = await openEdit({ platform })
    const card = cards(w)[0]
    expect(chip(card, 'feedback.modal.platform_desktop').attributes('aria-pressed')).toBe(desktopOn)
    expect(chip(card, 'feedback.modal.platform_mobile').attributes('aria-pressed')).toBe(mobileOn)

    await card.find('form').trigger('submit')
    await flushPromises()

    expect(h.apiPatch.mock.calls[0][1].platform).toBe(platform)
  })

  it('locks the form while the save runs', async () => {
    let finish
    h.apiPatch.mockReturnValue(new Promise(resolve => (finish = resolve)))
    const w = await openEdit()

    await w.find('form').trigger('submit')
    expect(w.findAll('form .fbm-actions button').map(b => b.element.disabled)).toEqual([true, true])

    finish({ ok: true })
    await flushPromises()
  })

  it('goes back to the report on cancel, without saving', async () => {
    const w = await openEdit()
    await button(cards(w)[0], 'feedback.moderation.cancel').trigger('click')

    expect(w.find('form').exists()).toBe(false)
    expect(cards(w)[0].find('.fbm-desc').text()).toBe('Sample description')
    expect(h.apiPatch).not.toHaveBeenCalled()
  })
})
