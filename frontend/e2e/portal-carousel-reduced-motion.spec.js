// An arrow of a portal carousel slides the track, or makes it jump when the device asks
// for reduced motion: the track's CSS chooses, the script no longer forces a slide.

import { test, expect } from '@playwright/test'
import { jsonResponse } from './_fixtures/api-mocks.js'
import {
  DEFAULT_VIEWER_PROFILE,
  mockAuthenticatedPortal,
  portalSettingsHandlers,
} from './_fixtures/portal-auth-mocks.js'

const CONTINUE = Array.from({ length: 10 }, (_, index) => ({
  id: index + 1,
  emby_item_id: `item-${index + 1}`,
  title: `Test Movie ${index + 1}`,
  poster_url: null,
  backdrop: null,
  emby_url: null,
}))

async function openContinueWatching(page, reducedMotion) {
  await page.setViewportSize({ width: 1280, height: 800 })
  await page.emulateMedia({ reducedMotion })
  const profile = { ...DEFAULT_VIEWER_PROFILE, language: 'fr' }
  await mockAuthenticatedPortal(page, {
    profile,
    pageHandlers: portalSettingsHandlers({ profile }),
    extraOverrides: [
      {
        name: 'portal-library-continue-items',
        match: url => url.pathname === '/api/portal/library/continue',
        handler: jsonResponse({ items: CONTINUE }),
      },
    ],
  })
  await page.goto('/portal/me')
  await expect(page.locator('.dp-cw-section .pt-carousel-arrow--right')).toHaveClass(
    /pt-carousel-arrow--visible/,
  )
}

// Clicks the right arrow and reads where the track stands in the same instant.
const clickRight = page =>
  page.locator('.dp-cw-track').evaluate(track => {
    const before = track.scrollLeft
    track.parentElement.querySelector('.pt-carousel-arrow--right').click()
    return { style: getComputedStyle(track).scrollBehavior, before, after: track.scrollLeft }
  })

test.describe('Arrows of a portal carousel', () => {
  test.skip(({ isMobile }) => isMobile, 'the arrows are for a pointer')

  test('slide the track by default', async ({ page }) => {
    await openContinueWatching(page, 'no-preference')
    const moved = await clickRight(page)
    expect(moved.style).toBe('smooth')
    expect(moved.after).toBe(moved.before)
    await expect
      .poll(() => page.locator('.dp-cw-track').evaluate(track => track.scrollLeft))
      .toBeGreaterThan(moved.before)
  })

  test('make it jump under reduced motion', async ({ page }) => {
    await openContinueWatching(page, 'reduce')
    const moved = await clickRight(page)
    expect(moved.style).toBe('auto')
    expect(moved.after).toBeGreaterThan(moved.before)
  })
})
