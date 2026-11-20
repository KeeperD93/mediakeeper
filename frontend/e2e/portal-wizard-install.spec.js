// First-login wizard, last step: it offers to install the portal as an app, through the
// browser's own window where there is one, with the steps to follow on iPhone and iPad, a
// browser that can install it for Firefox on a computer, and not at all where nothing tells
// it the browser can install. Fictional viewer, every API call mocked.

import { test, expect } from '@playwright/test'
import { openWizard } from './_fixtures/portal-wizard.js'

const IPHONE =
  'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
const FIREFOX = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0'

// Next, step after step, up to the last one.
async function walkToDone(page) {
  const step = page.locator('.wz-step')
  const without = page.getByRole('button', { name: 'Continue without' })
  for (let left = 12; left > 0 && !(await page.locator('.wz-step--done').isVisible()); left -= 1) {
    const before = await step.getAttribute('class')
    await page.locator('.wz-next').click()
    // Notifications blocked by the test browser: « are you sure? », then on without them.
    const moved = page.locator(`.wz-step:not(.${before.split(' ').at(-1)})`)
    await expect(moved.or(without)).toBeVisible()
    if (await without.isVisible()) await without.click()
    await expect(step).not.toHaveAttribute('class', before)
  }
  await expect(page.locator('.wz-step--done')).toBeVisible()
}

const installBox = page => page.locator('.wz-next-box', { hasText: 'Install the app' })

test('opens the browser’s install window from the last step', async ({ page }) => {
  const tracker = await openWizard(page)
  // The browser's offer, as Chrome sends it once the portal can be installed; its window
  // is refused here.
  const held = await page.evaluate(() => {
    window.installAsked = 0
    const offer = new Event('beforeinstallprompt', { cancelable: true })
    offer.prompt = async () => {
      window.installAsked += 1
    }
    offer.userChoice = Promise.resolve({ outcome: 'dismissed' })
    window.dispatchEvent(offer)
    return offer.defaultPrevented
  })
  expect(held, 'no browser banner over the portal').toBe(true)

  await walkToDone(page)
  const box = installBox(page)
  await expect(box).toContainText('Open MediaKeeper from its icon, like a real app.')
  await box.getByRole('button', { name: 'Install' }).click()

  await expect.poll(() => page.evaluate(() => window.installAsked)).toBe(1)
  // Refused: not offered again during this visit.
  await expect(box).toBeHidden()
  expect(tracker.unexpected).toEqual([])
})

test('offers nothing where the browser cannot install', async ({ page }) => {
  const tracker = await openWizard(page)
  await walkToDone(page)

  await expect(page.locator('.wz-next-box')).toHaveCount(1)
  await expect(installBox(page)).toHaveCount(0)
  expect(tracker.unexpected).toEqual([])
})

const TEXT_ONLY = [
  {
    where: 'On an iPhone',
    userAgent: IPHONE,
    what: 'shows the steps to add the portal to the home screen',
    texts: [
      'Tap the Share button, then "Add to Home Screen".',
      'this is also what lets you receive notifications',
    ],
  },
  {
    where: 'In Firefox on a computer',
    userAgent: FIREFOX,
    what: 'points to a browser that can install it',
    texts: ['open the portal in Chrome or Edge to install it'],
  },
]

for (const { where, userAgent, what, texts } of TEXT_ONLY) {
  test.describe(where, () => {
    test.use({ userAgent })

    test(what, async ({ page }) => {
      const tracker = await openWizard(page)
      await walkToDone(page)

      const box = installBox(page)
      for (const text of texts) await expect(box).toContainText(text)
      await expect(box.getByRole('button')).toHaveCount(0)
      expect(tracker.unexpected).toEqual([])
    })
  })
}
