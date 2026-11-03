// Top bar of the portal: one row at every width, the tabs scrolling sideways when an
// admin's full set doesn't fit on a tablet, and the page clearing the bar without a gap.

import { test, expect } from '@playwright/test'
import {
  ADMIN_VIEWER_PROFILE,
  mockAuthenticatedPortal,
  portalRequestsQueueHandlers,
  portalTicketsHandlers,
} from './_fixtures/portal-auth-mocks.js'

// The widest set of tabs and icons, in the language with the longest labels.
const WIDEST_ACCOUNT = {
  profile: { ...ADMIN_VIEWER_PROFILE, has_backoffice_access: true, effective_language: 'fr' },
  ui: { show_requests_tab: true, donation: { enabled: true } },
  pageHandlers: [...portalTicketsHandlers(), ...portalRequestsQueueHandlers()],
}

async function openAt(page, width, path) {
  await page.setViewportSize({ width, height: 900 })
  const tracker = await mockAuthenticatedPortal(page, WIDEST_ACCOUNT)
  await page.goto(path)
  await expect(page.locator('.pt-avatar-trigger')).toBeVisible()
  await expect(page.locator('.pt-tab--active')).toHaveCount(1)
  return tracker
}

const barFacts = page =>
  page.evaluate(() => {
    const rect = selector => document.querySelector(selector).getBoundingClientRect()
    const scroller = document.querySelector('.pt-nav-tabs')
    const tabs = scroller.getBoundingClientRect()
    const quick = rect('.pt-nav-quick')
    const active = rect('.pt-tab--active')
    const middle = box => box.top + box.height / 2
    const main = document.querySelector('main#main-content')
    const inner = document.querySelector('.pt-nav-inner')
    return {
      height: rect('nav.pt-nav').height,
      rowGap: Math.abs(middle(tabs) - middle(quick)),
      tabsRight: tabs.right,
      tabsLeft: tabs.left,
      iconsLeft: quick.left,
      iconsRight: quick.right,
      roomRightOfIcons:
        inner.getBoundingClientRect().right -
        parseFloat(getComputedStyle(inner).paddingRight) -
        quick.right,
      overflow: scroller.scrollWidth - scroller.clientWidth,
      scrollbar: getComputedStyle(scroller).scrollbarWidth,
      verticalOverflow: scroller.scrollHeight - scroller.clientHeight,
      activeLeft: active.left,
      activeRight: active.right,
      lastTabRight: rect('.pt-tab:last-child').right,
      ringRoomAbove: rect('.pt-tab').top - tabs.top,
      clearance: parseFloat(getComputedStyle(main.firstElementChild).paddingTop),
    }
  })

const roomRightOfActiveTab = async page => {
  const bar = await barFacts(page)
  return bar.tabsRight - bar.activeRight
}

test.describe('The top bar on a tablet', () => {
  test.skip(({ isMobile }) => isMobile, 'tablet widths')

  test('keeps one row and one clearance from 768 to 1023px', async ({ page }) => {
    await openAt(page, 1024, '/portal/requests')
    const { height: oneRow } = await barFacts(page)
    await page.setViewportSize({ width: 1023, height: 900 })
    const { clearance } = await barFacts(page)
    expect(clearance).toBeGreaterThan(oneRow)

    for (const width of [768, 800, 920, 921, 1023]) {
      await page.setViewportSize({ width, height: 900 })
      const bar = await barFacts(page)
      expect(bar.height, `height at ${width}px`).toBe(oneRow)
      expect(bar.rowGap, `tabs and icons on one row at ${width}px`).toBeLessThan(1)
      expect(bar.tabsRight, `tabs clear of the icons at ${width}px`).toBeLessThanOrEqual(
        bar.iconsLeft,
      )
      expect(bar.roomRightOfIcons, `icons against the edge at ${width}px`).toBeLessThan(1)
      expect(bar.iconsRight, `icons on screen at ${width}px`).toBeLessThanOrEqual(width)
      expect(bar.clearance, `page clearance at ${width}px`).toBe(clearance)
    }
  })

  test('scrolls the tabs sideways only, with room for the focus ring', async ({ page }) => {
    await openAt(page, 768, '/portal/requests')
    const bar = await barFacts(page)
    expect(bar.overflow).toBeGreaterThan(0)
    expect(bar.verticalOverflow).toBe(0)
    expect(bar.scrollbar).toBe('none')
    expect(bar.ringRoomAbove).toBeGreaterThanOrEqual(2)
    await expect(page.locator('nav.pt-bottom-nav')).toBeHidden()
  })

  test('shows the current tab whole when the page opens on it', async ({ page }) => {
    const tracker = await openAt(page, 768, '/portal/tickets')
    await expect.poll(() => roomRightOfActiveTab(page)).toBeGreaterThanOrEqual(2)
    const bar = await barFacts(page)
    expect(bar.overflow).toBeGreaterThan(0)
    expect(bar.activeLeft).toBeGreaterThanOrEqual(bar.tabsLeft)
    expect(tracker.unexpected).toEqual([])
  })

  test('shows the current tab whole after a click on one that is cut', async ({ page }) => {
    await openAt(page, 768, '/portal/requests')
    const before = await barFacts(page)
    expect(before.lastTabRight).toBeGreaterThan(before.tabsRight)

    // Not click(): Playwright would scroll the tab into view by itself first.
    const last = page.locator('.pt-tab').last()
    await last.dispatchEvent('click')

    await expect(last).toHaveClass(/pt-tab--active/)
    await expect.poll(() => roomRightOfActiveTab(page)).toBeGreaterThanOrEqual(2)
  })
})

test.describe('The top bar on a phone', () => {
  test.skip(({ isMobile }) => isMobile, 'set widths')

  for (const width of [320, 767]) {
    test(`keeps its icons on one row at ${width}px`, async ({ page }) => {
      await openAt(page, width, '/portal/requests')
      await expect(page.locator('.pt-nav-tabs')).toBeHidden()
      await expect(page.locator('nav.pt-bottom-nav')).toBeVisible()
      const icons = await page.evaluate(() =>
        [...document.querySelectorAll('.pt-nav-quick > *')]
          .filter(el => getComputedStyle(el).display !== 'none')
          .map(el => el.getBoundingClientRect())
          .map(box => ({ top: box.top, right: box.right })),
      )
      expect(icons.length).toBeGreaterThan(1)
      for (const icon of icons) {
        expect(icon.top).toBe(icons[0].top)
        expect(icon.right).toBeLessThanOrEqual(width)
      }
    })
  }
})
