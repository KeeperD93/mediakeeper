// Period tabs of the leaderboard page, in a real browser: each tab brings its own
// figures, the last one clicked wins and the keyboard works.

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { BY_PERIOD, openTabs, tab } from './_fixtures/portal-leaderboard-tabs.js'

const heroXp = page => page.locator('.lb-hero-xp-value')
const chips = page => page.locator('.lb-stats-chip-text')

test.describe('Each tab brings its own figures', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen')

  test('the month opens first and is asked once', async ({ page }) => {
    const asked = await openTabs(page)
    await expect(page.locator('h1')).toHaveText('Classement du mois')
    await expect(heroXp(page)).toHaveText('33 333')
    expect(asked).toEqual(['month:100'])
  })

  for (const [period, title, xp, chip] of [
    ['today', 'Classement du jour', '111', 'Lundi 2 novembre'],
    ['week', 'Classement de la semaine', '2 222', 'Du 2 au 8 novembre'],
    ['all', 'Classement de tous les temps', '444 444', 'Depuis le début'],
  ]) {
    test(`${period}: title, figures and band follow, days left go away`, async ({ page }) => {
      await openTabs(page)
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
    await openTabs(page)
    await expect(page.locator('.gc-lb-move').first()).toBeVisible()

    await tab(page, 'all').click()
    await expect(heroXp(page)).toHaveText('444 444')
    await expect(page.locator('.gc-lb-move')).toHaveCount(0)

    await tab(page, 'week').click()
    await expect(heroXp(page)).toHaveText('2 222')
    await expect(page.locator('.gc-lb-move').first()).toBeVisible()
  })

  for (const [period, words] of [
    ['today', 'depuis hier'],
    ['week', 'depuis la semaine dernière'],
    ['month', 'depuis le mois dernier'],
  ]) {
    test(`${period}: every arrow names what it compares with`, async ({ page }) => {
      await openTabs(page)
      await tab(page, period).click()
      await expect(tab(page, period)).toHaveAttribute('aria-selected', 'true')
      await expect(page.locator('.lb-hero')).toBeVisible()

      for (const selector of ['.pt-lb-podium-move', '.lb-top-row-move', '.lb-rest .gc-lb-move']) {
        const titles = await page
          .locator(selector)
          .evaluateAll(moves => moves.map(move => move.title))
        expect(titles.length).toBeGreaterThan(0)
        for (const title of titles) expect(title).toContain(words)
      }
    })
  }

  test('coming back to a tab uses what is loaded, and every figure returns', async ({ page }) => {
    const asked = await openTabs(page)
    await tab(page, 'week').click()
    await expect(heroXp(page)).toHaveText('2 222')
    await expect(chips(page).nth(2)).toContainText('22 220')

    await tab(page, 'month').click()

    await expect(heroXp(page)).toHaveText('33 333')
    await expect(chips(page).first()).toHaveText('Novembre 2026')
    await expect(chips(page).nth(2)).toContainText('333 330')
    expect(asked).toEqual(['month:100', 'week:100'])
  })

  test('with animations on, a tab already seen changes in place', async ({ page }) => {
    await openTabs(page, { reducedMotion: 'no-preference' })
    await tab(page, 'week').click()
    await expect(page.locator('.lb-stats-bar')).toBeVisible()
    await tab(page, 'month').click()
    await expect(heroXp(page)).toHaveText('33 333', { timeout: 5000 })
    const bar = await page.locator('.lb-stats-bar').elementHandle()
    const hero = await page.locator('.lb-hero').elementHandle()

    await tab(page, 'week').click()

    await expect(heroXp(page)).toHaveText('2 222', { timeout: 5000 })
    await expect(chips(page).nth(2)).toContainText('22 220', { timeout: 5000 })
    await expect(page.locator('.lb-stats-bar')).toHaveCount(1)
    expect(await bar.evaluate(element => element.isConnected)).toBe(true)
    expect(await hero.evaluate(element => element.isConnected)).toBe(true)
  })

  test('a slow tab left behind does not overwrite the last one clicked', async ({ page }) => {
    await openTabs(page, { delays: { week: 400 } })
    await tab(page, 'week').click()
    await tab(page, 'all').click()
    await expect(heroXp(page)).toHaveText('444 444')

    await page.waitForTimeout(600)

    await expect(heroXp(page)).toHaveText('444 444')
    await expect(page.locator('h1')).toHaveText('Classement de tous les temps')
  })

  test('an empty period says so and keeps the tabs', async ({ page }) => {
    const byPeriod = {
      ...BY_PERIOD,
      today: { items: [], viewer_rank: null, viewer_entry: null, stats: BY_PERIOD.today.stats },
    }
    await openTabs(page, { byPeriod })

    await tab(page, 'today').click()

    await expect(page.locator('.pt-lb-state')).toHaveText("Aucun joueur classé aujourd'hui.")
    await tab(page, 'month').click()
    await expect(heroXp(page)).toHaveText('33 333')
  })

  test('the viewer outside the list reads the XP of the tab, without the month outlook', async ({
    page,
  }) => {
    const week = { ...BY_PERIOD.week, stats: { ...BY_PERIOD.week.stats, my_xp: 77 } }
    await openTabs(page, { byPeriod: { ...BY_PERIOD, week } })
    const card = page.locator('.lb-my-rank')
    await expect(card).toContainText('XP CE MOIS', { ignoreCase: true })
    await expect(card).toContainText('Projection', { ignoreCase: true })
    await expect(card).toContainText('+123 XP cette semaine', { ignoreCase: true })

    await tab(page, 'week').click()

    await expect(card).toContainText('XP cette semaine', { ignoreCase: true })
    await expect(card).toContainText('77')
    await expect(card).not.toContainText('Projection', { ignoreCase: true })
    await expect(card).not.toContainText('+', { ignoreCase: true })
  })

  test('the keyboard moves between tabs and loads them', async ({ page }) => {
    await openTabs(page)
    await tab(page, 'month').focus()

    await page.keyboard.press('ArrowRight')
    await expect(tab(page, 'all')).toBeFocused()
    await expect(heroXp(page)).toHaveText('444 444')

    await page.keyboard.press('ArrowRight')
    await expect(tab(page, 'today')).toBeFocused()
    await expect(heroXp(page)).toHaveText('111')

    await page.keyboard.press('End')
    await expect(tab(page, 'all')).toBeFocused()
    await page.keyboard.press('Home')
    await expect(tab(page, 'today')).toBeFocused()
  })

  test('Tab enters the row on the active tab and leaves it after', async ({ page }) => {
    await openTabs(page)
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
    await openTabs(page)
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
