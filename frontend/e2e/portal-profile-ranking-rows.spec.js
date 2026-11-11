// Rows of the ranking card of "My profile": the figures line up on every row, and the row
// of the viewer looks as it does on the leaderboard page.

import { test, expect } from '@playwright/test'
import { roomAroundFigures } from './_fixtures/portal-leaderboard-page.js'
import {
  BY_PERIOD,
  card,
  menu,
  MONTH,
  openProfile,
  tab,
} from './_fixtures/portal-profile-ranking.js'

// Short XP under a wider badge on some rows, the largest XP on others.
const FIGURES = [64, 133, 12345, 98, 7]
const mixedFigures = entries =>
  entries.map((entry, index) => ({
    ...entry,
    period_xp: FIGURES[index % FIGURES.length],
    trophies_won: index % 3 ? 14 : 0,
  }))
const mixedMonth = mixedFigures(MONTH)
const mixedPeriods = Object.fromEntries(
  Object.entries(BY_PERIOD).map(([period, body]) => [
    period,
    { ...body, items: mixedFigures(body.items) },
  ]),
)

const withViewer = (index, name) =>
  MONTH.map((entry, position) => ({
    ...entry,
    is_current_user: position === index,
    display_name: position === index && name ? name : entry.display_name,
  }))

// Every row the same way, the XP on one edge, the trophies under it, on the tab shown.
async function expectFigures(page, expected) {
  const rows = await card(page)
    .locator('.gc-lb-row')
    .evaluateAll(items =>
      items.map(row => {
        const box = selector => row.querySelector(selector).getBoundingClientRect()
        const range = document.createRange()
        range.selectNodeContents(row.querySelector('.gc-lb-v'))
        const text = range.getBoundingClientRect()
        return {
          beside: box('.gc-lb-v').top < box('.gc-lb-tier').top,
          name: box('.gc-lb-info').width,
          xpRight: text.right,
          xpBottom: text.bottom,
          inside: row.getBoundingClientRect().right - text.right,
          trophies: row.querySelector('.lb-trophies')?.getBoundingClientRect().toJSON() ?? null,
        }
      }),
    )
  expect(rows.length).toBeGreaterThan(0)
  const edges = rows.map(row => row.xpRight)
  expect(Math.max(...edges) - Math.min(...edges)).toBeLessThanOrEqual(1)
  // The same count makes the same badge: it does not stretch with the figures above it.
  const badges = rows.filter(row => row.trophies).map(row => row.trophies.width)
  expect(badges.length).toBeGreaterThan(0)
  expect(Math.max(...badges) - Math.min(...badges)).toBeLessThanOrEqual(1)
  for (const row of rows) {
    expect(row.beside).toBe(expected.beside)
    expect(row.name).toBeGreaterThanOrEqual(100)
    expect(row.inside).toBeGreaterThan(0)
    if (row.trophies) {
      expect(row.trophies.top).toBeGreaterThanOrEqual(row.xpBottom - 1)
      expect(Math.abs(row.trophies.right - row.xpRight)).toBeLessThanOrEqual(1)
    }
  }
}

async function expectFiguresOnEachPeriod(page, expected) {
  await expectFigures(page, expected)
  for (const [period, xp] of [
    ['today', '64 XP'],
    ['all', '64 XP'],
  ]) {
    if (await menu(page).isVisible()) await menu(page).selectOption(period)
    else await tab(page, period).click()
    await expect(card(page).locator('.gc-lb-v').first()).toHaveText(xp)
    await expectFigures(page, expected)
    if (expected.beside) {
      // Beside the name, the block sits in the middle of its row, whatever it holds.
      const room = await roomAroundFigures(page, '.gc-lb-box--tabs .gc-lb-row', '.gc-lb-v')
      expect(room.length).toBeGreaterThan(0)
      for (const row of room) expect(Math.abs(row.above - row.under)).toBeLessThanOrEqual(1)
    }
  }
}

// The label as wide as its word, the colored edge, no separator above the row.
async function expectViewerRow(page) {
  const row = card(page).locator('.gc-lb-row--me')
  await expect(row.locator('.lb-me-pill')).toHaveText('VOUS')
  const facts = await row.evaluate(element => {
    const pill = element.querySelector('.lb-me-pill')
    const box = pill.getBoundingClientRect()
    const range = document.createRange()
    range.selectNodeContents(pill)
    const name = element.querySelector('.gc-lb-n')
    const nameText = document.createRange()
    nameText.selectNodeContents(name)
    const swatch = document.createElement('i')
    swatch.style.color = 'var(--portal-accent-500)'
    swatch.style.backgroundColor = 'var(--portal-row-me-bg)'
    document.body.append(swatch)
    const accent = getComputedStyle(swatch).color
    const tint = getComputedStyle(swatch).backgroundColor
    swatch.remove()
    const style = getComputedStyle(element)
    return {
      tinted: style.backgroundColor === tint && tint !== 'rgba(0, 0, 0, 0)',
      medal: style.backgroundImage,
      levelBelow:
        element.querySelector('.gc-lb-tier').getBoundingClientRect().top >=
        name.getBoundingClientRect().bottom - 1,
      margin: box.width - range.getBoundingClientRect().width,
      after: box.left - name.getBoundingClientRect().left - name.getBoundingClientRect().width,
      sameLine: box.top < name.getBoundingClientRect().bottom,
      cut: name.scrollWidth > name.clientWidth,
      infoRight: element.querySelector('.gc-lb-info').getBoundingClientRect().right - box.right,
      edge: [style.borderLeftWidth, style.borderLeftColor === accent],
      dashes: getComputedStyle(element, '::before').content,
    }
  })
  // Its own small margins on each side, nothing more.
  expect(facts.margin).toBeLessThanOrEqual(10)
  expect(facts.infoRight).toBeGreaterThanOrEqual(0)
  expect(facts.levelBelow).toBe(true)
  expect(facts.tinted).toBe(true)
  expect(facts.edge).toEqual(['3px', true])
  expect(facts.dashes).toBe('none')
  return facts
}

test.describe('On a large screen', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen')

  for (const [width, beside] of [
    [1280, false],
    [1366, false],
    [1600, true],
    [1680, true],
    [1920, true],
    [1024, true],
  ]) {
    test(`at ${width}px, the figures of all rows go ${beside ? 'beside' : 'under'} the name`, async ({
      page,
    }) => {
      await openProfile(page, { width, month: mixedMonth, byPeriod: mixedPeriods })
      await expectFiguresOnEachPeriod(page, { beside })
    })
  }

  for (const width of [1280, 1600, 1920]) {
    test(`at ${width}px, the row of the viewer looks as on the leaderboard`, async ({ page }) => {
      await openProfile(page, { width, month: withViewer(5) })
      const facts = await expectViewerRow(page)
      expect(facts.cut).toBe(false)
      expect(facts.sameLine).toBe(true)
      expect(facts.after).toBeLessThanOrEqual(7)
    })
  }

  test('a long name is cut, the label goes under it and stays whole', async ({ page }) => {
    const name = 'Alice-with-a-rather-long-display-name'
    await openProfile(page, { width: 1280, month: withViewer(5, name) })
    const facts = await expectViewerRow(page)
    expect(facts.cut).toBe(true)
    expect(facts.sameLine).toBe(false)
  })

  test('no separator above the viewer, even outside the top', async ({ page }) => {
    await openProfile(page, { width: 1280 })
    await menu(page).selectOption('today')
    const row = card(page).locator('.gc-lb-row--me')
    await expect(row.locator('.gc-lb-n')).toHaveText('Alice')
    expect(await row.evaluate(element => getComputedStyle(element, '::before').content)).toBe(
      'none',
    )
  })

  test('the daily digest keeps its separator above a viewer after its top 3', async ({ page }) => {
    await openProfile(page, { width: 1280, month: withViewer(5) })
    const separator = await card(page).evaluate(box => {
      box.classList.add('gc-lb-box--widget')
      const style = getComputedStyle(box.querySelector('.gc-lb-row--me'), '::before')
      return { content: style.content, border: style.borderTopStyle }
    })
    expect(separator).toEqual({ content: '""', border: 'dashed' })
  })

  test('a viewer on the podium keeps the look of the viewer, not of the medal', async ({
    page,
  }) => {
    await openProfile(page, { width: 1280, month: withViewer(1) })
    const facts = await expectViewerRow(page)
    expect(facts.medal).toBe('none')
  })
})

test.describe('On a phone', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone')

  for (const [width, beside] of [
    [320, false],
    [360, false],
    [375, true],
    [430, true],
  ]) {
    test(`at ${width}px, the figures of all rows go ${beside ? 'beside' : 'under'} the name`, async ({
      page,
    }) => {
      await openProfile(page, { width, month: mixedMonth, byPeriod: mixedPeriods })
      await expectFiguresOnEachPeriod(page, { beside })
    })

    test(`at ${width}px, the row of the viewer looks as on the leaderboard`, async ({ page }) => {
      await openProfile(page, { width, month: withViewer(5) })
      await expectViewerRow(page)
    })
  }
})
