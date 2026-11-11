// Bottom tab bar of the portal on a phone: every label shown whole, none ending in "…".

import { test, expect } from '@playwright/test'
import {
  ADMIN_VIEWER_PROFILE,
  mockAuthenticatedPortal,
  portalRequestsQueueHandlers,
  portalTicketsHandlers,
} from './_fixtures/portal-auth-mocks.js'

// Arial on Windows and macOS, its same-width twin Liberation Sans on the Linux CI:
// identical widths everywhere, and wider than Roboto or Segoe UI.
const SAME_WIDTH_FONT = ".pt-bottom-nav .pt-bottom-tab { font-family: Arial, 'Liberation Sans'; }"

// French at 320px fits by under 1px in Arial, too close for a CI check.
const WIDTHS = { fr: [360, 375], en: [320, 360, 375] }

async function openBar(page, lang) {
  await page.setViewportSize({ width: 375, height: 800 })
  const tracker = await mockAuthenticatedPortal(page, {
    profile: { ...ADMIN_VIEWER_PROFILE, effective_language: lang },
    ui: { show_requests_tab: true },
    pageHandlers: [...portalTicketsHandlers(), ...portalRequestsQueueHandlers()],
  })
  await page.goto('/portal/requests')
  await expect(page.locator('nav.pt-bottom-nav .pt-bottom-tab')).toHaveCount(5)
  return tracker
}

const cutLabels = page =>
  page.evaluate(() =>
    [...document.querySelectorAll('.pt-bottom-tab-label')]
      .filter(label => label.scrollWidth > label.clientWidth)
      .map(label => label.textContent),
  )

test.describe('The bottom tab bar on a phone', () => {
  test.skip(({ isMobile }) => isMobile, 'set widths')

  for (const [lang, widths] of Object.entries(WIDTHS)) {
    test(`shows every ${lang} label whole`, async ({ page }) => {
      const tracker = await openBar(page, lang)
      await page.addStyleTag({ content: SAME_WIDTH_FONT })
      for (const width of widths) {
        await page.setViewportSize({ width, height: 800 })
        expect(await cutLabels(page), `labels cut at ${width}px`).toEqual([])
      }
      expect(tracker.unexpected).toEqual([])
    })
  }

  test('lets a label use the full width of its tab at 320px', async ({ page }) => {
    await openBar(page, 'en')
    await page.setViewportSize({ width: 320, height: 800 })
    const room = await page.evaluate(() => {
      const tab = document.querySelector('.pt-bottom-tab')
      const label = tab.querySelector('.pt-bottom-tab-label')
      // Longer than any tab, so the label's max-width decides its width.
      label.textContent = 'W'.repeat(40)
      const inner = el => {
        const style = getComputedStyle(el)
        const sides = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight)
        return el.getBoundingClientRect().width - sides
      }
      return { text: inner(label), tab: inner(tab) }
    })
    expect(Math.abs(room.text - room.tab)).toBeLessThan(0.5)
  })
})
