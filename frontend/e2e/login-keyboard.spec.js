// Signing in with the keyboard in a real browser: Enter sends one try through
// the form, a held Enter never sends more, and the page never leaves /login.

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
  return state
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

    await expect(page).toHaveURL(/\/login$/)
    expect(state.tracker.unexpected).toEqual([])
  })

  test('a held Enter on the focused button sends one try', async ({ page }) => {
    const state = await openRefusingLoginPage(page)

    await page.locator('button.login-submit').focus()
    await page.keyboard.down('Enter')
    await expect.poll(() => state.tries).toBe(1)
    await holdEnterPastThePause(page)

    expect(state.tries).toBe(1)
    await expect(page).toHaveURL(/\/login$/)
    expect(state.tracker.unexpected).toEqual([])
  })

  test('Enter on the remember box signs in like the button', async ({ page }) => {
    const state = await openRefusingLoginPage(page)

    await page.locator('.login-checkbox').press('Enter')
    await expect.poll(() => state.tries).toBe(1)

    await expect(page).toHaveURL(/\/login$/)
    expect(state.tracker.unexpected).toEqual([])
  })
})
