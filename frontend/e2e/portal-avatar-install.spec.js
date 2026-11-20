// The avatar menu's « Install the app » line, right above « Log out »: the browser's own
// install window where there is one, the steps to follow in a small window elsewhere, no
// line where nothing tells it the browser can install. Fictional viewer, every API call
// mocked.

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mockAuthenticatedPortal, portalListsHandlers } from './_fixtures/portal-auth-mocks.js'

const FIREFOX = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0'

async function openPortal(page) {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  const tracker = await mockAuthenticatedPortal(page, { pageHandlers: portalListsHandlers() })
  await page.goto('/portal/lists')
  await expect(page.locator('.pt-avatar-trigger')).toBeVisible()
  return tracker
}

const menuLines = async page => {
  await page.locator('.pt-avatar-trigger').click()
  return page.locator('.pt-avatar-pop-item')
}

test('opens the browser’s install window from the line above « Log out »', async ({ page }) => {
  const tracker = await openPortal(page)
  // The browser's offer, as Chrome sends it; its window is refused here.
  await page.evaluate(() => {
    window.installAsked = 0
    const offer = new Event('beforeinstallprompt', { cancelable: true })
    offer.prompt = async () => {
      window.installAsked += 1
    }
    offer.userChoice = Promise.resolve({ outcome: 'dismissed' })
    window.dispatchEvent(offer)
  })

  const lines = await menuLines(page)
  await expect(lines.last()).toHaveClass(/pt-avatar-pop-item--danger/)
  await expect(lines.nth(-2)).toHaveText('Install the app')
  await lines.nth(-2).click()

  await expect.poll(() => page.evaluate(() => window.installAsked)).toBe(1)
  await expect(page.locator('.pis-panel')).toHaveCount(0)
  // Refused: the line is gone for this visit.
  await expect((await menuLines(page)).filter({ hasText: 'Install the app' })).toHaveCount(0)
  expect(tracker.unexpected).toEqual([])
})

test('has no line where nothing tells it the browser can install', async ({ page }) => {
  const tracker = await openPortal(page)
  await expect((await menuLines(page)).filter({ hasText: 'Install the app' })).toHaveCount(0)
  expect(tracker.unexpected).toEqual([])
})

test.describe('In Firefox on a computer', () => {
  test.use({ userAgent: FIREFOX })

  test('shows another browser to use in a small window, then gives the focus back', async ({
    page,
  }) => {
    const tracker = await openPortal(page)
    const lines = await menuLines(page)
    await lines.filter({ hasText: 'Install the app' }).click()

    const dialog = page.getByRole('dialog', { name: 'Install the app' })
    await expect(dialog).toContainText('open the portal in Chrome or Edge to install it')
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeFocused()
    const results = await new AxeBuilder({ page }).include('.pis-panel').analyze()
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])

    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)
    await expect(page.locator('.pt-avatar-trigger')).toBeFocused()
    expect(tracker.unexpected).toEqual([])
  })
})
