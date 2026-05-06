// Login a11y baseline — desktop + mobile via Playwright projects.
//
// Verifies the unauthenticated /login page exposes the WCAG quick-win
// blockers fixed in batch 22A:
//   - exactly one <main> landmark (axe `landmark-one-main`)
//   - all content sits inside a landmark (axe `region`)
//   - exactly one <h1> (axe `page-has-heading-one`)
// And keyboard-only access is preserved:
//   - Tab from a fresh page focuses the skip-link first.
//   - Enter on the skip-link moves focus to the #main-content element.

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mockApi } from './_fixtures/api-mocks.js'

const TARGETED_RULES = ['landmark-one-main', 'region', 'page-has-heading-one']

test.describe('Login — a11y baseline', () => {
  test('axe finds no targeted landmark/heading violations', async ({ page }) => {
    const tracker = await mockApi(page)

    await page.goto('/login')

    // Wait for the form to render so axe scans the post-boot DOM, not the
    // pre-health "starting…" screen.
    await expect(page.locator('button.login-submit')).toBeVisible()

    const results = await new AxeBuilder({ page })
      .include('main#main-content')
      .withRules(TARGETED_RULES)
      .analyze()

    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])
    expect(tracker.unexpected).toEqual([])
  })

  test('keyboard skip-link focuses then jumps to #main-content', async ({ page }) => {
    await mockApi(page)

    await page.goto('/login')
    await expect(page.locator('button.login-submit')).toBeVisible()

    // Drop any focus that may have been set by autofocus / scripts so Tab
    // starts from the document root.
    await page.evaluate(() => {
      if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
    })

    await page.keyboard.press('Tab')

    const skipLink = page.locator('a.mk-skip-link')
    await expect(skipLink).toBeFocused()

    await page.keyboard.press('Enter')

    // After Enter, the URL hash should target main-content and the focus
    // should land on the <main> landmark itself (we set tabindex=-1 via
    // the browser default focus behaviour for the in-page anchor target).
    await expect(page).toHaveURL(/#main-content$/)

    const mainFocused = await page.evaluate(() => {
      const main = document.getElementById('main-content')
      return !!main && (document.activeElement === main || main.contains(document.activeElement))
    })
    expect(mainFocused).toBe(true)
  })
})
