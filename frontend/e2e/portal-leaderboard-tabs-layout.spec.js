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

test.describe('The figures line up on a large screen', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen')

  // Numbers of every length, the longest included, and badges of every length.
  const XP = [7, 64, 133, 12345, 1234567]
  const mixed = Object.fromEntries(
    Object.entries(BY_PERIOD).map(([period, body]) => [
      period,
      {
        ...body,
        items: body.items.map((entry, index) => ({
          ...entry,
          period_xp: XP[index % XP.length],
          trophies_won: [3, 14, 123][index % 3],
        })),
      },
    ]),
  )

  for (const period of ['month', 'all']) {
    test(`on ${period}, from place 14 the arrows and the trophies fall in columns`, async ({
      page,
    }) => {
      await openTabs(page, { byPeriod: mixed })
      await tab(page, period).click()
      await expect(page.locator('.lb-rest .gc-lb-row').first()).toBeVisible()
      const rows = await page.locator('.lb-rest .gc-lb-row').evaluateAll(items =>
        items.map(row => {
          const right = selector => row.querySelector(selector)?.getBoundingClientRect().right
          const text = document.createRange()
          text.selectNodeContents(row.querySelector('.gc-lb-v'))
          return {
            xp: text.getBoundingClientRect().right,
            xpLeft: row.querySelector('.gc-lb-v').getBoundingClientRect().left,
            xpClipped:
              row.querySelector('.gc-lb-v').scrollWidth > row.querySelector('.gc-lb-v').clientWidth,
            arrow: right('.gc-lb-move'),
            trophies: right('.lb-trophies'),
          }
        }),
      )
      expect(rows.length).toBeGreaterThan(1)
      const spread = values => Math.max(...values) - Math.min(...values)
      expect(spread(rows.map(row => row.xp))).toBeLessThanOrEqual(1)
      expect(spread(rows.map(row => row.xpLeft))).toBeLessThanOrEqual(1)
      expect(spread(rows.map(row => row.trophies))).toBeLessThanOrEqual(1)
      if (period === 'all') expect(rows.every(row => row.arrow === undefined)).toBe(true)
      else expect(spread(rows.map(row => row.arrow))).toBeLessThanOrEqual(1)
      expect(rows.filter(row => row.xpClipped)).toEqual([])
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

  // Short XP under a wider badge, and a tab without arrows: the worst case of a row.
  const shortFigures = Object.fromEntries(
    Object.entries(BY_PERIOD).map(([period, body]) => [
      period,
      {
        ...body,
        items: body.items.map((entry, index) => ({
          ...entry,
          period_xp: index % 2 ? 64 : 133,
          trophies_won: index % 3 ? 14 : 0,
        })),
      },
    ]),
  )

  for (const width of [320, 375, 640]) {
    test(`at ${width}px, XP and trophies stay one under the other on each tab`, async ({
      page,
    }) => {
      await openTabs(page, { width, byPeriod: shortFigures })
      for (const period of Object.keys(LABELS)) {
        await tab(page, period).click()
        await expect(tab(page, period)).toHaveAttribute('aria-selected', 'true')
        await expect(page.locator('.lb-rest .gc-lb-row').first()).toBeVisible()
        const lists = await page.evaluate(() => {
          // The text itself: the box of the XP can be wider than what it shows.
          const textRight = element => {
            const range = document.createRange()
            range.selectNodeContents(element)
            return range.getBoundingClientRect().right
          }
          return [
            ['.lb-top-row', '.lb-top-row-xp'],
            ['.lb-rest .gc-lb-row', '.gc-lb-v'],
          ].map(([rowSelector, xpSelector]) =>
            [...document.querySelectorAll(rowSelector)].map(row => ({
              xp: textRight(row.querySelector(xpSelector)),
              trophies: row.querySelector('.lb-trophies')?.getBoundingClientRect().right ?? null,
            })),
          )
        })
        for (const rows of lists) {
          expect(rows.length).toBeGreaterThan(0)
          const edges = rows.map(row => row.xp)
          expect(Math.max(...edges) - Math.min(...edges)).toBeLessThanOrEqual(1)
          for (const row of rows.filter(item => item.trophies !== null)) {
            expect(Math.abs(row.xp - row.trophies)).toBeLessThanOrEqual(1)
          }
        }
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
