// Signing in with the keyboard in a real browser: Enter sends one try through
// the form, a held Enter never sends more, Enter works again after a refusal,
// and no press reloads the page.

import { test, expect } from '@playwright/test'
import { mockApi } from './_fixtures/api-mocks.js'

// Mirrors the page's pause after a refusal (RETRY_PAUSE_MS in LoginView.vue).
const PAST_RETRY_PAUSE_MS = 1100
// Long enough for a queued request to reach the mock, as in login-validation.
const SETTLE_MS = 300

async function openRefusingLoginPage(page) {
  const state = { tries: 0 }
  state.tracker = await mockApi(page, {
    overrides: [
      {
        name: 'portal-login-refused',
        match: url => url.pathname === '/api/auth/portal-login',
        handler: route => {
          state.tries += 1
          return route.fulfill({
            status: 401,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'invalid_credentials' }),
          })
        },
      },
    ],
  })
  await page.goto('/login')
  await page.locator('input[autocomplete="username"]').fill('Alice')
  await page.locator('input[autocomplete="current-password"]').fill('not-a-real-password')
  // A native form submission reloads the page, which drops this marker; the URL
  // alone cannot tell, the browser lands on /login again.
  await page.evaluate(() => {
    window.__stillHere = true
  })
  return state
}

async function expectNoReload(page, state) {
  expect(await page.evaluate(() => window.__stillHere)).toBe(true)
  expect(state.tracker.unexpected).toEqual([])
}

// A first keydown is a new press; the ones that follow while the key is still
// down are repeats, even once the pause after a refusal is over.
async function holdEnterPastThePause(page) {
  await page.waitForTimeout(PAST_RETRY_PAUSE_MS)
  await page.keyboard.down('Enter')
  await page.keyboard.down('Enter')
  await page.waitForTimeout(SETTLE_MS)
  await page.keyboard.up('Enter')
}

test.describe('Login — keyboard sign-in', () => {
  test('Enter in a field sends one try, a held Enter sends no more', async ({ page }) => {
    const state = await openRefusingLoginPage(page)
    const password = page.locator('input[autocomplete="current-password"]')

    await password.press('Enter')
    await expect.poll(() => state.tries).toBe(1)
    await expect(page.locator('.login-error')).toBeVisible()

    await page.waitForTimeout(PAST_RETRY_PAUSE_MS)
    await page.keyboard.down('Enter')
    await expect.poll(() => state.tries).toBe(2)
    await holdEnterPastThePause(page)
    expect(state.tries).toBe(2)

    await password.press('Enter')
    await expect.poll(() => state.tries).toBe(3)
    await expectNoReload(page, state)
  })

  test('Enter on the focused button sends one try', async ({ page }) => {
    const state = await openRefusingLoginPage(page)

    await page.locator('button.login-submit').press('Enter')
    await expect.poll(() => state.tries).toBe(1)
    await expectNoReload(page, state)
  })

  test('Enter held on the focused button sends no new try', async ({ page }) => {
    const state = await openRefusingLoginPage(page)

    await page.locator('input[autocomplete="current-password"]').press('Enter')
    await expect(page.locator('.login-error')).toBeVisible()
    // Pressed on the button while the pause after that refusal still runs, then
    // held past it: only repeats reach the button once a new try is allowed.
    await page.locator('button.login-submit').focus()
    await page.keyboard.down('Enter')
    await holdEnterPastThePause(page)

    expect(state.tries).toBe(1)
    await expectNoReload(page, state)
  })

  test('Enter on the remember box signs in like the button', async ({ page }) => {
    const state = await openRefusingLoginPage(page)

    await page.locator('.login-checkbox').press('Enter')
    await expect.poll(() => state.tries).toBe(1)
    await expectNoReload(page, state)
  })

  for (const [how, send] of [
    ['a click on', button => button.click()],
    ['Enter on', button => button.press('Enter')],
  ]) {
    test(`after a refusal sent by ${how} the button, Enter retries`, async ({ page }) => {
      const state = await openRefusingLoginPage(page)
      const error = page.locator('.login-error')
      // A click while the card still slides in is retried by scrolling the clipped
      // page, which can carry the message out of view: let the card settle first.
      await page
        .locator('.login-card')
        .evaluate(card => Promise.all(card.getAnimations().map(motion => motion.finished)))

      await send(page.locator('button.login-submit'))
      await expect.poll(() => state.tries).toBe(1)
      // The button, disabled while the try ran, loses the focus in some browsers.
      await expect(page.locator('input[autocomplete="current-password"]')).toBeFocused()
      // With the focus moved, the message stays in view and in an alert, which is announced.
      await expect(error).toHaveAttribute('role', 'alert')
      await expect(error).toBeInViewport()

      await page.waitForTimeout(PAST_RETRY_PAUSE_MS)
      await page.keyboard.press('Enter')
      await expect.poll(() => state.tries).toBe(2)
      await expectNoReload(page, state)
    })
  }
})
