// Leaderboard on a phone: the page stays as wide as the screen, whatever the
// names and totals of the fictional players, no figure is cut off, and the
// longest level title next to the longest chosen title stays inside its card.
// On every screen, the viewer appears once, with a label that stays whole and
// leaves their XP readable, and a link leads to a row far down the page.

import { test, expect } from '@playwright/test'
import {
  DEFAULT_VIEWER_PROFILE,
  mockAuthenticatedPortal,
  portalLeaderboardHandlers,
} from './_fixtures/portal-auth-mocks.js'

const LONG_NAME = 'Alice-with-a-rather-long-display-name'
const LONGEST_LEVEL_TITLE = 'spectator'
const LONGEST_CHOSEN_TITLE = 'portal.titles.supremeCollector'

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
]

function buildEntry(index) {
  return {
    rank: index + 1,
    user_id: 1000 + index,
    display_name: index % 2 ? `Player ${index}` : LONG_NAME,
    avatar_url: null,
    level: 50,
    tier: 'gold',
    title_key: LONGEST_LEVEL_TITLE,
    month_xp: 1234567 - index * 1000,
    selected_title: LONGEST_CHOSEN_TITLE,
    title_tier: 6,
    is_current_user: false,
    movement: 2,
  }
}

const LEADERBOARD = {
  items: Array.from({ length: 20 }, (_, index) => buildEntry(index)),
  viewer_rank: 120,
  viewer_entry: { ...buildEntry(119), is_current_user: true },
  stats: {
    month_label: 'Novembre 2026',
    total_players: 1234,
    total_xp_month: 1234567,
    total_trophies_month: 1234,
    days_remaining: 28,
    my_xp_month: 1234,
    my_delta_week: 123,
    projected_end_rank: 12,
  },
}

function viewerInList(viewerIndex) {
  return {
    ...LEADERBOARD,
    items: LEADERBOARD.items.map((entry, index) => ({
      ...entry,
      is_current_user: index === viewerIndex,
    })),
    viewer_rank: null,
    viewer_entry: null,
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
  third: { body: viewerInList(2), card: '.pt-lb-podium-card--3' },
}

async function openLeaderboard(page, width, body) {
  await page.setViewportSize({ width, height: 800 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.addInitScript(() => {
    window.localStorage.setItem('mediakeeper_locale', 'fr')
  })
  const tracker = await mockAuthenticatedPortal(page, {
    profile: { ...DEFAULT_VIEWER_PROFILE, language: 'fr' },
    pageHandlers: portalLeaderboardHandlers(body),
  })
  await page.goto('/portal/leaderboard')
  await expect(page.locator('.lb-hero')).toBeVisible()
  return tracker
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
