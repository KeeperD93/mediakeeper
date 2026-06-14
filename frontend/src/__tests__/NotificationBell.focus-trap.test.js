/**
 * Covers useFocusTrap wired into the notification bell popup: opening moves
 * focus into the dialog and Escape closes it; plus the read-timing contract —
 * the badge clears on open while the server "read-all" is deferred to close.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const apiGet = vi.fn()
const apiPost = vi.fn()

vi.mock('vue-i18n', async importOriginal => ({
  ...(await importOriginal()),
  useI18n: () => ({ t: key => key }),
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ apiGet, apiPost }) }))
vi.mock('@/utils/portal/notificationLabel', () => ({
  iconComponentForNotification: () => ({ name: 'IconStub', template: '<i />' }),
  labelForNotification: () => 'label',
  timeAgoForNotification: () => 'now',
}))

import NotificationBell from '@/components/portal/NotificationBell.vue'

const READ_ALL = '/api/portal/notifications/read-all'

function buildBell() {
  return mount(NotificationBell, {
    attachTo: document.body,
    global: {
      stubs: { EventDetailModal: true, PortalLoadMore: true },
      mocks: { $t: key => key },
    },
  })
}

beforeEach(() => {
  apiGet.mockReset().mockResolvedValue({ items: [], unread: 0, has_more: false, next_cursor: null })
  apiPost.mockReset().mockResolvedValue({})
})

describe('NotificationBell — focus trap + read timing', () => {
  it('opens a labelled dialog, traps focus on the panel, and closes on Escape', async () => {
    const w = buildBell()
    await flushPromises()

    await w.get('.pt-bell').trigger('click')
    await flushPromises()

    const panel = document.querySelector('.pt-bell-popup[role="dialog"][aria-modal="true"]')
    expect(panel).toBeTruthy()
    expect(document.activeElement).toBe(panel)

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()
    expect(document.querySelector('.pt-bell-popup')).toBeFalsy()

    w.unmount()
  })

  it('defers the server read-all from open to close', async () => {
    apiGet.mockResolvedValue({
      items: [{ id: 1, read: false, type: 'generic', created_at: '2026-01-01T00:00:00Z' }],
      unread: 1,
      has_more: false,
      next_cursor: null,
    })
    const w = buildBell()
    await flushPromises()

    await w.get('.pt-bell').trigger('click')
    await flushPromises()
    expect(apiPost).not.toHaveBeenCalledWith(READ_ALL)

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()
    expect(apiPost).toHaveBeenCalledWith(READ_ALL)

    w.unmount()
  })

  it('wraps Tab from the last item back to the first', async () => {
    apiGet.mockResolvedValue({
      items: [
        { id: 1, read: false, type: 'generic', created_at: '2026-01-01T00:00:00Z' },
        { id: 2, read: false, type: 'generic', created_at: '2026-01-01T00:00:00Z' },
      ],
      unread: 2,
      has_more: false,
      next_cursor: null,
    })
    const w = buildBell()
    await flushPromises()
    await w.get('.pt-bell').trigger('click')
    await flushPromises()

    const items = document.querySelectorAll('.pt-bell-item')
    expect(items.length).toBe(2)
    items[items.length - 1].focus()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }))
    expect(document.activeElement).toBe(items[0])

    w.unmount()
  })

  it('restores focus to the bell trigger after Escape', async () => {
    const w = buildBell()
    await flushPromises()
    const trigger = w.get('.pt-bell').element
    trigger.focus()

    await w.get('.pt-bell').trigger('click')
    await flushPromises()
    expect(document.activeElement).not.toBe(trigger) // focus moved into the dialog

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()
    expect(document.activeElement).toBe(trigger)

    w.unmount()
  })

  it('commits read-all on unmount while the panel is still open', async () => {
    apiGet.mockResolvedValue({
      items: [{ id: 1, read: false, type: 'generic', created_at: '2026-01-01T00:00:00Z' }],
      unread: 1,
      has_more: false,
      next_cursor: null,
    })
    const w = buildBell()
    await flushPromises()
    await w.get('.pt-bell').trigger('click')
    await flushPromises()
    apiPost.mockClear()

    w.unmount() // no close() fired — e.g. logout / programmatic navigation
    await flushPromises()
    expect(apiPost).toHaveBeenCalledWith(READ_ALL)
  })
})
