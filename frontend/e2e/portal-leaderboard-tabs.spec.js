// Period tabs of the leaderboard page, in a real browser: each tab brings its own
// figures, the last one clicked wins, the keyboard works and the row holds on a phone.

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { DEFAULT_VIEWER_PROFILE, mockAuthenticatedPortal } from './_fixtures/portal-auth-mocks.js'
import { LEADERBOARD, LEADERBOARD_ROUTE } from './_fixtures/portal-leaderboard-page.js'

const withLeaderXp = (xp, stats, movement = 2) => ({
  ...LEADERBOARD,
  items: LEADERBOARD.items.map((entry, index) => ({
    ...entry,
    period_xp: xp - index,
    movement,
  })),
  stats: { ...LEADERBOARD.stats, ...stats },
})

const SHORT_PERIOD = { days_remaining: null, my_delta_week: null, projected_end_rank: null }

const BY_PERIOD = {
  today: withLeaderXp(111, { period_label: 'Lundi 2 novembre', ...SHORT_PERIOD }),
  week: withLeaderXp(2222, { period_label: 'Du 2 au 8 novembre', ...SHORT_PERIOD }),
  month: withLeaderXp(33333, { period_label: 'Novembre 2026' }),
  all: withLeaderXp(444444, { period_label: 'Depuis le début', ...SHORT_PERIOD }, null),
}

const LABELS = { today: "Aujourd'hui", week: 'Semaine', month: 'Mois', all: 'Tout temps' }

async function openPage(page, { width = 1280, byPeriod = BY_PERIOD, delays = {} } = {}) {
  await page.setViewportSize({ width, height: 800 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.addInitScript(() => {
    window.localStorage.setItem('mediakeeper_locale', 'fr')
  })
  const asked = []
  await mockAuthenticatedPortal(page, {
    profile: { ...DEFAULT_VIEWER_PROFILE, language: 'fr' },
    pageHandlers: [
      {
        name: 'portal-leaderboard-activity',
        match: url => url.pathname === LEADERBOARD_ROUTE,
        handler: async route => {
          const url = new URL(route.request().url())
          const period = url.searchParams.get('period')
          asked.push(`${period}:${url.searchParams.get('limit')}`)
          if (delays[period]) await new Promise(resolve => setTimeout(resolve, delays[period]))
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(byPeriod[period]),
          })
        },
      },
    ],
  })
  await page.goto('/portal/leaderboard')
  await expect(page.getByRole('tab', { name: LABELS.month })).toHaveAttribute(
    'aria-selected',
    'true',
  )
  return asked
}

const heroXp = page => page.locator('.lb-hero-xp-value')
const chips = page => page.locator('.lb-stats-chip-text')
const tab = (page, period) => page.getByRole('tab', { name: LABELS[period] })

test.describe('Each tab brings its own figures', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen')

  test('the month opens first and is asked once', async ({ page }) => {
    const asked = await openPage(page)
    await expect(page.locator('h1')).toHaveText('Classement du mois')
    await expect(heroXp(page)).toHaveText('33,333')
    expect(asked).toEqual(['month:100'])
  })

  for (const [period, title, xp, chip] of [
    ['today', 'Classement du jour', '111', 'Lundi 2 novembre'],
    ['week', 'Classement de la semaine', '2,222', 'Du 2 au 8 novembre'],
    ['all', 'Classement de tous les temps', '444,444', 'Depuis le début'],
  ]) {
    test(`${period}: title, figures and band follow, days left go away`, async ({ page }) => {
      await openPage(page)
      await expect(page.locator('.lb-stats-progress')).toBeVisible()

      await tab(page, period).click()

      await expect(page.locator('h1')).toHaveText(title)
      await expect(heroXp(page)).toHaveText(xp)
      await expect(chips(page).first()).toHaveText(chip)
      await expect(page.locator('.lb-stats-progress')).toHaveCount(0)
      await expect(chips(page)).toHaveCount(4)
    })
  }

  test('all time shows no arrow, the other tabs do', async ({ page }) => {
    await openPage(page)
    await expect(page.locator('.gc-lb-move').first()).toBeVisible()

    await tab(page, 'all').click()
    await expect(heroXp(page)).toHaveText('444,444')
    await expect(page.locator('.gc-lb-move')).toHaveCount(0)

    await tab(page, 'week').click()
    await expect(heroXp(page)).toHaveText('2,222')
    await expect(page.locator('.gc-lb-move').first()).toBeVisible()
  })

  test('coming back to a tab uses what is already loaded', async ({ page }) => {
    const asked = await openPage(page)
    await tab(page, 'week').click()
    await expect(heroXp(page)).toHaveText('2,222')

    await tab(page, 'month').click()
    await expect(heroXp(page)).toHaveText('33,333')
    await expect(chips(page).first()).toHaveText('Novembre 2026')

    expect(asked).toEqual(['month:100', 'week:100'])
  })

  test('a slow tab left behind does not overwrite the last one clicked', async ({ page }) => {
    await openPage(page, { delays: { week: 400 } })
    await tab(page, 'week').click()
    await tab(page, 'all').click()
    await expect(heroXp(page)).toHaveText('444,444')

    await page.waitForTimeout(600)

    await expect(heroXp(page)).toHaveText('444,444')
    await expect(page.locator('h1')).toHaveText('Classement de tous les temps')
  })

  test('an empty period says so and keeps the tabs', async ({ page }) => {
    const byPeriod = {
      ...BY_PERIOD,
      today: { items: [], viewer_rank: null, viewer_entry: null, stats: BY_PERIOD.today.stats },
    }
    await openPage(page, { byPeriod })

    await tab(page, 'today').click()

    await expect(page.locator('.pt-lb-state')).toHaveText("Aucun joueur classé aujourd'hui.")
    await tab(page, 'month').click()
    await expect(heroXp(page)).toHaveText('33,333')
  })

  test('the viewer outside the list reads the XP of the tab, without the month outlook', async ({
    page,
  }) => {
    const week = { ...BY_PERIOD.week, stats: { ...BY_PERIOD.week.stats, my_xp: 77 } }
    await openPage(page, { byPeriod: { ...BY_PERIOD, week } })
    const card = page.locator('.lb-my-rank')
    await expect(card).toContainText('XP CE MOIS', { ignoreCase: true })
    await expect(card).toContainText('Projection', { ignoreCase: true })

    await tab(page, 'week').click()

    await expect(card).toContainText('XP cette semaine', { ignoreCase: true })
    await expect(card).toContainText('77')
    await expect(card).not.toContainText('Projection', { ignoreCase: true })
  })

  test('the keyboard moves between tabs and loads them', async ({ page }) => {
    await openPage(page)
    await tab(page, 'month').focus()

    await page.keyboard.press('ArrowRight')
    await expect(tab(page, 'all')).toBeFocused()
    await expect(heroXp(page)).toHaveText('444,444')

    await page.keyboard.press('ArrowRight')
    await expect(tab(page, 'today')).toBeFocused()
    await expect(heroXp(page)).toHaveText('111')

    await page.keyboard.press('End')
    await expect(tab(page, 'all')).toBeFocused()
    await page.keyboard.press('Home')
    await expect(tab(page, 'today')).toBeFocused()
  })

  test('Tab enters the row on the active tab and leaves it after', async ({ page }) => {
    await openPage(page)
    await tab(page, 'today').evaluate(element => {
      element.closest('[role="tablist"]').previousElementSibling.tabIndex = -1
      element.closest('[role="tablist"]').previousElementSibling.focus()
    })
    await page.keyboard.press('Tab')
    await expect(tab(page, 'month')).toBeFocused()
    await expect(tab(page, 'month')).toHaveCSS('outline-style', 'solid')
    await page.keyboard.press('Tab')
    await expect(page.locator('[role="tab"]:focus')).toHaveCount(0)
  })

  test('the row and its panel pass the accessibility checks', async ({ page }) => {
    await openPage(page)
    const roles = await new AxeBuilder({ page })
      .include('.lb-period-tabs')
      .include('[role="tabpanel"]')
      .withRules([
        'aria-allowed-role',
        'aria-required-children',
        'aria-required-parent',
        'aria-valid-attr-value',
        'button-name',
      ])
      .analyze()
    expect(roles.violations.map(violation => violation.id)).toEqual([])

    const contrast = await new AxeBuilder({ page })
      .include('.lb-period-tabs')
      .withRules(['color-contrast'])
      .analyze()
    expect(contrast.violations.map(violation => violation.id)).toEqual([])
  })
})

test.describe('The page keeps one width on a large screen', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen')

  // A short name here, the longest ones on the other tabs.
  const byPeriod = {
    ...BY_PERIOD,
    today: {
      ...BY_PERIOD.today,
      items: BY_PERIOD.today.items.map(entry => ({
        ...entry,
        display_name: 'Bob',
        selected_title: null,
      })),
    },
  }

  for (const width of [1024, 1280, 1366, 1920]) {
    test(`at ${width}px, a click moves neither the page nor the tabs`, async ({ page }) => {
      await openPage(page, { width, byPeriod })
      const facts = {}
      for (const period of Object.keys(LABELS)) {
        await tab(page, period).click()
        await expect(tab(page, period)).toHaveAttribute('aria-selected', 'true')
        await expect(page.locator('.lb-hero')).toBeVisible()
        facts[period] = await page.evaluate(() => ({
          page: document.querySelector('.pt-leaderboard').getBoundingClientRect().toJSON(),
          firstTab: document.querySelector('.lb-period-tab').getBoundingClientRect().left,
          note: document.querySelector('.pt-lb-note').getBoundingClientRect().height,
        }))
      }
      for (const fact of Object.values(facts)) {
        expect(fact.page.width).toBe(880)
        expect(fact.page.left).toBe(facts.month.page.left)
        expect(fact.firstTab).toBe(facts.month.firstTab)
        // The longest note stays on one line, like the shortest.
        expect(fact.note).toBe(facts.today.note)
      }
    })
  }
})

test.describe('The row holds on a phone', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone')

  for (const width of [320, 360, 375, 430]) {
    test(`at ${width}px, whichever tab is on: one line, inside the screen`, async ({ page }) => {
      await openPage(page, { width })
      for (const period of Object.keys(LABELS)) {
        await tab(page, period).click()
        await expect(tab(page, period)).toHaveAttribute('aria-selected', 'true')
        const facts = await page.locator('.lb-period-tab').evaluateAll(tabs => ({
          tops: new Set(tabs.map(item => Math.round(item.getBoundingClientRect().top))).size,
          right: Math.max(...tabs.map(item => item.getBoundingClientRect().right)),
          clipped: tabs.filter(item => item.scrollWidth > item.clientWidth).length,
          page: document.documentElement.scrollWidth,
        }))
        expect(facts.tops).toBe(1)
        expect(facts.right).toBeLessThanOrEqual(width)
        expect(facts.clipped).toBe(0)
        expect(facts.page).toBeLessThanOrEqual(width)
      }
    })
  }

  test('a finger gets 44 px on each tab', async ({ page }) => {
    await openPage(page, { width: 375 })
    const band = await tab(page, 'week').evaluate(element => {
      const style = getComputedStyle(element, '::after')
      return { height: style.height, position: style.position }
    })
    expect(band).toEqual({ height: '44px', position: 'absolute' })
    const box = await tab(page, 'week').boundingBox()
    const center = { x: box.x + box.width / 2, y: box.y + box.height / 2 }
    const hit = await page.evaluate(
      ({ x, y }) => document.elementFromPoint(x, y + 20)?.textContent?.trim(),
      center,
    )
    expect(hit).toBe(LABELS.week)
  })
})
