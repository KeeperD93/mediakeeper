// Floating "+" of the portal on a phone: above the page, under any open window,
// and its chat panel above it.

import { test, expect } from '@playwright/test'
import { jsonResponse } from './_fixtures/api-mocks.js'
import {
  DEFAULT_VIEWER_PROFILE,
  mockAuthenticatedPortal,
  portalTicketsHandlers,
} from './_fixtures/portal-auth-mocks.js'

const stub = (name, match, body) => ({ name, match, handler: jsonResponse(body) })

const CHAT_HANDLERS = [
  stub('chat-unread', url => url.pathname === '/api/portal/chat/unread', { unread: 0 }),
  stub('chat-rooms', url => url.pathname === '/api/portal/chat/rooms', {
    items: [{ id: 1, name: 'General' }],
  }),
  stub('chat-messages', url => /^\/api\/portal\/chat\/rooms\/\d+\/messages$/.test(url.pathname), {
    items: [],
    has_more: false,
    next_cursor: null,
  }),
  stub('chat-mark-read', url => url.pathname === '/api/portal/chat/mark-read', {}),
]

async function openTickets(page, profile = {}) {
  const tracker = await mockAuthenticatedPortal(page, {
    profile: { ...DEFAULT_VIEWER_PROFILE, effective_language: 'en', ...profile },
    pageHandlers: [...portalTicketsHandlers(), ...CHAT_HANDLERS],
  })
  await page.goto('/portal/tickets')
  await expect(page.getByRole('heading', { level: 1, name: 'Issues' })).toBeVisible()
  return tracker
}

// What the screen shows at the centre of an element: the floating cluster,
// the chat panel, an open window, or something else.
const layerAt = (page, selector) =>
  page.evaluate(sel => {
    const box = document.querySelector(sel).getBoundingClientRect()
    const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2)
    if (hit?.closest('.pt-chat')) return 'chat'
    if (hit?.closest('.pt-fab')) return 'fab'
    if (hit?.closest('.pt-popup-overlay')) return 'window'
    return hit ? hit.tagName : 'nothing'
  }, selector)

test.describe('The floating "+" on a phone', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone layout')
  test.use({ viewport: { width: 393, height: 851 } })

  test('sits above the page, its menu included', async ({ page }) => {
    const tracker = await openTickets(page)
    expect(await layerAt(page, '.pt-fab-main')).toBe('fab')

    await page.locator('.pt-fab-main').click()
    const subButtons = page.locator('.pt-fab-btn')
    await expect(subButtons).toHaveCount(2)
    for (let i = 0; i < 2; i++) {
      await expect.poll(() => layerAt(page, `.pt-fab-btn:nth-child(${i + 1})`)).toBe('fab')
    }
    expect(tracker.unexpected).toEqual([])
  })

  test('goes under an open window', async ({ page }) => {
    const tracker = await openTickets(page)
    await page.locator('.ptl-create').click()
    await expect(page.locator('.pt-popup-overlay')).toBeVisible()

    await expect.poll(() => layerAt(page, '.pt-fab-main')).toBe('window')
    expect(tracker.unexpected).toEqual([])
  })

  test('opens its chat panel above itself', async ({ page }) => {
    const tracker = await openTickets(page, { chat_enabled: true })
    await page.locator('.pt-fab-main').click()
    await page.locator('.pt-fab-btn[title="Chat"]').click()
    await expect(page.locator('.pt-chat')).toBeVisible()

    expect(await layerAt(page, '.pt-fab-main')).toBe('chat')
    expect(tracker.unexpected).toEqual([])
  })
})
