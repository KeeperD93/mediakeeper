// Toast placement on narrow phones — a sign-in refused by the rate limit
// (429 without a reason) shows the shared 8 s warning toast. It must stay
// on screen down to 320 px and keep its desktop place from 375 px up.

import { test, expect } from '@playwright/test'
import { mockApi } from './_fixtures/api-mocks.js'

const GUTTER_RIGHT = 24
const TOAST_WIDTH = 340

async function showRateLimitToast(page, width) {
  const tracker = await mockApi(page, {
    overrides: [
      {
        name: 'portal-login-rate-limited',
        match: url => url.pathname === '/api/auth/portal-login',
        handler: route =>
          route.fulfill({ status: 429, contentType: 'application/json', body: '{}' }),
      },
    ],
  })
  await page.setViewportSize({ width, height: 700 })
  await page.goto('/login')
  await page.locator('input[type="text"]').first().fill('alice')
  await page.locator('input[type="password"]').fill('test-password')
  await page.locator('button.login-submit').click()

  const toast = page.locator('.mk-toast.warn')
  await expect(toast).toBeVisible()
  // Measure once the slide-in has finished (the transition drops its classes then).
  await expect(toast).not.toHaveClass(/toast-enter/)
  expect(tracker.unexpected).toEqual([])
  return toast
}

test.describe('Toasts — placement on narrow screens', () => {
  for (const width of [320, 360]) {
    test(`stays whole on a ${width} px wide screen`, async ({ page }) => {
      const toast = await showRateLimitToast(page, width)
      const box = await toast.boundingBox()

      expect(box.x).toBeGreaterThanOrEqual(0)
      expect(width - (box.x + box.width)).toBeCloseTo(GUTTER_RIGHT, 0)
    })
  }

  for (const width of [375, 1280]) {
    test(`keeps its width and place at ${width} px`, async ({ page }) => {
      const toast = await showRateLimitToast(page, width)
      const box = await toast.boundingBox()

      expect(box.width).toBeCloseTo(TOAST_WIDTH, 0)
      expect(width - (box.x + box.width)).toBeCloseTo(GUTTER_RIGHT, 0)
    })
  }

  test('lets clicks through beside the toast and runs its bar for 8 s', async ({ page }) => {
    const toast = await showRateLimitToast(page, 1280)
    const box = await toast.boundingBox()
    const besideToast = await page.evaluate(
      ([x, y]) => !!document.elementFromPoint(x, y)?.closest('.mk-toast-container'),
      [box.x - 100, box.y + box.height / 2],
    )
    const barDuration = await toast
      .locator('.mk-toast-progress')
      .evaluate(bar => getComputedStyle(bar).animationDuration)

    expect(besideToast).toBe(false)
    expect(barDuration).toBe('8s')
  })
})
