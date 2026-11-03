// Layout of the period tabs: on a large screen a click moves neither the page nor the
// tabs, and on a phone the row holds on one line with a touch area of 44 px.

import { test, expect } from '@playwright/test'
import { BY_PERIOD, LABELS, openTabs, tab } from './_fixtures/portal-leaderboard-tabs.js'

test.describe('The page keeps one width on a large screen', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen')

  // A short name here, the longest ones on the other tabs.
  const byPeriod = {
    ...BY_PERIOD,
    today: {
      ...BY_PERIOD.today,
      items: BY_PERIOD.today.items.map(entry => ({
        ...entry,
        display_name: 'Bob',
        selected_title: null,
      })),
    },
  }

  for (const width of [1024, 1280, 1366, 1920]) {
    test(`at ${width}px, a click moves neither the page nor the tabs`, async ({ page }) => {
      await openTabs(page, { width, byPeriod })
      const facts = {}
      for (const period of Object.keys(LABELS)) {
        await tab(page, period).click()
        await expect(tab(page, period)).toHaveAttribute('aria-selected', 'true')
        await expect(page.locator('.lb-hero')).toBeVisible()
        facts[period] = await page.evaluate(() => ({
          page: document.querySelector('.pt-leaderboard').getBoundingClientRect().toJSON(),
          firstTab: document.querySelector('.lb-period-tab').getBoundingClientRect().left,
          note: document.querySelector('.pt-lb-note').getBoundingClientRect().height,
        }))
      }
      for (const fact of Object.values(facts)) {
        expect(fact.page.width).toBe(880)
        expect(fact.page.left).toBe(facts.month.page.left)
        expect(fact.firstTab).toBe(facts.month.firstTab)
        // The longest note stays on one line, like the shortest.
        expect(fact.note).toBe(facts.today.note)
      }
    })
  }
})

test.describe('The row holds on a phone', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone')

  for (const width of [320, 360, 375, 430]) {
    test(`at ${width}px, whichever tab is on: one line, inside the screen`, async ({ page }) => {
      await openTabs(page, { width })
      for (const period of Object.keys(LABELS)) {
        await tab(page, period).click()
        await expect(tab(page, period)).toHaveAttribute('aria-selected', 'true')
        const facts = await page.locator('.lb-period-tab').evaluateAll(tabs => ({
          tops: new Set(tabs.map(item => Math.round(item.getBoundingClientRect().top))).size,
          right: Math.max(...tabs.map(item => item.getBoundingClientRect().right)),
          clipped: tabs.filter(item => item.scrollWidth > item.clientWidth).length,
          page: document.documentElement.scrollWidth,
        }))
        expect(facts.tops).toBe(1)
        expect(facts.right).toBeLessThanOrEqual(width)
        expect(facts.clipped).toBe(0)
        expect(facts.page).toBeLessThanOrEqual(width)
      }
    })
  }

  test('a finger gets 44 px on each tab', async ({ page }) => {
    await openTabs(page, { width: 375 })
    const band = await tab(page, 'week').evaluate(element => {
      const style = getComputedStyle(element, '::after')
      return { height: style.height, position: style.position }
    })
    expect(band).toEqual({ height: '44px', position: 'absolute' })
    const box = await tab(page, 'week').boundingBox()
    const center = { x: box.x + box.width / 2, y: box.y + box.height / 2 }
    const hit = await page.evaluate(
      ({ x, y }) => document.elementFromPoint(x, y + 20)?.textContent?.trim(),
      center,
    )
    expect(hit).toBe(LABELS.week)
  })
})
