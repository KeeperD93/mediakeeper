// Layout of the leaderboard: on a phone, the page stays as wide as the screen,
// whatever the names and totals of the fictional players, no figure is cut off,
// and the longest level title next to the longest chosen title stays inside its
// card. On every screen, the viewer appears once, with a label that stays whole
// and leaves their XP readable, and a link leads to a row far down the page.

import { test, expect } from '@playwright/test'
import { LEADERBOARD, openLeaderboard, viewerInList } from './_fixtures/portal-leaderboard-page.js'

// Each card of the page, with the titles it must keep inside.
const TITLES_BY_CARD = {
  '.lb-hero': '.lb-hero-meta',
  '.pt-lb-podium-card': '.pt-lb-podium-meta',
  '.lb-top-row': '.lb-top-row-title',
  '.gc-lb-row': '.gc-lb-tier',
}

// Every figure the page must keep inside the screen.
const FIGURES = [
  '.lb-hero-xp-unit',
  '.lb-hero-lead',
  '.lb-stats-chip',
  '.pt-lb-podium-xp',
  '.lb-my-rank-rank',
  '.lb-top-row-xp',
  '.gc-lb-v',
  '.lb-trophies',
]

// On each kind of row, what the trophies must not cover.
const TROPHY_NEIGHBOURS = {
  '.lb-top-row': ['.lb-top-row-name', '.lb-top-row-title', '.lb-top-row-move', '.lb-top-row-xp'],
  '.lb-rest .gc-lb-row': ['.gc-lb-n', '.gc-lb-tier', '.gc-lb-move', '.gc-lb-v'],
}

async function expectTrophiesApart(page) {
  const collisions = await page.evaluate(neighbours => {
    const visible = rect => rect.width > 0 && rect.height > 0
    const overlap = (a, b) =>
      visible(a) &&
      visible(b) &&
      a.left < b.right &&
      b.left < a.right &&
      a.top < b.bottom &&
      b.top < a.bottom
    const out = []
    for (const [rowSelector, selectors] of Object.entries(neighbours)) {
      const rows = [...document.querySelectorAll(rowSelector)]
      const withTrophies = rows.filter(row => row.querySelector('.lb-trophies'))
      if (!withTrophies.length) out.push(`${rowSelector} shows no trophies`)
      for (const row of withTrophies) {
        const trophies = row.querySelector('.lb-trophies').getBoundingClientRect()
        if (trophies.right > row.getBoundingClientRect().right) out.push(`${rowSelector} overflows`)
        for (const selector of selectors) {
          if (overlap(trophies, row.querySelector(selector).getBoundingClientRect())) {
            out.push(`${rowSelector} covers ${selector}`)
          }
        }
      }
    }
    return out
  }, TROPHY_NEIGHBOURS)
  expect(collisions).toEqual([])
}

// On a phone the trophies go under the XP of their row, aligned with it.
async function expectTrophiesUnderXp(page) {
  const rows = await page.evaluate(() => {
    const out = []
    for (const [rowSelector, xpSelector] of [
      ['.lb-top-row', '.lb-top-row-xp'],
      ['.lb-rest .gc-lb-row', '.gc-lb-v'],
    ]) {
      for (const row of document.querySelectorAll(rowSelector)) {
        const trophies = row.querySelector('.lb-trophies')?.getBoundingClientRect()
        if (!trophies) continue
        const xp = row.querySelector(xpSelector).getBoundingClientRect()
        out.push({
          top: trophies.top,
          right: trophies.right,
          xpBottom: xp.bottom,
          xpRight: xp.right,
        })
      }
    }
    return out
  })
  expect(rows.length).toBeGreaterThan(0)
  for (const row of rows) {
    expect(row.top).toBeGreaterThanOrEqual(row.xpBottom - 1)
    expect(Math.abs(row.right - row.xpRight)).toBeLessThanOrEqual(1)
  }
}

// The viewer with the long name, in each list of the page.
const VIEWER_ROWS = {
  'in the top ten': {
    body: viewerInList(6),
    row: '.lb-top-row--me',
    xp: '.lb-top-row-xp',
  },
  'below the top ten': {
    body: viewerInList(16),
    row: '.lb-rest .gc-lb-row--me',
    xp: '.gc-lb-v',
  },
}

// Each card of the podium, where the label stands apart from the XP.
const VIEWER_CARDS = {
  first: { body: viewerInList(0), card: '.lb-hero' },
  third: { body: viewerInList(2), card: '.pt-lb-podium-card.lb-metal--bronze' },
}

// The label sits before the XP, and nothing leaves its row or the screen.
async function expectViewerRowReadable(page, { row: rowSelector, xp }) {
  const row = page.locator(rowSelector)
  await expect(row.locator('.lb-me-pill')).toHaveText('VOUS')
  const boxes = await row.evaluate((el, xpSelector) => {
    const pill = el.querySelector('.lb-me-pill').getBoundingClientRect()
    const figure = el.querySelector(xpSelector).getBoundingClientRect()
    return {
      pillRight: pill.right,
      xpLeft: figure.left,
      xpRight: figure.right,
      rowRight: el.getBoundingClientRect().right,
      screenRight: document.documentElement.clientWidth,
    }
  }, xp)
  expect(boxes.pillRight).toBeLessThanOrEqual(boxes.xpLeft)
  expect(boxes.xpRight).toBeLessThanOrEqual(boxes.rowRight)
  expect(boxes.rowRight).toBeLessThanOrEqual(boxes.screenRight)
}

// The label stays inside the card, and the top bar does not repeat the viewer.
async function expectViewerCardLabelled(page, { card }) {
  await expect(page.locator(`${card} .lb-me-pill`)).toHaveText('VOUS')
  await expect(page.locator(card)).toHaveAccessibleName(/VOUS/)
  await expect(page.locator('.lb-my-rank')).toHaveCount(0)
  const boxes = await page.locator(card).evaluate(el => ({
    pillRight: el.querySelector('.lb-me-pill').getBoundingClientRect().right,
    cardRight: el.getBoundingClientRect().right,
  }))
  expect(boxes.pillRight).toBeLessThanOrEqual(boxes.cardRight)
}

async function expectLinkReachesMyRow(page) {
  await expect(page.locator('.lb-my-rank')).toHaveCount(0)
  const link = page.locator('.pt-lb-my-place')
  await expect(link).toHaveText('Voir ma place (#17)')
  await link.click()
  await expect(page.locator('#lb-my-row')).toBeInViewport()
  await expect(page.locator('#lb-my-row')).toBeFocused()
}

test.describe('Portal leaderboard on a large screen', () => {
  test.skip(({ isMobile }) => isMobile, 'large screen layout only')

  for (const [place, viewerCard] of Object.entries(VIEWER_CARDS)) {
    test(`labels a ${place} viewer on their card`, async ({ page }) => {
      const tracker = await openLeaderboard(page, 1280, viewerCard.body)
      await expectViewerCardLabelled(page, viewerCard)
      expect(tracker.unexpected).toEqual([])
    })
  }

  test('keeps the trophies apart from the rest of a row', async ({ page }) => {
    const tracker = await openLeaderboard(page, 1280, LEADERBOARD)
    await expectTrophiesApart(page)
    expect(tracker.unexpected).toEqual([])
  })

  test('leads a viewer below the top ten to their row', async ({ page }) => {
    const tracker = await openLeaderboard(page, 1280, VIEWER_ROWS['below the top ten'].body)
    await expectLinkReachesMyRow(page)
    expect(tracker.unexpected).toEqual([])
  })

  for (const [where, viewerRow] of Object.entries(VIEWER_ROWS)) {
    test(`keeps the XP of a viewer ${where} readable`, async ({ page }) => {
      const tracker = await openLeaderboard(page, 1280, viewerRow.body)
      await expectViewerRowReadable(page, viewerRow)
      expect(tracker.unexpected).toEqual([])
    })
  }
})

test.describe('Portal leaderboard on a phone', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone layout only')

  for (const width of [320, 375, 430, 767]) {
    for (const [place, viewerCard] of Object.entries(VIEWER_CARDS)) {
      test(`labels a ${place} viewer on their card at ${width}px`, async ({ page }) => {
        const tracker = await openLeaderboard(page, width, viewerCard.body)
        await expectViewerCardLabelled(page, viewerCard)
        expect(tracker.unexpected).toEqual([])
      })
    }

    test(`leads a viewer below the top ten to their row at ${width}px`, async ({ page }) => {
      const tracker = await openLeaderboard(page, width, VIEWER_ROWS['below the top ten'].body)
      await expectLinkReachesMyRow(page)
      expect(tracker.unexpected).toEqual([])
    })

    for (const [where, viewerRow] of Object.entries(VIEWER_ROWS)) {
      test(`keeps the XP of a viewer ${where} readable at ${width}px`, async ({ page }) => {
        const tracker = await openLeaderboard(page, width, viewerRow.body)
        await expectViewerRowReadable(page, viewerRow)
        expect(tracker.unexpected).toEqual([])
      })
    }

    test(`fits a ${width}px screen, every figure included`, async ({ page }) => {
      const tracker = await openLeaderboard(page, width, LEADERBOARD)
      await expectTrophiesApart(page)
      if (width <= 640) await expectTrophiesUnderXp(page)

      const overflowing = await page.evaluate(selectors => {
        const screenWidth = document.documentElement.clientWidth
        const root = document.querySelector('.pt-leaderboard')
        const out = root.getBoundingClientRect().right > screenWidth ? ['.pt-leaderboard'] : []
        for (const selector of selectors) {
          const elements = [...root.querySelectorAll(selector)]
          if (!elements.length) out.push(`${selector} is missing`)
          if (elements.some(el => el.getBoundingClientRect().right > screenWidth)) {
            out.push(selector)
          }
        }
        return out
      }, FIGURES)

      const titlesOutOfCard = await page.evaluate(titlesByCard => {
        const out = []
        for (const [cardSelector, titleSelector] of Object.entries(titlesByCard)) {
          for (const card of document.querySelectorAll(`.pt-leaderboard ${cardSelector}`)) {
            const box = card.getBoundingClientRect()
            const range = document.createRange()
            range.selectNodeContents(card.querySelector(titleSelector))
            const lines = [...range.getClientRects()]
            if (lines.some(line => line.right > box.right || line.left < box.left)) {
              out.push(titleSelector)
            }
          }
        }
        return out
      }, TITLES_BY_CARD)

      const figureColors = await page.evaluate(() =>
        ['.gc-lb-v', '.lb-top-row-xp', '.lb-my-rank-rank'].map(
          selector => getComputedStyle(document.querySelector(selector)).color,
        ),
      )

      expect(overflowing).toEqual([])
      expect(titlesOutOfCard).toEqual([])
      // The same readable blue everywhere, whatever the accent color of the theme.
      expect(new Set(figureColors).size).toBe(1)
      expect(tracker.unexpected).toEqual([])
    })
  }
})
