// First-login wizard window: on a phone, the footer stays at the bottom of the screen and
// only the step scrolls, long or short; on a computer, a window of the same height at
// every step, centered. Fictional viewer, every API call mocked.

import { test, expect } from '@playwright/test'
import { jsonResponse } from './_fixtures/api-mocks.js'
import {
  DEFAULT_VIEWER_PROFILE,
  mockAuthenticatedPortal,
  portalListsHandlers,
} from './_fixtures/portal-auth-mocks.js'

const pathHandler = (name, pathname, body) => ({
  name,
  match: url => url.pathname === pathname,
  handler: jsonResponse(body),
})

// The viewer's name is free to keep: not locked, and judged « current » by the live check.
const WIZARD_HANDLERS = [
  pathHandler('portal-username-state', '/api/portal/profiles/me/username-state', {
    locked: false,
    locked_until: null,
    must_set: false,
    lock_days: 180,
  }),
  pathHandler('portal-check-username', '/api/portal/profiles/me/check-username', {
    available: true,
    reason: 'current',
    locked_until: null,
    suggestions: [],
  }),
]

async function openWizard(page) {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  const tracker = await mockAuthenticatedPortal(page, {
    profile: { ...DEFAULT_VIEWER_PROFILE, onboarding_pending: true },
    pageHandlers: [...portalListsHandlers(), ...WIZARD_HANDLERS],
  })
  await page.goto('/portal/lists')
  await expect(page.locator('.wz-step--welcome')).toBeVisible()
  return tracker
}

// Where the window and its footer sit, whether the step scrolls, and whether anything
// around the window does (a scroll that does not move means nothing to scroll).
const layout = page =>
  page.evaluate(() => {
    const edges = selector => {
      const { top, bottom, height } = document.querySelector(selector).getBoundingClientRect()
      return { top, bottom, height }
    }
    const overlay = document.querySelector('.wz-overlay')
    const body = document.querySelector('.wz-in')
    const token = name =>
      parseFloat(getComputedStyle(document.documentElement).getPropertyValue(name))
    overlay.scrollTop = 200
    const overlayMoves = overlay.scrollTop > 0
    overlay.scrollTop = 0
    return {
      screen: window.innerHeight,
      panel: edges('.wz'),
      foot: edges('.wz-foot'),
      stepScrolls: body.scrollHeight > body.clientHeight,
      // Scrollbars are no boxes: the window clipping its corners keeps the step's inside.
      windowClips: getComputedStyle(document.querySelector('.wz')).overflow === 'clip',
      overlayMoves,
      designHeight: token('--portal-wizard-window-height'),
      // Side margins of the step and of the footer, and the widest one the design sets.
      sides: [body, document.querySelector('.wz-foot')].map(el =>
        parseFloat(getComputedStyle(el).paddingLeft),
      ),
      widestSide: token('--portal-space-12'),
    }
  })

// The welcome's blocks: no eyebrow, the introduction under the title, then the list and
// the bottom sentence, each one step gap apart.
const welcomeSpacing = page =>
  page.evaluate(() => {
    const box = selector =>
      document.querySelector(`.wz-step--welcome ${selector}`).getBoundingClientRect()
    const token = name =>
      parseFloat(getComputedStyle(document.documentElement).getPropertyValue(name))
    return {
      eyebrow: document.querySelector('.wz-step--welcome .dd-date') !== null,
      titleToIntro: box('.dd-sub').top - box('h1').bottom,
      introToList: box('.wz-plan').top - box('.wz-head').bottom,
      listToNote: box('.wz-time').top - box('.wz-plan').bottom,
      near: token('--portal-space-3'),
      apart: token('--portal-space-5'),
    }
  })

// Within a pixel: box edges fall on fractions of a pixel.
const expectSame = (actual, expected, what) =>
  expect(Math.abs(actual - expected), `${what}: ${actual} vs ${expected}`).toBeLessThan(1)

test.describe('The first-login wizard on a phone', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone layout')

  test('keeps its footer at the bottom of the screen, long step or short', async ({ page }) => {
    const tracker = await openWizard(page)

    // The welcome is longer than the screen: the step scrolls, the footer stays put.
    const welcome = await layout(page)
    expect(welcome.stepScrolls, 'the welcome scrolls').toBe(true)
    expectSame(welcome.foot.bottom, welcome.screen, 'footer bottom, welcome')
    expect(welcome.overlayMoves).toBe(false)

    // The name is shorter: the footer still reaches the bottom edge, not the text's end.
    await page.locator('.wz-next').click()
    await expect(page.locator('.wz-step--name')).toBeVisible()
    const name = await layout(page)
    expect(name.stepScrolls, 'the name fits').toBe(false)
    expectSame(name.foot.bottom, name.screen, 'footer bottom, name')
    expect(name.overlayMoves).toBe(false)

    expect(tracker.unexpected).toEqual([])
  })
})

test.describe('The first-login wizard on a computer', () => {
  test.skip(({ isMobile }) => isMobile, 'computer layout')

  test('centers a window of the same height at every step', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    const tracker = await openWizard(page)

    const welcome = await layout(page)
    expectSame(welcome.panel.height, welcome.designHeight, 'window height')
    expectSame(welcome.panel.top, welcome.screen - welcome.panel.bottom, 'gap above and below')
    // Only the window's border under the footer.
    expect(welcome.foot.bottom).toBeLessThanOrEqual(welcome.panel.bottom)
    expect(welcome.panel.bottom - welcome.foot.bottom).toBeLessThan(2)
    expect(welcome.overlayMoves).toBe(false)
    // The margins widen with the window: the widest on a wide window, step and footer alike.
    expect(welcome.sides).toEqual([welcome.widestSide, welcome.widestSide])

    await page.locator('.wz-next').click()
    await expect(page.locator('.wz-step--name')).toBeVisible()
    const name = await layout(page)
    expect(name.panel).toEqual(welcome.panel)

    // A laptop's short screen: the window shrinks to fit, still centered.
    await page.setViewportSize({ width: 1366, height: 768 })
    const laptop = await layout(page)
    expect(laptop.panel.height).toBeLessThan(laptop.designHeight)
    expectSame(laptop.panel.top, laptop.screen - laptop.panel.bottom, 'gap above and below, laptop')
    expect(laptop.overlayMoves).toBe(false)
    expect(laptop.windowClips, 'the scrollbar stays inside the rounded window').toBe(true)

    expect(tracker.unexpected).toEqual([])
  })

  test('spaces the welcome out, without an eyebrow', async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 })
    const tracker = await openWizard(page)

    const spacing = await welcomeSpacing(page)
    expect(spacing.eyebrow, 'no eyebrow on the welcome').toBe(false)
    expectSame(spacing.titleToIntro, spacing.near, 'title to introduction')
    expectSame(spacing.introToList, spacing.apart, 'introduction to list')
    expectSame(spacing.listToNote, spacing.apart, 'list to bottom sentence')

    expect(tracker.unexpected).toEqual([])
  })
})
