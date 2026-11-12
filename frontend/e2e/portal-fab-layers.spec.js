// Floating "+" of the portal: on a phone above the page, under any open window,
// and its chat panel above it; with a keyboard, its open menu reachable with Tab.

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { jsonResponse } from './_fixtures/api-mocks.js'
import {
  DEFAULT_VIEWER_PROFILE,
  mockAuthenticatedPortal,
  portalTicketsHandlers,
} from './_fixtures/portal-auth-mocks.js'

const stub = (name, match, body) => ({ name, match, handler: jsonResponse(body) })

const chatHandlers = unread => [
  stub('chat-unread', url => url.pathname === '/api/portal/chat/unread', { unread }),
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

async function openTickets(page, profile = {}, unread = 0) {
  const tracker = await mockAuthenticatedPortal(page, {
    profile: { ...DEFAULT_VIEWER_PROFILE, effective_language: 'en', ...profile },
    pageHandlers: [...portalTicketsHandlers(), ...chatHandlers(unread)],
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

test.describe('The floating "+" with a keyboard', () => {
  test('Tab walks the open menu from the "+", nearest button first', async ({ page }) => {
    const tracker = await openTickets(page, { chat_enabled: true }, 3)
    const main = page.locator('.pt-fab-main')
    await expect(main).toHaveAccessibleName('Quick actions, 3 unread messages')

    await main.focus()
    await page.keyboard.press('Enter')
    await expect(main).toHaveAttribute('aria-expanded', 'true')
    // Each stop sits higher on screen: the menu still stacks upward from the "+".
    let previousTop = (await main.boundingBox()).y
    for (const name of ['Chat, 3 unread messages', 'Surprise me!', 'Create event']) {
      await page.keyboard.press('Tab')
      const focused = page.locator(':focus')
      await expect(focused).toHaveAccessibleName(name)
      // The portal's focus ring, not the browser's default one.
      await expect(focused).toHaveCSS('outline-style', 'solid')
      await expect(focused).toHaveCSS('outline-offset', '2px')
      const top = (await focused.boundingBox()).y
      expect(top, `${name} above the previous stop`).toBeLessThan(previousTop)
      previousTop = top
    }

    const results = await new AxeBuilder({ page })
      .include('.pt-fab')
      .withRules(['button-name', 'aria-allowed-attr', 'aria-valid-attr-value'])
      .analyze()
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])
    expect(tracker.unexpected).toEqual([])
  })
})
