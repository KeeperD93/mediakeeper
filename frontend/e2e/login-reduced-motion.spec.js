// Sign-in page under reduced motion: the particles never move, the orbs hold still, the
// card appears at once and the button stays in place under the pointer. Without the
// setting, everything moves as before.

import { test, expect } from '@playwright/test'
import { mockApi } from './_fixtures/api-mocks.js'

async function openLogin(page, reducedMotion) {
  await page.emulateMedia({ reducedMotion })
  // The card's entrance is over in a moment: its transition is read as it appears.
  await page.addInitScript(() => {
    new MutationObserver((_records, observer) => {
      const card = document.querySelector('.login-card')
      if (!card) return
      window.__cardEntrance = getComputedStyle(card).transitionDuration
      observer.disconnect()
    }).observe(document, { childList: true, subtree: true })
  })
  await mockApi(page)
  await page.goto('/login', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('button.login-submit')).toBeVisible()
}

const facts = page =>
  page.evaluate(() => {
    const canvas = document.querySelector('.login-particles')
    const pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data
    return {
      particles: pixels.some(value => value !== 0),
      orb: getComputedStyle(document.querySelector('.login-orb-1')).animationName,
      entrance: window.__cardEntrance,
    }
  })

const buttonMove = async page => {
  await page.locator('button.login-submit').hover()
  return page.locator('button.login-submit').evaluate(button => getComputedStyle(button).transform)
}

test.describe('Sign-in page motion', () => {
  test('moves by default', async ({ page, isMobile }) => {
    await openLogin(page, 'no-preference')
    await expect.poll(async () => (await facts(page)).particles).toBe(true)
    const seen = await facts(page)
    expect(seen.orb).toBe('lo-drift1')
    expect(seen.entrance).toBe('0.6s')
    if (!isMobile) expect(await buttonMove(page)).not.toBe('none')
  })

  test('holds still under reduced motion', async ({ page, isMobile }) => {
    await openLogin(page, 'reduce')
    // Long enough for a few frames of particles, had they started.
    await page.waitForTimeout(300)
    const seen = await facts(page)
    expect(seen).toEqual({ particles: false, orb: 'none', entrance: '0s' })
    if (!isMobile) expect(await buttonMove(page)).toBe('none')
  })
})
