// Periods of the ranking card of "My profile", in a real browser: what each one loads,
// what the card says while it does, and what a screen reader meets.

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import {
  BY_PERIOD,
  card,
  firstXp,
  LABELS,
  menu,
  openProfile,
  tab,
} from './_fixtures/portal-profile-ranking.js'

test.describe('Each period of the card', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen')

  test('the month opens from the profile, without a request', async ({ page }) => {
    const { asked, tracker } = await openProfile(page, { width: 1280 })
    await expect(firstXp(page)).toHaveText('33 333 XP')
    await expect(card(page).locator('.gc-lb-row')).toHaveCount(15)
    await expect(card(page).locator('.gc-box-title')).toHaveText('Classement')
    await expect(menu(page)).toHaveValue('month')
    expect(asked).toEqual([])
    expect(tracker.unexpected).toEqual([])
  })

  for (const [period, xp] of [
    ['today', '111 XP'],
    ['week', '2 222 XP'],
    ['all', '444 444 XP'],
  ]) {
    test(`${period} asks for 15 rows and shows them`, async ({ page }) => {
      const { asked } = await openProfile(page, { width: 1280 })
      await menu(page).selectOption(period)
      await expect(firstXp(page)).toHaveText(xp)
      expect(asked).toEqual([`${period}:15`])
    })
  }

  test('a viewer outside the top comes last, and not twice', async ({ page }) => {
    await openProfile(page, { width: 1280 })
    await menu(page).selectOption('today')
    await expect(card(page).locator('.gc-lb-row')).toHaveCount(16)
    const last = card(page).locator('.gc-lb-row').last()
    await expect(last).toHaveClass(/gc-lb-row--me/)
    await expect(last.locator('.gc-lb-pos')).toHaveText('42')
    await expect(last.locator('.gc-lb-n')).toHaveText('Alice')

    await menu(page).selectOption('week')
    await expect(firstXp(page)).toHaveText('2 222 XP')
    await expect(card(page).locator('.gc-lb-row')).toHaveCount(15)
    await expect(card(page).locator('.gc-lb-row--me')).toHaveCount(0)
  })

  test('all time shows no arrow, the other periods do', async ({ page }) => {
    await openProfile(page, { width: 1280 })
    await menu(page).selectOption('all')
    await expect(firstXp(page)).toHaveText('444 444 XP')
    await expect(card(page).locator('.gc-lb-move')).toHaveCount(0)

    await menu(page).selectOption('week')
    await expect(firstXp(page)).toHaveText('2 222 XP')
    await expect(card(page).locator('.gc-lb-move').first()).toBeVisible()
  })

  for (const [period, words] of [
    ['today', 'depuis hier'],
    ['week', 'depuis la semaine dernière'],
    ['month', 'depuis le mois dernier'],
  ]) {
    test(`${period}: every arrow names what it compares with`, async ({ page }) => {
      await openProfile(page, { width: 1280 })
      await menu(page).selectOption(period)
      await expect(card(page).locator('.gc-lb-move').first()).toBeVisible()
      const titles = await card(page)
        .locator('.gc-lb-move')
        .evaluateAll(moves => moves.map(move => move.title))
      expect(titles.length).toBeGreaterThan(0)
      for (const title of titles) expect(title).toContain(words)
    })
  }

  test('coming back uses what is loaded, the month without a request', async ({ page }) => {
    const { asked } = await openProfile(page, { width: 1280 })
    await menu(page).selectOption('week')
    await expect(firstXp(page)).toHaveText('2 222 XP')
    await menu(page).selectOption('month')
    await expect(firstXp(page)).toHaveText('33 333 XP')
    await menu(page).selectOption('week')
    await expect(firstXp(page)).toHaveText('2 222 XP')
    expect(asked).toEqual(['week:15'])
  })

  test('a period on its way says so, and the card can still change', async ({ page }) => {
    await openProfile(page, { width: 1280, delays: { week: 600 } })
    await menu(page).selectOption('week')
    await expect(card(page).locator('.gc-lb-state')).toHaveText('Chargement...')
    await expect(card(page).locator('.gc-lb-row')).toHaveCount(0)
    await menu(page).selectOption('month')
    await expect(firstXp(page)).toHaveText('33 333 XP')
    await expect(card(page).locator('.gc-lb-state')).toHaveCount(0)
  })

  test('a slow period left behind does not overwrite the last one chosen', async ({ page }) => {
    await openProfile(page, { width: 1280, delays: { week: 400 } })
    await menu(page).selectOption('week')
    await menu(page).selectOption('all')
    await expect(firstXp(page)).toHaveText('444 444 XP')
    await page.waitForTimeout(600)
    await expect(firstXp(page)).toHaveText('444 444 XP')
  })

  test('the viewer stays on an empty month, and can leave it', async ({ page }) => {
    await openProfile(page, { width: 1280, month: [] })
    await expect(card(page).locator('.gc-lb-state')).toHaveText('Aucun joueur classé ce mois.')
    await menu(page).selectOption('week')
    await expect(firstXp(page)).toHaveText('2 222 XP')
  })

  test('an empty period says so in its own words', async ({ page }) => {
    const byPeriod = {
      ...BY_PERIOD,
      today: { items: [], viewer_rank: null, viewer_entry: null, stats: null },
    }
    await openProfile(page, { width: 1280, byPeriod })
    await menu(page).selectOption('today')
    const state = card(page).locator('.gc-lb-state')
    await expect(state).toHaveText("Aucun joueur classé aujourd'hui.")
    await expect(state).toHaveCSS('padding-top', '24px')
  })

  test('the keyboard moves the tabs of a wide card and loads them', async ({ page }) => {
    await openProfile(page, { width: 1920 })
    await tab(page, 'month').focus()
    await page.keyboard.press('ArrowRight')
    await expect(tab(page, 'all')).toBeFocused()
    await expect(tab(page, 'all')).toHaveCSS('outline-style', 'solid')
    await expect(firstXp(page)).toHaveText('444 444 XP')
  })

  for (const [control, width] of [
    ['menu', 1280],
    ['tabs', 1920],
  ]) {
    test(`with the ${control}, the card passes the accessibility checks`, async ({ page }) => {
      await openProfile(page, { width })
      const roles = await new AxeBuilder({ page })
        .include('.gc-lb-box--tabs')
        .withRules([
          'aria-allowed-role',
          'aria-input-field-name',
          'aria-required-children',
          'aria-required-parent',
          'aria-valid-attr-value',
          'button-name',
          'select-name',
        ])
        .analyze()
      expect(roles.violations.map(violation => violation.id)).toEqual([])

      const contrast = await new AxeBuilder({ page })
        .include(control === 'menu' ? '.gc-lb-select' : '.lb-period-tabs')
        .withRules(['color-contrast'])
        .analyze()
      expect(contrast.violations.map(violation => violation.id)).toEqual([])
    })
  }

  test('a screen reader meets one control only', async ({ page }) => {
    await openProfile(page, { width: 1280 })
    await expect(card(page).getByRole('combobox')).toHaveCount(1)
    await expect(card(page).getByRole('tablist')).toHaveCount(0)
    await expect(card(page).getByRole('tabpanel')).toHaveAccessibleName(LABELS.month)
  })
})
