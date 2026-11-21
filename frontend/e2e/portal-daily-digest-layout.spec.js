// Daily digest window on a computer: the backdrop scrolls exactly to the window's end,
// never into the empty space its light used to add beyond the screen. Fictional viewer,
// every API call mocked.

import { test, expect } from '@playwright/test'
import { openDigest } from './_fixtures/portal-daily-digest.js'

// How far the backdrop scrolls, and where the window ends in it, its bottom gap included.
const scrollArea = page =>
  page.evaluate(() => {
    const overlay = document.querySelector('.dd-overlay')
    const panel = document.querySelector('.dd-panel')
    return {
      height: overlay.scrollHeight,
      screen: overlay.clientHeight,
      windowEnd:
        panel.offsetTop + panel.offsetHeight + parseFloat(getComputedStyle(overlay).paddingBottom),
      sideways: overlay.scrollWidth - overlay.clientWidth,
    }
  })

// Within a pixel: box edges fall on fractions of a pixel.
const expectSame = (actual, expected, what) =>
  expect(Math.abs(actual - expected), `${what}: ${actual} vs ${expected}`).toBeLessThan(1)

test.describe('The daily digest on a computer', () => {
  test.skip(({ isMobile }) => isMobile, 'computer layout')

  test('lets nothing scroll when the window fits the screen', async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1440 })
    const tracker = await openDigest(page, true)

    const area = await scrollArea(page)
    expect(area.windowEnd, 'the compact window fits').toBeLessThanOrEqual(area.screen)
    expectSame(area.height, area.screen, 'scroll height')
    expect(area.sideways).toBe(0)

    expect(tracker.unexpected).toEqual([])
  })

  test('stops scrolling at the end of a window taller than the screen', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    const tracker = await openDigest(page, false)

    const area = await scrollArea(page)
    expect(area.windowEnd, 'the full window is taller').toBeGreaterThan(area.screen)
    expectSame(area.height, area.windowEnd, 'scroll height')
    expect(area.sideways).toBe(0)

    expect(tracker.unexpected).toEqual([])
  })
})
